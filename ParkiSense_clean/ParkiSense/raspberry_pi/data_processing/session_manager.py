# =============================================================================
# ParkiSense -- data_processing/session_manager.py
# Crea data/sessions/session_N_YYYY-MM-DD/ por cada sesion (N = max + 1).
# =============================================================================

import os
import re
import time
from datetime import datetime

from .csv_writer import CSVWriter
from serial_comm.parser import EMGData, HRData, EventData


class SessionManager:
    _SESSION_RE = re.compile(r"^session_(\d+)_")

    def __init__(self, sessions_dir: str = "data/sessions"):
        self._sessions_dir = sessions_dir
        os.makedirs(sessions_dir, exist_ok=True)
        self._writer = None
        self._active = False
        self._start_time = None
        self._session_id  = None
        self._session_dir = None
        self.emg_count       = 0
        self.hr_count        = 0
        self.event_count     = 0
        self.contractions    = 0
        self._last_emg_state = "REST"

    def _next_session_number(self) -> int:
        if not os.path.isdir(self._sessions_dir):
            return 1
        max_n = 0
        for name in os.listdir(self._sessions_dir):
            m = self._SESSION_RE.match(name)
            if m:
                try:
                    n = int(m.group(1))
                    if n > max_n:
                        max_n = n
                except ValueError:
                    continue
        return max_n + 1

    def start(self) -> str:
        if self._active:
            return self._session_id
        n = self._next_session_number()
        today = datetime.now().strftime("%Y-%m-%d")
        self._session_id  = f"session_{n}_{today}"
        self._session_dir = os.path.join(self._sessions_dir, self._session_id)
        self._start_time  = time.time()
        self._active      = True
        self.emg_count       = 0
        self.hr_count        = 0
        self.event_count     = 0
        self.contractions    = 0
        self._last_emg_state = "REST"
        self._writer = CSVWriter(self._session_dir, self._session_id)
        print(f"[SessionManager] Sesion iniciada -> {self._session_id}")
        print(f"[SessionManager] Carpeta: {self._session_dir}")
        return self._session_id

    def end(self) -> dict:
        if not self._active or self._writer is None:
            return {}
        self._active = False
        duration_s   = time.time() - self._start_time
        csv_info     = self._writer.close()
        resumen = {
            **csv_info,
            "duration_s":   round(duration_s, 1),
            "contractions": self.contractions,
        }
        print(f"[SessionManager] Sesion finalizada -- {duration_s:.0f}s  "
              f"EMG:{self.emg_count}  HR:{self.hr_count}  "
              f"Eventos:{self.event_count}  Contracciones:{self.contractions}")
        print(f"  Carpeta: {csv_info['session_dir']}")
        return resumen

    def on_emg(self, data: EMGData):
        if not self._active:
            return
        self._writer.write_emg(data)
        self.emg_count += 1
        if data.emg_state == "CONTRACTION" and self._last_emg_state == "REST":
            self.contractions += 1
        self._last_emg_state = data.emg_state

    def on_hr(self, data: HRData):
        if not self._active:
            return
        self._writer.write_hr(data)
        self.hr_count += 1

    def on_event(self, data: EventData):
        if not self._active:
            return
        elapsed_ms = int((time.time() - self._start_time) * 1000)
        self._writer.write_event(data, time_ms=elapsed_ms)
        self.event_count += 1

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def elapsed_seconds(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time
