from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, Optional
from urllib.parse import urlsplit, urlunsplit


def build_rtsp_url(
    host: str,
    port: str,
    username: str,
    password: str,
    stream_path: str,
) -> str:
    host = (host or "").strip()
    port = (port or "").strip()
    username = (username or "").strip()
    password = (password or "").strip()
    stream_path = (stream_path or "").strip()

    if not host:
        return ""

    netloc = host
    if port:
        netloc = f"{host}:{port}"

    if username:
        if password:
            netloc = f"{username}:{password}@{netloc}"
        else:
            netloc = f"{username}@{netloc}"

    if stream_path and not stream_path.startswith("/"):
        stream_path = "/" + stream_path

    return urlunsplit(("rtsp", netloc, stream_path, "", ""))


def parse_rtsp_url(rtsp_url: str) -> Dict[str, str]:
    rtsp_url = (rtsp_url or "").strip()
    if not rtsp_url.lower().startswith("rtsp://"):
        return {
            "host": "",
            "port": "554",
            "username": "",
            "password": "",
            "stream_path": "",
        }

    try:
        parsed = urlsplit(rtsp_url)
        return {
            "host": parsed.hostname or "",
            "port": str(parsed.port or 554),
            "username": parsed.username or "",
            "password": parsed.password or "",
            "stream_path": (parsed.path or "").lstrip("/"),
        }
    except Exception:
        return {
            "host": "",
            "port": "554",
            "username": "",
            "password": "",
            "stream_path": "",
        }


class SourceDialog(tk.Toplevel):
    def __init__(self, parent, title_text: str, initial: Optional[Dict] = None) -> None:
        super().__init__(parent)
        self.title(title_text)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        initial = initial or {}
        self.result = None

        source_mode = initial.get("source_mode", "video")
        source_value = initial.get("source_value", "")

        parsed_rtsp = parse_rtsp_url(source_value) if source_mode == "rtsp" else {
            "host": initial.get("rtsp_host", ""),
            "port": str(initial.get("rtsp_port", "554")),
            "username": initial.get("rtsp_username", ""),
            "password": initial.get("rtsp_password", ""),
            "stream_path": initial.get("rtsp_path", ""),
        }

        self.var_display_name = tk.StringVar(value=initial.get("display_name", ""))
        self.var_mode = tk.StringVar(value=source_mode)
        self.var_source_value = tk.StringVar(value=source_value)
        self.var_roi_path = tk.StringVar(value=initial.get("roi_path", "configs/roi_cam01.json"))

        self.var_rtsp_host = tk.StringVar(value=initial.get("rtsp_host", parsed_rtsp["host"]))
        self.var_rtsp_port = tk.StringVar(value=str(initial.get("rtsp_port", parsed_rtsp["port"])))
        self.var_rtsp_username = tk.StringVar(value=initial.get("rtsp_username", parsed_rtsp["username"]))
        self.var_rtsp_password = tk.StringVar(value=initial.get("rtsp_password", parsed_rtsp["password"]))
        self.var_rtsp_path = tk.StringVar(value=initial.get("rtsp_path", parsed_rtsp["stream_path"]))

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

        # ----- VIDEO FRAME -----
        self.video_frame = ttk.LabelFrame(outer, text="Nguồn video", padding=8)
        self.video_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8, 4))

        ttk.Label(self.video_frame, text="File video").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(self.video_frame, textvariable=self.var_source_value, width=42).grid(
            row=0, column=1, sticky="ew", pady=4
        )
        self.btn_source = ttk.Button(self.video_frame, text="Browse", command=self._browse_source)
        self.btn_source.grid(row=0, column=2, sticky="ew", padx=(6, 0), pady=4)
        self.video_frame.columnconfigure(1, weight=1)

        # ----- RTSP FRAME -----
        self.rtsp_frame = ttk.LabelFrame(outer, text="Kết nối camera RTSP", padding=8)
        self.rtsp_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=4)

        ttk.Label(self.rtsp_frame, text="IP / Host").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(self.rtsp_frame, textvariable=self.var_rtsp_host, width=24).grid(
            row=0, column=1, sticky="ew", pady=4
        )

        ttk.Label(self.rtsp_frame, text="Port").grid(row=0, column=2, sticky="w", padx=(12, 0), pady=4)
        ttk.Entry(self.rtsp_frame, textvariable=self.var_rtsp_port, width=8).grid(
            row=0, column=3, sticky="ew", pady=4
        )

        ttk.Label(self.rtsp_frame, text="User").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(self.rtsp_frame, textvariable=self.var_rtsp_username, width=24).grid(
            row=1, column=1, sticky="ew", pady=4
        )

        ttk.Label(self.rtsp_frame, text="Password").grid(row=1, column=2, sticky="w", padx=(12, 0), pady=4)
        ttk.Entry(self.rtsp_frame, textvariable=self.var_rtsp_password, width=18, show="*").grid(
            row=1, column=3, sticky="ew", pady=4
        )

        ttk.Label(self.rtsp_frame, text="RTSP path").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(self.rtsp_frame, textvariable=self.var_rtsp_path, width=42).grid(
            row=2, column=1, columnspan=3, sticky="ew", pady=4
        )

        ttk.Label(
            self.rtsp_frame,
            text="Ví dụ path: Streaming/Channels/101 hoặc cam/realmonitor?channel=1&subtype=0",
            foreground="#666666",
            justify="left",
        ).grid(row=3, column=0, columnspan=4, sticky="w", pady=(2, 0))

        self.rtsp_frame.columnconfigure(1, weight=1)
        self.rtsp_frame.columnconfigure(3, weight=1)

        # ----- ROI -----
        ttk.Label(outer, text="ROI config").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Entry(outer, textvariable=self.var_roi_path, width=42).grid(
            row=4, column=1, sticky="ew", pady=4
        )
        ttk.Button(outer, text="Browse", command=self._browse_roi).grid(
            row=4, column=2, sticky="ew", padx=(6, 0), pady=4
        )

        info = (
            "video: chọn file video\n"
            "rtsp: nhập IP, port, tài khoản, mật khẩu, path stream\n"
            "none: tạo camera nhưng chưa gán nguồn"
        )
        ttk.Label(outer, text=info, justify="left", foreground="#555555").grid(
            row=5, column=0, columnspan=3, sticky="w", pady=(6, 10)
        )

        btn_row = ttk.Frame(outer)
        btn_row.grid(row=6, column=0, columnspan=3, sticky="e")
        ttk.Button(btn_row, text="OK", command=self._on_ok).pack(side="right")
        ttk.Button(btn_row, text="Cancel", command=self._on_cancel).pack(side="right", padx=(0, 6))

        outer.columnconfigure(1, weight=1)
        self._on_mode_change()

    def _on_mode_change(self) -> None:
        mode = self.var_mode.get().strip().lower()

        if mode == "video":
            self.video_frame.grid()
            self.rtsp_frame.grid_remove()
            self.btn_source.configure(state="normal")

        elif mode == "rtsp":
            self.video_frame.grid_remove()
            self.rtsp_frame.grid()

        else:
            self.video_frame.grid_remove()
            self.rtsp_frame.grid_remove()
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
        roi_path = self.var_roi_path.get().strip()

        if not display_name:
            messagebox.showerror("Thiếu dữ liệu", "Bạn chưa nhập tên camera", parent=self)
            return

        if not roi_path:
            messagebox.showerror("Thiếu dữ liệu", "Bạn chưa chọn file ROI", parent=self)
            return

        if source_mode == "video":
            source_value = self.var_source_value.get().strip()
            if not source_value:
                messagebox.showerror("Thiếu dữ liệu", "Bạn chưa chọn file video", parent=self)
                return

            self.result = {
                "display_name": display_name,
                "source_mode": "video",
                "source_value": source_value,
                "roi_path": roi_path,
                "rtsp_host": "",
                "rtsp_port": "554",
                "rtsp_username": "",
                "rtsp_password": "",
                "rtsp_path": "",
            }
            self.destroy()
            return

        if source_mode == "rtsp":
            host = self.var_rtsp_host.get().strip()
            port = self.var_rtsp_port.get().strip() or "554"
            username = self.var_rtsp_username.get().strip()
            password = self.var_rtsp_password.get().strip()
            stream_path = self.var_rtsp_path.get().strip()

            if not host:
                messagebox.showerror("Thiếu dữ liệu", "Bạn chưa nhập IP hoặc Host camera", parent=self)
                return

            if not port.isdigit():
                messagebox.showerror("Sai dữ liệu", "Port phải là số", parent=self)
                return

            if not stream_path:
                messagebox.showerror("Thiếu dữ liệu", "Bạn chưa nhập RTSP path", parent=self)
                return

            source_value = build_rtsp_url(
                host=host,
                port=port,
                username=username,
                password=password,
                stream_path=stream_path,
            )

            self.result = {
                "display_name": display_name,
                "source_mode": "rtsp",
                "source_value": source_value,
                "roi_path": roi_path,
                "rtsp_host": host,
                "rtsp_port": port,
                "rtsp_username": username,
                "rtsp_password": password,
                "rtsp_path": stream_path,
            }
            self.destroy()
            return

        self.result = {
            "display_name": display_name,
            "source_mode": "none",
            "source_value": "",
            "roi_path": roi_path,
            "rtsp_host": "",
            "rtsp_port": "554",
            "rtsp_username": "",
            "rtsp_password": "",
            "rtsp_path": "",
        }
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()


def ask_source(parent, title_text: str, initial: Optional[Dict] = None):
    dialog = SourceDialog(parent, title_text=title_text, initial=initial)
    dialog.wait_window()
    return dialog.result