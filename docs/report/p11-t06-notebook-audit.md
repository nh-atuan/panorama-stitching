<!-- Authors: Le Ha Thanh Chuong (23120195). External source: repository requirements, source and experiment evidence cited below. -->

# P11-T06 — Final Notebook Acceptance Audit

## 1. Repository Baseline and Scope

Audit ngày 20/11/2026 trên nhánh local `chuong/p11-t06-notebook-acceptance`, tạo từ `origin/main` sau fetch tại **`4a20d1a93607851a8fc48bccbbfe206a07c0a787`**. SHA này trùng mốc yêu cầu. Không push, tạo PR hoặc thay đổi remote. Hai mục có sẵn chưa được Git theo dõi là `docs/report/version-evolution-v0-v5.md` và `p3-t04/` được giữ nguyên.

Notebook được kiểm tra: [Group16_Final.ipynb](../../Group16_Final.ipynb), 42 cell: 23 Markdown và 19 code. SHA-256 trước và sau audit: `6bfa5bd248bdac740c9a617e5bd60a4b3542af8aff668e93895401ddcad143ef`. Audit không thay đổi notebook, production code, pin hoặc các kết quả đã công bố. Số cell trong báo cáo đếm từ 1; cell ID được nêu khi có.

Nguồn quy định bắt buộc là [đề cuối kỳ](../specs/CSC14120_2026_Final%20Project.md), đặc biệt mục 4.2, 5.2 và 6. [Final plan](../final-plan.md) và [task board](../task-board.md) xác định trách nhiệm nội bộ. P11-T06 phụ thuộc T04 về notebook và T02 về source freeze. Audit local chỉ chuẩn bị nghiệm thu; chưa có lần Run all T4 mới hoặc PDF được nghiệm thu trong công việc này.

### Acceptance Conditions

- Đủ 10 mục, theo thứ tự đề bài. Mỗi phiên bản tối ưu có Bottleneck, Idea, Implementation, Result và Analysis.
- Run all trên Colab GPU mới; không cần thao tác tay ngoài dataset upload nếu cần. Dùng phương pháp/tham số thống nhất giữa phiên bản.
- Bản nộp lưu output; mỗi số trong lời văn có output làm căn cứ. Chạy được về cú pháp chưa chứng minh điều kiện này.
- V0 dùng chrono; GPU dùng CUDA events; một warm-up, ít nhất 5 lượt đo; loại disk I/O; tách stage, kernel, H2D, D2H và end-to-end.
- Bảng so phiên bản cùng GPU và cùng phiên Colab, đủ ba độ phân giải, speedup so V0 và phiên bản trước. Báo cáo lịch sử giữ nhãn phiên gốc.
- Gallery có ảnh được cung cấp bởi môn học, ảnh nhóm và ca thất bại có giải thích. Có trích nguồn tại chỗ dùng, danh mục nguồn và AI disclosure.
- Xuất PDF đọc độc lập, giữ bảng/ảnh/công thức. Link video là đầu ra giai đoạn sau, cần bổ sung trước nộp cuối cùng.

## 2. Section Acceptance Matrix

Trạng thái là đánh giá hiện tại của từng mục, không phải kết quả chạy GPU. `PASS` chỉ xác nhận phần nội dung tĩnh đã kiểm tra; các điều kiện lưu output và PDF vẫn áp dụng toàn notebook.

| Section | Cells | Status | Findings and dependencies |
|---|---|---|---|
| 1. Team Information | 2–5, `team`, `runtime-setup`, `thanh-producer` | FIX REQUIRED | Có đủ tên/MSSV/phân vai V0–V4. Cần ghi đóng góp V5 thực tế; đoạn giới thiệu snapshot còn nói V0–V3/V4. Setup/pin và producer chưa bảo đảm V5. Thành cập nhật sau T02. |
| 2. Introduction | 6, `introduction` | PASS | Có bài toán và tóm tắt chuỗi S1–S6; không thấy placeholder. Thành rà văn phong tiếng Việt trong T04. |
| 3. Chosen Methods | 7–8, `chosen-methods`, `method-settings` | PASS | Có lý do chọn và giới hạn sáu stage; H theo chiều B→A, inverse gather S6. Cell 8 in tham số từ source, gồm seed và canvas limits; cần lưu output từ SHA freeze. |
| 4. V0 Sequential | 9–12 | REQUIRES T4 EXECUTION | Có thiết kế, code nguồn, bảng lịch sử và bảng stage/hot stage cùng phiên. Chưa có output timing hoặc panorama được lưu. Gallery chung thể hiện panorama phiên bản được chọn, chưa có preview V0 riêng ở mục 4. Thành bổ sung hoặc dẫn rõ panorama V0. |
| 5. V1 Basic CUDA | 13–16 | REQUIRES T4 EXECUTION | Có mapping sáu stage và quy tắc timing; dùng báo cáo lịch sử để trình bày parity. Cần kết quả hồi quy T02 và output benchmark mới, không suy correctness từ timing. Panorama V1 riêng chưa được hiển thị ở mục này. |
| 6. Optimized Versions | 17–32 | FIX REQUIRED | V2–V4 có năm phần và bảng đọc report lịch sử. V5 mới có ba đề mục, thiếu bảng so sequential/dual và profiling output; 1,027× chưa khớp bảng APOD. Cell 31–32 thiếu ID. Chưa có output V5 thực. |
| 7. Final Comparison | 33–36 | BLOCKED BY UPSTREAM | Helper hiện chỉ thử V0–V4. T02 chốt source; Thành tích hợp bảng V5, đúng session/provenance và tách phiên bản nhanh nhất theo metric khỏi quyết định chọn production. Sau đó Chương chạy T4. |
| 8. Results Gallery | 37–40 | FIX REQUIRED | Code có ba site + challenge medium và challenge small; không có entry cho cặp mẫu môn học, dù Markdown yêu cầu. Cần cặp mẫu thực và panorama, không dùng hình minh họa đề làm output. Cần xem seam/crop thực khi nghiệm thu. |
| 9. Conclusion | 41, `conclusion` | FIX REQUIRED | Vẫn nói phiên bản tiếp theo sẽ được bổ sung, chưa tổng kết V5. Cần thống nhất quyết định V4 production/V5 case study, giải thích giới hạn kết quả có căn cứ; không thay quyết định bằng aggregate tính lại. |
| 10. References | 42, `references` | PASS | Có nguồn FAST, BRIEF, ratio test, stitching/S6, CUDA, stb và AI disclosure. P10 được dẫn ở cell 31 nhưng chưa gom vào danh mục Evidence. Câu sẽ tổng hợp AI usage cần chốt trước nộp. Audit xác nhận hiện diện/link local, chưa xác minh nội dung mọi URL bên ngoài. |

## 3. Source Revision Audit

Pin ở **cell 3 `runtime-setup`** vẫn là `d42000c4d2847aeb8e1adea66132d35c23a9cb63`. Commit tồn tại trong Git. Source HEAD tại nền audit là `4a20d1a93607851a8fc48bccbbfe206a07c0a787`; không có bằng chứng đây đã là SHA freeze T02.

| Component at pinned revision | Result |
|---|---|
| Pipeline V0–V4; V5 dispatcher | Có `src/v0/v0_pipeline.cpp`, `src/v1` đến `src/v5/v5_pipeline.cu`. |
| P10-T02 API declaration | Có `src/v5/v5_image_branch.h`. |
| P10-T02 API implementation | **Thiếu `src/v5/v5_image_branch.cu`**. Không thể coi V5 production đầy đủ. |
| CLI version 5 | Có nhánh code nhưng phụ thuộc `PANORAMA_V5_IMAGE_API_AVAILABLE`; build.py chỉ bật khi có implementation. Pin này không tạo binary V5 qua đường build thông thường. |
| Benchmark/dataset tools | Có `scripts/build.py`, `scripts/final_notebook.py`, `scripts/run_benchmark.py`, `scripts/prepare_dataset.py`. |
| Automatic version detection | `CANDIDATE_VERSIONS=(0,1,2,3,4)` trong helper **ở pin và nền audit**; `supported_versions()` không thử V5 ngay cả khi binary có V5. |

Lịch sử xác nhận implementation đến ở `1e8212d`, sau đó sửa link collision tại `6efe2f6`, đã có trên nền audit. Đây không còn là việc chờ viết T02 của P10; còn chờ **P11-T02 regression và freeze**.

Hai nguy cơ bổ sung:

1. Cell 3 chỉ checkout pin nếu chưa có `scripts/build.py`. Khi mở trong checkout có sẵn, notebook chạy code local bất kể `SOURCE_REF`; chỉ in SHA, không assert equality. Chạy thành công local chưa chứng minh pin chạy được từ Colab trống.
2. Cell 5 dùng lại `BENCHMARK_DIR` nếu thấy `environment.json`. `load_benchmark()` kiểm version/schema/coverage, chưa đối chiếu `stitch_sha256` của session với binary vừa build hoặc xác minh session/source đang chạy. Metadata được thu không đồng nghĩa metadata đã được kiểm tra.

**Không đổi pin trong audit này.** Tuấn cung cấp SHA freeze cùng log hồi quy; Thành cập nhật pin và kiểm tra checkout/session, đưa V5 vào producer có chủ đích hoặc tải bằng chứng V5 riêng có hash nếu nhóm không đưa vào bảng chung. Không dùng fallback in “refer to APOD” làm bằng chứng V5 đã chạy.

## 4. Dataset and Artifact Dependencies

`scripts/final_notebook.py::fetch_dataset()` tải `dataset.zip` từ Drive đã cấu hình, giải nén an toàn, đối chiếu manifest SHA-256 **`99fc712988075326a351d0bf580405e418bb28d24d56d4cc1b31505c480bdd9d`**, kiểm hash ảnh. Không cần yêu cầu người chạy đổi tên synthetic ZIP thành dataset ZIP. Quyền Drive và download từ Colab trống còn phải kiểm thực tế.

| Artifact | Available basis | Remaining requirement |
|---|---|---|
| P7/P8/P9 reports | Các report đã commit, cell đọc theo đúng header; tách benchmark và acceptance. | Giữ nhãn lịch sử; không gộp session làm bảng speedup cuối. |
| P9 V4 APOD | [Report](p9-t05-v4-apod.md) ghi SHA snapshot/binary/dataset/archive, benchmark luân phiên và phạm vi counter. | Không coi đồ thị dựng từ bảng report là raw profiler trace mới. |
| P10-T01 | Có notebook đã chạy và raw probe CSV, checksum manifest, environment, trace trong `results/Group16_P10_T01_PreS4_Evidence/Group16_P10_T01_PreS4_Evidence/`. | Đo probe khác binary/session với V5; phân biệt mẫu số timing. |
| P10 V5 | Có [verification report](p10-v5-verification.md), [APOD report](p10-t05-v5-apod.md), source và notebook verification không output. | Chưa tìm thấy raw benchmark V4/V5 sequential/dual, NSYS V5, memcheck log gốc hoặc notebook V5 đã chạy trong cây `results/`. Cần bàn giao archive có hash, source SHA/binary hash chính xác. |
| Final session | Có code producer, loader, chart/gallery. | Chưa có output lưu trong 19 code cell; chưa có `Group16_Final.pdf`. |
| Course-provided pair | Gallery chỉ gọi ba site và challenge trong helper. | Thành/Tuấn xác nhận asset mẫu chính thức; chạy và lưu output của nhóm trên asset đó. |

Báo cáo V5 ghi 6 synthetic, 12 status khớp, 10 panorama Max RGB=0 và các memcheck sạch. Đây là **kết quả báo cáo bởi người chạy**, chưa được audit này xác minh độc lập bằng log thô. Không diễn đạt thành chứng minh “đúng đắn/an toàn tuyệt đối” ngoài phạm vi ca thử.
