# =============================================================================
# ParkiSense — ui/widgets/status_led.py
#
# Indicador LED pequeño con texto. Simula el LED físico del Arduino.
# =============================================================================

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt


class StatusLed(QWidget):
    """
    LED de estado: círculo de color + texto.
    Uso:
        led = StatusLed("Conectado", "#66bb6a")
        led.set_state("Desconectado", "#ef5350")
    """

    def __init__(self, text: str = "", color: str = "#78909c", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._dot = QLabel("●")
        self._dot.setStyleSheet(f"color: {color}; font-size: 12px;")
        self._dot.setFixedWidth(14)

        self._text = QLabel(text)
        self._text.setStyleSheet("color: #9fa8da; font-size: 11px;")

        layout.addWidget(self._dot)
        layout.addWidget(self._text)
        layout.addStretch()

    def set_state(self, text: str, color: str):
        self._dot.setStyleSheet(f"color: {color}; font-size: 12px;")
        self._text.setText(text)
