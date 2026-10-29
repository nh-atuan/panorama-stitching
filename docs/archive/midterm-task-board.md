<!-- Authors: Nguyen Ho Anh Tuan (23120185). External source: none. -->

# Bảng công việc giữa kỳ (P0–P4)

Tài liệu lưu trữ bảng công việc của giai đoạn giữa kỳ (từ P0 đến P4, hạn hoàn thành **23/10 (Thứ 6)**). Quy tắc chung của giai đoạn này nằm trong [kế hoạch giữa kỳ](midterm-plan.md). Bảng công việc cho các giai đoạn cuối kỳ nằm trong [bảng công việc](../task-board.md).

Mã task có dạng `P<số giai đoạn>-T<số thứ tự>` và được dùng làm scope trong commit message, ví dụ `feat(p1-t14): add RANSAC hypothesis loop` trên nhánh giai đoạn `de/p1`.

## P0 - Chuẩn bị

Hạn của giai đoạn: **06/10 (Thứ 3)**.

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
      <td>Thống nhất cách chọn ảnh (có bình chọn hay không)</td>
      <td></td>
      <td>Kết quả ghi vào <a href="../dataset.md">dataset</a> mục 6</td>
      <td>Xong</td>
      <td>Cách chọn ghi ở dataset mục 6: script kiểm tra và xếp thứ tự, từng thành viên review, cả Nhóm chốt. Bộ cặp được chốt theo cách này ngày 18/10.</td>
    </tr>
    <tr>
      <td>P0-T02</td>
      <td>Ghi địa điểm dự kiến vào <a href="../dataset.md">dataset</a> mục 5.1</td>
      <td></td>
      <td>Đủ 4 dòng</td>
      <td>Xong</td>
      <td>Đã có dòng của cả 4 người. Thành chụp ở 5 địa điểm, mỗi địa điểm một dòng (điền ngày 20/10).</td>
    </tr>
    <tr>
      <td>P0-T03</td>
      <td>Chụp ảnh theo quy định, upload ảnh gốc, điền bảng ứng viên</td>
      <td>P0-T06</td>
      <td>Đủ số lượng theo <a href="../dataset.md">dataset</a> mục 2</td>
      <td>Xong</td>
      <td>Cả 4 người đã upload ảnh gốc. Nhóm miễn cặp chuẩn thứ hai cho Chương (Quyết định đã chốt 18/10). Bảng 5.2 đã có dòng của Thành, Đế (lấy từ EXIF); site slug của Thành đã điền ngày 20/10.</td>
    </tr>
    <tr>
      <td>P0-T04</td>
      <td>Góp ý interface, xác nhận phần dữ liệu của stage mình, cùng thống nhất và merge</td>
      <td>P0-T14</td>
      <td>Interface đã merge vào <code>main</code></td>
      <td>Xong</td>
      <td><code>common.h</code> và <code>docs/interface.md</code> đã merge vào <code>main</code> qua PR #2. Sáu stage V0 và pipeline (PR #10) cài theo các quy ước này; mục 10 của interface bổ sung API pipeline.</td>
    </tr>
    <tr>
      <td rowspan="3">Tuấn</td>
      <td>P0-T05</td>
      <td>Tạo repo GitHub private, mời 3 thành viên, push lịch sử hiện có</td>
      <td></td>
      <td>Cả 4 người clone được repo</td>
      <td>Xong</td>
      <td></td>
    </tr>
    <tr>
      <td>P0-T06</td>
      <td>Tạo Google Drive chung để nộp ảnh gốc, cập nhật link vào <a href="../dataset.md">dataset</a> mục 4</td>
      <td></td>
      <td>Cả 4 người mở và upload được</td>
      <td>Xong</td>
      <td></td>
    </tr>
    <tr>
      <td>P0-T07</td>
      <td>Chọn sơ bộ phương pháp, đầu vào/đầu ra cho S1</td>
      <td></td>
      <td><code>docs/stages/s1-preprocessing.md</code> có mục 1 và 2 theo <a href="midterm-plan.md#6-mẫu-tài-liệu-thiết-kế-stage">mẫu ở mục 6 của kế hoạch giữa kỳ</a></td>
      <td>Xong</td>
      <td></td>
    </tr>
    <tr>
      <td rowspan="3">Thành</td>
      <td>P0-T08</td>
      <td>Chọn sơ bộ phương pháp, đầu vào/đầu ra cho S2, S3</td>
      <td></td>
      <td><code>docs/stages/s2-detection.md</code>, <code>docs/stages/s3-description.md</code> đều có mục 1 và 2 theo <a href="midterm-plan.md#6-mẫu-tài-liệu-thiết-kế-stage">mẫu ở mục 6 của kế hoạch giữa kỳ</a></td>
      <td>Xong</td>
      <td>Tuấn làm thay Thành. Mục 1, 2 của tài liệu S2 (FAST-9, score V, NMS 3×3, top-N) và S3 (BRIEF 256 bit không xoay, patch 31×31, pattern G II seed 16). Nhóm đồng ý việc làm thay và Thành xác nhận phương pháp, tham số S2, S3 ngày 18/10.</td>
    </tr>
    <tr>
      <td>P0-T09</td>
      <td>Viết script chuẩn bị dataset theo <a href="../dataset.md">dataset</a> mục 7</td>
      <td></td>
      <td>Chạy được trên Colab với ảnh mẫu</td>
      <td>Xong</td>
      <td>Tuấn làm thay Thành. scripts/prepare_dataset.py và test tests/test_dataset_scripts.py, merge PR #9. Colab T4 18/10: 9 test đạt. Nhóm đồng ý việc làm thay và Thành xác nhận phương pháp, tham số S2, S3 ngày 18/10.</td>
    </tr>
    <tr>
      <td>P0-T10</td>
      <td>Kiểm tra mọi cặp ảnh ứng viên có đạt yêu cầu hay không, ghi kết quả</td>
      <td>P0-T03</td>
      <td><a href="../dataset.md">dataset</a> mục 5.3 đã điền đầy đủ</td>
      <td>Xong</td>
      <td>Tuấn làm thay Thành. scripts/check_pairs.py chạy trên toàn bộ Drive ngày 18/10, kết quả ở dataset mục 5.3, thứ tự đề xuất và kết quả chạy thử V0 ở mục 6. Nhóm đồng ý việc làm thay và Thành xác nhận phương pháp, tham số S2, S3 ngày 18/10.</td>
    </tr>
    <tr>
      <td>Đế</td>
      <td>P0-T11</td>
      <td>Chọn sơ bộ phương pháp, đầu vào/đầu ra cho S4, S5; tự chuẩn bị phương án cặp synthetic và metric sai số homography</td>
      <td></td>
      <td><code>docs/stages/s4-matching.md</code>, <code>docs/stages/s5-homography.md</code> đều có mục 1 và 2 theo <a href="midterm-plan.md#6-mẫu-tài-liệu-thiết-kế-stage">mẫu ở mục 6 của kế hoạch giữa kỳ</a></td>
      <td>Xong</td>
      <td>Mục 1, 2 của tài liệu S4, S5 đã có. S4: exact 2-NN Hamming, ratio 0.80, cross-check=false. S5: uniform RANSAC, normalized DLT double, MSAC, adaptive termination, refit. Phương án cặp synthetic và metric ở mục 5.2, 5.3 tài liệu S5.</td>
    </tr>
    <tr>
      <td rowspan="3">Chương</td>
      <td>P0-T12</td>
      <td>Tự tạo và setup khung <code>src/</code> theo cây thư mục của đề giữa kỳ (<code>common.h</code>, <code>cuda_utils.cuh</code>, <code>versions.h</code>, <code>main.cu</code>, <code>stb_impl.cpp</code>), nhận đúng tham số dòng lệnh của đề cuối kỳ</td>
      <td>P0-T05</td>
      <td>Khung đã merge vào <code>main</code>, build được bằng <code>nvcc -arch=sm_75</code> trên Colab T4</td>
      <td>Xong</td>
      <td>Đã merge PR #2. Ngày 18/10 <code>main</code> build được bằng <code>nvcc -arch=sm_75</code> trên Colab T4 (CUDA 13.0) khi nối pipeline V0 (PR #10).</td>
    </tr>
    <tr>
      <td>P0-T13</td>
      <td>Chọn sơ bộ phương pháp, đầu vào/đầu ra cho S6</td>
      <td></td>
      <td><code>docs/stages/s6-warp-blend.md</code> có mục 1 và 2 theo <a href="midterm-plan.md#6-mẫu-tài-liệu-thiết-kế-stage">mẫu ở mục 6 của kế hoạch giữa kỳ</a></td>
      <td>Xong</td>
      <td>Đã viết tài liệu S6, phản biện hai đề xuất có nguồn; chọn sơ bộ inverse warp + bilinear tự tính + feather, xác định input/output và canvas/offset. Chưa cài thuật toán S6.</td>
    </tr>
    <tr>
      <td>P0-T14</td>
      <td>Soạn nháp <code>common.h</code> và <code>docs/interface.md</code> theo mục 7 của kế hoạch</td>
      <td>P0-T07, P0-T08, P0-T11, P0-T12, P0-T13</td>
      <td>Pull request mở để cả nhóm góp ý</td>
      <td>Xong</td>
      <td>Đã merge vào <code>main</code> cùng PR #2 (commit ac46b96). Sáu stage V0 và pipeline đã cài theo bản này. Ngày 18/10 Tuấn cập nhật phần mở đầu, mục 6 và mục 9 cho khớp code, merge PR #12.</td>
    </tr>
  </tbody>
</table>

## P1 - Cài đặt từng stage

Hạn của giai đoạn: **13/10 (Thứ 3)**.

Mỗi stage được cài đặt và kiểm thử độc lập bằng dữ liệu tự tạo theo mục 4 của [kế hoạch](midterm-plan.md), nên task của các stage chỉ phụ thuộc vào P0. Việc nối 6 stage thành pipeline hoàn chỉnh thuộc P2. Mục 6 (mapping GPU) của tài liệu thiết kế stage được viết ở P3, sau khi có số đo.

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
      <td rowspan="2">Cả nhóm</td>
      <td>P1-T01</td>
      <td>Chốt ngưỡng sai số homography trên cặp synthetic</td>
      <td>P0-T11</td>
      <td>Ngưỡng ghi vào mục "Quyết định đã chốt"</td>
      <td>Xong</td>
      <td>Cả Nhóm chốt ngưỡng ngày 18/10 (mục "Quyết định đã chốt"). Sai số V0 trên 6 cặp synthetic (mục 5.5 tài liệu S5, Colab T4 18/10): RMSE lớn nhất 0.100 px, Max lớn nhất 0.209 px, đều đạt ngưỡng.</td>
    </tr>
    <tr>
      <td>P1-T02</td>
      <td>Mỗi người mở pull request nhánh <code>&lt;tên&gt;/p1</code> và merge vào <code>main</code></td>
      <td>Các task code của mình trong P1</td>
      <td><code>main</code> build được bằng <code>nvcc -arch=sm_75</code> trên Colab T4 và có đủ 6 file <code>v0_*.cpp</code></td>
      <td>Xong</td>
      <td>Đã merge chuong/p1 (PR #4), de/p1 (PR #7), phần của Tuấn (PR #6) và S2, S3 (PR #8). <code>main</code> có đủ 6 file <code>v0_*.cpp</code>, build bằng <code>nvcc -arch=sm_75</code> trên Colab T4 ngày 18/10.</td>
    </tr>
    <tr>
      <td rowspan="4">Tuấn</td>
      <td>P1-T03</td>
      <td>Chốt tham số và viết thuật toán chi tiết cho S1</td>
      <td>P0-T04</td>
      <td><code>docs/stages/s1-preprocessing.md</code> có mục 3, 4 và 8</td>
      <td>Xong</td>
      <td></td>
    </tr>
    <tr>
      <td>P1-T04</td>
      <td>Cài đặt và kiểm thử <code>v0_preprocess.cpp</code></td>
      <td>P0-T12, P1-T03</td>
      <td>Đạt <a href="midterm-plan.md#14-tiêu-chí-hoàn-thành-một-task">mục 14 của kế hoạch</a>; mục 5 và 7 của tài liệu S1 có kết quả chạy trên Colab T4; báo lỗi khi đầu vào không hợp lệ theo quy ước trong <code>docs/interface.md</code></td>
      <td>Xong</td>
      <td>Mục 5 tài liệu S1 có số liệu ảnh xám trước và sau blur trên 4 cặp dataset ở 3 kích thước (Colab T4 18/10); mục 7 có kết quả T4 ngày 13/10, 16/10, 18/10 (1758 assertions, cả bản sanitizer).</td>
    </tr>
    <tr>
      <td>P1-T05</td>
      <td>Chọn cặp theo cách đã chốt ở P0-T01, chạy script chuẩn bị dataset, upload <code>dataset/</code> lên Drive chung</td>
      <td>P0-T01, P0-T09, P0-T10</td>
      <td><a href="../dataset.md">dataset</a> mục 8 đã điền; <code>dataset/</code> trên Drive có đủ 3 site và cặp khó, mỗi cặp đủ 3 kích thước</td>
      <td>Xong</td>
      <td>Cả Nhóm chốt bộ cặp ngày 18/10 (dataset mục 8). <code>dataset/</code> (24 ảnh, manifest khớp SHA-256) đã upload lên Drive chung. Tên địa điểm site 1 ở mục 8 đã điền ngày 20/10.</td>
    </tr>
    <tr>
      <td>P1-T06</td>
      <td>Viết mục 3.2 và 3.6 của báo cáo giữa kỳ vào <code>docs/report/</code></td>
      <td>P1-T05</td>
      <td><code>docs/report/3.2-problem-understanding.md</code> và <code>docs/report/3.6-dataset.md</code></td>
      <td>Xong</td>
      <td>Đã viết ở <code>docs/report/3.2-problem-understanding.md</code> và <code>docs/report/3.6-dataset.md</code>. Tên địa điểm site 1 trong 3.6 đã bổ sung ngày 20/10.</td>
    </tr>
    <tr>
      <td rowspan="4">Thành</td>
      <td>P1-T07</td>
      <td>Chốt tham số và viết thuật toán chi tiết cho S2</td>
      <td>P0-T04, P0-T08</td>
      <td><code>docs/stages/s2-detection.md</code> có mục 3, 4 và 8</td>
      <td>Xong</td>
      <td>Tuấn làm thay Thành. Mục 3, 4, 8 của tài liệu S2: t = 0.05, max_keypoints = 2000, border 15, tie-break raster. Nhóm đồng ý việc làm thay và Thành xác nhận phương pháp, tham số S2, S3 ngày 18/10.</td>
    </tr>
    <tr>
      <td>P1-T08</td>
      <td>Cài đặt và kiểm thử <code>v0_detect.cpp</code></td>
      <td>P0-T12, P1-T07</td>
      <td>Đạt <a href="midterm-plan.md#14-tiêu-chí-hoàn-thành-một-task">mục 14 của kế hoạch</a>; mục 5 và 7 của tài liệu S2 có kết quả chạy trên Colab T4; báo lỗi khi đầu vào không hợp lệ theo quy ước trong <code>docs/interface.md</code></td>
      <td>Xong</td>
      <td>Tuấn làm thay Thành, merge PR #8. Colab T4 18/10: <code>PASS: 19524 assertions</code>, đạt cả với ASan/UBSan; S2 chạy trong pipeline V0 trên cả 4 cặp dataset. Nhóm đồng ý việc làm thay và Thành xác nhận phương pháp, tham số S2, S3 ngày 18/10.</td>
    </tr>
    <tr>
      <td>P1-T09</td>
      <td>Chốt tham số và viết thuật toán chi tiết cho S3</td>
      <td>P0-T04, P0-T08</td>
      <td><code>docs/stages/s3-description.md</code> có mục 3, 4 và 8</td>
      <td>Xong</td>
      <td>Tuấn làm thay Thành. Mục 3, 4, 8 của tài liệu S3: làm mượt Gaussian σ = 2, r = 4, pattern sinh bằng tests/tool_gen_brief_pattern.py, compact keypoint ở mép. Nhóm đồng ý việc làm thay và Thành xác nhận phương pháp, tham số S2, S3 ngày 18/10.</td>
    </tr>
    <tr>
      <td>P1-T10</td>
      <td>Cài đặt và kiểm thử <code>v0_describe.cpp</code></td>
      <td>P0-T12, P1-T09</td>
      <td>Đạt <a href="midterm-plan.md#14-tiêu-chí-hoàn-thành-một-task">mục 14 của kế hoạch</a>; mục 5 và 7 của tài liệu S3 có kết quả chạy trên Colab T4; báo lỗi khi đầu vào không hợp lệ theo quy ước trong <code>docs/interface.md</code></td>
      <td>Xong</td>
      <td>Tuấn làm thay Thành, merge PR #8. Colab T4 18/10: <code>PASS: 2300 assertions</code>, đạt cả với ASan/UBSan. Nhóm đồng ý việc làm thay và Thành xác nhận phương pháp, tham số S2, S3 ngày 18/10.</td>
    </tr>
    <tr>
      <td rowspan="5">Đế</td>
      <td>P1-T11</td>
      <td>Chốt tham số và viết thuật toán chi tiết cho S4</td>
      <td>P0-T04, P0-T11</td>
      <td><code>docs/stages/s4-matching.md</code> có mục 3, 4 và 8</td>
      <td>Xong</td>
      <td>Mục 1, 3, 4, 8 tài liệu S4 đã có: exact 2-NN Hamming 256-bit, ratio 0.80, cross-check=false, so sánh ratio nguyên 4/5, thứ tự tất định theo indexA.</td>
    </tr>
    <tr>
      <td>P1-T12</td>
      <td>Cài đặt và kiểm thử <code>v0_match.cpp</code></td>
      <td>P0-T12, P1-T11</td>
      <td>Đạt <a href="midterm-plan.md#14-tiêu-chí-hoàn-thành-một-task">mục 14 của kế hoạch</a>; mục 5 và 7 của tài liệu S4 có kết quả chạy trên Colab T4; báo lỗi khi không đủ match theo quy ước trong <code>docs/interface.md</code></td>
      <td>Xong</td>
      <td>Đã merge PR #7. Tuấn ghi kết quả Colab T4 18/10 (66 checks, cả bản sanitizer) và số match trên 4 cặp dataset vào mục 5, 7 tài liệu S4, merge PR #11.</td>
    </tr>
    <tr>
      <td>P1-T13</td>
      <td>Chốt tham số và viết thuật toán chi tiết cho S5, gồm seed RANSAC và cách xử lý khi không đủ match hoặc homography suy biến</td>
      <td>P0-T04, P0-T11</td>
      <td><code>docs/stages/s5-homography.md</code> có mục 3, 4 và 8</td>
      <td>Xong</td>
      <td>Mục 3, 4, 8 tài liệu S5 đã có: seed 16, cap 2000, uniform deterministic sampling, normalized DLT double, MSAC, confidence 0.99, tau 2/3/6 px, tối đa hai all-inlier refit. Tolerance chung chốt cùng P1-T01.</td>
    </tr>
    <tr>
      <td>P1-T14</td>
      <td>Cài đặt và kiểm thử <code>v0_homography.cpp</code></td>
      <td>P0-T12, P1-T13</td>
      <td>Đạt <a href="midterm-plan.md#14-tiêu-chí-hoàn-thành-một-task">mục 14 của kế hoạch</a>; mục 5 và 7 của tài liệu S5 có kết quả chạy trên Colab T4; seed RANSAC lấy từ cấu hình và được in ra; báo lỗi khi homography suy biến theo quy ước trong <code>docs/interface.md</code></td>
      <td>Xong</td>
      <td>Đã merge PR #7. Tuấn ghi kết quả Colab T4 18/10 (7 suites, 5673 checks, cả bản sanitizer) và sai số synthetic vào mục 5, 7 tài liệu S5, merge PR #11.</td>
    </tr>
    <tr>
      <td>P1-T15</td>
      <td>Tạo cặp synthetic từ một homography biết trước và công cụ tính sai số homography so với ground truth</td>
      <td>P0-T11</td>
      <td>Tạo được cặp synthetic và in được sai số; cách tạo cặp và metric ghi trong mục 5 của tài liệu S5</td>
      <td>Xong</td>
      <td>Tuấn làm thay Đế, merge PR #11. <code>scripts/make_synthetic_pair.py</code>, <code>scripts/homography_error.py</code>, <code>scripts/homography_common.py</code>, test 18 case. Colab T4 18/10: V0 cho RMSE lớn nhất 0.100 px, Max lớn nhất 0.209 px trên 6 cặp (mục 5.5 tài liệu S5).</td>
    </tr>
    <tr>
      <td rowspan="3">Chương</td>
      <td>P1-T16</td>
      <td>Chốt tham số và viết thuật toán chi tiết cho S6, gồm cách tính kích thước khung ảnh đầu ra và độ lệch gốc tọa độ</td>
      <td>P0-T04, P0-T13</td>
      <td><code>docs/stages/s6-warp-blend.md</code> có mục 3, 4 và 8</td>
      <td>Xong</td>
      <td>Đã hoàn thành mục 3, 4 và 8 trong docs/stages/s6-warp-blend.md: bảng tham số/tolerances, thuật toán bbox/offset và inverse bilinear, bảng trường hợp biên/mã lỗi. Phần composite và ownership đã cập nhật sang average 50/50, S6 cấp phát output theo yêu cầu coding mới 13/10.</td>
    </tr>
    <tr>
      <td>P1-T17</td>
      <td>Cài đặt và kiểm thử <code>v0_warp_blend.cpp</code></td>
      <td>P0-T12, P1-T16</td>
      <td>Đạt <a href="midterm-plan.md#14-tiêu-chí-hoàn-thành-một-task">mục 14 của kế hoạch</a>; mục 5 và 7 của tài liệu S6 có kết quả chạy trên Colab T4; báo lỗi khi đầu vào không hợp lệ theo quy ước trong <code>docs/interface.md</code></td>
      <td>Xong</td>
      <td>Đã merge PR #4. Tuấn ghi kết quả Colab T4 18/10 (194 assertions, cả bản sanitizer) và canvas của 12 panorama trên dataset vào mục 5, 7 tài liệu S6, merge PR #13.</td>
    </tr>
    <tr>
      <td>P1-T18</td>
      <td>Cài đặt khung chạy trong <code>main.cu</code>: đo thời gian từng stage và tổng theo <a href="midterm-plan.md#12-quy-định-đo-thời-gian-v0">mục 12 của kế hoạch</a>, warm-up, <code>--runs</code>, in dòng CSV, cờ <code>--debug</code>, báo lỗi cấp chương trình (thiếu file, ảnh không đọc được, version không tồn tại, <code>--runs</code> không dương)</td>
      <td>P0-T04, P0-T12</td>
      <td>Merge vào <code>main</code> qua pull request file dùng chung; chạy được trên Colab T4 với các stage stub</td>
      <td>Xong</td>
      <td>Đã merge PR #3. Ngày 18/10 <code>main.cu</code> được nối 6 stage thật (PR #10) và chạy được trên Colab T4: warm-up, <code>--runs</code>, CSV 8 cột, average/minimum, báo lỗi cấp chương trình.</td>
    </tr>
  </tbody>
</table>

## P2 - Ghép và kiểm chứng V0

Hạn của giai đoạn: **18/10 (Chủ nhật)**.

Tuấn làm toàn bộ P2. Bảng dưới ghi lại các task đã làm.

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
      <td rowspan="2">Tuấn</td>
      <td>P2-T01</td>
      <td>Nối 6 stage V0 thành pipeline: <code>v0_config</code>, <code>v0_pipeline</code>, <code>main.cu</code> gọi stage thật, <code>versions.h</code>, công cụ xem kết quả từng stage</td>
      <td>P1-T02</td>
      <td><code>stitch</code> chạy đủ 6 stage trên Colab T4, ra panorama và CSV; test đạt trên Colab T4; mục 10 của <a href="../interface.md">interface</a> mô tả API pipeline</td>
      <td>Xong</td>
      <td>Nhánh tuan/shared-v0-pipeline, merge PR #10. Colab T4 (CUDA 13.0) ngày 18/10: build bằng <code>nvcc -arch=sm_75</code>, mọi test đạt, <code>stitch</code> chạy được 3 kích thước của <code>tuan-standard2</code>. Thêm <code>tests/test_v0_config.cpp</code>, <code>tests/test_v0_pipeline.cpp</code>, <code>tests/tool_pipeline_trace.cpp</code>.</td>
    </tr>
    <tr>
      <td>P2-T02</td>
      <td>Chạy thử V0 trên mọi cặp chính ở 3 kích thước để hỗ trợ chọn dataset</td>
      <td>P2-T01, P0-T10</td>
      <td>Kết quả ghi vào <a href="../dataset.md">dataset</a> mục 6</td>
      <td>Xong</td>
      <td>Chạy 13 cặp chính ngày 18/10, số inlier và lỗi của từng kích thước ở dataset mục 6. Cả Nhóm dựa vào kết quả này để chốt dataset.</td>
    </tr>
  </tbody>
</table>

## P3 - Đo và phân tích

Hạn của giai đoạn: **21/10 (Thứ 4)**.

P3 chỉ gồm task mới. Phần còn lại của P0, P1 được làm xong trước khi P3 bắt đầu; các task đang chờ merge pull request vẫn giữ ghi chú ở bảng P1. Khi kết thúc P3, mọi task từ P0 đến P3 đều ở trạng thái `Xong`; P4 chỉ còn ghép các mục báo cáo trong `docs/report/` vào notebook, chạy lại và nộp.

Mục 6 của tài liệu thiết kế stage và các phần phân tích cần số đo của P3-T05. Trong lúc chờ, phần mapping không phụ thuộc số đo có thể viết trước.

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
      <td>Cả nhóm</td>
      <td>P3-T01</td>
      <td>Chốt các stage đưa lên GPU và phân công V1-V3 dựa trên số đo</td>
      <td>P3-T05</td>
      <td>Quyết định ghi vào mục "Quyết định đã chốt"; bảng phân công ở mục 2 của <a href="midterm-plan.md">kế hoạch</a> được cập nhật nếu có thay đổi</td>
      <td>Xong</td>
      <td>Quyết định ngày 21/10 ghi ở mục "Quyết định đã chốt". Phân công V1-V3 giữ như mục 2 của kế hoạch.</td>
    </tr>
    <tr>
      <td rowspan="2">Tuấn</td>
      <td>P3-T02</td>
      <td>Viết mục 6 của tài liệu S1; viết mục 3.1 và phần S1 của mục 3.3 của báo cáo giữa kỳ vào <code>docs/report/</code>; thêm nguồn của S1 vào <code>docs/report/references.md</code></td>
      <td>P3-T05</td>
      <td><code>docs/stages/s1-preprocessing.md</code> có mục 6; <code>docs/report/3.1-team-plan.md</code>, <code>docs/report/3.3-s1-preprocessing.md</code>; <code>references.md</code> có phần S1</td>
      <td>Xong</td>
      <td>Mục 6 tài liệu S1 dựa trên benchmark V0 ngày 20/10; <code>docs/report/3.1-team-plan.md</code>, <code>docs/report/3.3-s1-preprocessing.md</code>; phần S1 trong <code>references.md</code>.</td>
    </tr>
    <tr>
      <td>P3-T03</td>
      <td>Viết mục 3.7 (kế hoạch GPU) của báo cáo giữa kỳ vào <code>docs/report/</code>, tổng hợp từ mục 6 của 6 tài liệu stage</td>
      <td>P3-T01, P3-T02, P3-T06, P3-T08, P3-T10</td>
      <td><code>docs/report/3.7-gpu-plan.md</code></td>
      <td>Xong</td>
      <td><code>docs/report/3.7-gpu-plan.md</code> tổng hợp mapping V1 của 6 stage, ba ý tưởng tối ưu cho S2, S4, S6, rủi ro và cách kiểm chứng V1.</td>
    </tr>
    <tr>
      <td rowspan="4">Thành</td>
      <td>P3-T04</td>
      <td>Viết script benchmark V0 <code>scripts/run_benchmark.py</code> và test</td>
      <td>P2-T01</td>
      <td>Script chạy <code>stitch</code> cho 3 site × 3 kích thước theo <a href="midterm-plan.md#12-quy-định-đo-thời-gian-v0">mục 12 của kế hoạch</a> (warm-up, <code>--runs 5</code>), in tên GPU và CPU, gom CSV, xuất bảng trung bình và nhỏ nhất của từng stage; test đạt trên Colab</td>
      <td>Xong</td>
      <td>Nhánh thanh/p3, đã merge PR #14 ngày 21/10. Colab T4 20/10: build bằng <code>nvcc -arch=sm_75</code>, <code>tests/test_run_benchmark.py</code> 10 test đạt, test notebook 16 test đạt; chạy đủ 9 cấu hình với <code>--runs 5</code>. Giao diện <code>--stitch --dataset --runs --out</code>, ghi <code>&lt;out&gt;/&lt;site&gt;/&lt;size&gt;.csv</code> đúng layout adapter của notebook, kèm <code>summary.csv</code>, <code>summary.md</code>, <code>environment.json</code>.</td>
    </tr>
    <tr>
      <td>P3-T05</td>
      <td>Chạy benchmark chính thức, xác định hot stage và tính giới hạn Amdahl</td>
      <td>P3-T04</td>
      <td>Bảng timing ở 3 kích thước và biểu đồ theo stage sinh từ CSV, đo trong cùng một phiên Colab T4; nêu hot stage và cách nó thay đổi theo độ phân giải; <code>p</code> và <code>1/(1-p)</code> tính bằng code</td>
      <td>Xong</td>
      <td>Nhánh thanh/p3, đã merge PR #14 ngày 21/10. Số đo trong một phiên Colab T4 ngày 20/10 (Tesla T4, <code>--runs 5</code>, 9 cấu hình). <code>scripts/plot_benchmark.py</code> sinh từ <code>summary.csv</code> hai biểu đồ cột chồng theo stage (ms và % của Total), bảng hot stage, <code>p</code> và <code>1/(1-p)</code>; 8 test đạt trên Colab T4. Hot stage: S4 ở small và medium cả 3 site (trung bình 56,2% và 40,0%); ở large là S2 với site1, S6 với site2 và site3. Lần Run all cuối của notebook đo lại nên số trong lời văn báo cáo phải đối chiếu với output đó.</td>
    </tr>
    <tr>
      <td>P3-T06</td>
      <td>Viết mục 6 của tài liệu S2, S3; viết phần S2, S3 của mục 3.3 của báo cáo giữa kỳ vào <code>docs/report/</code></td>
      <td>P3-T05</td>
      <td><code>docs/stages/s2-detection.md</code>, <code>docs/stages/s3-description.md</code> có mục 6; <code>docs/report/3.3-s2-detection.md</code>, <code>docs/report/3.3-s3-description.md</code></td>
      <td>Xong</td>
      <td>Mục 6 tài liệu S2, S3 dựa trên benchmark V0 ngày 20/10; <code>docs/report/3.3-s2-detection.md</code>, <code>docs/report/3.3-s3-description.md</code>.</td>
    </tr>
    <tr>
      <td>P3-T07</td>
      <td>Viết phần timing, hot stage và Amdahl của mục 3.5 của báo cáo giữa kỳ vào <code>docs/report/</code></td>
      <td>P3-T05</td>
      <td><code>docs/report/3.5-timing.md</code></td>
      <td>Xong</td>
      <td><code>docs/report/3.5-timing.md</code>: bảng timing 9 cấu hình, hot stage theo độ phân giải, p và 1/(1-p) cho S2 + S4 + S6.</td>
    </tr>
    <tr>
      <td>Đế</td>
      <td>P3-T08</td>
      <td>Viết mục 6 của tài liệu S4, S5; viết phần S4, S5 của mục 3.3 và phần correctness của mục 3.5 của báo cáo giữa kỳ vào <code>docs/report/</code></td>
      <td>P3-T05</td>
      <td><code>docs/stages/s4-matching.md</code>, <code>docs/stages/s5-homography.md</code> có mục 6; <code>docs/report/3.3-s4-matching.md</code>, <code>docs/report/3.3-s5-homography.md</code>, <code>docs/report/3.5-correctness.md</code></td>
      <td>Xong</td>
      <td>Đế hoàn thiện bản nháp ngày 21/10: mục 6 S4/S5 và ba file báo cáo 3.3-s4, 3.3-s5, 3.5-correctness. Mapping dựa trên benchmark V0 ngày 20/10; correctness bao gồm S1–S6, tích hợp và sáu cặp synthetic đã ghi nhận trên T4. Giữ nguyên code và tham số V0. Đủ đầu ra theo task và tiêu chí báo cáo tại mục 14 kế hoạch; chưa ghép notebook. P3-T05 vẫn chờ review; P3-T01 là quyết định chung chưa hoàn thành.</td>
    </tr>
    <tr>
      <td rowspan="2">Chương</td>
      <td>P3-T09</td>
      <td>Dựng khung code của <code>Group16_Midterm.ipynb</code> theo <a href="midterm-plan.md#13-quy-định-notebook-báo-cáo">mục 13 của kế hoạch</a>: <code>nvidia-smi</code>, lấy <code>src/</code> từ Drive, build, chạy test, cặp synthetic, benchmark, panorama</td>
      <td>P3-T04</td>
      <td>Run all thành công trên một phiên Colab T4 mới; không dùng <code>%%writefile</code>; notebook commit không kèm output</td>
      <td>Xong</td>
      <td>Notebook lấy <code>src/</code> upload qua panel Files và <code>Group16_support.zip</code> (dataset, <code>scripts/</code>, <code>tests/</code>, ảnh nguồn synthetic) từ Drive chung; benchmark gọi <code>scripts/run_benchmark.py</code>, Amdahl tính cho S2 + S4 + S6. Run all trên Colab T4 ngày 21/10 đạt mọi kiểm tra tự động: build, test, 6 cặp synthetic, 4 panorama, benchmark 9 cấu hình. Notebook commit không kèm output. Hướng dẫn chạy ở <a href="../notebook-guide.md">notebook-guide</a>.</td>
    </tr>
    <tr>
      <td>P3-T10</td>
      <td>Tạo panorama thu nhỏ của 3 site và cặp khó, phân tích chất lượng và trường hợp thất bại của cặp khó; viết mục 6 của tài liệu S6; viết phần S6 của mục 3.3, mục 3.4 và phần panorama của mục 3.5 của báo cáo giữa kỳ vào <code>docs/report/</code>; thêm nguồn của S6 vào <code>docs/report/references.md</code></td>
      <td>P3-T05</td>
      <td><code>docs/stages/s6-warp-blend.md</code> có mục 6; <code>docs/report/3.3-s6-warp-blend.md</code>, <code>docs/report/3.4-sequential-v0.md</code>, <code>docs/report/3.5-panoramas.md</code>; <code>references.md</code> có phần S6</td>
      <td>Xong</td>
      <td>Mục 6 tài liệu S6; <code>docs/report/3.3-s6-warp-blend.md</code>, <code>docs/report/3.4-sequential-v0.md</code>, <code>docs/report/3.5-panoramas.md</code>; phần S6 trong <code>references.md</code>. Phân tích panorama và crop dựa trên lần Run all ngày 21/10.</td>
    </tr>
  </tbody>
</table>

## P4 - Hoàn thiện và nộp

Hạn của giai đoạn: **23/10 (Thứ 6)**.

P4 là giai đoạn cuối. Chương phụ trách ghép các mục báo cáo trong `docs/report/` vào `Group16_Midterm.ipynb` và chạy lại notebook. Các thành viên đã xác nhận nội dung phần mình; không cần chờ xác nhận lại. Bản notebook cuối vẫn phải được đối chiếu với kết quả của lần Run all mới.

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
      <td>Cả nhóm</td>
      <td>P4-T01</td>
      <td>Rà bản notebook cuối sau lần chạy kỹ thuật của P4-T03: nội dung đúng với bản trong <code>docs/report/</code>, số liệu và nhận xét khớp output; sửa các chỗ sai lệch trước khi lưu bản nộp</td>
      <td>P4-T03</td>
      <td>Xác nhận nội dung của thành viên đã có; bản cuối được đối chiếu với output của phiên đang báo cáo</td>
      <td>Xong</td>
      <td>Đã đối chiếu nội dung với output phiên Colab T4 <code>20261024T113622Z-5c29204a</code>, xem panorama và 12 crop gốc. Sửa nhận xét site1 và giới hạn kết luận từ synthetic; các thành viên đã xác nhận, không chờ xác nhận lại.</td>
    </tr>
    <tr>
      <td rowspan="2">Chương</td>
      <td>P4-T02</td>
      <td>Ghép các mục báo cáo trong <code>docs/report/</code> vào <code>Group16_Midterm.ipynb</code>, thay các đoạn sơ bộ cũ (kể cả các câu "Chờ P3-T01/P3-T03")</td>
      <td></td>
      <td>Notebook có đủ mục 3.1-3.7 và mục tài liệu tham khảo theo <code>docs/report/</code>; pull request đã merge vào <code>main</code>, notebook trong repo không có output</td>
      <td>Xong</td>
      <td>Đủ nội dung và references; bản trước đã merge qua PR #19 và #20. Ngày 25/10 Chương chốt <code>Group16_Midterm1.ipynb</code> có output (86 cell, 21 code cell), đồng bộ sang <code>Group16_Midterm.ipynb</code> chỉ xóa output và execution count. Giữ nguyên toàn bộ source/thứ tự/metadata; gồm metadata synthetic, gallery A/B và trace đặc trưng. Theo yêu cầu trực tiếp của Chương, bản đồng bộ được commit lên <code>main</code> riêng với commit tài liệu/test.</td>
    </tr>
    <tr>
      <td>P4-T03</td>
      <td>Chạy Run all trên phiên Colab T4 mới; lưu output cho P4-T01 đối chiếu; sau khi rà panorama và nội dung thì bật <code>QUALITY_REVIEW_CONFIRMED</code>, <code>FINAL_REPORT_CONFIRMED</code> và kiểm tra cell cuối</td>
      <td>P4-T02</td>
      <td>Cell cuối in <code>READY</code>; mọi con số trong lời văn khớp output; bản notebook có output lưu trên Drive chung</td>
      <td>Xong</td>
      <td>Colab T4 24/10, phiên <code>20261024T113622Z-5c29204a</code>: build sm_75 và test đạt, sáu cặp synthetic đạt ngưỡng, chạy lặp H/pixel giống nhau, đủ chín cấu hình benchmark. Cell cuối <code>READY</code>, 16 check đạt. <a href="https://colab.research.google.com/drive/1iSOB8s5oUhBIv-opfKYZCO7SpTUWs-Op">Notebook có output trên Drive chung</a> đã đọc lại để kiểm tra đủ 42 cell và 18 ảnh, gồm 12 crop. Năm test cấu trúc được skip trong workspace Colab, đã chạy đạt trên local.</td>
    </tr>
  </tbody>
</table>
