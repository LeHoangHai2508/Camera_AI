import time
import cv2


def open_capture(source: str, use_ffmpeg: bool = True):
    if use_ffmpeg:
        return cv2.VideoCapture(source, cv2.CAP_FFMPEG)
    return cv2.VideoCapture(source)


def read_rtsp_loop(rtsp_url: str, reconnect_sec: int = 2):
    cap = open_capture(rtsp_url, use_ffmpeg=True)

    while True:
        if not cap.isOpened():
            print("[WARN] Mat ket noi camera. Dang thu ket noi lai...")
            time.sleep(reconnect_sec)
            try:
                cap.release()
            except Exception:
                pass
            cap = open_capture(rtsp_url, use_ffmpeg=True)
            continue

        ok, frame = cap.read()
        if not ok or frame is None:
            print("[WARN] Doc frame that bai. Dang ket noi lai...")
            time.sleep(reconnect_sec)
            try:
                cap.release()
            except Exception:
                pass
            cap = open_capture(rtsp_url, use_ffmpeg=True)
            continue

        yield frame