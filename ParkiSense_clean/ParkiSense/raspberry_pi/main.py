#!/usr/bin/env python3
# =============================================================================
# ParkiSense -- main.py
#
# Punto de entrada de la aplicacion.
# Ejecutar con:  python main.py
#
# Asegurate de tener instaladas las dependencias:
#   pip install -r requirements.txt
#
# Para probar sin Arduino:  DEMO_MODE = True en config.py
# Para usar el Arduino:     DEMO_MODE = False y ajusta SERIAL_PORT
# =============================================================================

import sys
import os

# Anade el directorio raiz al path para que los imports funcionen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

import config
from ui.main_window import MainWindow


def apply_global_stylesheet(app: QApplication):
    """Aplica el tema oscuro global a toda la aplicacion."""
    app.setStyleSheet(f"""
        * {{
            font-family: 'Segoe UI', 'Inter', 'Ubuntu', system-ui, sans-serif;
        }}
        QToolTip {{
            background-color: {config.COLOR_BG_WIDGET};
            color: {config.COLOR_TEXT};
            border: 1px solid {config.COLOR_ACCENT};
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
        }}
        QScrollBar:vertical {{
            background: {config.COLOR_BG_DARK};
            width: 8px;
        }}
        QScrollBar::handle:vertical {{
            background: {config.COLOR_BORDER};
            border-radius: 4px;
        }}
    """)


def main():
    # Habilitar High DPI (importante para pantallas de Raspberry Pi)
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)

    # Fuente base de la app
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    apply_global_stylesheet(app)

    window = MainWindow()
    window.show()

    print("\n" + "=" * 60)
    print(f"  {config.APP_NAME}  {config.APP_VERSION}")
    serial_mode = "DEMO (sin Arduino)" if config.DEMO_MODE else f"REAL -> {config.SERIAL_PORT}"
    print(f"  Modo serial : {serial_mode}")
    print(f"  Ollama      : {config.OLLAMA_HOST}  |  modelo {config.OLLAMA_MODEL}")
    print(f"  Idioma AI   : {config.AI_REPORT_LANGUAGE}")
    print("=" * 60 + "\n")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
