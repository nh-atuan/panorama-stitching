<!-- Authors: Le Thuong De (23120232). External source: none. -->

# Lời dẫn chi tiết phần Hiệu năng (Đế · 7 phút 30 giây)

Đế trình bày **Phần 3: Performance results and analysis** trong **7 phút 30 giây (12:00 – 19:30)**, đi tuần tự từ **Slide 12 đến Slide 21** (nằm giữa khung 6–9 phút theo yêu cầu đề bài). [Kịch bản chung 20–30 phút](video-outline.md)

| Mốc | Thời lượng | Slide / Tư liệu | Lời dẫn chính |
|---|---:|---|---|
| 12:00 – 12:45 | 0:45 | Slide 12 (*Môi trường thực nghiệm*) | Nêu quy tắc đo chuẩn trên Tesla T4 (`sm_75`, `-O2 --fmad=false`): 9 ca chuẩn (3 site × 3 cỡ) + ca `challenge`, 1 warm-up + 5 runs đo, tách riêng S1–S6, H2D, D2H, `Total_Kernel_ms` và `Total_ms`. Nhấn mạnh chỉ so speedup trong **cùng một phiên đo** (đợt đo chính V0–V4; bản V5 đo đối chứng riêng cùng V0 và V4). |
| 12:45 – 13:30 | 0:45 | Slide 13 (*Tổng hợp thời gian V0–V4*) | Đọc nhanh bước nhảy tổng thể trên 9 ca chuẩn: V1 đạt GM **3,80×**, V2 đạt **23,37×** (6,16× so với V1), V3 đạt **42,65×** (1,83× so với V2), V4 đạt **43,02×** (`site2/large` từ 5746,1 ms xuống 62,2 ms). Nêu trước rằng bản thử nghiệm V5 được đo đối chứng riêng cùng V0 và V4 ở các slide sau. |
| 13:30 – 14:45 | 1:15 | Slide 14–15 (*Dịch chuyển điểm nghẽn*, *Vì sao tối ưu S6 sau V3?*) | Giải thích vì sao điểm nghẽn dịch chuyển: ở V1, S5 chiếm 90–99% tổng thời gian nên V2 và V3 tập trung giải phóng S5. Sau V3, tại `site2/large`, S5 giảm còn 12,20 ms nhưng S6 đứng ở 28,47 ms — chiếm **45,7%** tổng thời gian. Theo Amdahl, ngay cả khi S6 nhanh gấp đôi thì toàn pipeline cũng chỉ tăng tối đa ~1,30×. |
| 14:45 – 15:45 | 1:00 | Slide 16 (*Benchmark V4*) | Trình bày kết quả V4: nhanh hơn V3 ở **8/9 ca chuẩn**, S6 nhanh hơn GM **1,04×** (1,036×), toàn pipeline đạt GM **1,01×** (1,009×). Tại `site2/large`, tổng thời gian giảm từ 62,87 → 62,20 ms. |
| 15:45 – 17:00 | 1:15 | Slide 17–18 (*NSYS V4*, *NCU V4*) | Dùng bảng đối chiếu NSYS V4 chỉ rõ 3 thao tác dựng canvas của V3 (clear + copy A + gather B) gộp thành 1 `render_canvas_kernel` ở V4; nhấn mạnh luôn dùng benchmark 5 run (28,71 → 28,19 ms) thay vì thời gian trong trace. Chuyển sang `ncu-v4.png`: trong các kernel lấy mẫu tại `site2/large`, tổng DRAM đọc + ghi tăng **+26,0%** (310,8 → 391,7 MB), L2 hit giảm 76,2% → 70,8% (lưu ý `cudaMemset` của V3 nằm ngoài counter NCU). |
| 17:00 – 18:15 | 1:15 | Slide 19 (*Benchmark V5*) | Trình bày kết quả V5 (đo đối chứng cùng V0 và V4 trên một phiên T4 riêng): đoạn pre-S4 (H2D + S1–S3) nhanh hơn GM **1,26×** (`site2/large` giảm 13,70 → 10,97 ms, 1,25×), đối chứng thuần túy Dual/Seq đạt GM **1,04×**, toàn pipeline đạt GM **49,9×** so với V0 (`site2/large` 58,9 ms, **110,3×**). |
| 18:15 – 19:30 | 1:15 | Slide 20–21 (*NSYS V5 overlap*, *Độ ổn định & quyết định*) | Dùng `nsys-v5.png` chứng minh chồng lấp GPU thực sự **16,6–24,5%** (2,05–2,89 ms) so với 0,0% ở V4/V5 seq; `H2D → S4 start` ở `site2/large` rút từ 23,19 ms (V4) xuống **17,66 ms** (V5 dual); Peak VRAM tăng **+64,3 MiB** (269,8 → 334,1 MiB, 0 B rò rỉ). Nêu kết quả 5 khối ghép cặp `site2/large` đạt median **1,07×** nhưng chỉ **3/5 khối** nghiêng về V5 (< 4/5) và kiểm tra lại `site3/small` (nhiễu giữa các lần chạy) → chốt giữ **V4** làm production baseline, giữ **V5** làm case study concurrency. Chuyển lời cho Chương. |

## Danh mục hiện vật cần mở sẵn khi quay

- `build/slides/project.pdf`: mở toàn màn hình chế độ 16:9 tại Slide 12–21.
- `slides/generated/ncu-v4.png`, `slides/generated/nsys-v5.png`: ảnh Nsight phóng to rõ đơn vị nếu cần zoom.

Lưu ý khi quay: giữ tốc độ nói đều, đọc rõ đơn vị (ms, MB, ×, %), nhấn mạnh nguyên tắc chỉ tính speedup trong cùng một phiên đo trên Colab để thể hiện kỷ luật thực nghiệm.
