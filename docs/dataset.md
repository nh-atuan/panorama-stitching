# Dataset: quy định chụp ảnh và chuẩn bị dữ liệu

Người điều phối: chưa phân công. Hạn của các việc liên quan nằm trong [bảng công việc](task-board.md).

## 1. Yêu cầu của đề

| Hạng mục | Tối thiểu |
|---|---|
| Địa điểm (site) | 3 địa điểm khác nhau, gợi ý 1 trong nhà, 1 ngoài trời, 1 tự chọn |
| Cặp chuẩn | 1 cặp cho mỗi địa điểm (3 cặp), dùng để benchmark và làm gallery |
| Cặp khó | 1 cặp, dùng để phân tích thất bại (ít texture, họa tiết lặp, người di chuyển, cảnh đêm...) |
| Kích thước | Mỗi cặp cắt về 16:9 và tạo 3 bản 1280×720, 1920×1080, 3840×2160 từ cùng một cảnh |
| Cách chụp | Đứng yên và xoay máy, không bước ngang; hai ảnh chồng lấn 30-50% |

## 2. Số lượng ảnh mỗi người chụp

Mỗi người chọn 1 địa điểm và chụp ít nhất:

| Loại | Số cặp tối thiểu | Ghi chú |
|---|---:|---|
| Cặp chuẩn | 2 | 2 khu vực hoặc khung cảnh khác nhau trong cùng địa điểm |
| Cặp khó | 1 | Có một yếu tố khó chính |
| **Tổng** | **3 cặp = 6 ảnh** | |

Nên chụp lặp mỗi cặp thêm một lần để dự phòng ảnh mờ hoặc rung.

Các quy định khác:

- Các thành viên **được chụp ở cùng địa điểm**, nhưng **ảnh không được trùng nhau**. Mỗi ảnh phải do chính người nộp chụp, không dùng lại ảnh của người khác và không nộp một ảnh hai lần.
- 3 địa điểm được chọn cuối cùng phải là 3 địa điểm khác nhau.

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

Link Drive: https://drive.google.com/drive/folders/127SOMhoY2EwBbkCxGWGPju-EbmG0QiOq?usp=sharing

1. Upload ảnh **gốc, chưa chỉnh sửa** vào thư mục con mang tên mình (`tuan`, `thanh`, `chuong`, `de`). Tên file không lặp lại tên thành viên vì đã có trong tên thư mục; khi tải về để kiểm tra hoặc chạy script chuẩn bị dataset phải giữ nguyên cấu trúc `raw/<tên thành viên>/`.
2. Đặt tên file bằng tiếng Anh theo dạng `<loại cặp><số>_<left|right>[_b<k>].jpg`, chỉ dùng chữ thường, không dấu cách:
    - cặp chuẩn: `standard1_left.jpg`, `standard1_right.jpg`, `standard2_left.jpg`, ...;
    - cặp khó: `challenge1_left.jpg`, `challenge1_right.jpg`, ...;
    - cặp backup: thêm hậu tố `_b1`, `_b2`, ..., ví dụ `standard1_left_b1.jpg`, `standard1_right_b1.jpg`.
3. Cặp không có hậu tố là cặp chính mà người chụp đề xuất dùng. Số `k` trong `_b<k>` là thứ tự ưu tiên dự phòng do người chụp tự quyết định (`b1` được dùng trước `b2`), không phải thứ tự thời gian chụp.
4. Ảnh trái và ảnh phải có cùng hậu tố tạo thành một cặp; không ghép ảnh của hai cặp khác nhau, ví dụ `standard1_left_b1.jpg` chỉ đi với `standard1_right_b1.jpg`.
5. Điền thông tin vào bảng ứng viên ở mục 5.2, mỗi cặp chính và mỗi cặp backup một dòng.

## 5. Địa điểm và ứng viên

### 5.1 Địa điểm dự kiến

| Người chụp | Tên địa điểm | Site slug | Loại (trong nhà / ngoài trời) | Mô tả ngắn |
|---|---|---|---|---|
| Tuấn | Ẩn Coffee | an-coffee | Cả hai | Quán cà phê; `standard1` chụp ngoài trời, `standard2` chụp trong nhà |
| Thành | | | | |
| Chương | | | | |
| Đế | | | | |

Site slug là tên địa điểm viết thường, không dấu, nối bằng gạch ngang, ví dụ `can-tin-b`.

### 5.2 Danh sách cặp ứng viên

| Mã cặp | Người chụp | Site slug | Loại (chuẩn / khó) | Yếu tố khó (nếu có) | Ngày, giờ chụp | Điện thoại | Độ phân giải gốc |
|---|---|---|---|---|---|---|---|
| tuan-standard1 | Tuấn | an-coffee | chuẩn | | 07/10 12:09 | nubia Neo 3 GT 5G | 8160×6144 |
| tuan-standard1-b1 | Tuấn | an-coffee | chuẩn | | 07/10 12:42 | nubia Neo 3 GT 5G | 4080×3072 |
| tuan-standard1-b2 | Tuấn | an-coffee | chuẩn | | 07/10 12:43 | nubia Neo 3 GT 5G | 4080×3072 |
| tuan-standard1-b3 | Tuấn | an-coffee | chuẩn | | | | |
| tuan-standard2 | Tuấn | an-coffee | chuẩn | | 07/10 12:10 | nubia Neo 3 GT 5G | 8160×6144 |
| tuan-standard2-b1 | Tuấn | an-coffee | chuẩn | | | | |
| tuan-challenge1 | Tuấn | an-coffee | khó | Ít texture | 07/10 12:35 | nubia Neo 3 GT 5G | 8160×6144 |
| tuan-challenge1-b1 | Tuấn | an-coffee | khó | | | | |

Mã cặp có dạng `<tên thành viên>-<loại cặp><số>[-b<k>]`, tương ứng với tên file ở mục 4, ví dụ `tuan-standard1-b1` gồm `tuan/standard1_left_b1.jpg` và `tuan/standard1_right_b1.jpg`.

### 5.3 Kết quả kiểm tra

Thành soạn script kiểm tra các cặp chính của từng thành viên theo quy trình ở mục 6, rồi ghi kết quả vào bảng dưới. Không xét các cặp backup.

| Mã cặp | Đạt? | Ghi chú |
|---|---|---|

## 6. Cách chọn ảnh

1. **Phạm vi:** chỉ xét các cặp chính do từng thành viên chụp, tức các cặp không có hậu tố `_b<k>` ở mục 4. Các cặp backup không được đưa vào kiểm tra hoặc xếp ưu tiên trong bước chọn ảnh này.
2. **Thành soạn script kiểm tra:** kiểm tra từng cặp chính có thỏa các yêu cầu của đề ở mục 1 và các quy định chụp ảnh ở mục 3 hay chưa. Kết quả phải ghi rõ tiêu chí đã kiểm tra, đạt hoặc chưa đạt và lý do; tiêu chí không thể xác minh tự động phải được đánh dấu để thành viên review, không mặc định là đạt.
3. **Xếp thứ tự ưu tiên:** Thành dùng kết quả kiểm tra để xếp các cặp chính theo mức độ phù hợp, kèm lý do cho thứ tự đề xuất. Cặp chuẩn và cặp khó được xếp riêng theo mục đích sử dụng; yếu tố khó có chủ đích không tự động khiến cặp khó bị đánh giá là không phù hợp. Ghi kết quả kiểm tra ở mục 5.3 và thứ tự ưu tiên đề xuất trong bảng dưới.
4. **Review và chốt:** từng thành viên review lại kết quả kiểm tra, thứ tự ưu tiên và ảnh thực tế; xác nhận hoặc ghi rõ điều chỉnh cùng lý do. Sau khi từng thành viên review, cả Nhóm chốt các cặp được chọn và ghi kết quả cuối cùng ở mục 8, bảo đảm đủ 3 địa điểm khác nhau, mỗi địa điểm 1 cặp chuẩn và ít nhất 1 cặp khó. Nếu có vấn đề chưa thống nhất, báo lại cho cả Nhóm để cùng quyết định.

| Loại (chuẩn / khó) | Thứ tự ưu tiên đề xuất | Mã cặp chính | Lý do đề xuất | Kết quả review của từng thành viên |
|---|---|---|---|---|

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
