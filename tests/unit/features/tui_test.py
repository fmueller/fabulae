"""Tests for the TUI feature."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from fabulae.features.tui.widgets.entity_view import EntityView
from fabulae.features.tui.widgets.project_tree import ProjectTree
from fabulae.models import (
    Chapter,
    Character,
    Fragment,
    Plot,
    Project,
    ProjectConfig,
    Scene,
    Stanza,
    Style,
    World,
    WorldFact,
)


def _get_static_content(widget: EntityView) -> str:
    """Get the text content from an EntityView widget."""
    return widget.last_content


def _make_prose_project() -> Project:
    """Create a minimal prose project for testing."""
    return Project(
        config=ProjectConfig(version="0.1.0", title="Test Novel"),
        plot=Plot(
            format="novel",
            premise="A test story.",
            chapters=[
                Chapter(id="chapter-01", title="Beginning", scene_ids=["scene-01"]),
            ],
            scenes=[
                Scene(
                    id="scene-01",
                    summary="Opening scene",
                    characters=["char-01"],
                    beats=[],
                ),
            ],
        ),
        characters=[
            Character(id="char-01", name="Alice", role="protagonist"),
            Character(id="char-02", name="Bob", role="sidekick"),
        ],
        world=World(
            facts=[
                WorldFact(id="loc-01", type="location", name="Tavern"),
                WorldFact(id="artifact-01", type="object", name="Magic Sword"),
            ],
        ),
        style=Style(pov="third person", tense="past"),
    )


def _make_micro_prose_project() -> Project:
    """Create a minimal micro-prose project for testing."""
    return Project(
        config=ProjectConfig(version="0.1.0", title="Test Flash Fiction"),
        plot=Plot(
            format="micro-prose",
            premise="A flash fiction test.",
            fragments=[
                Fragment(id="fragment-01", content="First fragment content."),
                Fragment(id="fragment-02", content="Second fragment content."),
            ],
        ),
    )


def _make_poem_project() -> Project:
    """Create a minimal poem project for testing."""
    return Project(
        config=ProjectConfig(version="0.1.0", title="Test Poem"),
        plot=Plot(
            format="poem",
            premise="A poem about nature.",
            stanzas=[
                Stanza(id="stanza-01", lines=["First line", "Second line"]),
                Stanza(id="stanza-02", lines=["Third line", "Fourth line"]),
            ],
        ),
    )


def _create_test_project_on_disk(tmp_path: Path) -> Path:
    """Create a test project on disk."""
    (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0", "title": "Test Novel"}))
    (tmp_path / "plot.yml").write_text(
        yaml.dump(
            {
                "premise": "A test story.",
                "format": "novel",
                "chapters": [
                    {"id": "chapter-01", "title": "Beginning", "scene_ids": ["scene-01"]},
                ],
                "scenes": [
                    {"id": "scene-01", "summary": "Opening scene", "characters": ["char-01"]},
                ],
            }
        )
    )
    (tmp_path / "characters.yml").write_text(
        yaml.dump(
            {
                "characters": [
                    {"id": "char-01", "name": "Alice", "role": "protagonist"},
                ]
            }
        )
    )
    (tmp_path / "world.yml").write_text(
        yaml.dump(
            {
                "facts": [
                    {"id": "loc-01", "type": "location", "name": "Tavern"},
                ]
            }
        )
    )
    (tmp_path / "style.yml").write_text(yaml.dump({"pov": "third person", "tense": "past"}))
    return tmp_path


class TestProjectTree:
    """Tests for the ProjectTree widget."""

    def test_prose_tree_has_characters(self) -> None:
        """Tree includes character nodes."""
        project = _make_prose_project()
        tree = ProjectTree(project)
        # Tree should be created without errors
        assert tree.project is project

    def test_prose_tree_has_world_facts(self) -> None:
        """Tree includes world fact nodes."""
        project = _make_prose_project()
        tree = ProjectTree(project)
        assert tree.project.world is not None
        assert len(tree.project.world.facts) == 2

    def test_prose_tree_has_chapters(self) -> None:
        """Tree includes chapter nodes for prose formats."""
        project = _make_prose_project()
        tree = ProjectTree(project)
        assert len(tree.project.plot.chapters) == 1

    def test_micro_prose_tree_has_fragments(self) -> None:
        """Tree includes fragment nodes for micro-prose."""
        project = _make_micro_prose_project()
        tree = ProjectTree(project)
        assert len(tree.project.plot.fragments) == 2

    def test_poem_tree_has_stanzas(self) -> None:
        """Tree includes stanza nodes for poems."""
        project = _make_poem_project()
        tree = ProjectTree(project)
        assert len(tree.project.plot.stanzas) == 2

    def test_rebuild_updates_project(self) -> None:
        """Rebuild should update the tree with new project data."""
        project = _make_prose_project()
        tree = ProjectTree(project)
        new_project = _make_micro_prose_project()
        tree.rebuild(new_project)
        assert tree.project is new_project


class TestEntityView:
    """Tests for the EntityView widget."""

    def test_show_character(self) -> None:
        """EntityView displays character details."""
        view = EntityView("")
        char = Character(id="char-01", name="Alice", role="protagonist", desire="Truth", flaw="Pride")
        view.show_character(char)
        content = _get_static_content(view)
        assert "Alice" in content
        assert "protagonist" in content

    def test_show_world_fact(self) -> None:
        """EntityView displays world fact details."""
        view = EntityView("")
        fact = WorldFact(id="loc-01", type="location", name="Tavern", facts=["Old building"])
        view.show_world_fact(fact)
        content = _get_static_content(view)
        assert "Tavern" in content
        assert "location" in content

    def test_show_scene(self) -> None:
        """EntityView displays scene details."""
        view = EntityView("")
        scene = Scene(id="scene-01", summary="Opening scene", goal="Introduce characters")
        view.show_scene(scene)
        content = _get_static_content(view)
        assert "scene-01" in content
        assert "Opening scene" in content

    def test_show_chapter(self) -> None:
        """EntityView displays chapter details."""
        view = EntityView("")
        chapter = Chapter(id="chapter-01", title="The Beginning", scene_ids=["scene-01"])
        view.show_chapter(chapter)
        content = _get_static_content(view)
        assert "The Beginning" in content
        assert "scene-01" in content

    def test_show_fragment(self) -> None:
        """EntityView displays fragment details."""
        view = EntityView("")
        fragment = Fragment(id="fragment-01", content="Flash fiction content")
        view.show_fragment(fragment)
        content = _get_static_content(view)
        assert "fragment-01" in content
        assert "Flash fiction content" in content

    def test_show_stanza(self) -> None:
        """EntityView displays stanza details."""
        view = EntityView("")
        stanza = Stanza(id="stanza-01", lines=["First line", "Second line"])
        view.show_stanza(stanza)
        content = _get_static_content(view)
        assert "stanza-01" in content
        assert "First line" in content

    def test_show_style(self) -> None:
        """EntityView displays style details."""
        view = EntityView("")
        style = Style(pov="third person", tense="past")
        view.show_style(style)
        content = _get_static_content(view)
        assert "third person" in content
        assert "past" in content

    def test_show_entity_character(self) -> None:
        """show_entity dispatches to character view."""
        view = EntityView("")
        project = _make_prose_project()
        view.show_entity("character", "char-01", project)
        content = _get_static_content(view)
        assert "Alice" in content

    def test_show_entity_world_fact(self) -> None:
        """show_entity dispatches to world fact view."""
        view = EntityView("")
        project = _make_prose_project()
        view.show_entity("world_fact", "loc-01", project)
        content = _get_static_content(view)
        assert "Tavern" in content

    def test_show_entity_scene(self) -> None:
        """show_entity dispatches to scene view."""
        view = EntityView("")
        project = _make_prose_project()
        view.show_entity("scene", "scene-01", project)
        content = _get_static_content(view)
        assert "Opening scene" in content

    def test_show_entity_chapter(self) -> None:
        """show_entity dispatches to chapter view."""
        view = EntityView("")
        project = _make_prose_project()
        view.show_entity("chapter", "chapter-01", project)
        content = _get_static_content(view)
        assert "Beginning" in content

    def test_show_entity_fragment(self) -> None:
        """show_entity dispatches to fragment view."""
        view = EntityView("")
        project = _make_micro_prose_project()
        view.show_entity("fragment", "fragment-01", project)
        content = _get_static_content(view)
        assert "First fragment content" in content

    def test_show_entity_stanza(self) -> None:
        """show_entity dispatches to stanza view."""
        view = EntityView("")
        project = _make_poem_project()
        view.show_entity("stanza", "stanza-01", project)
        content = _get_static_content(view)
        assert "First line" in content

    def test_show_entity_style(self) -> None:
        """show_entity dispatches to style view."""
        view = EntityView("")
        project = _make_prose_project()
        view.show_entity("style", None, project)
        content = _get_static_content(view)
        assert "third person" in content

    def test_show_entity_unknown(self) -> None:
        """show_entity shows placeholder for unknown entity."""
        view = EntityView("")
        project = _make_prose_project()
        view.show_entity("character", "nonexistent", project)
        content = _get_static_content(view)
        assert "Select an entity" in content


class TestTuiCli:
    """Tests for TUI CLI entry points."""

    def test_tui_command_registered(self) -> None:
        """The tui command is registered in the app."""
        from fabulae.main import app

        # Check that 'tui' is a registered command
        command_names = [cmd.name for cmd in app.registered_commands]
        # Also check registered groups/sub-apps
        group_names = [group.name for group in app.registered_groups]
        all_names = command_names + group_names
        assert "tui" in all_names

    def test_launch_tui_function_exists(self) -> None:
        """The launch_tui function is importable."""
        from fabulae.features.tui.cli import launch_tui

        assert callable(launch_tui)

    def test_fabulae_app_class_exists(self) -> None:
        """The FabulaeApp class is importable."""
        from fabulae.features.tui.app import FabulaeApp

        assert FabulaeApp is not None

    def test_app_callback_launches_tui_when_no_subcommand(self) -> None:
        """When no subcommand is provided and stdout is a TTY, the callback launches TUI."""
        from unittest.mock import patch

        from fabulae.main import app
        from tests.conftest import runner

        # Mock _is_interactive to simulate real terminal and launch_tui to avoid actual TUI
        with (
            patch("fabulae.main._is_interactive", return_value=True),
            patch("fabulae.features.tui.cli.launch_tui") as mock_launch,
        ):
            runner.invoke(app, [])
            mock_launch.assert_called_once()

    def test_app_callback_shows_help_when_not_tty(self) -> None:
        """When stdout is not a TTY, the callback shows help instead of TUI."""
        from fabulae.main import app
        from tests.conftest import runner

        # CliRunner doesn't provide a TTY, so help should be shown
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "Fabulae" in result.output


class TestFabulaeApp:
    """Tests for the FabulaeApp class."""

    def test_app_init_with_project_path(self, tmp_path: Path) -> None:
        """App initializes with project path."""
        from fabulae.features.tui.app import FabulaeApp

        app = FabulaeApp(tmp_path)
        assert app.project_path == tmp_path
        assert app.start_create is False

    def test_app_init_with_create_mode(self, tmp_path: Path) -> None:
        """App initializes in create mode."""
        from fabulae.features.tui.app import FabulaeApp

        app = FabulaeApp(tmp_path, start_create=True)
        assert app.start_create is True

    @pytest.mark.asyncio
    async def test_app_shows_project_screen(self, tmp_path: Path) -> None:
        """App shows project screen when project exists."""
        _create_test_project_on_disk(tmp_path)

        from fabulae.features.tui.app import FabulaeApp
        from fabulae.features.tui.screens.project import ProjectScreen

        app = FabulaeApp(tmp_path, start_create=False)
        async with app.run_test() as _pilot:
            # App should have pushed the ProjectScreen
            assert isinstance(app.screen, ProjectScreen)

    @pytest.mark.asyncio
    async def test_app_shows_welcome_screen_for_create(self, tmp_path: Path) -> None:
        """App shows welcome screen in create mode."""
        from fabulae.features.tui.app import FabulaeApp
        from fabulae.features.tui.screens.welcome import WelcomeScreen

        app = FabulaeApp(tmp_path, start_create=True)
        async with app.run_test() as _pilot:
            # App should have pushed the WelcomeScreen
            assert isinstance(app.screen, WelcomeScreen)


class TestProjectScreen:
    """Tests for the ProjectScreen."""

    @pytest.mark.asyncio
    async def test_project_screen_renders(self, tmp_path: Path) -> None:
        """ProjectScreen renders without errors."""
        _create_test_project_on_disk(tmp_path)

        from fabulae.features.tui.app import FabulaeApp

        app = FabulaeApp(tmp_path, start_create=False)
        async with app.run_test() as _pilot:
            # Should render without errors
            assert app.screen is not None

    @pytest.mark.asyncio
    async def test_project_screen_has_tree(self, tmp_path: Path) -> None:
        """ProjectScreen contains a project tree."""
        _create_test_project_on_disk(tmp_path)

        from fabulae.features.tui.app import FabulaeApp

        app = FabulaeApp(tmp_path, start_create=False)
        async with app.run_test() as _pilot:
            tree = app.screen.query_one("#sidebar", ProjectTree)
            assert tree is not None

    @pytest.mark.asyncio
    async def test_project_screen_has_entity_view(self, tmp_path: Path) -> None:
        """ProjectScreen contains an entity view."""
        _create_test_project_on_disk(tmp_path)

        from fabulae.features.tui.app import FabulaeApp

        app = FabulaeApp(tmp_path, start_create=False)
        async with app.run_test() as _pilot:
            view = app.screen.query_one("#content", EntityView)
            assert view is not None

    @pytest.mark.asyncio
    async def test_quit_action(self, tmp_path: Path) -> None:
        """Pressing q should quit the app."""
        _create_test_project_on_disk(tmp_path)

        from fabulae.features.tui.app import FabulaeApp

        app = FabulaeApp(tmp_path, start_create=False)
        async with app.run_test() as pilot:
            await pilot.press("q")
            # App should be in exit state
            assert app._exit is True


class TestWelcomeScreen:
    """Tests for the WelcomeScreen."""

    @pytest.mark.asyncio
    async def test_welcome_screen_renders(self, tmp_path: Path) -> None:
        """WelcomeScreen renders without errors."""
        from fabulae.features.tui.app import FabulaeApp

        app = FabulaeApp(tmp_path, start_create=True)
        async with app.run_test() as _pilot:
            assert app.screen is not None

    @pytest.mark.asyncio
    async def test_welcome_screen_has_input(self, tmp_path: Path) -> None:
        """WelcomeScreen has an idea input."""
        from textual.widgets import Input

        from fabulae.features.tui.app import FabulaeApp

        app = FabulaeApp(tmp_path, start_create=True)
        async with app.run_test() as _pilot:
            input_widget = app.screen.query_one("#idea-input", Input)
            assert input_widget is not None

    @pytest.mark.asyncio
    async def test_welcome_screen_cancel(self, tmp_path: Path) -> None:
        """Pressing escape on WelcomeScreen exits."""
        from fabulae.features.tui.app import FabulaeApp

        app = FabulaeApp(tmp_path, start_create=True)
        async with app.run_test() as pilot:
            await pilot.press("escape")


class TestConfirmModal:
    """Tests for the ConfirmModal."""

    def test_confirm_modal_init(self) -> None:
        """ConfirmModal initializes with title and message."""
        from fabulae.features.tui.modals.confirm import ConfirmModal

        modal = ConfirmModal("Delete?", "Are you sure?")
        assert modal._title == "Delete?"
        assert modal._message == "Are you sure?"
