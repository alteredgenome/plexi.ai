import pytest
from app.services.integrations.ringconn import RingConnService
from app.services.integrations.pavlok import PavlokClient
from app.services.integrations.home_assistant import HomeAssistantClient
from app.services.integrations.pixel_watch import PixelWatchService

def test_ringconn_readiness_scaling():
    # Optimal recovery
    res_high = RingConnService.parse_biometrics({"sleep_score": 90, "readiness_score": 90})
    assert res_high["recovery_status"] == "optimal"
    assert res_high["fatigue_scaling_factor"] == 1.15

    # Fatigued recovery
    res_low = RingConnService.parse_biometrics({"sleep_score": 40, "readiness_score": 40})
    assert res_low["recovery_status"] == "fatigued"
    assert res_low["fatigue_scaling_factor"] == 0.6

@pytest.mark.asyncio
async def test_pavlok_nudge_simulation():
    client = PavlokClient()
    res = await client.send_nudge(stimulus_type="vibration", intensity=60, reason="Test Alert")
    assert res["status"] == "mock_success"
    assert res["stimulus_type"] == "vibration"
    assert res["intensity"] == 60

@pytest.mark.asyncio
async def test_home_assistant_scene_simulation():
    client = HomeAssistantClient()
    res = await client.trigger_scene("focus_time")
    assert res["status"] == "mock_success"
    assert res["entity_id"] == "scene.focus_time"

def test_pixel_watch_notification_formatting():
    notif = PixelWatchService.format_task_notification(
        task_title="Deep Work Session",
        priority="P1",
        start_time="10:00"
    )
    assert notif["title"] == "[P1] Next Task: Deep Work Session"
    assert len(notif["actions"]) == 3
