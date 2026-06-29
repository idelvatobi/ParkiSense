# =============================================================================
# ParkiSense — ui/panels/monitoring_panel.py
#
# Panel central: fila de MetricCards + dos gráficas en tiempo real (pyqtgraph).
# Toda la actualización de datos pasa por métodos públicos llamados desde
# MainWindow — este panel no sabe nada del serial ni del hilo.
# =============================================================================

from collections import deque

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
)

import config
from ui.widgets.metric_card import MetricCard


# ---------------------------------------------------------------------------
# Configuración global de pyqtgraph (se aplica una sola vez)
# ---------------------------------------------------------------------------
pg.setConfigOption("background", config.COLOR_BG_WIDGET)
pg.setConfigOption("foreground", config.COLOR_TEXT_DIM)
pg.setConfigOptions(antialias=True)


class MonitoringPanel(QWidget):
    """
    Panel de monitorización en tiempo real.

    Método principal de entrada de datos:
        update_emg(emg_rms, emg_raw, emg_state)
        update_hr(hr_raw, hr_filtered, hr_valid)
        set_mode(mode_str)
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Buffers circulares para las gráficas
        self._emg_buf = deque([0.0] * config.CHART_MAX_POINTS,
                              maxlen=config.CHART_MAX_POINTS)
        self._hr_buf  = deque([75.0] * config.CHART_MAX_POINTS,
                              maxlen=config.CHART_MAX_POINTS)

        self._build_ui()

        # Timer que redibuja las gráficas a ~12 fps
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_charts)
        self._timer.start(config.CHART_UPDATE_MS)

    # ------------------------------------------------------------------
    # Construcción de la UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(10)

        # ── Fila de MetricCards ───────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(8)

        self._card_emg_rms   = MetricCard("EMG RMS",     "—",   "μV",   config.COLOR_EMG)
        self._card_emg_raw   = MetricCard("EMG Raw Avg", "—",   "ADC",  config.COLOR_EMG)
        self._card_emg_state = MetricCard("EMG State",   "—",   "",     "#78909c")
        self._card_hr_raw    = MetricCard("HR Raw",      "—",   "BPM",  config.COLOR_HR)
        self._card_hr_filt   = MetricCard("HR Filtered", "—",   "BPM",  config.COLOR_HR)
        self._card_mode      = MetricCard("Modo activo", "—",   "",     config.COLOR_ACCENT)

        for card in (self._card_emg_rms, self._card_emg_raw, self._card_emg_state,
                     self._card_hr_raw, self._card_hr_filt, self._card_mode):
            cards_row.addWidget(card)

        main_layout.addLayout(cards_row)

        # ── Gráficas en tiempo real ───────────────────────────────────
        charts_row = QHBoxLayout()
        charts_row.setSpacing(8)

        self._emg_plot = self._make_chart(
            title="📈  EMG RMS — Tiempo real",
            y_label="μV",
            y_min=config.EMG_Y_MIN,
            y_max=config.EMG_Y_MAX
        )
        self._hr_plot = self._make_chart(
            title="❤  HR BPM — Tiempo real",
            y_label="BPM",
            y_min=config.HR_Y_MIN,
            y_max=config.HR_Y_MAX
        )

        # Curvas
        self._emg_curve = self._emg_plot.plot(
            pen=pg.mkPen(config.COLOR_EMG, width=2)
        )
        self._hr_curve = self._hr_plot.plot(
            pen=pg.mkPen(config.COLOR_HR, width=2)
        )

        # Fill bajo la curva EMG
        self._emg_fill = pg.FillBetweenItem(
            self._emg_curve,
            self._emg_plot.plot(
                [0] * config.CHART_MAX_POINTS,
                pen=pg.mkPen(None)
            ),
            brush=pg.mkBrush(66, 165, 245, 25)
        )
        self._emg_plot.addItem(self._emg_fill)

        # Fill bajo la curva HR
        self._hr_fill = pg.FillBetweenItem(
            self._hr_curve,
            self._hr_plot.plot(
                [config.HR_Y_MIN] * config.CHART_MAX_POINTS,
                pen=pg.mkPen(None)
            ),
            brush=pg.mkBrush(239, 83, 80, 25)
        )
        self._hr_plot.addItem(self._hr_fill)

        # Línea horizontal de referencia en HR (80 BPM)
        ref_line = pg.InfiniteLine(
            pos=80, angle=0,
            pen=pg.mkPen("#ffd54f", width=1, style=pg.QtCore.Qt.PenStyle.DashLine)
        )
        self._hr_plot.addItem(ref_line)

        emg_container = self._wrap_chart(self._emg_plot)
        hr_container  = self._wrap_chart(self._hr_plot)

        charts_row.addWidget(emg_container)
        charts_row.addWidget(hr_container)
        main_layout.addLayout(charts_row)

    # ------------------------------------------------------------------
    # API pública — entrada de datos
    # ------------------------------------------------------------------

    def update_emg(self, emg_rms: float, emg_raw: float, emg_state: str):
        """Llamar cada vez que llega un sample EMG del hilo serial."""
        self._emg_buf.append(emg_rms)

        self._card_emg_rms.set_value(f"{emg_rms:.1f}")
        self._card_emg_raw.set_value(f"{emg_raw:.0f}")

        if emg_state == "CONTRACTION":
            self._card_emg_state.set_value("CONTRACTION")
            self._card_emg_state.set_value_color("#66bb6a")
            self._card_emg_state.set_subtitle("● activo", "#66bb6a")
        else:
            self._card_emg_state.set_value("REST")
            self._card_emg_state.set_value_color("#78909c")
            self._card_emg_state.set_subtitle("● reposo", "#78909c")

    def update_hr(self, hr_raw: float, hr_filtered: float, hr_valid: bool):
        """Llamar cada vez que llega un sample HR del hilo serial."""
        self._hr_buf.append(hr_filtered)

        self._card_hr_raw.set_value(f"{hr_raw:.1f}")
        self._card_hr_filt.set_value(f"{hr_filtered:.1f}")

        valid_color = "#66bb6a" if hr_valid else "#ef5350"
        valid_text  = "✓ válida" if hr_valid else "✗ inválida"
        self._card_hr_filt.set_subtitle(valid_text, valid_color)

    def set_mode(self, mode: str):
        """Actualiza la tarjeta de modo activo."""
        colors = {
            "EMG":     config.COLOR_EMG,
            "HR":      config.COLOR_HR,
            "WELCOME": config.COLOR_ACCENT,
            "OFF":     "#78909c",
        }
        color = colors.get(mode.upper(), config.COLOR_TEXT)
        self._card_mode.set_value(mode.upper())
        self._card_mode.set_value_color(color)

    # ------------------------------------------------------------------
    # Timer: redibuja las gráficas
    # ------------------------------------------------------------------

    def _refresh_charts(self):
        emg_arr = np.array(self._emg_buf, dtype=float)
        hr_arr  = np.array(self._hr_buf,  dtype=float)

        self._emg_curve.setData(emg_arr)
        self._hr_curve.setData(hr_arr)

    # ------------------------------------------------------------------
    # Helpers para construir las gráficas
    # ------------------------------------------------------------------

    @staticmethod
    def _make_chart(title: str, y_label: str, y_min: float, y_max: float) -> pg.PlotWidget:
        plot = pg.PlotWidget()
        plot.setTitle(title, color=config.COLOR_TEXT_DIM, size="10pt")
        plot.setLabel("left", y_label, color=config.COLOR_TEXT_DIM)
        plot.setYRange(y_min, y_max)
        plot.setXRange(0, config.CHART_MAX_POINTS)
        plot.showGrid(x=True, y=True, alpha=0.15)
        plot.getPlotItem().hideAxis("bottom")

        # Borde redondeado del widget
        plot.setStyleSheet(f"""
            border: 1px solid {config.COLOR_BORDER};
            border-radius: 8px;
        """)
        return plot

    @staticmethod
    def _wrap_chart(plot: pg.PlotWidget) -> QFrame:
        """Envuelve la gráfica en un QFrame con fondo y borde."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: {config.COLOR_BG_WIDGET};
                border: 1px solid {config.COLOR_BORDER};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(plot)
        return frame
