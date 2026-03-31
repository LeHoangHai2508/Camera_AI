# Working Protocol

## 1. Mục đích

File này dùng để giữ sự thống nhất ngữ cảnh giữa người làm dự án và trợ lý ở các phiên làm việc sau.

## 2. Quy ước làm việc

Mỗi khi bắt đầu một phiên làm việc mới, phải xác định rõ 4 câu:

1. trạng thái repo hiện tại là gì,
2. mục tiêu của phiên này là gì,
3. đầu ra cụ thể cần tạo là gì,
4. file nào sẽ bị tác động.

## 3. Mẫu cập nhật sau mỗi phiên

Sau khi kết thúc một phiên làm việc, cập nhật ngắn vào cuối file này theo mẫu:

```md
## Session YYYY-MM-DD
- Mục tiêu:
- Đã làm:
- File đã sửa:
- Kết quả tạo ra:
- Lỗi phát hiện:
- Bước tiếp theo:
```

## 4. Quy tắc khi thay đổi code

Nếu có thay đổi thuộc một trong các nhóm sau, bắt buộc cập nhật `01_SHARED_CONTEXT.md` hoặc `03_IMPLEMENTATION_PLAN.md`:

- đổi kiến trúc pipeline,
- thêm/xóa module trong `src/`,
- đổi format dữ liệu,
- đổi ROI/rule/runtime logic,
- đổi mục tiêu đề tài thực tế,
- chuyển từ POC sang production-like pipeline.

## 5. Quy tắc khi hỏi trợ lý

Nội dung nên luôn nói rõ:
- file hoặc thư mục đang muốn xử lý,
- mục tiêu mong muốn,
- đầu ra cần tạo,
- có muốn sửa code hay chỉ phân tích/document hay không.

Ví dụ tốt:
- “Đọc `src/infer_demo.py` và sửa lỗi import.”
- “Phân tích `datasets/person/` và cho biết thiếu gì để train.”
- “Cập nhật lại `03_IMPLEMENTATION_PLAN.md` theo trạng thái mới.”

## 6. Nguồn sự thật ưu tiên

Khi có mâu thuẫn, thứ tự ưu tiên là:
1. mã nguồn thực tế trong repo,
2. cấu trúc thư mục và dữ liệu thực tế,
3. tài liệu trong `docs/`,
4. README,
5. mô tả ý tưởng ban đầu.

Lý do:
- code và dữ liệu phản ánh trạng thái thật,
- README và ý tưởng có thể đi trước mức triển khai.

## 7. Trạng thái khởi tạo của dự án tại thời điểm viết file này

- Repo đã có khung POC.
- Chưa có dữ liệu train hoàn chỉnh.
- Chưa có model weights.
- Chưa có output kiểm chứng.
- `src/infer_demo.py` có lỗi import cần sửa trước khi chạy runtime thực tế.

## 8. Session log

## Session 2026-03-31
- Mục tiêu: đọc repo và tạo bộ tài liệu nền trong `docs/` để đồng bộ ngữ cảnh.
- Đã làm: phân tích cấu trúc dự án, đối chiếu luồng code, xác định trạng thái repo, xác định lỗi import trong `src/infer_demo.py`, viết 4 file tài liệu nền.
- File đã sửa: `docs/README.md`, `docs/plans/01_SHARED_CONTEXT.md`, `docs/plans/02_CODEBASE_MAP.md`, `docs/plans/03_IMPLEMENTATION_PLAN.md`, `docs/plans/04_WORKING_PROTOCOL.md`.
- Kết quả tạo ra: bộ tài liệu mô tả mục tiêu, bản đồ code, kế hoạch triển khai và giao thức cập nhật.
- Lỗi phát hiện: `infer_demo.py` import `crop_polygon_region` từ `tracker_utils.py` nhưng hàm này không tồn tại.
- Bước tiếp theo: sửa lỗi import, sau đó chuẩn bị dữ liệu thật để chạy vòng POC đầu tiên.
