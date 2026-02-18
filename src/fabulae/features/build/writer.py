"""Output writers for build results."""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Literal

from fabulae.features.build.schemas import BuildOutput, ChapterOutput, SceneHook

OutputFormat = Literal["md", "txt", "html"]


def _slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def _strip_markdown(text: str) -> str:
    """Strip markdown formatting from text."""
    # Remove headers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    # Remove links
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    # Remove horizontal rules
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)
    return text


def _markdown_to_html(text: str) -> str:
    """Convert basic markdown to HTML."""
    # Escape HTML entities first
    text = html.escape(text)

    # Convert headers
    text = re.sub(r"^###### (.+)$", r"<h6>\1</h6>", text, flags=re.MULTILINE)
    text = re.sub(r"^##### (.+)$", r"<h5>\1</h5>", text, flags=re.MULTILINE)
    text = re.sub(r"^#### (.+)$", r"<h4>\1</h4>", text, flags=re.MULTILINE)
    text = re.sub(r"^### (.+)$", r"<h3>\1</h3>", text, flags=re.MULTILINE)
    text = re.sub(r"^## (.+)$", r"<h2>\1</h2>", text, flags=re.MULTILINE)
    text = re.sub(r"^# (.+)$", r"<h1>\1</h1>", text, flags=re.MULTILINE)

    # Convert bold/italic
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)

    # Convert horizontal rules
    text = re.sub(r"^---+$", "<hr>", text, flags=re.MULTILINE)

    # Convert paragraphs (double newlines)
    paragraphs = re.split(r"\n\n+", text)
    html_parts: list[str] = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        # Don't wrap if it's already an HTML element
        if p.startswith("<h") or p.startswith("<hr"):
            html_parts.append(p)
        else:
            # Convert single newlines to <br> within paragraphs
            p = p.replace("\n", "<br>\n")
            html_parts.append(f"<p>{p}</p>")

    return "\n\n".join(html_parts)


def _wrap_html(content: str, title: str) -> str:
    """Wrap content in an HTML document."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>
        body {{
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            font-family: Georgia, serif;
            line-height: 1.6;
        }}
        h1 {{ margin-top: 2rem; }}
        h2 {{ margin-top: 1.5rem; }}
        p {{ margin-bottom: 1rem; }}
        hr {{ margin: 2rem 0; }}
        .hook {{
            font-style: italic;
            font-size: 1.1em;
            margin-bottom: 1.5rem;
            padding-left: 1rem;
            border-left: 3px solid #666;
        }}
    </style>
</head>
<body>
{content}
</body>
</html>"""


def _format_content(text: str, output_format: OutputFormat, title: str) -> str:
    """Format content based on output format."""
    if output_format == "md":
        return text
    elif output_format == "txt":
        return _strip_markdown(text)
    elif output_format == "html":
        return _wrap_html(_markdown_to_html(text), title)
    else:
        return text


def _format_hook(hook: SceneHook, output_format: OutputFormat) -> str:
    """Format a scene hook for the given output format."""
    if output_format == "md":
        return f"*{hook.content}*"
    elif output_format == "txt":
        return hook.content
    elif output_format == "html":
        return f'<p class="hook">{html.escape(hook.content)}</p>'
    return f"*{hook.content}*"


def _format_chapter(chapter: ChapterOutput, output_format: OutputFormat) -> str:
    """Format a single chapter for output."""
    parts: list[str] = []

    if chapter.title:
        if output_format == "md":
            parts.append(f"# {chapter.title}\n")
        elif output_format == "txt":
            parts.append(f"{chapter.title}\n{'=' * len(chapter.title)}\n")
        elif output_format == "html":
            parts.append(f"<h1>{html.escape(chapter.title)}</h1>")

    for scene in chapter.scenes:
        if scene.title:
            if output_format == "md":
                parts.append(f"## {scene.title}\n")
            elif output_format == "txt":
                parts.append(f"\n{scene.title}\n{'-' * len(scene.title)}\n")
            elif output_format == "html":
                parts.append(f"<h2>{html.escape(scene.title)}</h2>")

        if scene.hook:
            parts.append(_format_hook(scene.hook, output_format))

        if output_format == "html":
            parts.append(_markdown_to_html(scene.content))
        elif output_format == "txt":
            parts.append(_strip_markdown(scene.content))
        else:
            parts.append(scene.content)

    separator = "\n\n"
    return separator.join(parts)


def write_build_output(
    result: BuildOutput,
    output_dir: Path,
    output_format: OutputFormat = "md",
) -> None:
    """Write build output to files.

    Args:
        result: The build output to write.
        output_dir: Directory to write output files to.
        output_format: Output format (md, txt, html).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    title = result.metadata.project_name

    # Write metadata
    metadata_path = output_dir / "build.json"
    metadata_path.write_text(result.metadata.model_dump_json(indent=2))

    # Determine file extension
    ext = output_format

    # Write combined story with title header
    full_text = result.full_text
    if title and title != "Untitled":
        full_text = f"# {title}\n\n{full_text}"
    story_content = _format_content(full_text, output_format, title)
    story_path = output_dir / f"story.{ext}"
    story_path.write_text(story_content)

    # Write individual chapters if present
    if result.chapters:
        chapters_dir = output_dir / "chapters"
        chapters_dir.mkdir(exist_ok=True)

        for i, chapter in enumerate(result.chapters, 1):
            slug = _slugify(chapter.title) if chapter.title else chapter.chapter_id
            filename = f"{i:02d}-{slug}.{ext}"
            chapter_content = _format_chapter(chapter, output_format)

            if output_format == "html":
                chapter_title = chapter.title or f"Chapter {i}"
                chapter_content = _wrap_html(chapter_content, chapter_title)

            (chapters_dir / filename).write_text(chapter_content)

    # Write individual fragments if present
    if result.fragments:
        fragments_dir = output_dir / "fragments"
        fragments_dir.mkdir(exist_ok=True)

        for i, fragment in enumerate(result.fragments, 1):
            filename = f"{i:02d}-{fragment.fragment_id}.{ext}"
            fragment_text = fragment.content
            if fragment.hook:
                # Prepend hook as italic markdown; _format_content handles conversion
                fragment_text = f"*{fragment.hook.content}*\n\n{fragment_text}"
            content = _format_content(fragment_text, output_format, f"Fragment {i}")
            (fragments_dir / filename).write_text(content)


__all__ = ["OutputFormat", "write_build_output"]
