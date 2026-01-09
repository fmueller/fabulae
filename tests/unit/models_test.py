"""Tests for the Fabulae data models."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from fabulae.models import (
    Beat,
    Character,
    Fragment,
    NarrativePattern,
    Plot,
    PlotPattern,
    PlotPatternBeat,
    Project,
    ProjectConfig,
    Scene,
    Stanza,
    World,
    WorldFact,
    load_project,
    save_project,
)


class TestCharacter:
    """Tests for the Character model."""

    def test_valid_character_loads(self) -> None:
        """A valid character loads without error."""
        data = {
            "id": "marta",
            "name": "Marta",
            "role": "protagonist",
            "desire": "To save her bees",
            "flaw": "Too trusting",
            "traits": ["determined", "kind", "resourceful"],
        }
        char = Character.model_validate(data)
        assert char.id == "marta"
        assert char.name == "Marta"
        assert char.role == "protagonist"
        assert char.desire == "To save her bees"
        assert char.flaw == "Too trusting"
        assert char.traits == ["determined", "kind", "resourceful"]

    def test_invalid_id_format_raises_error(self) -> None:
        """ID with spaces or uppercase raises ValidationError."""
        data = {"id": "Invalid ID", "name": "Test"}
        with pytest.raises(ValidationError) as exc_info:
            Character.model_validate(data)
        assert "lowercase" in str(exc_info.value).lower()


class TestWorldFact:
    """Tests for the WorldFact model."""

    def test_valid_world_fact_loads(self) -> None:
        """A valid world fact loads without error."""
        data = {
            "id": "apiary",
            "type": "location",
            "name": "The Apiary",
            "facts": ["Located on the hillside", "Has 50 hives"],
        }
        wf = WorldFact.model_validate(data)
        assert wf.id == "apiary"
        assert wf.type == "location"
        assert wf.name == "The Apiary"
        assert len(wf.facts) == 2

    def test_invalid_type_raises_validation_error(self) -> None:
        """Invalid type raises ValidationError."""
        data = {"id": "apiary", "type": "place", "name": "The Apiary"}
        with pytest.raises(ValidationError) as exc_info:
            WorldFact.model_validate(data)
        assert "type" in str(exc_info.value)


class TestPlotPattern:
    """Tests for the PlotPattern model."""

    def test_valid_plot_pattern_loads(self) -> None:
        """A valid plot pattern loads without error."""
        data = {
            "id": "betrayal",
            "name": "Betrayal",
            "description": "One character betrays another's trust",
            "roles": [
                {"id": "betrayer", "description": "The one who betrays", "required": True},
                {"id": "victim", "description": "The one betrayed", "required": True},
            ],
            "required_beats": [
                {"type": "setup", "description": "{betrayer} gains {victim}'s trust"},
                {"type": "payoff", "description": "{betrayer} reveals their true nature"},
            ],
        }
        pattern = PlotPattern.model_validate(data)
        assert pattern.id == "betrayal"
        assert len(pattern.roles) == 2
        assert len(pattern.required_beats) == 2


class TestScene:
    """Tests for the Scene model."""

    def test_scene_with_beats_loads(self) -> None:
        """A scene with beats loads without error."""
        data = {
            "id": "discovery",
            "location": "apiary",
            "beats": [
                {"id": "quiet-yard", "kind": "setup"},
                {"id": "open-hive", "kind": "payoff", "summary": "The hive is dead."},
            ],
        }
        scene = Scene.model_validate(data)
        assert scene.id == "discovery"
        assert scene.location == "apiary"
        assert len(scene.beats) == 2

    def test_scene_without_location_loads(self) -> None:
        """A scene without a location loads without error."""
        data = {
            "id": "dream-sequence",
            "time": "night",
            "summary": "A surreal dreamscape",
        }
        scene = Scene.model_validate(data)
        assert scene.id == "dream-sequence"
        assert scene.location is None
        assert scene.time == "night"

    def test_scene_with_time_loads(self) -> None:
        """A scene with time field loads without error."""
        data = {
            "id": "morning-ritual",
            "location": "kitchen",
            "time": "early morning",
        }
        scene = Scene.model_validate(data)
        assert scene.time == "early morning"


class TestPlot:
    """Tests for the Plot model."""

    def test_plot_with_scenes_loads(self) -> None:
        """A valid plot loads without error."""
        data = {
            "premise": "A beekeeper fights to save her hives.",
            "scenes": [{"id": "intro", "location": "apiary"}],
        }
        plot = Plot.model_validate(data)
        assert plot.premise.startswith("A beekeeper")
        assert len(plot.scenes) == 1


class TestPlotPatternReferences:
    """Tests for plot pattern references and mappings."""

    def test_plot_pattern_beats_require_plot_pattern(self, tmp_path: Path) -> None:
        """plot.plot_pattern_beats requires plot.plot_pattern."""
        import yaml

        (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
        (tmp_path / "plot.yml").write_text(
            yaml.dump(
                {
                    "premise": "Mapping test",
                    "plot_pattern_beats": [{"type": "setup", "scene": "scene-one"}],
                    "scenes": [{"id": "scene-one", "location": "apiary"}],
                }
            )
        )
        (tmp_path / "world.yml").write_text(
            yaml.dump(
                {"facts": [{"id": "apiary", "type": "location", "name": "Apiary"}]}
            )
        )

        with pytest.raises(ValueError) as exc_info:
            load_project(tmp_path)
        assert "plot_pattern_beats" in str(exc_info.value)

    def test_plot_pattern_requires_known_pattern(self, tmp_path: Path) -> None:
        """Plot plot_pattern must reference a known plot pattern."""
        import yaml

        (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
        (tmp_path / "plot.yml").write_text(
            yaml.dump(
                {
                    "premise": "Unknown pattern test",
                    "plot_pattern": "unknown",
                    "scenes": [{"id": "scene-one", "location": "apiary"}],
                }
            )
        )
        (tmp_path / "world.yml").write_text(
            yaml.dump(
                {"facts": [{"id": "apiary", "type": "location", "name": "Apiary"}]}
            )
        )

        with pytest.raises(ValueError) as exc_info:
            load_project(tmp_path)
        assert "plot pattern" in str(exc_info.value).lower()

    def test_plot_pattern_beats_validate_scene_and_beat(self, tmp_path: Path) -> None:
        """Plot plot_pattern_beats validates scene and beat references."""
        import yaml

        (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
        (tmp_path / "plot.yml").write_text(
            yaml.dump(
                {
                    "premise": "Beat mapping test",
                    "plot_pattern": "betrayal",
                    "plot_pattern_beats": [
                        {"type": "setup", "scene": "scene-one", "scene_beat": "missing"}
                    ],
                    "scenes": [
                        {
                            "id": "scene-one",
                            "location": "apiary",
                            "beats": [{"id": "beat-one", "kind": "setup"}],
                        }
                    ],
                }
            )
        )
        (tmp_path / "plot_patterns.yml").write_text(
            yaml.dump(
                {
                    "plot_patterns": [
                        {
                            "id": "betrayal",
                            "name": "Betrayal",
                            "description": "Trust breaks.",
                            "required_beats": [
                                {"type": "setup", "description": "Trust forms."}
                            ],
                        }
                    ]
                }
            )
        )
        (tmp_path / "world.yml").write_text(
            yaml.dump(
                {"facts": [{"id": "apiary", "type": "location", "name": "Apiary"}]}
            )
        )

        with pytest.raises(ValueError) as exc_info:
            load_project(tmp_path)
        assert "scene beat" in str(exc_info.value).lower()

    def test_narrative_pattern_requires_known_plot_pattern(self, tmp_path: Path) -> None:
        """Narrative pattern plot_pattern must reference a known plot pattern."""
        import yaml

        (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
        (tmp_path / "plot.yml").write_text(
            yaml.dump(
                {
                    "premise": "Narrative pattern test",
                    "scenes": [{"id": "scene-one", "location": "apiary"}],
                }
            )
        )
        (tmp_path / "narrative_patterns.yml").write_text(
            yaml.dump(
                {
                    "narrative_patterns": [
                        {
                            "id": "lost-city",
                            "name": "Lost City",
                            "description": "A forgotten place resurfaces.",
                            "plot_pattern": "missing",
                        }
                    ]
                }
            )
        )
        (tmp_path / "world.yml").write_text(
            yaml.dump(
                {"facts": [{"id": "apiary", "type": "location", "name": "Apiary"}]}
            )
        )

        with pytest.raises(ValueError) as exc_info:
            load_project(tmp_path)
        assert "narrative pattern" in str(exc_info.value).lower()


class TestFormatSupport:
    """Tests for different narrative formats."""

    def test_micro_prose_format_loads(self) -> None:
        """A micro-prose work with fragments loads without error."""
        data = {
            "format": "micro-prose",
            "premise": "Flash fiction about memory",
            "fragments": [
                {"id": "opening", "content": "The watch stopped at 3:47."},
                {"id": "middle", "content": "She remembered the exact moment.", "target_words": 50},
            ],
        }
        plot = Plot.model_validate(data)
        assert plot.format == "micro-prose"
        assert len(plot.fragments) == 2
        assert plot.fragments[0].content == "The watch stopped at 3:47."

    def test_poem_format_with_stanzas_loads(self) -> None:
        """A poem with stanzas loads without error."""
        data = {
            "format": "poem",
            "premise": "A sonnet about time",
            "poem_form": "sonnet",
            "poem_rhyme_scheme": "ABAB CDCD EFEF GG",
            "stanzas": [
                {
                    "id": "quatrain-1",
                    "lines": ["Time slips through fingers like sand", "Each grain a moment that won't stay"],
                    "rhyme_scheme": "ABAB",
                },
                {
                    "id": "quatrain-2",
                    "lines": ["The clock's relentless secondhand", "Marks out the price we all must pay"],
                },
            ],
        }
        plot = Plot.model_validate(data)
        assert plot.format == "poem"
        assert plot.poem_form == "sonnet"
        assert len(plot.stanzas) == 2

    def test_poem_format_with_lines_loads(self) -> None:
        """A poem with just lines (no stanzas) loads without error."""
        data = {
            "format": "poem",
            "premise": "A haiku about autumn",
            "poem_form": "haiku",
            "lines": ["Leaves fall silently", "Red and gold carpet the ground", "Winter waits nearby"],
        }
        plot = Plot.model_validate(data)
        assert plot.format == "poem"
        assert len(plot.lines) == 3

    def test_short_story_format_loads(self) -> None:
        """A short story loads without error."""
        data = {
            "format": "short-story",
            "premise": "A brief encounter",
            "scenes": [{"id": "meeting", "location": "cafe"}],
        }
        plot = Plot.model_validate(data)
        assert plot.format == "short-story"
        assert len(plot.scenes) == 1

    def test_format_validation_prose_cannot_have_fragments(self, tmp_path: Path) -> None:
        """Prose formats should not mix with fragments."""
        import yaml

        (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
        (tmp_path / "plot.yml").write_text(
            yaml.dump(
                {
                    "format": "novel",
                    "premise": "Mixed format test",
                    "scenes": [{"id": "scene-one", "location": "place"}],
                    "fragments": [{"id": "frag-one", "content": "Should not be here"}],
                }
            )
        )
        (tmp_path / "world.yml").write_text(
            yaml.dump({"facts": [{"id": "place", "type": "location", "name": "Place"}]})
        )

        with pytest.raises(ValueError) as exc_info:
            load_project(tmp_path)
        assert "fragments" in str(exc_info.value).lower()

    def test_format_validation_poem_requires_stanzas_or_lines(self, tmp_path: Path) -> None:
        """Poem format requires stanzas or lines."""
        import yaml

        (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
        (tmp_path / "plot.yml").write_text(
            yaml.dump({"format": "poem", "premise": "A poem with no content"})
        )

        with pytest.raises(ValueError) as exc_info:
            load_project(tmp_path)
        assert "stanzas or lines" in str(exc_info.value).lower()

    def test_format_validation_micro_prose_requires_fragments(self, tmp_path: Path) -> None:
        """Micro-prose format requires fragments."""
        import yaml

        (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
        (tmp_path / "plot.yml").write_text(
            yaml.dump({"format": "micro-prose", "premise": "Micro-prose with no fragments"})
        )

        with pytest.raises(ValueError) as exc_info:
            load_project(tmp_path)
        assert "fragment" in str(exc_info.value).lower()

    def test_format_validation_micro_prose_cannot_have_scenes(self, tmp_path: Path) -> None:
        """Micro-prose format should not have scenes, even if fragments are present."""
        import yaml

        (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
        (tmp_path / "plot.yml").write_text(
            yaml.dump(
                {
                    "format": "micro-prose",
                    "premise": "Mixed format test",
                    "fragments": [{"id": "frag-one", "content": "Valid fragment"}],
                    "scenes": [{"id": "scene-one"}],
                }
            )
        )

        with pytest.raises(ValueError) as exc_info:
            load_project(tmp_path)
        assert "scenes" in str(exc_info.value).lower()

    def test_micro_prose_round_trip(self, tmp_path: Path) -> None:
        """Save and load a micro-prose project."""
        project = Project(
            config=ProjectConfig(version="0.1.0"),
            plot=Plot(
                format="micro-prose",
                premise="Brief moments",
                fragments=[
                    Fragment(id="moment-one", content="The door closed."),
                    Fragment(id="moment-two", content="Silence followed.", target_words=100),
                ],
            ),
        )

        save_project(project, tmp_path)
        loaded = load_project(tmp_path)

        assert loaded.plot.format == "micro-prose"
        assert len(loaded.plot.fragments) == 2
        assert loaded.plot.fragments[0].content == "The door closed."

    def test_poem_round_trip(self, tmp_path: Path) -> None:
        """Save and load a poem project."""
        project = Project(
            config=ProjectConfig(version="0.1.0"),
            plot=Plot(
                format="poem",
                premise="Nature's cycle",
                poem_form="free verse",
                stanzas=[
                    Stanza(id="stanza-1", lines=["The river flows", "Always moving forward"]),
                    Stanza(id="stanza-2", lines=["Yet always here", "In this moment"]),
                ],
            ),
        )

        save_project(project, tmp_path)
        loaded = load_project(tmp_path)

        assert loaded.plot.format == "poem"
        assert loaded.plot.poem_form == "free verse"
        assert len(loaded.plot.stanzas) == 2
        assert loaded.plot.stanzas[0].lines[0] == "The river flows"


class TestFileIO:
    """Tests for file I/O helpers."""

    def test_load_project_from_directory(self, tmp_path: Path) -> None:
        """load_project correctly loads a project from directory structure."""
        import yaml

        (tmp_path / "fabulae.yml").write_text(
            yaml.dump(
                {
                    "version": "0.1.0",
                    "paths": {
                        "plot": "plot.yml",
                        "characters": "characters.yml",
                        "world": "world.yml",
                        "style": "style.yml",
                        "plot_patterns": "plot_patterns.yml",
                    },
                }
            )
        )

        (tmp_path / "plot.yml").write_text(
            yaml.dump(
                {
                    "premise": "A test premise",
                    "chapters": [{"id": "chapter-one", "scene_ids": ["scene-one"]}],
                    "scenes": [
                        {
                            "id": "scene-one",
                            "chapter": "chapter-one",
                            "location": "apiary",
                            "characters": ["hero"],
                            "beats": [{"id": "beat-one", "kind": "setup"}],
                        }
                    ],
                }
            )
        )

        (tmp_path / "characters.yml").write_text(
            yaml.dump(
                {
                    "characters": [
                        {"id": "hero", "name": "The Hero", "role": "protagonist"}
                    ]
                }
            )
        )

        (tmp_path / "world.yml").write_text(
            yaml.dump(
                {
                    "setting": "Test valley",
                    "facts": [
                        {"id": "apiary", "type": "location", "name": "The Apiary"}
                    ],
                }
            )
        )

        (tmp_path / "style.yml").write_text(
            yaml.dump(
                {
                    "pov": "third_limited",
                    "tense": "past",
                }
            )
        )

        (tmp_path / "plot_patterns.yml").write_text(
            yaml.dump(
                {
                    "plot_patterns": [
                        {
                            "id": "betrayal",
                            "name": "Betrayal",
                            "description": "Trust is broken.",
                            "required_beats": [
                                {"type": "setup", "description": "Trust forms."}
                            ],
                        }
                    ]
                }
            )
        )

        (tmp_path / "narrative_patterns.yml").write_text(
            yaml.dump(
                {
                    "narrative_patterns": [
                        {
                            "id": "rusted-friendship",
                            "name": "Rusted Friendship",
                            "description": "Trust decays under hidden motives.",
                            "plot_pattern": "betrayal",
                            "roles": [
                                {"id": "friend", "description": "The betrayed friend"},
                                {"id": "traitor", "description": "The betrayer"},
                            ],
                            "themes": ["trust", "loss"],
                        }
                    ]
                }
            )
        )

        project = load_project(tmp_path)
        assert project.config.version == "0.1.0"
        assert project.plot.premise == "A test premise"
        assert len(project.characters) == 1
        assert project.world is not None
        assert project.world.setting == "Test valley"
        assert len(project.plot.scenes) == 1
        assert len(project.plot_patterns) == 1
        assert len(project.narrative_patterns) == 1

    def test_save_and_load_project_round_trip(self, tmp_path: Path) -> None:
        """save_project and load_project produce equivalent data."""
        project = Project(
            config=ProjectConfig(version="0.1.0"),
            plot=Plot(
                premise="Testing save and load",
                scenes=[
                    Scene(
                        id="intro",
                        location="test-lab",
                        beats=[Beat(id="beat-one", kind="setup")],
                    )
                ],
            ),
            characters=[
                Character(
                    id="tester",
                    name="The Tester",
                    role="protagonist",
                )
            ],
            world=World(
                setting="Lab city",
                facts=[WorldFact(id="test-lab", type="location", name="The Lab")],
            ),
            plot_patterns=[
                PlotPattern(
                    id="betrayal",
                    name="Betrayal",
                    description="Trust is broken.",
                    required_beats=[
                        PlotPatternBeat(type="setup", description="Trust forms.")
                    ],
                )
            ],
            narrative_patterns=[
                NarrativePattern(
                    id="lab-espionage",
                    name="Lab Espionage",
                    description="Secrets unfold in a sealed lab.",
                    plot_pattern="betrayal",
                    themes=["secrecy"],
                )
            ],
        )

        save_project(project, tmp_path)
        loaded = load_project(tmp_path)

        assert loaded.plot.premise == project.plot.premise
        assert loaded.characters[0].name == "The Tester"
        assert loaded.world is not None
        assert loaded.world.setting == "Lab city"

    def test_duplicate_ids_raise_error(self, tmp_path: Path) -> None:
        """Duplicate IDs across nodes raise an error."""
        import yaml

        (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
        (tmp_path / "plot.yml").write_text(
            yaml.dump(
                {
                    "premise": "Duplicate test",
                    "scenes": [{"id": "scene-one", "location": "dup"}],
                }
            )
        )
        (tmp_path / "characters.yml").write_text(
            yaml.dump({"characters": [{"id": "dup", "name": "Dup"}]})
        )
        (tmp_path / "world.yml").write_text(
            yaml.dump({"facts": [{"id": "dup", "type": "location", "name": "Dup"}]})
        )

        with pytest.raises(ValueError) as exc_info:
            load_project(tmp_path)
        assert "duplicate" in str(exc_info.value).lower()

    def test_scene_location_requires_location_fact(self, tmp_path: Path) -> None:
        """Scene locations must reference world facts of type location."""
        import yaml

        (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
        (tmp_path / "plot.yml").write_text(
            yaml.dump(
                {
                    "premise": "Location test",
                    "scenes": [{"id": "scene-one", "location": "not-a-place"}],
                }
            )
        )
        (tmp_path / "world.yml").write_text(
            yaml.dump(
                {
                    "facts": [
                        {
                            "id": "not-a-place",
                            "type": "culture",
                            "name": "Not a place",
                        }
                    ]
                }
            )
        )

        with pytest.raises(ValueError) as exc_info:
            load_project(tmp_path)
        assert "location" in str(exc_info.value).lower()

    def test_scene_without_location_no_world_required(self, tmp_path: Path) -> None:
        """Scenes without locations don't require world facts."""
        import yaml

        (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
        (tmp_path / "plot.yml").write_text(
            yaml.dump(
                {
                    "premise": "A simple story",
                    "scenes": [
                        {"id": "scene-one", "time": "morning"},
                        {"id": "scene-two", "time": "evening"},
                    ],
                }
            )
        )
        # No world.yml file

        project = load_project(tmp_path)
        assert len(project.plot.scenes) == 2
        assert project.plot.scenes[0].location is None
        assert project.plot.scenes[0].time == "morning"
