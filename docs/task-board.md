<!-- Authors: Le Thuong De (23120232), Nguyen Ho Anh Tuan (23120185). External source: none. -->

# Bảng công việc

Quy tắc chung nằm trong [kế hoạch cuối kỳ](final-plan.md) (mốc nộp bài **04/12 (Thứ 6)**, ngày **03/12 (Thứ 5)** họp tổng duyệt thử thuyết trình). Bảng công việc và kế hoạch giữa kỳ (các giai đoạn P0–P4) được lưu trữ tại [kế hoạch giữa kỳ](archive/midterm-plan.md) và [bảng công việc giữa kỳ](archive/midterm-task-board.md).

Kế hoạch được lập cuốn chiếu: chỉ giai đoạn hiện tại có task chi tiết; giai đoạn kế tiếp được lập khi giai đoạn trước hoàn thành. Hạn được ghi cho cả giai đoạn; mọi task trong giai đoạn phải xong trước hạn đó.

Mã task có dạng `P<số giai đoạn>-T<số thứ tự>` và được dùng làm scope trong commit message, ví dụ `feat(p5-t10): implement basic CUDA Hamming matcher` trên nhánh giai đoạn `de/p5`. Cách chọn nhánh và pull request theo loại thay đổi nằm ở mục 8.1 của [kế hoạch cuối kỳ](final-plan.md).

Task được nhóm theo thành viên, theo thứ tự stage phụ trách. Mỗi người tự cập nhật cột **Trạng thái** và **Ghi chú / PR** của task mình. Trạng thái dùng một trong các giá trị: `Chưa làm`, `Đang làm`, `Chờ review`, `Xong`, `Bị chặn`.

## P5 - Khung GPU, dataset và cài đặt từng stage V1

Hạn của giai đoạn: **02/11 (Thứ 2)**.

Các thành viên phát triển và kiểm thử độc lập từng stage V1 bằng dữ liệu đầu ra trung gian của V0 và bộ ảnh synthetic theo mục 5.3 của [kế hoạch cuối kỳ](final-plan.md), không chờ các stage GPU đứng trước hoặc việc rà soát lại dataset hoàn tất. Việc nối `v1_pipeline` end-to-end, chạy benchmark chính thức trên dataset cuối kỳ và thu thập profiling V1 thuộc P6.

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
      <td>P5-T01</td>
      <td>Thống nhất contract GPU dùng chung, chốt bộ cặp dataset cuối kỳ và merge nhánh <code>&lt;tên&gt;/p5</code> của từng thành viên vào <code>main</code></td>
      <td>Các task trong P5</td>
      <td>Contract GPU và đủ 6 stage V1 đã merge vào <code>main</code>, build được bằng <code>nvcc -arch=sm_75</code> trên Colab T4; bộ cặp dataset cuối kỳ ghi vào mục "Quyết định đã chốt"</td>
      <td>Xong</td>
      <td>03/11: Đủ 6 stage V1 và hạ tầng GPU đã merge vào <code>main</code>. Nhóm trưởng đã chốt dataset cuối kỳ và layout benchmark; đã hoàn tất P5-T05 và bổ sung công cụ tự động <code>scripts/fetch_and_prepare_dataset.py</code> chuẩn bị dữ liệu. P5 chính thức hoàn tất.</td>
    </tr>
    <tr>
      <td rowspan="2">Tuấn</td>
      <td>P5-T02</td>
      <td>Tái cấu trúc <code>src/</code> và <code>tests/</code> theo thư mục con, hợp nhất runner kiểm thử và thêm script build đa nền tảng</td>
      <td></td>
      <td>Đã merge vào <code>main</code>; build sạch bằng <code>nvcc -arch=sm_75</code> và toàn bộ test V0, Python đạt trên Colab T4</td>
      <td>Xong</td>
      <td>Đã merge PR #21. Colab T4 ngày 29/10: build bằng <code>nvcc -arch=sm_75</code>, đạt cả 13 suite C++ (kể cả bản sanitizer) và 5 suite Python.</td>
    </tr>
    <tr>
      <td>P5-T03</td>
      <td>Cài đặt, định nghĩa ngưỡng kiểm chứng và kiểm thử V1 cho S1</td>
      <td>P5-T04, P5-T12</td>
      <td>Đạt <a href="final-plan.md#9-tiêu-chí-hoàn-thành-một-task-và-checklist-nộp-bài">mục 9 của kế hoạch cuối kỳ</a>; test đối chiếu S1 với V0 đạt trên Colab T4; cập nhật <code>docs/stages/s1-preprocessing.md</code></td>
      <td>Xong</td>
      <td>03/11: Thành làm thay (xem mục "Quyết định đã chốt"). Blur dùng chung ở PR #28, S1 ở PR #29 (<code>thanh/p5</code>, đã merge vào <code>main</code>). Colab T4: suite <code>gpu_s1</code> 10706 checks, giống V0 từng bit (<code>max_abs_diff=0</code>, ngưỡng 1e-5) trên suite, 12 cặp dataset và 6 cặp synthetic; memcheck 0 lỗi.</td>
    </tr>
    <tr>
      <td rowspan="4">Thành</td>
      <td>P5-T04</td>
      <td>Mở rộng khung kiểm thử trong <code>tests/</code> để hỗ trợ biên dịch, chạy nhóm test GPU và tiện ích đối chiếu kết quả stage GPU với V0</td>
      <td>P5-T02</td>
      <td>Runner kiểm thử hỗ trợ nhóm test GPU và tiện ích nạp dữ liệu tham chiếu V0, chạy đạt trên Colab T4</td>
      <td>Xong</td>
      <td>03/11: Đã merge PR #26 (<code>thanh/shared-gpu-test-tools</code>) vào <code>main</code>. Colab T4: 14 suite V0 (45284 checks), 4 suite GPU (19647 checks) và 7 suite Python (102 test) đạt.</td>
    </tr>
    <tr>
      <td>P5-T05</td>
      <td>Nâng cấp công cụ benchmark và vẽ biểu đồ trong <code>scripts/</code> hỗ trợ đo đa phiên bản, schema CSV mở rộng và tính speedup theo đề cuối kỳ</td>
      <td>P5-T12</td>
      <td>Script kèm bộ unit test Python tương ứng chạy đạt trên Colab T4</td>
      <td>Xong</td>
      <td>03/11: Nhóm trưởng chốt layout output theo phiên bản <code>&lt;out&gt;/v&lt;k&gt;/&lt;site&gt;/&lt;size&gt;.csv</code> cho bài nộp cuối kỳ (<code>Group16_Final.ipynb</code>). Đã hoàn tất nâng cấp <code>scripts/run_benchmark.py</code> (hỗ trợ đa phiên bản, schema 11 cột, tính speedup V0/prev), <code>scripts/plot_benchmark.py</code> (vẽ biểu đồ speedup) và mở rộng unit test Python tương ứng.</td>
    </tr>
    <tr>
      <td>P5-T06</td>
      <td>Cài đặt, định nghĩa ngưỡng kiểm chứng và kiểm thử V1 cho S2</td>
      <td>P5-T04, P5-T12</td>
      <td>Đạt <a href="final-plan.md#9-tiêu-chí-hoàn-thành-một-task-và-checklist-nộp-bài">mục 9 của kế hoạch cuối kỳ</a>; test đối chiếu S2 với V0 đạt trên Colab T4; cập nhật <code>docs/stages/s2-detection.md</code></td>
      <td>Xong</td>
      <td>03/11: Đã merge PR #29 (<code>thanh/p5</code>) và PR #27 vào <code>main</code>. Colab T4: suite <code>gpu_s2</code> 2080 checks; keypoint giống V0 (tọa độ, bit score, thứ tự) trên suite và chuỗi S1→S2 với 12 cặp dataset, 6 cặp synthetic; memcheck 0 lỗi.</td>
    </tr>
    <tr>
      <td>P5-T07</td>
      <td>Cài đặt, định nghĩa ngưỡng kiểm chứng và kiểm thử V1 cho S3</td>
      <td>P5-T04, P5-T12</td>
      <td>Đạt <a href="final-plan.md#9-tiêu-chí-hoàn-thành-một-task-và-checklist-nộp-bài">mục 9 của kế hoạch cuối kỳ</a>; test đối chiếu S3 với V0 đạt trên Colab T4; cập nhật <code>docs/stages/s3-description.md</code></td>
      <td>Xong</td>
      <td>03/11: Đã merge PR #29 (<code>thanh/p5</code>) vào <code>main</code>. Colab T4: suite <code>gpu_s3</code> 1022 checks; descriptor giống V0 từng bit; chuỗi S1→S2→S3→<code>v1_match</code> giống V0 đến <code>v0_match</code> trên 12 cặp dataset và 6 cặp synthetic; memcheck và racecheck 0 lỗi.</td>
    </tr>
    <tr>
      <td rowspan="4">Đế</td>
      <td>P5-T08</td>
      <td>Đánh giá lại kho dữ liệu ảnh, đề xuất phương án chọn lại cặp chuẩn <code>site2</code> và cặp khó <code>challenge</code> phục vụ phân tích thất bại kèm lập luận, cập nhật <a href="dataset.md">dataset</a> và bộ <code>dataset/</code> trên Drive chung sau khi nhóm chốt</td>
      <td></td>
      <td>Lập luận và kết quả cập nhật trong <a href="dataset.md">dataset</a>; bộ <code>dataset/</code> kèm <code>manifest.csv</code> đã kiểm tra và upload lên Drive chung</td>
      <td>Xong</td>
      <td>03/11: Nhóm trưởng chốt chọn site2 <code>thanh-standard2</code>, challenge <code>de-challenge1</code> theo đề xuất của Đế; chấp nhận overlap ~58% của <code>thanh-standard2</code> để triệt tiêu bóng ma parallax; cập nhật <a href="dataset.md#83-bộ-dataset-cuối-kỳ-chính-thức-chốt-ngày-0311">dataset mục 8.3</a>; tiến hành chuẩn hóa tên nguồn và chạy <code>prepare_dataset.py</code> cập nhật Drive.</td>
    </tr>
    <tr>
      <td>P5-T09</td>
      <td>Xây dựng công cụ chạy gom batch thu thập bằng chứng profiling (<code>nsys</code>, <code>ncu</code>) và kiểm chứng sai số homography đa phiên bản trên bộ cặp synthetic</td>
      <td>P5-T12</td>
      <td>Script kèm kiểm thử chạy đạt trên Colab T4, xuất được kết quả profiling và sai số synthetic theo phiên bản</td>
      <td>Xong</td>
      <td>31/10: đã hoàn tất code và kiểm thử; công cụ batch profiling/synthetic trên <code>de/shared-p5-tools</code>, commit <code>7781024</code>; 20 test Python mới đạt trên Colab T4, nsys/ncu xuất report và NVTX cho S4/S5. Đã kiểm chứng 12 lượt synthetic theo scope S4/S5. hướng dẫn ở <code>docs/profiling.md</code>.</td>
    </tr>
    <tr>
      <td>P5-T10</td>
      <td>Cài đặt, định nghĩa ngưỡng kiểm chứng và kiểm thử V1 cho S4</td>
      <td>P5-T04, P5-T12</td>
      <td>Đạt <a href="final-plan.md#9-tiêu-chí-hoàn-thành-một-task-và-checklist-nộp-bài">mục 9 của kế hoạch cuối kỳ</a>; test đối chiếu S4 với V0 đạt trên Colab T4; cập nhật <code>docs/stages/s4-matching.md</code></td>
      <td>Xong</td>
      <td>31/10: đã hoàn tất code và kiểm thử; code/test trong <code>src/v1/s4/</code> trên <code>de/p5</code>, commit <code>deafa78</code>; 2387 checks trên Colab T4, memcheck 0 lỗi, match khớp V0 trên sáu cặp synthetic. NVTX ở commit <code>ebfd446</code>. Đã merge PR #25.</td>
    </tr>
    <tr>
      <td>P5-T11</td>
      <td>Cài đặt, định nghĩa ngưỡng kiểm chứng và kiểm thử V1 cho S5</td>
      <td>P5-T04, P5-T12</td>
      <td>Đạt <a href="final-plan.md#9-tiêu-chí-hoàn-thành-một-task-và-checklist-nộp-bài">mục 9 của kế hoạch cuối kỳ</a>; test đối chiếu S5 với V0 đạt trên Colab T4; cập nhật <code>docs/stages/s5-homography.md</code></td>
      <td>Xong</td>
      <td>31/10: đã hoàn tất code và kiểm thử; code/test trong <code>src/v1/s5/</code> trên <code>de/p5</code>, commit <code>a0fa80f</code>, test biên <code>427ee94</code>; 16521 checks trên Colab T4, memcheck 0 lỗi. Driver <code>ed001e0</code> đối chiếu prefix/mask và H trên sáu cặp synthetic, đạt ngưỡng CPU–GPU và ground truth. Đã merge PR #25.</td>
    </tr>
    <tr>
      <td rowspan="2">Chương</td>
      <td>P5-T12</td>
      <td>Xây dựng hạ tầng GPU dùng chung trong <code>src/common/cuda_utils.cuh</code>, thiết kế contract workspace Device-resident cho V1, mở rộng báo cáo timing CSV trong <code>src/main.cu</code> và cập nhật <a href="interface.md">interface</a></td>
      <td>P5-T02</td>
      <td>Merge vào <code>main</code> qua pull request file dùng chung; build sạch bằng <code>nvcc -arch=sm_75</code> và chạy đúng <code>--version 0</code> trên Colab T4</td>
      <td>Xong</td>
      <td>Đã merge PR #22. Colab Tesla T4 ngày 30/10, nvcc 13.0.88, target sm_75: build đạt, 13 suite V0 / 45.256 checks và CLI mặc định 5 runs đạt. Source/evidence đã đối chiếu hash; hạ tầng V1 vẫn là scaffold, timing toàn pipeline GPU thuộc P6. Xem <a href="report/p5-s6-cuda-verification.md">báo cáo nghiệm thu T4</a>.</td>
    </tr>
    <tr>
      <td>P5-T13</td>
      <td>Cài đặt, định nghĩa ngưỡng kiểm chứng và kiểm thử V1 cho S6</td>
      <td>P5-T04, P5-T12</td>
      <td>Đạt <a href="final-plan.md#9-tiêu-chí-hoàn-thành-một-task-và-checklist-nộp-bài">mục 9 của kế hoạch cuối kỳ</a>; test đối chiếu S6 với V0 đạt trên Colab T4; cập nhật <code>docs/stages/s6-warp-blend.md</code></td>
      <td>Xong</td>
      <td>30/10, <code>chuong/p5</code>: code và kiểm chứng Colab Tesla T4 đạt với nvcc 13.0.88, sm_75. Suite 709 checks / 66 đối chiếu; 12/12 case thật cùng H khớp, max RGB error 0 (ngưỡng 1). Memcheck fixtures và site2/large: 0 errors, 0 bytes leak. Đã cập nhật thiết kế, notebook tái lập và <a href="report/p5-s6-cuda-verification.md">báo cáo bằng chứng</a>. Đã merge PR #23 vào <code>main</code>; CLI tích hợp thuộc P6.</td>
    </tr>
  </tbody>
</table>

## P6 - Ghép pipeline, benchmark và profiling V1

Hạn của giai đoạn: **08/11 (Chủ nhật)**.

Giai đoạn P6 tập trung nối trọn vẹn 6 stage V1 thành pipeline `v1_pipeline` hoàn chỉnh theo kiến trúc `Device-resident`, kiểm thử tích hợp end-to-end, chạy bộ benchmark chính thức V0 vs V1 trên Google Colab GPU Tesla T4 và thu thập bằng chứng profiling Nsight (`nsys`, `ncu`) để chỉ ra bottleneck dẫn đường cho tối ưu V2 (P7).

Các công việc được tách độc lập để làm song song ngay từ đầu giai đoạn: Thành chạy trước baseline V0 và chuẩn bị biểu đồ; Đế chạy trước Nsight Compute (`ncu`) trên các kernel riêng lẻ; Tuấn mở rộng runner kiểm thử tích hợp CLI; Chương nối `v1_pipeline` trong `src/main.cu`. Sau khi merge pipeline, Thành chạy đo nốt V1, Tuấn kiểm tra an toàn bộ nhớ và Đế thu thập Nsight Systems (`nsys`) toàn pipeline, phân tích ca thất bại `challenge` để chốt bài toán tối ưu V2.

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
      <td>Chương</td>
      <td>P6-T01</td>
      <td>Ghép nối <code>v1_pipeline</code> hoàn chỉnh và quản lý bộ nhớ <code>DeviceWorkspace</code> trong CLI</td>
      <td>P5-T01</td>
      <td>Thay thế các stub trong <code>src/main.cu</code> bằng 6 stage thật; tính <code>max_scratch</code> cấp phát một lần cho <code>d_scratch</code> (căn chỉnh 16 byte); quản lý cấp phát canvas linh hoạt cho S6 theo ma trận H kèm cấp phát buffer output trên Host theo kích thước canvas thực tế (tránh tràn buffer); xử lý an toàn mã lỗi biên (<code>DegenerateHomography</code>, <code>TooFewKeypoints</code>). Lệnh <code>./stitch ... --version 1</code> chạy trọn vẹn 6 stage trên GPU và xuất ảnh panorama đạt chuẩn.</td>
      <td>Xong</td>
      <td>06/11: Thành làm thay (xem mục "Quyết định đã chốt"). Đã merge PR #31 vào <code>main</code>. Module <code>src/v1/v1_pipeline.{h,cu}</code> thay thế các stub trong <code>main.cu</code>, cấp pinned output theo canvas ở warm-up, đọc <code>d_counts-&gt;status</code> để báo đúng lỗi của S3–S5, đặt stack Device 32 KiB cho S5. Colab T4: build đạt; 14 suite V0 (45284 checks), 8 suite GPU (33730 checks), 7 suite Python (105 test) đạt; V1 khớp V0 trên 10 cấu hình dataset chạy được (H giống, pixel lệch tối đa 0), challenge medium/large cùng lỗi <code>NumericalFailure</code> như V0; 6 cặp synthetic đạt; memcheck 0 lỗi, 0 byte rò rỉ. Chi tiết ở <a href="interface.md#118-pipeline-v1-tích-hợp-p6-t01">interface mục 11.8</a>.</td>
    </tr>
    <tr>
      <td>Tuấn</td>
      <td>P6-T02</td>
      <td>Bổ sung target kiểm tra tích hợp V1 vào test runner và kiểm tra an toàn bộ nhớ</td>
      <td>P6-T01</td>
      <td>Mở rộng <code>tests/run_tests.py</code> hỗ trợ target/suite kiểm tra tích hợp CLI V1 trên ảnh synthetic và ảnh dataset; kiểm chứng H và kích thước canvas; chạy <code>compute-sanitizer</code> trên Colab T4 nghiệm thu 0 lỗi rò rỉ bộ nhớ.</td>
      <td>Xong</td>
      <td>06/11, nhánh <code>tuan/p6</code>: bổ sung suite C++/CUDA <code>gpu_pipeline</code> trong <code>tests/gpu/test_gpu_v1_pipeline.cu</code> kiểm tra end-to-end 6 stage V1; đăng ký <code>gpu_pipeline</code> vào <code>GPU_SUITES</code> và <code>GPU_STB_SUITES</code> của <code>tests/run_tests.py</code>; bổ sung suite Python <code>tests/python/test_v1_cli.py</code>. Nghiệm thu Colab T4 ngày 06/11: 14 suite V0 (45284 checks), 9 suite GPU (33783 checks, <code>gpu_pipeline</code> 53 checks, max RGB error 0), 8 suite Python (130 test) đạt; <code>compute-sanitizer</code> trên <code>gpu_pipeline</code> đạt 0 lỗi, 0 byte rò rỉ bộ nhớ.</td>
    </tr>
    <tr>
      <td>Thành</td>
      <td>P6-T03</td>
      <td>Chạy bộ benchmark chính thức V0 vs V1 trên Colab T4 và vẽ biểu đồ speedup</td>
      <td>P6-T01</td>
      <td>Đo trước baseline V0 trên 4 cặp ảnh dataset ở 3 độ phân giải (5 runs + warm-up); đo V1 khi có bản build pipeline; xuất đầy đủ CSV <code>&lt;out&gt;/v&lt;k&gt;/&lt;site&gt;/&lt;size&gt;.csv</code> theo schema 11 cột; chạy <code>scripts/plot_benchmark.py</code> tạo biểu đồ so sánh speedup V1/V0.</td>
      <td>Xong</td>
      <td>06/11: Thành chọn đo cả 4 cặp; bảng chính vẫn là 3 site chuẩn, challenge đo bổ sung qua cờ <code>--include-challenge</code>, cấu hình lỗi ghi vào <code>failures.csv</code>. Task không sửa code stage nên dùng nhánh <code>thanh/shared-benchmark-challenge</code> thay cho <code>thanh/p6</code>, đã merge PR #30: thêm challenge, chặn số đo của V1 stub, kiểm tra header CSV theo phiên bản, speedup từng stage. Lượt chạy thử V0 trước khi có V1 không dùng cho bảng chính thức.<br><br>06/11, đo chính thức V0 và V1 trong cùng một phiên Colab (Tesla T4, driver 580.82.07, nvcc 13.0.88, <code>main</code> tại <code>076a214</code>): 24 ảnh khớp SHA-256 trong <code>manifest.csv</code>; build đạt; 8 suite Python (130 test), 14 suite V0 (45284 checks), 9 suite GPU (33799 checks) đạt. Lệnh <code>run_benchmark.py --versions 0 1 --include-challenge</code> chạy 198 giây, exit 0. Speedup Total_ms của V1 so với V0 (small / medium / large): site1 2.24x / 3.23x / 11.89x, site2 1.20x / 1.99x / 11.34x, site3 2.52x / 3.48x / 9.53x; challenge small 3.02x. Challenge medium/large lỗi <code>NumericalFailure</code> ở cả V0 và V1 nên không có speedup. S1–S4 và S6 của V1 nhanh hơn V0 từ 51x đến hơn 1000x, nhưng S5 chậm hơn V0 (0.01x–0.46x) và chiếm trung bình 98.9% (small), 97.8% (medium), 90.7% (large) Total_ms của V1 trên 3 site chuẩn, nên hot stage của V1 là S5 ở cả 3 độ phân giải. Điều này khác với các hotspot S2, S4, S6 ghi trong <code>docs/report/4.1-v1-profiling-and-bottlenecks.md</code>; cần báo lại cho cả Nhóm để cùng quyết định. <code>Total_Kernel_ms</code> của V1 vẫn là 0 (chưa đo) nên chưa có kernel speedup. Kết quả (CSV, log, <code>speedup.md</code>, <code>speedup.png</code>, <code>stage_speedup_v1.png</code>, biểu đồ stage của từng phiên bản) nằm trong <code>p6-t03-official.zip</code> ở thư mục Drive <code>Trần Hữu Kim Thành/p6-t03</code>.</td>
    </tr>
    <tr>
      <td rowspan="2">Đế</td>
      <td>P6-T04</td>
      <td>Thu thập số liệu Nsight Compute (<code>ncu</code>) đo sâu các kernel V1 riêng lẻ</td>
      <td>P5-T09</td>
      <td>Chạy <code>scripts/run_profiling.py</code> trên Colab T4 thu thập metric chi tiết (Memory Bandwidth, Occupancy, Warp Stalls) cho từng kernel stage từ S1 đến S6 thông qua các test suite GPU độc lập.</td>
      <td>Xong</td>
      <td>06/11: Tuấn làm thay Đế (xem mục "Quyết định đã chốt") trên nhánh <code>tuan/p6</code>; thu thập và phân tích các chỉ số vi kiến trúc NCU (SOL Memory, SOL Compute, Occupancy, Warp Stalls) cho 6 kernel stage V1, ghi nhận tại <code>docs/report/4.1-v1-profiling-and-bottlenecks.md</code>.</td>
    </tr>
    <tr>
      <td>P6-T05</td>
      <td>Thu thập Nsight Systems toàn pipeline, phân tích ca lỗi <code>challenge</code> và viết báo cáo bottleneck V1</td>
      <td>P6-T01, P6-T03, P6-T04</td>
      <td>Chạy <code>nsys</code> lấy timeline NVTX toàn pipeline; phân tích cơ chế thất bại trên cặp <code>de-challenge1</code>; đối chiếu số liệu benchmark và profiling để xác định chính xác hotspot của V1; viết tài liệu đề xuất bài toán tối ưu cho V2 (P7) và soạn cuốn chiếu mục V1 vào <code>docs/report/</code>.</td>
      <td>Xong</td>
      <td>06/11: Tuấn làm thay Đế trên nhánh <code>tuan/p6</code>; thu thập NSYS timeline NVTX toàn pipeline, phân tích cơ chế thất bại do hoa văn lặp lan can gây thoái hóa descriptor BRIEF trên <code>de-challenge1</code>; hoàn thành báo cáo <code>docs/report/4.1-v1-profiling-and-bottlenecks.md</code> chỉ rõ các hotspot S2, S4, S6 và đề xuất giải pháp tối ưu cho V2 (P7).</td>
    </tr>
  </tbody>
</table>

## P7 - Tối ưu và profiling V2

Hạn của giai đoạn: **10/11 (Thứ 3)**.

Giai đoạn P7 áp dụng chu trình APOD (Assess → Parallelize → Optimize → Deploy) tập trung tối ưu hóa kernel S5 (Homography RANSAC), giải quyết điểm nghẽn chiếm 90–98% thời gian của V1. Các thành viên triển khai song song: Tuấn tối ưu kernel S5; Thành bổ sung timer `cudaEvent` đo `Total_Kernel_ms` và ghép `v2_pipeline`; Chương xây dựng suite kiểm tra tích hợp V2 và nghiệm thu an toàn bộ nhớ; Đế chạy benchmark V2, thu thập profiling Nsight và hoàn thành báo cáo APOD V2.

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
      <td>Tuấn</td>
      <td>P7-T01</td>
      <td>Thiết kế và cài đặt tối ưu kernel S5 V2 trong <code>src/v2/s5/</code></td>
      <td>P6-T01</td>
      <td>Người làm toàn quyền lựa chọn giải pháp kỹ thuật; build sạch bằng <code>nvcc -arch=sm_75</code>; giữ nguyên phương pháp và tham số V0; kết quả nhất quán với V0 (dung sai số học) trên 6 cặp synthetic; đạt bài test đơn vị của stage</td>
      <td>Xong</td>
      <td>07/11, nhánh <code>tuan/p7</code>: tối ưu song song hóa All-Inlier Refit và Jacobi SVD; PR #33 đã merge vào <code>main</code>. Colab T4: đạt các fixture đơn vị, H nhất quán với V0 trên 6 cặp synthetic.</td>
    </tr>
    <tr>
      <td>Thành</td>
      <td>P7-T02</td>
      <td>Bổ sung cơ chế đo thời gian <code>cudaEvent_t</code> trong <code>src/main.cu</code> và ghép nối <code>src/v2/v2_pipeline</code></td>
      <td>P6-T01</td>
      <td>Gắn <code>cudaEventRecord</code> quanh các kernel stage trên Device để đo chuẩn <code>Total_Kernel_ms</code>, H2D, D2H; ghép <code>src/v2/v2_pipeline.{h,cu}</code> gọi S5 V2 mới và tái sử dụng S1–S4, S6 từ <code>src/v1/</code>; CLI <code>./stitch ... --version 2</code> chạy thông suốt và xuất đủ 11 cột CSV; các test Python không bị hồi quy</td>
      <td>Xong</td>
      <td>Chương triển khai thay Thành phần pipeline V2, CLI và CUDA event timing. V2 gọi S5 V2, dùng lại S1–S4/S6 của V1. Colab T4 ngày 08/11 xác nhận build <code>sm_75</code>, CLI production, CSV 11 cột và các dòng tổng hợp đạt. Bàn giao cùng P7-T04 qua <a href="https://github.com/nh-atuan/panorama-stitching/pull/34">PR #34</a>. Xem <a href="report/p7-v2-verification.md">báo cáo nghiệm thu</a>.</td>
    </tr>
    <tr>
      <td>Đế</td>
      <td>P7-T03</td>
      <td>Đo benchmark V2 trên Colab T4, thu thập profiling Nsight và hoàn thành báo cáo APOD V2</td>
      <td>P7-T01, P7-T02</td>
      <td>Đo thời gian V2 trên Colab T4 (5 runs + warm-up), đối chiếu speedup với V0 và V1; thu thập trace timeline NSYS và chỉ số NCU cho kernel S5 V2; xuất đủ CSV và biểu đồ speedup vào Drive <a href="https://drive.google.com/drive/folders/1uJ-4_kgVONvIt5NQIPzdEWTIPrg8Sue1?usp=sharing"><code>v2/</code></a> (xem <a href="results-guide.md">hướng dẫn</a>); cập nhật <a href="apod-log.md">apod-log.md</a> và hoàn thành mục báo cáo V2 trong <code>docs/report/</code></td>
      <td>Xong</td>
      <td>10/11: Benchmark V2 (5 runs + warm-up), đối chiếu V0 P6 chính thức và V1 P7 cùng phiên; 4 trace NSYS, 8 report NCU, CSV/biểu đồ và báo cáo APOD tại <a href="report/p7-t03-v2-apod.md">docs/report/p7-t03-v2-apod.md</a>. Đã bổ sung 1 ảnh PNG NSYS và 4 PDF NCU; người phụ trách xác nhận đã upload gói kết quả lên Drive chung <code>v2/</code>.</td>
    </tr>
    <tr>
      <td>Chương</td>
      <td>P7-T04</td>
      <td>Xây dựng suite kiểm tra tích hợp CLI V2 trong <code>tests/</code> và kiểm tra an toàn bộ nhớ trên Colab T4</td>
      <td>P7-T01, P7-T02</td>
      <td>Tạo suite C++/CUDA <code>tests/gpu/test_gpu_v2_pipeline.cu</code> đối chiếu H và canvas của V2 với V0/V1 trên synthetic và dataset thật; chạy <code>compute-sanitizer</code> trên Colab Tesla T4 nghiệm thu 0 lỗi, 0 byte rò rỉ bộ nhớ</td>
      <td>Xong</td>
      <td>08/11 Colab Tesla T4 đạt 7/7 cổng. Sáu cặp synthetic đạt ngưỡng. Cả 12 cấu hình thật khớp trạng thái V0/V1/V2, 10 ca có panorama khớp canvas và Max RGB = 0. Hai lượt memcheck exit 0, 0 lỗi và 0 byte rò rỉ. Source đã chạy khớp commit <code>bc1226f</code>. <a href="report/p7-v2-verification.md">Báo cáo P7-T04</a> ghi kết quả và tên gói bằng chứng. Bàn giao qua <a href="https://github.com/nh-atuan/panorama-stitching/pull/34">PR #34</a>.</td>
    </tr>
  </tbody>
</table>

## P8 - Tối ưu vi kiến trúc S5 và profiling V3

Hạn của giai đoạn: **15/11 (Chủ nhật)**.

Giai đoạn P8 áp dụng chu trình APOD tiếp tục tối ưu hóa kernel S5 (Homography RANSAC), tập trung giải quyết bài toán Occupancy thấp (~25%) và chi phí launch tuần tự của kernel <code>compute_hypotheses</code> được ghi nhận từ báo cáo NCU của V2. Tuấn tối ưu kernel S5 V3. Thành ghép <code>v3_pipeline</code> và CLI <code>--version 3</code>. Đế chạy benchmark, profiling Nsight và lập báo cáo APOD V3. Chương và Thành cùng phụ trách P8-T04. Chương bàn giao bộ kiểm thử và notebook, Thành chạy nghiệm thu trên Colab T4 sau khi có bản tích hợp.

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
      <td>Tuấn</td>
      <td>P8-T01</td>
      <td>Thiết kế và cài đặt tối ưu vi kiến trúc kernel S5 V3 trong <code>src/v3/s5/</code></td>
      <td>P7-T01</td>
      <td>Người làm tự lựa chọn giải pháp kỹ thuật tối ưu vi kiến trúc để giải quyết bài toán Occupancy thấp (~25%) và overhead điều phối của <code>compute_hypotheses</code> trong S5 V2; build sạch bằng <code>nvcc -arch=sm_75</code>; giữ nguyên phương pháp và tham số V0; kết quả nhất quán với V0 (dung sai số học) trên 6 cặp synthetic; đạt bài test đơn vị của stage</td>
      <td>Xong</td>
      <td>13/11, nhánh <code>tuan/p8</code>: tối ưu vi kiến trúc S5 V3 (warp shuffle MSAC reduction không tốn scratch toàn cục, ma trận SVD trong shared memory, launch bounds 128/4, batch size 128). Colab Tesla T4: build <code>sm_75</code> sạch, đạt toàn bộ 16.624 checks suite <code>gpu_v3_s5</code> (11 fixture đơn vị, max_cpu_gpu_px = 0); <code>compute-sanitizer</code> xác nhận 0 lỗi, 0 byte rò rỉ bộ nhớ.</td>
    </tr>
    <tr>
      <td>Thành</td>
      <td>P8-T02</td>
      <td>Ghép nối <code>src/v3/v3_pipeline</code> và mở rộng CLI <code>--version 3</code></td>
      <td>P8-T01</td>
      <td>Người làm tự thiết kế kiến trúc điều phối và quản lý workspace; đảm bảo timer <code>cudaEvent_t</code> đo chuẩn xác <code>Total_Kernel_ms</code>, H2D, D2H và từng stage mà không tạo overhead; ghép <code>src/v3/v3_pipeline.{h,cu}</code> gọi S5 V3 mới và tái sử dụng S1–S4, S6 từ <code>src/v1/</code>; CLI <code>./stitch ... --version 3</code> chạy thông suốt và xuất đủ 11 cột CSV; các test Python không bị hồi quy</td>
      <td>Xong</td>
      <td>16/11, đã merge <a href="https://github.com/nh-atuan/panorama-stitching/pull/39">PR #39</a> vào <code>main</code>. Pipeline V3 gọi S5 V3 và tái sử dụng S1–S4, S6 của V1. Colab T4 xác nhận build <code>sm_75</code>, CLI <code>--version 3</code> và CSV 11 cột đạt kiểm tra. Xem <a href="report/p8-v3-verification.md#8-cli-and-csv-verification">kết quả CLI và CSV</a>.</td>
    </tr>
    <tr>
      <td>Đế</td>
      <td>P8-T03</td>
      <td>Đo benchmark V3 trên Colab T4, thu thập profiling Nsight và hoàn thành báo cáo APOD V3</td>
      <td>P8-T01, P8-T02</td>
      <td>Đo thời gian V3 trên Colab T4 (5 runs + warm-up), đối chiếu speedup với V0, V1 và V2; người làm tự lựa chọn các metric NCU/NSYS để phân tích vi kiến trúc kernel S5 V3; xuất đủ CSV và biểu đồ speedup vào Drive chung <code>v3/</code>; cập nhật <code>docs/apod-log.md</code> và hoàn thành mục báo cáo APOD V3 trong <code>docs/report/</code></td>
      <td>Xong</td>
      <td>16/11: Đế đã chạy <a href="../experiments/Group16_P8_T03_Benchmark_Profiling.ipynb">benchmark V0–V3</a> trên cùng phiên Tesla T4, một warm-up + 5 runs/cấu hình. V3/V2 trung bình nhân 1,85× trên 9 cấu hình chuẩn; 8/9 cấu hình nhanh hơn. Đã thu 30/30 mẫu NSYS/NCU và hoàn tất <a href="report/p8-t03-v3-apod.md">báo cáo APOD</a>. Đã cập nhật <code>apod-log.md</code> và hoàn tất bàn giao Drive chung <code>v3/</code>; PR #40 đã merge vào <code>main</code>.</td>
    </tr>
    <tr>
      <td>Chương, Thành</td>
      <td>P8-T04</td>
      <td>Xây dựng suite kiểm tra tích hợp CLI V3 trong <code>tests/</code> và kiểm tra an toàn bộ nhớ trên Colab T4</td>
      <td>P8-T01, P8-T02</td>
      <td>Người làm tự thiết kế bộ test case và kịch bản nghiệm thu trong <code>tests/gpu/test_gpu_v3_pipeline.cu</code>; đối chiếu H và canvas của V3 với V0/V1/V2 trên synthetic và dataset thật; chạy <code>compute-sanitizer</code> trên Colab Tesla T4 nghiệm thu 0 lỗi, 0 byte rò rỉ bộ nhớ</td>
      <td>Xong</td>
      <td>Chương bàn giao suite, harness CLI và <a href="../experiments/Group16_P8_V3_Verification.ipynb">notebook Colab T4</a> qua <a href="https://github.com/nh-atuan/panorama-stitching/pull/37">PR #37</a>. Thành chạy nghiệm thu trên T4 ngày 16/11 tại SHA production <code>1cf86ad</code> và đưa kết quả vào <a href="https://github.com/nh-atuan/panorama-stitching/pull/39">PR #39</a>. Cả hai PR đã merge vào <code>main</code>. Cả 6 cặp synthetic đạt ngưỡng, 12/12 cấu hình ảnh thật khớp trạng thái, 10 panorama có Max RGB = 0, CLI/CSV/D2H đạt và hai lượt memcheck báo 0 lỗi, 0 byte rò rỉ. Xem <a href="report/p8-v3-verification.md">báo cáo và bằng chứng nghiệm thu</a>.</td>
    </tr>
  </tbody>
</table>

## P9 - Tối ưu S6 V4 và chuẩn bị khung bài nộp cuối kỳ

Hạn của giai đoạn: **19/11 (Thứ 5)**.

Giai đoạn P9 kết hợp hai nhánh công việc chạy song song: tối ưu hóa kernel S6 (Single-pass Canvas Fusion) giải quyết điểm nghẽn mới lộ diện tại <code>site2/large</code> của V3, và chuẩn bị khung hạ tầng bài nộp cuối kỳ (khung slide thuyết trình Beamer và sườn notebook báo cáo 10 mục). Các thành viên làm việc độc lập ngay từ đầu giai đoạn: Tuấn và Đế phụ trách khung slide Beamer; Chương và Thành phụ trách sườn notebook <code>Group16_Final.ipynb</code>; Chương phát triển kernel S6 V4; Thành dựng scaffold pipeline và CLI <code>--version 4</code>; Tuấn xây dựng suite kiểm tra tích hợp CLI V4 và nghiệm thu memcheck; Đế đo benchmark V4, thu thập profiling Nsight và hoàn thành báo cáo APOD V4.

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
      <td>P9-T01</td>
      <td>Xây dựng khung slide thuyết trình bằng LaTeX (Beamer) và chuẩn bị sơ bộ cho video thuyết trình (phối hợp cùng Đế)</td>
      <td></td>
      <td>Người làm toàn quyền tự quyết định cấu trúc, theme, bố cục và nội dung các slide Beamer theo ý tưởng của nhóm (đề bài không ràng buộc cố định bố cục slide); biên dịch PDF sạch lỗi, chừa sẵn khung cho hình ảnh và số liệu các phiên bản tối ưu; kèm chuẩn bị sơ bộ cho video thuyết trình (lập dàn ý kịch bản, phân bổ thời lượng 20–30 phút và chuẩn bị tài liệu trực quan, chưa quay video hoàn chỉnh); Tuấn phụ trách cấu trúc chung của slide, phần tổng quan/pipeline và dàn ý kịch bản video</td>
      <td>Xong</td>
      <td>19/11: Tuấn và Đế phối hợp hoàn thành khung deck thuyết trình Beamer trong <code>slides/project.tex</code>, module hiệu năng <code>slides/performance.tex</code> và kịch bản video sơ bộ trong <code>slides/video-outline.md</code>; đã merge qua PR #46.</td>
    </tr>
    <tr>
      <td>P9-T02</td>
      <td>Xây dựng suite kiểm tra tích hợp CLI V4 trong <code>tests/</code> và kiểm tra an toàn bộ nhớ trên Colab T4</td>
      <td>P9-T04, P9-T08</td>
      <td>Người làm tự thiết kế kịch bản kiểm thử trong <code>tests/gpu/test_gpu_v4_pipeline.cu</code>; đối chiếu H, canvas và Max RGB ≤ 1 với V0/V1/V2/V3 trên 6 cặp synthetic và 12 cấu hình thật; chạy <code>compute-sanitizer</code> trên Colab Tesla T4 nghiệm thu 0 lỗi, 0 byte rò rỉ bộ nhớ</td>
      <td>Xong</td>
      <td>17/11: Nhánh <code>tuan/p9</code>, đã merge <a href="https://github.com/nh-atuan/panorama-stitching/pull/45">PR #45</a> vào <code>main</code>. Hoàn thành suite C++/CUDA <code>tests/gpu/test_gpu_v4_pipeline.cu</code> kiểm tra 4 tầng, harness CLI <code>scripts/verify_v4_cli.py</code> (CSV 11 cột, CLI âm, D2H canvas mở rộng), đăng ký suite <code>gpu_v4_pipeline</code> trong <code>tests/run_tests.py</code> và cập nhật notebook nghiệm thu <code>Group16_P9_V4_Verification.ipynb</code>. Colab T4 tại <code>ab8df98</code>: 6 cặp synthetic đạt RMSE ≤ 0,100 px, Max ≤ 0,209 px, drift so với V0–V3 ≤ 4,56e-13 px, Max RGB = 0; 12 cấu hình thật khớp 100% trạng thái V0–V4 (10 ca thành công có drift = 0 và Max RGB = 0, 2 ca challenge medium/large lỗi <code>NumericalFailure</code> tại S6 như thiết kế); <code>compute-sanitizer --tool memcheck --leak-check full</code> đạt 0 lỗi và 0 byte rò rỉ cho cả suite V4 và CLI production; báo cáo nghiệm thu chi tiết tại <a href="report/p9-v4-verification.md">docs/report/p9-v4-verification.md</a>.</td>
    </tr>
    <tr>
      <td rowspan="2">Thành</td>
      <td>P9-T03</td>
      <td>Xây dựng sườn báo cáo notebook cuối kỳ <code>Group16_Final.ipynb</code> đủ 10 mục theo đề bài (phối hợp cùng Chương)</td>
      <td></td>
      <td>Người làm tự thiết kế các hàm nạp dữ liệu, xuất bảng biểu và trực quan hóa kết quả; tích hợp với khung 10 mục của notebook; chuẩn bị sẵn code vẽ biểu đồ speedup đa phiên bản và hiển thị gallery</td>
      <td>Xong</td>
      <td>17/11: Nhánh <code>thanh/p9</code>, đã merge <a href="https://github.com/nh-atuan/panorama-stitching/pull/44">PR #44</a> vào <code>main</code>. Thành thêm <code>scripts/final_notebook.py</code> (tải và kiểm tra dataset, build, chạy một lượt benchmark cho mọi phiên bản CLI nhận, nạp dữ liệu, bảng, biểu đồ, gallery) cùng suite <code>test_final_notebook.py</code> (19 test), và chèn cell vào các điểm <code>thanh-*</code> của notebook; lời văn các cell này viết bằng tiếng Việt. Colab T4 tại <code>8588ec6</code>: notebook chạy hết từ đầu đến cuối bằng <code>jupyter nbconvert --execute</code> với dataset tải mới và thư mục benchmark mới, exit 0; lượt benchmark gồm V0–V4 và challenge.</td>
    </tr>
    <tr>
      <td>P9-T04</td>
      <td>Ghép nối <code>src/v4/v4_pipeline</code> và mở rộng CLI <code>--version 4</code></td>
      <td>P9-T08</td>
      <td>Người làm tự thiết kế điều phối pipeline; tạo trước scaffold CLI V4; tích hợp kernel S6 V4 mới và tái sử dụng S1–S4 V1, S5 V3; gắn timer <code>cudaEvent_t</code> đo chuẩn xác 11 cột CSV; CLI <code>./stitch ... --version 4</code> chạy thông suốt và xuất đủ 11 cột CSV; các test Python không bị hồi quy</td>
      <td>Xong</td>
      <td>17/11: Nhánh <code>thanh/p9</code>, đã merge <a href="https://github.com/nh-atuan/panorama-stitching/pull/44">PR #44</a> vào <code>main</code>. <code>src/v4/v4_pipeline.{h,cu}</code> chạy S1–S4 của V1, S5 V3 và S6 V4; <code>run_gpu_stages</code> nhận thêm tham số <code>warp_blend</code> (mặc định <code>v1_warp_blend</code>), CSV V4 dùng thứ tự cột của V1 (<a href="interface.md#114-timing-và-csv-v1v2v3v4">interface mục 11.4</a>). Colab T4 tại <code>b4a509f</code>: build <code>sm_75</code> đạt; 14 suite V0 (45284 checks), 14 suite GPU (68297 checks), 10 suite Python (145 test) đạt. CLI V4 trên 12 cấu hình thật đạt chuẩn, memcheck 0 lỗi.</td>
    </tr>
    <tr>
      <td rowspan="2">Đế</td>
      <td>P9-T05</td>
      <td>Đo benchmark V4 trên Colab T4, thu thập profiling Nsight và hoàn thành báo cáo APOD V4</td>
      <td>P9-T04, P9-T08</td>
      <td>Người làm tự lựa chọn metric NCU/NSYS để phân tích hiệu quả giảm truy cập bộ nhớ của kernel S6 V4; đo thời gian V4 trên Colab T4 (5 runs + warm-up) cùng phiên với V0–V3; xuất đủ CSV và biểu đồ speedup vào Drive chung <code>v4/</code>; cập nhật <code>docs/apod-log.md</code> và hoàn thành mục báo cáo APOD V4 trong <code>docs/report/</code></td>
      <td>Xong</td>
      <td>19/11: Nhánh <code>de/p9</code>, đã merge <a href="https://github.com/nh-atuan/panorama-stitching/pull/46">PR #46</a> vào <code>main</code>. Đã đo V0–V4 trên cùng T4, phân tích 8 NSYS và 12 NCU, cập nhật APOD. V4/V3 đạt 1,0086× toàn pipeline và 1,0357× ở S6. Gói bàn giao đã chuẩn bị và upload Drive nhóm. <a href="report/p9-t05-v4-apod.md">Báo cáo và bằng chứng</a>.</td>
    </tr>
    <tr>
      <td>P9-T06</td>
      <td>Xây dựng nội dung khung slide thuyết trình bằng LaTeX (Beamer) và chuẩn bị tư liệu video (phối hợp cùng Tuấn)</td>
      <td></td>
      <td>Người làm toàn quyền tự quyết định cách trình bày nội dung trên slide Beamer; phối hợp cùng Tuấn trên cùng mã nguồn Beamer; Đế phụ trách nội dung phân tích hiệu năng, chu trình APOD, profiling Nsight và bài học rút ra; chuẩn bị sẵn các bảng số liệu mẫu và danh mục tư liệu biểu đồ/timeline phục vụ cho video thuyết trình sau này</td>
      <td>Xong</td>
      <td>19/11: Nhánh <code>de/p9</code>, đã merge <a href="https://github.com/nh-atuan/panorama-stitching/pull/46">PR #46</a> vào <code>main</code>. Đã dựng khung Beamer toàn dự án (tổng quan S1–S6, demo, benchmark V0–V4, APOD và bài học) và tích hợp module hiệu năng của Đế. Có dàn ý video rút gọn 15 phút và danh mục tư liệu để review với Tuấn. <a href="../slides/README.md">Deck và hướng dẫn build</a> · <a href="../slides/video-outline.md">Kịch bản chung</a>.</td>
    </tr>
    <tr>
      <td rowspan="2">Chương</td>
      <td>P9-T07</td>
      <td>Xây dựng sườn báo cáo notebook cuối kỳ <code>Group16_Final.ipynb</code> đủ 10 mục theo đề bài (phối hợp cùng Thành)</td>
      <td></td>
      <td>Người làm tự thiết kế bố cục notebook theo chuẩn 10 mục của đề bài cuối kỳ; đưa sẵn các nội dung lý thuyết, phương pháp, phân tích V0–V3 từ <code>docs/report/</code> vào notebook; thiết lập cấu trúc cell chạy tuần tự từ trên xuống dưới sạch lỗi</td>
      <td>Xong</td>
      <td><a href="https://github.com/nh-atuan/panorama-stitching/pull/43">PR #43</a> đã merge vào <code>main</code> ngày 17/11. Phần Chương đã xong trên <code>chuong/p9</code>. <a href="../Group16_Final.ipynb">Notebook</a> có đủ 10 mục, trình bày phương pháp, phân tích V0–V3 và khung V4. Đã kiểm tra định dạng, liên kết và chạy tuần tự 8 cell code trên Python mới. Cell dữ liệu và trực quan hóa thuộc P9-T03 của Thành, số đo V4 thuộc P9-T05 của Đế.</td>
    </tr>
    <tr>
      <td>P9-T08</td>
      <td>Thiết kế và cài đặt tối ưu kernel S6 V4 (Single-pass Canvas Fusion) trong <code>src/v4/s6/</code></td>
      <td></td>
      <td>Người làm toàn quyền lựa chọn giải pháp kỹ thuật (Single-pass fused canvas rendering gộp clear, copy A, gather B; thread 2D); build sạch bằng <code>nvcc -arch=sm_75</code>; giữ nguyên phương pháp và tham số V0; kết quả nhất quán với V0 (Max RGB ≤ 1) trên fixture đơn vị và 6 cặp synthetic; mở PR trước 18/11 (Thứ 4)</td>
      <td>Xong</td>
      <td><a href="https://github.com/nh-atuan/panorama-stitching/pull/41">PR #41</a> đã merge vào <code>main</code> ngày 16/11. Phạm vi kernel S6 V4 đã build <code>sm_75</code> và kiểm thử trên GTX 1650. Cả 6 cặp synthetic dùng cùng <code>H_gt</code> khớp canvas/offset và Max RGB = 0. Nghiệm thu pipeline V4 và memcheck trên Colab T4 thuộc P9-T02.</td>
    </tr>
  </tbody>
</table>

## P10 - V5 hai CUDA stream và tích hợp kết quả vào bài nộp

**Hạn chốt bảy task: 23:59 thứ Ba 24/11/2026, giờ Việt Nam.** Chương điều phối P10. V5 thử chạy H2D và S1–S3 của hai ảnh trên hai stream, sau đó hội tụ trước S4. Bản đối chứng là V4 production đã nghiệm thu. Dùng kết quả T4 chính thức của Đế cho phần V4 trong báo cáo. Hạn nộp đồ án là 03/12. [Nghiệm thu V4](report/p9-v4-verification.md) · [Benchmark và APOD V4](report/p9-t05-v4-apod.md) · [Thiết kế thí nghiệm V5](report/v4-v5-optimization-plan.md)

| Task | Phụ trách | Loại việc · tải | Đầu ra cần bàn giao | Hạn (giờ Việt Nam) | Trạng thái | Ghi chú / PR |
|---|---|---|---|---|---|---|
| P10-T01 — Baseline và contract V5 | **Chương** | Thiết kế và đo baseline · Vừa | Chương tự rà evidence và thu baseline H2D đầu tiên đến khi S4 sẵn sàng trên `site1/large`, `site2/large`, `site3/large`, ghi điểm chờ ở S2 và VRAM còn trống. Chốt ca chính trước khi đo V5, giao diện xử lý một ảnh, ý nghĩa timing và ưu tiên lỗi. | **20/11 20:00** | Xong | 20/11: Đã nghiệm thu baseline Colab T4 tại SHA c4566e3. Năm lượt đo mỗi ca sau warm-up, 84 file khớp checksum, ba panorama probe khớp production và ba trace NSYS/SQLite đầy đủ. Giữ site2/large làm ca chính, pre-S4 mean 15,288 ms và share 21,44%. [Phân tích kết quả](report/p10-t01-pres4-baseline.md) · [Contract đã chốt](report/p10-v5-contract.md). Chương tiếp tục T03 theo API bàn giao T02. |
| P10-T02 — Tách S1–S3 theo từng ảnh | **Thành** | C++/CUDA production · Nặng | Tách entry point một ảnh, scratch, counters/status và vùng host nhận candidate count theo nhánh. Tách bước phát hiện candidate của S2 khỏi bước hoàn tất top-K, khởi tạo BRIEF trước khi tách stream. Chạy A rồi B qua API mới và đối chiếu V4 về thứ tự keypoint cùng từng bit descriptor. | **21/11 18:00** | Chưa làm | Bàn giao API chạy được và kết quả đối chiếu cho Chương. |
| P10-T03 — Dispatcher hai stream, CLI và timing | **Chương** | C++/CUDA production · Nặng | Cài `v5_pipeline` và `--version 5`. Stream điều phối chờ `doneA` và `doneB`, hợp nhất status/counts, chạy S4–S6 rồi D2H. Có chế độ đối chứng nối tiếp dùng cùng API, workspace, pinned buffers và kernel. Giữ CSV chính tương thích runner, ghi timing từng nhánh và thời gian đến điểm hội tụ. Build `sm_75`, chạy thử cả hai chế độ, kiểm tra đường lỗi và thu hồi tài nguyên. | **22/11 10:00** | Bị chặn | Đã triển khai owner, hai mode dispatcher, join, CLI và timing trên chuong/p10-v5. Còn thiếu implementation T02 tại src/v5/v5_image_branch.cu và build/runtime CUDA. [Bàn giao T03](report/p10-t03-v5-handoff.md). V5 chỉ bật khi có T02 thực. |
| P10-T04 — Regression, memcheck và evidence V5 | **Tuấn** | Code test và nghiệm thu T4 · Nặng | Mở rộng suite V4 cho hai ảnh khác kích thước, nhánh thiếu feature, lỗi từng nhánh và lặp lại trên cùng workspace. So status → keypoint/descriptor → match → H → canvas/offset → RGB. Chạy 6 synthetic và 12 cấu hình thật theo ngưỡng đã dùng ở V4. Chạy memcheck cho suite và CLI, yêu cầu 0 lỗi, 0 byte rò rỉ. Đăng ký test vào runner, lưu SHA, manifest, bảng parity và log T4. | **22/11 22:00** | Chưa làm | Chuẩn bị suite ngay sau T01. Bàn giao SHA đã nghiệm thu cho Đế trước benchmark chính thức. |
| P10-T05 — Benchmark, NSYS và quyết định giữ V5 | **Đế** | Thực nghiệm và phân tích · Nặng khi có binary | So V4 production, prototype nối tiếp và prototype hai stream trên 9 ca chuẩn, ghi riêng challenge. Đo V0 cùng phiên để tính speedup V5/V0. Báo V5/V4, `Total_ms`, thời gian đến S4 và peak VRAM. Thu trace NSYS để xác định có overlap hay không và S4 bắt đầu khi nào. Bàn giao CSV, trace và báo cáo APOD có kết luận giữ hoặc dừng V5. | **23/11 22:00** | Chưa làm | Chuẩn bị script trước. Dùng SHA đạt T04, đủ một warm-up và ít nhất 5 lượt đo mỗi cấu hình. Thu profiling riêng. |
| P10-T06 — Tích hợp kết quả vào notebook | **Thành** làm cell, **Chương** chốt lời văn | Python và tài liệu · Vừa | Đưa V4 chính thức vào mục 6 ngay. Sau T05, bổ sung kết quả và giới hạn của V5 vào mục 6–7. Ghim `SOURCE_REF` tới SHA đủ helper và pipeline, chạy từ Colab trống, so lời văn với output và ghi nhận tình trạng cặp ảnh mẫu của môn học. | **24/11 20:00** | Đang làm | Phần V4 của Chương đã xong trên chuong/p10-t06-v4-notebook: bổ sung bảng P9 chính thức, speedup, profiling, nghiệm thu và phân tích trong mục 6, thêm nguồn ở mục 10 và cập nhật kết luận. Đã chạy 10 cell evidence trên kernel Python sạch, mọi số tái hiện từ report. Ghim source d42000c để Colab tải đủ helper. Phần V5 và lượt Run all cuối trên T4 còn chờ kết quả tích hợp. |
| P10-T07 — Chốt slide và kịch bản | **Tuấn**, phối hợp **Đế** | Tài liệu · Nhẹ–vừa | Dùng `slides/project.tex`. Tuấn chốt tổng quan, demo, phân vai và kịch bản 20–30 phút. Đế hoàn thiện phần hiệu năng và thêm kết luận V5 sau T05. Build deck Beamer và bàn giao kịch bản đủ để quay. | **24/11 20:00** | Chưa làm | Chuẩn bị deck và kịch bản song song với phần code. |

**Thứ tự nghiệm thu và benchmark.** T01 chốt giao diện để Thành và Chương triển khai T02/T03. Tuấn có thể viết fixture ngay khi có contract và chạy nghiệm thu tích hợp khi nhận SHA từ Chương. Nếu T04 phát hiện lỗi, Thành hoặc Chương sửa phần phụ trách, Tuấn xác nhận lại trên SHA mới rồi Đế mới đo chính thức. Nếu đến hạn chốt vẫn thiếu bằng chứng, nhóm ghi rõ kết quả đã kiểm chứng và dùng V4 cho bài nộp.

### Tiến độ bàn giao của Chương

- [x] **P10-T01** — Hoàn tất baseline T4, phân tích evidence, chốt ca chính và contract.
- [x] **P10-T03, phần code độc lập** — Đã triển khai owner, hai mode scheduling, join counts/status, downstream S4–S6, CLI, timing và D2H trong [draft PR #48](https://github.com/nh-atuan/panorama-stitching/pull/48).
- [x] **P10-T03, kiểm tra local** — Hồi quy V0 đạt 45.284 checks, Python đạt 187 test với một test cũ skip theo môi trường, CLI host build bằng g++ với Werror và đạt tám ca parse/error.
- [ ] **P10-T03, tích hợp API** — Chờ Thành bàn giao implementation T02 tại `src/v5/v5_image_branch.cu`, rồi build CUDA và chạy smoke cả sequential/dual. Chưa có SHA V5 đã chạy trên GPU.
- [x] **P10-T06, phần V4** — Hoàn thiện nội dung, output đọc báo cáo P9, biểu đồ, hình NSYS/NCU, bảng nghiệm thu và nguồn tham khảo trong notebook. Các cell evidence đã chạy trên Python mới.
- [ ] **P10-T06, phần V5 và chốt bản nộp** — Chốt kết luận V5 với Thành sau T04/T05, rồi chạy notebook đầy đủ trên Colab T4, lưu output và xuất PDF.

PR #48 đang draft và GitHub ghi nhận không có conflict tại lần rà soát này. Chuyển sang review tích hợp sau khi có T02 và kết quả build/smoke CUDA. Phạm vi nghiệm thu đầy đủ T4 thuộc T04. [Bàn giao T03 và giới hạn kiểm chứng](report/p10-t03-v5-handoff.md)

**Tiêu chí đánh giá V5.** Theo kế hoạch thí nghiệm, trên ca chính chạy 5 khối đo ghép cặp luân phiên thứ tự V4/V5. Đề xuất giữ V5 khi đạt correctness/memcheck, trace có overlap, thời gian đến S4 giảm, median speedup end-to-end đạt ít nhất 1,05× và ít nhất 4/5 khối cùng chiều. Đo lại các ca nghi ngờ để kiểm tra không có ca chuẩn nào chậm quá 5%. `Total_Kernel_ms` cộng thời lượng từng kernel nên có thể tính cả các khoảng chồng lấn. Dùng `Total_ms` sau D2H để kết luận về tốc độ toàn pipeline.

## P11 - Chốt tài liệu tĩnh, tái cấu trúc codebase và chuẩn bị demo

Hạn của giai đoạn: **23/11 (Thứ 2)**.

Giai đoạn P11 tập trung chốt toàn bộ các tài liệu tĩnh của dự án, tái cấu trúc codebase khoa học và chuyên nghiệp, tổng duyệt kiểm thử toàn diện để đóng băng mã nguồn, rà soát và nghiệm thu notebook 10 mục (Thành và Chương phụ trách), biên dịch PDF slide Beamer và chuẩn bị công cụ Live Demo phục vụ quay video ở P12.

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
      <td>P11-T01</td>
      <td>Tái cấu trúc codebase, dọn dẹp repo và chuẩn hóa <code>README.md</code> chính</td>
      <td></td>
      <td>Repo gọn gàng, chuyên nghiệp; dọn dẹp thư mục gốc; chuẩn hóa comment tác giả 100% file nguồn; <code>README.md</code> có đầy đủ sơ đồ kiến trúc, bảng so sánh V0–V5 và hướng dẫn build/run/test</td>
      <td>Xong</td>
      <td>21/11, nhánh <code>tuan/p11</code> (<code>f2837a8</code>): gom 9 notebook phụ vào <code>experiments/</code> (kèm <code>experiments/README.md</code>), cập nhật toàn bộ liên kết trong <code>docs/</code> và <code>test_midterm_notebook.py</code>; rà 178/178 file nguồn đủ header; viết lại <code>README.md</code> chuẩn nộp bài V0–V5, cập nhật <code>src/README.md</code>, <code>tests/README.md</code> và đồng bộ <code>docs/apod-log.md</code>.</td>
    </tr>
    <tr>
      <td>P11-T02</td>
      <td>Tổng duyệt kiểm thử hồi quy toàn diện trên Colab T4 và đóng băng mã nguồn <code>src/</code></td>
      <td>P11-T01</td>
      <td>Toàn bộ 14 suite V0, 14 suite GPU (V1–V5), 193 test Python đạt sạch trên Colab T4; <code>compute-sanitizer</code> xác nhận 0 lỗi, 0 byte rò rỉ; chốt đóng băng mã nguồn</td>
      <td>Xong</td>
      <td>21/11, nhánh <code>tuan/p11</code> (Colab Tesla T4, driver 580.82.07, nvcc 13.0.88, SHA <code>f2837a8</code>): build <code>sm_75</code> đạt; 14 suite V0 (45.284 checks), 16 suite GPU V1–V5 (69.336 checks), 15 suite Python (193 tests) đạt; <code>compute-sanitizer</code> trên <code>gpu_v4_pipeline</code> và <code>gpu_v5_pipeline</code> đạt 0 lỗi, 0 byte rò rỉ. Chi tiết tại <a href="report/p11-t02-freeze-verification.md">báo cáo đóng băng mã nguồn</a>.</td>
    </tr>
    <tr>
      <td rowspan="2">Thành</td>
      <td>P11-T03</td>
      <td>Chuẩn hóa bộ công cụ <code>scripts/</code> và xây dựng công cụ Live Demo 1-click</td>
      <td></td>
      <td>Rà soát các script đo đạc; hoàn thiện <code>scripts/live_demo.py</code> kèm hướng dẫn chạy demo CLI mượt mà phục vụ riêng cho khâu quay video của Thành ở P12</td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td>P11-T04</td>
      <td>Rà soát, chuẩn hóa văn phong và hình thức notebook bài nộp 10 mục</td>
      <td></td>
      <td>Rà soát toàn diện <code>Group16_Final.ipynb</code>; trau chuốt văn phong tiếng Việt khoa học tự nhiên theo chuẩn; hoàn thiện công thức KaTeX, bảng biểu, sơ đồ</td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td>Đế</td>
      <td>P11-T05</td>
      <td>Hoàn thiện slide thuyết trình Beamer và đồng bộ số liệu APOD</td>
      <td></td>
      <td>Hoàn thiện <code>slides/project.tex</code> và <code>slides/performance.tex</code>; đồng bộ 100% số liệu speedup V0–V5; biên dịch PDF slide chính thức 16:9 sắc nét</td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td>Chương</td>
      <td>P11-T06</td>
      <td>Nghiệm thu thực thi trọn vẹn notebook trên Colab T4 và xuất file PDF bài nộp</td>
      <td>P11-T04</td>
      <td>Chạy <code>Run all</code> trên Colab T4 mới exit 0; lưu sẵn output đầy đủ; đối chiếu số liệu văn bản khớp 100% output cell; xuất bản in PDF <code>Group16_Final.pdf</code></td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
  </tbody>
</table>

## P12 - Quay video thuyết trình

Kế hoạch chi tiết được lập sau khi hoàn thành P11. Giai đoạn P12 tập trung quay và thu thập đầy đủ tư liệu thô của 4 phần video theo đúng yêu cầu đề bài (tổng thời lượng 20–30 phút, chuẩn 1080p, thu âm rõ ràng, video phải có mặt người nói):
- **Tuấn (4–6 phút)** — *Problem overview and approach*
- **Thành (6–9 phút)** — *Live demonstration of running code*
- **Đế (6–9 phút)** — *Performance results and analysis*
- **Chương (4–6 phút)** — *Key optimizations and lessons learned*

Đầu ra cần bàn giao: Thư mục chứa link video/source sẽ cập nhật sau.

## P13 - Biên tập video và cập nhật bài nộp

Kế hoạch chi tiết được lập sau khi hoàn thành P12. Giai đoạn P13 tập trung biên tập hậu kỳ video hoàn chỉnh và cập nhật các thành phần bài nộp:
- **Tuấn** — Biên tập và render video thuyết trình, upload YouTube Unlisted
- **Thành & Chương** — Nhúng link video vào notebook, README và xuất bản PDF bài nộp
- **Đế & Cả nhóm** — Nghiệm thu video và rà soát bài nộp trước khi đóng gói

Đầu ra cần bàn giao: Video YouTube Unlisted hoàn chỉnh, link video đã được nhúng vào notebook & README, file PDF notebook đã được cập nhật.

## P14 - Họp nhóm tổng duyệt thử thuyết trình

Kế hoạch chi tiết được lập sau khi hoàn thành P13. Giai đoạn P14 chuẩn bị sẵn sàng cho buổi bảo vệ vấn đáp / thuyết trình trực tiếp trước giảng viên (10 phút thuyết trình slide + 5 phút vấn đáp):
- **Từng thành viên** — Tinh chỉnh slide thuộc phần mình và chuẩn bị bài nói
- **Cả nhóm** — Chuẩn bị câu hỏi vấn đáp tiềm năng và phản biện chéo
- **Cả nhóm** — Họp tổng duyệt dry run, khớp giờ 10 phút thuyết trình và 5 phút vấn đáp

Đầu ra cần bàn giao: Bản slide thuyết trình hoàn thiện và khớp giờ toàn bộ bài nói của nhóm.

Mốc nộp bài cuối cùng: **04/12 (Thứ 6)** — Kiểm tra toàn bộ checklist mục 9 của kế hoạch cuối kỳ, đóng gói zip bài nộp và chính thức nộp bài.

## Quyết định đã chốt

Ghi lại các quyết định cả Nhóm đã thống nhất trong quá trình làm.

| Ngày | Quyết định |
|---|---|
| 18/10 | Chốt dataset: site1 `thanh-standard1`, site2 `tuan-standard2`, site3 `de-standard2`, challenge `chuong-challenge1` (chi tiết ở dataset mục 8) |
| 18/10 | Nhóm đồng ý Tuấn làm thay toàn bộ task của Thành ở P0, P1 và phần còn lại của Đế, Chương trước P3; dòng `Authors:` ghi người thực sự viết. Thành xác nhận phương pháp và tham số S2, S3 như tài liệu stage |
| 18/10 | Chương được miễn cặp chuẩn thứ hai theo dataset mục 2, vì bộ dataset đã chốt |
| 18/10 | Ngưỡng sai số homography so với ground truth (P1-T01): RMSE ≤ 0.5 px và Max ≤ 1 px trên cả 6 cặp synthetic ở mục 5.5 tài liệu S5 |
| 21/10 | P3-T01: V1 cài kernel cho cả 6 stage; V2, V3 ưu tiên tối ưu S2, S4, S6, ba stage chiếm nhiều thời gian nhất ở cả ba độ phân giải. Ước lượng Amdahl tính p cho S2 + S4 + S6; không tính cho cả 6 stage vì p gần bằng 1. Phân công V1-V3 giữ như mục 2 của kế hoạch |
| 21/10 | Notebook không cần comment tác giả; yêu cầu ở mục 9.3 của kế hoạch chỉ áp dụng cho file code |
| 24/10 | Nhóm trưởng xác nhận các thành viên đã xác nhận nội dung phần mình; P4 không chờ xác nhận lại. Tiếp tục đối chiếu bản notebook cuối với output mới trước khi nghiệm thu |
| 03/11 | Tuấn và cả Nhóm đồng ý để Thành làm thay P5-T03 (V1 cho S1); dòng `Authors:` ghi Thành. Tuấn vẫn phụ trách tài liệu S1 và xem lại phần V1 khi review |
| 03/11 | Nhóm trưởng chốt bộ dataset cuối kỳ: site1 `thanh-standard1`, site2 `thanh-standard2` (thay `tuan-standard2` để triệt tiêu bóng ma parallax, chấp nhận overlap ~58% của cảnh đường ngoài trời), site3 `de-standard2`, challenge `de-challenge1` (thay `chuong-challenge1` để tạo ca thất bại thực sự do hoa văn lặp trần/lan can). Tiến hành chạy `prepare_dataset.py` và cập nhật Drive chung |
| 03/11 | Nhóm trưởng chốt layout output của công cụ benchmark đa phiên bản (P5-T05): dùng cấu trúc phân cấp `<out>/v<k>/<site>/<size>.csv` cho bài nộp cuối kỳ (`Group16_Final.ipynb`); không ràng buộc tương thích ngược với notebook giữa kỳ |
| 03/11 | Chốt kế hoạch Phase 6 (hạn 08/11): thu hẹp còn 5 ngày để giữ nhịp tiến độ; thiết kế các task độc lập tối đa ngay từ đầu phase (Thành chạy trước benchmark V0, Đế chạy trước NCU các kernel stage, Tuấn viết target runner test tích hợp, Chương ghép `v1_pipeline`); Đế phụ trách thu thập NSYS toàn pipeline, phân tích ca lỗi `challenge` và chốt báo cáo bottleneck V1/đề xuất V2. Cập nhật mốc nộp bài cuối kỳ sang 03/12 (Thứ 5) |
| 03/11 | Chốt hạn chót nội bộ cho P6-T01 (Chương): phải hoàn thành ghép `v1_pipeline` và mở PR chậm nhất trong 2 ngày (05/11, Thứ 5) để gỡ nghẽn cho các task phụ thuộc (Tuấn chạy compute-sanitizer, Thành đo benchmark V1, Đế thu thập NSYS toàn pipeline); lưu ý Chương xử lý cấp phát động buffer output Host tránh tràn bộ nhớ khi canvas mở rộng |
| 06/11 | Nhóm đồng ý để Thành làm thay P6-T01 (ghép `v1_pipeline`) vì task chưa bắt đầu sau 05/11; dòng `Authors:` ghi Thành, code chuyển từ `main.cu` giữ tên Chương. `Total_Kernel_ms` của V1 tạm để 0 (chưa đo); cách đo kernel time được báo lại cho cả Nhóm để cùng quyết định |
| 06/11 | Tuấn (nhóm trưởng) review và merge PR #31 vào main gỡ nghẽn pipeline V1; Tuấn tiếp quản các task P6-T04 (đo NCU kernel) và P6-T05 (đo NSYS, phân tích ca lỗi challenge, báo cáo bottleneck V1) của Đế trên nhánh `tuan/p6` do Đế bận; dòng `Authors:` ở tài liệu và test mới ghi Tuấn |
| 07/11 | Nhóm trưởng chốt kế hoạch Phase 7 (hạn 10/11, Thứ 3): nhịp chạy sprint 3 ngày/version để mở rộng lên V4, V5, V6 mà vẫn giữ đủ 11 ngày chuẩn bị bài nộp cuối; áp dụng chu trình APOD chọn S5 (Homography RANSAC) làm mục tiêu tối ưu của V2 do chiếm 90–98% thời gian V1; phân công cân bằng kỹ thuật: Tuấn (kernel S5 V2), Thành (timer cudaEvent & v2_pipeline), Chương (test tích hợp V2 & compute-sanitizer T4), Đế (benchmark V2, profiling Nsight & báo cáo APOD V2); không đo lại V0 trong P7 |
| 07/11 | Chốt cấu trúc lưu trữ kết quả trên Drive chung theo mô hình Version Package ([CSC14120_Group16_Results](https://drive.google.com/drive/folders/1uJ-4_kgVONvIt5NQIPzdEWTIPrg8Sue1?usp=sharing)), quy ước chi tiết tại [docs/results-guide.md](results-guide.md) và nhật ký APOD tại [docs/apod-log.md](apod-log.md) |
| 12/11 | Chốt kế hoạch Phase 8 (hạn 15/11, Chủ nhật): sprint 3 ngày tập trung tối ưu vi kiến trúc kernel S5 V3 (giải quyết nút thắt Occupancy và launch overhead của `compute_hypotheses`); phân công theo thứ tự stage: Tuấn (kernel S5 V3), Thành (v3_pipeline & CLI), Đế (benchmark V3, profiling Nsight & báo cáo APOD V3), Chương (test tích hợp V3 & compute-sanitizer T4); các thành viên tự quyết định giải pháp kỹ thuật trong phạm vi module mình phụ trách; xác nhận hoàn tất nghiệm thu P7-T01 |
| 16/11 | Chốt kế hoạch Phase 9 (hạn 19/11, Thứ 5): sprint 3 ngày kết hợp hai nhánh việc chạy song song: tối ưu kernel S6 V4 (Single-pass Canvas Fusion giải quyết điểm nghẽn mới lộ diện tại site2/large của V3) và chuẩn bị khung bài nộp cuối kỳ (khung slide Beamer do người làm tự quyết định bố cục, kèm chuẩn bị sơ bộ cho video thuyết trình, và sườn notebook Group16_Final.ipynb); phân công độc lập: Tuấn & Đế (khung slide Beamer & chuẩn bị tư liệu video), Chương & Thành (sườn notebook 10 mục), Chương (kernel S6 V4), Thành (v4_pipeline & CLI), Tuấn (test tích hợp V4 & memcheck T4), Đế (benchmark V4, profiling Nsight & báo cáo APOD V4); các thành viên toàn quyền tự quyết phương án kỹ thuật và thiết kế trong phạm vi module mình phụ trách; video thuyết trình chính thức sẽ thực hiện tập trung ở giai đoạn sau |
| 20/11 | Chốt bảy task P10 đến 23:59 thứ Ba 24/11. Chương điều phối, chốt baseline với Đế và triển khai dispatcher V5. Thành tách S1–S3, Tuấn nghiệm thu trên T4, Đế đo benchmark và profiling. Thành và Chương tích hợp kết quả vào notebook, Tuấn và Đế chốt slide và kịch bản. |
| 20/11 | Chốt lộ trình 4 giai đoạn cuối hoàn thiện bài nộp: P11 (hạn 23/11), P12, P13, P14 (họp thử thuyết trình 10 phút + 5 phút vấn đáp), mốc nộp bài 04/12 |
| 20/11 | Chốt phân công P11 (6 task) và phân vai P12: P11 gồm Tuấn (codebase, README & regression), Thành (scripts/demo & văn phong notebook), Đế (slide Beamer & số liệu APOD), Chương (nghiệm thu Colab T4 & PDF notebook); P12 quay video: Tuấn (Overview), Thành (Live demo), Đế (Performance), Chương (Optimizations & lessons); Tuấn edit chính ở P13 |
