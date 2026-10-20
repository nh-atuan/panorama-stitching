# Midterm Notebook Execution Guide

Người soạn: Thanh Chuong (23120195). Task: P3-T09. Cập nhật: 20/10/2026.

## Scope and Status

`Group16_Midterm.ipynb` có 37 cell, đủ cấu trúc báo cáo 3.1–3.7. Các đề mục bằng tiếng Anh; giải thích Markdown bằng tiếng Việt; comment code bằng tiếng Anh. Notebook build từ `src/`, không dùng `%%writefile` hoặc chép lại implementation thuật toán.

Khung đã được kiểm tra cú pháp và helper/test local. Chưa có lần Run all chính thức trên Colab T4 cho bản notebook mới. P3-T04 của Thành chưa có trong repo; phần benchmark chỉ có adapter, không chạy thay script của Thành. Vì vậy P3-T09 vẫn `Đang làm`.

## Workspace Layout

Chuẩn bị thư mục hoặc ZIP có cấu trúc sau. ZIP có thể có một thư mục bao ngoài. Giữ `src/`, `scripts/`, `tests/` cùng revision; `tests/test_midterm_notebook.py` và `scripts/midterm_notebook.py` phải có trong bundle mới.

```text
workspace/
  src/
  scripts/
  tests/
  docs/
  dataset/
    manifest.csv
    site1/       # small_left.jpg, small_right.jpg, medium_*, large_*
    site2/
    site3/
    challenge/
  raw/
    tuan/
      standard1_left.jpg
```

Nguồn synthetic mặc định đúng ảnh trong tài liệu S5 mục 5.5, SHA-256 `e9fbe7ecfed6344a36610fe50f2c6019bcd1525f4e217c033ed8ded4f90bf1e8`. Không thay bằng ảnh dataset đã resize: generator cần scene đủ rộng cho cả hai ảnh ở kích thước large. Nếu nhóm chủ động đổi ảnh nguồn, phải cập nhật cấu hình, hash và mô tả thực nghiệm; không coi số đo cũ là số đo của ảnh mới.

Link dữ liệu có trong mục 0.2 và 3.6 của notebook. Chuẩn bị thư mục dataset từ bản đã chốt, không chạy lại chọn cặp trong notebook này.

## First Colab Run

1. Mở notebook trên Colab, chọn T4 GPU.
2. Sửa cell `Input Configuration`: dùng `upload`, `drive` hoặc `existing`. Với `drive`, điền đường dẫn workspace thật; `/content/drive/MyDrive/Group16/workspace` chỉ là đường dẫn cấu hình mẫu.
3. Với `upload`, tải một ZIP workspace khi cell yêu cầu; có thể đặt trước tại `/content/Group16_workspace.zip`.
4. Chạy từ trên xuống. Notebook in môi trường, kiểm tra 24 ảnh theo manifest, build, test, chạy synthetic và sinh panorama/crop.
5. Nếu thiếu script benchmark, notebook thông báo chờ P3-T04 và kết thúc `INCOMPLETE` ở chế độ bản nháp. Không có timing giả. Lỗi build/test/dataset/synthetic vẫn dừng ngay; không bị chuyển thành trạng thái chờ.
6. Kết quả riêng từng phiên ở `results/midterm/<session_id>/`. Không đọc kết quả của phiên cũ để tự điền bảng mới.

Python dùng Pillow/numpy/pandas/matplotlib để kiểm tra và trình bày, không thêm dependency vào chương trình C++.

## Benchmark Handoff

Đây là **giao diện đề xuất**, chưa được Thành xác nhận. P3-T04 vẫn thuộc Thành.

Notebook cung cấp bốn giá trị cho script `scripts/run_benchmark.py`: binary, dataset, số lần chạy, thư mục kết quả. Khi script có, điền `BENCHMARK_ARGS` bằng danh sách đối số chính xác. Có thể dùng các placeholder `{stitch}`, `{dataset}`, `{runs}`, `{out}` trong từng đối số; notebook thay chúng bằng đường dẫn của phiên hiện tại. Không dùng chuỗi shell và không giả định tên cờ khi chưa biết giao diện thật.

Adapter hiện chờ nguyên stdout CSV của `stitch` theo layout:

```text
<out>/site1/small.csv
<out>/site1/medium.csv
<out>/site1/large.csv
<out>/site2/small.csv
...
<out>/site3/large.csv
```

Mỗi file có header `Run_Index,S1_ms,S2_ms,S3_ms,S4_ms,S5_ms,S6_ms,Total_ms`, 5 dòng đo, `Average`, `Minimum`. Adapter kiểm tra nhãn, giá trị hữu hạn/không âm, summary khớp các lần đo và đủ 9 cấu hình. Nếu script Thành xuất schema khác thì điều chỉnh adapter theo schema thật, không đổi script của Thành trong task này.

Benchmark phải dùng binary, input và output của phiên hiện tại; không copy CSV lịch sử. Thành chịu trách nhiệm warm-up, 5 repeats, metadata và phép đo đúng quy định. Notebook không đo subprocess bằng Python để thay thời gian C++.

Sau P3-T01, điền `ACCELERATED_STAGES` theo quyết định nhóm để tính Amdahl. Không tự gán S6 là hot stage trước khi có số đo.

## Evidence and Final Submission

Notebook lưu môi trường/package versions, command build, SHA-256 nguồn, log test, synthetic accuracy, panorama/crop, timing sau khi tích hợp và `run_receipt.json`. Kiểm tra nguồn không đổi giữa đầu/cuối phiên.

Các xác nhận do người thực hiện chịu trách nhiệm:

- `QUALITY_REVIEW_CONFIRMED`: chỉ bật sau khi xem panorama và crop 1:1, ghi phân tích P3-T10.
- `FINAL_REPORT_CONFIRMED`: chỉ bật sau khi P4 ghép và rà nội dung nhóm, gồm địa điểm site1, nguồn và kế hoạch GPU.
- `REQUIRE_COMPLETE_RUN=True`: dùng cho lần Run all cuối; thiếu evidence/confirmation thì báo lỗi, không ghi READY.

Trước khi đưa notebook làm việc lên Git: xóa mọi output và execution count. Bản nộp `Group16_Midterm.zip` phải dùng notebook đã Run all và lưu output, kèm `src/` theo đề. Để tái chạy toàn bộ test/benchmark cells, vẫn cần `tests/` và `scripts/` từ workspace được hướng dẫn ở đầu notebook.

## Local Verification

```bash
python -m unittest discover -s tests -p test_midterm_notebook.py -v
```

Ngày 20/10/2026: 16 test local đạt, gồm parser CSV, đủ 9 cấu hình/45 lần đo giả lập cho adapter, phát hiện sửa dữ liệu/hash, metadata/layout sai, ZIP traversal, fingerprint nguồn, crop tọa độ và cấu trúc/cú pháp notebook. Dữ liệu giả lập chỉ dùng unit test; không được đưa vào bảng kết quả notebook. Kết quả local không thay thế nghiệm thu Colab T4.
