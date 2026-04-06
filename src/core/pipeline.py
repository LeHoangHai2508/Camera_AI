from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

import cv2
import numpy as np
import torch

from src.core.rule_engine import BacklogRule, WorkerAbsenceRule
from src.core.tracker_utils import PresenceTracker, StateSmoother, filter_persons_in_roi
from src.core.video_source import open_capture, read_rtsp_loop
from src.service.notifier import notify_console, notify_webhook, notify_zalo_oa
from src.utils.common import (
    COLOR_GREEN,
    COLOR_RED,
    COLOR_YELLOW,
    ensure_dir,
    frame_to_sec,
    sec_to_mmss,
)
from src.utils.config_utils import load_notify, load_roi_config, load_rules, load_runtime
from src.utils.draw_utils import (
    draw_alert_banner,
    draw_info_panel,
    draw_person_bbox,
    draw_polygon,
    draw_roi_state,
    draw_timer,
)
from src.utils.event_logger import EventLogger


class AICameraPipeline:
    """
    Pipeline dùng lại được cho cả CLI và Tkinter GUI.

    Luồng:
        setup() -> process_next_frame() nhiều lần -> close()

    GUI sẽ gọi process_next_frame() trong worker thread
    và nhận dict kết quả để render lên Tkinter.
    """

    def __init__(
        self,
        roi_path: str,
        rules_path: str,
        person_model_path: str,
        roi_cls_model_path: str,
        output_path: Optional[str] = None,
        runtime_path: Optional[str] = None,
        notify_path: Optional[str] = None,
        tracker_cfg: str = "bytetrack.yaml",
        device: str = "auto",
        save_output: bool = False,
    ) -> None:
        self.roi_path = roi_path
        self.rules_path = rules_path
        self.person_model_path = person_model_path
        self.roi_cls_model_path = roi_cls_model_path
        self.output_path = output_path or "outputs/videos/demo_output.mp4"
        self.runtime_path = runtime_path
        self.notify_path = notify_path
        self.tracker_cfg = tracker_cfg
        self.device = device
        self.save_output = save_output

        self.roi_cfg: Dict[str, Any] = {}
        self.rules_cfg: Dict[str, Any] = {}
        self.runtime_cfg: Dict[str, Any] = {}
        self.notify_cfg: Dict[str, Any] = {"enabled": False}

        self.person_model = None
        self.roi_cls_model = None

        self.cap = None
        self.frame_stream = None
        self.out_writer = None
        self.logger: Optional[EventLogger] = None

        self.video_path = ""
        self.video_name = ""
        self.camera_id = "cam01"
        self.active_source_type = "video_file"
        self.active_source_desc = ""

        self.video_fps = 15.0
        self.total_frames = -1
        self.frame_w = 0
        self.frame_h = 0
        self.frame_idx = 0
        self.processed = 0
        self.started_at = 0.0
        self.stopped = False

        self.process_fps = 5
        self.imgsz_detect = 640
        self.imgsz_cls = 224
        self.conf_detect = 0.45
        self.conf_cls = 0.40
        self.smooth_window = 10
        self.snapshot_on_alert = True
        self.source_type = "video_file"
        self.rtsp_url = ""
        self.reconnect_sec = 2
        self.process_every_n_frames = 3
        self.skip = 1
        self.provider = "none"
        self.send_on = set()

        self.worker_rois: List[Dict[str, Any]] = []
        self.buffer_rois: List[Dict[str, Any]] = []
        self.worker_trackers: Dict[str, PresenceTracker] = {}
        self.worker_rules: Dict[str, WorkerAbsenceRule] = {}
        self.buffer_smoothers: Dict[str, StateSmoother] = {}
        self.buffer_rules: Dict[str, BacklogRule] = {}

        self.t_absent = 15
        self.grace = 3
        self.t_backlog = 20
        self.trigger_states = ["full", "overload"]

        self.snap_dir = ""
        self.log_path = ""
        self.device_name = "CPU"
        self.device_runtime = "cpu"

    def setup(self, video_path: str = "") -> None:
        self._load_configs(video_path=video_path)
        self._resolve_device()
        self._load_models()
        self._open_source()
        self._setup_output_dirs()
        self._setup_rules_and_trackers()
        self.frame_idx = 0
        self.processed = 0
        self.started_at = time.time()
        self.stopped = False

    def _load_configs(self, video_path: str = "") -> None:
        self.roi_cfg = load_roi_config(self.roi_path)
        self.rules_cfg = load_rules(self.rules_path)
        self.runtime_cfg = (
            load_runtime(self.runtime_path)
            if self.runtime_path and os.path.exists(self.runtime_path)
            else {}
        )

        self.process_fps = 5
        self.imgsz_detect = 640
        self.imgsz_cls = 224
        self.conf_detect = 0.45
        self.conf_cls = 0.40
        self.smooth_window = 10
        self.snapshot_on_alert = True
        self.source_type = "video_file"
        self.rtsp_url = ""
        self.reconnect_sec = 2
        self.process_every_n_frames = 3

        if self.runtime_cfg:
            input_cfg = self.runtime_cfg.get("input", {})
            self.source_type = input_cfg.get("source_type", "video_file")
            self.rtsp_url = input_cfg.get("rtsp_url", "")
            self.reconnect_sec = int(input_cfg.get("reconnect_sec", 2))
            self.process_every_n_frames = int(input_cfg.get("process_every_n_frames", 3))

            if video_path and video_path.strip().lower() != "dummy":
                self.video_path = video_path
            else:
                self.video_path = input_cfg.get("video_path", "")

            self.process_fps = self.runtime_cfg.get("process_fps", self.process_fps)
            self.imgsz_detect = self.runtime_cfg.get("imgsz_detect", self.imgsz_detect)
            self.imgsz_cls = self.runtime_cfg.get("imgsz_classify", self.imgsz_cls)
            self.conf_detect = self.runtime_cfg.get("confidence_detect", self.conf_detect)
            self.conf_cls = self.runtime_cfg.get("confidence_classify", self.conf_cls)
            self.smooth_window = self.runtime_cfg.get("smoothing_window", self.smooth_window)
            self.tracker_cfg = self.runtime_cfg.get("tracker", self.tracker_cfg)
            self.snapshot_on_alert = self.runtime_cfg.get("snapshot_on_alert", self.snapshot_on_alert)
        else:
            self.video_path = video_path

        if self.notify_path and os.path.exists(self.notify_path):
            self.notify_cfg = load_notify(self.notify_path).get("notify", {})
            self.provider = self.notify_cfg.get("provider", "none")
            self.send_on = set(self.notify_cfg.get("send_on", []))
        else:
            self.notify_cfg = {"enabled": False}
            self.provider = "none"
            self.send_on = set()

        self.camera_id = self.roi_cfg.get("camera_id", "cam01")
        self.worker_rois = self.roi_cfg.get("worker_rois", [])
        self.buffer_rois = self.roi_cfg.get("buffer_rois", [])

        wa_cfg = self.rules_cfg.get("worker_absence", {})
        bl_cfg = self.rules_cfg.get("backlog_alert", {})
        self.t_absent = wa_cfg.get("threshold_sec", 15)
        self.grace = wa_cfg.get("grace_frames", 3)
        self.t_backlog = bl_cfg.get("threshold_sec", 20)
        self.trigger_states = bl_cfg.get("trigger_states", ["full", "overload"])

    def _resolve_device(self) -> None:
        device = self.device
        if device == "auto":
            device = "0" if torch.cuda.is_available() else "cpu"

        self.device = device
        use_gpu = device != "cpu" and torch.cuda.is_available()
        self.device_runtime = f"cuda:{device}" if use_gpu else "cpu"
        self.device_name = torch.cuda.get_device_name(int(device)) if use_gpu else "CPU"

    def _load_models(self) -> None:
        from ultralytics import YOLO

        self.person_model = YOLO(self.person_model_path)
        self.person_model.to(self.device_runtime)

        self.roi_cls_model = YOLO(self.roi_cls_model_path)
        self.roi_cls_model.to(self.device_runtime)

    def _open_video_file_source(self, video_path: str):
        if not video_path:
            raise ValueError("Khong co video_path de mo")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        video_fps = cap.get(cv2.CAP_PROP_FPS)
        if video_fps <= 0:
            video_fps = 15.0

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return cap, video_fps, total_frames, frame_w, frame_h

    def _open_source(self) -> None:
        self.cap = None
        self.frame_stream = None
        self.total_frames = -1
        self.video_fps = 15.0
        self.frame_w = 0
        self.frame_h = 0

        if self.source_type == "video_file":
            self.cap, self.video_fps, self.total_frames, self.frame_w, self.frame_h = \
                self._open_video_file_source(self.video_path)
            self.video_name = Path(self.video_path).stem
            self.active_source_type = "video_file"
            self.active_source_desc = self.video_path

        elif self.source_type == "rtsp":
            rtsp_url = (self.rtsp_url or "").strip()

            if not rtsp_url:
                self.cap, self.video_fps, self.total_frames, self.frame_w, self.frame_h = \
                    self._open_video_file_source(self.video_path)
                self.video_name = Path(self.video_path).stem
                self.active_source_type = "video_file"
                self.active_source_desc = self.video_path
            else:
                temp_cap = open_capture(rtsp_url, use_ffmpeg=True)

                if not temp_cap.isOpened():
                    try:
                        temp_cap.release()
                    except Exception:
                        pass

                    self.cap, self.video_fps, self.total_frames, self.frame_w, self.frame_h = \
                        self._open_video_file_source(self.video_path)
                    self.video_name = Path(self.video_path).stem
                    self.active_source_type = "video_file"
                    self.active_source_desc = self.video_path
                else:
                    fps = temp_cap.get(cv2.CAP_PROP_FPS)
                    self.video_fps = fps if fps > 0 else 15.0
                    self.frame_w = int(temp_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    self.frame_h = int(temp_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    temp_cap.release()

                    self.frame_stream = read_rtsp_loop(rtsp_url, reconnect_sec=self.reconnect_sec)
                    self.video_name = f"{self.camera_id}_rtsp"
                    self.active_source_type = "rtsp"
                    self.active_source_desc = rtsp_url
        else:
            raise ValueError(f"source_type khong hop le: {self.source_type}")

        self.skip = max(1, int(self.video_fps / self.process_fps)) if self.video_fps > 0 else 1

    def _setup_output_dirs(self) -> None:
        ensure_dir(os.path.dirname(self.output_path) or "outputs/videos")

        self.snap_dir = os.path.join("outputs", "snapshots", self.video_name)
        ensure_dir(self.snap_dir)

        self.log_path = os.path.join("outputs", "logs", f"{self.video_name}_events.csv")
        self.logger = EventLogger(
            self.log_path,
            video_name=self.video_name,
            camera_id=self.camera_id,
        )

    def _setup_rules_and_trackers(self) -> None:
        self.worker_trackers = {}
        self.worker_rules = {}
        for wroi in self.worker_rois:
            wid = wroi["id"]
            self.worker_trackers[wid] = PresenceTracker(grace_frames=self.grace)
            self.worker_rules[wid] = WorkerAbsenceRule(wid, threshold_sec=self.t_absent)

        self.buffer_smoothers = {}
        self.buffer_rules = {}
        for broi in self.buffer_rois:
            bid = broi["id"]
            self.buffer_smoothers[bid] = StateSmoother(window_size=self.smooth_window)
            self.buffer_rules[bid] = BacklogRule(
                bid,
                threshold_sec=self.t_backlog,
                trigger_states=self.trigger_states,
            )

    def crop_polygon_region_for_cls(
        self,
        frame: np.ndarray,
        points: List[List[int]],
    ) -> Optional[np.ndarray]:
        """
        Cắt ROI theo polygon + mask.
        Đây là bản đúng hơn so với bản infer cũ chỉ cắt boundingRect.
        """
        pts = np.array(points, dtype=np.int32)
        x, y, w, h = cv2.boundingRect(pts)

        fh, fw = frame.shape[:2]
        x, y = max(0, x), max(0, y)
        w = min(w, fw - x)
        h = min(h, fh - y)

        if w <= 0 or h <= 0:
            return None

        cropped = frame[y:y + h, x:x + w].copy()

        shifted_pts = pts - np.array([[x, y]])
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [shifted_pts], 255)

        masked = cv2.bitwise_and(cropped, cropped, mask=mask)
        return masked

    def _dispatch_notify(self, notify_event: Dict[str, Any]) -> None:
        if not self.notify_cfg.get("enabled", False):
            return

        event_type = notify_event.get("event_type", "")
        if event_type not in self.send_on:
            return

        if self.provider == "console":
            notify_console(notify_event)
            return

        if self.provider == "webhook":
            webhook_cfg = self.notify_cfg.get("webhook", {})
            url = webhook_cfg.get("url", "").strip()
            if url:
                notify_webhook(
                    notify_event,
                    url=url,
                    timeout_sec=webhook_cfg.get("timeout_sec", 10),
                )
            return

        if self.provider == "zalo_oa":
            zalo_cfg = self.notify_cfg.get("zalo", {})
            access_token = zalo_cfg.get("access_token", "").strip()
            recipient_uid = zalo_cfg.get("recipient_uid", "").strip()
            send_api_url = zalo_cfg.get("send_api_url", "").strip()

            if access_token and recipient_uid and send_api_url:
                notify_zalo_oa(
                    notify_event,
                    access_token=access_token,
                    recipient_uid=recipient_uid,
                    send_api_url=send_api_url,
                    timeout_sec=zalo_cfg.get("timeout_sec", 15),
                )

    def _ensure_writer(self, display: np.ndarray) -> None:
        if not self.save_output:
            return

        if self.out_writer is not None:
            return

        h, w = display.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer_fps = float(min(self.process_fps, self.video_fps)) if self.video_fps > 0 else float(self.process_fps)
        self.out_writer = cv2.VideoWriter(self.output_path, fourcc, writer_fps, (w, h))

    def _read_next_valid_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        while True:
            if self.stopped:
                return False, None

            if self.active_source_type == "rtsp":
                frame = next(self.frame_stream)
                ret = frame is not None
            else:
                ret, frame = self.cap.read()

            if not ret:
                return False, None

            should_process = (
                self.frame_idx % self.process_every_n_frames == 0
                if self.active_source_type == "rtsp"
                else self.frame_idx % self.skip == 0
            )

            if should_process:
                return True, frame

            self.frame_idx += 1

    def process_next_frame(self) -> Optional[Dict[str, Any]]:
        ok, frame = self._read_next_valid_frame()
        if not ok or frame is None:
            return None

        current_sec = frame_to_sec(self.frame_idx, self.video_fps)
        display = frame.copy()
        alert_banners: List[str] = []
        emitted_events: List[Dict[str, Any]] = []

        results = self.person_model.track(
            source=frame,
            imgsz=self.imgsz_detect,
            conf=self.conf_detect,
            tracker=self.tracker_cfg,
            persist=True,
            verbose=False,
            device=self.device_runtime,
        )

        person_bboxes: List[Tuple[int, int, int, int]] = []
        track_ids: List[int] = []

        if results and results[0].boxes is not None:
            boxes = results[0].boxes
            for i in range(len(boxes)):
                cls_id = int(boxes.cls[i])
                if cls_id == 0:
                    x1, y1, x2, y2 = boxes.xyxy[i].cpu().numpy().astype(int)
                    tid = int(boxes.id[i]) if boxes.id is not None else -1
                    person_bboxes.append((x1, y1, x2, y2))
                    track_ids.append(tid)
                    draw_person_bbox(display, x1, y1, x2, y2, track_id=tid)

        # Worker ROI
        for wroi in self.worker_rois:
            wid = wroi["id"]
            pts = wroi["points"]

            ids_in_roi = filter_persons_in_roi(person_bboxes, track_ids, pts)
            person_present = len(ids_in_roi) > 0

            stable_present = self.worker_trackers[wid].update(person_present)
            event = self.worker_rules[wid].update(stable_present, current_sec)

            roi_color = COLOR_GREEN if stable_present else COLOR_YELLOW
            draw_polygon(
                display,
                pts,
                color=roi_color,
                label=f"{wid} ({'OK' if stable_present else 'ABSENT'})",
            )

            if event:
                emitted = self._build_worker_event(event, display, wid, current_sec)
                emitted_events.append(emitted)
                self._dispatch_notify(emitted)

            if self.worker_rules[wid].is_alert:
                elapsed = self.worker_rules[wid].get_elapsed(current_sec)
                alert_banners.append(f"{wid}: ABSENT {sec_to_mmss(elapsed)}")
                draw_timer(display, pts[0][0], pts[0][1] - 25, elapsed, "Absent", COLOR_RED)

        # Buffer ROI
        for broi in self.buffer_rois:
            bid = broi["id"]
            pts = broi["points"]

            crop = self.crop_polygon_region_for_cls(frame, pts)

            raw_state = "unknown"
            if crop is not None and crop.size > 0:
                cls_results = self.roi_cls_model.predict(
                    source=crop,
                    imgsz=self.imgsz_cls,
                    conf=self.conf_cls,
                    verbose=False,
                    device=self.device_runtime,
                )
                if cls_results and cls_results[0].probs is not None:
                    probs = cls_results[0].probs
                    top_idx = int(probs.top1)
                    class_names = cls_results[0].names
                    raw_state = class_names.get(top_idx, "unknown")

            stable_state = self.buffer_smoothers[bid].update(raw_state)
            draw_roi_state(display, pts, stable_state, roi_id=bid)

            event = self.buffer_rules[bid].update(stable_state, current_sec)
            if event:
                emitted = self._build_backlog_event(event, display, bid, current_sec, stable_state)
                emitted_events.append(emitted)
                self._dispatch_notify(emitted)

            if self.buffer_rules[bid].is_alert:
                elapsed = self.buffer_rules[bid].get_elapsed(current_sec)
                alert_banners.append(f"{bid}: {stable_state.upper()} {sec_to_mmss(elapsed)}")

        for i, banner_text in enumerate(alert_banners):
            draw_alert_banner(display, banner_text, y_offset=i * 42)

        info_lines = [
            f"Frame: {self.frame_idx}" if self.total_frames < 0 else f"Frame: {self.frame_idx}/{self.total_frames}",
            f"Time:  {sec_to_mmss(current_sec)}",
            f"Persons: {len(person_bboxes)}",
            f"Source: {self.active_source_type}",
        ]
        draw_info_panel(display, info_lines)

        self._ensure_writer(display)
        if self.out_writer is not None:
            self.out_writer.write(display)

        self.processed += 1

        elapsed_real = time.time() - self.started_at
        runtime_fps = self.processed / elapsed_real if elapsed_real > 0 else 0.0

        result = {
            "ok": True,
            "frame_bgr": display,
            "raw_frame_bgr": frame,
            "frame_idx": self.frame_idx,
            "current_sec": current_sec,
            "person_count": len(person_bboxes),
            "events": emitted_events,
            "alerts": alert_banners,
            "source_type": self.active_source_type,
            "source_desc": self.active_source_desc,
            "camera_id": self.camera_id,
            "video_name": self.video_name,
            "fps_runtime": round(runtime_fps, 2),
        }

        self.frame_idx += 1
        return result

    def _build_worker_event(
        self,
        event: Dict[str, Any],
        frame: np.ndarray,
        wid: str,
        current_sec: float,
    ) -> Dict[str, Any]:
        if event["action"] == "start":
            event_type = "worker_absence_start"
            trigger_state = "absent"

            snap_frame = frame.copy()
            target_points = None
            for wroi in self.worker_rois:
                if wroi["id"] == wid:
                    target_points = wroi["points"]
                    break

            if target_points is not None:
                draw_polygon(
                    snap_frame,
                    target_points,
                    color=(0, 0, 255),
                    label=f"{wid} ALERT",
                )

            snap_path = self._save_snapshot(
                snap_frame,
                f"{self.video_name}_{wid}_absence_{current_sec:.0f}s.jpg",
            )
        else:
            event_type = "worker_absence_end"
            trigger_state = "returned"
            snap_path = ""

        payload = {
            "camera_id": self.camera_id,
            "roi_id": wid,
            "event_type": event_type,
            "start_time_sec": event["start_sec"],
            "end_time_sec": current_sec,
            "duration_sec": round(current_sec - event["start_sec"], 2),
            "trigger_state": trigger_state,
            "snapshot_path": snap_path,
            "video_name": self.video_name,
        }

        self.logger.log_event(
            roi_id=wid,
            event_type=event_type,
            start_sec=event["start_sec"],
            end_sec=current_sec,
            trigger_state=trigger_state,
            snapshot_path=snap_path,
        )

        return payload

    def _build_backlog_event(
        self,
        event: Dict[str, Any],
        frame: np.ndarray,
        bid: str,
        current_sec: float,
        stable_state: str,
    ) -> Dict[str, Any]:
        if event["action"] == "start":
            event_type = "backlog_alert_start"
            trigger_state = event.get("trigger_state", stable_state)

            snap_frame = frame.copy()
            target_points = None
            for broi in self.buffer_rois:
                if broi["id"] == bid:
                    target_points = broi["points"]
                    break

            if target_points is not None:
                draw_polygon(
                    snap_frame,
                    target_points,
                    color=(0, 0, 255),
                    label=f"{bid} ALERT",
                )

            snap_path = self._save_snapshot(
                snap_frame,
                f"{self.video_name}_{bid}_backlog_{current_sec:.0f}s.jpg",
            )
        else:
            event_type = "backlog_alert_end"
            trigger_state = "cleared"
            snap_path = ""

        payload = {
            "camera_id": self.camera_id,
            "roi_id": bid,
            "event_type": event_type,
            "start_time_sec": event["start_sec"],
            "end_time_sec": current_sec,
            "duration_sec": round(current_sec - event["start_sec"], 2),
            "trigger_state": trigger_state,
            "snapshot_path": snap_path,
            "video_name": self.video_name,
        }

        self.logger.log_event(
            roi_id=bid,
            event_type=event_type,
            start_sec=event["start_sec"],
            end_sec=current_sec,
            trigger_state=trigger_state,
            snapshot_path=snap_path,
        )

        return payload

    def _save_snapshot(self, frame: np.ndarray, name: str) -> str:
        if not self.snapshot_on_alert:
            return ""

        snap_path = os.path.join(self.snap_dir, name)
        cv2.imwrite(snap_path, frame)
        return snap_path

    def run(self) -> Generator[Dict[str, Any], None, None]:
        while not self.stopped:
            result = self.process_next_frame()
            if result is None:
                break
            yield result

    def stop(self) -> None:
        self.stopped = True
        self.close()

    def close(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None

        if self.out_writer is not None:
            self.out_writer.release()
            self.out_writer = None

    def get_runtime_summary(self) -> Dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "video_name": self.video_name,
            "source_type": self.active_source_type,
            "source_desc": self.active_source_desc,
            "video_fps": self.video_fps,
            "frame_size": (self.frame_w, self.frame_h),
            "total_frames": self.total_frames,
            "workers": len(self.worker_rois),
            "buffers": len(self.buffer_rois),
            "device": self.device_runtime,
            "device_name": self.device_name,
            "event_log": self.log_path,
            "snapshot_dir": self.snap_dir,
            "output_video": self.output_path,
        }