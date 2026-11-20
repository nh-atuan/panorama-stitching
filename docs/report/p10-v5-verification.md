<!-- Authors: Nguyen Ho Anh Tuan (23120185). External source: none. -->

# P10-T04 — V5 Verification Report

## 1. Scope

P10-T04 kiểm tra tính tương đương và nhất quán giữa V0–V4 và V5 (gồm cả hai chế độ điều phối `sequential` và `dual`), contract CLI `--version 5`, định dạng sidecar CSV và an toàn bộ nhớ trên GPU Tesla T4. Tuấn phụ trách xây dựng suite tích hợp C++/CUDA `tests/gpu/test_gpu_v5_pipeline.cu`, harness CLI `scripts/verify_v5_cli.py`, kiểm thử runner Python trong `tests/run_tests.py`, notebook nghiệm thu `Group16_P10_V5_Verification.ipynb`, cùng tài liệu nghiệm thu kỹ thuật và kiểm tra Compute Sanitizer trên Google Colab. [Phân công P10](../task-board.md)

## 2. Repository Baseline

| Hạng mục | Giá trị |
|---|---|
| Nhánh kiểm thử | `tuan/p10` |
| Nền nhánh | `5278365 Merge pull request #49 from nh-atuan/chuong/p10-t06-v4-notebook` |
| Thành phần V5 tích hợp | `src/v5/v5_image_branch.{h,cu}`, `src/v5/v5_pipeline.{h,cu}`, `src/main.cu` |
| Trạng thái mã nguồn | Tích hợp đầy đủ entry point một ảnh P10-T02 và dispatcher P10-T03, cờ `-DPANORAMA_V5_IMAGE_API_AVAILABLE` được kích hoạt tự động |

## 3. Environment

Môi trường kiểm chứng chuẩn của môn học là Google Colab GPU Tesla T4 (Compute Capability 7.5):
- GPU: Tesla T4 (ID 0), Compute Capability 7.5
- Driver: 580.82.07
- CUDA Compiler: nvcc 13.0.88, cờ build `-arch=sm_75 -std=c++11 -O2 --fmad=false`
- NVIDIA Compute Sanitizer: 2025.3.1.0

Trước khi chạy nghiệm thu GPU, runner Python và các test unit cho harness CLI V5 đã được kiểm tra đạt 15/15 suite (193 tests) sạch lỗi.

## 4. Dataset and Fixtures

- **Dataset:** 24 ảnh thuộc 4 cặp ảnh chính thức (`thanh-standard1`, `thanh-standard2`, `de-standard2`, `de-challenge1`) ở 3 độ phân giải `small`, `medium`, `large`. Kiểm tra khớp toàn bộ hash SHA-256 theo `manifest.csv` (`99fc712988075326a351d0bf580405e418bb28d24d56d4cc1b31505c480bdd9d`). [Dataset](../dataset.md)
- **Synthetic Fixtures:** 6 cặp synthetic (3 translation, 3 projective) kèm ma trận ground truth $H_{gt}$ theo chiều $B \to A$. Dùng chung cấu hình chuẩn `Config` và seed RANSAC cố định (16).

## 5. Synthetic Verification

Suite `tests/gpu/test_gpu_v5_pipeline.cu` kiểm tra bốn tầng tiêu chuẩn:
- **Tier 1:** Trạng thái trả về (`ErrorCode::Success` trên 6 cặp).
- **Tier 2:** Sai số hình học so với $H_{gt}$ (RMSE $\le 0,5$ px, Max $\le 1,0$ px); độ trôi (drift) giữa V5 và V4 $< 0,1$ px; độ trôi giữa V5 Sequential và V5 Dual bằng đúng 0 px.
- **Tier 3:** Kích thước canvas và tọa độ offset khớp tuyệt đối giữa V5 và V4.
- **Tier 4:** Sai lệch màu Max RGB $\le 1$ so với V4; giữa V5 Sequential và V5 Dual là **0 bit-for-bit** (Max RGB = 0).

| Ca kiểm thử | Số điểm Q | V5 RMSE vs H_gt | V5 Max vs H_gt | Drift V5 vs V4 (px) | Drift V5_dual vs V5_seq | Canvas (offset) | Max RGB vs V4 | Max RGB dual vs seq |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| translation/small | 180 | 7,20e-06 px | 7,20e-06 px | 0 px | 0 px | 1984×720 (0,0) | 0 | 0 |
| translation/medium | 180 | 0,00472 px | 0,0165 px | 0 px | 0 px | 2975×1082 (0,1) | 0 | 0 |
| translation/large | 180 | 2,62e-05 px | 2,62e-05 px | 0 px | 0 px | 5952×2160 (0,0) | 0 | 0 |
| projective/small | 165 | 0,0552 px | 0,143 px | 0 px | 0 px | 1979×791 (0,35) | 0 | 0 |
| projective/medium | 165 | 0,0625 px | 0,209 px | 0 px | 0 px | 2968×1185 (0,52) | 0 | 0 |
| projective/large | 165 | 0,100 px | 0,209 px | 0 px | 0 px | 5937×2369 (0,104) | 0 | 0 |

Toàn bộ 6 ca synthetic đều đạt chuẩn tuyệt đối ở cả 4 tầng.

## 6. Real-Image Regression

12 cấu hình ảnh thực tế được chạy trên V0, V4, V5 Sequential và V5 Dual:

| Cấu hình | Cặp ảnh | Trạng thái V0/V4/V5 | Drift V5 vs V4 (px) | Canvas (offset) | Max RGB vs V4 | Kết luận |
|---|---|---|---|---|---|---|
| site1/small | thanh-standard1 | Success cả bốn | 0 px | 2420×971 (0,84) | 0 | PASS |
| site1/medium | thanh-standard1 | Success cả bốn | 0 px | 3692×1496 (0,140) | 0 | PASS |
| site1/large | thanh-standard1 | Success cả bốn | 0 px | 7399×3028 (0,313) | 0 | PASS |
| site2/small | thanh-standard2 | Success cả bốn | 0 px | 2558×1440 (0,346) | 0 | PASS |
| site2/medium | thanh-standard2 | Success cả bốn | 0 px | 3818×2154 (0,513) | 0 | PASS |
| site2/large | thanh-standard2 | Success cả bốn | 0 px | 7676×4348 (0,1038) | 0 | PASS |
| site3/small | de-standard2 | Success cả bốn | 0 px | 2356×1241 (0,312) | 0 | PASS |
| site3/medium | de-standard2 | Success cả bốn | 0 px | 3558×1791 (0,414) | 0 | PASS |
| site3/large | de-standard2 | Success cả bốn | 0 px | 7008×3453 (0,758) | 0 | PASS |
| challenge/small | de-challenge1 | Success cả bốn | 0 px | 2835×1551 (0,794) | 0 | PASS |
| challenge/medium | de-challenge1 | NumericalFailure cả bốn | — | — | — | PASS (lỗi dự kiến) |
| challenge/large | de-challenge1 | NumericalFailure cả bốn | — | — | — | PASS (lỗi dự kiến) |

Kết quả hồi quy:
- 12/12 cấu hình có trạng thái thực thi hoàn toàn nhất quán giữa V0, V4 và hai chế độ của V5.
- 10 ca thành công có $H$ drift = 0 px và Max RGB delta = 0 (trùng khớp từng bit).
- Hai ca challenge medium/large thoát mã lỗi `NumericalFailure` tại S6 đúng như thiết kế, không tạo ảnh rác hay dòng CSV rác.

## 7. CLI, Timing & Sidecar Verification

Harness `scripts/verify_v5_cli.py` kiểm tra toàn bộ contract CLI:
- Khung CSV chính: 11 cột chuẩn theo `interface.md`. Do hai nhánh A và B chạy bất đồng bộ chồng lấn, tổng thời gian các stage có thể lớn hơn `Total_ms`; parser của `scripts/run_benchmark.py` đã hỗ trợ đặc tính này cho V5.
- Khung sidecar CSV: 14 cột chi tiết phân rã thời gian cho từng ảnh:
  `Run_Index,Mode,H2D_A_ms,H2D_B_ms,S1_A_ms,S1_B_ms,S2_A_ms,S2_B_ms,S3_A_ms,S3_B_ms,PreS4_ms,Host_PreS4_ms,CountWait_A_ms,CountWait_B_ms`
- Kiểm tra các lỗi âm: chạy `--version 5` với `--v5-schedule` không hợp lệ, `--v5-detail-csv` thiếu đường dẫn, ảnh không tồn tại, số lượt chạy runs = 0 đều được bắt lỗi sạch sẽ và trả mã lỗi tương ứng.

## 8. Memory Safety & Compute Sanitizer

Chạy `compute-sanitizer --tool memcheck --leak-check full` trên GPU Tesla T4 cho cả hai chế độ:
- Suite `gpu_v5_pipeline`: 0 lỗi bộ nhớ, 0 byte rò rỉ.
- CLI production `site1/small` ở cả chế độ `sequential` và `dual`: 0 lỗi bộ nhớ, 0 byte rò rỉ.
- Bộ nhớ Device scratch và pinned buffer được giải phóng an toàn qua RAII của `V5DeviceOwner`.
