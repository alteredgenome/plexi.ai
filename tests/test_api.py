import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import init_db

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"

@pytest.mark.asyncio
async def test_auth_and_task_lifecycle():
    unique_email = f"test.exec.{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Register user
        reg_res = await ac.post("/api/v1/auth/register", json={
            "email": unique_email,
            "password": "strongpassword123",
            "full_name": "Test Executive",
            "timezone": "UTC"
        })
        assert reg_res.status_code == 200
        user_id = reg_res.json()["id"]

        # 2. Login
        login_res = await ac.post("/api/v1/auth/token", data={
            "username": unique_email,
            "password": "strongpassword123"
        })
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Create Task
        task_res = await ac.post("/api/v1/tasks/", headers=headers, json={
            "title": "Strategy Briefing",
            "priority": "P1",
            "duration_minutes": 30,
            "momentum_critical": True
        })
        assert task_res.status_code == 200
        task_id = task_res.json()["id"]

        # 4. Ingest Biometrics
        bio_res = await ac.post("/api/v1/biometrics/ingest", headers=headers, json={
            "date": "2026-09-02",
            "sleep_score": 85.0,
            "readiness_score": 85.0
        })
        assert bio_res.status_code == 200

        # 5. Run Auto-Schedule
        sched_res = await ac.post("/api/v1/tasks/auto-schedule?target_date=2026-09-02", headers=headers)
        assert sched_res.status_code == 200
        sched_data = sched_res.json()
        assert sched_data["tasks_scheduled_count"] >= 1

        # 6. Test AI Assistant Chat
        chat_res = await ac.post("/api/v1/agent/chat", headers=headers, json={
            "messages": [{"role": "user", "content": "Set focus lights for deep work"}]
        })
        assert chat_res.status_code == 200
        assert len(chat_res.json()["tool_calls"]) > 0
