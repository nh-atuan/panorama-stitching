# Bảng công việc giữa kỳ

Quy tắc chung nằm trong [kế hoạch giữa kỳ](midterm-plan.md). Kế hoạch được lập cuốn chiếu: chỉ giai đoạn hiện tại có task chi tiết. Giai đoạn kế tiếp được lập khi giai đoạn trước hoàn thành. Hạn được ghi cho cả giai đoạn; mọi task trong giai đoạn phải xong trước hạn đó. Mốc cố định duy nhất là **23/10 (T6)**.

Mã task có dạng `P<số giai đoạn>-T<số thứ tự>` và được dùng trong tên nhánh và commit message, ví dụ nhánh `tuan/p0-t05-create-repo`.

Task được nhóm theo thành viên, theo thứ tự stage phụ trách. Mỗi người tự cập nhật cột **Trạng thái** và **Ghi chú / PR** của task mình. Trạng thái dùng một trong các giá trị: `Chưa làm`, `Đang làm`, `Chờ review`, `Xong`, `Bị chặn`.

## P0 - Chuẩn bị

Hạn của giai đoạn: **06/10 (T3)**.

<table>
  <thead>
    <tr>
      <th>Thành viên</th>
      <th>Mã</th>
      <th>Công việc</th>
      <th>Phụ thuộc</th>
      <th>Đầu ra / tiêu chí xong</th>
      <th>Trạng thái</th>
      <th>Ghi chú / PR</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td rowspan="4">Cả nhóm</td>
      <td>P0-T01</td>
      <td>Thống nhất số lượng ảnh/cặp mỗi người chụp và cách chọn ảnh (có bình chọn hay không)</td>
      <td></td>
      <td>Kết quả ghi vào <a href="dataset.md">dataset</a> mục 2 và mục 6</td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td>P0-T02</td>
      <td>Ghi địa điểm dự kiến vào <a href="dataset.md">dataset</a> mục 5.1</td>
      <td></td>
      <td>Đủ 4 dòng</td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td>P0-T03</td>
      <td>Chụp ảnh theo quy định, upload ảnh gốc, điền bảng ứng viên</td>
      <td>P0-T01, P0-T06</td>
      <td>Đủ số lượng đã thống nhất ở P0-T01</td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td>P0-T04</td>
      <td>Góp ý interface, xác nhận phần dữ liệu của stage mình, cùng thống nhất và merge</td>
      <td>P0-T14</td>
      <td>Interface đã merge vào <code>main</code></td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td rowspan="3">Tuấn</td>
      <td>P0-T05</td>
      <td>Tạo repo GitHub private, mời 3 thành viên, push lịch sử hiện có</td>
      <td></td>
      <td>Cả 4 người clone được repo</td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td>P0-T06</td>
      <td>Tạo Google Drive chung để nộp ảnh gốc, cập nhật link vào <a href="dataset.md">dataset</a> mục 4</td>
      <td></td>
      <td>Cả 4 người mở và upload được</td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td>P0-T07</td>
      <td>Chọn sơ bộ phương pháp, đầu vào/đầu ra cho S1</td>
      <td></td>
      <td><code>docs/stages/s1-preprocessing.md</code> có mục 1 và 2</td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td rowspan="3">Thành</td>
      <td>P0-T08</td>
      <td>Chọn sơ bộ phương pháp, đầu vào/đầu ra cho S2, S3</td>
      <td></td>
      <td><code>docs/stages/s2-detection.md</code>, <code>docs/stages/s3-description.md</code> có mục 1 và 2</td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td>P0-T09</td>
      <td>Viết script chuẩn bị dataset theo <a href="dataset.md">dataset</a> mục 7</td>
      <td></td>
      <td>Chạy được trên Colab với ảnh mẫu</td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td>P0-T10</td>
      <td>Kiểm tra mọi cặp ảnh ứng viên có đạt yêu cầu hay không, ghi kết quả</td>
      <td>P0-T03</td>
      <td><a href="dataset.md">dataset</a> mục 5.3 đã điền đầy đủ</td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td>Đế</td>
      <td>P0-T11</td>
      <td>Chọn sơ bộ phương pháp, đầu vào/đầu ra cho S4, S5; phương án cặp synthetic và metric sai số</td>
      <td>P0-T12</td>
      <td><code>docs/stages/s4-matching.md</code>, <code>docs/stages/s5-homography.md</code> có mục 1 và 2</td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td rowspan="3">Chương</td>
      <td>P0-T12</td>
      <td>Tìm starter notebook trên trang môn học; nếu không thấy thì hỏi Thầy/trợ giảng xem môn có phát starter không. Nếu có, xử lý theo mục 7 của kế hoạch</td>
      <td></td>
      <td>Đã xác định có hay không có starter; nếu có thì starter đã được đưa vào repo</td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td>P0-T13</td>
      <td>Chọn sơ bộ phương pháp, đầu vào/đầu ra cho S6</td>
      <td></td>
      <td><code>docs/stages/s6-warp-blend.md</code> có mục 1 và 2</td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td>P0-T14</td>
      <td>Soạn nháp <code>common.h</code> và <code>docs/interface.md</code> theo mục 8 của kế hoạch</td>
      <td>P0-T07, P0-T08, P0-T11, P0-T12, P0-T13</td>
      <td>Pull request mở để cả nhóm góp ý</td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
  </tbody>
</table>

## P1 - Cài đặt từng stage

Lập chi tiết khi P0 hoàn thành.

## P2 - Ghép và kiểm chứng V0

Lập chi tiết khi P1 hoàn thành.

## P3 - Đo và phân tích

Lập chi tiết khi P2 hoàn thành.

## P4 - Hoàn thiện và nộp

Lập chi tiết khi P3 hoàn thành. Hạn của giai đoạn: **23/10 (T6)**.

## Quyết định đã chốt

Ghi lại các quyết định cả Nhóm đã thống nhất trong quá trình làm.

| Ngày | Quyết định |
|---|---|
