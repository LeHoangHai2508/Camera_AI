from __future__ import annotations

import time
import cv2


def open_capture(source: str, use_ffmpeg: bool = False):
    """
    Không ép CAP_FFMPEG khi test local/video bình thường.
    Chỉ dùng backend mặc định của OpenCV để giảm crash libavcodec.
    """
    if use_ffmpeg:
        cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
        if cap.isOpened():
            return cap
        try:
            cap.release()
        except Exception:
            pass

    return cv2.VideoCapture(source)


def read_rtsp_loop(rtsp_url: str, reconnect_sec: int = 2):
    cap = open_capture(rtsp_url, use_ffmpeg=False)

    while True:
        if not cap.isOpened():
            print("[WARN] Mat ket noi camera. Dang thu ket noi lai...")
            time.sleep(reconnect_sec)
            try:
                cap.release()
            except Exception:
                pass
            cap = open_capture(rtsp_url, use_ffmpeg=False)
            continue

        ok, frame = cap.read()
        if not ok or frame is None:
            print("[WARN] Doc frame that bai. Dang ket noi lai...")
            time.sleep(reconnect_sec)
            try:
                cap.release()
            except Exception:
                pass
            cap = open_capture(rtsp_url, use_ffmpeg=False)
            continue

        yield frame