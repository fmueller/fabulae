# Build Command Improvement Issues

> Ready-to-file GitHub issues for improving the `fabulae build` command.
> Each section below is a self-contained issue.

---

## Issue 1: Pipeline selection bug — always defaults to sequential

**Labels**: `bug`, `build`

### Description

In `src/fabulae/features/build/cli.py:120`, the pipeline auto-selection has a copy-paste bug:

```python
actual_pipeline: BuildPipelineMode = pipeline or ("sequential" if is_small else "sequential")
```

Both branches of the ternary return `"sequential"`. Large models with big context windows never get `"batch"` mode automatically.

### Expected behavior

```python
actual_pipeline: BuildPipelineMode = pipeline or ("sequential" if is_small else "batch")
```

Large models should default to `batch` (full-context coherence), small models to `sequential` (sliding-window, lower memory).

### Files to change

- `src/fabulae/features/build/cli.py` — line 120

### Acceptance criteria

- [ ] Large models default to `batch` pipeline when `--pipeline` is not specified
- [ ] Small models default to `sequential` pipeline (unchanged)
- [ ] `--pipeline` CLI flag still overrides the auto-detection
- [ ] Existing tests pass; add a test for the auto-detection logic

---

## Issue 2: Scene summaries used as titles — produces bloated headers

**Labels**: `enhancement`, `build`, `prompt-engineering`

### Description

The `Scene` model has no `title` field — only `summary` (designed to be "2-3 sentences describing what happens"). The build pipeline uses `scene.summary` verbatim as the scene title:

**`src/fabulae/features/build/scene_builder.py:134` and `:444`:**
```python
title=scene.summary,
```

**`src/fabulae/features/build/service.py:53-54`:**
```python
if scene.title:
    parts.append(f"## {scene.title}\n")
```

This produces output like:
```markdown
## Elena arrives at the abandoned warehouse where she discovers the documents have been moved. She confronts Marcus about his betrayal.
```

...instead of a proper short title like `## The Warehouse`.

This is especially visible in **short stories**, where scene headers are the only structural separators.

### Proposed solutions (pick one or combine)

**Option A — Generate titles during build**: Add a lightweight LLM call (or prompt instruction) that generates a 2-5 word scene title from the summary before rendering.

**Option B — Add `title` field to Scene model**: Add an optional `title: str | None` field to the `Scene` model in `src/fabulae/models.py`. Have the `create` feature generate short titles. Fall back to a truncated summary if `title` is null.

**Option C — Format-aware headers**: For short stories, use scene breaks (`* * *` or `---`) instead of titled headers. Reserve `##` headers for novels/novellas where chapters already provide top-level structure.

### Files to change

- `src/fabulae/features/build/scene_builder.py` — both `build_scene()` and `build_enhanced_scene()`
- `src/fabulae/features/build/service.py` — `_combine_scenes()`
- `src/fabulae/features/build/writer.py` — if format-aware headers are chosen
- Possibly `src/fabulae/models.py` — if adding a `title` field to `Scene`
- Possibly `src/fabulae/features/entities/generation/schemas.py` — `SceneOutput` for create pipeline

### Acceptance criteria

- [ ] Scene headers in build output are short (2-5 words), not multi-sentence summaries
- [ ] Short stories use appropriate scene separators (not bloated `##` headers)
- [ ] Existing projects without scene titles still render correctly (graceful fallback)
- [ ] Tests cover the new title generation or formatting logic

---

## Issue 3: Build prompts produce insufficient dialogue

**Labels**: `enhancement`, `build`, `prompt-engineering`

### Description

The build system's prompts weakly encourage dialogue, resulting in prose that is predominantly narration/summary with little or no character speech.

**Current state:**

- **Standard scene prompt** (`prompts.py:117`): Only one line mentions dialogue: `"Show character emotions and reactions through action and dialogue"` — this frames dialogue as optional ("action *and* dialogue").
- **Enhanced scene prompt** (`prompts.py:386,393,479-480`): Three lines mention dialogue but use conditional language: `"Include natural dialogue when characters interact"`.
- **Character desire/need/flaw** are only passed in enhanced mode (`_format_characters(detailed=True)` at `prompts.py:454`), not standard mode (`prompts.py:162`). These fields exist explicitly "for dialog/inner monologue guidance" (comment at `prompts.py:34`).
- **No proportion guidance**: No instruction about how much of the prose should be dialogue.
- **No dialogue formatting instructions**: No guidance on new-line-per-speaker, attribution style, etc.

### Proposed changes

1. **Strengthen dialogue instructions** in both standard and enhanced system prompts:
   - Add explicit instruction: "Every scene with two or more characters MUST include dialogue exchanges."
   - Add: "Use a new paragraph for each speaker change."
   - Add: "Balance narration and dialogue — aim for at least 30% dialogue in scenes with multiple characters."

2. **Pass character detail in standard mode too**: Use `_format_characters(characters, detailed=True)` in `build_scene_prompt()`, not just `build_enhanced_scene_prompt()`. The desire/need/flaw fields directly inform how characters speak.

3. **Add dialogue formatting guidance** to the system prompt:
   - "Format dialogue with proper attribution and paragraph breaks."
   - "Vary dialogue tags — use action beats alongside 'said'."

### Files to change

- `src/fabulae/features/build/prompts.py` — `build_scene_system_prompt()`, `build_scene_prompt()`, `build_enhanced_scene_system_prompt()`, `build_enhanced_scene_prompt()`

### Acceptance criteria

- [ ] System prompt explicitly requires dialogue in multi-character scenes
- [ ] Character desire/need/flaw are included in standard scene prompts (not just enhanced)
- [ ] Dialogue formatting guidance is present in system prompt
- [ ] Existing tests pass

---

## Issue 4: No word count targets in build scene prompts

**Labels**: `enhancement`, `build`, `prompt-engineering`

### Description

The build prompts give the LLM **no guidance on prose length**. Per-beat `target_words` is formatted if present (`prompts.py:103-104`), but there is no scene-level word count target. The LLM may produce 50 words or 2000 words per scene with no steering.

The `word_count` field in output schemas (`SceneOutput`, `FragmentOutput`, etc.) is purely post-hoc — never fed back or used for validation.

### Proposed changes

1. **Add scene-level word count guidance** to the user prompt. Calculate a target from:
   - Sum of beat `target_words` if available
   - A format-based default (e.g., novel scenes ~1500-2500 words, short-story scenes ~800-1500 words, novella ~1000-2000)
   - Add to prompt: `"Target scene length: ~{target} words"`

2. **Add minimum length validation** (optional): Log a warning if generated scene prose is under a threshold (e.g., < 200 words for a scene with beats).

### Files to change

- `src/fabulae/features/build/prompts.py` — `build_scene_prompt()`, `build_enhanced_scene_prompt()`
- Possibly `src/fabulae/features/build/scene_builder.py` — for post-generation validation/warning
- Possibly `src/fabulae/features/build/schemas.py` — if adding a target field to `BuildOptions`

### Acceptance criteria

- [ ] Scene prompts include a word count target based on format and/or beat targets
- [ ] Generated prose consistently hits reasonable length targets
- [ ] Warning logged if a scene is significantly under target
- [ ] Tests cover word count target calculation

---

## Issue 5: Continuity summaries don't preserve dialogue threads

**Labels**: `enhancement`, `build`, `prompt-engineering`

### Description

The continuity summary prompt (`prompts.py:183-188`) only asks for plot-focused summaries:

```
"Summarize the key events that occurred"
"Note any significant character development or revelations"
"Highlight any plot points that might be referenced later"
```

It doesn't ask the LLM to note:
- Character speech patterns or tonal shifts
- Open dialogue threads (promises, questions, threats)
- Emotional register or tension level at scene end
- Unresolved interpersonal dynamics

When the next scene receives "prior context," it has no information about conversational threads. This makes cross-scene dialogue continuity nearly impossible — characters can't reference what was said earlier.

### Proposed changes

Update the continuity summary prompt guidelines to include:

```python
"Note any open dialogue threads: promises made, questions asked, threats, unresolved arguments",
"Capture the emotional state of key characters at scene end",
"Mention any distinctive speech patterns or tonal shifts",
```

### Files to change

- `src/fabulae/features/build/prompts.py` — `build_continuity_system_prompt()` and `build_continuity_prompt()`

### Acceptance criteria

- [ ] Continuity summaries include dialogue thread information
- [ ] Continuity summaries capture character emotional state
- [ ] Generated prose shows improved cross-scene dialogue continuity
- [ ] Existing tests pass

---

## Issue 6: Enhanced mode hooks generated but never rendered in output

**Labels**: `enhancement`, `build`

### Description

The enhanced pipeline generates `SceneHook` objects with `hook_type` and `content`, stored in `SceneOutput.hook` and `ChapterOutput.hook`. However:

1. **Writer never renders hooks separately**: `writer.py` only writes `scene.content`. While hook content is assembled *into* `scene.content` by the scene builder (`scene_builder.py:434-439`), it's not styled or marked up as a hook.

2. **Dead CSS**: The HTML template defines a `.hook` CSS class (`writer.py:98-104`) that's never applied to any HTML element.

3. **Chapter hooks unused**: `ChapterOutput.hook` (set from first scene's hook) is never referenced in the writer.

### Proposed changes

1. **Render hooks with styling in HTML output**: Wrap hook content in `<div class="hook">` in the HTML writer.
2. **Render hooks with emphasis in markdown output**: Format hooks with italic or blockquote markers.
3. **Either use or remove `ChapterOutput.hook`**: If chapter-level hooks have a purpose (e.g., epigraphs), render them. Otherwise, remove the field to avoid confusion.

### Files to change

- `src/fabulae/features/build/writer.py` — `_format_chapter()`, scene rendering logic
- `src/fabulae/features/build/scene_builder.py` — hook assembly into content (if separating hook from content)
- `src/fabulae/features/build/schemas.py` — `ChapterOutput.hook` field (if removing)

### Acceptance criteria

- [ ] Hook content is visually distinct in at least HTML output format
- [ ] `.hook` CSS class is actually applied in HTML output
- [ ] `ChapterOutput.hook` is either rendered or removed
- [ ] Tests cover hook rendering in all output formats (md, txt, html)

---

## Issue 7: No "show don't tell" or prose craft instructions in prompts

**Labels**: `enhancement`, `build`, `prompt-engineering`

### Description

The build prompts contain technical writing guidance (POV, tense, style constraints) but lack fundamental creative craft instructions. LLMs tend to default to summary/narration without explicit craft guidance.

**Missing instructions:**

- **"Show don't tell"** — the most fundamental prose guideline. Without it, LLMs summarize emotions ("She felt sad") instead of demonstrating them through action and sensory detail ("Her hand trembled as she set down the cup").
- **Pacing guidance** — no instruction about varying sentence length, paragraph rhythm, or building/releasing tension within scenes.
- **Anti-purple-prose** — the prompt says "vivid" and "engaging", which some LLMs interpret as permission for excessive ornamentation.
- **Dialogue formatting** — no instruction about attribution style, paragraph breaks per speaker, or balancing dialogue with action beats.

### Proposed changes

Add craft instructions to `build_scene_system_prompt()` and `build_enhanced_scene_system_prompt()`:

```python
"SHOW, don't TELL: reveal emotions through actions, gestures, and sensory detail — not by naming them",
"Vary sentence length: short punchy sentences for tension, longer ones for reflection",
"Avoid purple prose: prefer precise, concrete language over ornate abstractions",
"Format dialogue with a new paragraph for each speaker; vary attribution (action beats, 'said', unattributed)",
```

### Files to change

- `src/fabulae/features/build/prompts.py` — `build_scene_system_prompt()`, `build_enhanced_scene_system_prompt()`
- Optionally `build_fragment_system_prompt()` for micro-prose

### Acceptance criteria

- [ ] System prompts include "show don't tell" instruction
- [ ] System prompts include pacing and anti-purple-prose guidance
- [ ] System prompts include dialogue formatting instructions
- [ ] Generated prose quality noticeably improves (manual review)
- [ ] Existing tests pass

---

## Issue 8: Short-story scene headers are bloated — wrong separator style

**Labels**: `enhancement`, `build`

### Description

For short stories (no chapters), scenes get `## {summary}` headers (`service.py:53-54`), producing multi-sentence headers that break the reading flow. Short stories should use subtle scene breaks, not titled sections.

Example current output:
```markdown
## Elena arrives at the old library to search for the missing manuscript. The librarian watches her suspiciously.

[prose content]

## After the confrontation, Elena escapes through the back entrance with the manuscript hidden in her coat.

[prose content]
```

Expected for short stories:
```markdown
[prose content]

* * *

[prose content]
```

### Proposed changes

1. **Format-aware scene separation**: In `_combine_scenes()` and the writer, detect the format:
   - `novel` / `novella`: Keep `## Title` headers (but fix the title — see Issue 2)
   - `short-story`: Use `* * *` or `---` scene breaks instead of titled headers

2. Pass `format` through to `_combine_scenes()` or make the writer format-aware.

### Files to change

- `src/fabulae/features/build/service.py` — `_combine_scenes()`, `_build_short_story()`
- `src/fabulae/features/build/writer.py` — scene rendering for short-story format

### Acceptance criteria

- [ ] Short stories use scene break markers (`* * *` or `---`) instead of titled headers
- [ ] Novels/novellas retain section headers (with proper short titles per Issue 2)
- [ ] All three output formats (md, txt, html) handle scene breaks correctly
- [ ] Tests cover format-specific scene separation

---

## Issue 9: No per-format prose differentiation in prompts

**Labels**: `enhancement`, `build`, `prompt-engineering`

### Description

All prose formats (novel, novella, short-story) use **identical prompts and builders**. A novella scene and a novel scene get exactly the same instructions. In practice:

- **Novels** should produce longer, more detailed scenes with expansive description and dialogue.
- **Novellas** should produce tighter, more focused prose with selective detail.
- **Short stories** should produce dense, economical prose where every word earns its place.

Currently the only structural difference is that novels have chapters and short stories don't. The prose style/density guidance is identical.

### Proposed changes

1. **Add format context to prompts**: Pass the project format to `build_scene_system_prompt()` and include format-specific guidelines:
   - Novel: "Write expansive prose with rich description, extended dialogue, and detailed inner monologue."
   - Novella: "Write focused prose that balances detail with economy. Every scene should serve double duty."
   - Short story: "Write tight, economical prose. Every sentence should advance plot or reveal character. Prefer implication over exposition."

2. **Format-specific word count defaults**: See Issue 4 — the word count targets should also vary by format.

### Files to change

- `src/fabulae/features/build/prompts.py` — `build_scene_system_prompt()`, `build_scene_prompt()`, `build_enhanced_scene_system_prompt()`, `build_enhanced_scene_prompt()`
- `src/fabulae/features/build/scene_builder.py` — pass format to prompt builders

### Acceptance criteria

- [ ] Scene prompts include format-specific prose guidance
- [ ] Novel, novella, and short-story produce noticeably different prose densities
- [ ] Format name is passed through from service to prompt builders
- [ ] Existing tests pass

---

## Issue 10: Standard scene prompts significantly weaker than enhanced

**Labels**: `enhancement`, `build`, `prompt-engineering`

### Description

The standard (non-enhanced) scene prompt is significantly weaker than the enhanced version. Key differences:

| Aspect | Standard | Enhanced |
|--------|----------|----------|
| Character detail | name, role, traits only | + desire, need, flaw |
| Location detail | name, facts list | + "sensory details for environment description" |
| Beat formatting | kind, summary, goal, conflict, outcome | + beat IDs, constraints |
| Dialogue guidance | 1 vague line | 3 specific lines |
| Hook system | none | 5 hook types with diversity tracking |
| Prose craft | basic ("vivid, engaging") | + "inner thought", "sensory details (visual, auditory, tactile, olfactory)" |

While enhanced is the default (`--enhanced` is `True`), anyone using `--no-enhanced` gets a substantially inferior prompt. The gap is too large — standard mode should still produce good prose.

### Proposed changes

Backport key quality improvements from enhanced to standard prompts:

1. **Character detail**: Use `detailed=True` in standard `build_scene_prompt()` (pass desire/need/flaw)
2. **Location detail**: Use `detailed=True` in standard `_format_location()` call
3. **Prose craft guidelines**: Add the enhanced system prompt's stronger craft lines to the standard system prompt
4. **Keep structural differences**: The hook system and beat-level JSON output remain enhanced-only

### Files to change

- `src/fabulae/features/build/prompts.py` — `build_scene_system_prompt()`, `build_scene_prompt()`

### Acceptance criteria

- [ ] Standard scene prompts include character desire/need/flaw
- [ ] Standard scene prompts include sensory location details
- [ ] Standard system prompt includes stronger prose craft guidelines
- [ ] Enhanced mode retains its structural advantages (hooks, beat tracking)
- [ ] Existing tests pass
