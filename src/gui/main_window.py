from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from src.gui.controller import GUIController


class MainWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("AI Camera - Tkinter GUI")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 760)

        self.controller = GUIController(self)

        self.video_image_ref = None

        self.var_video = tk.StringVar(value="assets/videos/cam01_video1.mp4")
        self.var_roi = tk.StringVar(value="configs/roi_cam01.json")
        self.var_rules = tk.StringVar(value="configs/rules.yaml")
        self.var_runtime = tk.StringVar(value="configs/runtime.yaml")
        self.var_notify = tk.StringVar(value="configs/notify.yaml")
        self.var_person_model = tk.StringVar(value="models/person/best_person.pt")
        self.var_roi_cls_model = tk.StringVar(value="models/roi_state/best_roi_cls.pt")
        self.var_output = tk.StringVar(value="outputs/videos/gui_output.mp4")
        self.var_device = tk.StringVar(value="cpu")
        self.var_save_output = tk.BooleanVar(value=True)

        self.var_status = tk.StringVar(value="San sang")
        self.var_camera = tk.StringVar(value="-")
        self.var_source = tk.StringVar(value="-")
        self.var_video_name = tk.StringVar(value="-")
        self.var_frame_idx = tk.StringVar(value="0")
        self.var_time = tk.StringVar(value="0.0")
        self.var_person_count = tk.StringVar(value="0")
        self.var_fps = tk.StringVar(value="0.0")
        self.var_alerts = tk.StringVar(value="-")

        self._build_layout()
        self._schedule_poll()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self._build_top_controls()
        self._build_main_area()

    def _build_top_controls(self) -> None:
        outer = ttk.Frame(self.root, padding=8)
        outer.grid(row=0, column=0, sticky="nsew")

        for i in range(4):
            outer.columnconfigure(i, weight=1)

        self._path_row(outer, 0, "Video", self.var_video, self._pick_video)
        self._path_row(outer, 1, "ROI JSON", self.var_roi, self._pick_roi_json)
        self._path_row(outer, 2, "Rules YAML", self.var_rules, self._pick_rules_yaml)
        self._path_row(outer, 3, "Runtime YAML", self.var_runtime, self._pick_runtime_yaml)
        self._path_row(outer, 4, "Notify YAML", self.var_notify, self._pick_notify_yaml)
        self._path_row(outer, 5, "Person Model", self.var_person_model, self._pick_person_model)
        self._path_row(outer, 6, "ROI CLS Model", self.var_roi_cls_model, self._pick_roi_cls_model)
        self._path_row(outer, 7, "Output Video", self.var_output, self._pick_output)

        action_frame = ttk.Frame(outer)
        action_frame.grid(row=8, column=0, columnspan=4, sticky="ew", pady=(6, 0))

        ttk.Label(action_frame, text="Device").pack(side="left", padx=(0, 8))
        ttk.Combobox(
            action_frame,
            textvariable=self.var_device,
            values=["cpu", "auto", "0"],
            width=10,
            state="readonly",
        ).pack(side="left")

        ttk.Checkbutton(
            action_frame,
            text="Save output video",
            variable=self.var_save_output,
        ).pack(side="left", padx=12)

        self.btn_start = ttk.Button(action_frame, text="Start", command=self._on_start)
        self.btn_start.pack(side="left", padx=4)

        self.btn_stop = ttk.Button(action_frame, text="Stop", command=self._on_stop, state="disabled")
        self.btn_stop.pack(side="left", padx=4)

        ttk.Label(
            action_frame,
            textvariable=self.var_status,
            foreground="#004b8d",
        ).pack(side="left", padx=16)

    def _path_row(self, parent, row, title, var, browse_cmd) -> None:
        ttk.Label(parent, text=title).grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, columnspan=2, sticky="ew", padx=6, pady=2)
        ttk.Button(parent, text="Browse", command=browse_cmd).grid(row=row, column=3, sticky="ew", pady=2)

    def _build_main_area(self) -> None:
        main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

        left = ttk.Frame(main)
        right = ttk.Frame(main, width=420)

        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)

        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        main.add(left, weight=3)
        main.add(right, weight=1)

        self.video_panel = ttk.Label(left, anchor="center", background="black")
        self.video_panel.grid(row=0, column=0, sticky="nsew")

        status_box = ttk.LabelFrame(right, text="Runtime Status", padding=8)
        status_box.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self._status_line(status_box, 0, "Camera ID", self.var_camera)
        self._status_line(status_box, 1, "Source", self.var_source)
        self._status_line(status_box, 2, "Video", self.var_video_name)
        self._status_line(status_box, 3, "Frame", self.var_frame_idx)
        self._status_line(status_box, 4, "Time (s)", self.var_time)
        self._status_line(status_box, 5, "Persons", self.var_person_count)
        self._status_line(status_box, 6, "FPS", self.var_fps)
        self._status_line(status_box, 7, "Alerts", self.var_alerts)

        event_box = ttk.LabelFrame(right, text="Event Log", padding=6)
        event_box.grid(row=1, column=0, sticky="nsew")

        cols = ("event_type", "roi_id", "trigger_state", "start_sec", "end_sec")
        self.event_tree = ttk.Treeview(event_box, columns=cols, show="headings", height=18)
        self.event_tree.heading("event_type", text="Event")
        self.event_tree.heading("roi_id", text="ROI")
        self.event_tree.heading("trigger_state", text="State")
        self.event_tree.heading("start_sec", text="Start")
        self.event_tree.heading("end_sec", text="End")

        self.event_tree.column("event_type", width=150, anchor="w")
        self.event_tree.column("roi_id", width=70, anchor="center")
        self.event_tree.column("trigger_state", width=90, anchor="center")
        self.event_tree.column("start_sec", width=70, anchor="e")
        self.event_tree.column("end_sec", width=70, anchor="e")

        scrollbar = ttk.Scrollbar(event_box, orient="vertical", command=self.event_tree.yview)
        self.event_tree.configure(yscrollcommand=scrollbar.set)

        self.event_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        event_box.columnconfigure(0, weight=1)
        event_box.rowconfigure(0, weight=1)

    def _status_line(self, parent, row, label, var) -> None:
        ttk.Label(parent, text=f"{label}:").grid(row=row, column=0, sticky="w", padx=(0, 8), pady=2)
        ttk.Label(parent, textvariable=var).grid(row=row, column=1, sticky="w", pady=2)

    def _pick_video(self) -> None:
        path = filedialog.askopenfilename(
            title="Chon video",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv"), ("All files", "*.*")],
        )
        if path:
            self.var_video.set(path)

    def _pick_roi_json(self) -> None:
        path = filedialog.askopenfilename(
            title="Chon ROI JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self.var_roi.set(path)

    def _pick_rules_yaml(self) -> None:
        path = filedialog.askopenfilename(
            title="Chon Rules YAML",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
        )
        if path:
            self.var_rules.set(path)

    def _pick_runtime_yaml(self) -> None:
        path = filedialog.askopenfilename(
            title="Chon Runtime YAML",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
        )
        if path:
            self.var_runtime.set(path)

    def _pick_notify_yaml(self) -> None:
        path = filedialog.askopenfilename(
            title="Chon Notify YAML",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
        )
        if path:
            self.var_notify.set(path)

    def _pick_person_model(self) -> None:
        path = filedialog.askopenfilename(
            title="Chon person model",
            filetypes=[("PyTorch model", "*.pt"), ("All files", "*.*")],
        )
        if path:
            self.var_person_model.set(path)

    def _pick_roi_cls_model(self) -> None:
        path = filedialog.askopenfilename(
            title="Chon ROI classification model",
            filetypes=[("PyTorch model", "*.pt"), ("All files", "*.*")],
        )
        if path:
            self.var_roi_cls_model.set(path)

    def _pick_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Chon file output",
            defaultextension=".mp4",
            filetypes=[("MP4 video", "*.mp4"), ("All files", "*.*")],
        )
        if path:
            self.var_output.set(path)

    # def _set_latest_path(self, path: str) -> None:
    #     widget = self.root.focus_get()
    #     # Browse riêng cho từng ô đang dùng hàm khác nhau, nên gán theo biến phù hợp ở mức thủ công.
    #     # Nếu cần đơn giản tuyệt đối, cứ set theo file type qua nút riêng.
    #     # Ở đây ta không dùng focus-based mapping nữa.
    #     pass

    def _validate_inputs(self) -> bool:
        required_paths = [
            ("Video", self.var_video.get()),
            ("ROI JSON", self.var_roi.get()),
            ("Rules YAML", self.var_rules.get()),
            ("Person model", self.var_person_model.get()),
            ("ROI cls model", self.var_roi_cls_model.get()),
        ]

        for label, path in required_paths:
            if not path.strip():
                messagebox.showerror("Thiếu dữ liệu", f"Chua chon {label}")
                return False

            if not os.path.exists(path):
                messagebox.showerror("Sai duong dan", f"Khong tim thay file: {path}")
                return False

        runtime_path = self.var_runtime.get().strip()
        if runtime_path and not os.path.exists(runtime_path):
            messagebox.showerror("Sai duong dan", f"Khong tim thay runtime file: {runtime_path}")
            return False

        notify_path = self.var_notify.get().strip()
        if notify_path and not os.path.exists(notify_path):
            messagebox.showerror("Sai duong dan", f"Khong tim thay notify file: {notify_path}")
            return False

        output_dir = os.path.dirname(self.var_output.get().strip())
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        return True

    def _on_start(self) -> None:
        if not self._validate_inputs():
            return

        try:
            self.controller.start_pipeline(
                video_path=self.var_video.get().strip(),
                roi_path=self.var_roi.get().strip(),
                rules_path=self.var_rules.get().strip(),
                runtime_path=self.var_runtime.get().strip(),
                notify_path=self.var_notify.get().strip(),
                person_model_path=self.var_person_model.get().strip(),
                roi_cls_model_path=self.var_roi_cls_model.get().strip(),
                output_path=self.var_output.get().strip(),
                device=self.var_device.get().strip(),
                save_output=self.var_save_output.get(),
            )
        except Exception as e:
            messagebox.showerror("Loi khoi dong pipeline", str(e))
            return

        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.set_status_text("Dang chay pipeline")

    def _on_stop(self) -> None:
        self.controller.stop_pipeline()
        self.on_pipeline_stopped()

    def on_pipeline_stopped(self) -> None:
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")

    def update_video(self, tk_image) -> None:
        self.video_image_ref = tk_image
        self.video_panel.configure(image=tk_image, text="")

    def get_video_width(self) -> int:
        self.root.update_idletasks()
        w = self.video_panel.winfo_width()
        return w if w > 1 else 960

    def get_video_height(self) -> int:
        self.root.update_idletasks()
        h = self.video_panel.winfo_height()
        return h if h > 1 else 540

    def set_runtime_summary(self, summary: dict) -> None:
        self.var_camera.set(summary.get("camera_id", "-"))
        self.var_source.set(summary.get("source_type", "-"))
        self.var_video_name.set(summary.get("video_name", "-"))
        self.set_status_text("Khoi tao pipeline thanh cong")

    def set_frame_status(self, status: dict) -> None:
        self.var_camera.set(status.get("camera_id", "-"))
        self.var_source.set(status.get("source_type", "-"))
        self.var_video_name.set(status.get("video_name", "-"))
        self.var_frame_idx.set(str(status.get("frame_idx", 0)))
        self.var_time.set(str(round(float(status.get("current_sec", 0.0)), 2)))
        self.var_person_count.set(str(status.get("person_count", 0)))
        self.var_fps.set(str(status.get("fps_runtime", 0.0)))

        alerts = status.get("alerts", [])
        self.var_alerts.set(" | ".join(alerts) if alerts else "-")

    def append_event(self, event: dict) -> None:
        values = (
            event.get("event_type", ""),
            event.get("roi_id", ""),
            event.get("trigger_state", ""),
            round(float(event.get("start_time_sec", 0.0)), 2),
            round(float(event.get("end_time_sec", 0.0)), 2),
        )
        self.event_tree.insert("", 0, values=values)

    def set_status_text(self, text: str) -> None:
        self.var_status.set(text)

    def _schedule_poll(self) -> None:
        self.controller.poll_queues()
        self.root.after(50, self._schedule_poll)

    def _on_close(self) -> None:
        try:
            self.controller.stop_pipeline()
        finally:
            self.root.destroy()


def launch_app() -> None:
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()