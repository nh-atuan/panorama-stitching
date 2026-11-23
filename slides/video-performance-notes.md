<!-- Authors: Le Thuong De (23120232). External source: none. -->

# P10-T07 / P11-T05 — Lời dẫn chi tiết phần Hiệu năng (Đế · 7 phút 30 giây)

Đế trình bày **Phần 3: Performance results and analysis** trong **7 phút 30 giây (12:00 – 19:30)**, nằm giữa khung 6–9 phút theo yêu cầu đề bài. [Kịch bản chung 20–30 phút](video-outline.md)

| Mốc | Thời lượng | Slide / Tư liệu | Lời dẫn chính |
|---|---:|---|---|
| 12:00 – 12:45 | 0:45 | Slide 12 (*How the experiment is controlled*) | Nêu quy tắc đo chuẩn trên Tesla T4 (`sm_75`, `-O2 --fmad=false`): 9 ca chuẩn (3 site × 3 cỡ) + ca `challenge`, 1 warm-up + 5 runs đo, tách riêng S1–S6, H2D, D2H, `Total_Kernel_ms` và `Total_ms`. Nhấn mạnh chỉ so speedup trong **cùng một phiên đo** (P9 cho V0–V4; P10 cho V0/V4/V5). |
| 12:45 – 13:30 | 0:45 | Slide 10 (*V0--V5 timing summary*) | Đọc nhanh bước nhảy tổng thể trong phiên P9 trên 9 ca chuẩn: V1 đạt GM **3,80×**, V2 đạt **23,37×** (+6,16× so với V1), V3 đạt **42,65×** (+1,83× so với V2), V4 đạt **43,02×** (`site2/large` từ 5746,068 ms xuống 62,197 ms, tương đương 92,38×). Giới thiệu phiên P10-T05 đo V5 Dual đạt 58,926 ms ở `site2/large` (**110,29×** so với V0 P10, GM **49,88×**). |
| 13:30 – 14:45 | 1:15 | Slide 11 & 14 (*Bottleneck shifts*, *Why S6 after V3?*) | Giải thích vì sao điểm nghẽn dịch chuyển: ở V1 (P6), S5 chiếm 90–99% tổng thời gian nên V2 và V3 tập trung giải phóng S5. Sau V3 (P8), tại `site2/large`, S5 giảm còn 12,200 ms nhưng S6 đứng ở 28,468 ms — chiếm **45,7%** tổng thời gian. Theo Amdahl, ngay cả khi S6 nhanh gấp đôi thì toàn pipeline cũng chỉ tăng tối đa ~1,30×. |
| 14:45 – 15:45 | 1:00 | Slide 17 (*V4 benchmark: P9*) & Slide 20 | Trình bày kết quả P9: V4 nhanh hơn V3 ở **8/9 ca chuẩn**, S6 nhanh hơn GM **1,0357×**, toàn pipeline đạt GM **1,0086×**. Tại `site2/large`, S6 giảm 28,712 $\rightarrow$ 28,190 ms; 5 khối đo luân phiên cho median **1,0270×** (4/5 khối cùng chiều, khoảng 0,9774–1,0409×). Nêu rõ kết quả chưa đạt ngưỡng kỳ vọng 5%. |
| 15:45 – 17:00 | 1:15 | Slide 18 (*NSYS V4*) & Slide 19 (*NCU V4*) | Dùng hình `nsys-v4.png` chỉ rõ 3 thao tác dựng canvas của V3 (clear + copy A + gather B) gộp thành 1 `render_canvas_kernel` ở V4. Chuyển sang `ncu-v4.png`: trong các kernel lấy mẫu tại `site2/large`, tổng DRAM đọc + ghi lại tăng **+26,0%** (310,78 $\rightarrow$ 391,69 MB), tỷ lệ hit L2 giảm 76,19% $\rightarrow$ 70,75%. Lưu ý trung thực rằng memset V3 nằm ngoài phạm vi counter NCU, và luôn dùng benchmark 5 run (không dùng thời gian trong trace) để kết luận tốc độ. |
| 17:00 – 18:15 | 1:15 | Slide 21 & 22 (*V5 architecture*, *V5 benchmark P10*) | Giải thích động lực P10: baseline P10-T01 cho thấy đoạn pre-S4 (H2D + S1–S3) chiếm **21,44%** (`15,288 ms`) tại `site2/large`. V5 tách hai nhánh ảnh A/B lên hai non-blocking CUDA stream với chế độ đối chứng `--v5-schedule sequential`. Số đo P10-T05 thực tế cho thấy Pre-S4 nhanh hơn GM **1,257×** (`site2/large` giảm **13,700 → 10,971 ms**, **1,249×**), đối chứng thuần túy Dual/Seq đạt GM **1,036×**, toàn pipeline đạt GM **49,88×** so với V0. |
| 18:15 – 19:30 | 1:15 | Slide 23 & 24 (*NSYS V5 overlap*, *Stability & APOD*) | Dùng hình `nsys-v5.png` chứng minh chồng lấn GPU thực sự **16,6%–24,5%** (2,05–2,89 ms) so với 0,0% ở V4/V5 seq; `H2D → S4 start` ở `site2/large` rút từ 23,19 ms (V4) xuống **17,66 ms** (V5 dual); Peak VRAM tăng đúng **+64,30 MiB** (269,76 → 334,06 MiB, 0 B rò rỉ). Nêu 5 khối luân phiên `site2/large` đạt median **1,067×** nhưng chỉ **3/5 khối** cùng chiều (< 4/5) → chốt giữ **V4** làm production baseline, giữ **V5** làm case study concurrency. Chuyển lời cho Chương. |

## Danh mục hiện vật cần mở sẵn khi quay

- `build/slides/project.pdf`: mở toàn màn hình chế độ 16:9 tại Slide 10–23.
- `docs/report/p9-t05-v4-apod.md` và `docs/report/p10-t05-v5-apod.md`: mở sẵn tab để đối chiếu nhanh nếu cần chỉ nguồn số liệu.
- `slides/generated/nsys-v4.png`, `slides/generated/ncu-v4.png` và `slides/generated/screenshots/`: ảnh chụp Nsight phóng to rõ đơn vị (ms, MB, %).
- `docs/apod-log.md`: bảng tổng hợp V0–V5 nhất quán với `README.md` và `Group16_Final.ipynb`.

Lưu ý khi quay: giữ tốc độ nói đều, đọc rõ đơn vị (ms, MB, ×, %), nhấn mạnh sự khác biệt giữa hai phiên đo P9 và P10 để thể hiện kỷ luật thực nghiệm.
