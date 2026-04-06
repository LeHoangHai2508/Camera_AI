"""
event_logger.py — CSV event logging for alerts.
"""

import csv
import os
from pathlib import Path
from typing import Optional

from src.utils.common import ensure_dir


class EventLogger:
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

    def __init__(self, csv_path: str, video_name: str = "", camera_id: str = "cam01"):
        self.csv_path = csv_path
        self.video_name = video_name
        self.camera_id = camera_id
        self._counter = 0

        ensure_dir(str(Path(csv_path).parent))
        if not os.path.exists(csv_path):
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.HEADER)

    def log_event(
        self,
        roi_id: str,
        event_type: str,
        start_sec: float,
        end_sec: float,
        trigger_state: str = "",
        snapshot_path: str = "",
    ):
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

    def log_start(
        self,
        roi_id: str,
        event_type: str,
        start_sec: float,
        trigger_state: str = "",
        snapshot_path: str = "",
    ):
        self._counter += 1
        row = [
            self._counter,
            self.camera_id,
            roi_id,
            event_type,
            round(start_sec, 2),
            "",
            "",
            trigger_state,
            snapshot_path,
            self.video_name,
        ]
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)
        return self._counter