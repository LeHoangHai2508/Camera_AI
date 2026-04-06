"""
rule_engine.py — Alert state machines for business rules.

Two rules:
    1. WorkerAbsenceRule — alert when no person in worker ROI for T seconds
    2. BacklogRule — alert when buffer ROI state is full/overload for T seconds

Each rule emits (event_type, start/end) transitions suitable for
EventLogger.
"""

from typing import Optional, Dict, Any


class WorkerAbsenceRule:
    """
    State machine: detects when a worker is absent from their
    position for longer than `threshold_sec`.

    States:
        NORMAL   — person is present
        COUNTING — person absent, counting up
        ALERT    — threshold exceeded, alert active

    Transitions:
        person present  → reset to NORMAL
        person absent   → start/continue COUNTING
        counting >= T   → switch to ALERT
        person returns  → emit close event, back to NORMAL
    """

    def __init__(self, roi_id: str, threshold_sec: float = 15.0):
        self.roi_id = roi_id
        self.threshold_sec = threshold_sec

        # Internal state
        self._state = "NORMAL"       # NORMAL | COUNTING | ALERT
        self._absence_start: Optional[float] = None
        self._alert_start: Optional[float] = None

    def update(self, person_present: bool,
               current_sec: float) -> Optional[Dict[str, Any]]:
        """
        Update rule with current frame data.

        Args:
            person_present: True if at least one person in worker ROI
            current_sec: current video time in seconds

        Returns:
            dict with event info if a state transition occurs:
                {"action": "start" | "end",
                 "event_type": "worker_absence",
                 "roi_id": str,
                 "time_sec": float,
                 "elapsed_sec": float}
            or None if no transition
        """
        event = None

        if person_present:
            # ── Person returned ───────────────────────────────
            if self._state == "ALERT":
                elapsed = current_sec - self._alert_start if self._alert_start else 0
                event = {
                    "action": "end",
                    "event_type": "worker_absence",
                    "roi_id": self.roi_id,
                    "time_sec": current_sec,
                    "start_sec": self._alert_start,
                    "elapsed_sec": round(elapsed, 2),
                }
            self._state = "NORMAL"
            self._absence_start = None
            self._alert_start = None

        else:
            # ── Person absent ─────────────────────────────────
            if self._state == "NORMAL":
                self._state = "COUNTING"
                self._absence_start = current_sec

            if self._state == "COUNTING":
                elapsed = current_sec - self._absence_start
                if elapsed >= self.threshold_sec:
                    self._state = "ALERT"
                    self._alert_start = self._absence_start
                    event = {
                        "action": "start",
                        "event_type": "worker_absence",
                        "roi_id": self.roi_id,
                        "time_sec": current_sec,
                        "start_sec": self._absence_start,
                        "elapsed_sec": round(elapsed, 2),
                    }

        return event

    @property
    def is_alert(self) -> bool:
        return self._state == "ALERT"

    @property
    def absence_elapsed(self) -> float:
        """Seconds since absence started (0 if not absent)."""
        if self._absence_start is None:
            return 0.0
        return 0.0  # caller should compute from current_sec

    def get_elapsed(self, current_sec: float) -> float:
        """Get elapsed absence time at given moment."""
        if self._absence_start is not None:
            return current_sec - self._absence_start
        return 0.0


class BacklogRule:
    """
    State machine: detects when a buffer ROI is in a "trigger" state
    (e.g., full or overload) for longer than `threshold_sec`.

    States:
        NORMAL   — ROI state is acceptable
        COUNTING — ROI in trigger state, counting up
        ALERT    — threshold exceeded, alert active

    Transitions:
        state not in triggers → reset to NORMAL
        state in triggers     → start/continue COUNTING
        counting >= T         → switch to ALERT
        state normalizes      → emit close event, back to NORMAL
    """

    def __init__(self, roi_id: str, threshold_sec: float = 20.0,
                 trigger_states: list = None):
        self.roi_id = roi_id
        self.threshold_sec = threshold_sec
        self.trigger_states = trigger_states or ["full", "overload"]

        # Internal state
        self._state = "NORMAL"
        self._backlog_start: Optional[float] = None
        self._alert_start: Optional[float] = None
        self._last_trigger_state: str = ""

    def update(self, stable_state: str,
               current_sec: float) -> Optional[Dict[str, Any]]:
        """
        Update rule with current smoothed ROI state.

        Args:
            stable_state: smoothed classification output
            current_sec: current video time in seconds

        Returns:
            dict with event info on transition, or None
        """
        event = None
        is_trigger = stable_state in self.trigger_states

        if not is_trigger:
            # ── Back to normal ────────────────────────────────
            if self._state == "ALERT":
                elapsed = current_sec - self._alert_start if self._alert_start else 0
                event = {
                    "action": "end",
                    "event_type": "backlog_alert",
                    "roi_id": self.roi_id,
                    "time_sec": current_sec,
                    "start_sec": self._alert_start,
                    "elapsed_sec": round(elapsed, 2),
                    "trigger_state": self._last_trigger_state,
                }
            self._state = "NORMAL"
            self._backlog_start = None
            self._alert_start = None

        else:
            # ── In trigger state ──────────────────────────────
            self._last_trigger_state = stable_state

            if self._state == "NORMAL":
                self._state = "COUNTING"
                self._backlog_start = current_sec

            if self._state == "COUNTING":
                elapsed = current_sec - self._backlog_start
                if elapsed >= self.threshold_sec:
                    self._state = "ALERT"
                    self._alert_start = self._backlog_start
                    event = {
                        "action": "start",
                        "event_type": "backlog_alert",
                        "roi_id": self.roi_id,
                        "time_sec": current_sec,
                        "start_sec": self._backlog_start,
                        "elapsed_sec": round(elapsed, 2),
                        "trigger_state": stable_state,
                    }

        return event

    @property
    def is_alert(self) -> bool:
        return self._state == "ALERT"

    def get_elapsed(self, current_sec: float) -> float:
        """Get elapsed backlog time at given moment."""
        if self._backlog_start is not None:
            return current_sec - self._backlog_start
        return 0.0
