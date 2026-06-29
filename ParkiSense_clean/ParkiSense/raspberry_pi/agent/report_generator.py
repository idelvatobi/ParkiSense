# =============================================================================
# ParkiSense -- agent/report_generator.py
#
# Orquestador de la capa de agente con SAFETY LOOP.
#
#     features + ml_result
#            |
#            v
#     prompt_builder.build_prompt(...)
#            |
#            v
#     OllamaClient.generate(prompt)
#            |
#            v
#     validator.validate_report(text)
#            |          \
#            v           \-- if errors -->  build_correction_prompt
#       (is_valid)               loop hasta max_attempts
#            |
#            v
#     parse_response  -->  AgentReport(classification, summary, feedback)
#            |
#            v
#     opcional: save_report_to_disk(...)
#
# Si tras max_attempts el report sigue sin validar, devolvemos igualmente
# el ultimo intento con la lista de errores en validation_errors. La UI
# decide si mostrarlo con warning o como exito completo.
# =============================================================================

from __future__ import annotations

import os
import re
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Dict, List, Optional

import config
from .ollama_client import OllamaClient, OllamaError
from .prompt_builder  import build_prompt
from .validator       import validate_report, build_correction_prompt


# --------------------------------------------------------------------------
# Estructura del report parseado
# --------------------------------------------------------------------------
@dataclass
class AgentReport:
    """Resultado del agente listo para mostrar en la UI."""
    classification:    str
    summary:           str
    feedback:          str
    raw_response:      str               # texto completo del ultimo intento
    prompt:            str               # prompt del primer intento
    model:             str
    language:          str
    generated_at:      str
    attempts:          int               # cuantos intentos hicieron falta
    validation_passed: bool              # True si el ultimo intento valido OK
    validation_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


# --------------------------------------------------------------------------
# Parser: extrae las 3 secciones por nombre (no por brackets)
# --------------------------------------------------------------------------
_SECTION_RE = re.compile(
    r"Classification:\s*(?P<cls>.*?)"
    r"Session\s+summary:\s*(?P<sum>.*?)"
    r"Feedback\s*/\s*recommendation:\s*(?P<fb>.*)",
    re.IGNORECASE | re.DOTALL,
)


def _parse_response(text: str) -> Dict[str, str]:
    """
    Extrae las tres secciones del texto del LLM. Si el modelo no respeta
    los headers (deberia haber sido capturado por el validator antes), hace
    un fallback razonable: todo el texto va a 'summary'.
    """
    m = _SECTION_RE.search(text)
    if m:
        return {
            "classification": m.group("cls").strip(),
            "summary":        m.group("sum").strip(),
            "feedback":       m.group("fb").strip(),
        }
    # Fallback
    return {
        "classification": "(Section header 'Classification:' not found)",
        "summary":        text.strip(),
        "feedback":       "(Section header 'Feedback / recommendation:' not found)",
    }


# --------------------------------------------------------------------------
# Funcion principal con safety loop
# --------------------------------------------------------------------------
def generate_report(features: Dict,
                    ml_result: Dict,
                    *,
                    client:       Optional[OllamaClient] = None,
                    language:     Optional[str]          = None,
                    max_attempts: int                    = 3) -> AgentReport:
    """
    Pide al LLM local un report estructurado con bucle de validacion +
    correccion automatica.

    Parametros
    ----------
    features     : dict de features (output de feature_extractor.extract_features)
    ml_result    : dict con 'predicted_label' y 'probabilities'
    client       : OllamaClient. Si no se pasa, se instancia desde config.
    language     : 'english' (default) | 'spanish'
    max_attempts : intentos totales (1 inicial + N-1 correcciones). Default 3.

    Devuelve
    --------
    AgentReport. Si validation_passed == False y validation_errors no esta
    vacio, la UI deberia avisar con un warning amarillo de que el report
    se ha generado pero podria contener inconsistencias.

    Lanza
    -----
    OllamaError si Ollama no responde, no tiene el modelo, o falla la
    conexion. (Las inconsistencias logicas no lanzan, se devuelven en
    validation_errors.)
    """
    if client is None:
        client = OllamaClient(
            host    = config.OLLAMA_HOST,
            model   = config.OLLAMA_MODEL,
            timeout = config.OLLAMA_TIMEOUT,
        )
    if language is None:
        language = config.AI_REPORT_LANGUAGE

    predicted_label = str(ml_result.get("predicted_label", "unknown")).strip().lower()

    # 1. Primer prompt
    initial_prompt   = build_prompt(features, ml_result, language=language)
    current_prompt   = initial_prompt

    last_response    = ""
    last_errors: List[str] = []
    is_valid         = False
    attempts_done    = 0

    for attempt in range(1, max_attempts + 1):
        attempts_done = attempt
        print(f"[agent] Ollama attempt {attempt}/{max_attempts}...")

        last_response   = client.generate(current_prompt)
        is_valid, last_errors = validate_report(last_response, predicted_label)

        if is_valid:
            print(f"[agent] Validation passed on attempt {attempt}.")
            break

        print(f"[agent] Validation failed on attempt {attempt} "
              f"with {len(last_errors)} error(s):")
        for e in last_errors:
            print(f"        - {e}")

        # Si todavia quedan intentos, construye correction prompt
        if attempt < max_attempts:
            current_prompt = build_correction_prompt(
                original_report = last_response,
                features        = features,
                predicted_label = predicted_label,
                errors          = last_errors,
            )

    # 2. Parsear el ultimo intento (valido o no)
    parsed = _parse_response(last_response)

    return AgentReport(
        classification    = parsed["classification"],
        summary           = parsed["summary"],
        feedback          = parsed["feedback"],
        raw_response      = last_response,
        prompt            = initial_prompt,
        model             = client.model,
        language          = language,
        generated_at      = datetime.now().isoformat(timespec="seconds"),
        attempts          = attempts_done,
        validation_passed = is_valid,
        validation_errors = last_errors,
    )


# --------------------------------------------------------------------------
# Persistencia
# --------------------------------------------------------------------------
def save_report_to_disk(report: AgentReport,
                        session_dir: str,
                        filename: Optional[str] = None) -> str:
    """
    Guarda el report en `session_dir/<filename>` en formato legible.
    Devuelve la ruta absoluta del fichero creado.
    """
    if filename is None:
        filename = config.AI_REPORT_FILENAME

    os.makedirs(session_dir, exist_ok=True)
    path = os.path.join(session_dir, filename)

    if report.validation_passed:
        validation_block = "Validation : PASSED"
    else:
        errs = "\n             ".join(f"- {e}" for e in report.validation_errors)
        validation_block = f"Validation : FAILED ({len(report.validation_errors)} issues)\n             {errs}"

    content = (
        "ParkiSense -- Session Report (AI-generated)\n"
        "==========================================\n"
        f"Generated at : {report.generated_at}\n"
        f"Model        : {report.model}\n"
        f"Language     : {report.language}\n"
        f"Attempts     : {report.attempts}\n"
        f"{validation_block}\n\n"
        "------------------------------------------\n"
        "CLASSIFICATION\n"
        "------------------------------------------\n"
        f"{report.classification}\n\n"
        "------------------------------------------\n"
        "SESSION SUMMARY\n"
        "------------------------------------------\n"
        f"{report.summary}\n\n"
        "------------------------------------------\n"
        "FEEDBACK / RECOMMENDATION\n"
        "------------------------------------------\n"
        f"{report.feedback}\n\n"
        "==========================================\n"
        "Note: ParkiSense is an educational biomedical prototype.\n"
        "It is NOT a diagnostic device.\n"
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    return path
