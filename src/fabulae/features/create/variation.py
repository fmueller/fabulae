"""Data structures for narrative variation system."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class VariationConfig:
    """Configuration for narrative variation probabilities and randomization.

    Attributes:
        complication_probability: Probability (0.0-1.0) that a scene includes a complication
            (default 0.3).
        character_moment_probability: Probability (0.0-1.0) that a scene includes a
            character moment (default 0.4).
        subplot_seed_probability: Probability (0.0-1.0) that a scene includes a subplot
            seed (default 0.2).
        seed: Optional random seed for reproducible RNG (default None).
    """

    complication_probability: float = 0.3
    character_moment_probability: float = 0.4
    subplot_seed_probability: float = 0.2
    seed: int | None = None


@dataclass
class SceneVariation:
    """Variation decisions for a single scene.

    Attributes:
        scene_id: The ID of the scene this variation applies to.
        position: Narrative position of the scene (early/middle/late/climax).
        has_complication: Whether this scene includes a complication.
        complication_type: Type of complication if has_complication is True (e.g.,
            "external-obstacle", "internal-conflict").
        has_character_moment: Whether this scene includes a character moment.
        character_focus: The ID of the character to focus on if has_character_moment
            is True.
        subplot_seed: A subplot seed concept if applicable (e.g., "hidden-past",
            "secret-alliance").
        filler_beats: List of beat kind strings to use as filler in this scene.
    """

    scene_id: str
    position: str
    has_complication: bool
    complication_type: str | None = None
    has_character_moment: bool = False
    character_focus: str | None = None
    subplot_seed: str | None = None
    filler_beats: list[str] = field(default_factory=list)


@dataclass
class ProjectVariation:
    """Variation decisions for the entire project.

    Attributes:
        scene_variations: List of SceneVariation objects, one per scene.
        subplot_seeds: List of distinct subplot seed concepts used across the project.
        config: The VariationConfig used to generate these variations.
    """

    scene_variations: list[SceneVariation]
    subplot_seeds: list[str]
    config: VariationConfig


def assign_scene_positions(scene_ids: list[str]) -> dict[str, str]:
    """Assign narrative positions to scenes based on their index.

    Maps scenes to "early", "middle", "late", or "climax" based on their position
    in the scene list using percentage thresholds:
    - 0-25%: "early"
    - 25-70%: "middle"
    - 70-90%: "late"
    - 90-100%: "climax"

    Special cases:
    - Single scene: "climax"
    - Two scenes: first is "early", second is "climax"

    Args:
        scene_ids: List of scene IDs in narrative order.

    Returns:
        Dictionary mapping scene ID to position string.
    """
    total = len(scene_ids)
    positions: dict[str, str] = {}

    if total == 0:
        return positions

    if total == 1:
        positions[scene_ids[0]] = "climax"
        return positions

    if total == 2:
        positions[scene_ids[0]] = "early"
        positions[scene_ids[1]] = "climax"
        return positions

    for i, scene_id in enumerate(scene_ids):
        percentage = i / (total - 1)  # Use total-1 to ensure last scene is at 100%

        if percentage < 0.25:
            positions[scene_id] = "early"
        elif percentage < 0.70:
            positions[scene_id] = "middle"
        elif percentage < 0.90:
            positions[scene_id] = "late"
        else:
            positions[scene_id] = "climax"

    return positions


def select_filler_beats(count: int, position: str, rng: random.Random | None = None) -> list[str]:
    """Select filler beats appropriate for a narrative position.

    Beat kind pools by position:
    - "early": favors setup, bridge, foreshadow, character-moment
    - "middle": balanced escalation, complication, revelation, character-moment, bridge
    - "late": favors escalation, confrontation, revelation, turn
    - "climax": favors confrontation, turn, resolution, revelation

    Args:
        count: Number of filler beats to select.
        position: Narrative position (early/middle/late/climax).
        rng: Optional random.Random instance for reproducibility. If None, uses default random.

    Returns:
        List of beat kind strings.
    """
    if rng is None:
        rng = random.Random()

    beat_pools = {
        "early": ["setup", "bridge", "foreshadow", "character-moment"],
        "middle": ["escalation", "complication", "revelation", "character-moment", "bridge"],
        "late": ["escalation", "confrontation", "revelation", "turn"],
        "climax": ["confrontation", "turn", "resolution", "revelation"],
    }

    pool = beat_pools.get(position, beat_pools["middle"])
    return [rng.choice(pool) for _ in range(count)]


def create_variation_config_from_level(level: float, seed: int | None = None) -> VariationConfig:
    """Create a VariationConfig from a variation level using linear interpolation.

    The level controls the probabilities of narrative variations:
    - At level 0.0: all probabilities are 0.0 (minimal randomness/variation)
    - At level 1.0: all probabilities are at maximum (e.g., 0.6, 0.7, 0.5)
    - At level 0.5: default probabilities (0.3, 0.4, 0.2)

    Uses linear interpolation between minimum (0.0) and maximum probabilities.

    Args:
        level: Variation level from 0.0 (minimal) to 1.0 (maximum).
        seed: Optional random seed for reproducibility.

    Returns:
        A VariationConfig with probabilities interpolated from the level.

    Raises:
        ValueError: If level is not in range [0.0, 1.0].
    """
    if not 0.0 <= level <= 1.0:
        raise ValueError(f"Variation level must be in range [0.0, 1.0], got {level}")

    # Define minimum and maximum probabilities
    min_complication = 0.0
    max_complication = 0.6

    min_character_moment = 0.0
    max_character_moment = 0.7

    min_subplot_seed = 0.0
    max_subplot_seed = 0.5

    # Linear interpolation: min + (max - min) * level
    complication_probability = min_complication + (max_complication - min_complication) * level
    character_moment_probability = min_character_moment + (max_character_moment - min_character_moment) * level
    subplot_seed_probability = min_subplot_seed + (max_subplot_seed - min_subplot_seed) * level

    return VariationConfig(
        complication_probability=complication_probability,
        character_moment_probability=character_moment_probability,
        subplot_seed_probability=subplot_seed_probability,
        seed=seed,
    )


def select_complication_type(rng: random.Random | None = None) -> str:
    """Select a random complication type.

    Complication types include: obstacle, betrayal, revelation, deadline, loss,
    moral-dilemma, misunderstanding, reversal.

    Args:
        rng: Optional random.Random instance for reproducibility. If None, uses default random.

    Returns:
        A complication type string.
    """
    if rng is None:
        rng = random.Random()

    complication_types = [
        "obstacle",
        "betrayal",
        "revelation",
        "deadline",
        "loss",
        "moral-dilemma",
        "misunderstanding",
        "reversal",
    ]

    return rng.choice(complication_types)


def generate_subplot_seed(rng: random.Random | None = None) -> str:
    """Generate a random subplot seed concept.

    Subplot seeds include: romance, rivalry, secret, debt, grudge, ambition,
    loyalty-test, past-connection.

    Args:
        rng: Optional random.Random instance for reproducibility. If None, uses default random.

    Returns:
        A subplot seed string.
    """
    if rng is None:
        rng = random.Random()

    subplot_seeds = [
        "romance",
        "rivalry",
        "secret",
        "debt",
        "grudge",
        "ambition",
        "loyalty-test",
        "past-connection",
    ]

    return rng.choice(subplot_seeds)


class VariationEngine:
    """Main variation engine for generating controlled randomness in narratives.

    The engine uses a StoryShape to guide variation decisions and a VariationConfig
    to control randomness levels and probabilities. It maintains a seeded random
    number generator for reproducible variation.

    Attributes:
        shape: The StoryShape guiding variation decisions.
        config: The VariationConfig controlling probabilities and randomness.
        rng: The random.Random instance for controlled randomness.
    """

    def __init__(self, shape: object, config: VariationConfig) -> None:
        """Initialize the variation engine.

        Args:
            shape: The StoryShape to guide variation decisions (type hint as object
                to avoid circular import, but should be StoryShape from models.py).
            config: The VariationConfig controlling probabilities and randomness.
        """
        self.shape = shape
        self.config = config
        self.rng = random.Random(config.seed)

    def generate_project_variation(self, scene_ids: list[str], character_ids: list[str]) -> ProjectVariation:
        """Generate variation decisions for an entire project.

        This method assigns positions to all scenes, then for each scene:
        1. Decides whether to include a complication
        2. If complication, selects a complication type
        3. Decides whether to include a character moment
        4. If character moment, selects a character to focus on (balanced)
        5. Decides whether to include a subplot seed (only early/middle)
        6. If subplot, generates a subplot seed
        7. Selects filler beats appropriate for position

        Args:
            scene_ids: List of scene IDs in narrative order.
            character_ids: List of character IDs available for focus.

        Returns:
            A ProjectVariation containing all variation decisions.
        """
        # Assign positions to all scenes
        positions = assign_scene_positions(scene_ids)

        # Track character focus distribution for balancing
        character_focus_count: dict[str, int] = {char_id: 0 for char_id in character_ids}

        scene_variations: list[SceneVariation] = []
        subplot_seeds: list[str] = []

        for scene_id in scene_ids:
            position = positions[scene_id]

            # Decide if this scene has a complication
            has_complication = self.rng.random() < self.config.complication_probability
            complication_type = select_complication_type(self.rng) if has_complication else None

            # Decide if this scene has a character moment
            has_character_moment = self.rng.random() < self.config.character_moment_probability
            character_focus = None
            if has_character_moment and character_ids:
                # Select character with fewest focuses for balance
                min_count = min(character_focus_count.values())
                least_focused = [char_id for char_id, count in character_focus_count.items() if count == min_count]
                character_focus = self.rng.choice(least_focused)
                character_focus_count[character_focus] += 1

            # Decide if this scene has a subplot seed (only early/middle)
            subplot_seed = None
            if position in ["early", "middle"] and self.rng.random() < self.config.subplot_seed_probability:
                subplot_seed = generate_subplot_seed(self.rng)
                if subplot_seed not in subplot_seeds:
                    subplot_seeds.append(subplot_seed)

            # Select filler beats based on position
            # Use 2-4 beats based on position (climax gets more)
            beat_count = 4 if position == "climax" else 3 if position == "late" else 2
            filler_beats = select_filler_beats(beat_count, position, self.rng)

            # Create the scene variation
            scene_variation = SceneVariation(
                scene_id=scene_id,
                position=position,
                has_complication=has_complication,
                complication_type=complication_type,
                has_character_moment=has_character_moment,
                character_focus=character_focus,
                subplot_seed=subplot_seed,
                filler_beats=filler_beats,
            )
            scene_variations.append(scene_variation)

        return ProjectVariation(
            scene_variations=scene_variations,
            subplot_seeds=subplot_seeds,
            config=self.config,
        )
