"""
config_utils.py — Load and validate configuration files.
"""

import json
import yaml
from pathlib import Path
from typing import Any, Dict, List


# ── ROI Config ────────────────────────────────────────────────

def load_roi_config(json_path: str) -> Dict[str, Any]:
    """
    Load ROI configuration from a JSON file.

    Returns dict with keys:
        camera_id, video_path, worker_rois, buffer_rois
    Each ROI entry has 'id' and 'points' (list of [x, y]).
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"ROI config not found: {json_path}")

    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Basic validation
    for key in ("camera_id", "worker_rois", "buffer_rois"):
        if key not in cfg:
            raise KeyError(f"Missing required key '{key}' in ROI config")

    return cfg


def get_roi_points(roi_entry: Dict) -> List[List[int]]:
    """Extract polygon points from a single ROI entry."""
    return roi_entry.get("points", [])


# ── Rules Config ──────────────────────────────────────────────

def load_rules(yaml_path: str) -> Dict[str, Any]:
    """
    Load rule engine configuration from a YAML file.

    Expected keys:
        camera_id, worker_absence, backlog_alert
    """
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Rules config not found: {yaml_path}")

    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    return cfg


# ── Runtime Config ────────────────────────────────────────────

def load_runtime(yaml_path: str) -> Dict[str, Any]:
    """
    Load runtime/inference configuration from a YAML file.
    """
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Runtime config not found: {yaml_path}")

    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    return cfg


# ── Class Names Config ────────────────────────────────────────

def load_class_names(yaml_path: str) -> Dict[str, Any]:
    """
    Load class name mappings from a YAML file.
    """
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Class names config not found: {yaml_path}")

    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    return cfg


# ── Convenience ───────────────────────────────────────────────

def load_all_configs(roi_path: str, rules_path: str,
                     runtime_path: str = None) -> Dict[str, Any]:
    """Load ROI + rules (+ optional runtime) configs into one dict."""
    result = {
        "roi": load_roi_config(roi_path),
        "rules": load_rules(rules_path),
    }
    if runtime_path:
        result["runtime"] = load_runtime(runtime_path)
    return result
