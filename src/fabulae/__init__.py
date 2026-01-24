"""Fabulae package."""

import subprocess
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib


def _version_from_pyproject() -> str:
    """Read version from pyproject.toml as fallback."""
    pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
    if pyproject.exists():
        data = tomllib.loads(pyproject.read_text())
        project = data.get("project", {})
        if isinstance(project, dict):
            version_value = project.get("version")
            if isinstance(version_value, str):
                return version_value
    return "0.0.0"


def _git_description() -> str | None:
    """Get git description suffix for development versions."""
    git_dir = Path(__file__).parent.parent.parent / ".git"
    if not git_dir.exists():
        return None
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--exact-match"],
            capture_output=True,
            text=True,
            cwd=git_dir.parent,
        )
        if result.returncode == 0:
            return None
        result = subprocess.run(
            ["git", "describe", "--tags", "--dirty", "--always"],
            capture_output=True,
            text=True,
            cwd=git_dir.parent,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    return None


def _resolve_version() -> str:
    """Resolve the package version using multiple strategies."""
    # If we have a git description, use it directly (it already includes the version tag)
    git_desc = _git_description()
    if git_desc:
        return git_desc

    # Otherwise fall back to package metadata or pyproject.toml
    try:
        return pkg_version("fabulae")
    except PackageNotFoundError:
        return _version_from_pyproject()


__version__ = _resolve_version()
__all__ = ["__version__"]
