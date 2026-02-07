from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str


def _has_gemini_key() -> bool:
    return bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))


def _has_openai_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def get_llm_config() -> Optional[LLMConfig]:
    """Returns LLMConfig if configured, else None."""
    # Prefer Gemini if configured.
    if _has_gemini_key():
        model = os.getenv("GEMINI_MODEL") or "gemini-1.5-flash"
        return LLMConfig(provider="gemini", model=model)

    # OpenAI fallback (optional)
    if _has_openai_key():
        model = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        return LLMConfig(provider="openai", model=model)
    return None


def llm_summarize_gemini(prompt: str, model: str) -> str:
    """Calls Gemini via google-genai.

    Requires GEMINI_API_KEY (preferred) or GOOGLE_API_KEY.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return ""

    # Lazy import so dependency is only needed when used
    from google import genai

    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
    )

    # google-genai returns text in resp.text
    return getattr(resp, "text", "") or ""


def llm_summarize_openai(prompt: str, model: str) -> str:
    """Calls OpenAI Chat Completions (openai>=1.x).

    NOTE: This function is only executed when OPENAI_API_KEY is set.
    """
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a data quality and anomaly explanation assistant. Be factual and concise. Do not invent numbers."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    return resp.choices[0].message.content or ""


def llm_generate_text(prompt: str) -> Dict[str, Any]:
    """Generate text using configured LLM. Returns dict with fields.

    The AI layer uses LLM only to improve narrative; it should be safe to fall back.
    """
    cfg = get_llm_config()
    if cfg is None:
        return {"mode": "deterministic", "text": ""}

    if cfg.provider == "openai":
        return {"mode": "openai", "model": cfg.model, "text": llm_summarize_openai(prompt, cfg.model)}

    if cfg.provider == "gemini":
        return {"mode": "gemini", "model": cfg.model, "text": llm_summarize_gemini(prompt, cfg.model)}

    return {"mode": "deterministic", "text": ""}
