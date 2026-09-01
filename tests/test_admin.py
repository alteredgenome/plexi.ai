import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import init_db

@pytest.mark.asyncio
async def test_admin_user_and_hardware_management():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Register Admin User
        await ac.post("/api/v1/auth/register", json={
            "email": "corp.admin@plexi.fyi",
            "password": "adminpassword123",
            "full_name": "Executive Admin",
            "timezone": "America/New_York"
        })
        login_res = await ac.post("/api/v1/auth/token", data={
            "username": "corp.admin@plexi.fyi",
            "password": "adminpassword123"
        })
        admin_token = login_res.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. Register standard member
        await ac.post("/api/v1/auth/register", json={
            "email": "employee1@plexi.fyi",
            "password": "userpassword123",
            "full_name": "Senior Engineer",
            "timezone": "America/New_York"
        })
        user_login = await ac.post("/api/v1/auth/token", data={
            "username": "employee1@plexi.fyi",
            "password": "userpassword123"
        })
        user_token = user_login.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}

        # 3. Standard user should be forbidden from admin API
        forbidden_res = await ac.get("/api/v1/admin/users", headers=user_headers)
        assert forbidden_res.status_code == 403

        # 4. Admin creates/provisions a new team member
        create_res = await ac.post("/api/v1/admin/users", headers=admin_headers, json={
            "email": "sarah.lead@plexi.fyi",
            "password": "newuserpass123",
            "full_name": "Sarah Connor",
            "role": "manager",
            "department": "Engineering",
            "timezone": "America/Los_Angeles",
            "work_start_hour": 8,
            "work_end_hour": 17,
            "daily_capacity_minutes": 540
        })
        assert create_res.status_code == 200
        new_user = create_res.json()
        sarah_id = new_user["id"]
        assert new_user["role"] == "manager"
        assert new_user["department"] == "Engineering"

        # 5. Admin assigns Pavlok 3 Wearable to Sarah
        assign_pavlok = await ac.post("/api/v1/admin/devices/assign", headers=admin_headers, json={
            "user_id": sarah_id,
            "provider": "pavlok",
            "device_name": "Sarah's Pavlok 3 Wristband",
            "device_id": "PVLK-99812",
            "credentials": {"api_key": "test_pavlok_token_abc"}
        })
        assert assign_pavlok.status_code == 200

        # 6. Admin assigns RingConn Gen 2 Air to Sarah
        assign_ring = await ac.post("/api/v1/admin/devices/assign", headers=admin_headers, json={
            "user_id": sarah_id,
            "provider": "ringconn",
            "device_name": "Sarah's RingConn Gen 2 Air (Matte Black)",
            "device_id": "RNG-5521",
            "credentials": {"api_key": "ring_token_xyz"}
        })
        assert assign_ring.status_code == 200

        # 7. Admin tests Pavlok device stimulus
        test_stim = await ac.post("/api/v1/admin/devices/test", headers=admin_headers, json={
            "user_id": sarah_id,
            "provider": "pavlok",
            "stimulus_type": "vibration",
            "intensity": 60
        })
        assert test_stim.status_code == 200
        assert test_stim.json()["status"] == "success"

        # 8. Query Team Capacity Overview
        cap_res = await ac.get("/api/v1/admin/team-capacity", headers=admin_headers)
        assert cap_res.status_code == 200
        team = cap_res.json()
        assert len(team) >= 2
        sarah_overview = next(m for m in team if m["user_id"] == sarah_id)
        assert sarah_overview["daily_capacity_minutes"] == 540
        assert sarah_overview["burnout_risk"] == "low"
