"""Tests for plot-first pipeline functions."""

from __future__ import annotations

import random

import pytest

from fabulae.features.create.pipelines.plot_first import (
    BeatAssignment,
    OutlineStructure,
    assign_required_beats_to_scenes,
    build_beat_templates_with_variation,
    generate_characters_from_slots,
    generate_outline_structure,
    generate_world_from_slots,
)
from fabulae.features.create.schemas import CharacterOutput, StyleOutput, WorldFactOutput
from fabulae.features.create.service import StageResult
from fabulae.llm import LLMConfig
from fabulae.models import CharacterSlot, RequiredBeat, SettingSlot, StoryShape


def test_outline_structure_dataclass() -> None:
    """Test OutlineStructure can be instantiated."""
    structure = OutlineStructure(
        num_chapters=3,
        scenes_per_chapter=[2, 3, 2],
        beats_per_scene=[3, 3, 4, 3, 2, 3, 4],
        total_scenes=7,
        total_beats=22,
    )

    assert structure.num_chapters == 3
    assert structure.scenes_per_chapter == [2, 3, 2]
    assert structure.beats_per_scene == [3, 3, 4, 3, 2, 3, 4]
    assert structure.total_scenes == 7
    assert structure.total_beats == 22


def test_generate_outline_structure_novel() -> None:
    """Test novel format gets appropriate counts."""
    rng = random.Random(42)
    structure = generate_outline_structure("novel", None, rng)

    # Novel ranges: chapters (12-30), scenes (36-90), beats (180-360)
    assert 12 <= structure.num_chapters <= 30
    assert 36 <= structure.total_scenes <= 90
    assert 180 <= structure.total_beats <= 360

    # Verify scene distribution matches chapter count
    assert len(structure.scenes_per_chapter) == structure.num_chapters
    assert sum(structure.scenes_per_chapter) == structure.total_scenes

    # Verify beat distribution matches scene count
    assert len(structure.beats_per_scene) == structure.total_scenes
    assert sum(structure.beats_per_scene) == structure.total_beats


def test_generate_outline_structure_short_story() -> None:
    """Test short-story format gets fewer counts."""
    rng = random.Random(42)
    structure = generate_outline_structure("short-story", None, rng)

    # Short-story ranges: chapters (0-6), scenes (2-8), beats (6-24)
    assert 0 <= structure.num_chapters <= 6
    assert 2 <= structure.total_scenes <= 8
    assert 6 <= structure.total_beats <= 24

    # Verify totals are calculated correctly
    assert sum(structure.beats_per_scene) == structure.total_beats

    if structure.num_chapters > 0:
        assert sum(structure.scenes_per_chapter) == structure.total_scenes
    else:
        assert structure.scenes_per_chapter == []


def test_generate_outline_structure_novella() -> None:
    """Test novella format gets medium counts."""
    rng = random.Random(42)
    structure = generate_outline_structure("novella", None, rng)

    # Novella ranges: chapters (6-16), scenes (18-48), beats (72-192)
    assert 6 <= structure.num_chapters <= 16
    assert 18 <= structure.total_scenes <= 48
    assert 72 <= structure.total_beats <= 192


def test_generate_outline_structure_with_shape_beats() -> None:
    """Test structure respects shape's beat count needs."""
    # Create a shape with 20 required beats
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        required_beats=[RequiredBeat(type=f"beat-{i:02d}", description=f"Beat {i}") for i in range(1, 21)],
    )

    rng = random.Random(42)
    structure = generate_outline_structure("short-story", shape, rng)

    # Should have at least 20 beats to accommodate required beats
    assert structure.total_beats >= 20

    # Each beat should be within valid range (2-4 for short-story)
    for beat_count in structure.beats_per_scene:
        assert 2 <= beat_count <= 4


def test_generate_outline_structure_seeded_reproducibility() -> None:
    """Test with seeded RNG for reproducibility."""
    rng1 = random.Random(12345)
    structure1 = generate_outline_structure("novel", None, rng1)

    rng2 = random.Random(12345)
    structure2 = generate_outline_structure("novel", None, rng2)

    # Same seed should produce identical results
    assert structure1.num_chapters == structure2.num_chapters
    assert structure1.scenes_per_chapter == structure2.scenes_per_chapter
    assert structure1.beats_per_scene == structure2.beats_per_scene
    assert structure1.total_scenes == structure2.total_scenes
    assert structure1.total_beats == structure2.total_beats


def test_generate_outline_structure_different_seeds() -> None:
    """Test different seeds produce different results."""
    rng1 = random.Random(111)
    structure1 = generate_outline_structure("novel", None, rng1)

    rng2 = random.Random(222)
    structure2 = generate_outline_structure("novel", None, rng2)

    # Different seeds should produce different results (at least some difference)
    assert (
        structure1.num_chapters != structure2.num_chapters
        or structure1.scenes_per_chapter != structure2.scenes_per_chapter
        or structure1.beats_per_scene != structure2.beats_per_scene
    )


def test_generate_outline_structure_total_calculations() -> None:
    """Test total_scenes and total_beats are calculated correctly."""
    rng = random.Random(999)
    structure = generate_outline_structure("novella", None, rng)

    # total_scenes should equal sum of scenes_per_chapter if chapters exist
    if structure.num_chapters > 0:
        assert structure.total_scenes == sum(structure.scenes_per_chapter)

    # total_beats should equal sum of beats_per_scene
    assert structure.total_beats == sum(structure.beats_per_scene)

    # beats_per_scene length should equal total_scenes
    assert len(structure.beats_per_scene) == structure.total_scenes


def test_generate_outline_structure_invalid_format() -> None:
    """Test invalid format raises error."""
    rng = random.Random(42)

    with pytest.raises(ValueError, match="is not a prose format"):
        generate_outline_structure("micro-prose", None, rng)

    with pytest.raises(ValueError, match="is not a prose format"):
        generate_outline_structure("poem", None, rng)


def test_generate_outline_structure_no_chapters() -> None:
    """Test structure with zero chapters."""
    # Short-story can have 0 chapters
    rng = random.Random(42)

    # Force zero chapters by trying multiple seeds until we get one
    # (or just test the logic if we do get zero)
    for seed in range(1000):
        rng = random.Random(seed)
        structure = generate_outline_structure("short-story", None, rng)

        if structure.num_chapters == 0:
            # Should have empty scenes_per_chapter
            assert structure.scenes_per_chapter == []
            # But should still have scenes
            assert structure.total_scenes > 0
            assert len(structure.beats_per_scene) == structure.total_scenes
            break


def test_generate_outline_structure_beats_per_scene_range() -> None:
    """Test beats per scene are within format range."""
    rng = random.Random(42)

    # Novel: 3-6 beats per scene
    structure = generate_outline_structure("novel", None, rng)
    for beat_count in structure.beats_per_scene:
        assert 3 <= beat_count <= 6

    # Short-story: 2-4 beats per scene
    structure = generate_outline_structure("short-story", None, rng)
    for beat_count in structure.beats_per_scene:
        assert 2 <= beat_count <= 4

    # Novella: 2-5 beats per scene
    structure = generate_outline_structure("novella", None, rng)
    for beat_count in structure.beats_per_scene:
        assert 2 <= beat_count <= 5


def test_generate_outline_structure_with_many_required_beats() -> None:
    """Test shape with many required beats increases beat count."""
    # Create a shape with 50 required beats (more than typical short-story)
    shape = StoryShape(
        id="large-shape",
        name="Large Shape",
        description="A shape with many beats",
        required_beats=[RequiredBeat(type=f"beat-{i:02d}", description=f"Beat {i}") for i in range(1, 51)],
    )

    rng = random.Random(42)
    structure = generate_outline_structure("short-story", shape, rng)

    # Should have at least 50 beats
    assert structure.total_beats >= 50

    # May need more scenes to accommodate all beats
    # (since short-story has 2-4 beats per scene max)
    min_scenes_needed = (50 + 4 - 1) // 4  # ceiling division
    assert structure.total_scenes >= min_scenes_needed


# Tests for generate_world_from_slots


@pytest.mark.anyio
async def test_generate_world_from_slots_basic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test location generated for each required setting slot."""
    # Create a shape with two setting slots
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        setting_slots=[
            SettingSlot(slot="ordinary-world", needs="A safe, familiar place", optional=False),
            SettingSlot(slot="special-world", needs="A dangerous, unfamiliar place", optional=False),
        ],
    )

    # Mock run_stage to return predetermined outputs
    call_count = 0

    async def mock_run_stage(**kwargs):  # type: ignore
        nonlocal call_count
        call_count += 1

        # Return different outputs based on call count
        if call_count == 1:
            output = WorldFactOutput(
                id="location-01",
                type="location",
                name="Hometown Village",
                facts=["peaceful", "familiar faces", "market square"],
            )
        else:
            output = WorldFactOutput(
                id="location-02",
                type="location",
                name="Dark Forest",
                facts=["mysterious", "dangerous creatures", "ancient trees"],
            )

        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    # Call the function
    world_facts = await generate_world_from_slots(
        idea="A hero's journey",
        format="novel",
        shape=shape,
        location_ids=["location-01", "location-02"],
        slot_mapping={"ordinary-world": "location-01", "special-world": "location-02"},
        llm_config=LLMConfig(),
    )

    # Verify we got two locations
    assert len(world_facts) == 2

    # Verify first location
    assert world_facts[0].id == "location-01"
    assert world_facts[0].type == "location"
    assert world_facts[0].name == "Hometown Village"
    assert "peaceful" in world_facts[0].facts

    # Verify second location
    assert world_facts[1].id == "location-02"
    assert world_facts[1].type == "location"
    assert world_facts[1].name == "Dark Forest"
    assert "mysterious" in world_facts[1].facts


@pytest.mark.anyio
async def test_generate_world_from_slots_assigned_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test location has assigned ID (not generated)."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        setting_slots=[
            SettingSlot(slot="home", needs="A safe place", optional=False),
        ],
    )

    # Mock run_stage to return output with correct ID
    async def mock_run_stage(**kwargs):  # type: ignore
        output = WorldFactOutput(
            id="location-42",  # The assigned ID
            type="location",
            name="Safe Haven",
            facts=["secure", "comfortable"],
        )
        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    # Call with specific assigned ID
    world_facts = await generate_world_from_slots(
        idea="A journey",
        format="short-story",
        shape=shape,
        location_ids=["location-42"],
        slot_mapping={"home": "location-42"},
        llm_config=LLMConfig(),
    )

    # Verify the ID matches what we assigned
    assert len(world_facts) == 1
    assert world_facts[0].id == "location-42"


@pytest.mark.anyio
async def test_generate_world_from_slots_type_location(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test location has type='location'."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        setting_slots=[
            SettingSlot(slot="tavern", needs="A meeting place", optional=False),
        ],
    )

    # Mock run_stage
    async def mock_run_stage(**kwargs):  # type: ignore
        output = WorldFactOutput(
            id="location-01",
            type="location",  # Must be location
            name="The Rusty Nail",
            facts=["crowded", "warm hearth", "lively music"],
        )
        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    world_facts = await generate_world_from_slots(
        idea="A fantasy tale",
        format="novel",
        shape=shape,
        location_ids=["location-01"],
        slot_mapping={"tavern": "location-01"},
        llm_config=LLMConfig(),
    )

    # Verify type is location
    assert world_facts[0].type == "location"


@pytest.mark.anyio
async def test_generate_world_from_slots_optional_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test optional slots only generated if in slot_mapping."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        setting_slots=[
            SettingSlot(slot="required-place", needs="A required location", optional=False),
            SettingSlot(slot="optional-place", needs="An optional location", optional=True),
        ],
    )

    call_count = 0

    async def mock_run_stage(**kwargs):  # type: ignore
        nonlocal call_count
        call_count += 1
        output = WorldFactOutput(
            id="location-01",
            type="location",
            name="Required Location",
            facts=["important"],
        )
        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    # Only map the required slot, skip the optional one
    world_facts = await generate_world_from_slots(
        idea="A tale",
        format="novel",
        shape=shape,
        location_ids=["location-01"],
        slot_mapping={"required-place": "location-01"},  # optional-place not mapped
        llm_config=LLMConfig(),
    )

    # Should only have generated one location
    assert len(world_facts) == 1
    assert call_count == 1


@pytest.mark.anyio
async def test_generate_world_from_slots_optional_include(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test optional slots generated when in slot_mapping."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        setting_slots=[
            SettingSlot(slot="required-place", needs="A required location", optional=False),
            SettingSlot(slot="optional-place", needs="An optional location", optional=True),
        ],
    )

    call_count = 0

    async def mock_run_stage(**kwargs):  # type: ignore
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            output = WorldFactOutput(id="location-01", type="location", name="Place 1", facts=[])
        else:
            output = WorldFactOutput(id="location-02", type="location", name="Place 2", facts=[])
        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    # Map both slots
    world_facts = await generate_world_from_slots(
        idea="A tale",
        format="novel",
        shape=shape,
        location_ids=["location-01", "location-02"],
        slot_mapping={"required-place": "location-01", "optional-place": "location-02"},
        llm_config=LLMConfig(),
    )

    # Should have generated both locations
    assert len(world_facts) == 2
    assert call_count == 2


@pytest.mark.anyio
async def test_generate_world_from_slots_extra_world_facts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test extra world facts generated when IDs provided."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        setting_slots=[
            SettingSlot(slot="home", needs="A safe place", optional=False),
        ],
    )

    call_count = 0

    async def mock_run_stage(**kwargs):  # type: ignore
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Location
            output = WorldFactOutput(id="location-01", type="location", name="Home", facts=[])
        elif call_count == 2:
            # Extra world fact - culture
            output = WorldFactOutput(id="world-fact-01", type="culture", name="The Guild", facts=["ancient"])
        else:
            # Extra world fact - history
            output = WorldFactOutput(id="world-fact-02", type="history", name="The War", facts=["recent"])
        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    world_facts = await generate_world_from_slots(
        idea="A tale",
        format="novel",
        shape=shape,
        location_ids=["location-01"],
        slot_mapping={"home": "location-01"},
        llm_config=LLMConfig(),
        extra_world_fact_ids=["world-fact-01", "world-fact-02"],
    )

    # Should have 1 location + 2 extra facts
    assert len(world_facts) == 3
    assert world_facts[0].id == "location-01"
    assert world_facts[0].type == "location"
    assert world_facts[1].id == "world-fact-01"
    assert world_facts[1].type == "culture"
    assert world_facts[2].id == "world-fact-02"
    assert world_facts[2].type == "history"


@pytest.mark.anyio
async def test_generate_world_from_slots_with_style(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test style guidance is passed to prompts."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        setting_slots=[
            SettingSlot(slot="castle", needs="A fortress", optional=False),
        ],
    )

    captured_kwargs = None

    async def mock_run_stage(**kwargs):  # type: ignore
        nonlocal captured_kwargs
        captured_kwargs = kwargs
        output = WorldFactOutput(id="location-01", type="location", name="Castle", facts=[])
        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    style = StyleOutput(language="en", voice="dramatic", register="literary")

    await generate_world_from_slots(
        idea="A tale",
        format="novel",
        shape=shape,
        location_ids=["location-01"],
        slot_mapping={"castle": "location-01"},
        llm_config=LLMConfig(),
        style=style,
    )

    # Verify style was used
    assert captured_kwargs is not None
    assert captured_kwargs["expected_language"] == "en"
    assert "dramatic" in captured_kwargs["system_prompt"]
    assert "literary" in captured_kwargs["system_prompt"]


@pytest.mark.anyio
async def test_generate_world_from_slots_missing_required_slot() -> None:
    """Test error when required slot not in mapping."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        setting_slots=[
            SettingSlot(slot="required-place", needs="A required location", optional=False),
        ],
    )

    with pytest.raises(ValueError, match="Required setting slot 'required-place' not found"):
        await generate_world_from_slots(
            idea="A tale",
            format="novel",
            shape=shape,
            location_ids=["location-01"],
            slot_mapping={},  # Missing the required slot
            llm_config=LLMConfig(),
        )


@pytest.mark.anyio
async def test_generate_world_from_slots_no_extra_world_facts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test with no extra world facts."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        setting_slots=[
            SettingSlot(slot="place", needs="A location", optional=False),
        ],
    )

    async def mock_run_stage(**kwargs):  # type: ignore
        output = WorldFactOutput(id="location-01", type="location", name="Place", facts=[])
        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    world_facts = await generate_world_from_slots(
        idea="A tale",
        format="novel",
        shape=shape,
        location_ids=["location-01"],
        slot_mapping={"place": "location-01"},
        llm_config=LLMConfig(),
        extra_world_fact_ids=None,  # Explicitly None
    )

    # Should only have the one location
    assert len(world_facts) == 1


@pytest.mark.anyio
async def test_generate_world_from_slots_empty_extra_world_facts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test with empty extra world facts list."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        setting_slots=[
            SettingSlot(slot="place", needs="A location", optional=False),
        ],
    )

    async def mock_run_stage(**kwargs):  # type: ignore
        output = WorldFactOutput(id="location-01", type="location", name="Place", facts=[])
        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    world_facts = await generate_world_from_slots(
        idea="A tale",
        format="novel",
        shape=shape,
        location_ids=["location-01"],
        slot_mapping={"place": "location-01"},
        llm_config=LLMConfig(),
        extra_world_fact_ids=[],  # Empty list
    )

    # Should only have the one location
    assert len(world_facts) == 1


# Tests for generate_outline_content


@pytest.mark.anyio
async def test_generate_outline_content_all_chapter_ids_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test all provided chapter IDs appear in output."""
    structure = OutlineStructure(
        num_chapters=3,
        scenes_per_chapter=[2, 2, 2],
        beats_per_scene=[3, 3, 3, 3, 3, 3],
        total_scenes=6,
        total_beats=18,
    )

    chapter_ids = ["chapter-01", "chapter-02", "chapter-03"]
    scene_ids = ["scene-01", "scene-02", "scene-03", "scene-04", "scene-05", "scene-06"]

    # Mock run_stage
    async def mock_run_stage(**kwargs):  # type: ignore
        from fabulae.features.create.schemas import ChapterContentOutput, OutlineContentOutput, SceneContentOutput

        chapters = [
            ChapterContentOutput(id="chapter-01", title="Chapter One", summary="First chapter"),
            ChapterContentOutput(id="chapter-02", title="Chapter Two", summary="Second chapter"),
            ChapterContentOutput(id="chapter-03", title="Chapter Three", summary="Third chapter"),
        ]
        scenes = [
            SceneContentOutput(id="scene-01", chapter_id="chapter-01", title="Scene 1", summary="S1", beat_count=3),
            SceneContentOutput(id="scene-02", chapter_id="chapter-01", title="Scene 2", summary="S2", beat_count=3),
            SceneContentOutput(id="scene-03", chapter_id="chapter-02", title="Scene 3", summary="S3", beat_count=3),
            SceneContentOutput(id="scene-04", chapter_id="chapter-02", title="Scene 4", summary="S4", beat_count=3),
            SceneContentOutput(id="scene-05", chapter_id="chapter-03", title="Scene 5", summary="S5", beat_count=3),
            SceneContentOutput(id="scene-06", chapter_id="chapter-03", title="Scene 6", summary="S6", beat_count=3),
        ]
        output = OutlineContentOutput(chapters=chapters, scenes=scenes)
        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    from fabulae.features.create.pipelines.plot_first import generate_outline_content

    result = await generate_outline_content(
        idea="A test story",
        format="novel",
        structure=structure,
        shape=None,
        llm_config=LLMConfig(),
        chapter_ids=chapter_ids,
        scene_ids=scene_ids,
    )

    # All chapter IDs must be present
    assert len(result.chapters) == 3
    chapter_ids_in_result = {ch.id for ch in result.chapters}
    assert chapter_ids_in_result == {"chapter-01", "chapter-02", "chapter-03"}


@pytest.mark.anyio
async def test_generate_outline_content_all_scene_ids_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test all provided scene IDs appear in output."""
    structure = OutlineStructure(
        num_chapters=2,
        scenes_per_chapter=[3, 2],
        beats_per_scene=[3, 3, 3, 3, 3],
        total_scenes=5,
        total_beats=15,
    )

    chapter_ids = ["chapter-01", "chapter-02"]
    scene_ids = ["scene-01", "scene-02", "scene-03", "scene-04", "scene-05"]

    # Mock run_stage
    async def mock_run_stage(**kwargs):  # type: ignore
        from fabulae.features.create.schemas import ChapterContentOutput, OutlineContentOutput, SceneContentOutput

        chapters = [
            ChapterContentOutput(id="chapter-01", title="Ch1", summary="Chapter 1"),
            ChapterContentOutput(id="chapter-02", title="Ch2", summary="Chapter 2"),
        ]
        scenes = [
            SceneContentOutput(id="scene-01", chapter_id="chapter-01", title="S1", summary="Scene 1", beat_count=3),
            SceneContentOutput(id="scene-02", chapter_id="chapter-01", title="S2", summary="Scene 2", beat_count=3),
            SceneContentOutput(id="scene-03", chapter_id="chapter-01", title="S3", summary="Scene 3", beat_count=3),
            SceneContentOutput(id="scene-04", chapter_id="chapter-02", title="S4", summary="Scene 4", beat_count=3),
            SceneContentOutput(id="scene-05", chapter_id="chapter-02", title="S5", summary="Scene 5", beat_count=3),
        ]
        output = OutlineContentOutput(chapters=chapters, scenes=scenes)
        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    from fabulae.features.create.pipelines.plot_first import generate_outline_content

    result = await generate_outline_content(
        idea="A test story",
        format="novella",
        structure=structure,
        shape=None,
        llm_config=LLMConfig(),
        chapter_ids=chapter_ids,
        scene_ids=scene_ids,
    )

    # All scene IDs must be present
    assert len(result.scenes) == 5
    scene_ids_in_result = {sc.id for sc in result.scenes}
    assert scene_ids_in_result == {"scene-01", "scene-02", "scene-03", "scene-04", "scene-05"}


@pytest.mark.anyio
async def test_generate_outline_content_no_new_ids_created(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test no new IDs created (output uses exactly the IDs given)."""
    structure = OutlineStructure(
        num_chapters=2,
        scenes_per_chapter=[1, 1],
        beats_per_scene=[3, 3],
        total_scenes=2,
        total_beats=6,
    )

    chapter_ids = ["chapter-01", "chapter-02"]
    scene_ids = ["scene-01", "scene-02"]

    # Mock run_stage
    async def mock_run_stage(**kwargs):  # type: ignore
        from fabulae.features.create.schemas import ChapterContentOutput, OutlineContentOutput, SceneContentOutput

        # Validation should catch if LLM tries to add extra IDs
        chapters = [
            ChapterContentOutput(id="chapter-01", title="Ch1", summary="Chapter 1"),
            ChapterContentOutput(id="chapter-02", title="Ch2", summary="Chapter 2"),
        ]
        scenes = [
            SceneContentOutput(id="scene-01", chapter_id="chapter-01", title="S1", summary="Scene 1", beat_count=3),
            SceneContentOutput(id="scene-02", chapter_id="chapter-02", title="S2", summary="Scene 2", beat_count=3),
        ]
        output = OutlineContentOutput(chapters=chapters, scenes=scenes)
        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    from fabulae.features.create.pipelines.plot_first import generate_outline_content

    result = await generate_outline_content(
        idea="A test story",
        format="short-story",
        structure=structure,
        shape=None,
        llm_config=LLMConfig(),
        chapter_ids=chapter_ids,
        scene_ids=scene_ids,
    )

    # Should have exactly the IDs we provided, no more, no less
    assert len(result.chapters) == 2
    assert len(result.scenes) == 2
    assert {ch.id for ch in result.chapters} == set(chapter_ids)
    assert {sc.id for sc in result.scenes} == set(scene_ids)


@pytest.mark.anyio
async def test_generate_outline_content_scenes_distributed_across_chapters(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test scenes are distributed across chapters correctly."""
    structure = OutlineStructure(
        num_chapters=3,
        scenes_per_chapter=[1, 2, 1],  # Different distribution
        beats_per_scene=[3, 3, 3, 3],
        total_scenes=4,
        total_beats=12,
    )

    chapter_ids = ["chapter-01", "chapter-02", "chapter-03"]
    scene_ids = ["scene-01", "scene-02", "scene-03", "scene-04"]

    # Mock run_stage
    async def mock_run_stage(**kwargs):  # type: ignore
        from fabulae.features.create.schemas import ChapterContentOutput, OutlineContentOutput, SceneContentOutput

        chapters = [
            ChapterContentOutput(id="chapter-01", title="Ch1", summary="Chapter 1"),
            ChapterContentOutput(id="chapter-02", title="Ch2", summary="Chapter 2"),
            ChapterContentOutput(id="chapter-03", title="Ch3", summary="Chapter 3"),
        ]
        # Scenes distributed according to structure: 1, 2, 1
        scenes = [
            SceneContentOutput(id="scene-01", chapter_id="chapter-01", title="S1", summary="Scene 1", beat_count=3),
            SceneContentOutput(id="scene-02", chapter_id="chapter-02", title="S2", summary="Scene 2", beat_count=3),
            SceneContentOutput(id="scene-03", chapter_id="chapter-02", title="S3", summary="Scene 3", beat_count=3),
            SceneContentOutput(id="scene-04", chapter_id="chapter-03", title="S4", summary="Scene 4", beat_count=3),
        ]
        output = OutlineContentOutput(chapters=chapters, scenes=scenes)
        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    from fabulae.features.create.pipelines.plot_first import generate_outline_content

    result = await generate_outline_content(
        idea="A test story",
        format="novella",
        structure=structure,
        shape=None,
        llm_config=LLMConfig(),
        chapter_ids=chapter_ids,
        scene_ids=scene_ids,
    )

    # Verify distribution matches structure
    ch1_scenes = [sc for sc in result.scenes if sc.chapter_id == "chapter-01"]
    ch2_scenes = [sc for sc in result.scenes if sc.chapter_id == "chapter-02"]
    ch3_scenes = [sc for sc in result.scenes if sc.chapter_id == "chapter-03"]

    assert len(ch1_scenes) == 1
    assert len(ch2_scenes) == 2
    assert len(ch3_scenes) == 1


@pytest.mark.anyio
async def test_generate_outline_content_no_chapters(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test with no chapters (chapter_ids empty, scenes have no chapter_id)."""
    structure = OutlineStructure(
        num_chapters=0,
        scenes_per_chapter=[],
        beats_per_scene=[3, 3],
        total_scenes=2,
        total_beats=6,
    )

    chapter_ids: list[str] = []
    scene_ids = ["scene-01", "scene-02"]

    # Mock run_stage
    async def mock_run_stage(**kwargs):  # type: ignore
        from fabulae.features.create.schemas import OutlineContentOutput, SceneContentOutput

        # No chapters, scenes have chapter_id=None
        scenes = [
            SceneContentOutput(id="scene-01", chapter_id=None, title="S1", summary="Scene 1", beat_count=3),
            SceneContentOutput(id="scene-02", chapter_id=None, title="S2", summary="Scene 2", beat_count=3),
        ]
        output = OutlineContentOutput(chapters=[], scenes=scenes)
        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    from fabulae.features.create.pipelines.plot_first import generate_outline_content

    result = await generate_outline_content(
        idea="A test story",
        format="short-story",
        structure=structure,
        shape=None,
        llm_config=LLMConfig(),
        chapter_ids=chapter_ids,
        scene_ids=scene_ids,
    )

    # Should have no chapters
    assert len(result.chapters) == 0

    # Should have scenes with no chapter_id
    assert len(result.scenes) == 2
    assert all(sc.chapter_id is None for sc in result.scenes)


@pytest.mark.anyio
async def test_generate_outline_content_beat_counts_match(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test scene beat_count matches structure."""
    structure = OutlineStructure(
        num_chapters=1,
        scenes_per_chapter=[3],
        beats_per_scene=[2, 4, 3],  # Different beat counts
        total_scenes=3,
        total_beats=9,
    )

    chapter_ids = ["chapter-01"]
    scene_ids = ["scene-01", "scene-02", "scene-03"]

    # Mock run_stage
    async def mock_run_stage(**kwargs):  # type: ignore
        from fabulae.features.create.schemas import ChapterContentOutput, OutlineContentOutput, SceneContentOutput

        chapters = [ChapterContentOutput(id="chapter-01", title="Ch1", summary="Chapter 1")]
        scenes = [
            SceneContentOutput(id="scene-01", chapter_id="chapter-01", title="S1", summary="S1", beat_count=2),
            SceneContentOutput(id="scene-02", chapter_id="chapter-01", title="S2", summary="S2", beat_count=4),
            SceneContentOutput(id="scene-03", chapter_id="chapter-01", title="S3", summary="S3", beat_count=3),
        ]
        output = OutlineContentOutput(chapters=chapters, scenes=scenes)
        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    from fabulae.features.create.pipelines.plot_first import generate_outline_content

    result = await generate_outline_content(
        idea="A test story",
        format="short-story",
        structure=structure,
        shape=None,
        llm_config=LLMConfig(),
        chapter_ids=chapter_ids,
        scene_ids=scene_ids,
    )

    # Verify beat counts match structure
    assert result.scenes[0].beat_count == 2
    assert result.scenes[1].beat_count == 4
    assert result.scenes[2].beat_count == 3


@pytest.mark.anyio
async def test_generate_outline_content_mismatched_chapter_count_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test error when chapter_ids length doesn't match structure."""
    structure = OutlineStructure(
        num_chapters=3,
        scenes_per_chapter=[1, 1, 1],
        beats_per_scene=[3, 3, 3],
        total_scenes=3,
        total_beats=9,
    )

    chapter_ids = ["chapter-01", "chapter-02"]  # Only 2, expected 3
    scene_ids = ["scene-01", "scene-02", "scene-03"]

    from fabulae.features.create.pipelines.plot_first import generate_outline_content

    with pytest.raises(ValueError, match="Expected 3 chapter IDs, got 2"):
        await generate_outline_content(
            idea="A test story",
            format="novel",
            structure=structure,
            shape=None,
            llm_config=LLMConfig(),
            chapter_ids=chapter_ids,
            scene_ids=scene_ids,
        )


@pytest.mark.anyio
async def test_generate_outline_content_mismatched_scene_count_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test error when scene_ids length doesn't match structure."""
    structure = OutlineStructure(
        num_chapters=2,
        scenes_per_chapter=[2, 2],
        beats_per_scene=[3, 3, 3, 3],
        total_scenes=4,
        total_beats=12,
    )

    chapter_ids = ["chapter-01", "chapter-02"]
    scene_ids = ["scene-01", "scene-02", "scene-03"]  # Only 3, expected 4

    from fabulae.features.create.pipelines.plot_first import generate_outline_content

    with pytest.raises(ValueError, match="Expected 4 scene IDs, got 3"):
        await generate_outline_content(
            idea="A test story",
            format="novella",
            structure=structure,
            shape=None,
            llm_config=LLMConfig(),
            chapter_ids=chapter_ids,
            scene_ids=scene_ids,
        )


@pytest.mark.anyio
async def test_generate_outline_content_with_story_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test story shape is included in prompt context."""
    structure = OutlineStructure(
        num_chapters=1,
        scenes_per_chapter=[2],
        beats_per_scene=[3, 3],
        total_scenes=2,
        total_beats=6,
    )

    chapter_ids = ["chapter-01"]
    scene_ids = ["scene-01", "scene-02"]

    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test narrative shape",
    )

    captured_kwargs = None

    # Mock run_stage
    async def mock_run_stage(**kwargs):  # type: ignore
        from fabulae.features.create.schemas import ChapterContentOutput, OutlineContentOutput, SceneContentOutput

        nonlocal captured_kwargs
        captured_kwargs = kwargs

        chapters = [ChapterContentOutput(id="chapter-01", title="Ch1", summary="Chapter 1")]
        scenes = [
            SceneContentOutput(id="scene-01", chapter_id="chapter-01", title="S1", summary="S1", beat_count=3),
            SceneContentOutput(id="scene-02", chapter_id="chapter-01", title="S2", summary="S2", beat_count=3),
        ]
        output = OutlineContentOutput(chapters=chapters, scenes=scenes)
        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    from fabulae.features.create.pipelines.plot_first import generate_outline_content

    await generate_outline_content(
        idea="A test story",
        format="short-story",
        structure=structure,
        shape=shape,
        llm_config=LLMConfig(),
        chapter_ids=chapter_ids,
        scene_ids=scene_ids,
    )

    # Verify shape was included in prompt
    assert captured_kwargs is not None
    assert "Test Shape" in captured_kwargs["user_prompt"]
    assert "A test narrative shape" in captured_kwargs["user_prompt"]


# Tests for generate_characters_from_slots


@pytest.mark.anyio
async def test_generate_characters_from_slots_basic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test character generated for each required character slot."""
    # Create a shape with two character slots
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        character_slots=[
            CharacterSlot(slot="hero", needs="Brave protagonist who leads the quest", optional=False),
            CharacterSlot(slot="mentor", needs="Wise guide who provides counsel", optional=False),
        ],
    )

    # Mock run_stage to return predetermined outputs
    call_count = 0

    async def mock_run_stage(**kwargs):  # type: ignore
        nonlocal call_count
        call_count += 1

        # Return different outputs based on call count
        if call_count == 1:
            output = CharacterOutput(
                id="character-01",
                name="Aria Swift",
                role="protagonist",
                desire="save her village",
                need="learn to trust others",
                flaw="overly independent",
                secret="fears failure",
                traits=["brave", "determined"],
            )
        else:
            output = CharacterOutput(
                id="character-02",
                name="Elder Marcus",
                role="mentor",
                desire="pass on wisdom",
                need="let go of the past",
                flaw="haunted by regrets",
                secret="failed a previous hero",
                traits=["wise", "patient"],
            )

        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    # Call the function
    characters = await generate_characters_from_slots(
        idea="A hero's journey to save the realm",
        format="novel",
        shape=shape,
        character_ids=["character-01", "character-02"],
        slot_mapping={"hero": "character-01", "mentor": "character-02"},
        llm_config=LLMConfig(),
    )

    # Verify we got two characters
    assert len(characters) == 2

    # Verify first character
    assert characters[0].id == "character-01"
    assert characters[0].name == "Aria Swift"
    assert characters[0].role == "protagonist"
    assert characters[0].desire == "save her village"

    # Verify second character
    assert characters[1].id == "character-02"
    assert characters[1].name == "Elder Marcus"
    assert characters[1].role == "mentor"


@pytest.mark.anyio
async def test_generate_characters_from_slots_assigned_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test character has assigned ID (not generated)."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        character_slots=[
            CharacterSlot(slot="detective", needs="Clever investigator", optional=False),
        ],
    )

    # Mock run_stage to return output with correct ID
    async def mock_run_stage(**kwargs):  # type: ignore
        output = CharacterOutput(
            id="character-99",  # The assigned ID
            name="Detective Chen",
            role="investigator",
            desire="solve the case",
            need="learn to trust intuition",
            flaw="overanalyzes everything",
            secret="past mistake cost lives",
            traits=["clever", "methodical"],
        )
        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    # Call with specific assigned ID
    characters = await generate_characters_from_slots(
        idea="A mystery to solve",
        format="short-story",
        shape=shape,
        character_ids=["character-99"],
        slot_mapping={"detective": "character-99"},
        llm_config=LLMConfig(),
    )

    # Verify the ID matches what we assigned
    assert len(characters) == 1
    assert characters[0].id == "character-99"


@pytest.mark.anyio
async def test_generate_characters_from_slots_optional_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test optional slots only generated if in slot_mapping."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        character_slots=[
            CharacterSlot(slot="required-hero", needs="A required protagonist", optional=False),
            CharacterSlot(slot="optional-sidekick", needs="An optional companion", optional=True),
        ],
    )

    call_count = 0

    async def mock_run_stage(**kwargs):  # type: ignore
        nonlocal call_count
        call_count += 1
        output = CharacterOutput(
            id="character-01",
            name="Hero Name",
            role="protagonist",
            desire="quest",
            need="growth",
            flaw="flaw",
            secret="secret",
            traits=["trait"],
        )
        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    # Only map the required slot, skip the optional one
    characters = await generate_characters_from_slots(
        idea="A tale",
        format="novel",
        shape=shape,
        character_ids=["character-01"],
        slot_mapping={"required-hero": "character-01"},  # optional-sidekick not mapped
        llm_config=LLMConfig(),
    )

    # Should only have generated one character
    assert len(characters) == 1
    assert call_count == 1


@pytest.mark.anyio
async def test_generate_characters_from_slots_optional_include(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test optional slots generated when in slot_mapping."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        character_slots=[
            CharacterSlot(slot="required-hero", needs="A required protagonist", optional=False),
            CharacterSlot(slot="optional-sidekick", needs="An optional companion", optional=True),
        ],
    )

    call_count = 0

    async def mock_run_stage(**kwargs):  # type: ignore
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            output = CharacterOutput(id="character-01", name="Hero", role="protagonist")
        else:
            output = CharacterOutput(id="character-02", name="Sidekick", role="companion")
        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    # Map both slots
    characters = await generate_characters_from_slots(
        idea="A tale",
        format="novel",
        shape=shape,
        character_ids=["character-01", "character-02"],
        slot_mapping={"required-hero": "character-01", "optional-sidekick": "character-02"},
        llm_config=LLMConfig(),
    )

    # Should have generated both characters
    assert len(characters) == 2
    assert call_count == 2


@pytest.mark.anyio
async def test_generate_characters_from_slots_with_style(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test style guidance is passed to prompts."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        character_slots=[
            CharacterSlot(slot="warrior", needs="A fierce fighter", optional=False),
        ],
    )

    captured_kwargs = None

    async def mock_run_stage(**kwargs):  # type: ignore
        nonlocal captured_kwargs
        captured_kwargs = kwargs
        output = CharacterOutput(id="character-01", name="Warrior", role="fighter")
        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    style = StyleOutput(language="en", voice="epic", register="heroic")

    await generate_characters_from_slots(
        idea="A tale",
        format="novel",
        shape=shape,
        character_ids=["character-01"],
        slot_mapping={"warrior": "character-01"},
        llm_config=LLMConfig(),
        style=style,
    )

    # Verify style was used
    assert captured_kwargs is not None
    assert captured_kwargs["expected_language"] == "en"
    assert "epic" in captured_kwargs["system_prompt"]
    assert "heroic" in captured_kwargs["system_prompt"]


@pytest.mark.anyio
async def test_generate_characters_from_slots_missing_required_slot() -> None:
    """Test error when required slot not in mapping."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        character_slots=[
            CharacterSlot(slot="required-hero", needs="A required protagonist", optional=False),
        ],
    )

    with pytest.raises(ValueError, match="Required character slot 'required-hero' not found"):
        await generate_characters_from_slots(
            idea="A tale",
            format="novel",
            shape=shape,
            character_ids=["character-01"],
            slot_mapping={},  # Missing the required slot
            llm_config=LLMConfig(),
        )


@pytest.mark.anyio
async def test_generate_characters_from_slots_slot_needs_in_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test slot needs are included in character prompts."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        character_slots=[
            CharacterSlot(slot="trickster", needs="Cunning rogue who uses wit over strength", optional=False),
        ],
    )

    captured_kwargs = None

    async def mock_run_stage(**kwargs):  # type: ignore
        nonlocal captured_kwargs
        captured_kwargs = kwargs
        output = CharacterOutput(id="character-01", name="Rogue", role="trickster")
        return StageResult(output=output, warnings=[], attempts=1)

    monkeypatch.setattr("fabulae.features.create.pipelines.plot_first.run_stage", mock_run_stage)

    await generate_characters_from_slots(
        idea="A heist story",
        format="novel",
        shape=shape,
        character_ids=["character-01"],
        slot_mapping={"trickster": "character-01"},
        llm_config=LLMConfig(),
    )

    # Verify slot needs are in the prompt
    assert captured_kwargs is not None
    assert "trickster" in captured_kwargs["system_prompt"]
    assert "Cunning rogue who uses wit over strength" in captured_kwargs["system_prompt"]


# Tests for assign_required_beats_to_scenes


def test_assign_required_beats_to_scenes_all_beats_assigned() -> None:
    """Test all required beats are assigned."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        required_beats=[
            RequiredBeat(type="inciting-incident", description="Story begins", position="early"),
            RequiredBeat(type="midpoint", description="Major reversal", position="middle"),
            RequiredBeat(type="climax", description="Final confrontation", position="climax"),
        ],
    )

    scene_ids = ["scene-01", "scene-02", "scene-03", "scene-04", "scene-05"]
    rng = random.Random(42)

    assignments = assign_required_beats_to_scenes(shape, scene_ids, rng)

    # Should have one assignment per required beat
    assert len(assignments) == 3

    # All beat types should be present
    beat_types = {a.beat_type for a in assignments}
    assert beat_types == {"inciting-incident", "midpoint", "climax"}

    # All assignments should have valid scene IDs
    assigned_scene_ids = {a.scene_id for a in assignments}
    assert assigned_scene_ids.issubset(set(scene_ids))


def test_assign_required_beats_to_scenes_early_position() -> None:
    """Test 'early' beats go to early scenes (first 25%)."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        required_beats=[
            RequiredBeat(type="setup", description="Setup", position="early", flexibility="fixed"),
        ],
    )

    # 10 scenes: early should be 0-2 (first 25%)
    scene_ids = [f"scene-{i:02d}" for i in range(1, 11)]
    rng = random.Random(42)

    # Test multiple times to ensure it stays in early range
    for seed in range(10):
        rng = random.Random(seed)
        assignments = assign_required_beats_to_scenes(shape, scene_ids, rng)

        assert len(assignments) == 1
        # Early scenes are indices 0-2 (25% of 10 = 2.5, rounded to 2)
        early_scenes = {"scene-01", "scene-02"}
        assert assignments[0].scene_id in early_scenes


def test_assign_required_beats_to_scenes_middle_position() -> None:
    """Test 'middle' beats go to middle scenes (25-70%)."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        required_beats=[
            RequiredBeat(type="midpoint", description="Middle", position="middle", flexibility="fixed"),
        ],
    )

    # 10 scenes: middle should be 2-7 (25% to 70%)
    scene_ids = [f"scene-{i:02d}" for i in range(1, 11)]

    # Test multiple times to ensure it stays in middle range
    for seed in range(10):
        rng = random.Random(seed)
        assignments = assign_required_beats_to_scenes(shape, scene_ids, rng)

        assert len(assignments) == 1
        # Middle scenes are indices 2-6 (25% to 70% of 10)
        middle_scenes = {"scene-03", "scene-04", "scene-05", "scene-06", "scene-07"}
        assert assignments[0].scene_id in middle_scenes


def test_assign_required_beats_to_scenes_late_position() -> None:
    """Test 'late' beats go to late scenes (70-90%)."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        required_beats=[
            RequiredBeat(type="crisis", description="Crisis", position="late", flexibility="fixed"),
        ],
    )

    # 10 scenes: late should be 7-9 (70% to 90%)
    scene_ids = [f"scene-{i:02d}" for i in range(1, 11)]

    # Test multiple times to ensure it stays in late range
    for seed in range(10):
        rng = random.Random(seed)
        assignments = assign_required_beats_to_scenes(shape, scene_ids, rng)

        assert len(assignments) == 1
        # Late scenes are indices 7-8 (70% to 90% of 10)
        late_scenes = {"scene-08", "scene-09"}
        assert assignments[0].scene_id in late_scenes


def test_assign_required_beats_to_scenes_climax_position() -> None:
    """Test 'climax' beats go to final scenes (last 10%)."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        required_beats=[
            RequiredBeat(type="climax", description="Climax", position="climax", flexibility="fixed"),
        ],
    )

    # 10 scenes: climax should be 9-10 (last 10%)
    scene_ids = [f"scene-{i:02d}" for i in range(1, 11)]

    # Test multiple times to ensure it stays in climax range
    for seed in range(10):
        rng = random.Random(seed)
        assignments = assign_required_beats_to_scenes(shape, scene_ids, rng)

        assert len(assignments) == 1
        # Climax scenes are indices 9+ (last 10% of 10 = scene 10)
        climax_scenes = {"scene-10"}
        assert assignments[0].scene_id in climax_scenes


def test_assign_required_beats_to_scenes_anywhere_position() -> None:
    """Test 'anywhere' beats can go to any scene."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        required_beats=[
            RequiredBeat(type="revelation", description="Reveal", position="anywhere"),
        ],
    )

    scene_ids = [f"scene-{i:02d}" for i in range(1, 11)]
    rng = random.Random(42)

    assignments = assign_required_beats_to_scenes(shape, scene_ids, rng)

    assert len(assignments) == 1
    # Can be any scene
    assert assignments[0].scene_id in set(scene_ids)


def test_assign_required_beats_to_scenes_seeded_reproducibility() -> None:
    """Test with seeded RNG for reproducibility."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        required_beats=[
            RequiredBeat(type="beat-1", description="B1", position="early"),
            RequiredBeat(type="beat-2", description="B2", position="middle"),
            RequiredBeat(type="beat-3", description="B3", position="late"),
        ],
    )

    scene_ids = [f"scene-{i:02d}" for i in range(1, 11)]

    # Same seed should produce identical results
    rng1 = random.Random(12345)
    assignments1 = assign_required_beats_to_scenes(shape, scene_ids, rng1)

    rng2 = random.Random(12345)
    assignments2 = assign_required_beats_to_scenes(shape, scene_ids, rng2)

    assert len(assignments1) == len(assignments2)
    for a1, a2 in zip(assignments1, assignments2, strict=True):
        assert a1.beat_type == a2.beat_type
        assert a1.scene_id == a2.scene_id


def test_assign_required_beats_to_scenes_flexible_wider_range() -> None:
    """Test flexibility affects range (flexible has wider range)."""
    # With 10 scenes:
    # - Fixed early: 0-2
    # - Flexible early: allows ±10% (±1 scene) = could be 0-3 or even wider

    shape_fixed = StoryShape(
        id="test-shape-fixed",
        name="Test Shape Fixed",
        description="Fixed flexibility",
        required_beats=[
            RequiredBeat(type="setup", description="Setup", position="early", flexibility="fixed"),
        ],
    )

    shape_flexible = StoryShape(
        id="test-shape-flexible",
        name="Test Shape Flexible",
        description="Flexible flexibility",
        required_beats=[
            RequiredBeat(type="setup", description="Setup", position="early", flexibility="flexible"),
        ],
    )

    scene_ids = [f"scene-{i:02d}" for i in range(1, 11)]

    # Collect assignments from multiple runs to see range
    fixed_scenes = set()
    flexible_scenes = set()

    for seed in range(100):
        rng = random.Random(seed)
        assignments = assign_required_beats_to_scenes(shape_fixed, scene_ids, rng)
        fixed_scenes.add(assignments[0].scene_id)

        rng = random.Random(seed)
        assignments = assign_required_beats_to_scenes(shape_flexible, scene_ids, rng)
        flexible_scenes.add(assignments[0].scene_id)

    # Flexible should potentially include more scenes than fixed
    # At minimum, flexible should include all scenes that fixed includes
    # (This is a statistical test, so it might not always pass, but with 100 runs it should)
    assert len(flexible_scenes) >= len(fixed_scenes) or flexible_scenes == fixed_scenes


def test_assign_required_beats_to_scenes_very_flexible_widest_range() -> None:
    """Test very-flexible has wider range than flexible."""
    shape_very_flexible = StoryShape(
        id="test-shape-very-flexible",
        name="Test Shape Very Flexible",
        description="Very flexible",
        required_beats=[
            RequiredBeat(type="setup", description="Setup", position="early", flexibility="very-flexible"),
        ],
    )

    scene_ids = [f"scene-{i:02d}" for i in range(1, 11)]

    # Collect assignments to see range
    very_flexible_scenes = set()

    for seed in range(100):
        rng = random.Random(seed)
        assignments = assign_required_beats_to_scenes(shape_very_flexible, scene_ids, rng)
        very_flexible_scenes.add(assignments[0].scene_id)

    # Very flexible should allow placement in multiple scenes (more than just early)
    assert len(very_flexible_scenes) >= 2


def test_assign_required_beats_to_scenes_empty_scene_list() -> None:
    """Test error with empty scene list."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        required_beats=[
            RequiredBeat(type="beat", description="Beat"),
        ],
    )

    with pytest.raises(ValueError, match="Cannot assign beats to empty scene list"):
        assign_required_beats_to_scenes(shape, [], None)


def test_assign_required_beats_to_scenes_no_required_beats() -> None:
    """Test returns empty list when no required beats."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        required_beats=[],  # No beats
    )

    scene_ids = ["scene-01", "scene-02", "scene-03"]

    assignments = assign_required_beats_to_scenes(shape, scene_ids, None)
    assert assignments == []


def test_assign_required_beats_to_scenes_single_scene() -> None:
    """Test with single scene (all beats go to that scene)."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        required_beats=[
            RequiredBeat(type="early-beat", description="Early", position="early"),
            RequiredBeat(type="middle-beat", description="Middle", position="middle"),
            RequiredBeat(type="climax-beat", description="Climax", position="climax"),
        ],
    )

    scene_ids = ["scene-01"]  # Only one scene

    rng = random.Random(42)
    assignments = assign_required_beats_to_scenes(shape, scene_ids, rng)

    # All beats should be assigned to the only scene
    assert len(assignments) == 3
    assert all(a.scene_id == "scene-01" for a in assignments)


def test_assign_required_beats_to_scenes_multiple_beats_same_position() -> None:
    """Test multiple beats with same position."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        required_beats=[
            RequiredBeat(type="setup-1", description="Setup 1", position="early", flexibility="fixed"),
            RequiredBeat(type="setup-2", description="Setup 2", position="early", flexibility="fixed"),
            RequiredBeat(type="setup-3", description="Setup 3", position="early", flexibility="fixed"),
        ],
    )

    scene_ids = [f"scene-{i:02d}" for i in range(1, 11)]
    rng = random.Random(42)

    assignments = assign_required_beats_to_scenes(shape, scene_ids, rng)

    # Should have 3 assignments
    assert len(assignments) == 3

    # All should be in early scenes (first 25% with fixed flexibility)
    early_scenes = {"scene-01", "scene-02"}
    for assignment in assignments:
        assert assignment.scene_id in early_scenes


def test_assign_required_beats_to_scenes_dataclass_structure() -> None:
    """Test BeatAssignment dataclass has correct structure."""
    shape = StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test shape",
        required_beats=[
            RequiredBeat(type="test-beat", description="Test"),
        ],
    )

    scene_ids = ["scene-01", "scene-02"]
    rng = random.Random(42)

    assignments = assign_required_beats_to_scenes(shape, scene_ids, rng)

    assert len(assignments) == 1
    assignment = assignments[0]

    # Check fields
    assert hasattr(assignment, "beat_type")
    assert hasattr(assignment, "scene_id")
    assert isinstance(assignment.beat_type, str)
    assert isinstance(assignment.scene_id, str)
    assert assignment.beat_type == "test-beat"
    assert assignment.scene_id in scene_ids


def test_assign_required_beats_to_scenes_import_beat_assignment() -> None:
    """Test BeatAssignment can be imported."""

    # Create instance
    assignment = BeatAssignment(beat_type="test-beat", scene_id="scene-01")
    assert assignment.beat_type == "test-beat"
    assert assignment.scene_id == "scene-01"


# Tests for build_beat_templates_with_variation


def test_build_beat_templates_with_variation_basic() -> None:
    """Test basic beat template construction without variation."""

    scene_ids = ["scene-01", "scene-02", "scene-03"]
    beats_per_scene = [3, 4, 3]
    beat_assignments: list[BeatAssignment] = []
    rng = random.Random(42)

    templates = build_beat_templates_with_variation(
        scene_ids=scene_ids,
        beats_per_scene=beats_per_scene,
        beat_assignments=beat_assignments,
        scene_variations=None,
        rng=rng,
    )

    # Should have one template per scene
    assert len(templates) == 3
    assert "scene-01" in templates
    assert "scene-02" in templates
    assert "scene-03" in templates

    # Check beat counts match
    assert templates["scene-01"].beat_count == 3
    assert templates["scene-02"].beat_count == 4
    assert templates["scene-03"].beat_count == 3

    # Check all beats are filled with filler beats
    assert len(templates["scene-01"].beats) == 3
    assert len(templates["scene-02"].beats) == 4
    assert len(templates["scene-03"].beats) == 3

    # All beats should be non-required (filler)
    assert all(not beat.required for beat in templates["scene-01"].beats)


def test_build_beat_templates_with_variation_required_beats() -> None:
    """Test required beats appear in templates at correct scenes."""

    scene_ids = ["scene-01", "scene-02", "scene-03"]
    beats_per_scene = [4, 4, 4]

    # Assign required beats to specific scenes
    beat_assignments = [
        BeatAssignment(beat_type="inciting-incident", scene_id="scene-01"),
        BeatAssignment(beat_type="midpoint", scene_id="scene-02"),
        BeatAssignment(beat_type="climax", scene_id="scene-03"),
    ]

    rng = random.Random(42)

    templates = build_beat_templates_with_variation(
        scene_ids=scene_ids,
        beats_per_scene=beats_per_scene,
        beat_assignments=beat_assignments,
        scene_variations=None,
        rng=rng,
    )

    # Check that required beats appear in their assigned scenes
    scene_01_required = [b for b in templates["scene-01"].beats if b.required]
    scene_02_required = [b for b in templates["scene-02"].beats if b.required]
    scene_03_required = [b for b in templates["scene-03"].beats if b.required]

    assert len(scene_01_required) == 1
    assert scene_01_required[0].kind == "inciting-incident"
    assert scene_01_required[0].plot_pattern_beat == "inciting-incident"

    assert len(scene_02_required) == 1
    assert scene_02_required[0].kind == "midpoint"

    assert len(scene_03_required) == 1
    assert scene_03_required[0].kind == "climax"


def test_build_beat_templates_with_variation_filler_fills_remaining() -> None:
    """Test filler beats fill remaining slots after required beats."""

    scene_ids = ["scene-01"]
    beats_per_scene = [5]

    # One required beat, so 4 should be filler
    beat_assignments = [
        BeatAssignment(beat_type="required-beat", scene_id="scene-01"),
    ]

    rng = random.Random(42)

    templates = build_beat_templates_with_variation(
        scene_ids=scene_ids,
        beats_per_scene=beats_per_scene,
        beat_assignments=beat_assignments,
        scene_variations=None,
        rng=rng,
    )

    # Total beats should be 5
    assert len(templates["scene-01"].beats) == 5

    # 1 required, 4 filler
    required_beats = [b for b in templates["scene-01"].beats if b.required]
    filler_beats = [b for b in templates["scene-01"].beats if not b.required]

    assert len(required_beats) == 1
    assert len(filler_beats) == 4


def test_build_beat_templates_with_variation_complications_included() -> None:
    """Test complications included where flagged in scene_variations."""
    from fabulae.features.create.variation import SceneVariation

    scene_ids = ["scene-01", "scene-02"]
    beats_per_scene = [4, 4]
    beat_assignments: list[BeatAssignment] = []

    # scene-01 has complication, scene-02 does not
    scene_variations = [
        SceneVariation(
            scene_id="scene-01",
            position="early",
            has_complication=True,
            complication_type="obstacle",
            has_character_moment=False,
            filler_beats=["setup", "bridge"],
        ),
        SceneVariation(
            scene_id="scene-02",
            position="middle",
            has_complication=False,
            has_character_moment=False,
            filler_beats=["escalation", "turn"],
        ),
    ]

    rng = random.Random(42)

    templates = build_beat_templates_with_variation(
        scene_ids=scene_ids,
        beats_per_scene=beats_per_scene,
        beat_assignments=beat_assignments,
        scene_variations=scene_variations,
        rng=rng,
    )

    # scene-01 should have a complication beat
    scene_01_complication = [b for b in templates["scene-01"].beats if b.kind == "complication"]
    assert len(scene_01_complication) == 1
    assert scene_01_complication[0].notes == "complication: obstacle"

    # scene-02 should NOT have a complication beat
    scene_02_complication = [b for b in templates["scene-02"].beats if b.kind == "complication"]
    assert len(scene_02_complication) == 0


def test_build_beat_templates_with_variation_character_moments_included() -> None:
    """Test character moments included where flagged in scene_variations."""
    from fabulae.features.create.variation import SceneVariation

    scene_ids = ["scene-01", "scene-02"]
    beats_per_scene = [4, 4]
    beat_assignments: list[BeatAssignment] = []

    # scene-01 has character moment, scene-02 does not
    scene_variations = [
        SceneVariation(
            scene_id="scene-01",
            position="early",
            has_complication=False,
            has_character_moment=True,
            character_focus="character-01",
            filler_beats=["setup", "bridge"],
        ),
        SceneVariation(
            scene_id="scene-02",
            position="middle",
            has_complication=False,
            has_character_moment=False,
            filler_beats=["escalation", "turn"],
        ),
    ]

    rng = random.Random(42)

    templates = build_beat_templates_with_variation(
        scene_ids=scene_ids,
        beats_per_scene=beats_per_scene,
        beat_assignments=beat_assignments,
        scene_variations=scene_variations,
        rng=rng,
    )

    # scene-01 should have a character-moment beat
    scene_01_char_moment = [b for b in templates["scene-01"].beats if b.kind == "character-moment"]
    assert len(scene_01_char_moment) == 1
    assert scene_01_char_moment[0].notes == "focus: character-01"

    # scene-02 should NOT have a character-moment beat
    scene_02_char_moment = [b for b in templates["scene-02"].beats if b.kind == "character-moment"]
    assert len(scene_02_char_moment) == 0


def test_build_beat_templates_with_variation_total_beat_count_matches() -> None:
    """Test total beat count matches beats_per_scene allocation."""
    from fabulae.features.create.variation import SceneVariation

    scene_ids = ["scene-01", "scene-02", "scene-03"]
    beats_per_scene = [3, 5, 4]

    beat_assignments = [
        BeatAssignment(beat_type="setup", scene_id="scene-01"),
    ]

    scene_variations = [
        SceneVariation(
            scene_id="scene-01",
            position="early",
            has_complication=True,
            complication_type="obstacle",
            has_character_moment=False,
            filler_beats=["setup"],
        ),
        SceneVariation(
            scene_id="scene-02",
            position="middle",
            has_complication=False,
            has_character_moment=True,
            character_focus="character-02",
            filler_beats=["escalation"],
        ),
        SceneVariation(
            scene_id="scene-03",
            position="late",
            has_complication=True,
            complication_type="revelation",
            has_character_moment=True,
            character_focus="character-01",
            filler_beats=["turn"],
        ),
    ]

    rng = random.Random(42)

    templates = build_beat_templates_with_variation(
        scene_ids=scene_ids,
        beats_per_scene=beats_per_scene,
        beat_assignments=beat_assignments,
        scene_variations=scene_variations,
        rng=rng,
    )

    # Verify beat counts
    assert len(templates["scene-01"].beats) == 3
    assert len(templates["scene-02"].beats) == 5
    assert len(templates["scene-03"].beats) == 4

    # Verify total matches sum
    total_beats = sum(len(t.beats) for t in templates.values())
    assert total_beats == sum(beats_per_scene)


def test_build_beat_templates_with_variation_seeded_reproducibility() -> None:
    """Test with seeded RNG for reproducibility."""

    scene_ids = ["scene-01", "scene-02"]
    beats_per_scene = [4, 4]
    beat_assignments: list[BeatAssignment] = []

    # First run
    rng1 = random.Random(12345)
    templates1 = build_beat_templates_with_variation(
        scene_ids=scene_ids,
        beats_per_scene=beats_per_scene,
        beat_assignments=beat_assignments,
        scene_variations=None,
        rng=rng1,
    )

    # Second run with same seed
    rng2 = random.Random(12345)
    templates2 = build_beat_templates_with_variation(
        scene_ids=scene_ids,
        beats_per_scene=beats_per_scene,
        beat_assignments=beat_assignments,
        scene_variations=None,
        rng=rng2,
    )

    # Should produce identical results
    for scene_id in scene_ids:
        beats1 = templates1[scene_id].beats
        beats2 = templates2[scene_id].beats
        assert len(beats1) == len(beats2)
        for b1, b2 in zip(beats1, beats2, strict=True):
            assert b1.kind == b2.kind
            assert b1.required == b2.required


def test_build_beat_templates_with_variation_without_scene_variations() -> None:
    """Test without scene_variations (should still work with just required beats + random filler)."""

    scene_ids = ["scene-01", "scene-02"]
    beats_per_scene = [5, 5]

    beat_assignments = [
        BeatAssignment(beat_type="opening", scene_id="scene-01"),
        BeatAssignment(beat_type="climax", scene_id="scene-02"),
    ]

    rng = random.Random(42)

    templates = build_beat_templates_with_variation(
        scene_ids=scene_ids,
        beats_per_scene=beats_per_scene,
        beat_assignments=beat_assignments,
        scene_variations=None,  # No variations
        rng=rng,
    )

    # Should still work
    assert len(templates) == 2

    # Required beats should be present
    scene_01_required = [b for b in templates["scene-01"].beats if b.required]
    scene_02_required = [b for b in templates["scene-02"].beats if b.required]
    assert len(scene_01_required) == 1
    assert len(scene_02_required) == 1

    # Rest should be filler
    scene_01_filler = [b for b in templates["scene-01"].beats if not b.required]
    scene_02_filler = [b for b in templates["scene-02"].beats if not b.required]
    assert len(scene_01_filler) == 4
    assert len(scene_02_filler) == 4


def test_build_beat_templates_with_variation_uses_variation_filler_beats() -> None:
    """Test uses scene_variation.filler_beats when provided."""
    from fabulae.features.create.variation import SceneVariation

    scene_ids = ["scene-01"]
    beats_per_scene = [3]
    beat_assignments: list[BeatAssignment] = []

    # Provide specific filler beats
    scene_variations = [
        SceneVariation(
            scene_id="scene-01",
            position="early",
            has_complication=False,
            has_character_moment=False,
            filler_beats=["custom-beat-1", "custom-beat-2"],
        ),
    ]

    rng = random.Random(42)

    templates = build_beat_templates_with_variation(
        scene_ids=scene_ids,
        beats_per_scene=beats_per_scene,
        beat_assignments=beat_assignments,
        scene_variations=scene_variations,
        rng=rng,
    )

    # All beats should be from the custom filler pool
    beat_kinds = [b.kind for b in templates["scene-01"].beats]
    assert all(kind in ["custom-beat-1", "custom-beat-2"] for kind in beat_kinds)


def test_build_beat_templates_with_variation_uses_default_filler_when_no_variation() -> None:
    """Test uses DEFAULT_FILLER_BEAT_KINDS when no variation provided."""
    from fabulae.features.create.pipelines.plot_first import (
        DEFAULT_FILLER_BEAT_KINDS,
    )

    scene_ids = ["scene-01"]
    beats_per_scene = [3]
    beat_assignments: list[BeatAssignment] = []

    rng = random.Random(42)

    templates = build_beat_templates_with_variation(
        scene_ids=scene_ids,
        beats_per_scene=beats_per_scene,
        beat_assignments=beat_assignments,
        scene_variations=None,
        rng=rng,
    )

    # All beats should be from DEFAULT_FILLER_BEAT_KINDS
    beat_kinds = [b.kind for b in templates["scene-01"].beats]
    assert all(kind in DEFAULT_FILLER_BEAT_KINDS for kind in beat_kinds)


def test_build_beat_templates_with_variation_multiple_required_beats_spread() -> None:
    """Test multiple required beats are spread across the template."""

    scene_ids = ["scene-01"]
    beats_per_scene = [10]  # Large scene

    # Three required beats
    beat_assignments = [
        BeatAssignment(beat_type="beat-1", scene_id="scene-01"),
        BeatAssignment(beat_type="beat-2", scene_id="scene-01"),
        BeatAssignment(beat_type="beat-3", scene_id="scene-01"),
    ]

    rng = random.Random(42)

    templates = build_beat_templates_with_variation(
        scene_ids=scene_ids,
        beats_per_scene=beats_per_scene,
        beat_assignments=beat_assignments,
        scene_variations=None,
        rng=rng,
    )

    beats = templates["scene-01"].beats
    required_beat_indices = [i for i, b in enumerate(beats) if b.required]

    # Should have 3 required beats
    assert len(required_beat_indices) == 3

    # They should be spread out (not all clustered together)
    # Check that they're not all adjacent
    gaps = [required_beat_indices[i + 1] - required_beat_indices[i] for i in range(len(required_beat_indices) - 1)]
    assert any(gap > 1 for gap in gaps), "Required beats should be spread out"


def test_build_beat_templates_with_variation_mismatched_lengths_raises() -> None:
    """Test error when scene_ids and beats_per_scene have different lengths."""

    scene_ids = ["scene-01", "scene-02", "scene-03"]
    beats_per_scene = [4, 4]  # Only 2, expected 3

    with pytest.raises(ValueError, match="scene_ids and beats_per_scene must have same length"):
        build_beat_templates_with_variation(
            scene_ids=scene_ids,
            beats_per_scene=beats_per_scene,
            beat_assignments=[],
            scene_variations=None,
            rng=None,
        )


def test_build_beat_templates_with_variation_combined_variations() -> None:
    """Test scene with both complication and character moment."""
    from fabulae.features.create.variation import SceneVariation

    scene_ids = ["scene-01"]
    beats_per_scene = [6]
    beat_assignments = [
        BeatAssignment(beat_type="required-beat", scene_id="scene-01"),
    ]

    scene_variations = [
        SceneVariation(
            scene_id="scene-01",
            position="middle",
            has_complication=True,
            complication_type="betrayal",
            has_character_moment=True,
            character_focus="character-03",
            filler_beats=["setup"],
        ),
    ]

    rng = random.Random(42)

    templates = build_beat_templates_with_variation(
        scene_ids=scene_ids,
        beats_per_scene=beats_per_scene,
        beat_assignments=beat_assignments,
        scene_variations=scene_variations,
        rng=rng,
    )

    beats = templates["scene-01"].beats

    # Should have: 1 required + 1 complication + 1 character-moment + 3 filler = 6 total
    assert len(beats) == 6

    required_beats = [b for b in beats if b.required]
    complication_beats = [b for b in beats if b.kind == "complication"]
    char_moment_beats = [b for b in beats if b.kind == "character-moment"]
    filler_beats = [b for b in beats if not b.required and b.kind not in ["complication", "character-moment"]]

    assert len(required_beats) == 1
    assert len(complication_beats) == 1
    assert len(char_moment_beats) == 1
    assert len(filler_beats) == 3


def test_build_beat_templates_with_variation_empty_scene_list() -> None:
    """Test with empty scene list returns empty dict."""

    scene_ids: list[str] = []
    beats_per_scene: list[int] = []
    beat_assignments: list[BeatAssignment] = []

    templates = build_beat_templates_with_variation(
        scene_ids=scene_ids,
        beats_per_scene=beats_per_scene,
        beat_assignments=beat_assignments,
        scene_variations=None,
        rng=None,
    )

    assert templates == {}


def test_build_beat_templates_with_variation_single_beat_scene() -> None:
    """Test scene with only one beat slot."""

    scene_ids = ["scene-01"]
    beats_per_scene = [1]

    beat_assignments = [
        BeatAssignment(beat_type="single-beat", scene_id="scene-01"),
    ]

    rng = random.Random(42)

    templates = build_beat_templates_with_variation(
        scene_ids=scene_ids,
        beats_per_scene=beats_per_scene,
        beat_assignments=beat_assignments,
        scene_variations=None,
        rng=rng,
    )

    # Should have exactly one beat, which is the required beat
    assert len(templates["scene-01"].beats) == 1
    assert templates["scene-01"].beats[0].required is True
    assert templates["scene-01"].beats[0].kind == "single-beat"
