<!-- Authors: Le Thuong De (23120232), Nguyen Ho Anh Tuan (23120185). External source: none. -->

# Lời dẫn chi tiết phần Hiệu năng (Đế · 7 phút 30 giây)

Đế trình bày **Phần 3: Performance results and analysis** trong **7 phút 30 giây (12:00 – 19:30)**, đi tuần tự từ **Slide 12 đến Slide 19** (nằm giữa khung 6–9 phút theo yêu cầu đề bài). [Kịch bản chung 20–30 phút](video-outline.md)

| Mốc | Thời lượng | Slide / Tư liệu | Lời dẫn chính |
|---|---:|---|---|
| 12:00 – 12:45 | 0:45 | Slide 12 (*Môi trường thực nghiệm*) | Nêu quy tắc đo chuẩn trên Tesla T4 (`sm_75`, `-O2 --fmad=false`): 9 ca chuẩn (3 site × 3 cỡ) + ca `challenge`, 1 warm-up (V0) và 4 warm-up (GPU V1–V5) để ổn định xung nhịp trước 5 runs đo, tách riêng S1–S6, H2D, D2H, `Total_Kernel_ms` và `Total_ms`. Nhấn mạnh toàn bộ V0–V5 được đo trong **cùng một phiên Colab Tesla T4 duy nhất**. |
| 12:45 – 13:45 | 1:00 | Slide 13 (*Tổng hợp hiệu năng V0–V5*) | Đọc bảng tổng hợp duy nhất cho cả 6 phiên bản trên đủ 3 độ phân giải: V1 đạt GM **3,99×** (large 11,21×), V2 đạt **25,06×** (6,28× so với V1), V3 đạt **43,67×** (1,74× so với V2), V4 đạt **45,07×** (1,03× so với V3), và V5 đạt **46,52×** (large **56,89×**; `site2/large` từ 5897,7 ms xuống còn **60,0 ms**). Toàn bộ đều khớp V0 (Max RGB = 0, 0 B rò rỉ). |
| 13:45 – 15:00 | 1:15 | Slide 14–15 (*Dịch chuyển điểm nghẽn*, *Vì sao tối ưu S6 sau V3?*) | Giải thích vì sao điểm nghẽn dịch chuyển: ở V1, S5 chiếm 90–99% tổng thời gian nên V2 và V3 tập trung giải phóng S5. Sau V3, tại `site2/large`, S5 giảm từ 30,57 xuống 12,52 ms (2,44×) nhưng S6 đứng ở 29,15 ms — chiếm **45,9%** tổng thời gian (63,51 ms). Theo Amdahl, ngay cả khi S6 nhanh gấp đôi thì toàn pipeline cũng chỉ tăng tối đa ~1,30×. |
| 15:00 – 17:00 | 2:00 | Slide 16–17 (*NSYS V4*, *NCU V4*) | Dùng bảng đối chiếu NSYS V4 chỉ rõ 3 thao tác dựng canvas của V3 (clear + copy A + gather B) gộp thành 1 `render_canvas_kernel` ở V4; ở benchmark chuẩn S6 giảm 29,15 → 27,49 ms trên `site2/large` (GM 9 ca: S6 **1,06×**, toàn pipeline **1,03×**, nhanh hơn 6/9 ca). Chuyển sang `ncu-v4.png`: tổng DRAM đọc + ghi tăng **+26,0%** (310,8 → 391,7 MB), L2 hit giảm 76,2% → 70,8% (lưu ý `cudaMemset` của V3 nằm ngoài counter NCU). |
| 17:00 – 18:15 | 1:15 | Slide 18 (*Đối chứng V5 theo độ phân giải*) | Trình bày bảng tóm tắt V5 theo 3 cỡ ảnh (`small`, `medium`, `large`): đoạn pre-S4 (H2D + S1–S3) tăng tốc ổn định 1,26–1,29× (GM **1,28×**, `site2/large` giảm 11,75 → 9,45 ms), đối chứng thuần túy Dual/Seq đạt GM **1,01×** (8/9 ca nhanh hơn), nhanh hơn V4 ở **9/9** ca chuẩn (GM **1,03×**). |
| 18:15 – 19:30 | 1:15 | Slide 19 (*NSYS V5: chồng lấp stream và đánh đổi*) | Dùng `nsys-v5.png` chứng minh chồng lấp GPU thực sự **16,6–24,5%** (2,05–2,89 ms) so với 0,0% ở V4/V5 seq; `H2D → S4 start` trong trace ở `site2/large` rút từ 23,19 ms (V4) xuống **17,66 ms** (V5 dual); Peak VRAM tăng **+64,3 MiB** (269,8 → 334,1 MiB, nằm gọn trong 16 GB của T4; 0 B rò rỉ). Nhấn mạnh khi chạy đủ 4 lượt warm-up để ổn định xung nhịp GPU, V5 nhanh hơn V4 ở cả **9/9** cấu hình chuẩn và giữ nguyên Max RGB = 0. Chuyển lời cho Chương. |

## Danh mục hiện vật cần mở sẵn khi quay

- `build/slides/project.pdf`: mở toàn màn hình chế độ 16:9 tại Slide 12–19.
- `slides/generated/ncu-v4.png`, `slides/generated/nsys-v5.png`: ảnh Nsight phóng to rõ đơn vị nếu cần zoom.

Lưu ý khi quay: giữ tốc độ nói đều, đọc rõ đơn vị (ms, MB, ×, %), nhấn mạnh nguyên tắc toàn bộ V0–V5 được đo trong cùng một phiên Colab Tesla T4 và warm-up đầy đủ để đảm bảo kỷ luật thực nghiệm.
