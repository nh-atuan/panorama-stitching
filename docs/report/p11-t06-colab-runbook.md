<!-- Authors: Le Ha Thanh Chuong (23120195). External source: repository workflows and official requirements cited below. -->

# P11-T06 — Colab T4 Execution and PDF Runbook

## 1. Scope and Current Readiness

Dùng [notebook điều phối](../../Group16_P11_T06_Acceptance.ipynb) để chạy bản sao của [notebook báo cáo](../../Group16_Final.ipynb) trên Colab T4 và thu evidence/PDF. Không cần push nhánh local, tạo PR hoặc công bố evidence. Notebook điều phối không thay thế báo cáo 10 mục cần nộp.

Tại lượt kiểm tra 20/11/2026, `origin/main` vẫn là `4a20d1a93607851a8fc48bccbbfe206a07c0a787`; chưa có xác nhận source freeze P11-T02. Pin trong báo cáo gốc vẫn là `d42000c4d2847aeb8e1adea66132d35c23a9cb63`, thiếu implementation T02 của V5. Không đổi pin này thành SHA tự chọn rồi gọi đó là release. Cấu hình hiện tại mặc định **candidate**, không chứng nhận hoàn tất T06.

Các điều kiện còn thiếu về số liệu V5, cặp mẫu môn học và nội dung T04 được ghi trong [audit](p11-t06-notebook-audit.md). Giữ quyết định V4 production/V5 case study; không tự thay số công bố chỉ để khớp output mới. Tiêu chí cuối cùng theo [đề môn học](../specs/CSC14120_2026_Final%20Project.md), mục 4.2 và 5.2.

## 2. Required T4 Environment

Trong Colab, chọn **Runtime → Change runtime type → T4 GPU**. Bắt đầu bằng runtime mới, không dùng lại thư mục benchmark từ phiên trước.

Preflight yêu cầu đúng một GPU tên T4/Tesla T4/NVIDIA T4, compute capability **7.5**, có free VRAM; lưu UUID, driver, total/free VRAM, nvcc version, Python/package versions và `pip freeze`. Không chấp nhận L4/A100 làm evidence T4. Free VRAM được ghi nhận, không bảo đảm mọi allocation sẽ thành công.

Các công cụ bắt buộc: `nvidia-smi`, `nvcc`, `git`, `g++`; thư viện Python cho notebook, dataset và chart. Cell setup cài `nbformat`, `nbconvert`, `nbclient`, `ipykernel`, `playwright`, `pypdf`, Pillow, NumPy, Matplotlib và gdown; sau đó `python -m playwright install --with-deps chromium`. Không cài thư viện C++/CUDA ngoài quy định hoặc thay toolkit của Colab.

## 3. Prepare the Local Handoff Bundle

Sau khi các công cụ được commit local, chạy từ gốc repository:

```bash
python scripts/package_notebook_acceptance.py --ref HEAD \
  --output build/p11-t06-source/Group16_P11_T06_Source.zip
```

Nhận hai file cùng thư mục:

- `Group16_P11_T06_Source.zip`: source đã commit, scripts/tests/docs cần chạy, báo cáo và notebook điều phối. Không có `.git`, dataset, build, binary hoặc file chưa commit.
- `Group16_P11_T06_Source.json`: **source SHA đầy đủ** và **ZIP SHA-256**. Giữ sidecar cùng ZIP. Không tự đổi SHA bên trong để gắn nhãn freeze.

Packager đọc Git blobs, không đọc nội dung source đang sửa trên working tree. Nếu vừa sửa công cụ nhưng chưa commit, ZIP vẫn chứa bản commit cũ. Nếu file ZIP đã tồn tại, chọn thư mục handoff mới; công cụ từ chối ghi đè để giữ lần bàn giao trước. Archive giữ đường dẫn tương đối và có `source_manifest.json` với hash từng payload. Việc giải nén từ chối traversal, symlink, trùng đích và archive quá 256 MiB chưa nén; kiểm lại toàn bộ hash/inventory trước build.

Upload riêng [Group16_P11_T06_Acceptance.ipynb](../../Group16_P11_T06_Acceptance.ipynb) lên Colab qua **File → Upload notebook**. ZIP và JSON chỉ được upload vào runtime khi cell 2 yêu cầu. Không đổi `synthetic.zip` thành `dataset.zip`.

## 4. Source Mode A — Frozen Published Source

Chỉ dùng sau khi Tuấn bàn giao SHA freeze đã public và có log hồi quy phù hợp. Đặt trong cell Settings:

```python
SOURCE_MODE = "published"
FROZEN_SOURCE_SHA = "<full 40-character SHA confirmed by T02>"
FREEZE_CONFIRMED = True
```

Vẫn upload ZIP local và sidecar để mang **công cụ acceptance chưa public** lên runtime. Production source được fetch read-only từ URL GitHub của nhóm theo SHA chỉ định, checkout detached, kiểm SHA và file V0–V5/helper. Công cụ không fetch `main` thay cho SHA lỗi. Tools SHA và production SHA có thể khác nhau; notebook in rõ cả hai.

Nếu frozen source không có script acceptance thì dùng script từ ZIP công cụ; không chép production kernels từ ZIP lên checkout frozen. Không cần nhánh `chuong/p11-t06-notebook-acceptance` tồn tại trên GitHub.

## 5. Source Mode B — Local Source Archive

Đây là lựa chọn mặc định hiện tại:

```python
SOURCE_MODE = "archive"
FROZEN_SOURCE_SHA = ""
FREEZE_CONFIRMED = False
```

Upload ZIP/JSON đã tạo ở mục 3. Source SHA lấy từ sidecar và phải khớp manifest; toàn ZIP phải khớp SHA-256. Controller giải nén lại vào source directory mới và build từ chính archive này. Không clone GitHub hoặc thay archive bằng checkout khác.

Chỉ đặt `FREEZE_CONFIRMED=True` nếu Tuấn xác nhận **đúng SHA trong archive** là source freeze có evidence hồi quy; giá trị này là khai báo của người vận hành, không phải thuật toán tự xác minh quyết định nhóm. Source archive ứng viên hiện tại không được tự coi là bản frozen. Không upload source ZIP lên GitHub.

## 6. Dataset and Build Preparation

Giữ `DATASET_DIR="/content/group16-dataset"`. Loader `scripts/final_notebook.py::fetch_dataset()` tải `dataset.zip` từ Drive đã cấu hình trong repo, dùng lại `safe_extract()` và `validate_dataset()` của nhóm. Không cần nhập link ảnh mới hay upload lại dataset bằng tay.

Manifest chính thức có SHA-256:

```text
99fc712988075326a351d0bf580405e418bb28d24d56d4cc1b31505c480bdd9d
```

| Runtime site | Official pair | Files |
|---|---|---|
| site1 | thanh-standard1 | small/medium/large, left/right |
| site2 | thanh-standard2 | small/medium/large, left/right |
| site3 | de-standard2 | small/medium/large, left/right |
| challenge | de-challenge1 | small/medium/large, left/right |

Tổng 24 JPEG RGB, không EXIF; kích thước lần lượt 1280×720, 1920×1080 và 3840×2160. Kiểm đúng path, site/side, dimensions, SHA-256 và byte size. Nếu Drive lỗi, tải **đúng dataset.zip chính thức** bằng cách đã dùng trong P7/P8/P9 rồi giải nén vào `DATASET_DIR`; không regenerate/nội suy để làm khớp hash. Runtime report không cần ZIP synthetic riêng: cell lịch sử đọc report đã đóng gói; synthetic/regression T02 có evidence riêng.

Source bắt buộc có `src/v5/v5_image_branch.cu`, không chỉ header hoặc dispatcher. Build theo helper hiện có:

```bash
python scripts/build.py --compiler nvcc --require-t4 --out-dir build
```

Build script hiện dùng `-arch=sm_75 -std=c++11 -O2 --fmad=false`, tự bật `PANORAMA_V5_IMAGE_API_AVAILABLE` khi có API thật. Có thể kiểm lệnh mà chưa compile:

```bash
python scripts/build.py --compiler nvcc --enable-v5 --print-command
```

Trên runtime, producer thử V0–V5 rõ ràng và dừng nếu thiếu version. Không chấp nhận fallback chỉ in “refer to APOD” thay cho bảng V5.

## 7. Run-All Procedure and Runtime Overlay

1. Đọc Settings, chọn source mode và giữ candidate nếu chưa freeze.
2. Chạy **Run all**. Cell setup cài dependency, cell upload dừng để chọn ZIP/JSON; có thể chọn thêm `Group16_Final.ipynb` đã được Thành chốt nếu bản notebook ngoài archive mới hơn.
3. Cell Execute gọi `scripts/accept_final_notebook.py`; theo dõi tên cell đang chạy và thư mục evidence được in ra. Notebook báo cáo chạy trong kernel con theo thứ tự, không chạy song song cell.
4. Sau execution, notebook điều phối luôn cho tải ZIP, kể cả khi report bị lỗi. Cell timeout mặc định 3600 giây/cell; không tự bỏ qua cell chậm hoặc giữ output cũ.

Controller giữ nguyên notebook input trong `Group16_Final.input.ipynb`, tạo bản chạy với đúng SHA ở runtime. **Overlay công khai** gồm:

- Thay cell ID `runtime-setup`: dùng source đã kiểm, path dataset/evidence, SHA thực, 5 timed runs và V0–V5; từ chối cache benchmark tồn tại.
- Trong `thanh-producer`, đổi lời gọi thành `fn.supported_versions(STITCH, candidates=BASELINE_VERSIONS)`. Không sửa implementation helper/kernel.
- Bổ sung ID ổn định cho cell thiếu ID; clear output chỉ trên bản chuẩn bị **trước execution**, không clear sau chạy.

Không thay Markdown, phương pháp, số đo, thuật toán hoặc plotting code. Thay đổi được ghi vào `runtime_overlay.json` và metadata của notebook output. Nếu Thành đổi anchor/API, công cụ dừng để review thay vì đoán replacement. Vì nguyên văn được giữ, các claim chưa chốt trong input vẫn cần sửa bởi T04 rồi chạy lại; PDF export thành công không làm claim đó đúng.

Binary tự thực hiện warm-up/timing; Python chỉ điều phối. `Total_ms` không tính disk I/O, có D2H theo contract. CSV mỗi version được kiểm bằng parser hiện có, gồm Average/Minimum, không giả định vị trí cột V2 giống V1/V3–V5. Benchmark folder mới cho mỗi run, kiểm binary hash của session với binary vừa build.

## 8. Completion Checks and Evidence Layout

Hai trạng thái cần phân biệt:

- `failed`: execution, dataset, build, benchmark hoặc PDF QA thất bại. Giữ toàn bộ log/partial outputs; không ghi hoàn tất T06.
- `executed_review_pending`: notebook và exporter đã xong kiểm tự động; **chưa nghiệm thu cuối**. Phải chốt source freeze, lời văn/số liệu, cặp mẫu môn học, gallery và PDF visual review.

Trong `results/p11-t06/<UTC timestamp>-<run id>/` có các file theo bước đã chạy tới:

```text
Group16_Final.input.ipynb      # Original authored report
Group16_Final.ipynb            # Executed report, or partial report on failure
source_sha.txt
source_manifest.json           # Archive mode
environment.json
dataset.json
dataset_manifest.csv
runtime_overlay.json
execution.log
execution_summary.json
cell_errors.json
build.log
source_logs/                   # Includes build logs even after failure
logs/                          # GPU, nvcc, pip freeze
benchmark/                     # V0-V5 raw CSV, summaries, status logs, panoramas
benchmark_charts/              # Charts and gallery
numerical_audit.json            # Published-table reconciliation; raw V5 not certified
review_required.json
bootstrap_logs/
pdf/Group16_Final.pdf
pdf/Group16_Final.html
pdf/pdf_export.json
pdf/Group16_Final.txt
evidence_checksums.json
```

Controller tạo run-ID mới, không xóa failed run. Notebook JSON/schema/AST, số thứ tự execution, error output, các cell result và ảnh gallery embedded đều được kiểm. Execution count liên tiếp **không đủ**: còn kiểm trạng thái thực thi, output hiện diện, raw benchmark/parser, GPU, source, binary hash và PDF QA. Các kiểm tra này không thay thế regression H/canvas/RGB hoặc memcheck của T02.

## 9. PDF Export and Fallback

Exporter `scripts/export_notebook_pdf.py` nhận **notebook đã chạy có output**, từ chối notebook chưa chạy, count bị bỏ/skipped, error output hoặc thiếu output visible. Output cuối tên `Group16_Final.pdf`.

Luồng ưu tiên: nbconvert HTML có embedded images → Chromium headless → MathJax 3 SVG đã typeset → PDF A4 landscape. Print CSS wrap code/URL, lặp table header, giữ ảnh trong bề ngang trang; không sửa ảnh benchmark. Trước in, chờ font/ảnh/công thức load xong; lỗi MathJax hoặc ảnh không tải được là lỗi export, không được in TeX thô rồi coi đạt.

Nếu Chromium lỗi, giữ `chromium-error.log` và HTML. Fallback XeLaTeX được thử khi có cả `pandoc` và `xelatex`; dùng lại notebook/output gốc. Trên Colab, nếu cần fallback:

```bash
apt-get update -qq
apt-get install -y pandoc texlive-xetex texlive-fonts-recommended texlive-latex-extra
```

Không cài TeX mặc định vì dung lượng lớn. Giữ log lỗi trước khi retry; dùng thư mục PDF mới:

```bash
python scripts/export_notebook_pdf.py <run>/Group16_Final.ipynb \
  --output-dir <run>/pdf-retry-1
```

PDF QA kiểm header/structure/page count, text extraction, đủ heading 10 mục, dấu replacement Unicode và image objects khi có raster outputs. Exporter luôn ghi **visual review pending**: phải render và xem toàn bộ trang, nhất là bảng timing rộng, công thức, caption, seam/crop, dấu tiếng Việt và page breaks.

```bash
apt-get install -y poppler-utils
pdftoppm -png -scale-to 1600 <run>/pdf/Group16_Final.pdf <run>/pdf/page
```

Nếu thiếu layout/ảnh/công thức, không công bố PDF là đạt. Render từng trang và lưu nhận xét. Smoke test local của exporter không phải PDF kết quả đồ án.

## 10. Download and Return Evidence

Cell Download dùng `google.colab.files.download()` để tải ZIP. ZIP chứa notebook có output và PDF nếu xuất được. Đặt `DOWNLOAD_INDIVIDUAL_FILES=True` nếu muốn tải riêng hai file ngoài ZIP. Không mount Drive bắt buộc; nếu muốn, người chạy tự upload ZIP vào folder evidence của nhóm sau khi kiểm tra.

Đưa ZIP và JSON checksum sidecar về local, kiểm SHA-256 rồi giải nén vào thư mục mới dưới `results/p11-t06/`; không đè evidence cũ. Có thể recheck artifact:

```bash
python scripts/accept_final_notebook.py --validate-run results/p11-t06/<run-id>
```

Lệnh này kiểm hash evidence, notebook output/source/GPU manifest và PDF, tạo JSON validation mới. Kết quả `automatic_checks_passed_manual_review_pending` **không tự xác nhận** các claim khoa học, chất lượng đường nối, trạng thái cặp mẫu hoặc source freeze. Ghi riêng người kiểm/phiên bản/số trang/nhận xét; không sửa log gốc. Khi thêm review/render files, tạo ZIP mới bằng `bundle(run)`; không xóa archive cũ.

## 11. Common Failure Recovery

| Failure | Recovery |
|---|---|
| GPU khác T4, thiếu nvcc hoặc preflight dependency | Giữ manifest lỗi, đổi sang T4 runtime mới; không sửa điều kiện tên GPU để cho qua. |
| Drive thiếu quyền/quota, sai manifest | Kiểm quyền tải dataset chính thức; giữ log và dùng bản ZIP cùng hash. Không dùng raw/synthetic ZIP thay thế. |
| SHA public không fetch được hoặc thiếu V5 | Xác minh SHA T02 hoặc dùng archive candidate; không fallback main. |
| ZIP không khớp sidecar | Tạo/copy lại đúng cặp ZIP/JSON; không cập nhật hash chỉ để hợp thức hóa file chưa rõ nguồn. |
| Source/workspace hoặc benchmark đã tồn tại | Giữ lần cũ, dùng run-ID mới; không tiếp tục từ cache không rõ provenance. |
| Build/CLI V5 lỗi | Trả build log/SHA cho Tuấn/Thành; không bỏ V5 khỏi danh sách để gọi lượt chạy là đạt. |
| Cell lỗi hoặc timeout | Tải ZIP lỗi; xem `failure.log`, `cell_errors.json`, partial notebook và execution.log; sửa input/source rồi chạy mới. |
| Chromium/MathJax/CDN lỗi | Giữ HTML/error log; kiểm mạng hoặc cài fallback như mục 9; không export PDF thiếu công thức. |
| PDF bị tràn/cắt | Trả nhận xét layout cho Thành; sửa bản input theo T04 rồi export lại trong thư mục mới, không sửa chart số liệu bằng ảnh. |

Nếu setup lỗi trước controller, log nằm tại path `group16-p11-bootstrap-*` in trong cell; tải bằng `files.download(str(SETUP_ROOT / "setup.log"))`. Nếu user ngắt runtime hoàn toàn, Colab không bảo đảm giữ storage; tải failure evidence trước khi reset.

## 12. Local Validation and Final Checklist

Đã kiểm local bằng Windows/Python 3.14 và venv không commit tại `build/p11-venv`. Bộ test notebook audit/preflight/source/PDF/acceptance có **28 test đạt**. Manifest chính thức có đúng 24 path/pair và hash; chưa có đủ ảnh trong dataset local để gọi đó là kiểm 24 ảnh runtime. Build command in đúng sm_75/V0–V5, chưa compile CUDA ở máy này.

Toàn bộ Python regression sau tích hợp: **221 test, không failures/errors, 2 skip** (snapshot giữa kỳ có output không commit; test thiếu T02 không áp dụng vì implementation thật đã có). Các test failure-path cố ý in log lỗi hoặc trạng thái failed; không phải lỗi regression. Source archive generation/extraction được kiểm trên Git fixture đã commit, gồm sửa working tree, file untracked, checksum/SHA sai và traversal. Chưa chạy GPU, Run all T4 hoặc sanitizer trong lượt chuẩn bị này.

PDF smoke riêng đã thực thi cell Python trên CPU và export bằng nbconvert 7.17.2, Playwright 1.65.2/Chrome: **2 trang, một công thức MathJax đã render, một biểu đồ embedded, không có clipping candidate hoặc lỗi QA tự động**. Text extraction có đúng tiếng Việt; đã render/xem cả hai trang. Output nằm trong `build/p11-pdf-smoke/`, tên **Group16_PDF_Smoke.pdf**, không commit và không dùng thay báo cáo cuối. Unit test cũng kiểm đường lỗi/fallback giữ log. Fallback XeLaTeX chưa smoke vì local không có pandoc.

Lệnh test:

```bash
python -m unittest discover -s tests/python -p 'test_notebook_*.py' -v
python scripts/export_notebook_pdf.py --check-deps
git diff --check
```

Checklist trước khi Chương ghi T06 Xong:

- [ ] T02 xác nhận full frozen SHA và evidence hồi quy/memcheck tương ứng.
- [ ] T04 chốt notebook 10 mục, sửa số V5/probe/production, có output làm căn cứ và gallery cặp mẫu.
- [ ] Source mode/SHA/archive checksum rõ ràng; không có fallback sang main hoặc code local khác.
- [ ] Fresh Colab T4/sm_75, dataset hash đúng; Run all không lỗi, đủ V0–V5 cùng session, không có cell bị bỏ qua.
- [ ] Giữ execution outputs, benchmark/logs/manifest; đối chiếu từng số trong lời văn, không ghép số từ session khác.
- [ ] Đọc gallery và challenge, xác nhận status parity không bị hiểu thành chất lượng ảnh tốt.
- [ ] Export Group16_Final.pdf và kiểm thực tế từng trang; đủ heading/ảnh/bảng/công thức, tiếng Việt và đường dẫn nguồn.
- [ ] Tải ZIP evidence, kiểm checksum local, giữ cả failure attempts và nhận xét review.

**PREFLIGHT READY — SOURCE FREEZE PENDING**
