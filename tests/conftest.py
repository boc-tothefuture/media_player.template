"""Configuration for pytest."""
import pathlib
import pytest
import custom_components

# Add the project's custom_components to custom_components path
PROJECT_CUSTOM_COMPONENTS = str(pathlib.Path(__file__).parent.parent / "custom_components")
if PROJECT_CUSTOM_COMPONENTS not in custom_components.__path__:
    custom_components.__path__.insert(0, PROJECT_CUSTOM_COMPONENTS)

pytest_plugins = ["pytest_homeassistant_custom_component"]

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield
