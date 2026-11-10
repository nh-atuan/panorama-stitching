<!-- Authors: Nguyen Ho Anh Tuan (23120185). External source: none. -->

# Nhật ký tối ưu hóa APOD (CSC14120 - Nhóm 16)

Tài liệu theo dõi các chu trình tối ưu hóa song song theo quy trình **APOD (Assess → Parallelize → Optimize → Deploy)** từ bài giảng của Thầy Phạm Trọng Nghĩa (FIT HCMUS). Toàn bộ dữ liệu đo đạc chi tiết và bằng chứng profiling tương ứng được lưu trữ tại [thư mục kết quả thực nghiệm trên Google Drive](https://drive.google.com/drive/folders/1uJ-4_kgVONvIt5NQIPzdEWTIPrg8Sue1?usp=sharing).

---

## 1. Bảng theo dõi APOD Log tổng thể

| Ver. | Change (One thing!) | Hypothesis | Time Total (ms) | Speedup vs V0 (CPU) | Speedup vs Prev Ver | Correctness (Tolerance) | Conclusion |
|---|---|---|---|---|---|---|---|
| **v0** | CPU Sequential Baseline | Chuẩn tham chiếu CPU ban đầu | Theo từng size | 1.0x | - | Reference | Baseline |
| **v1** | Basic CUDA (All stages) | Chuyển toàn bộ 6 stage lên GPU theo Device-resident để loại bỏ truyền nhận trung gian | S: 1.2x – 2.5x<br>M: 2.0x – 3.5x<br>L: 9.5x – 11.9x | 1.2x – 11.9x | 1.2x – 11.9x | Khớp V0 (pixel max diff = 0) | **Keep** |
| **v2** | Parallel RANSAC & Inlier Reduction (S5) | P6 V1: S5 chiếm 89.86–99.17% ở 9 cặp chuẩn; V2 giảm S5 1.69–65.73× | Small: 21.51–372.63<br>Medium: 27.76–142.03<br>Large: 81.16–258.52 ms | 8.21–70.20× (V0 P6, lịch sử) | 1.59–43.18× (V1 cùng phiên P7) | P7-T04: synthetic đạt ngưỡng, H/canvas nhất quán; memcheck 0 lỗi | **Keep** |
| **v3** | *(Chưa chốt)* | Lập sau khi hoàn thành V2 cùng số đo profiling | | | | | |
| **v4** | *(Chưa chốt)* | Lập sau khi hoàn thành V3 cùng số đo profiling | | | | | |
| **v5** | *(Chưa chốt)* | Lập sau khi hoàn thành V4 cùng số đo profiling | | | | | |
| **v6** | *(Chưa chốt)* | Lập sau khi hoàn thành V5 cùng số đo profiling | | | | | |

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
