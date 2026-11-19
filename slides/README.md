# Khung thuyết trình chung — Nhóm 16

`project.tex` là file Beamer chính cho toàn bộ project. Deck đi qua bốn phần theo đề gồm bài toán và phương pháp, live demo, kết quả hiệu năng, tối ưu và bài học. Khung dùng nội dung tiếng Anh kèm kịch bản tiếng Việt.

| File | Vai trò |
|---|---|
| [project.tex](project.tex) | Khung chung, tổng quan S1–S6, kiến trúc V0–V4, demo, kiểm chứng, gallery và bảng kết quả toàn project. |
| [performance.tex](performance.tex) | Module của Đế về APOD, benchmark và Nsight. Deck chính chèn module này bằng `\input{performance.tex}`. |
| [video-outline.md](video-outline.md) | Kịch bản rút gọn 15 phút, đề xuất vai và danh mục tư liệu cho cả video. |
| [video-performance-notes.md](video-performance-notes.md) | Lời dẫn chi tiết cho phần hiệu năng và các đoạn kỹ thuật của Đế. |
| [performance-preview.tex](performance-preview.tex) | Bản xem riêng module hiệu năng để review từng phần. |

Biên dịch deck chính từ thư mục `slides/`:

```bash
mkdir -p ../build/slides
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=../build/slides project.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=../build/slides project.tex
```

PDF nằm tại `build/slides/project.pdf`. PDF riêng phần hiệu năng dùng cùng lệnh với `performance-preview.tex`.

Tuấn và Đế có thể cùng làm trên deck này. Tuấn chốt theme, tổng quan, pipeline, demo và kịch bản chung trong `project.tex` và `video-outline.md`. Đế cập nhật module `performance.tex`, bảng và hình trong `generated/`, cùng lời dẫn phần hiệu năng. Khi hợp nhất với một file Beamer khác, đặt `\input{performance.tex}` vào section hiệu năng hoặc tối ưu và giữ working directory là `slides/` để các đường dẫn hình hoạt động.

Bảng chính V0–V4 lấy từ benchmark cùng phiên T4 của P9. Bảng P8 giải thích vì sao chọn S6. Hình NSYS/NCU dựng từ SQLite và CSV của gói P9. Ảnh panorama trong `assets/` là đầu ra V4 site2/large của nhóm. [Nguồn số liệu và phương pháp đo](../docs/report/p9-t05-v4-apod.md)

Codex hỗ trợ soạn thảo và biên dịch deck. Nhóm rà nội dung trước khi hợp nhất vào khai báo AI chung.
