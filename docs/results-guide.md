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
├── v4/                     <- Thư mục dự phòng (nếu nhóm mở rộng thêm V4)
│   ├── benchmark/
│   └── profiling/
│
└── final_comparison/       <- Lượt đo tổng hợp cuối cùng cho toàn bộ phiên bản trên 1 phiên Colab T4 duy nhất
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

### 3. Thư mục `final_comparison/` (Phục vụ Mục 7 của Notebook)
Đề bài yêu cầu: *"All versions in one comparison table must be measured on the same GPU in the same Colab session"*.
- Thư mục này **dành riêng cho Phase 9** ở lượt chạy tổng hợp cuối cùng (đo đồng thời tất cả các phiên bản V0, V1, V2, V3... trong cùng 1 phiên Colab duy nhất).
- Chứa bảng speedup tổng hợp (`speedup.csv`, `speedup.md`), biểu đồ speedup toàn pipeline và log chi tiết của phiên đo chung. Không ném các kết quả đo lẻ tẻ của từng sprint vào đây.

