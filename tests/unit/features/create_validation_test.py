"""Tests for create validation functions."""

from fabulae.features.create.validation import (
    validate_character_references,
    validate_id_unchanged,
    validate_location_reference,
    validate_world_fact_references,
)


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
