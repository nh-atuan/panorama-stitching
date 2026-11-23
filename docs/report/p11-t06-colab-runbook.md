<!-- Authors: Le Ha Thanh Chuong (23120195). External source: repository tools and reports cited below. -->

# P11-T06 — Final Colab T4 Acceptance Runbook

## 1. Trạng thái và phạm vi

Cập nhật ngày 23/11/2026 trên nhánh `chuong/p11-t06-final-acceptance`, base public `cd5ee9d4bb6724b6a816d4d185f0531c47d43d17`. PR #56–58 đã merge; notebook có 43 cell, 20 code, 10 mục và giữ nguyên ID/anchor. Cell V5 đã bỏ regex theo câu văn cũ, đọc bảng benchmark, Pre-S4, năm khối luân phiên và NSYS bằng parser dùng chung. Nội dung mục 6/7/9 theo [phân tích cập nhật](p10-t06-v5-analysis.md).

Đây là **chuẩn bị nghiệm thu**, chưa phải chứng nhận T4 hoặc PDF cuối. Local kiểm Python và PDF smoke không thay Run all GPU. Báo cáo P10-T05 là lịch sử riêng; raw archive của Đế chưa được kiểm độc lập trong lượt chuẩn bị này.

## 2. Source và tooling được định danh riêng

| Phạm vi | Revision / ý nghĩa |
|---|---|
| Production source mặc định | `cd5ee9d4bb6724b6a816d4d185f0531c47d43d17`, reachable từ origin/main khi chuẩn bị |
| Report/tooling hiện tại | Exact local commit ghi trong JSON sidecar và source_manifest của ZIP; không gọi đây là revision đã public |
| Freeze cũ P11-T02 | `f2837a85b770e6c8bb2eba1bb6de7aee7fa23eb7` |
| Benchmark Đế | `26c8f241e056a7cf5e0c5bb0d85f036d9eafd9e1`; src/build khớp production pin |

Pin mới chứa V0–V5, API một ảnh và helper benchmark, dataset, CLI. So với freeze cũ, `src/v5/v5_image_branch.cu` có thêm host validation về Config, view/stride, scratch/alignment và capacity. Vì vậy không coi regression cũ bao phủ toàn bộ source mới. Không sửa CUDA trong nhánh chuẩn bị này; cần build/regression trên T4 với source được chọn để bổ sung bằng chứng.

Parser báo cáo mới không nằm trong production pin public. ZIP mang `scripts/v5_report.py`, notebook sửa và bộ công cụ acceptance có hash riêng. Controller nạp đúng parser từ ZIP bằng đường dẫn tuyệt đối, kiểm SHA-256, ghi tooling_files và hash notebook input vào metadata. Source production vẫn giữ nguyên; không chép helper hoặc sửa report trong checkout đã xác minh. Integration test đã mô phỏng đúng trường hợp production pin cũ + parser mới và chạy đủ đường phân tích CPU.

Mode `published` là mặc định: công cụ trong ZIP, production fetch từ SHA public trên. Mode `archive` dùng exact Git commit của ZIP làm **source thực**; overlay runtime và manifest đều ghi SHA đó. Archive mới chỉ thay tooling/docs so với production pin, nhưng vẫn là candidate so với freeze cũ. Không đặt FREEZE_CONFIRMED=True để ép qua kiểm tra.

## 3. Đóng gói từ local

Sau khi đã commit tất cả sửa đổi của task:

```powershell
python scripts/package_notebook_acceptance.py --ref HEAD --output build/p11-t06-final-acceptance/Group16_P11_T06_Source.zip
```

Packager chỉ lấy blob đã commit, không lấy working-tree/untracked, dataset, output hoặc build. Không overwrite ZIP cũ: chọn thư mục mới cho lần đóng gói khác. Giữ cùng nhau:

- `Group16_P11_T06_Source.zip`
- `Group16_P11_T06_Source.json` (source_sha/tooling revision và archive_sha256)
- `Group16_P11_T06_Acceptance.ipynb` mới nhất, có sẵn cả trong ZIP.

Không upload nhầm gói cũ ở `build/p11-t06-review/`. ZIP mới có notebook đã sửa regex và parser mới. Manifest kiểm inventory, từng checksum, Git SHA và so sánh freeze; giải nén từ chối traversal, symlink, duplicate và payload vượt ngân sách.

## 4. Chạy Colab T4

1. Mở `Group16_P11_T06_Acceptance.ipynb` mới nhất trên Colab.
2. Chọn **Runtime → Change runtime type → T4 GPU**.
3. Giữ Settings mặc định:

```python
SOURCE_MODE = "published"
PUBLIC_SOURCE_SHA = "cd5ee9d4bb6724b6a816d4d185f0531c47d43d17"
FREEZE_CONFIRMED = False
DATASET_DIR = "/content/group16-dataset"
```

4. Chọn **Run all**. Hộp upload nhận đúng ZIP + JSON mới; không cần upload riêng report notebook vì bản sửa nằm trong ZIP. Dependency setup có log và không thay CUDA toolkit.
5. Loader tải dataset chính thức từ Drive bằng cấu hình nhóm trong `scripts/notebook/final_notebook.py`. Manifest bắt buộc SHA-256 `99fc712988075326a351d0bf580405e418bb28d24d56d4cc1b31505c480bdd9d`, đủ 24 JPEG của site1/site2/site3/challenge, ba cỡ, trái/phải. Không regenerate ảnh để làm khớp hash. Nếu Drive lỗi, dùng dataset.zip chính thức đã có và chỉ định DATASET_DIR.
6. Theo dõi controller: GPU T4/sm_75, môi trường, dataset, build, thứ tự cell và thư mục evidence. Không chạy đồng thời profiler hoặc benchmark khác trong phiên đo cuối.
7. Cell download tải ZIP evidence, kể cả khi chạy lỗi. Không bỏ log/partial output và không tiếp tục dùng output cũ.

Source được fetch đúng SHA, không fallback về main. Runtime overlay thay bootstrap để dùng source/evidence đã xác minh; producer được truyền rõ V0–V5. Overlay không đổi Markdown, phương pháp, số đo hoặc plots. Manifest ghi source SHA thực và hash helper/nhật ký overlay. Report trong ZIP công cụ được dùng làm input, không thay bằng notebook cũ ở production pin.

## 5. Build, regression và memcheck trên cùng source

Controller build notebook qua helper chuẩn: `sm_75 -std=c++11 -O2 --fmad=false`, tự bật API V5. Nếu cần đối chiếu freeze cho source mới, chạy các lệnh dưới tại checkout production mà controller in trong evidence, lưu stdout/stderr và exit code cạnh evidence:

```bash
python scripts/build.py --compiler nvcc --require-t4 --out-dir build
python tests/run_tests.py --compiler nvcc --require-t4
compute-sanitizer --tool memcheck --leak-check full --error-exitcode 99 ./build/tests_gpu/gpu_v4_pipeline
compute-sanitizer --tool memcheck --leak-check full --error-exitcode 99 ./build/tests_gpu/gpu_v5_pipeline
```

Các lệnh là phần GPU người vận hành chạy, chưa được thực hiện local. Source pin có suite GPU/Python tại thời điểm commit public; parser/test tooling mới được kiểm riêng từ ZIP. Muốn kiểm Python mới trên Colab, chạy runner ở TOOLS_ROOT, không nhầm với source pin. Chỉ đóng freeze khi có evidence đúng SHA, không lấy số đếm suite cũ áp cho checkout mới.

## 6. Đọc kết quả và xuất PDF

Bản chạy mới cần đủ V0–V5, mỗi version một warm-up tự động và ít nhất năm timed runs. Mỗi bảng so sánh mới dùng cùng GPU/binary/session/dataset. GPU stages dùng CUDA events; Total_ms được đồng bộ sau D2H và không gồm disk I/O. Sum duration các stage/kernel V5 có thể overlap và không là elapsed Total.

Cell lịch sử P10-T05 in thời gian V0/V4/seq/dual, ratios tính lại, Pre-S4, năm khối, NSYS và provenance. Từ bảng mean làm tròn: GM V5/V4 1.068633×; dual/seq 1.036413×; Pre-S4 1.256430×; median khối 1.066629×; 3/5 khối có lợi. Không coi đây là timing của phiên mới. T01 share thuộc probe instrumented, không production.

Exporter xuất `pdf/Group16_Final.pdf` bằng nbconvert + Chromium; render Mermaid và MathJax trước in, kiểm PDF text/heading/image. Mạng/CDN lỗi phải giữ log và báo thất bại, không chấp nhận TeX thô. PDF smoke local chỉ kiểm khả năng trình bày, không thay bản đầy đủ sau Run all.

## 7. Evidence và điều kiện đóng task

ZIP evidence gồm notebook input/output (hoặc partial), runtime overlay, source/tooling hashes, GPU/dataset manifest, build/execution log, benchmark CSV/status/gallery, numerical audit, PDF và checksums. `validate_artifacts` kiểm hash, kết quả tự động và PDF cơ bản; `executed_review_pending` vẫn cần người đọc duyệt.

Sau chạy, kiểm:

- Không cell lỗi; output và execution order đầy đủ, source SHA khớp manifest.
- Không thiếu ca chuẩn; challenge medium/large ghi đúng NumericalFailure thay vì timing giả.
- Các số trong lời văn khớp output theo đúng phiên; bảng lịch sử khác bảng mới có nhãn rõ.
- Xem ảnh đầu vào/panorama/crop, giải thích challenge; kiểm trạng thái cặp mẫu môn học.
- Render và xem **từng trang** PDF: tiếng Việt, công thức inline/display, Mermaid, bảng, biểu đồ, page break.
- Giữ evidence regression/memcheck mới đúng source nếu dùng để đóng freeze; không tự suy từ benchmark PASS.
- Chốt P10-T06/P11-T06 sau khi đáp ứng tiêu chí task. Video link và bản cập nhật bài nộp sau P12/P13 là phần việc riêng, không giả định đã có.

Không tự push, tạo PR hoặc merge trong workflow. Bộ chuẩn bị này không chứng nhận T4 hay PDF cuối trước khi nhận và rà evidence.
