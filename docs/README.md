# Tài liệu vận hành dự án AI Camera

Mục đích của thư mục `docs/` là tạo một điểm tham chiếu cố định để các lần làm việc sau không bị lệch ngữ cảnh giữa mã nguồn, mục tiêu đề tài và kế hoạch triển khai.

## Thứ tự đọc khuyến nghị

1. `docs/plans/01_SHARED_CONTEXT.md`
2. `docs/plans/02_CODEBASE_MAP.md`
3. `docs/plans/03_IMPLEMENTATION_PLAN.md`
4. `docs/plans/04_WORKING_PROTOCOL.md`

## Cách dùng

- Trước khi sửa code: đọc `01_SHARED_CONTEXT.md`.
- Khi cần biết file nào làm gì: đọc `02_CODEBASE_MAP.md`.
- Khi cần biết bước tiếp theo: đọc `03_IMPLEMENTATION_PLAN.md`.
- Khi bắt đầu một phiên làm việc mới: cập nhật `04_WORKING_PROTOCOL.md` theo tình trạng mới.

## Trạng thái hiện tại của repo

Repo hiện tại là một khung POC khá đầy đủ cho bài toán:
- tách frame,
- chọn ROI,
- chuẩn bị crop cho classification,
- train detection người,
- train classification trạng thái vùng chứa,
- chạy pipeline suy luận có rule engine và log sự kiện.

Tuy nhiên repo chưa ở trạng thái chạy end-to-end ngay vì còn các thiếu hụt thực tế:
- chưa có dữ liệu train hoàn chỉnh,
- chưa có model weights,
- chưa có video mẫu trong `assets/videos/`,
- có ít nhất một lỗi import trong `src/infer_demo.py`.

## Nguyên tắc cập nhật

Khi có thay đổi đáng kể về kiến trúc, dữ liệu, rule, hoặc mục tiêu triển khai, phải cập nhật ít nhất 2 file:
- `01_SHARED_CONTEXT.md`
- `03_IMPLEMENTATION_PLAN.md`
