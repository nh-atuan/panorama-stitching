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
