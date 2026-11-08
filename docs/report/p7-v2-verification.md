<!-- Authors: Le Ha Thanh Chuong (23120195). External source: none. -->

# P7-T04 V2 Verification

## Acceptance Status

Lượt chạy Colab Tesla T4 ngày **08/11/2026** đạt **7/7 cổng tự động**. V0, V1 và V2 khớp trạng thái ở cả 12 cấu hình. Cả chín cấu hình chuẩn đều xuất panorama và đạt đối chiếu hình học, RGB. Ba cấu hình challenge tái lập hành vi đã ghi nhận ở P6. Hai lượt Compute Sanitizer đạt 0 lỗi và 0 byte rò rỉ. P7-T04 đủ bằng chứng kỹ thuật để chuyển **Chờ review**.

## Environment and Provenance

| Hạng mục | Giá trị |
|---|---|
| Thời điểm bắt đầu | `2026-11-08T02:45:30.840708+00:00` (09:45:30 tại Việt Nam) |
| Runtime | Colab Tesla T4, driver `580.82.07`, Intel Xeon @ 2.00 GHz |
| Build | CUDA 13.0, nvcc `13.0.88`, `-arch=sm_75 -std=c++11 -O2 --fmad=false` |
| Compute Sanitizer | `2025.3.1.0` |
| Git base ghi trong ZIP đã chạy | `5c2fd04acb31482bc8aafeb05d1d23d7dd170c8d` |
| Commit GitHub khớp payload đã chạy | `bc1226f3be0271a0fbd1b78e7b6a8790218191d1` |
| Source snapshot SHA-256 | `8ccfc6e69213839ac40fdf784576426b3df2c76ca9110a19d6b51f61d6ca7c24` |
| Stitch executable SHA-256 | `fbe59caae407d269347a32a1aff71fdcf21de6dccd65add95e872faef60e9608` |
| Dataset manifest SHA-256 | `99fc712988075326a351d0bf580405e418bb28d24d56d4cc1b31505c480bdd9d` |
| Summary SHA-256 | `f91b8de35403830286e8a6c461cc389df28f73c832ce511e062fa33ef25e9a3b` |
| Notebook có output SHA-256 | `9b953bf0992417aa65802eafffe3c4e3bdedac6370e6ae8f80c6ffc7cb37ed5d` |

Notebook dùng ZIP cục bộ có thay đổi trên Git base. Khi kiểm toán lại, SHA-256 của **143/143 file** trong manifest source khớp từng byte với file tương ứng ở commit GitHub nêu trên. Notebook có output giữ nguyên source của 22 cell so với notebook trong repo và không có cell báo lỗi. Manifest dataset có 24 ảnh, đúng bốn cặp cuối kỳ. Lượt chạy kiểm tra hash từng ảnh trước khi build. Gói evidence chỉ giữ manifest, log và các PNG được xuất kèm, nên hậu kiểm xác minh được hash manifest và các PNG có trong gói.

Đã đối chiếu 12 JSON từng ca với summary, đọc lại CSV và stderr của 36 lệnh ma trận, kiểm tra H, seed, canvas và mã thoát. Tổng cộng có 49 bản ghi lệnh, gồm 38 exit 0 và 11 exit 1 dự kiến. Mười một exit 1 gồm sáu lượt challenge medium/large và năm ca CLI âm. Không có timeout.

## Synthetic Verification

Suite `gpu_v2_pipeline` chạy pipeline production trên sáu cặp có ground truth, gồm tịnh tiến và phối cảnh ở ba độ phân giải. H chiếu từ B sang A. Lưới 20×20 lấy điểm vào tập kiểm tra theo `H_gt`. Mỗi fixture tịnh tiến giữ 180 điểm, mỗi fixture phối cảnh giữ 165 điểm.

| Fixture | RMSE V2 (px) | Max V2 (px) |
|---|---:|---:|
| translation/small | 0.000007 | 0.000007 |
| translation/medium | 0.004717 | 0.016462 |
| translation/large | 0.000026 | 0.000026 |
| projective/small | 0.055234 | 0.143111 |
| projective/medium | 0.062536 | 0.208769 |
| projective/large | 0.100223 | 0.209017 |

Cả sáu cặp đạt **RMSE ≤ 0,5 px**, **Max ≤ 1 px**. Độ lệch chiếu V1/V2 bằng 0 trên các điểm kiểm tra, dưới ngưỡng **< 0,1 px**. Các số này mô tả độ chính xác trên lưới đã chọn của sáu fixture.

## Real Dataset Matrix

Mỗi phiên bản chạy một warm-up và năm lượt đo cho ca thành công. Các bảng lấy `Total_ms` trung bình của cùng phiên Colab T4. `Total_ms` bao gồm H2D, các stage, D2H và điều phối trong lượt đo. Đọc và ghi ảnh trên đĩa nằm ngoài khoảng đo. Speedup được tính bằng `Total_ms(baseline) / Total_ms(V2)`.

| Cấu hình | Trạng thái chung | Canvas | Offset | Max RGB | V0 (ms) | V1 (ms) | V2 (ms) | V2/V0 | V2/V1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| site1/small | Success | 2420×971 | (0,84) | 0 | 1394.491 | 580.765 | 71.989 | 19.37× | 8.07× |
| site1/medium | Success | 3692×1496 | (0,140) | 0 | 1956.997 | 511.651 | 70.165 | 27.89× | 7.29× |
| site1/large | Success | 7399×3028 | (0,313) | 0 | 5263.380 | 409.115 | 256.962 | 20.48× | 1.59× |
| site2/small | Success | 2558×1440 | (0,346) | 0 | 1287.837 | 927.032 | 21.368 | 60.27× | 43.38× |
| site2/medium | Success | 3818×2154 | (0,513) | 0 | 2016.688 | 865.613 | 46.652 | 43.23× | 18.55× |
| site2/large | Success | 7676×4348 | (0,1038) | 0 | 6147.658 | 504.819 | 83.702 | 73.45× | 6.03× |
| site3/small | Success | 2356×1241 | (0,312) | 0 | 1036.689 | 363.911 | 111.390 | 9.31× | 3.27× |
| site3/medium | Success | 3558×1791 | (0,414) | 0 | 1729.385 | 387.699 | 145.070 | 11.92× | 2.67× |
| site3/large | Success | 7008×3453 | (0,758) | 0 | 4546.782 | 409.051 | 252.438 | 18.01× | 1.62× |
| challenge/small | Success | 2835×1551 | (0,794) | 0 | 1318.220 | 400.092 | 373.691 | 3.53× | 1.07× |
| challenge/medium | NumericalFailure | — | — | — | — | — | — | — | — |
| challenge/large | NumericalFailure | — | — | — | — | — | — | — | — |

Bốn cặp tương ứng là `thanh-standard1`, `thanh-standard2`, `de-standard2` và `de-challenge1`. Với 10 ca thành công, log xác nhận cùng `Config` và seed 16. Độ lệch chiếu cực đại bằng 0 trên lưới 20×20 của từng đối chiếu V0/V1, V0/V2 và V1/V2. Canvas và offset khớp chính xác. Max RGB bằng 0 mức mỗi kênh, trong ngưỡng ≤ 1. Hash PNG theo từng ca khớp giữa ba phiên bản trong kết quả harness. Đã tính lại hash và so RGB trực tiếp trên bộ PNG challenge/small có trong gói.

Cả 10 panorama có diện tích lớn hơn ảnh A. Ví dụ `site2/large` đi từ ảnh 3840×2160 đến canvas 7676×4348, và CLI đọc lại PNG đúng kích thước. D2H trung bình của V2 nằm trong khoảng 0,545–7,631 ms ở các ca thành công.

## Performance Analysis

- Trên chín cấu hình chuẩn, V2 nhanh hơn V0 **9,31–73,45×** và V1 **1,59–43,38×**. Hai tỷ số lớn nhất đến từ hai ca khác nhau. `site2/large` đạt 73,45× so với V0, còn `site2/small` đạt 43,38× so với V1.
- S5 giảm thời gian ở cả 10 ca thành công. Với chín ca chuẩn, S5 V2 nằm trong khoảng **13,893–218,994 ms**. S5 vẫn có thời gian lớn nhất trong sáu stage ở cả 10 ca, chiếm **37,9–94,4%** tổng thời gian trên các ca chuẩn. Ở `site2/large`, S5 còn 31,750 ms và S6 đã gần bằng, 29,599 ms. Nên dùng NSYS/NCU của P7-T03 để kiểm tra xu hướng này trước khi chọn mục tiêu V3.
- V2 ở `site1/medium` có trung bình 70,165 ms, min 54,254 ms và max 95,942 ms trong năm lượt, với hệ số biến thiên khoảng 27,4% theo độ lệch chuẩn tổng thể. Hai lượt đầu chậm hơn rõ ở nhiều stage, trong đó S5 tăng khoảng 35 ms so với các lượt sau. Giữ đủ năm lượt trong báo cáo và dùng trace hoặc một phiên lặp để tìm nguyên nhân trước khi diễn giải chênh lệch theo độ phân giải.

## Challenge Pair

- **Small.** Cả ba phiên bản exit 0 và tạo canvas 2835×1551, offset (0,794). Ảnh cho thấy phần trần và lan can bị kéo lệch ở vùng ghép, với đường biên chồng ảnh còn thấy rõ. Ba PNG trùng byte trong gói, cùng SHA-256 `9936fb0b0ba235f10fb15c5a6c9aa8783d7e855a8fc56b9bb2a17b6ee5bf7b35`. Điều này xác nhận V2 tái lập ảnh lỗi của baseline trên fixture này. Log ghi 17 inlier cuối trên 114 match và 2.000 lượt RANSAC, chạm trần cấu hình. S5 V2 mất 365,956 ms, khoảng 97,9% thời gian end-to-end, nên speedup so với V1 chỉ 1,07×.
- **Medium và large.** Cả ba phiên bản exit 1 tại warm-up, báo `Error: [NumericalFailure] S6 warp_blend failed.` và không tạo panorama hoặc hàng timing. Đây là kết quả dự kiến của bài kiểm tra, phù hợp baseline P6. Log xác định được stage báo lỗi. Nhánh kiểm tra số học cụ thể bên trong S6 cần trace bổ sung nếu muốn kết luận về mẫu số phép chiếu.

## CLI, Regression and Memcheck

CSV production V2 có đúng 11 cột, các lượt đo và hai dòng `Average`/`Minimum` khớp dữ liệu thô. Sáu kiểm tra CLI đạt. Thiếu file, file không giải mã được, `--runs 0`, `--version 99` và fixture zero-match trả đúng `InputNotFound`, `ImageReadFailed`, `InvalidArgument`, `UnsupportedVersion`, `InsufficientMatches` với exit 1. Lượt mặc định không bật debug exit 0, xuất PNG và năm hàng timing.

| Kiểm tra | Kết quả |
|---|---|
| V0 | 14 suite, 45.284 checks |
| GPU | 11 suite, 50.517 checks |
| Suite tích hợp V2 trong hồi quy | 197 checks, 7 so sánh thành công gồm sáu fixture ground truth và site1/small, 5 lỗi dự kiến |
| Python | 9 suite, runner ghi 137 test, gồm 9 skip do thiếu notebook giữa kỳ trong source ZIP |
| Memcheck suite | Exit 0, 185 checks với sáu fixture tịnh tiến nhúng, site1/small và 5 lỗi dự kiến |
| Memcheck CLI V2 | Exit 0, site1/small với `--runs 1`; hash PNG khớp lượt CLI thường |

Cả hai lượt dùng `compute-sanitizer --tool memcheck --leak-check full --error-exitcode 99`. Hai log gốc đều có các dòng sau.

```text
========= LEAK SUMMARY: 0 bytes leaked in 0 allocations
========= ERROR SUMMARY: 0 errors
```

Phạm vi memcheck là hai target trong bảng. Dùng CSV từ lượt chạy thường cho so sánh hiệu năng.

## Reproduction and Review Handoff

1. Mở [notebook](../../Group16_P7_V2_Verification.ipynb) trên Colab, chọn **T4 GPU**. Để tái lập bản đã kiểm tra, chọn `SOURCE_MODE = "github"` và đặt `GIT_REF` bằng commit khớp payload ở trên. Có thể dùng `SOURCE_MODE = "zip"` với gói source cùng hash snapshot.
2. Dùng bộ dataset cuối kỳ có manifest phù hợp và sáu fixture đã ghi trong notebook. Lượt này sinh fixture từ `standard1_left.jpg` có SHA-256 `e9fbe7ecfed6344a36610fe50f2c6019bcd1525f4e217c033ed8ded4f90bf1e8`. Chọn **Run all**.
3. Đính kèm evidence ở PR từ `chuong/p7` vào `main`. Notebook ghi tên ZIP `Group16_P7_T04_Evidence_20261108T030144Z.zip`. Bản đã giải nén dùng trong hậu kiểm chứa `verification_summary.json`, `dataset_manifest.csv`, `cases/`, `logs/`, panorama challenge và notebook có output. Cập nhật **Xong** sau khi PR merge.

P7-T03 dùng các số liệu ở đây để đối chiếu benchmark, bổ sung NSYS/NCU và hoàn tất nhật ký APOD trước khi chốt hướng P8. [Task board](../task-board.md#p7---tối-ưu-và-profiling-v2) · [Kế hoạch cuối kỳ](../final-plan.md)
