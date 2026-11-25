<!-- Authors: Nguyen Ho Anh Tuan (23120185), Le Thuong De (23120232). External source: none. -->

# Bộ slide thuyết trình và kịch bản video — Nhóm 16

`project.tex` là file Beamer chính (tỷ lệ 16:9) cho toàn bộ đồ án cuối kỳ CSC14120. Deck trình bày bằng tiếng Việt (giữ nguyên thuật ngữ chuyên ngành tiếng Anh), tổ chức theo ba phần tuyến tính: tổng quan bài toán và hướng tiếp cận, kiểm chứng và phân tích hiệu năng (V0–V5), cùng các tối ưu chính và bài học rút ra (phần live demo chạy trực tiếp trên Colab T4 bằng `scripts/live_demo.py`).

| File | Vai trò |
|---|---|
| [project.tex](project.tex) | Deck Beamer 16:9 chính (28 slide tuyến tính, gồm 3 slide chuyển mục): tổng quan S1–S6, lộ trình V0–V5, kiểm chứng, ảnh kết quả chuẩn & ca thất bại (`de-challenge1`), hiệu năng/profiling V0–V5, tối ưu S5 (V2/V3)/V4/V5, bài học rút ra và tài liệu tham khảo. |
| [performance.tex](performance.tex) | Module kết quả hiệu năng và Nsight V0–V5 (được chèn vào `project.tex` bằng `\input{performance.tex}`). |
| [generated/v5-table.tex](generated/v5-table.tex) | Bảng tóm tắt đối chứng V5 hai stream theo ba độ phân giải (small, medium, large và GM 9 ca chuẩn, Tesla T4). |
| [video-outline.md](video-outline.md) | Kịch bản phân cảnh chi tiết (cue sheet) 24 phút 30 giây cho 4 thành viên (Tuấn, Thành, Đế, Chương) theo đúng khung 20–30 phút của đề bài. |
| [video-performance-notes.md](video-performance-notes.md) | Lời dẫn chi tiết 7 phút 30 giây cho Phần 3 (Hiệu năng & Nsight V0–V5) của Đế. |
| [performance-preview.tex](performance-preview.tex) | Bản biên dịch độc lập riêng module hiệu năng để rà soát nhanh. |

## Biên dịch PDF từ thư mục `slides/`

```bash
mkdir -p ../build/slides
cd slides
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=../build/slides project.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=../build/slides project.tex
```

File PDF chính thức được xuất tại `build/slides/project.pdf`. Để biên dịch bản xem trước riêng phần hiệu năng, thay `project.tex` bằng `performance-preview.tex` (xuất tại `build/slides/performance-preview.pdf`).

## Nguồn số liệu đồng bộ

- Toàn bộ bảng thời gian và speedup V0–V5: đo hợp nhất trong cùng một phiên Google Colab Tesla T4 ngày 25/11/2026 tại SHA `f6dc3ee` (V0: 1 warm-up + 5 lượt đo; GPU V1–V5: 4 warm-up + 5 lượt đo).
- Hình và chỉ số profiling Nsight (`generated/ncu-v4.png`, `generated/nsys-v5.png`): đồng bộ từ [docs/report/p9-t05-v4-apod.md](../docs/report/p9-t05-v4-apod.md) và [docs/report/p10-t05-v5-apod.md](../docs/report/p10-t05-v5-apod.md).
- Số liệu kiểm chứng và đóng băng mã nguồn: đồng bộ từ [docs/report/p10-v5-verification.md](../docs/report/p10-v5-verification.md), [docs/report/p11-t02-freeze-verification.md](../docs/report/p11-t02-freeze-verification.md) và [docs/apod-log.md](../docs/apod-log.md).
