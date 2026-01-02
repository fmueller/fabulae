"""Fabulae package."""

from importlib.metadata import PackageNotFoundError, version as pkg_version
from pathlib import Path
import subprocess
import tomllib


def _version_from_pyproject() -> str:
    """Read version from pyproject.toml as fallback."""
    pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
    if pyproject.exists():
        data = tomllib.loads(pyproject.read_text())
        return data.get("project", {}).get("version", "0.0.0")
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
    try:
        base = pkg_version("fabulae")
    except PackageNotFoundError:
        base = _version_from_pyproject()

    git_suffix = _git_description()
    if git_suffix:
        return f"{base}+{git_suffix}"
    return base


__version__ = _resolve_version()
__all__ = ["__version__"]
