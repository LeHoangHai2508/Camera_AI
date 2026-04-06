"""
event_logger.py — CSV event logging for alerts.

Writes events to a CSV file with columns:
    event_id, camera_id, roi_id, event_type,
    start_time_sec, end_time_sec, duration_sec,
    trigger_state, snapshot_path, video_name
"""

import csv
import os
from pathlib import Path
from typing import Optional

from common import ensure_dir


class EventLogger:
    """Append-mode CSV logger for alert events."""

    HEADER = [
        "event_id",
        "camera_id",
        "roi_id",
        "event_type",
        "start_time_sec",
        "end_time_sec",
        "duration_sec",
        "trigger_state",
        "snapshot_path",
        "video_name",
    ]

    def __init__(self, csv_path: str, video_name: str = "",
                 camera_id: str = "cam01"):
        self.csv_path = csv_path
        self.video_name = video_name
        self.camera_id = camera_id
        self._counter = 0

        # Create directory and write header if file doesn't exist
        ensure_dir(str(Path(csv_path).parent))
        if not os.path.exists(csv_path):
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.HEADER)

    def log_event(self, roi_id: str, event_type: str,
                  start_sec: float, end_sec: float,
                  trigger_state: str = "",
                  snapshot_path: str = ""):
        """Append one event row to the CSV file."""
        self._counter += 1
        duration = round(end_sec - start_sec, 2)
        row = [
            self._counter,
            self.camera_id,
            roi_id,
            event_type,
            round(start_sec, 2),
            round(end_sec, 2),
            duration,
            trigger_state,
            snapshot_path,
            self.video_name,
        ]
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)

    def log_start(self, roi_id: str, event_type: str,
                  start_sec: float, trigger_state: str = "",
                  snapshot_path: str = ""):
        """Log an event start (end_sec and duration will be 0)."""
        self._counter += 1
        row = [
            self._counter,
            self.camera_id,
            roi_id,
            event_type,
            round(start_sec, 2),
            "",  # end_time_sec — not yet
            "",  # duration_sec — not yet
            trigger_state,
            snapshot_path,
            self.video_name,
        ]
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)
        return self._counter  # return event_id for later update
