"""Shared pytest fixtures for fabulae tests."""

from collections.abc import Generator

import pytest
from faker import Faker


@pytest.fixture
def fake() -> Generator[Faker, None, None]:
    """Provide a seeded Faker instance for deterministic test data."""
    yield Faker()
    Faker.seed(1337)
