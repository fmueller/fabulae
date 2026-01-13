"""Tests for build_enrichment_prompt function."""

from __future__ import annotations

from fabulae.features.create.prompts import build_enrichment_prompt
from fabulae.features.create.schemas import (
    ChapterContentOutput,
    OutlineContentOutput,
    SceneContentOutput,
    StyleOutput,
)
from fabulae.features.create.variation import (
    ProjectVariation,
    SceneVariation,
    VariationConfig,
)
from fabulae.models import Character, StoryShape, World, WorldFact


def _make_style() -> StyleOutput:
    """Create a minimal StyleOutput for testing."""
    return StyleOutput(
        language="en",
        pov="third",
        tense="past",
        voice="observant",
    )


def _make_characters() -> list[Character]:
    """Create test characters."""
    return [
        Character(
            id="character-01",
            name="Alice",
            role="protagonist",
            traits=["curious", "brave"],
        ),
        Character(
            id="character-02",
            name="Bob",
            role="antagonist",
            traits=["cunning", "cold"],
        ),
    ]


def _make_world() -> World:
    """Create a test world."""
    return World(
        setting="Coastal research town",
        time_period="near future",
        tone="moody",
        motifs=["fog", "radio static"],
        facts=[
            WorldFact(
                id="location-01",
                type="location",
                name="Harbor Lab",
                facts=["restricted access", "scent of ozone"],
            ),
            WorldFact(
                id="location-02",
                type="location",
                name="Downtown Cafe",
                facts=["popular hangout", "old jukebox"],
            ),
        ],
    )


def _make_outline() -> OutlineContentOutput:
    """Create a test outline."""
    return OutlineContentOutput(
        chapters=[
            ChapterContentOutput(id="chapter-01", title="Opening", summary="The story begins."),
            ChapterContentOutput(id="chapter-02", title="Rising", summary="Tension builds."),
        ],
        scenes=[
            SceneContentOutput(
                id="scene-01",
                chapter_id="chapter-01",
                title="Discovery",
                summary="Alice finds a clue.",
                beat_count=3,
            ),
            SceneContentOutput(
                id="scene-02",
                chapter_id="chapter-01",
                title="Confrontation",
                summary="Alice meets Bob.",
                beat_count=3,
            ),
            SceneContentOutput(
                id="scene-03",
                chapter_id="chapter-02",
                title="Investigation",
                summary="Alice investigates.",
                beat_count=4,
            ),
        ],
    )


def _make_variation() -> ProjectVariation:
    """Create a test variation with subplot seeds."""
    config = VariationConfig(seed=42)
    scene_variations = [
        SceneVariation(
            scene_id="scene-01",
            position="early",
            has_complication=False,
            subplot_seed="romance",
        ),
        SceneVariation(
            scene_id="scene-02",
            position="middle",
            has_complication=True,
            complication_type="betrayal",
        ),
    ]
    return ProjectVariation(
        scene_variations=scene_variations,
        subplot_seeds=["romance", "rivalry"],
        config=config,
    )


def _make_story_shape() -> StoryShape:
    """Create a test story shape."""
    return StoryShape(
        id="mystery-investigation",
        name="Mystery Investigation",
        description="A detective uncovers a mystery.",
        themes=["truth", "deception"],
        motifs=["shadows", "clues"],
        tone="noir",
    )


class TestBuildEnrichmentPromptIncludesIdea:
    """Test that the prompt includes the original idea."""

    def test_idea_is_present(self) -> None:
        idea = "A scientist discovers a hidden signal from space."
        prompt = build_enrichment_prompt(
            idea=idea,
            format_name="novel",
            style=_make_style(),
            characters=_make_characters(),
            world=_make_world(),
            outline=_make_outline(),
        )

        assert idea in prompt


class TestBuildEnrichmentPromptIncludesCharacters:
    """Test that the prompt includes existing characters."""

    def test_characters_are_present(self) -> None:
        characters = _make_characters()
        prompt = build_enrichment_prompt(
            idea="Test idea",
            format_name="novel",
            style=_make_style(),
            characters=characters,
            world=_make_world(),
            outline=_make_outline(),
        )

        assert "Alice" in prompt
        assert "Bob" in prompt
        assert "character-01" in prompt
        assert "character-02" in prompt
        assert "protagonist" in prompt
        assert "antagonist" in prompt

    def test_empty_characters_shows_none(self) -> None:
        prompt = build_enrichment_prompt(
            idea="Test idea",
            format_name="novel",
            style=_make_style(),
            characters=[],
            world=_make_world(),
            outline=_make_outline(),
        )

        assert "None yet." in prompt


class TestBuildEnrichmentPromptIncludesWorld:
    """Test that the prompt includes existing world facts."""

    def test_world_is_present(self) -> None:
        world = _make_world()
        prompt = build_enrichment_prompt(
            idea="Test idea",
            format_name="novel",
            style=_make_style(),
            characters=_make_characters(),
            world=world,
            outline=_make_outline(),
        )

        assert "Harbor Lab" in prompt
        assert "Downtown Cafe" in prompt
        assert "location-01" in prompt
        assert "Coastal research town" in prompt


class TestBuildEnrichmentPromptIncludesOutline:
    """Test that the prompt includes outline scenes."""

    def test_outline_scenes_are_present(self) -> None:
        outline = _make_outline()
        prompt = build_enrichment_prompt(
            idea="Test idea",
            format_name="novel",
            style=_make_style(),
            characters=_make_characters(),
            world=_make_world(),
            outline=outline,
        )

        assert "scene-01" in prompt
        assert "scene-02" in prompt
        assert "scene-03" in prompt
        assert "chapter-01" in prompt
        assert "chapter-02" in prompt
        assert "Discovery" in prompt
        assert "Confrontation" in prompt


class TestBuildEnrichmentPromptIncludesVariation:
    """Test that the prompt includes variation subplot seeds when provided."""

    def test_subplot_seeds_are_present(self) -> None:
        variation = _make_variation()
        prompt = build_enrichment_prompt(
            idea="Test idea",
            format_name="novel",
            style=_make_style(),
            characters=_make_characters(),
            world=_make_world(),
            outline=_make_outline(),
            variation=variation,
        )

        assert "romance" in prompt
        assert "rivalry" in prompt
        assert "Subplot Seeds from Variation" in prompt
        assert "subplot additions" in prompt.lower()

    def test_no_variation_no_subplot_section(self) -> None:
        prompt = build_enrichment_prompt(
            idea="Test idea",
            format_name="novel",
            style=_make_style(),
            characters=_make_characters(),
            world=_make_world(),
            outline=_make_outline(),
            variation=None,
        )

        assert "Subplot Seeds from Variation" not in prompt

    def test_empty_subplot_seeds_no_section(self) -> None:
        config = VariationConfig(seed=42)
        variation = ProjectVariation(
            scene_variations=[],
            subplot_seeds=[],
            config=config,
        )
        prompt = build_enrichment_prompt(
            idea="Test idea",
            format_name="novel",
            style=_make_style(),
            characters=_make_characters(),
            world=_make_world(),
            outline=_make_outline(),
            variation=variation,
        )

        assert "Subplot Seeds from Variation" not in prompt


class TestBuildEnrichmentPromptIncludesSchema:
    """Test that the prompt includes the EnrichmentOutput schema."""

    def test_schema_is_present(self) -> None:
        prompt = build_enrichment_prompt(
            idea="Test idea",
            format_name="novel",
            style=_make_style(),
            characters=_make_characters(),
            world=_make_world(),
            outline=_make_outline(),
        )

        assert "new_characters" in prompt
        assert "new_locations" in prompt
        assert "new_world_facts" in prompt
        assert "subplot_additions" in prompt
        assert "foreshadowing_elements" in prompt
        assert "setup_scene" in prompt
        assert "payoff_scene" in prompt


class TestBuildEnrichmentPromptConstraints:
    """Test that the prompt includes proper constraints."""

    def test_constraints_are_present(self) -> None:
        prompt = build_enrichment_prompt(
            idea="Test idea",
            format_name="novel",
            style=_make_style(),
            characters=_make_characters(),
            world=_make_world(),
            outline=_make_outline(),
        )

        assert "Do NOT change" in prompt
        assert "valid JSON only" in prompt
        assert "unique IDs" in prompt


class TestBuildEnrichmentPromptWithShape:
    """Test that the prompt includes story shape when provided."""

    def test_shape_is_present(self) -> None:
        shape = _make_story_shape()
        prompt = build_enrichment_prompt(
            idea="Test idea",
            format_name="novel",
            style=_make_style(),
            characters=_make_characters(),
            world=_make_world(),
            outline=_make_outline(),
            shape=shape,
        )

        assert "mystery-investigation" in prompt
        assert "Mystery Investigation" in prompt
        assert "noir" in prompt
        assert "Story Shape Guidance" in prompt
