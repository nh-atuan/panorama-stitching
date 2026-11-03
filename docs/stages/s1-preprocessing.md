# S1 - Preprocessing

Người phụ trách: Tuấn. Cập nhật lần cuối: 21/10.

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

Mã nguồn: `src/v0_preprocess.cpp` (kiểm tra đầu vào, chuyển ảnh xám), `src/gaussian_blur.cpp` (hai lượt blur, dùng chung với S3), `src/gaussian_kernel.cpp` (kiểm tra tham số, sinh trọng số) và `src/image_layout.cpp` (kiểm tra layout ảnh theo stride byte, dùng chung với S2, S3). Ngày 16/10 phần blur và kiểm tra layout được tách khỏi `v0_preprocess.cpp` để S3 dùng lại; thuật toán và thứ tự cộng không đổi.

## 5. Bằng chứng chất lượng

Công cụ `tests/tool_export_gray.cpp` chạy S1 trên một ảnh và xuất hai ảnh: chỉ chuyển xám (`_gray`) và chuyển xám rồi làm mượt với σ = 1.0, r = 3 (`_blur`), mỗi ảnh có bản PNG 8-bit để xem và bản `.f32` giữ nguyên giá trị `float`. File `.f32` gồm `int32 width`, `int32 height`, rồi `width × height` số `float` trong [0, 1], row-major, không padding, little-endian. Ảnh xuất ra nằm trong `results/` (đã ignore), không commit.

Ngày 18/10, trên Colab T4, công cụ chạy trên ảnh trái của 4 cặp dataset ở cả 3 kích thước. Các số dưới đây tính bằng numpy từ file `.f32`. "Gradient" là trung bình |hiệu hai pixel kề nhau| theo chiều ngang cộng theo chiều dọc, dùng để đo mức chi tiết tần số cao còn lại sau blur:

| Ảnh trái | Kích thước | Trung bình xám (trước = sau) | Độ lệch chuẩn trước → sau | Gradient trước → sau | Tỷ lệ gradient sau/trước |
|---|---|---:|---|---|---:|
| site1 | 1280×720 | 0.4936 | 0.1807 → 0.1610 | 0.10010 → 0.03575 | 0.357 |
| site1 | 1920×1080 | 0.4937 | 0.1837 → 0.1669 | 0.08525 → 0.03587 | 0.421 |
| site1 | 3840×2160 | 0.4937 | 0.1843 → 0.1761 | 0.04950 → 0.03185 | 0.643 |
| site2 | 1280×720 | 0.4499 | 0.2373 → 0.2307 | 0.04278 → 0.02270 | 0.531 |
| site2 | 1920×1080 | 0.4500 | 0.2382 → 0.2333 | 0.03533 → 0.01920 | 0.543 |
| site2 | 3840×2160 | 0.4501 | 0.2388 → 0.2364 | 0.02354 → 0.01431 | 0.608 |
| site3 | 1280×720 | 0.4405 | 0.2173 → 0.2147 | 0.02167 → 0.01391 | 0.642 |
| site3 | 1920×1080 | 0.4405 | 0.2174 → 0.2159 | 0.02039 → 0.01097 | 0.538 |
| site3 | 3840×2160 | 0.4405 | 0.2175 → 0.2169 | 0.01491 → 0.00832 | 0.558 |
| challenge | 1280×720 | 0.2391 | 0.2063 → 0.1726 | 0.13929 → 0.04867 | 0.349 |
| challenge | 1920×1080 | 0.2391 | 0.2147 → 0.1825 | 0.12755 → 0.04929 | 0.386 |
| challenge | 3840×2160 | 0.2390 | 0.2213 → 0.2000 | 0.08385 → 0.04686 | 0.559 |

Nhận xét:

- Độ sáng trung bình không đổi đến 4 chữ số thập phân, đúng với kernel có tổng bằng 1 và biên clamp.
- Blur giữ lại 35–64% gradient. Độ lệch chuẩn chỉ giảm ít (nhiều nhất ở cặp khó, 0.2063 → 0.1726), nghĩa là S1 bỏ chủ yếu nhiễu và chi tiết nhỏ, còn tương phản giữa các vùng lớn vẫn giữ.
- Cặp khó (cảnh đêm) mất gradient nhiều nhất ở cỡ small, phù hợp với nhiễu ảnh tối.
- Với cùng σ, ảnh lớn giữ lại nhiều gradient hơn (site1: 0.357 ở small, 0.643 ở large). Đây là hệ quả đã nêu ở mục 3: dùng một bộ tham số cho mọi kích thước thì ảnh 4K được làm mượt ít hơn so với nội dung.
- S2 nhận ảnh blur này và vẫn tìm đủ keypoint cho S4, S5: cả 12 lần chạy dataset đều ra panorama, số match và inlier ở mục 5 của `docs/stages/s4-matching.md`.

Lệnh tái lập từ gốc repo (`build/stb_impl.o` build riêng, không bật `-Werror` vì header stb sinh cảnh báo `missing-field-initializers`):

```bash
nvcc -arch=sm_75 -std=c++11 -O2 -I src -c src/stb_impl.cpp -o build/stb_impl.o
nvcc -arch=sm_75 -std=c++11 -O2 -Xcompiler=-Wall,-Wextra,-Werror -I src src/v0_preprocess.cpp     src/gaussian_kernel.cpp src/gaussian_blur.cpp src/image_layout.cpp build/stb_impl.o     tests/tool_export_gray.cpp -o build/tool_export_gray
./build/tool_export_gray dataset/site1/small_left.jpg results/s1/site1_small_left 1 3
```

## 6. Mức phù hợp với GPU và mapping V1 dự kiến

### 6.1 Căn cứ từ benchmark V0

Số đo do Thành chạy ngày 20/10 trong một phiên Colab Tesla T4 (CPU Intel Xeon @ 2.00GHz), một lần warm-up rồi `--runs 5`. Bảng lấy hàng `average` trong `results/p3-t04/benchmark/summary.csv` (nhánh `thanh/p3-results`). Thời gian S1 gồm cả hai ảnh A và B.

| Site | Kích thước | S1 (ms) | Tỷ trọng trong Total |
|---|---|---:|---:|
| site1 | small | 30.551 | 2.8% |
| site1 | medium | 69.432 | 4.2% |
| site1 | large | 305.414 | 6.8% |
| site2 | small | 30.111 | 2.7% |
| site2 | medium | 69.875 | 4.3% |
| site2 | large | 278.694 | 6.1% |
| site3 | small | 29.868 | 4.0% |
| site3 | medium | 67.999 | 5.2% |
| site3 | large | 280.722 | 8.0% |

Trung bình tỷ trọng trên ba site là 3.2% ở small, 4.6% ở medium và 7.0% ở large. S1 không phải hot stage ở cấu hình nào. Thời gian S1 gần như tỷ lệ với số pixel: medium có 2.25 lần số pixel của small và S1 chậm hơn khoảng 2.3 lần; large có 9 lần số pixel và S1 chậm hơn khoảng 9.3 đến 10 lần. Ba site cho thời gian gần bằng nhau ở cùng kích thước vì khối lượng việc của S1 không phụ thuộc nội dung ảnh. Tỷ trọng tăng theo độ phân giải vì S4 gần như không đổi theo kích thước (số descriptor bị chặn ở 2000), trong khi S1 tăng theo pixel.

### 6.2 Mapping V1 cơ bản

Cả ba lượt của S1 đều là phép tính độc lập trên từng pixel, nên mapping đơn giản là một thread cho một pixel output. V1 dùng ba kernel, theo đúng ba lượt ở mục 4:

| Kernel | Một thread làm gì | Đọc | Ghi |
|---|---|---|---|
| Grayscale | Pixel `(x, y)`: đọc 3 byte RGB, tính `(0.299R + 0.587G + 0.114B) / 255` | Ảnh RGB `uint8` trên Device | `output` `float` |
| Blur ngang | Pixel `(x, y)`: cộng `2r+1` tap theo thứ tự `k = -r..r`, chỉ số x clamp vào `[0, W-1]` | `output` | `temp` |
| Blur dọc | Pixel `(x, y)`: cộng `2r+1` tap theo thứ tự `k = -r..r`, chỉ số y clamp vào `[0, H-1]` | `temp` | `output` |

- Grid 2D, block ban đầu 32×8 thread để một warp đọc 32 pixel liên tiếp trên cùng hàng. 256 thread mỗi block nằm trong khoảng 128–256 mà CUDA C++ Best Practices Guide (mục 11.3) gợi ý để bắt đầu thử. Kích thước block là cấu hình để đo lại, không phải tham số của phương pháp.
- Trọng số kernel (tối đa 33 giá trị vì `r ≤ 16`) vẫn sinh trên Host bằng `make_gaussian_weights` như V0. Ở mỗi bước cộng, mọi thread trong warp đọc cùng một trọng số; theo mục 10.2.6 của cùng tài liệu, khi cả warp đọc cùng một địa chỉ thì constant memory nhanh gần bằng register. Bản V1 không dùng `cudaMemcpyToSymbol` mà truyền trọng số theo giá trị qua tham số kernel (struct `V1GaussianWeights`: 33 `float` và bán kính). Trên sm_75, tham số kernel nằm trong một constant bank nên vẫn có cơ chế broadcast này, và không có lệnh chép trọng số nào trong vùng đo.
- Thread nằm ngoài ảnh (khi W hoặc H không chia hết cho kích thước block) chỉ thoát, không ghi gì.
- Ảnh RGB được chép từ Host lên Device một lần cho mỗi ảnh. `output` ở lại trên Device để S2 dùng tiếp, không chép về Host giữa các stage.
- V1 dùng global memory cho cả ba lượt. Thứ tự cộng trong mỗi pixel giữ như V0, build với `--fmad=false` khi đối chiếu để chênh lệch chỉ đến từ làm tròn `float`.

S3 dùng lại blur của S1 (`gaussian_blur_in_place` với σ = 2, r = 4), nên hai kernel blur viết theo tham số `r` và trọng số truyền vào để S3 dùng chung.

Cài đặt V1 (P5-T03) gồm:

| File | Nội dung |
|---|---|
| `src/v1/s1/v1_grayscale.cuh` | Kernel grayscale, block 32×8, cùng biểu thức và thứ tự tính với `convert_to_gray` của V0 |
| `src/v1/common/v1_gaussian_blur.{h,cu}` | Hai kernel blur ngang và dọc, dùng chung với S3 |
| `src/v1/s1/v1_preprocess.{h,cu}` | `v1_preprocess(DeviceWorkspace&, const Config&, cudaStream_t)` và `v1_preprocess_scratch_bytes(W, H)` |

`v1_preprocess` xử lý A rồi B trên cùng stream, mỗi ảnh một kernel grayscale ghi thẳng vào `grayA` hoặc `grayB` rồi blur tại chỗ. Thứ tự kiểm tra đầu vào giống V0: ảnh trước (`InvalidImage`), config sau (`InvalidConfig`), cuối cùng là scratch (`InvalidArgument` khi `d_scratch` null, lệch 4 byte hoặc nhỏ hơn mức cần). Khi có lỗi thì không kernel nào được đưa vào stream, nên output giữ nguyên. S1 không có lỗi phát sinh trên Device, nên không đọc hay ghi `d_counts`.

### 6.3 Hướng tối ưu V2/V3 và rủi ro

S1 chỉ chiếm 3–8% thời gian V0 nên không thuộc nhóm stage ưu tiên tối ưu (S2, S4, S6). Các ý tưởng dưới đây chỉ làm khi profiling V1 cho thấy S1 hoặc phần truyền dữ liệu của S1 đáng kể:

1. **Shared memory tile có halo cho blur.** Mỗi block nạp một tile cùng `r` pixel halo mỗi phía vào shared memory, các thread đọc tap từ đó thay vì đọc lại global memory `2r+1` lần. Rủi ro: với `r = 3`, halo nhỏ nên lợi ích có thể thấp; phải đo trước khi giữ.
2. **Gộp grayscale với blur ngang.** Đề cuối kỳ gợi ý kernel fusion grayscale + blur. Một kernel đọc RGB, tính giá trị xám cho cả vùng halo rồi blur ngang luôn, bỏ một lượt ghi và đọc lại `output`. Thứ tự cộng vẫn phải giữ như V0.
3. **Xử lý hai ảnh song song và pinned memory.** A và B độc lập ở S1, có thể chạy trên hai CUDA stream; chép RGB từ pinned memory để chồng việc chép ảnh này với tính toán ảnh kia.

Rủi ro chính: S1 bị giới hạn bởi băng thông bộ nhớ. Ở large, mỗi ảnh RGB khoảng 24.9 MB phải chép lên Device, nên thời gian chép có thể lớn hơn thời gian kernel. Chi phí này cần đo riêng thay vì chỉ báo thời gian kernel. V0 cấp phát `temp` trong mỗi lần gọi. V1 thì không cấp phát gì trong S1: `temp` lấy từ `d_scratch`, do caller cấp trước vùng đo theo `v1_preprocess_scratch_bytes(W, H)` = W·H·4 byte (lấy giá trị lớn hơn giữa A và B). Hai ảnh chạy nối tiếp trên cùng stream nên dùng chung vùng này được.

### 6.4 Kiểm chứng V1

Chạy lại các test ở mục 7 với output của V1: ảnh hằng, ảnh một màu, điểm sáng, ảnh ngẫu nhiên nhiều kích thước và nhiều cặp (σ, r), ảnh nhỏ hơn bán kính, ảnh có kích thước không chia hết cho block. Sai lệch tuyệt đối lớn nhất so với V0 phải ≤ 1e-5 (mục 3). Sau đó so output S1 của V1 với V0 trên ảnh dataset ở cả ba kích thước, rồi chạy toàn pipeline và bộ cặp synthetic ở mục 5.5 của tài liệu S5.

Thời gian S1 trên GPU đo bằng CUDA events quanh ba kernel, có đồng bộ trước khi đọc kết quả; thời gian chép ảnh RGB lên Device ghi thành một cột riêng. Chưa có số đo speedup nào của S1, vì V1 chưa được nối vào pipeline (việc này thuộc P6).

Kết quả kiểm chứng của Thành ngày 03/11 trên Colab Tesla T4, CUDA 13.0 (V13.0.88), build với `--fmad=false`, commit `924e0d7` trên nhánh `thanh/p5`:

| Đầu vào | Kết quả |
|---|---|
| Suite `gpu_s1` (ảnh ngẫu nhiên, ảnh một màu, điểm sáng, chạy lặp, đầu vào sai) | `PASS GPU S1: 10706 checks`, 629536 pixel, cả 629536 pixel giống V0 từng bit, `max_abs_diff=0` |
| Dataset giữa kỳ: site1, site2, site3, challenge, mỗi bộ 3 kích thước | 12 cặp, tất cả `max_abs_diff=0` |
| 6 cặp synthetic (translation và projective, 3 kích thước) | Tất cả `max_abs_diff=0` |
| `compute-sanitizer --tool memcheck --leak-check full` trên suite kèm cặp site1 small | `0 errors`, `0 bytes leaked` |

Sai lệch đo được là 0 vì V1 giữ nguyên biểu thức và thứ tự cộng của V0, và cả hai phía đều tắt FMA (`--fmad=false` cho Device, `-ffp-contract=off` cho Host). Ngưỡng nghiệm thu vẫn là 1e-5 như mục 3.

## 7. Kiểm thử

Test nằm ở `tests/test_v0_preprocess.cpp`, mỗi test dùng dữ liệu tự tạo có đáp án tính độc lập (Gaussian 2D cài trực tiếp bằng `double`). Đã chạy trên Colab T4 ngày 13/10 (kết quả ở dưới).

Lệnh build và chạy ở máy cá nhân (g++):

```bash
g++ -std=c++11 -Wall -Wextra -Wpedantic -Werror -O2 -I src \
    src/v0_preprocess.cpp src/gaussian_kernel.cpp src/gaussian_blur.cpp src/image_layout.cpp \
    tests/test_v0_preprocess.cpp -o build/test_v0_preprocess
./build/test_v0_preprocess
```

Lệnh chạy trên Colab T4 từ gốc repo, in `nvidia-smi` trước:

```bash
nvcc -arch=sm_75 -I src src/v0_preprocess.cpp src/gaussian_kernel.cpp src/gaussian_blur.cpp \
    src/image_layout.cpp tests/test_v0_preprocess.cpp -o test_s1
./test_s1
```

Kết quả ngày 13/10:

| Môi trường | Lệnh | Kết quả |
|---|---|---|
| Máy cá nhân, g++ `-std=c++11 -Wall -Wextra -Wpedantic -Werror -O2` | Như trên | `PASS: 1758 assertions for S1 grayscale, blur, errors and OOM` |
| Colab Tesla T4, CUDA 13.0 (V13.0.88) | `nvcc -arch=sm_75 ...` | Build không lỗi; `PASS: 1758 assertions for S1 grayscale, blur, errors and OOM` |
| Colab Tesla T4 | `g++ -fsanitize=address,undefined -fno-sanitize-recover=all` | Build không lỗi; `PASS: 1758 assertions ...`, không có báo lỗi sanitizer |
| Colab Tesla T4, ngày 16/10, sau khi tách `gaussian_blur.cpp` và `image_layout.cpp` | `nvcc -arch=sm_75 ...` và g++ với sanitizer như trên | `PASS: 1758 assertions ...` ở cả hai, không có báo lỗi sanitizer |
| Colab Tesla T4, CUDA 13.0, ngày 18/10, bản trên `main` | `nvcc -arch=sm_75 -std=c++11 -O2 -Xcompiler=-Wall,-Wextra,-Werror ...` và g++ 13.3 với sanitizer | `PASS: 1758 assertions ...` ở cả hai, không có báo lỗi sanitizer |

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

Test V1 nằm ở `tests/gpu/test_gpu_s1_preprocess.cu` (suite `gpu_s1`) và `tests/gpu/test_gpu_gaussian_blur.cu` (suite `gpu_blur`). Hai suite này so output V1 với `v0_preprocess` và `gaussian_blur_in_place`, gồm các trường hợp ở bảng trên (trừ test cấp phát, vì V1 không cấp phát), thêm A và B khác kích thước, scratch null, thiếu hoặc lệch, và kiểm tra ảnh RGB không bị ghi. Lệnh chạy trên Colab T4 từ gốc repo:

```bash
python3 tests/run_tests.py --compiler nvcc --require-t4 --group gpu --suite gpu_blur
python3 tests/run_tests.py --compiler nvcc --require-t4 --group gpu --suite gpu_s1
./build/tests_gpu/gpu_s1 <left.jpg> <right.jpg>
compute-sanitizer --tool memcheck --leak-check full --error-exitcode 99 ./build/tests_gpu/gpu_s1
```

AddressSanitizer và UndefinedBehaviorSanitizer chạy trên Colab (MinGW trên máy cá nhân không hỗ trợ). Công cụ `tests/tool_export_gray.cpp` chạy trên Colab T4 ngày 18/10, kết quả ở mục 5.

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
- S1 là stage bị giới hạn bởi băng thông bộ nhớ. Số đo V0 ngày 20/10 ở mục 6.1: S1 chiếm 3–8% thời gian và tăng gần tỷ lệ với số pixel.

## 9. Nguồn tham khảo

| Nguồn | Ngày truy cập | Dùng cho phần nào |
|---|---|---|
| [Đề cuối kỳ CSC14120](../specs/CSC14120_2026_Final%20Project.md), mục 2.1 và 2.2 | 07/10 | Mục 1 |
| [Đề cuối kỳ CSC14120](../specs/CSC14120_2026_Final%20Project.md), phần tối ưu ở mức pipeline (kernel fusion grayscale + blur, pinned memory, CUDA stream) | 21/10 | Mục 6.3 |
| [ITU-R Recommendation BT.601-7 (03/2011)](https://www.itu.int/rec/R-REC-BT.601) | 21/10 | Hệ số đổi ảnh xám ở mục 1.1 |
| [NVIDIA CUDA C++ Best Practices Guide 13.0](https://docs.nvidia.com/cuda/archive/13.0.0/cuda-c-best-practices-guide/index.html), mục 9.1.2, 10.1.1, 10.1.2, 10.2.1, 10.2.3, 10.2.6, 11.3 | 21/10 | Mục 6: CUDA events, pinned memory, chồng truyền dữ liệu với tính toán, coalescing, shared memory, constant memory, kích thước block |

## 10. Lịch sử thay đổi tham số

| Ngày | Thay đổi | Lý do |
|---|---|---|
| 13/10 | Chốt σ = 1.0, r = 3 | Giá trị ban đầu theo mục 3. Ở P2 so số keypoint và inlier với σ bằng 0.8, 1.0, 1.5 trên cặp ảnh thật để xác nhận |
