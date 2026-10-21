# Midterm Notebook Execution Guide

Người soạn: Thanh Chuong (23120195). Task: P3-T09. Cập nhật: 21/10/2026.

## Scope and Status

`Group16_Midterm.ipynb` có 37 cell, đủ cấu trúc báo cáo 3.1–3.7. Các đề mục bằng tiếng Anh; giải thích Markdown bằng tiếng Việt; comment code bằng tiếng Anh. Notebook build từ `src/` của bài nộp, không dùng `%%writefile` hoặc chép lại implementation thuật toán.

Benchmark gọi `scripts/run_benchmark.py` của P3-T04 với các đối số `--stitch --dataset --runs --out`. Tập stage tính Amdahl là S2, S4, S6 theo quyết định P3-T01. Kết quả lần Run all trên Colab T4 ghi ở bảng công việc.

## Inputs

Đề yêu cầu notebook lấy `src/` của bài nộp vào phiên Colab rồi build. Notebook chia đầu vào làm hai phần:

| Phần | Nội dung | Cách đưa vào phiên Colab |
|---|---|---|
| `src/` | Mã nguồn chương trình, đúng thư mục `src/` trong `Group16_Midterm.zip` | Panel Files: tạo `/content/src` rồi tải các file vào, hoặc tải `src.zip` vào `/content`. Thiếu cả hai thì cell workspace hỏi upload `src.zip` |
| [`Group16_support.zip`](https://drive.google.com/file/d/1Jx6o5kUnpvxXVEHfYKD1GBvZMTbSeEGu/view?usp=sharing) | `dataset/` (24 ảnh và `manifest.csv`), `scripts/`, `tests/`, `raw/tuan/standard1_left.jpg` | Đặt trên Drive chung, chia sẻ "ai có link đều xem được", điền file id vào `SUPPORT_DRIVE_ID`; notebook tải bằng `gdown`. Có thể đặt sẵn tại `/content/Group16_support.zip`; tải lỗi thì notebook hỏi upload |

File hỗ trợ không được chứa `src/`, để mã nguồn chỉ có một nguồn là bài nộp. Cell workspace dựng thư mục `/content/group16-<session_id>/` gồm `src/` cùng các thư mục của file hỗ trợ, rồi chạy mọi bước trong đó.

Tạo `Group16_support.zip` từ gốc repo, sau khi đã có `dataset/` và ảnh nguồn synthetic:

```bash
zip -r Group16_support.zip dataset scripts tests raw/tuan/standard1_left.jpg -x "*/__pycache__/*"
```

Ảnh nguồn synthetic là ảnh trong tài liệu S5 mục 5.5, SHA-256 `e9fbe7ecfed6344a36610fe50f2c6019bcd1525f4e217c033ed8ded4f90bf1e8`. Không thay bằng ảnh dataset đã resize: generator cần scene đủ rộng cho cả hai ảnh ở kích thước large.

Chế độ `SOURCE_MODE = "existing"` dùng một bản checkout đầy đủ của repo tại `EXISTING_WORKSPACE`, chỉ để thử nghiệm.

## Run All

1. Mở notebook trên Colab, chọn T4 GPU.
2. Tải `src/` lên theo bảng trên; kiểm tra `SUPPORT_DRIVE_ID` trong cell `Input Configuration`.
3. Chọn Runtime → Run all. Notebook in môi trường, kiểm tra 24 ảnh theo manifest, build, chạy test, chạy synthetic, sinh panorama và crop, chạy benchmark 9 cấu hình rồi tính Amdahl.
4. Trong lúc cell benchmark chạy, không chạy cell nặng nào khác.
5. Kết quả của từng phiên nằm ở `results/midterm/<session_id>/` trong workspace. Không đọc kết quả của phiên cũ để điền bảng mới.

Python dùng Pillow/numpy/pandas/matplotlib để kiểm tra và trình bày, không thêm dependency vào chương trình C++.

## Evidence and Final Submission

Notebook lưu môi trường/package versions, command build, SHA-256 nguồn, log test, synthetic accuracy, panorama/crop, timing và `run_receipt.json`. Kiểm tra nguồn không đổi giữa đầu và cuối phiên.

Các xác nhận do người thực hiện chịu trách nhiệm:

- `QUALITY_REVIEW_CONFIRMED`: chỉ bật sau khi xem panorama và crop 1:1, ghi phân tích P3-T10.
- `FINAL_REPORT_CONFIRMED`: chỉ bật sau khi P4 ghép và rà nội dung nhóm, gồm nguồn và kế hoạch GPU.
- `REQUIRE_COMPLETE_RUN=True`: dùng cho lần Run all cuối; thiếu evidence/confirmation thì báo lỗi, không ghi READY.

Trước khi đưa notebook lên Git: xóa mọi output và execution count. Bản nộp `Group16_Midterm.zip` dùng notebook đã Run all và lưu output, kèm `src/` theo đề.

## Local Verification

```bash
python -m unittest discover -s tests -p test_midterm_notebook.py -v
```

Test kiểm tra parser CSV, đủ 9 cấu hình/45 lần đo giả lập cho adapter, phát hiện sửa dữ liệu/hash, ZIP traversal, fingerprint nguồn, crop tọa độ, cấu trúc và cú pháp notebook, và việc `BENCHMARK_ARGS` khớp giao diện của `scripts/run_benchmark.py`. Dữ liệu giả lập chỉ dùng cho unit test, không đưa vào bảng kết quả. Trong workspace Colab không có file notebook nên nhóm test cấu trúc notebook được bỏ qua. Kết quả local không thay thế nghiệm thu Colab T4.
