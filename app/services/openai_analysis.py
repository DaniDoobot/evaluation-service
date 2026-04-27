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

Cada criterio tiene estos campos:
- code: identificador interno del criterio.
- label: nombre visible del criterio.
- description: descripción de lo que debe evaluarse o extraerse.
- category: tipo de criterio. Puede ser general, procedimiento, argumentacion, extraccion, check u otro.
- scale_type: tipo de valoración esperada.
- requires_feedback: indica si debe devolverse feedback explicativo.
- weight: importancia relativa del criterio.
- is_active: indica si el criterio debe evaluarse.
- sort_order: posición del criterio.

────────────────────────────────
REGLAS PARA LOS CRITERIOS DINÁMICOS
────────────────────────────────
Debes evaluar TODOS los criterios activos recibidos en la lista anterior.

Los criterios deben devolverse dentro de:

"criterios_especificos": {{
  "<code_del_criterio>": ...
}}

Usa SIEMPRE el code exacto de cada criterio como clave.

No inventes criterios nuevos.
No omitas criterios activos.
Si no hay información suficiente, usa null en el valor correspondiente, pero mantén la clave del criterio.

────────────────────────────────
FORMATO SEGÚN scale_type
────────────────────────────────

1. Si scale_type = "numeric_0_10":
Devuelve:
"<code>": {{
  "score": number|null,
  "feedback": string|null
}}

La puntuación debe ir de 0 a 10.

Ejemplo:
"empatia": {{
  "score": 7,
  "feedback": "El agente escuchó y respondió correctamente, aunque pudo validar mejor la preocupación del cliente."
}}

2. Si scale_type = "numeric_0_100":
Devuelve:
"<code>": {{
  "score": number|null,
  "feedback": string|null
}}

La puntuación debe ir de 0 a 100.

3. Si scale_type = "boolean_si_no":
Devuelve:
"<code>": {{
  "value": "Si"|"No"|null,
  "feedback": string|null
}}

Usa:
- "Si" si el hecho evaluado ocurre claramente en la llamada.
- "No" si el hecho evaluado no ocurre.
- null si no hay contexto suficiente para determinarlo.

No devuelvas score para criterios boolean_si_no.
No conviertas un check Sí/No en puntuación numérica.

Ejemplo:
"pregunta_cita": {{
  "value": "Si",
  "feedback": "El agente preguntó explícitamente al cliente si quería avanzar con la reserva de una cita."
}}

4. Si scale_type = "text":
Devuelve:
"<code>": {{
  "value": string|null,
  "feedback": string|null
}}

Usa value para el texto extraído de la llamada.
Usa null si no aparece la información.

No devuelvas score para criterios text.

Ejemplo:
"motivo_no_cita": {{
  "value": "El cliente no podía acudir en los horarios disponibles.",
  "feedback": "La clienta indicó que buscaba cita el sábado por la tarde, pero el agente explicó que solo había disponibilidad por la mañana."
}}

5. Si scale_type = "category":
Devuelve:
"<code>": {{
  "value": string|null,
  "feedback": string|null
}}

Usa value para la categoría detectada.
Usa null si no se puede clasificar.

────────────────────────────────
REGLA SOBRE FEEDBACK
────────────────────────────────
Si requires_feedback = true:
- feedback debe ser siempre un texto explicativo breve, concreto y basado en la llamada.
- Debe explicar por qué se asignó ese score o value.
- No debe ser genérico.

Si requires_feedback = false:
- feedback puede ser null.
- Aun así, si ayuda a justificar una decisión importante, puedes incluirlo.

Por defecto, el feedback es útil para auditar el análisis, especialmente en checks Sí/No y campos de extracción.

────────────────────────────────
FORMATO / ESQUEMA DE SALIDA CONFIGURADO
────────────────────────────────
Si el esquema está vacío, devuelve un JSON válido con esta estructura general:

{{
  "metadata": {{
    "tipo_conversacion": string|null,
    "idioma": string|null,
    "duracion_estimada_segundos": number|null
  }},
  "resumen": {{
    "resumen_conversacion": string|null,
    "resultado_conversacion": string|null,
    "fortalezas": [string],
    "areas_mejora": [string]
  }},
  "criterios_generales": {{
    "sentiment": {{"score": number|null, "feedback": string|null}},
    "empatia": {{"score": number|null, "feedback": string|null}},
    "simpatia": {{"score": number|null, "feedback": string|null}},
    "claridad": {{"score": number|null, "feedback": string|null}},
    "gestion_objeciones": {{"score": number|null, "feedback": string|null}},
    "uso_nombre_cliente": {{"score": number|null, "feedback": string|null}},
    "uso_preguntas": {{"score": number|null, "feedback": string|null}},
    "saludo_inicio": {{"score": number|null, "feedback": string|null}},
    "despedida_con_refuerzo": {{"score": number|null, "feedback": string|null}},
    "evaluacion_global": {{"score": number|null, "feedback": string|null}},
    "hablando_agente": number|null,
    "hablando_cliente": number|null
  }},
  "criterios_especificos": {{
    "<code_criterio_1>": {{
      "score": number|null,
      "feedback": string|null
    }},
    "<code_criterio_booleano>": {{
      "value": "Si"|"No"|null,
      "feedback": string|null
    }},
    "<code_criterio_texto>": {{
      "value": string|null,
      "feedback": string|null
    }}
  }},
  "campos_extraccion": {{
    "motivo_principal": string|null,
    "resultado": string|null,
    "siguiente_paso": string|null,
    "objeciones": string|null,
    "objecion_1": string|null,
    "objecion_2": string|null,
    "objecion_3": string|null,
    "nombre_cliente": string|null,
    "telefono_cliente": string|null,
    "email_cliente": string|null,
    "fecha_cita": string|null,
    "hora_cita": string|null,
    "direccion": string|null
  }},
  "evaluacion_global_comentada": string|null,
  "recomendaciones": [string]
}}

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

Recuerda especialmente:
- Los criterios numeric_0_10 y numeric_0_100 devuelven score + feedback.
- Los criterios boolean_si_no devuelven value + feedback.
- Los criterios text devuelven value + feedback.
- No muestres boolean_si_no ni text como puntuaciones numéricas.
""".strip()


def extract_json_from_response(text: str) -> dict[str, Any]:
    cleaned = text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned.replace("```json", "", 1).strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```", "", 1).strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

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
