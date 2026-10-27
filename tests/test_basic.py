"""
Basic test to ensure CI/CD pipeline works.
This file contains minimal tests to validate the test infrastructure.
"""
import pytest


def test_basic():
    """A basic test to ensure pytest is working."""
    assert True


def test_config_import():
    """Test that configuration can be imported."""
    from app.core.config import settings
    assert settings.APP_NAME == "SPMS Academic Hub"
