"""Tests for generation metadata."""

from datetime import datetime

from fabulae import __version__
from fabulae.models import GenerationMetadata, ProjectConfig


def test_generation_metadata_creation() -> None:
    """Test GenerationMetadata can be created with all fields."""
    metadata = GenerationMetadata(
        generated_at=datetime.now(),
        generator_version=__version__,
        original_idea="test idea",
        model="test-model",
        temperature=0.7,
        variation=0.5,
        enrichment_enabled=True,
        format="novel",
    )
    assert metadata.original_idea == "test idea"
    assert metadata.generator_version == __version__
    assert metadata.model == "test-model"
    assert metadata.temperature == 0.7
    assert metadata.variation == 0.5
    assert metadata.enrichment_enabled is True
    assert metadata.format == "novel"


def test_generation_metadata_with_optional_fields() -> None:
    """Test GenerationMetadata with optional fields."""
    metadata = GenerationMetadata(
        generated_at=datetime.now(),
        generator_version=__version__,
        original_idea="test idea",
        model="test-model",
        temperature=0.7,
        variation=0.5,
        enrichment_enabled=True,
        format="novel",
        shape="heros-journey",
        seed=42,
        language="en",
    )
    assert metadata.shape == "heros-journey"
    assert metadata.seed == 42
    assert metadata.language == "en"


def test_generation_metadata_with_shape_file() -> None:
    """Test GenerationMetadata with shape_file path."""
    metadata = GenerationMetadata(
        generated_at=datetime.now(),
        generator_version=__version__,
        original_idea="test idea",
        model="test-model",
        temperature=0.7,
        variation=0.5,
        enrichment_enabled=True,
        format="novel",
        shape_file="/path/to/shape.yml",
    )
    assert metadata.shape_file == "/path/to/shape.yml"


def test_project_config_with_metadata() -> None:
    """Test ProjectConfig can include metadata."""
    metadata = GenerationMetadata(
        generated_at=datetime.now(),
        generator_version=__version__,
        original_idea="test idea",
        model="test-model",
        temperature=0.7,
        variation=0.5,
        enrichment_enabled=True,
        format="novel",
    )
    config = ProjectConfig(version=__version__, title="Test", metadata=metadata)
    assert config.metadata is not None
    assert config.metadata.original_idea == "test idea"


def test_project_config_metadata_is_optional() -> None:
    """Test ProjectConfig metadata is optional."""
    config = ProjectConfig(version=__version__, title="Test")
    assert config.metadata is None


def test_generation_metadata_timestamp() -> None:
    """Test GenerationMetadata preserves timestamp."""
    timestamp = datetime(2026, 1, 13, 12, 0, 0)
    metadata = GenerationMetadata(
        generated_at=timestamp,
        generator_version=__version__,
        original_idea="test idea",
        model="test-model",
        temperature=0.7,
        variation=0.5,
        enrichment_enabled=True,
        format="novel",
    )
    assert metadata.generated_at == timestamp


def test_generation_metadata_with_no_shape_true() -> None:
    """Test GenerationMetadata with no_shape=True (explicit free-form generation)."""
    metadata = GenerationMetadata(
        generated_at=datetime.now(),
        generator_version=__version__,
        original_idea="test idea",
        model="test-model",
        temperature=0.7,
        variation=0.5,
        enrichment_enabled=True,
        format="novel",
        no_shape=True,
    )
    assert metadata.no_shape is True
    assert metadata.shape is None
    assert metadata.shape_file is None


def test_generation_metadata_no_shape_defaults_to_none() -> None:
    """Test GenerationMetadata no_shape defaults to None (backward compatibility)."""
    metadata = GenerationMetadata(
        generated_at=datetime.now(),
        generator_version=__version__,
        original_idea="test idea",
        model="test-model",
        temperature=0.7,
        variation=0.5,
        enrichment_enabled=True,
        format="novel",
    )
    assert metadata.no_shape is None


def test_generation_metadata_shape_and_no_shape_both_false() -> None:
    """Test GenerationMetadata with auto-selected shape (no_shape is None/False, shape is set)."""
    metadata = GenerationMetadata(
        generated_at=datetime.now(),
        generator_version=__version__,
        original_idea="test idea",
        model="test-model",
        temperature=0.7,
        variation=0.5,
        enrichment_enabled=True,
        format="novel",
        shape="romance-arc",  # Auto-selected shape
        no_shape=None,  # Not explicitly set to --no-shape
    )
    assert metadata.shape == "romance-arc"
    assert metadata.no_shape is None
