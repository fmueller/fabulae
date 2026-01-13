"""Tests for data directory structure and package inclusion."""

from pathlib import Path


class TestDataDirectory:
    """Test data directory structure exists."""

    def test_data_directory_exists(self) -> None:
        """Verify src/fabulae/data directory exists."""
        data_dir = Path(__file__).parent.parent.parent.parent / "src" / "fabulae" / "data"
        assert data_dir.exists(), f"Data directory does not exist at {data_dir}"
        assert data_dir.is_dir(), f"Data path is not a directory: {data_dir}"

    def test_data_init_exists(self) -> None:
        """Verify __init__.py exists in data directory."""
        init_file = Path(__file__).parent.parent.parent.parent / "src" / "fabulae" / "data" / "__init__.py"
        assert init_file.exists(), f"__init__.py does not exist at {init_file}"

    def test_story_shapes_directory_exists(self) -> None:
        """Verify src/fabulae/data/story_shapes directory exists."""
        story_shapes_dir = Path(__file__).parent.parent.parent.parent / "src" / "fabulae" / "data" / "story_shapes"
        assert story_shapes_dir.exists(), f"Story shapes directory does not exist at {story_shapes_dir}"
        assert story_shapes_dir.is_dir(), f"Story shapes path is not a directory: {story_shapes_dir}"

    def test_story_shapes_init_exists(self) -> None:
        """Verify __init__.py exists in story_shapes directory."""
        init_file = (
            Path(__file__).parent.parent.parent.parent / "src" / "fabulae" / "data" / "story_shapes" / "__init__.py"
        )
        assert init_file.exists(), f"__init__.py does not exist at {init_file}"


class TestPackageDataInclusion:
    """Test that data files are included in package."""

    def test_pyproject_toml_includes_data_files(self) -> None:
        """Verify pyproject.toml includes data files in package-data."""
        pyproject_path = Path(__file__).parent.parent.parent.parent / "pyproject.toml"
        assert pyproject_path.exists(), f"pyproject.toml not found at {pyproject_path}"

        with open(pyproject_path) as f:
            content = f.read()

        assert "[tool.setuptools.package-data]" in content, "Missing package-data configuration section"
        assert "data/**/*.yml" in content or "data/**/*.yaml" in content, (
            "Data files not included in package-data configuration"
        )

    def test_data_can_be_imported(self) -> None:
        """Verify data package can be imported."""
        import fabulae.data  # noqa: F401
