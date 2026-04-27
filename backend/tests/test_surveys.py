"""Tests for Survey CRUD endpoints."""

import pytest


@pytest.mark.asyncio
async def test_list_surveys_returns_empty_list(async_client):
    """GET /api/v1/surveys should return an empty list when no surveys exist."""
    # TODO: Implement
    pass


@pytest.mark.asyncio
async def test_create_survey(async_client):
    """POST /api/v1/surveys should persist a manually authored survey."""
    # TODO: Implement
    pass


@pytest.mark.asyncio
async def test_get_survey_by_id(async_client):
    """GET /api/v1/surveys/{id} should return the correct survey."""
    # TODO: Implement
    pass


@pytest.mark.asyncio
async def test_update_survey(async_client):
    """PUT /api/v1/surveys/{id} should update the survey data."""
    # TODO: Implement
    pass


@pytest.mark.asyncio
async def test_delete_survey(async_client):
    """DELETE /api/v1/surveys/{id} should return 204 and remove the survey."""
    # TODO: Implement
    pass
