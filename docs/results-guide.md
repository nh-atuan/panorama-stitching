<!-- Authors: Nguyen Ho Anh Tuan (23120185). External source: none. -->

# Quy ước lưu trữ kết quả thực nghiệm trên Google Drive

Tài liệu quy định cấu trúc và hướng dẫn lưu trữ dữ liệu thực nghiệm cho bài nộp cuối kỳ môn Lập trình song song (CSC14120 - Nhóm 16).

- **Thư mục kết quả trên Google Drive:** [CSC14120_Group16_Results](https://drive.google.com/drive/folders/1uJ-4_kgVONvIt5NQIPzdEWTIPrg8Sue1?usp=sharing)
- **Nhật ký APOD tương ứng:** [docs/apod-log.md](apod-log.md)

---

## Cấu trúc thư mục trên Drive

```text
CSC14120_Group16_Results/
├── v0/                     <- Toàn bộ kết quả bản tuần tự V0 (CPU reference)
│   └── benchmark/          <- CSV, logs, failures.csv, environment.json và ảnh panorama V0
│
├── v1/                     <- Toàn bộ kết quả bản GPU cơ bản V1 (Basic CUDA)
│   ├── benchmark/          <- CSV, logs, failures.csv, speedup V1/V0 và ảnh panorama V1
│   └── profiling/          <- Trace NSYS, NCU và ảnh chụp màn hình timeline/chỉ số vi kiến trúc
│
├── v2/                     <- Toàn bộ kết quả bản tối ưu V2 (Tối ưu S5 - Phase 7)
│   ├── benchmark/          <- CSV V2, speedup V2/V1, V2/V0 (kèm log memcheck nếu có)
│   └── profiling/          <- Trace NSYS, NCU và ảnh chụp màn hình timeline/chỉ số kernel S5 V2
│
├── v3/                     <- Toàn bộ kết quả bản tối ưu V3 (Phase 8)
│   ├── benchmark/
│   └── profiling/
│
├── v4/
│   ├── benchmark/
│   └── profiling/
├── v5/
│   ├── benchmark/
│   └── profiling/
└── v6/
    ├── benchmark/
    └── profiling/
```

---

## Hướng dẫn lưu trữ cho từng thư mục

### 1. Thư mục `benchmark/` của từng phiên bản
Mỗi khi chạy xong một phiên bản trên Google Colab Tesla T4 bằng `scripts/run_benchmark.py`:
- **Dữ liệu thời gian và nhật ký chạy:** Ném toàn bộ thư mục do script sinh ra vào `benchmark/` (gồm các file CSV theo cấu trúc `<site>/<size>.csv`, `summary.csv`, `summary.md`, `failures.csv` và `environment.json`).
- **Ảnh Panorama kết quả:** File `<site>/<size>_panorama.jpg` do lệnh ghép ảnh xuất ra (đã nằm sẵn trong output của script).
- **Biểu đồ phân tích (nếu có):** Các ảnh `.png` do `scripts/plot_benchmark.py` vẽ ra để tiện xem nhanh trên Drive hoặc gắn vào slide.
- **Log an toàn bộ nhớ (nếu có):** File text log của `compute-sanitizer` (`memcheck.log`) chứng minh `0 errors`, `0 bytes leaked`.

### 2. Thư mục `profiling/` của từng phiên bản GPU
Phục vụ cung cấp bằng chứng định lượng cho Mục 5 (V1) và Mục 6 (V2, V3...) của báo cáo:
- **Ảnh chụp màn hình (Bắt buộc):** Ảnh `.png` chụp trực quan timeline Nsight Systems (chỉ ra hotspot chiếm thời gian) và biểu đồ Nsight Compute (SOL DRAM, SOL SM, Warp Stalls). Các file ảnh này sẽ được chèn trực tiếp vào Notebook báo cáo `Group16_Final.ipynb` và slide thuyết trình.
- **File trace Nsight:** File `.nsys-rep` và `.ncu-rep` gốc (nén thành file `.zip` nếu dung lượng lớn) để lưu trữ đối chứng.

Lưu ý: Bảng so sánh tổng hợp cuối cùng giữa tất cả các phiên bản (Mục 7 của đề bài) sẽ được sinh tự động trực tiếp bên trong notebook `Group16_Final.ipynb` khi chạy `Runtime -> Run all` trên cùng một phiên Colab nộp bài, không cần lưu trữ thư mục so sánh riêng biệt trên Drive.

