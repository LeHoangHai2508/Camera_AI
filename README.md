# AI Camera

Hệ thống AI Camera dùng để:
- giám sát vị trí công nhân trong vùng làm việc,
- phân loại trạng thái vùng chứa hàng theo ROI,
- sinh log sự kiện và chuẩn bị tích hợp cảnh báo.

README này được viết theo **đúng cấu trúc thư mục hiện tại** của dự án.

---

## 1. Cấu trúc thư mục

```text
.
├── app.py
├── configs/
│   ├── notify.yaml
│   ├── roi_cam01.json
│   ├── roi_cam02.json
│   ├── roi_cam03.json
│   ├── rules.yaml
│   ├── runtime.yaml
│   ├── zalo_service.yaml
│   └── zbs_service.yaml
├── datasets/
├── models/
├── outputs/
├── assets/
│   ├── videos/
│   ├── frames_person/
│   ├── roi_crops/
│   └── snapshots/
├── requirements.txt
└── src/
    ├── __init__.py
    ├── core/
    │   ├── __init__.py
    │   ├── cli/
    │   │   └── infer_demo.py
    │   ├── rule_engine.py
    │   └── video_source.py
    ├── gui/
    ├── service/
    │   ├── notifier.py
    │   ├── service_zalo.py
    │   └── service_zbs.py
    ├── tools/
    │   ├── crop_roi.py
    │   └── roi_tool.py
    ├── training/
    │   ├── extract_frames.py
    │   ├── tracker_utils.py
    │   └── train_person.py
    └── utils/
        ├── common.py
        ├── config_utils.py
        ├── draw_utils.py
        ├── event_logger.py
        └── train_roi_cls.py
```

---

## 2. Chức năng từng nhóm thư mục

### `src/core/`
Chứa phần lõi của pipeline suy luận:
- `cli/infer_demo.py`: điểm chạy inference từ dòng lệnh.
- `rule_engine.py`: luật phát hiện vắng người / backlog.
- `video_source.py`: đọc video file hoặc luồng camera.

### `src/tools/`
Công cụ chuẩn bị dữ liệu ROI:
- `roi_tool.py`: chọn ROI thủ công trên ảnh hoặc frame.
- `crop_roi.py`: cắt vùng ROI để tạo dữ liệu classification.

### `src/training/`
Công cụ chuẩn bị dữ liệu và train detection:
- `extract_frames.py`: tách frame từ video.
- `train_person.py`: train model phát hiện người.
- `tracker_utils.py`: hỗ trợ tracking và xử lý logic hình học.

### `src/utils/`
Các module hỗ trợ dùng chung:
- `common.py`: hằng số và hàm tiện ích.
- `config_utils.py`: đọc YAML / JSON config.
- `draw_utils.py`: vẽ overlay.
- `event_logger.py`: ghi log sự kiện.
- `train_roi_cls.py`: train model classification trạng thái ROI.

### `src/service/`
Tích hợp cảnh báo:
- `notifier.py`: dispatcher gửi cảnh báo.
- `service_zalo.py`: tích hợp Zalo.
- `service_zbs.py`: tích hợp ZBS.

### `src/gui/`
Dành cho giao diện Tkinter. Thư mục này là nơi phát triển giao diện, chưa phải luồng chạy chính nếu chưa hoàn thiện.

### `app.py`
File entry cho giao diện Tkinter.

---

## 3. Yêu cầu môi trường

### Khuyến nghị
- Windows 10/11
- Python **3.10+**
- GPU NVIDIA nếu muốn chạy inference/train nhanh

### Lưu ý về Python 3.9
Với mã hiện tại, nên dùng **Python 3.10+** để tránh lỗi cú pháp kiểu dữ liệu hiện đại trong `train_roi_cls.py`.

Nếu bắt buộc dùng Python 3.9, cần sửa code trước rồi mới chạy ổn định.

---

## 4. Tạo môi trường ảo và cài thư viện

### PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Nếu dùng GPU NVIDIA
Cài PyTorch đúng theo phiên bản CUDA trên máy trước, sau đó cài phần còn lại:

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements.txt
```

Nếu máy không có GPU, hệ thống có thể chạy CPU nhưng sẽ chậm hơn.

---

## 5. Chuẩn bị dữ liệu đầu vào

Cấu trúc tối thiểu nên có:

```text
assets/
├── videos/
│   ├── cam01_video1.mp4
│   ├── cam02_video2.mp4
│   └── cam03_video3.mp4
├── frames_person/
├── roi_crops/
└── snapshots/

datasets/
├── person/
└── roi_state/

models/
├── person/
└── roi_state/

outputs/
├── videos/
├── logs/
└── snapshots/
```

Tạo thư mục nếu chưa có:

```powershell
mkdir assets\videos -Force
mkdir assets\frames_person -Force
mkdir assets\roi_crops -Force
mkdir outputs\videos -Force
mkdir outputs\logs -Force
mkdir outputs\snapshots -Force
mkdir models\person -Force
mkdir models\roi_state -Force
```

---

## 6. Quy trình chạy dự án

## Bước 1. Tách frame từ video

```powershell
python src\training\extract_frames.py --video assets\videos\cam01_video1.mp4 --output_dir assets\frames_person --interval_sec 1.0
```

Ý nghĩa:
- `--video`: video nguồn
- `--output_dir`: thư mục lưu frame
- `--interval_sec`: mỗi bao nhiêu giây lấy 1 frame

---

## Bước 2. Chọn ROI

```powershell
python src\tools\roi_tool.py --frame assets\frames_person\cam01_video1_000000_0.0s.jpg --output configs\roi_cam01.json --camera_id cam01
```

Nếu công cụ hỗ trợ đọc từ video trực tiếp, có thể dùng thêm `--video_path` theo logic code hiện tại.

### Phím thao tác thường dùng
- Chuột trái: thêm điểm polygon
- `n`: kết thúc ROI hiện tại
- `m`: đổi mode worker / buffer
- `u`: xóa điểm cuối
- `r`: reset toàn bộ
- `s`: lưu và thoát

---

## Bước 3. Cắt crop ROI để tạo dữ liệu classification

```powershell
python src\tools\crop_roi.py --frames_dir assets\frames_person --roi_config configs\roi_cam01.json --output_dir assets\roi_crops
```

Sau đó chia crop vào các class:
- `empty`
- `normal`
- `full`
- `overload`

Cấu trúc dataset classification:

```text
datasets/roi_state/
├── train/
│   ├── empty/
│   ├── normal/
│   ├── full/
│   └── overload/
├── val/
│   ├── empty/
│   ├── normal/
│   ├── full/
│   └── overload/
└── test/
    ├── empty/
    ├── normal/
    ├── full/
    └── overload/
```

---

## Bước 4. Gán nhãn detection người

Chuẩn bị dataset detection theo YOLO format:

```text
datasets/person/
├── images/
│   ├── train/
│   ├── val/
│   └── test/
├── labels/
│   ├── train/
│   ├── val/
│   └── test/
└── data.yaml
```

Dùng LabelImg hoặc CVAT để gán nhãn class `person`.

Ví dụ `data.yaml`:

```yaml
path: datasets/person
train: images/train
val: images/val
test: images/test
names:
  0: person
```

---

## Bước 5. Train model detection người

```powershell
python src\training\train_person.py --data datasets\person\data.yaml --model yolov8n.pt --epochs 50 --imgsz 640 --batch 8 --device 0 --project models\person --name train
```

Nếu chạy CPU:

```powershell
python src\training\train_person.py --data datasets\person\data.yaml --model yolov8n.pt --epochs 50 --imgsz 640 --batch 8 --device cpu --project models\person --name train_cpu
```

Model tốt nhất thường nằm tại:

```text
models/person/train/weights/best.pt
```

Có thể đổi tên hoặc copy thành:

```text
models/person/best_person.pt
```

---

## Bước 6. Train model classification ROI

```powershell
python src\utils\train_roi_cls.py --data datasets\roi_state --model yolo26n-cls.pt --epochs 50 --imgsz 224 --batch 16 --device 0 --project models\roi_state --name train
```

Nếu chạy CPU:

```powershell
python src\utils\train_roi_cls.py --data datasets\roi_state --model yolo26n-cls.pt --epochs 50 --imgsz 224 --batch 16 --device cpu --project models\roi_state --name train_cpu
```

Model tốt nhất thường nằm tại:

```text
models/roi_state/train/weights/best.pt
```

Có thể đổi tên hoặc copy thành:

```text
models/roi_state/best_roi_cls.pt
```

---

## Bước 7. Chạy inference từ CLI

### Chạy trên video file

```powershell
python src\core\cli\infer_demo.py --video assets\videos\cam01_video1.mp4 --roi configs\roi_cam01.json --rules configs\rules.yaml --runtime configs\runtime.yaml --notify configs\notify.yaml --person_model models\person\best_person.pt --roi_cls_model models\roi_state\best_roi_cls.pt --output outputs\videos\cam01_demo.mp4 --device 0 --preview
```

### Chạy không preview, chỉ xuất file

```powershell
python src\core\cli\infer_demo.py --video assets\videos\cam01_video1.mp4 --roi configs\roi_cam01.json --rules configs\rules.yaml --runtime configs\runtime.yaml --notify configs\notify.yaml --person_model models\person\best_person.pt --roi_cls_model models\roi_state\best_roi_cls.pt --output outputs\videos\cam01_demo_clean.mp4 --device 0
```

### Chạy CPU

```powershell
python src\core\cli\infer_demo.py --video assets\videos\cam01_video1.mp4 --roi configs\roi_cam01.json --rules configs\rules.yaml --runtime configs\runtime.yaml --notify configs\notify.yaml --person_model models\person\best_person.pt --roi_cls_model models\roi_state\best_roi_cls.pt --output outputs\videos\cam01_demo_cpu.mp4 --device cpu
```

---

## Bước 8. Chạy giao diện Tkinter

Nếu `app.py` đã được nối đúng với `src/gui/`, lệnh chạy sẽ là:

```powershell
python app.py
```

Phần này phụ thuộc vào mã thực tế trong `app.py`. Nếu `app.py` chưa gọi GUI main loop hoặc chưa nối sang pipeline inference thì lệnh trên chỉ là entry dự kiến.

---ư

## 7. File cấu hình cần có

## `configs/rules.yaml`
Ví dụ:

```yaml
worker_absence:
  threshold_sec: 15

backlog_alert:
  threshold_sec: 20
  trigger_states: [full, overload]
```

## `configs/runtime.yaml`
Ví dụ:

```yaml
process_fps: 5
imgsz_detect: 640
imgsz_classify: 224
confidence_detect: 0.25
confidence_classify: 0.25
smoothing_window: 5
```

## `configs/notify.yaml`
Ví dụ tối thiểu:

```yaml
enabled: false
save_snapshot: true
cooldown_sec: 30
```

---

## 8. Đầu ra sau khi chạy inference

```text
outputs/
├── videos/
│   └── cam01_demo.mp4
├── logs/
│   └── cam01_video1_events.csv
└── snapshots/
    └── cam01_video1/
```

Ý nghĩa:
- `videos/`: video đã vẽ overlay
- `logs/`: log sự kiện theo thời gian
- `snapshots/`: ảnh chụp lúc phát sinh cảnh báo

---

## 9. Lệnh chạy nhanh theo đúng thứ tự

### Luồng chuẩn tối thiểu

```powershell
# 1) tạo môi trường
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2) tách frame
python src\training\extract_frames.py --video assets\videos\cam01_video1.mp4 --output_dir assets\frames_person --interval_sec 1.0

# 3) chọn ROI
python src\tools\roi_tool.py --frame assets\frames_person\cam01_video1_000000_0.0s.jpg --output configs\roi_cam01.json --camera_id cam01

# 4) crop ROI
python src\tools\crop_roi.py --frames_dir assets\frames_person --roi_config configs\roi_cam01.json --output_dir assets\roi_crops

# 5) train person
python src\training\train_person.py --data datasets\person\data.yaml --model yolov8n.pt --epochs 50 --imgsz 640 --batch 8 --device 0 --project models\person --name train

# 6) train ROI classification
python src\utils\train_roi_cls.py --data datasets\roi_state --model yolo26n-cls.pt --epochs 50 --imgsz 224 --batch 16 --device 0 --project models\roi_state --name train

# 7) chạy inference
python src\core\cli\infer_demo.py --video assets\videos\cam01_video1.mp4 --roi configs\roi_cam01.json --rules configs\rules.yaml --runtime configs\runtime.yaml --notify configs\notify.yaml --person_model models\person\best_person.pt --roi_cls_model models\roi_state\best_roi_cls.pt --output outputs\videos\cam01_demo.mp4 --device 0 --preview
```

---

## 10. Các lỗi thường gặp

### Lỗi import do đổi cấu trúc thư mục
Khi đã chuyển file sang thư mục mới, các import cũ kiểu:

```python
from common import ...
```

có thể phải đổi thành import theo package, ví dụ:

```python
from src.utils.common import ...
```

hoặc chạy bằng module:

```powershell
python -m src.core.cli.infer_demo ...
```

### Lỗi không thấy model
Kiểm tra đúng đường dẫn:
- `models\person\best_person.pt`
- `models\roi_state\best_roi_cls.pt`

### Lỗi không thấy video
Kiểm tra đúng file trong:
- `assets\videos\`

### Lỗi preview không hiện
Thường do OpenCV GUI hoặc môi trường remote desktop.

### Lỗi device 0
Nếu máy không có GPU CUDA, đổi:

```powershell
--device cpu
```

---

## 11. Gợi ý chuẩn hóa tiếp theo

Khi bắt đầu hoàn thiện Tkinter, nên thống nhất:
- `app.py` chỉ làm entry GUI,
- `src/core/cli/infer_demo.py` chỉ dành cho chạy dòng lệnh,
- toàn bộ logic dùng chung nên đặt ở `src/core/` để GUI và CLI cùng gọi lại.



Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass 


.\.venv_labelimg\Scripts\Activate.ps1   
   
py -3.9 src\infer_demo.py ^
  --video assets\videos\cam01_video1.mp4 ^
  --roi configs\roi_cam01.json ^
  --rules configs\rules.yaml ^
  --runtime configs\runtime.yaml ^
  --notify configs\notify.yaml ^
  --person_model models\person\best_person.pt ^
  --roi_cls_model models\roi_state\best_roi_cls.pt ^
  --output outputs\videos\cam01_notify_test.mp4 ^
  --device 0
python src\infer_demo.py --video assets\videos\cam01_video1.mp4 --roi configs\roi_cam01.json --rules configs\rules.yaml --runtime configs\runtime.yaml --person_model models\person\best_person.pt --roi_cls_model models\roi_state\best_roi_cls.pt --output outputs\videos\cam01_demo.mp4 --device 0 --preview



Chạy demo trên file output thẳng, không quay màn hình

Hiện video demo bạn gửi là video quay màn hình, không phải output sạch.

Bây giờ cần chạy lại để lấy file output trực tiếp từ pipeline:

python src\infer_demo.py --video assets\videos\cam04_video4.mp4 --roi configs\roi_cam04.json --rules configs\rules.yaml --runtime configs\runtime.yaml --person_model models\person\best_person.pt --roi_cls_model models\roi_state\best_roi_cls.pt --output outputs\videos\cam04_demo_clean.mp4 --device 0

Sau đó kiểm tra:

outputs\videos\cam01_demo_clean.mp4
outputs\logs\*_events.csv
outputs\snapshots\*

Đây mới là bộ đầu ra đúng để đánh giá kỹ.

python src\infer_demo.py --video dummy --roi configs\roi_cam01.json --rules configs\rules.yaml --runtime configs\runtime.yaml --notify configs\notify.yaml --person_model models\person\best_person.pt --roi_cls_model models\roi_state\best_roi_cls.pt --output outputs\videos\cam01_rtsp_demo.mp4 --device 0