<!-- Authors: Le Ha Thanh Chuong (23120195). External source: none. -->

# P7-T04 V2 Verification

## Acceptance Status

Workspace `chuong/p7` đã tích hợp pipeline P7-T02 và CLI `--version 2` trên Git base `5c2fd04acb31482bc8aafeb05d1d23d7dd170c8d`. Gói source giữ hash của từng file, hash snapshot và trạng thái Git để định danh chính xác bản chạy. Bảng dưới đây dành cho lần nghiệm thu Colab Tesla T4.

## Local Integration Check

Build `sm_75` với nvcc 12.6.85 trên GTX 1650 đạt. Suite production V2 đạt 175 checks, gồm sáu cặp synthetic và năm ca lỗi dự kiến. Suite V1 đạt 53 checks. Sai số RGB lớn nhất trong hai suite bằng 0.

CLI V0/V1/V2 đạt ở ba cấu hình `thanh-standard1`, mỗi cấu hình chạy năm lượt đo. Độ lệch chiếu lớn nhất trên lưới kiểm tra và sai số RGB lớn nhất đều bằng 0 cho cả ba đối chiếu phiên bản. Cả ba canvas có diện tích lớn hơn ảnh A và ảnh PNG đọc lại khớp hình học do S6 công bố.

| Cấu hình | Canvas chung V0/V1/V2 | Offset chung | Max RGB |
|---|---:|---:|---:|
| site1/small | 2420×971 | (0,84) | 0 |
| site1/medium | 3692×1496 | (0,140) | 0 |
| site1/large | 7399×3028 | (0,313) | 0 |

Sáu kiểm tra CLI đạt, gồm `InputNotFound`, `ImageReadFailed`, `InvalidArgument`, `UnsupportedVersion`, `InsufficientMatches` và chạy thành công với mặc định năm lượt đo. CSV V2, `Average` và `Minimum` đạt kiểm tra. Log cục bộ lưu ở `build/p7_local_production_r9c2q9rf/` và `build/p7_integrated_suite.log`. Ma trận đầy đủ, số đo chính thức và memcheck được ghi từ phiên T4.

## Reproduction on Colab

1. Mở [notebook](../../Group16_P7_V2_Verification.ipynb) và chọn nguồn ở cell `Verification Settings`. Mặc định `auto` thử GitHub public tại `refs/heads/chuong/p7` rồi yêu cầu ZIP nếu ref chưa có đủ file. Chọn `github` và điền SHA để chạy riêng một snapshot đã publish. Chọn `zip` để chạy bản tích hợp trong workspace. Khi cần tạo lại gói source, dùng lệnh sau.

   ```bash
   python scripts/package_s6_verification.py --output build/Group16_P7_Source.zip
   ```

2. Mở notebook trên Colab, chọn **T4 GPU** và **Run all**. Notebook ưu tiên `dataset.zip` có sẵn, sau đó mới tải và chuẩn bị dataset chính thức từ Drive. Nếu cần, cung cấp `synthetic.zip` có cả hai thư mục `translation/`, `projective/`, hoặc ảnh gốc dùng để sinh sáu fixture.
3. Tải `Group16_P7_T04_Evidence_<timestamp>.zip`. Đối chiếu gallery challenge với trạng thái trong báo cáo sinh tự động. Thay bảng chờ bên dưới bằng báo cáo trong ZIP sau khi xác nhận nguồn và log, rồi ghi link ZIP trên task board.

Có thể chạy harness trực tiếp từ repo đã tích hợp trên Colab T4.

```bash
python3 scripts/verify_v2_dataset.py --dataset dataset \
  --synthetic-dir results/synthetic --out results/p7-t04-acceptance
```

Harness build `sm_75` với `-O2 --fmad=false`, xác minh 24 ảnh theo manifest và giữ argv, stdout, stderr cùng exit code của từng lệnh. Mỗi ca thành công dùng 5 lượt đo. Canvas và offset phải khớp chính xác, độ lệch chiếu B→A phải dưới 0,1 px và RGB lệch tối đa 1 mức mỗi kênh. CSV V0/V1 dùng schema hiện hành. V2 được kiểm tra theo đúng schema nghiệm thu `Run_Index,S1_ms,S2_ms,S3_ms,S4_ms,S5_ms,S6_ms,H2D_ms,D2H_ms,Total_Kernel_ms,Total_ms`. Nếu dispatcher V2 xuất schema khác, kết quả ghi lỗi hợp đồng và giữ CSV gốc để đối chiếu.

## Real Dataset Matrix

| Cấu hình | Cặp ảnh | Status V0 / V1 / V2 | Canvas | Offset | Max RGB | Total trung bình (ms) |
|---|---|---|---|---|---|---|
| site1/small | thanh-standard1 | Chưa chạy | — | — | — | — |
| site1/medium | thanh-standard1 | Chưa chạy | — | — | — | — |
| site1/large | thanh-standard1 | Chưa chạy | — | — | — | — |
| site2/small | thanh-standard2 | Chưa chạy | — | — | — | — |
| site2/medium | thanh-standard2 | Chưa chạy | — | — | — | — |
| site2/large | thanh-standard2 | Chưa chạy | — | — | — | — |
| site3/small | de-standard2 | Chưa chạy | — | — | — | — |
| site3/medium | de-standard2 | Chưa chạy | — | — | — | — |
| site3/large | de-standard2 | Chưa chạy | — | — | — | — |
| challenge/small | de-challenge1 | Chưa chạy | — | — | — | — |
| challenge/medium | de-challenge1 | Chưa chạy | — | — | — | — |
| challenge/large | de-challenge1 | Chưa chạy | — | — | — | — |

## Challenge Pair and Memory Safety

Baseline P6 ghi nhận `de-challenge1` small sinh panorama lệch, medium và large báo `NumericalFailure`. Hành vi của V2 sẽ được đối chiếu từ log và gallery của lượt nghiệm thu. [Baseline P6](../task-board.md#p6---ghép-pipeline-benchmark-và-profiling-v1)

Hai lượt memcheck chờ phiên Colab T4. Báo cáo sinh tự động sẽ chép nguyên các dòng `ERROR SUMMARY` và `LEAK SUMMARY` từ `logs/memcheck_suite.*` và `logs/memcheck_cli.*`, kèm mã thoát và thông tin T4, driver, toolkit, thời điểm chạy, Git base và hash source.
