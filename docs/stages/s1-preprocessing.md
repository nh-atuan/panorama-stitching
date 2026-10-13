# S1 - Preprocessing

Người phụ trách: Tuấn. Cập nhật lần cuối: 13/10.

S1 nhận ảnh màu đã đọc bằng stb, chuyển sang ảnh xám rồi làm mượt để giảm nhiễu trước khi S2 tìm keypoint, theo mô tả của [đề cuối kỳ](../specs/CSC14120_2026_Final%20Project.md) mục 2.1. S1 chạy độc lập trên từng ảnh của cặp.

## 1. Phương pháp đã chọn và các phương án đã cân nhắc

Phương pháp đã chọn: **grayscale BT.601 có trọng số, sau đó Gaussian blur separable** (một lượt ngang, một lượt dọc), biên xử lý bằng **clamp**. Không dùng image pyramid ở V0.

### 1.1 Chuyển ảnh xám

| Phương án | Công thức | Chất lượng | Chi phí mỗi pixel | Mức phù hợp GPU |
|---|---|---|---|---|
| **BT.601 có trọng số (chọn)** | `Y = 0.299 R + 0.587 G + 0.114 B` | Sát độ nhạy sáng của mắt; giữ được tương phản giữa các vùng khác màu, là quy ước phổ biến nên dễ đối chiếu kết quả | 3 phép nhân, 2 phép cộng | Map 1 thread cho 1 pixel, không phụ thuộc giữa các pixel |
| Trung bình cộng | `Y = (R + G + B) / 3` | Hai vùng khác màu nhưng cùng tổng R+G+B cho cùng giá trị xám, nên mất bớt cạnh và góc | 2 phép cộng, 1 phép nhân | Như trên |

Lý do chọn: chênh lệch chi phí không đáng kể, vì S1 bị giới hạn bởi băng thông bộ nhớ chứ không bởi số phép tính. BT.601 giữ được nhiều cạnh hơn cho S2.

### 1.2 Làm mượt

| Phương án | Chất lượng | Chi phí mỗi pixel (kernel k×k) | Mức phù hợp GPU |
|---|---|---|---|
| **Gaussian separable (chọn)** | Cho kết quả bằng Gaussian 2D (sai khác chỉ do làm tròn số thực), vì kernel Gaussian tách được thành tích hai kernel 1D | 2k phép nhân-cộng, ví dụ k = 9 cần 18 | Stencil cổ điển. Mỗi lượt 1D dùng tile shared memory có halo; đề gợi ý đúng tối ưu này. Cần thêm một buffer trung gian |
| Gaussian 2D | Chuẩn tham chiếu | k² phép nhân-cộng, ví dụ k = 9 cần 81 | Song song tốt nhưng đọc nhiều hơn; với ảnh 3840×2160 chi phí tăng nhanh theo k |
| Separable + image pyramid | Cho S2 khả năng tìm keypoint ở nhiều tỉ lệ | Thêm các tầng thu nhỏ, cộng thêm khoảng 1/3 khối lượng | Mỗi tầng là một stencil nhỏ; các tầng nhỏ khó lấp đầy GPU. Kéo theo thay đổi interface của S2 và S3 |

Lý do chọn: separable cho cùng chất lượng với 2D nhưng chi phí tuyến tính theo k. Pyramid chưa cần cho V0 vì hai ảnh của cặp cùng độ phân giải và gần cùng tỉ lệ. Nếu Thành cần multi-scale cho S2, hai người sẽ cùng xem lại; nếu không thống nhất được thì báo lại cho cả Nhóm để cùng quyết định.

### 1.3 Xử lý biên

| Phương án | Ưu điểm | Nhược điểm |
|---|---|---|
| **Clamp, lặp pixel biên (chọn)** | Biên không bị tối; trên GPU chỉ cần `min`/`max` chỉ số | Biên hơi lệch so với ảnh thật khi kernel lớn |
| Reflect-101 | Mượt hơn ở biên | Công thức chỉ số phức tạp hơn một chút |
| Zero padding | Dễ cài nhất | Làm tối biên, có thể sinh keypoint giả ở mép ảnh |

## 2. Đầu vào và đầu ra

Các quy ước dưới đây khớp với `docs/interface.md` và `src/common.h`. Chữ ký hàm nằm ở `src/v0_preprocess.h`.

```cpp
ErrorCode v0_preprocess(const Image& input, GrayImage& output,
                        const Config& config, bool debug_mode = false);
```

| Mục | Đầu vào (`Image`) | Đầu ra (`GrayImage`) |
|---|---|---|
| Nội dung | Ảnh màu đọc bằng `stbi_load(..., 3)` | Ảnh xám đã làm mượt |
| Kiểu phần tử | `uint8_t` | `float` (32 bit) |
| Kênh | 3, RGB xen kẽ (`R G B R G B ...`) | 1 |
| Miền giá trị | [0, 255] | [0, 1] (giá trị xám chia cho 255) |
| Bố cục | Row-major, pixel `(x, y)` kênh `c` ở byte `y * stride + x * 3 + c` | Row-major, pixel `(x, y)` là phần tử thứ `x` của hàng bắt đầu ở byte `y * stride` |
| Stride | Tính bằng byte, `stride >= width * 3`. Ảnh không padding có `stride = width * 3` | Tính bằng byte, `stride >= width * 4` và chia hết cho 4. Ảnh `float` không padding có `stride = width * 4`, không phải `width` |
| Kích thước | `width × height` | Bằng đầu vào |
| Tọa độ | Gốc ở góc trên trái, x tăng sang phải, y tăng xuống dưới | Như đầu vào |

Đọc pixel `(x, y)` của ảnh xám:

```cpp
const unsigned char* base = reinterpret_cast<const unsigned char*>(img.data);
const float* row = reinterpret_cast<const float*>(base + size_t(y) * img.stride);
float v = row[x];
```

Cấp phát bộ nhớ:

| Buffer | Ai cấp phát | Lý do |
|---|---|---|
| `output` | Bên gọi, trước vùng đo, dùng lại qua các lần chạy | Kích thước bằng ảnh vào nên biết trước; thời gian đo chỉ gồm phần tính; V1 giữ được dữ liệu trên GPU giữa các stage |
| Buffer `float` `width × height` cho lượt blur ngang | S1 tự cấp phát trong mỗi lần gọi và giải phóng khi thoát | Chỉ sống trong S1. Thời gian cấp phát này tính vào S1 |

S6 tự cấp phát output vì kích thước canvas chỉ biết sau khi tính từ H; S1 không có ràng buộc đó.

`output` phải khác null, cùng `width`, `height` với `input`, `channels = 1`, stride hợp lệ và địa chỉ căn theo 4 byte; sai thì trả `InvalidImage` và không ghi gì vào `output`. Padding của cả hai ảnh không được đọc hay ghi. Ở chế độ debug, S1 chỉ ghi một dòng log ra stderr; ảnh minh họa do công cụ trong `tests/` tạo, nằm ngoài vùng đo.

Tham số của S1 nằm trong `Config`: `gaussian_sigma` và `gaussian_radius`.

## 3. Tham số

Các giá trị dưới đây dùng chung cho V0 đến V3 và cho cả ba kích thước ảnh. Chưa có thực nghiệm trên ảnh thật; việc xác nhận σ nằm ở P2 (xem mục 10).

| Tham số | Giá trị | Đơn vị | Lý do chọn | Ảnh hưởng khi tăng/giảm |
|---|---|---|---|---|
| `gaussian_sigma` | 1.0 | pixel | Đủ làm giảm nhiễu mà vẫn giữ góc cho FAST | Tăng: ảnh mượt hơn, keypoint ít và kém sắc hơn. Giảm: giữ nhiễu, FAST dễ nhận keypoint giả |
| `gaussian_radius` | 3 (kernel 7 tap) | pixel | `r = ⌈3σ⌉` giữ khoảng 99,7% khối lượng kernel. FAST dùng vòng tròn bán kính 3 nên blur mạnh hơn sẽ làm mất góc | Tăng: nhiều phép tính và halo lớn hơn trên GPU. Giảm: kernel bị cắt, mượt không đều |
| Hệ số xám | 0.299, 0.587, 0.114 (BT.601) | — | Sát độ nhạy sáng của mắt; giữ tương phản giữa vùng khác màu | Đổi sang trung bình cộng làm mất cạnh giữa vùng cùng tổng R+G+B |
| Chia chuẩn hóa | `/ 255` ra `float` | — | Miền [0, 1] theo `docs/interface.md` | — |
| Trọng số kernel | Tính bằng `double`, chuẩn hóa tổng bằng 1, rồi ép `float`; một hàm sinh trọng số dùng chung (`src/gaussian_kernel.cpp`) | — | Kernel bị cắt không làm tối ảnh; mọi phiên bản dùng cùng giá trị | — |
| Xử lý biên | Clamp, lặp pixel biên | — | Không làm tối mép, tránh keypoint giả ở mép | — |
| Giới hạn `gaussian_radius` | 1 ≤ r ≤ 16 | pixel | Chặn halo của tile shared memory ở V2 | — |
| Điều kiện σ, r | σ hữu hạn, σ > 0, r ≥ ⌈2σ⌉; sai trả `InvalidConfig` | — | Tránh kernel bị cắt quá nhiều | — |
| Image pyramid | Không dùng | — | Làm đổi interface của S2, S3; đề yêu cầu mọi phiên bản cùng phương pháp | — |
| Dung sai V0 so với GPU | Sai lệch tuyệt đối lớn nhất ≤ 1e-5 | [0, 1] | Lệch do FMA cỡ 1e-7; một mức xám là 0,0039 | — |

Một bộ σ, r cho 1280×720, 1920×1080 và 3840×2160 vì đề yêu cầu cùng tham số. Hệ quả: ở 4K ảnh được làm mượt ít hơn so với nội dung ảnh.

S2 dùng ảnh đầu ra này trực tiếp. Ngưỡng FAST của Thành phụ thuộc độ mượt, nên σ = 1.0 cần báo cho Thành. Nếu S3 cần ảnh mượt hơn thì S3 tự làm mượt thêm.

## 4. Thuật toán chi tiết

Với ảnh `W × H`, `r = gaussian_radius`, trọng số `w[-r..r]`:

```text
v0_preprocess(input, output, config):
    kiểm tra input, output           -> InvalidImage
    sinh w[] từ sigma, radius        -> InvalidConfig nếu tham số sai
    cấp phát temp (W*H float)        -> AllocationFailed nếu thất bại

    # lượt 1: grayscale, ghi vào output
    với mỗi (x, y):
        output(x, y) = (0.299*R + 0.587*G + 0.114*B) / 255

    # lượt 2: blur ngang, output -> temp
    với mỗi (x, y):
        temp(x, y) = tổng k = -r..r của w[k] * output(clamp(x+k, 0, W-1), y)

    # lượt 3: blur dọc, temp -> output
    với mỗi (x, y):
        output(x, y) = tổng k = -r..r của w[k] * temp(x, clamp(y+k, 0, H-1))
```

Điểm cần giữ khi cài đặt:

- Tổng bắt đầu từ 0 và cộng theo thứ tự cố định từ `k = -r` tới `k = +r`, nên chạy lại cho kết quả giống từng bit.
- Lượt dọc cộng dồn theo từng hàng (với mỗi `k`, duyệt cả hàng), nên bộ nhớ vẫn đọc theo hàng; thứ tự cộng của mỗi pixel không đổi.
- Input được đọc theo `stride` byte của nó, không giả định liền khít `W * 3`.
- Mỗi hàng chỉ ghi `W` phần tử đầu; padding không bị chạm tới.

Độ phức tạp: `O(W·H·(2(2r+1) + 1))` phép tính; bộ nhớ thêm `W·H·4` byte.

Mã nguồn: `src/v0_preprocess.cpp` (ba lượt, kiểm tra đầu vào) và `src/gaussian_kernel.cpp` (kiểm tra tham số, sinh trọng số).

## 5. Bằng chứng chất lượng

Chưa có. Mục này dùng ảnh xám trước và sau blur của một cặp ảnh dev; công cụ `tests/tool_export_gray.cpp` xuất hai ảnh đó dưới dạng PNG 8-bit (để xem) và file `.f32` (giá trị `float` nguyên vẹn, để làm đầu vào cho S2, S3). File `.f32` gồm `int32 width`, `int32 height`, rồi `width × height` số `float` trong [0, 1], row-major, không padding, little-endian. Cặp ảnh dev chưa chuẩn bị.

## 6. Mức phù hợp với GPU và mapping V1 dự kiến

Chưa viết.

## 7. Kiểm thử

Test nằm ở `tests/test_v0_preprocess.cpp`, mỗi test dùng dữ liệu tự tạo có đáp án tính độc lập (Gaussian 2D cài trực tiếp bằng `double`). Đã chạy trên Colab T4 ngày 13/10 (kết quả ở dưới).

Lệnh build và chạy ở máy cá nhân (g++):

```bash
g++ -std=c++11 -Wall -Wextra -Wpedantic -Werror -O2 -I src \
    src/v0_preprocess.cpp src/gaussian_kernel.cpp tests/test_v0_preprocess.cpp -o build/test_v0_preprocess
./build/test_v0_preprocess
```

Lệnh chạy trên Colab T4 từ gốc repo, in `nvidia-smi` trước:

```bash
nvcc -arch=sm_75 -I src src/v0_preprocess.cpp src/gaussian_kernel.cpp tests/test_v0_preprocess.cpp -o test_s1
./test_s1
```

Kết quả ngày 13/10:

| Môi trường | Lệnh | Kết quả |
|---|---|---|
| Máy cá nhân, g++ `-std=c++11 -Wall -Wextra -Wpedantic -Werror -O2` | Như trên | `PASS: 1758 assertions for S1 grayscale, blur, errors and OOM` |
| Colab Tesla T4, CUDA 13.0 (V13.0.88) | `nvcc -arch=sm_75 ...` | Build không lỗi; `PASS: 1758 assertions for S1 grayscale, blur, errors and OOM` |
| Colab Tesla T4 | `g++ -fsanitize=address,undefined -fno-sanitize-recover=all` | Build không lỗi; `PASS: 1758 assertions ...`, không có báo lỗi sanitizer |

| Test | Đầu vào | Kết quả mong đợi |
|---|---|---|
| Trọng số kernel | Một số cặp (σ, r) hợp lệ | Đối xứng, tổng bằng 1, khớp công thức |
| Ảnh hằng 128 | Mọi pixel bằng 128 | Mọi pixel, kể cả biên, bằng 128/255 |
| Ảnh thuần R, G, B; đen; trắng | Một màu | 0.299, 0.587, 0.114; 0; 1 |
| Một điểm sáng ở giữa | Ảnh đen, một pixel bằng 1 | Bằng tích ngoài hai kernel 1D, đối xứng, tổng bằng 1/255 |
| Ảnh ngẫu nhiên | Seed cố định, nhiều kích thước, nhiều cặp (σ, r) | Lệch ≤ 1e-5 so với Gaussian 2D cài trực tiếp |
| Input và output có padding | Cùng pixel, padding khác nhau | Giống input không padding; padding không đổi và không ảnh hưởng |
| Ảnh nhỏ | 1×1, 1×N, N×1, 2×2 và các ảnh nhỏ hơn bán kính | Khớp tham chiếu, không đọc ngoài bộ nhớ (cấp phát đúng kích thước) |
| Input, output, config sai | Null, kênh, kích thước, stride (kể cả tràn), căn lề, σ NaN, r ngoài khoảng | Đúng `ErrorCode`, output không đổi |
| Chạy hai lần, tái dùng output | Cùng đầu vào | Giống từng bit |
| Cấp phát thất bại | Giả lập `bad_alloc` | `AllocationFailed`, output không đổi |

AddressSanitizer và UndefinedBehaviorSanitizer chạy trên Colab (MinGW trên máy cá nhân không hỗ trợ). Công cụ `tests/tool_export_gray.cpp` chưa chạy trên Colab.

## 8. Trường hợp biên và rủi ro

S1 trả `ErrorCode`, không gọi `exit()`. Bên gọi chỉ dùng output khi nhận `Success`.

| Trường hợp | Phát hiện và xử lý | Trạng thái |
|---|---|---|
| `data` null, `width` hoặc `height` ≤ 0, `channels != 3` ở input | Kiểm tra đầu vào | `InvalidImage` |
| Output null, khác kích thước, `channels != 1`, stride < `width * 4`, stride không chia hết cho 4, địa chỉ lệch 4 byte | Kiểm tra output | `InvalidImage` |
| Stride nhỏ hơn một hàng pixel (ví dụ truyền stride theo phần tử cho ảnh `float`) | So `stride` với `width * bytes_per_pixel` | `InvalidImage` |
| Tràn số khi tính `width * bytes_per_pixel`, `stride * height` hoặc `W·H·4` | Kiểm tra bằng phép chia trước khi nhân | `InvalidImage` |
| σ NaN, vô hạn, ≤ 0 | `validate_gaussian_params` | `InvalidConfig` |
| `gaussian_radius` ngoài [1, 16] hoặc nhỏ hơn ⌈2σ⌉ | `validate_gaussian_params` | `InvalidConfig` |
| `Config` chưa đặt (giá trị 0) | Như trên | `InvalidConfig` |
| Cấp phát buffer trung gian thất bại | Bắt `std::bad_alloc` | `AllocationFailed` |
| Ảnh 1×1, 1×N, nhỏ hơn bán kính kernel | Clamp lặp pixel biên, không có nhánh riêng | `Success` |
| Padding của input hoặc output | Không đọc, không ghi | — |

Ghi chú:

- S1 chỉ kiểm tra được stride và kích thước, không kiểm tra được buffer thực sự có đủ `stride * height` byte. Việc đó thuộc bên gọi.
- Mọi lỗi đầu vào trả về trước khi ghi vào `output`. Khi cả ảnh và config sai, trả `InvalidImage`.
- Ở 4K cùng σ = 1.0 làm ảnh mượt ít hơn theo tỉ lệ nội dung so với 720p; số keypoint có thể khác nhau giữa các kích thước.
- S1 là stage bị giới hạn bởi băng thông bộ nhớ; chưa có số đo.

## 9. Nguồn tham khảo

| Nguồn | Ngày truy cập | Dùng cho phần nào |
|---|---|---|
| [Đề cuối kỳ CSC14120](../specs/CSC14120_2026_Final%20Project.md), mục 2.1 và 2.2 | 07/10 | Mục 1 |

## 10. Lịch sử thay đổi tham số

| Ngày | Thay đổi | Lý do |
|---|---|---|
| 13/10 | Chốt σ = 1.0, r = 3 | Giá trị ban đầu theo mục 3. Ở P2 so số keypoint và inlier với σ bằng 0.8, 1.0, 1.5 trên cặp ảnh thật để xác nhận |
