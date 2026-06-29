# =============================================================================
# ParkiSense -- agent (Fase 4)
#
# Capa de agente IA / LLM local con safety loop:
#   - ollama_client     : cliente HTTP a Ollama (localhost:11434)
#   - prompt_builder    : prompt estricto en ingles/espanol
#   - validator         : validacion + correction prompt
#   - report_generator  : orquesta features -> prompt -> Ollama -> validacion
#                         -> retry -> AgentReport parseado
# =============================================================================

from .ollama_client    import OllamaClient, OllamaError
from .prompt_builder   import build_prompt, build_feature_summary
from .validator        import validate_report, build_correction_prompt
from .report_generator import generate_report, save_report_to_disk, AgentReport

__all__ = [
    "OllamaClient",
    "OllamaError",
    "build_prompt",
    "build_feature_summary",
    "validate_report",
    "build_correction_prompt",
    "generate_report",
    "save_report_to_disk",
    "AgentReport",
]
