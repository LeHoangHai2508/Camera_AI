from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class CameraTile(ttk.Frame):
    def __init__(
        self,
        parent,
        camera_uid: str,
        on_select: Callable[[str], None],
        on_focus: Callable[[str], None],
        on_source_change: Callable[[str], None],
        on_start: Callable[[str], None],
        on_stop: Callable[[str], None],
    ) -> None:
        super().__init__(parent, padding=6, style="Tile.TFrame")

        self.camera_uid = camera_uid
        self.on_select = on_select
        self.on_focus = on_focus
        self.on_source_change = on_source_change
        self.on_start = on_start
        self.on_stop = on_stop

        self.video_image_ref = None

        self.var_title = tk.StringVar(value=camera_uid)
        self.var_source = tk.StringVar(value="Nguồn: chưa chọn")
        self.var_name = tk.StringVar(value="Tên nguồn: -")
        self.var_status = tk.StringVar(value="Trạng thái: idle")
        self.var_detail = tk.StringVar(value="Kết nối: chưa có")

        self._build_ui()
        self._bind_select_recursive(self)
        self._bind_focus_video()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            textvariable=self.var_title,
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, sticky="w")

        btns = ttk.Frame(header)
        btns.grid(row=0, column=1, sticky="e")

        ttk.Button(
            btns,
            text="Start",
            command=lambda: self.on_start(self.camera_uid),
        ).pack(side="left")

        ttk.Button(
            btns,
            text="Stop",
            command=lambda: self.on_stop(self.camera_uid),
        ).pack(side="left", padx=(4, 0))

        ttk.Button(
            btns,
            text="Source",
            command=lambda: self.on_source_change(self.camera_uid),
        ).pack(side="left", padx=(4, 0))

        self.video_container = ttk.Frame(self, relief="solid", borderwidth=1, height=220)
        self.video_container.grid(row=1, column=0, sticky="nsew")
        self.video_container.grid_propagate(False)
        self.video_container.columnconfigure(0, weight=1)
        self.video_container.rowconfigure(0, weight=1)

        self.video_label = tk.Label(
            self.video_container,
            text="No Signal",
            bg="black",
            fg="white",
            anchor="center",
        )
        self.video_label.grid(row=0, column=0, sticky="nsew")

        info = ttk.Frame(self)
        info.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        ttk.Label(info, textvariable=self.var_source).pack(anchor="w")
        ttk.Label(info, textvariable=self.var_name).pack(anchor="w")
        ttk.Label(info, textvariable=self.var_status).pack(anchor="w")
        ttk.Label(info, textvariable=self.var_detail).pack(anchor="w")

    def _bind_select_recursive(self, widget) -> None:
        widget.bind("<Button-1>", self._handle_select, add="+")
        for child in widget.winfo_children():
            self._bind_select_recursive(child)

    def _bind_focus_video(self) -> None:
        self.video_container.bind("<Double-Button-1>", self._handle_focus, add="+")
        self.video_label.bind("<Double-Button-1>", self._handle_focus, add="+")

    def _handle_select(self, _event) -> None:
        self.on_select(self.camera_uid)

    def _handle_focus(self, _event) -> None:
        self.on_focus(self.camera_uid)

    def set_selected(self, selected: bool) -> None:
        self.configure(style="SelectedTile.TFrame" if selected else "Tile.TFrame")

    def set_title_text(self, text: str) -> None:
        self.var_title.set(text)

    def set_source_info(self, source_text: str, name_text: str) -> None:
        self.var_source.set(f"Nguồn: {source_text}")
        self.var_name.set(f"Tên nguồn: {name_text}")

    def set_status_text(self, text: str) -> None:
        self.var_status.set(f"Trạng thái: {text}")

    def set_detail_text(self, text: str) -> None:
        self.var_detail.set(f"Kết nối: {text}")

    def update_video(self, tk_image: Optional[tk.PhotoImage]) -> None:
        self.video_image_ref = tk_image
        if tk_image is None:
            self.video_label.configure(image="", text="No Signal")
        else:
            self.video_label.configure(image=tk_image, text="")

    def get_video_size(self) -> tuple[int, int]:
        w = self.video_container.winfo_width()
        h = self.video_container.winfo_height()

        if w <= 10 or h <= 10:
            return (640, 360)

        return (w, h)