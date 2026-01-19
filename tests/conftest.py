"""Pytest configuration and fixtures for JARVIS tests."""

import pytest


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings for testing."""
    monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
    monkeypatch.setenv("GARMIN_PASSWORD", "test_password")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/test_vault")


@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary Obsidian vault for testing."""
    vault = tmp_path / "vault"
    vault.mkdir()

    # Create daily notes folder
    daily = vault / "Daily Notes"
    daily.mkdir()

    # Create a sample daily note
    note = daily / "2026-01-19.md"
    note.write_text("""# 2026-01-19

## Food
- **Breakfast**: Oatmeal, coffee
- **Lunch**: Salad, chicken
- **Dinner**: Salmon, rice

## Training
Easy 5K run at recovery pace

## Notes
Testing JARVIS integration.
""")

    return vault
