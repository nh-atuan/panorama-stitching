# CSC14120 - Panorama Stitching (Nhóm 16)

Đồ án cuối kỳ môn Lập trình song song (CSC14120): ghép hai ảnh chồng lấn thành một ảnh panorama. Cùng một pipeline gồm sáu stage (preprocessing, keypoint detection, description, matching, homography estimation, warping and blending) được cài đặt thành nhiều phiên bản: V0 tuần tự bằng C/C++, V1 CUDA cơ bản, V2 và V3 tối ưu. Mọi build, test và đo thời gian chạy trên Google Colab với GPU Tesla T4.

Mốc hiện tại là giai đoạn cuối kỳ (các phiên bản song song CUDA V1–V3, báo cáo notebook, slide và video), hạn hoàn tất 03/12/2026.

## Cấu trúc thư mục

| Đường dẫn | Ý nghĩa |
|---|---|
| `README.md` | Giới thiệu chung về repo và ý nghĩa của các file, thư mục |
| `AGENTS_TEMPLATE.md` | Bộ quy tắc tối thiểu cho AI agent của từng thành viên. Mỗi người sao chép thành `AGENTS.md` hoặc `CLAUDE.md` của riêng mình và không commit file đó |
| `.gitignore` | Các file không đưa lên Git: file hướng dẫn agent cá nhân, dataset, output, file build, PDF, file tạm |
| `docs/` | Tài liệu của Nhóm |
| `docs/final-plan.md` | Kế hoạch cuối kỳ: phân vai, lộ trình cuốn chiếu P5–P9, quy định code CUDA, profiling, báo cáo |
| `docs/task-board.md` | Bảng công việc hiện tại: task theo giai đoạn, người phụ trách, hạn, trạng thái |
| `docs/archive/` | Tài liệu lưu trữ giai đoạn giữa kỳ: `midterm-plan.md` và `midterm-task-board.md` (P0–P4) |
| `docs/dataset.md` | Quy định chụp ảnh, danh sách địa điểm và cặp ảnh ứng viên, yêu cầu chuẩn bị dataset |
| `docs/interface.md` | Contract dữ liệu chung giữa các stage và pipeline |
| `docs/specs/` | Đề bài môn học chép từ PDF (`CSC14120_2026_Final Project_MidTerm.md`, `CSC14120_2026_Final Project.md`) |
| `src/` | Toàn bộ mã nguồn C/C++/CUDA của chương trình `stitch` (`common/`, `v0/`, `v1/`...) |
| `tests/` | Bộ bài kiểm thử tự động C++/CUDA/Python và công cụ trung gian (`run_tests.py`) |
| `scripts/` | Script hỗ trợ build đa nền tảng (`build.py`), benchmark và chuẩn bị dữ liệu |

## Bắt đầu

1. Đọc `docs/final-plan.md` và `docs/task-board.md` để biết quy định chung và task của mình.
2. Nếu dùng AI agent, sao chép `AGENTS_TEMPLATE.md` thành `AGENTS.md` hoặc `CLAUDE.md` ở thư mục gốc repo. Mỗi lần `git pull`, kiểm tra template có thay đổi không để cập nhật lại file của mình.
