# =============================================================================
# ParkiSense — agent/ollama_client.py
#
# Cliente HTTP minimal para Ollama (LLM local).
# Ollama expone una API REST nativa en http://localhost:11434.
#
# Endpoints usados:
#   POST /api/generate   → inferencia one-shot (stream=False)
#   GET  /api/tags       → lista de modelos instalados (health check)
#
# Diseño:
#   - Sin dependencias pesadas: solo `requests`.
#   - Errores tipados (OllamaError) para que la UI los maneje.
#   - Timeout configurable (importante en la Pi: llama3.2:1b puede
#     tardar 30s-120s en generar el report completo).
# =============================================================================

from __future__ import annotations

import json
from typing import Optional

import requests


class OllamaError(Exception):
    """Error genérico al hablar con Ollama (servicio caído, modelo
    no instalado, timeout, respuesta malformada, etc.).
    """
    pass


class OllamaClient:
    """
    Cliente fino sobre Ollama. Una instancia se reutiliza durante
    toda la vida de la aplicación.

    Ejemplo:
        client = OllamaClient(host="http://localhost:11434",
                              model="llama3.2:1b",
                              timeout=180)
        if client.is_available():
            text = client.generate("Write a short test message.")
    """

    def __init__(self, host: str, model: str, timeout: int = 180):
        # Normalizamos el host (sin slash final)
        self.host    = host.rstrip("/")
        self.model   = model
        self.timeout = timeout

    # ── Health check ──────────────────────────────────────────────────

    def is_available(self) -> bool:
        """
        Devuelve True si el servicio Ollama responde y el modelo
        configurado está instalado. No lanza excepción: silencioso
        para usarse como flag desde la UI.
        """
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=5)
            if r.status_code != 200:
                return False
            data = r.json()
            installed = [m.get("name", "") for m in data.get("models", [])]
            # Aceptamos coincidencia exacta o por prefijo (llama3.2:1b vs llama3.2:1b-instruct)
            return any(self.model == name or name.startswith(self.model)
                       for name in installed)
        except Exception:
            return False

    # ── Inferencia ─────────────────────────────────────────────────────

    def generate(self,
                 prompt: str,
                 *,
                 temperature: float = 0.4,
                 num_predict: int = 600) -> str:
        """
        Llama a /api/generate con stream=False y devuelve el texto
        generado (string). Lanza OllamaError si algo falla.

        Parámetros:
            prompt        : prompt completo (ya formateado por prompt_builder)
            temperature   : 0.0=determinista, 1.0=creativo. 0.4 es buen
                            equilibrio para reports técnicos.
            num_predict   : máx. tokens de respuesta. ~600 cubre los 3
                            bloques (Classification + Summary + Feedback).
        """
        url = f"{self.host}/api/generate"
        payload = {
            "model":   self.model,
            "prompt":  prompt,
            "stream":  False,
            "options": {
                "temperature":  temperature,
                "num_predict":  num_predict,
            },
        }

        try:
            r = requests.post(url, json=payload, timeout=self.timeout)
        except requests.exceptions.ConnectionError as e:
            raise OllamaError(
                f"Cannot reach Ollama at {self.host}. "
                f"Is the service running? (try: ollama serve)\n{e}"
            )
        except requests.exceptions.Timeout:
            raise OllamaError(
                f"Ollama timeout after {self.timeout}s. "
                f"Try a smaller model or increase OLLAMA_TIMEOUT."
            )
        except requests.exceptions.RequestException as e:
            raise OllamaError(f"HTTP error talking to Ollama: {e}")

        if r.status_code != 200:
            raise OllamaError(
                f"Ollama returned HTTP {r.status_code}: {r.text[:200]}"
            )

        try:
            data = r.json()
        except json.JSONDecodeError:
            raise OllamaError("Ollama response was not valid JSON.")

        text: Optional[str] = data.get("response")
        if not text:
            raise OllamaError(
                f"Ollama response had no 'response' field. "
                f"Full payload: {data}"
            )

        return text.strip()
