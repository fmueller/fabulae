"""Unit tests for scene_builder guards integration."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from fabulae.features.build.scene_builder import (
    build_enhanced_fragment,
    build_enhanced_scene,
    build_enhanced_stanza,
    build_fragment,
    build_poem_from_lines,
    build_scene,
    build_stanza,
    generate_continuity_summary,
)
from fabulae.features.build.schemas import (
    BeatProseOutput,
    EnhancedFragmentProseOutput,
    EnhancedSceneProseOutput,
    EnhancedStanzaProseOutput,
    FragmentProseOutput,
    PoemProseOutput,
    SceneHook,
    SceneProseOutput,
    StanzaProseOutput,
)
from fabulae.llm import LLMConfig
from fabulae.llm.guards import GuardsResult
from fabulae.llm.json_guard import JsonGuardResult
from fabulae.llm.language_guard import LanguageGuardResult
from fabulae.models import Beat, Fragment, Plot, Project, ProjectConfig, Scene, Stanza


@pytest.fixture
def llm_config() -> LLMConfig:
    """Minimal LLM config for tests."""
    return LLMConfig(model="test-model")


@pytest.fixture
def simple_project() -> Project:
    """Create a simple project for testing."""
    return Project(
        config=ProjectConfig(version="0.1.0"),
        plot=Plot(
            premise="A test story.",
            format="short-story",
            scenes=[
                Scene(
                    id="scene-01",
                    summary="Test scene",
                    beats=[Beat(id="beat-01", kind="opening")],
                )
            ],
        ),
    )


@pytest.fixture
def micro_prose_project() -> Project:
    """Create a micro-prose project for testing."""
    return Project(
        config=ProjectConfig(version="0.1.0"),
        plot=Plot(
            premise="Flash fiction.",
            format="micro-prose",
            fragments=[Fragment(id="frag-01", content="Test content.")],
        ),
    )


@pytest.fixture
def poem_project() -> Project:
    """Create a poem project for testing."""
    return Project(
        config=ProjectConfig(version="0.1.0"),
        plot=Plot(
            premise="Nature poem.",
            format="poem",
            poem_form="free verse",
            stanzas=[Stanza(id="stanza-01", lines=["Line seed"])],
            lines=["Line one", "Line two"],
        ),
    )


def _make_guards_result(
    passed: bool = True,
    language_skipped: bool = True,
    json_skipped: bool = True,
) -> GuardsResult:
    """Create a GuardsResult for testing."""
    return GuardsResult(
        language=LanguageGuardResult(
            expected="en",
            detected="en" if passed else "fr",
            confidence=0.95,
            passed=passed,
            skipped=language_skipped,
        ),
        json=JsonGuardResult(
            passed=passed,
            skipped=json_skipped,
            error_type=None,
            error_message=None,
            attempts=1,
        ),
    )


class TestBuildSceneGuardsIntegration:
    """Tests for build_scene using run_with_guards."""

    def test_build_scene_uses_run_with_guards(self, simple_project: Project, llm_config: LLMConfig) -> None:
        """build_scene should use run_with_guards instead of run_with_language_guard."""
        mock_output = SceneProseOutput(title="Test Title", content="Generated content.")
        mock_result = _make_guards_result()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            result = asyncio.run(
                build_scene(
                    scene=simple_project.plot.scenes[0],
                    project=simple_project,
                    prior_context="",
                    config=llm_config,
                )
            )

        assert result.content == "Generated content."
        mock_guards.assert_called_once()

    def test_build_scene_passes_expected_language(self, simple_project: Project, llm_config: LLMConfig) -> None:
        """build_scene passes expected_language to run_with_guards."""
        mock_output = SceneProseOutput(title="Test Title", content="German content.")
        mock_result = _make_guards_result()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            asyncio.run(
                build_scene(
                    scene=simple_project.plot.scenes[0],
                    project=simple_project,
                    prior_context="",
                    config=llm_config,
                    expected_language="de",
                )
            )

        call_kwargs = mock_guards.call_args[1]
        assert call_kwargs["expected_language"] == "de"

    def test_build_scene_passes_on_language_correction_callback(
        self, simple_project: Project, llm_config: LLMConfig
    ) -> None:
        """build_scene passes on_language_correction callback to run_with_guards."""
        mock_output = SceneProseOutput(title="Test Title", content="Content.")
        mock_result = _make_guards_result()
        callback = MagicMock()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            asyncio.run(
                build_scene(
                    scene=simple_project.plot.scenes[0],
                    project=simple_project,
                    prior_context="",
                    config=llm_config,
                    on_language_correction=callback,
                )
            )

        call_kwargs = mock_guards.call_args[1]
        assert call_kwargs["on_language_correction"] is callback

    def test_build_scene_passes_on_json_error_callback(self, simple_project: Project, llm_config: LLMConfig) -> None:
        """build_scene passes on_json_error callback to run_with_guards."""
        mock_output = SceneProseOutput(title="Test Title", content="Content.")
        mock_result = _make_guards_result()
        callback = MagicMock()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            asyncio.run(
                build_scene(
                    scene=simple_project.plot.scenes[0],
                    project=simple_project,
                    prior_context="",
                    config=llm_config,
                    on_json_error=callback,
                )
            )

        call_kwargs = mock_guards.call_args[1]
        assert call_kwargs["on_json_error"] is callback

    def test_build_scene_passes_extract_text(self, simple_project: Project, llm_config: LLMConfig) -> None:
        """build_scene passes correct extract_text function to run_with_guards."""
        mock_output = SceneProseOutput(title="Test Title", content="Test content here.")
        mock_result = _make_guards_result()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            asyncio.run(
                build_scene(
                    scene=simple_project.plot.scenes[0],
                    project=simple_project,
                    prior_context="",
                    config=llm_config,
                )
            )

        call_kwargs = mock_guards.call_args[1]
        extract_fn = call_kwargs["extract_text"]
        # Verify the extract function extracts content correctly
        assert extract_fn(mock_output) == "Test content here."


class TestBuildFragmentGuardsIntegration:
    """Tests for build_fragment using run_with_guards."""

    def test_build_fragment_uses_run_with_guards(self, micro_prose_project: Project, llm_config: LLMConfig) -> None:
        """build_fragment should use run_with_guards."""
        mock_output = FragmentProseOutput(content="Fragment content.")
        mock_result = _make_guards_result()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            result = asyncio.run(
                build_fragment(
                    fragment=micro_prose_project.plot.fragments[0],
                    project=micro_prose_project,
                    prior_fragments=[],
                    config=llm_config,
                )
            )

        assert result.content == "Fragment content."
        mock_guards.assert_called_once()

    def test_build_fragment_passes_on_json_error_callback(
        self, micro_prose_project: Project, llm_config: LLMConfig
    ) -> None:
        """build_fragment passes on_json_error callback to run_with_guards."""
        mock_output = FragmentProseOutput(content="Content.")
        mock_result = _make_guards_result()
        callback = MagicMock()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            asyncio.run(
                build_fragment(
                    fragment=micro_prose_project.plot.fragments[0],
                    project=micro_prose_project,
                    prior_fragments=[],
                    config=llm_config,
                    on_json_error=callback,
                )
            )

        call_kwargs = mock_guards.call_args[1]
        assert call_kwargs["on_json_error"] is callback


class TestBuildStanzaGuardsIntegration:
    """Tests for build_stanza using run_with_guards."""

    def test_build_stanza_uses_run_with_guards(self, poem_project: Project, llm_config: LLMConfig) -> None:
        """build_stanza should use run_with_guards."""
        mock_output = StanzaProseOutput(lines=["Line one", "Line two"])
        mock_result = _make_guards_result()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            result = asyncio.run(
                build_stanza(
                    stanza=poem_project.plot.stanzas[0],
                    project=poem_project,
                    prior_stanzas=[],
                    config=llm_config,
                )
            )

        assert result.lines == ["Line one", "Line two"]
        mock_guards.assert_called_once()

    def test_build_stanza_passes_on_json_error_callback(self, poem_project: Project, llm_config: LLMConfig) -> None:
        """build_stanza passes on_json_error callback to run_with_guards."""
        mock_output = StanzaProseOutput(lines=["Line"])
        mock_result = _make_guards_result()
        callback = MagicMock()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            asyncio.run(
                build_stanza(
                    stanza=poem_project.plot.stanzas[0],
                    project=poem_project,
                    prior_stanzas=[],
                    config=llm_config,
                    on_json_error=callback,
                )
            )

        call_kwargs = mock_guards.call_args[1]
        assert call_kwargs["on_json_error"] is callback

    def test_build_stanza_extract_text_joins_lines(self, poem_project: Project, llm_config: LLMConfig) -> None:
        """build_stanza extract_text should join lines with newlines."""
        mock_output = StanzaProseOutput(lines=["First", "Second", "Third"])
        mock_result = _make_guards_result()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            asyncio.run(
                build_stanza(
                    stanza=poem_project.plot.stanzas[0],
                    project=poem_project,
                    prior_stanzas=[],
                    config=llm_config,
                )
            )

        call_kwargs = mock_guards.call_args[1]
        extract_fn = call_kwargs["extract_text"]
        assert extract_fn(mock_output) == "First\nSecond\nThird"


class TestBuildPoemFromLinesGuardsIntegration:
    """Tests for build_poem_from_lines using run_with_guards."""

    def test_build_poem_from_lines_uses_run_with_guards(self, poem_project: Project, llm_config: LLMConfig) -> None:
        """build_poem_from_lines should use run_with_guards."""
        mock_output = PoemProseOutput(content="Complete poem text.")
        mock_result = _make_guards_result()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            result = asyncio.run(
                build_poem_from_lines(
                    project=poem_project,
                    config=llm_config,
                )
            )

        assert result == "Complete poem text."
        mock_guards.assert_called_once()

    def test_build_poem_from_lines_passes_on_json_error_callback(
        self, poem_project: Project, llm_config: LLMConfig
    ) -> None:
        """build_poem_from_lines passes on_json_error callback."""
        mock_output = PoemProseOutput(content="Poem.")
        mock_result = _make_guards_result()
        callback = MagicMock()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            asyncio.run(
                build_poem_from_lines(
                    project=poem_project,
                    config=llm_config,
                    on_json_error=callback,
                )
            )

        call_kwargs = mock_guards.call_args[1]
        assert call_kwargs["on_json_error"] is callback


class TestEnhancedBuildSceneGuardsIntegration:
    """Tests for build_enhanced_scene using run_with_guards."""

    def test_build_enhanced_scene_uses_run_with_guards(self, simple_project: Project, llm_config: LLMConfig) -> None:
        """build_enhanced_scene should use run_with_guards."""
        mock_output = EnhancedSceneProseOutput(
            title="Hook Scene",
            hook=SceneHook(hook_type="action", content="Hook text."),
            beats=[BeatProseOutput(beat_id="beat-01", prose="Beat prose.", word_count=2)],
        )
        mock_result = _make_guards_result()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            result = asyncio.run(
                build_enhanced_scene(
                    scene=simple_project.plot.scenes[0],
                    project=simple_project,
                    prior_context="",
                    config=llm_config,
                )
            )

        assert result.hook is not None
        assert result.hook.content == "Hook text."
        mock_guards.assert_called_once()

    def test_build_enhanced_scene_passes_on_json_error_callback(
        self, simple_project: Project, llm_config: LLMConfig
    ) -> None:
        """build_enhanced_scene passes on_json_error callback."""
        mock_output = EnhancedSceneProseOutput(
            title="Prose Scene",
            hook=None,
            beats=[BeatProseOutput(beat_id="beat-01", prose="Prose.", word_count=1)],
        )
        mock_result = _make_guards_result()
        callback = MagicMock()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            asyncio.run(
                build_enhanced_scene(
                    scene=simple_project.plot.scenes[0],
                    project=simple_project,
                    prior_context="",
                    config=llm_config,
                    on_json_error=callback,
                )
            )

        call_kwargs = mock_guards.call_args[1]
        assert call_kwargs["on_json_error"] is callback


class TestEnhancedBuildFragmentGuardsIntegration:
    """Tests for build_enhanced_fragment using run_with_guards."""

    def test_build_enhanced_fragment_uses_run_with_guards(
        self, micro_prose_project: Project, llm_config: LLMConfig
    ) -> None:
        """build_enhanced_fragment should use run_with_guards."""
        mock_output = EnhancedFragmentProseOutput(
            hook=SceneHook(hook_type="image", content="Opening image."),
            content="Fragment content.",
        )
        mock_result = _make_guards_result()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            result = asyncio.run(
                build_enhanced_fragment(
                    fragment=micro_prose_project.plot.fragments[0],
                    project=micro_prose_project,
                    prior_fragments=[],
                    config=llm_config,
                )
            )

        assert result.hook is not None
        assert result.content == "Fragment content."
        mock_guards.assert_called_once()

    def test_build_enhanced_fragment_passes_on_json_error_callback(
        self, micro_prose_project: Project, llm_config: LLMConfig
    ) -> None:
        """build_enhanced_fragment passes on_json_error callback."""
        mock_output = EnhancedFragmentProseOutput(hook=None, content="Content.")
        mock_result = _make_guards_result()
        callback = MagicMock()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            asyncio.run(
                build_enhanced_fragment(
                    fragment=micro_prose_project.plot.fragments[0],
                    project=micro_prose_project,
                    prior_fragments=[],
                    config=llm_config,
                    on_json_error=callback,
                )
            )

        call_kwargs = mock_guards.call_args[1]
        assert call_kwargs["on_json_error"] is callback


class TestEnhancedBuildStanzaGuardsIntegration:
    """Tests for build_enhanced_stanza using run_with_guards."""

    def test_build_enhanced_stanza_uses_run_with_guards(self, poem_project: Project, llm_config: LLMConfig) -> None:
        """build_enhanced_stanza should use run_with_guards."""
        mock_output = EnhancedStanzaProseOutput(
            hook=SceneHook(hook_type="question", content="What dreams?"),
            lines=["Line one", "Line two"],
        )
        mock_result = _make_guards_result()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            result = asyncio.run(
                build_enhanced_stanza(
                    stanza=poem_project.plot.stanzas[0],
                    project=poem_project,
                    prior_stanzas=[],
                    config=llm_config,
                )
            )

        assert result.hook is not None
        assert result.lines == ["Line one", "Line two"]
        mock_guards.assert_called_once()

    def test_build_enhanced_stanza_passes_on_json_error_callback(
        self, poem_project: Project, llm_config: LLMConfig
    ) -> None:
        """build_enhanced_stanza passes on_json_error callback."""
        mock_output = EnhancedStanzaProseOutput(hook=None, lines=["Line"])
        mock_result = _make_guards_result()
        callback = MagicMock()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            asyncio.run(
                build_enhanced_stanza(
                    stanza=poem_project.plot.stanzas[0],
                    project=poem_project,
                    prior_stanzas=[],
                    config=llm_config,
                    on_json_error=callback,
                )
            )

        call_kwargs = mock_guards.call_args[1]
        assert call_kwargs["on_json_error"] is callback


class TestGenerateContinuitySummaryGuardsIntegration:
    """Tests for generate_continuity_summary using run_with_guards."""

    def test_generate_continuity_summary_uses_run_with_guards(self, llm_config: LLMConfig) -> None:
        """generate_continuity_summary should use run_with_guards."""
        from fabulae.features.build.schemas import ContinuitySummary

        mock_output = ContinuitySummary(summary="Scene summary here.")
        mock_result = _make_guards_result()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            result = asyncio.run(
                generate_continuity_summary(
                    scene_content="Some scene content.",
                    config=llm_config,
                )
            )

        assert result == "Scene summary here."
        mock_guards.assert_called_once()

    def test_generate_continuity_summary_passes_on_json_error_callback(self, llm_config: LLMConfig) -> None:
        """generate_continuity_summary passes on_json_error callback."""
        from fabulae.features.build.schemas import ContinuitySummary

        mock_output = ContinuitySummary(summary="Summary.")
        mock_result = _make_guards_result()
        callback = MagicMock()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            asyncio.run(
                generate_continuity_summary(
                    scene_content="Content.",
                    config=llm_config,
                    on_json_error=callback,
                )
            )

        call_kwargs = mock_guards.call_args[1]
        assert call_kwargs["on_json_error"] is callback


class TestSceneTitleFallback:
    """Tests for scene title fallback chain: scene.title > LLM title > scene.summary."""

    def test_build_scene_uses_llm_title(self, simple_project: Project, llm_config: LLMConfig) -> None:
        """build_scene uses LLM-generated title when scene has no explicit title."""
        mock_output = SceneProseOutput(title="Arrival at Dawn", content="Scene content.")
        mock_result = _make_guards_result()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            result = asyncio.run(
                build_scene(
                    scene=simple_project.plot.scenes[0],
                    project=simple_project,
                    prior_context="",
                    config=llm_config,
                )
            )

        assert result.title == "Arrival at Dawn"

    def test_build_scene_prefers_scene_model_title(self, simple_project: Project, llm_config: LLMConfig) -> None:
        """build_scene uses scene.title when set, even if LLM provides one."""
        simple_project.plot.scenes[0].title = "User Title"
        mock_output = SceneProseOutput(title="LLM Title", content="Content.")
        mock_result = _make_guards_result()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            result = asyncio.run(
                build_scene(
                    scene=simple_project.plot.scenes[0],
                    project=simple_project,
                    prior_context="",
                    config=llm_config,
                )
            )

        assert result.title == "User Title"

    def test_build_enhanced_scene_uses_llm_title(self, simple_project: Project, llm_config: LLMConfig) -> None:
        """build_enhanced_scene uses LLM-generated title when scene has no explicit title."""
        mock_output = EnhancedSceneProseOutput(
            title="Dark Encounter",
            hook=SceneHook(hook_type="action", content="Hook."),
            beats=[BeatProseOutput(beat_id="beat-01", prose="Prose.", word_count=1)],
        )
        mock_result = _make_guards_result()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            result = asyncio.run(
                build_enhanced_scene(
                    scene=simple_project.plot.scenes[0],
                    project=simple_project,
                    prior_context="",
                    config=llm_config,
                )
            )

        assert result.title == "Dark Encounter"

    def test_build_enhanced_scene_prefers_scene_model_title(
        self, simple_project: Project, llm_config: LLMConfig
    ) -> None:
        """build_enhanced_scene uses scene.title over LLM title."""
        simple_project.plot.scenes[0].title = "Manual Title"
        mock_output = EnhancedSceneProseOutput(
            title="LLM Title",
            hook=None,
            beats=[BeatProseOutput(beat_id="beat-01", prose="Prose.", word_count=1)],
        )
        mock_result = _make_guards_result()

        with patch("fabulae.features.build.scene_builder.run_with_guards") as mock_guards:
            mock_guards.return_value = (mock_output, mock_result)

            result = asyncio.run(
                build_enhanced_scene(
                    scene=simple_project.plot.scenes[0],
                    project=simple_project,
                    prior_context="",
                    config=llm_config,
                )
            )

        assert result.title == "Manual Title"
