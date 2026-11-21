<!-- Authors: Nguyen Ho Anh Tuan (23120185), Le Thuong De (23120232). External source: none. -->

# Nhật ký tối ưu hóa APOD (CSC14120 - Nhóm 16)

Tài liệu theo dõi các chu trình tối ưu hóa song song theo quy trình **APOD (Assess → Parallelize → Optimize → Deploy)** từ bài giảng của Thầy Phạm Trọng Nghĩa (FIT HCMUS). Toàn bộ dữ liệu đo đạc chi tiết và bằng chứng profiling tương ứng được lưu trữ tại [thư mục kết quả thực nghiệm trên Google Drive](https://drive.google.com/drive/folders/1uJ-4_kgVONvIt5NQIPzdEWTIPrg8Sue1?usp=sharing).

---

## 1. Bảng theo dõi APOD Log tổng thể

| Ver. | Change (One thing!) | Hypothesis | Time Total (ms) | Speedup vs V0 (CPU) | Speedup vs Prev Ver | Correctness (Tolerance) | Conclusion |
|---|---|---|---|---|---|---|---|
| **v0** | CPU Sequential Baseline | Chuẩn tham chiếu CPU ban đầu | Theo từng size | 1.0x | - | Reference | Baseline |
| **v1** | Basic CUDA (All stages) | Chuyển toàn bộ 6 stage lên GPU theo Device-resident để loại bỏ truyền nhận trung gian | S: 1.2x – 2.5x<br>M: 2.0x – 3.5x<br>L: 9.5x – 11.9x | 1.2x – 11.9x | 1.2x – 11.9x | Khớp V0 (pixel max diff = 0) | **Keep** |
| **v2** | Parallel RANSAC & Inlier Reduction (S5) | P6 V1: S5 chiếm 89.86–99.17% ở 9 cặp chuẩn; V2 giảm S5 1.69–65.73× | Small: 21.51–372.63<br>Medium: 27.76–142.03<br>Large: 81.16–258.52 ms | 8.21–70.20× (V0 P6, lịch sử) | 1.59–43.18× (V1 cùng phiên P7) | P7-T04: synthetic đạt ngưỡng, H/canvas nhất quán; memcheck 0 lỗi | **Keep** |
| **v3** | Tối ưu vi kiến trúc S5: warp shuffle reduction, shared-memory DLT/SVD và batch scheduling | Giảm thời gian S5 và chi phí điều phối | 21.265–108.170 ms (9 cấu hình chuẩn) | 16.93–89.98×; trung bình nhân 43.10× | 0.99–2.53×; trung bình nhân 1.85× | P8-T04: nghiệm thu T4 đạt, Max RGB = 0; memcheck 0 lỗi | **Keep** |
| **v4** | Single-pass Canvas Fusion (S6) | Gộp memset/copy A/gather B để giảm truy cập canvas | 21.142–107.157 ms (9 ca chuẩn) | 16.98–92.38×; trung bình nhân 43.02× | 0.9971–1.0131×; trung bình nhân 1.0086× | P9-T02: T4 đạt, Max RGB = 0 trên 10 ca thành công; memcheck 0 lỗi | **Keep (Production Baseline)** — giảm 3→1 pass dựng canvas; lợi ích thời gian nhỏ do DRAM lấy mẫu tăng |
| **v5** | Dual-stream Pipeline (H2D + S1–S3 song song 2 ảnh) | Chạy bất đồng bộ nhánh ảnh A và B trước S4 trên 2 CUDA stream | 20.686–102.925 ms (9 ca chuẩn) | 21.29–109.07× | 1.010–1.605×; trung bình nhân 1.027× (ca chính `site2/large` 1.029×, pre-S4 1.207×) | P10-T04: T4 đạt, Max RGB = 0 so với V4 & sequential; memcheck 0 lỗi | **Case Study** — pre-S4 giảm ~20%, nhưng toàn pipeline chưa đạt ngưỡng 1.05× do giới hạn SM trên T4 và tỷ trọng S5/S6; giữ V4 làm production |

---

## 2. Chi tiết từng chu trình APOD

### Chu trình V0 -> V1: Parallelize (Cài đặt GPU cơ bản)
- **Assess:** Đo V0 tuần tự trên CPU, S2, S4 và S6 là 3 stage chiếm phần lớn thời gian.
- **Parallelize:** Chuyển cả 6 stage lên GPU theo mô hình `Device-resident`. Giữ nguyên thuật toán, ánh xạ đơn giản (1 thread/pixel, 1 thread/keypoint).
- **Deploy:** Kiểm chứng trên Colab T4, khớp V0 tuyệt đối (max error 0). Speedup Total đạt từ 1.2x đến 11.9x. Kết luận: **Keep**.

### Chu trình V1 -> V2: Optimize Round 1 (Giải phóng Hotspot S5)
- **Assess (Đánh giá V1):** 
  - Benchmark P6-T03 chỉ ra S5 chạy chậm hơn CPU (0.01x – 0.46x) và chiếm từ **90.7% đến 98.9%** tổng thời gian V1.
  - NSYS và NCU xác nhận: S5 chỉ có 1 thread giải DLT 4 điểm trên stack Device (32 KiB), occupancy chỉ 12.5%, bước refit chạy `<<<1, 1>>>`, host launch 63 đợt kernel.
- **Hypothesis (Giả thuyết V2):** Song song hóa việc giải DLT 4 điểm qua đa thread, tính inlier reduction song song và tối ưu hóa cơ chế launch sẽ giảm mạnh thời gian S5, mang lại speedup toàn pipeline tăng vọt.
- **Change ONE thing:** Thiết kế lại kernel S5 và cập nhật `v2_pipeline`.
- **Deploy:** Đối chiếu kết quả H và canvas với V0/V1 trên synthetic và dataset thật; đo benchmark V2 trên Colab T4.



### Chu trình V1 -> V2: Optimize Round 1 (kết quả P7-T03)

- **Assess:** P6-T03 trên Tesla T4 cho thấy V1 S5 chiếm 89.86–99.17% `Total_ms` ở 9 cấu hình chuẩn, với thời gian S5 358.190–921.205 ms. Dùng các thời gian V1 P6 chính thức làm lịch sử; V1 P7 chạy cùng lượt V2 là baseline để tính speedup đồng phiên.
- **Parallelize / Optimize:** V2 thay S5 bằng RANSAC/refit chạy song song; tái sử dụng S1–S4/S6 V1. Thời gian S5 giảm 1.69–65.73×, tốc độ toàn pipeline tăng 1.59–43.18× so với V1 cùng phiên P7. Trung bình nhân trên 9 cấu hình lần lượt là 8.26× cho S5 và 6.25× cho pipeline.
- **Deploy:** P7-T04 ghi nhận các cổng correctness và memcheck đạt. Benchmark P7 dùng warm-up + 5 runs trên Tesla T4. V2 S5 vẫn là stage lớn nhất trong cả 9 cấu hình chuẩn (13.487–220.453 ms); tại `site2/large`, S6 gần ngang S5 (28.742 ms và 30.597 ms). Kết luận: **Keep V2**. Hướng V3 cần profiling sâu `compute_hypotheses`; ở `site2/large` tiếp tục kiểm tra S6.
- **Bằng chứng:** [báo cáo P7-T03](report/p7-t03-v2-apod.md); P6 baseline, P7 benchmark và trace/report gốc được liệt kê tại mục reproducibility của báo cáo.


### Chu trình V3 -> V4: Optimize Round 3 (P9-T05)

- **Assess:** P8 xác định S6 là hotspot ở site2/large (45,7% tổng thời gian V3). P9 đo lại toàn bộ V0–V4 cùng Tesla T4, một warm-up + năm runs/cấu hình, cùng source và dataset.
- **Optimize:** V4 thay chuỗi xóa canvas, copy A và gather/blend B bằng `render_canvas_kernel`; giữ setup, quy tắc số học và S1–S5 của bản đối chứng.
- **Result:** V4/V3 trung bình nhân 1,0086× trên chín ca chuẩn; 8/9 ca nhanh hơn. Riêng S6 đạt 1,0357×. Tại site2/large, total giảm 62,874 → 62,197 ms; S6 giảm 28,712 → 28,190 ms. Năm khối đo luân phiên cho median 1,0270×, min–max 0,9774–1,0409×, 4/5 khối cùng chiều; chưa đạt mức cải thiện 5% từng được đề xuất.
- **Verification:** Source production khớp `ab8df98d` đã nghiệm thu P9-T02. Challenge medium/large giữ NumericalFailure; không tính speedup cho ca lỗi. Đủ 8 NSYS và 12 NCU. NSYS xác nhận 3 → 1 thao tác dựng canvas mỗi lượt. NCU ghi nhận DRAM đọc + ghi tăng 13,6–26,0% trong bốn ca lấy mẫu, phạm vi gồm copy A + gather B ở V3 và renderer ở V4. Memset V3 nằm ngoài tổng counter.
- **Bằng chứng:** [P9-T05](report/p9-t05-v4-apod.md), [notebook benchmark/profiling](../notebooks/Group16_P9_T05_Benchmark_Profiling.ipynb), [nghiệm thu P9-T02](report/p9-v4-verification.md).

### Chu trình V4 -> V5: Optimize Round 4 — Thử nghiệm hai CUDA Stream (P10-T05)

- **Assess:** Baseline [P10-T01](report/p10-t01-pres4-baseline.md) trên Tesla T4 ghi nhận đoạn pre-S4 (H2D + S1–S3 của cả hai ảnh) chiếm 11,20% (`site3/large`), 12,23% (`site1/large`) và 21,44% (`site2/large`, 15,288 ms) tổng thời gian V4. Hai ảnh đầu vào độc lập về dữ liệu trước S4.
- **Optimize:** Tách pipeline trước S4 thành hai nhánh chạy bất đồng bộ trên hai non-blocking CUDA streams (`streamA`, `streamB`) với scratch, `DeviceCounts` và pinned count buffer riêng; điều phối theo mô hình prefix/suffix (H2D + S1 + S2 candidates → `cudaEventQuery` → S2 top-K + S3), hội tụ tại control stream bằng `cudaStreamWaitEvent` trước khi hợp nhất đếm và chạy S4–S6. Kèm chế độ đối chứng `--v5-schedule sequential`.
- **Result:** Trên Tesla T4 (5 runs + 1 warm-up), đoạn pre-S4 tại ca chính `site2/large` giảm từ ~15,288 ms xuống ~12,680 ms (nhanh hơn **1,207×**, tiết kiệm ~2,6 ms). Toàn pipeline đạt 20,686–102,925 ms trên 9 ca chuẩn (21,29–109,07× so với V0), trung bình nhân **1,027×** so với V4 (`site2/large`: 61,655 → 59,941 ms, **1,029×**).
- **Verification & Profiling:** [P10-T04](report/p10-v5-verification.md) xác nhận 6 cặp synthetic và 12 cấu hình thật đạt ngưỡng tuyệt đối (drift = 0 px, Max RGB = 0 so với V4 và giữa `dual`/`sequential`; `compute-sanitizer` 0 lỗi, 0 byte rò rỉ). Nsight Systems cho thấy H2D chồng lấn tốt với S1 nhờ 3 Copy Engine của T4, nhưng các kernel tính toán nặng ở S2/S3 bão hòa 40 SM nên mức overlap bị giới hạn, cộng thêm ~0,15–0,25 ms overhead thăm dò host.
- **Conclusion:** Do speedup toàn pipeline chưa vượt ngưỡng kỳ vọng 1,05×, nhóm giữ **V4** làm bản production chính thức và giữ nguyên **V5** trong mã nguồn như một nghiên cứu chuyên sâu (case study) về giới hạn đa stream trên Tesla T4.
- **Bằng chứng:** [P10-T05](report/p10-t05-v5-apod.md), [notebook benchmark/profiling V5](../notebooks/Group16_P10_T05_Benchmark_Profiling.ipynb), [nghiệm thu P10-T04](report/p10-v5-verification.md).
