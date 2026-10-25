"""Fixtures for testing.

Needs ``pytest-homeassistant-custom-component``; the Energy Advisor virtual
environment has it: ``../energyadvisor/venv/bin/python -m pytest``.
"""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""
    return
