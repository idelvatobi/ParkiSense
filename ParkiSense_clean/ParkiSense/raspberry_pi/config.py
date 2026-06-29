# =============================================================================
# ParkiSense -- config.py
# Configuracion central de la aplicacion. Modifica aqui los parametros
# antes de correr la app en la Raspberry Pi.
# =============================================================================

# ---------------------------------------------------------------------------
# SERIAL
# ---------------------------------------------------------------------------
SERIAL_PORT  = "/dev/ttyACM0"   # Cambia a /dev/ttyACM0 si es necesario
BAUD_RATE    = 115200
SERIAL_TIMEOUT = 1              # segundos

# ---------------------------------------------------------------------------
# MODO DEMO
# Ponlo a True para probar la app SIN Arduino (datos simulados).
# Ponlo a False cuando estes conectado al Arduino real.
# ---------------------------------------------------------------------------
DEMO_MODE = False

# ---------------------------------------------------------------------------
# GRAFICAS EN TIEMPO REAL
# ---------------------------------------------------------------------------
CHART_MAX_POINTS = 200          # Cuantos puntos de historia se muestran
CHART_UPDATE_MS  = 80           # Cada cuantos ms se redibuja la grafica (~12 fps)

EMG_Y_MIN = 0
EMG_Y_MAX = 600
HR_Y_MIN  = 40
HR_Y_MAX  = 140

# ---------------------------------------------------------------------------
# TEMA VISUAL (colores del dashboard)
# ---------------------------------------------------------------------------
COLOR_BG_DARK    = "#0f1117"
COLOR_BG_PANEL   = "#1a1d2e"
COLOR_BG_WIDGET  = "#252840"
COLOR_BORDER     = "#3d3f6e"
COLOR_ACCENT     = "#5c6bc0"
COLOR_TEXT       = "#e8eaf6"
COLOR_TEXT_DIM   = "#9fa8da"

COLOR_EMG        = "#42a5f5"    # azul
COLOR_HR         = "#ef5350"    # rojo
COLOR_REST       = "#78909c"    # gris
COLOR_CONTRACT   = "#66bb6a"    # verde
COLOR_LOW        = "#42a5f5"
COLOR_MODERATE   = "#ffd54f"
COLOR_HIGH       = "#66bb6a"

# ---------------------------------------------------------------------------
# OLLAMA / AI AGENT (Fase 4)
# El agente envia features + prediccion ML al LLM local y devuelve un
# report humano: classification + summary + feedback.
# ---------------------------------------------------------------------------
OLLAMA_HOST        = "http://localhost:11434"   # Pi: localhost. Remoto: http://192.168.x.x:11434
OLLAMA_MODEL       = "llama3.2:1b"              # Modelo ligero, validado en Pi
OLLAMA_TIMEOUT     = 600                         # segundos (Pi puede tardar 1-2 min)
AI_REPORT_LANGUAGE = "english"                   # "english" | "spanish"
AI_REPORT_FILENAME = "session_report.txt"        # Nombre del fichero por sesion

# ---------------------------------------------------------------------------
# APP
# ---------------------------------------------------------------------------
APP_NAME    = "ParkiSense Dashboard"
APP_VERSION = "v2.0 -- Phase 4 (AI Agent)"
WINDOW_W    = 1280
WINDOW_H    = 780
