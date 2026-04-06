"""
common.py — Shared constants and helper functions.
"""

import os
from datetime import datetime


# ── Colors (BGR for OpenCV) ───────────────────────────────────
COLOR_GREEN   = (0, 200, 0)
COLOR_RED     = (0, 0, 220)
COLOR_YELLOW  = (0, 220, 255)
COLOR_CYAN    = (255, 220, 0)
COLOR_WHITE   = (255, 255, 255)
COLOR_BLACK   = (0, 0, 0)
COLOR_ORANGE  = (0, 140, 255)
COLOR_MAGENTA = (200, 0, 200)

# ── ROI state → display color ────────────────────────────────
STATE_COLORS = {
    "empty":    COLOR_GREEN,
    "normal":   COLOR_CYAN,
    "full":     COLOR_YELLOW,
    "overload": COLOR_RED,
}

# ── Font ──────────────────────────────────────────────────────
FONT_SCALE   = 0.6
FONT_THICK   = 2
FONT_FACE    = None          # set after cv2 import


def _init_font():
    import cv2
    global FONT_FACE
    FONT_FACE = cv2.FONT_HERSHEY_SIMPLEX


_init_font()


# ── Helpers ───────────────────────────────────────────────────

def ensure_dir(path: str):
    """Create directory (and parents) if it does not exist."""
    os.makedirs(path, exist_ok=True)


def ts_now_str() -> str:
    """Return a file-safe timestamp string, e.g. '20260329_223045'."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def sec_to_mmss(seconds: float) -> str:
    """Convert seconds to MM:SS string."""
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"


def frame_to_sec(frame_idx: int, fps: float) -> float:
    """Convert frame index to seconds."""
    return frame_idx / fps if fps > 0 else 0.0
