<!-- Authors: Nguyen Ho Anh Tuan (23120185) -->
<!-- External source: none -->

# Cấu trúc và quy ước thư mục `src/`

Thư mục `src/` chứa toàn bộ mã nguồn C/C++/CUDA của chương trình ghép ảnh `stitch`. Mã nguồn được tách theo phần nền tảng dùng chung và từng phiên bản cài đặt (`V0`, `V1`, `V2`, `V3`) để bốn thành viên làm việc song song mà không nhân bản code giữa các phiên bản.

## 1. Tổ chức thư mục

```text
src/
├── main.cu          # Điểm vào CLI, đọc/ghi ảnh, vòng lặp warm-up + đo thời gian và in CSV
├── versions.h       # Khai báo hàm chạy pipeline của các phiên bản (--version 0|1|2|...)
├── common/          # Hợp đồng dữ liệu, cấu hình, tiện ích dùng chung và thư viện stb
├── v0/              # Bản tuần tự C/C++ đóng băng (chuẩn tham chiếu cho các bản GPU)
└── v1/, v2/, v3/    # Các phiên bản GPU (tạo tương ứng khi triển khai từng phiên bản)
```

Vai trò từng nhóm:

- `common/`: chứa `common.h` (struct dữ liệu standard-layout đi qua ranh giới Host–Device), `cuda_utils.cuh` (macro kiểm tra lỗi CUDA và đo `cudaEvent`), `v0_config.*` (tham số thuật toán dùng chung cho mọi phiên bản), các module hình học/lọc/biên/mẫu (`image_layout.*`, `gaussian_kernel.*`, `gaussian_blur.*`, `feature_border.h`, `fast_corner.*`, `brief_pattern.*`, `feature_support.*`) và `stb_image.h`, `stb_image_write.h`, `stb_impl.cpp`.
- `v0/`: cài đặt tuần tự 6 stage (`v0_preprocess.*`, `v0_detect.*`, `v0_describe.*`, `v0_match.*`, `v0_homography.*`, `v0_warp_blend.*`) và `v0_pipeline.*`.
- `v1/` (Basic CUDA): cài đặt GPU cơ bản cho đủ 6 stage cùng `v1_pipeline.*`.
- `v2/`, `v3/` (Optimized CUDA): chỉ tạo file mới cho những stage/kernel có thay đổi ở phiên bản đó cùng `v2_pipeline.*` / `v3_pipeline.*`. Những stage giữ nguyên gọi lại trực tiếp hàm từ phiên bản trước, không chép lại file cũ sang thư mục mới.

## 2. Quy ước viết code

- **Một gốc `#include` duy nhất (`-Isrc`):** mọi lệnh `#include` nội bộ phải ghi rõ tên thư mục con tính từ `src/`, ví dụ `#include "common/common.h"` hoặc `#include "v0/v0_pipeline.h"`. Không dùng đường dẫn tương đối kiểu `../common/common.h`.
- **Đặt tên file:** file gắn với một phiên bản cụ thể mang tiền tố `v<k>_` (`v0_detect.cpp`, `v1_detect.cu`, `v2_match.cu`...). File dùng chung trong `common/` không gắn tiền tố phiên bản (ngoại trừ `v0_config.*` giữ tên lịch sử của bộ tham số chuẩn).
- **Giới hạn thư viện và môi trường đích:** chỉ sử dụng thư viện chuẩn C/C++, CUDA Runtime và `stb` có sẵn trong `src/common/`. Mọi phiên bản phải biên dịch sạch trên Google Colab GPU Tesla T4 với `nvcc -arch=sm_75 -std=c++11 -O2`.
- **Bảo toàn chuẩn `V0`:** không sửa thuật toán hay tham số đã chốt của `V0`; không đưa OpenMP, `std::thread`, `std::async`, `std::execution` hoặc intrinsics SIMD vào `src/v0/`.
- **Ghi nhận tác giả và nguồn:** mọi file tạo mới hoặc chỉnh sửa phải có khối comment `Authors:` và `External source:` (hoặc `Adapted from:` kèm `Changes:`) ở đầu file; lưu mã hóa UTF-8 không BOM, xuống dòng LF.
- **Đo thời gian và gỡ lỗi:** log chi tiết và thao tác xuất ảnh trung gian chỉ bật khi có cờ `--debug` và phải nằm ngoài vùng bấm giờ của từng stage.

## 3. Biên dịch và chạy chương trình

Chạy từ thư mục gốc của repo thông qua `scripts/build.py`:

```bash
# Biên dịch chính thức bằng nvcc trên Colab Tesla T4
python3 scripts/build.py --compiler nvcc --require-t4

# Xem câu lệnh nvcc đầy đủ
python3 scripts/build.py --print-command

# Kiểm tra biên dịch sơ bộ trên máy cá nhân bằng g++ (khi chỉ chạy phần Host/V0)
python scripts/build.py --compiler g++

# Chạy ghép cặp ảnh với phiên bản được chọn
./build/stitch dataset/site1/small_left.jpg dataset/site1/small_right.jpg build/pano.png --version 0 --runs 5
```

