"""Tests for whitespace stripping in schemas."""

from fabulae.features.create.schemas import (
    BeatOutput,
    ChapterOutput,
    CharacterOutput,
    FragmentOutput,
    HookOutput,
    PlotOutput,
    PremiseOutput,
    SceneOutput,
    StakesOutput,
    StanzaOutput,
    StyleOutput,
    WorldFactOutput,
    WorldOutput,
    WorldPlanOutput,
)


def test_style_output_strips_whitespace() -> None:
    """Test StyleOutput strips whitespace from fields."""
    output = StyleOutput(
        language="  en  ",
        voice="  observant  ",
        pov="  third  ",
    )
    assert output.language == "en"
    assert output.voice == "observant"
    assert output.pov == "third"


def test_style_output_strips_all_fields() -> None:
    """Test StyleOutput strips whitespace from all string fields."""
    output = StyleOutput(
        language="  en  ",
        pov="  first  ",
        tense="  past  ",
        voice="  observant  ",
        register="  formal  ",
    )
    assert output.language == "en"
    assert output.pov == "first"
    assert output.tense == "past"
    assert output.voice == "observant"
    assert output.register_ == "formal"


def test_character_output_strips_whitespace() -> None:
    """Test CharacterOutput strips whitespace from fields."""
    output = CharacterOutput(
        id="character-01",
        name="  Alice  ",
        role="  protagonist  ",
    )
    assert output.name == "Alice"
    assert output.role == "protagonist"


def test_character_output_strips_all_fields() -> None:
    """Test CharacterOutput strips whitespace from all string fields."""
    output = CharacterOutput(
        id="character-01",
        name="  Alice  ",
        role="  protagonist  ",
        desire="  find the truth  ",
        need="  trust others  ",
        flaw="  stubborn  ",
        secret="  hiding a past  ",
    )
    assert output.name == "Alice"
    assert output.role == "protagonist"
    assert output.desire == "find the truth"
    assert output.need == "trust others"
    assert output.flaw == "stubborn"
    assert output.secret == "hiding a past"


def test_world_fact_output_strips_whitespace() -> None:
    """Test WorldFactOutput strips whitespace from name."""
    output = WorldFactOutput(
        id="location-01",
        type="location",
        name="  Harbor Lab  ",
    )
    assert output.name == "Harbor Lab"


def test_world_output_strips_whitespace() -> None:
    """Test WorldOutput strips whitespace from fields."""
    output = WorldOutput(
        setting="  coastal town  ",
        time_period="  near future  ",
        tone="  moody  ",
    )
    assert output.setting == "coastal town"
    assert output.time_period == "near future"
    assert output.tone == "moody"


def test_world_plan_output_strips_whitespace() -> None:
    """Test WorldPlanOutput strips whitespace from fields."""
    output = WorldPlanOutput(
        setting="  coastal town  ",
        time_period="  near future  ",
        tone="  moody  ",
    )
    assert output.setting == "coastal town"
    assert output.time_period == "near future"
    assert output.tone == "moody"


def test_beat_output_strips_whitespace() -> None:
    """Test BeatOutput strips whitespace from fields."""
    output = BeatOutput(
        id="scene-01-beat-01",
        kind="  setup  ",
        summary="  The opening moment  ",
    )
    assert output.kind == "setup"
    assert output.summary == "The opening moment"


def test_scene_output_strips_whitespace() -> None:
    """Test SceneOutput strips whitespace from fields."""
    output = SceneOutput(
        id="scene-01",
        time="  night  ",
        summary="  A tense encounter  ",
        goal="  find clues  ",
        conflict="  locked door  ",
        outcome="  success  ",
    )
    assert output.time == "night"
    assert output.summary == "A tense encounter"
    assert output.goal == "find clues"
    assert output.conflict == "locked door"
    assert output.outcome == "success"


def test_chapter_output_strips_whitespace() -> None:
    """Test ChapterOutput strips whitespace from fields."""
    output = ChapterOutput(
        id="chapter-01",
        title="  Opening  ",
        summary="  The beginning  ",
    )
    assert output.title == "Opening"
    assert output.summary == "The beginning"


def test_fragment_output_strips_whitespace() -> None:
    """Test FragmentOutput strips whitespace from fields."""
    output = FragmentOutput(
        id="fragment-01",
        content="  Fragment content  ",
        notes="  Optional notes  ",
    )
    assert output.content == "Fragment content"
    assert output.notes == "Optional notes"


def test_stanza_output_strips_whitespace() -> None:
    """Test StanzaOutput strips whitespace from fields."""
    output = StanzaOutput(
        id="stanza-01",
        lines=["line one", "line two"],
        meter="  iambic pentameter  ",
        rhyme_scheme="  ABAB  ",
    )
    assert output.meter == "iambic pentameter"
    assert output.rhyme_scheme == "ABAB"


def test_plot_output_strips_whitespace() -> None:
    """Test PlotOutput strips whitespace from fields."""
    output = PlotOutput(
        format="novel",
        title="  The Title  ",
        premise="  The premise  ",
        poem_form="  sonnet  ",
        poem_meter="  iambic  ",
        poem_rhyme_scheme="  ABAB  ",
    )
    assert output.title == "The Title"
    assert output.premise == "The premise"
    assert output.poem_form == "sonnet"
    assert output.poem_meter == "iambic"
    assert output.poem_rhyme_scheme == "ABAB"


def test_premise_output_strips_whitespace() -> None:
    """Test PremiseOutput strips whitespace from premise."""
    output = PremiseOutput(premise="  The premise  ")
    assert output.premise == "The premise"


def test_hook_output_strips_whitespace() -> None:
    """Test HookOutput strips whitespace from fields."""
    output = HookOutput(
        line="  Opening line  ",
        question="  What happens?  ",
        promise="  A promise  ",
    )
    assert output.line == "Opening line"
    assert output.question == "What happens?"
    assert output.promise == "A promise"


def test_stakes_output_strips_whitespace() -> None:
    """Test StakesOutput strips whitespace from fields."""
    output = StakesOutput(
        external="  External stakes  ",
        internal="  Internal stakes  ",
    )
    assert output.external == "External stakes"
    assert output.internal == "Internal stakes"


def test_whitespace_with_none_values() -> None:
    """Test that None values pass through validators without error."""
    # Character with None values
    char = CharacterOutput(id="character-01", name="Alice", role=None)
    assert char.role is None

    # World with None values
    world = WorldOutput(setting=None, tone=None)
    assert world.setting is None
    assert world.tone is None

    # Beat with None values
    beat = BeatOutput(id="scene-01-beat-01", kind="setup", summary=None)
    assert beat.summary is None
