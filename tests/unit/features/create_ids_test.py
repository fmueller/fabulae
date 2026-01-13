from __future__ import annotations

from fabulae.features.create.ids import (
    ProjectIds,
    allocate_micro_prose_ids,
    allocate_poem_ids,
    allocate_prose_ids,
    extend_ids_for_enrichment,
    generate_beat_id,
    generate_chapter_id,
    generate_character_id,
    generate_fragment_id,
    generate_id,
    generate_location_id,
    generate_scene_id,
    generate_stanza_id,
    generate_world_fact_id,
)


def test_generate_id_padding() -> None:
    assert generate_id("scene", 1) == "scene-01"
    assert generate_id("scene", 10) == "scene-10"
    assert generate_id("scene", 100) == "scene-100"


def test_generate_specialized_ids() -> None:
    assert generate_beat_id("scene-01", 1) == "scene-01-beat-01"
    assert generate_chapter_id(2) == "chapter-02"
    assert generate_scene_id(3) == "scene-03"
    assert generate_character_id(4) == "character-04"
    assert generate_location_id(5) == "location-05"
    assert generate_world_fact_id(6) == "world-fact-06"
    assert generate_fragment_id(7) == "fragment-07"
    assert generate_stanza_id(8) == "stanza-08"


def test_allocate_prose_ids_builds_sequences() -> None:
    project_ids = allocate_prose_ids(
        num_chapters=3,
        scenes_per_chapter=[2, 3, 2],
        beats_per_scene=[3, 3, 4, 3, 2, 3, 4],
        character_slots=["hero", "mentor"],
        location_slots=["home", "road"],
        extra_world_facts=2,
    )

    assert project_ids.chapters == ["chapter-01", "chapter-02", "chapter-03"]
    assert project_ids.scenes == [
        "scene-01",
        "scene-02",
        "scene-03",
        "scene-04",
        "scene-05",
        "scene-06",
        "scene-07",
    ]
    assert project_ids.scene_to_chapter == {
        "scene-01": "chapter-01",
        "scene-02": "chapter-01",
        "scene-03": "chapter-02",
        "scene-04": "chapter-02",
        "scene-05": "chapter-02",
        "scene-06": "chapter-03",
        "scene-07": "chapter-03",
    }
    assert project_ids.scene_beats["scene-01"] == ["scene-01-beat-01", "scene-01-beat-02", "scene-01-beat-03"]
    assert project_ids.scene_beats["scene-03"][-1] == "scene-03-beat-04"
    assert project_ids.characters == ["character-01", "character-02"]
    assert project_ids.character_slot_mapping == {"hero": "character-01", "mentor": "character-02"}
    assert project_ids.locations == ["location-01", "location-02"]
    assert project_ids.location_slot_mapping == {"home": "location-01", "road": "location-02"}
    assert project_ids.world_facts == ["world-fact-01", "world-fact-02"]


def test_allocate_micro_prose_ids() -> None:
    project_ids = allocate_micro_prose_ids(3)

    assert project_ids.fragments == ["fragment-01", "fragment-02", "fragment-03"]
    assert project_ids.characters == []
    assert project_ids.world_facts == []


def test_allocate_poem_ids() -> None:
    project_ids = allocate_poem_ids(4)

    assert project_ids.stanzas == ["stanza-01", "stanza-02", "stanza-03", "stanza-04"]
    assert project_ids.chapters == []
    assert project_ids.scenes == []


def test_extend_ids_for_enrichment_appends_sequences() -> None:
    base_ids = ProjectIds(
        characters=["character-01", "character-02", "character-03"],
        locations=["location-01"],
        world_facts=["world-fact-01", "world-fact-02"],
        character_slot_mapping={"hero": "character-01"},
        location_slot_mapping={"home": "location-01"},
    )

    extended = extend_ids_for_enrichment(
        base_ids,
        extra_characters=2,
        extra_locations=1,
        extra_world_facts=2,
    )

    assert extended.characters == [
        "character-01",
        "character-02",
        "character-03",
        "character-04",
        "character-05",
    ]
    assert extended.locations == ["location-01", "location-02"]
    assert extended.world_facts == ["world-fact-01", "world-fact-02", "world-fact-03", "world-fact-04"]
    assert extended.character_slot_mapping == {"hero": "character-01"}
    assert extended.location_slot_mapping == {"home": "location-01"}
