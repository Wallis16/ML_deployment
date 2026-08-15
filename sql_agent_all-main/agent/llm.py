"""Thin wrapper around the Groq API (OpenAI-compatible chat completions)
used by every node in the graph. Reads GROQ_API_KEY and GROQ_MODEL from
agent/.env (see agent/README.md) — both are required."""

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from groq import Groq

load_dotenv(Path(__file__).resolve().parent / ".env")

MODEL = os.environ["GROQ_MODEL"]

_client = Groq()


def call_llm(system: str, user: str, *, max_tokens: int = 4096, temperature: float = 0.2) -> str:
    response = _client.chat.completions.create(
        model=MODEL,
        max_completion_tokens=max_tokens,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content or ""


def call_llm_structured(
    system: str,
    user: str,
    schema: dict[str, Any],
    *,
    schema_name: str = "response",
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> dict[str, Any]:
    response = _client.chat.completions.create(
        model=MODEL,
        max_completion_tokens=max_tokens,
        temperature=temperature,
        response_format={
            "type": "json_schema",
            "json_schema": {"name": schema_name, "schema": schema, "strict": True},
        },
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return json.loads(response.choices[0].message.content or "{}")
