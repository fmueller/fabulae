"""Shared LLM configuration and helpers for Fabulae."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, cast

import httpx
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

T = TypeVar("T")

DEFAULT_MODEL = "ministral-3:3b"
DEFAULT_BASE_URL = "http://localhost:11434/v1"
DEFAULT_API_KEY = "ollama"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TIMEOUT_SECONDS = 5.0
FAKE_LLM_ENV = "FABULAE_FAKE_LLM"


@dataclass(frozen=True)
class LLMConfig:
    """Configuration for OpenAI-compatible LLM providers."""

    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    base_url: str = DEFAULT_BASE_URL
    api_key: str = DEFAULT_API_KEY
    seed: int | None = None


class LLMTestPromptResult(BaseModel):
    """Structured output for connectivity test prompts."""

    echo: str


@dataclass(frozen=True)
class LLMConnectionResult:
    """Structured diagnostics for LLM connectivity checks."""

    reachable: bool
    model_available: bool
    prompt_ok: bool
    latency_ms: float | None
    message: str
    errors: list[str]
    models: list[str]


def _read_env_str(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _read_env_float(name: str) -> float | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid float value for {name}: {value!r}") from exc


def _read_env_int(name: str) -> int | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid int value for {name}: {value!r}") from exc


def resolve_config(
    cli_model: str | None,
    cli_base_url: str | None,
    cli_api_key: str | None,
    cli_temperature: float | None,
    cli_seed: int | None,
) -> LLMConfig:
    """Resolve configuration with precedence: CLI > FABULAE_* > OPENAI_* > defaults."""
    model = cli_model or _read_env_str("FABULAE_LLM_MODEL") or DEFAULT_MODEL
    base_url = (
        cli_base_url or _read_env_str("FABULAE_LLM_BASE_URL") or _read_env_str("OPENAI_BASE_URL") or DEFAULT_BASE_URL
    )
    api_key = cli_api_key or _read_env_str("FABULAE_LLM_API_KEY") or _read_env_str("OPENAI_API_KEY") or DEFAULT_API_KEY
    temperature = cli_temperature if cli_temperature is not None else _read_env_float("FABULAE_LLM_TEMPERATURE")
    if temperature is None:
        temperature = DEFAULT_TEMPERATURE
    seed = cli_seed if cli_seed is not None else _read_env_int("FABULAE_LLM_SEED")
    return LLMConfig(model=model, temperature=temperature, base_url=base_url, api_key=api_key, seed=seed)


class FakeAgent(Generic[T]):
    """Placeholder agent used in tests to prevent live LLM calls."""

    def __init__(
        self,
        output_type: type[T],
        system_prompt: str,
        model_settings: dict[str, float | int | None] | None = None,
    ) -> None:
        self.output_type = output_type
        self.system_prompt = system_prompt
        self.model_settings = model_settings

    async def run(self, *_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError(
            f"LLM calls are disabled in tests ({FAKE_LLM_ENV}=1). Provide a fake agent or stub the call."
        )


DEFAULT_RETRIES = 2


def create_agent(
    result_type: type[T],
    system_prompt: str,
    config: LLMConfig | None = None,
    *,
    retries: int = DEFAULT_RETRIES,
) -> Any:
    """Create a Pydantic AI agent configured for OpenAI-compatible providers.

    Args:
        result_type: The Pydantic model type for structured output.
        system_prompt: The system prompt for the agent.
        config: Optional LLM configuration.
        retries: Number of retries on validation failure (default: 2).
            Pydantic AI automatically sends validation errors back to the LLM.

    Returns:
        A configured Pydantic AI Agent.
    """
    resolved = config or LLMConfig()
    if os.getenv(FAKE_LLM_ENV) == "1":
        return cast(
            Any,
            FakeAgent(
                result_type,
                system_prompt,
                model_settings={
                    "temperature": resolved.temperature,
                    "seed": resolved.seed,
                },
            ),
        )
    provider = OpenAIProvider(base_url=resolved.base_url, api_key=resolved.api_key)
    model = OpenAIModel(resolved.model, provider=provider)
    model_settings: dict[str, float | int] = {"temperature": resolved.temperature}
    if resolved.seed is not None:
        model_settings["seed"] = resolved.seed
    return cast(
        Any,
        Agent(
            model,
            output_type=result_type,
            system_prompt=system_prompt,
            model_settings=cast(Any, model_settings),
            retries=retries,
        ),
    )


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


async def check_model_available(
    config: LLMConfig,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[bool, list[str], str | None]:
    """Check whether the configured model is available on the provider."""
    base_url = _normalize_base_url(config.base_url)
    url = f"{base_url}/models"
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        return False, [], str(exc)
    try:
        payload: dict[str, Any] = response.json()
    except ValueError as exc:
        return False, [], f"Invalid JSON from {url}: {exc}"

    models: list[str] = []
    data = payload.get("data")
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                model_id = item.get("id")
                if isinstance(model_id, str):
                    models.append(model_id)
    return config.model in models, models, None


async def run_test_prompt(
    config: LLMConfig,
    prompt: str | None = None,
) -> LLMTestPromptResult:
    """Run a minimal structured prompt to validate end-to-end LLM execution."""
    system_prompt = "You are a connectivity test. Reply with the exact user message in the echo field."
    user_prompt = prompt or "fabulae"
    agent = create_agent(LLMTestPromptResult, system_prompt, config)
    result = await agent.run(user_prompt)
    return cast(LLMTestPromptResult, result.output)


async def test_llm_connection(
    config: LLMConfig,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> LLMConnectionResult:
    """Run a structured connectivity check for LLM providers."""
    errors: list[str] = []
    start = time.perf_counter()
    model_available, models, model_error = await check_model_available(config, timeout_seconds)
    reachable = model_error is None
    if model_error:
        errors.append(f"Endpoint unreachable: {model_error}")
    if reachable and not model_available:
        errors.append(f"Model {config.model!r} not found on provider.")

    prompt_ok = False
    if reachable and model_available:
        try:
            await run_test_prompt(config)
            prompt_ok = True
        except Exception as exc:  # pragma: no cover - exercised in doctor integration tests
            errors.append(f"Test prompt failed: {exc}")

    latency_ms = (time.perf_counter() - start) * 1000.0
    message = "LLM connection OK." if reachable and model_available and prompt_ok else "LLM connection failed."
    return LLMConnectionResult(
        reachable=reachable,
        model_available=model_available,
        prompt_ok=prompt_ok,
        latency_ms=latency_ms,
        message=message,
        errors=errors,
        models=models,
    )


__all__ = [
    "DEFAULT_API_KEY",
    "DEFAULT_BASE_URL",
    "DEFAULT_MODEL",
    "DEFAULT_RETRIES",
    "DEFAULT_TEMPERATURE",
    "FAKE_LLM_ENV",
    "FakeAgent",
    "LLMConfig",
    "LLMConnectionResult",
    "LLMTestPromptResult",
    "check_model_available",
    "create_agent",
    "resolve_config",
    "run_test_prompt",
    "test_llm_connection",
]
