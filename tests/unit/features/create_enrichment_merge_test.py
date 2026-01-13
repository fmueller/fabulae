"""Tests for enrichment merge functions."""

from __future__ import annotations

from fabulae.features.create.enrichment import (
    merge_enrichment_characters,
    merge_enrichment_plot,
    merge_enrichment_world,
)
from fabulae.features.create.schemas import (
    ChapterContentOutput,
    CharacterOutput,
    EnrichmentOutput,
    ForeshadowingElement,
    OutlineContentOutput,
    SceneContentOutput,
    SubplotAddition,
    WorldFactOutput,
)
from fabulae.models import Character, World, WorldFact


def test_merge_enrichment_characters_adds_new_characters_with_correct_ids() -> None:
    """Test that new characters are added with sequential IDs."""
    existing = [
        Character(id="character-01", name="Alice"),
        Character(id="character-02", name="Bob"),
    ]

    enrichment = EnrichmentOutput(
        new_characters=[
            CharacterOutput(
                id="temp-char-1",
                name="Charlie",
                role="sidekick",
                desire="adventure",
            ),
            CharacterOutput(
                id="temp-char-2",
                name="Diana",
                role="mentor",
                need="redemption",
            ),
        ]
    )

    merged, id_mapping = merge_enrichment_characters(existing, enrichment, next_character_index=3)

    assert len(merged) == 4
    assert merged[0].id == "character-01"
    assert merged[1].id == "character-02"
    assert merged[2].id == "character-03"
    assert merged[2].name == "Charlie"
    assert merged[2].role == "sidekick"
    assert merged[2].desire == "adventure"
    assert merged[3].id == "character-04"
    assert merged[3].name == "Diana"
    assert merged[3].role == "mentor"
    assert merged[3].need == "redemption"

    assert id_mapping == {
        "temp-char-1": "character-03",
        "temp-char-2": "character-04",
    }


def test_merge_enrichment_characters_preserves_existing_characters() -> None:
    """Test that existing characters are unchanged."""
    existing = [
        Character(id="character-01", name="Alice", role="protagonist", desire="freedom"),
        Character(id="character-02", name="Bob", flaw="pride"),
    ]

    enrichment = EnrichmentOutput(
        new_characters=[
            CharacterOutput(id="temp-char-1", name="Charlie"),
        ]
    )

    merged, _ = merge_enrichment_characters(existing, enrichment, next_character_index=3)

    # Check that first two characters are exact copies
    assert merged[0] == existing[0]
    assert merged[1] == existing[1]
    assert merged[0].id == "character-01"
    assert merged[0].name == "Alice"
    assert merged[0].role == "protagonist"
    assert merged[0].desire == "freedom"


def test_merge_enrichment_characters_returns_correct_id_mapping() -> None:
    """Test that the ID mapping is correct for reference updates."""
    existing: list[Character] = []

    enrichment = EnrichmentOutput(
        new_characters=[
            CharacterOutput(id="hero", name="Hero"),
            CharacterOutput(id="villain", name="Villain"),
            CharacterOutput(id="mentor", name="Mentor"),
        ]
    )

    _, id_mapping = merge_enrichment_characters(existing, enrichment, next_character_index=1)

    assert id_mapping == {
        "hero": "character-01",
        "villain": "character-02",
        "mentor": "character-03",
    }


def test_merge_enrichment_characters_handles_empty_enrichment() -> None:
    """Test that empty enrichment returns existing data unchanged."""
    existing = [
        Character(id="character-01", name="Alice"),
    ]

    enrichment = EnrichmentOutput(new_characters=[])

    merged, id_mapping = merge_enrichment_characters(existing, enrichment, next_character_index=2)

    assert len(merged) == 1
    assert merged[0] == existing[0]
    assert id_mapping == {}


def test_merge_enrichment_world_adds_locations_with_correct_ids() -> None:
    """Test that new locations are added with sequential IDs."""
    existing = World(
        facts=[
            WorldFact(id="location-01", type="location", name="City"),
        ]
    )

    enrichment = EnrichmentOutput(
        new_locations=[
            WorldFactOutput(id="temp-loc-1", type="location", name="Forest", facts=["Dark", "Ancient"]),
            WorldFactOutput(id="temp-loc-2", type="location", name="Castle", facts=["Fortified"]),
        ]
    )

    merged_world, id_mapping = merge_enrichment_world(
        existing, enrichment, next_location_index=2, next_world_fact_index=1
    )

    assert len(merged_world.facts) == 3
    assert merged_world.facts[0].id == "location-01"
    assert merged_world.facts[1].id == "location-02"
    assert merged_world.facts[1].name == "Forest"
    assert merged_world.facts[1].facts == ["Dark", "Ancient"]
    assert merged_world.facts[2].id == "location-03"
    assert merged_world.facts[2].name == "Castle"

    assert "temp-loc-1" in id_mapping
    assert id_mapping["temp-loc-1"] == "location-02"
    assert id_mapping["temp-loc-2"] == "location-03"


def test_merge_enrichment_world_adds_world_facts_with_correct_ids() -> None:
    """Test that new world facts are added with sequential IDs."""
    existing = World(
        facts=[
            WorldFact(id="world-fact-01", type="culture", name="Tradition"),
        ]
    )

    enrichment = EnrichmentOutput(
        new_world_facts=[
            WorldFactOutput(id="temp-fact-1", type="history", name="War", facts=["Ancient conflict"]),
            WorldFactOutput(id="temp-fact-2", type="rule", name="Magic Law", facts=["No dark magic"]),
        ]
    )

    merged_world, id_mapping = merge_enrichment_world(
        existing, enrichment, next_location_index=1, next_world_fact_index=2
    )

    assert len(merged_world.facts) == 3
    assert merged_world.facts[0].id == "world-fact-01"
    assert merged_world.facts[1].id == "world-fact-02"
    assert merged_world.facts[1].type == "history"
    assert merged_world.facts[1].name == "War"
    assert merged_world.facts[2].id == "world-fact-03"
    assert merged_world.facts[2].type == "rule"

    assert id_mapping["temp-fact-1"] == "world-fact-02"
    assert id_mapping["temp-fact-2"] == "world-fact-03"


def test_merge_enrichment_world_preserves_existing_world_data() -> None:
    """Test that existing world metadata is preserved."""
    existing = World(
        setting="Medieval fantasy",
        time_period="Dark Ages",
        tone="Grim",
        motifs=["Redemption", "Sacrifice"],
        facts=[
            WorldFact(id="location-01", type="location", name="City"),
        ],
    )

    enrichment = EnrichmentOutput(
        new_locations=[
            WorldFactOutput(id="temp-loc-1", type="location", name="Forest"),
        ]
    )

    merged_world, _ = merge_enrichment_world(existing, enrichment, next_location_index=2, next_world_fact_index=1)

    assert merged_world.setting == "Medieval fantasy"
    assert merged_world.time_period == "Dark Ages"
    assert merged_world.tone == "Grim"
    assert merged_world.motifs == ["Redemption", "Sacrifice"]
    assert len(merged_world.facts) == 2


def test_merge_enrichment_world_handles_both_locations_and_facts() -> None:
    """Test merging both locations and world facts together."""
    existing = World(facts=[])

    enrichment = EnrichmentOutput(
        new_locations=[
            WorldFactOutput(id="temp-loc-1", type="location", name="Forest"),
        ],
        new_world_facts=[
            WorldFactOutput(id="temp-fact-1", type="culture", name="Custom"),
        ],
    )

    merged_world, id_mapping = merge_enrichment_world(
        existing, enrichment, next_location_index=1, next_world_fact_index=1
    )

    assert len(merged_world.facts) == 2
    assert merged_world.facts[0].id == "location-01"
    assert merged_world.facts[0].type == "location"
    assert merged_world.facts[1].id == "world-fact-01"
    assert merged_world.facts[1].type == "culture"

    assert id_mapping["temp-loc-1"] == "location-01"
    assert id_mapping["temp-fact-1"] == "world-fact-01"


def test_merge_enrichment_plot_updates_scene_summaries_for_subplots() -> None:
    """Test that subplot additions are applied to scene summaries."""
    outline = OutlineContentOutput(
        scenes=[
            SceneContentOutput(id="scene-01", summary="Opening scene", beat_count=1),
            SceneContentOutput(id="scene-02", summary="Middle scene", beat_count=2),
            SceneContentOutput(id="scene-03", summary="Closing scene", beat_count=1),
        ]
    )

    enrichment = EnrichmentOutput(
        subplot_additions=[
            SubplotAddition(
                description="Romance subplot begins",
                involved_characters=["character-01", "character-02"],
                scenes_to_modify=["scene-01", "scene-02"],
            ),
        ]
    )

    id_mapping: dict[str, str] = {}

    updated_outline = merge_enrichment_plot(outline, enrichment, id_mapping)

    # Scene 1 and 2 should have subplot notes
    summary_0 = updated_outline.scenes[0].summary or ""
    summary_1 = updated_outline.scenes[1].summary or ""
    assert "[Subplot] Romance subplot begins" in summary_0
    assert "character-01, character-02" in summary_0
    assert "[Subplot] Romance subplot begins" in summary_1

    # Scene 3 should be unchanged
    assert updated_outline.scenes[2].summary == "Closing scene"


def test_merge_enrichment_plot_updates_foreshadowing_setup_and_payoff() -> None:
    """Test that foreshadowing elements are applied to setup and payoff scenes."""
    outline = OutlineContentOutput(
        scenes=[
            SceneContentOutput(id="scene-01", summary="Setup", beat_count=1),
            SceneContentOutput(id="scene-02", summary="Middle", beat_count=1),
            SceneContentOutput(id="scene-03", summary="Payoff", beat_count=1),
        ]
    )

    enrichment = EnrichmentOutput(
        foreshadowing_elements=[
            ForeshadowingElement(
                description="The sword is cursed",
                setup_scene="scene-01",
                payoff_scene="scene-03",
            ),
        ]
    )

    id_mapping: dict[str, str] = {}

    updated_outline = merge_enrichment_plot(outline, enrichment, id_mapping)

    # Scene 1 should have setup note
    summary_0 = updated_outline.scenes[0].summary or ""
    assert "[Foreshadowing setup] The sword is cursed" in summary_0
    assert "(payoff in scene-03)" in summary_0

    # Scene 2 should be unchanged
    assert updated_outline.scenes[1].summary == "Middle"

    # Scene 3 should have payoff note
    summary_2 = updated_outline.scenes[2].summary or ""
    assert "[Foreshadowing payoff] The sword is cursed" in summary_2
    assert "(setup in scene-01)" in summary_2


def test_merge_enrichment_plot_applies_id_mapping_to_character_references() -> None:
    """Test that character IDs in subplots are mapped correctly."""
    outline = OutlineContentOutput(
        scenes=[
            SceneContentOutput(id="scene-01", summary="Scene", beat_count=1),
        ]
    )

    enrichment = EnrichmentOutput(
        subplot_additions=[
            SubplotAddition(
                description="Test subplot",
                involved_characters=["temp-char-1", "temp-char-2"],
                scenes_to_modify=["scene-01"],
            ),
        ]
    )

    id_mapping: dict[str, str] = {
        "temp-char-1": "character-03",
        "temp-char-2": "character-04",
    }

    updated_outline = merge_enrichment_plot(outline, enrichment, id_mapping)

    # Should use mapped IDs
    summary = updated_outline.scenes[0].summary or ""
    assert "character-03, character-04" in summary


def test_merge_enrichment_plot_handles_empty_enrichment_gracefully() -> None:
    """Test that empty enrichment returns outline unchanged."""
    outline = OutlineContentOutput(
        scenes=[
            SceneContentOutput(id="scene-01", summary="Scene 1", beat_count=1),
            SceneContentOutput(id="scene-02", summary="Scene 2", beat_count=1),
        ]
    )

    enrichment = EnrichmentOutput()

    id_mapping: dict[str, str] = {}

    updated_outline = merge_enrichment_plot(outline, enrichment, id_mapping)

    assert updated_outline.scenes[0].summary == "Scene 1"
    assert updated_outline.scenes[1].summary == "Scene 2"


def test_merge_enrichment_plot_preserves_other_scene_fields() -> None:
    """Test that other scene fields are preserved during merge."""
    outline = OutlineContentOutput(
        chapters=[
            ChapterContentOutput(id="chapter-01", title="Chapter 1"),
        ],
        scenes=[
            SceneContentOutput(
                id="scene-01",
                chapter_id="chapter-01",
                title="Scene Title",
                summary="Original summary",
                beat_count=3,
            ),
        ],
    )

    enrichment = EnrichmentOutput(
        subplot_additions=[
            SubplotAddition(
                description="Test",
                involved_characters=[],
                scenes_to_modify=["scene-01"],
            ),
        ]
    )

    updated_outline = merge_enrichment_plot(outline, enrichment, {})

    assert updated_outline.scenes[0].id == "scene-01"
    assert updated_outline.scenes[0].chapter_id == "chapter-01"
    assert updated_outline.scenes[0].title == "Scene Title"
    assert updated_outline.scenes[0].beat_count == 3
    assert len(updated_outline.chapters) == 1


def test_merge_enrichment_plot_handles_scene_without_summary() -> None:
    """Test that scenes without summaries can still receive enrichment notes."""
    outline = OutlineContentOutput(
        scenes=[
            SceneContentOutput(id="scene-01", summary=None, beat_count=1),
        ]
    )

    enrichment = EnrichmentOutput(
        subplot_additions=[
            SubplotAddition(
                description="New subplot",
                involved_characters=["character-01"],
                scenes_to_modify=["scene-01"],
            ),
        ]
    )

    updated_outline = merge_enrichment_plot(outline, enrichment, {})

    # Should add subplot note even with no original summary
    assert updated_outline.scenes[0].summary is not None
    assert "[Subplot] New subplot" in updated_outline.scenes[0].summary
