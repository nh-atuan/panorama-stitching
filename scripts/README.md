<!-- Authors: Nguyen Ho Anh Tuan (23120185) -->
<!-- External source: none -->

# Cấu trúc và hướng dẫn sử dụng `scripts/`

Thư mục `scripts/` chứa các công cụ Python phục vụ biên dịch, chuẩn bị dữ liệu, tạo ảnh synthetic, chạy benchmark, thu thập profiling Nsight (`nsys`/`ncu`), kiểm chứng CLI và hỗ trợ notebook báo cáo.

## 1. Tổ chức thư mục

```text
scripts/
├── build.py                     # Trình biên dịch thống nhất cho stitch và tests/tools/
├── fetch_and_prepare_dataset.py # Tải ảnh gốc từ Drive và gọi dataset/prepare_dataset.py
├── run_benchmark.py             # Chạy benchmark đa phiên bản (V0–V5, 3 site + challenge x 3 cỡ)
├── plot_benchmark.py            # Vẽ biểu đồ phân rã stage, speedup và bảng hot stage
├── dataset/                     # Xử lý và kiểm tra bộ ảnh đầu vào
│   ├── dataset_common.py        # Quy ước tên file, xoay EXIF, cắt khung 16:9
│   ├── check_pairs.py           # Kiểm tra tự động các cặp ảnh ứng viên trong raw/
│   └── prepare_dataset.py       # Sinh dataset/<site>/<size>_<side>.jpg và manifest.csv
├── synthetic/                   # Tạo cặp ảnh synthetic có ground truth H và đánh giá sai số
│   ├── homography_common.py     # Đọc/ghi truth JSON và phép chiếu điểm 2D
│   ├── make_synthetic_pair.py   # Sinh 6 cặp translation/projective ở 3 kích thước
│   ├── homography_error.py      # Tính RMSE, Max error và NRMSE từ log stitch --debug
│   └── synthetic_batch.py       # Chạy đánh giá batch trên đủ 6 cặp synthetic
├── profiling/                   # Thu thập profiling Nsight và phân tích probe APOD
│   ├── profiling_common.py      # Ghi nhận lệnh chạy, thông tin môi trường và provenance
│   ├── profiler_batch.py        # Chạy nsys/ncu tách biệt khỏi benchmark chính thức
│   ├── run_profiling.py         # Điều phối batch profiling và đánh giá synthetic
│   ├── build_pres4_probe.py     # Biên dịch bản probe V4 pre-S4 cô lập (P10-T01)
│   ├── pres4_baseline.py        # Tổng hợp bằng chứng baseline pre-S4
│   └── analyze_pres4_trace.py   # Trích xuất khoảng đo pre-S4 từ trace NSYS SQLite
├── verify/                      # Kiểm chứng CLI và đối chiếu hợp đồng đầu ra V2–V5
│   ├── verify_v2_dataset.py     # Nghiệm thu V2 trên dataset và tiện ích đối chiếu chung
│   ├── verify_v3_cli.py         # Kiểm chứng CLI/CSV cho V3
│   ├── verify_v4_cli.py         # Kiểm chứng CLI/CSV 11 cột cho V4
│   ├── verify_v5_cli.py         # Kiểm chứng CLI/CSV và sidecar 14 cột cho V5
│   └── smoke_v5_dispatcher.py   # Kiểm tra nhanh bộ điều phối V4/V5 cục bộ
└── notebook/                    # Module hỗ trợ cho notebook báo cáo và kiểm chứng Colab
    ├── final_notebook.py        # Tải dữ liệu, bảng, biểu đồ và gallery cho Group16_Final.ipynb
    ├── midterm_notebook.py      # Tiện ích kiểm tra dataset, đọc CSV và hiển thị (dùng chung)
    ├── package_s6_verification.py # Đóng gói source ZIP kèm manifest SHA-256 cho S6
    └── s6_colab_helpers.py      # Tiện ích nhúng trong notebook kiểm chứng S6 CUDA
```

Các lệnh chạy thường xuyên nhất (`build.py`, `fetch_and_prepare_dataset.py`, `run_benchmark.py`, `plot_benchmark.py`) được đặt ngay tại gốc `scripts/` để giữ ngắn gọn cho tài liệu và notebook. Các module chuyên biệt được gom vào 5 thư mục con tương ứng.

## 2. Quy ước import và chạy script

- Mọi lệnh chạy từ thư mục gốc của repo, ví dụ:
  ```bash
  python3 scripts/build.py --compiler nvcc --require-t4
  python3 scripts/fetch_and_prepare_dataset.py --out dataset
  python3 scripts/run_benchmark.py --stitch build/stitch --dataset dataset --runs 5 --out results/bench --versions 0 1 2 3 4 5 --include-challenge
  python3 scripts/plot_benchmark.py --speedup results/bench/speedup.csv --out results/bench/plots
  python3 scripts/synthetic/make_synthetic_pair.py --source raw/tuan/standard1_left.jpg --out results/synthetic
  python3 scripts/profiling/run_profiling.py --stitch build/stitch --dataset dataset --versions 4 --sites site1 --sizes medium --out results/profile --require-t4
  python3 scripts/verify/verify_v4_cli.py --stitch build/stitch --dataset dataset --out results/v4-cli --require-t4
  ```
- Khi import từ `tests/python/` hoặc notebook, thêm `scripts/` vào `sys.path` rồi import theo thư mục con, ví dụ `from notebook import final_notebook as fn`, `from verify.verify_v4_cli import verify_csv`, `from synthetic.homography_common import load_truth`.
- Các script nằm trong thư mục con tự thêm `scripts/` (`Path(__file__).resolve().parents[1]`) vào `sys.path` để chạy độc lập trực tiếp qua CLI mà không cần đặt biến `PYTHONPATH`.

## 3. Kiểm thử

Toàn bộ script trong thư mục này được kiểm thử tự động bởi 15 suite trong `tests/python/`:

```bash
python3 tests/run_tests.py --group python
```
