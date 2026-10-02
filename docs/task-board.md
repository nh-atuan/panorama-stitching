# Bảng công việc giữa kỳ

Quy tắc chung nằm trong [kế hoạch giữa kỳ](midterm-plan.md). Kế hoạch được lập cuốn chiếu: chỉ giai đoạn hiện tại có task và hạn chi tiết. Giai đoạn kế tiếp được lập khi giai đoạn trước hoàn thành. Mốc cố định duy nhất là **23/10 (T6)**.

Mã task có dạng `P<số giai đoạn>-T<số thứ tự>` và được dùng trong tên nhánh và commit message, ví dụ nhánh `tuan/p0-t01-create-repo`.

Mỗi người tự cập nhật cột **Trạng thái** và **Ghi chú / PR** của task mình phụ trách. Trạng thái dùng một trong các giá trị: `Chưa làm`, `Đang làm`, `Chờ review`, `Xong`, `Bị chặn`.

## P0 - Khởi động

| Mã | Công việc | Phụ trách | Hạn | Phụ thuộc | Đầu ra / tiêu chí xong | Trạng thái | Ghi chú / PR |
|---|---|---|---|---|---|---|---|
| P0-T01 | Tạo repo GitHub private, mời 3 thành viên, push lịch sử hiện có | Tuấn | 03/10 (T7) | | Cả 4 người clone được repo | Chưa làm | |
| P0-T02 | Tạo Google Drive chung để nộp ảnh gốc, cập nhật link vào [dataset](dataset.md) mục 4 | Tuấn | 03/10 (T7) | | Cả 4 người mở và upload được | Chưa làm | |
| P0-T03 | Tìm starter notebook; nếu chưa có thì hỏi Thầy/trợ giảng; đưa starter vào thư mục `starter/` của repo | Chương | 03/10 (T7) | P0-T01 | Starter nằm trong repo, hoặc đã hỏi và áp dụng phương án dự phòng ở mục 7 của kế hoạch | Chưa làm | |
| P0-T04 | Thống nhất số lượng ảnh/cặp mỗi người chụp và cách chọn ảnh (có bình chọn hay không) | Cả nhóm | 03/10 (T7) | | Kết quả ghi vào [dataset](dataset.md) mục 2 và mục 6 | Chưa làm | |
| P0-T05 | Đọc đề giữa kỳ, đề cuối kỳ trong `docs/specs/` và kế hoạch giữa kỳ | Cả nhóm | 04/10 (CN) | | Mỗi người tự đánh dấu xong | Chưa làm | |
| P0-T06 | Ghi địa điểm dự kiến vào [dataset](dataset.md) mục 5.1 | Cả nhóm | 03/10 (T7) | | Đủ 4 dòng | Chưa làm | |
| P0-T07 | Chụp ảnh theo quy định, upload ảnh gốc, điền bảng ứng viên | Cả nhóm | 05/10 (T2) | P0-T02, P0-T04 | Đủ số lượng đã thống nhất ở P0-T04 | Chưa làm | |
| P0-T08 | Viết script chuẩn bị dataset theo [dataset](dataset.md) mục 7 | Thành | 05/10 (T2) | | Chạy được trên Colab với ảnh mẫu | Chưa làm | |
| P0-T09 | Kiểm tra mọi cặp ảnh ứng viên có đạt yêu cầu hay không, ghi kết quả | Thành | 06/10 (T3) | P0-T07 | [dataset](dataset.md) mục 5.3 đã điền đầy đủ | Chưa làm | |
| P0-T10 | Chọn sơ bộ phương pháp, đầu vào/đầu ra cho S1 | Tuấn | 04/10 (CN) | | `docs/stages/s1-preprocessing.md` có mục 1 và 2 | Chưa làm | |
| P0-T11 | Chọn sơ bộ phương pháp, đầu vào/đầu ra cho S2, S3 | Thành | 04/10 (CN) | | `docs/stages/s2-detection.md`, `docs/stages/s3-description.md` có mục 1 và 2 | Chưa làm | |
| P0-T12 | Chọn sơ bộ phương pháp, đầu vào/đầu ra cho S4, S5; phương án cặp synthetic và metric sai số | Đế | 04/10 (CN) | P0-T03 | `docs/stages/s4-matching.md`, `docs/stages/s5-homography.md` có mục 1 và 2 | Chưa làm | |
| P0-T13 | Chọn sơ bộ phương pháp, đầu vào/đầu ra cho S6 | Chương | 04/10 (CN) | | `docs/stages/s6-warp-blend.md` có mục 1 và 2 | Chưa làm | |
| P0-T14 | Soạn nháp `common.h` và `docs/interface.md` theo mục 8 của kế hoạch | Chương | 05/10 (T2) | P0-T03, P0-T10 đến P0-T13 | Pull request mở để góp ý | Chưa làm | |
| P0-T15 | Góp ý interface, xác nhận phần dữ liệu của stage mình | Tuấn, Thành, Đế | 05/10 (T2) | P0-T14 | Mỗi người đã góp ý hoặc xác nhận trong pull request | Chưa làm | |
| P0-T16 | Chốt interface: cả nhóm thống nhất và merge | Cả nhóm | 06/10 (T3) | P0-T15 | Interface đã merge vào `main` | Chưa làm | |

## P1 - Cài đặt từng stage

Lập chi tiết khi P0 hoàn thành.

## P2 - Ghép và kiểm chứng V0

Lập chi tiết khi P1 hoàn thành.

## P3 - Đo và phân tích

Lập chi tiết khi P2 hoàn thành.

## P4 - Hoàn thiện và nộp

Lập chi tiết khi P3 hoàn thành. Hạn cuối: 23/10 (T6).

## Quyết định đã chốt

Ghi lại các quyết định cả Nhóm đã thống nhất trong quá trình làm.

| Ngày | Quyết định |
|---|---|
