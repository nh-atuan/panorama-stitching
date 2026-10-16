# S3 - Description

Người phụ trách: Thành (23120166). Người soạn: Tuấn (23120185), làm thay ở P1. Cập nhật lần cuối: 16/10.

Task: P0-T08 (mục 1, 2), P1-T09 (mục 3, 4, 8), P1-T10 (code, mục 5, 7). Phương pháp và tham số trong tài liệu này là đề xuất của Tuấn, chờ Thành xác nhận; việc làm thay chờ cả Nhóm đồng ý.

S3 tính descriptor nhị phân 256 bit cho mỗi keypoint của S2 để S4 ghép bằng khoảng cách Hamming. S3 chạy độc lập trên từng ảnh của cặp.

## 1. Phương pháp đã chọn và các phương án đã cân nhắc

Phương pháp đã chọn: **BRIEF 256 bit không xoay** trên patch 31×31, ảnh được làm mượt thêm bằng Gaussian σ = 2 trước khi so sánh, pattern lấy mẫu theo kiểu G II của BRIEF (Gaussian đẳng hướng quanh keypoint), sinh một lần với seed cố định và lưu thành bảng hằng.

| Phương án | Chất lượng | Chi phí mỗi keypoint | Mức phù hợp GPU |
|---|---|---|---|
| **BRIEF không xoay (chọn)** | Phân biệt tốt khi hai ảnh gần như không xoay quanh trục quang; không bất biến xoay | 512 lần đọc, 256 phép so sánh | Mỗi keypoint một thread (hoặc một warp, mỗi lane 8 test); pattern nằm trong constant memory |
| Rotated BRIEF (ORB) | Bất biến xoay trong mặt phẳng ảnh | Thêm intensity centroid trên patch và xoay 512 tọa độ | Như trên, thêm một bước reduce trên patch |
| ORB với pattern học `bit_pattern_31` của OpenCV | Các test ít tương quan hơn pattern ngẫu nhiên | Như ORB | Như ORB; phải ghi nguồn bảng của OpenCV |
| BRISK, FREAK | Pattern vòng tròn, có orientation | Nhiều điểm làm mượt riêng | Phức tạp hơn, ít tài liệu hơn |
| Descriptor số thực (SIFT-like) | Bền với tỉ lệ và ánh sáng | Histogram gradient 128 chiều | S4 phải đổi sang L2, đổi interface `Descriptor` |

Lý do chọn: cặp ảnh được chụp bằng cách đứng yên, giữ máy ngang và xoay người quanh trục dọc (mục 3.2 của `docs/dataset.md`), nên giữa hai ảnh gần như không có phép xoay trong mặt phẳng ảnh. Khi đó orientation chỉ thêm nhiễu và thêm chi phí. Descriptor 256 bit khớp `Descriptor` trong `common.h` và matching Hamming của Đế. Nếu cặp khó cần bất biến xoay, rotated BRIEF dùng được trường `Keypoint::angle` đã có mà không phải đổi interface.

Làm mượt: BRIEF so sánh từng cặp pixel nên rất nhạy với nhiễu. Calonder và cộng sự (2010, mục 3.1) làm mượt patch bằng Gaussian σ = 2 trên cửa sổ 9×9 trước khi so sánh; OpenCV ORB làm mượt ảnh bằng Gaussian 7×7, σ = 2 trước khi tính bit. S1 chỉ blur σ = 1 để giữ góc cho FAST, nên S3 tự làm mượt thêm trên một bản sao riêng, không đổi ảnh của S1.

Pattern tự sinh thay vì dùng bảng của OpenCV: bảng tự sinh không phải mã lấy từ bên ngoài và giải thích được trọn vẹn. G II là cách lấy mẫu bài báo BRIEF chọn dùng vì nhỉnh hơn ba cách ngẫu nhiên còn lại trong phần lớn thí nghiệm (mục 3.2, hình 3).

## 2. Đầu vào và đầu ra

Chữ ký hàm nằm ở `src/v0_describe.h`:

```cpp
ErrorCode v0_describe(const GrayImage& image, std::vector<Keypoint>& keypoints,
                      std::vector<Descriptor>& descriptors, const Config& config,
                      bool debug_mode = false);
```

| Mục | Quy ước |
|---|---|
| Ảnh | `GrayImage` của S1 (cùng ảnh S2 dùng): `float` 1 kênh, [0, 1], stride tính bằng byte. S3 không ghi vào ảnh này |
| Keypoint vào | Output của S2. Chấp nhận tọa độ không nguyên: tâm patch là `(floor(x + 0.5), floor(y + 0.5))` |
| Keypoint ra | Chỉ giữ keypoint có patch 31×31 nằm trọn trong ảnh, giữ nguyên thứ tự; các trường `x, y, score, angle` không đổi |
| Descriptor ra | `descriptors[i]` ứng với `keypoints[i]`; bị xóa khi vào hàm |
| Bit | Test k nằm ở `data[k / 32]`, bit `k % 32`; bit bằng 1 khi điểm thứ nhất tối hơn điểm thứ hai (so sánh chặt), theo mục 3 của `docs/interface.md` |
| Cấu hình | S3 không có trường riêng trong `Config`; tham số `config` có mặt để các stage cùng dạng chữ ký |
| Lỗi | `ErrorCode`; khi lỗi, `keypoints` giữ nguyên và `descriptors` rỗng |

Với keypoint của S2, mọi keypoint đều được giữ vì S2 dùng border 15 (`kFeatureBorder`). Việc kiểm tra biên và compact vẫn có để S3 đúng với keypoint từ nguồn khác.

`std::vector<Descriptor>` cần bộ cấp phát trả địa chỉ căn 16 byte. Trên Linux x86-64 (Colab) `alignof(std::max_align_t)` bằng 16 nên điều này luôn đúng. Trên MinGW 32 bit ở máy cá nhân, `alignof(std::max_align_t)` chỉ là 8 và kiểm tra căn lề trong `FeatureView` của S4 có thể từ chối mảng; khi đó chỉ chạy test S3 riêng ở máy cá nhân, kết quả chính thức lấy từ Colab.

## 3. Tham số

Tất cả là hằng số của stage trong `src/brief_pattern.h`, dùng chung cho V0 đến V3 và cho cả ba kích thước ảnh. Không thêm trường vào `common.h`.

| Tham số | Giá trị | Đơn vị | Lý do chọn | Ảnh hưởng khi tăng/giảm |
|---|---|---|---|---|
| Số bit | 256 | bit | Cố định bởi `Descriptor` (8 word `uint32_t`) | — |
| Patch | 31×31, offset trong [-15, 15] | pixel | Cỡ patch của ORB; đủ ngữ cảnh mà vẫn nhỏ so với ảnh 1280×720 | Tăng: descriptor phân biệt hơn nhưng bỏ nhiều keypoint ở mép, cần đổi border của S2 |
| Pattern | G II: hai điểm độc lập theo Gaussian đẳng hướng σ = 31/5 = 6.2, làm tròn và kẹp trong patch | pixel | Phương án G II của BRIEF, σ² = S²/25 với S = 31 | σ lớn: test xa tâm, bền với nhiễu kém hơn khi ảnh lệch nhỏ |
| Seed pattern | 16 | — | Số nhóm; SplitMix64 | Đổi seed là đổi phương pháp, phải chạy lại mọi benchmark |
| Làm mượt σ | 2.0 | pixel | Giá trị BRIEF dùng (mục 3.1 của bài báo), cũng là giá trị của OpenCV ORB | Tăng: bền với nhiễu, kém phân biệt. Giảm: nhạy nhiễu |
| Làm mượt bán kính | 4 (9 tap) | pixel | Đúng cửa sổ 9×9 của BRIEF; thỏa r ≥ ⌈2σ⌉ của `validate_gaussian_params` | Nhỏ hơn làm kernel bị cắt nhiều |
| Biên khi làm mượt | Clamp, giống S1 | — | Dùng chung `gaussian_blur_in_place` với S1 | Chỉ ảnh hưởng keypoint sát mép; keypoint của S2 cách mép ít nhất 15 px |
| Orientation | Không | — | Mục 1 | — |

Ảnh hưởng lên tổng làm mượt: S1 σ = 1 rồi S3 σ = 2 tương đương một Gaussian σ = √5 ≈ 2.24 trên ảnh gốc.

## 4. Thuật toán chi tiết

### 4.1 Sinh pattern

`tests/tool_gen_brief_pattern.py` chạy một lần, ghi `src/brief_pattern.cpp`:

```text
rng = SplitMix64(seed = 16)
lặp tới khi đủ 256 test:
    lấy 4 số Gaussian chuẩn bằng Box-Muller từ rng
    mỗi số v -> offset = clamp(floor(6.2 * v + 0.5), -15, 15)
    test = (ax, ay, bx, by)
    bỏ nếu (ax, ay) == (bx, by), hoặc test đã có, hoặc test đảo ngược đã có
```

Bảng 256 dòng `{ax, ay, bx, by}` kiểu `int8_t` được commit cùng code; mọi version đọc cùng bảng. `python tests/tool_gen_brief_pattern.py --check` sinh lại và so với bảng đã commit. Trong bảng hiện tại độ lệch chuẩn của các offset là 6.30 (lý thuyết 6.2 trước khi kẹp) và 18 test có ít nhất một tọa độ bị kẹp ở ±15.

### 4.2 Tính descriptor

```text
v0_describe(image, keypoints, descriptors, config):
    descriptors.clear()
    kiểm tra image                         -> InvalidImage
    kiểm tra mọi x, y hữu hạn, số keypoint <= INT32_MAX -> InvalidArgument
    smoothed, temp = 2 mảng W*H float      -> AllocationFailed nếu thất bại
    smoothed = bản sao packed của image
    làm mượt smoothed: Gaussian separable σ=2, r=4, clamp biên

    với i theo thứ tự đầu vào:
        cx = floor(x_i + 0.5), cy = floor(y_i + 0.5)     # tính bằng double
        nếu cx ngoài [15, W-16] hoặc cy ngoài [15, H-16]: bỏ keypoint i
        d = 0 (8 word)
        với k = 0..255:
            (ax, ay, bx, by) = pattern[k]
            nếu smoothed(cx+ax, cy+ay) < smoothed(cx+bx, cy+by):
                d.data[k / 32] |= 1 << (k % 32)
        giữ keypoint i, thêm d

    thay keypoints bằng danh sách đã giữ, descriptors bằng các d tương ứng
```

Điểm cần giữ khi cài đặt và khi viết bản GPU:

- Kết quả chỉ phụ thuộc giá trị đã làm mượt và phép so sánh `<`, không có phép cộng dồn nào khác. Nếu V1 làm mượt đúng như V0 (cùng trọng số, cùng thứ tự cộng) thì descriptor giống từng bit.
- Thời gian làm mượt tính vào S3.
- Kết quả chỉ được công bố khi thành công: mọi buffer tạm được cấp phát trước khi thay `keypoints`.

Độ phức tạp: làm mượt `O(W·H·2·9)`; descriptor `O(N·256)`. Bộ nhớ thêm: `2·W·H·4` byte.

Mã nguồn:

| File | Nội dung |
|---|---|
| `src/brief_pattern.h`, `src/brief_pattern.cpp` | Hằng số S3 và bảng 256 test (file sinh tự động) |
| `src/v0_describe.h`, `src/v0_describe.cpp` | Kiểm tra đầu vào, làm mượt, compact, ghép bit |
| `src/gaussian_blur.h`, `src/gaussian_blur.cpp` | Blur separable tại chỗ, dùng chung với S1 (tách ra từ `v0_preprocess.cpp`, kết quả S1 không đổi) |
| `src/gaussian_kernel.h`, `src/gaussian_kernel.cpp` | Trọng số Gaussian của S1 |
| `tests/tool_gen_brief_pattern.py` | Sinh và kiểm tra bảng pattern |

## 5. Bằng chứng chất lượng

Chưa có kết quả trên Colab. Bằng chứng của S3 gộp với S2 (mục 5 của `docs/stages/s2-detection.md`): số match S4 và số inlier S5 trên cặp ảnh thật.

## 6. Mức phù hợp với GPU và mapping V1 dự kiến

Chưa viết (P3).

## 7. Kiểm thử

Test nằm ở `tests/test_v0_describe.cpp`, dùng dữ liệu tự tạo.

| Test | Đầu vào | Kết quả mong đợi |
|---|---|---|
| Bảng pattern | `kBriefPattern` | 256 test, offset trong [-15, 15], hai điểm khác nhau, không có test lặp hoặc đảo ngược |
| Quy ước bit theo x | Ảnh ramp tăng dần theo x | Bit k bằng 1 khi và chỉ khi `ax < bx`; `ax == bx` cho 0; kiểm tra đúng vị trí `data[k / 32]`, bit `k % 32` |
| Quy ước bit theo y | Ảnh ramp tăng dần theo y | Bit k bằng 1 khi và chỉ khi `ay < by` |
| Cùng điểm, cùng ảnh | Gọi hai lần | Cùng descriptor |
| Làm tròn tâm | (99.6, 80.4), (100.49, 79.5) | Giống descriptor của (100, 80) |
| Dịch ảnh | Ảnh B là ảnh A dịch (-7, 5); 40 điểm | Descriptor giống từng bit |
| Compact | Danh sách có keypoint ở đúng biên, ngoài biên sau khi làm tròn, tọa độ ±1e30, trùng lặp | Giữ đúng 5 keypoint theo thứ tự cũ; `descriptors[i]` khớp descriptor tính riêng của `keypoints[i]` |
| Căn lề | Mảng descriptor | Địa chỉ chia hết cho 16 |
| Ảnh hẹp hơn patch | 30×40 | `Success`, hai mảng rỗng |
| Danh sách rỗng | | `Success`, hai mảng rỗng |
| Khoảng cách | 60 điểm trên ảnh nhiễu | Hamming trung bình giữa các điểm khác nhau trong (110, 146) |
| Padding, ảnh không bị ghi | Cùng ảnh có và không có padding | Descriptor giống nhau; pixel và padding giữ nguyên |
| Tọa độ không hữu hạn | x NaN, y vô hạn | `InvalidArgument`, keypoints giữ nguyên, descriptors rỗng |
| Ảnh sai | Null, 3 kênh, stride theo phần tử, width 0 | `InvalidImage` |
| Ảnh và keypoint cùng sai | | `InvalidImage` |
| Cấp phát thất bại | Giả lập `bad_alloc` | `AllocationFailed`, keypoints giữ nguyên |

Test tích hợp S1 → S5 nằm ở `tests/test_v0_detect_describe.cpp` (mục 7 của tài liệu S2).

Lệnh build và chạy ở máy cá nhân:

```bash
python tests/tool_gen_brief_pattern.py --check
g++ -std=c++11 -Wall -Wextra -Wpedantic -Werror -O2 -I src \
    src/v0_describe.cpp src/brief_pattern.cpp src/gaussian_blur.cpp src/gaussian_kernel.cpp \
    src/image_layout.cpp tests/test_v0_describe.cpp -o build/test_v0_describe
./build/test_v0_describe
```

Lệnh chạy trên Colab T4 từ gốc repo:

```bash
nvidia-smi
nvcc -arch=sm_75 -std=c++11 -O2 -Xcompiler=-Wall,-Wextra,-Werror -I src \
    src/v0_describe.cpp src/brief_pattern.cpp src/gaussian_blur.cpp src/gaussian_kernel.cpp \
    src/image_layout.cpp tests/test_v0_describe.cpp -o build/test_v0_describe
./build/test_v0_describe
```

Kết quả:

| Ngày | Môi trường | Kết quả |
|---|---|---|
| 16/10 | Máy cá nhân, MinGW g++ 6.3.0 (32 bit) | `PASS: 2300 assertions for S3 BRIEF description` |
| 16/10 | Colab Tesla T4, CUDA 13.0 (V13.0.88), `nvcc` như trên | `OK: brief_pattern.cpp matches the generator (256 tests, seed 16)`; build không lỗi; `PASS: 2300 assertions for S3 BRIEF description` |
| 16/10 | Colab, g++ 13.3 với `-fsanitize=address,undefined -fno-sanitize-recover=all` | `PASS: 2300 assertions ...`, không có báo lỗi sanitizer |

Sau khi tách `gaussian_blur.cpp` và `image_layout.cpp` khỏi S1, test S1 vẫn đạt trên cùng phiên Colab T4: `PASS: 1758 assertions for S1 grayscale, blur, errors and OOM`, cả khi build với sanitizer.

## 8. Trường hợp biên và rủi ro

| Trường hợp | Phát hiện và xử lý | Kết quả |
|---|---|---|
| Ảnh null, sai kênh, sai stride, lệch căn lề, tràn kích thước | Kiểm tra layout dùng chung với S1, S2 | `InvalidImage` |
| x hoặc y NaN, vô hạn | Kiểm tra trước khi cấp phát | `InvalidArgument`, keypoints giữ nguyên |
| Hơn INT32_MAX keypoint | Kiểm tra số lượng (index của `Match` là `int32_t`) | `InvalidArgument` |
| Tọa độ hữu hạn nhưng rất lớn (±1e30) | Làm tròn bằng `double`, so với biên trước khi ép kiểu | Bị bỏ, không tràn số |
| Patch chạm mép ảnh | So tâm làm tròn với [15, W-16] × [15, H-16] | Bị bỏ, hai mảng compact cùng nhau |
| Ảnh nhỏ hơn 31 px theo một chiều | Mọi keypoint bị bỏ | `Success`, hai mảng rỗng |
| Cấp phát buffer làm mượt thất bại | Bắt `std::bad_alloc` | `AllocationFailed`, keypoints giữ nguyên |
| Hai ảnh lệch xoay quanh trục quang (máy nghiêng khi chụp) | BRIEF không xoay mất dần khả năng ghép khi góc lệch tăng | Rủi ro với cặp chụp nghiêng; phương án là rotated BRIEF, không đổi interface |
| Khác biệt sáng tối giữa hai ảnh | Test nhị phân chỉ phụ thuộc thứ tự cường độ trong patch | Bền với thay đổi độ sáng đều; không bền với bóng đổ cục bộ |
| Vùng phẳng, họa tiết lặp | Nhiều test bằng nhau cho bit 0, descriptor giống nhau giữa các điểm | Ratio test của S4 loại phần lớn; S5 loại phần còn lại |
| Căn lề `std::vector<Descriptor>` trên nền tảng có `alignof(max_align_t) < 16` | Không xảy ra trên Colab x86-64 | Chỉ ảnh hưởng chạy thử ở máy cá nhân 32 bit (mục 2) |

## 9. Nguồn tham khảo

| Nguồn | Ngày truy cập | Dùng cho phần nào |
|---|---|---|
| [Calonder, M., Lepetit, V., Strecha, C., Fua, P. (2010). BRIEF: Binary Robust Independent Elementary Features. ECCV](https://www.cs.ubc.ca/~lowe/525/papers/calonder_eccv10.pdf) | 16/10 | Test nhị phân, cách lấy mẫu G II (mục 3.2 của bài báo), làm mượt σ = 2 trên cửa sổ 9×9 (mục 3.1) (mục 1, 3, 4) |
| [Rublee, E. và cộng sự (2011). ORB: an efficient alternative to SIFT or SURF. ICCV](https://doi.org/10.1109/ICCV.2011.6126544) | 16/10 | Patch 31×31, phương án rotated BRIEF (mục 1, 3) |
| [OpenCV 4.x, `orb.cpp`](https://github.com/opencv/opencv/blob/4.x/modules/features2d/src/orb.cpp) | 16/10 | Đối chiếu cách làm mượt trước khi tính bit (mục 1); không dùng code hay bảng pattern |
| [Vigna, S. SplitMix64](https://prng.di.unimi.it/splitmix64.c) | 16/10 | Bộ sinh số ngẫu nhiên cho pattern (mục 4.1) |
| [Đề cuối kỳ CSC14120](../specs/CSC14120_2026_Final%20Project.md), mục 2 | 16/10 | Yêu cầu stage |

## 10. Lịch sử thay đổi tham số

| Ngày | Thay đổi | Lý do |
|---|---|---|
| 16/10 | Đề xuất BRIEF 256 bit không xoay, patch 31, G II σ = 6.2, seed 16, làm mượt σ = 2, r = 4 | Giá trị ban đầu, chờ Thành xác nhận. Ở P2 xem số inlier trên cặp khó để quyết định có cần orientation không |
