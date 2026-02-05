"""Scene, fragment, and stanza builders for generating narrative prose."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from fabulae.features.build.prompts import (
    build_continuity_prompt,
    build_continuity_system_prompt,
    build_enhanced_fragment_prompt,
    build_enhanced_fragment_system_prompt,
    build_enhanced_scene_prompt,
    build_enhanced_scene_system_prompt,
    build_enhanced_stanza_prompt,
    build_enhanced_stanza_system_prompt,
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
    EnhancedFragmentProseOutput,
    EnhancedSceneProseOutput,
    EnhancedStanzaProseOutput,
    FragmentOutput,
    FragmentProseOutput,
    PoemProseOutput,
    SceneOutput,
    SceneProseOutput,
    StanzaOutput,
    StanzaProseOutput,
)
from fabulae.llm import LLMConfig, create_agent
from fabulae.llm.guards import run_with_guards
from fabulae.llm.json_guard import JsonErrorType
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
    expected_language: str | None = None,
    on_language_correction: Callable[[str, str, int], None] | None = None,
    on_json_error: Callable[[JsonErrorType, str, int], None] | None = None,
) -> SceneOutput:
    """Generate prose for a single scene.

    Args:
        scene: The scene to generate prose for.
        project: The full project context.
        prior_context: Summary of previous scenes for continuity.
        config: LLM configuration.
        chapter_id: Optional chapter ID this scene belongs to.
        expected_language: ISO 639-1 code for language enforcement.
        on_language_correction: Callback for language correction notifications.
        on_json_error: Callback for JSON error notifications.

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

    async def runner() -> SceneProseOutput:
        agent = create_agent(SceneProseOutput, system_prompt, config)
        result = await agent.run(user_prompt)
        return cast(SceneProseOutput, result.output)

    prose_output, _ = await run_with_guards(
        runner=runner,
        result_type=SceneProseOutput,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        llm_config=config,
        extract_text=lambda o: o.content,
        expected_language=expected_language,
        on_language_correction=on_language_correction,
        on_json_error=on_json_error,
    )

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
    on_json_error: Callable[[JsonErrorType, str, int], None] | None = None,
) -> str:
    """Generate a continuity summary for a scene.

    Args:
        scene_content: The prose content of the scene.
        config: LLM configuration.
        on_json_error: Callback for JSON error notifications.

    Returns:
        A brief summary for continuity threading.
    """
    system_prompt = build_continuity_system_prompt()
    user_prompt = build_continuity_prompt(scene_content)

    async def runner() -> ContinuitySummary:
        agent = create_agent(ContinuitySummary, system_prompt, config)
        result = await agent.run(user_prompt)
        return cast(ContinuitySummary, result.output)

    summary_output, _ = await run_with_guards(
        runner=runner,
        result_type=ContinuitySummary,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        llm_config=config,
        extract_text=lambda o: o.summary,
        on_json_error=on_json_error,
    )

    return summary_output.summary


async def build_fragment(
    fragment: Fragment,
    project: Project,
    prior_fragments: list[str],
    config: LLMConfig,
    expected_language: str | None = None,
    on_language_correction: Callable[[str, str, int], None] | None = None,
    on_json_error: Callable[[JsonErrorType, str, int], None] | None = None,
) -> FragmentOutput:
    """Generate prose for a micro-prose fragment.

    Args:
        fragment: The fragment to generate prose for.
        project: The full project context.
        prior_fragments: Content of previous fragments for context.
        config: LLM configuration.
        expected_language: ISO 639-1 code for language enforcement.
        on_language_correction: Callback for language correction notifications.
        on_json_error: Callback for JSON error notifications.

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

    async def runner() -> FragmentProseOutput:
        agent = create_agent(FragmentProseOutput, system_prompt, config)
        result = await agent.run(user_prompt)
        return cast(FragmentProseOutput, result.output)

    prose_output, _ = await run_with_guards(
        runner=runner,
        result_type=FragmentProseOutput,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        llm_config=config,
        extract_text=lambda o: o.content,
        expected_language=expected_language,
        on_language_correction=on_language_correction,
        on_json_error=on_json_error,
    )

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
    expected_language: str | None = None,
    on_language_correction: Callable[[str, str, int], None] | None = None,
    on_json_error: Callable[[JsonErrorType, str, int], None] | None = None,
) -> StanzaOutput:
    """Generate lines for a poem stanza.

    Args:
        stanza: The stanza to generate lines for.
        project: The full project context.
        prior_stanzas: Lines of previous stanzas for context.
        config: LLM configuration.
        expected_language: ISO 639-1 code for language enforcement.
        on_language_correction: Callback for language correction notifications.
        on_json_error: Callback for JSON error notifications.

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

    async def runner() -> StanzaProseOutput:
        agent = create_agent(StanzaProseOutput, system_prompt, config)
        result = await agent.run(user_prompt)
        return cast(StanzaProseOutput, result.output)

    prose_output, _ = await run_with_guards(
        runner=runner,
        result_type=StanzaProseOutput,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        llm_config=config,
        extract_text=lambda o: "\n".join(o.lines),
        expected_language=expected_language,
        on_language_correction=on_language_correction,
        on_json_error=on_json_error,
    )

    content = "\n".join(prose_output.lines)
    return StanzaOutput(
        stanza_id=stanza.id,
        lines=prose_output.lines,
        word_count=_count_words(content),
    )


async def build_poem_from_lines(
    project: Project,
    config: LLMConfig,
    expected_language: str | None = None,
    on_language_correction: Callable[[str, str, int], None] | None = None,
    on_json_error: Callable[[JsonErrorType, str, int], None] | None = None,
) -> str:
    """Generate a complete poem from line seeds.

    Args:
        project: The full project context.
        config: LLM configuration.
        expected_language: ISO 639-1 code for language enforcement.
        on_language_correction: Callback for language correction notifications.
        on_json_error: Callback for JSON error notifications.

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

    async def runner() -> PoemProseOutput:
        agent = create_agent(PoemProseOutput, system_prompt, config)
        result = await agent.run(user_prompt)
        return cast(PoemProseOutput, result.output)

    prose_output, _ = await run_with_guards(
        runner=runner,
        result_type=PoemProseOutput,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        llm_config=config,
        extract_text=lambda o: o.content,
        expected_language=expected_language,
        on_language_correction=on_language_correction,
        on_json_error=on_json_error,
    )

    return prose_output.content


# --- Text extraction functions for language guard ---


def extract_enhanced_scene_text(output: EnhancedSceneProseOutput) -> str:
    """Extract all prose text from enhanced scene output for language detection."""
    parts: list[str] = []
    if output.hook:
        parts.append(output.hook.content)
    for beat in output.beats:
        parts.append(beat.prose)
    return "\n\n".join(parts)


def extract_enhanced_fragment_text(output: EnhancedFragmentProseOutput) -> str:
    """Extract all prose text from enhanced fragment output for language detection."""
    parts: list[str] = []
    if output.hook:
        parts.append(output.hook.content)
    parts.append(output.content)
    return "\n\n".join(parts)


def extract_enhanced_stanza_text(output: EnhancedStanzaProseOutput) -> str:
    """Extract all text from enhanced stanza output for language detection."""
    parts: list[str] = []
    if output.hook:
        parts.append(output.hook.content)
    parts.extend(output.lines)
    return "\n".join(parts)


# --- Enhanced build functions ---


async def build_enhanced_scene(
    scene: Scene,
    project: Project,
    prior_context: str,
    config: LLMConfig,
    chapter_id: str | None = None,
    prior_hooks: list[str] | None = None,
    expected_language: str | None = None,
    on_language_correction: Callable[[str, str, int], None] | None = None,
    on_json_error: Callable[[JsonErrorType, str, int], None] | None = None,
) -> SceneOutput:
    """Generate enhanced prose for a single scene with hooks and beat-level tracking.

    Args:
        scene: The scene to generate prose for.
        project: The full project context.
        prior_context: Summary of previous scenes for continuity.
        config: LLM configuration.
        chapter_id: Optional chapter ID this scene belongs to.
        prior_hooks: Previous scene hooks for diversity.
        expected_language: ISO 639-1 code for language enforcement.
        on_language_correction: Callback for language correction notifications.
        on_json_error: Callback for JSON error notifications.

    Returns:
        SceneOutput with hook, beat-level prose, and assembled content.
    """
    characters = _get_characters_in_scene(scene, project)
    location = _get_location(scene, project)
    world_facts = _get_world_facts(scene, project)

    system_prompt = build_enhanced_scene_system_prompt(project.style)
    user_prompt = build_enhanced_scene_prompt(
        scene=scene,
        characters=characters,
        location=location,
        world_facts=world_facts,
        style=project.style,
        prior_context=prior_context,
        premise=project.plot.premise,
        prior_hooks=prior_hooks,
    )

    async def runner() -> EnhancedSceneProseOutput:
        agent = create_agent(EnhancedSceneProseOutput, system_prompt, config)
        result = await agent.run(user_prompt)
        return cast(EnhancedSceneProseOutput, result.output)

    prose_output, _ = await run_with_guards(
        runner=runner,
        result_type=EnhancedSceneProseOutput,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        llm_config=config,
        extract_text=extract_enhanced_scene_text,
        expected_language=expected_language,
        on_language_correction=on_language_correction,
        on_json_error=on_json_error,
    )

    # Assemble content from beats
    content_parts: list[str] = []
    if prose_output.hook:
        content_parts.append(prose_output.hook.content)
    for beat in prose_output.beats:
        content_parts.append(beat.prose)
    content = "\n\n".join(content_parts)

    return SceneOutput(
        scene_id=scene.id,
        chapter_id=chapter_id,
        title=scene.summary,
        hook=prose_output.hook,
        beats=prose_output.beats,
        content=content,
        word_count=_count_words(content),
    )


async def build_enhanced_fragment(
    fragment: Fragment,
    project: Project,
    prior_fragments: list[str],
    config: LLMConfig,
    prior_hooks: list[str] | None = None,
    expected_language: str | None = None,
    on_language_correction: Callable[[str, str, int], None] | None = None,
    on_json_error: Callable[[JsonErrorType, str, int], None] | None = None,
) -> FragmentOutput:
    """Generate enhanced prose for a micro-prose fragment with opening hook.

    Args:
        fragment: The fragment to generate prose for.
        project: The full project context.
        prior_fragments: Content of previous fragments for context.
        config: LLM configuration.
        prior_hooks: Previous fragment hooks for diversity.
        expected_language: ISO 639-1 code for language enforcement.
        on_language_correction: Callback for language correction notifications.
        on_json_error: Callback for JSON error notifications.

    Returns:
        FragmentOutput with hook and generated prose content.
    """
    system_prompt = build_enhanced_fragment_system_prompt(project.style)
    user_prompt = build_enhanced_fragment_prompt(
        fragment=fragment,
        style=project.style,
        prior_fragments=prior_fragments,
        premise=project.plot.premise,
        prior_hooks=prior_hooks,
    )

    async def runner() -> EnhancedFragmentProseOutput:
        agent = create_agent(EnhancedFragmentProseOutput, system_prompt, config)
        result = await agent.run(user_prompt)
        return cast(EnhancedFragmentProseOutput, result.output)

    prose_output, _ = await run_with_guards(
        runner=runner,
        result_type=EnhancedFragmentProseOutput,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        llm_config=config,
        extract_text=extract_enhanced_fragment_text,
        expected_language=expected_language,
        on_language_correction=on_language_correction,
        on_json_error=on_json_error,
    )

    return FragmentOutput(
        fragment_id=fragment.id,
        hook=prose_output.hook,
        content=prose_output.content,
        word_count=_count_words(prose_output.content),
    )


async def build_enhanced_stanza(
    stanza: Stanza,
    project: Project,
    prior_stanzas: list[list[str]],
    config: LLMConfig,
    prior_hooks: list[str] | None = None,
    expected_language: str | None = None,
    on_language_correction: Callable[[str, str, int], None] | None = None,
    on_json_error: Callable[[JsonErrorType, str, int], None] | None = None,
) -> StanzaOutput:
    """Generate enhanced lines for a poem stanza with optional opening hook.

    Args:
        stanza: The stanza to generate lines for.
        project: The full project context.
        prior_stanzas: Lines of previous stanzas for context.
        config: LLM configuration.
        prior_hooks: Previous stanza hooks for diversity.
        expected_language: ISO 639-1 code for language enforcement.
        on_language_correction: Callback for language correction notifications.
        on_json_error: Callback for JSON error notifications.

    Returns:
        StanzaOutput with optional hook and generated lines.
    """
    system_prompt = build_enhanced_stanza_system_prompt(project.style)
    user_prompt = build_enhanced_stanza_prompt(
        stanza=stanza,
        style=project.style,
        prior_stanzas=prior_stanzas,
        premise=project.plot.premise,
        poem_form=project.plot.poem_form,
        poem_meter=project.plot.poem_meter,
        poem_rhyme_scheme=project.plot.poem_rhyme_scheme,
        prior_hooks=prior_hooks,
    )

    async def runner() -> EnhancedStanzaProseOutput:
        agent = create_agent(EnhancedStanzaProseOutput, system_prompt, config)
        result = await agent.run(user_prompt)
        return cast(EnhancedStanzaProseOutput, result.output)

    prose_output, _ = await run_with_guards(
        runner=runner,
        result_type=EnhancedStanzaProseOutput,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        llm_config=config,
        extract_text=extract_enhanced_stanza_text,
        expected_language=expected_language,
        on_language_correction=on_language_correction,
        on_json_error=on_json_error,
    )

    content = "\n".join(prose_output.lines)
    return StanzaOutput(
        stanza_id=stanza.id,
        hook=prose_output.hook,
        lines=prose_output.lines,
        word_count=_count_words(content),
    )


__all__ = [
    "build_enhanced_fragment",
    "build_enhanced_scene",
    "build_enhanced_stanza",
    "build_fragment",
    "build_poem_from_lines",
    "build_scene",
    "build_stanza",
    "extract_enhanced_fragment_text",
    "extract_enhanced_scene_text",
    "extract_enhanced_stanza_text",
    "generate_continuity_summary",
]
