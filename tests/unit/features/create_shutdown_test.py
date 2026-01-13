"""Tests for graceful shutdown handling."""

from __future__ import annotations

import signal
from pathlib import Path

import pytest
import yaml

from fabulae.features.create.shutdown import ShutdownHandler, graceful_shutdown
from fabulae.features.create.state import GenerationState
from fabulae.models import Beat, Character, Fragment, Scene, Stanza, WorldFact


class TestGenerationState:
    """Tests for GenerationState dataclass."""

    def test_init_defaults(self) -> None:
        """Test GenerationState initializes with correct defaults."""
        state = GenerationState()
        assert state.idea == ""
        assert state.format_name == ""
        assert state.premise is None
        assert state.style is None
        assert state.characters == []
        assert state.locations == []
        assert state.scenes == []
        assert state.current_stage == "initializing"

    def test_init_with_values(self) -> None:
        """Test GenerationState initializes with provided values."""
        state = GenerationState(
            idea="test idea",
            format_name="novel",
            current_stage="generating_characters",
        )
        assert state.idea == "test idea"
        assert state.format_name == "novel"
        assert state.current_stage == "generating_characters"

    def test_write_partial_creates_directory(self, tmp_path: Path) -> None:
        """Test write_partial creates partial output directory."""
        state = GenerationState(idea="test idea", format_name="novel")
        partial_dir = state.write_partial(tmp_path)

        assert partial_dir.exists()
        assert partial_dir == tmp_path / ".fabulae-create" / "partial"

    def test_write_partial_writes_state_yml(self, tmp_path: Path) -> None:
        """Test write_partial writes state.yml with progress."""
        state = GenerationState(
            idea="test idea",
            format_name="novel",
            premise="A test premise",
            current_stage="generating_characters",
        )
        partial_dir = state.write_partial(tmp_path)

        state_file = partial_dir / "state.yml"
        assert state_file.exists()

        data = yaml.safe_load(state_file.read_text())
        assert data["idea"] == "test idea"
        assert data["format"] == "novel"
        assert data["current_stage"] == "generating_characters"
        assert data["progress"]["premise"] is True
        assert data["progress"]["characters"] == 0

    def test_write_partial_writes_premise(self, tmp_path: Path) -> None:
        """Test write_partial writes premise.yml when premise exists."""
        state = GenerationState(
            idea="test idea",
            format_name="novel",
            premise="A heroic journey begins",
        )
        partial_dir = state.write_partial(tmp_path)

        premise_file = partial_dir / "premise.yml"
        assert premise_file.exists()

        data = yaml.safe_load(premise_file.read_text())
        assert data["premise"] == "A heroic journey begins"

    def test_write_partial_writes_characters(self, tmp_path: Path) -> None:
        """Test write_partial writes characters.yml when characters exist."""
        character = Character(
            id="char-01",
            name="Alice",
            role="protagonist",
        )
        state = GenerationState(
            idea="test idea",
            format_name="novel",
            characters=[character],
        )
        partial_dir = state.write_partial(tmp_path)

        chars_file = partial_dir / "characters.yml"
        assert chars_file.exists()

        data = yaml.safe_load(chars_file.read_text())
        assert len(data) == 1
        assert data[0]["id"] == "char-01"
        assert data[0]["name"] == "Alice"

    def test_write_partial_writes_locations(self, tmp_path: Path) -> None:
        """Test write_partial writes locations.yml when locations exist."""
        location = WorldFact(
            id="loc-01",
            type="location",
            name="Castle",
            facts=["Ancient stone walls"],
        )
        state = GenerationState(
            idea="test idea",
            format_name="novel",
            locations=[location],
        )
        partial_dir = state.write_partial(tmp_path)

        locs_file = partial_dir / "locations.yml"
        assert locs_file.exists()

        data = yaml.safe_load(locs_file.read_text())
        assert len(data) == 1
        assert data[0]["id"] == "loc-01"
        assert data[0]["type"] == "location"

    def test_write_partial_writes_scenes(self, tmp_path: Path) -> None:
        """Test write_partial writes scenes.yml when scenes exist."""
        beat = Beat(id="beat-01", kind="action", summary="Hero arrives")
        scene = Scene(
            id="scene-01",
            summary="Opening scene",
            beats=[beat],
        )
        state = GenerationState(
            idea="test idea",
            format_name="novel",
            scenes=[scene],
        )
        partial_dir = state.write_partial(tmp_path)

        scenes_file = partial_dir / "scenes.yml"
        assert scenes_file.exists()

        data = yaml.safe_load(scenes_file.read_text())
        assert len(data) == 1
        assert data[0]["id"] == "scene-01"

    def test_write_partial_writes_fragments(self, tmp_path: Path) -> None:
        """Test write_partial writes fragments.yml when fragments exist."""
        fragment = Fragment(
            id="frag-01",
            content="A moment of silence.",
        )
        state = GenerationState(
            idea="test idea",
            format_name="micro-prose",
            fragments=[fragment],
        )
        partial_dir = state.write_partial(tmp_path)

        frags_file = partial_dir / "fragments.yml"
        assert frags_file.exists()

        data = yaml.safe_load(frags_file.read_text())
        assert len(data) == 1
        assert data[0]["id"] == "frag-01"

    def test_write_partial_writes_stanzas(self, tmp_path: Path) -> None:
        """Test write_partial writes stanzas.yml when stanzas exist."""
        stanza = Stanza(
            id="stanza-01",
            lines=["The moon rises high", "Above the silent trees"],
        )
        state = GenerationState(
            idea="test idea",
            format_name="poem",
            stanzas=[stanza],
        )
        partial_dir = state.write_partial(tmp_path)

        stanzas_file = partial_dir / "stanzas.yml"
        assert stanzas_file.exists()

        data = yaml.safe_load(stanzas_file.read_text())
        assert len(data) == 1
        assert data[0]["id"] == "stanza-01"


class TestShutdownHandler:
    """Tests for ShutdownHandler class."""

    def test_init(self, tmp_path: Path) -> None:
        """Test ShutdownHandler initialization."""
        state = GenerationState()
        handler = ShutdownHandler(state, tmp_path)

        assert handler.state is state
        assert handler.output_dir == tmp_path
        assert handler.progress is None

    def test_install_sets_handlers(self, tmp_path: Path) -> None:
        """Test install() sets signal handlers."""
        state = GenerationState()
        handler = ShutdownHandler(state, tmp_path)

        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigterm = signal.getsignal(signal.SIGTERM)

        try:
            handler.install()
            assert signal.getsignal(signal.SIGINT) == handler._handle_signal
            assert signal.getsignal(signal.SIGTERM) == handler._handle_signal
        finally:
            handler.uninstall()

        # Verify original handlers are restored
        assert signal.getsignal(signal.SIGINT) == original_sigint
        assert signal.getsignal(signal.SIGTERM) == original_sigterm

    def test_uninstall_restores_handlers(self, tmp_path: Path) -> None:
        """Test uninstall() restores original signal handlers."""
        state = GenerationState()
        handler = ShutdownHandler(state, tmp_path)

        original_sigint = signal.getsignal(signal.SIGINT)

        handler.install()
        handler.uninstall()

        assert signal.getsignal(signal.SIGINT) == original_sigint


class TestGracefulShutdownContext:
    """Tests for graceful_shutdown context manager."""

    def test_context_manager_installs_and_uninstalls(self, tmp_path: Path) -> None:
        """Test context manager properly installs and uninstalls handlers."""
        state = GenerationState()
        original_sigint = signal.getsignal(signal.SIGINT)

        with graceful_shutdown(state, tmp_path):
            # Handler should be installed
            assert signal.getsignal(signal.SIGINT) != original_sigint

        # Handler should be restored
        assert signal.getsignal(signal.SIGINT) == original_sigint

    def test_context_manager_uninstalls_on_exception(self, tmp_path: Path) -> None:
        """Test context manager restores handlers even on exception."""
        state = GenerationState()
        original_sigint = signal.getsignal(signal.SIGINT)

        with pytest.raises(ValueError), graceful_shutdown(state, tmp_path):
            raise ValueError("Test error")

        # Handler should still be restored
        assert signal.getsignal(signal.SIGINT) == original_sigint


class TestGenerationStateProgress:
    """Tests for tracking generation progress in state."""

    def test_progress_summary_counts_entities(self, tmp_path: Path) -> None:
        """Test progress counts all entity types correctly."""
        state = GenerationState(
            idea="test",
            format_name="novel",
            characters=[Character(id="c1", name="Alice")],
            locations=[WorldFact(id="l1", type="location", name="Castle", facts=[])],
            world_facts=[WorldFact(id="w1", type="rule", name="Magic", facts=[])],
            scenes=[Scene(id="s1", summary="Scene 1", beats=[])],
        )
        partial_dir = state.write_partial(tmp_path)

        state_file = partial_dir / "state.yml"
        data = yaml.safe_load(state_file.read_text())

        assert data["progress"]["characters"] == 1
        assert data["progress"]["locations"] == 1
        assert data["progress"]["world_facts"] == 1
        assert data["progress"]["scenes"] == 1
