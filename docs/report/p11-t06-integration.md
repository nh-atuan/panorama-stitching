<!-- Authors: Le Ha Thanh Chuong (23120195). External source: repository source, freeze report and local validation cited below. -->

# P11-T06 — Upstream Integration and Acceptance Tooling

## 1. Integration Baseline

Ngày kiểm tra: 22/11/2026, nhánh local `chuong/p11-t06-notebook-acceptance`.

- HEAD trước tích hợp: `546085e96b5e42972e1405f386c14d2c2e65faff`.
- Upstream sau fetch: `26c8f241e056a7cf5e0c5bb0d85f036d9eafd9e1`, chứa PR #52–#55.
- Merge base: `4a20d1a93607851a8fc48bccbbfe206a07c0a787`.
- Merge commit: `b768452`, normal merge bằng `ort`, không reset/rebase/squash.
- Không có conflict. Hai file dùng chung `docs/task-board.md`, `tests/run_tests.py` auto-merge; đã kiểm đủ trạng thái mới của Tuấn/Thành và các suite acceptance của Chương.
- Giữ hai mục untracked `docs/report/version-evolution-v0-v5.md`, `p3-t04/`; không đưa chúng vào commit hoặc ZIP.
- Không push, tạo PR hoặc thay đổi remote. Không sửa production CUDA, build flags hoặc pin báo cáo để hợp thức hóa tooling.

## 2. Notebook Structure

[Group16_Final.ipynb](../../Group16_Final.ipynb) giữ nguyên byte từ upstream, SHA-256 `cbd7622df7fdb94bde3d8bce559fad3d99d402f2aac6d1a53ba5726d6e983b69`. Có 43 cell, 20 cell code; nbformat valid, ID đầy đủ, AST Python parse được. Các code role thiết yếu được kiểm theo thứ tự phụ thuộc, không khóa tổng cell count.

| Section | Anchor | Cell |
|---|---|---:|
| 1. Thông tin nhóm | team-information | 2 |
| 2. Giới thiệu | introduction | 6 |
| 3. Phương pháp đã chọn | chosen-methods | 7 |
| 4. V0 tuần tự | v0-sequential | 9 |
| 5. V1 CUDA cơ bản | v1-basic-cuda | 13 |
| 6. Các phiên bản tối ưu | optimized-versions | 17 |
| 7. So sánh tổng hợp | final-comparison | 34 |
| 8. Kết quả ghép ảnh | results-gallery | 38 |
| 9. Kết luận | conclusion | 42 |
| 10. Tài liệu tham khảo | references | 43 |

Validator chấp nhận đổi tên hiển thị hợp lệ; vẫn từ chối thiếu/nhân đôi/sai thứ tự section, anchor sai, body rỗng, thiếu code role và code role đặt trước dữ liệu cần dùng. Runtime chuẩn bị bản copy chỉ đổi bootstrap/source, version probing và ID khi cần; không sửa Markdown, phương pháp hoặc đo lường.

Audit có freeze reference hiện trả đúng **21 finding chưa lưu output**: 20 entry MISSING_OUTPUT và một UNEXECUTED_CELLS. Không còn finding mất file tại pin, V5 bị bỏ qua hoặc sai heading/ID. Exit 1 là đúng vì bản Git chưa có output; không coi đó là acceptance PASS. Những vấn đề khoa học trong lời văn vẫn cần review thủ công, không thể giải quyết chỉ bằng schema/regex.

## 3. Imports and Execution Dependencies

Các module acceptance được chuyển sang import package hiện có:

- `notebook.midterm_notebook`, `notebook.package_s6_verification`, `notebook.final_notebook`.
- `profiling.profiling_common`.
- File yêu cầu tại pin dùng `scripts/notebook/` và `scripts/dataset/prepare_dataset.py`.

Không tạo alias file cũ hoặc chép helper để tránh sửa import. `scripts/` vẫn là entry-point root theo quy ước của nhóm. [Hướng dẫn scripts](../../scripts/README.md) và [runbook](p11-t06-colab-runbook.md) mô tả CLI thực.

Chín cell evidence 8,10,14,19,21,23,25,27,32 đã chạy tuần tự trên CPU. Chúng kiểm đọc tham số/report và tính bảng lịch sử V0–V5; cell profiling có cảnh báo backend Agg không interactive, không lỗi. Chưa chạy producer GPU, benchmark mới hoặc gallery runtime. Không dùng số timing của cell lịch sử làm cùng-session comparison cuối.

Controller lấy notebook tác giả mới nhất từ ZIP công cụ hoặc file upload rõ ràng, ngay cả khi production checkout dùng SHA cũ đã kiểm chứng. Giữ `Group16_Final.input.ipynb`, input hash và runtime overlay độc lập; không âm thầm thay notebook Thành vừa bàn giao bằng notebook cũ trong source pin.

## 4. Source Pin and Freeze Coverage

[Báo cáo T02](p11-t02-freeze-verification.md) ghi SHA đã chạy T4 `f2837a85b770e6c8bb2eba1bb6de7aee7fa23eb7`: V0/GPU/Python suites và hai target memcheck. Đây là phạm vi đã được người chạy báo cáo, không phải lần nghiệm thu mới của Chương.

| Revision | Comparison against f2837a8 | Consequence |
|---|---|---|
| Notebook pin `696fc82c72b2098ea7ca24c7c89efdab9d3452ec` | `src/` và `scripts/build.py` giống hoàn toàn; helper/report/notebook đã đổi vị trí/nội dung. | Giữ pin. Có thể dùng snapshot này cho production đã kiểm theo phạm vi source, nhưng phải chạy lại notebook mới và kiểm helper/runtime. |
| Upstream `26c8f24` và nhánh tích hợp hiện tại | Thêm thay đổi `src/v5/v5_image_branch.cu`: kiểm host Config, view/stride, scratch, capacity và attribution; không chỉ thay docs. | Không lấy báo cáo T02 cũ để khẳng định source mới đã đạt. Archive HEAD là candidate, cần nghiệm thu phù hợp SHA mới. |

Công cụ ghi cả SHA chạy và SHA freeze, phân loại production/tooling/docs; thay đổi production làm `src_build_equivalent=false`. Manifest ZIP chứa comparison tính từ Git commit. Published mode fetch đúng SHA cùng freeze ref để so sánh; `--frozen` bị từ chối khi khác production hoặc thiếu bằng chứng so sánh. Không fallback main. So sánh bằng nhau trong src/build không chứng minh helper mới đã được chạy T4.

## 5. Mermaid and PDF

Cell Giới thiệu chứa một Mermaid flowchart. Exporter tạo bản copy chỉ dùng để render, phát hiện fence, giữ nguyên mã tại `pdf/mermaid_sources.json`, render SVG trước in. Dùng Mermaid 11.4.1 và API `mermaid.render` theo [hướng dẫn chính thức](https://mermaid.js.org/config/usage.html). Nếu renderer/CDN lỗi hoặc thiếu SVG, export thất bại rõ; không dùng LaTeX fallback để in Mermaid thô. Fallback LaTeX cũ chỉ còn áp dụng cho notebook không có sơ đồ.

Smoke mới tại `build/p11-integrated-smoke/`: notebook ghi rõ SMOKE ONLY, có đúng sơ đồ của report, công thức, tiếng Việt, bảng và chart từ cell CPU vừa chạy. Export được hai trang; manifest ghi 1 Mermaid, 1 MathJax, 1 ảnh embedded, không clipping candidate hoặc lỗi QA. Đã render/xem cả hai trang, đọc được nhãn diagram và không thấy mã Mermaid thô. Đây không phải `Group16_Final.pdf` nghiệm thu T4. Không đóng gói log/PDF smoke cũ làm evidence mới.

## 6. Validation and Handoff

Các kiểm tra đã chạy:

**Kết quả toàn bộ Python regression cuối: 237 test, không failures/errors, 2 skip có chủ đích.** Hai skip vẫn là snapshot giữa kỳ có output không commit và test thiếu API T02 không áp dụng khi API thật đã có. Không dùng con số 221 của phiên cũ cho bản tích hợp này.

- Python suite toàn repo; các suite notebook audit/acceptance/source/PDF, kể cả negative fixtures.
- nbformat + AST cho notebook chính và notebook điều phối; import tất cả module acceptance bằng package mới.
- Source pin inventory, Git diff scope và source ZIP round-trip bằng manifest/hash.
- Manifest dataset chính thức: 24 path, SHA-256 `99fc712988075326a351d0bf580405e418bb28d24d56d4cc1b31505c480bdd9d`. Chưa kiểm toàn bộ ảnh thật tại máy này.
- Exporter smoke mới có Mermaid và MathJax; code-source/Markdown gốc không đổi.
- `git diff --check`, đối chiếu `src/`, `scripts/build.py`, `Group16_Final.ipynb` không có chỉnh sửa local so upstream.

Lệnh tái lập:

```bash
python -m unittest discover -s tests/python
python scripts/audit_final_notebook.py \
  --frozen-source f2837a85b770e6c8bb2eba1bb6de7aee7fa23eb7 \
  --output build/p11-integrated-audit.json
python scripts/package_notebook_acceptance.py --ref HEAD \
  --output build/p11-t06-integrated/Group16_P11_T06_Source.zip
```

ZIP/JSON handoff mới nằm tại `build/p11-t06-integrated/`; manifest ghi exact committed SHA và ZIP SHA-256. ZIP `546085e` cũ ở folder khác là lịch sử, không dùng cho notebook cấu trúc mới. ZIP mới chỉ có committed payload, không chứa dataset/build/output/untracked. Phải tạo lại sau commit cuối; không đưa ZIP lớn vào Git.

## 7. Remaining Acceptance Work

- **P10-T06:** Chương chốt kết luận V5 mục 9; đối chiếu APOD 1,027×/1,039× với bảng tính lại 1,10133×/1,02859×, ghi rõ thiếu raw/session. Giữ V4 production/V5 case study; không đổi quyết định bằng aggregate sau nghiệm thu.
- Sửa diễn giải V4 là S1(A,B) → S2(A,B) → S3(A,B), phân biệt V5 branch-serial ablation; pre-S4 21,44% là mean share của probe T01. Chưa sửa các lời văn này trong nhiệm vụ tích hợp tooling.
- Chốt source thực nghiệm: snapshot pin có production scope đã kiểm hoặc HEAD candidate cần hồi quy mới. Không đổi pin chỉ để theo HEAD mới nhất.
- Fresh T4 Run all, lưu đủ output, đo V0–V5 cùng phiên, đọc gallery/challenge và cặp mẫu môn học; kiểm mọi số trong lời văn với output.
- Export PDF cuối, render/xem toàn bộ trang; lưu ZIP/hashes và nhận xét. Hạ tầng local đạt không đồng nghĩa T06 đã Xong.

**INTEGRATION COMPLETE — READY FOR P10-T06**
