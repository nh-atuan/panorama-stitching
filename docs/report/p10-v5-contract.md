<!-- Authors: Le Ha Thanh Chuong (23120195). External source: NVIDIA CUDA documentation linked below. -->

# P10-T01 — V5 Baseline and Execution Contract

Chương phụ trách điều tra baseline và chốt contract ngày 20/11/2026. Thành thực hiện API một ảnh ở T02, Chương thực hiện dispatcher ở T03, Tuấn nghiệm thu ở T04. Đế đo V5 chính thức ở T05. Các chữ ký dưới đây là giao diện cần triển khai, với semantics được chốt trước khi đo V5.

## 1. Baseline và bằng chứng

- Nền nhánh T01 là `ede4d51`, chứa merge PR #47 và toàn bộ P9. V4 production được nghiệm thu tại `ab8df98d7f15bb42d5e3306cf03a38311248b4a8`. P9-T05 checkout `ba97ed780785135e9d20ce36aac852efc4ebc898`, có `src/` và `scripts/build.py` khớp source nghiệm thu. [Nghiệm thu V4](p9-v4-verification.md) · [Benchmark P9](p9-t05-v4-apod.md)
- P9 đo Tesla T4, driver 580.82.07, nvcc 13.0.88, `sm_75 -O2 --fmad=false`, một warm-up và năm runs. Manifest ảnh SHA-256 là `99fc712988075326a351d0bf580405e418bb28d24d56d4cc1b31505c480bdd9d`. Đây là môi trường của bằng chứng P9.
- Máy điều tra T01 có GTX 1650, VRAM tổng 4096 MiB, còn trống 3935 MiB tại thời điểm truy vấn. PowerShell không tìm thấy `nvcc` hoặc `nsys`. Checkout có report và hình NSYS/NCU, chưa có SQLite, CSV timing thô hay ZIP evidence P9. Notebook P9 trên Git không lưu output. T01 chưa chạy đo mới trên T4. Bộ nhớ GTX là thông tin môi trường local.
- Bộ evidence P9 được report định danh bằng ZIP SHA-256 `a16c610c7a8bff02c6cd61c94bacd79a9d1d0793b2c838d58d996ca3c6e060c7`. Chương có thể tự trích khi nhận được archive từ kho chung. [Kho evidence](https://drive.google.com/drive/folders/1uJ-4_kgVONvIt5NQIPzdEWTIPrg8Sue1)

### Baseline ba ca large

| Ca | V4 Total (ms) | S6 V4 (ms) | Nguồn | H2D → S4 ready, H2D A/B, S1 A/B, S2, S3, host wait, GPU idle, peak/headroom T4 |
|---|---:|---:|---|---|
| site1/large | 107.157 | 19.531 | Bảng benchmark P9-T05 | Chưa có số trích được trong checkout |
| site2/large | 62.197 | 28.190 | Bảng benchmark P9-T05 | Chưa có số trích được trong checkout |
| site3/large | 100.393 | 20.405 | Bảng benchmark P9-T05 | Chưa có số trích được trong checkout |

Các số Total/S6 là kết quả được đọc từ report P9. Chúng không xác định thời gian trước S4. Các bảng NCU và NSYS của report chỉ chi tiết S6. Pre-S4 share, A/B imbalance, `asyncEngineCount`, `concurrentKernels` và mức contention còn cần được đo.

### Quy tắc chọn ca chính khi thiếu trace

Chốt **site2/large** trước khi xem số V5. Quy tắc dự phòng là chọn ca có Total V4 thấp nhất trong ba ca cùng kích thước ảnh large. Giả thuyết làm việc là công việc theo pixel trước S4 tương đương về quy mô, nên cùng mức giảm thời gian tuyệt đối có ảnh hưởng tương đối lớn hơn ở ca có Total nhỏ nhất. Số candidate và lịch sort có thể khác giữa các cảnh. Đây là quyết định theo proxy, có bất định, chưa phải xếp hạng từ pre-S4 timing. Kết quả trên cả ba ca và toàn bộ chín ca chuẩn vẫn phải báo cáo. Chốt này độc lập với lý do chọn hotspot S6 của P9.

### Thu thập phần baseline còn thiếu

Trên T4, ghi SHA checkout, hash binary và manifest, GPU/driver, nvcc, thuộc tính thiết bị, lệnh và exit code. Build bằng script production, chạy CLI V4 với một warm-up tự động và năm runs. Ghi lại stdout/stderr.

```bash
python scripts/build.py --compiler nvcc --require-t4 --out-dir build
mkdir -p results/p10-t01
for site in site1 site2 site3; do
  ./build/stitch dataset/$site/large_left.jpg dataset/$site/large_right.jpg \
    results/p10-t01/${site}.png --version 4 --runs 5 \
    > results/p10-t01/${site}.csv 2> results/p10-t01/${site}.log
  nsys profile --trace=cuda,nvtx,osrt --cuda-memory-usage=true \
    --force-overwrite=true -o results/p10-t01/${site} \
    ./build/stitch dataset/$site/large_left.jpg dataset/$site/large_right.jpg \
    results/p10-t01/${site}_profile.png --version 4 --runs 1
  nsys export --type sqlite --force-overwrite=true \
    -o results/p10-t01/${site}.sqlite results/p10-t01/${site}.nsys-rep
done
```

Trong SQLite, dùng correlation ID của CUDA API và GPU operations để tách warm-up khỏi run, xác định upload A/B và launch S4 đầu tiên. Báo hai mốc riêng là host submit đầu tiên → host submit S4, và GPU bắt đầu copy đầu tiên → GPU bắt đầu S4. Mốc thứ hai có thể gồm độ trễ launch sau khi dữ liệu sẵn sàng. Ghép NVTX `S1.image_a/b`, `S2.image_a/b`, `S3.image_a/b` với kernel/copy bên trong để xác định thời lượng A/B. Host wait lấy từ API `cudaStreamSynchronize` tại `S2.score_nms`, bao gồm thời gian đợi công việc trước đó.

GPU idle là phần bù của hợp các khoảng GPU copy/kernel trong cửa sổ trước S4. Không cộng các duration chồng lấn. Peak allocation lấy từ timeline memory của NSYS nếu có đủ allocation/free. Ghi free VRAM tại các mốc chuẩn bị xong, trước S4, sau S6, sau D2H bằng `cudaMemGetInfo` trong lượt chẩn đoán, và báo mức thấp nhất đã lấy mẫu. Ghi riêng tổng bytes buffer do dispatcher sở hữu và phần headroom lấy mẫu. Hai đại lượng này chưa bao phủ stack, context, cache allocator hoặc biến động giữa các lần lấy mẫu.

## 2. Audit đường chạy V4

1. `main.cu::run_gpu_once` dùng một stream nonblocking. Reset `DeviceCounts`, upload A rồi B bằng `cudaMemcpy2DAsync`, sau đó gọi pipeline. Input pinned được chuẩn bị ngoài timing.
2. `v4_run_stages` dùng bộ stage V1, thay S5 bằng V3 và S6 bằng V4. S1 chạy A rồi B, S2 chạy A rồi B, S3 chạy A rồi B.
3. S1 dùng scratch cho blur tạm. S2 tái sử dụng scratch cho counter, score và sort keys. Sau score/NMS, S2 copy count vào biến host rồi `cudaStreamSynchronize` trước top-K. Lần chờ A làm trì hoãn cả việc submit công việc S2 của B.
4. S3 dùng scratch cho smoothing, scan và compacted keypoints. `load_pattern` dùng static flag cùng copy constant memory và synchronize lần đầu. S3 kernels đọc/ghi `DeviceCounts::status`, có nhánh lỗi ghi cả hai descriptor counts.
5. S4 cần cả descriptor arrays và counts hợp lệ. S4/S5 tái sử dụng scratch production, S6 cấp canvas sau setup. S6 đọc metadata về host và chờ stream trước khi biết kích thước output.
6. Các vùng scratch và `d_counts` hiện hành chỉ an toàn khi dùng tuần tự. Owner giải phóng buffers qua RAII sau khi stream hoàn tất. Hook kernel timing hiện hành là thread-local trên host. [Driver](../../src/main.cu) · [Pipeline](../../src/v1/v1_pipeline.cu) · [S2](../../src/v1/s2/v1_detect.cu) · [S3](../../src/v1/s3/v1_describe.cu) · [Workspace](../../src/common/common.h)

## 3. API một ảnh giao cho Thành

T02 đặt khai báo chung ở `src/v5/v5_image_branch.h`. Giao diện dùng lại `Image`, `GrayImage`, `Config`, `DeviceCounts`, `ErrorCode`, `PinnedBuffer`, `CudaStream` và các kernel hiện có. T02 triển khai các entry point dưới đây. T03 quản lý owner và scheduler. Code fence này chốt chữ ký C++11 cần triển khai.

```cpp
namespace panorama {

struct V5ImageBranch {
    Image image;                    // Device RGB view.
    GrayImage gray;                  // Device normalized float view.
    Keypoint* keypoints = nullptr;
    Descriptor* descriptors = nullptr;
    DeviceCounts* counts = nullptr;  // Private record, local image uses A fields.
    std::uint8_t* scratch = nullptr;
    std::size_t scratch_bytes = 0;
    std::size_t feature_capacity = 0;
    std::uint32_t* host_candidates = nullptr;  // One pinned element.
};

// Preparation runs outside timing. Success publishes required scratch capacity.
ErrorCode v5_image_scratch_bytes(const Image& host, const Config& config,
                                 std::size_t& bytes);
// Initializes Gaussian weights and BRIEF constant memory on the current device.
// Returns only after initialization has completed.
ErrorCode v5_initialize_features(const Config& config, cudaStream_t stream);

// Each function enqueues on the supplied stream and checks launch/API errors.
ErrorCode v5_reset_image(V5ImageBranch& branch, cudaStream_t stream);
ErrorCode v5_upload_image(const Image& pinned_host, V5ImageBranch& branch,
                          cudaStream_t stream);
ErrorCode v5_preprocess_image(V5ImageBranch& branch, const Config& config,
                              cudaStream_t stream);
ErrorCode v5_detect_candidates(V5ImageBranch& branch, const Config& config,
                               cudaStream_t stream);
ErrorCode v5_finish_detect(V5ImageBranch& branch, const Config& config,
                           cudaStream_t stream);
ErrorCode v5_describe_image(V5ImageBranch& branch, const Config& config,
                            cudaStream_t stream);
}
```

- `V5ImageBranch` là view host mượn storage. Dispatcher cấp RGB, gray, feature arrays, một `DeviceCounts`, scratch căn hàng 16 byte và một `PinnedBuffer<uint32_t>(1)` riêng cho từng ảnh. `v5_image_scratch_bytes` lấy max nhu cầu S1, S2, S3 của đúng ảnh đó, kiểm tra dimensions, Config và overflow trước khi công bố bytes. S1–S3 chỉ mượn storage.
- `v5_reset_image` reset private counts/status, output counts và candidate slot về trạng thái sạch trên stream. API dùng local `keypointsA/descriptorsA` cho cả hai nhánh độc lập, các field B/matches private bằng 0. Đến hội tụ mới ánh xạ local A của nhánh B sang field B production.
- `v5_upload_image` dùng `cudaMemcpy2DAsync`, kiểm tra cùng kích thước, RGB, stride/capacity của nguồn và đích. Con trỏ host phải pinned và sống đến khi copy hoàn tất.
- `v5_detect_candidates` enqueue score/NMS và copy candidate count vào `host_candidates`, rồi trả về. Scheduler ghi `countReady` ngay sau lời gọi thành công. Count chỉ được đọc sau khi event này đã hoàn tất. Trường hợp ảnh quá nhỏ để có vùng candidate cũng phải ghi count = 0 và đi qua cùng giao thức event.
- `v5_finish_detect` yêu cầu countReady đã được host xác nhận, tính kept bằng đúng giới hạn hiện hành, sort theo tie-break của V4 rồi publish local keypoint count. Bỏ countReady wait sẽ đọc pinned storage khi D2H còn đang ghi.
- `v5_describe_image` enqueue smoothing, support check, scan, descriptor, copy-back và publish count. Private status có thể được device cập nhật sau khi API trả về. Nhánh hoàn tất khi event `done` sau S3 hoàn tất. Không nạp lại BRIEF hoặc đồng bộ ngầm ở API describe.
- T02 chuẩn bị Gaussian weights từ Config trước timing và dùng pattern chung bất biến đã khởi tạo trên đúng CUDA device. Thiết kế một host thread, một Config, một device trong vòng đời owner. Nếu đổi device/context, gọi initializer cho context mới. Tránh dùng static process flag thay cho điều kiện đã khởi tạo trên context hiện hành.

### Owner và vòng đời

T03 khai báo `V5DeviceOwner` tại `src/v5/v5_pipeline.h`, chứa hai branch owners, downstream owner, ba nonblocking streams, sự kiện từng nhánh và timing. Các method lifecycle cần có là `v5_prepare(const Image&, const Image&, const Config&, V5DeviceOwner&)` trả ErrorCode, cùng destructor `noexcept` chờ stream rồi thu hồi vùng sở hữu. Owner không copy được. API reset/run tái sử dụng allocation đã chuẩn bị.

Downstream `DeviceWorkspace` trỏ mượn RGB/gray/keypoint/descriptor hai nhánh, sở hữu record counts hợp nhất, match/H/canvas metadata và scratch S4/S5 riêng. Giữ scratch S5 sống qua S6 để lấy diagnostics. Chỉ một owner giải phóng mỗi allocation. `d_panorama` tiếp tục alias `d_canvas`. Tránh đặt view có con trỏ mượn vào `V1DeviceOwner`, vì destructor đó giải phóng tất cả pointer fields.

Khởi tạo có thể thất bại giữa chừng. Owner lưu các allocation thành công ngay, và chỉ gọi free sau khi mọi stream có thể dùng chúng đã được drain. Hai chế độ giữ cùng hai scratch allocations suốt lượt đo để đối chứng memory footprint công bằng. S6 giữ chính sách cấp canvas theo kích thước H của V4 trong vùng đo, pinned output được reserve bằng warm-up ngoài lượt đo.

## 4. Scheduler và điều kiện hội tụ

T03 dùng `enum class V5Schedule { Sequential, DualStream };` và thêm cờ `--v5-schedule sequential|dual`, chỉ hợp lệ với version 5. Mặc định là `dual`. Chế độ này điều khiển thứ tự phát việc, giữ cùng kernel, Config, storage, event và số lượng phép đo. T05 ghi rõ mode trong lệnh và thư mục evidence.

```text
control: drain prior run → reset downstream → record origin
                     ↙                            ↘
A: wait origin → reset → H2D → S1 → S2 candidates → countReadyA
B: wait origin → reset → H2D → S1 → S2 candidates → countReadyB
host: enqueue both prefixes, then query countReadyA/B
ready branch: finish S2 top-K → S3 → done + private status copy
control: wait doneA + doneB → merge counts/status → readyS4 → S4 → S5 → S6 → D2H → stop
```

Host một thread enqueue prefix cả A và B trước khi chờ count. Poll bằng `cudaEventQuery`, cho nhánh ready thực hiện finish/S3 trước. Nếu cả hai ready cùng lần poll thì phát A trước. Trả `cudaErrorNotReady` nghĩa là tiếp tục chờ, mọi lỗi khác đi vào cleanup. Host polling dùng yield để tránh vòng lặp bận không giới hạn. Tách NVTX `V5.A/B.count_wait` để định lượng chi phí host.

Ghi `done` sau S3 và copy private metadata cần dùng về pinned storage nếu có debug. Sự kiện phụ thuộc của control phải ghi sau mọi thao tác mà merge cần. Hợp nhất counts/status trên control bằng kernel nhỏ sau hai event. Kernel hội tụ ánh xạ local counts của A/B về production fields, chọn lỗi theo mục 6 và giữ matches = 0. S4 có thể enqueue theo stream ordering và đọc status device như V4, nên không cần một vòng D2H counts để quyết định trên host.

Chế độ Sequential dùng đúng hai branch streams và event như DualStream, nhưng B chờ `doneA` rồi host mới phát prefix B. Các endpoint và timing vẫn ghi cho cả hai. Control chờ cả hai done ở cả hai mode. Thời gian B chờ A không được cộng vào các interval H2D/S1/S2/S3 riêng của B.

Stream wait là dependency trên device. Host đọc count phải query/synchronize countReady. Downstream chỉ dùng private feature buffers sau hai done và merge trên control. Final output chỉ host-visible sau D2H stop hoàn tất. Tham khảo semantics `cudaStreamWaitEvent` và event timing của [CUDA Runtime API](https://docs.nvidia.com/cuda/cuda-runtime-api/group__CUDART__STREAM.html) và [Best Practices Guide](https://docs.nvidia.com/cuda/archive/13.0.0/cuda-c-best-practices-guide/index.html#asynchronous-and-overlapping-transfers-with-computation).

## 5. Timing và artifact chi tiết

Giữ stdout V5 đúng header mà `version_columns(5)` hiện tại tạo ra, rồi các run, Average, Minimum theo parser production.

```text
Run_Index,S1_V5_ms,S2_V5_ms,S3_V5_ms,S4_V5_ms,S5_V5_ms,S6_V5_ms,Total_ms,H2D_ms,D2H_ms,Total_Kernel_ms
```

| Đại lượng | Cách đo đã chốt |
|---|---|
| H2D A/B | Hai CUDA events trên đúng branch stream bao quanh copy ảnh, sau reset |
| S1, S2, S3 A/B | Events bao quanh mỗi stage trên branch stream. S2 start trước score/NMS, stop sau top-K/publish, gồm cả khoảng chờ host tiếp tục |
| Cột S1–S3 chính | Tổng interval A+B của cùng stage. Tổng có thể vượt wall time khi overlap |
| `H2D_ms` chính | Tổng duration H2D A+B, không gồm D2H candidate metadata |
| S4–S6 | Hai events mỗi stage trên control stream, giữ semantics V4, gồm setup hoặc chờ nằm trong interval |
| `D2H_ms` | Event quanh copy panorama cuối trên control |
| `Total_ms` | Host steady_clock từ trước reset per-run đến khi D2H stop synchronized. Cấp phát dài hạn, nạp pattern, I/O ảnh và ghi log ngoài vùng đo |
| `Total_Kernel_ms` | Tổng event duration từng kernel, bao gồm reset/publish/merge kernel khi instrumented, cộng cả interval đang overlap |
| Thời gian đến S4 | `origin` trên control trước upload, hai branches chờ origin. Control chờ hai done, merge rồi record `readyS4`. CUDA event elapsed origin → readyS4 là thời gian pre-S4, gồm reset, branch work và merge |
| Host pre-S4 | steady_clock mốc đầu run → host submit S4. Báo riêng với tên host, không dùng thay GPU event pre-S4 |
| Candidate-count wait | steady_clock đo thời gian CPU chờ count; đây là host wait, không gán thành kernel duration |

Mọi event đo thời gian được tạo ngoài run với timing enabled. Sự kiện chỉ dùng dependency có thể disable timing. Mốc origin và nhánh stop cùng CUDA device. Chỉ lấy elapsed sau khi các endpoint hoàn tất. Tránh event trên default stream làm phát sinh thứ tự ngầm. Reuse events sau khi run trước đã drain.

Đặt dữ liệu chi tiết tại sidecar CSV riêng bằng cờ `--v5-detail-csv <path>`. Header được chốt cho T03 như sau, đơn vị ms trừ bytes. Sidecar ghi timed runs, không ghi warm-up, giữ stdout đúng schema chính.

```text
Run_Index,Mode,H2D_A_ms,H2D_B_ms,S1_A_ms,S1_B_ms,S2_A_ms,S2_B_ms,S3_A_ms,S3_B_ms,PreS4_ms,Host_PreS4_ms,CountWait_A_ms,CountWait_B_ms
```

Owner dùng một host thread enqueue lên hai stream. Có thể dùng một `KernelTiming` như hiện tại, vì counter của nó tăng lúc host phát lệnh và mỗi event pair được record trên stream tương ứng. Warm-up phải bao phủ cùng launch count với timed runs của mode đó. Khi launch count thay đổi, xử lý lại capacity trước đo theo semantics hiện có. Nếu triển khai nhiều host threads sau này phải tách collectors hoặc đồng bộ host instrumentation.

Một warm-up precedes ít nhất năm timed runs. Timing benchmark không có profiler. Peak VRAM thu ở lượt chẩn đoán riêng bằng NSYS allocation timeline và device-owned bytes, bổ sung `cudaMemGetInfo` tại các checkpoint. Ghi free/total, asyncEngineCount và concurrentKernels vào environment artifact. Gắn nhãn sampled headroom nếu chỉ lấy mẫu, không gọi nó là peak chính xác. [Kernel instrumentation](../../src/common/kernel_timing.cuh) · [CSV parser](../../scripts/run_benchmark.py)
