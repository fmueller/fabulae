"""Tests for the pipelines module and format-specific pipeline submodules."""

import inspect
from typing import get_type_hints

from fabulae.features.create.schemas import CreateOptions
from fabulae.llm import LLMConfig


def test_pipelines_module_can_be_imported() -> None:
    """Test that the pipelines module can be imported."""
    from fabulae.features.create import pipelines  # noqa: F401

    assert pipelines is not None


def test_prose_submodule_can_be_imported() -> None:
    """Test that the prose submodule can be imported."""
    from fabulae.features.create.pipelines import prose  # noqa: F401

    assert prose is not None


def test_micro_prose_submodule_can_be_imported() -> None:
    """Test that the micro_prose submodule can be imported."""
    from fabulae.features.create.pipelines import micro_prose  # noqa: F401

    assert micro_prose is not None


def test_poem_submodule_can_be_imported() -> None:
    """Test that the poem submodule can be imported."""
    from fabulae.features.create.pipelines import poem  # noqa: F401

    assert poem is not None


def test_generate_prose_function_exists() -> None:
    """Test that generate_prose function exists and can be imported."""
    from fabulae.features.create.pipelines.prose import generate_prose

    assert generate_prose is not None
    assert callable(generate_prose)


def test_generate_prose_function_signature() -> None:
    """Test that generate_prose has the expected function signature."""
    from fabulae.features.create.pipelines.prose import generate_prose
    from fabulae.models import Project

    # Get the signature
    sig = inspect.signature(generate_prose)

    # Check parameter names
    param_names = list(sig.parameters.keys())
    assert param_names == ["idea", "format", "options", "llm_config", "progress", "artifacts_dir"]

    # Check that function is async
    assert inspect.iscoroutinefunction(generate_prose)

    # Check parameter types using get_type_hints for proper evaluation
    type_hints = get_type_hints(generate_prose)
    assert type_hints["idea"] is str
    assert type_hints["format"] is str
    assert type_hints["options"] is CreateOptions
    assert type_hints["llm_config"] is LLMConfig

    # Check return type annotation
    assert type_hints["return"] is Project


def test_generate_prose_accepts_expected_parameters() -> None:
    """Test that generate_prose accepts the expected parameters and returns a coroutine."""
    from fabulae.features.create.pipelines.prose import generate_prose

    # Create minimal test inputs
    options = CreateOptions()
    llm_config = LLMConfig(model="claude-3-haiku-20240307")

    # Just verify that calling the function with proper parameters creates a coroutine
    # We don't actually await it since this is a skeleton
    coro = generate_prose(
        idea="A test story",
        format="novel",
        options=options,
        llm_config=llm_config,
    )

    # Verify it returns a coroutine
    assert inspect.iscoroutine(coro)

    # Clean up the coroutine
    coro.close()


def test_generate_micro_prose_exists() -> None:
    """Test that generate_micro_prose function exists and is callable."""
    from fabulae.features.create.pipelines.micro_prose import generate_micro_prose

    assert callable(generate_micro_prose)
    assert inspect.iscoroutinefunction(generate_micro_prose)


def test_generate_micro_prose_signature() -> None:
    """Test that generate_micro_prose has the expected signature."""
    from fabulae.features.create.pipelines.micro_prose import generate_micro_prose

    sig = inspect.signature(generate_micro_prose)
    params = sig.parameters

    assert "idea" in params
    assert "options" in params
    assert "llm_config" in params
    assert "artifacts_dir" in params

    # Check that artifacts_dir has a default of None
    assert params["artifacts_dir"].default is None
