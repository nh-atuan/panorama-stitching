<!-- Authors: Le Thuong De (23120232), Nguyen Ho Anh Tuan (23120185) -->
<!-- External source: none -->

# Cấu trúc và hướng dẫn chạy `tests/`

Thư mục `tests/` chứa toàn bộ bài kiểm thử tự động (C++/CUDA và Python) cùng các công cụ CLI hỗ trợ xuất dữ liệu trung gian của pipeline.

## 1. Tổ chức thư mục

```text
tests/
├── run_tests.py     # Trình chạy kiểm thử thống nhất cho cả C++/CUDA và Python
├── support/         # Header và hàm tiện ích dùng chung giữa các bài test (feature_test_support.h)
├── v0/              # 13 suite C++ kiểm thử đơn vị và tích hợp cho từng stage S1-S6 và V0 pipeline
├── gpu/             # Các suite .cu đối chiếu kết quả GPU (V1, V2, V3) với V0 (thêm khi làm GPU)
├── python/          # 5 suite Python unittest kiểm thử scripts/ và cấu trúc notebook
└── tools/           # Công cụ CLI sinh bảng hằng và xuất ảnh/trace trung gian để debug
```

## 2. Quy ước viết và đăng ký bài test mới

- **Đường dẫn `#include`:** trình biên dịch test luôn nhận hai cờ `-Isrc -Itests`. Ghi rõ thư mục con trong mọi lệnh `#include`, ví dụ `#include "common/common.h"`, `#include "v0/v0_match.h"`, `#include "support/feature_test_support.h"`.
- **Tách file test GPU theo stage:** khi viết test trong `tests/gpu/`, mỗi thành viên đặt bài test vào file riêng của stage mình phụ trách (ví dụ `test_gpu_s1_preprocess.cu`, `test_gpu_s2_detect.cu`..., `test_gpu_pipeline.cu`) để tránh xung đột khi merge song song và tái sử dụng xuyên suốt từ `V1` sang `V3`.
- **Đăng ký suite vào `tests/run_tests.py`:** mỗi suite C++/CUDA khai báo rõ danh sách file nguồn tối thiểu cần liên kết trong `tests/run_tests.py`, không dùng wildcard gom toàn bộ `src/` để tránh kéo theo các phiên bản không liên quan.
- **Test Python:** đặt file dạng `test_*.py` trong `tests/python/` và xác định thư mục gốc repo bằng `ROOT = Path(__file__).resolve().parents[2]`.
- **Tính tái lập và comment đầu file:** mọi dữ liệu thử có yếu tố ngẫu nhiên phải cố định seed; mọi file test mới hoặc chỉnh sửa phải có comment `Authors:` và `External source:` ở đầu file.

## 3. Các lệnh chạy kiểm thử

Thực thi từ thư mục gốc của repo:

```bash
# Chạy đầy đủ toàn bộ kiểm thử chính thức trên Google Colab Tesla T4 (trước khi mở PR)
python3 tests/run_tests.py --compiler nvcc --require-t4

# Chạy toàn bộ 13 suite C++ V0 kèm AddressSanitizer + UBSan trên Linux 64-bit
python3 tests/run_tests.py --compiler g++ --group v0 --sanitizers

# Chạy nhanh một hoặc vài suite cụ thể trong lúc sửa code
python tests/run_tests.py --compiler g++ --suite preprocess --suite pipeline

# Chỉ chạy 5 suite kiểm thử Python (dataset, synthetic, benchmark, plot, notebook)
python tests/run_tests.py --group python

# Liệt kê danh sách các suite hiện có
python tests/run_tests.py --list
```

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

`gpu_s4`, `gpu_s5` đăng ký danh sách source riêng. `--group all` bao gồm V0, GPU và Python; test Python mới là `test_profiling_scripts.py`. Phần đăng ký này phục vụ S4/S5, phần mở rộng GPU tổng quát của P5-T04 vẫn do Thành phụ trách.

`tool_gpu_s45` là driver kiểm chứng từ ảnh với S1–S3/S6 trên CPU. Driver kiểm tra match, prefix, mask và H với V0 ngoài vùng CUDA events. Xem [hướng dẫn profiling](../docs/profiling.md) cho cách chạy batch và lưu bằng chứng.
