# Codebase Map

## 1. Sơ đồ luồng tổng

```text
extract_frames.py
    -> roi_tool.py
    -> crop_roi.py
    -> gán nhãn thủ công
    -> train_person.py
    -> train_roi_cls.py
    -> infer_demo.py
        -> config_utils.py
        -> tracker_utils.py
        -> rule_engine.py
        -> draw_utils.py
        -> event_logger.py
        -> common.py
```

## 2. Vai trò từng file trong `src/`

### `src/common.py`
Vai trò:
- chứa constant màu sắc,
- helper tạo thư mục,
- helper thời gian.

Hàm chính:
- `ensure_dir(path)`: tạo thư mục nếu chưa tồn tại.
- `ts_now_str()`: sinh timestamp dạng file-safe.
- `sec_to_mmss(seconds)`: đổi giây sang `MM:SS`.
- `frame_to_sec(frame_idx, fps)`: đổi số frame sang thời gian video.

Được gọi lại bởi:
- `extract_frames.py`
- `roi_tool.py`
- `draw_utils.py`
- `event_logger.py`
- `infer_demo.py`

---

### `src/config_utils.py`
Vai trò:
- load và validate file config JSON/YAML.

Hàm chính:
- `load_roi_config(json_path)`: nạp ROI config.
- `get_roi_points(roi_entry)`: lấy polygon points.
- `load_rules(yaml_path)`: nạp rule config.
- `load_runtime(yaml_path)`: nạp runtime config.
- `load_class_names(yaml_path)`: nạp map class name.
- `load_all_configs(...)`: gộp nhiều config.

Được gọi lại bởi:
- `crop_roi.py`
- `infer_demo.py`

---

### `src/extract_frames.py`
Vai trò:
- trích frame từ video theo chu kỳ thời gian.

Hàm chính:
- `extract_frames(video_path, out_dir, interval_sec=1.0)`

Đầu vào:
- video gốc trong `assets/videos/`

Đầu ra:
- ảnh frame trong `assets/frames_person/` hoặc thư mục chỉ định.

Được dùng ở giai đoạn:
- chuẩn bị dữ liệu.

---

### `src/roi_tool.py`
Vai trò:
- công cụ OpenCV tương tác để vẽ polygon ROI.

Class chính:
- `ROISelector`

Phương thức chính:
- `mouse_callback(...)`: nhận click chuột.
- `_redraw()`: vẽ lại toàn bộ giao diện chọn ROI.
- `finish_current_roi()`: chốt polygon hiện tại.
- `toggle_mode()`: chuyển giữa `worker` và `buffer`.
- `undo_point()`: xóa điểm cuối.
- `reset_all()`: reset toàn bộ ROI.
- `to_json(camera_id, video_path)`: xuất cấu hình ROI.

Hàm chạy:
- `run_roi_tool(...)`

Đầu ra:
- file `configs/roi_cam01.json`.

---

### `src/crop_roi.py`
Vai trò:
- cắt các vùng `buffer_roi` từ frame để tạo dữ liệu cho classification.

Hàm chính:
- `crop_polygon_region(frame, points)`: mask polygon rồi crop theo bounding rect.
- `save_roi_crops(frames_dir, roi_config_path, output_dir)`: chạy cắt trên toàn bộ frame.

Đầu vào:
- frame đã trích,
- ROI config.

Đầu ra:
- crop ảnh theo từng `buffer_roi` trong `assets/roi_crops/<roi_id>/`.

Được dùng ở giai đoạn:
- chuẩn bị dataset phân loại trạng thái vùng chứa.

---

### `src/train_person.py`
Vai trò:
- train YOLO detection model cho class `person`.

Hàm chính:
- `train_person(...)`

Đầu vào:
- `datasets/person/data.yaml`
- ảnh và nhãn YOLO format.

Đầu ra:
- thư mục run trong `models/person/`
- cố gắng copy `best.pt` thành `models/person/best_person.pt`

Được dùng ở giai đoạn:
- huấn luyện mô hình nhận diện người.

---

### `src/train_roi_cls.py`
Vai trò:
- train YOLO classification model cho trạng thái ROI.

Hàm chính:
- `train_roi_classifier(...)`

Đầu vào:
- `datasets/roi_state/` với cấu trúc phân lớp thư mục.

Đầu ra:
- thư mục run trong `models/roi_state/`
- cố gắng copy `best.pt` thành `models/roi_state/best_roi_cls.pt`

Được dùng ở giai đoạn:
- huấn luyện mô hình classification vùng chứa.

---

### `src/tracker_utils.py`
Vai trò:
- xử lý hình học ROI và làm mượt trạng thái.

Hàm chính:
- `point_in_polygon(point, polygon)`: kiểm tra điểm có trong polygon.
- `bbox_center(x1, y1, x2, y2)`: lấy tâm bbox.
- `is_bbox_in_roi(bbox, roi_points)`: kiểm tra tâm bbox có nằm trong ROI.
- `filter_persons_in_roi(...)`: lọc danh sách track ID nằm trong ROI.

Class chính:
- `StateSmoother(window_size=10)`: majority vote cho classification state.
- `PresenceTracker(grace_frames=3)`: chống flicker cho trạng thái có/người vắng.

Được gọi lại bởi:
- `infer_demo.py`

---

### `src/rule_engine.py`
Vai trò:
- quản lý state machine cho cảnh báo.

Class chính:
- `WorkerAbsenceRule`
- `BacklogRule`

#### `WorkerAbsenceRule`
Dùng để:
- theo dõi worker ROI có người hay không,
- đếm thời gian vắng mặt,
- phát event khi vượt ngưỡng,
- phát event khi người quay lại.

Luồng trạng thái:
- `NORMAL`
- `COUNTING`
- `ALERT`

#### `BacklogRule`
Dùng để:
- theo dõi state ổn định của buffer ROI,
- đếm thời gian ở trạng thái trigger (`full`, `overload`),
- phát event khi vượt ngưỡng,
- phát event khi trở lại bình thường.

Được gọi lại bởi:
- `infer_demo.py`

---

### `src/draw_utils.py`
Vai trò:
- vẽ overlay lên video output.

Hàm chính:
- `draw_polygon(...)`
- `draw_person_bbox(...)`
- `draw_roi_state(...)`
- `draw_timer(...)`
- `draw_alert_banner(...)`
- `draw_info_panel(...)`

Được gọi lại bởi:
- `infer_demo.py`

---

### `src/event_logger.py`
Vai trò:
- ghi sự kiện ra CSV.

Class chính:
- `EventLogger`

Phương thức:
- `log_event(...)`: ghi event hoàn chỉnh.
- `log_start(...)`: ghi event start chưa có thời điểm kết thúc.

Được gọi lại bởi:
- `infer_demo.py`

Ghi chú:
- hiện tại pipeline chủ yếu dùng `log_event(...)`.

---

### `src/infer_demo.py`
Vai trò:
- entry point suy luận tổng.
- đây là file ghép tất cả module còn lại thành pipeline hoàn chỉnh.

Hàm chính:
- `crop_polygon_region_for_cls(frame, points)`: crop vùng buffer để classify.
- `run_pipeline(...)`: chạy toàn bộ quy trình inference.

Các bước trong `run_pipeline(...)`:
1. load ROI config + rules + runtime,
2. resolve device `auto/GPU/CPU`,
3. load 2 model YOLO,
4. mở video,
5. khởi tạo logger, tracker, rule engine,
6. detect + track người từng frame,
7. xác định người có trong worker ROI hay không,
8. classify buffer ROI,
9. smoothing state,
10. phát hiện event,
11. lưu snapshot,
12. vẽ overlay,
13. ghi output video,
14. ghi log CSV,
15. in tiến độ và tổng kết.

## 3. Call graph quan trọng

### Chuẩn bị dữ liệu detection người
`extract_frames.py`
-> sinh frame
-> người dùng gán nhãn YOLO thủ công
-> `train_person.py`
-> `models/person/best_person.pt`

### Chuẩn bị dữ liệu classification buffer
`extract_frames.py`
-> `roi_tool.py`
-> `crop_roi.py`
-> người dùng phân loại thủ công vào `empty/normal/full/overload`
-> `train_roi_cls.py`
-> `models/roi_state/best_roi_cls.pt`

### Suy luận end-to-end
`infer_demo.py`
-> `config_utils.py`
-> `tracker_utils.py`
-> `rule_engine.py`
-> `draw_utils.py`
-> `event_logger.py`
-> output video + log + snapshot

## 4. Các file cấu hình

### `configs/roi_cam01.json`
Chứa:
- `camera_id`
- `video_path`
- `worker_rois`
- `buffer_rois`

### `configs/rules.yaml`
Chứa:
- ngưỡng vắng mặt công nhân,
- số frame grace,
- ngưỡng tồn hàng,
- trigger states.

### `configs/runtime.yaml`
Chứa:
- FPS xử lý,
- image size detect/classify,
- confidence,
- smoothing window,
- tracker config,
- đường dẫn model mặc định,
- output options.

### `configs/class_names.yaml`
Chứa:
- mapping class detection và classification.

## 5. Điểm cần nhớ khi đọc repo

- Đây là repo theo hướng pipeline script-based, chưa tách package lớn.
- `infer_demo.py` là file quan trọng nhất để hiểu toàn bộ hệ thống.
- `rule_engine.py` là nơi định nghĩa “nghiệp vụ cảnh báo”.
- `tracker_utils.py` chỉ xử lý ROI geometry và smoothing, không chứa crop cho classification.
- `crop_roi.py` và `roi_tool.py` là phần phục vụ xây dataset, không phải runtime production.
