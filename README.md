# CSC14120 - Panorama Stitching (Nhóm 16)

Đồ án cuối kỳ môn Lập trình song song (CSC14120): ghép hai ảnh chồng lấn thành một ảnh panorama. Cùng một pipeline gồm sáu stage (preprocessing, keypoint detection, description, matching, homography estimation, warping and blending) được cài đặt thành nhiều phiên bản: V0 tuần tự bằng C/C++, V1 CUDA cơ bản, V2 và V3 tối ưu. Mọi build, test và đo thời gian chạy trên Google Colab với GPU Tesla T4.

Mốc hiện tại là bài nộp giữa kỳ (proposal và phiên bản tuần tự V0), hạn 23/10/2026.

## Cấu trúc thư mục

| Đường dẫn | Ý nghĩa |
|---|---|
| `README.md` | Giới thiệu chung về repo và ý nghĩa của các file, thư mục |
| `AGENTS_TEMPLATE.md` | Bộ quy tắc tối thiểu cho AI agent của từng thành viên. Mỗi người sao chép thành `AGENTS.md` hoặc `CLAUDE.md` của riêng mình và không commit file đó |
| `.gitignore` | Các file không đưa lên Git: file hướng dẫn agent cá nhân, dataset, output, file build, PDF, file tạm |
| `docs/` | Tài liệu của Nhóm |
| `docs/midterm-plan.md` | Kế hoạch giữa kỳ: phân vai, các giai đoạn, quy định về code, Git, Colab, đo thời gian, notebook |
| `docs/task-board.md` | Bảng công việc: task theo giai đoạn, người phụ trách, hạn, trạng thái |
| `docs/dataset.md` | Quy định chụp ảnh, danh sách địa điểm và cặp ảnh ứng viên, yêu cầu chuẩn bị dataset |
| `docs/specs/` | Đề bài của môn học: bản Markdown chép nguyên văn từ PDF (`CSC14120_2026_Final Project_MidTerm.md`, `CSC14120_2026_Final Project.md`) cùng hình ảnh trong `images/`. Hai file PDF gốc đặt cùng thư mục nhưng không được commit |
| `Group16_Midterm.ipynb` | Notebook báo cáo giữa kỳ, nộp cùng `src/` trong `Group16_Midterm.zip` |
| `src/` | Toàn bộ mã nguồn C/C++/CUDA của chương trình `stitch` |

## Bắt đầu

1. Đọc `docs/midterm-plan.md` và `docs/task-board.md` để biết quy định chung và task của mình.
2. Nếu dùng AI agent, sao chép `AGENTS_TEMPLATE.md` thành `AGENTS.md` hoặc `CLAUDE.md` ở thư mục gốc repo. Mỗi lần `git pull`, kiểm tra template có thay đổi không để cập nhật lại file của mình.
