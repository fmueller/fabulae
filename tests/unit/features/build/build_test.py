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

            result = asyncio.run(build_project(project, config, seed=42))

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

            result = asyncio.run(build_project(project, config))

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

            result = asyncio.run(build_project(project, config))

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

            # Run with seed
            result = asyncio.run(build_project(project, config, seed=12345))

        assert result.metadata.seed == 12345

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
