"""LLM call wrapper using litellm for unified multi-model interface with auto-retry."""

import asyncio
import json
import logging
import os
import random
from pathlib import Path
from typing import Any

import litellm

logger = logging.getLogger(__name__)

_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:]
        if "=" in line:
            key, val = line.split("=", 1)
            val = val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                val = val[1:-1]
            else:
                if " #" in val:
                    val = val[:val.index(" #")].strip()
            os.environ.setdefault(key.strip(), val)
else:
    logger.warning(
        ".env file not found at %s — API configuration must be provided "
        "via environment variables. See .env.example for the template.",
        _env_path,
    )

_llm_provider = os.environ.get("LLM_PROVIDER", "dev").lower().strip()

_PROVIDER_CONFIGS = {
    "venus": {
        "base": os.environ.get("VENUS_API_BASE", ""),
        "key": os.environ.get("VENUS_API_KEY", ""),
    },
    "dev": {
        "base": os.environ.get("DEV_API_BASE", ""),
        "key": os.environ.get("DEV_API_KEY", "not-needed"),
    },
}

if _llm_provider not in _PROVIDER_CONFIGS:
    logger.warning("Unknown LLM_PROVIDER=%r, falling back to 'dev'", _llm_provider)
    _llm_provider = "dev"

_cfg = _PROVIDER_CONFIGS[_llm_provider]

if not _cfg["base"]:
    raise RuntimeError(
        f"LLM_PROVIDER='{_llm_provider}' but API base URL is empty. "
        f"Please set {_llm_provider.upper()}_API_BASE in .env file. "
        f"See .env.example for the configuration template."
    )
if _llm_provider == "venus" and not _cfg["key"]:
    raise RuntimeError(
        "LLM_PROVIDER='venus' but VENUS_API_KEY is empty. "
        "Please set VENUS_API_KEY in .env file."
    )

os.environ["OPENAI_API_BASE"] = _cfg["base"]
os.environ["OPENAI_API_KEY"] = _cfg["key"]
logger.info("LLM Provider: %s → %s", _llm_provider, _cfg["base"])

_VENUS_MODEL_MAP: dict[str, str] = {
    "claude-sonnet-4.6": "claude-sonnet-4-6",
    "claude-opus-4.6": "claude-opus-4-6",
}


def _map_model_name(model: str) -> str:
    if _llm_provider == "venus" and model in _VENUS_MODEL_MAP:
        mapped = _VENUS_MODEL_MAP[model]
        logger.debug("Venus model mapping: %s → %s", model, mapped)
        return mapped
    return model

litellm.set_verbose = False
litellm.drop_params = True



_RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    litellm.exceptions.RateLimitError,       # 429
    litellm.exceptions.ServiceUnavailableError,  # 503
    litellm.exceptions.APIConnectionError,
    litellm.exceptions.Timeout,
    litellm.exceptions.InternalServerError,  # 500
)

MAX_RETRIES = 5
BASE_DELAY = 1.5
MAX_DELAY = 60.0
JITTER_RANGE = 1.0


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, _RETRYABLE_EXCEPTIONS):
        return True
    if isinstance(exc, asyncio.CancelledError):
        return False
    if hasattr(exc, "status_code"):
        code = exc.status_code
        if code == 429 or code >= 500:
            return True
    msg = str(exc).lower()
    transient_keywords = (
        "no available passageway",
        "no available channel",
        "upstream timeout",
        "upstream connection",
        "bad gateway",                  # 502
        "service unavailable",          # 503
        "gateway timeout",              # 504
        "model service error",
        "model service error (cn)",
    )
    if any(kw in msg for kw in transient_keywords):
        return True
    return False


async def complete(
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float = 1.0,
    max_tokens: int = 16384,
    stop: list[str] | None = None,
) -> Any:
    """Call the LLM with auto-retry on transient errors (502, 429, timeout)."""
    model = _map_model_name(model)

    if "/" not in model and os.environ.get("OPENAI_API_BASE"):
        model = f"openai/{model}"

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        kwargs["tools"] = tools
    if stop:
        kwargs["stop"] = stop

    last_exc: Exception | None = None
    total_retry_delay = 0.0
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await litellm.acompletion(**kwargs)
            if attempt > 0:
                logger.info(
                    "LLM call succeeded after %d retries (total retry delay: %.1fs)",
                    attempt, total_retry_delay,
                )
            return response
        except Exception as exc:
            last_exc = exc
            if attempt >= MAX_RETRIES or not _is_retryable(exc):
                if attempt > 0:
                    logger.error(
                        "LLM call failed permanently after %d retries "
                        "(total retry delay: %.1fs): [%s] %s",
                        attempt, total_retry_delay,
                        type(exc).__name__, exc,
                    )
                raise
            delay = min(BASE_DELAY * (2 ** attempt) + random.uniform(0, JITTER_RANGE), MAX_DELAY)
            total_retry_delay += delay
            status_code = getattr(exc, "status_code", None)
            logger.warning(
                "LLM call failed (attempt %d/%d), retrying in %.1fs: "
                "[%s] %s%s",
                attempt + 1, MAX_RETRIES + 1, delay,
                type(exc).__name__, exc,
                f" (status={status_code})" if status_code else "",
            )
            await asyncio.sleep(delay)

    raise last_exc  # type: ignore[misc]


def extract_text(response) -> str:
    """Extract text content from LLM response."""
    if not response.choices:
        return ""
    msg = response.choices[0].message
    return msg.content or ""


def extract_tool_calls(response) -> list[dict]:
    """Extract tool call requests from LLM response."""
    if not response.choices:
        return []
    msg = response.choices[0].message
    if not msg.tool_calls:
        return []
    result = []
    for tc in msg.tool_calls:
        if isinstance(tc, dict):
            func = tc.get("function", {})
            tc_id = tc.get("id", "")
            name = func.get("name", "")
            args = func.get("arguments", "{}")
        else:
            tc_id = tc.id
            name = tc.function.name
            args = tc.function.arguments
        if isinstance(args, str):
            raw_args_str = args
            try:
                args = json.loads(args)
            except (json.JSONDecodeError, ValueError):
                logger.warning("Invalid JSON in tool_call arguments for '%s': %s", name, args[:200])
                args = {"_parse_error": f"Invalid JSON from LLM. Raw text: {args[:500]}"}
            if name in ("set_final_output", "finalize_task") and not args:
                logger.info(
                    "[diag] %s called with empty args. Raw arguments string "
                    "from LLM: %r (len=%d). msg.content len=%d",
                    name, raw_args_str, len(raw_args_str),
                    len(getattr(msg, "content", "") or ""),
                )
        result.append({
            "id": tc_id,
            "name": name,
            "arguments": args,
        })
    return result


def has_tool_calls(response) -> bool:
    """Check if response contains tool calls."""
    if not response.choices:
        return False
    msg = response.choices[0].message
    return bool(msg.tool_calls)


def response_to_message(response) -> dict:
    """Convert LLM response to OpenAI message format."""
    if not response.choices:
        return {"role": "assistant", "content": ""}
    msg = response.choices[0].message
    return msg.model_dump(exclude_none=True)
