# Bảng công việc giữa kỳ

Quy tắc chung nằm trong [kế hoạch giữa kỳ](midterm-plan.md). Kế hoạch được lập cuốn chiếu: chỉ giai đoạn hiện tại có task chi tiết. Giai đoạn kế tiếp được lập khi giai đoạn trước hoàn thành. Hạn được ghi cho cả giai đoạn; mọi task trong giai đoạn phải xong trước hạn đó. Mốc cố định duy nhất là **23/10 (Thứ 6)**.

Mã task có dạng `P<số giai đoạn>-T<số thứ tự>` và được dùng làm scope trong commit message, ví dụ `feat(p1-t14): add RANSAC hypothesis loop` trên nhánh giai đoạn `de/p1`. Cách chọn nhánh và pull request theo loại thay đổi nằm ở mục 10 của [kế hoạch](midterm-plan.md).

Task được nhóm theo thành viên, theo thứ tự stage phụ trách. Mỗi người tự cập nhật cột **Trạng thái** và **Ghi chú / PR** của task mình. Trạng thái dùng một trong các giá trị: `Chưa làm`, `Đang làm`, `Chờ review`, `Xong`, `Bị chặn`.

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
      <td>Kết quả ghi vào <a href="dataset.md">dataset</a> mục 6</td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td>P0-T02</td>
      <td>Ghi địa điểm dự kiến vào <a href="dataset.md">dataset</a> mục 5.1</td>
      <td></td>
      <td>Đủ 4 dòng</td>
      <td>Đang làm</td>
      <td></td>
    </tr>
    <tr>
      <td>P0-T03</td>
      <td>Chụp ảnh theo quy định, upload ảnh gốc, điền bảng ứng viên</td>
      <td>P0-T06</td>
      <td>Đủ số lượng theo <a href="dataset.md">dataset</a> mục 2</td>
      <td>Đang làm</td>
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
      <td>Xong</td>
      <td></td>
    </tr>
    <tr>
      <td>P0-T06</td>
      <td>Tạo Google Drive chung để nộp ảnh gốc, cập nhật link vào <a href="dataset.md">dataset</a> mục 4</td>
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
      <td>Chờ review</td>
      <td>Tuấn làm thay Thành. Đã viết mục 1, 2 của tài liệu S2 (FAST-9, score V, NMS 3×3, top-N) và S3 (BRIEF 256 bit không xoay, patch 31×31, pattern G II seed 16). Phương pháp là đề xuất, chờ Thành xác nhận; việc làm thay chờ cả Nhóm đồng ý.</td>
    </tr>
    <tr>
      <td>P0-T09</td>
      <td>Viết script chuẩn bị dataset theo <a href="dataset.md">dataset</a> mục 7</td>
      <td></td>
      <td>Chạy được trên Colab với ảnh mẫu</td>
      <td>Chờ review</td>
      <td>Tuấn làm thay Thành, nhánh tuan/shared-dataset-tools. Đã viết scripts/prepare_dataset.py (xoay theo EXIF, cắt 16:9 chung, 3 kích thước, bỏ EXIF, manifest SHA-256) và test tests/test_dataset_scripts.py. Colab 16/10: 9 test đạt; chạy thử với 3 cặp của Tuấn ra 18 ảnh đúng kích thước. Chưa merge.</td>
    </tr>
    <tr>
      <td>P0-T10</td>
      <td>Kiểm tra mọi cặp ảnh ứng viên có đạt yêu cầu hay không, ghi kết quả</td>
      <td>P0-T03</td>
      <td><a href="dataset.md">dataset</a> mục 5.3 đã điền đầy đủ</td>
      <td>Chờ review</td>
      <td>Tuấn làm thay Thành. scripts/check_pairs.py chạy lại trên toàn bộ Drive ngày 18/10 sau khi các thành viên cập nhật ảnh, kết quả ở dataset mục 5.3, thứ tự đề xuất và kết quả chạy thử pipeline V0 ở mục 6. Mọi cặp của Tuấn, Thành, Chương không có tiêu chí chưa đạt; ảnh của Đế chỉ còn sai tên file (.jpeg, cặp khó thiếu số). Từng thành viên còn phải review.</td>
    </tr>
    <tr>
      <td>Đế</td>
      <td>P0-T11</td>
      <td>Chọn sơ bộ phương pháp, đầu vào/đầu ra cho S4, S5; tự chuẩn bị phương án cặp synthetic và metric sai số homography</td>
      <td></td>
      <td><code>docs/stages/s4-matching.md</code>, <code>docs/stages/s5-homography.md</code> đều có mục 1 và 2 theo <a href="midterm-plan.md#6-mẫu-tài-liệu-thiết-kế-stage">mẫu ở mục 6 của kế hoạch giữa kỳ</a></td>
      <td>Đang làm</td>
      <td>Đế đã chốt S4 exact 2-NN Hamming + ratio 0.80, cross-check=false; S5 uniform RANSAC + normalized DLT double + MSAC/adaptive/refit. Đã viết/commit thiết kế input/output, phương án synthetic/metric và nguồn. Interface/cấu hình tích hợp còn cần cả Nhóm xác nhận.</td>
    </tr>
    <tr>
      <td rowspan="3">Chương</td>
      <td>P0-T12</td>
      <td>Tự tạo và setup khung <code>src/</code> theo cây thư mục của đề giữa kỳ (<code>common.h</code>, <code>cuda_utils.cuh</code>, <code>versions.h</code>, <code>main.cu</code>, <code>stb_impl.cpp</code>), nhận đúng tham số dòng lệnh của đề cuối kỳ</td>
      <td>P0-T05</td>
      <td>Khung đã merge vào <code>main</code>, build được bằng <code>nvcc -arch=sm_75</code> trên Colab T4</td>
      <td>Đang làm</td>
      <td>Đã có 5 file khung, CLI và stb; lịch sử local có merge PR #2 (4ced17d). Build/test C++ trên WSL đạt; chưa có bằng chứng build Colab T4 để nghiệm thu đầy đủ.</td>
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
      <td>Chờ review</td>
      <td>Đã có common.h và docs/interface.md (commit local ac46b96); layout/stride/Hamming/H kiểm tra bằng C++ trên WSL đạt. Cần cả Nhóm xác nhận quy ước và phần dữ liệu S2–S5 ở P0-T04; chưa xác minh review trên GitHub.</td>
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
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td>P1-T02</td>
      <td>Mỗi người mở pull request nhánh <code>&lt;tên&gt;/p1</code> và merge vào <code>main</code></td>
      <td>Các task code của mình trong P1</td>
      <td><code>main</code> build được bằng <code>nvcc -arch=sm_75</code> trên Colab T4 và có đủ 6 file <code>v0_*.cpp</code></td>
      <td>Chưa làm</td>
      <td></td>
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
      <td>Bị chặn</td>
      <td></td>
    </tr>
    <tr>
      <td>P1-T05</td>
      <td>Chọn cặp theo cách đã chốt ở P0-T01, chạy script chuẩn bị dataset, upload <code>dataset/</code> lên Drive chung</td>
      <td>P0-T01, P0-T09, P0-T10</td>
      <td><a href="dataset.md">dataset</a> mục 8 đã điền; <code>dataset/</code> trên Drive có đủ 3 site và cặp khó, mỗi cặp đủ 3 kích thước</td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td>P1-T06</td>
      <td>Viết nháp mục 3.2 và 3.6 của báo cáo giữa kỳ</td>
      <td>P1-T05</td>
      <td><code>docs/report/3.2-problem-understanding.md</code> và <code>docs/report/3.6-dataset.md</code></td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td rowspan="4">Thành</td>
      <td>P1-T07</td>
      <td>Chốt tham số và viết thuật toán chi tiết cho S2</td>
      <td>P0-T04, P0-T08</td>
      <td><code>docs/stages/s2-detection.md</code> có mục 3, 4 và 8</td>
      <td>Chờ review</td>
      <td>Tuấn làm thay Thành. Mục 3, 4, 8 của tài liệu S2: t = 0.05, max_keypoints = 2000, border 15, tie-break raster. Tham số chờ Thành xác nhận, hiệu chỉnh trên ảnh thật ở P2.</td>
    </tr>
    <tr>
      <td>P1-T08</td>
      <td>Cài đặt và kiểm thử <code>v0_detect.cpp</code></td>
      <td>P0-T12, P1-T07</td>
      <td>Đạt <a href="midterm-plan.md#14-tiêu-chí-hoàn-thành-một-task">mục 14 của kế hoạch</a>; mục 5 và 7 của tài liệu S2 có kết quả chạy trên Colab T4; báo lỗi khi đầu vào không hợp lệ theo quy ước trong <code>docs/interface.md</code></td>
      <td>Chờ review</td>
      <td>Tuấn làm thay Thành, nhánh tuan/shared-s2-s3. Đã cài v0_detect.cpp, fast_corner.cpp và test so với bản tham chiếu vét cạn. Colab T4 (CUDA 13.0) 16/10: 19524 assertions đạt bằng nvcc, đạt cả với ASan/UBSan; test tích hợp S1-S5 trên cặp dịch đạt. Mục 5 có số match/inlier trên 3 cặp của Tuấn ở 3 kích thước: tuan-standard2 đạt 62-186 inlier, tuan-standard1 chỉ 8-9 (cần xem lại ở P2). Chưa merge.</td>
    </tr>
    <tr>
      <td>P1-T09</td>
      <td>Chốt tham số và viết thuật toán chi tiết cho S3</td>
      <td>P0-T04, P0-T08</td>
      <td><code>docs/stages/s3-description.md</code> có mục 3, 4 và 8</td>
      <td>Chờ review</td>
      <td>Tuấn làm thay Thành. Mục 3, 4, 8 của tài liệu S3: làm mượt Gaussian σ = 2, r = 4, pattern sinh bằng tests/tool_gen_brief_pattern.py, compact keypoint ở mép. Chờ Thành xác nhận.</td>
    </tr>
    <tr>
      <td>P1-T10</td>
      <td>Cài đặt và kiểm thử <code>v0_describe.cpp</code></td>
      <td>P0-T12, P1-T09</td>
      <td>Đạt <a href="midterm-plan.md#14-tiêu-chí-hoàn-thành-một-task">mục 14 của kế hoạch</a>; mục 5 và 7 của tài liệu S3 có kết quả chạy trên Colab T4; báo lỗi khi đầu vào không hợp lệ theo quy ước trong <code>docs/interface.md</code></td>
      <td>Chờ review</td>
      <td>Tuấn làm thay Thành, nhánh tuan/shared-s2-s3. Đã cài v0_describe.cpp, bảng pattern và test; tách blur, kiểm tra layout của S1 thành gaussian_blur.cpp, image_layout.cpp để dùng chung (test S1 vẫn đạt). Colab T4 16/10: 2300 assertions đạt bằng nvcc, đạt cả với ASan/UBSan. Chưa merge.</td>
    </tr>
    <tr>
      <td rowspan="5">Đế</td>
      <td>P1-T11</td>
      <td>Chốt tham số và viết thuật toán chi tiết cho S4</td>
      <td>P0-T04, P0-T11</td>
      <td><code>docs/stages/s4-matching.md</code> có mục 3, 4 và 8</td>
      <td>Đang làm</td>
      <td>Đã chốt và cập nhật mục 1, 3, 4, 8: exact 2-NN Hamming 256-bit, ratio 0.80, cross-check=false, so sánh ratio nguyên 4/5, deterministic indexA. P1-T12 đã có code/test local; P0-T04 còn cần xác nhận cả Nhóm.</td>
    </tr>
    <tr>
      <td>P1-T12</td>
      <td>Cài đặt và kiểm thử <code>v0_match.cpp</code></td>
      <td>P0-T12, P1-T11</td>
      <td>Đạt <a href="midterm-plan.md#14-tiêu-chí-hoàn-thành-một-task">mục 14 của kế hoạch</a>; mục 5 và 7 của tài liệu S4 có kết quả chạy trên Colab T4; báo lỗi khi không đủ match theo quy ước trong <code>docs/interface.md</code></td>
      <td>Đang làm</td>
      <td>Đã cài/commit sequential matching và view/config helpers trên de/p1; C++11 warnings-as-errors và 66 checks local clang 23.1.3 Windows đạt; allocation/error cleanup còn được kiểm tra riêng cùng S5. Đã cập nhật API và lệnh Colab trong tài liệu S4; chờ nvcc Colab T4 và nghiệm thu tích hợp.</td>
    </tr>
    <tr>
      <td>P1-T13</td>
      <td>Chốt tham số và viết thuật toán chi tiết cho S5, gồm seed RANSAC và cách xử lý khi không đủ match hoặc homography suy biến</td>
      <td>P0-T04, P0-T11</td>
      <td><code>docs/stages/s5-homography.md</code> có mục 3, 4 và 8</td>
      <td>Đang làm</td>
      <td>Đã viết/commit thiết kế seed 16, cap 2000, uniform deterministic sampling, normalized DLT double, MSAC, confidence 0.99, tau 2/3/6 px và tối đa hai all-inlier refits. P1-T14 đã có code/test local. Cần cả Nhóm xác nhận tích hợp và numeric tolerances.</td>
    </tr>
    <tr>
      <td>P1-T14</td>
      <td>Cài đặt và kiểm thử <code>v0_homography.cpp</code></td>
      <td>P0-T12, P1-T13</td>
      <td>Đạt <a href="midterm-plan.md#14-tiêu-chí-hoàn-thành-một-task">mục 14 của kế hoạch</a>; mục 5 và 7 của tài liệu S5 có kết quả chạy trên Colab T4; seed RANSAC lấy từ cấu hình và được in ra; báo lỗi khi homography suy biến theo quy ước trong <code>docs/interface.md</code></td>
      <td>Đang làm</td>
      <td>Đã cài V0 S5 và các module nhỏ trên de/p1; stage có 174 checks local đạt, toàn runner gồm 7 suites/5673 assertions cùng S4/S6 đạt bằng clang 23.1.3 Windows. ASan/UBSan đạt theo phạm vi ghi ở tài liệu S5. API/report in seed ngoài timing đã có; chờ nvcc Colab T4, dataset và nghiệm thu tích hợp.</td>
    </tr>
    <tr>
      <td>P1-T15</td>
      <td>Tạo cặp synthetic từ một homography biết trước và công cụ tính sai số homography so với ground truth</td>
      <td>P0-T11</td>
      <td>Tạo được cặp synthetic và in được sai số; cách tạo cặp và metric ghi trong mục 5 của tài liệu S5</td>
      <td>Chưa làm</td>
      <td></td>
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
      <td>Đang làm</td>
      <td>Đã cài v0_warp_blend.cpp và header stage trên chuong/p1: inverse/bbox/bilinear, average 50/50 theo yêu cầu coding mới, stride byte, cleanup và ErrorCode. 194 assertions synthetic trên WSL đạt; AddressSanitizer/UndefinedBehaviorSanitizer đạt. Đã cập nhật tài liệu S6; chưa chạy Colab T4/dataset và chưa commit/merge nên chưa nghiệm thu Xong. main.cu chưa nối S6 thật.</td>
    </tr>
    <tr>
      <td>P1-T18</td>
      <td>Cài đặt khung chạy trong <code>main.cu</code>: đo thời gian từng stage và tổng theo <a href="midterm-plan.md#12-quy-định-đo-thời-gian-v0">mục 12 của kế hoạch</a>, warm-up, <code>--runs</code>, in dòng CSV, cờ <code>--debug</code>, báo lỗi cấp chương trình (thiếu file, ảnh không đọc được, version không tồn tại, <code>--runs</code> không dương)</td>
      <td>P0-T04, P0-T12</td>
      <td>Merge vào <code>main</code> qua pull request file dùng chung; chạy được trên Colab T4 với các stage stub</td>
      <td>Đang làm</td>
      <td>Đã triển khai main.cu: 6 stub, RGB I/O, warm-up, timing từng stage/tổng, CSV 8 cột, average/minimum, debug và lỗi. Build C++11 warnings-as-errors và 34 ca benchmark/CLI/I/O trên WSL đạt; output preview ảnh A được kiểm tra pixel. Nhánh chuong/shared-benchmark; chờ kiểm chứng Colab T4 và merge PR file dùng chung. Timing stub không dùng làm benchmark thuật toán.</td>
    </tr>
  </tbody>
</table>

## P2 - Ghép và kiểm chứng V0

Lập chi tiết khi P1 hoàn thành.

## P3 - Đo và phân tích

Lập chi tiết khi P2 hoàn thành.

## P4 - Hoàn thiện và nộp

Lập chi tiết khi P3 hoàn thành. Hạn của giai đoạn: **23/10 (Thứ 6)**.

## Quyết định đã chốt

Ghi lại các quyết định cả Nhóm đã thống nhất trong quá trình làm.

| Ngày | Quyết định |
|---|---|
