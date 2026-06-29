# =============================================================================
# ParkiSense -- data_processing/feature_extractor.py
#
# Extrae las features de sesion a partir de los 3 CSV generados por
# csv_writer.py. Adaptado a las columnas de nuestro pipeline:
#   EMG:    time_ms, emg_raw_avg, emg_rms, emg_state
#   HR:     time_ms, hr_raw_bpm, hr_filtered_bpm, hr_valid
#   Events: time_ms, event_type, value
# =============================================================================

import pandas as pd

HR_ALERT_THRESHOLD = 70  # BPM umbral para hr_above_threshold_ratio


def extract_features(emg_csv: str, hr_csv: str, events_csv: str) -> dict:
    """
    Lee los 3 CSV de una sesion y devuelve un dict con todas las features
    listas para pasarle al Random Forest.

    Parametros:
        emg_csv    : ruta al fichero emg_data_*.csv
        hr_csv     : ruta al fichero hr_data_*.csv
        events_csv : ruta al fichero events_*.csv

    Retorna:
        dict con las features de sesion (mismas que rf_feature_columns.json)
    """

    # -- Leer CSV
    emg    = pd.read_csv(emg_csv)
    hr     = pd.read_csv(hr_csv)
    events = pd.read_csv(events_csv)

    # -- Convertir columnas a numerico
    if len(emg) > 0:
        emg["time_ms"]     = pd.to_numeric(emg["time_ms"],     errors="coerce")
        emg["emg_raw_avg"] = pd.to_numeric(emg["emg_raw_avg"], errors="coerce")
        emg["emg_rms"]     = pd.to_numeric(emg["emg_rms"],     errors="coerce")

    if len(hr) > 0:
        hr["time_ms"]         = pd.to_numeric(hr["time_ms"],         errors="coerce")
        hr["hr_raw_bpm"]      = pd.to_numeric(hr["hr_raw_bpm"],      errors="coerce")
        hr["hr_filtered_bpm"] = pd.to_numeric(hr["hr_filtered_bpm"], errors="coerce")
        hr["hr_valid"]        = pd.to_numeric(hr["hr_valid"],        errors="coerce")

    # -- Features EMG
    if len(emg) > 0:
        emg_duration_s         = (emg["time_ms"].max() - emg["time_ms"].min()) / 1000.0
        emg_rms_mean           = emg["emg_rms"].mean()
        emg_rms_max            = emg["emg_rms"].max()
        emg_rms_std            = emg["emg_rms"].std()
        emg_contractions_count = int((emg["emg_state"] == "CONTRACTION").sum())
        emg_rest_count         = int((emg["emg_state"] == "REST").sum())
        emg_contraction_ratio  = emg_contractions_count / len(emg)
    else:
        emg_duration_s         = 0.0
        emg_rms_mean           = 0.0
        emg_rms_max            = 0.0
        emg_rms_std            = 0.0
        emg_contractions_count = 0
        emg_rest_count         = 0
        emg_contraction_ratio  = 0.0

    # Evitar NaN en std si solo hay 1 muestra
    if pd.isna(emg_rms_std):
        emg_rms_std = 0.0

    # -- Features HR
    if len(hr) > 0:
        hr_duration_s    = (hr["time_ms"].max() - hr["time_ms"].min()) / 1000.0
        hr_raw_mean      = hr["hr_raw_bpm"].mean()
        hr_filtered_mean = hr["hr_filtered_bpm"].mean()
        hr_filtered_max  = hr["hr_filtered_bpm"].max()
        hr_filtered_std  = hr["hr_filtered_bpm"].std()
        hr_valid_ratio   = (hr["hr_valid"] == 1).sum() / len(hr)

        hr_valid_only = hr[hr["hr_valid"] == 1].copy()
        if len(hr_valid_only) > 0:
            hr_above_threshold_ratio = (
                hr_valid_only["hr_filtered_bpm"] > HR_ALERT_THRESHOLD
            ).sum() / len(hr_valid_only)
        else:
            hr_above_threshold_ratio = 0.0
    else:
        hr_duration_s            = 0.0
        hr_raw_mean              = 0.0
        hr_filtered_mean         = 0.0
        hr_filtered_max          = 0.0
        hr_filtered_std          = 0.0
        hr_valid_ratio           = 0.0
        hr_above_threshold_ratio = 0.0

    # Evitar NaN en HR (chequeo explicito por variable)
    if pd.isna(hr_raw_mean):       hr_raw_mean = 0.0
    if pd.isna(hr_filtered_mean):  hr_filtered_mean = 0.0
    if pd.isna(hr_filtered_max):   hr_filtered_max = 0.0
    if pd.isna(hr_filtered_std):   hr_filtered_std = 0.0

    # -- Duracion total de sesion
    all_times = []
    if len(emg) > 0:
        all_times.extend(emg["time_ms"].dropna().tolist())
    if len(hr) > 0:
        all_times.extend(hr["time_ms"].dropna().tolist())

    session_duration_s = (max(all_times) - min(all_times)) / 1000.0 if all_times else 0.0

    # -- Resultado
    return {
        "session_duration_s":       round(session_duration_s,      3),
        "events_count":             len(events),
        "emg_duration_s":           round(emg_duration_s,          3),
        "emg_rms_mean":             round(float(emg_rms_mean),     4),
        "emg_rms_max":              round(float(emg_rms_max),      4),
        "emg_rms_std":              round(float(emg_rms_std),      4),
        "emg_contractions_count":   emg_contractions_count,
        "emg_rest_count":           emg_rest_count,
        "emg_contraction_ratio":    round(emg_contraction_ratio,   4),
        "hr_duration_s":            round(hr_duration_s,           3),
        "hr_raw_mean":              round(float(hr_raw_mean),      4),
        "hr_filtered_mean":         round(float(hr_filtered_mean), 4),
        "hr_filtered_max":          round(float(hr_filtered_max),  4),
        "hr_filtered_std":          round(float(hr_filtered_std),  4),
        "hr_valid_ratio":           round(hr_valid_ratio,          4),
        "hr_above_threshold_ratio": round(hr_above_threshold_ratio, 4),
    }
