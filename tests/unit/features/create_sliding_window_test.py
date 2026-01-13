"""Tests for sliding window context limiting in micro-prose and poem pipelines."""

from __future__ import annotations

from fabulae.features.create.context import (
    MicroProseState,
    PoemState,
    build_fragment_context,
    build_stanza_context,
)
from fabulae.features.create.graph import (
    FragmentSlot,
    MicroProseGraph,
    PoemGraph,
    StanzaSlot,
)
from fabulae.features.create.schemas import CreateOptions, StyleOutput
from fabulae.models import Fragment, Stanza


def _make_style_output() -> StyleOutput:
    """Create a minimal StyleOutput for testing."""
    return StyleOutput(
        language="en",
        pov="third",
        tense="past",
    )


class TestMicroProseSlidingWindow:
    """Test sliding window context for micro-prose fragments."""

    def test_no_sliding_window_full_context(self) -> None:
        """Test that without sliding window, all previous fragments are included."""
        # Create a graph with 5 fragments
        graph = MicroProseGraph(
            fragment_slots=[FragmentSlot(id=f"fragment-{i + 1:02d}", position=i) for i in range(5)],
            seed=42,
        )

        # Create state with 3 existing fragments
        state = MicroProseState()
        for i in range(3):
            state.fragments.append(Fragment(id=f"fragment-{i + 1:02d}", content=f"Content {i + 1}"))

        # Build context for fragment 4 (index 3) without sliding window
        options = CreateOptions(sliding_window_scenes=None)
        context = build_fragment_context(
            fragment_slot=graph.fragment_slots[3],
            graph=graph,
            state=state,
            premise="Test premise",
            style=_make_style_output(),
            options=options,
        )

        # All 3 previous fragments should be included
        assert len(context.previous_fragment_summaries) == 3

    def test_sliding_window_limits_context(self) -> None:
        """Test that sliding window limits the number of previous fragments."""
        # Create a graph with 10 fragments
        graph = MicroProseGraph(
            fragment_slots=[FragmentSlot(id=f"fragment-{i + 1:02d}", position=i) for i in range(10)],
            seed=42,
        )

        # Create state with 7 existing fragments
        state = MicroProseState()
        for i in range(7):
            state.fragments.append(Fragment(id=f"fragment-{i + 1:02d}", content=f"Content {i + 1}"))

        # Build context for fragment 8 (index 7) with sliding window of 3
        options = CreateOptions(sliding_window_scenes=3)
        context = build_fragment_context(
            fragment_slot=graph.fragment_slots[7],
            graph=graph,
            state=state,
            premise="Test premise",
            style=_make_style_output(),
            options=options,
        )

        # Only last 3 fragments should be included
        assert len(context.previous_fragment_summaries) == 3

    def test_sliding_window_at_start_no_context(self) -> None:
        """Test that first fragment has no previous context."""
        graph = MicroProseGraph(
            fragment_slots=[FragmentSlot(id=f"fragment-{i + 1:02d}", position=i) for i in range(5)],
            seed=42,
        )

        state = MicroProseState()

        options = CreateOptions(sliding_window_scenes=3)
        context = build_fragment_context(
            fragment_slot=graph.fragment_slots[0],
            graph=graph,
            state=state,
            premise="Test premise",
            style=_make_style_output(),
            options=options,
        )

        assert len(context.previous_fragment_summaries) == 0

    def test_fragment_summary_truncation(self) -> None:
        """Test that long fragment content is truncated in summaries."""
        state = MicroProseState()

        # Add a fragment with very long content
        long_content = "A" * 200
        state.fragments.append(Fragment(id="fragment-01", content=long_content))

        summary = state.get_fragment_summary("fragment-01")
        assert summary is not None
        assert len(summary) <= 103  # 100 chars + "..."
        assert summary.endswith("...")


class TestPoemSlidingWindow:
    """Test sliding window context for poem stanzas."""

    def test_no_sliding_window_full_context(self) -> None:
        """Test that without sliding window, all previous stanzas are included."""
        # Create a graph with 5 stanzas
        graph = PoemGraph(
            stanza_slots=[StanzaSlot(id=f"stanza-{i + 1:02d}", position=i, line_count=4) for i in range(5)],
            seed=42,
        )

        # Create state with 3 existing stanzas
        state = PoemState()
        for i in range(3):
            state.stanzas.append(
                Stanza(id=f"stanza-{i + 1:02d}", lines=[f"Line {j + 1} of stanza {i + 1}" for j in range(4)])
            )

        # Build context for stanza 4 (index 3) without sliding window
        options = CreateOptions(sliding_window_scenes=None)
        context = build_stanza_context(
            stanza_slot=graph.stanza_slots[3],
            graph=graph,
            state=state,
            premise="Test premise",
            style=_make_style_output(),
            options=options,
        )

        # All 3 previous stanzas should be included
        assert len(context.previous_stanza_texts) == 3

    def test_sliding_window_limits_context(self) -> None:
        """Test that sliding window limits the number of previous stanzas."""
        # Create a graph with 10 stanzas
        graph = PoemGraph(
            stanza_slots=[StanzaSlot(id=f"stanza-{i + 1:02d}", position=i, line_count=4) for i in range(10)],
            seed=42,
        )

        # Create state with 7 existing stanzas
        state = PoemState()
        for i in range(7):
            state.stanzas.append(
                Stanza(id=f"stanza-{i + 1:02d}", lines=[f"Line {j + 1} of stanza {i + 1}" for j in range(4)])
            )

        # Build context for stanza 8 (index 7) with sliding window of 3
        options = CreateOptions(sliding_window_scenes=3)
        context = build_stanza_context(
            stanza_slot=graph.stanza_slots[7],
            graph=graph,
            state=state,
            premise="Test premise",
            style=_make_style_output(),
            options=options,
        )

        # Only last 3 stanzas should be included
        assert len(context.previous_stanza_texts) == 3

    def test_sliding_window_at_start_no_context(self) -> None:
        """Test that first stanza has no previous context."""
        graph = PoemGraph(
            stanza_slots=[StanzaSlot(id=f"stanza-{i + 1:02d}", position=i, line_count=4) for i in range(5)],
            seed=42,
        )

        state = PoemState()

        options = CreateOptions(sliding_window_scenes=3)
        context = build_stanza_context(
            stanza_slot=graph.stanza_slots[0],
            graph=graph,
            state=state,
            premise="Test premise",
            style=_make_style_output(),
            options=options,
        )

        assert len(context.previous_stanza_texts) == 0

    def test_stanza_text_joining(self) -> None:
        """Test that stanza text is joined correctly."""
        state = PoemState()

        state.stanzas.append(Stanza(id="stanza-01", lines=["Line 1", "Line 2", "Line 3"]))

        text = state.get_stanza_text("stanza-01")
        assert text == "Line 1\nLine 2\nLine 3"


class TestContextBuilderIntegration:
    """Integration tests for context builders."""

    def test_fragment_context_position_info(self) -> None:
        """Test that fragment context includes correct position info."""
        graph = MicroProseGraph(
            fragment_slots=[FragmentSlot(id=f"fragment-{i + 1:02d}", position=i) for i in range(5)],
            seed=42,
        )

        state = MicroProseState()
        options = CreateOptions()

        context = build_fragment_context(
            fragment_slot=graph.fragment_slots[2],
            graph=graph,
            state=state,
            premise="Test premise",
            style=_make_style_output(),
            options=options,
        )

        assert context.fragment_id == "fragment-03"
        assert context.position == 2
        assert context.total_fragments == 5

    def test_stanza_context_position_info(self) -> None:
        """Test that stanza context includes correct position info."""
        graph = PoemGraph(
            stanza_slots=[StanzaSlot(id=f"stanza-{i + 1:02d}", position=i, line_count=4) for i in range(5)],
            poem_form="sonnet",
            seed=42,
        )

        state = PoemState()
        options = CreateOptions()

        context = build_stanza_context(
            stanza_slot=graph.stanza_slots[2],
            graph=graph,
            state=state,
            premise="Test premise",
            style=_make_style_output(),
            options=options,
        )

        assert context.stanza_id == "stanza-03"
        assert context.position == 2
        assert context.total_stanzas == 5
        assert context.target_line_count == 4
        assert context.poem_form == "sonnet"
