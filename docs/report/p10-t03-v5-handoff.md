<!-- Authors: Le Ha Thanh Chuong (23120195). External source: none. -->

# P10-T03 — V5 Dispatcher Integration Handoff

## Cập nhật 22/11 — Phần triển khai đã hoàn tất

Dispatcher/CLI/timing của Chương đã merge qua PR #48 (`d42000c`); API một ảnh hiện có trên main. [Verification V5](p10-v5-verification.md) và [freeze T02](p11-t02-freeze-verification.md) ghi kết quả nghiệm thu tích hợp. Không còn chờ implementation T02. Pin notebook `696fc82` có src/build khớp freeze `f2837a8`; source main mới sửa thêm kiểm tra host trong `v5_image_branch.cu`, cần evidence đúng SHA cho lần nghiệm thu cuối. Không lấy log cũ để chứng nhận thay đổi mới.

Các mục bên dưới giữ bản bàn giao tại checkpoint ban đầu để truy vết; trạng thái bị chặn ở đó không còn là trạng thái hiện tại.

## Historical Handoff Checkpoint

**BLOCKED — MISSING REQUIRED INTEGRATION.** Dispatcher được triển khai trên `chuong/p10-v5`, code checkpoint `828e075a19c4a89ee9fd94e113738ff8d3778801`. T01 giữ nguyên lịch sử và kết quả nghiệm thu T4. Khi fetch remote để triển khai T03, chưa có nhánh T02 của Thành và chưa có `src/v5/v5_image_branch.cu`. Do đó chưa có upstream T02 integration SHA và chưa có binary V5 đã chạy.

Header `src/v5/v5_image_branch.h` chỉ khai báo struct và tám hàm của [contract T01](p10-v5-contract.md). Thành bổ sung implementation tại `src/v5/v5_image_branch.cu` bằng kernel production hiện có. Khi có file này, builder bật `PANORAMA_V5_IMAGE_API_AVAILABLE`; link sẽ kiểm tra đủ các symbol. `--enable-v5` yêu cầu implementation tồn tại và báo lỗi rõ ràng nếu thiếu. Khi chưa có T02, các build production tiếp tục hỗ trợ V0–V4.

## Code đã triển khai

- `src/v5/v5_pipeline.h/.cu` cung cấp owner cho hai scratch/counters/features riêng, pinned candidate count riêng, hai nonblocking branch streams và một control stream. Downstream workspace chỉ mượn arrays của hai nhánh, sở hữu match/H/canvas/scratch riêng.
- Dual mode phát prefix H2D/S1/S2-candidates của cả A và B, query countReady và cho nhánh đã sẵn sàng hoàn tất top-K/S3 trước. Done event được ghi sau suffix. Kernel join trên control chờ cả hai event rồi hợp nhất status/counts trước S4.
- Sequential mode dùng cùng owner, API, allocation, kernel và timing. Nhánh B phụ thuộc doneA. Hai mode khác thứ tự phát việc.
- S4 dùng `v1_match`, S5 dùng `v3_homography`, S6 dùng `v4_warp_blend`. Status device tiếp tục đi theo cơ chế stage guard của production, các lỗi thuật toán được chọn theo stage rồi A trước B. Lỗi CUDA làm drain và trả `CudaFailure`.
- Owner drain mọi stream trước free, kể cả lỗi cấp phát một phần. Mỗi lượt reset private/public counts và H, đánh output chưa hợp lệ trước khi phát việc. Download chỉ nhận output của lượt thành công.
- CLI nhận `--version 5`, `--v5-schedule sequential|dual` và `--v5-detail-csv path`. Mặc định V5 là dual. Các option V5 chỉ hợp lệ với version 5.

## Timing

CSV chính dùng đúng `version_columns(5)`, gồm 11 cột và Average/Minimum. S1–S3 cùng H2D là tổng duration A+B. Các tổng này có thể lớn hơn wall time. Parser bỏ điều kiện tổng stage ≤ Total chỉ với V5, giữ kiểm tra đó cho V0–V4.

Sidecar có 14 cột theo contract. Branch duration và downstream duration lấy bằng CUDA events, đọc sau D2H synchronization. `PreS4_ms` dùng common origin và ready sau join. `Host_PreS4_ms` là host time tới lúc submit đoạn S4, không phải CUDA elapsed. Trong dual mode, CountWait là thời gian từ sau khi phát cả hai prefix đến khi host thấy countReady, có thể gồm thời gian host phát suffix của nhánh kia. Trong sequential mode, CountWait là thời gian host chờ riêng event của nhánh đó.

`Total_ms` dùng steady_clock đến thời điểm D2H stop synchronize xong, trước khi truy vấn event durations và ghi sidecar. `Total_Kernel_ms` cộng duration từng kernel qua hook host một thread, có thể cộng cả thời gian chồng lấn. Warm-up xác định launch count cho collector trước measured runs. Các tỷ lệ stage/Total trong công cụ summary biểu diễn duration công việc tương đối với wall time; với V5 không dùng chúng làm các phần độc lập cho phép tính Amdahl hay biểu đồ phân chia tổng thời gian.

## Validation đã thực hiện

- WSL Ubuntu, g++ 13.3.0: 14 suite V0 đạt, tổng 45.284 checks.
- Build CLI host với `-Wall -Wextra -Werror` đạt. Tám ca CLI âm/missing-input đạt, gồm version 5 khi thiếu T02, sai/nhân đôi mode, thiếu path sidecar, option V5 dùng cho V0 và runs bằng 0.
- Python regression sau thay đổi: 14 suite, tổng 187 test, exit 0, có một test cũ skip theo điều kiện môi trường. Suite mới có bảy test CPU về sidecar schema, mode, duration sums, giá trị không hữu hạn, thiếu run, feature gate và parser overlap. Có smoke harness chạy thực sau khi T02 đã tích hợp.
- Build command production vẫn target `sm_75`; `scripts/build.py --enable-v5 --print-command` báo thiếu T02 đúng dự kiến. Checkout dùng script build, không có cấu hình CMake riêng cần sửa.
- Máy local chưa có nvcc trong PowerShell hoặc WSL, nên code CUDA V5 chưa compile hoặc chạy. Chưa kiểm V5 sequential/dual, parity, timing trên GPU, failure injection hay memcheck. Kết quả T01 T4 xác nhận V4 baseline.

## Handoff cho Thành và Tuấn

Thành cần implement đủ chữ ký trong `v5_image_branch.h`, với local counts dùng các field A cho mỗi nhánh, D2H candidate vào pinned slot riêng và trả về sau enqueue. Scheduler đọc slot sau countReady. `v5_initialize_features` phải hoàn tất pattern/weights trước khi trả về, `v5_describe_image` không nạp pattern lần đầu hoặc đồng bộ host ngầm. Tránh chia sẻ trạng thái mutable giữa hai branch views.

Sau khi tích hợp T02, Chương kiểm build và chạy smoke rồi ghi SHA đã thực sự chạy vào bản bàn giao. Tuấn dùng SHA đó cho T04.

```bash
python scripts/build.py --compiler nvcc --require-t4 --enable-v5 --out-dir build
./build/stitch dataset/site1/small_left.jpg dataset/site1/small_right.jpg \
  build/v5-sequential.png --version 5 --v5-schedule sequential --runs 5 \
  --v5-detail-csv build/v5-sequential.csv --debug
./build/stitch dataset/site1/small_left.jpg dataset/site1/small_right.jpg \
  build/v5-dual.png --version 5 --v5-schedule dual --runs 5 \
  --v5-detail-csv build/v5-dual.csv --debug
python scripts/smoke_v5_dispatcher.py --stitch build/stitch --dataset dataset --out build/v5-smoke
```

Smoke harness chạy V4, V5 sequential và V5 dual với hai measured runs mỗi ca, so CSV/sidecar, H/canvas debug và RGB ở site1/small. Tuấn tiếp tục sáu synthetic và 12 cấu hình thật, ảnh khác kích thước, một/cả hai nhánh thiếu feature, lỗi event/launch/allocation, workspace reuse, challenge và memcheck. T05 của Đế chỉ dùng SHA đã được T04 nghiệm thu.
