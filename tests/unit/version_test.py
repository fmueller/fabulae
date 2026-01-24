"""Tests for version resolution logic."""

from unittest.mock import patch

import fabulae


def test_git_description_does_not_duplicate_version() -> None:
    """When git describe returns a tag-based string, version should not be duplicated.

    Bug: If base version is "0.1.0" and git describe returns "v0.1.0-13-gcfeefb2-dirty",
    the result was "0.1.0+v0.1.0-13-gcfeefb2-dirty" (duplicated).
    Expected: "v0.1.0-13-gcfeefb2-dirty" (the git describe output directly).
    """
    with (
        patch.object(fabulae, "_version_from_pyproject", return_value="0.1.0"),
        patch.object(fabulae, "_git_description", return_value="v0.1.0-13-gcfeefb2-dirty"),
    ):
        result = fabulae._resolve_version()

    # The version string should NOT contain duplicates
    assert result == "v0.1.0-13-gcfeefb2-dirty"
    assert "0.1.0-v0.1.0" not in result
    assert "0.1.0+v0.1.0" not in result


def test_git_description_dirty_without_commits_after_tag() -> None:
    """When at a tag but dirty, git describe returns tag-dirty format."""
    with (
        patch.object(fabulae, "_version_from_pyproject", return_value="0.1.0"),
        patch.object(fabulae, "_git_description", return_value="v0.1.0-dirty"),
    ):
        result = fabulae._resolve_version()

    assert result == "v0.1.0-dirty"


def test_exact_tag_match_uses_base_version() -> None:
    """When at exact tag, _git_description returns None and base version is used."""
    with (
        patch.object(fabulae, "_version_from_pyproject", return_value="0.1.0"),
        patch.object(fabulae, "_git_description", return_value=None),
    ):
        result = fabulae._resolve_version()

    assert result == "0.1.0"


def test_no_git_uses_base_version() -> None:
    """When not in a git repo, use base version from package metadata."""
    with (
        patch.object(fabulae, "_version_from_pyproject", return_value="0.1.0"),
        patch.object(fabulae, "_git_description", return_value=None),
    ):
        result = fabulae._resolve_version()

    assert result == "0.1.0"
