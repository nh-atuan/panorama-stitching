<!-- Authors: Nguyen Ho Anh Tuan (23120185). External source: none. -->

# P9-T02 — V4 Verification

## 1. Scope

P9-T02 kiểm tra tính tương đương V0–V4, contract CLI V4 và an toàn bộ nhớ trên Tesla T4. Tuấn phụ trách xây dựng suite tích hợp C++/CUDA `tests/gpu/test_gpu_v4_pipeline.cu`, harness CLI `scripts/verify_v4_cli.py`, kiểm thử runner Python, notebook `Group16_P9_V4_Verification.ipynb`, cùng toàn bộ quá trình thực thi nghiệm thu và kiểm tra an toàn bộ nhớ Compute Sanitizer trên môi trường Google Colab GPU Tesla T4. [Phân công P9](../task-board.md)

## 2. Repository Baseline

| Hạng mục | Giá trị |
|---|---|
| Nhánh kiểm thử | `tuan/p9` |
| Nền nhánh | `d558bdb135bfdb0e82cb2088f118d0987f4cbfa1` |
| SHA production V4 đã merge | `8751a7551af8b5a6bbb347f2d3bb73c74a911cac` |
| SHA checkout nghiệm thu V4 | `ab8df98d7f15bb42d5e3306cf03a38311248b4a8` |
| Trạng thái mã nguồn | Khớp production SHA, không phát sinh file chưa theo dõi |

## 3. Environment

Môi trường kiểm chứng chính thức là Google Colab GPU Tesla T4, compute capability 7.5. Runner dùng `nvcc -arch=sm_75 -std=c++11 -O2 --fmad=false` qua `scripts/build.py` và `tests/run_tests.py`.

Thông số môi trường thu thập trực tiếp tại phiên nghiệm thu:
- GPU: Tesla T4 (ID 0), Compute Capability 7.5
- Driver: 580.82.07
- CUDA Compiler: nvcc 13.0.88
- CUDA Runtime API: 13000 (CUDA 13.0)
- NVIDIA Compute Sanitizer: 2025.3.1.0

Trước khi chạy Colab, runner Python và các test unit cho harness CLI V4 đã được kiểm tra cục bộ đạt 12/12 suite (172 tests).

## 4. Dataset and Fixtures

- Dataset gồm 24 ảnh thuộc bốn cặp `thanh-standard1`, `thanh-standard2`, `de-standard2` và `de-challenge1`. Mỗi cặp có ba độ phân giải `small` 1280×720, `medium` 1920×1080 và `large` 3840×2160. Toàn bộ 24 ảnh đã được đối chiếu khớp hoàn toàn với manifest SHA-256 `99fc712988075326a351d0bf580405e418bb28d24d56d4cc1b31505c480bdd9d`. [Dataset](../dataset.md)
- Synthetic fixture gồm đúng sáu cặp từ P7/P8, mỗi cặp có hai ảnh PNG và một file JSON H_gt theo chiều B→A. Toàn bộ 18 file synthetic đã được đối chiếu khớp SHA-256. Runner dùng cùng một `Config` cho mọi phiên bản trong từng ca, bao gồm seed RANSAC 16 cố định.

## 5. Synthetic Verification

Suite `tests/gpu/test_gpu_v4_pipeline.cu` kiểm tra bốn tầng (Tier 1: exit status, Tier 2: H_gt RMSE ≤ 0,5 px, Max ≤ 1 px, drift < 0,1 px, Tier 3: canvas/offset khớp tuyệt đối, Tier 4: Max RGB ≤ 1).

| Ca kiểm thử | Số điểm Q | V4 RMSE vs H_gt | V4 Max vs H_gt | Drift cực đại vs V0–V3 (px) | Canvas (offset) | Max RGB |
|---|---:|---:|---:|---|---|---:|
| translation/small | 180 | 7,20e-06 px | 7,20e-06 px | 4,56e-13, 0, 0, 0 | 1984×720 (0,0) | 0 |
| translation/medium | 180 | 0,00472 px | 0,0165 px | 0, 0, 0, 0 | 2975×1082 (0,1) | 0 |
| translation/large | 180 | 2,62e-05 px | 2,62e-05 px | 1,14e-12, 0, 0, 0 | 5952×2160 (0,0) | 0 |
| projective/small | 165 | 0,0552 px | 0,143 px | 0, 0, 0, 0 | 1979×791 (0,35) | 0 |
| projective/medium | 165 | 0,0625 px | 0,209 px | 0, 0, 0, 0 | 2968×1185 (0,52) | 0 |
| projective/large | 165 | 0,100 px | 0,209 px | 0, 0, 0, 0 | 5937×2369 (0,104) | 0 |

Toàn bộ sáu ca synthetic đều thỏa mãn chặt chẽ cả bốn tầng tiêu chuẩn:
- Sai số H_gt lớn nhất là RMSE 0,100 px và Max 0,209 px (ngưỡng cho phép RMSE ≤ 0,5 px, Max ≤ 1,0 px).
- Độ lệch chiếu so với V0, V1, V2, V3 tối đa chỉ 4,56e-13 px (ngưỡng cho phép < 0,1 px).
- Kích thước canvas và offset khớp chính xác tuyệt đối.
- Max RGB = 0 trên toàn bộ các ca.

## 6. Real-Image Regression

Ma trận kiểm thử 12 cấu hình ảnh thực tế được chạy trên cả năm phiên bản (V0, V1, V2, V3, V4):

| Cấu hình | Cặp ảnh | Trạng thái V0–V4 | Drift vs V0–V3 (px) | Canvas (offset) | Max RGB vs V4 | Kết luận |
|---|---|---|---|---|---|---|
| site1/small | thanh-standard1 | Success cả năm | [0, 0, 0, 0] | 2420×971 (0,84) | [0, 0, 0, 0] | PASS |
| site1/medium | thanh-standard1 | Success cả năm | [0, 0, 0, 0] | 3692×1496 (0,140) | [0, 0, 0, 0] | PASS |
| site1/large | thanh-standard1 | Success cả năm | [0, 0, 0, 0] | 7399×3028 (0,313) | [0, 0, 0, 0] | PASS |
| site2/small | thanh-standard2 | Success cả năm | [0, 0, 0, 0] | 2558×1440 (0,346) | [0, 0, 0, 0] | PASS |
| site2/medium | thanh-standard2 | Success cả năm | [0, 0, 0, 0] | 3818×2154 (0,513) | [0, 0, 0, 0] | PASS |
| site2/large | thanh-standard2 | Success cả năm | [0, 0, 0, 0] | 7676×4348 (0,1038) | [0, 0, 0, 0] | PASS |
| site3/small | de-standard2 | Success cả năm | [0, 0, 0, 0] | 2356×1241 (0,312) | [0, 0, 0, 0] | PASS |
| site3/medium | de-standard2 | Success cả năm | [0, 0, 0, 0] | 3558×1791 (0,414) | [0, 0, 0, 0] | PASS |
| site3/large | de-standard2 | Success cả năm | [0, 0, 0, 0] | 7008×3453 (0,758) | [0, 0, 0, 0] | PASS |
| challenge/small | de-challenge1 | Success cả năm | [0, 0, 0, 0] | 2835×1551 (0,794) | [0, 0, 0, 0] | PASS |
| challenge/medium | de-challenge1 | NumericalFailure cả năm | — | — | — | PASS (lỗi dự kiến) |
| challenge/large | de-challenge1 | NumericalFailure cả năm | — | — | — | PASS (lỗi dự kiến) |

Kết quả hồi quy:
- 12/12 cấu hình có trạng thái thực thi hoàn toàn nhất quán giữa cả năm phiên bản V0–V4.
- 10 ca thành công có độ lệch chiếu H drift = 0 px trên lưới so sánh 20×20 và Max RGB delta = 0 (trùng khớp từng pixel).
- Mọi canvas thành công đều mở rộng lớn hơn ảnh A, xác nhận D2H của canvas mở rộng hoạt động chính xác.
- Hai ca challenge medium và large thoát mã 1 tại S6 (`NumericalFailure`) đúng như quy định thiết kế, không tạo ảnh PNG hay dòng thời gian CSV rác.

## 7. Challenge Observations

Hành vi của cặp ảnh challenge trên V4 hoàn toàn nhất quán với các phiên bản tiền nhiệm V0–V3:
- Ở mức `small`, V4 hoàn tất và sinh ra ảnh ghép trùng khớp từng pixel với V0–V3 (Max RGB = 0). Do góc chụp và thị sai thực tế giữa hai ảnh lớn, vùng lan can và dầm trần xuất hiện hiện tượng nhân đôi đường nét. Đây là đặc tính thị sai đã ghi nhận từ V0 giữa kỳ, không phải lỗi phát sinh từ tối ưu hóa V4.
- Ở mức `medium` và `large`, phép tính ma trận biến đổi tại S6 dẫn tới suy biến hình học, pipeline bắt lỗi `NumericalFailure` và dừng đúng điểm thiết kế.

## 8. CLI and CSV Verification

Harness `scripts/verify_v4_cli.py` và runner `scripts/run_benchmark.py` kiểm tra contract giao tiếp của CLI V4:
- Header CSV V4 tuân thủ chặt chẽ định dạng 11 cột quy định trong `docs/interface.md`:
  `Run_Index,S1_V4_ms,S2_V4_ms,S3_V4_ms,S4_V4_ms,S5_V4_ms,S6_V4_ms,Total_ms,H2D_ms,D2H_ms,GPU_Internal_ms`
- `verify_v4_cli.py` kiểm tra số dòng, thứ tự cột, tính hợp lệ của các giá trị thời gian, dòng `Average`, dòng `Minimum`, các trường hợp kiểm tra lỗi âm (thiếu tham số, sai file, sai phiên bản) và giải mã ảnh D2H: kết quả đạt exit 0.
- `run_benchmark.py --versions 4 --runs 2 --include-challenge` thực thi thành công, trích xuất bảng thời gian và ghi nhận đúng 2 ca thất bại trong `failures.csv` tương ứng với `challenge/medium` và `challenge/large`.

## 9. Compute Sanitizer

NVIDIA Compute Sanitizer kiểm tra an toàn bộ nhớ với công cụ memcheck và cờ `--leak-check full` trên GPU Tesla T4:

| Mục tiêu kiểm tra | Lệnh thực thi | Exit Code | Lỗi bộ nhớ | Bộ nhớ rò rỉ | Kết luận |
|---|---|---:|---:|---:|---|
| Suite V4 | `compute-sanitizer --tool memcheck --leak-check full ./build/tests_gpu/gpu_v4_pipeline` | 0 | 0 errors | 0 bytes (0 allocations) | PASS |
| CLI Production | `compute-sanitizer --tool memcheck --leak-check full ./build/stitch site1/small ... --version 4` | 0 | 0 errors | 0 bytes (0 allocations) | PASS |

Cả hai lượt chạy đều hoàn tất với exit 0, báo cáo `0 errors` và `0 bytes leaked in 0 allocations`, chứng minh pipeline V4 không có bất kỳ truy cập ngoài biên, bộ nhớ chưa cấp phát hay rò rỉ VRAM nào trên GPU.

## 10. Reproduction

Các lệnh chạy lại quá trình kiểm chứng trên Google Colab Tesla T4:

```bash
# 1. Biên dịch production và suite kiểm thử
python3 scripts/build.py --compiler nvcc --require-t4 --out-dir build

# 2. Chạy hồi quy GPU V4 đầy đủ (synthetic và dataset)
python3 tests/run_tests.py --compiler nvcc --group gpu \
  --suite gpu_pipeline --suite gpu_v2_pipeline --suite gpu_v3_pipeline --suite gpu_v4_pipeline \
  --require-v2-pipeline --v2-synthetic-dir tests/data/synthetic \
  --v3-synthetic-dir tests/data/synthetic --v3-dataset-dir data \
  --require-v4-pipeline --v4-synthetic-dir tests/data/synthetic --v4-dataset-dir data \
  --require-t4

# 3. Kiểm tra contract CLI V4
python3 scripts/verify_v4_cli.py --stitch build/stitch --dataset data \
  --out results/p9-v4-cli-smoke --require-t4

# 4. Kiểm tra an toàn bộ nhớ Compute Sanitizer
compute-sanitizer --tool memcheck --leak-check full --error-exitcode 99 \
  ./build/tests_gpu/gpu_v4_pipeline

compute-sanitizer --tool memcheck --leak-check full --error-exitcode 99 \
  ./build/stitch data/site1/small_left.jpg data/site1/small_right.jpg \
  build/p9-v4-memcheck.png --version 4 --runs 1 --debug
```

Toàn bộ gói bằng chứng nghiệm thu được nén tự động từ notebook: `Group16_V4_P9-T02_TeslaT4_Evidence_ab8df98d_20261117T125642Z.zip` với mã SHA-256 `1cf66d071e34b8fe7085b75579e2f571f3fd0b3c3dd3ebde02e4e57b6d2bccc6` (lưu tại thư mục Drive chung theo quy ước kết quả).

## 11. Final Acceptance Summary

| Cổng kiểm tra nghiệm thu | Tiêu chí đánh giá | Trạng thái |
|---|---|---|
| `production_build` | Biên dịch `build/stitch` bằng nvcc sm_75 | PASS |
| `v0_regression` | Hồi quy tuần tự V0 | PASS |
| `pipeline_regression` | Chạy 4 suite GPU (V1, V2, V3, V4) | PASS |
| `six_synthetic` | 6 cặp synthetic thỏa 4 tầng tiêu chuẩn | PASS |
| `real_matrix` | 12 cấu hình ảnh thực tế khớp trạng thái V0–V4 | PASS |
| `expanded_canvas_d2h` | Canvas mở rộng và D2H tải ảnh hợp lệ | PASS |
| `cli_csv` | Contract CSV 11 cột, CLI âm và giải mã PNG | PASS |
| `benchmark_runner` | Runner benchmark tích hợp và phân tích lỗi | PASS |
| `memcheck` | 0 errors, 0 bytes rò rỉ cho suite và CLI | PASS |
| `challenge_small_visual_review` | Đánh giá trực quan ảnh challenge/small | PASS |
| `source_unchanged` | Giữ nguyên snapshot mã nguồn | PASS |

**Kết luận chung: READY FOR REVIEW (Tất cả 11 cổng kiểm tra đều đạt PASS).**
