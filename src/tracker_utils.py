"""
tracker_utils.py — ROI geometry helpers and state smoothing.

Provides:
    - point_in_polygon: check if a point is inside a polygon
    - bbox_center: get center of a bounding box
    - is_bbox_in_roi: check if a bbox center is inside a ROI
    - StateSmoother: majority-vote smoothing over N recent predictions
"""

import numpy as np
from collections import Counter, deque
from typing import List, Tuple, Optional


# ── Geometry Helpers ──────────────────────────────────────────

def point_in_polygon(point: Tuple[int, int],
                     polygon: List[List[int]]) -> bool:
    """
    Ray-casting algorithm to test if a point is inside a polygon.

    Args:
        point: (x, y) coordinates
        polygon: list of [x, y] vertices

    Returns:
        True if point is inside the polygon
    """
    x, y = point
    n = len(polygon)
    inside = False

    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]

        if ((yi > y) != (yj > y)) and \
           (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i

    return inside


def bbox_center(x1: int, y1: int, x2: int, y2: int) -> Tuple[int, int]:
    """Return center point of a bounding box."""
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    return (cx, cy)


def is_bbox_in_roi(bbox: Tuple[int, int, int, int],
                   roi_points: List[List[int]]) -> bool:
    """
    Check if the center of a bounding box falls inside a ROI polygon.

    Args:
        bbox: (x1, y1, x2, y2) bounding box coordinates
        roi_points: polygon vertices as list of [x, y]

    Returns:
        True if bbox center is inside ROI
    """
    cx, cy = bbox_center(*bbox)
    return point_in_polygon((cx, cy), roi_points)


def filter_persons_in_roi(bboxes: List[Tuple[int, int, int, int]],
                          track_ids: List[int],
                          roi_points: List[List[int]]) -> List[int]:
    """
    Return track IDs of persons whose bbox center is inside the ROI.

    Args:
        bboxes: list of (x1, y1, x2, y2)
        track_ids: list of track IDs (same length as bboxes)
        roi_points: polygon vertices

    Returns:
        list of track IDs inside the ROI
    """
    inside_ids = []
    for bbox, tid in zip(bboxes, track_ids):
        if is_bbox_in_roi(bbox, roi_points):
            inside_ids.append(tid)
    return inside_ids


# ── State Smoothing ──────────────────────────────────────────

class StateSmoother:
    """
    Majority-vote smoothing over a sliding window of predictions.

    Reduces frame-to-frame noise in classification outputs.
    """

    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.buffer = deque(maxlen=window_size)

    def update(self, state: str) -> str:
        """Add a prediction and return the smoothed (majority) state."""
        self.buffer.append(state)
        return self.get_stable_state()

    def get_stable_state(self) -> str:
        """Return the most common state in the buffer."""
        if not self.buffer:
            return "unknown"
        counter = Counter(self.buffer)
        return counter.most_common(1)[0][0]

    def reset(self):
        """Clear the buffer."""
        self.buffer.clear()


# ── Person Presence Tracker ──────────────────────────────────

class PresenceTracker:
    """
    Track whether at least one person is present in a ROI,
    with a grace period to avoid flicker.

    grace_frames: number of consecutive "absent" frames before
                  confirming absence (e.g., 3 frames).
    """

    def __init__(self, grace_frames: int = 3):
        self.grace_frames = grace_frames
        self._absent_count = 0
        self.present = False

    def update(self, person_detected: bool) -> bool:
        """
        Update presence state.

        Returns True if person is present (or within grace period).
        """
        if person_detected:
            self._absent_count = 0
            self.present = True
        else:
            self._absent_count += 1
            if self._absent_count > self.grace_frames:
                self.present = False

        return self.present

    def reset(self):
        self._absent_count = 0
        self.present = False
