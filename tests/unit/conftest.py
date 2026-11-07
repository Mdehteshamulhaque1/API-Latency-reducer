"""
Unit-test fixtures that do not require live Redis or database services.
"""
import pytest_asyncio


@pytest_asyncio.fixture(scope="session", autouse=True)
async def app_env():
    """Override the integration suite's database/Redis bootstrap."""
    yield


@pytest_asyncio.fixture(autouse=True)
async def _clean_state():
    """Override the integration suite's Redis cleanup fixture."""
    yield
