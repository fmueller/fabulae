"""Tests for create validation functions."""

from fabulae.features.create.validation import (
    _calculate_title_similarity,
    _tokenize_title,
    find_similar_titles,
    validate_character_references,
    validate_id_unchanged,
    validate_location_reference,
    validate_title_diversity,
    validate_world_fact_references,
)
from fabulae.models import Chapter, Plot, Project, ProjectConfig, ProjectDefaults


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


class TestTokenizeTitle:
    """Tests for _tokenize_title function."""

    def test_removes_stop_words(self) -> None:
        """Test that stop words are removed from titles."""
        result = _tokenize_title("The Journey of the Hero")
        assert "the" not in result
        assert "of" not in result
        assert "journey" in result
        assert "hero" in result

    def test_filters_short_words(self) -> None:
        """Test that words with 2 or fewer characters are filtered."""
        result = _tokenize_title("A New Day in the City")
        assert "a" not in result
        assert "in" not in result
        assert "day" in result
        assert "city" in result

    def test_normalizes_to_lowercase(self) -> None:
        """Test that words are normalized to lowercase."""
        result = _tokenize_title("The DARK Knight")
        assert "dark" in result
        assert "knight" in result
        assert "DARK" not in result

    def test_empty_title_returns_empty_set(self) -> None:
        """Test that empty title returns empty set."""
        result = _tokenize_title("")
        assert result == set()

    def test_all_stop_words_returns_empty_set(self) -> None:
        """Test that title with only stop words returns empty set."""
        result = _tokenize_title("The a an of to")
        assert result == set()


class TestCalculateTitleSimilarity:
    """Tests for _calculate_title_similarity function."""

    def test_identical_titles_return_one(self) -> None:
        """Test that identical titles return similarity of 1.0."""
        result = _calculate_title_similarity("The Dark Knight", "The Dark Knight")
        assert result == 1.0

    def test_completely_different_titles_return_zero(self) -> None:
        """Test that titles with no common words return 0.0."""
        result = _calculate_title_similarity("Shadows Rising", "Ocean Dreams")
        assert result == 0.0

    def test_partial_overlap_returns_fraction(self) -> None:
        """Test that partial word overlap returns appropriate fraction."""
        # "Journey Begins" vs "Journey Continues" -> only "journey" overlaps
        result = _calculate_title_similarity("The Journey Begins", "The Journey Continues")
        # Words after filtering: {journey, begins} vs {journey, continues}
        # Intersection: {journey}, Union: {journey, begins, continues}
        # Jaccard: 1/3 = 0.333...
        assert 0.25 < result < 0.5

    def test_similar_titles_with_patterns(self) -> None:
        """Test similarity detection for patterned titles."""
        result = _calculate_title_similarity(
            "The Beginning of the Journey",
            "The End of the Journey"
        )
        # Common: journey; Different: beginning, end
        assert result > 0.0  # Some overlap
        assert result < 1.0  # Not identical

    def test_empty_title_returns_zero(self) -> None:
        """Test that empty titles return 0.0 similarity."""
        result = _calculate_title_similarity("", "The Journey")
        assert result == 0.0

        result = _calculate_title_similarity("The Journey", "")
        assert result == 0.0


class TestFindSimilarTitles:
    """Tests for find_similar_titles function."""

    def test_finds_similar_titles(self) -> None:
        """Test that similar titles are detected."""
        titles = [
            "The Beginning of the Journey",
            "The Journey Continues",
            "A New Discovery",
        ]
        # First two share "journey", threshold 0.3 should catch it
        similar = find_similar_titles(titles, threshold=0.3)
        assert len(similar) >= 1

    def test_no_duplicates_when_titles_unique(self) -> None:
        """Test that unique titles return empty list."""
        titles = ["The Storm", "A Quiet Night", "Final Confrontation"]
        similar = find_similar_titles(titles, threshold=0.5)
        assert len(similar) == 0

    def test_returns_pairs_with_similarity(self) -> None:
        """Test that returned tuples include both titles and similarity."""
        titles = ["Dark Journey", "Journey Home"]
        similar = find_similar_titles(titles, threshold=0.3)
        if similar:
            title1, title2, score = similar[0]
            assert isinstance(title1, str)
            assert isinstance(title2, str)
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0

    def test_empty_list_returns_empty(self) -> None:
        """Test that empty list returns empty result."""
        similar = find_similar_titles([], threshold=0.5)
        assert similar == []

    def test_single_title_returns_empty(self) -> None:
        """Test that single title returns empty result."""
        similar = find_similar_titles(["Only Title"], threshold=0.5)
        assert similar == []

    def test_threshold_affects_results(self) -> None:
        """Test that threshold controls which pairs are flagged."""
        titles = ["Journey Begins", "Journey Ends"]
        # Jaccard: 1/3 = 0.33
        high_threshold = find_similar_titles(titles, threshold=0.5)
        low_threshold = find_similar_titles(titles, threshold=0.2)
        assert len(low_threshold) >= len(high_threshold)


class TestValidateTitleDiversity:
    """Tests for validate_title_diversity function."""

    def _make_project_with_chapters(self, titles: list[str]) -> Project:
        """Helper to create a project with chapter titles."""
        chapters = [
            Chapter(id=f"chapter-{i+1:02d}", title=title, scene_ids=[])
            for i, title in enumerate(titles)
        ]
        return Project(
            config=ProjectConfig(defaults=ProjectDefaults()),
            plot=Plot(format="novel", premise="Test premise", chapters=chapters, scenes=[]),
            characters=[],
        )

    def test_warns_on_similar_chapter_titles(self) -> None:
        """Test that similar chapter titles generate warnings."""
        # These titles share multiple meaningful words: journey + begins/starts/starts
        project = self._make_project_with_chapters([
            "Journey Begins Again",
            "Journey Begins Anew",  # Shares "journey" and "begins"
            "A Different Story",
        ])
        # Jaccard of first two: {journey, begins, again} vs {journey, begins, anew}
        # Intersection: {journey, begins} = 2
        # Union: {journey, begins, again, anew} = 4
        # Jaccard: 2/4 = 0.5
        warnings = validate_title_diversity(project, threshold=0.4)
        assert len(warnings) > 0
        assert any("chapter" in w.lower() for w in warnings)

    def test_no_warnings_for_diverse_titles(self) -> None:
        """Test that diverse titles don't generate warnings."""
        project = self._make_project_with_chapters([
            "Shadows Fall",
            "Morning Light",
            "The Final Reckoning",
        ])
        warnings = validate_title_diversity(project, threshold=0.5)
        assert len(warnings) == 0

    def test_handles_single_chapter(self) -> None:
        """Test that single chapter doesn't generate warnings."""
        project = self._make_project_with_chapters(["Only Chapter"])
        warnings = validate_title_diversity(project)
        assert len(warnings) == 0

    def test_handles_no_chapters(self) -> None:
        """Test that project without chapters doesn't generate warnings."""
        project = Project(
            config=ProjectConfig(defaults=ProjectDefaults()),
            plot=Plot(format="short-story", premise="Test premise", chapters=[], scenes=[]),
            characters=[],
        )
        warnings = validate_title_diversity(project)
        assert len(warnings) == 0

    def test_handles_chapters_without_titles(self) -> None:
        """Test that chapters without titles are handled."""
        chapters = [
            Chapter(id="chapter-01", title=None, scene_ids=[]),
            Chapter(id="chapter-02", title=None, scene_ids=[]),
        ]
        project = Project(
            config=ProjectConfig(defaults=ProjectDefaults()),
            plot=Plot(format="novel", premise="Test premise", chapters=chapters, scenes=[]),
            characters=[],
        )
        warnings = validate_title_diversity(project)
        assert len(warnings) == 0

    def test_threshold_parameter_respected(self) -> None:
        """Test that threshold parameter affects validation sensitivity."""
        project = self._make_project_with_chapters([
            "Dark Shadows",
            "Shadow Dance",
        ])
        # Lower threshold should be more sensitive
        strict_warnings = validate_title_diversity(project, threshold=0.2)
        lenient_warnings = validate_title_diversity(project, threshold=0.8)
        # Strict should catch more or equal warnings
        assert len(strict_warnings) >= len(lenient_warnings)
