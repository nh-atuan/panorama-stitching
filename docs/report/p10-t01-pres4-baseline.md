<!-- Authors: Le Ha Thanh Chuong (23120195). External source: measured P10-T01 Colab evidence. -->

# P10-T01 — V4 Pre-S4 Baseline Results

## 1. Kết quả nghiệm thu

**T01 hoàn tất.** Chương đã chạy notebook trên Tesla T4, kiểm tra timing ba cấu hình large, đối chiếu panorama production/probe và thu đủ ba NSYS trace cùng SQLite. Chốt **site2/large** làm ca chính trước khi quan sát kết quả V5. Contract API, ownership, scheduler, timing và lỗi được giữ tại [contract V5](p10-v5-contract.md).

Evidence tại `results/Group16_P10_T01_PreS4_Evidence/Group16_P10_T01_PreS4_Evidence/`. Notebook đã thực thi nằm ở `results/Group16_P10_T01_PreS4_Baseline.ipynb`. Thư mục lồng nhau là cấu trúc archive đã giải nén.

- Source SHA đo là `c4566e3f656493bc48bb8edddaa5e8ac95d27831`, nhánh `chuong/p10-v5`.
- Phiên bắt đầu `2026-11-20T03:19:46.431273+00:00`, tương đương 10:19:46 ngày 20/11 giờ Việt Nam.
- GPU Tesla T4, compute capability 7.5, driver 580.82.07, runtime 13000, nvcc 13.0.88, NSYS 2025.3.1.0, CMake 3.31.10. Thuộc tính thiết bị ghi `asyncEngineCount=3`, `concurrentKernels=1`.
- Production binary SHA-256 `b4bc33befd9a0adb806025c3718a9006821d41fe4eb372a607e13af499cda3ab`; probe `e5a3c68aa2f63c3f0b2fcec8c0b7b068e649c771ff11061dcd11c706f851cd09`.
- Manifest dataset khớp P7–P9, SHA-256 `99fc712988075326a351d0bf580405e418bb28d24d56d4cc1b31505c480bdd9d`.
- Kiểm lại 84 file theo `checksums.json`, tất cả khớp. SHA-256 của chính manifest checksum là `5c8c82faf4da7877916133b8d76d6c77412a176dd77a22a1778ea43db4a3d1ca`.
- Hai build, sáu lệnh production/probe, ba lệnh NSYS và ba lệnh export SQLite đều exit 0. Notebook có execution count liên tiếp 1–10 và không có error output. PNG của probe trùng SHA-256 với production ở cả ba ca.

## 2. Pre-S4 và độ ổn định

Mỗi binary chạy một warm-up và năm lượt đo. Pre-S4 CUDA dùng origin trước upload A đến event sau S3(B), trước S4. Host pre-S4 chờ endpoint hoàn tất. Các số dưới đây tính lại từ CSV thô và khớp statistics JSON, đơn vị ms. SD dùng mẫu với mẫu số n−1.

| Ca | CUDA mean | Median | Min | Max | SD | Host mean | Pre-S4 / Total probe |
|---|---:|---:|---:|---:|---:|---:|---:|
| site1/large | 13.086 | 12.645 | 12.571 | 14.983 | 1.061 | 13.095 | 12.23% |
| site2/large | 15.288 | 16.149 | 13.650 | 16.531 | 1.496 | 15.297 | 21.44% |
| site3/large | 11.234 | 10.893 | 10.845 | 12.487 | 0.708 | 11.244 | 11.20% |

Tỷ trọng là trung bình tỷ lệ pre-S4/Total của từng run probe. CV pre-S4 khoảng 8,11%, 9,79%, 6,30% tương ứng ba site. Giữ đủ các run. Khác biệt median/mean ở site2 cho thấy biến động vẫn đáng kể, cần đo luân phiên khi đánh giá V5.

| Ca | Total production mean | Total probe mean | Chênh probe / production |
|---|---:|---:|---:|
| site1/large | 106.883 | 106.893 | +0.009% |
| site2/large | 69.684 | 71.734 | +2.942% |
| site3/large | 100.512 | 100.231 | −0.281% |

Probe có event bổ sung, queries ngoài timing và một readiness wait. Hai binary chạy nối tiếp theo nhóm, nên chênh Total chứa cả overhead và biến động phiên đo. Mức âm ở site3 cho thấy không thể dùng chênh này làm overhead cố định để trừ. Pre-S4 share và mô hình dự báo dưới đây chỉ dùng cùng lượt probe, tránh ghép CUDA interval của probe với Total production.

## 3. Công việc từng ảnh

Các số là mean event interval trong probe, đơn vị ms. Cột S2 bao gồm score/NMS, phụ thuộc count host và top-K/publish.

| Ca | H2D A | H2D B | S1 A | S1 B | S2 A | S2 B | S3 A | S3 B |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| site1/large | 2.019 | 2.011 | 1.058 | 1.057 | 2.451 | 2.450 | 1.006 | 0.997 |
| site2/large | 2.023 | 2.012 | 1.152 | 1.148 | 3.312 | 3.331 | 1.124 | 1.148 |
| site3/large | 2.023 | 2.017 | 1.061 | 1.058 | 1.591 | 1.570 | 0.940 | 0.935 |

Upload tương đương ở ba site vì ảnh cùng kích thước. S2 là phần thay đổi rõ nhất giữa các cảnh và lớn nhất ở site2. Hai nhánh trong từng site có thời lượng gần nhau. Đây là điều kiện thuận lợi để thử overlap, còn mức overlap thực phải được xem trên trace V5.

Tổng host time nằm trong `cudaStreamSynchronize` S2 của probe chỉ 0,01155 / 0,01135 / 0,01054 ms cho site1/2/3. Event spans bao quanh D2H candidate A+B lần lượt khoảng 0,03250 / 0,03819 / 0,03841 ms. Hai metric này có phạm vi khác nhau và đều chịu ảnh hưởng instrumentation cùng pageable count storage.

## 4. Trace production và điểm chờ S2

Phân tích `capture.sqlite` bằng [script trích trace](../../scripts/analyze_pres4_trace.py), chọn lần thứ hai của mỗi NVTX range để bỏ warm-up. Nối runtime API với GPU operation theo correlation ID và host thread. Bắt đầu ở GPU upload ảnh A của measured run, kết thúc readiness ở operation cuối thuộc S1–S3. Đo thêm thời điểm operation S4 đầu tiên. Interval GPU idle là phần bù của hợp kernel/copy/memset của process trong cửa sổ đã chọn.

| Ca | H2D → features ready | H2D → S4 đầu | Ready → S4 đầu | Khoảng không có GPU operation được ghi |
|---|---:|---:|---:|---:|
| site1/large | 13.237 | 13.246 | 0.0088 | 2.056 |
| site2/large | 20.199 | 20.210 | 0.0112 | 3.372 |
| site3/large | 17.325 | 17.336 | 0.0114 | 1.167 |

Đơn vị ms, mỗi trace chỉ có một measured run. Các khoảng không có operation thuộc process này chưa chứng minh toàn GPU không chạy công việc khác. Timing dưới profiler khác probe, nhất là site3; giữ chúng làm bằng chứng lịch thực thi và điểm chờ.

| Ca | Host API copy count A / B (ms) | GPU copy 4 byte A / B (µs) |
|---|---|---|
| site1/large | 7.131 / 1.154 | 1.504 / 1.216 |
| site2/large | 8.882 / 2.207 | 2.304 / 1.632 |
| site3/large | 9.860 / 2.278 | 2.112 / 1.664 |

Copy count vào biến host pageable có thể chặn host trong API copy trước khi đi đến lệnh synchronize rõ ràng. Thời gian API ở đây gồm chờ công việc trước copy và overhead profiler. Bằng chứng cho thấy cần tách **enqueue cả hai nhánh trước khi host chờ count**, dùng pinned count buffers riêng như contract. Chỉ tối ưu lệnh synchronize sau copy sẽ bỏ sót điểm host bị chặn.

## 5. VRAM và chi phí scratch riêng

| Ca | Free thấp nhất đã lấy mẫu (GiB) | Toàn device dùng lớn nhất đã lấy mẫu (GiB) | Peak dynamic device allocation quan sát trong trace (MiB) |
|---|---:|---:|---:|
| site1/large | 13.010 | 1.554 | 238.367 |
| site2/large | 12.980 | 1.583 | 269.755 |
| site3/large | 13.006 | 1.557 | 243.501 |

Peak allocation trong trace cộng các allocation/free loại device của process theo địa chỉ/context, gồm cả warm-up và measured run. Cả ba trace kết thúc với 0 byte allocation loại này còn sống. Số này loại trừ context, device static, stack nội bộ và các allocation không hiện trong bảng. Nó khác whole-device VRAM và không thay thế nghiệm thu memcheck V5.

Scratch calculator production cho mỗi nhánh large là **66.395.216 byte**. Cấp thêm cả hai scratch trong khi giữ scratch downstream cần thêm **132.790.432 byte**, khoảng **126,639 MiB**. Headroom lấy mẫu nhỏ nhất còn khoảng **12,98 GiB**, vượt đáng kể nhu cầu này. T03 vẫn phải xử lý allocation failure và tính metadata/event/tài nguyên thực của owner V5.

## 6. Quyết định và chuyển sang T03

**Giữ site2/large làm ca chính V5.** Cả probe và trace production đều xếp site2 cao nhất theo thời gian trước S4 trong các lần quan sát. Probe ghi tỷ trọng 21,44%, cao hơn 12,23% và 11,20% của hai site còn lại. VRAM hỗ trợ việc tách scratch, các nhánh A/B có tải gần nhau, thiết bị báo khả năng copy/compute và concurrent kernels.

Nếu giả định rút ngắn đúng một nửa phần pre-S4 và mọi phần còn lại giữ nguyên, p = 0,2144 cho speedup minh họa khoảng **1,12×** trên nền probe. Nếu loại bỏ toàn bộ phần đó, giới hạn mô hình khoảng **1,27×**. Đây là mô hình từ tỷ trọng đo, chưa dự báo phần overlap sẽ đạt trên V5. Mức contention, host scheduling và chi phí hợp nhất còn phải đo.

Chương tiếp tục **P10-T03**, triển khai owner, hai stream, hai mode, hội tụ và timing theo contract. Thành cung cấp API T02. Tuấn kiểm status/feature/match/H/canvas/RGB cùng memcheck ở T04. Đế chỉ chạy benchmark V5 chính thức sau khi có SHA đã nghiệm thu.

Tái lập phân tích trace từ gốc repo:

```bash
python scripts/analyze_pres4_trace.py \
  --evidence results/Group16_P10_T01_PreS4_Evidence/Group16_P10_T01_PreS4_Evidence \
  --output build/p10-t01-trace-analysis.json
```
