# Kịch bản video toàn project — Nhóm 16

Kịch bản rút gọn **15 phút**, vẫn có đủ bốn phần nội dung. Đề bài hiện quy định video nộp chính thức dài 20–30 phút. Dùng mốc 15 phút khi tập hoặc khi nhóm đã được phép nộp bản ngắn. Tuấn và Đế dùng dàn ý này để thống nhất lời dẫn, người nói và bản slide trước buổi quay. Các vai dưới đây là đề xuất để nhóm chốt khi tập.

| Thời gian | Phần | Người dẫn đề xuất | Nội dung và hình trên màn hình |
|---|---|---|---|
| 00:00–03:00 | Tổng quan và phương pháp | Tuấn, Thành và Chương | Giới thiệu bài toán, chỉ vùng chồng lấn trên hai ảnh, cho xem panorama. Giải thích S1–S3 làm riêng trên từng ảnh, S4 ghép điểm, S5 ước lượng homography, S6 dựng canvas. Tóm tắt lộ trình V0–V5 (V4 production, V5 thử nghiệm stream concurrency). |
| 03:00–07:00 | Live demo | Tuấn và Thành | Chuẩn bị sẵn binary và dataset. Trên Colab, hiện GPU và source SHA, chạy V0 và V4 trên site2/small, rồi mở hai output. Dùng log challenge/medium đã lưu để giải thích trạng thái lỗi. |
| 07:00–12:00 | Kết quả và phân tích hiệu năng | Đế và Tuấn | Dùng bảng V0–V4 cùng phiên và một hình Nsight. Nêu mức tăng của V2, V3, mức cải thiện của V4 và kết quả thử nghiệm V5 hai stream. Xem lời dẫn của Đế để chia đúng 5 phút. |
| 12:00–15:00 | Tối ưu chính và bài học | Đế, Chương và Tuấn | Dùng APOD nối các vòng tối ưu. Minh họa S5 chuyển từ RANSAC tuần tự sang tính giả thuyết song song, V3 giảm chi phí thực thi S5, V4 hợp nhất dựng canvas, V5 khai thác concurrency. Kết luận về kiểm chứng, cách đọc counter và ảnh hưởng của hotspot lên tốc độ tổng. |

## Chuẩn bị ghi hình

| Tư liệu | Nguồn | Cảnh sử dụng |
|---|---|---|
| Slide toàn project | `project.tex`, xuất từ Beamer | Bốn phần, sơ đồ S1–S6 và tổng kết. |
| Ảnh A/B cho demo | Dataset chính thức, `site2/small_left.jpg` và `site2/small_right.jpg` | Mở hai ảnh và chỉ vùng overlap trước khi chạy. |
| Panorama mẫu | `assets/site2-large-panorama.jpg` | Kết quả V4 trên dataset nhóm. Bản thu nhỏ từ output P9. |
| Panorama của đề | Bộ ảnh do môn học cung cấp | Tư liệu cho gallery cuối kỳ khi nhóm đã chuẩn bị được cặp ảnh và kết quả ghép. |
| Lệnh build và chạy | Slide “Build and run on the same Tesla T4”, notebook P9, `scripts/build.py` | Đặt thư mục dataset đúng chỗ, xác nhận `nvidia-smi -L`, chạy V0 và V4, rồi mở output. |
| Ca khó và log | `v4/benchmark/challenge/medium.log` trong gói P9 | Chỉ dòng `[NumericalFailure] S6 warp_blend failed` và giải thích cách pipeline báo lỗi. |
| Bảng hiệu năng | `v4/benchmark/all_versions_speedup.csv`, báo cáo APOD và `generated/v4-table.tex` | Dùng số đo cùng phiên cho so sánh V0–V4. Giữ nhãn riêng cho số lịch sử P6–P8. |
| Hồ sơ Nsight | Báo cáo P7/P8, `generated/nsys-v4.png`, `generated/ncu-v4.png`, `generated/screenshots/` | Chỉ hotspot S5 và diễn biến S6, minh họa thao tác NSYS bằng timeline và giải thích phạm vi counter NCU. |
| Kiểm chứng | `docs/report/p9-v4-verification.md` | Cho xem kết quả geometry, Max RGB và memcheck. |

Trước buổi quay, Tuấn chốt phần mở đầu, thứ tự chuyển người nói và lượt demo. Đế đối chiếu các bảng với CSV, chuẩn bị tab trace và báo cáo cùng lời dẫn chi tiết phần hiệu năng. Mỗi người tập chuyển giữa slide và Colab ở đúng mốc thời gian.

Khi ghi, dùng timing chính thức trên slide để kết luận hiệu năng. Lượt chạy một run trên màn hình dùng để trình bày thao tác chạy, nhận output và đọc log. Sau buổi quay, nhóm đặt link YouTube Unlisted vào notebook và README theo đề.
