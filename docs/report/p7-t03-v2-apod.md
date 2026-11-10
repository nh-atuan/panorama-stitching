<!-- Authors: Le Thuong De (23120232). External source: none. -->

# P7-T03 — Benchmark V2 và profiling Nsight

Người thực hiện: Lê Thượng Đế (23120232). Benchmark V2 và bộ profiling được chạy trên Colab Tesla T4 ngày 10/11/2026. V0/V1 P6 là số liệu chính thức từ lượt T4 ngày 06/11/2026. V1 P7 được đo lại trong cùng lượt với V2 để làm phép so sánh tốc độ chính.

## 1. Assess — tình trạng trước tối ưu

P6-T03 đo V1 trên Tesla T4, warm-up và 5 lượt cho mỗi cấu hình. Trong 9 cấu hình chuẩn, S5 chiếm 89,86–99,17% `Total_ms`; thời gian S5 chính thức P6 nằm trong khoảng 358,190–921,205 ms. Thời gian toàn pipeline V1 P6 là 364,491–928,958 ms. V1 chậm nhất ở `site2/small` và nhanh nhất ở `site3/small` theo tổng thời gian tuyệt đối của bộ ảnh này.

P7 dùng cùng bản build cho V1 và V2 trong một phiên T4. P6 V0 được giữ làm baseline CPU lịch sử theo quyết định không đo lại V0 ở P7. Vì các phiên đo P6/P7 khác ngày, speedup V2/V0 được báo là đối chiếu lịch sử; speedup V2/V1 trong cùng phiên P7 là phép so sánh thực nghiệm chính. Có mâu thuẫn giữa báo cáo micro-profiling P6-T05 tại [mục 4.1](4.1-v1-profiling-and-bottlenecks.md), vốn kết luận S5 dưới 5% và S2/S4/S6 là hotspot, với benchmark full-pipeline chính thức P6-T03 bên dưới, vốn đo S5 chiếm 89,86–99,17%. Phân tích P7 này dùng CSV production end-to-end của P6-T03 làm căn cứ chọn bottleneck; micro-profile cũ chỉ mô tả lượt chạy riêng của kernel, không đại diện cho thời gian pipeline.

### Thời gian tuyệt đối V1 P6 và V2

tất cả số dưới đây là trung bình 5 lượt, đơn vị ms. Cột V1 P6 là benchmark chính thức, không lấy từ lượt V1 P7.

| Site | Size | V1 P6 total | V1 P6 S5 | V1 P6 S6 | V1 P7 total | V2 total | V2 S5 | V2 S6 | V2/V1 P7 |
|---|---|---|---|---|---|---|---|---|---|
| site1 | small | 580.865 | 575.386 | 2.422 | 582.068 | 72.244 | 65.970 | 2.314 | 8.06x |
| site1 | medium | 517.468 | 506.704 | 5.226 | 512.828 | 54.528 | 43.194 | 5.063 | 9.40x |
| site1 | large | 409.647 | 373.023 | 19.725 | 410.034 | 258.520 | 220.453 | 19.753 | 1.59x |
| site2 | small | 933.350 | 926.462 | 3.574 | 928.958 | 21.515 | 14.015 | 3.425 | 43.18x |
| site2 | medium | 871.124 | 857.645 | 7.486 | 866.375 | 27.756 | 13.487 | 7.352 | 31.21x |
| site2 | large | 502.389 | 453.523 | 28.690 | 499.457 | 81.156 | 30.597 | 28.742 | 6.15x |
| site3 | small | 365.742 | 359.870 | 2.980 | 364.491 | 112.324 | 105.838 | 2.997 | 3.25x |
| site3 | medium | 389.047 | 377.977 | 5.989 | 392.054 | 142.031 | 130.400 | 5.992 | 2.76x |
| site3 | large | 410.038 | 372.303 | 21.511 | 411.083 | 252.474 | 214.215 | 21.474 | 1.63x |

V1 P6 cho thấy S5 tiêu tốn hàng trăm ms cho mỗi cặp: 575,386 ms ở `site1/small`, 921,205 ms ở `site2/small`, và 358,190 ms ở `site3/small`. Cùng lúc đó S6 ở V1 P6 chỉ 2,422–28,751 ms. Đây là cơ sở định lượng để chọn S5 làm mục tiêu P7.

## 2. Parallelize / Optimize — thay đổi V2

V2 thay S5 bằng triển khai RANSAC song song; S1–S4 và S6 tái sử dụng V1. Ý tưởng là phân phối công việc tính điểm các giả thuyết và refit inlier trên GPU, giảm thời gian tuần tự trong S5. P7-T04 ghi nhận sáu synthetic đạt ngưỡng, trạng thái V0/V1/V2 khớp trên 12 cấu hình, mười panorama thành công khớp canvas và Max RGB = 0; memcheck có 0 lỗi, 0 bytes rò rỉ. Xem [báo cáo nghiệm thu V2](p7-v2-verification.md).

## 3. Result — speedup

V2 giảm tổng thời gian so với V1 P7 trên cả chín cấu hình chuẩn: 1,59–43,18×; trung bình nhân 6,25×. S5 riêng lẻ nhanh hơn 1,69–65,73×; trung bình nhân 8,26×. Mức cải thiện pipeline phụ thuộc vào tỷ trọng S5 ban đầu: các cấu hình site1/site3 large chỉ tăng 1,59–1,63× vì các stage khác cùng chiếm tỷ trọng lớn hơn sau tối ưu.

| Site | Size | V0 P6 (ms) | V1 P6 (ms) | V1 P7 cùng phiên (ms) | V2 (ms) | V2/V0 P6 lịch sử | V2/V1 P7 cùng phiên |
|---|---|---:|---:|---:|---:|---:|---:|
| site1 | small | 1299.988 | 580.865 | 582.068 | 72.244 | 17.99x | 8.06x |
| site1 | medium | 1672.254 | 517.468 | 512.828 | 54.528 | 30.67x | 9.40x |
| site1 | large | 4872.060 | 409.647 | 410.034 | 258.520 | 18.85x | 1.59x |
| site2 | small | 1118.264 | 933.350 | 928.958 | 21.515 | 51.98x | 43.18x |
| site2 | medium | 1731.547 | 871.124 | 866.375 | 27.756 | 62.38x | 31.21x |
| site2 | large | 5696.801 | 502.389 | 499.457 | 81.156 | 70.20x | 6.15x |
| site3 | small | 922.186 | 365.742 | 364.491 | 112.324 | 8.21x | 3.25x |
| site3 | medium | 1352.599 | 389.047 | 392.054 | 142.031 | 9.52x | 2.76x |
| site3 | large | 3906.304 | 410.038 | 411.083 | 252.474 | 15.47x | 1.63x |

V2/V0 P6 lịch sử trên chín cấu hình là 8,21–70,20×, trung bình nhân 24,22×. Đây không phải phép so sánh cùng phiên Colab. Bộ P6 ZIP không có manifest ảnh, do đó chưa thể xác nhận hash dataset giữa hai lần đo từ hai gói evidence; chỉ dùng kết quả này theo baseline V0 chính thức đã lưu của nhóm.

### Phân bố thời gian V2 theo kích thước

Tỷ lệ trung bình trên ba site chuẩn; tính theo `Total_ms` end-to-end. `Other` là phần ngoài sáu stage, gồm truyền và điều phối.

| Size | S1 | S2 | S3 | S4 | S5 | S6 | Other |
|---|---|---|---|---|---|---|---|
| small | 0.58% | 3.32% | 1.13% | 1.25% | 83.56% | 7.26% | 2.90% |
| medium | 1.07% | 4.24% | 1.47% | 1.13% | 73.20% | 13.33% | 5.55% |
| large | 1.35% | 3.25% | 1.29% | 0.36% | 69.27% | 17.19% | 7.28% |

S5 vẫn là stage đơn lẻ lớn nhất ở cả 9 cấu hình chuẩn: 13,487–220,453 ms, tương đương 37,70–94,23% tổng thời gian. Trung bình tỷ trọng S5 giảm từ 83,56% ở small xuống 73,21% ở medium và 69,27% ở large. S6 tăng từ 7,26% lên 13,33% và 17,19% theo kích thước. Ở `site2/large`, S5 mất 30,597 ms, S6 mất 28,742 ms; khoảng cách chỉ 1,855 ms nên hai stage là hotspot ngang nhau ở trường hợp này.

![Tỷ trọng thời gian từng stage V2](../../results/p7-t03-comparison-20261110T051250Z/v2_stage_share.png)

## 4. Nsight Systems và Nsight Compute

Bốn NSYS trace bao phủ `site1/small`, `site1/medium`, `site1/large`, `site2/large`; tám NCU report đo riêng `compute_hypotheses` và `refit_homography` ở bốn cấu hình này. Mỗi command profiling chạy pipeline một lần sau warm-up. Bảng kernel duration của NSYS gộp hai lần pipeline và 126 launch `compute_hypotheses`, vì vậy dùng tỷ lệ dưới đây để nhận diện hotspot bên trong phiên profiler, không so thời gian trực tiếp với benchmark 5 runs.

| Cấu hình | compute_hypotheses: thời gian / tỷ lệ GPU kernel | refit_homography: thời gian / tỷ lệ | gather_b_kernel (S6): thời gian / tỷ lệ |
|---|---:|---:|---:|
| site1/small | 174.93 ms / 86.1% | 16.71 ms / 8.2% | 5.07 ms / 2.5% |
| site1/medium | 156.88 ms / 74.6% | 24.27 ms / 11.5% | 16.90 ms / 8.0% |
| site1/large | 526.96 ms / 88.6% | 7.30 ms / 1.2% | 37.04 ms / 6.2% |
| site2/large | 107.82 ms / 40.3% | 22.69 ms / 8.5% | 103.99 ms / 38.9% |

`compute_hypotheses` chiếm 74,6–88,6% tổng kernel time ở ba cấu hình site1. Với `site2/large`, hai kernel `compute_hypotheses` và `gather_b_kernel` chiếm lần lượt 40,3% và 38,9% tổng kernel time profiler, phù hợp số timing end-to-end cho thấy S5/S6 gần ngang nhau.

NCU xác nhận occupancy đạt được của `compute_hypotheses` khoảng 24,98–25,00%, với 100 registers/thread; `refit_homography` đạt 12,50%, 118 registers/thread, block 256 threads và grid chỉ một block. DRAM throughput báo cáo rất thấp (0,04–0,05% cho compute hypotheses và 0,01% cho refit trong các mẫu này); dữ liệu không chỉ ra nghẽn băng thông DRAM. `refit_homography` có khoảng 1,1 active threads/warp và 22,7–22,9 warp cycles/instruction, gợi ý thực thi kém hiệu quả do mức hoạt động lane thấp; đây là chỉ dấu cần đào sâu, không tự nó xác định nguyên nhân code.

Ảnh NSYS và các trang NCU đã lưu trong `results/nsight/`: một PNG timeline `site1/medium`, cùng bốn PDF một trang gồm Summary và Details của `compute_hypotheses` cho `site1/medium` và `site2/large`. Các PDF là ảnh giao diện Nsight độ phân giải cao, còn trace/reports gốc `.nsys-rep` và `.ncu-rep` nằm trong gói P7.

![NSYS timeline cho site1/medium](../../results/nsight/nsight-site1-medium.png)

## 5. Analysis và đề xuất vòng kế tiếp

V2 đạt mục tiêu P7: loại bỏ phần lớn thời gian S5 và tạo speedup rõ so với V1, đồng thời kết quả tích hợp giữ độ chính xác đã nghiệm thu. Kết luận APOD cho V2 là **Keep**.

V3 nên tiếp tục ưu tiên `compute_hypotheses` vì đây vẫn là kernel S5 chiếm phần lớn kernel time ở site1. Cần xem lại phân bố công việc 126 launch, thời gian launch/điều phối và các chỉ số warp stalls trong NCU trước khi chọn hướng tối ưu. Với `site2/large`, profiling cần tập trung so S5 với S6; tối ưu riêng S5 có thể cho lợi ích giới hạn vì S6 đã gần bằng. Chưa đề xuất đổi thuật toán hay tham số RANSAC dựa trên các số hiện có.

## 6. Reproducibility và bàn giao

- GPU: Tesla T4, driver 580.82.07; P7 benchmark timestamp `2026-11-10T02:14:29Z`; 5 runs. P6 official timestamp `2026-11-06T13:57:27Z`; 5 runs; V0/V1.
- P6 dataset manifest không có trong ZIP; so sánh P6/P7 cần ghi nhận đây là baseline lịch sử, không cùng phiên.
- P7 có 4 `.nsys-rep`, 8 `.ncu-rep`, CSV raw, CSV metrics NCU, logs, biểu đồ, một ảnh PNG NSYS và bốn trang PDF NCU. Notebook status trong ZIP được tạo trước khi bổ sung ảnh nên vẫn báo chưa có screenshot; các bằng chứng hình ảnh bổ sung nằm ở `results/nsight/`.
- ZIP benchmark và evidence hiện có ở `results/Group16_P7_Comparison_20261110T051250Z.zip`, `results/p6-t03-official.zip`, và `results/Group16_P7_T03_Evidence_20261110T021853Z.zip`. Người phụ trách xác nhận package kết quả đã được chép tới Drive chung `v2/`.
- Bảng comparison có challenge/small nhanh hơn 1,08×; challenge/medium và large báo `NumericalFailure` nhất quán với V0/V1, không có timing để tính speedup.
