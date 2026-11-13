<!-- Authors: Le Ha Thanh Chuong (23120195). External source: none. -->

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
| SHA production V3 dùng chung với Đế | **BLOCKED**. Các ref đã kiểm tra chưa có T01/T02 tích hợp. |
| SHA checkout đã chạy V3 | **BLOCKED**. Notebook sẽ ghi SHA thực tế và kiểm tra source chương trình cùng script build khớp SHA production. |

## 3. Environment

Mục tiêu là Google Colab Tesla T4, compute capability 7.5. Runner dùng `nvcc -arch=sm_75 -std=c++11 -O2 --fmad=false` qua `scripts/build.py` và `tests/run_tests.py`. Notebook ghi GPU, driver, compute capability, phiên bản compiler, runtime CUDA từ `cudaRuntimeGetVersion`, Compute Sanitizer và hash của binary. Repo dùng runner Python. [Hướng dẫn build và test](../../tests/README.md)

Trên máy cục bộ ở lượt chuẩn bị, CUDA 12.6/WSL biên dịch được object suite V3. Hồi quy V0 đạt 14 suite với 45.284 checks. GTX 1650 chạy được V1 với 53 checks và V2 production với 175 checks, gồm sáu synthetic P7, năm ca lỗi dự kiến và Max RGB bằng 0. Đây là kết quả V0–V2 của lượt chuẩn bị. T4 và V3 vẫn chờ lượt chạy trong notebook.

Lượt chuẩn bị notebook kiểm tra cấu trúc JSON, cú pháp tám cell Python, hash manifest và 18 file trong ZIP synthetic. Hai nhóm test Python của runner và harness đạt 30 test.

## 4. Dataset and Fixtures

- Dataset P7 gồm 24 ảnh thuộc bốn cặp `thanh-standard1`, `thanh-standard2`, `de-standard2` và `de-challenge1`. Mỗi cặp có ba độ phân giải `small` 1280×720, `medium` 1920×1080 và `large` 3840×2160. Notebook đối chiếu hash từng ảnh theo manifest, đồng thời ghim SHA-256 manifest `99fc712988075326a351d0bf580405e418bb28d24d56d4cc1b31505c480bdd9d`. [Dataset](../dataset.md) · [Provenance P7](p7-v2-verification.md#environment-and-provenance)
- Synthetic dùng đúng sáu cặp P7, mỗi cặp gồm hai PNG và một JSON H_gt theo chiều B→A. Cả 18 file đã được đối chiếu với hash lưu trong evidence P7. Runner dùng một `Config` cho mọi phiên bản trong từng ca. CLI đối chiếu `Config` đầy đủ trong stderr, gồm seed RANSAC 16.

## 5. Synthetic Verification

| Ca | Điểm Q theo P7 | V3 RMSE / Max / drift / canvas / RGB |
|---|---:|---|
| translation/small | 180 | BLOCKED |
| translation/medium | 180 | BLOCKED |
| translation/large | 180 | BLOCKED |
| projective/small | 165 | BLOCKED |
| projective/medium | 165 | BLOCKED |
| projective/large | 165 | BLOCKED |

Suite dùng lưới 20×20 trên B và chọn Q bằng H_gt. Các ngưỡng là RMSE ≤ 0,5 px, Max ≤ 1 px, drift cực đại V3/V2 < 0,1 px, kích thước và offset canvas khớp chính xác, Max RGB ≤ 1 mức/kênh. Notebook thu từng dòng đo của suite vào `synthetic_results.json` và giữ stdout đầy đủ. [Suite V3](../../tests/gpu/test_gpu_v3_pipeline.cu) · [Synthetic P7](p7-v2-verification.md#synthetic-verification)

## 6. Real-Image Regression

| Cấu hình | V0/V1/V2 tại P7 | Trạng thái V0–V3, drift, canvas và RGB của lượt P8 |
|---|---|---|
| site1/small | Success cả ba | BLOCKED |
| site1/medium | Success cả ba | BLOCKED |
| site1/large | Success cả ba | BLOCKED |
| site2/small | Success cả ba | BLOCKED |
| site2/medium | Success cả ba | BLOCKED |
| site2/large | Success cả ba | BLOCKED |
| site3/small | Success cả ba | BLOCKED |
| site3/medium | Success cả ba | BLOCKED |
| site3/large | Success cả ba | BLOCKED |
| challenge/small | Success cả ba | BLOCKED |
| challenge/medium | NumericalFailure cả ba | BLOCKED |
| challenge/large | NumericalFailure cả ba | BLOCKED |

P7 ghi nhận 12/12 cấu hình khớp trạng thái. Cả 10 ca có panorama đều có Max RGB = 0 giữa V0/V1/V2. Lượt P8 sẽ chạy lại bốn phiên bản, chỉ so H, canvas và RGB ở ca thành công. Số đo từng ca nằm trong `cases/*.json` và `p8-v3-verification-run.md`. [Ma trận P7](p7-v2-verification.md#real-dataset-matrix)

## 7. Challenge Observations

Ở P7, challenge/small trả Success và sinh panorama lệch ở vùng trần và lan can. Challenge/medium và large trả `NumericalFailure` ở S6, exit 1, không có panorama hay CSV. Notebook ghi lại hành vi V3 và hiển thị bốn ảnh small để Chương xem lại chất lượng ghép. Đánh giá chất lượng V3 hiện **BLOCKED**. [Phân tích ảnh challenge P7](p7-v2-verification.md#challenge-pair)

## 8. CLI and CSV Verification

Notebook nhận header 11 cột từ T02, so với `version_columns(3)`, rồi xác nhận trên stdout production. Harness kiểm tra số lượt, tên và thứ tự cột, trường timing, `Average`, `Minimum`, CLI âm, và giải mã PNG của một canvas mở rộng. Lượt runner benchmark dùng để xác nhận parser xử lý được output của CLI. Contract production hiện **BLOCKED**. [Harness CLI](../../scripts/verify_v3_cli.py) · [Parser benchmark](../../scripts/run_benchmark.py)

## 9. Compute Sanitizer

| Target | Exit | Errors | Leaked bytes | Bằng chứng dự kiến |
|---|---:|---:|---:|---|
| Suite production V3 | — | — | — | `logs/memcheck_suite.*` |
| CLI `site1/small --version 3 --runs 1` | — | — | — | `logs/memcheck_cli.*` |

Hai lượt **BLOCKED**. Kết quả cần exit 0 và đầy đủ tổng kết lỗi và rò rỉ, mỗi chỉ số bằng 0. Gói evidence giữ stdout, stderr, argv, exit code, hash binary và SHA checkout. [Hướng dẫn T4](../../tests/README.md#kiểm-thử-tích-hợp-v3-p8-t04)

## 10. Reproduction

Mở [notebook P8](../../Group16_P8_V3_Verification.ipynb), chọn T4, điền `PRODUCTION_SHA`, `VERIFICATION_REF` và `T02_CSV_HEADER`. Để trống `DATASET_INPUT` và `SYNTHETIC_INPUT` để notebook tải dữ liệu từ Drive. Notebook ưu tiên `dataset.zip` trong thư mục cuối kỳ, rồi thử chuẩn bị lại từ ảnh gốc theo quy trình P7 nếu cần. Synthetic được sinh từ ảnh nguồn của P7. Nếu Drive giới hạn tải hoặc dữ liệu tái tạo lệch hash, điền đường dẫn ZIP hoặc thư mục đúng bộ P7 vào ô cấu hình. Các lệnh chính tương đương:

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

Notebook xuất `Group16_V3_P8-T04_TeslaT4_Evidence_<checkout>_<UTC>.zip` và SHA-256. Gói chứa `environment.json`, `dataset_manifest.csv`, `fixture_manifest.json`, JSON từng ca, log thô và ảnh challenge. Vị trí Drive và checksum sẽ được bổ sung khi có gói thực tế.

## 11. Known Limitations

Thành sẽ xác nhận SHA production và schema CSV, chạy notebook trên Colab T4 và ghi nhận chất lượng ảnh challenge/small. Chưa có log V3, ảnh đầu ra V3 hoặc evidence ZIP. PR bàn giao có thể được review ở trạng thái draft trong khi chờ bằng chứng nghiệm thu.

## 12. Final Acceptance Summary

| Kiểm tra | Trạng thái |
|---|---|
| Suite V3 được đăng ký, harness và notebook đã chuẩn bị | PASS |
| Sáu synthetic và 12 cấu hình thật qua V3 | BLOCKED |
| CLI, CSV, runner và canvas D2H qua V3 | BLOCKED |
| Đánh giá challenge/small | BLOCKED |
| Hai lượt memcheck T4, SHA production và gói evidence | BLOCKED |

**Verdict — BLOCKED — MISSING REQUIRED EVIDENCE**
