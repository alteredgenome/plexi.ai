import httpx
from typing import Optional, Dict, Any
from app.config import settings

class PavlokClient:
    """
    Client for Pavlok 3 Shock Clock API (vibrate, beep, zap nudges).
    Used to keep momentum on critical, overdue tasks.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.PAVLOK_API_KEY
        self.base_url = "https://api.pavlok.com/api/v1"

    async def send_nudge(
        self,
        stimulus_type: str = "beep", # "vibration", "beep", "shock"
        intensity: int = 50, # 1 - 100
        count: int = 1,
        reason: str = "Momentum Task Alert"
    ) -> Dict[str, Any]:
        if not self.api_key:
            return {
                "status": "mock_success",
                "stimulus_type": stimulus_type,
                "intensity": intensity,
                "count": count,
                "reason": reason,
                "message": "Pavlok API key not configured. Stimulus simulated successfully."
            }

        endpoint = f"{self.base_url}/stimuli/send/{stimulus_type}"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "val": intensity,
            "count": count,
            "reason": reason
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(endpoint, json=payload, headers=headers)
                resp.raise_for_status()
                return {"status": "success", "data": resp.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}
