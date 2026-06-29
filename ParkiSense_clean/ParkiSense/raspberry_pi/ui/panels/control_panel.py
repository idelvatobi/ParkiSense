# =============================================================================
# ParkiSense — ui/panels/control_panel.py
#
# Panel izquierdo: selector de puerto, botones de sesión, info en tiempo real.
# =============================================================================

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
import serial.tools.list_ports

import config
from ui.widgets.status_led import StatusLed


def _section_title(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(f"""
        color: {config.COLOR_ACCENT};
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 1.5px;
        padding-top: 8px;
    """)
    return lbl


def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color: {config.COLOR_BORDER};")
    return line


class ControlPanel(QWidget):
    connect_clicked    = pyqtSignal(str)
    disconnect_clicked = pyqtSignal()
    start_clicked      = pyqtSignal()
    end_clicked        = pyqtSignal()
    report_clicked     = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(210)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {config.COLOR_BG_PANEL};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Parki<b>Sense</b>")
        title.setStyleSheet(f"""
            color: {config.COLOR_EMG};
            font-size: 18px;
            font-weight: 300;
            letter-spacing: 1px;
        """)
        title.setTextFormat(Qt.TextFormat.RichText)
        version = QLabel(config.APP_VERSION)
        version.setStyleSheet(f"color: {config.COLOR_TEXT_DIM}; font-size: 9px;")

        layout.addWidget(title)
        layout.addWidget(version)
        layout.addWidget(_divider())

        layout.addWidget(_section_title("Conexion"))

        port_label = QLabel("Puerto serial")
        port_label.setStyleSheet(f"color: {config.COLOR_TEXT_DIM}; font-size: 10px;")
        layout.addWidget(port_label)

        self._port_combo = QComboBox()
        self._port_combo.setStyleSheet(f"""
            QComboBox {{
                background: {config.COLOR_BG_WIDGET};
                border: 1px solid {config.COLOR_BORDER};
                color: {config.COLOR_TEXT};
                padding: 4px 6px;
                border-radius: 4px;
                font-size: 10px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background: {config.COLOR_BG_WIDGET};
                color: {config.COLOR_TEXT};
                selection-background-color: {config.COLOR_ACCENT};
            }}
        """)
        self._refresh_ports()
        layout.addWidget(self._port_combo)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._btn_connect = self._make_btn("Connect", "#1b5e20", "#a5d6a7", "#2e7d32")
        self._btn_connect.clicked.connect(self._on_connect)
        self._btn_disconnect = self._make_btn("Disconnect", "#37474f", "#90a4ae", "#546e7a")
        self._btn_disconnect.clicked.connect(self.disconnect_clicked)
        self._btn_disconnect.setEnabled(False)

        btn_row.addWidget(self._btn_connect)
        btn_row.addWidget(self._btn_disconnect)
        layout.addLayout(btn_row)

        self._conn_led = StatusLed("Desconectado", "#ef5350")
        layout.addWidget(self._conn_led)

        layout.addWidget(_divider())

        layout.addWidget(_section_title("Sesion"))

        self._btn_start = self._make_btn("Start Session", "#0d47a1", "#90caf9", "#1565c0")
        self._btn_start.clicked.connect(self.start_clicked)
        self._btn_start.setEnabled(False)

        self._btn_end = self._make_btn("End Session", "#b71c1c", "#ef9a9a", "#c62828")
        self._btn_end.clicked.connect(self.end_clicked)
        self._btn_end.setEnabled(False)

        self._btn_report = self._make_btn("Generate Report", "#4a148c", "#ce93d8", "#6a1b9a")
        self._btn_report.clicked.connect(self.report_clicked)
        self._btn_report.setEnabled(False)

        self._btn_save = self._make_btn("Save Session", "#e65100", "#ffcc80", "#f57c00")
        self._btn_save.setEnabled(False)

        layout.addWidget(self._btn_start)
        layout.addWidget(self._btn_end)
        layout.addWidget(self._btn_report)
        layout.addWidget(self._btn_save)

        layout.addWidget(_divider())

        layout.addWidget(_section_title("Estado"))
        self._info_frame = _InfoBlock()
        layout.addWidget(self._info_frame)

        layout.addStretch()

        btn_refresh = QPushButton("Refrescar puertos")
        btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {config.COLOR_TEXT_DIM};
                border: 1px solid {config.COLOR_BORDER};
                border-radius: 4px;
                padding: 4px;
                font-size: 10px;
            }}
            QPushButton:hover {{ background: {config.COLOR_BG_WIDGET}; }}
        """)
        btn_refresh.clicked.connect(self._refresh_ports)
        layout.addWidget(btn_refresh)

    def set_connected(self, connected: bool, msg: str = ""):
        if connected:
            self._conn_led.set_state(msg or "Conectado", "#66bb6a")
            self._btn_connect.setEnabled(False)
            self._btn_disconnect.setEnabled(True)
            self._btn_start.setEnabled(True)
        else:
            self._conn_led.set_state(msg or "Desconectado", "#ef5350")
            self._btn_connect.setEnabled(True)
            self._btn_disconnect.setEnabled(False)
            self._btn_start.setEnabled(False)
            self._btn_end.setEnabled(False)

    def set_session_active(self, active: bool):
        self._btn_start.setEnabled(not active)
        self._btn_end.setEnabled(active)
        self._btn_report.setEnabled(False)
        self._btn_save.setEnabled(not active)

    def set_report_ready(self, ready: bool):
        self._btn_report.setEnabled(ready)

    def update_info(self, **kwargs):
        self._info_frame.update_values(**kwargs)

    def _on_connect(self):
        port = self._port_combo.currentText()
        self.connect_clicked.emit(port)

    def _refresh_ports(self):
        self._port_combo.clear()
        if config.DEMO_MODE:
            self._port_combo.addItem("DEMO (simulado)")
            return
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if ports:
            for p in ports:
                self._port_combo.addItem(p)
        else:
            self._port_combo.addItem(config.SERIAL_PORT)

    @staticmethod
    def _make_btn(text: str, bg: str, fg: str, border: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 7px 10px;
                font-size: 11px;
                font-weight: 600;
                text-align: left;
            }}
            QPushButton:hover {{ background: {border}; }}
            QPushButton:disabled {{ opacity: 0.4; }}
        """)
        return btn


class _InfoBlock(QWidget):
    _ROWS = [
        ("mode",         "Modo",         "-",     config.COLOR_TEXT),
        ("emg_state",    "EMG state",    "-",     config.COLOR_TEXT),
        ("contractions", "Contracciones","0",     config.COLOR_EMG),
        ("hr_valid",     "HR valida",    "-",     config.COLOR_TEXT),
        ("duration",     "Duracion",     "00:00", "#ffd54f"),
        ("events",       "Eventos",      "0",     config.COLOR_TEXT),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            background: {config.COLOR_BG_WIDGET};
            border-radius: 6px;
            border: 1px solid {config.COLOR_BORDER};
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self._labels = {}
        for key, name, default, color in self._ROWS:
            row = QHBoxLayout()
            lbl_key = QLabel(name)
            lbl_key.setStyleSheet(f"color: {config.COLOR_ACCENT}; font-size: 10px;")
            lbl_val = QLabel(default)
            lbl_val.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 600;")
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(lbl_key)
            row.addWidget(lbl_val)
            layout.addLayout(row)
            self._labels[key] = lbl_val

    def update_values(self, **kwargs):
        mapping = {
            "mode":         ("mode",         lambda v: (v, config.COLOR_ACCENT)),
            "emg_state":    ("emg_state",    lambda v: (v, "#66bb6a" if v == "CONTRACTION" else "#78909c")),
            "contractions": ("contractions", lambda v: (str(v), config.COLOR_EMG)),
            "hr_valid":     ("hr_valid",     lambda v: ("Si OK" if v else "No", "#66bb6a" if v else "#ef5350")),
            "duration":     ("duration",     lambda v: (v, "#ffd54f")),
            "events":       ("events",       lambda v: (str(v), config.COLOR_TEXT)),
        }
        for key, value in kwargs.items():
            if key in mapping:
                label_key, formatter = mapping[key]
                if label_key in self._labels:
                    text, color = formatter(value)
                    self._labels[label_key].setText(text)
                    self._labels[label_key].setStyleSheet(
                        f"color: {color}; font-size: 11px; font-weight: 600;"
                    )
