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

## 5. Numerical Discrepancy Register

Không sửa âm thầm APOD hoặc notebook. Bảng dưới giữ cả nhận định gốc và kết quả kiểm tra. Dòng báo cáo là tại nền `4a20d1a`; cell notebook đếm từ 1.

| ID / severity | Original claim and location | Audit result / evidence / formula | Resolution and owner |
|---|---|---|---|
| N01 / BLOCKER | APOD V5 dòng 78 và notebook cell 31: trung bình nhân V5/V4 **1,027×**. | Chín dòng chuẩn của bảng APOD mục 4 cho **1,101330×**, tính `exp(mean(log(T4_i/T5_i)))`. Không dùng challenge. Đây là tính lại từ mean đã làm tròn, **chưa có raw CSV V5**. | Sai khác chưa được giải thích. Tuấn (người công bố APOD thay Đế) bàn giao raw và xác nhận metric/filter; Thành sửa lời văn/bảng output sau đối chiếu; Chương kiểm lại. |
| N02 / MAJOR | APOD dòng 78: site2/large **1,039×**. | Dòng 54 ghi 61,655 / 59,941 ms → **1,028594785×**, làm tròn **1,029×**, đúng cột speedup bảng nhưng khác kết luận. | Chưa giải thích bằng raw/session. Không ghép với ratio 1,039× của phiên khác. Tuấn xác nhận nguồn, Thành đồng bộ cell phân tích. |
| N03 / MAJOR | APOD dòng 13: pre-S4 15,288 ms chiếm 21,44% “Total V4”; dòng 61: “V4 Production Pre-S4”. Cell 31 chưa nói rõ probe. | Raw T01 xác nhận **probe** mean 15,287987 ms; `mean(PreS4_run/Total_probe_run)` = **21,439554%**. Production là binary khác. | Cơ sở được xác minh; nhãn production và mô tả session cần sửa. Giữ con số khi gắn đúng probe. Thành sửa notebook, Tuấn sửa APOD. |
| N04 / MAJOR | APOD dòng 77: rút ngắn pre-S4 “~20%”. | Từ hai số công bố seq 15,310 và dual 12,680: speedup **1,207413×**, nhưng giảm thời gian **17,178315%**, `(1−12.680/15.310)×100`. | Phải phân biệt tăng tốc và giảm latency. Raw sequential/dual còn thiếu, chưa xác nhận số đo hay paired statistic. |
| N05 / MAJOR | APOD dòng 73: overhead query 0,15–0,25 ms; mục 5 và cell 31 giải thích contention/overlap. | Chưa có NSYS V5/raw range trong evidence local để xác định cửa sổ, lượt đo và latency. `asyncEngineCount=3` là khả năng thiết bị, không tự chứng minh overlap hoặc nguyên nhân chậm. | Giữ là kết luận của report, chưa independently verified. Tuấn cung cấp trace/range/export; tránh giải thích nhân quả chỉ từ số SM. |
| N06 / MAJOR | Cell 31/APOD: “đúng đắn và an toàn bộ nhớ tuyệt đối”. | Report chỉ ghi kết quả trên fixture, 12 cấu hình và các target memcheck đã chạy. Không phải bảo đảm trên mọi input/lịch chạy. Log thô chưa có trong checkout. | Thu hẹp thành “đạt các ca kiểm thử đã báo cáo”, ghi SHA, tolerance, target và log. |
| N07 / MAJOR | APOD dòng 9: V4 xử lý toàn bộ S1–S3(A), rồi mới B; memory đã “khai thác triệt để”. | `v4_run_stages()` dùng `run_gpu_stages()` trong V1: stage S1 xử lý A/B, tiếp S2 A/B, rồi S3 A/B. Một stream nhưng thứ tự không phải branch-serial như V5 sequential. Không có phép đo chứng minh mọi hướng memory đã hết. | Tuấn sửa mô tả, giữ phân biệt V4 production với V5 sequential đối chứng. |

## 6. V5 Benchmark Reconciliation

Dữ liệu dùng tính là **bảng mean đã công bố**, [APOD V5 mục 4](p10-t05-v5-apod.md#4-benchmark-results). Không phải CSV từng lượt. Không suy raw variance, median paired speedup, confidence interval hoặc sự công bằng giữa session từ bảng này.

| Standard configuration | V4 mean Total (ms) | V5 dual mean Total (ms) | T4/T5 recomputed |
|---|---:|---:|---:|
| site1/small | 51.758 | 32.246 | 1.605098× |
| site1/medium | 31.042 | 30.085 | 1.031810× |
| site1/large | 105.309 | 102.925 | 1.023162× |
| site2/small | 21.214 | 20.686 | 1.025525× |
| site2/medium | 27.701 | 27.090 | 1.022554× |
| site2/large | 61.655 | 59.941 | 1.028595× |
| site3/small | 63.224 | 49.738 | 1.271141× |
| site3/medium | 55.968 | 55.433 | 1.009651× |
| site3/large | 100.810 | 99.205 | 1.016179× |

Đặt `r_i=T4_i/T5_i`, với mỗi T là mean end-to-end của một cấu hình. Các cách tổng hợp không thay thế nhau:

| Metric | Formula | Recomputed value |
|---|---|---:|
| Arithmetic mean of configuration speedups | `sum(r_i)/9` | **1.114857×** |
| Geometric mean of configuration speedups | `exp(sum(log(r_i))/9)` | **1.101330×** |
| Ratio of aggregate mean timings | `sum(T4_i)/sum(T5_i)` | **1.086587×** |
| Median of nine configuration speedups | `median(r_i)` | **1.025525×** |
| Median paired-run speedup | `median(T4_ij/T5_ij)` với cặp đo được định nghĩa trước | **Chưa tính được**: không có dữ liệu paired/raw V5. |

Không có metric nào ở trên xác nhận trung bình nhân 1,027×. Hai ca site1/small và site3/small có ratio lớn; không tự loại chúng hoặc chọn tập con để làm khớp kết luận. Cần raw để kiểm session, warm-up, số run, CPU/GPU, binary, thứ tự đo, clock/variance và cả V5 sequential. Mean từng case không chứng minh ý nghĩa thống kê.

Challenge small là 112,074 / 113,776 = **0,985040×**: có chậm hơn V4 theo bảng; giữ riêng, không đưa vào aggregate chín cấu hình chuẩn. Challenge medium/large NumericalFailure không có timing/speedup hợp lệ. Status parity không đồng nghĩa ảnh challenge small có chất lượng tốt.

**Phạm vi metric:** bảng trên là `Total_ms`, có D2H/host orchestration theo contract, loại disk I/O. Không thay mẫu số bằng `Total_Kernel_ms`, sum stage, hoặc pre-S4. Với dual stream, sum khoảng stage/H2D của A+B có thể lớn hơn elapsed pipeline do overlap; parser hiện có xử lý riêng V5. Raw sidecar cần được kiểm song song CSV chính.

## 7. Pre-S4 Measurement Interpretation

Đọc lại [baseline T01](p10-t01-pres4-baseline.md), raw `raw_timing.csv` và manifest checksum trong evidence T01. Audit kiểm đủ **84/84 checksum khớp**, không file thiếu; dataset manifest hash khớp giá trị cấu hình của notebook. Nguồn đo T01 là `c4566e3f656493bc48bb8edddaa5e8ac95d27831`. Hai binary production/probe có hash khác nhau như report gốc.

| Probe case | Runs | Pre-S4 mean (ms) | Total probe mean (ms) | Mean of per-run shares | Ratio of means |
|---|---:|---:|---:|---:|---:|
| site1/large | 5 | 13.085715 | 106.892569 | 12.232893% | 12.241932% |
| site2/large | 5 | 15.287987 | 71.734220 | **21.439554%** | **21.311986%** |
| site3/large | 5 | 11.234458 | 100.230507 | 11.204155% | 11.208621% |

Tỷ trọng công bố 21,44% dùng `mean(p_i/t_i)` trên **cùng run probe**; không phải `mean(p_i)/mean(t_i)`. Càng không phải 15,288 chia cho production Total 69,684 ms, hoặc V4 61,655 ms của bảng benchmark V5. Những phép chia trộn binary/session không phải phép đo cùng cửa sổ.

Câu phù hợp để Thành thay trong cell 31 sau khi có output tái hiện:

> Trong phiên đo probe V4 của P10-T01, site2/large có pre-S4 trung bình 15,288 ms. Trung bình tỷ lệ pre-S4/Total của từng lượt probe là 21,44%. Các số này dùng để chọn ca thử và đánh giá cơ hội overlap; không phải timing đo trực tiếp trên binary production của phiên benchmark V5.

V5 sequential/dual 15,310→12,680 ms hiện chỉ có trong report. Chưa đủ chứng cứ để kết luận phần chênh chính xác do concurrency thay vì session/host scheduling, hoặc khẳng định tiết kiệm pre-S4 bằng tiết kiệm Total. Cần cùng phiên ablation, cùng kernels/scratch/pinned buffers, thêm trace và per-run sidecar.

## 8. V4/V5 Adoption Consistency

**Giữ quyết định nhóm đã công bố: V4 là production baseline; V5 là concurrency case study.** Đây là quyết định lựa chọn sản phẩm, tách khỏi bảng đo. Cell 31 có quyết định đúng nhưng lập luận số 1,027× chưa đáng tin; cell 41 chưa cập nhật V5.

Từ bảng mean công bố, geomean 1,10133× lớn hơn ngưỡng 1,05× được report nhắc đến, trong khi ca chính site2/large 1,02859× thấp hơn ngưỡng đó. Vì vậy câu “geomean không vượt 1,05×” không đứng vững theo bảng. Phải ghi rõ tiêu chí áp dụng cho **ca chính đã chọn trước** hay toàn bộ ma trận, kiểm raw và độ ổn định, rồi người phụ trách xác nhận lại lý do giữ V4. Audit không tạo tiêu chí mới sau khi xem kết quả.

`fn.best_version()` chọn theo geomean speedup so V0 trên chín cấu hình. Hiện chỉ có V0–V4 vì candidate list. Khi thêm V5, nếu V5 đứng đầu thì chart/gallery chọn V5 là hợp lệ dưới nhãn “nhanh nhất theo metric”, nhưng không được tự gọi đó là production. Cần nêu rõ lựa chọn này và giữ gallery production V4 nếu dùng để demo bản nộp.
