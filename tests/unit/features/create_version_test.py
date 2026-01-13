"""Tests for version handling in generated projects."""

from fabulae import __version__
from fabulae.models import ProjectConfig


def test_project_config_accepts_version() -> None:
    """Test that ProjectConfig can be created with a version."""
    config = ProjectConfig(version=__version__, title="Test")
    assert config.version == __version__


def test_project_config_version_is_optional() -> None:
    """Test that ProjectConfig version is optional."""
    config = ProjectConfig(title="Test")
    assert config.version is None


def test_project_config_version_can_be_string() -> None:
    """Test that ProjectConfig version accepts any string."""
    config = ProjectConfig(version="1.2.3", title="Test")
    assert config.version == "1.2.3"
