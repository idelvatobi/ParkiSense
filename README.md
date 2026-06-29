# ParkiSense

**Wearable biomedical prototype for objective physiological monitoring — EMG · Heart Rate · Machine Learning · Local AI**

Developed as part of the Biomedical Systems and Prototyping course at the University of Deusto (Biomedical Engineering, 2025–26).

> ParkiSense is not a diagnostic device. It demonstrates a complete end-to-end biomedical monitoring pipeline for educational purposes.

---

## Overview

ParkiSense is a two-device embedded system that acquires EMG and heart rate signals during guided sessions, processes them into structured data, classifies the session activation level using a Random Forest model, and generates a human-readable report via a locally deployed LLM — all without cloud dependency.

The system was designed around a real clinical problem: Parkinson's disease monitoring depends heavily on subjective observation and periodic consultations. ParkiSense demonstrates how objective, structured physiological data can be collected and automatically interpreted using low-cost embedded hardware.

---

## System Architecture

```
Arduino (C/C++)                          Raspberry Pi (Python)
─────────────────                        ──────────────────────────────────────
EMG sensor (A0)   ──┐                    serial_comm/   → parser → Qt signals
HR sensor (I2C)   ──┤  USB serial        data_processing/ → CSV writer
Button (D4)       ──┤  115200 baud  ──▶  ml/            → Random Forest classifier
LED (D6)          ──┤                    agent/         → Ollama LLM (llama3.2:1b)
LCD 16×2 (I2C)   ──┘                    ui/            → PyQt6 real-time dashboard
```

---

## Hardware Components

| Component | Interface | Role |
|---|---|---|
| Grove EMG Sensor | Analog (A0) | Muscle activation acquisition |
| Grove Finger-clip HR Sensor | I2C (0x50) | Heart rate measurement |
| Grove Button | Digital (D4) | Mode control |
| Grove LED | Digital (D6) | Visual contraction/HR feedback |
| Grove LCD 16×2 | I2C | Real-time status display |
| Arduino UNO/Nano | USB Serial | Acquisition and feedback layer |
| Raspberry Pi | Python over USB | Processing, storage, ML and AI report |

---

## Pipeline

1. **Signal acquisition** — Arduino reads EMG (RMS with adaptive baseline + hysteresis) and HR (BPM via I2C, physiological range validation)
2. **Serial communication** — Structured CSV-format packets at 115200 baud
3. **Data logging** — Raspberry Pi stores timestamped CSV files per session (EMG, HR, events)
4. **Feature extraction** — 16 session-level features computed from CSV files
5. **Classification** — Random Forest model (scikit-learn) predicts activation level: Low / Moderate / High
6. **AI report generation** — Ollama (llama3.2:1b) generates a structured session summary locally
7. **Dashboard** — PyQt6 real-time interface with live signal plots and session management

---

## Repository Structure

```
ParkiSense/
├── arduino/
│   ├── firmware/
│   │   └── ParkiSense_firmware.ino     # Final combined firmware (EMG + HR + LCD + Button)
│   └── tests/
│       ├── EMG_test.ino                # EMG sensor unit test
│       └── HR_test.ino                 # Heart rate sensor unit test
│
├── raspberry_pi/
│   ├── main.py                         # Application entry point
│   ├── config.py                       # Shared configuration parameters
│   ├── requirements.txt                # Python dependencies
│   ├── serial_comm/                    # Arduino serial reader and parser
│   ├── data_processing/                # CSV writer, feature extractor, session manager
│   ├── ml/
│   │   ├── inference.py                # Random Forest inference
│   │   ├── train_random_forest.py      # Model training script
│   │   └── models/                     # Trained model (.pkl) and feature columns (.json)
│   ├── agent/                          # Ollama client, prompt builder, report generator
│   └── ui/                             # PyQt6 dashboard (main window, panels, widgets)
│
├── csv/
│   ├── ml_dataset.csv                  # Real session data used for training
│   └── synthetic_ml_dataset.csv        # Synthetic data for classifier bootstrapping
│
└── docs/
    └── ParkiSense_Final_Report.pdf     # Full project report
```

---

## Getting Started

### Arduino

1. Open `arduino/firmware/ParkiSense_firmware.ino` in Arduino IDE
2. Connect hardware according to the component table above
3. Upload to Arduino UNO or Nano
4. Open Serial Monitor at 115200 baud to verify packet output

### Raspberry Pi

```bash
# Install dependencies
pip install -r raspberry_pi/requirements.txt

# Install Ollama (optional — system falls back to rule-based report if unavailable)
# See: https://ollama.com

# Run
cd raspberry_pi
python main.py
```

---

## Session Output

Each session generates three CSV files and a session report:

```
data/sessions/session_N_YYYY-MM-DD/
├── emg_data.csv          # time_ms, emg_raw_avg, emg_rms, emg_state
├── hr_data.csv           # time_ms, hr_raw_bpm, hr_filtered_bpm, hr_valid
├── events.csv            # time_ms, event_type, value
└── session_report.txt    # AI-generated summary + classification result
```

---

## Classification Results (Integrated Session Test)

| Metric | Value |
|---|---|
| Session duration | 228.4 s |
| EMG contractions detected | 37 |
| EMG RMS mean | 28.93 μV |
| EMG RMS peak | 687.58 μV |
| HR filtered mean | 54.8 BPM |
| HR valid ratio | 100% |
| Predicted activation class | **HIGH** (66% confidence) |

---

## Authors

**Iñigo Del Valle** — Arduino firmware, AI pipeline, machine learning layer, PyQt6 dashboard, system integration
**Ander Ruiz de Olalla** — System architecture, documentation, validation

University of Deusto · Biomedical Engineering · May 2026

---

## Disclaimer

ParkiSense is an educational prototype developed for academic purposes. It is not a medical device and has not undergone clinical validation. All outputs should be interpreted as demonstrative and non-clinical.
