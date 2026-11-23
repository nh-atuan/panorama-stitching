<!-- Authors: Le Ha Thanh Chuong (23120195). External source: repository code, reports and locally generated checks cited below. -->

# P10-T06 / P11-T06 — Final Acceptance Preparation

## Branch và ranh giới công việc

Nhánh local: `chuong/p11-t06-final-acceptance`. Base: `cd5ee9d4bb6724b6a816d4d185f0531c47d43d17`, khớp origin/main lúc bắt đầu. PR #56–58 đã merge; không tiếp tục nhánh P11-T06 cũ. Không push, tạo PR hoặc merge trong lượt này. Giữ nguyên hai mục untracked có sẵn: `docs/report/version-evolution-v0-v5.md` và `p3-t04/`.

Không thay `src/`, thuật toán, Config, ngưỡng nghiệm thu hoặc `scripts/build.py`. P10-T06 đã xong phần triển khai nội dung/chuẩn bị; tiêu chí nghiệm thu trọn vẹn còn mở. P11-T06 vẫn Đang làm đến khi có Run all T4, output đầy đủ và PDF được duyệt.

## Lỗi và sửa ở nguyên nhân gốc

Cell thật `v5-p10-results` đã được tái hiện qua test CPU: regex tìm câu kết luận APOD cũ trả None rồi `.group()` gây AttributeError. Các regex tìm Pre-S4 phía sau cũng lỗi thời. Report mới có schema bảng khác và thêm sequential, paired blocks, NSYS; không giải quyết bằng guard hoặc số fallback.

`scripts/v5_report.py` đọc bảng theo header, kiểm row width/field, số hữu hạn và đơn vị, đúng chín ca chuẩn, năm khối luân phiên tại site2/large, chín cấu hình profiler. Parser dùng chung cho notebook và numerical audit. Decision đọc từ các nhãn production/case-study trong mục APOD; không tự suy lựa chọn nhóm từ speedup. Thiếu bảng/field/provenance phải lỗi rõ tên nguồn. Số liệu speedup được tính từ ms, không đọc cột ratio đã làm tròn. Hàm table reader cũng được dùng lại bởi các cell lịch sử.

## Kết quả và cách diễn giải

Từ bảng báo cáo chính thức [P10-T05](p10-t05-v5-apod.md), không phải raw CSV/SQLite đã kiểm độc lập:

| Metric | Tính lại |
|---|---:|
| GM V5/V0, chín ca chuẩn | 49.876178× |
| GM V5/V4, chín ca chuẩn | 1.068633× |
| GM V5 dual/sequential | 1.036413× |
| GM Pre-S4 sequential/dual | 1.256430× |
| site2/large Pre-S4 | 13.700 → 10.971 ms |
| Median năm paired-block ratios | 1.066629× |
| Khối có lợi cho V5 | 3/5 |
| NSYS overlap V5 dual | 16.6–24.5% |
| Peak VRAM dual trừ V4, ba ca large | 64.30 MiB |

Pre-S4 GM 1,256430× từ mean làm tròn khác chữ số cuối so với 1,2565× trong report. Cần sidecar gốc để đối soát; không sửa số cho khớp bằng tay. Archive Đế chưa có local; checksum/provenance trong report được in, raw_independently_verified luôn False. Bảng chính có 8/9 ca nhanh hơn V4, không gọi mọi ca đều nhanh hơn dựa trên lượt đo lại.

Notebook giữ **43 cell, 20 code cell và toàn bộ ID/anchor**. Mục 6 hiển thị đủ bảng timing, Pre-S4, stability, profiling và provenance; mục 7 tách so sánh cùng phiên khỏi lịch sử; mục 9 giải thích lợi ích có thật nhưng chưa nhất quán và giữ V4 production/V5 case study. T01 share dùng Total_probe instrumented. V4 đúng thứ tự stage-by-stage từ source, không xử lý trọn A trước B. [Phân tích chi tiết](p10-t06-v5-analysis.md)

## Source pin và freeze coverage

Production pin public: `cd5ee9d4bb6724b6a816d4d185f0531c47d43d17`. Mọi file V0–V5, API một ảnh, helper benchmark/dataset và hai ảnh profiling V4 cần cho cell đều có tại pin. Reachability được đối chiếu origin/main; đây không phải branch name thay đổi theo thời gian.

So với freeze `f2837a85b770e6c8bb2eba1bb6de7aee7fa23eb7`, source pin có thêm host validation trong `src/v5/v5_image_branch.cu`; cần nghiệm thu mới. So với source benchmark Đế `26c8f24`, src/build khớp. Mọi commit nhánh này chỉ đổi tooling/test/notebook/docs/assets metadata, không thay production scope.

Parser mới không nằm trong production pin. Gói công cụ exact local commit mang notebook và parser; controller nạp parser từ đường dẫn tuyệt đối, kiểm hash và lưu tooling_files trong metadata. Không sửa checkout production hoặc dùng notebook cũ từ pin. Test integration giải nén production pin, nạp parser hiện hành và chạy đường phân tích thật, gồm cell profiling đọc ảnh.

Mặc định `SOURCE_MODE="published"`, PUBLIC_SOURCE_SHA là pin trên, FREEZE_CONFIRMED=False. Mode archive vẫn có, dùng SHA của ZIP làm source thực; overlay/runtime/manifest phải cùng SHA. [Runbook](p11-t06-colab-runbook.md)

## Local preflight và giới hạn

Lệnh chuẩn:

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:MPLBACKEND='Agg'
python tests/run_tests.py --group python
python scripts/audit_final_notebook.py --notebook Group16_Final.ipynb --frozen-source f2837a85b770e6c8bb2eba1bb6de7aee7fa23eb7 --apod docs/report/p10-t05-v5-apod.md --output build/p11-t06-final-audit.json
git diff --check
```

Đã chạy bằng `build/p11-venv/Scripts/python.exe`: 23 suite, 260 tests, không failure/error; hai skip có điều kiện (snapshot giữa kỳ có output không commit và phép thử stub T02 khi implementation thật đã có). Có integration thực thi cell V5 thật, Decimal độc lập, thiếu/sai bảng/field/số, challenge exclusion, pin/freeze, archive verification và parser provenance. Nbformat, AST, 10 mục, anchor, Markdown local links và output-free đều đạt.

Static audit còn 22 findings có chủ đích: 20 cell chưa có output, một UNEXECUTED_CELLS và một FREEZE_MISMATCH. Đây là các gate còn chờ T4/freeze, không bị xóa để tạo báo cáo xanh. Không có lỗi syntax/section/pin-file/link hoặc placeholder mới.

PDF smoke CPU ở `build/p11-t06-final-smoke/`: chạy kernel thật hai cell smoke, trong đó chuẩn bị và thực thi đường phân tích lịch sử; dùng nội dung V5/kết luận hiện hành. Chromium xuất 12 trang, Mermaid 1 sơ đồ, MathJax 3 công thức; QA không có clipping candidate hoặc lỗi text. Đã render đủ 12 trang và kiểm trực quan. Đây không phải `Group16_Final.pdf` đầy đủ; còn phải kiểm Mermaid trên Colab và từng trang PDF cuối sau Run all. Pandoc không có nên không kiểm fallback XeLaTeX.

Local không có nvcc/T4 và chưa có dataset/manifest.csv chính thức. Không chạy build CUDA, GPU suites, memcheck, tải dataset Drive hoặc benchmark mới trong lượt này. Dataset validator và đường lỗi được unit test; 24 ảnh thực vẫn phải kiểm hash trên Colab.

## Gói bàn giao và bước tiếp theo

Gói mới tại `build/p11-t06-final-acceptance/Group16_P11_T06_Source.zip` cùng `.json`. Exact tooling commit và ZIP SHA-256 ở sidecar; không commit ZIP/build/output. Gói chỉ lấy blob đã commit, loại untracked và giữ manifest/checksums. Đã bổ sung allowlist hai ảnh profiling `slides/generated/nsys-v4.png` và `ncu-v4.png`, tránh lỗi cell khi chạy mode archive. Không đóng toàn bộ slide hoặc thêm cây source trùng lặp trong ZIP.

Mở `Group16_P11_T06_Acceptance.ipynb` mới nhất, chọn T4, giữ published/default pin và FREEZE_CONFIRMED=False, Run all, upload ZIP + JSON mới. Dataset tự tải từ Drive. Tải evidence sau chạy, kể cả partial nếu lỗi. Theo runbook chạy regression/memcheck đúng checkout khi bổ sung freeze evidence.

Chương còn: nhận output T4, đối chiếu mỗi claim theo đúng session, kiểm gallery/cặp mẫu môn học, kiểm PDF đầy đủ, đóng P10-T06/P11-T06 khi đạt. Quy trình không tự đánh Xong từ CPU smoke và không tự xuất bản lên GitHub.

**READY FOR COLAB T4 RUN** — sẵn sàng chạy workflow nghiệm thu candidate, chưa chứng nhận kết quả GPU hoặc PDF cuối.
