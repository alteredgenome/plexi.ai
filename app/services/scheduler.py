import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

@dataclass
class TimeBlock:
    start: datetime.datetime
    end: datetime.datetime
    block_type: str # "event", "buffer_travel", "buffer_recovery", "habit", "task"
    title: str
    id: Optional[int] = None
    is_fixed: bool = True
    priority: int = 0 # higher = harder to displace

class DynamicScheduler:
    def __init__(self, work_start_hour: int = 9, work_end_hour: int = 18, base_capacity_minutes: int = 480):
        self.work_start_hour = work_start_hour
        self.work_end_hour = work_end_hour
        self.base_capacity_minutes = base_capacity_minutes

    def calculate_adjusted_capacity(self, fatigue_scaling_factor: float = 1.0) -> int:
        """Scales daily capacity minutes based on biometric recovery factor."""
        factor = max(0.4, min(1.3, fatigue_scaling_factor))
        return int(self.base_capacity_minutes * factor)

    def extract_busy_intervals(
        self,
        events: List[Dict[str, Any]],
        habits: List[Dict[str, Any]],
        target_date: datetime.date
    ) -> List[TimeBlock]:
        """
        Builds occupied time intervals for a target date including travel and recovery buffers.
        """
        busy_blocks: List[TimeBlock] = []

        for ev in events:
            ev_start = ev["start_time"]
            ev_end = ev["end_time"]
            
            # If string, parse to datetime
            if isinstance(ev_start, str):
                ev_start = datetime.datetime.fromisoformat(ev_start)
            if isinstance(ev_end, str):
                ev_end = datetime.datetime.fromisoformat(ev_end)

            if ev_start.date() != target_date and ev_end.date() != target_date:
                continue

            # Add pre-event travel buffer if specified
            travel_mins = ev.get("travel_buffer_before_minutes", 0)
            if travel_mins > 0:
                t_start = ev_start - datetime.timedelta(minutes=travel_mins)
                busy_blocks.append(TimeBlock(
                    start=t_start,
                    end=ev_start,
                    block_type="buffer_travel",
                    title=f"Travel Buffer: {ev.get('title', 'Event')}",
                    id=ev.get("id"),
                    is_fixed=True,
                    priority=100
                ))

            # Fixed event itself
            busy_blocks.append(TimeBlock(
                start=ev_start,
                end=ev_end,
                block_type="event",
                title=ev.get("title", "Event"),
                id=ev.get("id"),
                is_fixed=True,
                priority=100
            ))

            # Post-event recovery buffer if specified
            recovery_mins = ev.get("recovery_buffer_after_minutes", 0)
            if recovery_mins > 0:
                r_end = ev_end + datetime.timedelta(minutes=recovery_mins)
                busy_blocks.append(TimeBlock(
                    start=ev_end,
                    end=r_end,
                    block_type="buffer_recovery",
                    title=f"Recovery Buffer: {ev.get('title', 'Event')}",
                    id=ev.get("id"),
                    is_fixed=True,
                    priority=90
                ))

        # Habit blocks for the day
        weekday_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
        today_abbr = weekday_map[target_date.weekday()]

        for habit in habits:
            days = habit.get("days_of_week", "").lower()
            if today_abbr not in days:
                continue

            duration = habit.get("duration_minutes", 30)
            window = habit.get("target_time_window", "morning")
            strictness = habit.get("defense_strictness", "protected")
            prio = 80 if strictness == "lock" else (50 if strictness == "protected" else 20)

            # Assign default anchor based on window
            if window == "morning":
                h_start = datetime.datetime.combine(target_date, datetime.time(hour=max(self.work_start_hour - 1, 8), minute=0))
            elif window == "afternoon":
                h_start = datetime.datetime.combine(target_date, datetime.time(hour=13, minute=0))
            elif window == "evening":
                h_start = datetime.datetime.combine(target_date, datetime.time(hour=min(self.work_end_hour, 18), minute=0))
            else:
                h_start = datetime.datetime.combine(target_date, datetime.time(hour=self.work_start_hour, minute=0))

            h_end = h_start + datetime.timedelta(minutes=duration)
            busy_blocks.append(TimeBlock(
                start=h_start,
                end=h_end,
                block_type="habit",
                title=f"Habit: {habit.get('title')}",
                id=habit.get("id"),
                is_fixed=(strictness == "lock"),
                priority=prio
            ))

        # Sort blocks chronologically
        busy_blocks.sort(key=lambda b: b.start)
        return busy_blocks

    def find_free_slots(
        self,
        busy_blocks: List[TimeBlock],
        target_date: datetime.date,
        day_start_hour: Optional[int] = None,
        day_end_hour: Optional[int] = None
    ) -> List[Tuple[datetime.datetime, datetime.datetime]]:
        """
        Calculates all free, continuous available time slots between working hours.
        """
        start_h = day_start_hour if day_start_hour is not None else self.work_start_hour
        end_h = day_end_hour if day_end_hour is not None else self.work_end_hour

        day_start = datetime.datetime.combine(target_date, datetime.time(hour=start_h, minute=0))
        day_end = datetime.datetime.combine(target_date, datetime.time(hour=end_h, minute=0))

        free_slots: List[Tuple[datetime.datetime, datetime.datetime]] = []
        current_cursor = day_start

        # Merge overlapping busy blocks
        merged_blocks: List[Tuple[datetime.datetime, datetime.datetime]] = []
        for block in sorted(busy_blocks, key=lambda b: b.start):
            b_start = max(day_start, block.start)
            b_end = min(day_end, block.end)
            if b_start >= b_end:
                continue
            if not merged_blocks:
                merged_blocks.append((b_start, b_end))
            else:
                last_s, last_e = merged_blocks[-1]
                if b_start <= last_e:
                    merged_blocks[-1] = (last_s, max(last_e, b_end))
                else:
                    merged_blocks.append((b_start, b_end))

        for b_start, b_end in merged_blocks:
            if current_cursor < b_start:
                free_slots.append((current_cursor, b_start))
            current_cursor = max(current_cursor, b_end)

        if current_cursor < day_end:
            free_slots.append((current_cursor, day_end))

        return free_slots

    def auto_schedule_tasks(
        self,
        tasks: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        habits: List[Dict[str, Any]],
        target_date: datetime.date,
        fatigue_scaling_factor: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        Intelligently places tasks into free slots sorted by priority and deadline.
        Enforces daily bio-scaled capacity.
        """
        prio_weights = {"P1": 4, "P2": 3, "P3": 2, "P4": 1}
        
        # Filter and sort tasks
        schedulable_tasks = [t for t in tasks if t.get("auto_schedule", True) and not t.get("is_completed", False)]
        
        def task_sort_key(t):
            p = prio_weights.get(t.get("priority", "P3"), 1)
            is_crit = 1 if t.get("momentum_critical") else 0
            # Deadline urgency
            dl = t.get("deadline")
            dl_ts = 9999999999
            if dl:
                if isinstance(dl, str):
                    dl = datetime.datetime.fromisoformat(dl)
                dl_ts = dl.timestamp()
            # Sort: Momentum Critical first, then High Priority (P1 > P4), then earliest deadline
            return (-is_crit, -p, dl_ts)

        schedulable_tasks.sort(key=task_sort_key)

        adjusted_capacity = self.calculate_adjusted_capacity(fatigue_scaling_factor)
        busy_blocks = self.extract_busy_intervals(events, habits, target_date)
        free_slots = self.find_free_slots(busy_blocks, target_date)

        scheduled_results: List[Dict[str, Any]] = []
        allocated_minutes = 0

        current_slot_idx = 0
        slot_offset_minutes = 0

        for task in schedulable_tasks:
            duration = task.get("duration_minutes", 30)
            
            # Check capacity exhaustion
            if allocated_minutes + duration > adjusted_capacity:
                task_res = dict(task)
                task_res["scheduled_start"] = None
                task_res["scheduled_end"] = None
                task_res["schedule_status"] = "deferred_capacity_limit"
                scheduled_results.append(task_res)
                continue

            placed = False
            while current_slot_idx < len(free_slots):
                slot_start, slot_end = free_slots[current_slot_idx]
                effective_start = slot_start + datetime.timedelta(minutes=slot_offset_minutes)
                potential_end = effective_start + datetime.timedelta(minutes=duration)

                if potential_end <= slot_end:
                    task_res = dict(task)
                    task_res["scheduled_start"] = effective_start.isoformat()
                    task_res["scheduled_end"] = potential_end.isoformat()
                    task_res["schedule_status"] = "scheduled"
                    scheduled_results.append(task_res)
                    
                    slot_offset_minutes += duration
                    allocated_minutes += duration
                    placed = True
                    break
                else:
                    # Move to next slot
                    current_slot_idx += 1
                    slot_offset_minutes = 0

            if not placed:
                task_res = dict(task)
                task_res["scheduled_start"] = None
                task_res["scheduled_end"] = None
                task_res["schedule_status"] = "unfit_no_slot"
                scheduled_results.append(task_res)

        return scheduled_results

    @staticmethod
    def mask_private_events(events: List[Dict[str, Any]], viewer_user_id: int) -> List[Dict[str, Any]]:
        """
        Sanitizes events based on visibility and viewing user permissions.
        """
        masked = []
        for ev in events:
            owner_id = ev.get("user_id")
            vis = ev.get("visibility", "full")
            if owner_id == viewer_user_id or vis == "full" or vis == "public":
                masked.append(ev)
            else:
                # Private masked event
                masked.append({
                    "id": ev.get("id"),
                    "calendar_id": ev.get("calendar_id"),
                    "user_id": owner_id,
                    "title": "Busy",
                    "description": None,
                    "location": None,
                    "start_time": ev.get("start_time"),
                    "end_time": ev.get("end_time"),
                    "is_all_day": ev.get("is_all_day", False),
                    "is_masked": True
                })
        return masked
