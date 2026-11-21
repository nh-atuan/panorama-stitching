<!-- Authors: Le Ha Thanh Chuong (23120195), Tran Huu Kim Thanh (23120166). External source: none. -->

# P8-T04 — V3 Verification

## 1. Scope

P8-T04 kiểm tra tính tương đương V0–V3, contract CLI và an toàn bộ nhớ trên Tesla T4. Chương đã hoàn tất phần chuẩn bị suite, harness CLI, notebook và báo cáo. Thành tiếp nhận lượt chạy T4 và cập nhật bằng chứng sau khi tích hợp S5 V3 của T01 vào dispatcher T02. T03 phụ trách benchmark hiệu năng. [Phân công P8](../task-board.md)

## 2. Repository Baseline

| Hạng mục | Giá trị |
|---|---|
| Nhánh kiểm thử | `chuong/p8-v3-verification` |
| Nền nhánh | `932338e0c46f2f3250b6fbbad567f273597ff7c0` |
| Đăng ký suite | `813b1302a3565fd8c0290d7ac0dd7f5453cd1c39` |
| Hoàn thiện suite và harness CLI | `36119b0a72b46dd1dce4e39b4484bc44d00e063f` |
| Nhánh tích hợp T01 + T02 | `thanh/shared-v3-pipeline` (từ `main` tại `838e5b7`, đã có PR #37 và #38) |
| SHA production V3 dùng chung với Đế | `1cf86ad939fb821c3b2ee50fca47375ea8ae874a` |
| SHA checkout đã chạy V3 | `1cf86ad939fb821c3b2ee50fca47375ea8ae874a`. Notebook xác nhận `src/` và `scripts/build.py` khớp SHA production, checkout chứa commit `36119b0`. |

## 3. Environment

Mục tiêu là Google Colab Tesla T4, compute capability 7.5. Runner dùng `nvcc -arch=sm_75 -std=c++11 -O2 --fmad=false` qua `scripts/build.py` và `tests/run_tests.py`. Notebook ghi GPU, driver, compute capability, phiên bản compiler, runtime CUDA từ `cudaRuntimeGetVersion`, Compute Sanitizer và hash của binary. Repo dùng runner Python. [Hướng dẫn build và test](../../tests/README.md)

Trên máy cục bộ ở lượt chuẩn bị, CUDA 12.6/WSL biên dịch được object suite V3. Hồi quy V0 đạt 14 suite với 45.284 checks. GTX 1650 chạy được V1 với 53 checks và V2 production với 175 checks, gồm sáu synthetic P7, năm ca lỗi dự kiến và Max RGB bằng 0. Đây là kết quả V0–V2 của lượt chuẩn bị. T4 và V3 vẫn chờ lượt chạy trong notebook.

Lượt chuẩn bị notebook kiểm tra cấu trúc JSON, cú pháp tám cell Python, hash manifest và 18 file trong ZIP synthetic. Hai nhóm test Python của runner và harness đạt 30 test.

Lượt nghiệm thu chạy ngày 16/11/2026 trên Colab: Tesla T4, compute capability 7.5, driver 580.82.07, nvcc 13.0.88, CUDA runtime 13000, Compute Sanitizer 2025.3.1.0.

## 4. Dataset and Fixtures

- Dataset P7 gồm 24 ảnh thuộc bốn cặp `thanh-standard1`, `thanh-standard2`, `de-standard2` và `de-challenge1`. Mỗi cặp có ba độ phân giải `small` 1280×720, `medium` 1920×1080 và `large` 3840×2160. Notebook đối chiếu hash từng ảnh theo manifest, đồng thời ghim SHA-256 manifest `99fc712988075326a351d0bf580405e418bb28d24d56d4cc1b31505c480bdd9d`. [Dataset](../dataset.md) · [Provenance P7](p7-v2-verification.md#environment-and-provenance)
- Synthetic dùng đúng sáu cặp P7, mỗi cặp gồm hai PNG và một JSON H_gt theo chiều B→A. Cả 18 file đã được đối chiếu với hash lưu trong evidence P7. Runner dùng một `Config` cho mọi phiên bản trong từng ca. CLI đối chiếu `Config` đầy đủ trong stderr, gồm seed RANSAC 16.

## 5. Synthetic Verification

| Ca | Điểm Q theo P7 | V3 RMSE / Max / drift / canvas / RGB |
|---|---:|---|
| translation/small | 180 | 7.20e-06 / 7.20e-06 px / 4.56e-13, 0, 0 px / 1984×720 (0,0) / 0 |
| translation/medium | 180 | 0.00472 / 0.0165 px / 0, 0, 0 px / 2975×1082 (0,1) / 0 |
| translation/large | 180 | 2.62e-05 / 2.62e-05 px / 1.14e-12, 0, 0 px / 5952×2160 (0,0) / 0 |
| projective/small | 165 | 0.0552 / 0.143 px / 0, 0, 0 px / 1979×791 (0,35) / 0 |
| projective/medium | 165 | 0.0625 / 0.209 px / 0, 0, 0 px / 2968×1185 (0,52) / 0 |
| projective/large | 165 | 0.100 / 0.209 px / 0, 0, 0 px / 5937×2369 (0,104) / 0 |

Cột drift ghi độ lệch chiếu cực đại của V3 so với V0, V1, V2. Cả sáu ca đạt mọi ngưỡng. Sai số lớn nhất so với H_gt là RMSE 0,100 px và Max 0,209 px ở projective/large.

Suite dùng lưới 20×20 trên B và chọn Q bằng H_gt. Các ngưỡng là RMSE ≤ 0,5 px, Max ≤ 1 px, drift cực đại V3/V2 < 0,1 px, kích thước và offset canvas khớp chính xác, Max RGB ≤ 1 mức/kênh. Notebook thu từng dòng đo của suite vào `synthetic_results.json` và giữ stdout đầy đủ. [Suite V3](../../tests/gpu/test_gpu_v3_pipeline.cu) · [Synthetic P7](p7-v2-verification.md#synthetic-verification)

## 6. Real-Image Regression

| Cấu hình | V0/V1/V2 tại P7 | Trạng thái V0–V3, drift, canvas và RGB của lượt P8 |
|---|---|---|
| site1/small | Success cả ba | Success cả bốn; drift 0; 2420×971 (0,84); RGB 0 |
| site1/medium | Success cả ba | Success cả bốn; drift 0; 3692×1496 (0,140); RGB 0 |
| site1/large | Success cả ba | Success cả bốn; drift 0; 7399×3028 (0,313); RGB 0 |
| site2/small | Success cả ba | Success cả bốn; drift 0; 2558×1440 (0,346); RGB 0 |
| site2/medium | Success cả ba | Success cả bốn; drift 0; 3818×2154 (0,513); RGB 0 |
| site2/large | Success cả ba | Success cả bốn; drift 0; 7676×4348 (0,1038); RGB 0 |
| site3/small | Success cả ba | Success cả bốn; drift 0; 2356×1241 (0,312); RGB 0 |
| site3/medium | Success cả ba | Success cả bốn; drift 0; 3558×1791 (0,414); RGB 0 |
| site3/large | Success cả ba | Success cả bốn; drift 0; 7008×3453 (0,758); RGB 0 |
| challenge/small | Success cả ba | Success cả bốn; drift 0; 2835×1551 (0,794); RGB 0 |
| challenge/medium | NumericalFailure cả ba | NumericalFailure cả bốn, exit 1 ở S6, không có PNG và CSV |
| challenge/large | NumericalFailure cả ba | NumericalFailure cả bốn, exit 1 ở S6, không có PNG và CSV |

P7 ghi nhận 12/12 cấu hình khớp trạng thái. Cả 10 ca có panorama đều có Max RGB = 0 giữa V0/V1/V2. Lượt P8 chạy lại bốn phiên bản và chỉ so H, canvas, RGB ở ca thành công. Kết quả 12/12 cấu hình khớp trạng thái. Ở cả 10 ca có panorama, drift của V3 so với V0, V1, V2 bằng 0 và Max RGB bằng 0. Mọi canvas đều rộng hơn ảnh A, nên lượt này cũng kiểm tra được D2H của canvas mở rộng. Số đo từng ca nằm trong `cases/*.json` và `p8-v3-verification-run.md`. [Ma trận P7](p7-v2-verification.md#real-dataset-matrix)

## 7. Challenge Observations

Ở P7, challenge/small trả Success và sinh panorama lệch ở vùng trần và lan can. Challenge/medium và large trả `NumericalFailure` ở S6, exit 1, không có panorama hay CSV. Notebook ghi lại hành vi V3 và hiển thị bốn ảnh small để xem lại chất lượng ghép. Ở P8, V3 trả cùng trạng thái với V0–V2 ở cả ba mức. Panorama small của V3 trùng từng pixel với V0–V2. Ảnh B bị warp xoay và kéo xiên mạnh. Dầm trần nối tương đối liền, nhưng lan can ở vùng chồng lấn bị nhân đôi. Ảnh vẫn ghép lệch như ở P7, và đây không phải lỗi mới của V3. [Phân tích ảnh challenge P7](p7-v2-verification.md#challenge-pair)

## 8. CLI and CSV Verification

Notebook nhận header 11 cột từ T02, so với `version_columns(3)`, rồi xác nhận trên stdout production. Harness kiểm tra số lượt, tên và thứ tự cột, trường timing, `Average`, `Minimum`, CLI âm, và giải mã PNG của một canvas mở rộng. Lượt runner benchmark dùng để xác nhận parser xử lý được output của CLI. T02 dùng header `Run_Index,S1_V3_ms,S2_V3_ms,S3_V3_ms,S4_V3_ms,S5_V3_ms,S6_V3_ms,Total_ms,H2D_ms,D2H_ms,Total_Kernel_ms`, khớp `version_columns(3)`. Trên T4, `verify_v3_cli.py` trả exit 0. `run_benchmark.py --versions 3 --runs 2 --include-challenge` cũng trả exit 0, và `failures.csv` chỉ chứa challenge medium và large với `NumericalFailure`. Số đo thời gian của lượt này chỉ dùng để kiểm tra contract, không dùng cho bảng hiệu năng của P8-T03. [Harness CLI](../../scripts/verify_v3_cli.py) · [Parser benchmark](../../scripts/run_benchmark.py)

## 9. Compute Sanitizer

| Target | Exit | Errors | Leaked bytes | Bằng chứng |
|---|---:|---:|---:|---|
| Suite production V3 | 0 | 0 | 0 (0 allocations) | `logs/memcheck_suite.*` |
| CLI `site1/small --version 3 --runs 1` | 0 | 0 | 0 (0 allocations) | `logs/memcheck_cli.*` |

Cả hai lượt đạt: exit 0, có đủ dòng `ERROR SUMMARY` và `LEAK SUMMARY`, và mọi chỉ số bằng 0. Gói evidence giữ stdout, stderr, argv, exit code, hash binary và SHA checkout. [Hướng dẫn T4](../../tests/README.md#kiểm-thử-tích-hợp-v3-p8-t04)

## 10. Reproduction

Mở [notebook P8](../../experiments/Group16_P8_V3_Verification.ipynb), chọn T4, điền `PRODUCTION_SHA`, `VERIFICATION_REF` và `T02_CSV_HEADER`. Để trống `DATASET_INPUT` và `SYNTHETIC_INPUT` để notebook tải dữ liệu từ Drive. Notebook ưu tiên `dataset.zip` trong thư mục cuối kỳ, rồi thử chuẩn bị lại từ ảnh gốc theo quy trình P7 nếu cần. Synthetic được sinh từ ảnh nguồn của P7. Nếu Drive giới hạn tải hoặc dữ liệu tái tạo lệch hash, điền đường dẫn ZIP hoặc thư mục đúng bộ P7 vào ô cấu hình. Các lệnh chính tương đương:

```bash
python3 scripts/build.py --compiler nvcc --require-t4 --out-dir build
python3 tests/run_tests.py --compiler nvcc --group gpu --suite gpu_v3_pipeline \
  --require-t4 --v3-synthetic-dir /path/to/synthetic --v3-dataset-dir /path/to/dataset
python3 scripts/verify_v3_cli.py --stitch build/stitch --dataset /path/to/dataset \
  --out results/p8-v3-cli-smoke --require-t4
python3 scripts/run_benchmark.py --stitch build/stitch --dataset /path/to/dataset \
  --out results/p8-v3-benchmark-contract --versions 3 --runs 2 --include-challenge
compute-sanitizer --tool memcheck --leak-check full --error-exitcode 99 \
  ./build/tests_gpu/gpu_v3_pipeline
compute-sanitizer --tool memcheck --leak-check full --error-exitcode 99 \
  ./build/stitch /path/to/dataset/site1/small_left.jpg /path/to/dataset/site1/small_right.jpg \
  build/p8-v3-memcheck.png --version 3 --runs 1 --debug
```

Notebook xuất `Group16_V3_P8-T04_TeslaT4_Evidence_<checkout>_<UTC>.zip` và SHA-256. Gói chứa `environment.json`, `dataset_manifest.csv`, `fixture_manifest.json`, JSON từng ca, log thô và ảnh challenge. Gói của lượt nghiệm thu là `Group16_V3_P8-T04_TeslaT4_Evidence_1cf86ad9_20261116T053455Z.zip`, SHA-256 `c385c7bfb21175b4f6d4d6414d87e0eb449a24ea17b4224c537b0412be3dabcd`, được lưu cùng file `.sha256` trong `v3/benchmark/` của [thư mục kết quả chung](https://drive.google.com/drive/folders/1uJ-4_kgVONvIt5NQIPzdEWTIPrg8Sue1?usp=sharing) theo [quy ước lưu kết quả](../results-guide.md). Bản tải lại từ Drive có cùng SHA-256 với bản sinh trên Colab.

## 11. Known Limitations

Lượt nghiệm thu không chạy notebook nguyên trạng ở ba điểm. Các điểm này không đổi ngưỡng hay cổng kiểm tra nào:

- Cell "Run the Production Matrix" ghi `evidence/cases/<site>_<size>.json`, nhưng không cell nào tạo thư mục `cases`, và `write_json` không tự tạo thư mục cha. Lượt chạy đầu dừng ở site1/small vì lỗi này. Lượt chạy chính thức tạo thư mục trước khi gọi cell. Sau lượt chạy, cell này được thêm lệnh `(EVIDENCE / "cases").mkdir(exist_ok=True)` để notebook chạy được nguyên trạng. Thay đổi không đụng tới `src/` và `scripts/build.py`, nên cổng so khớp SHA production vẫn giữ nguyên.
- Lần tải dataset thứ hai bị gdown chặn vì Drive giới hạn lượt truy cập. Lượt chính thức dùng `DATASET_INPUT` trỏ tới `dataset.zip` và `SYNTHETIC_SOURCE` trỏ tới `raw/tuan/standard1_left.jpg`, cả hai đã tải ở lần đầu trong cùng phiên. Notebook vẫn kiểm tra SHA-256 của manifest, ảnh nguồn và 18 file synthetic, và tất cả đều khớp P7.
- Ô `CHALLENGE_SMALL_REVIEW` được điền bằng nhận xét ở mục 7 trước khi chạy cell tổng hợp.

## 12. Final Acceptance Summary

| Kiểm tra | Trạng thái |
|---|---|
| Suite V3 được đăng ký, harness và notebook đã chuẩn bị | PASS |
| Sáu synthetic và 12 cấu hình thật qua V3 | PASS |
| CLI, CSV, runner và canvas D2H qua V3 | PASS |
| Đánh giá challenge/small | PASS |
| Hai lượt memcheck T4, SHA production và gói evidence | PASS |

**Verdict — READY FOR REVIEW**
