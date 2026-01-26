# Task: Language Guard Correction Prompts

**Priority:** Medium - improves multilingual output quality.
**Depends on:** None (language guard infrastructure already in place)

## Overview

The language guard currently detects wrong-language LLM output and retries by re-running the **same prompt** with a slightly reinforced system message. This is ineffective: the model already had the language instruction and ignored it, so repeating the request rarely changes the outcome.

Replace the blind re-prompt with a **correction prompt** that takes the wrong-language output and asks the LLM to translate it into the target language while preserving the structured output format. This turns the retry from "generate again, but harder" into "translate this specific text," which is a much simpler task that even small models handle reliably.

## Current Behavior

`run_with_language_guard()` in `src/fabulae/llm/language_guard.py`:

1. Calls `runner()` to get LLM output
2. Extracts text via `extract_text(output)`
3. Detects language via `lingua`
4. On mismatch, calls `reprompt(attempt)` which modifies the system prompt
5. Loops back to `runner()` — same user prompt, louder system prompt
6. The previous wrong-language output is **discarded entirely**

The `reprompt` callback in `src/fabulae/features/create/service.py` (line 250):

```python
def reprompt(attempt: int) -> None:
    guard_prompt = build_language_guard_prompt(expected_language)
    prompt_state["system"] = f"{system_prompt}\n\n{guard_prompt}\n\nRetry attempt: {attempt}"
```

This only appends the language guard instruction to the system prompt. The user prompt stays identical. The model's previous output is never fed back.

## Desired Behavior

On language mismatch:

1. Take the wrong-language structured output (the full JSON/Pydantic object)
2. Construct a **correction prompt** that includes the previous output and asks the LLM to translate all narrative text fields into the target language
3. The correction prompt must emphasize: translate the text, keep the structured output format intact (same JSON schema, same field names, same non-text field values)
4. Parse the corrected output with the same Pydantic model
5. Re-evaluate language on the corrected output

## Implementation Steps

### Step 1: Design the Correction Prompt
**Model: Opus**

Create a correction prompt template in `src/fabulae/prompts/language.py`:

```python
LANGUAGE_CORRECTION_TEMPLATE = (
    "The following output was generated in the wrong language. "
    "Translate ALL narrative text into {language_name} ({iso_code}). "
    "Keep the exact same JSON structure and field names. "
    "Only change the text content — preserve all IDs, numbers, and structural fields unchanged.\n\n"
    "Original output:\n{original_output}\n\n"
    "Return the corrected output in the same JSON format."
)
```

Key design decisions:
- The correction prompt replaces the original user prompt entirely
- The system prompt stays the same (with language guard appended)
- The original output is serialized as JSON and included verbatim

### Step 2: Extend `run_with_language_guard` Signature
**Model: Sonnet**

The current `reprompt` callback only receives `attempt: int`. The correction approach needs to pass the previous output back to the caller so it can construct the correction prompt.

Option A — Change the `reprompt` callback signature:

```python
reprompt: Callable[[int, T], None] | None = None
# reprompt(attempt, previous_output) — caller can build correction prompt from output
```

Option B — Add a separate `correct` callback:

```python
correct: Callable[[int, T], T | Awaitable[T]] | None = None
# correct(attempt, previous_output) — returns corrected output directly
```

Option B is cleaner because it separates the two strategies (re-prompt vs. correct) and lets the correction path run its own LLM call with a different prompt.

Update `language_guard.py` retry loop:

```python
while True:
    output = await _maybe_await(runner())
    text = extract_text(output)
    result = _evaluate_text(text, expected_code, resolved_config)
    if result.passed or result.skipped or attempt >= resolved_config.max_retries:
        return output, result
    attempt += 1
    if correct is not None:
        output = await _maybe_await(correct(attempt, output))
        text = extract_text(output)
        result = _evaluate_text(text, expected_code, resolved_config)
        if result.passed or result.skipped:
            return output, result
    elif reprompt is not None:
        reprompt(attempt)
```

### Step 3: Implement Correction in Create Service
**Model: Sonnet**

Update `_invoke_stage` in `src/fabulae/features/create/service.py`:

```python
async def correct(attempt: int, previous_output: T) -> T:
    # Serialize previous output to JSON
    if hasattr(previous_output, 'model_dump_json'):
        original_json = previous_output.model_dump_json(indent=2)
    else:
        original_json = str(previous_output)

    correction_prompt = build_language_correction_prompt(
        expected_language, original_json
    )
    guard_prompt = build_language_guard_prompt(expected_language)
    correction_system = f"{system_prompt}\n\n{guard_prompt}"

    agent = create_agent(result_type, correction_system, config)
    result = await agent.run(correction_prompt)
    return cast(T, result.output)
```

Pass `correct` instead of `reprompt` to `run_with_language_guard()`.

### Step 4: Add Correction Prompt Builder
**Model: Sonnet**

Add `build_language_correction_prompt()` to `src/fabulae/prompts/language.py`:

```python
def build_language_correction_prompt(iso_code: str, original_output: str) -> str:
    # Resolve language name from ISO code
    # Format LANGUAGE_CORRECTION_TEMPLATE
    # Return the correction prompt
```

### Step 5: Update Tests
**Model: Sonnet**

Update `tests/unit/llm_language_guard_test.py`:

1. Test that `correct` callback is called with the previous output on mismatch
2. Test that corrected output is re-evaluated for language
3. Test that `correct` takes precedence over `reprompt` when both provided
4. Test backward compatibility: existing `reprompt`-only callers still work

Add integration-level test in `tests/unit/features/create_service_test.py`:

1. Mock LLM to return English output on first call, German on correction call
2. Verify the correction prompt includes the original English output
3. Verify the final output is the corrected German version

### Step 6: Integrate Language Guard into Build Command
**Model: Sonnet**

The build command (`src/fabulae/features/build/`) currently does **not** use `run_with_language_guard()`. It only includes the language guard as a system prompt instruction in the system prompt builders (`build_scene_system_prompt`, `build_stanza_system_prompt`, etc.). This means wrong-language build output is never detected or corrected.

#### 6a: Add `--language` CLI flag to build command

Add an explicit `--language` option to `src/fabulae/features/build/cli.py`:

```python
language: Annotated[
    str | None,
    typer.Option("--language", "-l", help="Target language (ISO 639-1 code, e.g. 'de', 'fr'). Overrides style.yml."),
] = None,
```

Resolution order:
1. `--language` CLI flag (explicit override)
2. `project.style.language` (from `style.yml`)
3. `None` (no enforcement)

Pass the resolved language into `build_project()`.

#### 6b: Wire `run_with_language_guard` into scene_builder.py

Update `build_scene`, `build_fragment`, `build_stanza`, and `build_poem_from_lines` in `src/fabulae/features/build/scene_builder.py` to wrap their LLM calls with `run_with_language_guard()`, using the new `correct` callback.

Each builder function needs an `expected_language: str | None` parameter threaded from the service layer. When set, the output is detected and corrected on mismatch using the same correction prompt infrastructure from Steps 1-4.

#### 6c: Thread language through build service

Update `build_project()` and all format-specific builders (`_build_chaptered`, `_build_short_story`, `_build_micro_prose`, `_build_poem`) in `src/fabulae/features/build/service.py` to accept and forward `expected_language`.

#### 6d: Add build-specific tests

Add tests to `tests/unit/features/build/build_test.py`:

1. Test that `--language de` CLI flag is accepted and passed through
2. Test that language from `style.yml` is used when no CLI flag provided
3. Test that wrong-language scene output triggers the correction callback
4. Test that corrected output replaces the original in the final build

### Step 7: Update Files Table

See updated Files table below.

### Final Step: Opus Verification
**Model: Opus**

After all implementation steps are complete, switch to Opus model and verify:

1. **Code Quality Review:**
   - All changes follow codebase conventions
   - No duplicate code introduced
   - Backward compatibility preserved for existing `reprompt` callers
   - Type hints are complete

2. **Integration Check:**
   - All new code integrates properly with existing code
   - Imports are correct
   - No circular dependencies

3. **Test Verification:**
   - Run `uv run ruff check --fix && uv run mypy && uv run pytest`
   - All tests pass
   - No regressions introduced

4. **Manual Verification:**
   - Create a project with `language: de` in `style.yml`
   - Run `fabulae create` with a small model
   - Verify that wrong-language output triggers the correction path
   - Verify that the corrected output is in the target language

5. **Documentation Review:**
   - Review and update `CLAUDE.md` if architectural patterns changed
   - Update language guard section in Architecture docs

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/fabulae/prompts/language.py` | Modify | Add correction prompt template and builder |
| `src/fabulae/llm/language_guard.py` | Modify | Add `correct` callback support to retry loop |
| `src/fabulae/features/create/service.py` | Modify | Replace `reprompt` with `correct` in `_invoke_stage` |
| `src/fabulae/features/build/cli.py` | Modify | Add `--language` CLI flag |
| `src/fabulae/features/build/service.py` | Modify | Thread `expected_language` through all builders |
| `src/fabulae/features/build/scene_builder.py` | Modify | Wrap LLM calls with `run_with_language_guard` + `correct` |
| `tests/unit/llm_language_guard_test.py` | Modify | Add correction callback tests |
| `tests/unit/features/create_service_test.py` | Modify | Add integration test for correction flow |
| `tests/unit/features/build/build_test.py` | Modify | Add `--language` flag and correction tests |

## Acceptance Criteria

### Core: Correction prompt infrastructure
- [ ] Wrong-language output is passed back to LLM as correction input
- [ ] Correction prompt emphasizes translating text while preserving JSON structure
- [ ] Corrected output is re-evaluated for language compliance
- [ ] Existing `reprompt` callback still works for backward compatibility
- [ ] `correct` callback takes precedence over `reprompt` when both provided

### Build command: Language enforcement
- [ ] `fabulae build --language de` overrides `style.yml` language
- [ ] Build uses `style.yml` language when no `--language` flag provided
- [ ] All build format builders (chaptered, short-story, micro-prose, poem) enforce language via `run_with_language_guard`
- [ ] Wrong-language build output triggers the correction flow

### Quality
- [ ] All existing tests pass without modification
- [ ] New tests cover the correction flow for both create and build
- [ ] `ruff check`, `mypy`, and `pytest` pass

## Notes

- The correction approach is fundamentally different from re-prompting: translation is a simpler task than generation, so even small models handle it reliably
- Keep `reprompt` as a fallback for callers that don't provide structured output (where serializing the previous output isn't straightforward)
- `max_retries` still applies: if correction also fails language detection, the loop stops after the configured number of attempts
- The `--language` flag for build mirrors the `--idea-language` flag in create, giving users explicit control when `style.yml` is absent or they want to override it
