<!-- Authors: Le Ha Thanh Chuong (23120195). External source: repository source and experiment reports linked below. -->

# P10-T06 — Phân tích V5 theo báo cáo chính thức ngày 23/11

## Phạm vi và nguồn

Bản cập nhật này thay phân tích trên báo cáo P10 cũ trước PR #57–58. [Notebook cuối kỳ](../../Group16_Final.ipynb), cell `v5-p10-results`, đọc các bảng trong [P10-T05](p10-t05-v5-apod.md) qua `scripts/v5_report.py`. Không sửa bảng của Đế hoặc sinh số đo GPU mới. Báo cáo P10-T05 định danh phiên `2026-11-23T06:47:04Z`, source `26c8f241e056a7cf5e0c5bb0d85f036d9eafd9e1`, Tesla T4, driver 580.82.07, nvcc 13.0.88 và NSYS 2025.3.1.0.

Archive được báo cáo định danh là `results/Group16_P10_T05_Evidence.zip`, SHA-256 `e80a7e9ed2932139a13271264a631c9ba3e2171a36b6e6cf20528e614f41ade7`. Archive chưa có trong workspace khi rà soát. Vì vậy mọi phép tính dưới đây lấy từ **bảng báo cáo đã commit, mean làm tròn**, không được gọi là xác minh độc lập CSV, sidecar hoặc SQLite gốc. Kết quả nghiệm thu hình học/RGB/memcheck thuộc [P10-T04](p10-v5-verification.md), tách khỏi benchmark.

## Thứ tự thực thi và ý nghĩa timing

V4 qua CLI: `H2D(A) → H2D(B) → S1(A,B) → S2(A,B) → S3(A,B) → S4 → S5(V3) → S6(V4) → D2H`. [main.cu](../../src/main.cu) phát hai upload trước [v4_run_stages](../../src/v4/v4_pipeline.cu), hàm này gọi [run_gpu_stages](../../src/v1/v1_pipeline.cu). Mỗi stage xử lý A rồi B; V4 không hoàn tất cả S1–S3(A) trước khi bắt đầu B. S2 chép candidate count về host và đồng bộ trước top-K; vùng pageable có thể khiến lời gọi copy chặn host.

[V5](../../src/v5/v5_pipeline.cu) dùng scratch/counts/features/pinned slot riêng. Dual phát prefix hai ảnh, query `count_ready`, phát suffix nhánh sẵn sàng; control chờ `doneA/doneB`, merge rồi chạy S4–S6/D2H. Sequential dùng cùng API/kernel/workspace, thêm phụ thuộc B sau A. V4 production và V5 sequential khác cách nhóm stage/workspace, nên đối chứng dual/sequential giúp phân biệt tác động lịch chạy.

| Metric | Phạm vi và giới hạn |
|---|---|
| T01 pre-S4 share | Mean từng `PreS4_i / Total_probe_i` của binary instrumented, không phải tỷ trọng production. Site2/large là 21,439554%; production Total thuộc binary khác. |
| V5 PreS4_ms | CUDA event từ common origin đến ready sau join/merge, không cộng duration hai nhánh. |
| Host_PreS4 / CountWait | Host-observed intervals; không dùng thay duration kernel hoặc cộng với GPU elapsed. |
| Stage/H2D và Total_Kernel_ms V5 | Sum các duration có thể overlap, không phải phân chia độc lập của elapsed Total. |
| Total_ms | Host elapsed đã đồng bộ tới D2H xong, gồm điều phối; loại trừ disk I/O. |
| NSYS đến S4 / overlap | Lượt có profiler riêng; không thay benchmark không profiler hoặc CUDA-event sidecar. |
| NSYS remaining allocations | Bộ nhớ cấp phát còn tồn tại ở cuối trace; không phải VRAM vật lý còn trống và không thay Compute Sanitizer. |

Nguồn baseline và denominator: [P10-T01](p10-t01-pres4-baseline.md); semantics đã chốt trước đo: [contract](p10-v5-contract.md).

## Tính lại từ các bảng hiện hành

Với chín ca chuẩn, `r_i = mean(T4_i) / mean(T5dual_i)`. Trung bình nhân là `exp(mean(log(r_i)))`. Không dùng cột speedup đã làm tròn hoặc ghép mean từ P9. Challenge không nằm trong tập chín ca.

| Thống kê | Tính lại từ bảng |
|---|---:|
| GM V5/V0 | 49.876178× |
| GM V5/V4 | 1.068633× |
| GM V5 dual/sequential | 1.036413× |
| GM V5/V4, tập medium/large (kiểm độ nhạy) | 1.032431× |
| Trung bình cộng V5/V4 | 1.080774× |
| Tỉ số tổng các mean V4/V5 | 1.056082× |
| V5/V4 tại site2/large | 1.056834× |
| GM Pre-S4 sequential/dual | 1.256430× |
| Median năm tỉ số khối ghép cặp | 1.066629× |
| Số khối có lợi | 3/5 |

Pre-S4 site2/large: `13.700 / 10.971 = 1.248747×`, giảm latency khoảng 19,920%. GM Pre-S4 suy từ mean làm tròn là 1,256430×; báo cáo ghi 1,2565×. Chưa có sidecar gốc để phân biệt tác động làm tròn với sai khác tổng hợp. Không thay số tính lại bằng số báo cáo chỉ để trùng chữ số cuối.

Bảng chính có 8/9 ca chuẩn nhanh hơn V4; site3/small là ca chậm hơn. Báo cáo có phép đo lại cho ca đó. Không thể quy nguyên nhân biến thiên cho clocks hoặc SM contention chỉ từ các bảng tóm tắt. Challenge/small có output nhưng được giữ ngoài aggregate; medium/large có NumericalFailure theo T04, không có speedup hợp lệ. Status/RGB parity không bảo đảm chất lượng căn chỉnh.

NSYS có chín cấu hình, ba mode trên ba ca large. V5 dual có overlap 16,6–24,5%, còn V4 và V5 sequential được báo 0%. Chênh peak VRAM dual trừ V4 là 64,30 MiB ở cả ba ca. Đây là bằng chứng concurrency được báo cáo; không suy occupancy hoặc saturation từ overlap riêng lẻ.

## Quyết định và độ ổn định

Ngưỡng chốt trước đo là median ít nhất 1,05× và ít nhất 4/5 khối có lợi tại ca chính. Tính lại từ năm cặp mean cho median 1,066629× (đạt), nhưng chỉ 3/5 khối có lợi (không đạt). Đây là median của **năm tỉ số từng khối**, không phải GM của chín ca hoặc tỉ số tổng các mean.

Giữ **V4 production baseline, V5 concurrency case study** theo quyết định nhóm. Hai stream giảm Pre-S4, nhưng lợi ích end-to-end nhỏ hơn và chưa nhất quán qua các khối. Notebook trình bày kết quả thuận lợi lẫn giới hạn; không gọi V5 chậm toàn diện hoặc phủ nhận overlap.

## Kiểm chứng cục bộ và phần còn lại

Parser kiểm header, row width, đủ chín ca chuẩn, năm khối luân phiên, chín cấu hình NSYS, số hữu hạn/đơn vị và provenance. Notebook, audit và test dùng chung parser; thiếu dữ liệu phải báo lỗi có tên bảng/field, không fallback về số cũ. Integration test thực thi cell thật với report thật và đối chiếu GM bằng Decimal độc lập.

Mục 6/7/9 đã đồng bộ cách diễn giải. P11-T06 còn chạy notebook trên T4 mới với source được định danh, lưu output, đối chiếu gallery/số liệu và kiểm từng trang PDF. Local CPU/PDF smoke không thay nghiệm thu GPU hoặc bản PDF cuối.
