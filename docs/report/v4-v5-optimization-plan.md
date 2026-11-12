# Kế hoạch thực nghiệm V4–V5 cho Panorama Stitching

Nhóm 16 · CSC14120 · 12/11/2026 · Mốc rà soát `main` tại `8a56c62`.

## Material Passport

| Trường | Giá trị |
|---|---|
| Workflow | Academic Research Suite · Experiment Agent · Plan |
| Phiên bản tài liệu | `code_plan_v1` |
| Trạng thái thực nghiệm | `UNVERIFIED`. Các số liệu lịch sử được đối chiếu với báo cáo của nhóm. V4 và V5 chưa được triển khai hoặc đo trong lần rà soát này. |
| Căn cứ | Đề xuất của Chương về reduction, bộ nhớ và streams, mã nguồn production, đề bài CSC14120, task board, số đo P7 và tài liệu chính thức của NVIDIA. Tên các chủ đề bài học theo đề xuất của Chương. Thư mục slide liên kết trong repo chưa đọc được khi rà soát. |

## 1. Phạm vi và quyết định thiết kế

P8-T01 đã giao Tuấn tối ưu S5 V3, với mục tiêu cụ thể ở `compute_hypotheses`, giữ phương pháp và tham số của V0, kiểm thử sáu cặp synthetic và build `sm_75`. Phương án kernel cụ thể do Tuấn lựa chọn. Tại mốc rà soát, tài liệu công khai của repo xác nhận phạm vi và tiêu chí P8 nhưng chưa có mã S5 V3 để đối chiếu triển khai. Kế hoạch này bắt đầu từ V4 và dùng bản V3 đã nghiệm thu làm đối chứng. V4/V5 chỉ mở nếu còn đủ thời gian cho bài nộp 03/12 và có điểm nghẽn được đo trên bản liền trước. [Task board P8](../task-board.md) · [Kế hoạch cuối kỳ](../final-plan.md) · [Đề bài, mục 3–4](../specs/CSC14120_2026_Final%20Project.md)

| Ý tưởng trong đề xuất | Kết quả đối chiếu và hướng xử lý |
|---|---|
| V3 · `__launch_bounds__`, persistent kernel, warp shuffle | Chuyển làm thông tin tham khảo cho Tuấn. Launch bounds tác động đến giới hạn thanh ghi và có thể kéo theo spill hoặc tăng số lệnh. Occupancy 25% và 100 thanh ghi/thread là số đo V2. 126 lần launch trong trace bao gồm warm-up và một lượt đo. Một work queue phân phối hypothesis vẫn cần cách công bố kết quả theo thứ tự ID để giữ logic dừng sớm. Reduction cho warp 32 lane có thể dùng năm bước shuffle theo cây, cộng với phép tính, mask và chi phí xử lý ngoài warp. Các mục tiêu như occupancy 75–100% hoặc S5 nhanh gấp đôi cần số đo mới. [Profiling P7](p7-t03-v2-apod.md) · [S5 V2 và commit prefix](../../src/v2/s5/v2_homography.cu) · [NVIDIA Programming Guide, mục 10.22 và 10.38](https://docs.nvidia.com/cuda/archive/13.0.3/cuda-c-programming-guide/index.html) |
| V4 · Gộp các lượt dựng canvas | Chọn làm một ý tưởng chính để thử. Mỗi pixel output được ghi một lần ở mức mã nguồn. Lưu lượng DRAM thực tế còn phụ thuộc vùng A/B hợp lệ, cache, đọc nguồn và kiểu giao dịch bộ nhớ. Đo riêng DRAM đọc/ghi và thời gian S6 để định lượng lợi ích. [S6 V1](../../src/v1/v1_warp_blend.cu) · [NVIDIA Best Practices, mục 10.2.1](https://docs.nvidia.com/cuda/archive/13.0.2/cuda-c-best-practices-guide/index.html#coalesced-access-to-global-memory) |
| V4 · Texture hoặc read-only cache cho ảnh B | Để thành thí nghiệm riêng nếu gather vẫn chi phối sau fusion. Texture lọc tuyến tính cần kiểu trả về số thực và dùng trọng số với 8 bit phần lẻ cùng quy ước half-texel. Ưu tiên khảo sát point fetch giữ bilinear tự tính, đồng thời đo chi phí layout/pitch, packing và tạo resource với RGB 3 byte/pixel. Những lợi ích về cache hoặc thời gian nội suy cần kiểm chứng trên T4. [NVIDIA Programming Guide, mục 6.2.14 và 19.2](https://docs.nvidia.com/cuda/archive/13.0.3/cuda-c-programming-guide/index.html#linear-filtering) · [Thiết kế S6, mục 6.3](../stages/s6-warp-blend.md) |
| V5 · Hai stream và pinned memory | Chọn **hai stream cho hai nhánh ảnh A/B** làm một ý tưởng chính. Driver hiện dùng `PinnedBuffer` với `cudaMallocHost` cho cả hai ảnh vào và panorama, nên pinned memory là điều kiện chung của hai bản đo. Mức overlap phụ thuộc khả năng copy/compute đồng thời, phụ thuộc dữ liệu và tải trên T4. [Driver hiện tại](../../src/main.cu) · [PinnedBuffer](../../src/common/cuda_utils.cuh) · [NVIDIA Best Practices, mục 10.1](https://docs.nvidia.com/cuda/archive/13.0.2/cuda-c-best-practices-guide/index.html#asynchronous-and-overlapping-transfers-with-computation) |
| V5 · S4 tiling | Giữ làm ứng viên cho một vòng tối ưu độc lập nếu có số đo phù hợp. S4 hiện đã dùng XOR và `__popc`, một block cho một descriptor A. Shared-memory tiling có ý nghĩa khi nhiều A trong cùng block cùng dùng lại tile B. Tỷ trọng S4 trung bình trong V2 chỉ 0,36–1,25% tùy độ phân giải. Nếu thử sau này, đo S4 và end-to-end, đối chiếu hai láng giềng, tie-break và thứ tự match. [Kernel S4](../../src/v1/s4/v1_match.cu) · [Phân bố thời gian V2](p7-t03-v2-apod.md) · [NVIDIA Best Practices, mục 10.2.3](https://docs.nvidia.com/cuda/archive/13.0.2/cuda-c-best-practices-guide/index.html#shared-memory) |

## 2. V4 — Dựng canvas S6 trong một lượt

**Câu hỏi thực nghiệm.** Với cùng ảnh, homography và kích thước canvas, gộp xóa nền, chép A và gather B có làm giảm thời gian S6 và thời gian toàn pipeline trên T4? Giả thuyết là giảm số lượt ghi và bỏ đọc lại pixel A từ canvas tại vùng chồng lấp. Số liệu V2 ở `site2/large` cho thấy S6 mất 28,742 ms trên tổng 81,156 ms, gần S5 là 30,597 ms. Nếu chỉ S6 nhanh gấp đôi và mọi chi phí khác giữ nguyên, toàn pipeline của cấu hình V2 này chỉ nhanh khoảng **1,22×**. Đây là phép tính minh họa từ V2. Quyết định mở V4 dựa trên số đo V3. [Benchmark P7-T03](p7-t03-v2-apod.md)

### Triển khai và đối chứng

1. Đo V3 sau nghiệm thu, ưu tiên `site2/large`, `site3/large` và `site1/small`. Trên trace, định lượng khoảng thời gian xóa, copy A và gather. Dùng bộ đếm Nsight Compute cho kernel và timeline Nsight Systems cho cả các thao tác bộ nhớ. Chọn `site2/large` làm ca chính trước khi xem kết quả V4.
2. Giữ setup S6 hiện hành, gồm nghịch đảo H, kiểm tra suy biến/horizon, tính canvas và offset, đọc metadata và cấp phát. Thay chuỗi `cudaMemsetAsync → copy_a_kernel → gather_b_kernel` bằng một kernel 2D, khởi đầu với block 32×8 như renderer hiện tại. Mỗi thread trong canvas xác định vùng A theo hình học, chiếu ngược về B, áp dụng cùng quy tắc snap/clamp, nội suy bilinear và chọn một trong bốn màu đầu ra là A, B, trung bình 50/50 hoặc nền đen. Đọc A trực tiếp theo stride và ghi RGB đầu ra đúng một lần. Giữ độ chính xác số học, thứ tự tính và cách làm tròn.
3. Dùng cùng H trong test riêng S6 để tách ảnh hưởng renderer khỏi S5. So baseline V3 với V4 trên cùng dữ liệu, grid và quy ước stride. Khi tích hợp, gọi lại S1–S5 của V3, giữ đường D2H và đo cả thời gian setup S6. Duy trì cơ chế cũ trong đường CLI V3 để đối chứng.
4. Đo `S6_ms`, `Total_ms`, số kernel và memory operations, DRAM bytes đọc/ghi nếu profiler hỗ trợ, peak VRAM và D2H. Tách byte truy cập ước tính ở mức mã nguồn khỏi byte DRAM được profiler ghi nhận. Trường hợp fusion tăng branch divergence hoặc áp lực thanh ghi, ghi thêm occupancy và thời gian kernel để giải thích. [Nguồn renderer](../../src/v1/v1_warp_blend.cu) · [Thiết kế S6](../stages/s6-warp-blend.md) · [Hướng dẫn Nsight Compute](https://docs.nvidia.com/nsight-compute/ProfilingGuide/)

**Kiểm chứng riêng.** So canvas/offset/stride chính xác, Max RGB ≤ 1, kiểm tra bốn vùng A/B/overlap/nền, pixel nguồn đen hợp lệ, hàng/cột cuối, tịnh tiến phân số, phối cảnh và canvas lớn hơn ảnh A. Chạy lại các ca lỗi H, canvas quá giới hạn và cấp phát. Đề xuất Chương phụ trách prototype S6, test so cùng H và tổng hợp bằng chứng, sau khi nhóm quyết định mở V4. [Bộ test S6 hiện hành](../../tests/gpu/test_gpu_s6_warp_blend.cu) · [Quy ước S6](../stages/s6-warp-blend.md)

## 3. V5 — Điều phối hai nhánh ảnh bằng CUDA streams

**Câu hỏi thực nghiệm.** Khi giữ cùng pinned buffers và cùng kernel, chạy H2D và S1–S3 của A/B trên hai stream có rút ngắn thời gian từ bắt đầu upload đến lúc S4 sẵn sàng và giảm `Total_ms`? Giả thuyết là một phần H2D và tính toán của hai nhánh có thể chồng lấn. S4 chờ cả hai bộ descriptor. D2H panorama vẫn phụ thuộc S6 trong cùng cặp ảnh. [NVIDIA Best Practices, mục 10.1](https://docs.nvidia.com/cuda/archive/13.0.2/cuda-c-best-practices-guide/index.html#asynchronous-and-overlapping-transfers-with-computation) · [NVIDIA Programming Guide, mục Streams](https://docs.nvidia.com/cuda/archive/13.0.3/cuda-c-programming-guide/index.html)

```text
control: reset + start
            |                              |
stream A: H2D(A) -> S1(A) -> S2(A) -> S3(A) -> doneA
stream B: H2D(B) -> S1(B) -> S2(B) -> S3(B) -> doneB
            control waits for doneA and doneB
control: merge status/counts -> S4 -> S5 -> S6 -> D2H -> stop
```

1. **Xác định dư địa trên bản đã nghiệm thu.** Dùng Nsight Systems đo đoạn từ upload đầu tiên đến S4, các điểm đồng bộ của S2 và tỷ trọng H2D/S1–S3. Ghi `asyncEngineCount`, `concurrentKernels`, mức sử dụng bộ nhớ và khả năng cấp thêm scratch. Chọn trước ca large có đoạn trước S4 chiếm tỷ trọng lớn nhất trong baseline làm ca chính. Nếu V4 đạt và được giữ thì dùng V4 làm baseline. Nếu V4 bị loại và nhóm vẫn mở vòng này, dùng V3 và đặt số phiên bản theo chuỗi thực tế.
2. **Tách trạng thái theo ảnh.** Trích entry point xử lý một ảnh cho S1–S3 từ mã đã có. Mỗi nhánh có vùng `d_scratch`, counters/status và buffer Host chứa metadata S2 riêng. Dùng lại ảnh, grayscale, keypoint và descriptor A/B đã tách sẵn. Khởi tạo bảng BRIEF trước khi tách stream và cấp phát ngoài vòng đo. Sau khi hai nhánh kết thúc, hợp nhất counts/status theo thứ tự lỗi hiện hành rồi mới chạy S4. Kiểm tra lại quyền sở hữu tài nguyên khi một nhánh lỗi hoặc allocation thất bại. [Workspace và scratch dùng chung hiện tại](../../src/v1/v1_pipeline.cu) · [S3 và khởi tạo BRIEF](../../src/v1/s3/v1_describe.cu)
3. **Giữ thứ tự trong mỗi nhánh và bỏ chờ tuần tự ở Host giữa A/B.** S2 hiện đọc candidate count về Host rồi đồng bộ stream trước top-N. Tách phần enqueue tìm ứng viên/copy count và phần hoàn tất top-N. Enqueue phần đầu cho cả A/B trước khi chờ count, dùng event theo từng nhánh và cho phép nhánh sẵn sàng đi tiếp. Sau khi hoàn tất S3, ghi `doneA` và `doneB`, rồi dùng `cudaStreamWaitEvent` để nối về stream điều phối. Đường reset, đọc kết quả và giải phóng chỉ đi tiếp khi các công việc liên quan đã hoàn tất. [S2 hiện tại](../../src/v1/s2/v1_detect.cu) · [NVIDIA Programming Guide, mục Streams](https://docs.nvidia.com/cuda/archive/13.0.3/cuda-c-programming-guide/index.html)
4. **Dùng hai đối chứng.** Giữ bản production trước V5 để đo lợi ích người dùng nhận được. Thêm chế độ chạy nối tiếp của prototype dùng cùng workspace tách riêng, pinned buffers, entry point một ảnh và kernel như V5 để đo riêng tác động của cách lập lịch. Hai chế độ prototype chỉ khác việc xếp hai nhánh nối tiếp hay cho phép chồng lấn. Giữ S4–S6, cấu hình và phép đo output giống bản trước.
5. **Kiểm tra cách ghi thời gian.** Tái dùng CUDA events theo từng nhánh và theo lần chạy, ghi riêng H2D và S1–S3 của A/B. Đo thời gian đến điểm nối từ một mốc chung và thu thời gian end-to-end sau khi D2H hoàn tất theo quy ước driver. Tổng thời lượng từng kernel có thể đếm trùng khoảng chồng lấn. Giữ rõ nghĩa của `Total_Kernel_ms` là tổng thời lượng từng kernel, kèm thời gian đến điểm nối và CSV riêng của từng nhánh. Nếu dùng nhiều luồng Host, tách recorder theo luồng vì recorder hiện là `thread_local`. Lấy bằng chứng overlap từ timeline Nsight Systems. Dùng Nsight Compute cho bộ đếm kernel vì replay thường tuần tự hóa launch. [Recorder hiện tại](../../src/common/kernel_timing.cuh) · [Nsight Systems User Guide](https://docs.nvidia.com/nsight-systems/UserGuide/) · [Nsight Compute Profiling Guide](https://docs.nvidia.com/nsight-compute/ProfilingGuide/)

**Kiểm chứng riêng.** So keypoint theo thứ tự, descriptor từng bit và số lượng A/B sau S3. So danh sách match và trạng thái trước khi so H, canvas và ảnh. Chạy ảnh hai bên khác kích thước, ca zero-feature, lỗi từng nhánh và các lần chạy lặp trên cùng workspace. Dùng memcheck và xem xét việc mỗi nhánh chỉ ghi vào vùng được cấp riêng. Đo peak VRAM vì hai vùng scratch có thể làm tăng chi phí bộ nhớ.

## 4. Quy trình đo và điều kiện giữ phiên bản

| Hạng mục | Quy trình đề xuất |
|---|---|
| Môi trường và đối chứng | Cùng phiên Colab Tesla T4, `sm_75 -O2 --fmad=false`, cùng bộ 24 ảnh và hash, cùng `Config` và seed. Lưu commit, toolchain, driver, flags và câu lệnh. Mỗi phiên bản ứng viên kế thừa bản đã giữ gần nhất. |
| Kiểm thử bắt buộc | Sáu synthetic, chín cấu hình chuẩn và ba challenge. Trạng thái phải khớp baseline, synthetic RMSE ≤ 0,5 px và Max ≤ 1 px, sai lệch tái chiếu so với bản trước < 0,1 px trên tập kiểm tra, canvas/offset khớp chính xác và Max RGB ≤ 1. Ghi riêng ca challenge/small xuất ảnh lệch và lỗi dự kiến ở medium/large nếu bản đối chứng vẫn tái lập hành vi P7. Memcheck cho suite tương ứng và CLI production phải đạt 0 lỗi và 0 byte rò rỉ. |
| Đo chính thức | Một warm-up và ít nhất năm lượt đo mỗi cấu hình, không bật profiler trong lượt benchmark. Báo thời gian từng stage, H2D, D2H, tổng kernel, end-to-end và speedup so với bản trước và V0 trong cùng phiên. V4 đo thêm S6 và lưu lượng bộ nhớ. V5 đo thêm thời gian đến S4, overlap và peak VRAM. |
| Kiểm tra độ ổn định | Ca chính chạy thêm năm khối đo ghép cặp, luân phiên thứ tự baseline/ứng viên. Mỗi khối dùng trung bình năm lượt đo sau warm-up. Báo median và khoảng min–max của mức cải thiện theo khối, cùng bảng kết quả từng ca chuẩn. Tách dữ liệu profiling khỏi dữ liệu timing chính thức. |
| Quyết định đề xuất | Giữ ứng viên nếu đạt correctness/memcheck, ca chính cải thiện median `Total_ms` ít nhất 5% với ít nhất 4/5 khối cùng chiều và không có cấu hình chuẩn nào chậm quá 5% sau khi đo lại ca nghi ngờ. Với V4, kiểm tra thêm tín hiệu giảm thời gian S6. Với V5, kiểm tra giảm thời gian đến S4 và overlap thực tế. Đây là ngưỡng ra quyết định đề xuất trước phép đo, có thể chốt với nhóm trước khi chạy. |
| Bàn giao | Lưu CSV thô, manifest ảnh, log test, trace `.nsys-rep`, report `.ncu-rep` liên quan, ảnh/crop challenge và kết luận APOD theo Bottleneck → Idea → Implementation → Result → Analysis. Ghi kết quả đo kể cả khi ứng viên bị loại. |

Chạy từ gốc repo trên Colab. Các lệnh V4/V5 dưới đây dùng khi dispatcher, CSV parser và suite tương ứng đã được đăng ký. Tạo thư mục output riêng cho từng lần chạy benchmark.

```bash
python scripts/build.py --require-t4 --out-dir build
python tests/run_tests.py --group all --require-t4
python scripts/run_benchmark.py --stitch build/stitch --dataset dataset \
    --runs 5 --versions 0 1 2 3 4 --include-challenge --out results/v4-comparison
compute-sanitizer --tool memcheck --leak-check full --error-exitcode 99 \
    ./build/stitch dataset/site2/large_left.jpg dataset/site2/large_right.jpg \
    build/v4-memcheck.png --version 4 --runs 1
```

Với vòng hai stream, dùng cùng quy trình cho ứng viên và bản đối chứng đã chốt. Thêm một trace Nsight Systems trên ca chính để xem thứ tự event và vùng chồng lấn. Chương có thể dùng lại cấu trúc nghiệm thu P7/P8 cho ma trận ảnh thật, log memcheck và gói bằng chứng. Nếu V3 hoặc bài nộp còn thiếu bằng chứng, dừng ở V3 và hoàn tất phần bắt buộc trước. [Đề bài, mục 4–5](../specs/CSC14120_2026_Final%20Project.md) · [Hướng dẫn profiling của nhóm](../profiling.md) · [Nghiệm thu P7](p7-v2-verification.md)
