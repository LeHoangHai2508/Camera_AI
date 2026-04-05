from typing import Dict, Any
import requests


def notify_console(event: Dict[str, Any]) -> None:
    print("[NOTIFY]", event)


def notify_webhook(event: Dict[str, Any], url: str, timeout_sec: int = 10):
    r = requests.post(url, json=event, timeout=timeout_sec)
    return r.status_code, r.text


def build_zalo_text(event: Dict[str, Any]) -> str:
    return (
        "[AI CAMERA]\n"
        f"camera={event.get('camera_id', '')}\n"
        f"roi={event.get('roi_id', '')}\n"
        f"type={event.get('event_type', '')}\n"
        f"start={event.get('start_time_sec', '')}\n"
        f"state={event.get('trigger_state', '')}\n"
        f"snapshot={event.get('snapshot_path', '')}"
    )


def notify_zalo_oa(
    event: Dict[str, Any],
    access_token: str,
    recipient_uid: str,
    send_api_url: str,
    timeout_sec: int = 15,
):
    payload = {
        "recipient": {"user_id": recipient_uid},
        "message": {
            "text": build_zalo_text(event)
        }
    }

    headers = {
        "access_token": access_token,
        "Content-Type": "application/json"
    }

    r = requests.post(
        send_api_url,
        headers=headers,
        json=payload,
        timeout=timeout_sec,
    )
    return r.status_code, r.text