from __future__ import annotations

from dataclasses import dataclass, field


def generate_id(entity_type: str, index: int) -> str:
    width = max(2, len(str(index)))
    return f"{entity_type}-{index:0{width}d}"


def generate_beat_id(scene_id: str, beat_index: int) -> str:
    return f"{scene_id}-beat-{beat_index:02d}"


def generate_chapter_id(index: int) -> str:
    return generate_id("chapter", index)


def generate_scene_id(index: int) -> str:
    return generate_id("scene", index)


def generate_character_id(index: int) -> str:
    return generate_id("character", index)


def generate_location_id(index: int) -> str:
    return generate_id("location", index)


def generate_world_fact_id(index: int) -> str:
    return generate_id("world-fact", index)


def generate_fragment_id(index: int) -> str:
    return generate_id("fragment", index)


def generate_stanza_id(index: int) -> str:
    return generate_id("stanza", index)


@dataclass
class ProjectIds:
    chapters: list[str] = field(default_factory=list)
    scenes: list[str] = field(default_factory=list)
    scene_to_chapter: dict[str, str] = field(default_factory=dict)
    scene_beats: dict[str, list[str]] = field(default_factory=dict)
    characters: list[str] = field(default_factory=list)
    character_slot_mapping: dict[str, str] = field(default_factory=dict)
    locations: list[str] = field(default_factory=list)
    location_slot_mapping: dict[str, str] = field(default_factory=dict)
    world_facts: list[str] = field(default_factory=list)
    fragments: list[str] = field(default_factory=list)
    stanzas: list[str] = field(default_factory=list)


def allocate_prose_ids(
    num_chapters: int,
    scenes_per_chapter: list[int],
    beats_per_scene: list[int],
    character_slots: list[str] | None = None,
    location_slots: list[str] | None = None,
    extra_world_facts: int = 0,
) -> ProjectIds:
    if num_chapters < 0:
        raise ValueError("num_chapters must be non-negative.")
    if num_chapters and len(scenes_per_chapter) != num_chapters:
        raise ValueError("scenes_per_chapter length must match num_chapters when chapters are present.")
    total_scenes = sum(scenes_per_chapter) if num_chapters else len(beats_per_scene)
    if total_scenes != len(beats_per_scene):
        raise ValueError("beats_per_scene length must equal total scenes.")

    chapters = [generate_chapter_id(index + 1) for index in range(num_chapters)]

    scenes: list[str] = []
    scene_to_chapter: dict[str, str] = {}
    beat_ids: dict[str, list[str]] = {}
    scene_index = 0
    if num_chapters:
        for chapter_index, scene_count in enumerate(scenes_per_chapter):
            chapter_id = chapters[chapter_index]
            for _ in range(scene_count):
                scene_index += 1
                scene_id = generate_scene_id(scene_index)
                scenes.append(scene_id)
                scene_to_chapter[scene_id] = chapter_id
    else:
        for scene_index in range(1, total_scenes + 1):
            scene_id = generate_scene_id(scene_index)
            scenes.append(scene_id)

    for scene_id, beat_count in zip(scenes, beats_per_scene, strict=True):
        beat_ids[scene_id] = [generate_beat_id(scene_id, index + 1) for index in range(beat_count)]

    characters: list[str] = []
    character_slot_mapping: dict[str, str] = {}
    for slot_index, slot in enumerate(character_slots or [], start=1):
        character_id = generate_character_id(slot_index)
        characters.append(character_id)
        character_slot_mapping[slot] = character_id

    locations: list[str] = []
    location_slot_mapping: dict[str, str] = {}
    for slot_index, slot in enumerate(location_slots or [], start=1):
        location_id = generate_location_id(slot_index)
        locations.append(location_id)
        location_slot_mapping[slot] = location_id

    world_facts = [generate_world_fact_id(index + 1) for index in range(extra_world_facts)]

    return ProjectIds(
        chapters=chapters,
        scenes=scenes,
        scene_to_chapter=scene_to_chapter,
        scene_beats=beat_ids,
        characters=characters,
        character_slot_mapping=character_slot_mapping,
        locations=locations,
        location_slot_mapping=location_slot_mapping,
        world_facts=world_facts,
    )


def allocate_micro_prose_ids(num_fragments: int) -> ProjectIds:
    fragments = [generate_fragment_id(index + 1) for index in range(max(num_fragments, 0))]
    return ProjectIds(fragments=fragments)


def allocate_poem_ids(num_stanzas: int) -> ProjectIds:
    stanzas = [generate_stanza_id(index + 1) for index in range(max(num_stanzas, 0))]
    return ProjectIds(stanzas=stanzas)


def extend_ids_for_enrichment(
    project_ids: ProjectIds,
    extra_characters: int = 0,
    extra_locations: int = 0,
    extra_world_facts: int = 0,
) -> ProjectIds:
    new_characters = list(project_ids.characters)
    for _index in range(extra_characters):
        new_characters.append(generate_character_id(len(new_characters) + 1))

    new_locations = list(project_ids.locations)
    for _index in range(extra_locations):
        new_locations.append(generate_location_id(len(new_locations) + 1))

    new_world_facts = list(project_ids.world_facts)
    for _index in range(extra_world_facts):
        new_world_facts.append(generate_world_fact_id(len(new_world_facts) + 1))

    return ProjectIds(
        chapters=list(project_ids.chapters),
        scenes=list(project_ids.scenes),
        scene_to_chapter=dict(project_ids.scene_to_chapter),
        scene_beats={scene_id: list(beats) for scene_id, beats in project_ids.scene_beats.items()},
        characters=new_characters,
        character_slot_mapping=dict(project_ids.character_slot_mapping),
        locations=new_locations,
        location_slot_mapping=dict(project_ids.location_slot_mapping),
        world_facts=new_world_facts,
        fragments=list(project_ids.fragments),
        stanzas=list(project_ids.stanzas),
    )
