"""Service layer for entity CRUD operations with LLM integration."""

from __future__ import annotations

import asyncio
from typing import TypeVar, cast

from pydantic import BaseModel

from fabulae.llm import LLMConfig, create_agent

T = TypeVar("T", bound=BaseModel)


async def suggest_entity(
    result_type: type[T],
    system_prompt: str,
    config: LLMConfig,
    user_prompt: str = "Generate the entity based on the context provided.",
) -> T:
    """Generate an entity suggestion using the LLM.

    Args:
        result_type: The Pydantic model type for the suggestion.
        system_prompt: The system prompt with context.
        config: LLM configuration.
        user_prompt: Optional user prompt (defaults to generic request).

    Returns:
        The generated suggestion as a Pydantic model instance.
    """
    agent = create_agent(result_type, system_prompt, config)
    result = await agent.run(user_prompt)
    return cast(T, result.output)


def suggest_entity_sync(
    result_type: type[T],
    system_prompt: str,
    config: LLMConfig,
    user_prompt: str = "Generate the entity based on the context provided.",
) -> T:
    """Synchronous wrapper for suggest_entity."""
    return asyncio.run(suggest_entity(result_type, system_prompt, config, user_prompt))
