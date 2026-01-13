"""Tests for error context and formatting."""

from fabulae.features.create.errors import (
    STAGE_DESCRIPTIONS,
    ErrorContext,
    ErrorType,
    GenerationStage,
    classify_error,
    format_json_retry_hint,
    get_error_guidance,
    is_json_error,
    is_transient_error,
)


def test_generation_stage_enum() -> None:
    """Test all generation stages exist."""
    assert GenerationStage.STYLE
    assert GenerationStage.PREMISE
    assert GenerationStage.SCENES
    assert GenerationStage.CHARACTERS
    assert GenerationStage.WORLD
    assert GenerationStage.BEATS
    assert GenerationStage.ENRICHMENT


def test_generation_stage_all_variants() -> None:
    """Test all generation stage variants exist."""
    expected_stages = {
        "STYLE",
        "PREMISE",
        "OUTLINE_STRUCTURE",
        "OUTLINE_CONTENT",
        "CHARACTERS",
        "CHARACTER_PLAN",
        "WORLD",
        "WORLD_PLAN",
        "BEATS",
        "SCENES",
        "ENRICHMENT",
        "FRAGMENT_PLAN",
        "FRAGMENTS",
        "POEM_PLAN",
        "STANZAS",
    }
    actual_stages = {stage.name for stage in GenerationStage}
    assert actual_stages == expected_stages


def test_stage_descriptions_complete() -> None:
    """Test all stages have descriptions."""
    for stage in GenerationStage:
        assert stage in STAGE_DESCRIPTIONS
        assert isinstance(STAGE_DESCRIPTIONS[stage], str)
        assert len(STAGE_DESCRIPTIONS[stage]) > 0


def test_stage_descriptions_content() -> None:
    """Test stage descriptions have expected content."""
    assert "style" in STAGE_DESCRIPTIONS[GenerationStage.STYLE].lower()
    assert "premise" in STAGE_DESCRIPTIONS[GenerationStage.PREMISE].lower()
    assert "scene" in STAGE_DESCRIPTIONS[GenerationStage.SCENES].lower()
    assert "character" in STAGE_DESCRIPTIONS[GenerationStage.CHARACTERS].lower()
    assert "world" in STAGE_DESCRIPTIONS[GenerationStage.WORLD].lower()


def test_error_context_creation() -> None:
    """Test ErrorContext can be created."""
    ctx = ErrorContext(
        stage=GenerationStage.SCENES,
        attempt=2,
        max_attempts=3,
    )
    assert ctx.stage == GenerationStage.SCENES
    assert ctx.attempt == 2
    assert ctx.max_attempts == 3


def test_error_context_format_message_with_string() -> None:
    """Test ErrorContext formats user-friendly messages with string error."""
    ctx = ErrorContext(
        stage=GenerationStage.SCENES,
        attempt=2,
        max_attempts=3,
    )
    message = ctx.format_user_message("Validation failed")
    assert "expanding scenes" in message
    assert "attempt 2/3" in message
    assert "Validation failed" in message


def test_error_context_format_message_with_exception() -> None:
    """Test ErrorContext formats user-friendly messages with exception."""
    ctx = ErrorContext(
        stage=GenerationStage.CHARACTERS,
        attempt=1,
        max_attempts=3,
    )
    error = ValueError("Invalid character data")
    message = ctx.format_user_message(error)
    assert "developing character details" in message
    assert "attempt 1/3" in message
    assert "Invalid character data" in message


def test_error_context_message_includes_suggestions() -> None:
    """Test error message includes helpful suggestions."""
    ctx = ErrorContext(
        stage=GenerationStage.PREMISE,
        attempt=1,
        max_attempts=3,
    )
    message = ctx.format_user_message("Test error")
    assert "What you can do:" in message
    assert "Try again" in message
    # The new implementation has error-type-specific suggestions
    # For unknown errors, the default suggestion is about retrying


def test_error_context_message_structure() -> None:
    """Test error message has expected structure."""
    ctx = ErrorContext(
        stage=GenerationStage.WORLD,
        attempt=1,
        max_attempts=3,
    )
    message = ctx.format_user_message("Test error")

    # Should have clear sections
    assert "Error during" in message
    assert "What happened:" in message
    assert "What you can do:" in message
    assert "Technical details:" in message


def test_error_context_first_attempt() -> None:
    """Test error context formatting for first attempt."""
    ctx = ErrorContext(
        stage=GenerationStage.STYLE,
        attempt=1,
        max_attempts=3,
    )
    message = ctx.format_user_message("Test error")
    assert "attempt 1/3" in message


def test_error_context_last_attempt() -> None:
    """Test error context formatting for last attempt."""
    ctx = ErrorContext(
        stage=GenerationStage.ENRICHMENT,
        attempt=3,
        max_attempts=3,
    )
    message = ctx.format_user_message("Test error")
    assert "attempt 3/3" in message


# Error classification tests


def test_classify_error_json_truncated() -> None:
    """Test classification of JSON truncation errors."""
    exc = Exception("status_code: 500, body: {'message': 'unexpected end of JSON input'}")
    assert classify_error(exc) == ErrorType.JSON_TRUNCATED


def test_classify_error_server_error() -> None:
    """Test classification of server errors."""
    exc = Exception("status_code: 500, internal server error")
    assert classify_error(exc) == ErrorType.SERVER_ERROR


def test_classify_error_rate_limit() -> None:
    """Test classification of rate limit errors."""
    exc = Exception("status_code: 429, rate limit exceeded")
    assert classify_error(exc) == ErrorType.RATE_LIMIT


def test_classify_error_auth_error() -> None:
    """Test classification of auth errors."""
    exc = Exception("status_code: 401, unauthorized")
    assert classify_error(exc) == ErrorType.AUTH_ERROR


def test_classify_error_model_not_found() -> None:
    """Test classification of model not found errors."""
    exc = Exception("status_code: 404, model not found")
    assert classify_error(exc) == ErrorType.MODEL_NOT_FOUND


def test_classify_error_timeout() -> None:
    """Test classification of timeout errors."""
    exc = Exception("Request timed out after 30s")
    assert classify_error(exc) == ErrorType.TIMEOUT


def test_classify_error_json_parse() -> None:
    """Test classification of JSON parse errors."""
    exc = Exception("Invalid JSON: expecting property name")
    assert classify_error(exc) == ErrorType.JSON_PARSE_ERROR


def test_classify_error_context_too_long() -> None:
    """Test classification of context length errors."""
    exc = Exception("Context length exceeded maximum tokens")
    assert classify_error(exc) == ErrorType.CONTEXT_TOO_LONG


def test_classify_error_unknown() -> None:
    """Test classification of unknown errors."""
    exc = Exception("Some random error")
    assert classify_error(exc) == ErrorType.UNKNOWN


def test_is_transient_error() -> None:
    """Test transient error detection."""
    assert is_transient_error(ErrorType.SERVER_ERROR)
    assert is_transient_error(ErrorType.RATE_LIMIT)
    assert is_transient_error(ErrorType.TIMEOUT)
    assert is_transient_error(ErrorType.JSON_TRUNCATED)
    assert is_transient_error(ErrorType.JSON_PARSE_ERROR)
    assert is_transient_error(ErrorType.VALIDATION_ERROR)
    assert not is_transient_error(ErrorType.AUTH_ERROR)
    assert not is_transient_error(ErrorType.MODEL_NOT_FOUND)
    assert not is_transient_error(ErrorType.CONTEXT_TOO_LONG)


def test_is_json_error() -> None:
    """Test JSON error detection."""
    assert is_json_error(ErrorType.JSON_TRUNCATED)
    assert is_json_error(ErrorType.JSON_PARSE_ERROR)
    assert not is_json_error(ErrorType.SERVER_ERROR)
    assert not is_json_error(ErrorType.VALIDATION_ERROR)


def test_get_error_guidance() -> None:
    """Test error guidance messages."""
    guidance = get_error_guidance(ErrorType.JSON_TRUNCATED)
    assert "truncated" in guidance.lower()

    guidance = get_error_guidance(ErrorType.AUTH_ERROR)
    assert "authentication" in guidance.lower() or "api key" in guidance.lower()


def test_format_json_retry_hint() -> None:
    """Test JSON retry hint formatting."""
    hint = format_json_retry_hint()
    assert "JSON" in hint
    assert "valid" in hint.lower()


def test_error_context_with_json_error() -> None:
    """Test ErrorContext with JSON truncation error."""
    ctx = ErrorContext(
        stage=GenerationStage.SCENES,
        attempt=1,
        max_attempts=3,
        error_type=ErrorType.JSON_TRUNCATED,
    )
    message = ctx.format_user_message("unexpected end of JSON input")
    assert "truncated" in message.lower()
    assert "larger model" in message.lower() or "small" in message.lower()


def test_error_context_with_model_name() -> None:
    """Test ErrorContext includes model name when provided."""
    ctx = ErrorContext(
        stage=GenerationStage.SCENES,
        attempt=1,
        max_attempts=3,
        model_name="ministral-3:3b",
    )
    message = ctx.format_user_message("Test error")
    assert "ministral-3:3b" in message
