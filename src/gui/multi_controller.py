from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Dict, Optional

import cv2
from PIL import Image, ImageTk

from src.core.pipeline import AICameraPipeline


@dataclass
class TileState:
    tile_id: str
    camera_name: str = "-"
    source_mode: str = "none"
    source_value: str = ""
    roi_path: str = ""
    running: bool = False
    selected: bool = False
    status: str = "idle"
    detail: str = "chưa có"


class TileRuntime:
    def __init__(self) -> None:
        self.worker_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.frame_queue: queue.Queue = queue.Queue(maxsize=2)
        self.event_queue: queue.Queue = queue.Queue()
        self.status_queue: queue.Queue = queue.Queue()
        self.pipeline: Optional[AICameraPipeline] = None


class MultiController:
    def __init__(self, ui) -> None:
        self.ui = ui
        self.tiles = {}
        self.runtimes = {}
        self.selected_tile_id = None

        self.rules_path = "configs/rules.yaml"
        self.runtime_path = "configs/runtime.yaml"
        self.notify_path = "configs/notify.yaml"
        self.person_model_path = "models/person/best_person.pt"
        self.roi_cls_model_path = "models/roi_state/best_roi_cls.pt"
        self.device = "cpu"

    def load_cameras(self, cameras) -> None:
        current_ids = set(self.tiles.keys())
        next_ids = set(cam.get("camera_uid") for cam in cameras)

        for camera_uid in list(current_ids - next_ids):
            self.unregister_camera(camera_uid)

        for cam in cameras:
            self.register_camera(cam)

        if self.selected_tile_id not in self.tiles:
            self.selected_tile_id = next(iter(self.tiles.keys()), None)
            if self.selected_tile_id is not None:
                self.select_tile(self.selected_tile_id)

    def register_camera(self, cam: dict) -> None:
        camera_uid = cam["camera_uid"]
        if camera_uid not in self.tiles:
            self.tiles[camera_uid] = TileState(tile_id=camera_uid)
        if camera_uid not in self.runtimes:
            self.runtimes[camera_uid] = TileRuntime()
        self.update_camera_config(camera_uid, cam)

    def unregister_camera(self, camera_uid: str) -> None:
        self.stop_tile(camera_uid, add_log=False)
        if camera_uid in self.tiles:
            del self.tiles[camera_uid]
        if camera_uid in self.runtimes:
            del self.runtimes[camera_uid]

    def update_camera_config(self, camera_uid: str, cam: dict) -> None:
        state = self.tiles[camera_uid]
        state.camera_name = cam.get("display_name", camera_uid)
        state.source_mode = cam.get("source_mode", "none")
        state.source_value = cam.get("source_value", "")
        state.roi_path = cam.get("roi_path", "")

        if state.running:
            state.detail = state.source_value
        elif state.source_mode == "none":
            state.status = "idle"
            state.detail = "chưa có nguồn"
        else:
            state.status = "idle"
            state.detail = state.source_value or "chưa có nguồn"

    def configure_source(self, camera_uid: str, cam: dict) -> None:
        self.stop_tile(camera_uid, add_log=False)
        self.update_camera_config(camera_uid, cam)
        self.ui.refresh_camera_tile(camera_uid)
        state = self.tiles[camera_uid]
        self.ui.add_system_log(camera_uid, state.camera_name, "source_changed", state.source_mode, state.detail)

    def select_tile(self, camera_uid: str) -> None:
        self.selected_tile_id = camera_uid
        for uid, state in self.tiles.items():
            state.selected = uid == camera_uid
        self.ui.refresh_tile_selection()

    def start_tile(self, camera_uid: str) -> None:
        if camera_uid not in self.tiles:
            return

        state = self.tiles[camera_uid]
        runtime = self.runtimes[camera_uid]

        if state.running:
            return

        if state.source_mode == "none" or not state.source_value:
            self.ui.add_system_log(camera_uid, state.camera_name, "start_failed", "none", "Chưa có nguồn")
            self.ui.set_status_text("{} chưa có nguồn".format(state.camera_name))
            return

        if not state.roi_path:
            self.ui.add_system_log(camera_uid, state.camera_name, "start_failed", state.source_mode, "Thiếu ROI")
            self.ui.set_status_text("{} chưa có file ROI".format(state.camera_name))
            return

        runtime.stop_event.clear()
        state.status = "connecting"
        state.detail = state.source_value
        self.ui.refresh_camera_tile(camera_uid)

        runtime.worker_thread = threading.Thread(
            target=self._pipeline_worker,
            args=(camera_uid,),
            name="{}-pipeline-worker".format(camera_uid),
            daemon=True,
        )
        runtime.worker_thread.start()

    def _pipeline_worker(self, camera_uid: str) -> None:
        state = self.tiles[camera_uid]
        runtime = self.runtimes[camera_uid]

        try:
            pipeline = AICameraPipeline(
                roi_path=state.roi_path,
                rules_path=self.rules_path,
                person_model_path=self.person_model_path,
                roi_cls_model_path=self.roi_cls_model_path,
                runtime_path=self.runtime_path,
                notify_path=self.notify_path,
                device=self.device,
                save_output=False,
            )
            runtime.pipeline = pipeline
            pipeline.setup(source_mode=state.source_mode, source_value=state.source_value)

            summary = pipeline.get_runtime_summary()
            runtime.status_queue.put({
                "type": "connected",
                "message": summary.get("source_desc", state.source_value),
            })

            while not runtime.stop_event.is_set():
                result = pipeline.process_next_frame()
                if result is None:
                    runtime.status_queue.put({
                        "type": "ended",
                        "message": "Luồng kết thúc",
                    })
                    break

                try:
                    if runtime.frame_queue.full():
                        runtime.frame_queue.get_nowait()
                except queue.Empty:
                    pass

                runtime.frame_queue.put_nowait(result["frame_bgr"])

                for event in result.get("events", []):
                    runtime.event_queue.put(event)

        except Exception as e:
            runtime.status_queue.put({
                "type": "error",
                "message": str(e),
            })
        finally:
            if runtime.pipeline is not None:
                try:
                    runtime.pipeline.close()
                except Exception:
                    pass
                runtime.pipeline = None

    def stop_tile(self, camera_uid: str, add_log: bool = True) -> None:
        if camera_uid not in self.tiles:
            return

        state = self.tiles[camera_uid]
        runtime = self.runtimes[camera_uid]

        runtime.stop_event.set()

        if runtime.pipeline is not None:
            try:
                runtime.pipeline.stop()
            except Exception:
                pass

        if runtime.worker_thread and runtime.worker_thread.is_alive():
            runtime.worker_thread.join(timeout=2.0)

        runtime.pipeline = None
        state.running = False
        state.status = "idle"
        state.detail = "đã dừng" if state.source_mode != "none" else "chưa có nguồn"

        self.ui.refresh_camera_tile(camera_uid)
        self.ui.update_tile_video(camera_uid, None)

        if add_log:
            self.ui.add_system_log(camera_uid, state.camera_name, "stopped", state.source_mode, "Đã dừng")

    def start_all(self) -> None:
        for camera_uid in list(self.tiles.keys()):
            self.start_tile(camera_uid)

    def stop_all(self) -> None:
        for camera_uid in list(self.tiles.keys()):
            self.stop_tile(camera_uid)

    def get_tile_state(self, camera_uid: str) -> TileState:
        return self.tiles[camera_uid]

    def poll(self) -> None:
        for camera_uid in list(self.tiles.keys()):
            self._poll_tile(camera_uid)

    def shutdown(self) -> None:
        self.stop_all()

    def _poll_tile(self, camera_uid: str) -> None:
        if camera_uid not in self.tiles:
            return

        state = self.tiles[camera_uid]
        runtime = self.runtimes[camera_uid]

        latest_frame = None
        while True:
            try:
                latest_frame = runtime.frame_queue.get_nowait()
            except queue.Empty:
                break

        if latest_frame is not None:
            tk_image = self._frame_to_tk(latest_frame, camera_uid)
            self.ui.update_tile_video(camera_uid, tk_image)

        while True:
            try:
                item = runtime.status_queue.get_nowait()
            except queue.Empty:
                break

            msg_type = item["type"]
            msg = item["message"]

            if msg_type == "connected":
                state.running = True
                state.status = "running"
                state.detail = msg
                self.ui.add_system_log(camera_uid, state.camera_name, "connected", state.source_mode, msg)
            elif msg_type == "error":
                state.running = False
                state.status = "error"
                state.detail = msg
                self.ui.update_tile_video(camera_uid, None)
                self.ui.add_system_log(camera_uid, state.camera_name, "error", state.source_mode, msg)
            elif msg_type == "ended":
                state.running = False
                state.status = "ended"
                state.detail = msg
                self.ui.add_system_log(camera_uid, state.camera_name, "ended", state.source_mode, msg)

            self.ui.refresh_camera_tile(camera_uid)

        while True:
            try:
                event = runtime.event_queue.get_nowait()
            except queue.Empty:
                break
            self.ui.add_ai_event(camera_uid, state.camera_name, event)

    def _frame_to_tk(self, frame_bgr, camera_uid: str):
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame_rgb)

        target_w, target_h = self.ui.get_tile_video_size(camera_uid)
        target_w = max(320, target_w)
        target_h = max(180, target_h)

        img_w, img_h = image.size
        scale = min(target_w / img_w, target_h / img_h)

        new_w = max(1, int(img_w * scale))
        new_h = max(1, int(img_h * scale))

        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)