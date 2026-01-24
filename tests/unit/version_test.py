"""Tests for package version formatting."""

from _pytest.monkeypatch import MonkeyPatch

import fabulae


def test_resolve_version_deduplicates_tag_prefix(monkeypatch: MonkeyPatch) -> None:
    """Ensure git describe tags do not duplicate the base version."""
    monkeypatch.setattr(fabulae, "pkg_version", lambda _: "0.1.0")
    monkeypatch.setattr(fabulae, "_git_description", lambda: "v0.1.0-13-gcfeefb2-dirty")

    assert fabulae._resolve_version() == "0.1.0-13-gcfeefb2-dirty"
