# S2 - Keypoint detection

Người phụ trách: Thành (23120166). Cập nhật lần cuối: 21/10.

Task: P0-T08 (mục 1, 2), P1-T07 (mục 3, 4, 8), P1-T08 (code, mục 5, 7).

S2 tìm các điểm góc trên ảnh xám đã làm mượt của S1 để S3 mô tả và S4 ghép. S2 chạy độc lập trên từng ảnh của cặp.

## 1. Phương pháp đã chọn và các phương án đã cân nhắc

Phương pháp đã chọn: **FAST-9** (segment test trên vòng tròn 16 pixel, cần 9 pixel liên tiếp), score V của Rosten và Drummond, non-maximum suppression 3×3, giữ N keypoint mạnh nhất. Một tỉ lệ, không dùng image pyramid.

| Phương án | Chất lượng | Chi phí mỗi pixel | Mức phù hợp GPU |
|---|---|---|---|
| **FAST-9 + score V (chọn)** | Lặp lại tốt giữa hai ảnh cùng tỉ lệ; Rosten và cộng sự (2010) cho thấy n = 9 lặp lại tốt hơn các n khác. Không bất biến tỉ lệ | 16 phép trừ, so sánh; điểm góc thêm 16 phép cộng | Mỗi pixel một thread, chỉ đọc vùng 7×7, không phụ thuộc giữa pixel |
| FAST-12 | Ít góc hơn, kém lặp lại hơn FAST-9 | Như trên, có kiểm tra nhanh 4 điểm | Như trên |
| Harris | Response ổn định, xếp hạng góc tốt | Gradient, tích các gradient trên cửa sổ, định thức và vết | Stencil nhiều bước, cần thêm buffer |
| Shi-Tomasi | Tương tự Harris, chọn theo trị riêng nhỏ | Như Harris, thêm căn bậc hai | Như Harris |
| FAST + xếp hạng Harris (ORB) | Chọn góc tốt hơn khi lấy top-N | Cộng cả hai | Hai kernel, thêm buffer |
| FAST nhiều tỉ lệ | Bất biến tỉ lệ | Thêm các tầng pyramid | Đổi interface S1, S2, S3 |

Lý do chọn: ảnh trái và phải của một cặp chụp bằng cách đứng yên, xoay người, nên cùng độ phân giải và gần cùng tỉ lệ; bất biến tỉ lệ chưa cần. FAST rẻ nhất trong các phương án và map trực tiếp lên GPU. Score V có sẵn từ segment test nên không cần thêm stage Harris. Khi đã có số đo ở P2, nếu top-N theo V cho ít inlier, phương án đầu tiên cần xem lại là xếp hạng bằng Harris.

Không dùng cây quyết định học máy và không kiểm tra nhanh 4 điểm như bản gốc của FAST: kết quả không đổi, còn code V0 giữ dạng dễ đọc và giống bản GPU.

## 2. Đầu vào và đầu ra

Chữ ký hàm nằm ở `src/v0_detect.h`:

```cpp
ErrorCode v0_detect(const GrayImage& image, std::vector<Keypoint>& output,
                    const Config& config, bool debug_mode = false);
```

| Mục | Quy ước |
|---|---|
| Đầu vào | `GrayImage` của S1: `float` 1 kênh, miền [0, 1], stride tính bằng byte, `stride >= width * 4` và chia hết cho 4 |
| Cấu hình | `config.fast_threshold`, `config.max_keypoints` |
| Đầu ra | `std::vector<Keypoint>` của Host, do bên gọi sở hữu; bị xóa khi vào hàm và chỉ được điền khi `Success` |
| Tọa độ | Tâm pixel nguyên theo `docs/interface.md` mục 3: `x` là cột, `y` là hàng, không có phần lẻ |
| `score` | Score V của FAST, luôn > 0 |
| `angle` | 0; S3 không dùng orientation |
| Thứ tự | Score giảm dần, bằng nhau thì raster index `y * width + x` tăng dần |
| Số lượng | Tối đa `max_keypoints`, có thể ít hơn hoặc bằng 0 |
| Lỗi | `ErrorCode`, không gọi `exit()` |

Không đủ keypoint để ghép không phải lỗi của S2: S2 vẫn trả `Success`, S4 trả `InsufficientKeypoints` theo quy ước của Đế. Output dùng `std::vector` giống stub trong `main.cu` và output của S4.

## 3. Tham số

Các giá trị dùng chung cho V0 đến V3 và cho cả ba kích thước ảnh. Chưa hiệu chỉnh trên ảnh thật; việc đó nằm ở P2 (mục 10).

| Tham số | Giá trị | Đơn vị | Lý do chọn | Ảnh hưởng khi tăng/giảm |
|---|---|---|---|---|
| `fast_threshold` | 0.05 | intensity [0, 1] | Bằng 12.75/255. Trên thang 0-255, ORB của OpenCV mặc định dùng ngưỡng FAST 20 (0.078), `FastFeatureDetector` dùng 10 (0.039), đều trên ảnh chưa làm mượt. Ảnh của S1 đã blur σ = 1 nên tương phản ở góc giảm; 0.05 nằm giữa hai giá trị trên | Tăng: ít góc, chỉ còn góc tương phản mạnh, cặp ít texture dễ thiếu match. Giảm: nhiều góc yếu do nhiễu, S2 tốn thời gian sắp xếp hơn |
| `max_keypoints` | 2000 | keypoint mỗi ảnh | S4 vét cạn 2000 × 2000 = 4 triệu phép Hamming mỗi cặp; vùng chồng lấn 30-50% vẫn còn vài trăm keypoint | Tăng: nhiều match hơn, S4 tăng theo bình phương. Giảm: S5 có thể thiếu inlier |
| Số pixel liên tiếp | 9 | pixel | FAST-9, lặp lại tốt nhất theo Rosten và cộng sự (2010) | Tăng: ít góc, bỏ sót góc tù |
| Bán kính vòng tròn | 3 (16 pixel) | pixel | Vòng Bresenham của bản gốc | — |
| Border | 15 (`kFeatureBorder`) | pixel | Đủ cho vòng FAST (3) và patch BRIEF 31×31 của S3 (15), nên S3 không phải bỏ keypoint nào | Nhỏ hơn 15 làm S3 phải bỏ keypoint ở mép |
| NMS | 3×3, hòa thì raster nhỏ hơn thắng | — | Mỗi pixel quyết định độc lập, GPU làm được mà vẫn giống V0 | — |
| Giới hạn hợp lệ | `fast_threshold` hữu hạn, 0 < t < 1; 1 ≤ `max_keypoints` ≤ 1 000 000 | — | Sai trả `InvalidConfig` | — |

Một bộ tham số cho cả ba kích thước theo yêu cầu của đề. Ở 3840×2160, 2000 keypoint chỉ là phần nhỏ của các góc tìm được, nên keypoint tập trung ở các góc tương phản mạnh nhất.

## 4. Thuật toán chi tiết

Vòng tròn 16 điểm `(dx, dy)`, bắt đầu ở đỉnh, theo chiều kim đồng hồ trên ảnh (hình 1 của Rosten và Drummond, 2006):

```text
 0:( 0,-3)  1:( 1,-3)  2:( 2,-2)  3:( 3,-1)  4:( 3, 0)  5:( 3, 1)  6:( 2, 2)  7:( 1, 3)
 8:( 0, 3)  9:(-1, 3) 10:(-2, 2) 11:(-3, 1) 12:(-3, 0) 13:(-3,-1) 14:(-2,-2) 15:(-1,-3)
```

```text
v0_detect(image, output, config):
    output.clear()
    kiểm tra image                        -> InvalidImage
    kiểm tra config                       -> InvalidConfig
    nếu W <= 30 hoặc H <= 30: trả Success, output rỗng
    score = mảng W*H float, khởi tạo 0    -> AllocationFailed nếu thất bại

    # bước 1: segment test và score V
    với y = 15..H-16, x = 15..W-16:
        c = I(x, y)
        với i = 0..15: d_i = I(x + dx_i, y + dy_i) - c
            bright_i = d_i > t;  dark_i = d_i < -t
        nếu có 9 phần tử liên tiếp (vòng 15 -> 0) cùng bright hoặc cùng dark:
            score(x, y) = max( tổng_{bright} (d_i - t), tổng_{dark} (-d_i - t) )

    # bước 2: NMS 3x3
    với mỗi (x, y) có score > 0:
        bỏ nếu có hàng xóm q với score(q) > score(p)
        hoặc score(q) == score(p) và q đứng trước p theo raster

    # bước 3: top-N
    sắp xếp các điểm còn lại theo (score giảm, raster tăng)
    output = N điểm đầu: {x, y, score, angle = 0}
```

Điểm cần giữ khi cài đặt và khi viết bản GPU:

- Mọi phép so sánh dùng hiệu `d_i = I_x - I_p` tính bằng `float`, so sánh chặt với `t`. Hiệu đúng bằng `t` không phải sáng hay tối.
- Hai tổng của score V cộng theo thứ tự i = 0..15. Mỗi số hạng dương, nên mọi góc có score > 0, và score 0 trong bản đồ nghĩa là không phải góc.
- Bản đồ score có giá trị 0 ngoài vùng border, nên mọi hàng xóm của một ứng viên đều nằm trong ảnh.
- Quy tắc hòa của NMS bảo đảm một plateau score chỉ còn đúng một điểm và không có hai keypoint là hàng xóm 8 hướng của nhau.
- Khóa sắp xếp (score, raster) không trùng nhau nên thứ tự output là duy nhất; GPU sắp xếp theo cùng khóa sẽ ra cùng thứ tự.

Độ phức tạp: bước 1 là `O(W·H)` với hằng số 16; bước 3 là `O(M log M)` với M là số điểm sau NMS. Bộ nhớ thêm: `W·H·4` byte cho bản đồ score, cộng danh sách ứng viên.

Mã nguồn:

| File | Nội dung |
|---|---|
| `src/fast_corner.h`, `src/fast_corner.cpp` | Bảng 16 offset, segment test và score V của một pixel |
| `src/v0_detect.h`, `src/v0_detect.cpp` | Kiểm tra đầu vào, vòng lặp ảnh, NMS, top-N |
| `src/feature_border.h` | `kFeatureBorder = 15`, dùng chung với S3 |
| `src/image_layout.h`, `src/image_layout.cpp` | Kiểm tra layout ảnh xám và truy cập hàng theo stride byte, dùng chung với S1, S3 |

## 5. Bằng chứng chất lượng

Công cụ `tests/tool_export_keypoints.cpp` chạy S1 → S3 trên một cặp ảnh, sau đó chạy S4, S5 của Đế với cấu hình `configure_v0_features`, vẽ keypoint lên ảnh xám và in số keypoint, số match, số inlier. Ngày 16/10 công cụ chạy trên Colab T4 với ba cặp của Tuấn, chuẩn bị bằng `scripts/prepare_dataset.py`. Đây là lần chạy thử để có bằng chứng ban đầu; việc chọn cặp cho dataset thuộc P1-T05 và chưa làm.

Cấu hình đề xuất (t = 0.05, N = 2000):

| Cặp | Kích thước | Keypoint trái / phải | Match S4 | Inlier S5 | Trạng thái S5 |
|---|---|---|---:|---:|---|
| tuan-standard1 | 1280×720 | 2000 / 2000 | 196 | 8 | Success |
| tuan-standard1 | 1920×1080 | 2000 / 2000 | 163 | 9 | Success |
| tuan-standard1 | 3840×2160 | 2000 / 2000 | 134 | 0 | `DegenerateHomography` |
| tuan-standard2 | 1280×720 | 2000 / 2000 | 420 | 186 | Success |
| tuan-standard2 | 1920×1080 | 2000 / 2000 | 383 | 153 | Success |
| tuan-standard2 | 3840×2160 | 2000 / 2000 | 246 | 62 | Success |
| tuan-challenge1 | 1280×720 | 2000 / 1621 | 75 | 5 | Success |
| tuan-challenge1 | 1920×1080 | 2000 / 2000 | 88 | 6 | Success |
| tuan-challenge1 | 3840×2160 | 2000 / 2000 | 90 | 6 | Success |

Nhận xét:

- `tuan-standard2` cho nhiều inlier ở cả ba kích thước, nên S2, S3 tìm được correspondence đúng trên ảnh thật.
- `tuan-standard1` chỉ có 8-9 inlier, ở 3840×2160 S5 không tìm được mô hình. Trên ảnh vẽ keypoint, phần lớn keypoint nằm ở tán cây và bụi cây, ít nằm ở tòa nhà trong vùng chồng lấn. Cảnh còn có lan can và giàn che rất gần máy, dễ gây parallax (mục 3.3 của `docs/dataset.md`). Chồng lấn ước lượng của cặp này chỉ khoảng 28% (mục 5.3 của `docs/dataset.md`).
- `tuan-challenge1` (ít texture có chủ đích) có 5-6 inlier, đúng là một cặp khó.
- Số inlier giảm khi ảnh lớn hơn: N cố định 2000 nên ở 3840×2160 keypoint chỉ còn ở các góc tương phản mạnh nhất.

Thử thêm vài cấu hình chỉ để chẩn đoán, không đổi tham số đề xuất:

| Cặp | Kích thước | t = 0.03, N = 2000 | t = 0.08, N = 2000 | t = 0.05, N = 5000 |
|---|---|---:|---:|---:|
| tuan-standard1 | 1280×720 | 14 inlier | 12 inlier | 34 inlier |
| tuan-standard1 | 3840×2160 | 8 inlier | 7 inlier | 11 inlier |
| tuan-standard2 | 1280×720 | 173 inlier | 213 inlier | 357 inlier |
| tuan-standard2 | 3840×2160 | 58 inlier | 72 inlier | 201 inlier |

Đổi ngưỡng t không cứu được `tuan-standard1`; tăng N giúp nhiều hơn. Việc chọn lại N, chia lưới để keypoint phân bố đều, hay thay cặp ảnh cần Thành và cả Nhóm quyết định ở P2. Số inlier chưa đủ để kết luận về chất lượng panorama; P2 mới ghép đủ S1-S6 và xem ảnh kết quả.

Lệnh trên Colab, từ gốc repo, sau khi có `dataset/`:

```bash
nvcc -arch=sm_75 -std=c++11 -O2 -I src src/v0_preprocess.cpp src/gaussian_kernel.cpp \
    src/gaussian_blur.cpp src/image_layout.cpp src/v0_detect.cpp src/fast_corner.cpp \
    src/v0_describe.cpp src/brief_pattern.cpp src/feature_support.cpp src/v0_match.cpp \
    src/v0_homography.cpp src/stb_impl.cpp tests/tool_export_keypoints.cpp -o build/tool_export_keypoints
./build/tool_export_keypoints dataset/site1/small_left.jpg dataset/site1/small_right.jpg results/site1_small
```

## 6. Mức phù hợp với GPU và mapping V1 dự kiến

### 6.1 Căn cứ từ benchmark V0

Số đo do Thành chạy ngày 20/10 trong một phiên Colab Tesla T4 (CPU Intel Xeon @ 2.00GHz), một lần warm-up rồi `--runs 5`. Bảng lấy hàng `average` trong `results/p3-t04/benchmark/summary.csv` (nhánh `thanh/p3-results`); số keypoint lấy từ log `--debug` cùng lần chạy. Thời gian S2 gồm cả hai ảnh A và B.

| Site | Kích thước | S2 (ms) | Tỷ trọng trong Total | Keypoint A / B |
|---|---|---:|---:|---|
| site1 | small | 197.815 | 17.9% | 2000 / 2000 |
| site1 | medium | 516.806 | 30.9% | 2000 / 2000 |
| site1 | large | 1790.494 | 39.9% | 2000 / 2000 |
| site2 | small | 144.385 | 13.0% | 2000 / 2000 |
| site2 | medium | 316.481 | 19.6% | 2000 / 2000 |
| site2 | large | 1192.493 | 26.2% | 2000 / 2000 |
| site3 | small | 131.086 | 17.6% | 1461 / 1440 |
| site3 | medium | 274.675 | 20.9% | 1684 / 1780 |
| site3 | large | 1046.092 | 29.9% | 1458 / 1779 |

Trung bình tỷ trọng trên ba site là 16.1% ở small, 23.8% ở medium và 32.0% ở large. S2 là hot stage ở site1 large và đứng thứ hai ở site2, site3 large (sau S6). Thời gian S2 tăng theo số pixel (large gấp 8 đến 9 lần small) vì segment test và NMS chạy trên mọi pixel trong vùng border. Ở cùng kích thước, S2 của site1 chậm hơn hai site còn lại: ảnh site1 nhiều texture hơn nên có nhiều pixel qua segment test và nhiều ứng viên sau NMS phải sắp xếp. Vì S2 là một trong ba stage ưu tiên (S2, S4, S6), mục 6.3 có hướng tối ưu cụ thể.

### 6.2 Mapping V1 cơ bản

S2 gồm ba bước có mức song song khác nhau. Score và NMS là phép tính độc lập trên từng pixel; bước chọn top-N cần sắp xếp toàn cục.

| Kernel | Một thread làm gì | Output |
|---|---|---|
| Score | Pixel `(x, y)` trong `[15, W-16] × [15, H-16]`: đọc tâm và 16 điểm trên vòng tròn, làm segment test, tính score V cộng theo thứ tự `i = 0..15` như V0 | Bản đồ score `W·H` float, đặt 0 trước bằng `cudaMemset` |
| NMS | Pixel có score > 0: so với 8 hàng xóm, cùng quy tắc hòa theo raster như V0 | Nếu là cực đại, ghi `(score, raster)` vào danh sách ứng viên |
| Top-N | Sắp xếp ứng viên theo khóa (score giảm, raster tăng), lấy N phần tử đầu | Mảng `Keypoint` cho S3 |

- Score và NMS dùng grid 2D, block ban đầu 32×8 thread; ảnh xám của S1 đã nằm trên Device.
- Ghi ứng viên dùng một bộ đếm `atomicAdd` trên global memory. Thứ tự ghi phụ thuộc thứ tự thread chạy, nhưng khóa (score, raster) không trùng nhau nên sau khi sắp xếp thứ tự output là duy nhất và giống V0.
- Top-N ở V1 dùng sort tự viết trên Device, ví dụ bitonic sort trên khóa 64 bit: 32 bit cao là bit pattern của score (score dương nên thứ tự số nguyên giống thứ tự số thực, đảo bit để được thứ tự giảm), 32 bit thấp là raster. Dùng CUB hoặc Thrust là thêm thư viện, cần cả Nhóm quyết định trước.
- Score V chỉ có phép trừ và cộng nên FMA không làm đổi kết quả (mục 8). So sánh với ngưỡng vẫn dùng hiệu `float` và so sánh chặt như V0.

### 6.3 Hướng tối ưu V2/V3 và rủi ro

1. **Shared memory tile cho segment test.** Mỗi pixel đọc 17 giá trị trong cửa sổ 7×7, các thread kề nhau đọc chồng lên nhau rất nhiều. Mỗi block nạp tile cùng halo 3 pixel mỗi phía vào shared memory rồi đọc vòng tròn từ đó. Có thể tính luôn score cho thêm 1 pixel halo để làm NMS trong cùng kernel, bỏ một lượt ghi và đọc lại bản đồ score.
2. **Loại sớm bằng 4 điểm la bàn.** Một cung 9 điểm liên tiếp trên vòng 16 điểm luôn chứa ít nhất 2 trong 4 điểm 0, 4, 8, 12. Kiểm tra 4 điểm này trước giúp phần lớn pixel thoát sớm mà không đổi kết quả. Rủi ro: warp divergence khi trong cùng warp có pixel thoát sớm và pixel phải kiểm tra đủ 16 điểm; cần đo trước khi giữ.
3. **Chọn top-N thay vì sắp xếp toàn bộ.** Chỉ cần 2000 phần tử đầu. Dựng histogram score để tìm ngưỡng mà số ứng viên trên ngưỡng vừa đủ N, rồi chỉ sắp xếp các ứng viên đó. Phải giữ đúng quy tắc hòa ở biên ngưỡng.

Rủi ro chung: số ứng viên sau NMS phụ thuộc nội dung ảnh nên thời gian sort thay đổi giữa các site; bản đồ score ở large chiếm khoảng 33 MB mỗi ảnh; sort trên GPU phải cho đúng thứ tự của `std::sort` với khóa duy nhất. Chưa có kernel hay số đo GPU nào của S2.

### 6.4 Kiểm chứng V1

So danh sách keypoint của V1 với V0 từng phần tử: tọa độ, score (giống từng bit) và thứ tự. Dùng lại các test ở mục 7: bảng vòng tròn, cung bị ngắt, hiệu bằng ngưỡng, ảnh 3 mức xám nhiều score bằng nhau, ảnh nhỏ hơn border, N lớn hơn số ứng viên. Sau đó so trên ảnh dataset ở cả ba kích thước, chạy toàn pipeline và bộ cặp synthetic ở mục 5.5 tài liệu S5. Thời gian đo bằng CUDA events quanh cả ba bước, kể cả sort và chép keypoint, không chỉ kernel score.

## 7. Kiểm thử

Test nằm ở `tests/test_v0_detect.cpp`, dùng dữ liệu tự tạo. Phần so sánh với bản tham chiếu dùng một cài đặt vét cạn viết riêng trong test: thử mọi điểm bắt đầu của cung 9 điểm, NMS so sánh theo cặp (score, raster) và sắp xếp bằng `std::sort`.

| Test | Đầu vào | Kết quả mong đợi |
|---|---|---|
| Bảng vòng tròn | `kFastCircle` | Khớp hình 1 của bài báo, mọi điểm nằm trên vòng bán kính 3 |
| Độ dài cung | Mọi điểm bắt đầu 0..15, độ dài 1..16, cả sáng và tối | Dưới 9 không phải góc; từ 9 trở lên có score = 0.25 × độ dài |
| Cung bị ngắt | Hai cung 7 điểm cách nhau bởi điểm tương tự | Không phải góc |
| Hiệu bằng ngưỡng | `d = ±t` chính xác | Không phải góc |
| Score V tính tay | 9 sáng và 3 tối; 9 tối và 4 sáng | 2.25 và 3.375 |
| So với bản tham chiếu | Ảnh hình chữ nhật ngẫu nhiên và ảnh 3 mức xám (nhiều score bằng nhau), 5 kích thước, 4 ngưỡng, 3 giới hạn N | Giống từng phần tử: tọa độ, score, thứ tự |
| Hình vuông sáng trên nền tối | 120×120 | Mọi keypoint cách một góc không quá 2 px, mỗi góc có keypoint |
| Ảnh hằng | 64×64 | Không có keypoint |
| Ảnh nhỏ | 1×1, 2×2, 30×30, 30×200, 200×30 | `Success`, output rỗng |
| Ảnh 31×31 | Một chấm tối ở (15, 15) | Đúng một keypoint ở (15, 15) |
| Border, thứ tự, NMS | Ảnh dày góc | Keypoint trong [15, W-16] × [15, H-16], tọa độ nguyên, đúng thứ tự, không có hai keypoint kề nhau |
| Giới hạn N | N = 1..20 | Đúng N phần tử, là phần đầu của danh sách đầy đủ |
| Padding | Cùng ảnh, có và không có padding | Kết quả giống nhau, ảnh và padding không bị ghi |
| Chạy lại | Cùng đầu vào | Giống từng bit |
| Đầu vào sai | Null, 3 kênh, kích thước ≤ 0, stride theo phần tử, stride lẻ, lệch căn lề, tràn `stride * height` | `InvalidImage`, output rỗng |
| Config sai | t bằng 0, 1, âm, NaN, vô hạn; N bằng 0, âm, vượt giới hạn; `Config` mặc định | `InvalidConfig`, output rỗng |
| Ảnh và config cùng sai | | `InvalidImage` |
| Cấp phát thất bại | Giả lập `bad_alloc` | `AllocationFailed`, output rỗng |

Test tích hợp `tests/test_v0_detect_describe.cpp` chạy S1 → S5 trên một cặp ảnh tổng hợp, trong đó ảnh B là ảnh A dịch (37, -11) pixel. Kỳ vọng: S3 giữ đủ mọi keypoint của S2, ít nhất 90% match đúng phép dịch, H của S5 đưa 4 góc của B về A với sai số dưới 0.1 px.

Lệnh build và chạy ở máy cá nhân:

```bash
g++ -std=c++11 -Wall -Wextra -Wpedantic -Werror -O2 -I src \
    src/v0_detect.cpp src/fast_corner.cpp src/image_layout.cpp \
    tests/test_v0_detect.cpp -o build/test_v0_detect
./build/test_v0_detect
```

Lệnh chạy trên Colab T4 từ gốc repo:

```bash
nvidia-smi
nvcc -arch=sm_75 -std=c++11 -O2 -Xcompiler=-Wall,-Wextra,-Werror -I src \
    src/v0_detect.cpp src/fast_corner.cpp src/image_layout.cpp \
    tests/test_v0_detect.cpp -o build/test_v0_detect
./build/test_v0_detect
```

Kết quả:

| Ngày | Môi trường | Kết quả |
|---|---|---|
| 16/10 | Máy cá nhân, MinGW g++ 6.3.0 (32 bit), cờ như trên | `PASS: 19524 assertions for S2 FAST-9 detection` |
| 16/10 | Colab Tesla T4, CUDA 13.0 (V13.0.88), `nvcc` như trên | Build không lỗi; `PASS: 19524 assertions for S2 FAST-9 detection` |
| 16/10 | Colab, g++ 13.3 với `-fsanitize=address,undefined -fno-sanitize-recover=all` | `PASS: 19524 assertions ...`, không có báo lỗi sanitizer |
| 16/10 | Colab Tesla T4, `nvcc`, test tích hợp | `integration: keypoints A=1235 B=1265 matches=1113 exact=1090`; `PASS: 18 assertions for S1-S5 integration on a translated pair`; cũng đạt khi build với sanitizer |

Cùng phiên Colab, `nvcc -arch=sm_75 -O2 -I src src/*.cpp src/main.cu` build được chương trình đầy đủ cùng các stage khác.

## 8. Trường hợp biên và rủi ro

| Trường hợp | Phát hiện và xử lý | Kết quả |
|---|---|---|
| `data` null, `channels != 1`, kích thước ≤ 0 | Kiểm tra layout | `InvalidImage` |
| Stride nhỏ hơn một hàng (ví dụ tính theo phần tử), không chia hết cho 4, địa chỉ lệch 4 byte | Kiểm tra layout | `InvalidImage` |
| Tràn số khi tính `stride * height` hoặc `W·H·4` | Kiểm tra bằng phép chia trước khi nhân | `InvalidImage` |
| `fast_threshold` NaN, vô hạn, ≤ 0, ≥ 1 | Kiểm tra config | `InvalidConfig` |
| `max_keypoints` ≤ 0 hoặc > 1 000 000; `Config` chưa đặt | Kiểm tra config | `InvalidConfig` |
| Cả ảnh và config sai | Kiểm tra ảnh trước | `InvalidImage` |
| Cấp phát bản đồ score hoặc danh sách thất bại | Bắt `std::bad_alloc` | `AllocationFailed`, output rỗng |
| Ảnh có cạnh ≤ 30 px | Không có vùng ứng viên | `Success`, output rỗng |
| Ảnh phẳng, thiếu texture | Ít hoặc không có góc | `Success`; S4 báo `InsufficientKeypoints` nếu không đủ |
| Nhiều score bằng nhau | Quy tắc hòa theo raster | Kết quả tất định |
| Keypoint dồn vào vùng nhiều texture | Top-N toàn cục không phân bố đều trên ảnh | Rủi ro: vùng chồng lấn có thể ít keypoint. Xem lại ở P2 bằng số inlier; phương án là chia lưới |
| Ảnh lớn (3840×2160) | Bản đồ score 33 MB | Chấp nhận được trên Colab |
| Phép toán số thực trên GPU | `nvcc` mặc định gộp nhân-cộng (FMA) trong device code | Score V chỉ có phép trừ và cộng nên không bị ảnh hưởng; khi so V0 với V1 vẫn so cả tập keypoint và score |

## 9. Nguồn tham khảo

| Nguồn | Ngày truy cập | Dùng cho phần nào |
|---|---|---|
| [Rosten, E., Drummond, T. (2006). Machine learning for high-speed corner detection. ECCV](https://www.edwardrosten.com/work/rosten_2006_machine.pdf) | 16/10 | Segment test, vòng tròn 16 điểm, score V (mục 1, 4) |
| [Rosten, E., Porter, R., Drummond, T. (2010). Faster and better: a machine learning approach to corner detection. IEEE TPAMI](https://arxiv.org/abs/0810.2434) | 16/10 | So sánh độ lặp lại theo n (mục 1, 3) |
| [OpenCV 4.x, `features2d.hpp`](https://github.com/opencv/opencv/blob/4.x/modules/features2d/include/opencv2/features2d.hpp) | 16/10 | Đối chiếu ngưỡng FAST mặc định của `FastFeatureDetector` và `ORB` (mục 3); không dùng code |
| [Rublee, E. và cộng sự (2011). ORB: an efficient alternative to SIFT or SURF. ICCV](https://doi.org/10.1109/ICCV.2011.6126544) | 16/10 | Phương án xếp hạng FAST bằng Harris (mục 1) |
| [Đề cuối kỳ CSC14120](../specs/CSC14120_2026_Final%20Project.md), mục 2 | 16/10 | Yêu cầu stage |
| [NVIDIA CUDA C++ Best Practices Guide 13.0](https://docs.nvidia.com/cuda/archive/13.0.0/cuda-c-best-practices-guide/index.html), mục 9.1.2, 10.2.1, 10.2.3, 11.3 | 21/10 | Mục 6: CUDA events, coalescing, shared memory, kích thước block |

## 10. Lịch sử thay đổi tham số

| Ngày | Thay đổi | Lý do |
|---|---|---|
| 16/10 | Đề xuất FAST-9, t = 0.05, N = 2000, border 15, NMS 3×3 | Giá trị ban đầu. Ở P2 so số keypoint và inlier với t bằng 0.03, 0.05, 0.08 trên cặp ảnh thật |
