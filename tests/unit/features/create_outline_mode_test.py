"""Tests for outline-only mode (without --full flag)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from fabulae.features.create.schemas import (
    ChapterSketchOutput,
    CharacterSketchOutput,
    CreateOptions,
    LocationSketchOutput,
    OutlineOutput,
    SceneSketchOutput,
)
from fabulae.llm import LLMConfig
from fabulae.models import Plot, Project, ProjectConfig


class TestOutlineSchemas:
    """Tests for outline-only schemas."""

    def test_character_sketch_output_minimal_fields(self) -> None:
        """Test that CharacterSketchOutput has minimal required fields."""
        sketch = CharacterSketchOutput(
            id="character-01",
            name="Vera Mellifer",
            role="protagonist",
            description="A detective with synesthesia",
        )

        assert sketch.id == "character-01"
        assert sketch.name == "Vera Mellifer"
        assert sketch.role == "protagonist"
        assert sketch.description == "A detective with synesthesia"

        # Should not have full character attributes
        assert not hasattr(sketch, "desire")
        assert not hasattr(sketch, "need")
        assert not hasattr(sketch, "flaw")
        assert not hasattr(sketch, "secret")
        assert not hasattr(sketch, "traits")

    def test_scene_sketch_output_no_beats(self) -> None:
        """Test that SceneSketchOutput has no beats field."""
        sketch = SceneSketchOutput(
            id="scene-01",
            title="The Crime Scene",
            summary="Vera arrives at the symphony hall to find the conductor dead.",
            character_ids=["character-01"],
        )

        assert sketch.id == "scene-01"
        assert sketch.title == "The Crime Scene"
        assert sketch.summary is not None
        assert sketch.character_ids == ["character-01"]

        # Should not have beats
        assert not hasattr(sketch, "beats")
        assert not hasattr(sketch, "beat_count")

    def test_chapter_sketch_output_has_scene_ids(self) -> None:
        """Test that ChapterSketchOutput has scene_ids but no detailed content."""
        sketch = ChapterSketchOutput(
            id="chapter-01",
            title="The Discovery",
            summary="Vera is called to investigate a murder at the symphony hall.",
            scene_ids=["scene-01", "scene-02", "scene-03"],
        )

        assert sketch.id == "chapter-01"
        assert sketch.title == "The Discovery"
        assert sketch.summary is not None
        assert sketch.scene_ids == ["scene-01", "scene-02", "scene-03"]

    def test_location_sketch_output_minimal_fields(self) -> None:
        """Test that LocationSketchOutput has only id and name."""
        sketch = LocationSketchOutput(id="location-01", name="Symphony Hall")

        assert sketch.id == "location-01"
        assert sketch.name == "Symphony Hall"

        # Should not have detailed facts
        assert not hasattr(sketch, "facts")
        assert not hasattr(sketch, "type")

    def test_outline_output_has_all_components(self) -> None:
        """Test that OutlineOutput contains all outline components."""
        outline = OutlineOutput(
            title="The Synesthesia Detective",
            premise="A detective with synesthesia investigates a murder at a symphony hall.",
            chapters=[
                ChapterSketchOutput(
                    id="chapter-01",
                    title="The Discovery",
                    summary="Chapter summary",
                    scene_ids=["scene-01"],
                )
            ],
            scenes=[
                SceneSketchOutput(
                    id="scene-01",
                    title="The Crime Scene",
                    summary="Scene summary",
                    character_ids=["character-01"],
                )
            ],
            characters=[
                CharacterSketchOutput(
                    id="character-01",
                    name="Vera Mellifer",
                    role="protagonist",
                    description="A detective with synesthesia",
                )
            ],
            locations=[LocationSketchOutput(id="location-01", name="Symphony Hall")],
        )

        assert outline.title == "The Synesthesia Detective"
        assert len(outline.chapters) == 1
        assert len(outline.scenes) == 1
        assert len(outline.characters) == 1
        assert len(outline.locations) == 1


class TestCreateOptionsFullFlag:
    """Tests for CreateOptions full flag."""

    def test_create_options_full_default_false(self) -> None:
        """Test that CreateOptions.full defaults to False."""
        options = CreateOptions()
        assert options.full is False

    def test_create_options_full_can_be_set_true(self) -> None:
        """Test that CreateOptions.full can be set to True."""
        options = CreateOptions(full=True)
        assert options.full is True


class TestOutlineValidation:
    """Tests for outline output validation."""

    def test_validate_outline_detects_duplicate_ids(self) -> None:
        """Test that duplicate IDs are detected in outline validation."""
        from fabulae.features.create.pipelines.outline import _validate_outline_output

        outline = OutlineOutput(
            title="Test",
            premise="Test premise",
            chapters=[
                ChapterSketchOutput(id="chapter-01", scene_ids=["scene-01"]),
                ChapterSketchOutput(id="chapter-01", scene_ids=["scene-02"]),  # Duplicate
            ],
            scenes=[
                SceneSketchOutput(id="scene-01", character_ids=[]),
                SceneSketchOutput(id="scene-02", character_ids=[]),
            ],
            characters=[],
            locations=[],
        )

        error = _validate_outline_output(outline)
        assert error is not None
        assert "Duplicate chapter ID" in error

    def test_validate_outline_detects_orphan_scenes(self) -> None:
        """Test that scenes not assigned to chapters are detected."""
        from fabulae.features.create.pipelines.outline import _validate_outline_output

        outline = OutlineOutput(
            title="Test",
            premise="Test premise",
            chapters=[
                ChapterSketchOutput(id="chapter-01", scene_ids=["scene-01"]),
            ],
            scenes=[
                SceneSketchOutput(id="scene-01", character_ids=[]),
                SceneSketchOutput(id="scene-02", character_ids=[]),  # Orphan
            ],
            characters=[],
            locations=[],
        )

        error = _validate_outline_output(outline)
        assert error is not None
        assert "not assigned to any chapter" in error

    def test_validate_outline_detects_unknown_scene_refs(self) -> None:
        """Test that chapter referencing unknown scene is detected."""
        from fabulae.features.create.pipelines.outline import _validate_outline_output

        outline = OutlineOutput(
            title="Test",
            premise="Test premise",
            chapters=[
                ChapterSketchOutput(id="chapter-01", scene_ids=["scene-99"]),  # Unknown
            ],
            scenes=[
                SceneSketchOutput(id="scene-01", character_ids=[]),
            ],
            characters=[],
            locations=[],
        )

        error = _validate_outline_output(outline)
        assert error is not None
        assert "unknown scene" in error

    def test_validate_outline_detects_unknown_character_refs(self) -> None:
        """Test that scene referencing unknown character is detected."""
        from fabulae.features.create.pipelines.outline import _validate_outline_output

        outline = OutlineOutput(
            title="Test",
            premise="Test premise",
            chapters=[
                ChapterSketchOutput(id="chapter-01", scene_ids=["scene-01"]),
            ],
            scenes=[
                SceneSketchOutput(id="scene-01", character_ids=["character-99"]),  # Unknown
            ],
            characters=[
                CharacterSketchOutput(id="character-01", name="Test"),
            ],
            locations=[],
        )

        error = _validate_outline_output(outline)
        assert error is not None
        assert "unknown character" in error

    def test_validate_outline_valid_outline_passes(self) -> None:
        """Test that a valid outline passes validation."""
        from fabulae.features.create.pipelines.outline import _validate_outline_output

        outline = OutlineOutput(
            title="Test",
            premise="Test premise",
            chapters=[
                ChapterSketchOutput(id="chapter-01", scene_ids=["scene-01", "scene-02"]),
            ],
            scenes=[
                SceneSketchOutput(id="scene-01", character_ids=["character-01"]),
                SceneSketchOutput(id="scene-02", character_ids=["character-01"]),
            ],
            characters=[
                CharacterSketchOutput(id="character-01", name="Test"),
            ],
            locations=[
                LocationSketchOutput(id="location-01", name="Test Location"),
            ],
        )

        error = _validate_outline_output(outline)
        assert error is None


class TestOutlineProjectConversion:
    """Tests for converting outline to Project."""

    def test_convert_outline_creates_project_with_empty_beats(self) -> None:
        """Test that converted project has scenes with empty beats list."""
        from fabulae.features.create.pipelines.outline import _convert_outline_to_project
        from fabulae.features.create.schemas import StyleOutput

        outline = OutlineOutput(
            title="Test Story",
            premise="Test premise",
            chapters=[
                ChapterSketchOutput(id="chapter-01", title="Chapter 1", scene_ids=["scene-01"]),
            ],
            scenes=[
                SceneSketchOutput(
                    id="scene-01",
                    title="Scene 1",
                    summary="Scene summary",
                    character_ids=["character-01"],
                ),
            ],
            characters=[
                CharacterSketchOutput(id="character-01", name="Test Character", role="protagonist"),
            ],
            locations=[
                LocationSketchOutput(id="location-01", name="Test Location"),
            ],
        )

        style_output = StyleOutput(pov="third", tense="past", language="en")
        llm_config = LLMConfig()
        options = CreateOptions()

        project = _convert_outline_to_project(
            outline=outline,
            style_output=style_output,
            format_name="novel",
            idea="Test idea",
            llm_config=llm_config,
            options=options,
        )

        assert project.plot.scenes[0].beats == []

    def test_convert_outline_creates_characters_without_detailed_attrs(self) -> None:
        """Test that converted characters have no detailed attributes."""
        from fabulae.features.create.pipelines.outline import _convert_outline_to_project
        from fabulae.features.create.schemas import StyleOutput

        outline = OutlineOutput(
            title="Test Story",
            premise="Test premise",
            chapters=[],
            scenes=[],
            characters=[
                CharacterSketchOutput(
                    id="character-01",
                    name="Vera",
                    role="protagonist",
                    description="A detective",
                ),
            ],
            locations=[],
        )

        style_output = StyleOutput(pov="third", tense="past", language="en")
        llm_config = LLMConfig()
        options = CreateOptions()

        project = _convert_outline_to_project(
            outline=outline,
            style_output=style_output,
            format_name="novel",
            idea="Test idea",
            llm_config=llm_config,
            options=options,
        )

        char = project.characters[0]
        assert char.name == "Vera"
        assert char.role == "protagonist"
        # Detailed attributes should be None/empty
        assert char.desire is None
        assert char.need is None
        assert char.flaw is None
        assert char.secret is None
        assert char.traits == []

    def test_convert_outline_creates_locations_without_facts(self) -> None:
        """Test that converted locations have no detailed facts."""
        from fabulae.features.create.pipelines.outline import _convert_outline_to_project
        from fabulae.features.create.schemas import StyleOutput

        outline = OutlineOutput(
            title="Test Story",
            premise="Test premise",
            chapters=[],
            scenes=[],
            characters=[],
            locations=[
                LocationSketchOutput(id="location-01", name="Symphony Hall"),
            ],
        )

        style_output = StyleOutput(pov="third", tense="past", language="en")
        llm_config = LLMConfig()
        options = CreateOptions()

        project = _convert_outline_to_project(
            outline=outline,
            style_output=style_output,
            format_name="novel",
            idea="Test idea",
            llm_config=llm_config,
            options=options,
        )

        assert project.world is not None
        loc = project.world.facts[0]
        assert loc.name == "Symphony Hall"
        assert loc.type == "location"
        assert loc.facts == []


@pytest.mark.anyio
async def test_dispatcher_routes_to_outline_when_full_false(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """Test that dispatcher routes to outline pipeline when full=False."""
    from fabulae.features.create.service import generate_project_from_idea

    called = {"outline": False, "prose": False}

    async def fake_generate_outline_only(
        idea: str,
        format: str,
        options: CreateOptions,
        llm_config: Any,
        progress: Any = None,
        artifacts_dir: Path | None = None,
    ) -> Project:
        called["outline"] = True
        assert format == "novel"
        return Project(
            config=ProjectConfig(version="1.0.0", title="Test"),
            plot=Plot(format="novel", premise="Test premise"),
            characters=[],
            world=None,
            style=None,
        )

    async def fake_generate_prose(
        idea: str,
        format: str,
        options: CreateOptions,
        llm_config: Any,
        progress: Any = None,
        artifacts_dir: Path | None = None,
    ) -> Project:
        called["prose"] = True
        return Project(
            config=ProjectConfig(version="1.0.0", title="Test"),
            plot=Plot(format="novel", premise="Test premise"),
            characters=[],
            world=None,
            style=None,
        )

    monkeypatch.setattr(
        "fabulae.features.create.pipelines.outline.generate_outline_only",
        fake_generate_outline_only,
    )
    monkeypatch.setattr("fabulae.features.create.pipelines.prose.generate_prose", fake_generate_prose)

    # full=False (default) should route to outline pipeline
    await generate_project_from_idea(
        idea="A test novel",
        format_name="novel",
        config=LLMConfig(model="claude-3-haiku-20240307"),
        output_dir=tmp_path,
        options=CreateOptions(full=False),
    )

    assert called["outline"] is True
    assert called["prose"] is False


@pytest.mark.anyio
async def test_dispatcher_routes_to_prose_when_full_true(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """Test that dispatcher routes to prose pipeline when full=True."""
    from fabulae.features.create.service import generate_project_from_idea

    called = {"outline": False, "prose": False}

    async def fake_generate_outline_only(
        idea: str,
        format: str,
        options: CreateOptions,
        llm_config: Any,
        progress: Any = None,
        artifacts_dir: Path | None = None,
    ) -> Project:
        called["outline"] = True
        return Project(
            config=ProjectConfig(version="1.0.0", title="Test"),
            plot=Plot(format="novel", premise="Test premise"),
            characters=[],
            world=None,
            style=None,
        )

    async def fake_generate_prose(
        idea: str,
        format: str,
        options: CreateOptions,
        llm_config: Any,
        progress: Any = None,
        artifacts_dir: Path | None = None,
    ) -> Project:
        called["prose"] = True
        assert format == "novel"
        return Project(
            config=ProjectConfig(version="1.0.0", title="Test"),
            plot=Plot(format="novel", premise="Test premise"),
            characters=[],
            world=None,
            style=None,
        )

    monkeypatch.setattr(
        "fabulae.features.create.pipelines.outline.generate_outline_only",
        fake_generate_outline_only,
    )
    monkeypatch.setattr("fabulae.features.create.pipelines.prose.generate_prose", fake_generate_prose)

    # full=True should route to prose pipeline
    await generate_project_from_idea(
        idea="A test novel",
        format_name="novel",
        config=LLMConfig(model="claude-3-haiku-20240307"),
        output_dir=tmp_path,
        options=CreateOptions(full=True),
    )

    assert called["outline"] is False
    assert called["prose"] is True


def test_outline_prompt_mentions_outline_only() -> None:
    """Test that outline prompt explicitly mentions outline-only mode."""
    from fabulae.features.create.prompts import build_outline_only_prompt
    from fabulae.features.create.schemas import StyleOutput

    style = StyleOutput(pov="third", tense="past", voice="literary", language="en")
    count_ranges = {
        "chapters": (6, 12),
        "scenes": (18, 36),
        "characters": (4, 8),
        "locations": (4, 8),
    }

    prompt = build_outline_only_prompt("novel", style, count_ranges)

    # Should mention outline-only
    assert "OUTLINE only" in prompt or "outline only" in prompt.lower()
    # Schema should not include detailed beats (the JSON example shouldn't have beats field)
    assert '"beats"' not in prompt.lower()


def test_no_circular_imports_from_outline_pipeline() -> None:
    """Test that outline pipeline can be imported without circular import errors."""
    try:
        from fabulae.features.create.pipelines import outline  # noqa: F401
    except ImportError as e:
        pytest.fail(f"Circular import or import error detected: {e}")


class TestOutlineShapeAutoSelection:
    """Tests for shape auto-selection in outline pipeline."""

    def test_convert_outline_uses_auto_selected_shape_in_metadata(self) -> None:
        """Test that _convert_outline_to_project uses auto-selected shape ID in metadata."""
        from fabulae.features.create.pipelines.outline import _convert_outline_to_project
        from fabulae.features.create.schemas import StyleOutput

        outline = OutlineOutput(
            title="Test Story",
            premise="Test premise",
            chapters=[],
            scenes=[],
            characters=[],
            locations=[],
        )

        style_output = StyleOutput(pov="third", tense="past", language="en")
        llm_config = LLMConfig()

        # Simulate auto-selected shape by passing shape parameter
        # (The actual auto-selection happens in generate_outline_only, not _convert_outline_to_project)
        options = CreateOptions()

        project = _convert_outline_to_project(
            outline=outline,
            style_output=style_output,
            format_name="novel",
            idea="Test idea",
            llm_config=llm_config,
            options=options,
            auto_selected_shape_id="betrayal-arc",  # New parameter for auto-selected shape
        )

        # Metadata should include the auto-selected shape
        assert project.config.metadata is not None
        assert project.config.metadata.shape == "betrayal-arc"

    def test_convert_outline_prefers_explicit_shape_over_auto_selected(self) -> None:
        """Test that explicit shape_id option takes precedence over auto-selected shape."""
        from fabulae.features.create.pipelines.outline import _convert_outline_to_project
        from fabulae.features.create.schemas import StyleOutput

        outline = OutlineOutput(
            title="Test Story",
            premise="Test premise",
            chapters=[],
            scenes=[],
            characters=[],
            locations=[],
        )

        style_output = StyleOutput(pov="third", tense="past", language="en")
        llm_config = LLMConfig()

        # Explicit shape option should take precedence
        options = CreateOptions(shape_id="heros-journey")

        project = _convert_outline_to_project(
            outline=outline,
            style_output=style_output,
            format_name="novel",
            idea="Test idea",
            llm_config=llm_config,
            options=options,
            auto_selected_shape_id="betrayal-arc",  # Should be ignored
        )

        # Metadata should use explicit shape, not auto-selected
        assert project.config.metadata is not None
        assert project.config.metadata.shape == "heros-journey"

    def test_convert_outline_no_shape_when_no_shape_flag_set(self) -> None:
        """Test that no shape is recorded when --no-shape flag is used."""
        from fabulae.features.create.pipelines.outline import _convert_outline_to_project
        from fabulae.features.create.schemas import StyleOutput

        outline = OutlineOutput(
            title="Test Story",
            premise="Test premise",
            chapters=[],
            scenes=[],
            characters=[],
            locations=[],
        )

        style_output = StyleOutput(pov="third", tense="past", language="en")
        llm_config = LLMConfig()

        # no_shape flag should prevent shape from being recorded
        options = CreateOptions(no_shape=True)

        project = _convert_outline_to_project(
            outline=outline,
            style_output=style_output,
            format_name="novel",
            idea="Test idea",
            llm_config=llm_config,
            options=options,
            auto_selected_shape_id=None,  # No auto-selection when no_shape=True
        )

        # Metadata should have no_shape=True and shape=None
        assert project.config.metadata is not None
        assert project.config.metadata.shape is None
        assert project.config.metadata.no_shape is True

    @pytest.mark.anyio
    async def test_generate_outline_only_auto_selects_shape(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test that generate_outline_only calls select_shape_for_idea when no shape provided."""
        from unittest.mock import MagicMock

        from fabulae.features.create.pipelines.outline import generate_outline_only
        from fabulae.features.create.progress import CreateProgress
        from fabulae.models import StoryShape

        # Track if select_shape_for_idea was called
        shape_selection_called = False
        selected_shape_id = "mystery-reveal"

        # Create a mock StoryShape
        mock_shape = MagicMock(spec=StoryShape)
        mock_shape.id = selected_shape_id

        async def mock_select_shape(idea: str, config: LLMConfig) -> StoryShape:
            nonlocal shape_selection_called
            shape_selection_called = True
            return mock_shape

        monkeypatch.setattr(
            "fabulae.features.create.pipelines.outline.select_shape_for_idea",
            mock_select_shape,
        )

        # Mock run_stage to return valid outputs
        style_output = MagicMock()
        style_output.pov = "third"
        style_output.tense = "past"
        style_output.voice = "literary"
        style_output.language = "en"
        style_output.model_dump = MagicMock(return_value={"pov": "third", "tense": "past", "language": "en"})

        outline_output = OutlineOutput(
            title="Test Story",
            premise="Test premise",
            chapters=[],
            scenes=[],
            characters=[],
            locations=[],
        )

        call_count = 0

        async def mock_run_stage(*args, **kwargs):  # type: ignore[no-untyped-def]
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.output = style_output
            else:
                result.output = outline_output
            return result

        monkeypatch.setattr(
            "fabulae.features.create.pipelines.outline.run_stage",
            mock_run_stage,
        )

        # Run generate_outline_only without shape options
        llm_config = LLMConfig(model="test-model")
        options = CreateOptions()  # No shape, no no_shape
        progress = CreateProgress()

        project = await generate_outline_only(
            idea="A detective investigates a murder",
            format="novel",
            options=options,
            llm_config=llm_config,
            progress=progress,
            artifacts_dir=tmp_path,
        )

        # Verify shape auto-selection was called
        assert shape_selection_called is True

        # Verify metadata includes auto-selected shape
        assert project.config.metadata is not None
        assert project.config.metadata.shape == selected_shape_id

    @pytest.mark.anyio
    async def test_generate_outline_only_skips_shape_selection_when_no_shape(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test that generate_outline_only skips shape selection when --no-shape is used."""
        from unittest.mock import MagicMock

        from fabulae.features.create.pipelines.outline import generate_outline_only
        from fabulae.features.create.progress import CreateProgress
        from fabulae.models import StoryShape

        # Track if select_shape_for_idea was called
        shape_selection_called = False

        async def mock_select_shape(idea: str, config: LLMConfig) -> StoryShape:
            nonlocal shape_selection_called
            shape_selection_called = True
            raise AssertionError("Should not be called when no_shape=True")

        monkeypatch.setattr(
            "fabulae.features.create.pipelines.outline.select_shape_for_idea",
            mock_select_shape,
        )

        # Mock run_stage to return valid outputs
        style_output = MagicMock()
        style_output.pov = "third"
        style_output.tense = "past"
        style_output.voice = "literary"
        style_output.language = "en"
        style_output.model_dump = MagicMock(return_value={"pov": "third", "tense": "past", "language": "en"})

        outline_output = OutlineOutput(
            title="Test Story",
            premise="Test premise",
            chapters=[],
            scenes=[],
            characters=[],
            locations=[],
        )

        call_count = 0

        async def mock_run_stage(*args, **kwargs):  # type: ignore[no-untyped-def]
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.output = style_output
            else:
                result.output = outline_output
            return result

        monkeypatch.setattr(
            "fabulae.features.create.pipelines.outline.run_stage",
            mock_run_stage,
        )

        # Run generate_outline_only with no_shape=True
        llm_config = LLMConfig(model="test-model")
        options = CreateOptions(no_shape=True)
        progress = CreateProgress()

        project = await generate_outline_only(
            idea="A detective investigates a murder",
            format="novel",
            options=options,
            llm_config=llm_config,
            progress=progress,
            artifacts_dir=tmp_path,
        )

        # Verify shape auto-selection was NOT called
        assert shape_selection_called is False

        # Verify metadata has no shape
        assert project.config.metadata is not None
        assert project.config.metadata.shape is None
        assert project.config.metadata.no_shape is True

    @pytest.mark.anyio
    async def test_generate_outline_only_writes_shape_artifact(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test that generate_outline_only writes shape artifact when shape is auto-selected."""
        from unittest.mock import MagicMock

        from fabulae.features.create.pipelines.outline import generate_outline_only
        from fabulae.features.create.progress import CreateProgress
        from fabulae.models import StoryShape

        # Create a mock StoryShape
        mock_shape = MagicMock(spec=StoryShape)
        mock_shape.id = "betrayal-arc"

        async def mock_select_shape(idea: str, config: LLMConfig) -> StoryShape:
            return mock_shape

        monkeypatch.setattr(
            "fabulae.features.create.pipelines.outline.select_shape_for_idea",
            mock_select_shape,
        )

        # Mock run_stage to return valid outputs
        style_output = MagicMock()
        style_output.pov = "third"
        style_output.tense = "past"
        style_output.voice = "literary"
        style_output.language = "en"
        style_output.model_dump = MagicMock(return_value={"pov": "third", "tense": "past", "language": "en"})

        outline_output = OutlineOutput(
            title="Test Story",
            premise="Test premise",
            chapters=[],
            scenes=[],
            characters=[],
            locations=[],
        )

        call_count = 0

        async def mock_run_stage(*args, **kwargs):  # type: ignore[no-untyped-def]
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.output = style_output
            else:
                result.output = outline_output
            return result

        monkeypatch.setattr(
            "fabulae.features.create.pipelines.outline.run_stage",
            mock_run_stage,
        )

        # Create artifacts dir
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        # Run generate_outline_only
        llm_config = LLMConfig(model="test-model")
        options = CreateOptions()
        progress = CreateProgress()

        await generate_outline_only(
            idea="A story about betrayal",
            format="novel",
            options=options,
            llm_config=llm_config,
            progress=progress,
            artifacts_dir=artifacts_dir,
        )

        # Verify shape artifact was written (artifacts are in .fabulae/create subdirectory)
        shape_artifact = artifacts_dir / ".fabulae" / "create" / "01a-shape.yml"
        assert shape_artifact.exists()

        # Verify artifact contents
        import yaml

        with open(shape_artifact) as f:
            content = yaml.safe_load(f)
        assert content["shape_id"] == "betrayal-arc"
        assert content["auto_selected"] is True
