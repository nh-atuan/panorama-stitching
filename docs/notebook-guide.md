# Hướng dẫn chạy notebook giữa kỳ

Người soạn: Thanh Chương (23120195). Task: P3-T09. Cập nhật: 25/10/2026.

## Cấu trúc

`Group16_Midterm.ipynb` là báo cáo giữa kỳ, gồm mục lục và các phần đánh số 0–8. Phần 1–7 tương ứng mục 3.1–3.7 của đề, phần 8 là tài liệu tham khảo và khai báo dùng AI. Tiêu đề và giải thích viết bằng tiếng Việt, code và comment bằng tiếng Anh. Mỗi mục `##` hoặc `###` nằm ở đầu một cell riêng để thanh mục lục của Colab liệt kê đủ các mục.

Code trình bày gom vào cell `helpers` ở đầu notebook. Dòng đầu của cell này là `# @title ... { display-mode: "form" }`, nên Colab thu gọn code và chỉ hiện tiêu đề; bấm **Show code** để xem. Các cell code còn lại chỉ vài dòng gọi hàm trong `helpers`. Notebook không chép lại code của `src/` và không dùng `%%writefile`.

Một số điểm hiển thị đã kiểm tra trên Colab ngày 25/10:

- Colab không vẽ sơ đồ mermaid, nên sơ đồ pipeline được vẽ bằng matplotlib trong cell `pipeline-figure`.
- Colab bỏ thuộc tính `style` và thẻ `<svg>` trong markdown, bảng markdown luôn có chữ nhỏ. Bảng markdown giữ ngắn; bảng kết quả xuất từ code bằng pandas Styler với cỡ chữ 14px.
- Link trong mục lục dùng neo `<a name="muc-…"></a>` đặt ngay trước tiêu đề, chạy được trên cả Colab và VS Code.
- Thanh mục lục của Colab bỏ phần "1. " ở đầu tiêu đề, nên tiêu đề cấp `##` viết dạng `## 1\. Tên mục` (thoát dấu chấm). Nội dung hiển thị vẫn là "1. Tên mục".

## Đầu vào

| Phần | Nội dung | Cách đưa vào phiên Colab |
|---|---|---|
| `src/` | Mã nguồn chương trình, đúng thư mục `src/` trong `Group16_Midterm.zip` | Panel Files: tải `src.zip` vào `/content`, hoặc tạo `/content/src` rồi tải các file vào. Thiếu cả hai thì cell `setup` hỏi upload `src.zip` |
| [`Group16_support.zip`](https://drive.google.com/file/d/1Jx6o5kUnpvxXVEHfYKD1GBvZMTbSeEGu/view?usp=sharing) | `dataset/` (24 ảnh và `manifest.csv`), `scripts/`, `tests/`, `raw/tuan/standard1_left.jpg` | Cell `setup` tải bằng `gdown` theo `SUPPORT_DRIVE_ID` trong cell `helpers`. Có thể đặt sẵn tại `/content/Group16_support.zip`; tải lỗi thì notebook hỏi upload |

File hỗ trợ không được chứa `src/`, để mã nguồn chỉ có một nguồn là bài nộp. Cell `setup` dựng thư mục `/content/group16-<phiên>/` gồm `src/` và các thư mục của file hỗ trợ, rồi chạy mọi bước trong đó.

Tạo `Group16_support.zip` từ gốc repo, sau khi đã có `dataset/` và ảnh nguồn synthetic:

```bash
zip -r Group16_support.zip dataset scripts tests raw/tuan/standard1_left.jpg -x "*/__pycache__/*"
```

Ảnh nguồn synthetic là ảnh trong tài liệu S5 mục 5.5, SHA-256 `e9fbe7ecfed6344a36610fe50f2c6019bcd1525f4e217c033ed8ded4f90bf1e8`. Không thay bằng ảnh dataset đã resize: generator cần cảnh đủ rộng cho cả hai ảnh ở kích thước large.

## Run all

1. Mở notebook trên Colab, chọn T4 GPU.
2. Tải `src/` lên theo bảng trên.
3. Chọn Runtime → Run all. Notebook kiểm tra môi trường và 24 ảnh theo manifest, build, in bảng tham số đọc từ `src/`, chạy test, chạy cặp synthetic, sinh panorama và vùng cắt, chạy benchmark 9 cấu hình rồi tính Amdahl.
4. Trong lúc cell benchmark chạy, không chạy cell nặng nào khác.

Output chỉ hiện bảng và hình tóm tắt. Log đầy đủ của mọi lệnh nằm trong `results/logs/` của thư mục làm việc; CSV, panorama và vùng cắt nằm trong `results/`. Mỗi lệnh lỗi làm cell dừng và in 30 dòng cuối của log.

Python dùng Pillow, numpy, pandas và matplotlib để kiểm tra và trình bày, không thêm dependency vào chương trình C++.

## Số liệu trong lời văn

Mọi con số trong phần giải thích phải có trong output. Tham số của các stage được đọc từ hằng số `constexpr` trong `src/` (hàm `show_parameters`) và từ dòng `config` mà `stitch --debug` in ra (hàm `demo_run`), không gõ tay trong code. Các con số về timing, hot stage và Amdahl dao động giữa các lần chạy, nên phải cập nhật theo output của chính bản nộp.

## Bản trong Git và bản nộp

Trước khi đưa notebook lên Git: xóa mọi output và execution count. Bản nộp `Group16_Midterm.zip` dùng notebook đã Run all và lưu output, kèm `src/` theo đề.

## Kiểm tra trên máy

```bash
python -m unittest discover -s tests -p test_midterm_notebook.py -v
```

Test kiểm tra parser CSV, đủ 9 cấu hình và 45 lần đo giả lập, phát hiện sửa dữ liệu hoặc hash, ZIP traversal, fingerprint nguồn, crop tọa độ, và cấu trúc notebook: mục 0–8 và neo của mục lục, cell `helpers` ở dạng form, cell báo cáo ngắn và chỉ gọi hàm có trong `helpers`, không còn mã task, cờ nội bộ hay sơ đồ mermaid, `BENCHMARK_ARGS` khớp giao diện của `scripts/run_benchmark.py`. Dữ liệu giả lập chỉ dùng cho unit test. Trong workspace Colab không có file notebook nên nhóm test cấu trúc notebook được bỏ qua. Kết quả trên máy không thay thế lần chạy trên Colab T4.
