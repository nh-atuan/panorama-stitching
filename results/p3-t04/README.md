# Kết quả benchmark V0 ngày 20/10 và file để chạy lại

Người soạn: Thành (23120166). Cập nhật: 21/10.

Thư mục này nằm trên nhánh `thanh/p3-results`. Nhóm đồng ý ngoại lệ với mục 10.8 của kế hoạch giữa kỳ để commit output ở nhánh này cho thành viên khác xem và chạy lại. Nhánh không merge vào `main`.

## Nội dung

| Đường dẫn | Ý nghĩa |
|---|---|
| `benchmark/` | Output của `scripts/run_benchmark.py`: stdout CSV và log `--debug` của 9 cấu hình (site1, site2, site3 ở small, medium, large), `summary.csv`, `summary.md`, `environment.json`. Không có ảnh panorama |
| `analysis/` | Output của `scripts/plot_benchmark.py` trên `benchmark/summary.csv`: hai biểu đồ cột chồng theo stage, bảng hot stage |
| `panorama-stitching-thanh-p3.zip` | Mã nguồn nhánh `thanh/p3` ở commit `adcc232`, tạo bằng `git archive`. Cell 3 của notebook P3-T04 và cell 2 của notebook P3-T05 yêu cầu upload file này |
| `P3-T04_colab_benchmark.ipynb` | Notebook build `stitch`, chạy test và chạy benchmark. Không có output |
| `P3-T05_colab_tests.ipynb` | Notebook chạy test của hai script. Không có output |

Số đo lấy trên Google Colab với GPU Tesla T4 (driver 580.82.07), CPU Intel Xeon 2.00GHz, CUDA 13.0, một warm-up không đo và `--runs 5`. Cả 9 cấu hình đo trong cùng một phiên. Mã nguồn lúc đo là commit `905f759`; commit `adcc232` chỉ thêm `plot_benchmark.py` và test, không đổi `src/`.

## Chạy lại benchmark

1. Trên GitHub, chọn nhánh `thanh/p3-results`, vào thư mục `results/p3-t04/`, tải `P3-T04_colab_benchmark.ipynb` và `panorama-stitching-thanh-p3.zip` về máy.
2. Mở link `dataset/` của Drive chung (mục 8 của `docs/dataset.md`), bấm chuột phải vào thư mục, chọn Sắp xếp, Thêm lối tắt, Drive của tôi. Không có lối tắt thì Colab không thấy thư mục được chia sẻ.
3. Trên Colab chọn File, Upload notebook rồi chọn notebook vừa tải. Đổi runtime sang T4 GPU.
4. Chọn Runtime, Run all. Cell 3 hỏi file zip mã nguồn; cell 4 hỏi quyền truy cập Google Drive.
5. Trong lúc cell benchmark chạy, không chạy cell nặng nào khác (mục 12.6 của kế hoạch). Cell cuối tải về `benchmark_results.zip`.

Nếu cell 4 không tìm thấy dataset, điền đường dẫn thư mục vào `DATASET_DRIVE_PATH` ở cell cấu hình, hoặc tải thư mục `dataset/` về máy dạng zip rồi đặt `DATASET_MODE = "upload"`.

Số đo của mỗi phiên Colab lệch nhau một ít. Mọi số trong cùng một bảng phải lấy từ cùng một phiên (mục 12.5 của kế hoạch), nên không ghép số của lần chạy lại với số trong thư mục này.

## Vẽ lại biểu đồ từ số có sẵn

Từ gốc repo trên máy có Python và matplotlib:

```bash
python scripts/plot_benchmark.py --summary results/p3-t04/benchmark/summary.csv --out results/p3-t04/analysis
```
