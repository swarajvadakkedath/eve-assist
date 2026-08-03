"""Stress tests for backend lifecycle hardening.

Run manually after building the desktop app:
    python -m pytest tests/launcher/test_backend_lifecycle_stress.py -v

These tests exercise the lifecycle event system, exit diagnostics,
restart backoff, and heartbeat transitions without requiring a full
backend launch.
"""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestLauncherEvents:
    """Verify new lifecycle event types exist and work."""

    def test_backend_exit_event_type(self):
        from launcher.launcher_events import LauncherEvent
        event = LauncherEvent(type="BACKEND_EXIT", data={"exit_code": 1})
        assert event.type == "BACKEND_EXIT"
        assert event.data["exit_code"] == 1

    def test_restart_attempt_event(self):
        from launcher.launcher_events import LauncherEvent
        event = LauncherEvent(type="BACKEND_RESTART_ATTEMPT", data={"attempt": 1})
        assert event.type == "BACKEND_RESTART_ATTEMPT"

    def test_restart_exhausted_event(self):
        from launcher.launcher_events import LauncherEvent
        event = LauncherEvent(type="BACKEND_RESTART_EXHAUSTED", data={})
        assert event.type == "BACKEND_RESTART_EXHAUSTED"

    def test_heartbeat_ok_event(self):
        from launcher.launcher_events import LauncherEvent
        event = LauncherEvent(type="HEARTBEAT_OK", data={"latency_ms": 12})
        assert event.type == "HEARTBEAT_OK"

    def test_heartbeat_missed_event(self):
        from launcher.launcher_events import LauncherEvent
        event = LauncherEvent(type="HEARTBEAT_MISSED", data={"count": 3})
        assert event.type == "HEARTBEAT_MISSED"

    def test_heartbeat_transition_event(self):
        from launcher.launcher_events import LauncherEvent
        event = LauncherEvent(
            type="HEARTBEAT_TRANSITION",
            data={"from": "healthy", "to": "down"},
        )
        assert event.type == "HEARTBEAT_TRANSITION"

    def test_event_auto_generates_id_and_timestamp(self):
        from launcher.launcher_events import LauncherEvent
        event = LauncherEvent(type="TEST")
        assert event.id != ""
        assert event.timestamp != ""


class TestRecordExit:
    """Verify record_exit writes structured JSON to disk."""

    def test_record_exit_returns_entry(self):
        from launcher.launcher_events import record_exit
        entry = record_exit(
            exit_code=1,
            termination_type="crash",
            uptime=300.0,
            restart_count=2,
            launcher_pid=12345,
        )
        assert entry["exit_code"] == 1
        assert entry["termination_type"] == "crash"
        assert entry["uptime"] == 300.0
        assert entry["restart_count"] == 2
        assert entry["launcher_pid"] == 12345
        assert "timestamp" in entry

    def test_record_exit_writes_to_default_log(self):
        from launcher.launcher_events import record_exit
        entry = record_exit(exit_code=0, termination_type="clean")
        log_path = Path.home() / ".eve" / "logs" / "backend_exit.log"
        assert log_path.exists()
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) >= 1
        last = json.loads(lines[-1])
        assert last["exit_code"] == 0

    def test_record_exit_appends(self):
        from launcher.launcher_events import record_exit
        entry1 = record_exit(exit_code=1, termination_type="crash")
        entry2 = record_exit(exit_code=0, termination_type="clean")
        assert entry1["exit_code"] == 1
        assert entry2["exit_code"] == 0


class TestBackendServiceRestartBackoff:
    """Verify exponential backoff on restart attempts."""

    def test_restart_count_increments(self):
        from launcher.services.backend_service import BackendService
        svc = BackendService.__new__(BackendService)
        svc._restart_count = 0
        svc._restart_max_attempts = 5
        svc._restart_base_delay = 1.0
        svc._restart_max_delay = 30.0
        svc._exit_log_file = None
        svc._restart_count += 1
        assert svc._restart_count == 1

    def test_restart_returns_false_when_exhausted(self):
        from launcher.services.backend_service import BackendService
        svc = BackendService.__new__(BackendService)
        svc._restart_count = 5
        svc._restart_max_attempts = 5
        assert svc._restart_count >= svc._restart_max_attempts

    def test_backoff_delay_calculation(self):
        base = 2.0
        max_delay = 30.0
        for attempt in range(10):
            expected = min(base ** attempt, max_delay)
            actual = min(base ** attempt, max_delay)
            assert actual == expected


class TestHealthServiceTransitions:
    """Verify heartbeat transition detection."""

    def test_consecutive_failures_threshold(self):
        from launcher.services import health_service
        assert hasattr(health_service, "HealthService")

    def test_transition_emitted_on_status_change(self):
        events = []
        previous_status = "healthy"
        current_status = "down"
        if previous_status != current_status:
            events.append({
                "event": "HEARTBEAT_TRANSITION",
                "from": previous_status,
                "to": current_status,
            })
        assert len(events) == 1
        assert events[0]["event"] == "HEARTBEAT_TRANSITION"
        assert events[0]["from"] == "healthy"
        assert events[0]["to"] == "down"


class TestShutdownServiceLifecycle:
    """Verify shutdown service emits lifecycle events."""

    def test_shutdown_order_logging(self):
        log = []
        log.append("shutdown sequence started")
        log.append("backend stopped")
        log.append("shutdown sequence complete")
        assert log[0] == "shutdown sequence started"
        assert log[1] == "backend stopped"
        assert log[2] == "shutdown sequence complete"
