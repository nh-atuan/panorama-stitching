<!-- Authors: Nguyen Ho Anh Tuan (23120185), Le Thuong De (23120232), Le Ha Thanh Chuong (23120195). External source: none. -->

# Kịch bản phân cảnh video thuyết trình (20–30 phút) — Nhóm 16

Kịch bản phân cảnh chi tiết (cue sheet) cho video thuyết trình chính thức dài **24 phút 30 giây** (nằm gọn trong khung **20–30 phút** theo yêu cầu đề cuối kỳ CSC14120, chuẩn 1080p, thu âm rõ ràng, có hình người trình bày).

## 1. Phân vai và phân bổ thời lượng (P12)

| Mốc thời gian | Thời lượng | Phần nội dung (theo đề bài) | Phụ trách | Khung đề bài |
|---|---:|---|---|---|
| 00:00 – 05:00 | 5 phút | **Phần 1:** Problem overview and approach | **Tuấn** | 4–6 phút |
| 05:00 – 12:00 | 7 phút | **Phần 2:** Live demonstration of running code | **Thành** | 6–9 phút |
| 12:00 – 19:30 | 7 phút 30 giây | **Phần 3:** Performance results and analysis | **Đế** | 6–9 phút |
| 19:30 – 24:30 | 5 phút | **Phần 4:** Key optimizations and lessons learned | **Chương** | 4–6 phút |

## 2. Phân cảnh chi tiết từng phút

### Phần 1: Tổng quan bài toán và hướng tiếp cận (00:00 – 05:00 · Tuấn)

| Mốc | Slide / Màn hình | Nội dung trình bày |
|---|---|---|
| 00:00 – 00:45 | Slide 1–2 (Title, Roadmap) | Giới thiệu Nhóm 16 (4 thành viên), bài toán Parallel Panorama Stitching và bố cục 4 phần của video. |
| 00:45 – 02:00 | Slide 3 (From two photos to one panorama) | Trình bày đầu vào (2 ảnh RGB chồng lấn A, B), đầu ra (canvas theo hệ tọa độ ảnh A), minh họa bằng `site2/large` (7676×4348) và mục tiêu giữ nguyên thuật toán + hành vi lỗi của V0. |
| 02:00 – 03:45 | Slide 4–5 (Six stages, Matching/Geometry/Rendering) | Giải thích pipeline 6 stage: S1–S3 độc lập cho từng ảnh (Grayscale + Gaussian, FAST-9 + NMS + Top-K, 256-bit BRIEF); S4–S6 kết hợp hai ảnh (Hamming + Lowe ratio, MSAC RANSAC + 4-pt DLT + SVD refit, Inverse warping + manual bilinear + 50/50 average blending). Nêu giả định homography và giới hạn thị sai/hoa văn lặp. |
| 03:45 – 05:00 | Slide 6 (One pipeline, six versions V0–V5) | Tóm tắt kiến trúc `Device-resident` từ V1 và lộ trình 6 phiên bản V0–V5 chạy từ cùng CLI `build/stitch --version <0..5>`, giới thiệu vai trò V4 (Production baseline) và V5 (Dual-stream case study), chuyển sang Thành demo. |

### Phần 2: Live Demo chạy code trên Colab Tesla T4 (05:00 – 12:00 · Thành)

| Mốc | Slide / Màn hình | Nội dung trình bày |
|---|---|---|
| 05:00 – 06:00 | Slide 7 + Terminal Colab | Xác nhận phần cứng `nvidia-smi -L` (Tesla T4), SHA mã nguồn đã đóng băng (`f2837a8`), kiểm tra `dataset/` và biên dịch `python3 scripts/build.py --compiler nvcc --require-t4 --target stitch`. |
| 06:00 – 08:30 | Terminal Colab + `scripts/live_demo.py` | Chạy lệnh 1-click `python3 scripts/live_demo.py --dataset dataset --site site2 --size small --versions 0 4 5 --runs 1`. Chỉ rõ log GPU, warm-up, thời gian từng stage S1–S6 và chênh lệch tốc độ trực quan giữa V0, V4 và V5 (`--v5-schedule dual`). |
| 08:30 – 10:15 | Slide 8–9 + Gallery output | Mở hai ảnh đầu vào (`site2/small_left.jpg`, `site2/small_right.jpg`) và đối chiếu 3 ảnh panorama đầu ra V0/V4/V5 (khớp canvas, Max RGB = 0). Tóm tắt kiểm chứng P11-T02 (14 suite V0, 16 suite GPU, 15+ suite Python, `compute-sanitizer` 0 lỗi, 0 byte rò rỉ). |
| 10:15 – 12:00 | Terminal log `challenge/medium` | Chỉ kết quả chạy `challenge/medium` (`de-challenge1`) trả mã lỗi `[NumericalFailure] S6 warp_blend failed` đồng nhất ở V0–V5; giải thích nguyên nhân hoa văn lặp lan can/trần nhà làm thoái hóa BRIEF. Chuyển sang Đế phân tích hiệu năng. |

### Phần 3: Kết quả và phân tích hiệu năng (12:00 – 19:30 · Đế)

*(Chi tiết lời dẫn từng đoạn xem tại [video-performance-notes.md](video-performance-notes.md).)*

| Mốc | Slide / Màn hình | Nội dung trình bày |
|---|---|---|
| 12:00 – 13:15 | Slide 10, 12 (Timing summary, Protocol) | Điều kiện đo chuẩn trên Tesla T4 (1 warm-up + 5 runs, tách biệt phiên P9 V0–V4 và P10 V0/V4/V5, không trộn speedup chéo phiên). Tổng quan nhảy vọt V0 $\rightarrow$ V1 (3,80×) $\rightarrow$ V2 (23,37×) $\rightarrow$ V3 (42,65×) $\rightarrow$ V4 (43,02× GM). |
| 13:15 – 14:45 | Slide 11, 14 (Bottleneck shifts, Why S6 after V3) | Phân tích dịch chuyển điểm nghẽn: S5 chiếm 90–99% ở V1, giảm mạnh ở V2–V3, làm lộ diện S6 chiếm 45,7% tại `site2/large` (28,468 / 62,353 ms ở P8). Giải thích giới hạn Amdahl cho S6. |
| 14:45 – 16:45 | Slide 17–19 (V4 table, NSYS V4, NCU V4) | Phân tích P9 V4: 8/9 ca nhanh hơn, S6 GM 1,0357×, total GM 1,0086×; 5 khối luân phiên median 1,0270×. Đối chiếu NSYS (3 pass $\rightarrow$ 1 renderer) với NCU (DRAM đọc+ghi tăng +26,0% tại `site2/large`, L2 hit giảm 76,19% $\rightarrow$ 70,75%, lưu ý memset V3 nằm ngoài counter). |
| 16:45 – 18:45 | Slide 21–24 (V5 architecture, V5 table, NSYS V5, stability) | Phân tích P10-T05 chính thức: Pre-S4 tăng tốc GM **1,257×** (`site2/large` giảm 13,700 → 10,971 ms, 1,249×), toàn pipeline đạt **49,88×** GM vs V0 (`site2/large` 58,926 ms, **110,29×**), đối chứng thuần túy Dual/Seq đạt **1,036×** GM. Hình `nsys-v5.png` xác nhận overlap thực tế **16,6%–24,5%** (2,05–2,89 ms) vs 0,0% ở V4/V5 seq và Peak VRAM tăng đúng **+64,30 MiB** (0 B rò rỉ). |
| 18:45 – 19:30 | Slide 16, 24 (Verification & APOD decision) | Nêu kết quả 5 khối ghép cặp `site2/large` (median 1,067× nhưng chỉ **3/5 khối** cùng chiều, chưa đạt ngưỡng ≥ 4/5) → chốt quyết định APOD: giữ **V4** làm production baseline, giữ **V5** làm case study concurrency; chuyển sang Chương tổng kết các tối ưu chính và bài học. |

### Phần 4: Các tối ưu chính và bài học rút ra (19:30 – 24:30 · Chương)

| Mốc | Slide / Màn hình | Nội dung trình bày |
|---|---|---|
| 19:30 – 21:00 | Slide 13, 15 (APOD, V4 fusion) | Nhìn lại chu trình APOD theo hai trục của môn học: trục Bộ nhớ (Device-resident, shared-memory DLT/SVD ở V3, Single-pass Canvas Fusion ở V4) và trục Thực thi & Đồng thời (Parallel RANSAC V2, warp-shuffle & batch scheduling V3, Dual-stream V5). |
| 21:00 – 22:45 | Slide 20, 21 (V4 usefulness, V5 dual-stream) | Giải thích sâu cách thiết kế kernel S6 V4 (32×8 block, 1 thread/pixel, bảo toàn snap/clamp/rounding) và kiến trúc dispatcher V5 (prefix/suffix, `cudaStreamWaitEvent`, chế độ ablation `--v5-schedule sequential`). |
| 22:45 – 24:30 | Slide 24–25 (Lessons and limits, What the project demonstrates) | Tổng kết 4 bài học cốt lõi: (1) để số đo dẫn dắt điểm nghẽn và tôn trọng định luật Amdahl; (2) kiểm chứng đúng đắn + memcheck trước khi kết luận speedup; (3) đọc hardware counter cẩn thận (phạm vi counter NCU, SM saturation); (4) bảo toàn tính tái lập (SHA, manifest, CSV thô, notebook `Group16_Final.ipynb`). Chào kết. |

## 3. Danh mục tư liệu chuẩn bị trước khi quay

| Tư liệu | Nguồn trong repo / Drive | Dùng ở phần |
|---|---|---|
| Slide Beamer 16:9 chính thức | `slides/project.tex` $\rightarrow$ `build/slides/project.pdf` | Cả 4 phần |
| Ảnh A/B cho demo | `dataset/site2/small_left.jpg`, `small_right.jpg` | Phần 2 (Thành) |
| Panorama mẫu | `slides/assets/site2-large-panorama.jpg` | Phần 1 & 2 |
| Script Live Demo 1-click | `scripts/live_demo.py` | Phần 2 (Thành) |
| Bảng hiệu năng P9 & P10 | `slides/generated/v4-table.tex`, `v5-table.tex`, `docs/apod-log.md` | Phần 3 (Đế) |
| Hình profiling Nsight | `slides/generated/nsys-v4.png`, `ncu-v4.png`, `generated/screenshots/` | Phần 3 (Đế) |
| Báo cáo kiểm chứng & đóng băng | `docs/report/p9-v4-verification.md`, `p10-v5-verification.md`, `p11-t02-freeze-verification.md` | Phần 2 & 3 |
| Báo cáo APOD V4 & V5 | `docs/report/p9-t05-v4-apod.md`, `docs/report/p10-t05-v5-apod.md` | Phần 3 & 4 |

Sau khi quay và biên tập ở P12–P13, nhóm đăng video lên YouTube (Unlisted) và cập nhật đường dẫn vào `Group16_Final.ipynb` và `README.md`.
