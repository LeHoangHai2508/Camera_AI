from __future__ import annotations

import queue
import threading
import time
from typing import Any, Dict, Optional

import cv2
from PIL import Image, ImageTk

from src.core.pipeline import AICameraPipeline


class GUIController:
    def __init__(self, ui) -> None:
        self.ui = ui

        self.pipeline: Optional[AICameraPipeline] = None
        self.worker_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        self.frame_queue: queue.Queue = queue.Queue(maxsize=2)
        self.status_queue: queue.Queue = queue.Queue()
        self.event_queue: queue.Queue = queue.Queue()

        self.running = False
        self._last_tk_image = None

    def start_pipeline(
        self,
        video_path: str,
        roi_path: str,
        rules_path: str,
        runtime_path: str,
        notify_path: str,
        person_model_path: str,
        roi_cls_model_path: str,
        output_path: str,
        device: str,
        save_output: bool,
    ) -> None:
        if self.running:
            return

        self.stop_event.clear()

        self.pipeline = AICameraPipeline(
            roi_path=roi_path,
            rules_path=rules_path,
            person_model_path=person_model_path,
            roi_cls_model_path=roi_cls_model_path,
            output_path=output_path,
            runtime_path=runtime_path or None,
            notify_path=notify_path or None,
            device=device,
            save_output=save_output,
        )

        self.pipeline.setup(video_path=video_path)

        summary = self.pipeline.get_runtime_summary()
        self.status_queue.put(
            {
                "type": "runtime_summary",
                "data": summary,
            }
        )

        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            name="pipeline-worker",
            daemon=True,
        )
        self.worker_thread.start()
        self.running = True

    def _worker_loop(self) -> None:
        assert self.pipeline is not None

        try:
            while not self.stop_event.is_set():
                result = self.pipeline.process_next_frame()
                if result is None:
                    break

                self._push_latest_frame(result)
                self.status_queue.put(
                    {
                        "type": "frame_status",
                        "data": {
                            "frame_idx": result["frame_idx"],
                            "current_sec": result["current_sec"],
                            "person_count": result["person_count"],
                            "fps_runtime": result["fps_runtime"],
                            "source_type": result["source_type"],
                            "camera_id": result["camera_id"],
                            "video_name": result["video_name"],
                            "alerts": result["alerts"],
                        },
                    }
                )

                for event in result["events"]:
                    self.event_queue.put(event)

        except Exception as e:
            self.status_queue.put(
                {
                    "type": "error",
                    "data": str(e),
                }
            )
        finally:
            if self.pipeline is not None:
                self.pipeline.close()

            self.running = False
            self.status_queue.put({"type": "stopped", "data": "Pipeline stopped"})

    def _push_latest_frame(self, result: Dict[str, Any]) -> None:
        try:
            if self.frame_queue.full():
                self.frame_queue.get_nowait()
        except queue.Empty:
            pass

        self.frame_queue.put_nowait(result)

    def stop_pipeline(self) -> None:
        if not self.running:
            return

        self.stop_event.set()

        if self.pipeline is not None:
            try:
                self.pipeline.stop()
            except Exception:
                pass

        if self.worker_thread is not None and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)

        self.running = False

    def poll_queues(self) -> None:
        self._poll_frame_queue()
        self._poll_status_queue()
        self._poll_event_queue()

    def _poll_frame_queue(self) -> None:
        latest = None
        while True:
            try:
                latest = self.frame_queue.get_nowait()
            except queue.Empty:
                break

        if latest is None:
            return

        frame_bgr = latest["frame_bgr"]
        tk_image = self._convert_bgr_to_tk(frame_bgr)
        self._last_tk_image = tk_image
        self.ui.update_video(tk_image)

    def _poll_status_queue(self) -> None:
        while True:
            try:
                item = self.status_queue.get_nowait()
            except queue.Empty:
                break

            msg_type = item["type"]
            data = item["data"]

            if msg_type == "runtime_summary":
                self.ui.set_runtime_summary(data)
            elif msg_type == "frame_status":
                self.ui.set_frame_status(data)
            elif msg_type == "error":
                self.ui.set_status_text(f"Loi runtime: {data}")
                self.ui.on_pipeline_stopped()
            elif msg_type == "stopped":
                self.ui.set_status_text(str(data))
                self.ui.on_pipeline_stopped()

    def _poll_event_queue(self) -> None:
        while True:
            try:
                event = self.event_queue.get_nowait()
            except queue.Empty:
                break

            self.ui.append_event(event)

    def _convert_bgr_to_tk(self, frame_bgr):
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame_rgb)

        target_w = max(320, self.ui.get_video_width())
        target_h = max(240, self.ui.get_video_height())

        img_w, img_h = image.size
        scale = min(target_w / img_w, target_h / img_h)
        new_w = max(1, int(img_w * scale))
        new_h = max(1, int(img_h * scale))

        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)

    def is_running(self) -> bool:
        return self.running