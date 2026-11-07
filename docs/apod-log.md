<!-- Authors: Nguyen Ho Anh Tuan (23120185). External source: none. -->

# Nhật ký tối ưu hóa APOD (CSC14120 - Nhóm 16)

Tài liệu theo dõi các chu trình tối ưu hóa song song theo quy trình **APOD (Assess → Parallelize → Optimize → Deploy)** từ bài giảng của Thầy Phạm Trọng Nghĩa (FIT HCMUS). Toàn bộ dữ liệu đo đạc chi tiết và bằng chứng profiling tương ứng được lưu trữ tại [thư mục kết quả thực nghiệm trên Google Drive](https://drive.google.com/drive/folders/1uJ-4_kgVONvIt5NQIPzdEWTIPrg8Sue1?usp=sharing).

---

## 1. Bảng theo dõi APOD Log tổng thể

| Ver. | Change (One thing!) | Hypothesis | Time Total (ms) | Speedup vs V0 (CPU) | Speedup vs Prev Ver | Correctness (Tolerance) | Conclusion |
|---|---|---|---|---|---|---|---|
| **v0** | CPU Sequential Baseline | Chuẩn tham chiếu CPU ban đầu | Theo từng size | 1.0x | - | Reference | Baseline |
| **v1** | Basic CUDA (All stages) | Chuyển toàn bộ 6 stage lên GPU theo Device-resident để loại bỏ truyền nhận trung gian | S: 1.2x – 2.5x<br>M: 2.0x – 3.5x<br>L: 9.5x – 11.9x | 1.2x – 11.9x | 1.2x – 11.9x | Khớp V0 (pixel max diff = 0) | **Keep** |
| **v2** | Parallel RANSAC & Inlier Reduction (S5) | S5 chiếm 98% runtime V1 do 1-thread DLT & launch overhead; song song hóa giả thuyết DLT và inlier reduction sẽ gỡ nghẽn | | | | | (keep / revert) |
| **v3** | Shared Memory Tiling (S4) | S4 bị memory-bound do đọc lặp Global Memory; nạp descriptor B vào Shared Memory sẽ giảm DRAM traffic | | | | | (keep / revert) |
| **v4** | Shared Memory Halo Tiling (S2) | S2 đọc phân tán vòng tròn FAST; tile hóa ảnh kèm halo buffer giảm uncoalesced và warp divergence | | | | | (keep / revert) |

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

