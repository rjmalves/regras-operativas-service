"""Pytest configuration and fixtures."""

import logging

import pytest

from app.utils.log import Log


@pytest.fixture(autouse=True, scope="session")
def configure_logging():
    """Configure logging for tests."""
    # Set up a basic logger for tests
    if Log.LOGGER is None:
        logger = logging.getLogger("main")
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(handler)
        Log.LOGGER = logger
    yield
