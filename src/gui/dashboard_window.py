from __future__ import annotations

import math
import os
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import Dict, Optional

from src.gui.camera_tile import CameraTile
from src.gui.multi_controller import MultiController
from src.gui.snapshot_viewer import SnapshotViewer
from src.gui.source_dialog import ask_source
from src.service.camera_store import CameraStore


class DashboardWindow:
    def __init__(self, root: tk.Toplevel, user: Dict, on_logout) -> None:
        self.root = root
        self.user = user
        self.on_logout = on_logout

        self.root.title("AI Camera - Dashboard")
        self.root.geometry("1600x920")
        self.root.minsize(1280, 760)

        self.var_status = tk.StringVar(
            value=f"Đăng nhập: {self.user.get('display_name', self.user.get('username', ''))}"
        )

        self.camera_store = CameraStore()
        self.controller = MultiController(self)

        self.tiles: Dict[str, CameraTile] = {}
        self.event_payloads: Dict[str, dict] = {}

        self.selected_camera_uid: Optional[str] = None
        self.focused_camera_uid: Optional[str] = None

        self._setup_styles()
        self._build_ui()
        self._reload_cameras()
        self._schedule_poll()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_styles(self) -> None:
        style = ttk.Style()
        style.configure("Tile.TFrame", relief="ridge", borderwidth=1)
        style.configure("SelectedTile.TFrame", relief="solid", borderwidth=2)

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)
        self.root.rowconfigure(3, weight=0)

        self._build_menu()
        self._build_toolbar()
        self._build_camera_area()
        self._build_event_panel()

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Output Folder", command=self._open_output_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Logout", command=self._logout)
        file_menu.add_command(label="Exit", command=self._on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        self.root.config(menu=menubar)

    def _build_toolbar(self) -> None:
        toolbar = ttk.Frame(self.root, padding=8)
        toolbar.grid(row=0, column=0, sticky="ew")

        ttk.Button(toolbar, text="Thêm cam", command=self._add_camera).pack(side="left")
        ttk.Button(toolbar, text="Start All", command=self.controller.start_all).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Stop All", command=self.controller.stop_all).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Zoom", command=self._toggle_focus_selected).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Open Output Folder", command=self._open_output_folder).pack(side="left", padx=(12, 0))

        ttk.Label(toolbar, textvariable=self.var_status).pack(side="right")

    def _build_camera_area(self) -> None:
        wrapper = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        wrapper.grid(row=2, column=0, sticky="nsew")
        wrapper.columnconfigure(0, weight=4)
        wrapper.columnconfigure(1, weight=1)
        wrapper.rowconfigure(0, weight=1)

        left = ttk.Frame(wrapper)
        left.grid(row=0, column=0, sticky="nsew")
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)

        self.camera_canvas = tk.Canvas(left, highlightthickness=0)
        self.camera_canvas.grid(row=0, column=0, sticky="nsew")

        self.h_scroll = ttk.Scrollbar(left, orient="horizontal", command=self.camera_canvas.xview)
        self.h_scroll.grid(row=1, column=0, sticky="ew")
        self.camera_canvas.configure(xscrollcommand=self.h_scroll.set)

        self.tiles_container = ttk.Frame(self.camera_canvas)
        self.tiles_window = self.camera_canvas.create_window((0, 0), window=self.tiles_container, anchor="nw")

        self.tiles_container.bind("<Configure>", self._on_tiles_configure)
        self.camera_canvas.bind("<Configure>", self._on_canvas_configure)
        self._bind_horizontal_scroll()

        self.manager_panel = ttk.LabelFrame(wrapper, text="Quản trị camera", padding=8)
        self.manager_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.manager_panel.columnconfigure(1, weight=1)

        self.var_mgr_name = tk.StringVar(value="-")
        self.var_mgr_mode = tk.StringVar(value="-")
        self.var_mgr_source = tk.StringVar(value="-")
        self.var_mgr_roi = tk.StringVar(value="-")
        self.var_mgr_status = tk.StringVar(value="-")

        self._manager_line(self.manager_panel, 0, "Tên", self.var_mgr_name)
        self._manager_line(self.manager_panel, 1, "Mode", self.var_mgr_mode)
        self._manager_line(self.manager_panel, 2, "Source", self.var_mgr_source)
        self._manager_line(self.manager_panel, 3, "ROI", self.var_mgr_roi)
        self._manager_line(self.manager_panel, 4, "Status", self.var_mgr_status)

        btns = ttk.Frame(self.manager_panel)
        btns.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Button(btns, text="Start", command=self._start_selected_camera).pack(fill="x", pady=2)
        ttk.Button(btns, text="Stop", command=self._stop_selected_camera).pack(fill="x", pady=2)
        ttk.Button(btns, text="Sửa nguồn", command=self._edit_selected_camera).pack(fill="x", pady=2)
        ttk.Button(btns, text="Xóa cam", command=self._remove_selected_camera).pack(fill="x", pady=2)

    def _build_event_panel(self) -> None:
        box = ttk.LabelFrame(self.root, text="Event Log", padding=8)
        box.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 8))

        cols = ("time", "camera", "event", "roi", "state", "snapshot")
        self.event_tree = ttk.Treeview(box, columns=cols, show="headings", height=8)

        self.event_tree.heading("time", text="Time")
        self.event_tree.heading("camera", text="Camera")
        self.event_tree.heading("event", text="Event")
        self.event_tree.heading("roi", text="ROI")
        self.event_tree.heading("state", text="State")
        self.event_tree.heading("snapshot", text="Snapshot")

        self.event_tree.column("time", width=140, anchor="center")
        self.event_tree.column("camera", width=140, anchor="center")
        self.event_tree.column("event", width=180, anchor="w")
        self.event_tree.column("roi", width=100, anchor="center")
        self.event_tree.column("state", width=100, anchor="center")
        self.event_tree.column("snapshot", width=420, anchor="w")

        self.event_tree.pack(fill="x", expand=False)
        self.event_tree.bind("<<TreeviewSelect>>", self._on_event_click)

    def _manager_line(self, parent, row: int, label: str, var: tk.StringVar) -> None:
        ttk.Label(parent, text=f"{label}:").grid(row=row, column=0, sticky="nw", padx=(0, 8), pady=4)
        ttk.Label(parent, textvariable=var, wraplength=220, justify="left").grid(
            row=row, column=1, sticky="nw", pady=4
        )

    def _bind_horizontal_scroll(self) -> None:
        def _on_shift_mousewheel(event):
            if event.delta:
                self.camera_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

        self.camera_canvas.bind_all("<Shift-MouseWheel>", _on_shift_mousewheel)

    def _on_tiles_configure(self, _event=None) -> None:
        self.camera_canvas.configure(scrollregion=self.camera_canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        self.camera_canvas.itemconfigure(self.tiles_window, height=event.height)

    def _reload_cameras(self) -> None:
        cameras = self.camera_store.load_all()
        self.controller.load_cameras(cameras)

        for child in self.tiles_container.winfo_children():
            child.destroy()
        self.tiles = {}

        for cam in cameras:
            camera_uid = cam["camera_uid"]
            tile = CameraTile(
                self.tiles_container,
                camera_uid=camera_uid,
                on_select=self._select_camera,
                on_focus=self._focus_camera,
                on_source_change=self._edit_camera_source,
                on_start=self.controller.start_tile,
                on_stop=self.controller.stop_tile,
            )
            self.tiles[camera_uid] = tile

        self._relayout_tiles()

        for camera_uid in self.tiles:
            self.refresh_camera_tile(camera_uid)

        if cameras and self.selected_camera_uid is None:
            self._select_camera(cameras[0]["camera_uid"])
        else:
            self.refresh_manager_panel()

    def _clear_tile_grid_weights(self) -> None:
        for i in range(20):
            self.tiles_container.rowconfigure(i, weight=0, minsize=0)
            self.tiles_container.columnconfigure(i, weight=0, minsize=0)

    def _relayout_tiles(self) -> None:
        for widget in self.tiles_container.winfo_children():
            widget.grid_forget()

        for i in range(20):
            self.tiles_container.rowconfigure(i, weight=0, minsize=0)
            self.tiles_container.columnconfigure(i, weight=0, minsize=0)

        camera_ids = list(self.tiles.keys())
        if not camera_ids:
            return

        # Focus 1 camera
        if self.focused_camera_uid is not None and self.focused_camera_uid in self.tiles:
            self.tiles_container.rowconfigure(0, weight=1, minsize=520)
            self.tiles_container.columnconfigure(0, weight=3, minsize=760)
            self.tiles_container.columnconfigure(1, weight=1, minsize=320)

            focus_tile = self.tiles[self.focused_camera_uid]
            focus_tile.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=6, pady=6)

            others = [cid for cid in camera_ids if cid != self.focused_camera_uid]
            for idx, cid in enumerate(others):
                self.tiles_container.rowconfigure(idx, weight=1, minsize=180)
                self.tiles[cid].grid(row=idx, column=1, sticky="nsew", padx=6, pady=6)

            self.tiles_container.update_idletasks()
            self.camera_canvas.configure(scrollregion=self.camera_canvas.bbox("all"))
            return

        # Chế độ bình thường: luôn chia 2 hàng
        num_rows = 2
        num_cols = max(1, (len(camera_ids) + 1) // 2)

        for r in range(num_rows):
            self.tiles_container.rowconfigure(r, weight=1, minsize=300)

        for c in range(num_cols):
            self.tiles_container.columnconfigure(c, weight=1, minsize=420)

        for idx, camera_uid in enumerate(camera_ids):
            row = idx // num_cols
            col = idx % num_cols
            self.tiles[camera_uid].grid(row=row, column=col, sticky="nsew", padx=6, pady=6)

        self.tiles_container.update_idletasks()
        self.camera_canvas.configure(scrollregion=self.camera_canvas.bbox("all"))

    def _get_camera_config(self, camera_uid: str) -> Optional[Dict]:
        return self.camera_store.get_by_uid(camera_uid)

    def _select_camera(self, camera_uid: str) -> None:
        self.selected_camera_uid = camera_uid
        self.controller.select_tile(camera_uid)
        self.refresh_manager_panel()

    def _focus_camera(self, camera_uid: str) -> None:
        if self.focused_camera_uid == camera_uid:
            self.focused_camera_uid = None
        else:
            self.focused_camera_uid = camera_uid
            self._select_camera(camera_uid)

        self._relayout_tiles()

    def _toggle_focus_selected(self) -> None:
        if self.selected_camera_uid is None:
            return
        self._focus_camera(self.selected_camera_uid)

    def _add_camera(self) -> None:
        initial = self.camera_store.create_camera(display_name="Camera mới")
        result = ask_source(self.root, "Thêm camera", initial=initial)
        if result is None:
            return

        camera = dict(initial)
        camera.update(result)

        self.camera_store.upsert(camera)
        self.controller.register_camera(camera)
        self._reload_cameras()
        self._select_camera(camera["camera_uid"])
        self.set_status_text(f"Đã thêm {camera['display_name']}")

    def _edit_camera_source(self, camera_uid: str) -> None:
        self._select_camera(camera_uid)
        self._edit_selected_camera()

    def _edit_selected_camera(self) -> None:
        if self.selected_camera_uid is None:
            return

        camera = self._get_camera_config(self.selected_camera_uid)
        if camera is None:
            return

        result = ask_source(self.root, "Sửa camera", initial=camera)
        if result is None:
            return

        camera.update(result)
        self.camera_store.upsert(camera)
        self.controller.configure_source(self.selected_camera_uid, camera)
        self.refresh_camera_tile(self.selected_camera_uid)
        self.refresh_manager_panel()
        self.set_status_text(f"Đã cập nhật {camera['display_name']}")

    def _remove_selected_camera(self) -> None:
        if self.selected_camera_uid is None:
            return

        camera = self._get_camera_config(self.selected_camera_uid)
        if camera is None:
            return

        if not messagebox.askyesno(
            "Xóa camera",
            f"Xóa {camera.get('display_name', self.selected_camera_uid)}?",
            parent=self.root,
        ):
            return

        camera_uid = self.selected_camera_uid
        self.controller.unregister_camera(camera_uid)
        self.camera_store.delete(camera_uid)

        self.selected_camera_uid = None
        if self.focused_camera_uid == camera_uid:
            self.focused_camera_uid = None

        self._reload_cameras()
        self.set_status_text("Đã xóa camera")

    def _start_selected_camera(self) -> None:
        if self.selected_camera_uid is not None:
            self.controller.start_tile(self.selected_camera_uid)

    def _stop_selected_camera(self) -> None:
        if self.selected_camera_uid is not None:
            self.controller.stop_tile(self.selected_camera_uid)

    def refresh_manager_panel(self) -> None:
        if self.selected_camera_uid is None:
            self.var_mgr_name.set("-")
            self.var_mgr_mode.set("-")
            self.var_mgr_source.set("-")
            self.var_mgr_roi.set("-")
            self.var_mgr_status.set("-")
            return

        camera = self._get_camera_config(self.selected_camera_uid)
        if camera is None:
            return

        state = self.controller.get_tile_state(self.selected_camera_uid)

        self.var_mgr_name.set(camera.get("display_name", "-"))
        self.var_mgr_mode.set(camera.get("source_mode", "-"))
        self.var_mgr_source.set(camera.get("source_value", "-"))
        self.var_mgr_roi.set(camera.get("roi_path", "-"))
        self.var_mgr_status.set(state.status)

    def refresh_camera_tile(self, camera_uid: str) -> None:
        if camera_uid not in self.tiles:
            return

        state = self.controller.get_tile_state(camera_uid)
        tile = self.tiles[camera_uid]

        tile.set_title_text(state.camera_name)

        if state.source_mode == "video":
            source_text = f"VIDEO | {os.path.basename(state.source_value)}"
        elif state.source_mode == "rtsp":
            source_text = "RTSP"
        else:
            source_text = "chưa chọn"

        tile.set_source_info(source_text, state.camera_name)
        tile.set_status_text(state.status)
        tile.set_detail_text(state.detail)

        self.refresh_manager_panel()

    def refresh_tile_selection(self) -> None:
        for camera_uid, tile in self.tiles.items():
            tile.set_selected(self.controller.get_tile_state(camera_uid).selected)

    def update_tile_video(self, camera_uid: str, tk_image) -> None:
        if camera_uid in self.tiles:
            self.tiles[camera_uid].update_video(tk_image)

    def get_tile_video_size(self, camera_uid: str):
        if camera_uid not in self.tiles:
            return (640, 360)
        return self.tiles[camera_uid].get_video_size()

    def add_system_log(self, camera_uid: str, camera_name: str, event_type: str, state: str, detail: str) -> None:
        payload = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "camera": camera_name,
            "event_type": event_type,
            "roi_id": "-",
            "trigger_state": state,
            "snapshot_path": detail if os.path.exists(str(detail)) else "",
            "detail": detail,
            "camera_uid": camera_uid,
        }
        item_id = self.event_tree.insert(
            "",
            0,
            values=(
                payload["time"],
                payload["camera"],
                payload["event_type"],
                payload["roi_id"],
                payload["trigger_state"],
                detail,
            ),
        )
        self.event_payloads[item_id] = payload

    def add_ai_event(self, camera_uid: str, camera_name: str, event: dict) -> None:
        payload = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "camera": camera_name,
            "event_type": event.get("event_type", ""),
            "roi_id": event.get("roi_id", ""),
            "trigger_state": event.get("trigger_state", ""),
            "snapshot_path": event.get("snapshot_path", ""),
            "detail": event,
            "camera_uid": camera_uid,
        }
        item_id = self.event_tree.insert(
            "",
            0,
            values=(
                payload["time"],
                payload["camera"],
                payload["event_type"],
                payload["roi_id"],
                payload["trigger_state"],
                payload["snapshot_path"],
            ),
        )
        self.event_payloads[item_id] = payload

    def _on_event_click(self, _event=None) -> None:
        selection = self.event_tree.selection()
        if not selection:
            return

        item_id = selection[0]
        payload = self.event_payloads.get(item_id)
        if payload:
            SnapshotViewer(self.root, payload)

    def set_status_text(self, text: str) -> None:
        self.var_status.set(text)

    def _schedule_poll(self) -> None:
        if not self.root.winfo_exists():
            return
        self.controller.poll()
        self.root.after(40, self._schedule_poll)

    def _open_output_folder(self) -> None:
        output_dir = os.path.abspath("outputs")
        os.makedirs(output_dir, exist_ok=True)

        try:
            os.startfile(output_dir)
        except Exception:
            messagebox.showinfo("Output", output_dir)

    def _logout(self) -> None:
        self.controller.shutdown()
        self.root.destroy()
        self.on_logout()

    def _on_close(self) -> None:
        try:
            self.controller.shutdown()
        finally:
            try:
                self.root.destroy()
            finally:
                try:
                    self.on_logout()
                except Exception:
                    pass