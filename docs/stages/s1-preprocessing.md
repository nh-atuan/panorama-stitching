# S1 - Preprocessing

Người phụ trách: Tuấn. Cập nhật lần cuối: 07/10.

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

Các quy ước dưới đây là phần dữ liệu của S1 đóng góp cho `docs/interface.md` (P0-T14). Tên kiểu và tên trường cụ thể sẽ theo `common.h` sau khi chốt.

| Mục | Đầu vào | Đầu ra |
|---|---|---|
| Nội dung | Ảnh màu đọc bằng `stbi_load(..., 3)` | Ảnh xám đã làm mượt |
| Kiểu phần tử | `uint8_t` | `float` (32 bit) |
| Kênh | 3, RGB xen kẽ (`R G B R G B ...`) | 1 |
| Miền giá trị | [0, 255] | [0, 1] (giá trị xám chia cho 255) |
| Bố cục | Row-major, pixel `(x, y)` kênh `c` ở chỉ số `(y * width + x) * 3 + c` | Row-major, pixel `(x, y)` ở chỉ số `y * width + x` |
| Stride | Đề xuất: không padding, stride bằng `width * 3` byte | Đề xuất: không padding, stride bằng `width` phần tử |
| Kích thước | `width × height` | Giữ nguyên `width × height` |
| Tọa độ | Gốc ở góc trên trái, x tăng sang phải, y tăng xuống dưới | Như đầu vào |

Bộ nhớ đầu ra do bên gọi cấp phát. S1 dùng thêm một buffer `float` `width × height` cho kết quả lượt blur ngang; buffer này là dữ liệu nội bộ của S1.

Các tham số của S1 nằm trong struct cấu hình chung: độ lệch chuẩn `sigma` của Gaussian và bán kính kernel. Giá trị cụ thể sẽ chốt ở mục 3.

## 3. Tham số

Chưa chốt.

| Tham số | Giá trị | Đơn vị | Lý do chọn | Ảnh hưởng khi tăng/giảm |
|---|---|---|---|---|

## 4. Thuật toán chi tiết

Chưa viết.

## 5. Bằng chứng chất lượng

Chưa có.

## 6. Mức phù hợp với GPU và mapping V1 dự kiến

Chưa viết.

## 7. Kiểm thử

Chưa viết.

## 8. Trường hợp biên và rủi ro

Chưa viết.

## 9. Nguồn tham khảo

| Nguồn | Ngày truy cập | Dùng cho phần nào |
|---|---|---|
| [Đề cuối kỳ CSC14120](../specs/CSC14120_2026_Final%20Project.md), mục 2.1 và 2.2 | 07/10 | Mục 1 |

## 10. Lịch sử thay đổi tham số

| Ngày | Thay đổi | Lý do |
|---|---|---|
