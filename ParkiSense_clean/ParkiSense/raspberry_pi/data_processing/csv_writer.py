# =============================================================================
# ParkiSense -- data_processing/csv_writer.py
# Escribe los 3 CSV de sesion DENTRO de la carpeta de sesion.
# =============================================================================

import csv
import os
from serial_comm.parser import EMGData, HRData, EventData


class CSVWriter:
    EMG_HEADERS   = ["time_ms", "emg_raw_avg", "emg_rms", "emg_state"]
    HR_HEADERS    = ["time_ms", "hr_raw_bpm", "hr_filtered_bpm", "hr_valid"]
    EVENT_HEADERS = ["time_ms", "event_type", "value"]

    def __init__(self, session_dir: str, session_id: str):
        os.makedirs(session_dir, exist_ok=True)
        self._session_id  = session_id
        self._session_dir = session_dir
        self._path_emg    = os.path.join(session_dir, "emg_data.csv")
        self._path_hr     = os.path.join(session_dir, "hr_data.csv")
        self._path_events = os.path.join(session_dir, "events.csv")
        self._f_emg    = open(self._path_emg,    "w", newline="")
        self._f_hr     = open(self._path_hr,     "w", newline="")
        self._f_events = open(self._path_events, "w", newline="")
        self._w_emg    = csv.writer(self._f_emg)
        self._w_hr     = csv.writer(self._f_hr)
        self._w_events = csv.writer(self._f_events)
        self._w_emg.writerow(self.EMG_HEADERS)
        self._w_hr.writerow(self.HR_HEADERS)
        self._w_events.writerow(self.EVENT_HEADERS)
        self.emg_count   = 0
        self.hr_count    = 0
        self.event_count = 0
        self._t_start_ms = None

    def write_emg(self, data: EMGData):
        if self._t_start_ms is None:
            self._t_start_ms = data.time_ms
        self._w_emg.writerow([
            data.time_ms,
            f"{data.emg_raw_avg:.2f}",
            f"{data.emg_rms:.2f}",
            data.emg_state,
        ])
        self._f_emg.flush()
        self.emg_count += 1

    def write_hr(self, data: HRData):
        if self._t_start_ms is None:
            self._t_start_ms = data.time_ms
        self._w_hr.writerow([
            data.time_ms,
            f"{data.hr_raw_bpm:.2f}",
            f"{data.hr_filtered_bpm:.2f}",
            int(data.hr_valid),
        ])
        self._f_hr.flush()
        self.hr_count += 1

    def write_event(self, data: EventData, time_ms: int = 0):
        self._w_events.writerow([time_ms, data.event_type, data.value])
        self._f_events.flush()
        self.event_count += 1

    def close(self) -> dict:
        self._f_emg.close()
        self._f_hr.close()
        self._f_events.close()
        return {
            "session_id":   self._session_id,
            "session_dir":  self._session_dir,
            "timestamp":    self._session_id,
            "path_emg":     self._path_emg,
            "path_hr":      self._path_hr,
            "path_events":  self._path_events,
            "emg_count":    self.emg_count,
            "hr_count":     self.hr_count,
            "event_count":  self.event_count,
        }
