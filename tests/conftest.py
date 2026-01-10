"""Shared pytest fixtures for fabulae tests."""

from __future__ import annotations

import builtins
import os
from collections.abc import Callable
from pathlib import Path
from typing import IO, Any, cast

import pytest

from fabulae.llm import FAKE_LLM_ENV


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
