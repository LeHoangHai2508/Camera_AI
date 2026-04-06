from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, Optional


class SourceDialog(tk.Toplevel):
    def __init__(self, parent, title_text: str, initial: Optional[Dict] = None) -> None:
        super().__init__(parent)
        self.title(title_text)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        initial = initial or {}
        self.result = None

        self.var_display_name = tk.StringVar(value=initial.get("display_name", ""))
        self.var_mode = tk.StringVar(value=initial.get("source_mode", "video"))
        self.var_source_value = tk.StringVar(value=initial.get("source_value", ""))
        self.var_roi_path = tk.StringVar(value=initial.get("roi_path", "configs/roi_cam01.json"))

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Tên camera").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(outer, textvariable=self.var_display_name, width=42).grid(
            row=0, column=1, columnspan=2, sticky="ew", pady=4
        )

        ttk.Label(outer, text="Kiểu nguồn").grid(row=1, column=0, sticky="w", pady=4)
        mode_box = ttk.Combobox(
            outer,
            textvariable=self.var_mode,
            values=["video", "rtsp", "none"],
            state="readonly",
            width=18,
        )
        mode_box.grid(row=1, column=1, columnspan=2, sticky="ew", pady=4)
        mode_box.bind("<<ComboboxSelected>>", lambda _e: self._on_mode_change())

        ttk.Label(outer, text="File / URL").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(outer, textvariable=self.var_source_value, width=42).grid(
            row=2, column=1, sticky="ew", pady=4
        )
        self.btn_source = ttk.Button(outer, text="Browse", command=self._browse_source)
        self.btn_source.grid(row=2, column=2, sticky="ew", padx=(6, 0), pady=4)

        ttk.Label(outer, text="ROI config").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(outer, textvariable=self.var_roi_path, width=42).grid(
            row=3, column=1, sticky="ew", pady=4
        )
        ttk.Button(outer, text="Browse", command=self._browse_roi).grid(
            row=3, column=2, sticky="ew", padx=(6, 0), pady=4
        )

        info = (
            "video: chọn file video\n"
            "rtsp: dán URL rtsp://...\n"
            "none: tạo camera nhưng chưa gán nguồn"
        )
        ttk.Label(outer, text=info, justify="left", foreground="#555555").grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(6, 10)
        )

        btn_row = ttk.Frame(outer)
        btn_row.grid(row=5, column=0, columnspan=3, sticky="e")
        ttk.Button(btn_row, text="OK", command=self._on_ok).pack(side="right")
        ttk.Button(btn_row, text="Cancel", command=self._on_cancel).pack(side="right", padx=(0, 6))

        outer.columnconfigure(1, weight=1)
        self._on_mode_change()

    def _on_mode_change(self) -> None:
        mode = self.var_mode.get().strip().lower()
        if mode == "video":
            self.btn_source.configure(state="normal")
        elif mode == "rtsp":
            self.btn_source.configure(state="disabled")
        else:
            self.btn_source.configure(state="disabled")
            self.var_source_value.set("")

    def _browse_source(self) -> None:
        path = filedialog.askopenfilename(
            title="Chọn video",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv"), ("All files", "*.*")],
            parent=self,
        )
        if path:
            self.var_source_value.set(path)

    def _browse_roi(self) -> None:
        path = filedialog.askopenfilename(
            title="Chọn file ROI",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=os.path.abspath("configs"),
            parent=self,
        )
        if path:
            self.var_roi_path.set(path)

    def _on_ok(self) -> None:
        display_name = self.var_display_name.get().strip()
        source_mode = self.var_mode.get().strip().lower()
        source_value = self.var_source_value.get().strip()
        roi_path = self.var_roi_path.get().strip()

        if not display_name:
            messagebox.showerror("Thiếu dữ liệu", "Bạn chưa nhập tên camera", parent=self)
            return

        if source_mode in {"video", "rtsp"} and not source_value:
            messagebox.showerror("Thiếu dữ liệu", "Bạn chưa nhập nguồn video hoặc RTSP", parent=self)
            return

        if not roi_path:
            messagebox.showerror("Thiếu dữ liệu", "Bạn chưa chọn file ROI", parent=self)
            return

        self.result = {
            "display_name": display_name,
            "source_mode": source_mode,
            "source_value": source_value,
            "roi_path": roi_path,
        }
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()


def ask_source(parent, title_text: str, initial: Optional[Dict] = None):
    dialog = SourceDialog(parent, title_text=title_text, initial=initial)
    dialog.wait_window()
    return dialog.result