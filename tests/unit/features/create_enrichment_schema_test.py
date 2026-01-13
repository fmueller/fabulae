"""Tests for enrichment-related schemas in create feature."""

from __future__ import annotations

from fabulae.features.create.schemas import (
    CharacterOutput,
    CreateOptions,
    EnrichmentOutput,
    ForeshadowingElement,
    SubplotAddition,
    WorldFactOutput,
)


def test_subplot_addition_validation() -> None:
    """Test SubplotAddition schema validation."""
    subplot = SubplotAddition(description="A secret betrayal subplot")
    assert subplot.description == "A secret betrayal subplot"
    assert subplot.involved_characters == []
    assert subplot.scenes_to_modify == []


def test_subplot_addition_with_characters_and_scenes() -> None:
    """Test SubplotAddition with involved characters and scenes."""
    subplot = SubplotAddition(
        description="A forbidden romance",
        involved_characters=["char-1", "char-2"],
        scenes_to_modify=["scene-3", "scene-5"],
    )
    assert subplot.description == "A forbidden romance"
    assert subplot.involved_characters == ["char-1", "char-2"]
    assert subplot.scenes_to_modify == ["scene-3", "scene-5"]


def test_foreshadowing_element_validation() -> None:
    """Test ForeshadowingElement schema validation."""
    foreshadow = ForeshadowingElement(description="A mysterious locked box")
    assert foreshadow.description == "A mysterious locked box"
    assert foreshadow.setup_scene is None
    assert foreshadow.payoff_scene is None


def test_foreshadowing_element_with_scenes() -> None:
    """Test ForeshadowingElement with setup and payoff scenes."""
    foreshadow = ForeshadowingElement(
        description="The hero's hidden past",
        setup_scene="scene-2",
        payoff_scene="scene-10",
    )
    assert foreshadow.description == "The hero's hidden past"
    assert foreshadow.setup_scene == "scene-2"
    assert foreshadow.payoff_scene == "scene-10"


def test_enrichment_output_default_empty_lists() -> None:
    """Test EnrichmentOutput defaults all lists to empty."""
    enrichment = EnrichmentOutput()
    assert enrichment.new_characters == []
    assert enrichment.new_locations == []
    assert enrichment.new_world_facts == []
    assert enrichment.subplot_additions == []
    assert enrichment.foreshadowing_elements == []


def test_enrichment_output_with_new_characters() -> None:
    """Test EnrichmentOutput with new characters."""
    char1 = CharacterOutput(id="char-mentor", name="The Wise Mentor")
    char2 = CharacterOutput(id="char-rival", name="The Rival", role="antagonist")

    enrichment = EnrichmentOutput(new_characters=[char1, char2])
    assert len(enrichment.new_characters) == 2
    assert enrichment.new_characters[0].id == "char-mentor"
    assert enrichment.new_characters[1].role == "antagonist"


def test_enrichment_output_with_locations() -> None:
    """Test EnrichmentOutput with new locations."""
    loc1 = WorldFactOutput(id="loc-tavern", type="location", name="The Tavern")
    loc2 = WorldFactOutput(id="loc-castle", type="location", name="The Dark Castle", facts=["imposing", "ancient"])

    enrichment = EnrichmentOutput(new_locations=[loc1, loc2])
    assert len(enrichment.new_locations) == 2
    assert enrichment.new_locations[0].name == "The Tavern"
    assert enrichment.new_locations[1].facts == ["imposing", "ancient"]


def test_enrichment_output_with_world_facts() -> None:
    """Test EnrichmentOutput with other world facts."""
    fact1 = WorldFactOutput(id="culture-magic", type="culture", name="Magic System")
    fact2 = WorldFactOutput(
        id="rule-ancient-law",
        type="rule",
        name="Ancient Law",
        facts=["binding", "magical"],
    )

    enrichment = EnrichmentOutput(new_world_facts=[fact1, fact2])
    assert len(enrichment.new_world_facts) == 2
    assert enrichment.new_world_facts[0].type == "culture"
    assert enrichment.new_world_facts[1].type == "rule"


def test_enrichment_output_with_subplots() -> None:
    """Test EnrichmentOutput with subplot additions."""
    subplot1 = SubplotAddition(
        description="Hidden alliance",
        involved_characters=["char-1"],
        scenes_to_modify=["scene-3"],
    )
    subplot2 = SubplotAddition(description="Betrayal revelation")

    enrichment = EnrichmentOutput(subplot_additions=[subplot1, subplot2])
    assert len(enrichment.subplot_additions) == 2
    assert enrichment.subplot_additions[0].involved_characters == ["char-1"]


def test_enrichment_output_with_foreshadowing() -> None:
    """Test EnrichmentOutput with foreshadowing elements."""
    foreshadow1 = ForeshadowingElement(
        description="Mysterious prophecy",
        setup_scene="scene-1",
        payoff_scene="scene-8",
    )
    foreshadow2 = ForeshadowingElement(description="Hidden clue")

    enrichment = EnrichmentOutput(foreshadowing_elements=[foreshadow1, foreshadow2])
    assert len(enrichment.foreshadowing_elements) == 2
    assert enrichment.foreshadowing_elements[0].setup_scene == "scene-1"


def test_enrichment_output_full_example() -> None:
    """Test EnrichmentOutput with all fields populated."""
    char = CharacterOutput(id="char-new", name="New Character")
    loc = WorldFactOutput(id="loc-new", type="location", name="New Location")
    fact = WorldFactOutput(id="fact-new", type="history", name="New History")
    subplot = SubplotAddition(description="New subplot")
    foreshadow = ForeshadowingElement(description="New foreshadowing")

    enrichment = EnrichmentOutput(
        new_characters=[char],
        new_locations=[loc],
        new_world_facts=[fact],
        subplot_additions=[subplot],
        foreshadowing_elements=[foreshadow],
    )

    assert len(enrichment.new_characters) == 1
    assert len(enrichment.new_locations) == 1
    assert len(enrichment.new_world_facts) == 1
    assert len(enrichment.subplot_additions) == 1
    assert len(enrichment.foreshadowing_elements) == 1


def test_create_options_enrich_default_true() -> None:
    """Test CreateOptions.enrich defaults to True."""
    options = CreateOptions()
    assert options.enrich is True


def test_create_options_enrich_can_be_disabled() -> None:
    """Test CreateOptions.enrich can be set to False."""
    options = CreateOptions(enrich=False)
    assert options.enrich is False


def test_create_options_with_all_fields() -> None:
    """Test CreateOptions with all fields including enrich."""
    options = CreateOptions(
        narrative_patterns_mode="artifact",
        use_narrative_patterns_in_prompts=True,
        shape_id="heros-journey",
        variation=0.7,
        seed=42,
        enrich=False,
    )
    assert options.narrative_patterns_mode == "artifact"
    assert options.use_narrative_patterns_in_prompts is True
    assert options.shape_id == "heros-journey"
    assert options.variation == 0.7
    assert options.seed == 42
    assert options.enrich is False
