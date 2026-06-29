# =============================================================================
# ParkiSense — serial_comm/serial_reader.py
#
# QThread que lee el puerto serial del Arduino en background.
# Emite señales Qt cuando llegan datos, de forma segura con la GUI.
#
# Incluye MODO DEMO: genera datos simulados sin necesitar Arduino.
# Para activarlo, pon DEMO_MODE = True en config.py
# =============================================================================

import math
import random
import time

import serial
from PyQt6.QtCore import QThread, pyqtSignal

import config
from .parser import parse_line, EMGData, HRData, EventData


class SerialReaderThread(QThread):
    """
    Hilo de lectura serial. Se ejecuta en background y comunica
    datos a la GUI mediante señales Qt (thread-safe).

    Señales:
        emg_received(EMGData)          — nuevo sample EMG
        hr_received(HRData)            — nuevo sample HR
        event_received(EventData)      — evento del sistema
        connection_status(bool, str)   — (conectado, mensaje)
    """

    emg_received       = pyqtSignal(object)
    hr_received        = pyqtSignal(object)
    event_received     = pyqtSignal(object)
    connection_status  = pyqtSignal(bool, str)

    def __init__(self, port: str = None, baud_rate: int = None, parent=None):
        super().__init__(parent)
        self.port      = port      or config.SERIAL_PORT
        self.baud_rate = baud_rate or config.BAUD_RATE
        self.running   = False
        self._serial   = None

    # ------------------------------------------------------------------
    # Arranque / parada
    # ------------------------------------------------------------------

    def run(self):
        """Punto de entrada del hilo. Qt lo llama al hacer thread.start()."""
        self.running = True
        if config.DEMO_MODE:
            self._run_demo()
        else:
            self._run_serial()

    def stop(self):
        """Para el hilo de forma ordenada."""
        self.running = False
        if self._serial and self._serial.is_open:
            self._serial.close()
        self.wait(2000)  # espera máximo 2 s a que el hilo termine

    # ------------------------------------------------------------------
    # Modo real: lectura del puerto serial
    # ------------------------------------------------------------------

    def _run_serial(self):
        try:
            self._serial = serial.Serial(
                self.port, self.baud_rate, timeout=config.SERIAL_TIMEOUT
            )
            self.connection_status.emit(True, f"Conectado → {self.port} @ {self.baud_rate} baud")
        except Exception as e:
            self.connection_status.emit(False, f"Error al abrir puerto: {e}")
            return

        while self.running:
            try:
                if self._serial.in_waiting > 0:
                    raw = self._serial.readline()
                    line = raw.decode("utf-8", errors="ignore")
                    result = parse_line(line)
                    if result:
                        tipo, dato = result
                        if tipo == "EMG":
                            self.emg_received.emit(dato)
                        elif tipo == "HR":
                            self.hr_received.emit(dato)
                        elif tipo == "EVENT":
                            self.event_received.emit(dato)
            except Exception as e:
                self.connection_status.emit(False, f"Error serial: {e}")
                break
            time.sleep(0.005)  # evita busy-loop

        if self._serial and self._serial.is_open:
            self._serial.close()

    # ------------------------------------------------------------------
    # Modo demo: datos simulados (sin Arduino)
    # ------------------------------------------------------------------

    def _run_demo(self):
        """
        Genera datos realistas de EMG y HR simulados.
        Alterna entre modo EMG y modo HR cada ~10 segundos.
        """
        self.connection_status.emit(True, "Modo DEMO activo — datos simulados")

        # Evento de arranque
        self.event_received.emit(EventData("SYSTEM_STARTED"))

        tick        = 0          # contador de samples
        mode        = "EMG"      # modo inicial
        mode_ticks  = 0          # ticks desde último cambio de modo
        MODE_PERIOD = 100        # cambiar de modo cada 100 ticks (~10 s a 100 ms)

        while self.running:
            t_ms = tick * 100

            # --- Cambio de modo automático ---
            mode_ticks += 1
            if mode_ticks >= MODE_PERIOD:
                mode_ticks = 0
                mode = "HR" if mode == "EMG" else "EMG"
                self.event_received.emit(
                    EventData("MODE_CHANGED", mode)
                )

            # --- Generar sample según modo ---
            if mode == "EMG":
                self._emit_emg_demo(tick, t_ms)
            else:
                self._emit_hr_demo(tick, t_ms)

            tick += 1
            time.sleep(0.1)   # 10 Hz de muestreo simulado

        # Evento de apagado
        self.event_received.emit(EventData("SYSTEM_OFF"))

    def _emit_emg_demo(self, tick: int, t_ms: int):
        """Simula contracciones musculares periódicas."""
        # Onda de contracción: seno lento con amplitud variable
        contraction_env = max(0.0, math.sin(tick * 0.12))
        emg_rms = 80 + contraction_env * 340 + random.gauss(0, 25)
        emg_rms = max(0.0, emg_rms)
        emg_raw = emg_rms * 1.8 + random.gauss(0, 40)

        state = "CONTRACTION" if emg_rms > 180 else "REST"

        self.emg_received.emit(EMGData(
            time_ms     = t_ms,
            emg_raw_avg = emg_raw,
            emg_rms     = emg_rms,
            emg_state   = state
        ))

    def _emit_hr_demo(self, tick: int, t_ms: int):
        """Simula frecuencia cardíaca con pequeñas variaciones."""
        base_bpm    = 75
        variation   = math.sin(tick * 0.06) * 6
        hr_raw      = base_bpm + variation + random.gauss(0, 2.5)
        hr_filtered = base_bpm + variation * 0.7  # filtrado suaviza
        hr_valid    = random.random() > 0.04       # 96% de muestras válidas

        self.hr_received.emit(HRData(
            time_ms         = t_ms,
            hr_raw_bpm      = hr_raw,
            hr_filtered_bpm = hr_filtered,
            hr_valid        = hr_valid
        ))
