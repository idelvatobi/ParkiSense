# =============================================================================
# ParkiSense — serial_comm/parser.py
#
# Parsea las líneas que envía el Arduino por serial.
# Formatos esperados:
#   DATA,EMG,time_ms,emg_raw_avg,emg_rms,emg_state
#   DATA,HR,time_ms,hr_raw_bpm,hr_filtered_bpm,hr_valid
#   EVENT,SYSTEM_STARTED
#   EVENT,MODE_CHANGED,EMG
#   EVENT,SYSTEM_OFF
# =============================================================================

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class EMGData:
    """Datos de un sample de EMG."""
    time_ms:     int
    emg_raw_avg: float
    emg_rms:     float
    emg_state:   str    # "REST" o "CONTRACTION"


@dataclass
class HRData:
    """Datos de un sample de Heart Rate."""
    time_ms:          int
    hr_raw_bpm:       float
    hr_filtered_bpm:  float
    hr_valid:         bool


@dataclass
class EventData:
    """Evento del sistema (cambio de modo, encendido, apagado...)."""
    event_type: str   # p.ej. "MODE_CHANGED", "SYSTEM_STARTED"
    value:      str = ""  # p.ej. "EMG", "HR", "OFF"


def parse_line(line: str) -> Optional[Tuple[str, object]]:
    """
    Parsea una línea serial del Arduino.

    Retorna:
        ("EMG",   EMGData)    si es un dato EMG
        ("HR",    HRData)     si es un dato HR
        ("EVENT", EventData)  si es un evento
        None                  si la línea es inválida o no reconocida

    Ejemplo de uso:
        result = parse_line("DATA,EMG,5000,512.0,247.3,CONTRACTION")
        if result:
            tipo, dato = result
    """
    line = line.strip()
    if not line:
        return None

    parts = line.split(",")
    msg_type = parts[0]

    try:
        if msg_type == "DATA" and len(parts) >= 2:
            sensor = parts[1]

            # --- EMG ---
            if sensor == "EMG" and len(parts) >= 6:
                return ("EMG", EMGData(
                    time_ms     = int(float(parts[2])),
                    emg_raw_avg = float(parts[3]),
                    emg_rms     = float(parts[4]),
                    emg_state   = parts[5].strip().upper()
                ))

            # --- HR ---
            if sensor == "HR" and len(parts) >= 6:
                return ("HR", HRData(
                    time_ms         = int(float(parts[2])),
                    hr_raw_bpm      = float(parts[3]),
                    hr_filtered_bpm = float(parts[4]),
                    hr_valid        = parts[5].strip() in ("1", "true", "True")
                ))

        elif msg_type == "EVENT" and len(parts) >= 2:
            event_type = parts[1].strip()
            value      = parts[2].strip() if len(parts) > 2 else ""
            return ("EVENT", EventData(event_type=event_type, value=value))

    except (ValueError, IndexError):
        # Línea malformada — la ignoramos silenciosamente
        pass

    return None
