import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.agent import OpenRouterAgent
from app.services.integrations.home_assistant import HomeAssistantClient

router = APIRouter(prefix="/voice", tags=["Voice Protocol & Assist Pipeline"])

@router.websocket("/ws")
async def voice_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for bidirectional real-time voice/intent communication.
    Compatible with browser audio stream, Home Assistant Assist, and Wyoming protocol events.
    """
    await websocket.accept()
    agent = OpenRouterAgent()

    try:
        await websocket.send_json({
            "type": "ready",
            "message": "Voice pipeline connected. Speak or stream audio/text intent.",
            "supported_codecs": ["pcm_16000", "webm_opus", "text_intent"]
        })

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type", "text_intent")

            if msg_type == "text_intent" or msg_type == "transcript":
                transcript = message.get("text", "")
                
                # Stream acknowledgement
                await websocket.send_json({
                    "type": "processing",
                    "transcript": transcript
                })

                # Route to LLM / Tool calling orchestrator
                response = await agent.chat([{"role": "user", "content": transcript}])

                # Send synthesis / action result
                await websocket.send_json({
                    "type": "response",
                    "text": response.get("content", ""),
                    "tool_calls": response.get("tool_calls", []),
                    "audio_synthesis_url": None, # Hook for Piper TTS / HA voice
                    "finished": True
                })

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "error": str(e)})
        except Exception:
            pass
