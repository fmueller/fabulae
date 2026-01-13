# Fabulae `create` Command Refactoring Plan

## Overview

This document contains a detailed, step-by-step implementation plan for refactoring the `create` command. Each step is designed to be small, testable, and self-contained.

---

## Phase 1: Foundation Infrastructure

### Step 1.1: Create ErrorMode Enum and StageResult Dataclass
**Model: Haiku**

Create the basic data structures for unified stage execution.

**Tasks:**
- [ ] Create `ErrorMode` enum with values: `STRICT`, `WARN`, `STRICT_THEN_WARN`
- [ ] Create `StageResult[T]` dataclass with fields: `output: T`, `warnings: list[str]`, `attempts: int`
- [ ] Add to `src/fabulae/features/create/service.py`

**Tests:**
- [ ] Test `ErrorMode` enum values exist
- [ ] Test `StageResult` can be instantiated with various types
- [ ] Test `StageResult` fields are accessible

**Acceptance Criteria:**
- Enums and dataclasses importable from service module
- All tests pass

---

### Step 1.2: Implement Unified `run_stage()` Function
**Model: Sonnet**

Consolidate the four existing wrapper functions into one.

**Tasks:**
- [ ] Implement `run_stage()` with all parameters from existing functions
- [ ] Handle `ErrorMode.STRICT`: raise after max retries
- [ ] Handle `ErrorMode.WARN`: warn and return last output
- [ ] Handle `ErrorMode.STRICT_THEN_WARN`: try strict, fall back to warn
- [ ] Integrate language guard logic
- [ ] Keep old functions temporarily (mark deprecated)

**Tests:**
- [ ] Test `STRICT` mode raises `CreateProjectError` after retries
- [ ] Test `WARN` mode returns last output with warning
- [ ] Test `STRICT_THEN_WARN` mode behavior
- [ ] Test retry logic appends error to prompt
- [ ] Test language guard integration
- [ ] Test successful execution returns `StageResult`

**Acceptance Criteria:**
- New function passes all test cases
- Old functions still work (not yet removed)

---

### Step 1.3: Migrate Existing Call Sites to `run_stage()`
**Model: Sonnet**

Update all existing usages to use the new unified function.

**Tasks:**
- [ ] Identify all calls to `_run_stage_with_validation()`
- [ ] Identify all calls to `_run_stage_with_validation_or_warn()`
- [ ] Identify all calls to `_run_stage_with_validation_and_warning()`
- [ ] Migrate each call site to use `run_stage()` with appropriate `ErrorMode`
- [ ] Verify behavior unchanged

**Tests:**
- [ ] Existing integration tests still pass
- [ ] Existing unit tests still pass
- [ ] Manual smoke test of `create` command

**Acceptance Criteria:**
- All call sites migrated
- No references to old function names in active code paths
- All existing tests pass

---

### Step 1.4: Remove Deprecated Stage Wrapper Functions
**Model: Haiku**

Clean up the old functions.

**Tasks:**
- [ ] Remove `_run_stage()` (base function)
- [ ] Remove `_run_stage_with_validation()`
- [ ] Remove `_run_stage_with_validation_or_warn()`
- [ ] Remove `_run_stage_with_validation_and_warning()`
- [ ] Update imports if needed

**Tests:**
- [ ] All existing tests still pass
- [ ] No import errors

**Acceptance Criteria:**
- Old functions deleted (~120 lines removed)
- Codebase compiles and tests pass

---

### Step 1.5: Create `ids.py` Module with ID Generation Functions
**Model: Haiku**

Create the module for sequential ID generation.

**Tasks:**
- [ ] Create `src/fabulae/features/create/ids.py`
- [ ] Implement `generate_id(entity_type: str, index: int) -> str`
- [ ] Implement `generate_beat_id(scene_id: str, beat_index: int) -> str`
- [ ] Implement `generate_chapter_id(index: int) -> str`
- [ ] Implement `generate_scene_id(index: int) -> str`
- [ ] Implement `generate_character_id(index: int) -> str`
- [ ] Implement `generate_location_id(index: int) -> str`
- [ ] Implement `generate_world_fact_id(index: int) -> str`
- [ ] Implement `generate_fragment_id(index: int) -> str`
- [ ] Implement `generate_stanza_id(index: int) -> str`

**Tests:**
- [ ] Test `generate_id("scene", 1)` returns `"scene-01"`
- [ ] Test `generate_id("scene", 10)` returns `"scene-10"`
- [ ] Test `generate_id("scene", 100)` returns `"scene-100"`
- [ ] Test `generate_beat_id("scene-01", 1)` returns `"scene-01-beat-01"`
- [ ] Test all specialized generators return correct format

**Acceptance Criteria:**
- All ID generators produce consistent `{type}-{nn}` format
- Zero-padded to at least 2 digits

---

### Step 1.6: Create `ProjectIds` Dataclass
**Model: Haiku**

Create the container for all project IDs.

**Tasks:**
- [ ] Create `ProjectIds` dataclass in `ids.py`
- [ ] Add fields: `chapters`, `scenes`, `scene_to_chapter`, `scene_beats`
- [ ] Add fields: `characters`, `character_slot_mapping`
- [ ] Add fields: `locations`, `location_slot_mapping`
- [ ] Add fields: `world_facts`, `fragments`, `stanzas`

**Tests:**
- [ ] Test `ProjectIds` instantiation with empty defaults
- [ ] Test `ProjectIds` instantiation with populated fields
- [ ] Test field access

**Acceptance Criteria:**
- Dataclass is fully typed
- All fields have sensible defaults

---

### Step 1.7: Implement `allocate_prose_ids()` Function
**Model: Sonnet**

Implement the main ID allocation function for prose formats.

**Tasks:**
- [ ] Implement `allocate_prose_ids()` function
- [ ] Generate chapter IDs based on count
- [ ] Generate scene IDs distributed across chapters
- [ ] Map scenes to chapters in `scene_to_chapter`
- [ ] Generate beat IDs for each scene
- [ ] Generate character IDs mapped to slots
- [ ] Generate location IDs mapped to slots
- [ ] Generate extra world fact IDs

**Tests:**
- [ ] Test with 3 chapters, [2, 3, 2] scenes, [3, 3, 4, 3, 2, 3, 4] beats
- [ ] Verify chapter IDs: `["chapter-01", "chapter-02", "chapter-03"]`
- [ ] Verify scene IDs: `["scene-01", ..., "scene-07"]`
- [ ] Verify scene-to-chapter mapping is correct
- [ ] Verify beat IDs are scoped to scenes
- [ ] Verify character slot mapping works
- [ ] Verify location slot mapping works

**Acceptance Criteria:**
- All IDs generated correctly
- Slot mappings populated
- No duplicate IDs

---

### Step 1.8: Implement `allocate_micro_prose_ids()` and `allocate_poem_ids()`
**Model: Haiku**

Implement simpler ID allocation for non-prose formats.

**Tasks:**
- [ ] Implement `allocate_micro_prose_ids(num_fragments: int) -> ProjectIds`
- [ ] Implement `allocate_poem_ids(num_stanzas: int) -> ProjectIds`

**Tests:**
- [ ] Test `allocate_micro_prose_ids(3)` returns 3 fragment IDs
- [ ] Test `allocate_poem_ids(4)` returns 4 stanza IDs
- [ ] Verify other fields are empty lists

**Acceptance Criteria:**
- Functions return properly structured `ProjectIds`

---

### Step 1.9: Implement `extend_ids_for_enrichment()`
**Model: Haiku**

Implement function to add more IDs during enrichment pass.

**Tasks:**
- [ ] Implement `extend_ids_for_enrichment()` function
- [ ] Add new character IDs starting after existing
- [ ] Add new location IDs starting after existing
- [ ] Add new world fact IDs starting after existing
- [ ] Return updated `ProjectIds`

**Tests:**
- [ ] Test extending from 3 characters by 2 gives `["character-01", ..., "character-05"]`
- [ ] Test extending preserves existing slot mappings
- [ ] Test extending with 0 extras returns unchanged

**Acceptance Criteria:**
- New IDs continue sequence
- Existing data preserved

---

### Step 1.10: Create `SceneContext` Dataclass
**Model: Haiku**

Extract scene generation context into explicit dataclass.

**Tasks:**
- [ ] Create `SceneContext` dataclass in `service.py` (or new file)
- [ ] Add all fields needed for scene generation
- [ ] Document each field's purpose

**Tests:**
- [ ] Test instantiation with all required fields
- [ ] Test all fields accessible

**Acceptance Criteria:**
- Dataclass captures all context needed for scene generation
- Fully typed

---

### Step 1.11: Refactor Scene Loop to Use `SceneContext`
**Model: Sonnet**

Remove closure captures by using explicit context.

**Tasks:**
- [ ] Create `SceneContext` instance for each scene
- [ ] Pass context to normalize function instead of capturing
- [ ] Pass context to validate function instead of capturing
- [ ] Remove nested closure definitions
- [ ] Extract to standalone function if helpful

**Tests:**
- [ ] Existing scene generation tests pass
- [ ] Integration test: full `create` command works
- [ ] Verify no closure captures of mutable state

**Acceptance Criteria:**
- Scene loop no longer uses closures capturing outer variables
- Behavior unchanged
- Tests pass

---

## Phase 2: Story Shapes

### Step 2.1: Create Story Shape Models
**Model: Sonnet**

Add new models to `models.py`.

**Tasks:**
- [ ] Create `CharacterSlot` model with: `slot`, `needs`, `can_merge_with`, `optional`
- [ ] Create `SettingSlot` model with: `slot`, `needs`, `used_in`, `optional`
- [ ] Create `RequiredBeat` model with: `type`, `description`, `position`, `flexibility`
- [ ] Create `VariationPoint` model with: `type`, `description`, `probability`, `position`
- [ ] Create `StoryShape` model combining all above
- [ ] Add appropriate validators

**Tests:**
- [ ] Test `CharacterSlot` validation (required fields)
- [ ] Test `SettingSlot` validation
- [ ] Test `RequiredBeat` position literals
- [ ] Test `VariationPoint` probability bounds
- [ ] Test `StoryShape` with full example data
- [ ] Test `StoryShape` serialization/deserialization

**Acceptance Criteria:**
- All models defined with proper typing
- Validation works correctly
- Can round-trip through YAML

---

### Step 2.2: Create Story Shapes Data Directory
**Model: Haiku**

Set up the directory structure for shape files.

**Tasks:**
- [ ] Create `src/fabulae/data/` directory
- [ ] Create `src/fabulae/data/story_shapes/` directory
- [ ] Create empty `__init__.py` files as needed
- [ ] Update `pyproject.toml` to include data files in package

**Tests:**
- [ ] Verify directory exists after install
- [ ] Verify data directory is included in package

**Acceptance Criteria:**
- Directory structure in place
- Package includes data files

---

### Step 2.3: Write "Hero's Journey" Story Shape
**Model: Opus**

Create the first and most complex story shape.

**Tasks:**
- [ ] Create `src/fabulae/data/story_shapes/heros-journey.yml`
- [ ] Define 8-10 required beats (call, threshold, tests, ordeal, reward, return, etc.)
- [ ] Define character slots (hero, mentor, herald, threshold guardian, shapeshifter, shadow, ally)
- [ ] Define setting slots (ordinary world, special world, innermost cave, etc.)
- [ ] Define themes, motifs, tone
- [ ] Define variation points

**Tests:**
- [ ] Test YAML loads without error
- [ ] Test validates against `StoryShape` model
- [ ] Test all required fields present

**Acceptance Criteria:**
- Complete, well-crafted hero's journey shape
- Validates correctly

---

### Step 2.4: Write "Betrayal Arc" Story Shape
**Model: Opus**

Create the betrayal-focused story shape.

**Tasks:**
- [ ] Create `src/fabulae/data/story_shapes/betrayal-arc.yml`
- [ ] Define required beats (trust, doubt, revelation, confrontation, aftermath)
- [ ] Define character slots (protagonist, betrayer, witness)
- [ ] Define setting slots (trust-space, revelation-space, confrontation-space)
- [ ] Define themes, motifs, tone
- [ ] Define variation points

**Tests:**
- [ ] Test YAML loads without error
- [ ] Test validates against `StoryShape` model

**Acceptance Criteria:**
- Complete betrayal arc shape

---

### Step 2.5: Write "Coming of Age" Story Shape
**Model: Opus**

**Tasks:**
- [ ] Create `src/fabulae/data/story_shapes/coming-of-age.yml`
- [ ] Define beats: innocence, challenge, failure, growth, maturity
- [ ] Define character slots: young protagonist, guide figure, peer, antagonist
- [ ] Define setting slots, themes, motifs

**Tests:**
- [ ] YAML loads and validates

---

### Step 2.6: Write "Mystery Reveal" Story Shape
**Model: Opus**

**Tasks:**
- [ ] Create `src/fabulae/data/story_shapes/mystery-reveal.yml`
- [ ] Define beats: hook, investigation, clues, red herring, revelation, resolution
- [ ] Define character slots: detective/investigator, suspect, victim, witness
- [ ] Define setting slots, themes, motifs

**Tests:**
- [ ] YAML loads and validates

---

### Step 2.7: Write "Romance Arc" Story Shape
**Model: Opus**

**Tasks:**
- [ ] Create `src/fabulae/data/story_shapes/romance-arc.yml`
- [ ] Define beats: meet, attraction, obstacle, crisis, declaration, union
- [ ] Define character slots: lover-a, lover-b, rival, confidant
- [ ] Define setting slots, themes, motifs

**Tests:**
- [ ] YAML loads and validates

---

### Step 2.8: Write "Fall and Redemption" Story Shape
**Model: Opus**

**Tasks:**
- [ ] Create `src/fabulae/data/story_shapes/fall-redemption.yml`
- [ ] Define beats: status, temptation, fall, bottom, catalyst, climb, redemption
- [ ] Define character slots, setting slots, themes, motifs

**Tests:**
- [ ] YAML loads and validates

---

### Step 2.9: Write "Fish Out of Water" Story Shape
**Model: Opus**

**Tasks:**
- [ ] Create `src/fabulae/data/story_shapes/fish-out-of-water.yml`
- [ ] Define beats: displacement, confusion, struggle, adaptation, mastery
- [ ] Define character slots, setting slots, themes, motifs

**Tests:**
- [ ] YAML loads and validates

---

### Step 2.10: Write "Revenge Quest" Story Shape
**Model: Opus**

**Tasks:**
- [ ] Create `src/fabulae/data/story_shapes/revenge-quest.yml`
- [ ] Define beats: wrong, vow, pursuit, cost, reckoning, aftermath
- [ ] Define character slots, setting slots, themes, motifs

**Tests:**
- [ ] YAML loads and validates

---

### Step 2.11: Write "Forbidden Knowledge" Story Shape
**Model: Opus**

**Tasks:**
- [ ] Create `src/fabulae/data/story_shapes/forbidden-knowledge.yml`
- [ ] Define beats: curiosity, discovery, obsession, corruption, choice, consequence
- [ ] Define character slots, setting slots, themes, motifs

**Tests:**
- [ ] YAML loads and validates

---

### Step 2.12: Write "Transformation" Story Shape
**Model: Opus**

**Tasks:**
- [ ] Create `src/fabulae/data/story_shapes/transformation.yml`
- [ ] Define beats: stasis, catalyst, resistance, struggle, surrender, emergence
- [ ] Define character slots, setting slots, themes, motifs

**Tests:**
- [ ] YAML loads and validates

---

### Step 2.13: Create Shape Loader Module
**Model: Sonnet**

Create module to load story shapes from files.

**Tasks:**
- [ ] Create `src/fabulae/features/create/shapes/__init__.py`
- [ ] Create `src/fabulae/features/create/shapes/loader.py`
- [ ] Implement `load_shape(shape_id: str) -> StoryShape`
- [ ] Implement `load_shape_from_file(path: Path) -> StoryShape`
- [ ] Implement `load_all_shapes() -> list[StoryShape]`
- [ ] Implement `get_shape_ids() -> list[str]`
- [ ] Handle missing shape errors gracefully

**Tests:**
- [ ] Test `load_shape("betrayal-arc")` returns valid shape
- [ ] Test `load_shape("nonexistent")` raises appropriate error
- [ ] Test `load_shape_from_file()` with custom YAML
- [ ] Test `load_all_shapes()` returns all 10 shapes
- [ ] Test `get_shape_ids()` returns all IDs

**Acceptance Criteria:**
- Can load any built-in shape by ID
- Can load custom shapes from file path
- Proper error handling

---

### Step 2.14: Create Shape Selector Module
**Model: Sonnet**

Create module to auto-select shape based on idea.

**Tasks:**
- [ ] Create `src/fabulae/features/create/shapes/selector.py`
- [ ] Implement `select_shape_for_idea(idea: str, config: LLMConfig) -> StoryShape`
- [ ] Create prompt for shape selection
- [ ] Parse LLM response to get shape ID
- [ ] Fall back to default shape if selection fails

**Tests:**
- [ ] Test selection with betrayal-themed idea returns `betrayal-arc`
- [ ] Test selection with mystery idea returns `mystery-reveal`
- [ ] Test fallback when LLM returns invalid shape
- [ ] Mock LLM for deterministic testing

**Acceptance Criteria:**
- Can auto-select appropriate shape
- Graceful fallback behavior

---

### Step 2.15: Add Shape CLI Commands
**Model: Sonnet**

Add CLI commands for listing and showing shapes.

**Tasks:**
- [ ] Add `shapes` command to list all available shapes
- [ ] Add `shape <id>` command to show shape details
- [ ] Format output nicely (beats, slots, themes)
- [ ] Handle unknown shape ID error

**Tests:**
- [ ] Test `shapes` command output contains all 10 shapes
- [ ] Test `shape betrayal-arc` shows correct details
- [ ] Test `shape nonexistent` shows error message

**Acceptance Criteria:**
- CLI commands work correctly
- Output is readable and helpful

---

### Step 2.16: Add `--shape` and `--shape-file` Flags to Create Command
**Model: Sonnet**

Integrate shape selection into create command.

**Tasks:**
- [ ] Add `--shape` option (string, shape ID)
- [ ] Add `--shape-file` option (Path, custom shape file)
- [ ] Validate mutual exclusivity or precedence
- [ ] Load shape in create command
- [ ] Pass shape to generation pipeline (placeholder for now)

**Tests:**
- [ ] Test `--shape betrayal-arc` loads correct shape
- [ ] Test `--shape-file custom.yml` loads custom shape
- [ ] Test both flags together (define expected behavior)
- [ ] Test invalid shape ID error message

**Acceptance Criteria:**
- Flags work correctly
- Shape loaded and available for pipeline

---

## Phase 3: Sequential IDs Integration

### Step 3.1: Update Schema Examples to Use Sequential IDs
**Model: Haiku**

Update prompt examples to show sequential ID format.

**Tasks:**
- [ ] Update character example: `"id": "character-01"`
- [ ] Update scene example: `"id": "scene-01"`
- [ ] Update beat example: `"id": "scene-01-beat-01"`
- [ ] Update chapter example: `"id": "chapter-01"`
- [ ] Update location/world fact examples
- [ ] Update fragment and stanza examples

**Tests:**
- [ ] Verify all schema examples in prompts use new format
- [ ] Manual review of prompt output

**Acceptance Criteria:**
- All examples show sequential ID format

---

### Step 3.2: Update Prompts to Provide IDs Instead of Requesting Them
**Model: Sonnet**

Modify prompts to give pre-assigned IDs.

**Tasks:**
- [ ] Update `build_character_prompt()` to include assigned ID
- [ ] Update `build_scene_prompt()` to include assigned ID
- [ ] Update `build_world_fact_prompt()` to include assigned ID
- [ ] Add instruction: "Use the provided ID exactly, do not change it"
- [ ] Update all other entity prompts similarly

**Tests:**
- [ ] Test prompt contains provided ID
- [ ] Test instruction about keeping ID is present
- [ ] Integration test: LLM returns same ID we provided

**Acceptance Criteria:**
- All prompts provide IDs
- Clear instruction to preserve ID

---

### Step 3.3: Create Simple ID Validation Function
**Model: Haiku**

Replace complex normalization with simple validation.

**Tasks:**
- [ ] Create `validate_id_unchanged(output_id: str, expected_id: str) -> str | None`
- [ ] Return error message if IDs don't match
- [ ] Return `None` if valid

**Tests:**
- [ ] Test matching IDs return `None`
- [ ] Test mismatched IDs return error message
- [ ] Test error message includes both IDs

**Acceptance Criteria:**
- Simple validation function works

---

### Step 3.4: Create Reference Validation Functions
**Model: Sonnet**

Replace silent filtering with strict validation.

**Tasks:**
- [ ] Create `validate_character_references(refs: list[str], available: list[str]) -> str | None`
- [ ] Create `validate_location_reference(ref: str | None, available: list[str]) -> str | None`
- [ ] Create `validate_world_fact_references(refs: list[str], available: list[str]) -> str | None`
- [ ] Return clear error messages listing available IDs

**Tests:**
- [ ] Test valid references return `None`
- [ ] Test invalid reference returns error with available list
- [ ] Test empty references are valid
- [ ] Test `None` location is valid

**Acceptance Criteria:**
- Strict validation with helpful errors

---

### Step 3.5: Remove `_normalize_id()` and Related Functions
**Model: Haiku**

Delete the normalization code.

**Tasks:**
- [ ] Delete `_normalize_id()`
- [ ] Delete `_normalize_id_list()`
- [ ] Delete `_normalize_character_plan_output()`
- [ ] Delete `_normalize_character_output()`
- [ ] Delete `_normalize_world_plan_output()`
- [ ] Delete `_normalize_world_fact_output()`
- [ ] Delete `_normalize_plot_outline_output()`
- [ ] Delete `_normalize_scene_output()`
- [ ] Delete `_normalize_fragment_plan_output()`
- [ ] Delete `_normalize_fragment_output()`
- [ ] Delete `_normalize_poem_plan_output()`
- [ ] Delete `_normalize_stanza_output()`
- [ ] Delete pattern-related normalize functions

**Tests:**
- [ ] Verify functions are removed
- [ ] Verify no import errors
- [ ] Note: Some tests will fail until next step

**Acceptance Criteria:**
- ~120 lines of normalization code removed

---

### Step 3.6: Update Generation Pipeline to Use New Validation
**Model: Sonnet**

Replace normalization calls with validation calls.

**Tasks:**
- [ ] Update character generation to validate ID unchanged
- [ ] Update scene generation to validate ID unchanged
- [ ] Update scene generation to validate references strictly
- [ ] Update all other entity generation similarly
- [ ] Remove reference filtering code (lines 1836-1862 area)

**Tests:**
- [ ] Test character with wrong ID triggers retry
- [ ] Test scene with invalid character ref triggers retry
- [ ] Test valid generation succeeds
- [ ] Integration test: full create command works

**Acceptance Criteria:**
- Pipeline uses validation instead of normalization
- Invalid IDs cause retries, not silent fixes

---

### Step 3.7: Update Tests for New ID Behavior
**Model: Sonnet**

Fix tests that relied on normalization.

**Tasks:**
- [ ] Update tests that expected normalized IDs
- [ ] Update tests that expected silent reference filtering
- [ ] Add new tests for strict validation behavior
- [ ] Remove tests for deleted normalize functions

**Tests:**
- [ ] All unit tests pass
- [ ] All integration tests pass

**Acceptance Criteria:**
- Test suite passes
- Test coverage maintained

---

## Phase 4: Variation System

### Step 4.1: Create Variation Config and Data Classes
**Model: Haiku**

Create basic data structures for variation system.

**Tasks:**
- [ ] Create `src/fabulae/features/create/variation.py`
- [ ] Create `VariationConfig` dataclass with probability fields
- [ ] Create `SceneVariation` dataclass
- [ ] Create `ProjectVariation` dataclass

**Tests:**
- [ ] Test dataclass instantiation
- [ ] Test default values
- [ ] Test field access

**Acceptance Criteria:**
- Data structures defined and typed

---

### Step 4.2: Implement Scene Position Assignment
**Model: Haiku**

Implement logic to determine narrative position of scenes.

**Tasks:**
- [ ] Implement `_assign_scene_positions(scene_ids: list[str]) -> dict[str, str]`
- [ ] Map scenes to "early", "middle", "late", "climax" based on position
- [ ] Use percentage thresholds (25%, 70%, 90%)

**Tests:**
- [ ] Test 10 scenes: first 2-3 are "early", middle are "middle", etc.
- [ ] Test single scene is "climax"
- [ ] Test two scenes: one "early", one "climax"

**Acceptance Criteria:**
- Position assignment works correctly

---

### Step 4.3: Implement Filler Beat Selection
**Model: Sonnet**

Implement position-aware filler beat selection.

**Tasks:**
- [ ] Implement `_select_filler_beats(count: int, position: str) -> list[str]`
- [ ] Weight beat kinds by position (setup early, escalation late, etc.)
- [ ] Use shape's `filler_beat_kinds` pool
- [ ] Use RNG for randomization

**Tests:**
- [ ] Test "early" position favors setup/bridge beats
- [ ] Test "climax" position favors confrontation/turn beats
- [ ] Test with seeded RNG for reproducibility
- [ ] Test count matches requested

**Acceptance Criteria:**
- Filler beats selected appropriately for position

---

### Step 4.4: Implement Complication Type Selection
**Model: Haiku**

Implement random complication type selection.

**Tasks:**
- [ ] Implement `_select_complication_type() -> str`
- [ ] Define complication types list
- [ ] Random selection from list

**Tests:**
- [ ] Test returns valid complication type
- [ ] Test with seeded RNG

**Acceptance Criteria:**
- Complication selection works

---

### Step 4.5: Implement Subplot Seed Generation
**Model: Haiku**

Implement random subplot seed generation.

**Tasks:**
- [ ] Implement `_generate_subplot_seed() -> str`
- [ ] Define subplot seed types list
- [ ] Random selection from list

**Tests:**
- [ ] Test returns valid subplot seed
- [ ] Test with seeded RNG

**Acceptance Criteria:**
- Subplot seed generation works

---

### Step 4.6: Implement `VariationEngine` Class
**Model: Sonnet**

Implement the main variation engine.

**Tasks:**
- [ ] Create `VariationEngine` class
- [ ] Initialize with `StoryShape` and `VariationConfig`
- [ ] Implement `generate_project_variation()` method
- [ ] Generate `SceneVariation` for each scene
- [ ] Track character focus distribution for balance
- [ ] Collect subplot seeds

**Tests:**
- [ ] Test with seeded RNG for reproducibility
- [ ] Test complication probability (run many times, check distribution)
- [ ] Test character moment distribution is balanced
- [ ] Test subplot seeds only in early/middle scenes

**Acceptance Criteria:**
- Variation engine generates consistent, controllable randomness

---

### Step 4.7: Add `--variation` CLI Flag
**Model: Haiku**

Add CLI control for variation level.

**Tasks:**
- [ ] Add `--variation` option (float, 0.0-1.0, default 0.5)
- [ ] Map variation level to `VariationConfig` probabilities
- [ ] Pass to generation pipeline

**Tests:**
- [ ] Test `--variation 0.0` minimizes randomness
- [ ] Test `--variation 1.0` maximizes randomness
- [ ] Test default value works

**Acceptance Criteria:**
- CLI flag controls variation level

---

## Phase 5: Pipeline Split

### Step 5.1: Create Pipelines Directory Structure
**Model: Haiku**

Set up the directory for format-specific pipelines.

**Tasks:**
- [ ] Create `src/fabulae/features/create/pipelines/`
- [ ] Create `__init__.py`
- [ ] Create empty `prose.py`, `micro_prose.py`, `poem.py`

**Tests:**
- [ ] Verify imports work

**Acceptance Criteria:**
- Directory structure in place

---

### Step 5.2: Extract Shared Utilities to Service Module
**Model: Sonnet**

Identify and organize shared code.

**Tasks:**
- [ ] Identify functions used by multiple pipelines
- [ ] Keep in `service.py`: `run_stage()`, `ErrorMode`, `StageResult`
- [ ] Keep in `service.py`: `CreateProjectError`, helpers
- [ ] Export from `service.py` for pipeline imports

**Tests:**
- [ ] Verify exports work
- [ ] No circular imports

**Acceptance Criteria:**
- Shared utilities accessible to all pipelines

---

### Step 5.3: Implement Prose Pipeline Skeleton
**Model: Sonnet**

Create the prose pipeline structure.

**Tasks:**
- [ ] Create `generate_prose()` async function
- [ ] Define function signature with all parameters
- [ ] Add pass 1, 2, 3 structure as comments
- [ ] Implement basic flow calling existing functions
- [ ] Return `Project`

**Tests:**
- [ ] Test function is callable
- [ ] Integration test with mock LLM

**Acceptance Criteria:**
- Prose pipeline structure in place
- Can be called from main service

---

### Step 5.4: Implement Micro-Prose Pipeline
**Model: Sonnet**

Create the simplified micro-prose pipeline.

**Tasks:**
- [ ] Create `generate_micro_prose()` async function
- [ ] Implement: Style → Fragment Intent → Fragments
- [ ] Use `allocate_micro_prose_ids()`
- [ ] No story shapes, minimal structure

**Tests:**
- [ ] Test generates fragments
- [ ] Test correct number of fragments
- [ ] Test IDs are sequential

**Acceptance Criteria:**
- Micro-prose pipeline works independently

---

### Step 5.5: Implement Poem Pipeline
**Model: Sonnet**

Create the form-focused poem pipeline.

**Tasks:**
- [ ] Create `generate_poem()` async function
- [ ] Implement: Style → Poetic Form → Stanzas
- [ ] Use `allocate_poem_ids()`
- [ ] No story shapes, form-driven

**Tests:**
- [ ] Test generates stanzas
- [ ] Test correct number of stanzas
- [ ] Test IDs are sequential

**Acceptance Criteria:**
- Poem pipeline works independently

---

### Step 5.6: Update Main Service to Dispatch by Format
**Model: Sonnet**

Make main function a thin dispatcher.

**Tasks:**
- [ ] Update `generate_project_from_idea()` to check format
- [ ] Dispatch to `generate_prose()` for novel/novella/short-story
- [ ] Dispatch to `generate_micro_prose()` for micro-prose
- [ ] Dispatch to `generate_poem()` for poem
- [ ] Remove format-specific code from main function

**Tests:**
- [ ] Test dispatch to prose for "novel"
- [ ] Test dispatch to micro-prose for "micro-prose"
- [ ] Test dispatch to poem for "poem"
- [ ] Integration tests for all formats

**Acceptance Criteria:**
- Main function is small (~50 lines)
- Format-specific logic in separate files

---

## Phase 6: Plot-First Reorder

### Step 6.1: Implement `generate_outline_structure()`
**Model: Sonnet**

Generate structure counts before content.

**Tasks:**
- [ ] Create function to determine: num_chapters, scenes_per_chapter, beats_per_scene
- [ ] Use story shape to guide structure
- [ ] Use format ranges for constraints
- [ ] Return structure object (not full outline)

**Tests:**
- [ ] Test novel format gets appropriate counts
- [ ] Test short-story format gets fewer counts
- [ ] Test structure respects shape's beat count needs

**Acceptance Criteria:**
- Structure determined before content generation

---

### Step 6.2: Implement `generate_outline_content()`
**Model: Sonnet**

Fill pre-allocated IDs with content.

**Tasks:**
- [ ] Create function to generate chapter titles/summaries
- [ ] Generate scene summaries for pre-allocated scene IDs
- [ ] Use story shape for guidance
- [ ] IDs are provided, not generated

**Tests:**
- [ ] Test all provided IDs appear in output
- [ ] Test no new IDs created
- [ ] Test content is relevant to idea

**Acceptance Criteria:**
- Outline content fills pre-assigned IDs

---

### Step 6.3: Implement `generate_characters_from_slots()`
**Model: Sonnet**

Generate characters to fill shape slots.

**Tasks:**
- [ ] Create function that takes character slots and IDs
- [ ] For each slot, generate character with pre-assigned ID
- [ ] Use slot's `needs` as generation guidance
- [ ] Handle optional slots

**Tests:**
- [ ] Test character generated for each required slot
- [ ] Test character has assigned ID
- [ ] Test character meets slot needs (manual inspection)
- [ ] Test optional slots handled correctly

**Acceptance Criteria:**
- Characters serve specific story functions

---

### Step 6.4: Implement `generate_world_from_slots()`
**Model: Sonnet**

Generate world elements to fill shape slots.

**Tasks:**
- [ ] Create function that takes setting slots and IDs
- [ ] For each slot, generate location with pre-assigned ID
- [ ] Use slot's `needs` as generation guidance
- [ ] Generate additional world facts if needed

**Tests:**
- [ ] Test location generated for each required slot
- [ ] Test location has assigned ID
- [ ] Test location meets slot needs
- [ ] Test extra world facts generated

**Acceptance Criteria:**
- World elements serve specific story functions

---

### Step 6.5: Implement `assign_required_beats_to_scenes()`
**Model: Sonnet**

Map shape's required beats to scenes.

**Tasks:**
- [ ] Create function that assigns beats to scenes
- [ ] Respect position hints (early beats to early scenes, etc.)
- [ ] Ensure all required beats assigned
- [ ] Use RNG for flexibility within constraints

**Tests:**
- [ ] Test all required beats are assigned
- [ ] Test "early" beats go to early scenes
- [ ] Test "climax" beats go to final scenes
- [ ] Test with seeded RNG for reproducibility

**Acceptance Criteria:**
- Beat assignment respects shape constraints

---

### Step 6.6: Implement `build_beat_templates_with_variation()`
**Model: Sonnet**

Build beat templates incorporating variation decisions.

**Tasks:**
- [ ] Create function that builds `SceneBeatTemplate` for each scene
- [ ] Place required beats in appropriate positions
- [ ] Fill remaining slots with varied filler beats
- [ ] Include complication beats where variation decided
- [ ] Include character moment beats where decided

**Tests:**
- [ ] Test required beats appear in templates
- [ ] Test filler beats fill remaining slots
- [ ] Test complications included where flagged
- [ ] Test total beat count matches scene allocation

**Acceptance Criteria:**
- Beat templates ready for scene expansion

---

### Step 6.7: Update Prose Pipeline with Plot-First Flow
**Model: Opus**

Integrate all pieces into prose pipeline.

**Tasks:**
- [ ] Reorder pipeline: Shape → Structure → IDs → Outline → Characters → World
- [ ] Call `generate_outline_structure()` early
- [ ] Call `allocate_prose_ids()` after structure
- [ ] Call `generate_outline_content()` with IDs
- [ ] Call `generate_characters_from_slots()` with outline context
- [ ] Call `generate_world_from_slots()` with outline + character context
- [ ] Integrate beat assignment and templates
- [ ] Call scene expansion with full context

**Tests:**
- [ ] Integration test: full prose pipeline works
- [ ] Test characters reference outline
- [ ] Test world references outline + characters
- [ ] Test scenes reference all prior elements

**Acceptance Criteria:**
- Plot-first pipeline fully functional

---

## Phase 7: Enrichment Pass

### Step 7.1: Define Enrichment Output Schema
**Model: Haiku**

Create schemas for enrichment output.

**Tasks:**
- [ ] Create `EnrichmentOutput` schema
- [ ] Include: new_characters, new_locations, new_world_facts
- [ ] Include: subplot_additions, foreshadowing_elements
- [ ] Add to `schemas.py`

**Tests:**
- [ ] Test schema validation
- [ ] Test optional fields

**Acceptance Criteria:**
- Enrichment output structure defined

---

### Step 7.2: Create Enrichment Prompt
**Model: Opus**

Design the enrichment generation prompt.

**Tasks:**
- [ ] Create `build_enrichment_prompt()` function
- [ ] Include existing characters, world, outline as context
- [ ] Include variation decisions (subplot seeds, etc.)
- [ ] Request specific types of enrichment
- [ ] Guide toward depth without structural changes

**Tests:**
- [ ] Test prompt includes all context
- [ ] Manual review of prompt quality

**Acceptance Criteria:**
- Prompt guides LLM to add depth appropriately

---

### Step 7.3: Implement `generate_enrichment()`
**Model: Sonnet**

Implement the enrichment generation function.

**Tasks:**
- [ ] Create async function
- [ ] Build prompt with full context
- [ ] Call LLM for enrichment
- [ ] Validate output
- [ ] Return `EnrichmentOutput`

**Tests:**
- [ ] Test with mock LLM
- [ ] Test output validates
- [ ] Test handles empty enrichment

**Acceptance Criteria:**
- Enrichment generation works

---

### Step 7.4: Implement Merge Functions
**Model: Sonnet**

Implement functions to merge enrichment into existing data.

**Tasks:**
- [ ] Implement `merge_enrichment_characters()`
- [ ] Implement `merge_enrichment_world()`
- [ ] Implement `merge_enrichment_plot()`
- [ ] Assign new IDs from extended `ProjectIds`
- [ ] Preserve existing data

**Tests:**
- [ ] Test new characters added with correct IDs
- [ ] Test existing characters unchanged
- [ ] Test world facts merged correctly
- [ ] Test plot additions integrated

**Acceptance Criteria:**
- Enrichment cleanly merged

---

### Step 7.5: Add `--enrich/--no-enrich` CLI Flag
**Model: Haiku**

Add CLI control for enrichment.

**Tasks:**
- [ ] Add `--enrich` flag (default True)
- [ ] Add `--no-enrich` to disable
- [ ] Pass to generation pipeline

**Tests:**
- [ ] Test `--enrich` enables enrichment
- [ ] Test `--no-enrich` disables enrichment
- [ ] Test default is enabled

**Acceptance Criteria:**
- CLI flag controls enrichment

---

### Step 7.6: Integrate Enrichment into Prose Pipeline
**Model: Sonnet**

Add enrichment pass to pipeline.

**Tasks:**
- [ ] Check `options.enrich` flag
- [ ] Call `generate_enrichment()` after pass 1
- [ ] Call `extend_ids_for_enrichment()` for new entities
- [ ] Call merge functions
- [ ] Update beat templates with enriched content

**Tests:**
- [ ] Test pipeline with enrichment enabled
- [ ] Test pipeline with enrichment disabled
- [ ] Test enriched entities appear in final output

**Acceptance Criteria:**
- Enrichment integrated into pipeline

---

## Phase 8: Cleanup

### Step 8.1: Remove Old Pattern Models
**Model: Haiku**

Delete deprecated pattern models.

**Tasks:**
- [ ] Remove `PlotPattern` model
- [ ] Remove `PlotPatternRole` model
- [ ] Remove `PlotPatternBeat` model
- [ ] Remove `PlotPatternBeatAssignment` model
- [ ] Remove `NarrativePattern` model
- [ ] Remove `NarrativeRole` model
- [ ] Remove file wrapper models if unused

**Tests:**
- [ ] No import errors
- [ ] Tests updated to not reference old models

**Acceptance Criteria:**
- Old models removed

---

### Step 8.2: Remove Old Pattern Generation Code
**Model: Haiku**

Delete deprecated pattern prompts and functions.

**Tasks:**
- [ ] Remove `build_plot_patterns_prompt()`
- [ ] Remove `build_narrative_patterns_prompt()`
- [ ] Remove `build_plot_pattern_assignment_prompt()`
- [ ] Remove related validation functions
- [ ] Remove related schema classes

**Tests:**
- [ ] No import errors
- [ ] All tests pass

**Acceptance Criteria:**
- Old generation code removed

---

### Step 8.3: Clean Up Unused Imports and Dead Code
**Model: Haiku**

Final cleanup pass.

**Tasks:**
- [ ] Run linter to find unused imports
- [ ] Remove unused imports
- [ ] Remove any remaining dead code
- [ ] Fix any linter warnings

**Tests:**
- [ ] `ruff check` passes
- [ ] `mypy` passes

**Acceptance Criteria:**
- Clean codebase, no warnings

---

### Step 8.4: Update CLAUDE.md Architecture Section
**Model: Sonnet**

Document the new architecture.

**Tasks:**
- [ ] Update Architecture section in CLAUDE.md
- [ ] Document story shapes system
- [ ] Document pipeline structure
- [ ] Document ID generation approach
- [ ] Document variation system

**Tests:**
- [ ] Manual review for accuracy
- [ ] All documented commands work

**Acceptance Criteria:**
- Documentation reflects new architecture

---

### Step 8.5: Final Integration Testing
**Model: Sonnet**

Comprehensive testing of refactored system.

**Tasks:**
- [ ] Run full test suite
- [ ] Manual test: `fabulae create "..." --format novel`
- [ ] Manual test: `fabulae create "..." --format short-story --shape betrayal-arc`
- [ ] Manual test: `fabulae create "..." --format micro-prose`
- [ ] Manual test: `fabulae create "..." --format poem`
- [ ] Manual test: `fabulae create "..." --no-enrich --variation 0.0`
- [ ] Manual test: `fabulae shapes` and `fabulae shape <id>`
- [ ] Verify output quality

**Tests:**
- [ ] All automated tests pass
- [ ] Manual tests produce valid output
- [ ] No regressions

**Acceptance Criteria:**
- Refactoring complete and working
