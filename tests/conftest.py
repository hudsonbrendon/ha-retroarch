"""Fixtures for RetroArch tests."""
from unittest.mock import AsyncMock, patch

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in all tests."""
    yield


@pytest.fixture(autouse=True)
def mock_github_release():
    """Keep the update entity offline by default (no real GitHub call in tests)."""
    with patch(
        "custom_components.retroarch.update.async_fetch_latest_version",
        new=AsyncMock(return_value=None),
    ):
        yield
