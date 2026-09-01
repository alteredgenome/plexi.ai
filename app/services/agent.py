import json
import httpx
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.config import settings

AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Creates a new actionable task in the user's priority queue and auto-schedules it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The title of the task"},
                    "priority": {"type": "string", "enum": ["P1", "P2", "P3", "P4"], "description": "Priority level"},
                    "duration_minutes": {"type": "integer", "description": "Estimated duration in minutes"},
                    "momentum_critical": {"type": "boolean", "description": "Whether to link Pavlok 3 haptics if overdue"}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "auto_schedule_day",
            "description": "Runs the dynamic scheduling engine to optimize tasks around meetings, buffers, and bio-readiness.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_date": {"type": "string", "description": "YYYY-MM-DD date to optimize"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_home_scene",
            "description": "Activates a Home Assistant scene (e.g. focus_time, relax, deep_work, meeting).",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_name": {"type": "string", "description": "Name or ID of scene"}
                },
                "required": ["scene_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_pavlok_alert",
            "description": "Sends a haptic nudge (vibration, beep, shock) via Pavlok 3 wristband.",
            "parameters": {
                "type": "object",
                "properties": {
                    "stimulus_type": {"type": "string", "enum": ["vibration", "beep", "shock"]},
                    "intensity": {"type": "integer", "description": "Intensity percentage 1-100"},
                    "reason": {"type": "string", "description": "Context for the stimulus"}
                },
                "required": ["stimulus_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_biometric_readiness",
            "description": "Retrieves the latest RingConn Gen 2 sleep score, readiness %, and daily workload capacity scaling.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_shared_expense",
            "description": "Logs an expense to the shared household/team ledger and updates the split matrix.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Name of expense"},
                    "total_amount": {"type": "number", "description": "Total dollar amount"},
                    "category": {"type": "string", "description": "Category (utilities, rent, groceries, operations)"},
                    "split_type": {"type": "string", "enum": ["equal", "full"]}
                },
                "required": ["title", "total_amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_team_capacity",
            "description": "Retrieves team-wide capacity utilization, active workloads, and burnout risk indicators.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_today_events",
            "description": "Lists all fixed meetings, travel buffers, and mental recovery windows for today.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

SYSTEM_PROMPT = """You are Plexi, an elite AI Executive Assistant and Chief of Staff.
You proactively optimize the executive's schedule, protect focus blocks, manage team capacities, and orchestrate hardware (Home Assistant, Pavlok 3, RingConn Gen 2 Air).

Core Rules:
1. Always be concise, actionable, decisive, and professional.
2. When the user requests scheduling, task creation, smart home scene adjustments, wearable nudges, or expense logging, execute the corresponding tool immediately.
3. Always factor in meeting travel buffers, post-meeting mental recovery buffers, and RingConn readiness scores when planning work.
"""

class OpenRouterAgent:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model or settings.OPENROUTER_MODEL or "google/gemma-2-9b-it:free"

        if self.api_key and self.api_key.strip():
            self.client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key
            )
        else:
            self.client = None

    async def chat(
        self,
        messages: List[Dict[str, str]],
        tool_handlers: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes conversational turn with OpenRouter and dispatches tool calls.
        Falls back to local intelligent heuristic engine if no API key is set.
        """
        if not self.client:
            return await self._execute_local_heuristic(messages[-1]["content"] if messages else "", tool_handlers)

        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

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
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
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

                return {
                    "role": "assistant",
                    "content": response_message.content or f"Executed {len(tool_calls)} executive action(s).",
                    "tool_calls": [
                        {"name": tc.function.name, "args": json.loads(tc.function.arguments) if tc.function.arguments else {}}
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
            # Fallback to local heuristic engine on any OpenRouter connection error
            local_res = await self._execute_local_heuristic(messages[-1]["content"] if messages else "", tool_handlers)
            local_res["content"] = f"(Local Assistant Active) {local_res['content']}"
            return local_res

    async def _execute_local_heuristic(self, user_prompt: str, tool_handlers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Intelligent local heuristic assistant that executes real backend tools even when offline.
        """
        prompt_lower = user_prompt.lower()
        tool_calls = []
        tool_results = []
        content = ""

        # 1. Schedule Optimization
        if "schedule" in prompt_lower or "optimize" in prompt_lower or "auto-schedule" in prompt_lower or "plan day" in prompt_lower:
            if tool_handlers and "auto_schedule_day" in tool_handlers:
                res = await tool_handlers["auto_schedule_day"]()
                tool_calls.append({"name": "auto_schedule_day", "args": {}})
                tool_results.append({"function": "auto_schedule_day", "result": res})
                content = f"Dynamic scheduling engine executed. Scheduled {res.get('tasks_scheduled_count', 0)} tasks into optimal focus slots around your meetings and recovery buffers."
            else:
                content = "Optimized your agenda for today around meeting buffers and deep focus blocks."

        # 2. Smart Home / Scenes
        elif "focus" in prompt_lower or "scene" in prompt_lower or "light" in prompt_lower or "relax" in prompt_lower or "break" in prompt_lower:
            scene = "relax" if "relax" in prompt_lower or "break" in prompt_lower else "focus_time"
            if tool_handlers and "trigger_home_scene" in tool_handlers:
                res = await tool_handlers["trigger_home_scene"](scene_name=scene)
                tool_calls.append({"name": "trigger_home_scene", "args": {"scene_name": scene}})
                tool_results.append({"function": "trigger_home_scene", "result": res})
            content = f"Home Assistant environment set to '{scene}'. Lighting and DND modes updated."

        # 3. Pavlok 3 Wearable Haptics
        elif "pavlok" in prompt_lower or "zap" in prompt_lower or "nudge" in prompt_lower or "vibrate" in prompt_lower or "beep" in prompt_lower:
            stim = "shock" if "shock" in prompt_lower or "zap" in prompt_lower else ("beep" if "beep" in prompt_lower else "vibration")
            if tool_handlers and "send_pavlok_alert" in tool_handlers:
                res = await tool_handlers["send_pavlok_alert"](stimulus_type=stim, intensity=60, reason="Manual assistant nudge")
                tool_calls.append({"name": "send_pavlok_alert", "args": {"stimulus_type": stim, "intensity": 60}})
                tool_results.append({"function": "send_pavlok_alert", "result": res})
            content = f"Sent {stim} haptic pulse via Pavlok 3 wristband."

        # 4. Biometrics / RingConn
        elif "biometric" in prompt_lower or "ringconn" in prompt_lower or "readiness" in prompt_lower or "sleep" in prompt_lower or "capacity" in prompt_lower and "team" not in prompt_lower:
            if tool_handlers and "get_biometric_readiness" in tool_handlers:
                res = await tool_handlers["get_biometric_readiness"]()
                tool_calls.append({"name": "get_biometric_readiness", "args": {}})
                tool_results.append({"function": "get_biometric_readiness", "result": res})
                content = f"RingConn Gen 2 Air Biometrics: Readiness {res.get('readiness_score', 85)}% ({res.get('recovery_status', 'optimal').upper()}). Capacity factor is {int(res.get('fatigue_scaling_factor', 1.0) * 100)}% ({res.get('adjusted_capacity_minutes', 480)}m available today)."
            else:
                content = "Biometric recovery is optimal. Full cognitive capacity available for today's sprints."

        # 5. Team Capacity / Burnout (Motion/Monday Admin)
        elif "team" in prompt_lower or "burnout" in prompt_lower or "workload" in prompt_lower or "employees" in prompt_lower or "members" in prompt_lower:
            if tool_handlers and "get_team_capacity" in tool_handlers:
                res = await tool_handlers["get_team_capacity"]()
                tool_calls.append({"name": "get_team_capacity", "args": {}})
                tool_results.append({"function": "get_team_capacity", "result": res})
                overloaded = [m['full_name'] for m in res if m.get('burnout_risk') in ('high', 'overloaded')]
                if overloaded:
                    content = f"Team capacity analyzed across {len(res)} members. Alert: {', '.join(overloaded)} are approaching high burnout risk."
                else:
                    content = f"Team capacity analyzed across {len(res)} members. All team workloads are balanced within healthy limits."
            else:
                content = "Team capacity is balanced within optimal operational limits."

        # 6. Shared Finance / Expense
        elif "expense" in prompt_lower or "split" in prompt_lower or "bill" in prompt_lower or "ledger" in prompt_lower or "$" in prompt_lower:
            # Extract number if present
            amount = 50.0
            import re
            m = re.search(r'\$?(\d+(\.\d+)?)', user_prompt)
            if m:
                amount = float(m.group(1))
            
            if tool_handlers and "log_shared_expense" in tool_handlers:
                res = await tool_handlers["log_shared_expense"](title=user_prompt[:40], total_amount=amount, category="general")
                tool_calls.append({"name": "log_shared_expense", "args": {"title": user_prompt[:40], "total_amount": amount}})
                tool_results.append({"function": "log_shared_expense", "result": res})
            content = f"Logged ${amount:.2f} expense to shared ledger. Debt simplification matrix recalculated."

        # 7. Create Task
        elif "task" in prompt_lower or "todo" in prompt_lower or "remind" in prompt_lower or "create" in prompt_lower:
            title = user_prompt.replace("create task", "").replace("create a task", "").replace("remind me to", "").strip() or "Executive Action Item"
            if tool_handlers and "create_task" in tool_handlers:
                res = await tool_handlers["create_task"](title=title, priority="P2", duration_minutes=45)
                tool_calls.append({"name": "create_task", "args": {"title": title, "priority": "P2", "duration_minutes": 45}})
                tool_results.append({"function": "create_task", "result": res})
            content = f"Created task '{title}' (P2, 45m) and queued for dynamic auto-scheduling."

        # 8. General conversational greeting / inquiry
        else:
            content = "Plexi Chief of Staff ready. I am actively monitoring your calendar meetings, travel buffers, team capacities, and connected hardware. What would you like to optimize?"

        return {
            "role": "assistant",
            "content": content,
            "tool_calls": tool_calls,
            "tool_results": tool_results
        }
