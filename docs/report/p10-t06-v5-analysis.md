<!-- Authors: Le Ha Thanh Chuong (23120195). External source: repository implementation and experiment reports cited below. -->

# P10-T06 — V5 Interpretation and Measurement Reconciliation

## 1. Scope and Evidence

Chương chốt diễn giải cho notebook, không sửa bảng mean hoặc quyết định trong [APOD của Tuấn](p10-t05-v5-apod.md). Nguồn gồm [baseline probe T01](p10-t01-pres4-baseline.md), [contract](p10-v5-contract.md), [verification T04](p10-v5-verification.md), source V4/V5 và dữ liệu local. `results/` hiện có raw probe T01, không có raw CSV/paired blocks hoặc trace V5 để xác minh lại APOD. Số tính từ bảng là thống kê trên mean đã làm tròn, không phải số đo từng lượt.

## 2. Execution Order Verified Against Source

V4: `H2D(A) → H2D(B) → S1(A,B) → S2(A,B) → S3(A,B) → S4 → S5(V3) → S6(V4) → D2H`. [Driver](../../src/main.cu) phát hai upload trước pipeline. [V4](../../src/v4/v4_pipeline.cu) gọi `run_gpu_stages` trong [V1](../../src/v1/v1_pipeline.cu); mỗi stage xử lý lần lượt hai ảnh. [S2](../../src/v1/s2/v1_detect.cu) copy candidate count về biến host rồi synchronize trước sort; copy vào vùng pageable có thể chặn host ngay trong API copy, theo trace T01. Không mô tả V4 là hoàn tất toàn S1–S3(A) rồi mới tới B.

[V5](../../src/v5/v5_pipeline.cu) có scratch/counts/features/pinned candidate slot riêng mỗi ảnh; khởi tạo BRIEF/weights trước phát nhánh. Dual enqueue cả hai prefix, query `count_ready`, phát suffix cho nhánh sẵn sàng và ghi done. Control chờ doneA/doneB rồi merge counts/status trước downstream. Sequential dùng cùng kernel/owner/API, thêm phụ thuộc doneA trước prefix B. Thời gian query/yield trên host vẫn tồn tại; query không đồng nghĩa host không tốn thời gian.

## 3. Measurement Definitions

| Metric | Basis | Interpretation |
|---|---|---|
| T01 PreS4 mean | CUDA event interval của binary probe, đầu H2D(A) đến sau S3(B), trước S4 | Có overhead event/readiness wait; không đổi nhãn thành production. |
| T01 PreS4 share | Mean của từng `PreS4_i / Total_probe_i` | Không phải ratio of means; không trộn Total production hoặc phiên V5. |
| T01 Host PreS4 / NSYS | Host-observed completion / profiler timeline | Phạm vi và instrumentation khác CUDA event probe. |
| V5 PreS4 | Event common origin đến ready sau join trên control stream | Elapsed GPU interval trước S4, không cộng duration hai nhánh. |
| V5 Host_PreS4 | Host steady-clock trong `v5_run_stages` tới lúc submit sau join | Không chứng minh GPU đã hoàn tất tại lúc host submit. |
| Stage/H2D V5 | Sum CUDA-event duration A+B; S4–S6 đo trên control stream | Có thể lớn hơn elapsed Total do overlap. |
| Total_Kernel_ms | Sum duration từng kernel | Có thể cộng các khoảng overlap; không dùng thay elapsed pipeline. |
| Total_ms | Host elapsed tới khi D2H hoàn tất, đồng bộ; disk I/O ngoài khoảng đo | Bao gồm điều phối/chờ trong interval; không dùng CPU timer suy duration kernel async. |

Tại site2/large, raw T01 cho PreS4 mean 15,287987 ms, Total probe mean 71,734220 ms và mean run-share 21,439554%. Ratio of means là 21,311986%, một thống kê khác. Production mean 69,684386 ms thuộc binary khác. Các giá trị này không phải mẫu số của bảng V4 61,655 ms trong phiên APOD V5.

## 4. Recomputed Historical Metrics

Đặt `r_i = mean_Total_V4_i / mean_Total_V5dual_i`. Chỉ dùng các dòng mean đã làm tròn của cùng bảng APOD, không dùng cột speedup đã làm tròn và không lấy mẫu số từ P9.

| Case | V4 mean ms | V5 dual mean ms | Recomputed V5/V4 |
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

| Statistic | Formula / selected cases | Value |
|---|---|---:|
| Geometric mean V5/V4 | `exp(mean(log(r_i)))`, 9 standard cases | **1.101330×** |
| Medium/large geometric mean | Cùng công thức, 6 ca không gồm small | **1.021965×** |
| Arithmetic mean V5/V4 | `mean(r_i)`, 9 ca | **1.114857×** |
| Ratio of summed means | `sum(T4_i)/sum(T5_i)` | **1.086587×** |
| Primary case | `61.655/59.941` | **1.028595×** |
| Historical geomean V5/V0 | `exp(mean(log(T0_i/T5_i)))`, cùng 9 dòng P10 | **52.846197×** |
| Paired-block median / number of same-direction blocks | Cần raw các khối ghép cặp | **Không dựng lại được** |

Geomean P10 toàn bộ bị ảnh hưởng bởi hai ratio small lớn; phân tích medium/large là kiểm độ nhạy được ghi rõ, không tự loại ca để thay aggregate chính. Chưa có raw CSV nên không đánh giá variance, warm-up, thứ tự đo, clocks hoặc ý nghĩa thống kê. APOD ghi geomean 1,027× và primary 1,039×; không metric nào tính trên bảng mean ở trên xác nhận hai giá trị đó. Nguồn phiên/aggregation của chúng vẫn chưa giải thích được. Bảng gốc không bị sửa; notebook in các giá trị cũ dưới nhãn chưa đối soát và tính lại riêng.

Challenge small có `112.074/113.776 = 0.985041×`, giữ ngoài aggregate chuẩn; medium/large trả NumericalFailure theo verification, không có speedup hợp lệ. Status parity không bảo đảm panorama small có chất lượng tốt.

V5 pre-S4 quoted trong APOD: sequential 15,310 ms, dual 12,680 ms → ratio **1,207413×**, latency reduction **17,178315%**, chênh **2,630 ms**. Đây là phép tính từ hai số được trích, không phải kiểm độc lập sidecar V5. Khoảng timing không cho phép khẳng định Total giảm cùng 2,630 ms, hoặc so nó trực tiếp với probe T01 của phiên/binary khác. Khả năng concurrent kernels/async copy của thiết bị không tự chứng minh overlap thực; báo cáo NSYS chưa có trace V5 local để audit lại.

## 5. Notebook Result Provenance

Cell `v5-p10-results` kiểm đúng tập chín cấu hình và dùng giá trị ms để tính; hiển thị bảng tính lại, probe T01, các giá trị V5 quoted và độ giảm latency. `thanh-v5-tables` và mục 7 dùng benchmark mới do binary chạy cùng phiên; không tái sử dụng mean P9/P10 lịch sử để tạo speedup mới. `fn.best_version()` chọn geomean so V0 trên chín ca; đó là định nghĩa nhanh nhất theo bảng đo, tách khỏi quyết định production V4.

Raw T01 có ở local nên đã đối chiếu lại mean/share. Notebook đọc summary baseline đã commit vì không buộc người chạy tải thêm ZIP probe; output mang nhãn report summary. Source/benchmark freeze scope và kiểm Run all/PDF cuối thuộc P11-T06, không lấy kết quả CPU này thay T4.

## 6. Final Interpretation and Adoption

Giữ quyết định đã công bố: **V4 production baseline, V5 concurrency case study**. Bảng mean cho phép nói chín ca chuẩn đều nhanh hơn theo số đã công bố, nhưng không chứng minh mức cải thiện ổn định hoặc kiểm chứng tiêu chí median các khối đo luân phiên. Geomean trên chín dòng vượt 1,05× còn mean-ratio ca chính thấp hơn; cả hai đều không phải median paired speedup. Vì thiếu raw, không khẳng định tiêu chí adoption định trước đã đạt hay thất bại. Sai khác báo cáo được công khai thay vì thay bảng hoặc chế metric để hợp thức hóa quyết định.

V0 → V1 làm bottleneck chuyển từ công việc so khớp/pixel sang RANSAC; V2/V3 giảm S5, V4 gộp renderer S6 với lợi ích nhỏ đã đo. V5 tối ưu execution trước S4, không thay downstream hoặc mô hình hình học. Report NSYS gợi ý overlap copy/compute và contention; số SM/copy engines chỉ mô tả khả năng thiết bị, chưa đủ chứng minh hiệu quả thực tế khi thiếu trace. Phân tích giữ các nhận xét đó theo nguồn report, không nâng thành kết luận nhân quả đã được audit độc lập.

Kết luận notebook đã bỏ placeholder V5, giữ giới hạn chất lượng panorama và phạm vi parity. Dữ liệu lịch sử đã đối soát về số học và nguồn đo; raw provenance còn thiếu được ghi như giới hạn bằng chứng, không là metric mới để chứng nhận V5. Hạ tầng chuẩn bị có thể review/merge, còn release acceptance phải có T4/output/PDF thật.
