# =============================================================================
# ParkiSense -- agent/validator.py
#
# Capa de seguridad sobre la salida del LLM. Comprueba:
#   1. Que estan las 3 secciones (Classification / Session summary / Feedback)
#   2. Que el report afirma claramente "<predicted_label> activation"
#   3. Que no contradice el label (no dice "high activation" si es "low", etc.)
#   4. Que no usa vocabulario clinico prohibido (Parkinson, paciente, ...)
#   5. Que no hay bullets ni markdown bold
#   6. Que no mezcla EMG/HR (no atribuye contracciones a HR, etc.)
#   7. Que el Feedback no explica la clasificacion ni invoca causas
#   8. Que el Feedback no supera 2 frases
#   9. Que el Session summary cita >= 2 valores numericos concretos
#
# Si algo falla, devuelve la lista de errores y se pasa al
# build_correction_prompt para pedir al modelo una version corregida.
#
# Adaptado del run_full_pipeline.py original del usuario.
# =============================================================================

from __future__ import annotations

import json
import re
from typing import Dict, List, Tuple


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _get_section_text(report: str, section_name: str) -> str:
    """
    Extrae el texto entre 'section_name:' y la proxima cabecera 'Algo:'.
    """
    pattern = rf"{re.escape(section_name)}:\s*(.*?)(?=\n[A-Za-z ]+ /? ?[A-Za-z ]*:\s*|\Z)"
    match = re.search(pattern, report, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def _count_sentences(text: str) -> int:
    if not text:
        return 0
    sentences = re.split(r"[.!?]+", text.strip())
    return len([s for s in sentences if s.strip()])


# --------------------------------------------------------------------------
# Validacion principal
# --------------------------------------------------------------------------
def validate_report(report: str, predicted_label: str) -> Tuple[bool, List[str]]:
    """
    Devuelve (is_valid, errors). Si is_valid=False, errors contiene
    mensajes humanos que se inyectan en el prompt de correccion.
    """
    errors: List[str] = []
    report_lower = report.lower()
    predicted_label = str(predicted_label).strip().lower()

    # ── 1. Secciones obligatorias ─────────────────────────────────────
    required_sections = [
        "classification:",
        "session summary:",
        "feedback / recommendation:",
    ]
    for section in required_sections:
        if section not in report_lower:
            errors.append(f"Missing section: {section}")

    # ── 2. Debe afirmar "<label> activation" ──────────────────────────
    expected_phrase = f"{predicted_label} activation"
    if expected_phrase not in report_lower:
        errors.append(f"The report does not clearly state '{expected_phrase}'.")

    # ── 3. No contradicciones con otras clases ────────────────────────
    label_classes = ["low", "moderate", "high"]
    wrong_labels = [lbl for lbl in label_classes if lbl != predicted_label]

    for wrong_label in wrong_labels:
        bad_phrases = [
            f"{wrong_label} activation",
            f"{wrong_label} overall activation",
            f"overall {wrong_label}",
            f"classified as {wrong_label}",
            f"predicted class for this session is {wrong_label}",
            f"predicted label for this session is {wrong_label}",
            f"activity level consistent with {wrong_label}",
            f"session is {wrong_label}",
            f"{wrong_label} emg activity",
            f"{wrong_label} hr activity",
            f"{wrong_label} activity",
        ]
        for phrase in bad_phrases:
            if phrase in report_lower:
                errors.append(
                    f"Contradiction detected: report mentions '{phrase}' "
                    f"while predicted_label is '{predicted_label}'."
                )

    # ── 3b. Frases inconsistentes especificas por label ───────────────
    if predicted_label == "low":
        forbidden = [
            "moderate emg activity", "moderate hr activity", "moderate activity",
            "high emg activity",     "high hr activity",     "high activity",
            "periods of high",       "periods of moderate",
        ]
        for p in forbidden:
            if p in report_lower:
                errors.append(f"Inconsistent phrase for low activation: '{p}'.")

    elif predicted_label == "moderate":
        forbidden = [
            "low overall activation", "high overall activation",
            "low activation session", "high activation session",
        ]
        for p in forbidden:
            if p in report_lower:
                errors.append(f"Inconsistent phrase for moderate activation: '{p}'.")

    elif predicted_label == "high":
        forbidden = [
            "low overall activation", "moderate overall activation",
            "low activation session", "moderate activation session",
        ]
        for p in forbidden:
            if p in report_lower:
                errors.append(f"Inconsistent phrase for high activation: '{p}'.")

    # ── 4. Vocabulario clinico prohibido ──────────────────────────────
    forbidden_terms = [
        "diagnosis", "disease", "treatment", "medication",
        "medical condition", "neurological", "parkinson",
        "patient", "clinician", "doctor", "clinical decision",
    ]
    for term in forbidden_terms:
        if term in report_lower:
            errors.append(f"Forbidden term detected: '{term}'.")

    # ── 5. Sin bullets / markdown ─────────────────────────────────────
    if "- " in report:
        errors.append("Bullet points detected.")
    if "**" in report:
        errors.append("Markdown bold detected.")

    # ── 6. EMG/HR no se mezclan ───────────────────────────────────────
    feature_mixups = [
        "contractions or rest windows detected in the hr",
        "contractions were detected in the hr",
        "rest windows detected in the hr",
        "hr contractions",
        "hr rest windows",
        "rest windows in the hr",
        "contractions in the hr",
    ]
    for p in feature_mixups:
        if p in report_lower:
            errors.append(f"EMG/HR feature mix-up detected: '{p}'.")

    # ── 7. Feedback no explica la clasificacion ni causas ─────────────
    feedback_text  = _get_section_text(report, "Feedback / recommendation")
    feedback_lower = feedback_text.lower()

    if feedback_text:
        if _count_sentences(feedback_text) > 2:
            errors.append("Feedback section has more than 2 sentences.")

        feedback_forbidden_phrases = [
            "predicted class", "predicted label", "classification",
            "classified", "model decision",
            "caused by", "due to", "contributing factors", "led to",
        ]
        for phrase in feedback_forbidden_phrases:
            if phrase in feedback_lower:
                errors.append(
                    f"Feedback explains classification or causes: '{phrase}'."
                )

    # ── 8. Session summary debe citar >= 2 valores numericos ──────────
    session_summary = _get_section_text(report, "Session summary")
    if session_summary:
        numeric_values = re.findall(r"\d+(?:\.\d+)?", session_summary)
        if len(numeric_values) < 2:
            errors.append(
                "Session summary does not mention at least two concrete numeric values."
            )

    return len(errors) == 0, errors


# --------------------------------------------------------------------------
# Correction prompt: se construye a partir del report rechazado + errores.
# --------------------------------------------------------------------------
def build_correction_prompt(original_report: str,
                            features: Dict,
                            predicted_label: str,
                            errors: List[str]) -> str:
    """
    Construye el prompt de correccion para el LLM. Inyecta:
      - el report original (para que el modelo edite, no escriba desde cero)
      - la lista de errores tipados
      - el feature summary (re-import dinamico para evitar circularidad)
    """
    # Import diferido para evitar ciclos prompt_builder <-> validator
    from .prompt_builder import build_feature_summary

    feature_summary = build_feature_summary(features)
    predicted_label = str(predicted_label).strip().lower()

    return f"""Rewrite the following technical report for a student sensor prototype called ParkiSense.

The fixed predicted label is:
{predicted_label} activation

The previous report had these problems:
{json.dumps(errors, indent=4)}

Original report:
{original_report}

Feature summary:
{feature_summary}

Rewrite the report with exactly these three sections:

Classification:
Session summary:
Feedback / recommendation:

Strict rules:
- The report must clearly state that the predicted class is {predicted_label} activation.
- Do not mention any other activation class as the final interpretation.
- Do not contradict the predicted label.
- The Session summary must mention at least two concrete numeric values from the feature summary.
- Use EMG terms only for EMG features.
- Use HR terms only for HR features.
- Do not say that contractions or rest windows are HR features.
- Do not use bullet points.
- Do not use numbered lists.
- Do not use markdown bold.
- Do not mention diagnosis, disease, treatment, medication, medical conditions, neurological conditions, Parkinson, patient, clinician, doctor, or clinical decision.
- The Feedback / recommendation section must only include technical recommendations.
- The Feedback / recommendation section must not mention the predicted class.
- The Feedback / recommendation section must not explain the model decision.
- The Feedback / recommendation section must not include causes or contributing factors.
- The Feedback / recommendation section must be maximum 2 sentences.
- Keep the report short and neutral.
"""
