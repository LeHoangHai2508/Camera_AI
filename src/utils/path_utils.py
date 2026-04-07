from __future__ import annotations

import sys
from pathlib import Path


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def resource_path(path_str: str) -> str:
    if not path_str:
        return ""
    p = Path(path_str)
    if p.is_absolute():
        return str(p)
    return str((app_base_dir() / p).resolve())


def file_output_path(path_str: str) -> str:
    p = Path(resource_path(path_str))
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p)


def dir_output_path(path_str: str) -> str:
    p = Path(resource_path(path_str))
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


def to_portable_path(path_str: str) -> str:
    if not path_str:
        return ""
    p = Path(path_str)
    try:
        rel = p.resolve().relative_to(app_base_dir().resolve())
        return rel.as_posix()
    except Exception:
        return str(p)