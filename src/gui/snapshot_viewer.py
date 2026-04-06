from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk, messagebox

from PIL import Image, ImageTk


class SnapshotViewer(tk.Toplevel):
    def __init__(self, parent, event_data: dict) -> None:
        super().__init__(parent)
        self.title("Event Snapshot")
        self.geometry("1000x700")
        self.minsize(700, 500)

        self.event_data = event_data
        self.image_ref = None

        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        self._build_ui()
        self._load_snapshot()

    def _build_ui(self) -> None:
        left = ttk.Frame(self, padding=8)
        left.grid(row=0, column=0, sticky="nsew")
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)

        right = ttk.Frame(self, padding=8)
        right.grid(row=0, column=1, sticky="nsew")

        self.image_label = tk.Label(
            left,
            text="Không có ảnh",
            bg="black",
            fg="white",
            anchor="center",
        )
        self.image_label.grid(row=0, column=0, sticky="nsew")

        fields = [
            ("Time", self.event_data.get("time", "")),
            ("Camera", self.event_data.get("camera", "")),
            ("Event", self.event_data.get("event_type", "")),
            ("ROI", self.event_data.get("roi_id", "")),
            ("State", self.event_data.get("trigger_state", "")),
            ("Snapshot", self.event_data.get("snapshot_path", "")),
        ]

        for idx, (label, value) in enumerate(fields):
            ttk.Label(right, text=f"{label}:", font=("Segoe UI", 10, "bold")).grid(
                row=idx, column=0, sticky="nw", padx=(0, 8), pady=4
            )
            ttk.Label(right, text=str(value), wraplength=320, justify="left").grid(
                row=idx, column=1, sticky="nw", pady=4
            )

        ttk.Button(right, text="Đóng", command=self.destroy).grid(
            row=len(fields), column=1, sticky="e", pady=(16, 0)
        )

        self.bind("<Configure>", self._on_resize)

    def _load_snapshot(self) -> None:
        path = self.event_data.get("snapshot_path", "")
        if not path or not os.path.exists(path):
            self.image_label.configure(text="Event này không có snapshot", image="")
            self.image_ref = None
            return

        self._render_image(path)

    def _render_image(self, path: str) -> None:
        try:
            image = Image.open(path)

            self.update_idletasks()
            target_w = max(400, self.image_label.winfo_width())
            target_h = max(300, self.image_label.winfo_height())

            img_w, img_h = image.size
            scale = min(target_w / img_w, target_h / img_h)
            new_w = max(1, int(img_w * scale))
            new_h = max(1, int(img_h * scale))

            image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
            tk_image = ImageTk.PhotoImage(image)
            self.image_ref = tk_image
            self.image_label.configure(image=tk_image, text="")
        except Exception as e:
            messagebox.showerror("Lỗi mở ảnh", str(e), parent=self)

    def _on_resize(self, _event=None) -> None:
        path = self.event_data.get("snapshot_path", "")
        if path and os.path.exists(path):
            self._render_image(path)