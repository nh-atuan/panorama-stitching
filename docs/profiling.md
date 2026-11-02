<!-- Authors: Le Thuong De (23120232). External source: none. -->

# Chạy profiling và kiểm chứng synthetic theo batch

P5-T09 cung cấp `scripts/run_profiling.py`, tách phần lưu lệnh/log, gọi profiler và đánh giá synthetic thành các module riêng. Script dùng bộ đánh giá H đã có trong `homography_error.py`, giữ ngưỡng ground truth RMSE ≤ 0,5 px và Max ≤ 1 px.

## 1. Môi trường và phạm vi

Chạy từ gốc repo trên Colab GPU Tesla T4 với `nvcc`, `nsys`, `ncu` và các phụ thuộc Python hiện có. Build CUDA dùng `-arch=sm_75`, `--fmad=false`; nhãn NVTX dùng header v3 có sẵn trong CUDA Toolkit và `-ldl` trên Linux.

Trong P5, S4/S5 được kiểm chứng độc lập bằng `tool_gpu_s45`: S1–S3/S6 chạy V0, S4/S5 chọn V0 hoặc V1. Driver so match, sampler/prefix, mask và H với V0 ngoài vùng CUDA events. Các cột thời gian của driver chỉ mô tả hai stage trên cùng input feature; không dùng chúng làm speedup toàn pipeline.

Chương trình `stitch --version 1` hiện vẫn là scaffold. Script từ chối nhận output scaffold làm kết quả kiểm chứng. Khi P6 có pipeline đầy đủ, có thể chuyển `--stitch` sang binary chính và dùng scope mặc định `pipeline`.

## 2. Build và test

```bash
python3 scripts/build.py --compiler nvcc --target all --require-t4
python3 tests/run_tests.py --compiler nvcc --require-t4
```

Runner có hai suite `gpu_s4`, `gpu_s5` và suite Python `test_profiling_scripts.py`. Có thể chạy từng nhóm bằng `--group gpu` hoặc `--group python`.

## 3. Sáu cặp synthetic

Ảnh nguồn là `raw/tuan/standard1_left.jpg`, SHA-256 `e9fbe7ecfed6344a36610fe50f2c6019bcd1525f4e217c033ed8ded4f90bf1e8`. Link `Group16_support.zip` và bước tải/kiểm tra dữ liệu có trong `Group16_Midterm.ipynb`. Khi giải nén gói hỗ trợ, chỉ lấy `dataset/` và `raw/`, giữ code đang kiểm chứng từ `src/` của repo.

```bash
python3 scripts/make_synthetic_pair.py --source raw/tuan/standard1_left.jpg --out results/synthetic
python3 scripts/run_profiling.py --stitch build/tool_gpu_s45 --synthetic results/synthetic --versions 0 1 --scope s45 --out results/p5-synthetic --require-t4
```

Script kiểm tra đủ ảnh trái/phải và truth của hai case `translation`, `projective` ở ba kích thước trước khi chạy. Mỗi lượt lưu panorama, stdout, stderr, argv, exit code và `evaluation.json`. `synthetic.csv` tổng hợp sai số theo version/case/kích thước; `summary.json` giữ cả lượt thất bại. Lệnh trả mã khác 0 nếu có lượt không đạt.

Driver dùng ngưỡng so H CPU–GPU do Đế xác nhận: RMSE ≤ 0,0001 px, Max ≤ 0,001 px trên lưới 20×20 ảnh B. Ngưỡng này tách biệt với phép so ground truth. Match, sample prefix và inlier mask phải khớp chính xác.

## 4. Profiling từng stage

```bash
python3 scripts/run_profiling.py --out results/p5-profile-s4 --require-t4 --kernel-regex nearest_two --profile-command build/tests_gpu/gpu_s4
python3 scripts/run_profiling.py --out results/p5-profile-s5 --require-t4 --kernel-regex compute_hypotheses --profile-command build/tests_gpu/gpu_s5
```

Mỗi lệnh chạy `nsys` và `ncu`. Nhánh Systems giữ timeline, xuất bảng kernel/copy và tổng hợp NVTX; nhánh Compute giữ `.ncu-rep` và xuất CSV. `--kernel-regex` lọc kernel cho Compute, `--launch-count` mặc định 1 để giới hạn số launch thu thập. Có thể chọn riêng profiler bằng `--profilers nsys` hoặc `--profilers ncu`. Cú pháp và hành vi thu thập được đối chiếu với [Nsight Systems User Guide](https://docs.nvidia.com/nsight-systems/UserGuide/index.html) và [Nsight Compute CLI](https://docs.nvidia.com/nsight-compute/NsightComputeCli/index.html).

Các lượt fixture ở trên kiểm tra công cụ thu thập bằng chứng. Muốn phân tích bottleneck trên ảnh thật sau khi có pipeline CUDA đầy đủ:

```bash
python3 scripts/run_profiling.py --stitch build/stitch --dataset dataset --versions 1 --sites site1 --sizes medium --out results/profile-v1-site1-medium --require-t4
```

Không gộp thời gian từ lượt có profiler vào bảng benchmark chính thức. Kernel filter, số launch và toàn bộ argv được lưu cùng report để đối chiếu phạm vi thu thập.

## 5. Bằng chứng và lỗi

Thư mục output phải mới hoặc rỗng; script từ chối ghi đè bằng chứng cũ. `environment.json` lưu GPU/driver, hệ điều hành, Python, đường dẫn profiler và SHA-256 executable. Mỗi lệnh lưu `.command.json`, `.stdout`, `.stderr`; kết quả tổng hợp ghi rõ scope `pipeline`, `s45` hoặc `standalone`.

Thiếu profiler, lỗi quyền performance counter, không có kernel khớp filter, thiếu report, lỗi export, timeout, H thiếu hoặc không hợp lệ đều không được tính là thành công. Script vẫn lưu nguyên bằng chứng và trả mã lỗi. Report, ảnh, log và notebook output nằm ngoài Git; chỉ commit source, test và tài liệu.

Kiểm tra ngày 31/10/2026 trên Colab Tesla T4, CUDA 13.0.88, Nsight Systems/Compute 2025.3.1: 20 test Python mới đạt; cả hai profiler thu thập/export được report cho fixture S4 và S5, có nhãn NVTX trong bảng xuất. Cả 12 lượt synthetic theo hai version đạt; RMSE lớn nhất 0,100222 px và Max lớn nhất 0,209020 px. Memcheck của S4/S5 báo 0 lỗi. Đây là kiểm chứng P5 cho công cụ và hai stage, chưa phải benchmark V1 end-to-end của P6.
