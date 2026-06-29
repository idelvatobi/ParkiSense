# =============================================================================
# ParkiSense -- agent/prompt_builder.py
#
# Construye el prompt que se envia al LLM (Ollama). Adoptamos el enfoque
# del run_full_pipeline.py original del usuario:
#
#   - Feature summary en prosa natural ("EMG features only: ...; ...")
#     en lugar de listas con valores raw. El modelo de 1B se confunde
#     menos con prosa.
#
#   - Reglas estrictas que evitan los fallos tipicos del modelo pequeno:
#       * contradiccion del label predicho
#       * mezcla de EMG/HR
#       * vocabulario clinico (Parkinson, paciente, diagnostico, etc.)
#       * bullets / markdown / numeracion
#       * Feedback explicando la clasificacion
#
#   - Formato fijo de salida con secciones por nombre:
#       Classification:
#       Session summary:
#       Feedback / recommendation:
#     Mas natural para el LLM que [BRACKETS] y mas facil de parsear que
#     una respuesta libre.
# =============================================================================

from __future__ import annotations

from typing import Dict, Optional


# --------------------------------------------------------------------------
# Helpers de formateo seguro: si un campo viene None / NaN / no numerico,
# devuelve None y se omite del summary, asi nunca metemos basura en el prompt.
# --------------------------------------------------------------------------
def _safe_float(value, decimals: int = 2) -> Optional[str]:
    if value is None:
        return None
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return None


def _safe_int(value) -> Optional[str]:
    if value is None:
        return None
    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
# Feature summary en prosa (no listas con bullets).
# El modelo recibe asi solo las features con valor real, sin floats con
# 6 decimales, lo que ayuda a que cite valores exactos en el summary.
# --------------------------------------------------------------------------
def build_feature_summary(features: Dict) -> str:
    f = features

    session_duration         = _safe_float(f.get("session_duration_s"))
    events_count             = _safe_int(f.get("events_count"))

    emg_duration             = _safe_float(f.get("emg_duration_s"))
    emg_rms_mean             = _safe_float(f.get("emg_rms_mean"))
    emg_rms_max              = _safe_float(f.get("emg_rms_max"))
    emg_rms_std              = _safe_float(f.get("emg_rms_std"))
    emg_contractions         = _safe_int(f.get("emg_contractions_count"))
    emg_rest_count           = _safe_int(f.get("emg_rest_count"))
    emg_contraction_ratio    = _safe_float(f.get("emg_contraction_ratio"))

    hr_duration              = _safe_float(f.get("hr_duration_s"))
    hr_raw_mean              = _safe_float(f.get("hr_raw_mean"))
    hr_filtered_mean         = _safe_float(f.get("hr_filtered_mean"))
    hr_filtered_max          = _safe_float(f.get("hr_filtered_max"))
    hr_filtered_std          = _safe_float(f.get("hr_filtered_std"))
    hr_valid_ratio           = _safe_float(f.get("hr_valid_ratio"))
    hr_above_threshold_ratio = _safe_float(f.get("hr_above_threshold_ratio"))

    lines = []

    general_parts = []
    if session_duration is not None:
        general_parts.append(f"total session duration = {session_duration} s")
    if events_count is not None:
        general_parts.append(f"recorded events = {events_count}")
    if general_parts:
        lines.append("General session features: " + "; ".join(general_parts) + ".")

    emg_parts = []
    if emg_duration is not None:          emg_parts.append(f"EMG duration = {emg_duration} s")
    if emg_rms_mean is not None:          emg_parts.append(f"mean EMG RMS = {emg_rms_mean}")
    if emg_rms_max is not None:           emg_parts.append(f"maximum EMG RMS = {emg_rms_max}")
    if emg_rms_std is not None:           emg_parts.append(f"EMG RMS standard deviation = {emg_rms_std}")
    if emg_contractions is not None:      emg_parts.append(f"detected EMG contractions = {emg_contractions}")
    if emg_rest_count is not None:        emg_parts.append(f"EMG rest windows = {emg_rest_count}")
    if emg_contraction_ratio is not None: emg_parts.append(f"EMG contraction ratio = {emg_contraction_ratio}")
    if emg_parts:
        lines.append("EMG features only: " + "; ".join(emg_parts) + ".")

    hr_parts = []
    if hr_duration is not None:              hr_parts.append(f"HR duration = {hr_duration} s")
    if hr_raw_mean is not None:              hr_parts.append(f"mean raw HR = {hr_raw_mean}")
    if hr_filtered_mean is not None:         hr_parts.append(f"mean filtered HR = {hr_filtered_mean}")
    if hr_filtered_max is not None:          hr_parts.append(f"maximum filtered HR = {hr_filtered_max}")
    if hr_filtered_std is not None:          hr_parts.append(f"filtered HR standard deviation = {hr_filtered_std}")
    if hr_valid_ratio is not None:           hr_parts.append(f"HR valid ratio = {hr_valid_ratio}")
    if hr_above_threshold_ratio is not None: hr_parts.append(f"HR above-threshold ratio = {hr_above_threshold_ratio}")
    if hr_parts:
        lines.append("HR features only: " + "; ".join(hr_parts) + ".")

    return "\n".join(lines)


# --------------------------------------------------------------------------
# Prompt principal (primer intento). Ingles por defecto.
# El switch a espanol cambia solo el preambulo y las plantillas de las
# secciones; las reglas tecnicas siguen en ingles para que el modelo
# pequeno no se pierda con dos idiomas a la vez.
# --------------------------------------------------------------------------
def build_prompt(features: Dict,
                 ml_result: Dict,
                 *,
                 language: str = "english") -> str:
    """
    Construye el prompt completo.

    Parametros
    ----------
    features  : dict de features (mismas keys que rf_feature_columns.json).
    ml_result : dict con "predicted_label" y "probabilities".
    language  : "english" (default) o "spanish".

    Devuelve
    --------
    str listo para OllamaClient.generate().
    """
    predicted_label = str(ml_result.get("predicted_label", "unknown")).strip().lower()
    feature_summary = build_feature_summary(features)

    if language == "spanish":
        return _build_prompt_es(predicted_label, feature_summary)
    return _build_prompt_en(predicted_label, feature_summary)


# --------------------------------------------------------------------------
# Plantilla en INGLES
# --------------------------------------------------------------------------
def _build_prompt_en(predicted_label: str, feature_summary: str) -> str:
    return f"""You are a technical report assistant for a student sensor prototype called ParkiSense.

The session has already been classified by a Machine Learning model.

The fixed predicted label is: {predicted_label} activation.

Your task is to write a short technical report based only on the feature summary.

The report must contain exactly these three sections:

Classification:
Session summary:
Feedback / recommendation:

Strict rules:
- Use "{predicted_label} activation" as the final and only activation class.
- Do not classify the session again.
- Do not contradict the predicted label.
- Do not mention low, moderate, or high activation unless it matches "{predicted_label} activation".
- Do not describe the session using any activation class other than "{predicted_label}".
- Do not use bullet points.
- Do not use numbered lists.
- Do not use markdown bold.
- Do not add extra context.
- Do not mention diagnosis, disease, treatment, medication, symptoms, medical conditions, neurological conditions, Parkinson, patient, clinician, doctor, or clinical decision.
- Use EMG terms only for EMG features.
- Use HR terms only for HR features.
- Do not say that contractions or rest windows are HR features.
- Do not invent durations or values.
- If both session duration and EMG duration are present, describe them clearly as different metrics.
- The Session summary must mention at least two concrete values from the feature summary.
- The Session summary must be consistent with "{predicted_label} activation".
- The Feedback / recommendation section must only include technical recommendations.
- The Feedback / recommendation section must not explain the model decision.
- The Feedback / recommendation section must not mention the predicted class.
- The Feedback / recommendation section must not include causes or contributing factors.
- The Feedback / recommendation section must be maximum 2 sentences.
- Keep the whole report short.

Feature summary:
{feature_summary}

Write the report exactly in this format:

Classification:
The predicted class for this session is {predicted_label} activation.

Session summary:
Write one short paragraph of 2 to 4 sentences. Mention at least two concrete values from the feature summary. Use EMG features only as EMG features and HR features only as HR features.

Feedback / recommendation:
Write one short paragraph of maximum 2 sentences. Include only technical recommendations such as checking sensor placement, repeating the session under similar conditions, and comparing with baseline or future sessions.
"""


# --------------------------------------------------------------------------
# Plantilla en ESPANOL (mantenemos los nombres de seccion en ingles para
# que el parser y el validator sigan funcionando igual)
# --------------------------------------------------------------------------
def _build_prompt_es(predicted_label: str, feature_summary: str) -> str:
    return f"""Eres un asistente tecnico de informes para un prototipo de sensores estudiantil llamado ParkiSense.

La sesion ya ha sido clasificada por un modelo de Machine Learning.

La etiqueta predicha fija es: {predicted_label} activation.

Tu tarea es escribir un informe tecnico corto basado unicamente en el resumen de features.

El informe debe contener exactamente estas tres secciones (en ingles, no traduzcas los titulos):

Classification:
Session summary:
Feedback / recommendation:

Reglas estrictas (escribe las secciones en castellano):
- Usa "{predicted_label} activation" como la unica clase de activacion final.
- No vuelvas a clasificar la sesion.
- No contradigas la etiqueta predicha.
- No menciones low, moderate ni high activation salvo cuando coincida con "{predicted_label} activation".
- No uses bullets, listas numeradas ni markdown en negrita.
- No anadas contexto extra.
- No menciones diagnostico, enfermedad, tratamiento, medicacion, sintomas, condiciones medicas, neurologicas, Parkinson, paciente, clinico, medico, ni decision clinica.
- Usa terminos EMG solo para features EMG.
- Usa terminos HR solo para features HR.
- No digas que las contracciones o las ventanas de reposo son features HR.
- No inventes duraciones ni valores.
- Si la duracion de sesion y la duracion EMG aparecen, descrubelas claramente como metricas distintas.
- El Session summary debe mencionar al menos dos valores concretos del resumen de features.
- El Session summary debe ser coherente con "{predicted_label} activation".
- La seccion Feedback / recommendation solo debe incluir recomendaciones tecnicas.
- La seccion Feedback / recommendation no debe explicar la decision del modelo.
- La seccion Feedback / recommendation no debe mencionar la clase predicha.
- La seccion Feedback / recommendation no debe incluir causas ni factores contribuyentes.
- La seccion Feedback / recommendation debe tener como maximo 2 frases.
- Manten todo el informe corto.

Feature summary:
{feature_summary}

Escribe el informe exactamente con este formato:

Classification:
La clase predicha para esta sesion es {predicted_label} activation.

Session summary:
Escribe un parrafo corto de 2 a 4 frases. Menciona al menos dos valores concretos del resumen de features. Usa features EMG solo como features EMG y features HR solo como features HR.

Feedback / recommendation:
Escribe un parrafo corto de maximo 2 frases. Incluye solo recomendaciones tecnicas como comprobar la colocacion de los sensores, repetir la sesion en condiciones similares y comparar con sesiones de referencia o futuras.
"""
