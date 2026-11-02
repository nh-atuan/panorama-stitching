<!-- Authors: Le Thuong De (23120232). External source: none. -->

# Interface chung của pipeline Panorama Stitching

Người soạn: Chương (23120195). Cập nhật: 30/10/2026, P5-T12: contract Device workspace và luồng V1 stub. Tuấn (23120185) bổ sung mục 10 và cập nhật mục 6–8 khi nối pipeline V0 ngày 18/10/2026.

Tài liệu mô tả contract trong [`src/common/common.h`](../src/common/common.h). Contract V0 đã được dùng cho 6 stage cùng pipeline; phần GPU được bổ sung ở mục 11. Tham số thuật toán do người phụ trách chốt ở mục 3 tài liệu từng stage. V1 hiện là luồng thử hạ tầng, chưa phải thuật toán ghép ảnh CUDA hoàn chỉnh.

Pipeline dự kiến: S1 preprocessing → S2 FAST → S3 BRIEF/ORB → S4 Hamming matching → S5 RANSAC homography → S6 warp/blend. S3 dùng BRIEF 256 bit không xoay, pattern sinh với seed 16 (chi tiết ở [tài liệu S3](stages/s3-description.md)); cấu trúc 256-bit không tự xác định thuật toán ORB đầy đủ.

## 1. Kiểu dữ liệu và ranh giới Host–Device

Các kiểu nằm trong namespace `panorama`. `Image`, `GrayImage`, `Keypoint`, `Descriptor`, `Match`, `Homography`, `Panorama`, `Config`, `TimingStats` có standard layout và trivially copyable, được kiểm tra bằng `static_assert`. Không có virtual method, destructor cấp phát/giải phóng hoặc STL container bên trong các kiểu này.

`CliOptions` giữ nguyên để parser hiện tại build được. Nó chứa `std::string`, chỉ dùng trên Host; không đưa đối tượng này vào `cudaMemcpy`. Header có include STL không có nghĩa các struct truyền sang GPU chứa STL.

Ảnh và danh sách dữ liệu là **view không sở hữu bộ nhớ**. Bên gọi cấp phát và giải phóng. Copy struct chứa con trỏ chỉ copy địa chỉ, không copy buffer hay chuyển Host pointer thành Device pointer.

Danh sách keypoint/descriptor/match truyền bằng con trỏ mảng cùng `count` và `capacity`; không lưu `std::vector` trong payload GPU. Bên gọi kiểm tra `0 <= count <= capacity` và cấp phát đủ phần tử. Device nhận buffer đã cấp phát trên Device; metadata trên Host không được dereference Device pointer.

## 2. Image và bố cục bộ nhớ

`ImageView<T>` chứa `T* data`, `size_t stride`, `int32_t width`, `height`, `channels`.

| Kiểu | Phần tử / số kênh | Miền giá trị và mục đích |
|---|---|---|
| `Image` = `ImageView<uint8_t>` | 3 kênh RGB hoặc 1 kênh xám byte | [0,255]; RGB đầu vào và panorama S6; ảnh xám byte chỉ dùng khi stage công bố cần |
| `GrayImage` = `ImageView<float>` | 1 kênh | [0,1]; kết quả grayscale/blur S1 và input S2/S3 |

Row-major: mỗi hàng liên tiếp trong vùng dữ liệu của hàng đó, hàng kế tiếp bắt đầu sau `stride` byte. Ảnh RGB xen kẽ theo thứ tự `R G B R G B ...`, không phải BGR hoặc planar.

Địa chỉ kênh c của pixel (x,y):

```text
row_bytes = reinterpret_cast<unsigned char*>(data) + size_t(y) * stride
pixel = reinterpret_cast<T*>(row_bytes) + size_t(x) * channels + c
```

`stride` **luôn tính bằng byte**, kể cả ảnh `float`; không tính bằng số pixel hay phần tử. Packed RGB: `stride = width * 3`. Packed `GrayImage`: `stride = width * sizeof(float)`, ví dụ ảnh xám rộng 1280 có `stride = 5120`, không phải 1280.

Điều kiện ảnh hợp lệ:

- `data != nullptr`, width/height dương, channels phù hợp với stage: RGB 3, grayscale 1.
- `stride >= size_t(width) * channels * sizeof(T)`; mọi phép nhân kích thước phải kiểm tra tràn trước.
- Pointer và đầu mỗi hàng được căn theo `alignof(T)`; stride chia hết cho `sizeof(T)`.
- Buffer do bên gọi cấp phát đủ `stride * height` byte; không đọc hoặc ghi vào padding như pixel.

Không dùng `#pragma pack` để ép nhỏ struct pointer/stride: alignment tự nhiên phù hợp hơn cho truy cập. Kích thước ImageView phụ thuộc ABI; không lưu raw struct này như định dạng file hoặc chuyển giữa kiến trúc khác nhau.

Khi dùng CUDA pitched allocation, nhận pitch thực tế vào `stride` của Device view. Với `cudaMemcpy2D`, width là số **byte dữ liệu pixel mỗi hàng**, height là số hàng; Host và Device có thể có stride khác nhau. Sau khi copy pixels, tạo Device view với Device pointer và Device pitch. Không `cudaMemcpy` nguyên Host view rồi sử dụng Host pointer trong kernel. Căn cứ API: [NVIDIA CUDA Runtime, Memory Management](https://docs.nvidia.com/cuda/cuda-runtime-api/group__CUDART__MEMORY.html).

Ảnh màu A/B gốc phải còn tồn tại đến S6; ảnh xám đã blur không thay thế nguồn màu. Input không bị stage ghi đè nếu bên gọi chưa cho phép riêng.

## 3. Keypoint và descriptor

Hệ tọa độ chung: gốc (0,0) ở góc trái trên; X sang phải, Y xuống dưới. **Tâm pixel ở số nguyên**: pixel góc trên trái có tâm (0,0), pixel cuối ở (width-1,height-1). Biên vật lý ở -0.5 và width-0.5 / height-0.5. Tọa độ sub-pixel của Keypoint là float trong cùng hệ này; không tự cộng 0.5 khi chuyển S2 → S5.

`Keypoint` gồm `float x`, `y`, `score`, `angle`, tổng 16 byte. `score` là response do S2 định nghĩa, lớn hơn được coi là mạnh hơn; công thức/tie-break và max-keypoint selection phải được ghi trong S2.

`angle` tính bằng radian, chiều dương từ +X về +Y nên nhìn trên ảnh là chiều kim đồng hồ; miền biểu diễn [-pi,pi). Đây là phần bổ sung để rotated BRIEF có chỗ lưu orientation. BRIEF không xoay dùng 0 và bỏ qua trường này; S3 phụ trách tính orientation nếu cần. Không thêm scale/octave trong lần thiết kế này vì chưa chốt multi-scale ORB.

`Descriptor` có `alignas(16)` và `uint32_t data[8]`, đúng 32 byte. Không có padding trong payload 256-bit. Mỗi phần tử descriptor phải nằm ở địa chỉ căn 16 byte, kể cả khi nằm trong buffer gộp.

Quy ước bit: test số k (0..255) nằm ở `data[k / 32]`, bit `k % 32`, từ bit thấp lên cao. Đặt bit 1 khi intensity của điểm thứ nhất **nhỏ hơn** điểm thứ hai; bằng nhau đặt 0. Sampling pattern, smoothing, rotation và xử lý keypoint gần biên do S3 chốt, giữ cùng mọi phiên bản. Quy ước bit này là contract thiết kế, không tuyên bố toàn bộ descriptor tương thích OpenCV ORB.

`descriptors[i]` luôn tương ứng `keypoints[i]`. Nếu S3 loại keypoint gần biên, phải compact cả hai mảng đồng bộ trước S4; không chỉ xóa descriptor làm lệch index. S3 không tự thay đổi thứ tự một mảng riêng lẻ.

Hamming distance:

```text
distance = sum(popcount(A.data[word] XOR B.data[word]), word=0..7)
```

GPU có thể dùng `__popc` trên từng word; V0 dùng phép đếm bit tuần tự theo quy định, không dùng SIMD viết tay. Descriptor là 256-bit BRIEF/rotated BRIEF với từng test nhị phân; biến thể ORB đa điểm WTA_K=3/4 và Hamming2 không thuộc contract này.

## 4. Match và quy tắc correspondence

`Match` gồm `int32_t indexA`, `indexB`, `uint32_t distance`, tổng 12 byte. A là ảnh trái, B là ảnh phải.

- Match hợp lệ: `0 <= indexA < countA`, `0 <= indexB < countB`, distance thuộc [0,256]. Default index -1 chưa hợp lệ.
- Index tham chiếu mảng keypoint/descriptor đã compact của mỗi ảnh, không phải chỉ số pixel.
- Cặp điểm cho S5 là `pB = keypointsB[indexB]` và `pA = keypointsA[indexA]`, dùng để ước lượng B → A.
- Ratio test cần best và second-best; không nhận match chỉ vì chỉ có một ứng viên. Đề xuất contract dùng bất đẳng thức chặt `best < ratio * second_best`; second_best=0 không qua. Tie-break khoảng cách bằng nhau chọn indexB nhỏ hơn để tái lập; chi tiết thuật toán S4 cần ghi nhận quy ước này.
- Cross-check, nếu bật, đòi hỏi nearest-neighbor tương hỗ. `match_cross_check` chỉ được 0 hoặc 1. Không nhầm cross-check với ratio test.

## 5. Homography và panorama

`Homography` chứa `float data[9]`, row-major:

```text
data = [h00, h01, h02, h10, h11, h12, h20, h21, h22]
```

Dùng vector cột và chiều **B → A**:

```text
u = h00*xB + h01*yB + h02
v = h10*xB + h11*yB + h12
w = h20*xB + h21*yB + h22
xA = u/w
yA = v/w
```

Ma trận khởi tạo mặc định toàn 0, không phải H=I; chỉ dùng sau khi S5 thành công. H hữu hạn, khác ma trận 0 và đủ ổn định để nghịch đảo. Homography xác định đến hệ số scale: quy ước bàn giao là chia tất cả hệ số cho `max(abs(data[i]))` để trị tuyệt đối lớn nhất bằng 1. Không buộc chia h22 vì nó có thể bằng 0. Hai ma trận khác dấu tổng thể vẫn biểu diễn cùng phép chiếu.

Storage dùng **float32 theo yêu cầu P0-T14**. S5/S6 có thể dùng double cho giải hệ, inversion hoặc kiểm tra số học nội bộ; vẫn trả/nhận float[9] và kiểm chứng ảnh hưởng khi chuyển kiểu. Không mặc định float đủ ổn định cho mọi H. `homography_epsilon` là tolerance tương đối dương sau chuẩn hóa: ngưỡng projective denominator so với tổng độ lớn các hạng tạo denominator; inversion dùng scaled-pivot kiểm tra tương đối, không chỉ `abs(det) < epsilon`. Các chi tiết solver được Đế/Chương xác nhận ở P1.

`Panorama` chứa `Image image` RGB 3 kênh cùng `int32_t offset_x`, `offset_y`. Đây là translation đưa hệ A vào hệ canvas. Theo yêu cầu coding S6 ngày 13/10, `v0_warp_blend` nhận output rỗng, kiểm tra canvas rồi cấp phát bằng `new uint8_t[]`; chỉ chuyển pointer cho caller khi thành công. Caller sở hữu output, phải `delete[] output.image.data` và reset Panorama sau khi dùng. Thất bại giữ output rỗng, tự dọn buffer tạm; output đã có pointer bị từ chối, không tự free bộ nhớ không rõ ownership. Quy ước này thay thế đề xuất P0 caller cấp phát trước; chữ ký stage nằm trong `src/v0_warp_blend.h`.

Theo miền tâm pixel đã chọn, S6 hợp bốn góc A với bốn góc B biến đổi qua H. Nếu denominator đổi dấu/đi qua 0 trong miền B, từ chối phép chiếu trước khi lấy bbox. Sau khi có xmin/xmax/ymin/ymax hữu hạn:

```text
x0=floor(xmin), x1=ceil(xmax)
y0=floor(ymin), y1=ceil(ymax)
canvas_width=x1-x0+1, canvas_height=y1-y0+1
offset_x=-x0, offset_y=-y0
```

Kiểm tra tràn int32, tổng pixel, byte allocation và `max_canvas_pixels` trước cấp phát. Quy tắc số thực sát số nguyên và tolerance màu giữa version còn cần chốt ở P1; không điều chỉnh tùy từng phiên bản.

Với T đưa A → canvas, inverse sampling dùng `pA=T^-1*pCanvas`, `pB=H^-1*T^-1*pCanvas`. Validity là trạng thái riêng, không dùng RGB=0 để nhận diện ngoài ảnh. Không yêu cầu giữ panorama 16:9 hoặc crop/resize âm thầm.

## 6. Config và tham số chưa hiệu chỉnh

`Config` chỉ chứa số nguyên/float; không string, vector hoặc pointer. Giá trị 0 của các tham số thuật toán là **chưa cấu hình**, không phải giá trị khuyến nghị benchmark. Pipeline thật phải validate trước khi chạy. Giá trị dùng cho mọi version được điền bởi `make_v0_config()` trong `src/v0_config.h`, lấy từ mục 3 của tài liệu từng stage; `main.cu` gọi hàm này theo kích thước ảnh A. Seed chỉ in khi bật debug để stdout giữ định dạng CSV; notebook benchmark chính thức phải in đầy đủ cấu hình và hardware riêng.

| Trường | Đơn vị / điều kiện | Người chốt |
|---|---|---|
| `max_keypoints` | Số tối đa mỗi ảnh, >0, đủ cho downstream | Thành |
| `gaussian_sigma` | Pixel, >0 | Tuấn |
| `gaussian_radius` | Pixel, 1 <= r <= 16 và r >= ceil(2 * sigma); chi tiết ở mục 3 của [tài liệu S1](stages/s1-preprocessing.md) | Tuấn |
| `fast_threshold` | Intensity ảnh gray [0,1], >0 và <1 | Thành |
| `match_ratio_threshold` | Ratio, 0<r<1 | Đế |
| `match_cross_check` | 0/1. Giá trị mặc định của struct trong `common.h` là 1, nhưng S4 đã chốt 0 (không cross-check) và `make_v0_config()` đặt 0 | Đế |
| `ransac_iters` | Số hypothesis, >0 | Đế |
| `ransac_threshold` | Pixel trong hệ A, >0; nếu so squared error dùng threshold² | Đế |
| `seed` | uint32, default 16 để tái lập; cùng mọi version | Đế và cả Nhóm |
| `homography_epsilon` | Tolerance số học tương đối, >0, hữu hạn | Đế và Chương |
| `max_canvas_pixels` | Giới hạn pixel output, uint64, >0 | Chương |

Mọi float trong Config phải hữu hạn. Max-keypoint count phải phù hợp với int32 indexes và capacity thực tế. Các fields này chưa thay thế toàn bộ thiết kế từng stage: FAST contiguous count, BRIEF pattern, NMS/tie-break và quality tolerance sẽ được ghi/chốt khi có tài liệu stage. Nếu cần thêm field để tránh magic constant, cập nhật interface chung có ghi nhận của Nhóm.

Seed giống nhau chưa bảo đảm CPU/GPU dùng cùng chuỗi ngẫu nhiên: S5 phải định nghĩa RNG và mapping hypothesis theo index, hoặc dùng cùng danh sách mẫu. Mục tiêu là kết quả tái lập trong mỗi version và consistent với V0.

## 7. TimingStats và CSV

Tất cả thời gian là `double` tính bằng **millisecond**. `stage_ms[0..5]` theo enum Stage: Preprocess, Detect, Describe, Match, Homography, WarpBlend. S1–S3 mỗi mục bao gồm việc xử lý **cả A và B**, không phải một ảnh.

| Trường | Ý nghĩa |
|---|---|
| `stage_ms[6]` | V0: CPU elapsed từng stage; GPU: event elapsed của công việc từng stage |
| `total_kernel_ms` | Tổng thời gian kernel được đo, không gồm transfer; V0 để 0 |
| `h2d_ms` | CUDA event elapsed của lượt copy hai ảnh H2D; V0 để 0 |
| `d2h_ms` | CUDA event elapsed của lượt copy panorama D2H; V0 để 0 |
| `end_to_end_ms` | Wall-clock toàn pipeline sau khi input được đọc và trước ghi output; GPU phải đồng bộ trước kết thúc |

Default bằng 0 chỉ là trạng thái khởi tạo. Không dùng 0 để tuyên bố một phép đo chưa chạy đã hoàn tất. Một TimingStats đại diện một lần chạy; average/min được tổng hợp riêng sau warm-up và ít nhất 5 lần có đo. Config và seed phải được in cùng báo cáo.

End-to-end đo riêng, không ép bằng tổng stage_ms. **H2D và D2H bắt buộc nằm trong end-to-end**, bao gồm thời gian đợi copy hoàn tất. Chỉ đọc/ghi file ảnh trên ổ đĩa nằm ngoài khoảng thực thi này; log/debug, xuất CSV và tổng hợp thống kê cũng thực hiện sau phép đo. Nếu xử lý đồng thời A/B, stage elapsed phải bao phủ cả hai nhánh theo quan hệ phụ thuộc stream; không cộng elapsed chồng lấp rồi gọi đó là elapsed thực tế. Tổng kernel busy time có thể khác stage elapsed và end-to-end; khi có overlap phải ghi rõ cách lấy `total_kernel_ms`.

Định dạng CSV **V0 giữ nguyên** theo P1-T18, một dòng mỗi lần có đo. `Run_Index` đánh số từ 1, warm-up không có dòng dữ liệu:

```csv
Run_Index,S1_ms,S2_ms,S3_ms,S4_ms,S5_ms,S6_ms,Total_ms
```

Sau N dòng dữ liệu, stdout có hai dòng `Average,<7 giá trị>` và `Minimum,<7 giá trị>` cùng schema 8 cột. Average là trung bình của N lần có đo; Minimum tính độc lập cho mỗi cột, không nhất thiết cùng một lần chạy. `Total_ms` là `end_to_end_ms`, được đo riêng. Thời gian dùng dấu chấm thập phân, 9 chữ số sau dấu chấm; loader CSV cần lọc Run_Index dạng số để tách dữ liệu chạy khỏi summary. Định dạng 17 cột dự thảo P0 đã được thay bằng 8 cột theo yêu cầu mới; các trường GPU trong TimingStats vẫn bằng 0 ở V0.

Warm-up chạy đúng một lần và không gọi clock. Trong các lần đo, mọi stage nhận debug=false; log debug chỉ phát trong warm-up hoặc trước/sau vùng đo và đi ra stderr. Đọc hai ảnh bằng stb diễn ra trước warm-up; ghi ảnh sau tất cả lần đo. Xuất CSV và cập nhật summary cũng nằm ngoài vùng đo.

Từ 18/10, `main.cu` gọi 6 stage V0 thật qua `v0_run()` (mục 10), nên CSV là thời gian thuật toán V0. S1–S3 gọi mỗi stage hai lần cho A/B; S4–S6 gọi một lần. Output là panorama của S6. Output hỗ trợ `.png`, `.jpg`, `.jpeg` (không phân biệt chữ hoa); JPEG quality=95 chỉ là cấu hình writer, không phải tham số pipeline.

Các buffer input được quản lý bằng RAII với `stbi_image_free`. Panorama của S6 thuộc `V0Workspace` và được giải phóng theo mục 10. Khi làm benchmark chính thức, notebook in GPU/CPU, cấu hình và kích thước input/canvas riêng, ngoài CSV và ngoài vùng đo.

## 8. ErrorCode và xử lý lỗi

ErrorCode là enum uint32 cho trạng thái nội bộ; không dùng số enum trực tiếp làm process exit code. Stage trả trạng thái cho bên gọi; GPU có thể ghi một status code vào buffer và Host nhận sau synchronization. Không gọi `exit` trong kernel hoặc truyền `std::string` qua Device.

| Số | Enum | Điều kiện |
|---|---|---|
| 0 | `Success` | Thao tác hoàn tất |
| 1 | `InvalidArgument` | Thiếu argument, sai số/overflow, runs<=0, cờ lặp hoặc positional sai |
| 2 | `UnknownOption` | Cờ CLI không hỗ trợ |
| 3 | `UnsupportedVersion` | Số version hợp lệ nhưng chưa có implementation trong dispatcher thật |
| 4 | `InputNotFound` | Không tìm thấy file đầu vào |
| 5 | `ImageReadFailed` | Không mở/đọc/giải mã được ảnh, đường dẫn thư mục hoặc không có quyền |
| 6 | `ImageWriteFailed` | Ghi output thất bại |
| 7 | `InvalidImage` | Null buffer, kích thước/channel/stride sai hoặc kích thước tràn |
| 8 | `InvalidConfig` | Tham số chưa cấu hình, không hữu hạn hoặc ngoài miền hợp lệ |
| 9 | `InsufficientKeypoints` | Không đủ keypoint/descriptor hợp lệ cho matching |
| 10 | `InsufficientMatches` | Ít hơn 4 correspondences để bắt đầu 4-point homography hoặc không đủ inliers theo tiêu chí đã chốt |
| 11 | `DegenerateHomography` | Mẫu điểm suy biến, hệ không giải được, H không khả nghịch/không ổn định hoặc không tìm được mô hình hợp lệ |
| 12 | `NumericalFailure` | NaN/Inf, projective denominator gần 0 hoặc horizon qua miền ảnh |
| 13 | `InvalidCanvas` | Bounds/kích thước/offset output không hợp lệ, tràn số hoặc vượt giới hạn canvas |
| 14 | `AllocationFailed` | Không đủ bộ nhớ cho buffer |
| 15 | `CudaFailure` | CUDA runtime hoặc kernel execution thất bại |

Thông báo CLI định dạng `Error: <message>` gửi stderr; có usage khi lỗi tham số. Khi tích hợp trạng thái stage, dùng `Error: [<Enum>] <message>` để truy nguyên. Process thành công trả EXIT_SUCCESS; lỗi fatal trả EXIT_FAILURE sau khi giải phóng tài nguyên. Muốn phân biệt file không tồn tại với không có quyền phải kiểm tra thực tế, không gán mọi lỗi open cho InputNotFound.

`main.cu` decode ảnh về RGB, kiểm tra CLI và chấp nhận các version mà `is_supported_version()` trong `versions.h` cho phép: bản build Host có V0; bản build nvcc có V0 và V1 stub kèm cảnh báo rõ ràng. Lỗi parse/I/O và lỗi stage dùng ErrorCode trong exception nội bộ; main bắt sau khi RAII giải phóng buffer, in stderr và gọi `exit(EXIT_FAILURE)`. Lỗi stage có dạng `Error: [<Enum>] <tên stage> failed.`, ví dụ `Error: [InsufficientKeypoints] S4 match failed.` Không âm thầm trả identity H hoặc panorama đen như kết quả thành công khi S5/S6 thật lỗi.

## 9. Trạng thái bàn giao

Các kiểu và quy ước đã dùng trong code: ảnh/pitch byte, gray float, pixel center nguyên, descriptor bit order, index pairing, H float B→A, panorama offset, config, timing và lỗi. Chữ ký từng stage nằm trong header `src/v0_<stage>.h`; API pipeline ở mục 10. Phương pháp và tham số S1–S6 đã chốt ở mục 1, 3 của tài liệu từng stage.

Ngày 18/10/2026 `main` build bằng `nvcc -arch=sm_75` và toàn bộ test đạt trên Colab T4. Còn để lại cho các phiên bản CUDA: cách đo khi dùng nhiều stream và tolerance so sánh CPU–GPU.

## 10. Pipeline V0

`src/v0_pipeline.h` nối 6 stage cho V0. Các phiên bản CUDA sẽ có pipeline riêng nhưng giữ cùng cách đo và cùng Config.

```cpp
ErrorCode v0_prepare(const Image& left, const Image& right, const Config& config,
                     V0Workspace& workspace);
ErrorCode v0_run(const Image& left, const Image& right, const Config& config,
                 V0Workspace& workspace, TimingStats* timing, Stage* failed_stage,
                 HomographyReport* report = nullptr);
void v0_release_output(V0Workspace& workspace);
```

| Hàm | Vai trò | Có nằm trong vùng đo |
|---|---|---|
| `v0_prepare` | Cấp phát hai ảnh xám (hàng liền khít, stride `width * 4` byte) cho S1 và đặt trước dung lượng `max_keypoints` cho các vector keypoint, descriptor, match | Không |
| `v0_run` | Chạy S1 → S6 một lần. Khi `timing` khác null, đo từng stage và end-to-end của 6 stage bằng `std::chrono::high_resolution_clock`; khi null thì không gọi clock | Có (6 stage) |
| `v0_release_output` | `delete[]` panorama cũ và reset `Panorama` | Không |

Quy tắc:

- `V0Workspace` giữ buffer của mọi stage và được dùng lại cho warm-up và các lần đo. Destructor giải phóng panorama, workspace không copy được.
- `v0_run` giải phóng panorama cũ trước khi bắt đầu đo. `main.cu` vẫn gọi `v0_release_output` trước mỗi lần đo để việc giải phóng nằm rõ ngoài vùng đo.
- Khi một stage lỗi, `v0_run` dừng, trả mã lỗi của stage đó và ghi stage vào `*failed_stage`; panorama để trống.
- S4 và S5 nhận `FeatureView` tạo từ vector của workspace, capacity là dung lượng thật của vector.
- Báo cáo S5 (`HomographyReport`, kèm inlier mask) chỉ lấy ở lần warm-up không đo. V0 tất định nên các lần đo cho cùng match, H và panorama.
- Với `--debug`, sau khi in CSV, `main.cu` in ra stderr: kích thước ảnh, Config, số keypoint sau S2 và sau S3, số match, báo cáo S5, H và canvas. Dòng `[debug] H(B->A)=h0 ... h8` có định dạng cố định để script so sánh H với ground truth đọc được.

## 11. Cơ chế quản lý bộ nhớ GPU (V1)

### 11.1. Phạm vi hiện tại và quyền sở hữu

P5-T12 cung cấp **luồng thử hạ tầng V1 với sáu hàm stub**, không thực hiện FAST, BRIEF, matching, RANSAC hay warping thật. S1–S5 trả về ngay; S6 chỉ copy ảnh A từ Device sang canvas Device để kiểm tra đường D2H và ghi ảnh. Khi chọn `--version 1`, chương trình luôn cảnh báo trên stderr rằng output là bản sao A và số đo không phải benchmark ghép ảnh. Không đưa kết quả stub vào bảng speedup hay dùng nó để nghiệm thu sáu stage GPU.

`main.cu` sở hữu bộ nhớ thông qua `OwnedDeviceWorkspace`. `DeviceWorkspace` trong `common/common.h` chỉ giữ **con trỏ mượn**, metadata và capacity. Các kernel/stage không được giải phóng input hoặc giữ con trỏ sau khi workspace bị hủy. Ngoại lệ được chốt ở P5-T13: Host entry point S6 được quản lý allocation output `d_canvas` thay mặt owner theo kích thước H tính được; owner vẫn chịu trách nhiệm giải phóng cuối cùng. Các alias `imageA.data`, `imageB.data`, `grayA.data`, `grayB.data`, `canvas.image.data` cùng trỏ tới allocation gốc; chỉ giải phóng allocation gốc một lần.

| Buffer | Kiểu dữ liệu / dung lượng | Bên ghi và bên đọc khi có stage thật |
|---|---|---|
| `d_imageA`, `d_imageB` | RGB interleaved `uint8_t`; dimensions/stride trong `imageA`, `imageB` | Host copy H2D; S1/S3/S6 đọc |
| `d_grayA`, `d_grayB` | `float`, một kênh; view `grayA`, `grayB`, stride tính bằng byte | S1 ghi; S2/S3 đọc |
| `d_keypointsA`, `d_keypointsB` | Mảng `Keypoint`; `keypoint_capacityA/B` | S2 ghi; S3 lọc/cập nhật; S5 đọc |
| `d_descriptorsA`, `d_descriptorsB` | Mảng `Descriptor`; `descriptor_capacityA/B` | S3 ghi; S4 đọc |
| `d_matches` | Mảng `Match`; `match_capacity` | S4 ghi; S5 đọc |
| `d_homography` | Một `Homography`, row-major `float[9]`, B → A | S5 ghi; S6 đọc |
| `d_counts` | Một `DeviceCounts` | S2/S3/S4 cập nhật số phần tử hợp lệ và trạng thái; stage sau đọc |
| `d_canvas_info` | Một `DeviceCanvasInfo`: width, height, stride, offsets, status | Setup S6 ghi; Host đọc metadata nhỏ để kiểm tra/cấp phát |
| `d_canvas` | RGB panorama; `canvas_capacity_bytes` | S6 ghi; Host copy D2H |
| `d_panorama` | Alias của `d_canvas` khi S6 thật enqueue thành công; không sở hữu bộ nhớ | Caller chờ stream/event rồi dùng để D2H; không free alias |
| `d_scratch` | Byte scratch; `scratch_capacity_bytes` | Chủ stage khai báo nhu cầu; Host owner cấp phát trước khi sử dụng |

Counts là số phần tử hợp lệ, không phải capacity. S3 phải giữ keypoint/descriptor cùng chỉ số sau compaction; cập nhật counts tương ứng. Với cặp keypoint/descriptor đã mô tả, số phần tử của hai mảng phải khớp. Mỗi stage phải kiểm tra capacity trước khi ghi; báo trạng thái lỗi thay vì ghi vượt mảng. Gray ảnh A và B có thể khác kích thước. Scratch chưa được cấp phát trong scaffold, nên con trỏ là null và capacity bằng 0.

Luồng **Device-resident**: hai ảnh gốc H2D ở đầu mỗi lượt chạy; S1 → S6 truyền con trỏ Device, không copy các mảng trung gian về Host; panorama D2H ở cuối. Chỉ counts, status, kích thước canvas hoặc metadata nhỏ được đọc về Host khi cần điều phối. Workspace là metadata launch trên Host, không tự copy toàn bộ workspace rồi dereference trên Device.

Scaffold cấp canvas bằng kích thước A vì output thử là A. Module S6 thật trong `src/v1/v1_warp_blend.cu` đã tách setup/render: kernel setup công bố `DeviceCanvasInfo`, Host đợi metadata nhỏ cùng inverse H, kiểm tra overflow/giới hạn canvas rồi thay allocation output, cập nhật `d_canvas`, `d_panorama`, alias `canvas` và capacity. Không giả định capacity của scaffold đủ cho panorama thật. Chi phí điều phối/cấp phát canvas phụ thuộc H và copy metadata phải nằm trong end-to-end của lượt chạy; không giấu chúng trong warm-up. Nối module thật vào dispatcher và mở rộng pinned output theo canvas động thuộc P6.

### 11.2. Contract hàm và stream

Sáu entry point tạm thời nằm trong `main.cu`, namespace `panorama`:

```cpp
ErrorCode v1_preprocess(DeviceWorkspace&, const Config&, cudaStream_t);
ErrorCode v1_detect(DeviceWorkspace&, const Config&, cudaStream_t);
ErrorCode v1_describe(DeviceWorkspace&, const Config&, cudaStream_t);
ErrorCode v1_match(DeviceWorkspace&, const Config&, cudaStream_t);
ErrorCode v1_homography(DeviceWorkspace&, const Config&, cudaStream_t);
ErrorCode v1_scaffold_warp_blend(DeviceWorkspace&, const Config&, cudaStream_t);
```

Stage enqueue công việc trên stream được truyền vào và trả `ErrorCode`. Không ghi log trong vùng đo. Lỗi launch được kiểm tra ngay; lỗi bất đồng bộ được phát hiện khi chờ event/stream. Nếu kernel ghi lỗi thuật toán vào `d_counts->status` hoặc `d_canvas_info->status`, bên điều phối phải đọc và xử lý trước khi dùng output; scaffold chưa kiểm chứng lỗi thuật toán vì chưa có kernel thuật toán. Khi thay stub bằng implementation trong `src/v1/`, phải xóa định nghĩa stub tương ứng để tránh trùng symbol và bổ sung header công khai cho stage.

S6 thật có API `v1_warp_blend(DeviceWorkspace&, const Config&, cudaStream_t)` trong [`v1/v1_warp_blend.h`](../src/v1/v1_warp_blend.h), được kiểm thử độc lập bằng dữ liệu V0 ở P5. CLI vẫn gọi hàm scaffold đã đổi tên để không dùng H chưa được S5 stub tính. S6 thật chờ metadata setup, nhưng không chờ render sau cùng: `Success` nghĩa là enqueue thành công; caller phải chờ stream/event trước D2H hoặc free. Lỗi config/geometry không công bố panorama; allocation cũ còn giữ trong `d_canvas` vẫn thuộc owner. Chi tiết tolerance và test ở [S6 mục 7.1](stages/s6-warp-blend.md#71-cài-đặt-và-kiểm-chứng-v1--p5-t13).

V1 scaffold dùng một stream non-blocking, các stage thực hiện theo thứ tự. Không đặt synchronize thừa giữa sáu stage. Khi dùng thêm stream trong tương lai, chủ stage phải nối dependency bằng event trước khi stage sau đọc dữ liệu; event kết thúc stage phải bao phủ mọi nhánh.

### 11.3. CUDA_CHECK và giải phóng khi lỗi

`CUDA_CHECK(call)` đánh giá call đúng một lần, in file/dòng/call/mã lỗi ra stderr rồi ném `CudaError`. Exception tháo stack để destructor chờ stream, hủy event/stream, giải phóng pinned memory và mọi Device allocation đã cấp phát, kể cả khi prepare mới hoàn thành một phần. `main` bắt lỗi sau cleanup và gọi `exit(EXIT_FAILURE)`. Không gọi `exit` trực tiếp trong macro vì làm vậy bỏ qua destructor của các biến cục bộ. Khi dùng helper ở executable khác, executable đó cũng cần catch ở biên chương trình và trả lỗi sau khi unwind.

`device_allocate<T>` chỉ nhận con trỏ rỗng, kiểm tra overflow `count * sizeof(T)`, và giữ con trỏ rỗng khi allocation thất bại. Count bằng 0 không cấp phát. `device_free<T>` cho phép null, reset con trỏ sau khi free và không ném exception trong destructor; lỗi cleanup được báo stderr. Ownership không copy được. Không dùng `cudaDeviceReset` để dọn một workspace vì thao tác đó phá cả tài nguyên CUDA khác trong context.

### 11.4. Timing và CSV V1

Một lượt warm-up chạy đủ H2D → sáu stub → D2H, không gọi clock hoặc record event timing. Sau đó chạy N lượt đo (`--runs`, mặc định 5). Input đã decode, pinned staging, Device buffers, stream và events được chuẩn bị trước warm-up; chúng được tái sử dụng. CPU copy từ ảnh stb sang pinned input cũng nằm ngoài phép đo. Đây là chính sách chuẩn bị bộ nhớ của scaffold, cần ghi rõ khi so sánh với phiên bản khác.

- **GPU stage timing:** dùng `cudaEventRecord` trước/sau stage trên cùng stream; sau khi event cuối hoàn tất mới gọi `cudaEventElapsedTime`. `stage_ms[0..5]` tương ứng S1_V1 đến S6_V1. S1–S3 của implementation thật phải bao gồm cả A và B. Đây là elapsed của toàn stage, có thể bao gồm memory operations và khoảng chờ, không mặc định là kernel busy time.
- **Transfer timing:** cặp events riêng đo `h2d_ms` của hai ảnh và `d2h_ms` của panorama. Dùng pinned Host buffers và `cudaMemcpy2DAsync`; stride luôn là byte.
- **End-to-end:** `std::chrono::high_resolution_clock` bao từ trước H2D đến sau `cudaEventSynchronize` của event D2H cuối. Đây là thời gian Host quan sát toàn pipeline đã đồng bộ, **không phải CPU timer dùng để suy ra thời gian kernel bất đồng bộ**. H2D, sáu stage, D2H và overhead điều phối trong lượt chạy đều nằm trong khoảng này. Đọc/ghi file ảnh, log, xuất CSV và tính average/min nằm ngoài.
- **Kernel-only total:** scaffold không launch compute kernel, nên `total_kernel_ms = 0`; copy Device-to-Device của S6 không phải kernel. Không cộng sáu stage elapsed rồi gọi đó là kernel-only total. Khi tích hợp kernel thật, phải bổ sung phép đo kernel-only và tổng hợp trường này trước khi công bố benchmark V1; số 0 hiện tại chỉ mô tả stub.

CSV V1 có 11 cột; CSV V0 vẫn có 8 cột để công cụ giữa kỳ tiếp tục hoạt động:

```csv
Run_Index,S1_V1_ms,S2_V1_ms,S3_V1_ms,S4_V1_ms,S5_V1_ms,S6_V1_ms,Total_ms,H2D_ms,D2H_ms,Total_Kernel_ms
```

`Total_ms` là `TimingStats::end_to_end_ms`. `Average` và `Minimum` tổng hợp độc lập từng cột của N lượt đo, không gồm warm-up. Trường H2D/D2H cũ trong bản nháp (`host_to_device_ms`, `device_to_host_ms`) được đổi tên thành `h2d_ms`, `d2h_ms`; dữ liệu V0 và CSV V0 không đổi. Công cụ đa phiên bản của P5-T05 cần nhận biết header V1; parser V0 hiện tại không dùng để đọc CSV V1. Giá trị thời gian stub không được dùng tính speedup.

### 11.5. Build và kiểm chứng

```bash
python3 scripts/build.py --compiler nvcc --require-t4
./build/stitch <left.jpg> <right.jpg> <v0.png> --version 0
./build/stitch <left.jpg> <right.jpg> <stub.png> --version 1 --runs 5 --debug
python3 tests/run_tests.py --compiler nvcc --require-t4
```

V0 phải giữ nguyên ảnh kết quả và schema CSV. Output PNG của V1 scaffold phải có cùng pixel RGB và kích thước với ảnh A đã decode, không phải panorama. Kiểm tra thêm lỗi thiếu GPU, allocation/cleanup, event timing, số dòng CSV và average/min. Log kiểm tra cục bộ phải ghi GPU thực tế; chỉ đánh dấu nghiệm thu chính thức sau build/test trên Colab T4 và merge PR.

Kiểm tra cục bộ ngày 30/10/2026: WSL Ubuntu, GTX 1650, nvcc 12.6.85, target `sm_75`; build Host g++ 13 và build CUDA đều đạt. Bộ V0 đạt 13 suite / 45.256 checks; bộ Python chạy 67 test thuộc 5 suite, có 1 test skip. V0 trên site1 small, default 5 runs, giữ CSV 8 cột và PNG khớp từng byte với baseline trước thay đổi, kể cả khi ẩn GPU. V1 stub được kiểm tra CSV 11 cột, average/min, H2D/D2H, output khớp ảnh A giải mã bằng stb, lỗi thiếu GPU và lỗi CUDA chủ động để kiểm tra unwind. Đây là bằng chứng kiểm tra cục bộ, chưa thay thế nghiệm thu Colab T4. Log/script thử cục bộ nằm trong `build/gpu_contract_*`, không đưa dữ liệu thực nghiệm vào Git.

Căn cứ API: [NVIDIA CUDA Runtime — Event Management](https://docs.nvidia.com/cuda/cuda-runtime-api/group__CUDART__EVENT.html), [Memory Management](https://docs.nvidia.com/cuda/cuda-runtime-api/group__CUDART__MEMORY.html), [CUDA Programming Guide — Asynchronous Execution](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/asynchronous-execution.html). Code helper do nhóm viết; các tài liệu này được dùng để kiểm tra semantics của API.

Nghiệm thu bổ sung ngày 30/10/2026 trên Colab Tesla T4, nvcc 13.0.88, target `sm_75`: build chương trình đạt, 13 suite V0 / 45.256 checks và CLI mặc định năm lượt đo đạt. S6 CUDA độc lập đạt fixture, 12 case cùng H và memcheck; xem [báo cáo nghiệm thu](report/p5-s6-cuda-verification.md). Các phép đo H2D/D2H/kernel và end-to-end của pipeline GPU tích hợp vẫn thuộc P6; không dùng kết quả correctness này làm số đo speedup.

### 11.6. Entry point S4/S5 sau P5

Hai API thật nằm trong `src/v1/s4/v1_match.h` và `src/v1/s5/v1_homography.h`, giữ chữ ký `ErrorCode(DeviceWorkspace&, const Config&, cudaStream_t)`. `DeviceWorkspace`, `DeviceCounts` và các kiểu truyền dữ liệu không thay đổi.

Caller sở hữu scratch, cấp phát theo `v1_match_scratch_bytes()` và `v1_homography_scratch_bytes()`; S4/S5 có thể dùng chung buffer bằng dung lượng lớn hơn khi chạy nối tiếp trên cùng stream. S5 yêu cầu căn chỉnh 16 byte. Stage không giải phóng hoặc thay con trỏ workspace. Return code phản ánh lỗi Host/launch; caller phải đợi stream/event và kiểm tra `d_counts->status` để nhận lỗi thuật toán.

Scaffold trong `main.cu` giữ hai hàm riêng `v1_stub_match`, `v1_stub_homography` trong bảng điều phối. Vì S1–S3 chưa phát sinh feature, chương trình chính chưa gọi hai API thật và vẫn cảnh báo sáu stub. Cách đặt tên này cho phép link module S4/S5 mà không trùng symbol, đồng thời giữ smoke test hạ tầng của P5-T12. Việc đổi bảng điều phối sang sáu stage thật thuộc P6.

S5 cung cấp diagnostics và inlier mask dưới dạng con trỏ Device mượn trong scratch. Chỉ đọc sau khi stream hoàn tất và trước khi scratch được dùng lại. Không chuyển STL container qua Device. Ngưỡng so H CPU–GPU do Đế xác nhận ngày 31/10/2026: RMSE ≤ 0,0001 px, Max ≤ 0,001 px trên lưới 20×20 của ảnh B; match, sample prefix và mask phải khớp chính xác. Ngưỡng ground truth giữ RMSE ≤ 0,5 px và Max ≤ 1 px.
