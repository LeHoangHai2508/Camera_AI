from __future__ import annotations

import os
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import Dict

from src.gui.camera_tile import CameraTile
from src.gui.multi_controller import MultiController
from src.gui.snapshot_viewer import SnapshotViewer
from src.gui.source_dialog import ask_source


class DashboardWindow:
    def __init__(self, root: tk.Toplevel, user: Dict, on_logout) -> None:
        self.root = root
        self.user = user
        self.on_logout = on_logout

        self.root.title("AI Camera - Dashboard")
        self.root.geometry("1500x920")
        self.root.minsize(1280, 760)

        self.var_status = tk.StringVar(
            value=f"Đăng nhập: {self.user.get('display_name', self.user.get('username', ''))}"
        )

        self.controller = MultiController(self)
        self.tiles: Dict[int, CameraTile] = {}
        self.focused_tile_id: int | None = None
        self.event_payloads: Dict[str, dict] = {}

        self._setup_styles()
        self._build_ui()
        self.controller.select_tile(1)
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
        self._build_camera_grid()
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

        ttk.Button(toolbar, text="Start All", command=self.controller.start_all).pack(side="left")
        ttk.Button(toolbar, text="Stop All", command=self.controller.stop_all).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Open Output Folder", command=self._open_output_folder).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Save Picture", command=self._not_ready).pack(side="left", padx=(20, 0))
        ttk.Button(toolbar, text="Save Video", command=self._not_ready).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="ROI Bold", command=self._not_ready).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Zoom", command=self._toggle_focus_selected).pack(side="left", padx=(6, 0))

        ttk.Label(toolbar, textvariable=self.var_status).pack(side="right")

    def _build_camera_grid(self) -> None:
        self.grid_frame = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        self.grid_frame.grid(row=2, column=0, sticky="nsew")

        for tile_id in (1, 2, 3, 4):
            tile = CameraTile(
                self.grid_frame,
                tile_id=tile_id,
                on_select=self.controller.select_tile,
                on_focus=self._toggle_focus_tile,
                on_source_change=self._change_source_for_tile,
                on_start=self.controller.start_tile,
                on_stop=self.controller.stop_tile,
            )
            self.tiles[tile_id] = tile

        self._layout_tiles()
        for tile_id in self.tiles:
            self.refresh_tile(tile_id)

    def _layout_tiles(self) -> None:
        for widget in self.grid_frame.winfo_children():
            widget.grid_forget()

        for i in range(4):
            self.grid_frame.rowconfigure(i, weight=0)
            self.grid_frame.columnconfigure(i, weight=0)

        if self.focused_tile_id is None:
            for r in range(2):
                self.grid_frame.rowconfigure(r, weight=1)
            for c in range(2):
                self.grid_frame.columnconfigure(c, weight=1)

            positions = {
                1: (0, 0),
                2: (0, 1),
                3: (1, 0),
                4: (1, 1),
            }

            for tile_id, (r, c) in positions.items():
                self.tiles[tile_id].grid(row=r, column=c, sticky="nsew", padx=6, pady=6)
        else:
            self.grid_frame.rowconfigure(0, weight=1)
            self.grid_frame.rowconfigure(1, weight=1)
            self.grid_frame.rowconfigure(2, weight=1)
            self.grid_frame.columnconfigure(0, weight=3)
            self.grid_frame.columnconfigure(1, weight=1)

            focus_tile = self.tiles[self.focused_tile_id]
            focus_tile.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=6, pady=6)

            others = [tid for tid in (1, 2, 3, 4) if tid != self.focused_tile_id]
            for idx, tid in enumerate(others):
                self.tiles[tid].grid(row=idx, column=1, sticky="nsew", padx=6, pady=6)

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
        self.event_tree.column("camera", width=80, anchor="center")
        self.event_tree.column("event", width=180, anchor="w")
        self.event_tree.column("roi", width=100, anchor="center")
        self.event_tree.column("state", width=100, anchor="center")
        self.event_tree.column("snapshot", width=420, anchor="w")

        self.event_tree.pack(fill="x", expand=False)
        self.event_tree.bind("<<TreeviewSelect>>", self._on_event_click)

    def _change_source_for_tile(self, tile_id: int) -> None:
        result = ask_source(self.root, tile_id)
        if result is None:
            return

        mode, name, value = result
        self.controller.configure_source(tile_id, mode, name, value)
        self.set_status_text(f"Tile {tile_id}: đã chọn nguồn {mode}")

    def _toggle_focus_tile(self, tile_id: int) -> None:
        if self.focused_tile_id == tile_id:
            self.focused_tile_id = None
        else:
            self.focused_tile_id = tile_id
            self.controller.select_tile(tile_id)

        self._layout_tiles()

    def _toggle_focus_selected(self) -> None:
        selected_id = self.controller.selected_tile_id
        if selected_id is None:
            return
        self._toggle_focus_tile(selected_id)

    def refresh_tile(self, tile_id: int) -> None:
        state = self.controller.get_tile_state(tile_id)
        tile = self.tiles[tile_id]

        if state.source_mode == "video":
            source_text = f"VIDEO | {os.path.basename(state.source_value)}"
        elif state.source_mode == "rtsp":
            source_text = "RTSP"
        else:
            source_text = "chưa chọn"

        tile.set_source_info(source_text, state.source_name)
        tile.set_status_text(state.status)
        tile.set_detail_text(state.detail)

    def refresh_tile_selection(self) -> None:
        for tile_id, tile in self.tiles.items():
            tile.set_selected(self.controller.get_tile_state(tile_id).selected)

    def update_tile_video(self, tile_id: int, tk_image) -> None:
        self.tiles[tile_id].update_video(tk_image)

    def get_tile_video_size(self, tile_id: int):
        return self.tiles[tile_id].get_video_size()

    def add_system_log(self, tile_id: int, event_type: str, state: str, detail: str) -> None:
        payload = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "camera": f"Cam {tile_id}",
            "event_type": event_type,
            "roi_id": "-",
            "trigger_state": state,
            "snapshot_path": detail if os.path.exists(str(detail)) else "",
            "detail": detail,
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

    def add_ai_event(self, tile_id: int, event: dict) -> None:
        payload = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "camera": f"Cam {tile_id}",
            "event_type": event.get("event_type", ""),
            "roi_id": event.get("roi_id", ""),
            "trigger_state": event.get("trigger_state", ""),
            "snapshot_path": event.get("snapshot_path", ""),
            "detail": event,
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
        if not payload:
            return

        SnapshotViewer(self.root, payload)

    def set_status_text(self, text: str) -> None:
        self.var_status.set(text)

    def _schedule_poll(self) -> None:
        self.controller.poll()
        self.root.after(40, self._schedule_poll)

    def _open_output_folder(self) -> None:
        output_dir = os.path.abspath("outputs")
        os.makedirs(output_dir, exist_ok=True)

        try:
            os.startfile(output_dir)
        except Exception:
            messagebox.showinfo("Output", output_dir)

    def _not_ready(self) -> None:
        messagebox.showinfo("Thông báo", "Chức năng này sẽ nối ở bước sau")

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