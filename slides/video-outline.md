<!-- Authors: Nguyen Ho Anh Tuan (23120185), Le Thuong De (23120232), Le Ha Thanh Chuong (23120195). External source: none. -->

# Kịch bản phân cảnh video thuyết trình (20–30 phút) — Nhóm 16

Kịch bản phân cảnh chi tiết (cue sheet) cho video thuyết trình chính thức dài **24 phút 30 giây** (nằm gọn trong khung **20–30 phút** theo yêu cầu đề cuối kỳ CSC14120, chuẩn 1080p, thu âm rõ ràng, có hình người trình bày).

## 1. Phân vai và phân bổ thời lượng

| Mốc thời gian | Thời lượng | Phần nội dung (theo đề bài) | Phụ trách | Khung đề bài |
|---|---:|---|---|---|
| 00:00 – 05:00 | 5 phút | **Phần 1:** Problem overview and approach | **Tuấn** | 4–6 phút |
| 05:00 – 12:00 | 7 phút | **Phần 2:** Live demonstration of running code | **Thành** | 6–9 phút |
| 12:00 – 19:30 | 7 phút 30 giây | **Phần 3:** Performance results and analysis | **Đế** | 6–9 phút |
| 19:30 – 24:30 | 5 phút | **Phần 4:** Key optimizations and lessons learned | **Chương** | 4–6 phút |

## 2. Phân cảnh chi tiết từng phút (tuyến tính Slide 1 → 30)

### Phần 1: Tổng quan bài toán và hướng tiếp cận (00:00 – 05:00 · Tuấn)

| Mốc | Slide / Màn hình | Nội dung trình bày |
|---|---|---|
| 00:00 – 00:45 | Slide 1–3 (Bìa, Mục lục, Chuyển mục 1) | Giới thiệu Nhóm 16 (4 thành viên), bài toán Parallel Panorama Stitching và bố cục 4 phần của video. |
| 00:45 – 02:00 | Slide 4 (Từ hai ảnh chồng lấn đến một ảnh panorama) | Trình bày đầu vào (2 ảnh RGB chồng lấn A, B), đầu ra (canvas theo hệ tọa độ ảnh A), minh họa bằng `site2/large` (7676×4348) và mục tiêu giữ nguyên thuật toán + hành vi lỗi của V0. |
| 02:00 – 03:45 | Slide 5–6 (Sáu giai đoạn, Khớp đặc trưng/Hình học/Kết xuất) | Giải thích pipeline 6 stage: S1–S3 độc lập cho từng ảnh (Grayscale + Gaussian, FAST-9 + NMS + Top-K, 256-bit BRIEF); S4–S6 kết hợp hai ảnh (Hamming + Lowe ratio, MSAC RANSAC + 4-pt DLT + SVD refit, Inverse warping + manual bilinear + 50/50 average blending). Nêu giả định homography và giới hạn thị sai/hoa văn lặp. |
| 03:45 – 05:00 | Slide 7 (Một pipeline, sáu phiên bản V0–V5) | Tóm tắt kiến trúc `Device-resident` từ V1 và lộ trình 6 phiên bản V0–V5 chạy từ cùng CLI `build/stitch --version <0..5>`, giới thiệu vai trò V4 (Production baseline) và V5 (Dual-stream case study), chuyển sang Thành demo. |

### Phần 2: Live Demo chạy code trên Colab Tesla T4 (05:00 – 12:00 · Thành)

| Mốc | Slide / Màn hình | Nội dung trình bày |
|---|---|---|
| 05:00 – 06:00 | Slide 8 + Terminal Colab | Xác nhận phần cứng `nvidia-smi -L` (Tesla T4), kiểm tra `dataset/` và biên dịch `python3 scripts/build.py --compiler nvcc --require-t4 --target stitch`. |
| 06:00 – 08:30 | Terminal Colab + `scripts/live_demo.py` | Chạy `python3 scripts/live_demo.py --dataset dataset --site site2 --size small --versions 0 4 5 --runs 1`. Chỉ rõ log GPU, warm-up, thời gian từng stage S1–S6 và chênh lệch tốc độ trực quan giữa V0, V4 và V5 (`--v5-schedule dual`). |
| 08:30 – 10:15 | Slide 9–10 + Gallery output | Tóm tắt kiểm chứng đúng đắn (Slide 9: 6 ca synthetic RMSE ≤ 0,10 px, 10/10 ca thực Max RGB = 0, `compute-sanitizer` 0 lỗi, 0 byte rò rỉ), giới thiệu kết quả ảnh ghép đạt chuẩn `site1` và `site3` (Slide 10) và đối chiếu ảnh đầu ra V0/V4/V5. |
| 10:15 – 12:00 | Slide 11 + Terminal log `challenge/medium` | Phân tích trực quan ca thất bại trên cặp khó `de-challenge1` (Slide 11: ảnh S5 matches `challenge/medium` với outlier đỏ chằng chịt và 8 inlier xanh, ảnh ghép lệch `challenge/small`); giải thích hoa văn lặp lan can/trần gỗ gây suy biến $H$ và trả `[NumericalFailure] S6 warp_blend failed` đồng nhất ở V0–V5. Chuyển sang Đế phân tích hiệu năng. |

### Phần 3: Kết quả và phân tích hiệu năng (12:00 – 19:30 · Đế)

*(Chi tiết lời dẫn từng đoạn xem tại [video-performance-notes.md](video-performance-notes.md).)*

| Mốc | Slide / Màn hình | Nội dung trình bày |
|---|---|---|
| 12:00 – 13:15 | Slide 12–13 (Môi trường đo, Tổng hợp thời gian V0–V4) | Điều kiện đo chuẩn trên Tesla T4 (1 warm-up + 5 runs, chỉ tính speedup trong cùng một phiên chạy; V5 đo đối chứng riêng cùng V0 và V4). Tổng quan bước nhảy V0 → V1 (3,80×) → V2 (23,37×) → V3 (42,65×) → V4 (43,02× GM). |
| 13:15 – 14:45 | Slide 14–15 (Dịch chuyển điểm nghẽn, Vì sao tối ưu S6 sau V3?) | Phân tích dịch chuyển điểm nghẽn: S5 chiếm 90–99% ở V1, giảm mạnh ở V2–V3, làm lộ diện S6 chiếm 45,7% tại `site2/large` (28,47 / 62,35 ms). Giải thích giới hạn Amdahl cho S6 (~1,30×). |
| 14:45 – 16:45 | Slide 16–18 (Bảng V4, NSYS V4, NCU V4) | Phân tích V4: 8/9 ca nhanh hơn, S6 GM 1,04×, total GM 1,01×. Đối chiếu bảng NSYS V4 (3 pass → 1 renderer; lưu ý overhead profiler) với NCU (DRAM đọc+ghi tăng +26,0% tại `site2/large`, L2 hit giảm 76,2% → 70,8%, lưu ý `cudaMemset` V3 nằm ngoài counter). |
| 16:45 – 18:45 | Slide 19–20 (Bảng V5, NSYS V5) | Phân tích V5 (đo đối chứng riêng cùng V0 và V4): Pre-S4 tăng tốc GM **1,26×** (`site2/large` giảm 13,70 → 10,97 ms), toàn pipeline đạt **49,9×** GM vs V0 (`site2/large` 58,9 ms, **110,3×**), đối chứng Dual/Seq đạt **1,04×** GM. Hình `nsys-v5.png` xác nhận overlap **16,6–24,5%** (2,05–2,89 ms) vs 0,0% ở V4/V5 seq và Peak VRAM tăng **+64,3 MiB**. |
| 18:45 – 19:30 | Slide 21 (Độ ổn định V5 & quyết định production) | Nêu kết quả 5 khối ghép cặp `site2/large` (median 1,07× nhưng chỉ **3/5 khối** nghiêng về V5, dưới ngưỡng 4/5) và kiểm tra lại nhiễu ở `site3/small` → chốt giữ **V4** làm production baseline, giữ **V5** làm case study concurrency; chuyển sang Chương. |

### Phần 4: Các tối ưu chính và bài học rút ra (19:30 – 24:30 · Chương)

| Mốc | Slide / Màn hình | Nội dung trình bày |
|---|---|---|
| 19:30 – 20:45 | Slide 22–25 (Chuyển mục 3, Chu trình APOD, S5 V2 & V3) | Nhìn lại chu trình APOD (Slide 23) và phân tích sâu bước nhảy lớn nhất ở S5: V2 (Slide 24: Parallel RANSAC + inlier reduction + GPU refit → 6,16× so với V1) và V3 (Slide 25: warp-shuffle MSAC + shared-memory DLT/SVD + batch scheduling → thêm 1,83×). |
| 20:45 – 22:45 | Slide 26–27 (V4 fusion, V5 dual-stream) | Giải thích thiết kế kernel S6 V4 (Slide 26: 1 thread/pixel, gộp 3 pass thành 1, bảo toàn biên/nội suy/làm tròn, đánh đổi DRAM traffic) và kiến trúc hai stream V5 (Slide 27: `streamA`/`streamB`, lập lịch prefix/suffix, `cudaStreamWaitEvent`, cờ ablation `--v5-schedule sequential`). |
| 22:45 – 24:30 | Slide 28–30 (Bài học tối ưu, Kiểm chứng/giới hạn & Tài liệu tham khảo) | Tổng kết bài học tối ưu trên GPU (Slide 28: Amdahl, NCU counter, giới hạn SM/VRAM của dual-stream) và bài học kiểm chứng, giới hạn homography 2D cùng khả năng tái lập từ `Group16_Final.ipynb` (Slide 29–30). Chào kết. |

## 3. Danh mục tư liệu chuẩn bị trước khi quay

| Tư liệu | Nguồn trong repo | Dùng ở phần |
|---|---|---|
| Slide Beamer 16:9 chính thức | `slides/project.tex` → `build/slides/project.pdf` | Cả 4 phần |
| Ảnh A/B cho demo | `dataset/site2/small_left.jpg`, `small_right.jpg` | Phần 2 (Thành) |
| Panorama mẫu | `slides/assets/site2-large-panorama.jpg` | Phần 1 & 2 |
| Script Live Demo | `scripts/live_demo.py` | Phần 2 (Thành) |
| Bảng hiệu năng V4 & V5 | `slides/generated/v4-table.tex`, `v5-table.tex` | Phần 3 (Đế) |
| Hình profiling Nsight | `slides/generated/ncu-v4.png`, `nsys-v5.png` | Phần 3 (Đế) |
| Notebook báo cáo chính thức | `Group16_Final.ipynb` | Đối chiếu tổng thể |

Sau khi quay và biên tập, nhóm đăng video lên YouTube (Unlisted) và cập nhật đường dẫn vào `Group16_Final.ipynb` và `README.md`.
