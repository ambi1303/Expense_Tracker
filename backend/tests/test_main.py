"""
Tests for main application setup
"""
import pytest
from httpx import AsyncClient


@pytest.mark.unit
async def test_root_endpoint(client: AsyncClient):
    """Test the health check endpoint"""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Gmail AI Expense Tracker API"
    assert "version" in data


@pytest.mark.unit
async def test_docs_endpoint(client: AsyncClient):
    """Test that OpenAPI docs are available"""
    response = await client.get("/docs")
    assert response.status_code == 200
