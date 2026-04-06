from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional, Tuple


class SourceDialog(tk.Toplevel):
    def __init__(self, parent, tile_id: int) -> None:
        super().__init__(parent)
        self.title(f"Chọn nguồn - Camera {tile_id}")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result: Optional[Tuple[str, str, str]] = None

        self.var_mode = tk.StringVar(value="video")
        self.var_name = tk.StringVar(value=f"cam{tile_id:02d}")
        self.var_value = tk.StringVar(value="")

        self._build_ui(tile_id)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _build_ui(self, tile_id: int) -> None:
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text=f"Nguồn cho Camera {tile_id}",
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        ttk.Label(outer, text="Kiểu nguồn").grid(row=1, column=0, sticky="w", pady=4)
        mode_box = ttk.Combobox(
            outer,
            textvariable=self.var_mode,
            values=["video", "rtsp", "none"],
            state="readonly",
            width=16,
        )
        mode_box.grid(row=1, column=1, columnspan=2, sticky="ew", pady=4)
        mode_box.bind("<<ComboboxSelected>>", lambda _e: self._on_mode_change())

        ttk.Label(outer, text="Tên hiển thị").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(outer, textvariable=self.var_name, width=30).grid(
            row=2, column=1, columnspan=2, sticky="ew", pady=4
        )

        ttk.Label(outer, text="Đường dẫn / URL").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(outer, textvariable=self.var_value, width=42).grid(
            row=3, column=1, sticky="ew", pady=4
        )
        self.btn_browse = ttk.Button(outer, text="Browse", command=self._browse_video)
        self.btn_browse.grid(row=3, column=2, sticky="ew", padx=(6, 0), pady=4)

        info = (
            "video: chọn file mp4/avi/mov/mkv\n"
            "rtsp: dán URL camera, ví dụ rtsp://user:pass@ip:554/...\n"
            "none: bỏ nguồn khỏi ô"
        )
        ttk.Label(outer, text=info, foreground="#555555", justify="left").grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(8, 10)
        )

        btn_row = ttk.Frame(outer)
        btn_row.grid(row=5, column=0, columnspan=3, sticky="e")
        ttk.Button(btn_row, text="OK", command=self._on_ok).pack(side="right")
        ttk.Button(btn_row, text="Cancel", command=self._on_cancel).pack(
            side="right", padx=(0, 6)
        )

        outer.columnconfigure(1, weight=1)
        self._on_mode_change()

    def _on_mode_change(self) -> None:
        mode = self.var_mode.get().strip().lower()
        if mode == "video":
            self.btn_browse.configure(state="normal")
        else:
            self.btn_browse.configure(state="disabled")
            if mode == "none":
                self.var_value.set("")

    def _browse_video(self) -> None:
        path = filedialog.askopenfilename(
            title="Chọn video",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv"), ("All files", "*.*")],
            parent=self,
        )
        if path:
            self.var_value.set(path)

    def _on_ok(self) -> None:
        mode = self.var_mode.get().strip().lower()
        name = self.var_name.get().strip()
        value = self.var_value.get().strip()

        if not name:
            messagebox.showerror("Thiếu dữ liệu", "Bạn chưa nhập tên hiển thị", parent=self)
            return

        if mode in {"video", "rtsp"} and not value:
            messagebox.showerror("Thiếu dữ liệu", "Bạn chưa chọn đường dẫn hoặc URL", parent=self)
            return

        if mode == "none":
            value = ""

        self.result = (mode, name, value)
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()


def ask_source(parent, tile_id: int):
    dialog = SourceDialog(parent, tile_id)
    dialog.wait_window()
    return dialog.result