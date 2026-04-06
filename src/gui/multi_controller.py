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
    tile_id: int
    source_mode: str = "none"
    source_name: str = "-"
    source_value: str = ""
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

        self.tiles: Dict[int, TileState] = {
            1: TileState(tile_id=1),
            2: TileState(tile_id=2),
            3: TileState(tile_id=3),
            4: TileState(tile_id=4),
        }

        self.runtimes: Dict[int, TileRuntime] = {
            1: TileRuntime(),
            2: TileRuntime(),
            3: TileRuntime(),
            4: TileRuntime(),
        }

        self.selected_tile_id: Optional[int] = 1

        self.default_roi_map = {
            1: "configs/roi_cam01.json",
            2: "configs/roi_cam02.json",
            3: "configs/roi_cam03.json",
            4: "configs/roi_cam04.json",
        }
        self.rules_path = "configs/rules.yaml"
        self.runtime_path = "configs/runtime.yaml"
        self.notify_path = "configs/notify.yaml"
        self.person_model_path = "models/person/best_person.pt"
        self.roi_cls_model_path = "models/roi_state/best_roi_cls.pt"
        self.device = "cpu"

    def select_tile(self, tile_id: int) -> None:
        self.selected_tile_id = tile_id
        for tid, state in self.tiles.items():
            state.selected = (tid == tile_id)
        self.ui.refresh_tile_selection()

    def configure_source(self, tile_id: int, source_mode: str, source_name: str, source_value: str) -> None:
        self.stop_tile(tile_id, add_log=False)

        state = self.tiles[tile_id]
        state.source_mode = source_mode
        state.source_name = source_name
        state.source_value = source_value
        state.running = False

        if source_mode == "none":
            state.status = "idle"
            state.detail = "đã xóa nguồn"
        elif source_mode == "video":
            state.status = "idle"
            state.detail = source_value
        elif source_mode == "rtsp":
            state.status = "idle"
            state.detail = source_value

        self.ui.refresh_tile(tile_id)
        self.ui.add_system_log(tile_id, "source_changed", state.source_mode, state.detail)

    def start_tile(self, tile_id: int) -> None:
        state = self.tiles[tile_id]
        runtime = self.runtimes[tile_id]

        if state.running:
            return

        if state.source_mode == "none" or not state.source_value:
            self.ui.set_status_text(f"Tile {tile_id} chưa có nguồn")
            self.ui.add_system_log(tile_id, "start_failed", "none", "Chưa có nguồn")
            return

        roi_path = self.default_roi_map.get(tile_id, "")
        if not roi_path:
            self.ui.add_system_log(tile_id, "error", state.source_mode, "Thiếu file ROI")
            return

        runtime.stop_event.clear()
        state.status = "connecting"
        state.detail = state.source_value
        self.ui.refresh_tile(tile_id)

        runtime.worker_thread = threading.Thread(
            target=self._pipeline_worker,
            args=(tile_id,),
            name=f"tile-{tile_id}-pipeline-worker",
            daemon=True,
        )
        runtime.worker_thread.start()

    def _pipeline_worker(self, tile_id: int) -> None:
        state = self.tiles[tile_id]
        runtime = self.runtimes[tile_id]

        try:
            pipeline = AICameraPipeline(
                roi_path=self.default_roi_map[tile_id],
                rules_path=self.rules_path,
                person_model_path=self.person_model_path,
                roi_cls_model_path=self.roi_cls_model_path,
                runtime_path=self.runtime_path,
                notify_path=self.notify_path,
                device=self.device,
                save_output=False,
            )
            runtime.pipeline = pipeline
            pipeline.setup(video_path=state.source_value)

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

    def stop_tile(self, tile_id: int, add_log: bool = True) -> None:
        state = self.tiles[tile_id]
        runtime = self.runtimes[tile_id]

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
        if state.source_mode == "none":
            state.status = "idle"
            state.detail = "chưa có"
        else:
            state.status = "idle"
            state.detail = "đã dừng"

        self.ui.refresh_tile(tile_id)
        self.ui.update_tile_video(tile_id, None)

        if add_log:
            self.ui.add_system_log(tile_id, "stopped", state.source_mode, "Đã dừng")

    def start_all(self) -> None:
        for tile_id in self.tiles:
            self.start_tile(tile_id)

    def stop_all(self) -> None:
        for tile_id in self.tiles:
            self.stop_tile(tile_id)

    def get_tile_state(self, tile_id: int) -> TileState:
        return self.tiles[tile_id]

    def poll(self) -> None:
        for tile_id in self.tiles:
            self._poll_tile(tile_id)

    def shutdown(self) -> None:
        self.stop_all()

    def _poll_tile(self, tile_id: int) -> None:
        state = self.tiles[tile_id]
        runtime = self.runtimes[tile_id]

        latest_frame = None
        while True:
            try:
                latest_frame = runtime.frame_queue.get_nowait()
            except queue.Empty:
                break

        if latest_frame is not None:
            tk_image = self._frame_to_tk(latest_frame, tile_id)
            self.ui.update_tile_video(tile_id, tk_image)

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
                self.ui.add_system_log(tile_id, "connected", state.source_mode, msg)

            elif msg_type == "error":
                state.running = False
                state.status = "error"
                state.detail = msg
                self.ui.update_tile_video(tile_id, None)
                self.ui.add_system_log(tile_id, "error", state.source_mode, msg)

            elif msg_type == "ended":
                state.running = False
                state.status = "ended"
                state.detail = msg
                self.ui.add_system_log(tile_id, "ended", state.source_mode, msg)

            self.ui.refresh_tile(tile_id)

        while True:
            try:
                event = runtime.event_queue.get_nowait()
            except queue.Empty:
                break

            self.ui.add_ai_event(tile_id, event)

    def _frame_to_tk(self, frame_bgr, tile_id: int):
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame_rgb)

        target_w, target_h = self.ui.get_tile_video_size(tile_id)
        target_w = max(320, target_w)
        target_h = max(180, target_h)

        img_w, img_h = image.size
        scale = min(target_w / img_w, target_h / img_h)

        new_w = max(1, int(img_w * scale))
        new_h = max(1, int(img_h * scale))

        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)