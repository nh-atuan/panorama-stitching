<!-- Authors: Le Thuong De (23120232), Nguyen Ho Anh Tuan (23120185), Tran Huu Kim Thanh (23120166), Le Ha Thanh Chuong (23120195). External source: none. -->

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
| Thành | Nhà thờ | nha-tho | Ngoài trời | `standard1` |
| Thành | Đường ngoài trời | duong-ngoai-troi | Ngoài trời | `standard2` |
| Thành | Quán cafe Houjicha | houjicha-cafe | Trong nhà | `standard3` |
| Thành | Sau khuôn viên Trường Đại học Đồng Nai | dai-hoc-dong-nai | Ngoài trời | `standard4`, `standard4-b1` |
| Thành | Trên đường đi | duong-di | Ngoài trời | `challenge1`: có người di chuyển |
| Chương | Khuôn viên Trường Đại học Khoa học Tự nhiên, ĐHQG-HCM | hcmus-campus | Ngoài trời | `standard1`: bờ tường đá; `standard2`: bia đá khuôn viên |
| Chương | Khu vực ký túc xá | ky-tuc-xa | Ngoài trời | `challenge1`: cảnh đêm, chênh sáng và đối tượng chuyển động |
| Đế | Tiệm cà phê Mai An | mai-an-coffee | Cả hai | Quán cà phê; `standard1` chụp trong nhà, `standard2` chụp ngoài trời|

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
| thanh-standard1 | Thành | nha-tho | chuẩn | | 07/10 16:41 | Xiaomi 2210129SG | 4096×3072 |
| thanh-standard2 | Thành | duong-ngoai-troi | chuẩn | | 07/10 16:33 | Xiaomi 2210129SG | 4096×3072 |
| thanh-standard3 | Thành | houjicha-cafe | chuẩn | | 07/10 16:26 | Xiaomi 2210129SG | 4096×3072 |
| thanh-standard4 | Thành | dai-hoc-dong-nai | chuẩn | | 07/10 14:19 | Xiaomi 2210129SG | 4096×3072 |
| thanh-standard4-b1 | Thành | dai-hoc-dong-nai | chuẩn | | 07/10 14:18 | Xiaomi 2210129SG | 4096×3072 |
| thanh-challenge1 | Thành | duong-di | khó | Người di chuyển | 07/10 16:37 | Xiaomi 2210129SG | 4096×3072 |
| chuong-standard1 | Chương | hcmus-campus | chuẩn | | 08/10/2026 10:25:05 | vivo iQOO Neo10 | 4096×2304 |
| chuong-standard2 | Chương | hcmus-campus | chuẩn | | 08/10/2026 10:27:33 | vivo iQOO Neo10 | 4096×2304 |
| chuong-challenge1 | Chương | ky-tuc-xa | khó | Cảnh đêm (chính); chênh sáng, người/xe chuyển động và motion blur (kèm theo) | 07/10/2026 18:01:27 | vivo iQOO Neo10 | 4096×2304 |
| de-standard1 | Đế | mai-an-coffee | chuẩn | | Không có EXIF | Không có EXIF | 4032×3024 |
| de-standard2 | Đế | mai-an-coffee | chuẩn | | Không có EXIF | Không có EXIF | 4032×3024 |
| de-challenge1 | Đế | mai-an-coffee | khó | Họa tiết lặp ở trần và lan can; cần phân tích ảnh hưởng đến matching | Không có EXIF | Không có EXIF | 4032×3024 |

Mã cặp có dạng `<tên thành viên>-<loại cặp><số>[-b<k>]`, tương ứng với tên file ở mục 4, ví dụ `tuan-standard1-b1` gồm `tuan/standard1_left_b1.jpg` và `tuan/standard1_right_b1.jpg`.

### 5.3 Kết quả kiểm tra

Thành soạn script kiểm tra các cặp chính của từng thành viên theo quy trình ở mục 6, rồi ghi kết quả vào bảng dưới. Không xét các cặp backup.

Kết quả dưới đây do Tuấn làm thay Thành (P0-T10), chạy `scripts/check_pairs.py` ngày 18/10 trên toàn bộ thư mục Drive ở mục 4, tải lại bằng `gdown` sau khi các thành viên cập nhật ảnh. Kết quả lần chạy ngày 16/10 không còn đúng với Drive hiện tại. Mỗi tiêu chí nhận một trong ba kết quả: `Đạt`, `Chưa đạt`, `Cần review`. Tiêu chí không kiểm tra tự động được (cảnh tĩnh, ít parallax, đủ texture với cặp chuẩn, không lộ mặt người lạ) luôn là `Cần review`. Chồng lấn là ước lượng bằng cách tìm độ dịch ngang tốt nhất giữa hai ảnh thu nhỏ; khi tương quan thấp hơn 0.3, ước lượng được ghi là không tin cậy. Ngưỡng độ nét là một nửa trung vị của các cặp đã kiểm tra (lần này là 900), chỉ dùng để so sánh tương đối. Bảng này là kết quả của script, chưa phải kết luận review.

Chạy lại từ gốc repo, với ảnh gốc đặt trong `raw/<thành viên>/`:

```bash
python scripts/check_pairs.py --raw raw --out results/check_pairs.md
```

| Mã cặp | Đạt? | Ghi chú |
|---|---|---|
| tuan-standard1 | Cần review | Đạt: tên file, JPEG, ảnh ngang, 8160×6144 cắt 16:9 còn 8160×4590, cùng kích thước, cùng thiết bị, chụp liền nhau, độ nét. Cần review: EXIF có tọa độ GPS; không có tiêu cự quy đổi 35 mm (tiêu cự thật 3.98 mm); chồng lấn ước lượng 28%, không tin cậy (tương quan 0.25); các tiêu chí thủ công |
| tuan-standard2 | Cần review | Như `tuan-standard1`. Cần review thêm: độ nét 631; chồng lấn ước lượng 56% (tương quan 0.37), cao hơn khoảng 30-50% |
| tuan-challenge1 | Cần review | Như `tuan-standard1`. Cần review thêm: độ nét 288; chồng lấn ước lượng 58%, không tin cậy (tương quan 0.04). Yếu tố khó có chủ đích là ít texture, nên ước lượng chồng lấn không tin cậy là hợp lý |
| thanh-standard1 | Cần review | Đạt: tên file, JPEG, ảnh ngang, 4096×3072 cắt 16:9 còn 4096×2304, cùng kích thước, cùng thiết bị, chụp liền nhau, không có GPS, độ nét, chồng lấn ước lượng 40%. Cần review: tiêu cự quy đổi 35 mm là 46 mm, cần xác nhận là camera chính 1x; các tiêu chí thủ công |
| thanh-standard2 | Cần review | Như `thanh-standard1` nhưng camera chính đạt. Cần review: chồng lấn ước lượng 68% (tương quan 0.34); các tiêu chí thủ công |
| thanh-standard3 | Cần review | Như `thanh-standard2`. Cần review: chồng lấn ước lượng 37%, không tin cậy (tương quan 0.22); các tiêu chí thủ công |
| thanh-standard4 | Cần review | Như `thanh-standard2`. Cần review: chồng lấn ước lượng 56%, không tin cậy (tương quan 0.28); các tiêu chí thủ công |
| thanh-challenge1 | Cần review | Như `thanh-standard2`. Cần review: chồng lấn ước lượng 58% (tương quan 0.33); các tiêu chí thủ công |
| chuong-standard1 | Cần review | Đạt: tên file, JPEG, ảnh ngang, 4096×2304 (đã là 16:9), cùng kích thước, cùng thiết bị, chụp liền nhau, độ nét. Cần review: EXIF có tọa độ GPS; chồng lấn ước lượng 74%, không tin cậy (tương quan 0.19); các tiêu chí thủ công |
| chuong-challenge1 | Cần review | Như `chuong-standard1`. Cần review: chồng lấn ước lượng 80%, không tin cậy (tương quan 0.21) |
| de-standard1 | Chưa đạt | Tên file có phần mở rộng `.jpeg` thay vì `.jpg`. Ảnh là JPEG 4032×3024, cắt 16:9 còn 4032×2268. Cần review: không có EXIF nên không kiểm tra được tiêu cự, thiết bị, thời gian chụp; chồng lấn ước lượng 57%, không tin cậy (tương quan 0.16); các tiêu chí thủ công |
| de-standard2 | Chưa đạt | Như `de-standard1`. Cần review thêm: độ nét 149; chồng lấn ước lượng 62%, không tin cậy (tương quan 0.28) |
| de-challenge (thiếu số) | Chưa đạt | Như `de-standard1`; tên file `challenge_left`, `challenge_right` còn thiếu số thứ tự của cặp. Cần review thêm: độ nét 278; chồng lấn ước lượng 47%, không tin cậy (tương quan 0.12) |

Ghi chú khi tải: bản `gdown` 6.1 ở máy cá nhân giữ phần mở rộng của file, còn `gdown` 5.2.2 trên Colab lưu file của Thành và Đế không có phần mở rộng. Bảng trên dùng bản tải bằng `gdown` 6.1.

**Kiểm tra bổ sung cho P5-T08:** ngày 02/11, Đế chạy lại `scripts/check_pairs.py` trên bản tải về của 13 cặp chính, giữ tên file nhận được khi tải. Kết quả dưới đây bổ sung cho hai cặp được Đế chọn ở mục 6.1; bảng ngày 18/10 ở trên là kết quả lịch sử. `de-challenge1` tương ứng với `de-challenge?` trong output mới vì tên gốc thiếu số thứ tự.

| Mã cặp | Đạt? | Ghi chú kiểm tra ngày 02/11 |
|---|---|---|
| thanh-standard2 | Chưa đạt | Đạt: JPEG, ảnh ngang, cùng kích thước 4096×3072, crop 16:9 còn 4096×2304, camera chính 1x theo EXIF, cùng thiết bị, chụp liền nhau, không có GPS, độ nét theo ngưỡng của script. Chưa đạt: bản tải về có tên `standard2_left`, `standard2_right`, thiếu `.jpg`. Cần review: chồng lấn ước lượng 68% bằng dịch ngang (tương quan 0.34), vượt khoảng 30–50%; đứng yên xoay máy, ít parallax và các tiêu chí thủ công ở mục 3 |
| de-challenge1 | Chưa đạt | Đạt: JPEG, ảnh ngang, cùng kích thước 4032×3024, crop 16:9 còn 4032×2268, không có GPS trong bản tải về. Chưa đạt: tên `challenge_left`, `challenge_right` thiếu số thứ tự và `.jpg`. Cần review: không có EXIF để xác minh camera, cùng thiết bị và thời điểm chụp; độ nét 278 so với ngưỡng tương đối 900; chồng lấn ước lượng 47% không tin cậy (tương quan 0.12); đứng yên xoay máy và các tiêu chí thủ công ở mục 3 |

Kết quả chi tiết được lưu cục bộ ở `results/p5-t08-review/check_pairs-20261102.md`. Bản sao dùng để chạy V0 được chuẩn hóa tên thành `.jpg`, giữ nguyên nội dung ảnh; chưa đổi tên file nguồn trên Drive. Việc chuẩn hóa bản sao không làm tiêu chí tên file của bản tải về tự chuyển thành `Đạt`.

## 6. Cách chọn ảnh

1. **Phạm vi:** chỉ xét các cặp chính do từng thành viên chụp, tức các cặp không có hậu tố `_b<k>` ở mục 4. Các cặp backup không được đưa vào kiểm tra hoặc xếp ưu tiên trong bước chọn ảnh này.
2. **Thành soạn script kiểm tra:** kiểm tra từng cặp chính có thỏa các yêu cầu của đề ở mục 1 và các quy định chụp ảnh ở mục 3 hay chưa. Kết quả phải ghi rõ tiêu chí đã kiểm tra, đạt hoặc chưa đạt và lý do; tiêu chí không thể xác minh tự động phải được đánh dấu để thành viên review, không mặc định là đạt.
3. **Xếp thứ tự ưu tiên:** Thành dùng kết quả kiểm tra để xếp các cặp chính theo mức độ phù hợp, kèm lý do cho thứ tự đề xuất. Cặp chuẩn và cặp khó được xếp riêng theo mục đích sử dụng; yếu tố khó có chủ đích không tự động khiến cặp khó bị đánh giá là không phù hợp. Ghi kết quả kiểm tra ở mục 5.3 và thứ tự ưu tiên đề xuất trong bảng dưới.
4. **Review và chốt:** từng thành viên review lại kết quả kiểm tra, thứ tự ưu tiên và ảnh thực tế; xác nhận hoặc ghi rõ điều chỉnh cùng lý do. Sau khi từng thành viên review, cả Nhóm chốt các cặp được chọn và ghi kết quả cuối cùng ở mục 8, bảo đảm đủ 3 địa điểm khác nhau, mỗi địa điểm 1 cặp chuẩn và ít nhất 1 cặp khó. Nếu có vấn đề chưa thống nhất, báo lại cho cả Nhóm để cùng quyết định.

| Loại (chuẩn / khó) | Thứ tự ưu tiên đề xuất | Mã cặp chính | Lý do đề xuất | Kết quả review của từng thành viên |
|---|---|---|---|---|
| chuẩn | 1 | thanh-standard1 | Thứ tự do script đề xuất ngày 18/10: không có tiêu chí chưa đạt, 2 cần review; chồng lấn ước lượng 40% | |
| chuẩn | 2 | thanh-standard3 | Không có tiêu chí chưa đạt, 2 cần review; chồng lấn ước lượng 37% | |
| chuẩn | 3 | thanh-standard4 | Không có tiêu chí chưa đạt, 2 cần review; chồng lấn ước lượng 56% | |
| chuẩn | 4 | thanh-standard2 | Không có tiêu chí chưa đạt, 2 cần review; chồng lấn ước lượng 68% | Đế, 02/11: chọn thay site2 theo chất lượng panorama và kết quả V0 ở mục 6.1; giữ yêu cầu xác minh overlap, chưa xác nhận đạt toàn bộ tiêu chí |
| chuẩn | 5 | chuong-standard1 | Không có tiêu chí chưa đạt, 3 cần review; chồng lấn ước lượng 74% | |
| chuẩn | 6 | tuan-standard1 | Không có tiêu chí chưa đạt, 4 cần review; chồng lấn ước lượng 28% | |
| chuẩn | 7 | tuan-standard2 | Không có tiêu chí chưa đạt, 5 cần review; chồng lấn ước lượng 56% | |
| chuẩn | 8 | de-standard1 | 1 chưa đạt (tên file), 5 cần review; chồng lấn ước lượng 57% | |
| chuẩn | 9 | de-standard2 | 1 chưa đạt (tên file), 6 cần review; chồng lấn ước lượng 62% | |
| khó | 1 | thanh-challenge1 | Không có tiêu chí chưa đạt, 2 cần review; chồng lấn ước lượng 58% | Đế, 02/11: không chọn; small/medium xuất được panorama, large báo `InvalidCanvas`; riêng lỗi canvas chưa chứng minh chuyển động gây ghép sai |
| khó | 2 | chuong-challenge1 | Không có tiêu chí chưa đạt, 3 cần review; chồng lấn ước lượng 80% | Đế, 02/11: không chọn; V0 vẫn xuất panorama cả ba kích thước, chưa tạo ca thất bại rõ cần thay ở P5 |
| khó | 3 | tuan-challenge1 | Không có tiêu chí chưa đạt, 5 cần review; ít texture có chủ đích | Đế, 02/11: không chọn; vùng chung gần như chỉ có tường trắng, quá ít thông tin để làm ca challenge mong muốn |
| khó | 4 | de-challenge (thiếu số) | 1 chưa đạt (tên file), 6 cần review; chồng lấn ước lượng 47% | Đế, 02/11: chọn làm challenge (`de-challenge1`); có các cấu trúc chung nhận ra được và ca ghép lệch/H không dùng được ở mục 6.1; còn các mục cần xử lý ở mục 5.3 |

Thứ tự trên do script xếp ngày 18/10: cặp có tiêu chí chưa đạt xếp cuối, sau đó ít tiêu chí chưa đạt hoặc chưa kiểm tra được hơn, chồng lấn ước lượng gần 40% hơn, độ nét cao hơn. Script không biết cặp nào chụp ở địa điểm nào, nên thứ tự này chưa tính yêu cầu 3 địa điểm khác nhau. Cột review ghi ý kiến của người thực hiện; phần Đế bổ sung ngày 02/11 không thay cho xác nhận của các thành viên còn lại.

Để hỗ trợ review, Tuấn chạy thử pipeline V0 (nhánh `tuan/shared-v0-pipeline`) ngày 18/10 trên cả 13 cặp chính ở 3 kích thước. Ảnh của Đế được đổi tên thành `.jpg` trên bản sao để chạy, ảnh trên Drive giữ nguyên. Đây là kết quả chạy thử, không phải kết luận review:

| Mã cặp | Số inlier small / medium / large | Kết quả |
|---|---|---|
| thanh-standard1 | 310 / 274 / 109 | Ra panorama ở cả 3 kích thước |
| thanh-standard2 | 465 / 423 / 270 | Ra panorama ở cả 3 kích thước |
| thanh-standard3 | 253 / 187 / 101 | S6 báo `NumericalFailure` ở cả 3 kích thước: phép chiếu đưa một phần ảnh phải qua đường chân trời |
| thanh-standard4 | 318 / 322 / 155 | Small, medium ra panorama; large bị S6 từ chối vì canvas vượt 10.000 px |
| tuan-standard1 | 8 / 9 / 0 | Thất bại ở S5 hoặc S6; mái pergola sát máy gây parallax |
| tuan-standard2 | 186 / 153 / 62 | Ra panorama ở cả 3 kích thước |
| chuong-standard1 | 186 / 158 / 105 | Ra panorama ở cả 3 kích thước |
| de-standard1 | 92 / 69 / 7 | Small, medium ra panorama; large thất bại ở S6 |
| de-standard2 | 167 / 160 / 85 | Ra panorama ở cả 3 kích thước |
| thanh-challenge1 | 123 / 94 / 39 | Small, medium ra panorama; large bị S6 từ chối vì canvas vượt 10.000 px |
| chuong-challenge1 | 440 / 391 / 289 | Ra panorama ở cả 3 kích thước |
| tuan-challenge1 | 5 / 6 / 6 | Thất bại ở S6 ở cả 3 kích thước, đúng với yếu tố ít texture |
| de-challenge (thiếu số) | 17 / 8 / 8 | Small ra panorama nhưng lệch; medium, large thất bại ở S6 |

### 6.1 Review và lựa chọn của Đế cho P5-T08

Ngày 02/11, Đế chọn **`site2 = thanh-standard2`** và **`challenge = de-challenge1`** sau khi chạy V0 trên 13 cặp chính ở ba kích thước và xem ảnh đầu vào, panorama, ảnh matches. Lựa chọn này được ghi lại để báo lại cho cả Nhóm cùng quyết định; các tiêu chí chưa xác minh ở mục 5.3 vẫn giữ trạng thái tương ứng. Chưa cập nhật bộ ảnh và manifest trên Drive.

| Vai trò | Cặp chọn | Lý do chọn |
|---|---|---|
| Cặp chuẩn site2 | thanh-standard2 | Cảnh đường ngoài trời có nhiều chi tiết ở mép nhà, tường và dãy xe; khác địa điểm nhà thờ của site1 và Mai An của site3. V0 xuất panorama ở cả ba kích thước, với 465/423/270 inlier. Khi xem ảnh, bóng đôi giảm rõ so với `tuan-standard2` ở site2 cũ. Crop 4K vẫn có lệch nhỏ ở xe/biển số và phần phải méo phối cảnh; chưa coi là ảnh ghép hoàn hảo |
| Cặp khó challenge | de-challenge1 | Hai ảnh cùng thấy ô thông gió, dầm trần, đèn và lan can; có các chi tiết chung rõ hơn vùng tường trắng của `tuan-challenge1`. Họa tiết lặp ở trần/lan can là yếu tố chính được chọn để phân tích matching. Small xuất panorama nhưng trần và lan can lệch/bóng đôi; medium/large có H không dùng được, tạo ca thất bại cụ thể để phân tích chuỗi matching → H → kiểm tra canvas. Chưa khẳng định họa tiết lặp là nguyên nhân duy nhất; góc nhìn và độ nét có thể cùng ảnh hưởng |

**Cấu hình kiểm tra.** Đế chạy V0 trên CPU cục bộ, biên dịch bằng clang++ 23.1.3 với C++11/O2, tắt FMA contraction và auto-vectorization. Cấu hình ảnh và số lượt lấy từ `Group16_Midterm.ipynb`: small 1280×720, medium 1920×1080, large 3840×2160; yêu cầu 5 lượt đo sau một warm-up. Giữ nguyên Gaussian sigma=1/radius=3, FAST threshold=0.05, tối đa 2000 keypoint, match ratio=0.8, cross-check tắt, seed=16, RANSAC tối đa 2000 hypothesis và các giới hạn S6. Threshold RANSAC do `make_v0_config` tính theo kích thước, lần lượt 2/3/6 px. Không thay phương pháp hay tham số V0 theo từng cặp.

| Cặp | Kích thước | Matches | Inlier | Lượt đo hoàn tất | Kết quả |
|---|---|---|---|---|---|
| thanh-standard2 | small, 1280×720 | 635 | 465 | 5 | Xuất panorama 2558×1440 |
| thanh-standard2 | medium, 1920×1080 | 599 | 423 | 5 | Xuất panorama 3818×2154 |
| thanh-standard2 | large, 3840×2160 | 494 | 270 | 5 | Xuất panorama 7676×4348 |
| de-challenge1 | small, 1280×720 | 114 | 17 | 5 | Xuất panorama 2835×1551, quan sát thấy trần/lan can ghép lệch |
| de-challenge1 | medium, 1920×1080 | 140 | 8 | 0 | Warm-up thất bại: S6 `NumericalFailure` |
| de-challenge1 | large, 3840×2160 | 227 | 8 | 0 | Warm-up thất bại: S6 `NumericalFailure` |

Các ca lỗi dừng ngay warm-up; sau đó Đế chạy công cụ trace không đo thời gian để lấy matches, inlier, H và ảnh trung gian. Không tính trace vào 5 lượt benchmark. Toàn bộ lần đánh giá có 39 cấu hình: 25 cấu hình hoàn tất đủ 5 lượt, 14 cấu hình dừng ở warm-up. Kết quả này chưa được kiểm chứng trên Colab T4 và không dùng làm số đo benchmark T4 chính thức.

Ở `de-challenge1` medium/large, mẫu số phép chiếu `q(x,y)=h20*x+h21*y+h22` đổi dấu giữa các góc ảnh B. Ví dụ medium: `q(0,0)=0.000677859`, `q(1919,1079)` xấp xỉ `-0.000421031`, theo H in trong trace. Vì vậy có đường `q=0` cắt miền ảnh; phép chiếu không tạo được canvas hữu hạn bao trùm ảnh. S6 phát hiện và trả `NumericalFailure` trước khi blend. S5 trả thành công với 8 inlier không bảo đảm H dùng được trên toàn ảnh. Ở small không có đổi dấu nên chương trình vẫn xuất ảnh, nhưng panorama lệch cho thấy việc xuất được ảnh chưa đủ để xác nhận ghép đúng. Không sửa điều kiện S6 để ép ca này chạy qua.

So với các cặp khó khác, `chuong-challenge1` vẫn ghép được ở cả ba cỡ; `tuan-challenge1` thiếu thông tin chung do tường trắng, chỉ còn 5/6/6 inlier. `thanh-challenge1` nhẹ hơn cặp Đế, có 123/94/39 inlier; small/medium xuất được panorama còn large bị giới hạn chiều canvas 10.000 px. Đế chọn cặp trần để phân tích H không phù hợp với ảnh, thay vì chỉ dùng ca vượt giới hạn canvas. Đề không yêu cầu challenge phải ghép thành công hoặc phải thất bại ở cả ba kích thước.

**Các tiêu chí cần xử lý trước khi nghiệm thu bộ ảnh.** Với `thanh-standard2`, diện tích chung ước tính từ H trên lưới 480×270 vào khoảng 58% ở cả ba cỡ, còn phép tìm dịch ngang của script cho 68%. Hai cách ước lượng khác nhau đều chưa hỗ trợ việc xác nhận đạt 30–50%. Với `de-challenge1`, script ước lượng 47% nhưng tương quan chỉ 0.12; H ở small cho khoảng 52% diện tích chung nhưng panorama đã lệch, nên không dùng số này làm bằng chứng đạt overlap. Cần xác minh bằng mốc chung trên ảnh và thông tin cách chụp; nếu không đạt phải báo lại cho cả Nhóm để cùng quyết định, không bỏ qua yêu cầu của đề. Các mục camera/cách chụp, độ nét và tên file cần xử lý theo bảng ở mục 5.3.

Bằng chứng cục bộ nằm trong `results/p5-t08-review/`: `raw-manifest.json` ghi tên gốc và SHA-256, `prepared-manifest.csv` ghi crop/resize và hash ảnh đầu vào, `review-results.json`/`.csv` ghi kết quả 39 cấu hình, `execution-environment.json` ghi cấu hình notebook và hash binary. Thư mục `runs/<mã cặp>/<kích thước>/` chứa command, exit code, stdout/stderr và ảnh đầu ra hoặc trace. Đây là dữ liệu thực nghiệm ngoài Git; các bảng trên là phần tổng hợp để review.

Khi có Colab T4, sau khi đặt cùng bộ ảnh đã chuẩn bị ở `results/p5-t08-review/prepared/`, chạy từ gốc repo để đối chiếu hai cặp ở cả ba cấu hình:

```bash
python scripts/build.py --target stitch --require-t4
```

```python
from pathlib import Path
import subprocess

review = Path("results/p5-t08-review")
for pair in ("thanh-standard2", "de-challenge1"):
    for size in ("small", "medium", "large"):
        output = review / "colab-t4" / pair / size
        output.mkdir(parents=True, exist_ok=True)
        result = subprocess.run([
            str(Path("build/stitch").resolve()),
            str(review / "prepared" / pair / f"{size}_left.jpg"),
            str(review / "prepared" / pair / f"{size}_right.jpg"),
            str(output / "panorama.png"), "--version", "0", "--runs", "5", "--debug",
        ], capture_output=True, text=True)
        (output / "run.stdout").write_text(result.stdout)
        (output / "run.stderr").write_text(result.stderr)
        print(pair, size, result.returncode)
```

Output mong đợi để đối chiếu: `thanh-standard2` xuất panorama và đủ 5 lượt ở mỗi cỡ; `de-challenge1` xuất ảnh small bị lệch, medium/large báo S6 `NumericalFailure`. Nếu kết quả khác, kiểm tra log thay vì điều chỉnh tham số để ép khớp CPU.

## 7. Chuẩn bị dataset

Với mỗi cặp được chọn, script chuẩn bị dataset phải bảo đảm:

1. Ảnh được xoay đúng theo thông tin EXIF orientation, vì stb bỏ qua EXIF và có thể đọc ra ảnh bị xoay sai.
2. Ảnh trái và ảnh phải của một cặp được cắt về 16:9 bằng cùng một khung cắt.
3. Ba kích thước 1280×720, 1920×1080, 3840×2160 được tạo từ cùng một ảnh đã cắt.
4. File đầu ra không còn EXIF và được đặt tên theo dạng `dataset/site1/small_left.jpg`, `dataset/site1/medium_right.jpg`, `dataset/challenge/large_left.jpg`.

Script: `scripts/prepare_dataset.py` (P0-T09). Script kiểm tra mọi cặp trước khi ghi file; nếu một cặp không đạt (thiếu file, không phải JPEG, hai ảnh khác kích thước sau khi xoay, ảnh dọc, khung cắt 16:9 nhỏ hơn 3840×2160) thì báo lỗi và không ghi gì. Resize bằng Lanczos, lưu JPEG quality 95, ghi thêm `dataset/manifest.csv` gồm file nguồn, khung cắt và SHA-256 của từng file đầu ra. Cần Python 3 với Pillow và numpy (có sẵn trên Colab).

```bash
python scripts/prepare_dataset.py --raw raw --out dataset \
    --pair site1=<mã cặp> --pair site2=<mã cặp> --pair site3=<mã cặp> --pair challenge=<mã cặp>
```

Ngày 16/10 script chạy được trên Colab với các cặp `tuan-standard1`, `tuan-standard2`, `tuan-challenge1` làm ảnh mẫu (khung cắt `0 777 8160 5367`, 18 ảnh đúng kích thước, không còn EXIF), và báo lỗi đúng với `chuong-standard1` (khung cắt 2560×1440). Đây chỉ là lần chạy thử, chưa phải lựa chọn cặp của P1-T05.

## 8. Kết quả cuối cùng

### 8.1 Bộ giữa kỳ đã chuẩn bị và upload

Cả Nhóm chốt bộ cặp dưới đây ngày 18/10, dựa trên thứ tự đề xuất và kết quả chạy thử V0 ở mục 6.

| Vai trò | Site | Địa điểm | Loại | Người chụp | Cặp chính | Cặp dự phòng |
|---|---|---|---|---|---|---|
| Site 1 | site1 | Nhà thờ (`nha-tho`), ngoài trời | chuẩn | Thành | thanh-standard1 | |
| Site 2 | site2 | Ẩn Coffee (`an-coffee`), trong nhà | chuẩn | Tuấn | tuan-standard2 | |
| Site 3 | site3 | Tiệm cà phê Mai An (`mai-an-coffee`), trong nhà | chuẩn | Đế | de-standard2 | |
| Cặp khó | challenge | Khu vực ký túc xá (`ky-tuc-xa`), ngoài trời | khó: cảnh đêm, chênh sáng, người và xe chuyển động | Chương | chuong-challenge1 | |

Tuấn tạo `dataset/` ngày 18/10 bằng `scripts/prepare_dataset.py` trên máy cá nhân (Python 3.11, Pillow 10.4.0, numpy 2.4.3), từ ảnh gốc tải lại từ Drive cùng ngày. SHA-256 của 8 ảnh gốc trùng với bản đã dùng ở mục 5.3 và ở lần chạy thử V0. Ảnh của Đế trên Drive vẫn có đuôi `.jpeg`, nên bản sao dùng để chạy được đổi tên thành `.jpg`, nội dung giữ nguyên. Đế cần đổi tên trên Drive thì lệnh dưới mới chạy lại được từ `raw/`:

```bash
python scripts/prepare_dataset.py --raw raw --out dataset \
    --pair site1=thanh-standard1 --pair site2=tuan-standard2 \
    --pair site3=de-standard2 --pair challenge=chuong-challenge1
```

| Site | Khung cắt 16:9 trên ảnh gốc (x0 y0 x1 y1) |
|---|---|
| site1 | `0 384 4096 2688` |
| site2 | `0 777 8160 5367` |
| site3 | `0 378 4032 2646` |
| challenge | `0 0 4096 2304` |

Script ghi ra 24 ảnh (4 cặp × 3 kích thước × 2 ảnh) và `dataset/manifest.csv`. Đã kiểm tra mọi ảnh có đúng kích thước 1280×720, 1920×1080 hoặc 3840×2160, là JPEG RGB, không còn EXIF, và SHA-256 trong manifest khớp với file.

Link `dataset/` trên Drive chung: https://drive.google.com/drive/folders/1HOvnly1k1QHOsV17qLzSAG4ihszNzCqO?usp=sharing. Ngày 18/10 đã tải lại thư mục này mà không đăng nhập, cả 25 file trùng SHA-256 với bản tạo ra ở trên.

### 8.2 Lựa chọn của Đế cho P5-T08

Ngày 02/11, Đế chốt hai cặp thay thế dưới đây; lý do và kết quả review ở mục 6.1. Site1 và site3 giữ cặp giữa kỳ để duy trì ba địa điểm chuẩn khác nhau. Đây là lựa chọn của Đế để báo lại cho cả Nhóm cùng quyết định; bộ `dataset/` và manifest trên Drive ở mục 8.1 chưa được thay bằng phương án này.

| Vai trò | Site | Địa điểm | Loại | Người chụp | Cặp chọn | Trạng thái |
|---|---|---|---|---|---|---|
| Site 1 | site1 | Nhà thờ (`nha-tho`), ngoài trời | chuẩn | Thành | thanh-standard1 | Giữ cặp giữa kỳ |
| Site 2 | site2 | Đường ngoài trời (`duong-ngoai-troi`) | chuẩn | Thành | thanh-standard2 | Đế chọn thay `tuan-standard2`; còn tiêu chí cần xử lý ở mục 5.3 và 6.1 |
| Site 3 | site3 | Tiệm cà phê Mai An (`mai-an-coffee`), trong nhà | chuẩn | Đế | de-standard2 | Giữ cặp giữa kỳ |
| Cặp khó | challenge | Tiệm cà phê Mai An (`mai-an-coffee`), trong nhà | khó: họa tiết lặp ở trần/lan can | Đế | de-challenge1 | Đế chọn thay `chuong-challenge1`; còn tiêu chí cần xử lý ở mục 5.3 và 6.1 |

Khung cắt của hai cặp thay thế đã dùng trong lượt đánh giá, áp dụng giống nhau cho ảnh trái/phải:

| Site | Cặp | Khung cắt (x0 y0 x1 y1) | Kích thước sau cắt |
|---|---|---|---|
| site2 | thanh-standard2 | `0 384 4096 2688` | 4096×2304 |
| challenge | de-challenge1 | `0 378 4032 2646` | 4032×2268 |

P5-T08 chưa hoàn tất: cần giải quyết các tiêu chí còn mở, báo lại cho cả Nhóm để cùng quyết định, chuẩn hóa tên nguồn, tạo và kiểm tra bộ `dataset/manifest.csv` theo mục 7 rồi cập nhật Drive. Việc ghi lựa chọn vào tài liệu không xác nhận các tiêu chí còn mở đã đạt và không xác nhận bộ ảnh mới đã upload.
