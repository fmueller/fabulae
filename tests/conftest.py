"""Shared pytest fixtures for fabulae tests."""

from __future__ import annotations

import builtins
import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import IO, Any, cast

import pytest
import yaml
from typer.testing import CliRunner

from fabulae.llm import FAKE_LLM_ENV


def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text.

    Use this when checking CLI output that may contain Rich formatting.
    """
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


runner = CliRunner()


@pytest.fixture
def prose_project(tmp_path: Path) -> Path:
    """Create a minimal prose (novel) test project."""
    (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
    (tmp_path / "plot.yml").write_text(
        yaml.dump(
            {
                "premise": "A test story.",
                "format": "novel",
                "chapters": [
                    {"id": "chapter-01", "title": "Beginning", "scene_ids": ["scene-01"]},
                    {"id": "chapter-02", "title": "Middle", "scene_ids": []},
                ],
                "scenes": [
                    {"id": "scene-01", "summary": "First scene", "characters": ["char-01"]},
                ],
            }
        )
    )
    (tmp_path / "characters.yml").write_text(
        yaml.dump(
            {
                "characters": [
                    {"id": "char-01", "name": "Alice", "role": "protagonist"},
                    {"id": "char-02", "name": "Bob"},
                ]
            }
        )
    )
    (tmp_path / "world.yml").write_text(
        yaml.dump(
            {
                "facts": [
                    {"id": "loc-01", "type": "location", "name": "Tavern"},
                    {"id": "artifact-01", "type": "object", "name": "Magic Sword"},
                    {"id": "rule-01", "type": "rule", "name": "No magic after midnight"},
                ]
            }
        )
    )
    return tmp_path


@pytest.fixture
def micro_prose_project(tmp_path: Path) -> Path:
    """Create a minimal micro-prose test project."""
    (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
    (tmp_path / "plot.yml").write_text(
        yaml.dump(
            {
                "premise": "A flash fiction test.",
                "format": "micro-prose",
                "fragments": [
                    {"id": "fragment-01", "content": "First fragment content."},
                    {"id": "fragment-02", "content": "Second fragment content."},
                ],
            }
        )
    )
    return tmp_path


@pytest.fixture
def poem_project(tmp_path: Path) -> Path:
    """Create a minimal poem test project."""
    (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
    (tmp_path / "plot.yml").write_text(
        yaml.dump(
            {
                "premise": "A poem about nature.",
                "format": "poem",
                "stanzas": [
                    {"id": "stanza-01", "lines": ["First line of verse", "Second line of verse"]},
                    {"id": "stanza-02", "lines": ["Another verse begins", "And here it ends"]},
                ],
            }
        )
    )
    return tmp_path


@pytest.fixture
def empty_prose_project(tmp_path: Path) -> Path:
    """Create a prose project with no characters or world facts."""
    (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
    (tmp_path / "plot.yml").write_text(
        yaml.dump(
            {
                "premise": "A test story.",
                "format": "novel",
                "scenes": [{"id": "scene-01"}],
            }
        )
    )
    (tmp_path / "characters.yml").write_text(yaml.dump({"characters": []}))
    return tmp_path


@pytest.fixture(autouse=True)
def _disable_llm_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(FAKE_LLM_ENV, "1")


@pytest.fixture(autouse=True)
def _guard_tmp_writes(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> None:
    base_tmp = tmp_path_factory.getbasetemp().resolve()

    def is_tmp_path(path: Path) -> bool:
        resolved = path.resolve()
        try:
            return resolved.is_relative_to(base_tmp)
        except AttributeError:
            return str(resolved).startswith(str(base_tmp))

    def guard_path(path: Path) -> None:
        if not is_tmp_path(path):
            raise RuntimeError(f"Tests may only write under {base_tmp}; got {path}")

    original_open = Path.open
    original_write_text = Path.write_text
    original_write_bytes = Path.write_bytes
    original_mkdir = Path.mkdir
    original_unlink = Path.unlink
    original_builtin_open = builtins.open

    def guarded_open(self: Path, *args: object, **kwargs: object) -> IO[Any]:
        mode = kwargs.get("mode")
        if mode is None and args:
            mode = args[0]
        mode = mode or "r"
        if any(flag in str(mode) for flag in ("w", "a", "x", "+")):
            guard_path(self)
        return cast(Callable[..., IO[Any]], original_open)(self, *args, **kwargs)

    def guarded_write_text(self: Path, *args: object, **kwargs: object) -> int:
        guard_path(self)
        return cast(Callable[..., int], original_write_text)(self, *args, **kwargs)

    def guarded_write_bytes(self: Path, *args: object, **kwargs: object) -> int:
        guard_path(self)
        return cast(Callable[..., int], original_write_bytes)(self, *args, **kwargs)

    def guarded_mkdir(self: Path, *args: object, **kwargs: object) -> None:
        guard_path(self)
        cast(Callable[..., None], original_mkdir)(self, *args, **kwargs)

    def guarded_unlink(self: Path, *args: object, **kwargs: object) -> None:
        guard_path(self)
        cast(Callable[..., None], original_unlink)(self, *args, **kwargs)

    def guarded_builtin_open(file: object, *args: object, **kwargs: object) -> IO[Any]:
        mode = kwargs.get("mode")
        if mode is None and args:
            mode = args[0]
        mode = mode or "r"
        if any(flag in str(mode) for flag in ("w", "a", "x", "+")):
            if isinstance(file, (str, Path)):
                guard_path(Path(file))
            elif isinstance(file, os.PathLike):
                guard_path(Path(cast(os.PathLike[str], file)))
        return cast(Callable[..., IO[Any]], original_builtin_open)(file, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    monkeypatch.setattr(Path, "write_text", guarded_write_text)
    monkeypatch.setattr(Path, "write_bytes", guarded_write_bytes)
    monkeypatch.setattr(Path, "mkdir", guarded_mkdir)
    monkeypatch.setattr(Path, "unlink", guarded_unlink)
    monkeypatch.setattr(builtins, "open", guarded_builtin_open)
