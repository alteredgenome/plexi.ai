import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import init_db

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()

@pytest.mark.asyncio
async def test_setup_status_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/setup/status")
        assert res.status_code == 200
        data = res.json()
        assert data["instance_name"] == "Plexi"
        assert "is_setup_completed" in data
