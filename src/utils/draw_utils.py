"""
draw_utils.py — Overlay rendering for video output.

Draws ROI polygons, person bounding boxes with track IDs,
ROI state labels, timers, and alert banners.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional

from src.utils.common import (
    COLOR_GREEN, COLOR_RED, COLOR_YELLOW, COLOR_CYAN,
    COLOR_WHITE, COLOR_BLACK, COLOR_ORANGE,
    STATE_COLORS, FONT_FACE, FONT_SCALE, FONT_THICK,
    sec_to_mmss,
)


# ── Polygon Drawing ──────────────────────────────────────────

def draw_polygon(frame: np.ndarray, points: List[List[int]],
                 color: Tuple[int, int, int] = COLOR_CYAN,
                 thickness: int = 2, label: str = None,
                 fill_alpha: float = 0.15):
    """Draw a polygon outline with optional semi-transparent fill."""
    pts = np.array(points, dtype=np.int32)

    # Semi-transparent fill
    if fill_alpha > 0:
        overlay = frame.copy()
        cv2.fillPoly(overlay, [pts], color)
        cv2.addWeighted(overlay, fill_alpha, frame, 1 - fill_alpha, 0, frame)

    # Outline
    cv2.polylines(frame, [pts], isClosed=True, color=color,
                  thickness=thickness)

    # Label
    if label:
        x, y = pts[0]
        cv2.putText(frame, label, (x, y - 8), FONT_FACE,
                    FONT_SCALE, color, FONT_THICK)


# ── Person BBox ───────────────────────────────────────────────

def draw_person_bbox(frame: np.ndarray,
                     x1: int, y1: int, x2: int, y2: int,
                     track_id: int = None,
                     color: Tuple[int, int, int] = COLOR_GREEN,
                     thickness: int = 2):
    """Draw bounding box around a person with optional track ID."""
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

    label = f"ID:{track_id}" if track_id is not None else "person"
    (tw, th), _ = cv2.getTextSize(label, FONT_FACE, FONT_SCALE, FONT_THICK)
    cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
    cv2.putText(frame, label, (x1 + 2, y1 - 4), FONT_FACE,
                FONT_SCALE, COLOR_WHITE, FONT_THICK)


# ── ROI State Label ──────────────────────────────────────────

def draw_roi_state(frame: np.ndarray, points: List[List[int]],
                   state: str, roi_id: str = ""):
    """Draw ROI polygon colored by state and label the state."""
    color = STATE_COLORS.get(state, COLOR_CYAN)
    label = f"{roi_id}: {state}" if roi_id else state
    draw_polygon(frame, points, color=color, thickness=2,
                 label=label, fill_alpha=0.20)


# ── Timer Display ────────────────────────────────────────────

def draw_timer(frame: np.ndarray, x: int, y: int,
               elapsed_sec: float, label: str,
               color: Tuple[int, int, int] = COLOR_YELLOW):
    """Draw an elapsed-time timer at a given position."""
    text = f"{label}: {sec_to_mmss(elapsed_sec)}"
    cv2.putText(frame, text, (x, y), FONT_FACE,
                FONT_SCALE, color, FONT_THICK)


# ── Alert Banner ─────────────────────────────────────────────

def draw_alert_banner(frame: np.ndarray, text: str,
                      color: Tuple[int, int, int] = COLOR_RED,
                      y_offset: int = 0):
    """Draw a full-width alert banner at the top of the frame."""
    h, w = frame.shape[:2]
    banner_h = 40
    y_start = y_offset
    y_end = y_offset + banner_h

    # Semi-transparent background
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, y_start), (w, y_end), color, -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    # Text centered
    (tw, th), _ = cv2.getTextSize(text, FONT_FACE, 0.7, 2)
    tx = (w - tw) // 2
    ty = y_start + (banner_h + th) // 2
    cv2.putText(frame, text, (tx, ty), FONT_FACE, 0.7,
                COLOR_WHITE, 2)


# ── Info Panel ────────────────────────────────────────────────

def draw_info_panel(frame: np.ndarray, lines: List[str],
                    x: int = 10, y_start: int = None):
    """Draw a small info panel in the bottom-left corner."""
    h, w = frame.shape[:2]
    if y_start is None:
        y_start = h - 20 * len(lines) - 10

    for i, line in enumerate(lines):
        y = y_start + i * 20
        cv2.putText(frame, line, (x, y), FONT_FACE,
                    0.5, COLOR_WHITE, 1)
