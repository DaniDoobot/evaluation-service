import base64
import json
import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()


def build_evaluation_prompt(
    base_instructions: str,
    criteria: list[dict[str, Any]],
    output_schema: dict[str, Any] | None = None,
) -> str:
    criteria_text = json.dumps(
        criteria,
        ensure_ascii=False,
        indent=2,
    )

    output_schema_text = json.dumps(
        output_schema or {},
        ensure_ascii=False,
        indent=2,
    )

    return f"""
{base_instructions}

────────────────────────────────
CRITERIOS DINÁMICOS CONFIGURADOS PARA ESTA EVALUACIÓN
────────────────────────────────
Evalúa la llamada teniendo en cuenta estos criterios configurados para este prompt:

{criteria_text}

────────────────────────────────
FORMATO / ESQUEMA DE SALIDA CONFIGURADO
────────────────────────────────
Si el esquema está vacío, devuelve un JSON válido con:
- metadata
- resumen
- criterios_generales
- criterios_especificos
- campos_extraccion
- evaluacion_global_comentada
- recomendaciones

Si el esquema NO está vacío, respeta estrictamente este esquema:

{output_schema_text}

────────────────────────────────
REGLAS DE RESPUESTA OBLIGATORIAS
────────────────────────────────
Devuelve exclusivamente JSON válido.
No uses markdown.
No añadas texto antes ni después del JSON.
No incluyas ```json ni bloques de código.
No inventes información.
Si no hay información suficiente para un campo, usa null.
La respuesta debe poder parsearse directamente con json.loads().
""".strip()


def extract_json_from_response(text: str) -> dict[str, Any]:
    cleaned = text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned.replace("```json", "", 1).strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```", "", 1).strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    # Por si el modelo mete texto antes o después, intentamos quedarnos
    # con el primer objeto JSON completo.
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")

    if first_brace != -1 and last_brace != -1:
        cleaned = cleaned[first_brace:last_brace + 1]

    return json.loads(cleaned)


def analyze_audio_with_openai_chat_completions(
    audio_bytes: bytes,
    filename: str,
    mime_type: str,
    prompt_text: str,
) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_ANALYSIS_MODEL", "gpt-4o-audio-preview")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY no está configurada")

    suffix = filename.lower().split(".")[-1]

    if suffix not in ["mp3", "wav"]:
        if "wav" in mime_type:
            suffix = "wav"
        elif "mpeg" in mime_type or "mp3" in mime_type:
            suffix = "mp3"
        else:
            suffix = "mp3"

    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

    payload = {
        "model": model,
        "modalities": ["text"],
        "messages": [
            {
                "role": "system",
                "content": (
                    "Eres un evaluador experto de conversaciones telefónicas. "
                    "Debes analizar el audio completo y devolver exclusivamente JSON válido. "
                    "No devuelvas markdown, explicaciones ni texto adicional."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt_text,
                    },
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": audio_base64,
                            "format": suffix,
                        },
                    },
                ],
            },
        ],
    }

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=300,
    )

    if response.status_code >= 400:
        raise RuntimeError(f"OpenAI error {response.status_code}: {response.text}")

    data = response.json()
    content = data["choices"][0]["message"]["content"]

    try:
        return extract_json_from_response(content)
    except Exception as exc:
        raise RuntimeError(
            f"No se pudo parsear la respuesta como JSON. Respuesta recibida: {content}"
        ) from exc