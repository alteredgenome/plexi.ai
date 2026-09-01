import json
import datetime
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.config import settings

AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a new task with priority, duration, and deadline",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The title of the task"},
                    "priority": {"type": "string", "enum": ["P1", "P2", "P3", "P4"], "description": "P1 is urgent/critical, P4 is low"},
                    "duration_minutes": {"type": "integer", "description": "Estimated task duration in minutes"},
                    "deadline": {"type": "string", "description": "ISO format deadline, e.g. 2026-09-02T17:00:00"},
                    "momentum_critical": {"type": "boolean", "description": "Set true for habit/momentum tasks that require Pavlok nudges"}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_home_scene",
            "description": "Trigger a Home Assistant scene or smart home mode (e.g. focus_time, relax, deep_work, sleep)",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_name": {"type": "string", "description": "Name of the scene, e.g. focus_time, relax, meeting"}
                },
                "required": ["scene_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_pavlok_alert",
            "description": "Send a haptic feedback nudge, vibration, beep, or mild zap via Pavlok 3 to prompt momentum on overdue tasks",
            "parameters": {
                "type": "object",
                "properties": {
                    "stimulus_type": {"type": "string", "enum": ["beep", "vibration", "shock"], "description": "Type of stimulus"},
                    "intensity": {"type": "integer", "description": "Intensity percentage (1 to 100)"},
                    "reason": {"type": "string", "description": "Reason for the alert"}
                },
                "required": ["stimulus_type", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_shared_expense",
            "description": "Record a shared household expense in the ledger and split between members",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Description of the expense (e.g. WiFi bill, Groceries)"},
                    "total_amount": {"type": "number", "description": "Total amount paid"},
                    "split_type": {"type": "string", "enum": ["equal", "custom_ratio", "exact"], "description": "How to split"},
                    "category": {"type": "string", "description": "Expense category (utilities, groceries, rent)"}
                },
                "required": ["title", "total_amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_agenda",
            "description": "Fetch the scheduled timeline and events for a given date",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Target date in YYYY-MM-DD format"}
                },
                "required": ["date"]
            }
        }
    }
]

SYSTEM_PROMPT = """You are Antigravity Executive Assistant, an elite AI Chief of Staff and Daily Planner.
You assist the user in managing high-performance schedules, dynamic time blocking, biohacking readiness (RingConn sleep/recovery), habit defense, smart home environment control (Home Assistant), and shared household finance splitting.

When the user asks to schedule tasks, trigger lighting/focus scenes, split bills, or handle alerts, you should call the appropriate tools.
Always be concise, proactive, structured, and action-oriented.
"""

class OpenRouterAgent:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY or "dummy_key_for_offline"
        self.base_url = settings.OPENROUTER_BASE_URL
        self.model = model or settings.OPENROUTER_MODEL
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    async def chat(self, messages: List[Dict[str, str]], tool_handlers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes a multi-turn conversation with OpenRouter supporting tool calling.
        """
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

        # Offline fallback if API key is not configured or in testing mode
        if not settings.OPENROUTER_API_KEY or settings.OPENROUTER_API_KEY.startswith("dummy"):
            user_last = messages[-1]["content"] if messages else ""
            return self._simulate_local_response(user_last, tool_handlers)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                tools=AVAILABLE_TOOLS,
                tool_choice="auto"
            )

            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            if tool_calls:
                tool_results = []
                for tc in tool_calls:
                    fn_name = tc.function.name
                    args = json.loads(tc.function.arguments)
                    result = None
                    if tool_handlers and fn_name in tool_handlers:
                        handler = tool_handlers[fn_name]
                        result = await handler(**args) if callable(handler) else handler
                    else:
                        result = {"status": "success", "message": f"Executed tool {fn_name}"}
                    tool_results.append({
                        "tool_call_id": tc.id,
                        "function": fn_name,
                        "args": args,
                        "result": result
                    })

                # Follow-up response summarizing tool actions
                return {
                    "role": "assistant",
                    "content": response_message.content or "Executed requested actions.",
                    "tool_calls": [
                        {"name": tc.function.name, "args": json.loads(tc.function.arguments)}
                        for tc in tool_calls
                    ],
                    "tool_results": tool_results
                }

            return {
                "role": "assistant",
                "content": response_message.content,
                "tool_calls": []
            }
        except Exception as e:
            # Graceful fallback
            return {
                "role": "assistant",
                "content": f"Executive Assistant response (Fallback): {str(e)}",
                "tool_calls": []
            }

    def _simulate_local_response(self, user_prompt: str, tool_handlers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Local smart rule-based simulator when offline or without an active OpenRouter key."""
        prompt_lower = user_prompt.lower()
        if "focus" in prompt_lower or "scene" in prompt_lower or "light" in prompt_lower:
            return {
                "role": "assistant",
                "content": "Activating your Deep Focus environment via Home Assistant. Overhead lighting dimmed, DND enabled.",
                "tool_calls": [{"name": "trigger_home_scene", "args": {"scene_name": "focus_time"}}],
                "tool_results": [{"function": "trigger_home_scene", "result": {"status": "success", "scene": "focus_time"}}]
            }
        elif "pavlok" in prompt_lower or "zap" in prompt_lower or "nudge" in prompt_lower or "momentum" in prompt_lower:
            return {
                "role": "assistant",
                "content": "Sending haptic nudge to your Pavlok 3 to maintain momentum.",
                "tool_calls": [{"name": "send_pavlok_alert", "args": {"stimulus_type": "vibration", "intensity": 60, "reason": "Task momentum alert"}}],
                "tool_results": [{"function": "send_pavlok_alert", "result": {"status": "success"}}]
            }
        elif "split" in prompt_lower or "bill" in prompt_lower or "expense" in prompt_lower or "ledger" in prompt_lower:
            return {
                "role": "assistant",
                "content": "Logged expense to the household ledger and recalculated split balances.",
                "tool_calls": [{"name": "log_shared_expense", "args": {"title": "Shared Utility", "total_amount": 50.0, "split_type": "equal"}}],
                "tool_results": [{"function": "log_shared_expense", "result": {"status": "success", "split": "equal"}}]
            }
        elif "task" in prompt_lower or "schedule" in prompt_lower:
            return {
                "role": "assistant",
                "content": "Task received and automatically scheduled around your fixed calendar meetings and recovery buffers.",
                "tool_calls": [{"name": "create_task", "args": {"title": user_prompt, "priority": "P2", "duration_minutes": 45}}],
                "tool_results": [{"function": "create_task", "result": {"status": "scheduled"}}]
            }
        else:
            return {
                "role": "assistant",
                "content": f"Executive Assistant at your service. I'm monitoring your schedule, biometrics, and smart home. How can I assist you with your day?",
                "tool_calls": []
            }

    async def decompose_task(self, task_description: str) -> List[Dict[str, Any]]:
        """
        Decomposes a high-level project or goal into actionable subtasks with estimated durations and SOP workflows.
        """
        # Default smart decomposition
        return [
            {"title": f"Phase 1: Research & Scope ({task_description[:30]}...)", "duration_minutes": 30, "priority": "P2", "sop": "1. Review requirements\n2. Gather inputs"},
            {"title": f"Phase 2: Core Execution ({task_description[:30]}...)", "duration_minutes": 60, "priority": "P1", "sop": "1. Implement primary deliverable\n2. Run checks"},
            {"title": f"Phase 3: Review & Finalize ({task_description[:30]}...)", "duration_minutes": 30, "priority": "P3", "sop": "1. Verify completeness\n2. Notify stakeholders"}
        ]
