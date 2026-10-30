<!-- Authors: Le Thuong De (23120232), Nguyen Ho Anh Tuan (23120185). External source: none. -->

# Bảng công việc

Quy tắc chung nằm trong [kế hoạch cuối kỳ](final-plan.md) (mốc hoàn thành **27/11 (Thứ 6)**). Bảng công việc và kế hoạch giữa kỳ (các giai đoạn P0–P4) được lưu trữ tại [kế hoạch giữa kỳ](archive/midterm-plan.md) và [bảng công việc giữa kỳ](archive/midterm-task-board.md).

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
      <td>Chưa làm</td>
      <td></td>
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
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td rowspan="4">Thành</td>
      <td>P5-T04</td>
      <td>Mở rộng khung kiểm thử trong <code>tests/</code> để hỗ trợ biên dịch, chạy nhóm test GPU và tiện ích đối chiếu kết quả stage GPU với V0</td>
      <td>P5-T02</td>
      <td>Runner kiểm thử hỗ trợ nhóm test GPU và tiện ích nạp dữ liệu tham chiếu V0, chạy đạt trên Colab T4</td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td>P5-T05</td>
      <td>Nâng cấp công cụ benchmark và vẽ biểu đồ trong <code>scripts/</code> hỗ trợ đo đa phiên bản, schema CSV mở rộng và tính speedup theo đề cuối kỳ</td>
      <td>P5-T12</td>
      <td>Script kèm bộ unit test Python tương ứng chạy đạt trên Colab T4</td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td>P5-T06</td>
      <td>Cài đặt, định nghĩa ngưỡng kiểm chứng và kiểm thử V1 cho S2</td>
      <td>P5-T04, P5-T12</td>
      <td>Đạt <a href="final-plan.md#9-tiêu-chí-hoàn-thành-một-task-và-checklist-nộp-bài">mục 9 của kế hoạch cuối kỳ</a>; test đối chiếu S2 với V0 đạt trên Colab T4; cập nhật <code>docs/stages/s2-detection.md</code></td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td>P5-T07</td>
      <td>Cài đặt, định nghĩa ngưỡng kiểm chứng và kiểm thử V1 cho S3</td>
      <td>P5-T04, P5-T12</td>
      <td>Đạt <a href="final-plan.md#9-tiêu-chí-hoàn-thành-một-task-và-checklist-nộp-bài">mục 9 của kế hoạch cuối kỳ</a>; test đối chiếu S3 với V0 đạt trên Colab T4; cập nhật <code>docs/stages/s3-description.md</code></td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td rowspan="4">Đế</td>
      <td>P5-T08</td>
      <td>Đánh giá lại kho dữ liệu ảnh, đề xuất phương án chọn lại cặp chuẩn <code>site2</code> và cặp khó <code>challenge</code> phục vụ phân tích thất bại kèm lập luận, cập nhật <a href="dataset.md">dataset</a> và bộ <code>dataset/</code> trên Drive chung sau khi nhóm chốt</td>
      <td></td>
      <td>Lập luận và kết quả cập nhật trong <a href="dataset.md">dataset</a>; bộ <code>dataset/</code> kèm <code>manifest.csv</code> đã kiểm tra và upload lên Drive chung</td>
      <td>Chưa làm</td>
      <td></td>
    </tr>
    <tr>
      <td>P5-T09</td>
      <td>Xây dựng công cụ chạy gom batch thu thập bằng chứng profiling (<code>nsys</code>, <code>ncu</code>) và kiểm chứng sai số homography đa phiên bản trên bộ cặp synthetic</td>
      <td>P5-T12</td>
      <td>Script kèm kiểm thử chạy đạt trên Colab T4, xuất được kết quả profiling và sai số synthetic theo phiên bản</td>
      <td>Đang làm</td>
      <td>31/10: công cụ batch profiling/synthetic trên <code>de/shared-p5-tools</code>, commit <code>7781024</code>; 20 test Python mới đạt trên Colab T4, nsys/ncu xuất report và NVTX cho S4/S5. Đã kiểm chứng 12 lượt synthetic theo scope S4/S5. Chưa mở PR/merge vào main; hướng dẫn ở <code>docs/profiling.md</code>.</td>
    </tr>
    <tr>
      <td>P5-T10</td>
      <td>Cài đặt, định nghĩa ngưỡng kiểm chứng và kiểm thử V1 cho S4</td>
      <td>P5-T04, P5-T12</td>
      <td>Đạt <a href="final-plan.md#9-tiêu-chí-hoàn-thành-một-task-và-checklist-nộp-bài">mục 9 của kế hoạch cuối kỳ</a>; test đối chiếu S4 với V0 đạt trên Colab T4; cập nhật <code>docs/stages/s4-matching.md</code></td>
      <td>Đang làm</td>
      <td>31/10: code/test trong <code>src/v1/s4/</code> trên <code>de/p5</code>, commit <code>deafa78</code>; 2387 checks trên Colab T4, memcheck 0 lỗi, match khớp V0 trên sáu cặp synthetic. NVTX ở commit <code>ebfd446</code>. Chưa mở PR/merge vào main.</td>
    </tr>
    <tr>
      <td>P5-T11</td>
      <td>Cài đặt, định nghĩa ngưỡng kiểm chứng và kiểm thử V1 cho S5</td>
      <td>P5-T04, P5-T12</td>
      <td>Đạt <a href="final-plan.md#9-tiêu-chí-hoàn-thành-một-task-và-checklist-nộp-bài">mục 9 của kế hoạch cuối kỳ</a>; test đối chiếu S5 với V0 đạt trên Colab T4; cập nhật <code>docs/stages/s5-homography.md</code></td>
      <td>Đang làm</td>
      <td>31/10: code/test trong <code>src/v1/s5/</code> trên <code>de/p5</code>, commit <code>a0fa80f</code>, test biên <code>427ee94</code>; 16521 checks trên Colab T4, memcheck 0 lỗi. Driver <code>ed001e0</code> đối chiếu prefix/mask và H trên sáu cặp synthetic, đạt ngưỡng CPU–GPU và ground truth. Chưa mở PR/merge vào main.</td>
    </tr>
    <tr>
      <td rowspan="2">Chương</td>
      <td>P5-T12</td>
      <td>Xây dựng hạ tầng GPU dùng chung trong <code>src/common/cuda_utils.cuh</code>, thiết kế contract workspace Device-resident cho V1, mở rộng báo cáo timing CSV trong <code>src/main.cu</code> và cập nhật <a href="interface.md">interface</a></td>
      <td>P5-T02</td>
      <td>Merge vào <code>main</code> qua pull request file dùng chung; build sạch bằng <code>nvcc -arch=sm_75</code> và chạy đúng <code>--version 0</code> trên Colab T4</td>
      <td>Đang làm</td>
      <td>30/10: triển khai trên <code>chuong/shared-gpu-contract</code>: CUDA error/memory/event helpers, Device workspace, dispatcher V1 stub và CSV mở rộng. Build cục bộ WSL bằng nvcc 12.6, <code>-arch=sm_75</code>, chạy trên GTX 1650; V0 default 5 runs có PNG khớp từng byte baseline, V1 kiểm tra H2D/D2H và output copy A. Chờ nghiệm thu Colab T4 và merge PR; chưa đánh dấu hoàn tất.</td>
    </tr>
    <tr>
      <td>P5-T13</td>
      <td>Cài đặt, định nghĩa ngưỡng kiểm chứng và kiểm thử V1 cho S6</td>
      <td>P5-T04, P5-T12</td>
      <td>Đạt <a href="final-plan.md#9-tiêu-chí-hoàn-thành-một-task-và-checklist-nộp-bài">mục 9 của kế hoạch cuối kỳ</a>; test đối chiếu S6 với V0 đạt trên Colab T4; cập nhật <code>docs/stages/s6-warp-blend.md</code></td>
      <td>Chưa làm</td>
      <td></td>
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
