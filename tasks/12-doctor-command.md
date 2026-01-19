# Task: Doctor Command (Environment Diagnostics)

**Priority:** Medium - valuable for onboarding and troubleshooting.
**Depends on:** `10-tui-simple.md` (v0.1.0 release)

## Overview

Add a `doctor` command that performs comprehensive diagnostics on the Fabulae environment. This command helps users verify their setup is working correctly, diagnose issues, and understand their current configuration.

All LLM interactions must use structured output (Pydantic models) via `create_agent()` from `src/fabulae/llm/`.

## Execution Methodology

This task should be implemented step-by-step, using the recommended model for each step:
- **Haiku**: Simple/straightforward changes (boilerplate, simple edits)
- **Sonnet**: Complex logic and architectural decisions
- **Opus**: Prompt engineering and final verification

After completing all implementation steps, switch to **Opus** model to verify the implementation is correct and complete.

## Command Signature

```bash
fabulae doctor [project-dir] [--json] [--model MODEL] [--temperature TEMP] [--base-url URL]
```

## Example Output

```
$ fabulae doctor

╭─────────────────────────────────────────────────────────────────────────────╮
│                            Fabulae Doctor                                   │
╰─────────────────────────────────────────────────────────────────────────────╯

Environment
───────────
  ✓ Python 3.12.1
  ✓ Fabulae 0.1.0

LLM Connection
──────────────
  ✓ Endpoint: http://localhost:11434/v1
  ✓ Connection: reachable (45ms)
  ✓ Model: ministral-3:3b
    └─ Status: available
    └─ Parameters: 3B
  ✓ Test generation: successful (1.2s)
    └─ "The quick brown fox jumps over the lazy dog."

Configuration
─────────────
  Source priority: CLI > FABULAE_* > OPENAI_* > Defaults

  Model:
    └─ Active: ministral-3:3b (default)
    └─ FABULAE_LLM_MODEL: not set

  Endpoint:
    └─ Active: http://localhost:11434/v1 (default)
    └─ FABULAE_LLM_BASE_URL: not set
    └─ OPENAI_BASE_URL: not set

  API Key:
    └─ Active: ollama (default)
    └─ FABULAE_LLM_API_KEY: not set
    └─ OPENAI_API_KEY: not set

  Temperature:
    └─ Active: 0.7 (default)
    └─ FABULAE_LLM_TEMPERATURE: not set

Project
───────
  ✓ Valid Fabulae project found: ./my-novel
  ✓ Format: novel
  ✓ Entities:
    └─ Characters: 3
    └─ World facts: 8
    └─ Chapters: 3
    └─ Scenes: 12
    └─ Beats: 45
  ⚠ Warnings:
    └─ 2 world facts are never referenced in scenes

Available Models (Ollama)
─────────────────────────
  • ministral-3:3b (3.0 GB) ← active
  • llama3:8b (4.7 GB)
  • codellama:7b (3.8 GB)

───────────────────────────────────────────────────────────────────────────────
Summary: 10 checks passed, 0 failed, 1 warning
───────────────────────────────────────────────────────────────────────────────
```

## Diagnostic Categories

### 1. Environment Checks
| Check | Description | Failure Action |
|-------|-------------|----------------|
| Python version | Verify Python >= 3.10 | Show required version |
| Fabulae version | Display installed version | - |

### 2. LLM Connection Checks
| Check | Description | Failure Action |
|-------|-------------|----------------|
| Endpoint reachable | HTTP HEAD to base_url | Show connection help |
| Response latency | Measure ping time | Warn if > 5s |
| Model available | Check model exists | List available models |
| Model metadata | Get model info (params, size) | Skip if unavailable |
| Test generation | Run simple prompt | Show error details |

### 3. Configuration Checks
| Check | Description | Failure Action |
|-------|-------------|----------------|
| Show active config | Display resolved values | - |
| Show env var status | Which vars are set | - |
| Show priority chain | Explain which source won | - |
| Validate temperature | Check range 0.0-2.0 | Warn if out of range |

### 4. Project Checks (if in project directory)
| Check | Description | Failure Action |
|-------|-------------|----------------|
| Valid project | Can load project | Show validation errors |
| Entity counts | Summarize contents | - |
| Reference integrity | Check all refs valid | List broken refs |
| Unused entities | Find orphaned entities | Warn about unused |
| Format validation | Check format-specific rules | Show issues |

### 5. Available Models (Ollama-specific)
| Check | Description | Failure Action |
|-------|-------------|----------------|
| List models | Query Ollama for installed models | Skip if not Ollama |
| Model sizes | Show disk usage | - |
| Highlight active | Mark currently configured model | - |

## Implementation Steps

### Step 1: Design Check Result Models
**Model: Sonnet**

Create `src/fabulae/features/doctor/models.py`:

```python
from enum import Enum
from pydantic import BaseModel

class CheckStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"

class CheckResult(BaseModel):
    name: str
    status: CheckStatus
    message: str
    details: list[str] = []
    suggestion: str | None = None

class CategoryResult(BaseModel):
    name: str
    checks: list[CheckResult]

class DoctorReport(BaseModel):
    categories: list[CategoryResult]
    passed: int
    failed: int
    warnings: int
    skipped: int

    @property
    def success(self) -> bool:
        return self.failed == 0
```

Add a structured output model for the LLM test prompt:
```python
class LLMTestPromptResult(BaseModel):
    echo: str
```

### Step 2: Implement Environment Checks
**Model: Sonnet**

Create `src/fabulae/features/doctor/environment.py`:

```python
import sys
import importlib.metadata

async def check_environment() -> CategoryResult:
    checks = []

    # Python version
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 10)
    checks.append(CheckResult(
        name="Python version",
        status=CheckStatus.PASSED if py_ok else CheckStatus.FAILED,
        message=py_version,
        suggestion=None if py_ok else "Python 3.10+ required",
    ))

    # Fabulae version
    try:
        version = importlib.metadata.version("fabulae")
        checks.append(CheckResult(
            name="Fabulae version",
            status=CheckStatus.PASSED,
            message=version,
        ))
    except importlib.metadata.PackageNotFoundError:
        checks.append(CheckResult(
            name="Fabulae version",
            status=CheckStatus.FAILED,
            message="not installed",
            suggestion="Run: pip install fabulae",
        ))

    return CategoryResult(name="Environment", checks=checks)
```

### Step 3: Implement LLM Connection Checks
**Model: Sonnet**

Create `src/fabulae/features/doctor/llm_connection.py`:

```python
import httpx
import time
from fabulae.llm import LLMConfig, create_agent

async def check_llm_connection(config: LLMConfig) -> CategoryResult:
    checks = []

    # Endpoint reachability
    try:
        start = time.monotonic()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{config.base_url}/models",
                timeout=10.0,
            )
        latency_ms = (time.monotonic() - start) * 1000

        checks.append(CheckResult(
            name="Endpoint",
            status=CheckStatus.PASSED,
            message=config.base_url,
        ))
        checks.append(CheckResult(
            name="Connection",
            status=CheckStatus.PASSED if latency_ms < 5000 else CheckStatus.WARNING,
            message=f"reachable ({latency_ms:.0f}ms)",
            suggestion="Connection is slow" if latency_ms >= 5000 else None,
        ))
    except httpx.ConnectError:
        checks.append(CheckResult(
            name="Endpoint",
            status=CheckStatus.FAILED,
            message=config.base_url,
            suggestion="Is Ollama running? Try: ollama serve",
        ))
        return CategoryResult(name="LLM Connection", checks=checks)

    # Test generation (using structured output)
    try:
        start = time.monotonic()
        agent = create_agent(LLMTestPromptResult, "Echo 'test successful'", config)
        result = await agent.run()
        duration = time.monotonic() - start
        checks.append(CheckResult(
            name="Test generation",
            status=CheckStatus.PASSED,
            message=f"successful ({duration:.1f}s)",
            details=[f'"{result.data.echo[:50]}..."' if len(result.data.echo) > 50 else f'"{result.data.echo}"'],
        ))
    except Exception as e:
        checks.append(CheckResult(
            name="Test generation",
            status=CheckStatus.FAILED,
            message="failed",
            details=[str(e)],
        ))

    return CategoryResult(name="LLM Connection", checks=checks)
```

### Step 4: Implement Configuration Checks
**Model: Sonnet**

Create `src/fabulae/features/doctor/configuration.py`:

```python
import os
from fabulae.llm import LLMConfig

async def check_configuration(config: LLMConfig) -> CategoryResult:
    checks = []

    # Model configuration
    fabulae_model = os.getenv("FABULAE_LLM_MODEL")
    checks.append(CheckResult(
        name="Model",
        status=CheckStatus.PASSED,
        message="",
        details=[
            f"Active: {config.model}" + (" (default)" if not fabulae_model else " (from FABULAE_LLM_MODEL)"),
            f"FABULAE_LLM_MODEL: {fabulae_model or 'not set'}",
        ],
    ))

    # Endpoint configuration
    fabulae_url = os.getenv("FABULAE_LLM_BASE_URL")
    openai_url = os.getenv("OPENAI_BASE_URL")
    source = "default"
    if fabulae_url:
        source = "FABULAE_LLM_BASE_URL"
    elif openai_url:
        source = "OPENAI_BASE_URL"

    checks.append(CheckResult(
        name="Endpoint",
        status=CheckStatus.PASSED,
        message="",
        details=[
            f"Active: {config.base_url} (from {source})",
            f"FABULAE_LLM_BASE_URL: {fabulae_url or 'not set'}",
            f"OPENAI_BASE_URL: {openai_url or 'not set'}",
        ],
    ))

    # API Key configuration (masked)
    fabulae_key = os.getenv("FABULAE_LLM_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    def mask_key(key: str | None) -> str:
        if not key:
            return "not set"
        if key == "ollama":
            return "ollama"
        return f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "***"

    checks.append(CheckResult(
        name="API Key",
        status=CheckStatus.PASSED,
        message="",
        details=[
            f"Active: {mask_key(config.api_key)}",
            f"FABULAE_LLM_API_KEY: {mask_key(fabulae_key)}",
            f"OPENAI_API_KEY: {mask_key(openai_key)}",
        ],
    ))

    # Temperature
    temp_env = os.getenv("FABULAE_LLM_TEMPERATURE")
    temp_valid = 0.0 <= config.temperature <= 2.0
    checks.append(CheckResult(
        name="Temperature",
        status=CheckStatus.PASSED if temp_valid else CheckStatus.WARNING,
        message="",
        details=[
            f"Active: {config.temperature}" + (" (default)" if not temp_env else ""),
            f"FABULAE_LLM_TEMPERATURE: {temp_env or 'not set'}",
        ],
        suggestion=None if temp_valid else "Temperature should be between 0.0 and 2.0",
    ))

    return CategoryResult(name="Configuration", checks=checks)
```

### Step 5: Implement Project Checks
**Model: Sonnet**

Create `src/fabulae/features/doctor/project.py`:

```python
from pathlib import Path
from fabulae.models import load_project, Project

async def check_project(project_dir: Path | None) -> CategoryResult | None:
    if project_dir is None:
        return None

    checks = []

    # Try to load project
    try:
        project = load_project(project_dir)
        checks.append(CheckResult(
            name="Valid project",
            status=CheckStatus.PASSED,
            message=str(project_dir),
        ))
    except Exception as e:
        checks.append(CheckResult(
            name="Valid project",
            status=CheckStatus.FAILED,
            message=str(project_dir),
            details=[str(e)],
        ))
        return CategoryResult(name="Project", checks=checks)

    # Format
    checks.append(CheckResult(
        name="Format",
        status=CheckStatus.PASSED,
        message=project.plot.format,
    ))

    # Entity counts
    entity_counts = gather_entity_counts(project)
    checks.append(CheckResult(
        name="Entities",
        status=CheckStatus.PASSED,
        message="",
        details=[f"{name}: {count}" for name, count in entity_counts.items()],
    ))

    # Check for unused entities
    warnings = find_unused_entities(project)
    if warnings:
        checks.append(CheckResult(
            name="Warnings",
            status=CheckStatus.WARNING,
            message=f"{len(warnings)} issues found",
            details=warnings,
        ))

    return CategoryResult(name="Project", checks=checks)

def gather_entity_counts(project: Project) -> dict[str, int]:
    counts = {
        "Characters": len(project.characters),
        "World facts": len(project.world.facts) if project.world else 0,
    }

    if project.plot.chapters:
        counts["Chapters"] = len(project.plot.chapters)
    if project.plot.scenes:
        counts["Scenes"] = len(project.plot.scenes)
        counts["Beats"] = sum(len(s.beats) for s in project.plot.scenes if s.beats)
    if project.plot.fragments:
        counts["Fragments"] = len(project.plot.fragments)
    if project.plot.stanzas:
        counts["Stanzas"] = len(project.plot.stanzas)

    return counts

def find_unused_entities(project: Project) -> list[str]:
    warnings = []

    # Find unused world facts
    used_fact_ids = set()
    for scene in project.plot.scenes or []:
        if scene.world_fact_ids:
            used_fact_ids.update(scene.world_fact_ids)
        if scene.location:
            used_fact_ids.add(scene.location)

    if project.world:
        for fact in project.world.facts:
            if fact.id not in used_fact_ids:
                warnings.append(f"World fact '{fact.id}' is never referenced")

    # Find unused characters
    used_char_ids = set()
    for scene in project.plot.scenes or []:
        if scene.characters:
            used_char_ids.update(scene.characters)

    for char in project.characters:
        if char.id not in used_char_ids:
            warnings.append(f"Character '{char.id}' appears in no scenes")

    return warnings
```

### Step 6: Implement Available Models Check (Ollama)
**Model: Sonnet**

Create `src/fabulae/features/doctor/available_models.py`:

```python
import httpx
from fabulae.llm import LLMConfig

async def check_available_models(config: LLMConfig) -> CategoryResult | None:
    # Only works for Ollama endpoints
    if "ollama" not in config.base_url and "11434" not in config.base_url:
        return None

    checks = []

    try:
        async with httpx.AsyncClient() as client:
            # Ollama-specific API
            response = await client.get(
                config.base_url.replace("/v1", "/api/tags"),
                timeout=10.0,
            )
            data = response.json()

        models = data.get("models", [])
        for model in models:
            name = model.get("name", "unknown")
            size_bytes = model.get("size", 0)
            size_gb = size_bytes / (1024 ** 3)

            is_active = name == config.model or name.startswith(config.model.split(":")[0])

            checks.append(CheckResult(
                name=name,
                status=CheckStatus.PASSED,
                message=f"({size_gb:.1f} GB)" + (" ← active" if is_active else ""),
            ))

        if not models:
            checks.append(CheckResult(
                name="No models",
                status=CheckStatus.WARNING,
                message="No models installed",
                suggestion=f"Try: ollama pull {config.model}",
            ))

    except Exception:
        return None  # Skip this section if we can't query Ollama

    return CategoryResult(name="Available Models (Ollama)", checks=checks)
```

### Step 7: Implement Doctor Orchestrator
**Model: Sonnet**

Create `src/fabulae/features/doctor/service.py`:

```python
from pathlib import Path
from fabulae.llm import LLMConfig, resolve_config
from fabulae.features.doctor.models import DoctorReport, CategoryResult, CheckStatus
from fabulae.features.doctor.environment import check_environment
from fabulae.features.doctor.llm_connection import check_llm_connection
from fabulae.features.doctor.configuration import check_configuration
from fabulae.features.doctor.project import check_project
from fabulae.features.doctor.available_models import check_available_models

async def run_doctor(
    project_dir: Path | None = None,
    config: LLMConfig | None = None,
) -> DoctorReport:
    """Run all diagnostic checks."""
    if config is None:
        config = resolve_config(None, None, None, None)

    categories: list[CategoryResult] = []

    # Environment checks
    categories.append(await check_environment())

    # LLM connection checks
    categories.append(await check_llm_connection(config))

    # Configuration checks
    categories.append(await check_configuration(config))

    # Project checks (optional)
    project_result = await check_project(project_dir)
    if project_result:
        categories.append(project_result)

    # Available models (Ollama only)
    models_result = await check_available_models(config)
    if models_result:
        categories.append(models_result)

    # Calculate totals
    passed = sum(1 for c in categories for r in c.checks if r.status == CheckStatus.PASSED)
    failed = sum(1 for c in categories for r in c.checks if r.status == CheckStatus.FAILED)
    warnings = sum(1 for c in categories for r in c.checks if r.status == CheckStatus.WARNING)
    skipped = sum(1 for c in categories for r in c.checks if r.status == CheckStatus.SKIPPED)

    return DoctorReport(
        categories=categories,
        passed=passed,
        failed=failed,
        warnings=warnings,
        skipped=skipped,
    )
```

### Step 8: Implement CLI Command
**Model: Sonnet**

Create `src/fabulae/features/doctor/cli.py`:

```python
from pathlib import Path
from typing import Annotated
import typer

from fabulae.cli_options import base_url_option, model_option, temperature_option
from fabulae.llm import resolve_config


def register_doctor_command(app: typer.Typer) -> None:
    @app.command()
    def doctor(
        project_dir: Annotated[Path | None, typer.Argument()] = None,
        json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
        model: str = model_option(),
        temperature: float = temperature_option(),
        base_url: str | None = base_url_option(),
    ) -> None:
        """
        Run diagnostic checks on the Fabulae environment.

        Checks LLM connectivity, configuration, and optionally validates
        a project directory.

        Examples:
            fabulae doctor
            fabulae doctor ./my-novel
            fabulae doctor --json
        """
        import asyncio
        from fabulae.features.doctor.service import run_doctor
        from fabulae.features.doctor.formatter import format_report

        # Detect project directory
        if project_dir is None:
            cwd = Path.cwd()
            if (cwd / "fabulae.yml").exists():
                project_dir = cwd

        # Resolve config with CLI overrides, env vars, then defaults
        config = resolve_config(
            cli_model=model,
            cli_base_url=base_url,
            cli_api_key=None,
            cli_temperature=temperature,
        )

        # Run diagnostics
        report = asyncio.run(run_doctor(project_dir, config))

        # Output
        if json_output:
            typer.echo(report.model_dump_json(indent=2))
        else:
            format_report(report)

        # Exit code
        if not report.success:
            raise typer.Exit(1)
```

Wire it in `src/fabulae/main.py`:

```python
from fabulae.features.doctor.cli import register_doctor_command

register_doctor_command(app)
```

### Step 9: Implement Rich Formatter
**Model: Sonnet**

Create `src/fabulae/features/doctor/formatter.py`:

```python
from rich.console import Console
from rich.panel import Panel
from fabulae.features.doctor.models import DoctorReport, CheckResult, CheckStatus

console = Console()

STATUS_ICONS = {
    CheckStatus.PASSED: "[green]✓[/green]",
    CheckStatus.FAILED: "[red]✗[/red]",
    CheckStatus.WARNING: "[yellow]⚠[/yellow]",
    CheckStatus.SKIPPED: "[dim]○[/dim]",
}

def format_report(report: DoctorReport) -> None:
    """Print formatted doctor report to console."""

    # Header
    console.print()
    console.print(Panel.fit(
        "[bold]Fabulae Doctor[/bold]",
        border_style="blue",
    ))
    console.print()

    # Categories
    for category in report.categories:
        console.print(f"[bold]{category.name}[/bold]")
        console.print("─" * len(category.name))

        for check in category.checks:
            icon = STATUS_ICONS[check.status]
            console.print(f"  {icon} {check.name}: {check.message}")

            for detail in check.details:
                console.print(f"    └─ {detail}")

            if check.suggestion:
                console.print(f"    [dim]→ {check.suggestion}[/dim]")

        console.print()

    # Summary
    console.print("─" * 60)
    summary_parts = []
    if report.passed:
        summary_parts.append(f"[green]{report.passed} passed[/green]")
    if report.failed:
        summary_parts.append(f"[red]{report.failed} failed[/red]")
    if report.warnings:
        summary_parts.append(f"[yellow]{report.warnings} warnings[/yellow]")
    if report.skipped:
        summary_parts.append(f"[dim]{report.skipped} skipped[/dim]")

    console.print(f"Summary: {', '.join(summary_parts)}")
    console.print("─" * 60)
```

### Step 10: Write Tests
**Model: Sonnet**

Create `tests/unit/features/doctor_test.py`:

1. Test each check category independently with mocked responses
2. Test report aggregation (passed/failed/warning counts)
3. Test CLI with various scenarios
4. Test JSON output format
5. Test exit codes (0 for success, 1 for failures)
6. Test project detection in current directory

### Final Step: Opus Verification
**Model: Opus**

After all implementation steps are complete, switch to Opus model and verify:

1. **Code Quality Review:**
   - All changes follow codebase conventions
   - No duplicate code introduced
   - Error handling is appropriate
   - Type hints are complete

2. **Integration Check:**
   - All new code integrates properly with existing code
   - Imports are correct
   - No circular dependencies

3. **Test Verification:**
   - Run `uv run ruff check --fix && uv run mypy && uv run pytest`
   - All tests pass
   - No regressions introduced

4. **Acceptance Criteria Validation:**
   - Verify each acceptance criterion is met
   - Test the doctor command manually with various configurations

5. **Documentation Review:**
   - Review and update `README.md` if the feature adds/changes CLI commands or user-facing behavior
   - Review and update `CLAUDE.md` if architectural patterns, conventions, or key implementation details changed
   - Keep all documentation concise but detailed enough for coding agents and human users

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/fabulae/features/doctor/__init__.py` | Create | Package init, exports models |
| `src/fabulae/features/doctor/models.py` | Create | Doctor result models |
| `src/fabulae/features/doctor/environment.py` | Create | Environment checks |
| `src/fabulae/features/doctor/llm_connection.py` | Create | LLM connectivity checks |
| `src/fabulae/features/doctor/configuration.py` | Create | Config display |
| `src/fabulae/features/doctor/project.py` | Create | Project validation checks |
| `src/fabulae/features/doctor/available_models.py` | Create | Ollama model listing |
| `src/fabulae/features/doctor/service.py` | Create | Orchestrator |
| `src/fabulae/features/doctor/formatter.py` | Create | Rich output formatting |
| `src/fabulae/features/doctor/cli.py` | Create | CLI command implementation |
| `src/fabulae/main.py` | Modify | Add doctor command |
| `tests/unit/features/doctor_test.py` | Create | Unit tests |

## Example Failure Scenarios

### Ollama Not Running
```
$ fabulae doctor

LLM Connection
──────────────
  ✗ Endpoint: http://localhost:11434/v1
    → Is Ollama running? Try: ollama serve

Summary: 3 passed, 1 failed, 0 warnings
```

### Model Not Installed
```
$ fabulae doctor

LLM Connection
──────────────
  ✓ Endpoint: http://localhost:11434/v1
  ✓ Connection: reachable (45ms)
  ✗ Model: ministral-3:3b
    → Model not found. Try: ollama pull ministral-3:3b

Available Models (Ollama)
─────────────────────────
  • llama3:8b (4.7 GB)
  • codellama:7b (3.8 GB)

Summary: 5 passed, 1 failed, 0 warnings
```

### Invalid Project
```
$ fabulae doctor ./broken-project

Project
───────
  ✗ Valid project: ./broken-project
    └─ Character 'unknown-char' referenced in scene 'scene-01' does not exist

Summary: 8 passed, 1 failed, 0 warnings
```

## Acceptance Criteria

- [ ] `fabulae doctor` runs all diagnostic checks
- [ ] Environment checks verify Python and package versions
- [ ] LLM connection checks verify endpoint, model, and generation
- [ ] Configuration shows resolved values and sources
- [ ] Project checks run when in a project directory
- [ ] Available models listed for Ollama endpoints
- [ ] `--json` outputs machine-readable format
- [ ] `--model`, `--temperature`, and `--base-url` CLI options override env/defaults following the documented priority chain
- [ ] Exit code 1 when any check fails
- [ ] Clear, actionable suggestions for failures
- [ ] All tests pass
- [ ] `ruff check`, `mypy`, and `pytest` pass

## Notes

- The doctor command should be fast for the common case (< 3s)
- Test generation uses a minimal prompt to minimize latency
- API keys are masked in output for security
- Consider caching Ollama model list if called frequently
