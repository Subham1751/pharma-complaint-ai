"""
Thin wrapper around the Groq client.

Centralizing the LLM call here means every LangGraph node uses the same
retry/fallback/JSON-parsing behaviour instead of duplicating it. The primary
model is `gemma2-9b-it` (fast + cheap, good for structured extraction);
`llama-3.3-70b-versatile` is used as a fallback when the primary model
errors out or returns malformed JSON, since it is more reliable on
reasoning-heavy prompts (root cause / CAPA generation).
"""
import json
import logging

from groq import Groq

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client = Groq(api_key=settings.GROQ_API_KEY)


def call_llm_json(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> dict:
    """
    Call Groq and parse the response as JSON.

    Tries the primary model first; falls back to the larger model if the
    primary call fails or the response isn't valid JSON. Raises the last
    error if both attempts fail, so the caller (a LangGraph node) can decide
    how to degrade gracefully (e.g. mark the field as "unclassified").
    """
    for model in (settings.GROQ_PRIMARY_MODEL, settings.GROQ_FALLBACK_MODEL):
        try:
            completion = _client.chat.completions.create(
                model=model,
                temperature=temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = completion.choices[0].message.content
            return json.loads(content)
        except (json.JSONDecodeError, Exception) as exc:  # noqa: BLE001 - broad on purpose, we fall back
            logger.warning("LLM call failed with model=%s: %s", model, exc)
            last_error = exc
            continue

    raise RuntimeError(f"All Groq models failed. Last error: {last_error}")
