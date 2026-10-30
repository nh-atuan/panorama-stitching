# S6 CUDA Verification on Colab

Người soạn: Lê Hà Thanh Chương (23120195). Cập nhật: 30/10/2026. Phạm vi: P5-T12/P5-T13.

## Files to Prepare

Mở [`Group16_S6_CUDA_Verification.ipynb`](../Group16_S6_CUDA_Verification.ipynb) trên Colab. Notebook này dành riêng cho kiểm chứng S6; không thay notebook báo cáo giữa kỳ và không gọi scaffold V1 để giả lập kết quả ghép ảnh GPU.

| File | Bạn cần làm |
|---|---|
| `Group16_S6_CUDA_Verification.ipynb` | Trên Colab chọn File → Upload notebook, mở file này |
| `Group16_S6_Source.zip` | Upload khi cell Source Snapshot hỏi, hoặc tải sẵn vào `/content` bằng panel Files |
| `Group16_support.zip` | Notebook tự tải từ Drive nhóm; chỉ cần upload nếu tải tự động lỗi |

ZIP source đã được tạo tại `build/Group16_S6_Source.zip`. Để tạo lại từ code hiện tại, chạy trong thư mục gốc repo:

```powershell
python scripts/package_s6_verification.py
```

Gói chứa `src/`, `scripts/`, `tests/` cùng `source_manifest.json`, giữ nguyên thư mục con. Các file quan trọng gồm S6 CUDA, S6 V0, common headers, `main.cu`, build script, runner V0 và test GPU. Không cần tự chọn từng file `.cu/.h` để upload.

Không dùng `src.zip` cũ trong `Group16_Midterm/`: gói đó chưa chứa S6 CUDA mới. Không cần upload `raw/`, `p3-t04/`, `build/`, PDF hoặc notebook giữa kỳ. ZIP hỗ trợ giữa kỳ có script/test cũ, nhưng notebook mới **chỉ giải nén `dataset/`** từ đó.

## Run All on Tesla T4

1. Mở notebook trên [Google Colab](https://colab.research.google.com/).
2. Chọn Runtime → Change runtime type → T4 GPU → Save.
3. Giữ các thiết lập mặc định: `REQUIRE_T4 = True`, `RUN_FULL_V0_TESTS = True`, `RUN_MEMCHECK = True`, bốn cặp và ba kích thước.
4. Chọn Runtime → Run all. Khi hộp upload xuất hiện, chọn `Group16_S6_Source.zip`.
5. Chờ dataset tải từ [file hỗ trợ của nhóm](https://drive.google.com/file/d/1Jx6o5kUnpvxXVEHfYKD1GBvZMTbSeEGu/view?usp=sharing). Nếu tải lỗi, upload chính file ZIP này khi được hỏi.
6. Chờ các cell chạy lần lượt; không chạy tác vụ GPU khác trong phiên kiểm chứng.

Có thể upload sẵn cả hai ZIP vào `/content` trước Run all để tránh hộp upload giữa chừng. Tên file cần đúng như bảng trên. Nếu helper/notebook và ZIP source không cùng phiên bản, cell Source Snapshot sẽ dừng; dùng lại đúng cặp notebook/ZIP đã tạo cùng nhau.

## Verification Sequence

| Phần | Kiểm tra gì | Bằng chứng |
|---|---|---|
| Runtime | GPU thực sự là T4, nvcc, driver, CPU/Python | Bảng môi trường, `environment.json` |
| Source / Dataset | Hash từng file source và 24 ảnh | Source snapshot, manifest và hash |
| Build | `stitch` và `test_gpu_s6`, target `sm_75` | Lệnh và log compiler |
| V0 regression | Mọi suite V0; một cặp thật với mặc định 5 runs | PASS, CSV tám cột, Average/Minimum, PNG hợp lệ |
| S6 fixtures | Oracle tính tay, so V0/GPU, bounds, blending, lỗi/OOM | Checks/comparisons/max RGB error từ binary thật |
| Real pairs | 4 cặp × 3 kích thước, dùng cùng H cho CPU/GPU | Bảng 12 trường hợp, H và hash input từng case |
| Gallery | A/B và panorama V0 reference | Hình tham khảo có nhãn đúng |
| Memcheck | Fixture và site2/large mặc định | Target PASS, zero-error summary, leak check |
| Summary | Các gate, hash sau kiểm tra và gói evidence | READY hoặc INCOMPLETE, ZIP tải về |

H được lấy từ `stitch --version 0 --debug` chạy trên chính phiên Colab; không lấy H từ log cũ trên máy. C++ test gọi S6 CPU/GPU với cùng H và input. GPU panorama được đọc lại bên trong test để so mọi pixel; CLI test hiện không xuất file GPU panorama, nên gallery chỉ hiển thị V0 reference.

Tolerance giữ theo source: geometry/status khớp chính xác, max absolute RGB error không quá `Tols::max_channel_error = 1`; oracle giải tích và tính tái lập phải khớp chính xác. Notebook không chọn tolerance theo số đo thu được.

## Memcheck and Failure Handling

Notebook tự tìm `compute-sanitizer` trong PATH và thư mục CUDA. Lệnh chính:

```bash
compute-sanitizer --tool memcheck --leak-check full --error-exitcode 99 ./build/test_gpu_s6
```

Cell memcheck cũng chạy ca site2/large với H đã ghi ở phần Real Image Pairs. Có thể bổ sung case trong `MEMCHECK_REAL_CASES`; không cần chép lại hệ số H bằng tay.

- `PASS`: target test đạt, exit code 0 và log sanitizer không có lỗi/leak.
- `FAIL`: xem hai file stdout/stderr tương ứng trong `results/logs/`.
- `UNAVAILABLE`: không tìm thấy công cụ; cần cài Compute Sanitizer phù hợp CUDA của runtime rồi chạy lại cell memcheck.
- `SKIPPED`: người chạy tắt memcheck; không đủ điều kiện READY.

Không dựa duy nhất vào exit code. Lỗi khởi tạo debugger hoặc thông báo không hỗ trợ thiết bị không phải kết quả memcheck sạch. Notebook giữ trạng thái INCOMPLETE trong các trường hợp đó, kể cả khi công cụ trả code 0. Nếu build/test lỗi ở cell trước, sửa nguyên nhân rồi chạy lại từ cell phù hợp; không sửa output hay bỏ assert.

Nếu chọn chế độ V0 nhanh (`RUN_FULL_V0_TESTS = False`) hoặc giảm tập cặp/kích thước, vẫn có thể xem kết quả phát triển nhưng summary không xác nhận bộ kiểm chứng đầy đủ.

## Save Evidence for Review

Sau khi chạy:

1. Tải ZIP bằng chứng ở cell Download. Nếu trình duyệt chặn tải tự động, mở panel Files và tải file có hậu tố `-evidence.zip` trong `/content`.
2. Chọn File → Download → Download .ipynb để lưu notebook có output.
3. Giữ cả hai file để review PR; không commit ảnh dataset hoặc build/output thực nghiệm vào repo.

ZIP bằng chứng chứa môi trường, source snapshot, mọi command/log, H của từng case, bảng real-pair/memcheck và `verification_summary.json`. Dataset và các panorama PNG không được đóng gói lại để tránh ZIP lớn; hình gallery vẫn được lưu trong notebook có output.

READY chỉ là bằng chứng đủ điều kiện review trên T4. Task còn cần review/merge theo kế hoạch nhóm. Việc ghép S6 thật vào pipeline V1, resize pinned output theo canvas và đo speedup toàn pipeline thuộc P6.

## Validation Record

Bản trong Git được giữ không có output. Kiểm tra local trước đó dùng WSL/GTX 1650 để kiểm tra luồng notebook, không thay thế Colab T4.

Lượt Run all trên Colab Tesla T4 ngày 30/10/2026 đã đạt tất cả gate, gồm 13 suite V0, fixture S6, 12 case thật và hai lượt memcheck. Chi tiết, hash source và giới hạn kết luận được ghi trong [báo cáo nghiệm thu T4](report/p5-s6-cuda-verification.md). Notebook có output gốc và bundle evidence được giữ ngoài Git. Khi thay source hoặc tham số, cần tạo lại gói và kiểm chứng lại; không dùng log cũ để nghiệm thu code mới.

Tài liệu API: [Colab FAQ](https://research.google.com/colaboratory/faq.html), [NVIDIA Compute Sanitizer](https://docs.nvidia.com/compute-sanitizer/ComputeSanitizer/index.html), [gdown](https://github.com/wkentaro/gdown).
