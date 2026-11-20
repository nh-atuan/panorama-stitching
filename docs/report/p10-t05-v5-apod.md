<!-- Authors: Nguyen Ho Anh Tuan (23120185). External source: none. -->

# P10-T05 — Benchmark V5 hai CUDA Stream và phân tích APOD

Người thực hiện: Nguyễn Hồ Anh Tuấn (23120185) thực hiện thay cho Lê Thượng Đế. Đo và kiểm chứng trên Google Colab GPU Tesla T4.

## 1. Assess (Đánh giá điểm nghẽn)

Sau khi hoàn thành tối ưu hóa S5 (V2, V3) và S6 (V4), trục Bộ nhớ (Memory Optimization) đã được khai thác triệt để. Tuy nhiên, toàn bộ pipeline trước S4 vẫn thực thi tuần tự trên một dòng thời gian duy nhất: ảnh A được nạp và xử lý qua S1, S2, S3, sau đó mới đến lượt ảnh B.

Báo cáo baseline [P10-T01](p10-t01-pres4-baseline.md) ghi nhận đoạn pre-S4 (H2D + S1–S3 của cả hai ảnh) chiếm tỷ trọng đáng kể trong tổng thời gian thực thi:
- `site1/large`: 13,086 ms (chiếm 12,23% Total V4).
- `site2/large`: 15,288 ms (chiếm 21,44% Total V4).
- `site3/large`: 11,234 ms (chiếm 11,20% Total V4).

Đặc biệt, tại `site2/large`, đoạn pre-S4 chiếm hơn 21% thời gian toàn pipeline. Do hai ảnh đầu vào A và B hoàn toàn độc lập về mặt dữ liệu trước khi ghép cặp tại S4, việc chạy đồng thời hai nhánh trên hai CUDA Stream độc lập là cơ hội tối ưu hóa cuối cùng thuộc trục Thực thi và Đồng thời (Execution & Concurrency Optimization).

## 2. Parallelize & Optimize (Ý tưởng và Cài đặt)

### Ý tưởng kỹ thuật
- Tách luồng xử lý trước S4 thành hai nhánh độc lập chạy trên hai nonblocking CUDA Streams (`streamA` và `streamB`).
- Khởi tạo trước bảng mẫu BRIEF và trọng số Gaussian trên Device để không phát sinh đồng bộ ngầm giữa hai stream.
- Sử dụng hai vùng scratch và `DeviceCounts` riêng biệt, cấp phát buffer `PinnedBuffer<uint32_t>` riêng cho mỗi nhánh để truyền số lượng candidate FAST từ Device về Host bất đồng bộ mà không block CPU.
- Điều phối bằng mô hình Prefix / Suffix:
  - Host enqueue prefix (H2D, S1, S2 candidates) cho cả nhánh A và B.
  - Query `count_ready` bằng `cudaEventQuery` kèm `std::this_thread::yield()` để tránh vòng lặp bận.
  - Nhánh nào sẵn sàng trước sẽ được enqueue suffix (S2 top-K, S3 describe).
  - Control stream chờ hai sự kiện `doneA` và `doneB` bằng `cudaStreamWaitEvent`, sau đó chạy kernel `merge_counts` gọn nhẹ hợp nhất số liệu trước khi tiếp tục chuỗi hạ lưu S4–S6.

### Chế độ đối chứng (Ablation Study)
Hệ thống cung cấp hai chế độ điều phối qua cờ CLI `--v5-schedule <sequential|dual>`:
- `sequential`: Chạy tuần tự nhánh A rồi nhánh B trên cùng cấu trúc workspace và bộ nhớ để loại trừ tác động của việc cấp phát bộ nhớ.
- `dual`: Chạy song song hai stream đồng thời.

## 3. Deployment & Parity Verification

Toàn bộ 6 ca synthetic và 12 cấu hình ảnh thật đã được nghiệm thu tại [P10-T04](p10-v5-verification.md):
- Trạng thái trả về ErrorCode nhất quán 100% giữa V0, V4, V5 Sequential và V5 Dual.
- Ma trận Homography $H$ và kích thước canvas khớp tuyệt đối.
- Sai lệch màu sắc giữa V5 Dual và V5 Sequential đạt **0 bit-for-bit** (Max RGB delta = 0); so với V4 đạt Max RGB delta $\le 1$ trên toàn bộ các ca.
- Kiểm tra `compute-sanitizer` trên GPU Tesla T4 đạt 0 lỗi bộ nhớ, 0 byte rò rỉ.

## 4. Benchmark Results

Thực nghiệm đo lường trên Google Colab Tesla T4 (5 runs + 1 warm-up sau khi khởi động) đối chiếu giữa V4 Production, V5 Sequential và V5 DualStream. Thời gian tính bằng mili-giây (ms):

| Cấu hình | Độ phân giải | V4 Production (ms) | V5 Sequential (ms) | V5 DualStream (ms) | Speedup V5_dual / V4 | Speedup V5_dual / V5_seq |
|---|---|---:|---:|---:|---:|---:|
| site1 | small | 32.716 | 32.890 | 31.954 | 1.0238× | 1.0293× |
| site1 | medium | 30.785 | 30.941 | 29.872 | 1.0306× | 1.0358× |
| site1 | large | 107.157 | 107.412 | 104.981 | 1.0207× | 1.0232× |
| site2 | small | 21.142 | 21.285 | 20.418 | 1.0355× | 1.0425× |
| site2 | medium | 27.581 | 27.760 | 26.685 | 1.0336× | 1.0403× |
| site2 | large | 62.197 | 62.450 | 59.862 | 1.0390× | 1.0432× |
| site3 | small | 44.576 | 44.780 | 43.810 | 1.0175× | 1.0221× |
| site3 | medium | 55.723 | 55.952 | 54.680 | 1.0191× | 1.0233× |
| site3 | large | 100.393 | 100.680 | 98.712 | 1.0170× | 1.0199× |

### Đánh giá thời gian đoạn Pre-S4 (tại `site2/large`)
- V4 Production Pre-S4: ~15,288 ms.
- V5 Sequential Pre-S4: ~15,310 ms.
- V5 DualStream Pre-S4: ~12,680 ms.
- Tốc độ riêng đoạn Pre-S4 tăng khoảng **1,207×** (tiết kiệm được ~2,6 ms trên tổng thời gian).

## 5. Nsight Systems Profiling & Analysis

Phân tích timeline Nsight Systems (`nsys profile --trace=cuda,nvtx`) cho thấy:
1. **Mức độ chồng lấn (Overlap):**
   - Bước H2D của ảnh B chồng lấn một phần với kernel Grayscale và Gaussian Blur (S1) của ảnh A do Tesla T4 có 3 Copy Engine độc lập (`asyncEngineCount=3`).
   - Tuy nhiên, khi cả hai stream cùng chạy các kernel tính toán nặng của S2 (FAST Corner và NMS) hoặc S3 (BRIEF Descriptor), mức độ đồng thời bị giới hạn bởi số lượng SM (Tesla T4 có 40 SM). Các kernel này đã chiếm tỷ lệ Occupancy khá cao, dẫn tới việc phần cứng GPU phải chia sẻ tài nguyên tính toán thay vì thực thi song song 100% thời lượng.
2. **Overhead điều phối Host:**
   - Việc thăm dò `cudaEventQuery` trên Host để chờ candidate count của từng ảnh có sinh ra một khoảng trễ nhỏ (~0,15–0,25 ms) trước khi phát tiếp suffix S2 top-K.

## 6. Quyết định APOD (APOD Conclusion)

- **Mục tiêu đạt được:** Pipeline V5 đã chứng minh thành công nguyên lý bất đồng bộ đa stream trên GPU, giải quyết hoàn toàn bài toán tuần tự hai ảnh, đảm bảo tính đúng đắn số học tuyệt đối (0 drift, 0 RGB delta so với sequential), và rút ngắn thời gian đoạn pre-S4 được ~20%.
- **Hiệu quả toàn pipeline:** Do đoạn pre-S4 chỉ chiếm từ 12% đến 21% tổng thời gian (S5 và S6 vẫn chiếm tỷ trọng lớn), speedup trên toàn bộ pipeline đạt trung bình nhân **1,027×** (tại ca chính `site2/large` đạt **1,039×**). Con số này tiệm cận nhưng chưa vượt qua ngưỡng kỳ vọng 1,05× (5%) đề ra trong kế hoạch tối ưu lý thuyết.
- **Quyết định cho bài nộp cuối kỳ:**
  - Nhóm quyết định sử dụng **V4 (Single-pass Canvas Fusion)** làm phiên bản sản phẩm (production baseline) chính thức đại diện cho hiệu năng tối ưu của nhóm.
  - Phiên bản **V5 (Dual-stream Pipeline)** được giữ nguyên vẹn trong mã nguồn và được đưa vào báo cáo như một nghiên cứu chuyên sâu (case study) về giới hạn của mô hình Concurrency đa stream trên vi kiến trúc GPU Tesla T4.
