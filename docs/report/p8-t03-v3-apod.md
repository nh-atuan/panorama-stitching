<!-- Authors: Le Thuong De (23120232). External source: none. -->

# P8-T03 — Benchmark V3 và profiling Nsight

Người thực hiện: Lê Thượng Đế (23120232). Benchmark đã chạy ngày 16/11/2026 trên Colab Tesla T4. Đã đo V0–V3 cùng phiên; profiling đang được thu thập, chưa chốt Keep/Revert hoặc hoàn tất bàn giao Drive.

## 1. Bottleneck

[Kết quả P7-T03](p7-t03-v2-apod.md) cho thấy `compute_hypotheses` của V2 đạt occupancy khoảng 25% với 100 registers/thread trong các mẫu NCU đã thu. Trên ba cấu hình site1, kernel này chiếm 74,6–88,6% tổng kernel time trong trace NSYS. Các trace có cả warm-up và lượt chạy chẩn đoán; tỷ trọng đó dùng để xác định hotspot, không thay thế benchmark không có profiler.

P8 tiếp tục tối ưu S5 để giảm chi phí tính giả thuyết và điều phối kernel. Tại site2/large của P7, S5 và S6 đã có thời gian gần nhau; vì vậy cần đo cả pipeline để xác định lợi ích thực tế của thay đổi S5.

## 2. Idea

V3 thay cách thực thi S5 bằng warp shuffle reduction cho MSAC, đặt ma trận DLT/SVD trong shared memory và điều chỉnh batch scheduling. Giả thuyết cần kiểm chứng là những thay đổi này giảm thời gian S5 và cải thiện tốc độ toàn pipeline. Occupancy cao hơn chỉ là một chỉ số chẩn đoán; kết luận hiệu quả phải dựa trên timing.

## 3. Implementation

Kernel nằm trong `src/v3/s5/`; `src/v3/v3_pipeline.cu` gọi `v3_homography` ở vị trí S5 và dùng lại hạ tầng pipeline GPU cùng các stage S1–S4/S6 của V1. `compute_hypotheses` dùng `__launch_bounds__(128, 4)`. Các thay đổi được đánh giá chung như phiên bản V3; lượt đo này không tách riêng tác dụng từng thay đổi bằng ablation.

Notebook [Group16_P8_T03_Benchmark_Profiling.ipynb](../../Group16_P8_T03_Benchmark_Profiling.ipynb) ghim checkout `b3c79d783aa79401cfe2b2a03add1e03f55a32d0` và đối chiếu `src/`, `scripts/build.py` với SHA production đã nghiệm thu `1cf86ad939fb821c3b2ee50fca47375ea8ae874a`. Build dùng script của repo và kiến trúc `sm_75`.

## 4. Result

V3 nhanh hơn V2 ở 8/9 cấu hình chuẩn, với trung bình nhân speedup 1.85×. Speedup so với V0 cùng phiên đạt 16.93–89.98×, trung bình nhân 43.10×. Riêng S5 có trung bình nhân speedup 2.27× so với V2.

Tất cả thời gian dưới đây là trung bình 5 runs sau một warm-up, đơn vị ms. V0–V3 được đo trên cùng Tesla T4, driver 580.82.07, CPU Intel Xeon 2,00 GHz. Build dùng nvcc 13.0.88. Thời điểm bắt đầu benchmark: `2026-11-16T07:13:54+00:00`.

| Site | Size | V0 ms | V1 ms | V2 ms | V3 ms | V3/V0 | V3/V1 | V3/V2 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| site1 | small | 1203.424 | 583.420 | 71.859 | 32.869 | 36.61× | 17.75× | 2.19× |
| site1 | medium | 1581.937 | 517.381 | 54.345 | 31.043 | 50.96× | 16.67× | 1.75× |
| site1 | large | 4791.904 | 409.836 | 258.028 | 108.170 | 44.30× | 3.79× | 2.39× |
| site2 | small | 1114.905 | 934.151 | 29.053 | 21.265 | 52.43× | 43.93× | 1.37× |
| site2 | medium | 1917.972 | 871.021 | 27.543 | 27.880 | 68.79× | 31.24× | 0.99× |
| site2 | large | 5610.307 | 497.820 | 81.826 | 62.353 | 89.98× | 7.98× | 1.31× |
| site3 | small | 756.046 | 364.699 | 111.547 | 44.646 | 16.93× | 8.17× | 2.50× |
| site3 | medium | 1565.322 | 390.812 | 141.421 | 55.939 | 27.98× | 6.99× | 2.53× |
| site3 | large | 4069.046 | 408.915 | 252.403 | 100.835 | 40.35× | 4.06× | 2.50× |

| Site | Size | S5 V2 ms | S5 V3 ms | S5 speedup | S5 / V3 total | S6 V3 ms |
|---|---|---:|---:|---:|---:|---:|
| site1 | small | 65.622 | 26.576 | 2.47× | 80.9% | 2.334 |
| site1 | medium | 43.064 | 19.726 | 2.18× | 63.5% | 5.096 |
| site1 | large | 219.506 | 70.180 | 3.13× | 64.9% | 19.759 |
| site2 | small | 19.549 | 13.809 | 1.42× | 64.9% | 3.423 |
| site2 | medium | 13.374 | 13.625 | 0.98× | 48.9% | 7.365 |
| site2 | large | 30.538 | 12.200 | 2.50× | 19.6% | 28.468 |
| site3 | small | 105.344 | 38.466 | 2.74× | 86.2% | 2.864 |
| site3 | medium | 129.884 | 44.428 | 2.92× | 79.4% | 5.884 |
| site3 | large | 214.223 | 62.085 | 3.45× | 61.6% | 21.446 |

![Speedup V3 so với V2 cùng phiên](../../results/p8-t03-20261116/speedup_vs_v2.png)

![Tỷ trọng stage V3](../../results/p8-t03-20261116/stage_share.png)

CV tổng thời gian V3 trên chín cấu hình chuẩn nằm trong khoảng 0,18–1,27%. Site2/medium giảm tốc khoảng 1,2% (27,543 → 27,880 ms); kết quả được giữ nguyên và case này được bổ sung vào ma trận profiling. Site2/small có cả các stage không đổi nhanh hơn khoảng 22–41% trong lượt V3; do đó không quy toàn bộ speedup pipeline của case này cho thay đổi S5. Log timing từng run được giữ để đối chiếu.

Challenge/small có V3 total 112,567 ms và speedup V3/V2 3,32×; CV V3 là 2,69%. Challenge medium/large trả `NumericalFailure` ở cả bốn phiên bản, không có timing để tính speedup. Chín cấu hình chuẩn được dùng khi tính trung bình nhân; challenge không nằm trong phép tổng hợp đó.

Correctness và an toàn bộ nhớ dựa trên [P8-T04](p8-v3-verification.md): sáu synthetic, 12 cấu hình thật, contract CLI/CSV/D2H và hai lượt memcheck T4 đạt. Timing hai runs của lượt kiểm tra contract không được đưa vào các bảng trên.

## 5. Analysis

Sau tối ưu, S5 vẫn là stage lớn nhất ở tám cấu hình chuẩn. Site2/large chuyển sang bị giới hạn nhiều hơn bởi S6: S5 giảm từ 30,538 xuống 12,200 ms, trong khi S6 V3 là 28,468 ms, chiếm 45,7% tổng thời gian. Điều này giải thích vì sao speedup toàn pipeline của case này là 1,31× dù riêng S5 nhanh hơn 2,50×.

### NSYS: thời gian S5 giảm cùng với số launch

NSYS được thu trên cùng năm cấu hình, với mỗi trace gồm một warm-up và một lượt pipeline. Vì vậy bảng này mô tả đúng hai lượt được profiler quan sát, còn benchmark 5 runs ở mục 4 mới là nguồn timing so sánh chính. Ở site1, `compute_hypotheses` giảm từ 126 xuống 32 launch trong trace (giảm 74,6%). Tổng kernel time của nó giảm từ 234,59 xuống 74,22 ms ở small, từ 142,92 xuống 68,54 ms ở medium, và từ 536,71 xuống 210,51 ms ở large. Tỷ trọng của kernel giảm tương ứng từ 84,6%, 75,0%, 88,3% xuống 65,2%, 51,5%, 71,6%.

| Cấu hình | `compute_hypotheses` V2 → V3 (ms) | Tỷ trọng V2 → V3 | Launch V2 → V3 | `gather_b_kernel` V2 → V3 (ms) |
|---|---:|---:|---:|---:|
| site1/small | 234,59 → 74,22 | 84,6% → 65,2% | 126 → 32 | 7,77 → 7,42 |
| site1/medium | 142,92 → 68,54 | 75,0% → 51,5% | 126 → 32 | 14,89 → 23,22 |
| site1/large | 536,71 → 210,51 | 88,3% → 71,6% | 126 → 32 | 36,99 → 47,42 |
| site2/medium | 22,04 → 31,22 | 26,1% → 28,7% | 126 → 32 | 25,68 → 32,76 |
| site2/large | 67,48 → 23,28 | 37,7% → 14,7% | 126 → 32 | 71,76 → 88,50 |

S5 có thêm thời gian refit: 2 launch ở mọi trace, tăng nhẹ ở site1/large (7,29 → 9,39 ms) và site2/large (14,15 → 19,10 ms). Đặc biệt, site2/large đã bị S6 chi phối trong V2: `gather_b_kernel` chiếm 40,1% kernel time; ở V3 tăng lên 55,8%, trong khi S5 `compute_hypotheses` còn 14,7%. Đây khớp benchmark không có profiler: S5 giảm 30,538 → 12,200 ms, S6 vẫn tốn 28,468 ms, nên toàn pipeline tăng 1,31× dù kernel giả thuyết tăng tốc gần 2,9× trong benchmark. Site2/medium là ngoại lệ: launch giảm nhưng `compute_hypotheses` time trong trace tăng 22,04 → 31,22 ms; ở benchmark S5 cũng gần như không đổi (13,374 → 13,625 ms), và toàn pipeline chậm hơn khoảng 1,2%. Trace của case này cho thấy `refit_homography` và S6 cũng chiếm khoảng 30% mỗi bên, vì vậy phần lớn thời gian không nằm trong kernel giả thuyết.

![NSYS timeline V3 site1/medium](../../results/p8-t03-20261116/package/v3/profiling/v3/site1/medium/nsys/v3/site1/medium/nsys/capture.png)

### NCU: occupancy cải thiện, stall tại barrier vẫn còn

NCU dùng `--launch-count 1`; mỗi mẫu mô tả một launch đầu và không đại diện toàn bộ đợt RANSAC. So sánh `compute_hypotheses` ở site1/medium, block size giữ 128 threads, grid tăng 32 → 128 blocks, register tăng 118 → 120/thread và static shared memory tăng 904 B → 1,60 KiB/block. Achieved occupancy tăng 12,50% → 37,77%, còn mức lý thuyết là 50% ở cả hai phiên bản. Không có local-memory spill trong hai report. Đây là cải thiện mức hoạt động của SM, nhưng không thể một mình giải thích speedup toàn pipeline.

| NCU metric, site1/medium `compute_hypotheses` | V2 | V3 |
|---|---:|---:|
| Achieved occupancy | 12,50% | 37,77% |
| Registers/thread | 118 | 120 |
| Shared memory/block (static) | 904 B | 1,60 KiB |
| Compute (SM) throughput | 9,01% | 34,32% |
| DRAM throughput | 0,04% | 0,61% |
| Avg. active threads/warp | 1,12 | 1,05 |
| No eligible warps | 95,61% | 87,28% |
| Warp cycles/issued instruction | 22,76 | 23,72 |
| PC-sampling stalls attributed to CTA barrier | 74,8% | 76,9% |

Hai report đều cho thấy DRAM gần như không bão hòa, nên chưa có bằng chứng cho bottleneck băng thông bộ nhớ ngoài. Throughput SM tăng đáng kể cùng occupancy, nhưng active lanes/warp vẫn chỉ khoảng một thread. PC sampling gán khoảng ba phần tư stall samples cho barrier ở cả hai bản; do đó V3 vẫn chịu đồng bộ trong block và mất cân bằng giữa các warp. Con số stall là tỷ lệ mẫu PC, không phải tỷ lệ thời gian kernel. V3 cũng dùng nhiều shared memory và register hơn một chút; hiện không có local-memory spill. Các metric này gợi ý hướng điều tra tiếp về điểm đồng bộ và phân bố công việc, chưa chứng minh riêng nguyên nhân của chênh lệch timing.

NCU ở `refit_homography` gần như không đổi giữa V2/V3: 256 threads/block, một block, 100 registers/thread và occupancy đạt được xấp xỉ 25%. Đây là kernel riêng với grid một block, nên thay đổi `compute_hypotheses` không cải thiện occupancy refit.

![NCU V3 site1/medium: throughput và grid](../../results/p8-t03-20261116/screenshots/ncu-v3-site1-medium.png)

![NCU V3 site1/medium: chi tiết throughput và tài nguyên](../../results/p8-t03-20261116/screenshots/ncu-v3-site1-medium-details.png)

Benchmark cho thấy V3 có lợi ích rõ ở tám cấu hình chuẩn, còn site2/medium không nhanh hơn. Kết quả chung ủng hộ giữ V3 cho cấu hình đang đo, đồng thời theo dõi site2/medium và chuyển sự chú ý sang S6 ở site2/large. V3 gộp warp shuffle, shared-memory DLT/SVD và batch scheduling; lượt này không có ablation để tách phần đóng góp của từng thay đổi.

## 6. Reproducibility và bàn giao

- Checkout: `b3c79d783aa79401cfe2b2a03add1e03f55a32d0`; `src/` và `scripts/build.py` khớp SHA production P8-T04.
- Source snapshot SHA-256: `ca5c6ba41c0fc2b5f601f7b835d7d62bdca9527067dbc1925a94490ac0472e12`.
- Binary SHA-256: `8d31b6d12887fdae46640ba108f16474e9e106a71d33863d2e9b7778ab4ec002`.
- Dataset manifest SHA-256: `99fc712988075326a351d0bf580405e418bb28d24d56d4cc1b31505c480bdd9d`; cả 24 ảnh được kiểm tra hash.
- Số liệu và biểu đồ đã lấy về `results/p8-t03-20261116/`. Report gốc và log đầy đủ đang nằm trong workspace Colab `/content/group16_p8_t03_ev69i3zs`.
- Chưa có gói bàn giao hoàn chỉnh trên Drive; lần mount đầu trả `ValueError: mount failed`. Không có runtime T4 nào bị ngắt hoặc tạo lại trong quá trình đo.
