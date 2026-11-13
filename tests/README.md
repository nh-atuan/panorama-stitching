<!-- Authors: Le Thuong De (23120232), Nguyen Ho Anh Tuan (23120185), Tran Huu Kim Thanh (23120166) -->
<!-- External source: none -->

# Cấu trúc và hướng dẫn chạy `tests/`

Thư mục `tests/` chứa toàn bộ bài kiểm thử tự động (C++/CUDA và Python) cùng các công cụ CLI hỗ trợ xuất dữ liệu trung gian của pipeline.

## 1. Tổ chức thư mục

```text
tests/
├── run_tests.py     # Trình chạy kiểm thử thống nhất cho cả C++/CUDA và Python
├── support/         # Header dùng chung: feature_test_support.h, v0_reference.h, gpu_compare.h
├── v0/              # 14 suite C++: 13 suite cho S1-S6 và V0 pipeline, 1 suite cho tiện ích tham chiếu
├── gpu/             # Các suite .cu đối chiếu kết quả GPU (V1, V2, V3) với V0
├── python/          # 7 suite Python unittest kiểm thử scripts/, runner và cấu trúc notebook
└── tools/           # Công cụ CLI sinh bảng hằng và xuất ảnh/trace trung gian để debug
```

## 2. Quy ước viết và đăng ký bài test mới

- **Đường dẫn `#include`:** trình biên dịch test luôn nhận hai cờ `-Isrc -Itests`. Ghi rõ thư mục con trong mọi lệnh `#include`, ví dụ `#include "common/common.h"`, `#include "v0/v0_match.h"`, `#include "support/feature_test_support.h"`.
- **Tách file test GPU theo stage:** khi viết test trong `tests/gpu/`, mỗi thành viên đặt bài test vào file riêng của stage mình phụ trách (ví dụ `test_gpu_s1_preprocess.cu`, `test_gpu_s2_detect.cu`..., `test_gpu_pipeline.cu`) để tránh xung đột khi merge song song và tái sử dụng xuyên suốt từ `V1` sang `V3`.
- **Đăng ký suite vào `tests/run_tests.py`:** mỗi suite C++/CUDA khai báo rõ danh sách file nguồn tối thiểu cần liên kết trong `tests/run_tests.py`, không dùng wildcard gom toàn bộ `src/` để tránh kéo theo các phiên bản không liên quan.
- **Dòng PASS:** suite C++/CUDA in `PASS: <n> checks` hoặc `PASS <tên>: <n> checks` khi đạt; runner đọc số này để cộng tổng, thiếu dòng này thì suite bị tính là lỗi.
- **Test Python:** đặt file dạng `test_*.py` trong `tests/python/` và xác định thư mục gốc repo bằng `ROOT = Path(__file__).resolve().parents[2]`.
- **Tính tái lập và comment đầu file:** mọi dữ liệu thử có yếu tố ngẫu nhiên phải cố định seed; mọi file test mới hoặc chỉnh sửa phải có comment `Authors:` và `External source:` ở đầu file.

## 3. Các lệnh chạy kiểm thử

Thực thi từ thư mục gốc của repo:

```bash
# Chạy đầy đủ toàn bộ kiểm thử chính thức trên Google Colab Tesla T4 (trước khi mở PR)
python3 tests/run_tests.py --compiler nvcc --require-t4

# Chạy toàn bộ suite C++ V0 kèm AddressSanitizer + UBSan trên Linux 64-bit
python3 tests/run_tests.py --compiler g++ --group v0 --sanitizers

# Chạy nhanh một hoặc vài suite cụ thể trong lúc sửa code
python tests/run_tests.py --compiler g++ --suite preprocess --suite pipeline

# Chỉ chạy các suite kiểm thử Python
python tests/run_tests.py --group python

# Chạy V0 và Python ở máy không có nvcc; nhóm GPU được bỏ qua kèm thông báo
python tests/run_tests.py --compiler g++

# Liệt kê danh sách các suite hiện có
python tests/run_tests.py --list
```

### Kiểm thử tích hợp V2 (P7-T04)

Suite `gpu_v2_pipeline` liên kết S5 V2 thật. Khi có `src/v2/v2_pipeline.{h,cu}`, suite gọi `v2_prepare` và `v2_run_stages` giống CLI, chờ stream rồi đọc H và canvas trên Device. Bản source trước tích hợp dùng dispatcher riêng của test và ghi `test-only dispatcher smoke`. Cờ `--require-v2-pipeline` chỉ chấp nhận chế độ production.

```bash
# Smoke test trên Colab T4 trước khi tích hợp P7-T02.
python3 tests/run_tests.py --compiler nvcc --group gpu --suite gpu_v2_pipeline --require-t4

# Nghiệm thu sau P7-T02 với sáu fixture translation/projective và dataset cuối kỳ.
python3 tests/run_tests.py --compiler nvcc --group gpu --suite gpu_v2_pipeline \
  --require-t4 --require-v2-pipeline --v2-synthetic-dir results/synthetic \
  --v2-dataset-dir dataset

# Kiểm tra bộ nhớ với pipeline chính thức, các fixture nhúng và dataset cuối kỳ.
compute-sanitizer --tool memcheck --leak-check full --error-exitcode 99 \
  build/tests_gpu/gpu_v2_pipeline --require-v2-pipeline --dataset dataset
```

Tạo `results/synthetic` bằng `scripts/make_synthetic_pair.py` với ảnh nguồn synthetic của nhóm. Nếu không truyền `--v2-synthetic-dir`, suite dùng sáu fixture tịnh tiến nhúng. Khi chỉ định dataset, suite yêu cầu đủ 12 cấu hình, gồm hai ca lỗi dự kiến `challenge/medium` và `challenge/large`. Để thử một cặp chuẩn, có thể truyền hai đường dẫn ảnh vào executable.

Suite kiểm tra lần lượt trạng thái, sai số chiếu B→A, hình học canvas và RGB. Ngưỡng synthetic là RMSE ≤ 0,5 px và Max ≤ 1 px trên lưới 20×20 lọc bằng ground truth. Độ lệch chiếu giữa phiên bản phải dưới 0,1 px. Kích thước và offset phải khớp chính xác, sai số RGB tối đa là 1 mức mỗi kênh. Khi RGB vượt ngưỡng, suite chạy lại S6 với cùng H để phân biệt ảnh hưởng từ H với lỗi lấy mẫu hoặc bàn giao canvas. Lệnh CLI `stitch --version 2` và CSV timing cần kiểm tra cùng dispatcher của P7-T02.

### Kiểm thử tích hợp V3 (P8-T04)

Runner phát hiện `src/v3/v3_pipeline.{h,cu}` và link các nguồn trong `src/v3/` cùng pipeline V0–V2. Suite dự kiến gọi `v3_prepare` và `v3_run_stages` theo contract workspace và stream của V2. Khi thiếu file production, yêu cầu chạy V3 trực tiếp trả lỗi P8-T02, còn lượt chạy toàn bộ GPU suite ghi rõ V3 được bỏ qua. Khi có đủ hai file, lỗi build, link hoặc test V3 làm runner thất bại.

Suite V2/V3 dùng chung cách nạp ảnh, fixture tịnh tiến nhúng, ma trận ảnh thật, `make_v0_config` và phép đo. Cùng một `Config` và seed RANSAC được truyền cho mọi phiên bản trong một ca. Seed tạo ảnh synthetic là dữ liệu riêng của fixture. Suite đợi stream kết thúc trước khi đọc H hoặc sao chép panorama từ Device.

V3 kiểm tra theo thứ tự trạng thái → H → canvas → RGB. Hai ca challenge dự kiến trả `NumericalFailure` kết thúc sau bước trạng thái. Ngưỡng ground truth là RMSE ≤ 0,5 px và Max ≤ 1 px, tính khoảng cách Euclid sau chiếu B→A trên lưới 20×20 của ảnh B. Với synthetic, tập điểm Q chỉ lấy các điểm mà H_gt chiếu vào ảnh A. Với ảnh thật, dùng toàn bộ lưới B. Sai lệch chiếu cực đại giữa V3 và mỗi bản V0/V1/V2 phải < 0,1 px. Canvas phải khớp width, height và offset chính xác. RGB được so trên cả canvas, gồm nền đen và bỏ qua padding, với sai lệch tối đa ≤ 1 mức/kênh.

```bash
# Smoke test sau khi T01/T02 đã bàn giao, dùng fixture nhúng và ca lỗi.
python3 tests/run_tests.py --compiler nvcc --group gpu --suite gpu_v3_pipeline --require-t4

# Nghiệm thu với đúng bộ synthetic P7 và toàn bộ dataset cuối kỳ.
python3 tests/run_tests.py --compiler nvcc --group gpu --suite gpu_v3_pipeline \
  --require-t4 --v3-synthetic-dir results/synthetic --v3-dataset-dir dataset

# Memcheck suite và đường CLI production trên T4.
compute-sanitizer --tool memcheck --leak-check full --error-exitcode 99 \
  ./build/tests_gpu/gpu_v3_pipeline
python3 scripts/build.py --require-t4 --out-dir build
compute-sanitizer --tool memcheck --leak-check full --error-exitcode 99 \
  ./build/stitch dataset/site1/small_left.jpg dataset/site1/small_right.jpg \
  build/p8-v3-site1-small.png --version 3 --runs 1
```

Lượt nghiệm thu yêu cầu cả sáu fixture translation/projective và 12 cấu hình ảnh thật. Sau khi Thành tích hợp CLI, kiểm tra thêm header và các hàng CSV của `--version 3` theo `version_columns(3)` trong `scripts/run_benchmark.py`, thống nhất schema nếu contract production thay đổi. Lưu SHA, manifest ảnh, kết quả từng ca và hai log memcheck trước khi cập nhật task board.

## 4. Công cụ phát triển trong `tests/tools/`

- Kiểm tra hoặc sinh lại bảng mẫu BRIEF `src/common/brief_pattern.cpp` (seed 16):
  ```bash
  python tests/tools/tool_gen_brief_pattern.py --check
  ```
- Biên dịch và chạy 3 công cụ C++ (`tool_export_gray`, `tool_export_keypoints`, `tool_pipeline_trace`):
  ```bash
  python3 scripts/build.py --target tools
  ./build/tool_pipeline_trace dataset/site1/small_left.jpg dataset/site1/small_right.jpg build/trace_site1
  ```

## 5. Kiểm chứng S4/S5 GPU và công cụ P5-T09

```bash
python3 tests/run_tests.py --group gpu --compiler nvcc --require-t4
python3 tests/run_tests.py --suite gpu_s4 --suite gpu_s5 --compiler nvcc --require-t4
python3 scripts/build.py --target tools --tool tool_gpu_s45 --compiler nvcc --require-t4
compute-sanitizer --tool memcheck --error-exitcode 99 build/tests_gpu/gpu_s4
compute-sanitizer --tool memcheck --error-exitcode 99 build/tests_gpu/gpu_s5
```

`gpu_s4`, `gpu_s5` đăng ký danh sách source riêng. `--group all` bao gồm V0, GPU và Python; test Python mới là `test_profiling_scripts.py`.

S1 đến S3 của V1 (P5-T03, T06, T07) có các suite `gpu_blur`, `gpu_s1`, `gpu_s2`, `gpu_s3`. Ba suite `gpu_s1`, `gpu_s2` và `gpu_s3` nhận thêm `<left> <right>` để chạy trên ảnh thật; `gpu_s2` và `gpu_s3` chạy cả chuỗi stage V1 so với V0 (S1 → S2, và S1 → S4). Lệnh và kết quả ghi trong mục 7 của tài liệu từng stage.

```bash
python3 tests/run_tests.py --group gpu --suite gpu_blur --suite gpu_s1 --suite gpu_s2 --suite gpu_s3 --compiler nvcc --require-t4
./build/tests_gpu/gpu_s3 dataset/site1/small_left.jpg dataset/site1/small_right.jpg
```

`tool_gpu_s45` là driver kiểm chứng từ ảnh với S1–S3/S6 trên CPU. Driver kiểm tra match, prefix, mask và H với V0 ngoài vùng CUDA events. Xem [hướng dẫn profiling](../docs/profiling.md) cho cách chạy batch và lưu bằng chứng.

## 6. Viết suite GPU mới

Khai báo suite trong `GPU_SUITES` của `tests/run_tests.py`. Suite cần thêm cờ link khai báo ở `GPU_LINK_FLAGS`, suite đọc ảnh bằng stb thêm tên vào `GPU_STB_SUITES`.

Hai header trong `tests/support/` dùng để đối chiếu với V0, chỉ chạy trên Host:

| Header | Nội dung |
|---|---|
| `v0_reference.h` | `compute_v0_features` chạy V0 S1 đến S3 và giữ gray, keypoint, descriptor; `make_test_image` tạo ảnh có seed; `load_rgb_image` đọc ảnh thật |
| `gpu_compare.h` | `keypoint_mismatch`, `descriptor_mismatch`, `float_array_mismatch` so từng bit hoặc theo ngưỡng; trả chuỗi rỗng khi khớp, ngược lại mô tả phần tử lệch đầu tiên |

Không include `feature_test_support.h` trong suite GPU vì header đó thay global `new`. Bộ đệm Device và stream dùng lại namespace `gpu_test` trong `tests/gpu/s45_test_support.cuh`.
