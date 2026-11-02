# S6 CUDA Verification — Colab Tesla T4

Người soạn: Lê Hà Thanh Chương (23120195). Ngày kiểm chứng: 30/10/2026. Phạm vi: P5-T12/P5-T13.

## Acceptance Result

Lượt chạy `Group16_S6_CUDA_Verification.ipynb` trên Colab T4 đạt toàn bộ 10 gate và kết thúc bằng `READY FOR T4 REVIEW`. Log build, test, command, metadata từng cặp và summary trong gói `group16-s6-569cc1abce-evidence` đã được đối chiếu lại; 78 file source/script/test trong manifest khớp SHA-256 với source hiện tại trước khi commit tài liệu.

P5-T12 đáp ứng tiêu chí build/chạy V0 trên T4 và đã merge qua PR #22. P5-T13 hoàn tất cài đặt và kiểm chứng kỹ thuật, chuyển sang **Chờ review**; chỉ đánh dấu Xong sau khi PR của stage được merge vào `main`.

## Environment and Provenance

| Thuộc tính | Giá trị từ evidence |
|---|---|
| Bắt đầu phiên | 30/10/2026, 08:21:30 UTC, tương ứng 15:21:30 Việt Nam |
| GPU | Tesla T4, 15.360 MiB |
| Driver | 580.82.07 |
| CUDA compiler | 13.0, nvcc V13.0.88 |
| Target | `-arch=sm_75`, C++11, `-O2`, `--fmad=false` |
| CPU | Intel Xeon CPU @ 2.00 GHz |
| Python | 3.13.16 |
| Git base commit của source chạy | `c49a6d0e564382dc493d0ba463782b1ea8b8796c` |
| Source snapshot SHA-256 | `6bbcf3595c3631d8df91a906bc88f781046a5dad1b2ac305c00dc97c6390fb28` |
| `verification_summary.json` SHA-256 | `1ce88f86d7d55c85c5c6bb4c81bc9daab9ea7d8ce7b86bc8bbe4c902978c23a9` |
| Notebook có output SHA-256 | `fba751d6773e6fe029a60eea8b56f396754f2cf38198cd9d7cb55522915c6c2e` |

Source package khi chạy có hai script hỗ trợ chưa commit (`package_s6_verification.py`, `s6_colab_helpers.py`); chúng được hash trong snapshot và giữ nguyên nội dung khi đưa vào Git. Vì vậy Git base commit được ghi cùng snapshot digest, không dùng riêng commit SHA để mô tả toàn bộ gói chạy.

Notebook có output gốc được giữ ngoài Git; bản `Group16_S6_CUDA_Verification.ipynb` trong repo giữ nguyên Markdown/code, chỉ bỏ output, execution count và metadata thực thi. Raw evidence, ảnh và binary không được commit theo quy định nhóm.

## Build and V0 Regression

- `scripts/build.py --compiler /usr/local/cuda/bin/nvcc --require-t4` thành công, có link module S6 CUDA mới.
- Binary test S6 liên kết V0 reference và wrapper `cudaMalloc` dùng để giả lập OOM; production allocator không bị thay đổi.
- Toàn bộ **13 suite V0 / 45.256 checks** đạt trên T4.
- Cặp site1/small chạy `--version 0 --debug`, không truyền `--runs`, tạo đủ năm dòng đo cùng Average/Minimum và PNG RGB hợp lệ. CSV vẫn giữ tám cột.

Smoke test này ghi Total trung bình **1.104,1949736 ms**, nhỏ nhất **1.087,608352 ms**. Đây là kiểm tra luồng V0 trên một cặp, không phải bảng benchmark đa phiên bản. Không dùng các số này để suy ra speedup S6 GPU.

## S6 Fixtures and Fixed Tolerances

Suite fixture đạt **709 checks**, gồm **66 lần đối chiếu V0/V1** và các oracle giải tích độc lập. Sai số RGB lớn nhất quan sát được là **0**, thấp hơn ngưỡng đã chốt **1 mức màu/kênh**. Geometry, offset, stride và ErrorCode phải khớp chính xác; oracle giải tích, chạy lặp và bảo toàn input/padding yêu cầu khớp từng byte.

Các nhóm kiểm tra bao gồm identity, tịnh tiến nguyên/phân số/âm, projective, scale/sign H, snap gần số nguyên, hàng/cột cuối, ảnh nhỏ, padding, bốn vùng blending, pixel đen hợp lệ, singular/horizon, NaN/Inf, giới hạn canvas, OOM và ownership khi thay output. Không nới tolerance sau khi chạy.

## Real Image Pairs with the Same H

Mỗi case lấy H B→A từ lượt V0 trên chính phiên Colab này, rồi truyền đúng chín hệ số đó cho C++ test. Hai renderer dùng cùng input và cùng H; case thật chỉ đạt khi có output để đối chiếu, không chấp nhận hai bên cùng trả lỗi như một phép so ảnh thành công.

| Cặp | Kích thước | Canvas W × H | Max absolute RGB error | Ngưỡng | Kết quả |
|---|---|---|---|---|---|
| site1 | small | 2420 × 971 | 0 | 1 | PASS |
| site1 | medium | 3692 × 1496 | 0 | 1 | PASS |
| site1 | large | 7399 × 3028 | 0 | 1 | PASS |
| site2 | small | 2732 × 1426 | 0 | 1 | PASS |
| site2 | medium | 4162 × 2148 | 0 | 1 | PASS |
| site2 | large | 8477 × 4507 | 0 | 1 | PASS |
| site3 | small | 2356 × 1241 | 0 | 1 | PASS |
| site3 | medium | 3558 × 1791 | 0 | 1 | PASS |
| site3 | large | 7008 × 3453 | 0 | 1 | PASS |
| challenge | small | 1832 × 976 | 0 | 1 | PASS |
| challenge | medium | 2746 × 1489 | 0 | 1 | PASS |
| challenge | large | 5514 × 2956 | 0 | 1 | PASS |

Kết quả **12/12** cho thấy S6 GPU tái hiện cùng raster RGB như V0 trên các input/H đã thử. Điều này kiểm chứng renderer; không chứng minh H do S5 ước lượng là ground truth, không bảo đảm panorama hết parallax/ghosting và không kiểm chứng pipeline GPU S1–S5.

## Compute Sanitizer

| Target | Kết quả target | Error summary | Leak summary |
|---|---|---|---|
| Fixtures | 709 checks / 66 đối chiếu PASS | 0 errors | 0 bytes / 0 allocations |
| site2/large | 720 checks / 67 đối chiếu PASS | 0 errors | 0 bytes / 0 allocations |

Invocation site2/large chạy lại suite synthetic rồi thêm một cặp thật; không cộng các counts ở hai dòng thành số test độc lập. Log và command xác nhận dùng `--tool memcheck --leak-check full --error-exitcode 99`; không dựa duy nhất vào return code.

Memcheck sạch cho hai target đã chạy giải quyết phần kiểm tra bị giới hạn WDDM ở máy local. Không suy rộng thành memcheck cho mọi cặp hoặc mọi homography có thể có.

## Integration Handoff

Code S6 và test đáp ứng nghiệm thu kỹ thuật P5-T13; phần còn lại là review/merge. Không đổi phương pháp V0, không có feather blending và không có thay đổi kernel sau lượt T4 này.

Phần tích hợp thuộc P6:

1. Nối `v1_warp_blend` thật sau khi S5 GPU cung cấp H hợp lệ; CLI hiện vẫn gọi `v1_scaffold_warp_blend`.
2. Cấp pinned output theo canvas động trước D2H; không dùng dung lượng bằng ảnh A của scaffold cho panorama thật.
3. Hoàn thiện GPU timing, kernel-only total và transfer/end-to-end trên pipeline tích hợp. Notebook này không có số đo kernel S6 hoặc speedup GPU.
4. Benchmark/profiling V1 trên dataset cuối kỳ đã chốt, rồi mới quyết định tối ưu V2/V3.

Quy trình tái lập: [S6 Colab guide](../s6-colab-guide.md); thiết kế và lệnh test: [S6](../stages/s6-warp-blend.md). Gói evidence gốc chứa 30 command record, log stdout/stderr, source manifest, input hash và H của từng case; notebook có output và gói này được giữ làm tài liệu review ngoài Git.
