"""Scene, fragment, and stanza builders for generating narrative prose."""

from __future__ import annotations

from fabulae.features.build.prompts import (
    build_continuity_prompt,
    build_continuity_system_prompt,
    build_fragment_prompt,
    build_fragment_system_prompt,
    build_poem_prompt,
    build_poem_system_prompt,
    build_scene_prompt,
    build_scene_system_prompt,
    build_stanza_prompt,
    build_stanza_system_prompt,
)
from fabulae.features.build.schemas import (
    ContinuitySummary,
    FragmentOutput,
    FragmentProseOutput,
    PoemProseOutput,
    SceneOutput,
    SceneProseOutput,
    StanzaOutput,
    StanzaProseOutput,
)
from fabulae.llm import LLMConfig, create_agent
from fabulae.models import Character, Fragment, Project, Scene, Stanza, WorldFact


def _get_characters_in_scene(scene: Scene, project: Project) -> list[Character]:
    """Get Character objects for characters in a scene."""
    char_map = {c.id: c for c in project.characters}
    return [char_map[char_id] for char_id in scene.characters if char_id in char_map]


def _get_location(scene: Scene, project: Project) -> WorldFact | None:
    """Get the location WorldFact for a scene."""
    if not scene.location or not project.world:
        return None
    for fact in project.world.facts:
        if fact.id == scene.location:
            return fact
    return None


def _get_world_facts(scene: Scene, project: Project) -> list[WorldFact]:
    """Get WorldFact objects referenced by a scene."""
    if not project.world:
        return []
    fact_map = {f.id: f for f in project.world.facts}
    return [fact_map[fact_id] for fact_id in scene.world_fact_ids if fact_id in fact_map]


def _count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


async def build_scene(
    scene: Scene,
    project: Project,
    prior_context: str,
    config: LLMConfig,
    chapter_id: str | None = None,
) -> SceneOutput:
    """Generate prose for a single scene.

    Args:
        scene: The scene to generate prose for.
        project: The full project context.
        prior_context: Summary of previous scenes for continuity.
        config: LLM configuration.
        chapter_id: Optional chapter ID this scene belongs to.

    Returns:
        SceneOutput with generated prose content.
    """
    characters = _get_characters_in_scene(scene, project)
    location = _get_location(scene, project)
    world_facts = _get_world_facts(scene, project)

    system_prompt = build_scene_system_prompt(project.style)
    user_prompt = build_scene_prompt(
        scene=scene,
        characters=characters,
        location=location,
        world_facts=world_facts,
        style=project.style,
        prior_context=prior_context,
        premise=project.plot.premise,
    )

    agent = create_agent(SceneProseOutput, system_prompt, config)
    result = await agent.run(user_prompt)
    prose_output: SceneProseOutput = result.output

    return SceneOutput(
        scene_id=scene.id,
        chapter_id=chapter_id,
        title=scene.summary,
        content=prose_output.content,
        word_count=_count_words(prose_output.content),
    )


async def generate_continuity_summary(
    scene_content: str,
    config: LLMConfig,
) -> str:
    """Generate a continuity summary for a scene.

    Args:
        scene_content: The prose content of the scene.
        config: LLM configuration.

    Returns:
        A brief summary for continuity threading.
    """
    system_prompt = build_continuity_system_prompt()
    user_prompt = build_continuity_prompt(scene_content)

    agent = create_agent(ContinuitySummary, system_prompt, config)
    result = await agent.run(user_prompt)
    summary_output: ContinuitySummary = result.output

    return summary_output.summary


async def build_fragment(
    fragment: Fragment,
    project: Project,
    prior_fragments: list[str],
    config: LLMConfig,
) -> FragmentOutput:
    """Generate prose for a micro-prose fragment.

    Args:
        fragment: The fragment to generate prose for.
        project: The full project context.
        prior_fragments: Content of previous fragments for context.
        config: LLM configuration.

    Returns:
        FragmentOutput with generated prose content.
    """
    system_prompt = build_fragment_system_prompt(project.style)
    user_prompt = build_fragment_prompt(
        fragment=fragment,
        style=project.style,
        prior_fragments=prior_fragments,
        premise=project.plot.premise,
    )

    agent = create_agent(FragmentProseOutput, system_prompt, config)
    result = await agent.run(user_prompt)
    prose_output: FragmentProseOutput = result.output

    return FragmentOutput(
        fragment_id=fragment.id,
        content=prose_output.content,
        word_count=_count_words(prose_output.content),
    )


async def build_stanza(
    stanza: Stanza,
    project: Project,
    prior_stanzas: list[list[str]],
    config: LLMConfig,
) -> StanzaOutput:
    """Generate lines for a poem stanza.

    Args:
        stanza: The stanza to generate lines for.
        project: The full project context.
        prior_stanzas: Lines of previous stanzas for context.
        config: LLM configuration.

    Returns:
        StanzaOutput with generated lines.
    """
    system_prompt = build_stanza_system_prompt(project.style)
    user_prompt = build_stanza_prompt(
        stanza=stanza,
        style=project.style,
        prior_stanzas=prior_stanzas,
        premise=project.plot.premise,
        poem_form=project.plot.poem_form,
        poem_meter=project.plot.poem_meter,
        poem_rhyme_scheme=project.plot.poem_rhyme_scheme,
    )

    agent = create_agent(StanzaProseOutput, system_prompt, config)
    result = await agent.run(user_prompt)
    prose_output: StanzaProseOutput = result.output

    content = "\n".join(prose_output.lines)
    return StanzaOutput(
        stanza_id=stanza.id,
        lines=prose_output.lines,
        word_count=_count_words(content),
    )


async def build_poem_from_lines(
    project: Project,
    config: LLMConfig,
) -> str:
    """Generate a complete poem from line seeds.

    Args:
        project: The full project context.
        config: LLM configuration.

    Returns:
        Complete poem text.
    """
    system_prompt = build_poem_system_prompt(project.style)
    user_prompt = build_poem_prompt(
        lines=project.plot.lines,
        style=project.style,
        premise=project.plot.premise,
        poem_form=project.plot.poem_form,
        poem_meter=project.plot.poem_meter,
        poem_rhyme_scheme=project.plot.poem_rhyme_scheme,
    )

    agent = create_agent(PoemProseOutput, system_prompt, config)
    result = await agent.run(user_prompt)
    prose_output: PoemProseOutput = result.output

    return prose_output.content


__all__ = [
    "build_fragment",
    "build_poem_from_lines",
    "build_scene",
    "build_stanza",
    "generate_continuity_summary",
]
