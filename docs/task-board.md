<!-- Authors: Le Thuong De (23120232), Nguyen Ho Anh Tuan (23120185). External source: none. -->

# Bảng công việc

Quy tắc chung nằm trong [kế hoạch cuối kỳ](final-plan.md) (mốc hoàn thành **03/12 (Thứ 5)**). Bảng công việc và kế hoạch giữa kỳ (các giai đoạn P0–P4) được lưu trữ tại [kế hoạch giữa kỳ](archive/midterm-plan.md) và [bảng công việc giữa kỳ](archive/midterm-task-board.md).

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
      <td>Chờ review</td>
      <td></td>
    </tr>
    <tr>
      <td>Thành</td>
      <td>P7-T02</td>
      <td>Bổ sung cơ chế đo thời gian <code>cudaEvent_t</code> trong <code>src/main.cu</code> và ghép nối <code>src/v2/v2_pipeline</code></td>
      <td>P6-T01</td>
      <td>Gắn <code>cudaEventRecord</code> quanh các kernel stage trên Device để đo chuẩn <code>Total_Kernel_ms</code>, H2D, D2H; ghép <code>src/v2/v2_pipeline.{h,cu}</code> gọi S5 V2 mới và tái sử dụng S1–S4, S6 từ <code>src/v1/</code>; CLI <code>./stitch ... --version 2</code> chạy thông suốt và xuất đủ 11 cột CSV; các test Python không bị hồi quy</td>
      <td>Đang làm</td>
      <td>07/11 Chương triển khai pipeline V2, CLI và CUDA event timing trên <code>chuong/p7</code>. V2 gọi S5 V2, dùng lại S1–S4/S6 của V1; V1/V2 cùng đo thời gian kernel và parser đọc đúng CSV từng phiên bản. Đã build và kiểm tra cục bộ, chờ bằng chứng Colab T4 và review.</td>
    </tr>
    <tr>
      <td>Đế</td>
      <td>P7-T03</td>
      <td>Đo benchmark V2 trên Colab T4, thu thập profiling Nsight và hoàn thành báo cáo APOD V2</td>
      <td>P7-T01, P7-T02</td>
      <td>Đo thời gian V2 trên Colab T4 (5 runs + warm-up), đối chiếu speedup với V0 và V1; thu thập trace timeline NSYS và chỉ số NCU cho kernel S5 V2; xuất đủ CSV và biểu đồ speedup vào Drive <a href="https://drive.google.com/drive/folders/1uJ-4_kgVONvIt5NQIPzdEWTIPrg8Sue1?usp=sharing"><code>v2/</code></a> (xem <a href="results-guide.md">hướng dẫn</a>); cập nhật <a href="apod-log.md">apod-log.md</a> và hoàn thành mục báo cáo V2 trong <code>docs/report/</code></td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td>Chương</td>
      <td>P7-T04</td>
      <td>Xây dựng suite kiểm tra tích hợp CLI V2 trong <code>tests/</code> và kiểm tra an toàn bộ nhớ trên Colab T4</td>
      <td>P7-T01, P7-T02</td>
      <td>Tạo suite C++/CUDA <code>tests/gpu/test_gpu_v2_pipeline.cu</code> đối chiếu H và canvas của V2 với V0/V1 trên synthetic và dataset thật; chạy <code>compute-sanitizer</code> trên Colab Tesla T4 nghiệm thu 0 lỗi, 0 byte rò rỉ bộ nhớ</td>
      <td>Đang làm</td>
      <td>07/11 đã nối suite vào pipeline V2 thật. Suite đạt 175 checks trên GTX 1650, gồm sáu cặp synthetic. <a href="../Group16_P7_V2_Verification.ipynb">Notebook Colab T4</a> nhận gói source tích hợp để chạy 12 cấu hình và memcheck. Theo dõi bằng chứng tại <a href="report/p7-v2-verification.md">báo cáo P7-T04</a>.</td>
    </tr>
  </tbody>
</table>

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
