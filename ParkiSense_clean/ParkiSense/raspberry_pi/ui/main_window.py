# =============================================================================
# ParkiSense -- ui/main_window.py  (Fase 4)
# =============================================================================

import os
import time

from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QLabel, QMessageBox
from PyQt6.QtCore import Qt, QTimer

import config
from serial_comm import SerialReaderThread, EMGData, HRData, EventData
from data_processing import SessionManager
from data_processing.feature_extractor import extract_features
from ml import MLInference
from ui.panels.control_panel import ControlPanel
from ui.panels.monitoring_panel import MonitoringPanel
from ui.panels.ml_result_dialog import MLResultDialog


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self._base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        sessions_dir = os.path.join(self._base_dir, "data", "sessions")
        self._session = SessionManager(sessions_dir)

        self._last_session_info = None
        self._serial_thread = None
        self._connected = False
        self._current_mode = "-"
        self._emg_count = 0
        self._hr_count = 0

        # Cargar modelo ML una sola vez
        model_path    = os.path.join(self._base_dir, "ml", "models", "random_forest_model.pkl")
        features_path = os.path.join(self._base_dir, "ml", "models", "rf_feature_columns.json")
        try:
            self._ml = MLInference(model_path, features_path)
            print("[MainWindow] Modelo ML cargado correctamente")
        except Exception as e:
            print(f"[MainWindow] Modelo ML no disponible: {e}")
            self._ml = None

        self._build_window()
        self._connect_signals()
        self._start_clock()

        if config.DEMO_MODE:
            QTimer.singleShot(500, lambda: self._on_connect("DEMO"))

    def _build_window(self):
        self.setWindowTitle(f"{config.APP_NAME}  --  {config.APP_VERSION}")
        self.resize(config.WINDOW_W, config.WINDOW_H)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background-color: {config.COLOR_BG_DARK}; color: {config.COLOR_TEXT}; }}
            QStatusBar {{ background-color: {config.COLOR_BG_WIDGET}; color: {config.COLOR_TEXT_DIM}; font-size: 10px; border-top: 1px solid {config.COLOR_BORDER}; }}
        """)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._control    = ControlPanel()
        self._monitoring = MonitoringPanel()
        self._control.setStyleSheet(self._control.styleSheet() + f"border-right: 1px solid {config.COLOR_BORDER};")
        root.addWidget(self._control)
        root.addWidget(self._monitoring, stretch=1)

        self._sb_port    = QLabel("Puerto: -")
        self._sb_session = QLabel("Sesion: inactiva")
        self._sb_samples = QLabel("EMG: 0  |  HR: 0")
        self._sb_mode    = QLabel("Modo: -")
        for lbl in (self._sb_port, self._sb_session, self._sb_samples, self._sb_mode):
            lbl.setStyleSheet(f"color: {config.COLOR_TEXT_DIM}; padding: 0 12px;")
            self.statusBar().addPermanentWidget(lbl)

        ml_status = "ML listo" if self._ml else "ML no disponible"
        self.statusBar().showMessage(
            f"Bienvenido a ParkiSense  -  {'Modo DEMO' if config.DEMO_MODE else config.SERIAL_PORT}  -  {ml_status}"
        )

    def _connect_signals(self):
        self._control.connect_clicked.connect(self._on_connect)
        self._control.disconnect_clicked.connect(self._on_disconnect)
        self._control.start_clicked.connect(self._on_start_session)
        self._control.end_clicked.connect(self._on_end_session)
        self._control.report_clicked.connect(self._on_generate_report)

    def _start_clock(self):
        self._clock = QTimer(self)
        self._clock.timeout.connect(self._tick)
        self._clock.start(1000)

    def _tick(self):
        if self._session.is_active:
            elapsed = int(self._session.elapsed_seconds)
            m, s = divmod(elapsed, 60)
            self._control.update_info(duration=f"{m:02d}:{s:02d}")

    # ------------------------------------------------------------------
    # Conexion serial
    # ------------------------------------------------------------------

    def _on_connect(self, port):
        if self._serial_thread and self._serial_thread.isRunning():
            return
        self._serial_thread = SerialReaderThread(port=None if config.DEMO_MODE else port)
        self._serial_thread.emg_received.connect(self._handle_emg)
        self._serial_thread.hr_received.connect(self._handle_hr)
        self._serial_thread.event_received.connect(self._handle_event)
        self._serial_thread.connection_status.connect(self._handle_conn_status)
        self._serial_thread.start()
        self._sb_port.setText(f"Puerto: {port}")

    def _on_disconnect(self):
        if self._serial_thread:
            self._serial_thread.stop()
            self._serial_thread = None
        self._connected = False
        self._control.set_connected(False, "Desconectado")
        self._sb_port.setText("Puerto: -")

    # ------------------------------------------------------------------
    # Sesion
    # ------------------------------------------------------------------

    def _on_start_session(self):
        session_id = self._session.start()
        self._emg_count = 0
        self._hr_count  = 0
        self._control.set_session_active(True)
        self._control.update_info(contractions=0, events=0, duration="00:00")
        self._sb_session.setText("Sesion: ACTIVA")
        self._sb_samples.setText("EMG: 0  |  HR: 0")
        self.statusBar().showMessage(f"Sesion iniciada -- guardando en data/sessions/{session_id}/")

    def _on_end_session(self):
        resumen = self._session.end()
        self._control.set_session_active(False)

        if resumen:
            dur  = resumen.get("duration_s", 0)
            m, s = divmod(int(dur), 60)
            emg_c = resumen.get("emg_count", 0)
            hr_c  = resumen.get("hr_count", 0)
            contr = resumen.get("contractions", 0)
            sid   = resumen.get("session_id", "")

            self._last_session_info = resumen

            if self._ml is not None:
                self._control.set_report_ready(True)

            self._sb_session.setText("Sesion: guardada")
            self.statusBar().showMessage(
                f"Sesion guardada  -  {m:02d}:{s:02d}  -  EMG:{emg_c}  HR:{hr_c}  Contr:{contr}"
                + ("  --  Pulsa Generate Report" if self._ml else "")
            )

            msg = QMessageBox(self)
            msg.setWindowTitle("Sesion guardada")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText(
                f"<b>Sesion {sid} guardada.</b><br><br>"
                f"Duracion: {m:02d}:{s:02d}<br>"
                f"EMG: {emg_c} muestras  |  HR: {hr_c} muestras<br>"
                f"Contracciones: {contr}<br><br>"
                f"Carpeta: data/sessions/{sid}/<br>"
                f"&nbsp;&nbsp;emg_data.csv<br>"
                f"&nbsp;&nbsp;hr_data.csv<br>"
                f"&nbsp;&nbsp;events.csv<br><br>"
                + ("<b>Pulsa Generate Report para el analisis ML</b>"
                   if self._ml else "<i>Modelo ML no encontrado</i>")
            )
            msg.exec()

    # ------------------------------------------------------------------
    # Generate Report (ML + AI Agent -- Fase 4)
    # ------------------------------------------------------------------

    def _on_generate_report(self):
        if self._ml is None:
            QMessageBox.warning(self, "ML no disponible",
                "No se encontro random_forest_model.pkl en ml/models/")
            return

        if self._last_session_info is None:
            QMessageBox.information(self, "Sin sesion",
                "Primero realiza y guarda una sesion completa.")
            return

        # Carpeta por sesion: los CSV viven en
        #   data/sessions/session_N_YYYY-MM-DD/{emg_data,hr_data,events}.csv
        session_id  = self._last_session_info.get("session_id", "")
        session_dir = self._last_session_info.get("session_dir", "")
        emg_csv     = os.path.join(session_dir, "emg_data.csv")
        hr_csv      = os.path.join(session_dir, "hr_data.csv")
        events_csv  = os.path.join(session_dir, "events.csv")

        self.statusBar().showMessage("Extrayendo features y ejecutando Random Forest...")

        try:
            features = extract_features(emg_csv, hr_csv, events_csv)
            result   = self._ml.predict(features)

            # session_dir apunta a la subcarpeta de esta sesion: el agente
            # guardara session_report.txt directamente ahi.
            dialog = MLResultDialog(
                result,
                session_id  = session_id,
                session_dir = session_dir,
                parent      = self,
            )
            dialog.exec()

            self.statusBar().showMessage(
                f"ML completado  -  Prediccion: {result['predicted_label'].upper()}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Error en ML", f"Error al procesar la sesion:\n{e}")
            self.statusBar().showMessage(f"Error ML: {e}")

    # ------------------------------------------------------------------
    # Handlers de datos
    # ------------------------------------------------------------------

    def _handle_emg(self, data):
        self._monitoring.update_emg(data.emg_rms, data.emg_raw_avg, data.emg_state)
        self._control.update_info(emg_state=data.emg_state)
        self._session.on_emg(data)
        if self._session.is_active:
            self._emg_count += 1
            self._control.update_info(contractions=self._session.contractions)
            self._sb_samples.setText(f"EMG: {self._emg_count}  |  HR: {self._hr_count}")

    def _handle_hr(self, data):
        self._monitoring.update_hr(data.hr_raw_bpm, data.hr_filtered_bpm, data.hr_valid)
        self._control.update_info(hr_valid=data.hr_valid)
        self._session.on_hr(data)
        if self._session.is_active:
            self._hr_count += 1
            self._sb_samples.setText(f"EMG: {self._emg_count}  |  HR: {self._hr_count}")

    def _handle_event(self, data):
        self._session.on_event(data)
        if data.event_type == "MODE_CHANGED":
            mode = data.value or "-"
            self._current_mode = mode
            self._monitoring.set_mode(mode)
            self._control.update_info(mode=mode)
            self._sb_mode.setText(f"Modo: {mode}")
        elif data.event_type == "SYSTEM_STARTED":
            self.statusBar().showMessage("Arduino conectado -- sistema inicializado")
        elif data.event_type == "SYSTEM_OFF":
            self._sb_mode.setText("Modo: OFF")

    # ------------------------------------------------------------------
    # Estado de la conexion serial
    # ------------------------------------------------------------------

    def _handle_conn_status(self, ok: bool, msg: str):
        self._connected = ok
        self._control.set_connected(ok, msg)
        if ok:
            self.statusBar().showMessage(f"Conectado: {msg}")
        else:
            self.statusBar().showMessage(f"Aviso: {msg}")

    # ------------------------------------------------------------------
    # Cierre
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        if self._serial_thread is not None:
            try:
                self._serial_thread.stop()
            except Exception:
                pass
        super().closeEvent(event)
