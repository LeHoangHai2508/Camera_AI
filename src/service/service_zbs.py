from pathlib import Path
from typing import Any, Dict, List
import json
import time

import requests
import yaml
from fastapi import FastAPI, HTTPException

from src.utils.path_utils import app_base_dir

ROOT = app_base_dir()
CFG_PATH = ROOT / "configs" / "zbs_service.yaml"
LOG_DIR = ROOT / "outputs" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

INBOX_LOG = LOG_DIR / "zbs_inbox.jsonl"
OUTBOX_LOG = LOG_DIR / "zbs_outbox.jsonl"

app = FastAPI(title="AI Camera ZBS Webhook")


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
    return (
        "[AI CAMERA CANH BAO]\n"
        f"Camera: {event.get('camera_id', '')}\n"
        f"ROI: {event.get('roi_id', '')}\n"
        f"Video: {event.get('video_name', '')}\n"
        f"Su kien: {event.get('event_type', '')}\n"
        f"Trang thai: {event.get('trigger_state', '')}\n"
        f"Bat dau: {fmt_mmss(event.get('start_time_sec', ''))}\n"
        f"Ket thuc: {fmt_mmss(event.get('end_time_sec', ''))}\n"
        f"Snapshot local: {event.get('snapshot_path', '')}"
    )


def validate_event(event: Dict[str, Any]) -> None:
    required_keys = ["camera_id", "roi_id", "event_type"]
    missing = [k for k in required_keys if k not in event]
    if missing:
        raise HTTPException(status_code=400, detail=f"Thieu field: {missing}")


def get_zbs_cfg() -> Dict[str, Any]:
    cfg = load_cfg().get("zbs", {})
    if not isinstance(cfg, dict):
        raise ValueError("Section 'zbs' khong hop le")
    return cfg


def send_zbs_mock(event: Dict[str, Any]) -> Dict[str, Any]:
    text = build_text(event)
    result = {
        "mode": "mock",
        "accepted": True,
        "message": "ZBS mock accepted",
        "preview_text": text,
    }
    append_jsonl(
        OUTBOX_LOG,
        {
            "ts": time.time(),
            "mode": "mock",
            "event": event,
            "result": result,
        },
    )
    return result


def send_zbs_real(event: Dict[str, Any]) -> Dict[str, Any]:
    cfg = get_zbs_cfg()

    access_token = str(cfg.get("access_token", "")).strip()
    send_api_url = str(cfg.get("send_api_url", "")).strip()
    timeout_sec = int(cfg.get("timeout_sec", 15))

    recipient_phone = str(cfg.get("recipient_phone", "")).strip()
    recipient_uid = str(cfg.get("recipient_uid", "")).strip()
    template_id = str(cfg.get("template_id", "")).strip()

    if not access_token:
        raise ValueError("Thieu zbs.access_token")
    if not send_api_url:
        raise ValueError("Thieu zbs.send_api_url")
    if not template_id:
        raise ValueError("Thieu zbs.template_id")
    if not recipient_phone and not recipient_uid:
        raise ValueError("Can co zbs.recipient_phone hoac zbs.recipient_uid")

    # Luu y:
    # Payload duoi day CHI LA KHUNG NOI BO de ban thay cho ro luong du lieu.
    # Ban phai doi cac key theo dung tai lieu ZBS/API thuc te cua tai khoan ban.
    payload = {
        "template_id": template_id,
        "phone": recipient_phone or None,
        "uid": recipient_uid or None,
        "tracking_id": f"{event.get('camera_id','')}-{event.get('roi_id','')}-{int(time.time())}",
        "template_data": {
            "camera_id": event.get("camera_id", ""),
            "roi_id": event.get("roi_id", ""),
            "event_type": event.get("event_type", ""),
            "trigger_state": event.get("trigger_state", ""),
            "start_time_sec": str(event.get("start_time_sec", "")),
            "end_time_sec": str(event.get("end_time_sec", "")),
            "snapshot_path": str(event.get("snapshot_path", "")),
            "video_name": str(event.get("video_name", "")),
        },
    }

    headers = {
        "access_token": access_token,
        "Content-Type": "application/json",
    }

    try:
        r = requests.post(
            send_api_url,
            headers=headers,
            json=payload,
            timeout=timeout_sec,
        )
        result = {
            "mode": "real",
            "status_code": r.status_code,
            "response_text": r.text,
        }
    except requests.RequestException as e:
        result = {
            "mode": "real",
            "status_code": -1,
            "response_text": str(e),
        }

    append_jsonl(
        OUTBOX_LOG,
        {
            "ts": time.time(),
            "mode": "real",
            "event": event,
            "payload": payload,
            "result": result,
        },
    )

    return result


@app.get("/")
def root():
    return {
        "ok": True,
        "service": "AI Camera ZBS Webhook",
        "routes": ["/health", "/notify"],
    }


@app.get("/health")
def health():
    cfg = get_zbs_cfg()
    return {
        "ok": True,
        "mode": cfg.get("mode", "mock"),
    }


@app.post("/notify")
def notify(event: Dict[str, Any]):
    validate_event(event)

    append_jsonl(
        INBOX_LOG,
        {
            "ts": time.time(),
            "event": event,
        },
    )

    cfg = get_zbs_cfg()
    mode = str(cfg.get("mode", "mock")).strip().lower()

    if mode == "mock":
        result = send_zbs_mock(event)
        return {"ok": True, "result": result}

    if mode == "real":
        result = send_zbs_real(event)
        code = int(result.get("status_code", -1))
        if code < 0 or code >= 400:
            raise HTTPException(status_code=502, detail=result)
        return {"ok": True, "result": result}

    raise HTTPException(status_code=500, detail=f"Mode khong hop le: {mode}")