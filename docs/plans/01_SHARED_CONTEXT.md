# Shared Context

## 1. Mục tiêu thực tế của repo hiện tại

Repo hiện tại đang hiện thực một POC giám sát dây chuyền theo hướng computer vision.

Phần mã nguồn đang bám theo 2 bài toán chính:
1. phát hiện công nhân có còn đứng trong vùng làm việc hay không,
2. phân loại trạng thái vùng chứa/buffer (`empty`, `normal`, `full`, `overload`) để cảnh báo tồn hàng.

## 2. Repo đang làm gì ở mức kỹ thuật

Pipeline hiện tại trong code là:

1. đọc video đầu vào,
2. detect người bằng YOLO,
3. track người bằng tracker của Ultralytics,
4. kiểm tra bbox center có nằm trong `worker_roi` hay không,
5. crop vùng `buffer_roi`,
6. classify trạng thái vùng chứa,
7. làm mượt kết quả classification bằng majority vote,
8. chạy rule engine để sinh cảnh báo,
9. ghi log CSV, snapshot và video output có overlay.

## 3. Repo chưa làm gì

Repo hiện tại **chưa** làm các phần sau ở mức mã nguồn thực thi:

- chưa đọc RTSP thực tế từ camera IP,
- chưa gửi thông báo qua Zalo / Telegram / webhook,
- chưa đếm sản phẩm theo từng object ID,
- chưa có luồng detect sản phẩm + track sản phẩm + counting logic,
- chưa có module triển khai đa camera,
- chưa có benchmark chính thức về tốc độ, độ chính xác, độ trễ,
- chưa có script evaluation hoàn chỉnh cho mô hình.

## 4. Độ khớp giữa repo và hướng đề tài

Theo tài liệu đề tài, hướng mong muốn là kiến trúc 4 tầng: Thu thập → Nhận diện → Phân tích → Phản hồi, có nhắc đến RTSP, product detection, tracking, counting logic và alert; đồng thời phần cải tiến về sau có cảnh báo khi nhân viên rời vị trí quá lâu. fileciteturn0file0

Đối chiếu với mã nguồn hiện tại:

### Phần đã khớp
- Có pipeline theo kiểu end-to-end từ video đến cảnh báo.
- Có phần worker absence alert.
- Có phần backlog alert qua phân loại trạng thái vùng chứa.
- Có ROI, tracker, event log, output video.

### Phần mới chỉ là thay thế gần đúng
- Thay vì đếm trực tiếp sản phẩm theo từng object, repo đang phân loại cả vùng buffer thành trạng thái `empty/normal/full/overload`.
- Đây là một hướng POC hợp lý để ra kết quả sớm, nhưng chưa phải product counting đúng nghĩa.

### Phần còn thiếu so với đích cuối
- RTSP input.
- Notification API.
- Product detection/tracking/counting.
- Hạ tầng triển khai thực tế nhiều camera.

## 5. Tình trạng dữ liệu và tài nguyên trong repo

Quan sát trực tiếp cấu trúc thư mục cho thấy:

### Đã có
- `datasets/person/data.yaml`
- cấu trúc thư mục dự án đầy đủ
- các file cấu hình `configs/*.yaml`, `configs/*.json`

### Chưa có hoặc đang trống
- `assets/videos/`
- `assets/frames_person/`
- `assets/roi_crops/`
- `datasets/roi_state/`
- ảnh và label cho `datasets/person/`
- weights trong `models/person/` và `models/roi_state/`
- output thực nghiệm trong `outputs/videos/`, `outputs/logs/`

Kết luận: repo hiện tại là **khung pipeline + công cụ chuẩn bị dữ liệu + script train/infer**, chưa phải repo đã có dữ liệu và model hoàn chỉnh.

## 6. Điểm nghẽn kỹ thuật đã xác định

### Lỗi 1 — `infer_demo.py` import sai
`src/infer_demo.py` đang import:

```python
from tracker_utils import (
    is_bbox_in_roi, bbox_center, crop_polygon_region,
    StateSmoother, PresenceTracker, filter_persons_in_roi,
)
```

Nhưng `src/tracker_utils.py` không có hàm `crop_polygon_region`.

Hệ quả:
- file `infer_demo.py` có thể compile,
- nhưng khi import/chạy thực tế sẽ lỗi `ImportError` ngay từ đầu.

### Lỗi 2 — có dấu hiệu dư thừa thiết kế
Trong `infer_demo.py` đã tự định nghĩa hàm `crop_polygon_region_for_cls()`, nên import `crop_polygon_region` từ `tracker_utils` là thừa và sai.

### Lỗi 3 — tài liệu và code chưa thống nhất hoàn toàn
README và ý tưởng đề tài có xu hướng nói về hệ thống hoàn chỉnh hơn mức mã nguồn hiện tại. Cần luôn phân biệt:
- `ý tưởng/đích cuối`,
- `mức đã có trong code`.

## 7. Cách hiểu đúng về trạng thái dự án hiện tại

Phải xem repo này là:

> Một POC trung gian để chứng minh được cảnh báo vắng mặt công nhân và cảnh báo tồn hàng theo ROI state classification.

Không nên xem repo này là hệ thống hoàn chỉnh cho bài toán đếm sản phẩm ngoài nhà máy.

## 8. Định nghĩa “xong” cho giai đoạn hiện tại

Giai đoạn hiện tại chỉ được coi là xong khi đạt đủ:

- có ít nhất 1 video thật trong `assets/videos/`,
- có ROI config đúng,
- có dataset person detection,
- có dataset ROI state classification,
- train được 2 model cơ bản,
- sửa lỗi import của `infer_demo.py`,
- chạy được pipeline từ video đầu vào đến video output + log CSV,
- sinh được tối thiểu 1 event `worker_absence` hoặc `backlog_alert` trên dữ liệu thử nghiệm.

## 9. Định nghĩa “xong” cho giai đoạn mở rộng

Giai đoạn mở rộng chỉ được coi là xong khi có thêm:

- RTSP input,
- notification API,
- product detection/tracking/counting,
- cấu hình đa camera,
- benchmark hiệu năng,
- tài liệu triển khai thực tế.
