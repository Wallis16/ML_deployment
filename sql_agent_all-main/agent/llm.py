"""Thin wrapper around the Groq API (OpenAI-compatible chat completions),
including tool-calling support. Reads GROQ_API_KEY and GROQ_MODEL from
agent/.env (see agent/README.md) — both are required."""

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


def call_llm_tools(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    *,
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> Any:
    """One turn of a tool-calling conversation. Returns the raw assistant
    message (with `.content` and, if the model chose to call a tool,
    `.tool_calls`) — the caller drives the loop and appends results."""
    response = _client.chat.completions.create(
        model=MODEL,
        max_completion_tokens=max_tokens,
        temperature=temperature,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    return response.choices[0].message
