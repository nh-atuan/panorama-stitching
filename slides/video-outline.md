<!-- Authors: Nguyen Ho Anh Tuan (23120185), Le Thuong De (23120232). External source: none. -->

# Kịch bản phân cảnh video thuyết trình (20–30 phút) — Nhóm 16

Kịch bản phân cảnh chi tiết (cue sheet) cho video thuyết trình chính thức dài **24 phút 30 giây** (nằm gọn trong khung **20–30 phút** theo yêu cầu đề cuối kỳ CSC14120, chuẩn 1080p, thu âm rõ ràng, có hình người trình bày).

## 1. Phân vai và phân bổ thời lượng

| Mốc thời gian | Thời lượng | Phần nội dung (theo đề bài) | Phụ trách | Khung đề bài |
|---|---:|---|---|---|
| 00:00 – 05:00 | 5 phút | **Phần 1:** Problem overview and approach | **Tuấn** | 4–6 phút |
| 05:00 – 12:00 | 7 phút | **Phần 2:** Live demonstration of running code | **Thành** | 6–9 phút |
| 12:00 – 19:30 | 7 phút 30 giây | **Phần 3:** Performance results and analysis | **Đế** | 6–9 phút |
| 19:30 – 24:30 | 5 phút | **Phần 4:** Key optimizations and lessons learned | **Chương** | 4–6 phút |

## 2. Phân cảnh chi tiết từng phút (tuyến tính Slide 1 → 24)

### Phần 1: Tổng quan bài toán và hướng tiếp cận (00:00 – 05:00 · Tuấn)

| Mốc | Slide / Màn hình | Nội dung trình bày |
|---|---|---|
| 00:00 – 00:45 | Slide 1–2 (Title, Roadmap) | Giới thiệu Nhóm 16 (4 thành viên), bài toán Parallel Panorama Stitching và bố cục 4 phần của video. |
| 00:45 – 02:00 | Slide 3 (From two overlapping photos to one panorama) | Trình bày đầu vào (2 ảnh RGB chồng lấn A, B), đầu ra (canvas theo hệ tọa độ ảnh A), minh họa bằng `site2/large` (7676×4348) và mục tiêu giữ nguyên thuật toán + hành vi lỗi của V0. |
| 02:00 – 03:45 | Slide 4–5 (Six stages, Matching/Geometry/Rendering) | Giải thích pipeline 6 stage: S1–S3 độc lập cho từng ảnh (Grayscale + Gaussian, FAST-9 + NMS + Top-K, 256-bit BRIEF); S4–S6 kết hợp hai ảnh (Hamming + Lowe ratio, MSAC RANSAC + 4-pt DLT + SVD refit, Backward bilinear + Feather blend). Nêu giả định homography và giới hạn thị sai/hoa văn lặp. |
| 03:45 – 05:00 | Slide 6 (One pipeline, six versions V0–V5) | Tóm tắt kiến trúc `Device-resident` từ V1 và lộ trình 6 phiên bản V0–V5 chạy từ cùng CLI `build/stitch --version <0..5>`, giới thiệu vai trò V4 (Production baseline) và V5 (Dual-stream case study), chuyển sang Thành demo. |

### Phần 2: Live Demo chạy code trên Colab Tesla T4 (05:00 – 12:00 · Thành)

| Mốc | Slide / Màn hình | Nội dung trình bày |
|---|---|---|
| 05:00 – 06:00 | Slide 7 + Terminal Colab | Xác nhận phần cứng `nvidia-smi -L` (Tesla T4), kiểm tra `dataset/` và biên dịch `python3 scripts/build.py --compiler nvcc --require-t4 --target stitch`. |
| 06:00 – 08:30 | Terminal Colab + `scripts/live_demo.py` | Chạy `python3 scripts/live_demo.py --dataset dataset --site site2 --size small --versions 0 4 5 --runs 1`. Chỉ rõ log GPU, warm-up, thời gian từng stage S1–S6 và chênh lệch tốc độ trực quan giữa V0, V4 và V5 (`--v5-schedule dual`). |
| 08:30 – 10:15 | Slide 8–9 + Gallery output | Mở hai ảnh đầu vào (`site2/small_left.jpg`, `small_right.jpg`) và đối chiếu 3 ảnh panorama đầu ra V0/V4/V5 (khớp canvas, Max RGB = 0). Tóm tắt kiểm chứng đúng đắn (6 ca synthetic RMSE ≤ 0,10 px, 10/10 ca thực Max RGB = 0, `compute-sanitizer` 0 lỗi, 0 byte rò rỉ). |
| 10:15 – 12:00 | Slide 9 + Terminal log `challenge/medium` | Chỉ kết quả chạy `challenge/medium` trả mã lỗi `[NumericalFailure] S6 warp_blend failed` đồng nhất ở V0–V5; giải thích nguyên nhân hoa văn lặp lan can/trần nhà làm thoái hóa BRIEF. Chuyển sang Đế phân tích hiệu năng. |

### Phần 3: Kết quả và phân tích hiệu năng (12:00 – 19:30 · Đế)

*(Chi tiết lời dẫn từng đoạn xem tại [video-performance-notes.md](video-performance-notes.md).)*

| Mốc | Slide / Màn hình | Nội dung trình bày |
|---|---|---|
| 12:00 – 13:15 | Slide 10–11 (Experimental setup, Timing summary) | Điều kiện đo chuẩn trên Tesla T4 (1 warm-up + 5 runs, tách biệt Session A cho V0–V4 và Session B cho V0/V4/V5, không trộn speedup chéo phiên). Tổng quan bước nhảy V0 → V1 (3,80×) → V2 (23,37×) → V3 (42,65×) → V4 (43,02× GM). |
| 13:15 – 14:45 | Slide 12–13 (Bottleneck shifts, Why S6 after V3) | Phân tích dịch chuyển điểm nghẽn: S5 chiếm 90–99% ở V1, giảm mạnh ở V2–V3, làm lộ diện S6 chiếm 45,7% tại `site2/large` (28,47 / 62,35 ms). Giải thích giới hạn Amdahl cho S6 (~1,30×). |
| 14:45 – 16:45 | Slide 14–16 (V4 table, NSYS V4, NCU V4) | Phân tích V4 (Session A): 8/9 ca nhanh hơn, S6 GM 1,04×, total GM 1,01×. Đối chiếu NSYS (3 pass → 1 renderer) với NCU (DRAM đọc+ghi tăng +26,0% tại `site2/large`, L2 hit giảm 76,2% → 70,8%, lưu ý `cudaMemset` V3 nằm ngoài counter). |
| 16:45 – 18:45 | Slide 17–18 (V5 table, NSYS V5) | Phân tích V5 (Session B): Pre-S4 tăng tốc GM **1,26×** (`site2/large` giảm 13,70 → 10,97 ms), toàn pipeline đạt **49,9×** GM vs V0 (`site2/large` 58,9 ms, **110,3×**), đối chứng Dual/Seq đạt **1,04×** GM. Hình `nsys-v5.png` xác nhận overlap **16,6–24,5%** (2,05–2,89 ms) vs 0,0% ở V4/V5 seq và Peak VRAM tăng **+64,3 MiB**. |
| 18:45 – 19:30 | Slide 19 (V5 stability & decision) | Nêu kết quả 5 khối ghép cặp `site2/large` (median 1,07× nhưng chỉ **3/5 khối** nghiêng về V5, dưới ngưỡng 4/5) và kiểm tra lại nhiễu ở `site3/small` → chốt giữ **V4** làm production baseline, giữ **V5** làm case study concurrency; chuyển sang Chương. |

### Phần 4: Các tối ưu chính và bài học rút ra (19:30 – 24:30 · Chương)

| Mốc | Slide / Màn hình | Nội dung trình bày |
|---|---|---|
| 19:30 – 20:30 | Slide 20–21 (APOD workflow, S5 V2 & V3) | Nhìn lại chu trình APOD và phân tích sâu bước nhảy lớn nhất ở S5: V2 (Parallel RANSAC + inlier reduction + GPU refit → 6,16× so với V1) và V3 (warp-shuffle MSAC + shared-memory DLT/SVD + batch scheduling → thêm 1,83×). |
| 20:30 – 22:45 | Slide 22–23 (V4 fusion, V5 dual-stream) | Giải thích thiết kế kernel S6 V4 (1 thread/pixel, gộp 3 pass thành 1, bảo toàn biên/nội suy/làm tròn, đánh đổi DRAM traffic) và kiến trúc V5 (hai non-blocking stream, lập lịch prefix/suffix, `cudaStreamWaitEvent`, cờ ablation `--v5-schedule sequential`). |
| 22:45 – 24:30 | Slide 24 (Key lessons and limitations) | Tổng kết 4 bài học cốt lõi: bám số đo và định luật Amdahl; kiểm chứng bằng hardware counter; hiểu giới hạn SM saturation và VRAM của dual-stream trên Tesla T4; kiểm chứng đúng đắn + memcheck trước khi kết luận speedup. Chào kết. |

## 3. Danh mục tư liệu chuẩn bị trước khi quay

| Tư liệu | Nguồn trong repo | Dùng ở phần |
|---|---|---|
| Slide Beamer 16:9 chính thức | `slides/project.tex` → `build/slides/project.pdf` | Cả 4 phần |
| Ảnh A/B cho demo | `dataset/site2/small_left.jpg`, `small_right.jpg` | Phần 2 (Thành) |
| Panorama mẫu | `slides/assets/site2-large-panorama.jpg` | Phần 1 & 2 |
| Script Live Demo | `scripts/live_demo.py` | Phần 2 (Thành) |
| Bảng hiệu năng Session A & B | `slides/generated/v4-table.tex`, `v5-table.tex` | Phần 3 (Đế) |
| Hình profiling Nsight | `slides/generated/nsys-v4.png`, `ncu-v4.png`, `nsys-v5.png` | Phần 3 (Đế) |
| Notebook báo cáo chính thức | `Group16_Final.ipynb` | Đối chiếu tổng thể |

Sau khi quay và biên tập, nhóm đăng video lên YouTube (Unlisted) và cập nhật đường dẫn vào `Group16_Final.ipynb` và `README.md`.
