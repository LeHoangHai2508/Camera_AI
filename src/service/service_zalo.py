from pathlib import Path
from typing import Any, Dict, List
import json
import time

import requests
import yaml
from fastapi import FastAPI, HTTPException

from src.utils.path_utils import app_base_dir

ROOT = app_base_dir()
CFG_PATH = ROOT / "configs" / "zalo_service.yaml"
LOG_DIR = ROOT / "outputs" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
OUTBOX_LOG = LOG_DIR / "zalo_outbox.jsonl"

app = FastAPI(title="AI Camera Zalo Webhook")


def load_cfg() -> Dict[str, Any]:
    if not CFG_PATH.exists():
        raise FileNotFoundError(f"Khong tim thay config: {CFG_PATH}")

    with open(CFG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError("Noi dung config khong hop le")
    return data


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def fmt_mmss(v: Any) -> str:
    try:
        v = float(v)
        m = int(v // 60)
        s = int(v % 60)
        return f"{m:02d}:{s:02d}"
    except Exception:
        return str(v)


def build_text(event: Dict[str, Any]) -> str:
    event_type = str(event.get("event_type", ""))
    trigger_state = str(event.get("trigger_state", ""))
    camera_id = str(event.get("camera_id", ""))
    roi_id = str(event.get("roi_id", ""))
    video_name = str(event.get("video_name", ""))
    start_sec = fmt_mmss(event.get("start_time_sec", ""))
    end_sec = fmt_mmss(event.get("end_time_sec", ""))
    snapshot_path = str(event.get("snapshot_path", ""))

    return (
        "[AI CAMERA CANH BAO]\n"
        f"Camera: {camera_id}\n"
        f"ROI: {roi_id}\n"
        f"Video: {video_name}\n"
        f"Su kien: {event_type}\n"
        f"Trang thai: {trigger_state}\n"
        f"Bat dau: {start_sec}\n"
        f"Ket thuc: {end_sec}\n"
        f"Snapshot local: {snapshot_path}"
    )


def get_zalo_cfg() -> Dict[str, Any]:
    cfg = load_cfg().get("zalo", {})
    if not isinstance(cfg, dict):
        raise ValueError("Section 'zalo' trong config khong hop le")

    access_token = str(cfg.get("access_token", "")).strip()
    send_api_url = str(cfg.get("send_api_url", "")).strip()
    timeout_sec = int(cfg.get("timeout_sec", 15))

    recipient_uids = cfg.get("recipient_uids", [])
    if not isinstance(recipient_uids, list):
        recipient_uids = []

    recipient_uids = [str(x).strip() for x in recipient_uids if str(x).strip()]

    if not access_token:
        raise ValueError("Thieu zalo.access_token")
    if not send_api_url:
        raise ValueError("Thieu zalo.send_api_url")
    if not recipient_uids:
        raise ValueError("Thieu zalo.recipient_uids")

    return {
        "access_token": access_token,
        "send_api_url": send_api_url,
        "timeout_sec": timeout_sec,
        "recipient_uids": recipient_uids,
    }


def send_zalo_text(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    zalo_cfg = get_zalo_cfg()
    text = build_text(event)

    headers = {
        "access_token": zalo_cfg["access_token"],
        "Content-Type": "application/json",
    }

    results: List[Dict[str, Any]] = []

    for uid in zalo_cfg["recipient_uids"]:
        payload = {
            "recipient": {"user_id": uid},
            "message": {"text": text},
        }

        try:
            r = requests.post(
                zalo_cfg["send_api_url"],
                headers=headers,
                json=payload,
                timeout=zalo_cfg["timeout_sec"],
            )
            item = {
                "uid": uid,
                "status_code": r.status_code,
                "response_text": r.text,
            }
        except requests.RequestException as e:
            item = {
                "uid": uid,
                "status_code": -1,
                "response_text": str(e),
            }

        results.append(item)

        append_jsonl(
            OUTBOX_LOG,
            {
                "ts": time.time(),
                "event": event,
                "uid": uid,
                "payload": payload,
                "result": item,
            },
        )

    return results


def validate_event(event: Dict[str, Any]) -> None:
    required_keys = ["camera_id", "roi_id", "event_type"]
    missing = [k for k in required_keys if k not in event]
    if missing:
        raise HTTPException(status_code=400, detail=f"Thieu field: {missing}")


@app.get("/")
def root():
    return {
        "ok": True,
        "service": "AI Camera Zalo Webhook",
        "routes": ["/health", "/notify"],
    }


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/notify")
def notify(event: Dict[str, Any]):
    validate_event(event)

    try:
        results = send_zalo_text(event)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    has_error = any(int(x["status_code"]) < 0 or int(x["status_code"]) >= 400 for x in results)
    if has_error:
        raise HTTPException(status_code=502, detail=results)

    return {
        "ok": True,
        "sent": len(results),
        "results": results,
    }