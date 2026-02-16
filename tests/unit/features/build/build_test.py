"""Tests for build command."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml
from typer.testing import CliRunner

from fabulae.features.build.schemas import (
    BuildMetadata,
    BuildOptions,
    BuildOutput,
    ChapterOutput,
    FragmentOutput,
    SceneOutput,
)
from fabulae.features.build.writer import write_build_output
from fabulae.main import app

runner = CliRunner()


def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def create_novel_project(tmp_path: Path) -> Path:
    """Create a minimal novel project for testing."""
    (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0", "title": "Test Novel"}))
    (tmp_path / "plot.yml").write_text(
        yaml.dump(
            {
                "premise": "A test story about adventure.",
                "format": "novel",
                "title": "Test Novel",
                "chapters": [
                    {"id": "chapter-01", "title": "Beginning", "scene_ids": ["scene-01"]},
                    {"id": "chapter-02", "title": "Middle", "scene_ids": ["scene-02"]},
                ],
                "scenes": [
                    {
                        "id": "scene-01",
                        "summary": "First scene",
                        "characters": ["char-01"],
                        "beats": [{"id": "beat-01", "kind": "opening"}],
                    },
                    {
                        "id": "scene-02",
                        "summary": "Second scene",
                        "characters": ["char-01"],
                        "beats": [{"id": "beat-02", "kind": "development"}],
                    },
                ],
            }
        )
    )
    (tmp_path / "characters.yml").write_text(
        yaml.dump(
            {
                "characters": [
                    {"id": "char-01", "name": "Alice", "role": "protagonist"},
                ]
            }
        )
    )
    (tmp_path / "style.yml").write_text(
        yaml.dump(
            {
                "language": "en",
                "pov": "third-person limited",
                "tense": "past",
            }
        )
    )
    return tmp_path


def create_short_story_project(tmp_path: Path) -> Path:
    """Create a minimal short-story project for testing."""
    (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
    (tmp_path / "plot.yml").write_text(
        yaml.dump(
            {
                "premise": "A brief tale.",
                "format": "short-story",
                "scenes": [
                    {"id": "scene-01", "summary": "Only scene"},
                ],
            }
        )
    )
    return tmp_path


def create_micro_prose_project(tmp_path: Path) -> Path:
    """Create a minimal micro-prose project for testing."""
    (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
    (tmp_path / "plot.yml").write_text(
        yaml.dump(
            {
                "premise": "Flash fiction.",
                "format": "micro-prose",
                "fragments": [
                    {"id": "frag-01", "content": "Opening moment."},
                    {"id": "frag-02", "content": "Closing moment."},
                ],
            }
        )
    )
    return tmp_path


def create_poem_project(tmp_path: Path) -> Path:
    """Create a minimal poem project for testing."""
    (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
    (tmp_path / "plot.yml").write_text(
        yaml.dump(
            {
                "premise": "Nature's beauty.",
                "format": "poem",
                "poem_form": "free verse",
                "stanzas": [
                    {"id": "stanza-01", "lines": ["First line seed"]},
                    {"id": "stanza-02", "lines": ["Second line seed"]},
                ],
            }
        )
    )
    return tmp_path


def create_poem_lines_project(tmp_path: Path) -> Path:
    """Create a poem project with only lines (no stanzas)."""
    (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
    (tmp_path / "plot.yml").write_text(
        yaml.dump(
            {
                "premise": "Haiku about snow.",
                "format": "poem",
                "poem_form": "haiku",
                "lines": ["Snow falls softly", "Winter silence"],
            }
        )
    )
    return tmp_path


def create_novella_project_without_chapters(tmp_path: Path) -> Path:
    """Create a novella project with scenes but no chapters."""
    (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
    (tmp_path / "plot.yml").write_text(
        yaml.dump(
            {
                "premise": "A botanist returns to confront the family land sale.",
                "format": "novella",
                "scenes": [
                    {
                        "id": "scene-01",
                        "summary": "June walks the orchard rows.",
                    },
                    {
                        "id": "scene-02",
                        "summary": "June confronts her uncle.",
                    },
                ],
            }
        )
    )
    return tmp_path


class TestBuildCommand:
    """Tests for build CLI command."""

    def test_build_help_shows_options(self) -> None:
        """Build command help shows all options."""
        result = runner.invoke(app, ["build", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "--output" in output
        assert "--seed" in output
        assert "--model" in output
        assert "--temperature" in output
        assert "--format" in output

    def test_build_invalid_project_path_fails(self, tmp_path: Path) -> None:
        """Building with invalid project path fails."""
        result = runner.invoke(app, ["build", str(tmp_path / "nonexistent")])
        assert result.exit_code == 1
        assert "Failed to load project" in result.output or "not found" in result.output.lower()

    def test_build_malformed_yaml_shows_clean_error(self, tmp_path: Path) -> None:
        """Building with malformed YAML shows a clean error, not a traceback."""
        (tmp_path / "fabulae.yml").write_text("version: 0.1.0\n")
        (tmp_path / "plot.yml").write_text("{{{broken\n")

        result = runner.invoke(app, ["build", str(tmp_path)])
        output = strip_ansi(result.output)
        assert result.exit_code == 1
        assert "Failed to load project" in output
        assert "Traceback" not in output

    def test_build_invalid_format_project_fails(self, tmp_path: Path) -> None:
        """Building with invalid format project fails."""
        (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
        (tmp_path / "plot.yml").write_text(
            yaml.dump(
                {
                    "premise": "Test",
                    "format": "novel",
                    # Missing required scenes
                }
            )
        )

        result = runner.invoke(app, ["build", str(tmp_path)])
        assert result.exit_code == 1


class TestBuildSchemas:
    """Tests for build output schemas."""

    def test_build_metadata_serialization(self) -> None:
        """BuildMetadata serializes correctly."""
        metadata = BuildMetadata(
            project_name="Test",
            format="novel",
            seed=42,
            model="test-model",
            temperature=0.7,
            timestamp=datetime(2024, 1, 15, 14, 30, 52),
            version="0.1.0",
        )
        json_str = metadata.model_dump_json()
        assert "Test" in json_str
        assert "42" in json_str

    def test_scene_output_validation(self) -> None:
        """SceneOutput validates word count."""
        scene = SceneOutput(
            scene_id="scene-01",
            content="Hello world",
            word_count=2,
        )
        assert scene.word_count == 2

    def test_build_output_with_chapters(self) -> None:
        """BuildOutput accepts chapters."""
        output = BuildOutput(
            metadata=BuildMetadata(
                project_name="Test",
                format="novel",
                model="test",
                temperature=0.7,
                timestamp=datetime.now(),
                version="0.1.0",
            ),
            chapters=[
                ChapterOutput(
                    chapter_id="ch-01",
                    title="First",
                    scenes=[
                        SceneOutput(scene_id="s-01", content="Test", word_count=1),
                    ],
                    word_count=1,
                )
            ],
            full_text="# First\n\nTest",
            total_word_count=1,
        )
        assert output.chapters is not None and len(output.chapters) == 1


class TestBuildWriter:
    """Tests for build output writer."""

    def _create_metadata(self) -> BuildMetadata:
        return BuildMetadata(
            project_name="Test Story",
            format="novel",
            seed=42,
            model="test-model",
            temperature=0.7,
            timestamp=datetime(2024, 1, 15, 14, 30, 52),
            version="0.1.0",
        )

    def test_write_build_output_creates_files(self, tmp_path: Path) -> None:
        """Writer creates expected output files."""
        output = BuildOutput(
            metadata=self._create_metadata(),
            full_text="# Test\n\nHello world.",
            total_word_count=2,
        )
        output_dir = tmp_path / "output"

        write_build_output(output, output_dir, "md")

        assert (output_dir / "build.json").exists()
        assert (output_dir / "story.md").exists()

        story_content = (output_dir / "story.md").read_text()
        assert story_content.startswith("# Test Story\n\n")

    def test_write_build_output_txt_format(self, tmp_path: Path) -> None:
        """Writer strips markdown for txt format."""
        output = BuildOutput(
            metadata=self._create_metadata(),
            full_text="# Heading\n\n**Bold** text.",
            total_word_count=3,
        )
        output_dir = tmp_path / "output"

        write_build_output(output, output_dir, "txt")

        txt_content = (output_dir / "story.txt").read_text()
        assert "# Heading" not in txt_content
        assert "**Bold**" not in txt_content
        assert "Bold text" in txt_content
        assert txt_content.startswith("Test Story")

    def test_write_build_output_html_format(self, tmp_path: Path) -> None:
        """Writer converts to HTML correctly."""
        output = BuildOutput(
            metadata=self._create_metadata(),
            full_text="# Heading\n\nParagraph text.",
            total_word_count=3,
        )
        output_dir = tmp_path / "output"

        write_build_output(output, output_dir, "html")

        html_content = (output_dir / "story.html").read_text()
        assert "<h1>Test Story</h1>" in html_content
        assert "<h1>Heading</h1>" in html_content
        assert "<p>Paragraph text.</p>" in html_content
        assert "<!DOCTYPE html>" in html_content

    def test_write_build_output_with_chapters(self, tmp_path: Path) -> None:
        """Writer creates chapter files when chapters present."""
        output = BuildOutput(
            metadata=self._create_metadata(),
            chapters=[
                ChapterOutput(
                    chapter_id="ch-01",
                    title="First Chapter",
                    scenes=[
                        SceneOutput(scene_id="s-01", content="Scene content.", word_count=2),
                    ],
                    word_count=2,
                ),
            ],
            full_text="# First Chapter\n\nScene content.",
            total_word_count=2,
        )
        output_dir = tmp_path / "output"

        write_build_output(output, output_dir, "md")

        chapters_dir = output_dir / "chapters"
        assert chapters_dir.exists()
        chapter_files = list(chapters_dir.glob("*.md"))
        assert len(chapter_files) == 1
        assert "first-chapter" in chapter_files[0].name

    def test_write_build_output_with_fragments(self, tmp_path: Path) -> None:
        """Writer creates fragment files when fragments present."""
        output = BuildOutput(
            metadata=BuildMetadata(
                project_name="Test",
                format="micro-prose",
                model="test",
                temperature=0.7,
                timestamp=datetime.now(),
                version="0.1.0",
            ),
            fragments=[
                FragmentOutput(fragment_id="frag-01", content="First fragment.", word_count=2),
                FragmentOutput(fragment_id="frag-02", content="Second fragment.", word_count=2),
            ],
            full_text="First fragment.\n\n---\n\nSecond fragment.",
            total_word_count=4,
        )
        output_dir = tmp_path / "output"

        write_build_output(output, output_dir, "md")

        fragments_dir = output_dir / "fragments"
        assert fragments_dir.exists()
        fragment_files = list(fragments_dir.glob("*.md"))
        assert len(fragment_files) == 2

    def test_write_build_output_no_title_header_for_untitled(self, tmp_path: Path) -> None:
        """Writer does not add title header when project is 'Untitled'."""
        metadata = BuildMetadata(
            project_name="Untitled",
            format="novel",
            seed=None,
            model="test-model",
            temperature=0.7,
            timestamp=datetime(2024, 1, 15, 14, 30, 52),
            version="0.1.0",
        )
        output = BuildOutput(
            metadata=metadata,
            full_text="Some content.",
            total_word_count=2,
        )
        output_dir = tmp_path / "output"

        write_build_output(output, output_dir, "md")

        story_content = (output_dir / "story.md").read_text()
        assert story_content == "Some content."

    def test_write_build_metadata_json(self, tmp_path: Path) -> None:
        """Writer saves metadata as JSON."""
        output = BuildOutput(
            metadata=self._create_metadata(),
            full_text="Test",
            total_word_count=1,
        )
        output_dir = tmp_path / "output"

        write_build_output(output, output_dir, "md")

        import json

        metadata = json.loads((output_dir / "build.json").read_text())
        assert metadata["project_name"] == "Test Story"
        assert metadata["seed"] == 42
        assert metadata["model"] == "test-model"


class TestBuildPrompts:
    """Tests for build prompts."""

    def test_scene_prompt_includes_premise(self) -> None:
        """Scene prompt includes story premise."""
        from fabulae.features.build.prompts import build_scene_prompt
        from fabulae.models import Beat, Scene

        scene = Scene(
            id="scene-01",
            summary="Test scene",
            beats=[Beat(id="beat-01", kind="opening")],
        )

        prompt = build_scene_prompt(
            scene=scene,
            characters=[],
            location=None,
            world_facts=[],
            style=None,
            prior_context="",
            premise="A story about testing.",
        )

        assert "A story about testing" in prompt
        assert "scene-01" in prompt

    def test_fragment_prompt_includes_context(self) -> None:
        """Fragment prompt includes prior fragments."""
        from fabulae.features.build.prompts import build_fragment_prompt
        from fabulae.models import Fragment

        fragment = Fragment(id="frag-01", content="Test fragment.")

        prompt = build_fragment_prompt(
            fragment=fragment,
            style=None,
            prior_fragments=["Previous fragment content."],
            premise="Flash fiction.",
        )

        assert "Previous fragment content" in prompt
        assert "Flash fiction" in prompt

    def test_stanza_prompt_includes_form(self) -> None:
        """Stanza prompt includes poem form."""
        from fabulae.features.build.prompts import build_stanza_prompt
        from fabulae.models import Stanza

        stanza = Stanza(id="stanza-01", lines=["Line seed"])

        prompt = build_stanza_prompt(
            stanza=stanza,
            style=None,
            prior_stanzas=[],
            premise="Nature poem.",
            poem_form="sonnet",
            poem_meter="iambic pentameter",
            poem_rhyme_scheme="ABAB",
        )

        assert "sonnet" in prompt
        assert "iambic pentameter" in prompt
        assert "ABAB" in prompt


class TestBuildService:
    """Tests for build service orchestration."""

    def test_build_project_chaptered_format(self, tmp_path: Path) -> None:
        """Build service handles chaptered formats."""
        import asyncio

        from fabulae.features.build.schemas import SceneProseOutput
        from fabulae.features.build.service import build_project
        from fabulae.llm import LLMConfig
        from fabulae.models import load_project

        create_novel_project(tmp_path)
        project = load_project(tmp_path)
        config = LLMConfig(model="test")

        # Mock the agent to return test content
        mock_result = AsyncMock()
        mock_result.output = SceneProseOutput(content="Generated scene content.")

        summary_mock = AsyncMock()
        summary_mock.output = type("Summary", (), {"summary": "Scene summary."})()

        with patch("fabulae.features.build.scene_builder.create_agent") as mock_create:
            mock_agent = AsyncMock()
            mock_agent.run = AsyncMock(side_effect=[mock_result, summary_mock] * 10)
            mock_create.return_value = mock_agent

            # Use non-enhanced mode for simpler mocking
            options = BuildOptions(enhanced=False)
            result = asyncio.run(build_project(project, config, seed=42, options=options))

        assert result.chapters is not None
        assert len(result.chapters) == 2
        assert result.total_word_count > 0

    def test_build_project_micro_prose_format(self, tmp_path: Path) -> None:
        """Build service handles micro-prose format."""
        import asyncio

        from fabulae.features.build.schemas import FragmentProseOutput
        from fabulae.features.build.service import build_project
        from fabulae.llm import LLMConfig
        from fabulae.models import load_project

        create_micro_prose_project(tmp_path)
        project = load_project(tmp_path)
        config = LLMConfig(model="test")

        mock_result = AsyncMock()
        mock_result.output = FragmentProseOutput(content="Generated fragment content.")

        with patch("fabulae.features.build.scene_builder.create_agent") as mock_create:
            mock_agent = AsyncMock()
            mock_agent.run = AsyncMock(return_value=mock_result)
            mock_create.return_value = mock_agent

            # Use non-enhanced mode for simpler mocking
            options = BuildOptions(enhanced=False)
            result = asyncio.run(build_project(project, config, options=options))

        assert result.fragments is not None
        assert len(result.fragments) == 2

    def test_build_project_poem_format(self, tmp_path: Path) -> None:
        """Build service handles poem format with stanzas."""
        import asyncio

        from fabulae.features.build.schemas import StanzaProseOutput
        from fabulae.features.build.service import build_project
        from fabulae.llm import LLMConfig
        from fabulae.models import load_project

        create_poem_project(tmp_path)
        project = load_project(tmp_path)
        config = LLMConfig(model="test")

        mock_result = AsyncMock()
        mock_result.output = StanzaProseOutput(lines=["Line one", "Line two"])

        with patch("fabulae.features.build.scene_builder.create_agent") as mock_create:
            mock_agent = AsyncMock()
            mock_agent.run = AsyncMock(return_value=mock_result)
            mock_create.return_value = mock_agent

            # Use non-enhanced mode for simpler mocking
            options = BuildOptions(enhanced=False)
            result = asyncio.run(build_project(project, config, options=options))

        assert result.stanzas is not None
        assert len(result.stanzas) == 2

    def test_build_project_poem_lines_format(self, tmp_path: Path) -> None:
        """Build service handles poem format with only lines."""
        import asyncio

        from fabulae.features.build.schemas import PoemProseOutput
        from fabulae.features.build.service import build_project
        from fabulae.llm import LLMConfig
        from fabulae.models import load_project

        create_poem_lines_project(tmp_path)
        project = load_project(tmp_path)
        config = LLMConfig(model="test")

        mock_result = AsyncMock()
        mock_result.output = PoemProseOutput(content="Complete poem text\nLine two")

        with patch("fabulae.features.build.scene_builder.create_agent") as mock_create:
            mock_agent = AsyncMock()
            mock_agent.run = AsyncMock(return_value=mock_result)
            mock_create.return_value = mock_agent

            result = asyncio.run(build_project(project, config))

        assert result.poem is not None
        assert "Complete poem text" in result.poem

    def test_build_project_with_seed(self, tmp_path: Path) -> None:
        """Build service uses seed for reproducibility."""
        import asyncio

        from fabulae.features.build.schemas import SceneProseOutput
        from fabulae.features.build.service import build_project
        from fabulae.llm import LLMConfig
        from fabulae.models import load_project

        create_short_story_project(tmp_path)
        project = load_project(tmp_path)
        config = LLMConfig(model="test")

        mock_result = AsyncMock()
        mock_result.output = SceneProseOutput(content="Content.")

        summary_mock = AsyncMock()
        summary_mock.output = type("Summary", (), {"summary": "Summary."})()

        with patch("fabulae.features.build.scene_builder.create_agent") as mock_create:
            mock_agent = AsyncMock()
            mock_agent.run = AsyncMock(side_effect=[mock_result, summary_mock])
            mock_create.return_value = mock_agent

            # Run with seed (use non-enhanced mode for simpler mocking)
            options = BuildOptions(enhanced=False)
            result = asyncio.run(build_project(project, config, seed=12345, options=options))

        assert result.metadata.seed == 12345

    def test_build_project_chaptered_without_chapters_falls_back(self, tmp_path: Path) -> None:
        """Chaptered format without chapters falls back to scene-based build."""
        import asyncio

        from fabulae.features.build.schemas import SceneProseOutput
        from fabulae.features.build.service import build_project
        from fabulae.llm import LLMConfig
        from fabulae.models import load_project

        create_novella_project_without_chapters(tmp_path)
        project = load_project(tmp_path)
        config = LLMConfig(model="test")

        mock_result = AsyncMock()
        mock_result.output = SceneProseOutput(content="Generated scene content.")

        summary_mock = AsyncMock()
        summary_mock.output = type("Summary", (), {"summary": "Scene summary."})()

        with patch("fabulae.features.build.scene_builder.create_agent") as mock_create:
            mock_agent = AsyncMock()
            mock_agent.run = AsyncMock(side_effect=[mock_result, summary_mock] * 10)
            mock_create.return_value = mock_agent

            # Use non-enhanced mode for simpler mocking
            options = BuildOptions(enhanced=False)
            result = asyncio.run(build_project(project, config, options=options))

        assert result.scenes is not None
        assert len(result.scenes) == 2
        assert result.chapters is None
        assert result.total_word_count > 0
        assert "Generated scene content" in result.full_text

    def test_build_project_chaptered_without_chapters_warns(self, tmp_path: Path) -> None:
        """Chaptered format without chapters issues a warning via progress."""
        import asyncio
        from unittest.mock import MagicMock

        from fabulae.features.build.schemas import SceneProseOutput
        from fabulae.features.build.service import build_project
        from fabulae.llm import LLMConfig
        from fabulae.models import load_project

        create_novella_project_without_chapters(tmp_path)
        project = load_project(tmp_path)
        config = LLMConfig(model="test")

        mock_result = AsyncMock()
        mock_result.output = SceneProseOutput(content="Content.")

        summary_mock = AsyncMock()
        summary_mock.output = type("Summary", (), {"summary": "Summary."})()

        progress = MagicMock()

        with patch("fabulae.features.build.scene_builder.create_agent") as mock_create:
            mock_agent = AsyncMock()
            mock_agent.run = AsyncMock(side_effect=[mock_result, summary_mock] * 10)
            mock_create.return_value = mock_agent

            # Use non-enhanced mode for simpler mocking
            options = BuildOptions(enhanced=False)
            asyncio.run(build_project(project, config, progress=progress, options=options))

        progress.warn.assert_called_once()
        assert "No chapters found" in progress.warn.call_args[0][0]

    def test_build_project_unknown_format_raises(self, tmp_path: Path) -> None:
        """Build service raises for unknown format."""
        import asyncio

        from fabulae.features.build.service import build_project
        from fabulae.llm import LLMConfig
        from fabulae.models import Plot, Project, ProjectConfig

        project = Project(
            config=ProjectConfig(version="0.1.0"),
            plot=Plot(
                premise="Test",
                format="novel",  # Will be overwritten
                scenes=[],
            ),
        )
        # Hack to set invalid format
        object.__setattr__(project.plot, "format", "unknown-format")
        config = LLMConfig(model="test")

        with pytest.raises(ValueError, match="Unknown format"):
            asyncio.run(build_project(project, config))


class TestBuildLanguageGuard:
    """Tests for language enforcement in build."""

    def test_build_help_shows_language_option(self) -> None:
        """Build command help shows --language option."""
        result = runner.invoke(app, ["build", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "--language" in output

    def test_build_language_flag_accepted(self, tmp_path: Path) -> None:
        """Build command accepts --language flag."""
        import asyncio

        from fabulae.features.build.schemas import SceneProseOutput
        from fabulae.features.build.service import build_project
        from fabulae.llm import LLMConfig
        from fabulae.models import load_project

        create_short_story_project(tmp_path)
        project = load_project(tmp_path)
        config = LLMConfig(model="test")

        # Patch language guard to skip detection (test just ensures no crash)
        with patch("fabulae.features.build.scene_builder.run_with_language_guard") as mock_guard:
            mock_guard.return_value = (
                SceneProseOutput(content="Inhalt auf Deutsch."),
                type("Result", (), {"passed": True, "skipped": True})(),
            )
            # Also mock generate_continuity_summary since it's called after scene building
            with patch(
                "fabulae.features.build.pipelines.sequential.generate_continuity_summary",
                new_callable=AsyncMock,
                return_value="Summary of the scene.",
            ):
                # Use non-enhanced mode for simpler mocking
                options = BuildOptions(enhanced=False)
                result = asyncio.run(build_project(project, config, expected_language="de", options=options))

        assert result.scenes is not None

    def test_build_uses_style_language_when_no_flag(self, tmp_path: Path) -> None:
        """Build resolves language from style.yml when no --language flag."""
        import asyncio

        from fabulae.features.build.schemas import SceneProseOutput
        from fabulae.features.build.service import build_project
        from fabulae.llm import LLMConfig
        from fabulae.models import load_project

        create_novel_project(tmp_path)
        project = load_project(tmp_path)
        config = LLMConfig(model="test")

        # project has style.language = "en" from create_novel_project
        assert project.style is not None
        assert project.style.language == "en"

        with patch("fabulae.features.build.scene_builder.run_with_language_guard") as mock_guard:
            mock_guard.return_value = (
                SceneProseOutput(content="English content."),
                type("Result", (), {"passed": True, "skipped": True})(),
            )
            # Also mock generate_continuity_summary since it's called after scene building
            with patch(
                "fabulae.features.build.pipelines.sequential.generate_continuity_summary",
                new_callable=AsyncMock,
                return_value="Summary of the scene.",
            ):
                # Use non-enhanced mode for simpler mocking
                options = BuildOptions(enhanced=False)
                asyncio.run(build_project(project, config, expected_language=project.style.language, options=options))

        # Verify language guard was called with expected language
        assert mock_guard.call_count > 0
        call_kwargs = mock_guard.call_args
        assert call_kwargs[1].get("expected_language") == "en" or call_kwargs[0][2] == "en"

    def test_build_scene_builder_passes_expected_language(self, tmp_path: Path) -> None:
        """scene_builder.build_scene passes expected_language to run_with_language_guard."""
        import asyncio

        from fabulae.features.build.scene_builder import build_scene
        from fabulae.features.build.schemas import SceneProseOutput
        from fabulae.llm import LLMConfig
        from fabulae.models import Beat, Plot, Project, ProjectConfig, Scene

        project = Project(
            config=ProjectConfig(version="0.1.0"),
            plot=Plot(
                premise="Test",
                format="short-story",
                scenes=[Scene(id="scene-01", summary="Test", beats=[Beat(id="b-01", kind="opening")])],
            ),
        )
        scene = project.plot.scenes[0]
        config = LLMConfig(model="test")

        with patch("fabulae.features.build.scene_builder.run_with_language_guard") as mock_guard:
            mock_guard.return_value = (
                SceneProseOutput(content="German content."),
                type("Result", (), {"passed": True, "skipped": False})(),
            )
            result = asyncio.run(build_scene(scene, project, "", config, expected_language="de"))

        assert result.content == "German content."
        # Verify expected_language was passed
        call_kwargs = mock_guard.call_args[1]
        assert call_kwargs["expected_language"] == "de"
        # Verify correct callback was provided
        assert call_kwargs["correct"] is not None


class TestEnhancedBuild:
    """Tests for enhanced build features (hooks, beat tracking)."""

    def test_enhanced_scene_prose_output_schema(self) -> None:
        """EnhancedSceneProseOutput validates correctly."""
        from fabulae.features.build.schemas import (
            BeatProseOutput,
            EnhancedSceneProseOutput,
            SceneHook,
        )

        output = EnhancedSceneProseOutput(
            hook=SceneHook(hook_type="action", content="The door burst open."),
            beats=[
                BeatProseOutput(beat_id="beat-01", prose="First beat content.", word_count=3),
                BeatProseOutput(beat_id="beat-02", prose="Second beat content.", word_count=3),
            ],
        )
        assert output.hook is not None
        assert output.hook.hook_type == "action"
        assert len(output.beats) == 2

    def test_enhanced_fragment_prose_output_schema(self) -> None:
        """EnhancedFragmentProseOutput validates correctly."""
        from fabulae.features.build.schemas import (
            EnhancedFragmentProseOutput,
            SceneHook,
        )

        output = EnhancedFragmentProseOutput(
            hook=SceneHook(hook_type="image", content="Snow fell silently."),
            content="The full fragment content here.",
        )
        assert output.hook is not None
        assert output.hook.hook_type == "image"
        assert "full fragment" in output.content

    def test_enhanced_stanza_prose_output_schema(self) -> None:
        """EnhancedStanzaProseOutput validates correctly."""
        from fabulae.features.build.schemas import (
            EnhancedStanzaProseOutput,
            SceneHook,
        )

        output = EnhancedStanzaProseOutput(
            hook=SceneHook(hook_type="question", content="What dreams may come?"),
            lines=["First line of poetry", "Second line of poetry"],
        )
        assert output.hook is not None
        assert output.hook.hook_type == "question"
        assert len(output.lines) == 2

    def test_scene_output_with_hook_and_beats(self) -> None:
        """SceneOutput accepts hook and beats."""
        from fabulae.features.build.schemas import (
            BeatProseOutput,
            SceneHook,
            SceneOutput,
        )

        output = SceneOutput(
            scene_id="scene-01",
            hook=SceneHook(hook_type="dialog", content='"We need to leave now."'),
            beats=[
                BeatProseOutput(beat_id="beat-01", prose="Action scene.", word_count=2),
            ],
            content="Full scene content.",
            word_count=3,
        )
        assert output.hook is not None
        assert output.hook.hook_type == "dialog"
        assert len(output.beats) == 1

    def test_extract_enhanced_scene_text(self) -> None:
        """extract_enhanced_scene_text extracts all prose for language detection."""
        from fabulae.features.build.scene_builder import extract_enhanced_scene_text
        from fabulae.features.build.schemas import (
            BeatProseOutput,
            EnhancedSceneProseOutput,
            SceneHook,
        )

        output = EnhancedSceneProseOutput(
            hook=SceneHook(hook_type="action", content="Hook text here."),
            beats=[
                BeatProseOutput(beat_id="beat-01", prose="Beat one prose.", word_count=3),
                BeatProseOutput(beat_id="beat-02", prose="Beat two prose.", word_count=3),
            ],
        )

        extracted = extract_enhanced_scene_text(output)
        assert "Hook text here." in extracted
        assert "Beat one prose." in extracted
        assert "Beat two prose." in extracted

    def test_extract_enhanced_fragment_text(self) -> None:
        """extract_enhanced_fragment_text extracts all prose for language detection."""
        from fabulae.features.build.scene_builder import extract_enhanced_fragment_text
        from fabulae.features.build.schemas import (
            EnhancedFragmentProseOutput,
            SceneHook,
        )

        output = EnhancedFragmentProseOutput(
            hook=SceneHook(hook_type="image", content="Opening image."),
            content="Main fragment content.",
        )

        extracted = extract_enhanced_fragment_text(output)
        assert "Opening image." in extracted
        assert "Main fragment content." in extracted

    def test_extract_enhanced_stanza_text(self) -> None:
        """extract_enhanced_stanza_text extracts all text for language detection."""
        from fabulae.features.build.scene_builder import extract_enhanced_stanza_text
        from fabulae.features.build.schemas import (
            EnhancedStanzaProseOutput,
            SceneHook,
        )

        output = EnhancedStanzaProseOutput(
            hook=SceneHook(hook_type="question", content="Shall I compare thee?"),
            lines=["Line one", "Line two"],
        )

        extracted = extract_enhanced_stanza_text(output)
        assert "Shall I compare thee?" in extracted
        assert "Line one" in extracted
        assert "Line two" in extracted

    def test_build_options_defaults(self) -> None:
        """BuildOptions has correct defaults."""
        from fabulae.features.build.schemas import BuildOptions

        options = BuildOptions()
        assert options.pipeline == "sequential"
        assert options.enhanced is True
        assert options.sliding_window_size == 5

    def test_enhanced_scene_prompt_includes_prior_hooks(self) -> None:
        """Enhanced scene prompt includes prior hooks for diversity."""
        from fabulae.features.build.prompts import build_enhanced_scene_prompt
        from fabulae.models import Beat, Scene

        scene = Scene(
            id="scene-01",
            summary="Test scene",
            beats=[Beat(id="beat-01", kind="opening")],
        )

        prompt = build_enhanced_scene_prompt(
            scene=scene,
            characters=[],
            location=None,
            world_facts=[],
            style=None,
            prior_context="",
            premise="A story about testing.",
            prior_hooks=["The door slammed shut.", "She ran into the night."],
        )

        assert "Previous Hooks" in prompt
        assert "The door slammed shut." in prompt
        assert "She ran into the night." in prompt
        assert "beat-01" in prompt

    def test_cli_shows_pipeline_and_enhanced_options(self) -> None:
        """Build CLI shows --pipeline and --enhanced options."""
        result = runner.invoke(app, ["build", "--help"])
        output = strip_ansi(result.output)
        assert "--pipeline" in output
        assert "--enhanced" in output
        assert "sequential" in output.lower() or "batch" in output.lower()


class TestPipelineAutoSelection:
    """Tests for automatic pipeline mode selection based on model size."""

    def test_large_model_defaults_to_batch(self, tmp_path: Path) -> None:
        """Large models default to batch pipeline when no --pipeline flag is given."""
        create_short_story_project(tmp_path)

        with patch("fabulae.features.build.cli.build_project", new_callable=AsyncMock) as mock_build:
            mock_build.return_value = BuildOutput(
                metadata=BuildMetadata(
                    project_name="Test",
                    format="short-story",
                    model="gpt-4o",
                    temperature=0.7,
                    timestamp=datetime.now(),
                    version="0.1.0",
                ),
                scenes=[SceneOutput(scene_id="s-01", content="Test", word_count=1)],
                full_text="Test",
                total_word_count=1,
            )

            result = runner.invoke(app, ["build", str(tmp_path), "--model", "gpt-4o", "--no-history"])
            output = strip_ansi(result.output)
            assert "Pipeline: batch" in output

    def test_small_model_defaults_to_sequential(self, tmp_path: Path) -> None:
        """Small models default to sequential pipeline when no --pipeline flag is given."""
        create_short_story_project(tmp_path)

        with patch("fabulae.features.build.cli.build_project", new_callable=AsyncMock) as mock_build:
            mock_build.return_value = BuildOutput(
                metadata=BuildMetadata(
                    project_name="Test",
                    format="short-story",
                    model="llama:7b",
                    temperature=0.7,
                    timestamp=datetime.now(),
                    version="0.1.0",
                ),
                scenes=[SceneOutput(scene_id="s-01", content="Test", word_count=1)],
                full_text="Test",
                total_word_count=1,
            )

            result = runner.invoke(app, ["build", str(tmp_path), "--model", "llama:7b", "--no-history"])
            output = strip_ansi(result.output)
            assert "Pipeline: sequential" in output

    def test_explicit_pipeline_flag_overrides_auto(self, tmp_path: Path) -> None:
        """Explicit --pipeline flag overrides auto-detection."""
        create_short_story_project(tmp_path)

        with patch("fabulae.features.build.cli.build_project", new_callable=AsyncMock) as mock_build:
            mock_build.return_value = BuildOutput(
                metadata=BuildMetadata(
                    project_name="Test",
                    format="short-story",
                    model="gpt-4o",
                    temperature=0.7,
                    timestamp=datetime.now(),
                    version="0.1.0",
                ),
                scenes=[SceneOutput(scene_id="s-01", content="Test", word_count=1)],
                full_text="Test",
                total_word_count=1,
            )

            result = runner.invoke(
                app, ["build", str(tmp_path), "--model", "gpt-4o", "--pipeline", "sequential", "--no-history"]
            )
            output = strip_ansi(result.output)
            assert "Pipeline: sequential" in output
