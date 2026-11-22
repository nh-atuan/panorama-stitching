<!-- Authors: Nguyen Ho Anh Tuan (23120185). External source: none. -->

# P11-T02 — Nghiệm thu hồi quy toàn diện và đóng băng mã nguồn `src/`

## 1. Phạm vi và mốc mã nguồn

Báo cáo ghi nhận lượt chạy nghiệm thu tổng thể trên Google Colab GPU Tesla T4 cho nhánh `tuan/p11` sau khi hoàn tất tái cấu trúc và chuẩn hóa repo (`P11-T01`), làm cơ sở đóng băng mã nguồn `src/` trước các giai đoạn quay và biên tập video (P12–P13).

| Hạng mục | Giá trị |
|---|---|
| Nhánh kiểm chứng | `tuan/p11` |
| Commit SHA kiểm chứng | `f2837a85b770e6c8bb2eba1bb6de7aee7fa23eb7` |
| GPU / Driver | NVIDIA Tesla T4 (15360 MiB), Driver `580.82.07` |
| CUDA Compiler | `nvcc` release 13.0, V13.0.88 (`-arch=sm_75 -std=c++11 -O2 --fmad=false -Werror`) |
| Hệ điều hành / CPU | Linux `6.6.159+` x86_64, Intel Xeon @ 2.00 GHz |
| Compute Sanitizer | NVIDIA Compute Sanitizer (CUDA 13.0) |

## 2. Kết quả biên dịch và bộ kiểm thử tự động

| Hạng mục | Lệnh thực thi | Kết quả |
|---|---|---|
| Biên dịch chương trình chính (`V0`–`V5`) | `python3 scripts/build.py --compiler nvcc --require-t4` | **PASS** (`BUILD_RC=0`, tạo `build/stitch` với `-DPANORAMA_V5_IMAGE_API_AVAILABLE`) |
| Bộ kiểm thử V0 (CPU tuần tự) | `python3 tests/run_tests.py --compiler nvcc --require-t4` | **PASS** — `14` suite, `45.284` checks |
| Bộ kiểm thử GPU (`V1`–`V5`) | `python3 tests/run_tests.py --compiler nvcc --require-t4` | **PASS** — `16` suite, `69.336` checks (gồm `gpu_s1`–`gpu_s6`, `gpu_blur`, `gpu_reference`, `gpu_v2_s5`, `gpu_v3_s5`, `gpu_v4_s6`, `gpu_pipeline`, `gpu_v2_pipeline`–`gpu_v5_pipeline`; Max RGB error = 0 trên toàn bộ ca ghép, drift V5 vs V4 = 0 px) |
| Bộ kiểm thử Python | `python3 tests/run_tests.py --compiler nvcc --require-t4` | **PASS** — `15` suite, `193` tests (gồm `test_midterm_notebook.py` sau khi chuyển vị trí sang `notebooks/`) |
| Kiểm tra chính sách & header mã nguồn | Quét 178 file trong `src/`, `tests/`, `scripts/` | **PASS** — 0 file thiếu `Authors:` / `External source:`, 0 từ khóa song song bị cấm trong `src/v0/`, 0 thư viện GPU ngoài phạm vi trong `src/` |

## 3. Kiểm tra an toàn bộ nhớ (`compute-sanitizer`)

Chạy `compute-sanitizer --tool memcheck --leak-check full --error-exitcode 99` trên Tesla T4:

| Target | Exit code | Kết quả bộ nhớ |
|---|---:|---|
| `./build/tests_gpu/gpu_v4_pipeline` (603 checks, 6 panoramas, 5 ca lỗi) | `0` | `0 bytes leaked in 0 allocations`, `0 errors` |
| `./build/tests_gpu/gpu_v5_pipeline` (436 checks, 6 panoramas, 5 ca lỗi) | `0` | `0 bytes leaked in 0 allocations`, `0 errors` |

## 4. Kết luận

Toàn bộ `14` suite V0 (`45.284` checks), `16` suite GPU V1–V5 (`69.336` checks), `15` suite Python (`193` tests) và hai lượt `compute-sanitizer` đều đạt sạch lỗi trên Google Colab GPU Tesla T4. Mã nguồn `src/` đủ điều kiện đóng băng phục vụ hoàn thiện báo cáo, slide và quay demo ở P12–P14.
