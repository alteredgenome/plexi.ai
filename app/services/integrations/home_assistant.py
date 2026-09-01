import httpx
from typing import Optional, Dict, Any
from app.config import settings

class HomeAssistantClient:
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        self.base_url = (base_url or settings.HOME_ASSISTANT_URL or "").rstrip("/")
        self.token = token or settings.HOME_ASSISTANT_TOKEN

    @property
    def headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def trigger_scene(self, scene_name: str) -> Dict[str, Any]:
        """
        Triggers a scene in Home Assistant, e.g. 'scene.focus_time', 'scene.relax'
        """
        if not scene_name.startswith("scene."):
            entity_id = f"scene.{scene_name}"
        else:
            entity_id = scene_name

        if not self.token:
            return {"status": "mock_success", "entity_id": entity_id, "message": "Home Assistant token not set; running in simulated mode"}

        url = f"{self.base_url}/api/services/scene/turn_on"
        payload = {"entity_id": entity_id}

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(url, json=payload, headers=self.headers)
                resp.raise_for_status()
                return {"status": "success", "entity_id": entity_id, "data": resp.json()}
        except Exception as e:
            return {"status": "error", "entity_id": entity_id, "error": str(e)}

    async def toggle_light(self, entity_id: str, state: str = "toggle", brightness_pct: Optional[int] = None) -> Dict[str, Any]:
        """
        Turns on/off or adjusts brightness of lighting.
        """
        service = "turn_on" if state == "on" else ("turn_off" if state == "off" else "toggle")
        url = f"{self.base_url}/api/services/light/{service}"
        
        payload: Dict[str, Any] = {"entity_id": entity_id}
        if brightness_pct is not None and service == "turn_on":
            payload["brightness_pct"] = brightness_pct

        if not self.token:
            return {"status": "mock_success", "service": service, "payload": payload}

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(url, json=payload, headers=self.headers)
                resp.raise_for_status()
                return {"status": "success", "data": resp.json()}
        except Exception as e:
            return {"status": "error", "error": str(e)}
