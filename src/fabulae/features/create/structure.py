"""Structure generation for deterministic plot graph creation.

This module generates the complete narrative structure (chapters, scenes, beats,
characters, locations) using RNG before any LLM calls. The structure is deterministic
given a seed, allowing reproducible story skeletons.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from fabulae.features.create.graph import (
    BeatSlot,
    ChapterSlot,
    CharacterSlot,
    FragmentSlot,
    LocationSlot,
    MicroProseGraph,
    PlotGraph,
    PoemGraph,
    SceneSlot,
    StanzaSlot,
    WorldFactSlot,
)
from fabulae.features.create.ids import (
    generate_beat_id,
    generate_chapter_id,
    generate_character_id,
    generate_fragment_id,
    generate_location_id,
    generate_scene_id,
    generate_stanza_id,
    generate_world_fact_id,
)
from fabulae.features.create.service import FORMAT_BEATS_PER_SCENE, FORMAT_COUNT_RANGES
from fabulae.features.create.variation import (
    assign_scene_positions,
    select_filler_beats,
)
from fabulae.models import LiteratureFormat

if TYPE_CHECKING:
    from fabulae.models import StoryShape


def generate_plot_graph(
    format: LiteratureFormat,
    shape: StoryShape | None,
    variation: float,
    seed: int | None = None,
) -> PlotGraph:
    """Generate a complete plot structure using RNG.

    This function creates a PlotGraph with all structural decisions made deterministically:
    - Number of chapters (based on format and variation)
    - Scenes per chapter (distributed based on variation)
    - Beats per scene (from shape required beats + filler)
    - Character slots (from shape or format defaults)
    - Location slots (from shape or format defaults)
    - Character and location assignments to scenes

    Args:
        format: Narrative format (novel, novella, short-story)
        shape: Optional story shape providing structural guidance
        variation: Variation level (0.0-1.0) affecting count spread
        seed: Optional RNG seed for reproducibility

    Returns:
        A PlotGraph with all structure determined but no content
    """
    rng = random.Random(seed)

    graph = PlotGraph(format=format, seed=seed)

    # Calculate counts based on format and variation
    chapter_count = _calculate_chapter_count(format, variation, rng)
    total_scenes = _calculate_total_scenes(format, variation, rng)
    scenes_per_chapter = _distribute_scenes_to_chapters(total_scenes, chapter_count, rng)

    # Create chapter slots
    for i in range(chapter_count):
        chapter_id = generate_chapter_id(i + 1)
        graph.chapters.append(
            ChapterSlot(
                id=chapter_id,
                scene_ids=[],
                position=i,
            )
        )

    # Create scene slots and assign to chapters
    scene_index = 0
    for chapter_idx, scene_count in enumerate(scenes_per_chapter):
        scene_chapter_id: str | None = graph.chapters[chapter_idx].id if graph.chapters else None
        for _ in range(scene_count):
            scene_index += 1
            scene_id = generate_scene_id(scene_index)

            graph.scenes.append(
                SceneSlot(
                    id=scene_id,
                    chapter_id=scene_chapter_id,
                    beat_slots=[],
                    position=scene_index - 1,
                )
            )

            if scene_chapter_id:
                graph.chapters[chapter_idx].scene_ids.append(scene_id)

    # Assign position labels to scenes
    scene_ids = [s.id for s in graph.scenes]
    positions = assign_scene_positions(scene_ids)
    for scene in graph.scenes:
        scene.position_label = positions.get(scene.id, "middle")

    # Generate character slots
    graph.characters = _create_character_slots(shape, format, rng)

    # Generate location slots
    graph.locations = _create_location_slots(shape, format, rng)

    # Generate additional world fact slots
    graph.world_facts = _create_world_fact_slots(format, len(graph.locations), rng)

    # Assign characters to scenes
    _assign_characters_to_scenes(graph, shape, rng)

    # Assign locations to scenes
    _assign_locations_to_scenes(graph, rng)

    # Create beat slots for each scene
    _create_beat_slots_for_scenes(graph, shape, format, variation, rng)

    return graph


def _calculate_chapter_count(format: LiteratureFormat, variation: float, rng: random.Random) -> int:
    """Calculate number of chapters based on format and variation."""
    ranges = FORMAT_COUNT_RANGES.get(format, {})
    min_ch, max_ch = ranges.get("chapters", (1, 5))

    if min_ch == 0 and max_ch == 0:
        return 0

    # Variation affects how much we deviate from the midpoint
    mid = (min_ch + max_ch) / 2
    range_size = max_ch - min_ch

    # With low variation, stay close to mid; with high variation, use full range
    effective_min = max(min_ch, int(mid - (range_size / 2) * variation))
    effective_max = min(max_ch, int(mid + (range_size / 2) * variation))

    # Ensure we have at least one valid value
    if effective_min > effective_max:
        effective_min = effective_max = int(mid)

    return rng.randint(effective_min, effective_max)


def _calculate_total_scenes(format: LiteratureFormat, variation: float, rng: random.Random) -> int:
    """Calculate total number of scenes based on format and variation."""
    ranges = FORMAT_COUNT_RANGES.get(format, {})
    min_scenes, max_scenes = ranges.get("scenes", (2, 10))

    mid = (min_scenes + max_scenes) / 2
    range_size = max_scenes - min_scenes

    effective_min = max(min_scenes, int(mid - (range_size / 2) * variation))
    effective_max = min(max_scenes, int(mid + (range_size / 2) * variation))

    if effective_min > effective_max:
        effective_min = effective_max = int(mid)

    return rng.randint(effective_min, effective_max)


def _distribute_scenes_to_chapters(total_scenes: int, chapter_count: int, rng: random.Random) -> list[int]:
    """Distribute scenes across chapters with some randomness."""
    if chapter_count == 0:
        return [total_scenes] if total_scenes > 0 else []

    if total_scenes <= 0:
        return [0] * chapter_count

    # Start with even distribution
    base_per_chapter = total_scenes // chapter_count
    remainder = total_scenes % chapter_count

    # Distribute base counts
    distribution = [base_per_chapter] * chapter_count

    # Randomly distribute remainder
    if remainder > 0:
        indices = rng.sample(range(chapter_count), remainder)
        for idx in indices:
            distribution[idx] += 1

    # Shuffle distribution slightly for more natural variation
    # Swap some adjacent elements
    for i in range(len(distribution) - 1):
        if rng.random() < 0.3 and distribution[i] > 1:
            # Move one scene from this chapter to next
            distribution[i] -= 1
            distribution[i + 1] += 1

    return distribution


def _create_character_slots(
    shape: StoryShape | None, format: LiteratureFormat, rng: random.Random
) -> list[CharacterSlot]:
    """Create character slots from shape or format defaults."""
    slots: list[CharacterSlot] = []

    if shape and shape.character_slots:
        # Use shape-defined character slots
        for i, shape_slot in enumerate(shape.character_slots):
            if shape_slot.optional and rng.random() < 0.5:
                continue  # Skip optional slots with 50% probability

            char_id = generate_character_id(i + 1)
            # Infer role from shape slot
            role = _infer_role_from_slot(shape_slot.slot, shape_slot.needs)

            slots.append(
                CharacterSlot(
                    id=char_id,
                    role=role,
                    shape_slot_id=shape_slot.slot,
                    needs=shape_slot.needs,
                )
            )
    else:
        # Use format defaults
        ranges = FORMAT_COUNT_RANGES.get(format, {})
        min_chars, max_chars = ranges.get("characters", (2, 5))
        char_count = rng.randint(min_chars, max_chars)

        # Standard roles distribution
        roles = ["protagonist"]
        if char_count > 1:
            roles.append("antagonist")
        if char_count > 2:
            roles.extend(["supporting"] * (char_count - 2))

        for i, role in enumerate(roles):
            slots.append(
                CharacterSlot(
                    id=generate_character_id(i + 1),
                    role=role,
                )
            )

    return slots


def _infer_role_from_slot(slot_name: str, needs: str) -> str:
    """Infer character role from shape slot name and needs."""
    slot_lower = slot_name.lower()
    needs_lower = needs.lower()

    if any(x in slot_lower or x in needs_lower for x in ["protagonist", "hero", "main"]):
        return "protagonist"
    if any(x in slot_lower or x in needs_lower for x in ["antagonist", "villain", "enemy"]):
        return "antagonist"
    if any(x in slot_lower or x in needs_lower for x in ["mentor", "guide", "teacher"]):
        return "mentor"
    if any(x in slot_lower or x in needs_lower for x in ["ally", "friend", "companion"]):
        return "ally"
    if any(x in slot_lower or x in needs_lower for x in ["love", "romantic", "interest"]):
        return "love-interest"

    return "supporting"


def _create_location_slots(
    shape: StoryShape | None, format: LiteratureFormat, rng: random.Random
) -> list[LocationSlot]:
    """Create location slots from shape or format defaults."""
    slots: list[LocationSlot] = []

    if shape and shape.setting_slots:
        # Use shape-defined setting slots
        for i, shape_slot in enumerate(shape.setting_slots):
            if shape_slot.optional and rng.random() < 0.5:
                continue

            slots.append(
                LocationSlot(
                    id=generate_location_id(i + 1),
                    shape_setting_id=shape_slot.slot,
                    needs=shape_slot.needs,
                )
            )
    else:
        # Use format defaults - roughly half of world facts are locations
        ranges = FORMAT_COUNT_RANGES.get(format, {})
        min_facts, max_facts = ranges.get("world_facts", (2, 6))
        total_facts = rng.randint(min_facts, max_facts)
        location_count = max(1, total_facts // 2)

        for i in range(location_count):
            slots.append(
                LocationSlot(
                    id=generate_location_id(i + 1),
                )
            )

    return slots


def _create_world_fact_slots(format: LiteratureFormat, location_count: int, rng: random.Random) -> list[WorldFactSlot]:
    """Create non-location world fact slots."""
    ranges = FORMAT_COUNT_RANGES.get(format, {})
    min_facts, max_facts = ranges.get("world_facts", (2, 6))
    total_facts = rng.randint(min_facts, max_facts)

    # Subtract locations already created
    extra_facts = max(0, total_facts - location_count)

    fact_types = ["culture", "history", "rule", "object"]
    slots: list[WorldFactSlot] = []

    for i in range(extra_facts):
        slots.append(
            WorldFactSlot(
                id=generate_world_fact_id(i + 1),
                fact_type=rng.choice(fact_types),
            )
        )

    return slots


def _assign_characters_to_scenes(graph: PlotGraph, shape: StoryShape | None, rng: random.Random) -> None:
    """Assign characters to scenes based on shape or balanced distribution."""
    if not graph.characters or not graph.scenes:
        return

    character_ids = [c.id for c in graph.characters]
    protagonist_ids = [c.id for c in graph.characters if c.role == "protagonist"]

    # Track character appearances for balance
    appearance_count: dict[str, int] = {cid: 0 for cid in character_ids}

    for scene in graph.scenes:
        scene_chars: list[str] = []

        # Protagonist appears in most scenes (80% chance)
        for prot_id in protagonist_ids:
            if rng.random() < 0.8:
                scene_chars.append(prot_id)
                appearance_count[prot_id] += 1

        # Add 1-3 additional characters based on position
        additional_count = 2 if scene.position_label in ["middle", "late"] else 1
        if scene.position_label == "climax":
            additional_count = min(3, len(character_ids) - len(scene_chars))

        # Select least-appeared characters for balance
        available = [cid for cid in character_ids if cid not in scene_chars]
        if available:
            # Sort by appearance count, pick least appeared
            available.sort(key=lambda x: appearance_count[x])
            to_add = available[:additional_count]
            for cid in to_add:
                scene_chars.append(cid)
                appearance_count[cid] += 1

        scene.character_ids = scene_chars


def _assign_locations_to_scenes(graph: PlotGraph, rng: random.Random) -> None:
    """Assign locations to scenes with some variety but avoiding too much jumping."""
    if not graph.locations or not graph.scenes:
        return

    location_ids = [loc.id for loc in graph.locations]

    # Group scenes into location runs (consecutive scenes at same location)
    # Typical run length: 1-3 scenes
    current_location = rng.choice(location_ids)
    run_remaining = rng.randint(1, 3)

    for scene in graph.scenes:
        if run_remaining <= 0:
            # Pick a new location (preferring different from current)
            other_locations = [lid for lid in location_ids if lid != current_location]
            if other_locations:
                current_location = rng.choice(other_locations)
            run_remaining = rng.randint(1, 3)

        scene.location_id = current_location
        run_remaining -= 1


def _create_beat_slots_for_scenes(
    graph: PlotGraph,
    shape: StoryShape | None,
    format: LiteratureFormat,
    variation: float,
    rng: random.Random,
) -> None:
    """Create beat slots for each scene based on shape and variation."""
    min_beats, max_beats = FORMAT_BEATS_PER_SCENE.get(format, (2, 4))

    # Distribute required beats from shape across scenes
    required_beat_assignments: dict[str, list[tuple[str, str]]] = {}  # scene_id -> [(beat_type, description)]
    if shape and shape.required_beats:
        required_beat_assignments = _distribute_required_beats(graph, shape, rng)

    for scene in graph.scenes:
        beat_slots: list[BeatSlot] = []
        beat_index = 0

        # Add required beats from shape
        scene_required = required_beat_assignments.get(scene.id, [])
        for beat_type, _description in scene_required:
            beat_index += 1
            beat_id = generate_beat_id(scene.id, beat_index)
            beat_slots.append(
                BeatSlot(
                    id=beat_id,
                    kind=beat_type,
                    required=True,
                    shape_beat_type=beat_type,
                )
            )

        # Add filler beats to reach target count
        # Target varies by position: climax gets more beats
        target = max_beats if scene.position_label == "climax" else rng.randint(min_beats, max_beats)
        filler_needed = max(0, target - len(beat_slots))

        if filler_needed > 0:
            filler_kinds = select_filler_beats(filler_needed, scene.position_label, rng)
            for kind in filler_kinds:
                beat_index += 1
                beat_id = generate_beat_id(scene.id, beat_index)
                beat_slots.append(
                    BeatSlot(
                        id=beat_id,
                        kind=kind,
                        required=False,
                    )
                )

        scene.beat_slots = beat_slots


def _distribute_required_beats(
    graph: PlotGraph, shape: StoryShape, rng: random.Random
) -> dict[str, list[tuple[str, str]]]:
    """Distribute required beats from shape to appropriate scenes."""
    assignments: dict[str, list[tuple[str, str]]] = {}

    # Group scenes by position
    scenes_by_position: dict[str, list[SceneSlot]] = {
        "early": [],
        "middle": [],
        "late": [],
        "climax": [],
    }
    for scene in graph.scenes:
        pos = scene.position_label
        if pos in scenes_by_position:
            scenes_by_position[pos].append(scene)

    for beat in shape.required_beats:
        # Find appropriate scenes based on beat position
        if beat.position == "anywhere":
            # Can go in any scene
            candidate_scenes = graph.scenes
        else:
            candidate_scenes = scenes_by_position.get(beat.position, graph.scenes)

        if not candidate_scenes:
            candidate_scenes = graph.scenes

        # For flexible beats, randomly select a scene
        # For fixed beats, prefer early scenes in the position group
        if beat.flexibility == "fixed" and candidate_scenes:
            target_scene = candidate_scenes[0]
        elif beat.flexibility == "very-flexible":
            target_scene = rng.choice(candidate_scenes)
        else:
            # flexible - slight preference for earlier scenes in group
            weight_count = max(1, len(candidate_scenes) // 2)
            weighted = candidate_scenes[:weight_count] * 2 + candidate_scenes[weight_count:]
            target_scene = rng.choice(weighted)

        if target_scene.id not in assignments:
            assignments[target_scene.id] = []
        assignments[target_scene.id].append((beat.type, beat.description))

    return assignments


def _calculate_count_with_variation(min_val: int, max_val: int, variation: float, rng: random.Random) -> int:
    """Calculate a count within a range, influenced by variation.

    Args:
        min_val: Minimum value of range
        max_val: Maximum value of range
        variation: Variation level (0.0-1.0). Low variation stays near midpoint.
        rng: Random number generator

    Returns:
        An integer count within the effective range
    """
    if min_val == max_val:
        return min_val

    mid = (min_val + max_val) / 2
    range_size = max_val - min_val

    # With low variation, stay close to mid; with high variation, use full range
    effective_min = max(min_val, int(mid - (range_size / 2) * variation))
    effective_max = min(max_val, int(mid + (range_size / 2) * variation))

    # Ensure we have at least one valid value
    if effective_min > effective_max:
        effective_min = effective_max = int(mid)

    return rng.randint(effective_min, effective_max)


def generate_micro_prose_graph(
    variation: float,
    seed: int | None = None,
) -> MicroProseGraph:
    """Generate micro-prose structure using RNG.

    Creates a MicroProseGraph with all fragment slots pre-allocated.
    The structure is deterministic given a seed.

    Args:
        variation: Variation level (0.0-1.0) affecting fragment count
        seed: Optional RNG seed for reproducibility

    Returns:
        A MicroProseGraph with all fragment slots determined
    """
    rng = random.Random(seed)

    # Get fragment count range from format configuration
    ranges = FORMAT_COUNT_RANGES.get("micro-prose", {})
    min_frags, max_frags = ranges.get("fragments", (1, 5))

    # Calculate fragment count based on variation
    fragment_count = _calculate_count_with_variation(min_frags, max_frags, variation, rng)

    # Create fragment slots with pre-allocated IDs
    fragment_slots = []
    for i in range(fragment_count):
        fragment_slots.append(
            FragmentSlot(
                id=generate_fragment_id(i + 1),
                position=i,
            )
        )

    return MicroProseGraph(fragment_slots=fragment_slots, seed=seed)


def generate_poem_graph(
    variation: float,
    seed: int | None = None,
) -> PoemGraph:
    """Generate poem structure using RNG.

    Creates a PoemGraph with all stanza slots pre-allocated, including
    target line counts for each stanza.

    Args:
        variation: Variation level (0.0-1.0) affecting stanza and line counts
        seed: Optional RNG seed for reproducibility

    Returns:
        A PoemGraph with all stanza slots determined
    """
    rng = random.Random(seed)

    # Get ranges from format configuration
    ranges = FORMAT_COUNT_RANGES.get("poem", {})
    min_stanzas, max_stanzas = ranges.get("stanzas", (1, 6))
    min_lines, max_lines = ranges.get("lines", (3, 18))

    # Calculate stanza count based on variation
    stanza_count = _calculate_count_with_variation(min_stanzas, max_stanzas, variation, rng)

    # Per-stanza line count range (more constrained than total)
    # Typically 2-8 lines per stanza
    per_stanza_min = max(2, min_lines // max(1, stanza_count))
    per_stanza_max = min(8, max_lines // max(1, stanza_count))
    if per_stanza_min > per_stanza_max:
        per_stanza_min = per_stanza_max = 4

    # Create stanza slots with varying line counts
    stanza_slots = []
    for i in range(stanza_count):
        line_count = rng.randint(per_stanza_min, per_stanza_max)
        stanza_slots.append(
            StanzaSlot(
                id=generate_stanza_id(i + 1),
                position=i,
                line_count=line_count,
            )
        )

    return PoemGraph(stanza_slots=stanza_slots, seed=seed)
