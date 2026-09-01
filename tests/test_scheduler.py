import pytest
import datetime
from app.services.scheduler import DynamicScheduler, TimeBlock

def test_buffer_extraction():
    scheduler = DynamicScheduler(work_start_hour=9, work_end_hour=18)
    target_date = datetime.date(2026, 9, 2)
    
    events = [
        {
            "id": 1,
            "title": "Strategy Sync",
            "start_time": datetime.datetime(2026, 9, 2, 10, 0),
            "end_time": datetime.datetime(2026, 9, 2, 11, 0),
            "travel_buffer_before_minutes": 15,
            "recovery_buffer_after_minutes": 15
        }
    ]
    habits = []

    blocks = scheduler.extract_busy_intervals(events, habits, target_date)
    # Expect 3 blocks: travel buffer (9:45-10:00), event (10:00-11:00), recovery buffer (11:00-11:15)
    assert len(blocks) == 3
    assert blocks[0].block_type == "buffer_travel"
    assert blocks[0].start == datetime.datetime(2026, 9, 2, 9, 45)
    assert blocks[1].block_type == "event"
    assert blocks[2].block_type == "buffer_recovery"
    assert blocks[2].end == datetime.datetime(2026, 9, 2, 11, 15)

def test_find_free_slots():
    scheduler = DynamicScheduler(work_start_hour=9, work_end_hour=17)
    target_date = datetime.date(2026, 9, 2)
    
    busy = [
        TimeBlock(
            start=datetime.datetime(2026, 9, 2, 12, 0),
            end=datetime.datetime(2026, 9, 2, 13, 0),
            block_type="event",
            title="Lunch Meeting"
        )
    ]
    
    free_slots = scheduler.find_free_slots(busy, target_date)
    # Expect 2 free slots: 09:00 - 12:00 (180 mins) and 13:00 - 17:00 (240 mins)
    assert len(free_slots) == 2
    assert free_slots[0] == (datetime.datetime(2026, 9, 2, 9, 0), datetime.datetime(2026, 9, 2, 12, 0))
    assert free_slots[1] == (datetime.datetime(2026, 9, 2, 13, 0), datetime.datetime(2026, 9, 2, 17, 0))

def test_auto_schedule_priority_and_buffers():
    scheduler = DynamicScheduler(work_start_hour=9, work_end_hour=17, base_capacity_minutes=480)
    target_date = datetime.date(2026, 9, 2)

    events = [
        {
            "id": 1,
            "title": "Client Meeting",
            "start_time": datetime.datetime(2026, 9, 2, 10, 0),
            "end_time": datetime.datetime(2026, 9, 2, 11, 0),
            "travel_buffer_before_minutes": 15,
            "recovery_buffer_after_minutes": 15
        }
    ]
    habits = []
    tasks = [
        {"id": 101, "title": "Critical Bugfix", "priority": "P1", "duration_minutes": 30, "auto_schedule": True},
        {"id": 102, "title": "Momentum Habit Task", "priority": "P2", "duration_minutes": 30, "momentum_critical": True, "auto_schedule": True},
        {"id": 103, "title": "Low Priority Cleanup", "priority": "P4", "duration_minutes": 60, "auto_schedule": True}
    ]

    results = scheduler.auto_schedule_tasks(tasks, events, habits, target_date, fatigue_scaling_factor=1.0)
    
    # Momentum critical task should be placed first
    assert results[0]["id"] == 102
    assert results[0]["schedule_status"] == "scheduled"
    assert results[0]["scheduled_start"] == "2026-09-02T09:00:00"
    assert results[0]["scheduled_end"] == "2026-09-02T09:30:00"

    # P1 task placed second (09:30 - 10:00 is blocked by travel buffer starting at 09:45, so 30m fits 09:30-10:00? No, buffer is 09:45, so slot 1 is 09:00-09:45, fits 30m)
    # The 30m P1 task won't fit into remaining 15m (09:30-09:45), so it moves to next free slot after recovery buffer (11:15 onwards)
    assert results[1]["id"] == 101
    assert results[1]["schedule_status"] == "scheduled"
    assert results[1]["scheduled_start"] == "2026-09-02T11:15:00"

def test_privacy_masking():
    events = [
        {"id": 1, "user_id": 10, "visibility": "full", "title": "Open Office Hours"},
        {"id": 2, "user_id": 10, "visibility": "private_masked", "title": "Confidential Doctor Visit"}
    ]
    
    # Viewer is owner (user 10)
    owner_view = DynamicScheduler.mask_private_events(events, viewer_user_id=10)
    assert owner_view[1]["title"] == "Confidential Doctor Visit"

    # Viewer is roommate (user 20)
    roommate_view = DynamicScheduler.mask_private_events(events, viewer_user_id=20)
    assert roommate_view[0]["title"] == "Open Office Hours"
    assert roommate_view[1]["title"] == "Busy"
    assert roommate_view[1]["is_masked"] is True
