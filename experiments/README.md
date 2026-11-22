<!-- Authors: Nguyen Ho Anh Tuan (23120185). External source: none. -->

# Mục lục notebook thực nghiệm và kiểm chứng (`experiments/`)

Thư mục này lưu các Jupyter Notebook phụ trợ dùng để kiểm chứng đúng đắn, đo benchmark, thu thập profiling (`nsys`/`ncu`) theo từng giai đoạn P5–P10 và lưu trữ bản báo cáo giữa kỳ (`V0`).

Notebook báo cáo cuối kỳ chính thức dùng để nộp bài nằm ở thư mục gốc: [`Group16_Final.ipynb`](../Group16_Final.ipynb).

## 1. Kiểm chứng và nghiệm thu trên Colab T4

| Giai đoạn / Phiên bản | Notebook | Mục đích | Báo cáo đối chiếu |
|---|---|---|---|
| P5 (S6 CUDA) | [Group16_S6_CUDA_Verification.ipynb](Group16_S6_CUDA_Verification.ipynb) | Kiểm chứng độc lập kernel S6 CUDA và memcheck trên T4 | [p5-s6-cuda-verification.md](../docs/report/p5-s6-cuda-verification.md), [s6-colab-guide.md](../docs/archive/s6-colab-guide.md) |
| P7 (V2) | [Group16_P7_V2_Verification.ipynb](Group16_P7_V2_Verification.ipynb) | Nghiệm thu pipeline V2 (6 synthetic, 12 ca ảnh thật, memcheck) | [p7-v2-verification.md](../docs/report/p7-v2-verification.md) |
| P8 (V3) | [Group16_P8_V3_Verification.ipynb](Group16_P8_V3_Verification.ipynb) | Nghiệm thu pipeline V3, contract CLI/CSV và memcheck | [p8-v3-verification.md](../docs/report/p8-v3-verification.md) |
| P9 (V4) | [Group16_P9_V4_Verification.ipynb](Group16_P9_V4_Verification.ipynb) | Nghiệm thu pipeline V4, đối chiếu parity V0–V4 và memcheck | [p9-v4-verification.md](../docs/report/p9-v4-verification.md) |
| P10 (V5) | [Group16_P10_V5_Verification.ipynb](Group16_P10_V5_Verification.ipynb) | Nghiệm thu pipeline V5 (`dual`/`sequential`) và memcheck | [p10-v5-verification.md](../docs/report/p10-v5-verification.md) |

## 2. Benchmark, profiling và probe APOD

| Giai đoạn / Phiên bản | Notebook | Mục đích | Báo cáo đối chiếu |
|---|---|---|---|
| P9 (V0–V4) | [Group16_P9_T05_Benchmark_Profiling.ipynb](Group16_P9_T05_Benchmark_Profiling.ipynb) | Benchmark cùng phiên T4 (V0–V4) và profiling NSYS/NCU cho S6 V4 | [p9-t05-v4-apod.md](../docs/report/p9-t05-v4-apod.md) |
| P10 (V4 pre-S4) | [Group16_P10_T01_PreS4_Baseline.ipynb](Group16_P10_T01_PreS4_Baseline.ipynb) | Đo baseline đoạn pre-S4 (H2D + S1–S3) của V4 bằng probe riêng và NSYS | [p10-t01-pres4-baseline.md](../docs/report/p10-t01-pres4-baseline.md), [p10-v5-contract.md](../docs/report/p10-v5-contract.md) |
| P10 (V4 vs V5) | [Group16_P10_T05_Benchmark_Profiling.ipynb](Group16_P10_T05_Benchmark_Profiling.ipynb) | Benchmark ghép cặp V4/V5 (`dual`/`sequential`) và phân tích trace NSYS | [p10-t05-v5-apod.md](../docs/report/p10-t05-v5-apod.md) |

## 3. Lưu trữ giai đoạn giữa kỳ

| Giai đoạn | Notebook | Mục đích | Tài liệu liên quan |
|---|---|---|---|
| P0–P4 (V0) | [Group16_Midterm.ipynb](Group16_Midterm.ipynb) | Notebook báo cáo giữa kỳ cho phiên bản tuần tự CPU (`V0`) | [notebook-guide.md](../docs/archive/notebook-guide.md), [test_midterm_notebook.py](../tests/python/test_midterm_notebook.py) |

## 4. Lưu ý khi chạy và quản lý phiên bản

- Các notebook kiểm chứng và benchmark chạy trên **Google Colab GPU Tesla T4 (`sm_75`)**, biên dịch trực tiếp từ `src/` qua `scripts/build.py` và tải bộ ảnh từ Google Drive chung.
- Không commit output của các notebook trong thư mục này để tránh xung đột khi merge; xóa output trước khi commit bằng `jupyter nbconvert --clear-output --inplace <file>.ipynb`.
