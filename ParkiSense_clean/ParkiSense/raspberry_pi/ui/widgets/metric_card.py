# =============================================================================
# ParkiSense — ui/widgets/metric_card.py
#
# Widget reutilizable: tarjeta de métrica con label, valor grande y subtítulo.
# Se usa para mostrar EMG RMS, HR BPM, Modo actual, etc.
# =============================================================================

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
import config


class MetricCard(QFrame):
    """
    Tarjeta visual que muestra una métrica con:
        - label superior (nombre de la métrica)
        - valor grande central (el número)
        - subtítulo inferior (unidad o estado)

    Uso:
        card = MetricCard("EMG RMS", "—", "μV", color=config.COLOR_EMG)
        card.set_value("247.3")
        card.set_subtitle("CONTRACTION", color="#66bb6a")
    """

    def __init__(self, label: str, value: str = "—", unit: str = "",
                 color: str = config.COLOR_TEXT, parent=None):
        super().__init__(parent)

        self._color = color

        # --- Estilo del frame ---
        self.setStyleSheet(f"""
            MetricCard {{
                background-color: {config.COLOR_BG_WIDGET};
                border: 1px solid {config.COLOR_BORDER};
                border-radius: 8px;
            }}
        """)

        # --- Layout ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        # Label superior
        self._label_widget = QLabel(label.upper())
        self._label_widget.setStyleSheet(f"""
            color: {config.COLOR_ACCENT};
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 1px;
        """)
        self._label_widget.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Valor central (grande)
        self._value_widget = QLabel(value)
        self._value_widget.setStyleSheet(f"""
            color: {color};
            font-size: 22px;
            font-weight: 700;
        """)
        self._value_widget.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Subtítulo / unidad
        self._unit_widget = QLabel(unit)
        self._unit_widget.setStyleSheet(f"""
            color: {config.COLOR_TEXT_DIM};
            font-size: 10px;
        """)
        self._unit_widget.setAlignment(Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(self._label_widget)
        layout.addWidget(self._value_widget)
        layout.addWidget(self._unit_widget)

    def set_value(self, text: str):
        """Actualiza el valor numérico mostrado."""
        self._value_widget.setText(text)

    def set_subtitle(self, text: str, color: str = None):
        """Actualiza el subtítulo y opcionalmente su color."""
        self._unit_widget.setText(text)
        if color:
            self._unit_widget.setStyleSheet(f"color: {color}; font-size: 10px;")

    def set_value_color(self, color: str):
        """Cambia el color del valor principal."""
        self._value_widget.setStyleSheet(f"""
            color: {color};
            font-size: 22px;
            font-weight: 700;
        """)
