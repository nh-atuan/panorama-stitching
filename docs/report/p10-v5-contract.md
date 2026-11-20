<!-- Authors: Le Ha Thanh Chuong (23120195). External source: NVIDIA CUDA documentation linked below. -->

# P10-T01 — V5 Baseline and Execution Contract

Chương phụ trách điều tra baseline và chốt contract ngày 20/11/2026. Thành thực hiện API một ảnh ở T02, Chương thực hiện dispatcher ở T03, Tuấn nghiệm thu ở T04. Đế đo V5 chính thức ở T05. Các chữ ký dưới đây là giao diện cần triển khai, với semantics được chốt trước khi đo V5.

## 1. Baseline và bằng chứng

- Nền nhánh T01 là `ede4d51`, chứa merge PR #47 và toàn bộ P9. V4 production được nghiệm thu tại `ab8df98d7f15bb42d5e3306cf03a38311248b4a8`. P9-T05 checkout `ba97ed780785135e9d20ce36aac852efc4ebc898`, có `src/` và `scripts/build.py` khớp source nghiệm thu. [Nghiệm thu V4](p9-v4-verification.md) · [Benchmark P9](p9-t05-v4-apod.md)
- P9 đo Tesla T4, driver 580.82.07, nvcc 13.0.88, `sm_75 -O2 --fmad=false`, một warm-up và năm runs. Manifest ảnh SHA-256 là `99fc712988075326a351d0bf580405e418bb28d24d56d4cc1b31505c480bdd9d`. Đây là môi trường của bằng chứng P9.
- Máy điều tra T01 có GTX 1650, VRAM tổng 4096 MiB, còn trống 3935 MiB tại thời điểm truy vấn. PowerShell không tìm thấy `nvcc` hoặc `nsys`. Checkout có report và hình NSYS/NCU, chưa có SQLite, CSV timing thô hay ZIP evidence P9. Notebook P9 trên Git không lưu output. T01 chưa chạy đo mới trên T4. Bộ nhớ GTX là thông tin môi trường local.
- Bộ evidence P9 được report định danh bằng ZIP SHA-256 `a16c610c7a8bff02c6cd61c94bacd79a9d1d0793b2c838d58d996ca3c6e060c7`. Chương có thể tự trích khi nhận được archive từ kho chung. [Kho evidence](https://drive.google.com/drive/folders/1uJ-4_kgVONvIt5NQIPzdEWTIPrg8Sue1)

### Baseline ba ca large

| Ca | V4 Total (ms) | S6 V4 (ms) | Nguồn | H2D → S4 ready, H2D A/B, S1 A/B, S2, S3, host wait, GPU idle, peak/headroom T4 |
|---|---:|---:|---|---|
| site1/large | 107.157 | 19.531 | Bảng benchmark P9-T05 | Chưa có số trích được trong checkout |
| site2/large | 62.197 | 28.190 | Bảng benchmark P9-T05 | Chưa có số trích được trong checkout |
| site3/large | 100.393 | 20.405 | Bảng benchmark P9-T05 | Chưa có số trích được trong checkout |

Các số Total/S6 là kết quả được đọc từ report P9. Chúng không xác định thời gian trước S4. Các bảng NCU và NSYS của report chỉ chi tiết S6. Pre-S4 share, A/B imbalance, `asyncEngineCount`, `concurrentKernels` và mức contention còn cần được đo.

### Quy tắc chọn ca chính khi thiếu trace

Chốt **site2/large** trước khi xem số V5. Quy tắc dự phòng là chọn ca có Total V4 thấp nhất trong ba ca cùng kích thước ảnh large. Giả thuyết làm việc là công việc theo pixel trước S4 tương đương về quy mô, nên cùng mức giảm thời gian tuyệt đối có ảnh hưởng tương đối lớn hơn ở ca có Total nhỏ nhất. Số candidate và lịch sort có thể khác giữa các cảnh. Đây là quyết định theo proxy, có bất định, chưa phải xếp hạng từ pre-S4 timing. Kết quả trên cả ba ca và toàn bộ chín ca chuẩn vẫn phải báo cáo. Chốt này độc lập với lý do chọn hotspot S6 của P9.

### Thu thập phần baseline còn thiếu

Trên T4, ghi SHA checkout, hash binary và manifest, GPU/driver, nvcc, thuộc tính thiết bị, lệnh và exit code. Build bằng script production, chạy CLI V4 với một warm-up tự động và năm runs. Ghi lại stdout/stderr.

```bash
python scripts/build.py --compiler nvcc --require-t4 --out-dir build
mkdir -p results/p10-t01
for site in site1 site2 site3; do
  ./build/stitch dataset/$site/large_left.jpg dataset/$site/large_right.jpg \
    results/p10-t01/${site}.png --version 4 --runs 5 \
    > results/p10-t01/${site}.csv 2> results/p10-t01/${site}.log
  nsys profile --trace=cuda,nvtx,osrt --cuda-memory-usage=true \
    --force-overwrite=true -o results/p10-t01/${site} \
    ./build/stitch dataset/$site/large_left.jpg dataset/$site/large_right.jpg \
    results/p10-t01/${site}_profile.png --version 4 --runs 1
  nsys export --type sqlite --force-overwrite=true \
    -o results/p10-t01/${site}.sqlite results/p10-t01/${site}.nsys-rep
done
```

Trong SQLite, dùng correlation ID của CUDA API và GPU operations để tách warm-up khỏi run, xác định upload A/B và launch S4 đầu tiên. Báo hai mốc riêng là host submit đầu tiên → host submit S4, và GPU bắt đầu copy đầu tiên → GPU bắt đầu S4. Mốc thứ hai có thể gồm độ trễ launch sau khi dữ liệu sẵn sàng. Ghép NVTX `S1.image_a/b`, `S2.image_a/b`, `S3.image_a/b` với kernel/copy bên trong để xác định thời lượng A/B. Host wait lấy từ API `cudaStreamSynchronize` tại `S2.score_nms`, bao gồm thời gian đợi công việc trước đó.

GPU idle là phần bù của hợp các khoảng GPU copy/kernel trong cửa sổ trước S4. Không cộng các duration chồng lấn. Peak allocation lấy từ timeline memory của NSYS nếu có đủ allocation/free. Ghi free VRAM tại các mốc chuẩn bị xong, trước S4, sau S6, sau D2H bằng `cudaMemGetInfo` trong lượt chẩn đoán, và báo mức thấp nhất đã lấy mẫu. Ghi riêng tổng bytes buffer do dispatcher sở hữu và phần headroom lấy mẫu. Hai đại lượng này chưa bao phủ stack, context, cache allocator hoặc biến động giữa các lần lấy mẫu.

## 2. Audit đường chạy V4

1. `main.cu::run_gpu_once` dùng một stream nonblocking. Reset `DeviceCounts`, upload A rồi B bằng `cudaMemcpy2DAsync`, sau đó gọi pipeline. Input pinned được chuẩn bị ngoài timing.
2. `v4_run_stages` dùng bộ stage V1, thay S5 bằng V3 và S6 bằng V4. S1 chạy A rồi B, S2 chạy A rồi B, S3 chạy A rồi B.
3. S1 dùng scratch cho blur tạm. S2 tái sử dụng scratch cho counter, score và sort keys. Sau score/NMS, S2 copy count vào biến host rồi `cudaStreamSynchronize` trước top-K. Lần chờ A làm trì hoãn cả việc submit công việc S2 của B.
4. S3 dùng scratch cho smoothing, scan và compacted keypoints. `load_pattern` dùng static flag cùng copy constant memory và synchronize lần đầu. S3 kernels đọc/ghi `DeviceCounts::status`, có nhánh lỗi ghi cả hai descriptor counts.
5. S4 cần cả descriptor arrays và counts hợp lệ. S4/S5 tái sử dụng scratch production, S6 cấp canvas sau setup. S6 đọc metadata về host và chờ stream trước khi biết kích thước output.
6. Các vùng scratch và `d_counts` hiện hành chỉ an toàn khi dùng tuần tự. Owner giải phóng buffers qua RAII sau khi stream hoàn tất. Hook kernel timing hiện hành là thread-local trên host. [Driver](../../src/main.cu) · [Pipeline](../../src/v1/v1_pipeline.cu) · [S2](../../src/v1/s2/v1_detect.cu) · [S3](../../src/v1/s3/v1_describe.cu) · [Workspace](../../src/common/common.h)
