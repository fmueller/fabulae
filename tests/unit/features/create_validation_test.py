"""Tests for create validation functions."""

from fabulae.features.create.validation import (
    _find_similar_titles,
    validate_character_references,
    validate_id_unchanged,
    validate_location_reference,
    validate_title_diversity,
    validate_world_fact_references,
)
from fabulae.models import Chapter, Plot, Project, ProjectConfig


class TestValidateIdUnchanged:
    """Tests for validate_id_unchanged function."""

    def test_matching_ids_return_none(self) -> None:
        """Test that matching IDs return None."""
        result = validate_id_unchanged("scene-01", "scene-01")
        assert result is None

    def test_mismatched_ids_return_error_message(self) -> None:
        """Test that mismatched IDs return an error message."""
        result = validate_id_unchanged("scene-02", "scene-01")
        assert result is not None
        assert "scene-01" in result
        assert "scene-02" in result

    def test_error_message_includes_both_ids(self) -> None:
        """Test that error message includes both expected and actual IDs."""
        result = validate_id_unchanged("character-foo", "character-01")
        assert result is not None
        assert "expected" in result.lower()
        assert "character-01" in result
        assert "got" in result.lower() or "received" in result.lower() or "character-foo" in result
        assert "character-foo" in result

    def test_case_sensitive_comparison(self) -> None:
        """Test that ID comparison is case-sensitive."""
        result = validate_id_unchanged("Scene-01", "scene-01")
        assert result is not None

    def test_whitespace_sensitive_comparison(self) -> None:
        """Test that ID comparison is whitespace-sensitive."""
        result = validate_id_unchanged("scene-01 ", "scene-01")
        assert result is not None


class TestValidateCharacterReferences:
    """Tests for validate_character_references function."""

    def test_valid_references_return_none(self) -> None:
        """Test that valid references return None."""
        refs = ["character-01", "character-02"]
        available = ["character-01", "character-02", "character-03"]
        result = validate_character_references(refs, available)
        assert result is None

    def test_empty_references_return_none(self) -> None:
        """Test that empty reference list returns None."""
        result = validate_character_references([], ["character-01"])
        assert result is None

    def test_invalid_reference_returns_error(self) -> None:
        """Test that invalid reference returns error message."""
        refs = ["character-99"]
        available = ["character-01", "character-02"]
        result = validate_character_references(refs, available)
        assert result is not None
        assert "character-99" in result

    def test_error_includes_available_list(self) -> None:
        """Test that error message includes the available character list."""
        refs = ["character-99"]
        available = ["character-01", "character-02"]
        result = validate_character_references(refs, available)
        assert result is not None
        assert "character-01" in result
        assert "character-02" in result

    def test_multiple_invalid_references(self) -> None:
        """Test that multiple invalid references are all reported."""
        refs = ["character-99", "character-88"]
        available = ["character-01"]
        result = validate_character_references(refs, available)
        assert result is not None
        assert "character-99" in result
        assert "character-88" in result

    def test_mixed_valid_and_invalid_references(self) -> None:
        """Test that only invalid references are reported."""
        refs = ["character-01", "character-99"]
        available = ["character-01", "character-02"]
        result = validate_character_references(refs, available)
        assert result is not None
        assert "character-99" in result
        assert "character-01" in result  # Should be in available list

    def test_empty_available_list(self) -> None:
        """Test error message when no characters are available."""
        refs = ["character-01"]
        available: list[str] = []
        result = validate_character_references(refs, available)
        assert result is not None
        assert "character-01" in result
        assert "none" in result.lower() or "available" in result.lower()


class TestValidateLocationReference:
    """Tests for validate_location_reference function."""

    def test_valid_reference_returns_none(self) -> None:
        """Test that valid reference returns None."""
        ref = "location-01"
        available = ["location-01", "location-02"]
        result = validate_location_reference(ref, available)
        assert result is None

    def test_none_reference_returns_none(self) -> None:
        """Test that None reference returns None (location is optional)."""
        result = validate_location_reference(None, ["location-01"])
        assert result is None

    def test_none_reference_with_empty_available_returns_none(self) -> None:
        """Test that None reference is valid even with no available locations."""
        result = validate_location_reference(None, [])
        assert result is None

    def test_invalid_reference_returns_error(self) -> None:
        """Test that invalid reference returns error message."""
        ref = "location-99"
        available = ["location-01", "location-02"]
        result = validate_location_reference(ref, available)
        assert result is not None
        assert "location-99" in result

    def test_error_includes_available_list(self) -> None:
        """Test that error message includes the available location list."""
        ref = "location-99"
        available = ["location-01", "location-02"]
        result = validate_location_reference(ref, available)
        assert result is not None
        assert "location-01" in result
        assert "location-02" in result

    def test_empty_available_list(self) -> None:
        """Test error message when no locations are available."""
        ref = "location-01"
        available: list[str] = []
        result = validate_location_reference(ref, available)
        assert result is not None
        assert "location-01" in result
        assert "none" in result.lower() or "available" in result.lower()


class TestValidateWorldFactReferences:
    """Tests for validate_world_fact_references function."""

    def test_valid_references_return_none(self) -> None:
        """Test that valid references return None."""
        refs = ["world-01", "world-02"]
        available = ["world-01", "world-02", "world-03"]
        result = validate_world_fact_references(refs, available)
        assert result is None

    def test_empty_references_return_none(self) -> None:
        """Test that empty reference list returns None."""
        result = validate_world_fact_references([], ["world-01"])
        assert result is None

    def test_invalid_reference_returns_error(self) -> None:
        """Test that invalid reference returns error message."""
        refs = ["world-99"]
        available = ["world-01", "world-02"]
        result = validate_world_fact_references(refs, available)
        assert result is not None
        assert "world-99" in result

    def test_error_includes_available_list(self) -> None:
        """Test that error message includes the available world fact list."""
        refs = ["world-99"]
        available = ["world-01", "world-02"]
        result = validate_world_fact_references(refs, available)
        assert result is not None
        assert "world-01" in result
        assert "world-02" in result

    def test_multiple_invalid_references(self) -> None:
        """Test that multiple invalid references are all reported."""
        refs = ["world-99", "world-88"]
        available = ["world-01"]
        result = validate_world_fact_references(refs, available)
        assert result is not None
        assert "world-99" in result
        assert "world-88" in result

    def test_mixed_valid_and_invalid_references(self) -> None:
        """Test that only invalid references are reported."""
        refs = ["world-01", "world-99"]
        available = ["world-01", "world-02"]
        result = validate_world_fact_references(refs, available)
        assert result is not None
        assert "world-99" in result
        assert "world-01" in result  # Should be in available list

    def test_empty_available_list(self) -> None:
        """Test error message when no world facts are available."""
        refs = ["world-01"]
        available: list[str] = []
        result = validate_world_fact_references(refs, available)
        assert result is not None
        assert "world-01" in result
        assert "none" in result.lower() or "available" in result.lower()


class TestFindSimilarTitles:
    """Tests for _find_similar_titles function."""

    def test_find_similar_titles_with_repetition(self) -> None:
        """Test that similar titles are detected."""
        titles = [
            "The Beginning of the Journey",
            "The Journey Continues",
            "A New Discovery",
        ]
        similar = _find_similar_titles(titles, threshold=0.5)
        # First two titles share "Journey"
        assert len(similar) == 1
        assert "Journey" in similar[0]

    def test_find_similar_titles_no_duplicates(self) -> None:
        """Test that distinct titles are not flagged."""
        titles = ["The Storm", "A Quiet Night", "Final Confrontation"]
        similar = _find_similar_titles(titles, threshold=0.7)
        assert len(similar) == 0

    def test_find_similar_titles_empty_list(self) -> None:
        """Test that empty list returns no similar titles."""
        similar = _find_similar_titles([], threshold=0.5)
        assert len(similar) == 0

    def test_find_similar_titles_single_title(self) -> None:
        """Test that single title list returns no similar titles."""
        similar = _find_similar_titles(["The Only Title"], threshold=0.5)
        assert len(similar) == 0

    def test_find_similar_titles_excludes_stop_words(self) -> None:
        """Test that stop words are excluded from comparison."""
        titles = ["The Beginning", "A Beginning"]
        # Both titles share only "Beginning" after excluding "The" and "A"
        similar = _find_similar_titles(titles, threshold=0.5)
        # "Beginning" is > 2 chars and not a stop word, so they should be flagged
        assert len(similar) == 1

    def test_find_similar_titles_case_insensitive(self) -> None:
        """Test that comparison is case-insensitive."""
        titles = ["The Great Adventure", "the great quest"]
        similar = _find_similar_titles(titles, threshold=0.5)
        # "Great" is shared
        assert len(similar) == 1

    def test_find_similar_titles_threshold_effect(self) -> None:
        """Test that threshold affects detection sensitivity."""
        titles = ["Dark Forest Journey", "Light Forest Path"]
        # Shares "Forest" (1 word out of 3 meaningful = ~33%)
        similar_low = _find_similar_titles(titles, threshold=0.3)
        similar_high = _find_similar_titles(titles, threshold=0.7)
        # Low threshold should flag, high should not
        assert len(similar_low) == 1
        assert len(similar_high) == 0


class TestValidateTitleDiversity:
    """Tests for validate_title_diversity function."""

    def _create_project_with_chapters(self, titles: list[str]) -> Project:
        """Create a minimal project with the given chapter titles."""
        chapters = [
            Chapter(id=f"chapter-{i+1:02d}", title=title, scene_ids=[])
            for i, title in enumerate(titles)
        ]
        plot = Plot(
            format="novel",
            premise="Test premise",
            chapters=chapters,
            scenes=[],
        )
        config = ProjectConfig()
        return Project(config=config, plot=plot, characters=[])

    def test_validate_title_diversity_no_issues(self) -> None:
        """Test that diverse titles produce no warnings."""
        project = self._create_project_with_chapters([
            "A Fateful Meeting",
            "Shadows in the Palace",
            "The Final Reckoning",
        ])
        warnings = validate_title_diversity(project)
        assert len(warnings) == 0

    def test_validate_title_diversity_detects_similar_titles(self) -> None:
        """Test that similar titles produce warnings."""
        project = self._create_project_with_chapters([
            "The Journey Begins",
            "The Journey Continues",
            "The Journey's End",
        ])
        warnings = validate_title_diversity(project)
        assert len(warnings) > 0
        assert "chapter titles" in warnings[0].lower()

    def test_validate_title_diversity_empty_chapters(self) -> None:
        """Test that empty chapter list produces no warnings."""
        plot = Plot(format="novel", premise="Test", chapters=[], scenes=[])
        config = ProjectConfig()
        project = Project(config=config, plot=plot, characters=[])
        warnings = validate_title_diversity(project)
        assert len(warnings) == 0

    def test_validate_title_diversity_none_titles_ignored(self) -> None:
        """Test that None titles are ignored in validation."""
        chapters = [
            Chapter(id="chapter-01", title="The Adventure", scene_ids=[]),
            Chapter(id="chapter-02", title=None, scene_ids=[]),  # None title
            Chapter(id="chapter-03", title="Different Story", scene_ids=[]),
        ]
        plot = Plot(format="novel", premise="Test", chapters=chapters, scenes=[])
        config = ProjectConfig()
        project = Project(config=config, plot=plot, characters=[])
        warnings = validate_title_diversity(project)
        assert len(warnings) == 0
