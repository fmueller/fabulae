"""Unit tests for shared LLM infrastructure."""

from __future__ import annotations

from typing import Any, cast

import pytest
from pydantic import BaseModel

from fabulae import llm
from fabulae.llm import FAKE_LLM_ENV


class DummyResult(BaseModel):
    value: str


def test_resolve_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FABULAE_LLM_MODEL", raising=False)
    monkeypatch.delenv("FABULAE_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("FABULAE_LLM_API_KEY", raising=False)
    monkeypatch.delenv("FABULAE_LLM_TEMPERATURE", raising=False)
    monkeypatch.delenv("FABULAE_LLM_SEED", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    config = llm.resolve_config(None, None, None, None, None)
    assert config.model == llm.DEFAULT_MODEL
    assert config.base_url == llm.DEFAULT_BASE_URL
    assert config.api_key == llm.DEFAULT_API_KEY
    assert config.temperature == llm.DEFAULT_TEMPERATURE


def test_resolve_config_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FABULAE_LLM_MODEL", "env-model")
    monkeypatch.setenv("FABULAE_LLM_BASE_URL", "http://env.example/v1")
    monkeypatch.setenv("FABULAE_LLM_API_KEY", "env-key")
    monkeypatch.setenv("FABULAE_LLM_TEMPERATURE", "0.42")
    monkeypatch.setenv("FABULAE_LLM_SEED", "42")

    config = llm.resolve_config(None, None, None, None, None)
    assert config.model == "env-model"
    assert config.base_url == "http://env.example/v1"
    assert config.api_key == "env-key"
    assert config.temperature == 0.42
    assert config.seed == 42


def test_resolve_config_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FABULAE_LLM_MODEL", "env-model")
    monkeypatch.setenv("FABULAE_LLM_BASE_URL", "http://fabulae.example/v1")
    monkeypatch.setenv("FABULAE_LLM_API_KEY", "fab-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://openai.example/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("FABULAE_LLM_TEMPERATURE", "0.55")

    config = llm.resolve_config("cli-model", "http://cli.example/v1", "cli-key", 0.11, 7)
    assert config.model == "cli-model"
    assert config.base_url == "http://cli.example/v1"
    assert config.api_key == "cli-key"
    assert config.temperature == 0.11
    assert config.seed == 7

    config = llm.resolve_config(None, None, None, None, None)
    assert config.model == "env-model"
    assert config.base_url == "http://fabulae.example/v1"
    assert config.api_key == "fab-key"
    assert config.temperature == 0.55

    config = llm.resolve_config(None, None, None, 0.9, None)
    assert config.temperature == 0.9


def test_create_agent_uses_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(FAKE_LLM_ENV, raising=False)

    class DummyProvider:
        def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
            self.base_url = base_url
            self.api_key = api_key

    class DummyOpenAIModel:
        def __init__(self, model: str, *, provider: DummyProvider) -> None:
            self.model = model
            self.provider = provider

    class DummyAgent:
        def __init__(
            self,
            model: DummyOpenAIModel,
            output_type: type[BaseModel],
            system_prompt: str,
            model_settings: dict[str, float] | None = None,
            retries: int = 2,
        ) -> None:
            self.model = model
            self.output_type = output_type
            self.system_prompt = system_prompt
            self.model_settings = model_settings
            self.retries = retries

    monkeypatch.setattr(llm, "OpenAIProvider", DummyProvider)
    monkeypatch.setattr(llm, "OpenAIModel", DummyOpenAIModel)
    monkeypatch.setattr(llm, "Agent", DummyAgent)

    config = llm.LLMConfig(
        model="test-model",
        temperature=0.33,
        base_url="http://example/v1",
        api_key="test-key",
        seed=123,
    )
    agent = cast(Any, llm.create_agent(DummyResult, "system prompt", config))
    assert agent.model.model == "test-model"
    assert agent.model.provider.base_url == "http://example/v1"
    assert agent.model.provider.api_key == "test-key"
    assert agent.output_type is DummyResult
    assert agent.system_prompt == "system prompt"
    assert agent.model_settings == {"temperature": 0.33, "seed": 123}
