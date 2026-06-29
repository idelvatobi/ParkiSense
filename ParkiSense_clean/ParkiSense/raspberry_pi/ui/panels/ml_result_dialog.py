# =============================================================================
# ParkiSense — ui/panels/ml_result_dialog.py  (Fase 4)
#
# Diálogo que muestra los resultados del Random Forest y permite
# generar un AI Report con Ollama (LLM local) sin bloquear la UI.
#
# Estructura visual:
#   ┌──────────────────────────────────────────┐
#   │  Sesión: <id>                            │
#   │  ┌────────────────────┐                  │
#   │  │  🟡 MODERATE       │   ← badge ML     │
#   │  └────────────────────┘                  │
#   │  Class probabilities                     │
#   │  Session features                        │
#   │  ─────────────────────────────────────── │
#   │  AI REPORT (Ollama · llama3.2:1b)        │
#   │  [ Generate AI Report ]                  │
#   │  ── Classification ──                    │
#   │  ── Session summary ──                   │
#   │  ── Feedback ──                          │
#   │  💾 session_report.txt                    │
#   └──────────────────────────────────────────┘
#
# Concurrencia:
#   La llamada a Ollama puede tardar 30s-2min en la Pi. Se ejecuta en
#   un QThread (AgentWorker) para que la ventana no se congele. La UI
#   se actualiza por señales (report_ready / report_failed).
# =============================================================================

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QProgressBar, QPushButton, QScrollArea, QWidget,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

import config
from agent import OllamaClient, OllamaError, generate_report, AgentReport
from agent.report_generator import save_report_to_disk


# =============================================================================
# Worker thread: corre la inferencia LLM sin bloquear la UI
# =============================================================================
class AgentWorker(QThread):
    """
    Lanza generate_report() en un hilo aparte. Emite:
        report_ready(AgentReport)  cuando termina bien
        report_failed(str)         cuando hay un error
    """
    report_ready  = pyqtSignal(object)   # AgentReport
    report_failed = pyqtSignal(str)

    def __init__(self, features: dict, ml_result: dict, parent=None):
        super().__init__(parent)
        self._features  = features
        self._ml_result = ml_result

    def run(self):
        try:
            report = generate_report(self._features, self._ml_result)
            self.report_ready.emit(report)
        except OllamaError as e:
            self.report_failed.emit(str(e))
        except Exception as e:                                  # noqa: BLE001
            self.report_failed.emit(f"Unexpected error: {e}")


# =============================================================================
# Diálogo principal
# =============================================================================
class MLResultDialog(QDialog):
    """
    Ventana emergente con:
      - Resultados del Random Forest (badge + probabilidades + features)
      - Sección AI Report con Ollama (Generate / Loading / Result)
    """

    LABEL_COLORS = {
        "low":      ("#0d47a1", "#90caf9", "🔵 LOW"),
        "moderate": ("#f57f17", "#fff9c4", "🟡 MODERATE"),
        "high":     ("#1b5e20", "#a5d6a7", "🟢 HIGH"),
    }

    def __init__(self, result: dict, session_id: str,
                 session_dir: str | None = None, parent=None):
        super().__init__(parent)
        self._result      = result
        self._session_id  = session_id
        self._session_dir = session_dir

        self._agent_worker: AgentWorker | None = None
        self._saved_path:   str | None = None

        self.setWindowTitle("ParkiSense — Session Report")
        self.setMinimumSize(560, 700)
        self.resize(620, 820)
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {config.COLOR_BG_PANEL};
                color: {config.COLOR_TEXT};
            }}
            QLabel {{ color: {config.COLOR_TEXT}; }}
        """)

        self._build_ui()

    # ── Construcción de la UI ────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: {config.COLOR_BG_PANEL}; border: none; }}
        """)
        outer.addWidget(scroll, stretch=1)

        body = QWidget()
        scroll.setWidget(body)

        layout = QVBoxLayout(body)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # ── Cabecera ─────────────────────────────────────────────────
        header = QLabel(f"Sesión:  {self._session_id}")
        header.setStyleSheet(f"color: {config.COLOR_TEXT_DIM}; font-size: 11px;")
        layout.addWidget(header)

        # ── Badge ML ─────────────────────────────────────────────────
        layout.addWidget(self._build_ml_badge())

        pred_label = QLabel("Random Forest classification")
        pred_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pred_label.setStyleSheet(f"color: {config.COLOR_TEXT_DIM}; font-size: 10px;")
        layout.addWidget(pred_label)

        layout.addWidget(self._divider())

        # ── Probabilidades ───────────────────────────────────────────
        layout.addWidget(self._section_title("CLASS PROBABILITIES"))
        for cls in ("low", "moderate", "high"):
            layout.addLayout(self._build_prob_row(cls))

        layout.addWidget(self._divider())

        # ── Features clave ───────────────────────────────────────────
        layout.addWidget(self._section_title("SESSION FEATURES"))
        layout.addWidget(self._build_features_grid())

        layout.addWidget(self._divider())

        # ── AI Report (Ollama) ───────────────────────────────────────
        layout.addWidget(self._section_title(
            f"AI REPORT  ·  Ollama  ·  {config.OLLAMA_MODEL}"
        ))

        self._ai_status = QLabel(
            "Press the button below to generate a human-readable report "
            "with the local LLM."
        )
        self._ai_status.setWordWrap(True)
        self._ai_status.setStyleSheet(
            f"color: {config.COLOR_TEXT_DIM}; font-size: 10px;"
        )
        layout.addWidget(self._ai_status)

        self._btn_generate = QPushButton("⚡  Generate AI Report")
        self._btn_generate.setStyleSheet(self._primary_btn_style())
        self._btn_generate.clicked.connect(self._on_generate_clicked)
        layout.addWidget(self._btn_generate)

        # Barra de progreso indeterminada
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)              # indeterminada
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(6)
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                background: {config.COLOR_BG_DARK};
                border: 1px solid {config.COLOR_BORDER};
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: {config.COLOR_ACCENT};
                border-radius: 3px;
            }}
        """)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # Bloques del report (vacíos al principio)
        self._lbl_classification = self._make_report_block("Classification")
        self._lbl_summary        = self._make_report_block("Session summary")
        self._lbl_feedback       = self._make_report_block("Feedback / recommendation")
        layout.addWidget(self._lbl_classification["card"])
        layout.addWidget(self._lbl_summary["card"])
        layout.addWidget(self._lbl_feedback["card"])

        # Path donde quedó guardado el txt
        self._lbl_saved_path = QLabel("")
        self._lbl_saved_path.setStyleSheet(
            f"color: {config.COLOR_TEXT_DIM}; font-size: 9px;"
        )
        self._lbl_saved_path.setWordWrap(True)
        layout.addWidget(self._lbl_saved_path)

        layout.addStretch(1)

        # ── Botón cerrar (fuera del scroll) ──────────────────────────
        close_row = QHBoxLayout()
        close_row.setContentsMargins(20, 10, 20, 14)
        close_row.addStretch(1)
        btn_close = QPushButton("Close")
        btn_close.setStyleSheet(self._secondary_btn_style())
        btn_close.clicked.connect(self.accept)
        close_row.addWidget(btn_close)
        outer.addLayout(close_row)

    # ── Bloques visuales ─────────────────────────────────────────────

    def _build_ml_badge(self) -> QLabel:
        label = self._result["predicted_label"]
        bg, fg, text = self.LABEL_COLORS.get(
            label, ("#37474f", "#eceff1", f"? {label.upper()}")
        )
        badge = QLabel(text)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"""
            background-color: {bg};
            color: {fg};
            font-size: 26px;
            font-weight: 700;
            border-radius: 10px;
            padding: 14px;
            letter-spacing: 2px;
        """)
        return badge

    def _build_prob_row(self, cls: str) -> QHBoxLayout:
        bar_colors = {
            "low":      "#42a5f5",
            "moderate": "#ffd54f",
            "high":     "#66bb6a",
        }
        prob = self._result["probabilities"].get(cls, 0.0)
        pct  = int(prob * 100)

        row = QHBoxLayout()
        row.setSpacing(10)

        lbl = QLabel(cls.upper())
        lbl.setFixedWidth(75)
        lbl.setStyleSheet(
            f"color: {config.COLOR_TEXT_DIM}; font-size: 11px; font-weight: 600;"
        )

        bar = QProgressBar()
        bar.setValue(pct)
        bar.setTextVisible(False)
        bar.setFixedHeight(14)
        bar_color = bar_colors.get(cls, config.COLOR_ACCENT)
        bar.setStyleSheet(f"""
            QProgressBar {{
                background: {config.COLOR_BG_DARK};
                border-radius: 7px;
                border: 1px solid {config.COLOR_BORDER};
            }}
            QProgressBar::chunk {{
                background: {bar_color};
                border-radius: 7px;
            }}
        """)

        pct_lbl = QLabel(f"{prob:.1%}")
        pct_lbl.setFixedWidth(45)
        pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        pct_lbl.setStyleSheet(
            f"color: {bar_color}; font-size: 11px; font-weight: 700;"
        )

        row.addWidget(lbl)
        row.addWidget(bar)
        row.addWidget(pct_lbl)
        return row

    def _build_features_grid(self) -> QWidget:
        feats = self._result["features"]
        key_features = [
            ("Session duration",    f"{feats.get('session_duration_s', 0):.1f} s"),
            ("EMG RMS mean",        f"{feats.get('emg_rms_mean', 0):.2f} μV"),
            ("EMG RMS max",         f"{feats.get('emg_rms_max', 0):.2f} μV"),
            ("EMG contractions",    f"{feats.get('emg_contractions_count', 0)}"),
            ("Contraction ratio",   f"{feats.get('emg_contraction_ratio', 0):.2%}"),
            ("HR filtered mean",    f"{feats.get('hr_filtered_mean', 0):.1f} BPM"),
            ("HR filtered max",     f"{feats.get('hr_filtered_max', 0):.1f} BPM"),
            ("HR valid ratio",      f"{feats.get('hr_valid_ratio', 0):.2%}"),
        ]

        grid = QWidget()
        grid_layout = QVBoxLayout(grid)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(4)

        for name, value in key_features:
            row = QHBoxLayout()
            key_lbl = QLabel(name)
            key_lbl.setStyleSheet(f"color: {config.COLOR_TEXT_DIM}; font-size: 10px;")
            val_lbl = QLabel(value)
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            val_lbl.setStyleSheet(
                f"color: {config.COLOR_TEXT}; font-size: 10px; font-weight: 600;"
            )
            row.addWidget(key_lbl)
            row.addWidget(val_lbl)
            grid_layout.addLayout(row)
        return grid

    def _make_report_block(self, title: str) -> dict:
        """
        Crea una 'card' con título + cuerpo de texto, vacía al principio.
        Devuelve referencias para poder rellenar el cuerpo después.
        """
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {config.COLOR_BG_WIDGET};
                border: 1px solid {config.COLOR_BORDER};
                border-radius: 6px;
            }}
        """)
        v = QVBoxLayout(card)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(4)

        t = QLabel(title.upper())
        t.setStyleSheet(
            f"color: {config.COLOR_ACCENT}; font-size: 9px; "
            f"font-weight: 700; letter-spacing: 1px; border: none;"
        )
        body = QLabel("—")
        body.setWordWrap(True)
        body.setStyleSheet(
            f"color: {config.COLOR_TEXT}; font-size: 11px; border: none;"
        )

        v.addWidget(t)
        v.addWidget(body)

        return {"card": card, "title": t, "body": body}

    # ── Lógica del agente ────────────────────────────────────────────

    def _on_generate_clicked(self):
        """
        Lanza el AgentWorker para llamar a Ollama en segundo plano.
        Antes hace un health-check rápido para fallar pronto si el
        servicio no está corriendo.
        """
        client = OllamaClient(
            host=config.OLLAMA_HOST,
            model=config.OLLAMA_MODEL,
            timeout=config.OLLAMA_TIMEOUT,
        )
        if not client.is_available():
            self._show_error(
                f"Ollama is not reachable at {config.OLLAMA_HOST} "
                f"or the model '{config.OLLAMA_MODEL}' is not installed.\n\n"
                f"On the Raspberry Pi, run:\n"
                f"  ollama serve     (in one terminal)\n"
                f"  ollama pull {config.OLLAMA_MODEL}    (only the first time)"
            )
            return

        # UI: bloquear botón + mostrar progreso
        self._btn_generate.setEnabled(False)
        self._btn_generate.setText("⏳  Generating with Ollama…")
        self._progress.setVisible(True)
        self._ai_status.setText(
            f"Calling local LLM ({config.OLLAMA_MODEL}). This can take "
            f"30s–2 min on a Raspberry Pi. The window will not freeze."
        )
        self._ai_status.setStyleSheet(
            f"color: {config.COLOR_TEXT_DIM}; font-size: 10px;"
        )

        # Worker
        self._agent_worker = AgentWorker(
            features=self._result["features"],
            ml_result=self._result,
            parent=self,
        )
        self._agent_worker.report_ready.connect(self._on_report_ready)
        self._agent_worker.report_failed.connect(self._on_report_failed)
        self._agent_worker.start()

    def _on_report_ready(self, report: AgentReport):
        # Pintar los tres bloques
        self._lbl_classification["body"].setText(report.classification or "—")
        self._lbl_summary["body"].setText(report.summary or "—")
        self._lbl_feedback["body"].setText(report.feedback or "—")

        # UI: restaurar botón
        self._progress.setVisible(False)
        self._btn_generate.setEnabled(True)
        self._btn_generate.setText("⟳  Re-generate AI Report")

        # Estado: éxito / éxito con warnings
        if report.validation_passed:
            status = (
                f"✅ Report generated by {report.model} at "
                f"{report.generated_at}  ·  validation passed in "
                f"{report.attempts} attempt(s)."
            )
            self._ai_status.setStyleSheet(
                f"color: {config.COLOR_TEXT_DIM}; font-size: 10px;"
            )
        else:
            n = len(report.validation_errors)
            status = (
                f"⚠ Report generated by {report.model} after "
                f"{report.attempts} attempt(s) but {n} validation issue(s) "
                f"remain. The model may have ignored some rules."
            )
            self._ai_status.setStyleSheet(
                "color: #ffcc80; font-size: 10px;"
            )
        self._ai_status.setText(status)

        # Persistir si tenemos session_dir. Nombre: session_report_<id>.txt
        # para no pisar reports de sesiones anteriores.
        if self._session_dir:
            filename = f"session_report.txt"
            try:
                self._saved_path = save_report_to_disk(
                    report, self._session_dir, filename=filename
                )
                self._lbl_saved_path.setText(f"💾  Saved to: {self._saved_path}")
            except Exception as e:                              # noqa: BLE001
                self._lbl_saved_path.setText(
                    f"⚠ Could not save report file: {e}"
                )
        else:
            self._lbl_saved_path.setText(
                "ℹ Report not saved (no session directory provided)."
            )

    def _on_report_failed(self, message: str):
        self._progress.setVisible(False)
        self._btn_generate.setEnabled(True)
        self._btn_generate.setText("⚡  Generate AI Report")
        self._show_error(message)

    def _show_error(self, message: str):
        self._ai_status.setText(message)
        self._ai_status.setStyleSheet(
            "color: #ef9a9a; font-size: 10px;"
        )
        for blk in (self._lbl_classification, self._lbl_summary, self._lbl_feedback):
            blk["body"].setText("—")
        self._lbl_saved_path.setText("")

    # ── Cierre seguro: si el worker sigue vivo, lo paramos ───────────

    def closeEvent(self, event):                               # noqa: N802
        if self._agent_worker is not None and self._agent_worker.isRunning():
            self._agent_worker.quit()
            self._agent_worker.wait(2000)
        super().closeEvent(event)

    # ── Helpers de estilo ────────────────────────────────────────────

    @staticmethod
    def _divider() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {config.COLOR_BORDER};")
        return line

    @staticmethod
    def _section_title(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {config.COLOR_ACCENT}; font-size: 9px; "
            f"font-weight: 700; letter-spacing: 1px;"
        )
        return lbl

    @staticmethod
    def _primary_btn_style() -> str:
        return f"""
            QPushButton {{
                background: {config.COLOR_ACCENT};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover    {{ background: #7986cb; }}
            QPushButton:disabled {{ background: #3d3f6e; color: #9fa8da; }}
        """

    @staticmethod
    def _secondary_btn_style() -> str:
        return f"""
            QPushButton {{
                background: {config.COLOR_BG_WIDGET};
                color: {config.COLOR_TEXT};
                border: 1px solid {config.COLOR_BORDER};
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {config.COLOR_BORDER}; }}
        """
