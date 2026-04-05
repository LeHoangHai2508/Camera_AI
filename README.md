# AI Camera — Hệ thống giám sát vị trí công nhân & trạng thái tồn hàng

Hệ thống AI Camera kiến trúc 4 tầng: **Thu thập → Nhận diện → Phân tích → Phản hồi**.  
Sử dụng **YOLO26n/s** cho detection & classification, **ByteTrack** cho tracking, **Rule Engine** cho cảnh báo.

## Cấu trúc dự án

```
ai_camera_project/
├── assets/               # Video, frames, ROI crops, snapshots
├── configs/              # ROI, rules, runtime configs
├── datasets/             # Person detection + ROI classification datasets
├── models/               # Trained model weights
├── outputs/              # Output videos, logs, metrics
├── src/                  # Source code (xem bên dưới)
├── requirements.txt
└── README.md
```

### Source modules (`src/`)

| File | Mô tả |
|------|--------|
| `common.py` | Constants, colors, helpers |
| `config_utils.py` | Load ROI / rules / runtime configs |
| `extract_frames.py` | Trích frame từ video |
| `roi_tool.py` | Công cụ chọn ROI tương tác |
| `crop_roi.py` | Cắt vùng buffer ROI cho classification |
| `train_person.py` | Train YOLO26 person detection |
| `train_roi_cls.py` | Train YOLO26-cls ROI state classification |
| `tracker_utils.py` | Geometry, smoothing, presence tracking |
| `rule_engine.py` | State machines: worker absence & backlog alerts |
| `draw_utils.py` | Overlay rendering |
| `event_logger.py` | CSV event logging |
| `infer_demo.py` | **Pipeline suy luận tổng** |

---

## Cài đặt

```bash
# 1. Cài PyTorch với CUDA (khuyến nghị cho GPU NVIDIA)
# Truy cập https://pytorch.org/get-started/locally/ để chọn đúng phiên bản CUDA
# Ví dụ cho CUDA 12.6:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126

# 2. Cài các dependencies còn lại
pip install -r requirements.txt
```

Yêu cầu: Python 3.10+, PyTorch với CUDA (GPU NVIDIA).

> **Lưu ý:** Nếu không có GPU, hệ thống sẽ tự động fallback về CPU nhưng tốc độ sẽ chậm hơn đáng kể.

---
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass 


.\.venv_labelimg\Scripts\Activate.ps1      


## Quy trình sử dụng

### 1. Trích frame từ video

```bash
python src/extract_frames.py --video assets/videos/video1.mp4 \
                              --output_dir assets/frames_person \
                              --interval_sec 1.0
```

### 2. Chọn ROI

```bash
python src/roi_tool.py --frame assets/frames_person/video1_000000_0.0s.jpg \
                        --output configs/roi_cam01.json \
                        --camera_id cam01
```

**Phím tắt:**
- Click chuột → thêm điểm polygon
- `n` → hoàn thành ROI hiện tại, bắt đầu ROI mới
- `m` → chuyển mode (worker ↔ buffer)
- `u` → undo điểm cuối
- `s` → lưu JSON và thoát
- `r` → reset tất cả

### 3. Cắt ROI crops cho classification

```bash
python src/crop_roi.py --frames_dir assets/frames_person \
                        --roi_config configs/roi_cam01.json \
                        --output_dir assets/roi_crops
```

Sau đó phân loại thủ công các crop vào thư mục `empty/normal/full/overload`.

### 4. Gán nhãn person detection

Dùng tool gán nhãn (ví dụ: [LabelImg](https://github.com/HumanSignal/labelImg), [CVAT](https://cvat.ai/)) để gán bbox cho class `person`, lưu label YOLO format vào `datasets/person/labels/`.

### 5. Train person detection

```bash
python src/train_person.py --data datasets/person/data.yaml \
                            --model yolo26n.pt \
                            --epochs 50 --imgsz 640 \
                            --batch 8 --device 0
```

### 6. Train ROI state classification

```bash
python src/train_roi_cls.py --data datasets/roi_state \
                             --model yolo26n-cls.pt \
                             --epochs 50 --imgsz 224 \
                             --batch 16 --device 0
```

### 7. Chạy inference đầy đủ

```bash
# GPU tự động (mặc định: dùng GPU nếu có, fallback CPU)
python src/infer_demo.py \
    --video assets/videos/video1.mp4 \
    --roi configs/roi_cam01.json \
    --rules configs/rules.yaml \
    --person_model models/person/best_person.pt \
    --roi_cls_model models/roi_state/best_roi_cls.pt \
    --output outputs/videos/demo_output.mp4 \
    --preview

# Chỉ định GPU cụ thể
python src/infer_demo.py \
    --video assets/videos/video1.mp4 \
    --roi configs/roi_cam01.json \
    --rules configs/rules.yaml \
    --person_model models/person/best_person.pt \
    --roi_cls_model models/roi_state/best_roi_cls.pt \
    --output outputs/videos/demo_output.mp4 \
    --device 0   # GPU 0
```

**Đầu ra:**
- `outputs/videos/demo_output.mp4` — video có overlay
- `outputs/logs/{video}_events.csv` — log sự kiện
- `outputs/snapshots/{video}/` — ảnh snapshot khi có alert

---

## Cấu hình

### ROI (`configs/roi_cam01.json`)
Polygon points cho worker và buffer ROI. Dùng `roi_tool.py` để tạo tương tác.

### Rules (`configs/rules.yaml`)
- `worker_absence.threshold_sec`: ngưỡng vắng mặt (mặc định 15s)
- `backlog_alert.threshold_sec`: ngưỡng tồn hàng (mặc định 20s)
- `backlog_alert.trigger_states`: trạng thái kích hoạt (`full`, `overload`)

### Runtime (`configs/runtime.yaml`)
- `process_fps`: FPS xử lý (mặc định 5)
- `imgsz_detect/classify`: kích thước ảnh đầu vào
- `confidence_detect/classify`: ngưỡng confidence
- `smoothing_window`: số frame cho majority vote

---

## Luật cảnh báo

### Worker Absence
Khi không có người trong `worker_roi` liên tục > `T_absent` giây → sinh event `worker_absence_start`. Khi người quay lại → sinh event `worker_absence_end`.

### Backlog Alert
Khi trạng thái buffer ROI ở `full/overload` liên tục > `T_backlog` giây → sinh event `backlog_alert_start`. Khi quay về `normal/empty` → sinh event `backlog_alert_end`.

---

## Hướng mở rộng

1. **RTSP** — đổi input sang camera IP RTSP stream
2. **Notification** — Telegram Bot / Zalo OA webhook
3. **Multi-camera** — nhiều ROI config, nhiều camera ID
4. **Product counting** — detect + track sản phẩm trong khay
5. **Tối ưu** — export TensorRT (GPU) để tăng tốc inference
6. **Multi-GPU** — hỗ trợ chạy trên nhiều GPU



python src\infer_demo.py --video assets\videos\cam01_video1.mp4 --roi configs\roi_cam01.json --rules configs\rules.yaml --runtime configs\runtime.yaml --person_model models\person\best_person.pt --roi_cls_model models\roi_state\best_roi_cls.pt --output outputs\videos\cam01_demo.mp4 --device 0 --preview



Chạy demo trên file output thẳng, không quay màn hình

Hiện video demo bạn gửi là video quay màn hình, không phải output sạch.

Bây giờ cần chạy lại để lấy file output trực tiếp từ pipeline:

python src\infer_demo.py --video assets\videos\cam01_video1.mp4 --roi configs\roi_cam01.json --rules configs\rules.yaml --runtime configs\runtime.yaml --person_model models\person\best_person.pt --roi_cls_model models\roi_state\best_roi_cls.pt --output outputs\videos\cam01_demo_clean.mp4 --device 0

Sau đó kiểm tra:

outputs\videos\cam01_demo_clean.mp4
outputs\logs\*_events.csv
outputs\snapshots\*

Đây mới là bộ đầu ra đúng để đánh giá kỹ.

python src\infer_demo.py --video dummy --roi configs\roi_cam01.json --rules configs\rules.yaml --runtime configs\runtime.yaml --notify configs\notify.yaml --person_model models\person\best_person.pt --roi_cls_model models\roi_state\best_roi_cls.pt --output outputs\videos\cam01_rtsp_demo.mp4 --device 0