# Dataset: quy định chụp ảnh và chuẩn bị dữ liệu

Người điều phối: Thành. Hạn của các việc liên quan nằm trong [bảng công việc](task-board.md).

## 1. Yêu cầu của đề

| Hạng mục | Tối thiểu |
|---|---|
| Địa điểm (site) | 3 địa điểm khác nhau, gợi ý 1 trong nhà, 1 ngoài trời, 1 tự chọn |
| Cặp chuẩn | 1 cặp cho mỗi địa điểm (3 cặp), dùng để benchmark và làm gallery |
| Cặp khó | 1 cặp, dùng để phân tích thất bại (ít texture, họa tiết lặp, người di chuyển, cảnh đêm...) |
| Kích thước | Mỗi cặp cắt về 16:9 và tạo 3 bản 1280×720, 1920×1080, 3840×2160 từ cùng một cảnh |
| Cách chụp | Đứng yên và xoay máy, không bước ngang; hai ảnh chồng lấn 30-50% |

## 2. Số lượng ảnh mỗi người chụp

Số lượng ảnh/cặp mỗi người chụp **chưa chốt**. Cả Nhóm sẽ thống nhất trong task P0-T01 và ghi kết quả vào đây.

Đề xuất để Nhóm cân nhắc: mỗi người chọn 1 địa điểm và chụp ít nhất 3 cặp chuẩn (3 hướng nhìn khác nhau) cùng 2 cặp khó (mỗi cặp một yếu tố khó khác nhau). Như vậy mỗi người có tối thiểu 10 ảnh. Nên chụp lặp mỗi cặp thêm một lần để dự phòng ảnh mờ hoặc rung.

Các quy định áp dụng dù Nhóm chốt số lượng nào:

- Các thành viên **được chụp ở cùng địa điểm**, nhưng **ảnh không được trùng nhau**. Mỗi ảnh phải do chính người nộp chụp, không dùng lại ảnh của người khác và không nộp một ảnh hai lần.
- 3 địa điểm được chọn cuối cùng phải là 3 địa điểm khác nhau, nên có ít nhất 1 trong nhà và 1 ngoài trời.

## 3. Quy định khi chụp

### 3.1 Cài đặt máy

1. Dùng **camera chính (1x)**. Không dùng ống góc siêu rộng (méo hình mạnh), ống tele hay zoom số.
2. Chụp **ngang** (landscape).
3. Định dạng **JPEG**. Trên iPhone chọn `Settings -> Camera -> Formats -> Most Compatible`, vì stb không đọc được HEIC.
4. Tắt chế độ chân dung, bộ lọc, làm đẹp, tối ưu cảnh bằng AI và chế độ đêm (trừ khi cặp khó chủ đích là cảnh đêm). Nếu tắt được HDR thì tắt; nếu không, giữ cùng một thiết lập cho cả hai ảnh.
5. Sau khi cắt về 16:9, ảnh phải còn **ít nhất 3840×2160**. Ảnh 12 MP tỷ lệ 4:3 (4032×3024) cắt còn 4032×2268 là đạt. Nếu máy chụp trực tiếp 16:9, kiểm tra lại độ phân giải vì một số máy giảm xuống dưới 3840 px.
6. Tắt lưu vị trí GPS trong ảnh, vì link dataset sẽ được chia sẻ cho người chấm.

### 3.2 Cách chụp một cặp

1. Đứng cố định một chỗ, giữ máy ngang bằng (bật lưới hoặc thước cân bằng nếu có), giữ máy sát người.
2. Chạm giữ lên màn hình để **khóa phơi sáng và lấy nét (AE/AF lock)** nếu máy hỗ trợ, rồi chụp **ảnh trái** trước.
3. **Xoay người tại chỗ** sang phải, không bước ngang, không nâng hạ máy. Chụp **ảnh phải** ngay sau đó để ánh sáng không đổi.
4. Kiểm tra độ chồng lấn 30-50%: chọn một vật mốc nằm ở khoảng 80% chiều ngang ảnh trái (gần mép phải). Xoay đến khi vật đó nằm ở khoảng 10-30% chiều ngang ảnh phải. Với camera chính, góc xoay thường vào khoảng 35-45°.
5. Phóng to ảnh trên điện thoại để kiểm tra độ nét. Nếu mờ, chụp lại ngay.

### 3.3 Chọn cảnh

| Nên | Tránh |
|---|---|
| Cảnh có nhiều chi tiết: chữ, cửa sổ, kệ đồ, mép tường, cây | Mặt phẳng trơn trong vùng chồng lấn (với cặp chuẩn) |
| Vật trong vùng chồng lấn ở xa vài mét trở lên | Vật rất gần máy (dưới khoảng 2 m) trong vùng chồng lấn, vì gây parallax |
| Cảnh tĩnh | Người, xe di chuyển trong vùng chồng lấn (với cặp chuẩn) |
| Ánh sáng đều | Ngược sáng mạnh, đèn nhấp nháy |

**Cặp khó** vẫn chụp theo mục 3.2, nhưng có chủ đích một yếu tố khó: ít texture, họa tiết lặp, người di chuyển, thiếu sáng hoặc cảnh đêm, chênh sáng mạnh, hoặc vật ở gần gây parallax. Mỗi cặp khó chỉ nên có một yếu tố chính để dễ phân tích nguyên nhân thất bại.

### 3.4 Lịch sự và quyền riêng tư

- Tránh chụp rõ mặt người lạ. Không chụp ở nơi cấm chụp ảnh hoặc chụp tài liệu riêng tư.
- Nếu chụp trong nhà ở nơi không công cộng, phải xin phép chủ địa điểm.

## 4. Nộp ảnh gốc

**Hiện chưa có link Google Drive.** Tuấn sẽ tạo và cập nhật link vào đây (task P0-T06).

Link Drive: (chưa có)

1. Upload ảnh **gốc, chưa chỉnh sửa**.
2. Đặt tên file bằng tiếng Anh:
    - cặp chuẩn: `pair1_left.jpg`, `pair1_right.jpg`, `pair2_left.jpg`, ...;
    - cặp khó: `challenge1_left.jpg`, `challenge1_right.jpg`, ...;
    - lần chụp lặp: thêm hậu tố `_b`, ví dụ `pair1_left_b.jpg`.
3. Điền thông tin vào bảng ứng viên ở mục 5.2.

## 5. Địa điểm và ứng viên

### 5.1 Địa điểm dự kiến

| Người chụp | Tên địa điểm | Site slug | Loại (trong nhà / ngoài trời) | Mô tả ngắn |
|---|---|---|---|---|
| Tuấn | | | | |
| Thành | | | | |
| Chương | | | | |
| Đế | | | | |

Site slug là tên địa điểm viết thường, không dấu, nối bằng gạch ngang, ví dụ `can-tin-b`.

### 5.2 Danh sách cặp ứng viên

| Mã cặp | Người chụp | Site slug | Loại (chuẩn / khó) | Yếu tố khó (nếu có) | Ngày, giờ chụp | Điện thoại | Độ phân giải gốc |
|---|---|---|---|---|---|---|---|
| tuan-pair1 | Tuấn | | chuẩn | | | | |

### 5.3 Kết quả kiểm tra

Thành kiểm tra mọi cặp ứng viên có đạt các yêu cầu ở mục 1 và mục 3 hay không, rồi ghi kết quả vào bảng dưới.

| Mã cặp | Đạt? | Ghi chú |
|---|---|---|

## 6. Cách chọn ảnh

**Chưa chốt** cách chọn ảnh (có bình chọn hay không). Cả Nhóm sẽ quyết định trong task P0-T01, cùng lúc với số lượng ảnh ở mục 2, và ghi kết quả vào đây.

## 7. Chuẩn bị dataset

Với mỗi cặp được chọn, script chuẩn bị dataset phải bảo đảm:

1. Ảnh được xoay đúng theo thông tin EXIF orientation, vì stb bỏ qua EXIF và có thể đọc ra ảnh bị xoay sai.
2. Ảnh trái và ảnh phải của một cặp được cắt về 16:9 bằng cùng một khung cắt.
3. Ba kích thước 1280×720, 1920×1080, 3840×2160 được tạo từ cùng một ảnh đã cắt.
4. File đầu ra không còn EXIF và được đặt tên theo dạng `dataset/site1/small_left.jpg`, `dataset/site1/medium_right.jpg`, `dataset/challenge/large_left.jpg`.

## 8. Kết quả cuối cùng

| Vai trò | Site | Địa điểm | Loại | Người chụp | Cặp chính | Cặp dự phòng |
|---|---|---|---|---|---|---|
| Site 1 | site1 | | | | | |
| Site 2 | site2 | | | | | |
| Site 3 | site3 | | | | | |
| Cặp khó | challenge | | | | | |
