import pytest


@pytest.mark.asyncio
async def test_get_teaser_success(client):
    """Verify that teaser returns metadata without leaking the full fact text or explanation."""
    response = await client.get("/api/facts/teaser")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "title" in data
    assert "teaser" in data
    assert "category" in data
    # Security: full fact and explanation must NOT be present in teaser response
    assert "fact_text" not in data
    assert "explanation" not in data
    assert data["is_unlocked"] is False


@pytest.mark.asyncio
async def test_get_categories(client):
    """Verify listing categories with counts."""
    response = await client.get("/api/facts/categories")
    assert response.status_code == 200
    cats = response.json()
    assert len(cats) >= 2
    cat_names = [c["name"] for c in cats]
    assert "Space" in cat_names
    assert "India" in cat_names


@pytest.mark.asyncio
async def test_locked_fact_access_blocked(client):
    """Verify that attempting to fetch locked full fact returns HTTP 402 Payment Required."""
    response = await client.get("/api/facts/1?session_id=unpaid_session_12345")
    assert response.status_code == 402
    assert "locked" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_nonexistent_fact_404(client):
    """Verify that querying a non-existent fact ID returns 404."""
    response = await client.get("/api/facts/99999?session_id=some_session")
    assert response.status_code == 404
