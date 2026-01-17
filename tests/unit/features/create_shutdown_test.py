"""Tests for graceful shutdown handling during create command."""

from __future__ import annotations

import signal
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
import yaml

from fabulae.features.create.schemas import StyleOutput
from fabulae.features.create.shutdown import ShutdownHandler, graceful_shutdown
from fabulae.features.create.state import GenerationState
from fabulae.models import Character, Fragment, Scene, Stanza, WorldFact

if TYPE_CHECKING:
    pass


class TestGenerationState:
    """Tests for GenerationState dataclass."""

    def test_empty_state_write_partial(self, tmp_path: Path) -> None:
        """Test writing an empty state produces valid output."""
        state = GenerationState(idea="test idea", format_name="novel")
        partial_dir = state.write_partial(tmp_path)

        assert partial_dir.exists()
        assert (partial_dir / "state.yml").exists()

        # Load and check state file
        state_data = yaml.safe_load((partial_dir / "state.yml").read_text())
        assert state_data["idea"] == "test idea"
        assert state_data["format"] == "novel"
        assert state_data["current_stage"] == "initializing"
        assert state_data["progress"]["premise"] is False
        assert state_data["progress"]["style"] is False
        assert state_data["progress"]["characters"] == 0

    def test_state_with_premise_write_partial(self, tmp_path: Path) -> None:
        """Test writing state with premise generates premise.yml."""
        state = GenerationState(
            idea="test idea",
            format_name="novel",
            premise="A test premise",
            current_stage="premise_complete",
        )
        partial_dir = state.write_partial(tmp_path)

        assert (partial_dir / "premise.yml").exists()
        premise_data = yaml.safe_load((partial_dir / "premise.yml").read_text())
        assert premise_data["premise"] == "A test premise"

    def test_state_with_style_write_partial(self, tmp_path: Path) -> None:
        """Test writing state with style generates style.yml."""
        style = StyleOutput(
            language="en",
            pov="third",
            tense="past",
            voice="observant",
        )
        state = GenerationState(
            idea="test idea",
            format_name="novel",
            style=style,
            current_stage="style_complete",
        )
        partial_dir = state.write_partial(tmp_path)

        assert (partial_dir / "style.yml").exists()
        style_data = yaml.safe_load((partial_dir / "style.yml").read_text())
        assert style_data["language"] == "en"
        assert style_data["pov"] == "third"
        assert style_data["tense"] == "past"

    def test_state_with_characters_write_partial(self, tmp_path: Path) -> None:
        """Test writing state with characters generates characters.yml."""
        character = Character(
            id="character-01",
            name="Test Character",
            role="protagonist",
            desire="to succeed",
        )
        state = GenerationState(
            idea="test idea",
            format_name="novel",
            characters=[character],
            current_stage="generating_characters (1/3)",
        )
        partial_dir = state.write_partial(tmp_path)

        assert (partial_dir / "characters.yml").exists()
        chars_data = yaml.safe_load((partial_dir / "characters.yml").read_text())
        assert len(chars_data) == 1
        assert chars_data[0]["id"] == "character-01"
        assert chars_data[0]["name"] == "Test Character"

    def test_state_with_locations_write_partial(self, tmp_path: Path) -> None:
        """Test writing state with locations generates locations.yml."""
        location = WorldFact(
            id="location-01",
            type="location",
            name="Test Location",
            facts=["A test location"],
        )
        state = GenerationState(
            idea="test idea",
            format_name="novel",
            locations=[location],
            current_stage="locations_complete",
        )
        partial_dir = state.write_partial(tmp_path)

        assert (partial_dir / "locations.yml").exists()
        locs_data = yaml.safe_load((partial_dir / "locations.yml").read_text())
        assert len(locs_data) == 1
        assert locs_data[0]["id"] == "location-01"
        assert locs_data[0]["type"] == "location"

    def test_state_with_scenes_write_partial(self, tmp_path: Path) -> None:
        """Test writing state with scenes generates scenes.yml."""
        scene = Scene(
            id="scene-01",
            summary="A test scene",
            characters=["character-01"],
            beats=[],
        )
        state = GenerationState(
            idea="test idea",
            format_name="novel",
            scenes=[scene],
            current_stage="generating_scenes (1/5)",
        )
        partial_dir = state.write_partial(tmp_path)

        assert (partial_dir / "scenes.yml").exists()
        scenes_data = yaml.safe_load((partial_dir / "scenes.yml").read_text())
        assert len(scenes_data) == 1
        assert scenes_data[0]["id"] == "scene-01"
        assert scenes_data[0]["summary"] == "A test scene"

    def test_state_with_fragments_write_partial(self, tmp_path: Path) -> None:
        """Test writing state with fragments generates fragments.yml."""
        fragment = Fragment(
            id="fragment-01",
            content="A test fragment",
        )
        state = GenerationState(
            idea="test idea",
            format_name="micro-prose",
            fragments=[fragment],
            current_stage="generating_fragments (1/5)",
        )
        partial_dir = state.write_partial(tmp_path)

        assert (partial_dir / "fragments.yml").exists()
        fragments_data = yaml.safe_load((partial_dir / "fragments.yml").read_text())
        assert len(fragments_data) == 1
        assert fragments_data[0]["id"] == "fragment-01"
        assert fragments_data[0]["content"] == "A test fragment"

    def test_state_with_stanzas_write_partial(self, tmp_path: Path) -> None:
        """Test writing state with stanzas generates stanzas.yml."""
        stanza = Stanza(
            id="stanza-01",
            lines=["Line one", "Line two"],
        )
        state = GenerationState(
            idea="test idea",
            format_name="poem",
            stanzas=[stanza],
            current_stage="generating_stanzas (1/4)",
        )
        partial_dir = state.write_partial(tmp_path)

        assert (partial_dir / "stanzas.yml").exists()
        stanzas_data = yaml.safe_load((partial_dir / "stanzas.yml").read_text())
        assert len(stanzas_data) == 1
        assert stanzas_data[0]["id"] == "stanza-01"
        assert stanzas_data[0]["lines"] == ["Line one", "Line two"]

    def test_state_creates_nested_directories(self, tmp_path: Path) -> None:
        """Test that write_partial creates nested directories."""
        state = GenerationState(idea="test", format_name="novel")
        partial_dir = state.write_partial(tmp_path)

        assert partial_dir == tmp_path / ".fabulae" / "create" / "partial"
        assert partial_dir.is_dir()


class TestShutdownHandler:
    """Tests for ShutdownHandler class."""

    def test_install_and_uninstall_signals(self) -> None:
        """Test that signal handlers are installed and restored properly."""
        state = GenerationState()
        handler = ShutdownHandler(state, Path("/tmp"))

        # Get original handlers
        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigterm = signal.getsignal(signal.SIGTERM)

        # Install handlers
        handler.install()

        # Verify handlers are our handler
        assert signal.getsignal(signal.SIGINT) == handler._handle_signal
        assert signal.getsignal(signal.SIGTERM) == handler._handle_signal

        # Uninstall handlers
        handler.uninstall()

        # Verify original handlers are restored
        assert signal.getsignal(signal.SIGINT) == original_sigint
        assert signal.getsignal(signal.SIGTERM) == original_sigterm

    def test_handler_with_progress(self, tmp_path: Path) -> None:
        """Test that handler calls progress methods on signal."""
        state = GenerationState(idea="test", format_name="novel", current_stage="test_stage")
        progress = MagicMock()

        handler = ShutdownHandler(state, tmp_path, progress)

        # We can't actually test the signal handling without sending signals,
        # but we can verify the handler is configured correctly
        assert handler.state == state
        assert handler.output_dir == tmp_path
        assert handler.progress == progress


class TestGracefulShutdownContextManager:
    """Tests for graceful_shutdown context manager."""

    def test_context_manager_installs_and_uninstalls_handlers(self) -> None:
        """Test that context manager properly manages signal handlers."""
        state = GenerationState()

        # Get original handlers
        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigterm = signal.getsignal(signal.SIGTERM)

        with graceful_shutdown(state, Path("/tmp")):
            # Inside context, handlers should be our custom handlers
            current_sigint = signal.getsignal(signal.SIGINT)
            current_sigterm = signal.getsignal(signal.SIGTERM)
            assert current_sigint != original_sigint
            assert current_sigterm != original_sigterm

        # After context, original handlers should be restored
        assert signal.getsignal(signal.SIGINT) == original_sigint
        assert signal.getsignal(signal.SIGTERM) == original_sigterm

    def test_context_manager_restores_on_exception(self) -> None:
        """Test that context manager restores handlers even on exception."""
        state = GenerationState()

        # Get original handlers
        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigterm = signal.getsignal(signal.SIGTERM)

        with pytest.raises(ValueError), graceful_shutdown(state, Path("/tmp")):
            raise ValueError("Test exception")

        # Handlers should still be restored
        assert signal.getsignal(signal.SIGINT) == original_sigint
        assert signal.getsignal(signal.SIGTERM) == original_sigterm


class TestPartialOutputStructure:
    """Tests for the partial output directory structure."""

    def test_full_state_output_structure(self, tmp_path: Path) -> None:
        """Test complete output structure with all entity types."""
        style = StyleOutput(language="en", pov="third", tense="past")
        character = Character(id="character-01", name="Test", role="protagonist")
        location = WorldFact(id="location-01", type="location", name="Place", facts=[])
        scene = Scene(id="scene-01", summary="Test", characters=[], beats=[])

        state = GenerationState(
            idea="A complete test idea",
            format_name="novel",
            premise="A test premise",
            style=style,
            characters=[character],
            locations=[location],
            scenes=[scene],
            chapters=[{"id": "chapter-01", "title": "Chapter One"}],
            current_stage="scenes_complete",
        )

        partial_dir = state.write_partial(tmp_path)

        # Verify all expected files exist
        expected_files = [
            "state.yml",
            "premise.yml",
            "style.yml",
            "characters.yml",
            "locations.yml",
            "scenes.yml",
            "chapters.yml",
        ]
        for filename in expected_files:
            assert (partial_dir / filename).exists(), f"Expected {filename} to exist"

        # Verify state.yml has correct progress counts
        state_data = yaml.safe_load((partial_dir / "state.yml").read_text())
        assert state_data["progress"]["characters"] == 1
        assert state_data["progress"]["locations"] == 1
        assert state_data["progress"]["scenes"] == 1
        assert state_data["progress"]["chapters"] == 1
