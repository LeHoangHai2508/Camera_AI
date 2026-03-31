# Implementation Plan

## 1. Mục tiêu của kế hoạch này

Kế hoạch này không nhắm ngay đến hệ thống nhà máy hoàn chỉnh.
Kế hoạch này nhắm đến việc đưa repo hiện tại từ trạng thái “khung code” sang “POC chạy được, có kết quả kiểm chứng”.

## 2. Ưu tiên tổng

Thứ tự ưu tiên đúng là:
1. làm cho pipeline hiện tại chạy được,
2. có dữ liệu thật tối thiểu,
3. có model cơ bản,
4. có output kiểm chứng,
5. sau đó mới mở rộng RTSP, thông báo, product counting.

## 3. Giai đoạn A — Ổn định mã nguồn

### Mục tiêu
Loại bỏ lỗi chặn chạy.

### Việc phải làm
- [ ] sửa import sai trong `src/infer_demo.py`
- [ ] chạy test import từng file chính
- [ ] kiểm tra lại README với mã nguồn thực tế
- [ ] xác nhận lệnh chạy inference đúng với tên file hiện có

### Tiêu chí xong
- `python src/infer_demo.py --help` chạy được
- import `infer_demo.py` không lỗi

## 4. Giai đoạn B — Chuẩn bị dữ liệu tối thiểu

### Mục tiêu
Tạo bộ dữ liệu đủ để train bản POC.

### Việc phải làm
- [ ] đặt video thật vào `assets/videos/`
- [ ] dùng `extract_frames.py` để tách frame
- [ ] dùng `roi_tool.py` để tạo ROI config đúng video thực tế
- [ ] dùng `crop_roi.py` để cắt buffer ROI
- [ ] gán nhãn detection người cho frame
- [ ] phân loại crop vào `empty/normal/full/overload`
- [ ] chia train/val/test cho cả 2 bài toán

### Tiêu chí xong
- `datasets/person/` có đủ `images/` và `labels/`
- `datasets/roi_state/` có đủ `train/val/test`
- kiểm tra ngẫu nhiên dữ liệu không lỗi đường dẫn, không sai lớp

## 5. Giai đoạn C — Huấn luyện mô hình cơ bản

### Mục tiêu
Có 2 model baseline để chạy pipeline.

### Việc phải làm
- [ ] train person detection
- [ ] train ROI state classification
- [ ] lưu `best_person.pt`
- [ ] lưu `best_roi_cls.pt`
- [ ] ghi lại thông số train quan trọng: epochs, imgsz, batch, device
- [ ] chụp lại metric train/val để lưu trong `docs/`

### Tiêu chí xong
- có weights trong `models/person/` và `models/roi_state/`
- chạy predict thử trên vài ảnh thấy hợp lý

## 6. Giai đoạn D — Chạy POC end-to-end

### Mục tiêu
Chạy video đầu vào và sinh cảnh báo đúng logic.

### Việc phải làm
- [ ] chạy `infer_demo.py` trên ít nhất 1 video thật
- [ ] kiểm tra overlay ROI
- [ ] kiểm tra detection/tracking người
- [ ] kiểm tra classification state của buffer
- [ ] kiểm tra event CSV
- [ ] kiểm tra snapshot alert
- [ ] điều chỉnh `rules.yaml` và `runtime.yaml` nếu cần

### Tiêu chí xong
- có `outputs/videos/*.mp4`
- có `outputs/logs/*_events.csv`
- có snapshot khi xảy ra alert

## 7. Giai đoạn E — Tinh chỉnh để demo ổn định

### Mục tiêu
Giảm cảnh báo sai và làm video demo đủ thuyết phục.

### Việc phải làm
- [ ] chỉnh ROI chính xác hơn
- [ ] chỉnh threshold worker absence
- [ ] chỉnh threshold backlog
- [ ] chỉnh `process_fps`
- [ ] chỉnh `smoothing_window`
- [ ] thêm dữ liệu cho tình huống ánh sáng xấu / che khuất
- [ ] kiểm tra các trường hợp false positive / false negative

### Tiêu chí xong
- video demo ít nhiễu
- event log bám khá sát thực tế quan sát thủ công

## 8. Giai đoạn F — Mở rộng theo đề tài

### Mục tiêu
Tiến từ POC sang hướng gần hơn với đề tài gốc.

### Việc phải làm
- [ ] chuyển input từ file video sang RTSP
- [ ] bổ sung notification API
- [ ] thiết kế product detection/tracking/counting
- [ ] chuẩn hóa cấu hình đa camera
- [ ] bổ sung benchmark FPS / latency
- [ ] xem xét export TensorRT / OpenVINO

### Tiêu chí xong
- có thể chạy gần thời gian thực trên môi trường triển khai mục tiêu

## 9. Kế hoạch thực thi ngắn hạn đề xuất

### Sprint 1
Mục tiêu: repo chạy được ở mức import và command line.
- sửa lỗi import
- kiểm tra command
- chuẩn hóa docs

### Sprint 2
Mục tiêu: tạo dữ liệu thật đầu tiên.
- thêm video
- tách frame
- tạo ROI
- crop ROI
- gán nhãn sơ bộ

### Sprint 3
Mục tiêu: train baseline.
- train detection người
- train classification buffer
- lưu weights

### Sprint 4
Mục tiêu: chạy demo end-to-end.
- infer video
- kiểm tra log
- chỉnh threshold

## 10. Những gì chưa nên làm ngay

Không nên ưu tiên ngay các phần sau khi repo hiện tại còn chưa chạy hết vòng cơ bản:
- microservice hóa,
- UI dashboard,
- multi-camera production,
- RTSP ở quy mô lớn,
- tối ưu TensorRT,
- product counting đầy đủ.

Lý do:
- hiện chưa có baseline chạy ổn định để đo.
- nếu mở rộng quá sớm sẽ khó biết lỗi nằm ở dữ liệu, model hay hạ tầng.
