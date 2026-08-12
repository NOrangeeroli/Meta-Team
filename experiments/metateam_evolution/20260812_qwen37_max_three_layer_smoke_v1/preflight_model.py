#!/usr/bin/env python3
"""Credential-safe qwen3.7-max tool-call preflight through Meta-Team's wrapper."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
from core import llm


MODEL = "qwen3.7-max"
TOOL_NAME = "record_probe"


async def run() -> int:
    response = await llm.complete(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": (
                    "Call record_probe exactly once with value 391. "
                    "Return no natural-language answer."
                ),
            }
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": TOOL_NAME,
                    "description": "Record the integer used by this API capability probe.",
                    "parameters": {
                        "type": "object",
                        "properties": {"value": {"type": "integer"}},
                        "required": ["value"],
                    },
                },
            }
        ],
        temperature=0.0,
        max_tokens=128,
    )
    calls = llm.extract_tool_calls(response)
    passed = (
        len(calls) == 1
        and calls[0].get("name") == TOOL_NAME
        and calls[0].get("arguments", {}).get("value") == 391
    )
    print(
        json.dumps(
            {
                "status": "PASS" if passed else "FAIL",
                "requested_model": MODEL,
                "returned_model": getattr(response, "model", None),
                "tool_call_count": len(calls),
                "tool_names": [call.get("name") for call in calls],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
