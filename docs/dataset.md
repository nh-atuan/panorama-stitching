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
| de-challenge1 | Đế | mai-an-coffee | khó | | Không có EXIF | Không có EXIF | 4032×3024 |

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
| chuẩn | 4 | thanh-standard2 | Không có tiêu chí chưa đạt, 2 cần review; chồng lấn ước lượng 68% | |
| chuẩn | 5 | chuong-standard1 | Không có tiêu chí chưa đạt, 3 cần review; chồng lấn ước lượng 74% | |
| chuẩn | 6 | tuan-standard1 | Không có tiêu chí chưa đạt, 4 cần review; chồng lấn ước lượng 28% | |
| chuẩn | 7 | tuan-standard2 | Không có tiêu chí chưa đạt, 5 cần review; chồng lấn ước lượng 56% | |
| chuẩn | 8 | de-standard1 | 1 chưa đạt (tên file), 5 cần review; chồng lấn ước lượng 57% | |
| chuẩn | 9 | de-standard2 | 1 chưa đạt (tên file), 6 cần review; chồng lấn ước lượng 62% | |
| khó | 1 | thanh-challenge1 | Không có tiêu chí chưa đạt, 2 cần review; chồng lấn ước lượng 58% | |
| khó | 2 | chuong-challenge1 | Không có tiêu chí chưa đạt, 3 cần review; chồng lấn ước lượng 80% | |
| khó | 3 | tuan-challenge1 | Không có tiêu chí chưa đạt, 5 cần review; ít texture có chủ đích | |
| khó | 4 | de-challenge (thiếu số) | 1 chưa đạt (tên file), 6 cần review; chồng lấn ước lượng 47% | |

Thứ tự trên do script xếp: cặp có tiêu chí chưa đạt xếp cuối, sau đó ít tiêu chí chưa đạt hoặc chưa kiểm tra được hơn, chồng lấn ước lượng gần 40% hơn, độ nét cao hơn. Script không biết cặp nào chụp ở địa điểm nào, nên thứ tự này chưa tính yêu cầu 3 địa điểm khác nhau. Cột review để trống cho từng thành viên điền.

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

Cả Nhóm chốt bộ cặp dưới đây ngày 18/10, dựa trên thứ tự đề xuất và kết quả chạy thử V0 ở mục 6.

| Vai trò | Site | Địa điểm | Loại | Người chụp | Cặp chính | Cặp dự phòng |
|---|---|---|---|---|---|---|
| Site 1 | site1 | Nhà thờ (`nha-tho`), ngoài trời | chuẩn | Thành | thanh-standard1 | |
| Site 2 | site2 | Ẩn Coffee (`an-coffee`), trong nhà | chuẩn | Tuấn | tuan-standard2 | |
| Site 3 | site3 | Tiệm cà phê Mai An (`mai-an-coffee`), ngoài trời | chuẩn | Đế | de-standard2 | |
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
