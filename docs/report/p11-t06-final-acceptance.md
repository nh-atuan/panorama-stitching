<!-- Authors: Le Ha Thanh Chuong (23120195). External source: returned Colab artifacts and repository reports cited below. -->

# P11-T06 — Colab T4 Notebook and PDF Handoff

PR bàn giao: [#59](https://github.com/nh-atuan/panorama-stitching/pull/59), base `main`, chưa merge.

## 1. Kết luận nghiệm thu

**P11-T06 READY FOR REVIEW.** Phiên Colab thật `20261123T144350Z-25b763c7` đã chạy xong 20/20 cell code, đủ 10 mục, V0–V5, bảng/biểu đồ và gallery. Controller gốc kết thúc `failed` vì PDF QA không nhận ra khoảng trắng do text extraction chèn trong từ tiếng Việt; không phải lỗi CUDA hoặc cell notebook. Đã sửa validator, kiểm lại và xem đủ 59 trang PDF. Giữ nguyên summary, failure.log, PDF và notebook gốc; không sửa lịch sử để đổi failed thành passed.

P10-T06 đã hoàn thành phần kỹ thuật và đối soát nội dung, chuyển Chờ review. P11-T06 chuyển Chờ review, chưa đánh Xong trước khi review/merge. Lượt này không tái chứng nhận source freeze, toàn bộ đồ án, cặp mẫu môn học hoặc video. Chi tiết máy đọc được: [p11-t06-t4-evidence.json](p11-t06-t4-evidence.json).

## 2. Source và danh tính artifact

| Hạng mục | Giá trị |
|---|---|
| Nhánh review | chuong/p11-t06-final-acceptance, base cd5ee9d |
| Production SHA thực chạy | cd5ee9d4bb6724b6a816d4d185f0531c47d43d17 |
| Notebook/tooling revision chuẩn bị | 497b08ced5ffb26f69afbe5f8e0ed83971df7ffa |
| Notebook input SHA-256 | 41e28530dc5bb24fd0d60d41352373c3d5ebce47bbc6c113cce3446a06d2427d |
| Notebook output SHA-256 | 530f39f57001b0033a442fb1c937fae3a274ed65633a9f0fb2b86cb7010c2a39 |
| PDF SHA-256 | f80a610673578e19c447522b0f5876bc2f2bd3f397c70493e892cb11c3020fa3 |
| Binary stitch SHA-256, manifest Colab | 839d725705479e2e467733b6aeb0bc39eac5963112360647e70b06be4a6ab84a |
| Dataset manifest SHA-256 | 99fc712988075326a351d0bf580405e418bb28d24d56d4cc1b31505c480bdd9d |

Input notebook và năm hash helper được đối chiếu với blob Git ở tooling revision trên. Source references ghi trong metadata được đối chiếu với Git tree production. Chỉ hai cell bootstrap/producer có runtime overlay đúng dự kiến; cell phương pháp, Markdown và kết quả không bị thay. Không fallback về checkout chỉ có V4.

So với freeze P11-T02 tại `f2837a85b770e6c8bb2eba1bb6de7aee7fa23eb7`, production có thêm host validation trong `src/v5/v5_image_branch.cu`. Lượt benchmark/Run all này kiểm hành vi thực tế trên source mới, nhưng không có full regression, synthetic hoặc Compute Sanitizer mới. Không gán log memcheck lịch sử cho source vừa chạy. [Freeze cũ](p11-t02-freeze-verification.md)

## 3. Môi trường và giao thức

- Tesla T4, compute capability 7.5; driver 580.82.07, VRAM tổng 15.360 MiB và còn 14.913 MiB tại preflight.
- Linux 6.6.159+, Intel Xeon @ 2.00 GHz, Python 3.13.16, nvcc 13.0.88.
- Build thật ghi `-arch=sm_75 -std=c++11 -O2 --fmad=false`, tắt vectorization/FMA CPU, bật `PANORAMA_V5_IMAGE_API_AVAILABLE`.
- Dataset preflight báo đủ 24 ảnh, manifest/sizes/hashes khớp ba site và challenge ở ba độ phân giải. Ảnh đầu vào không nằm trong ZIP evidence; đây là xác nhận manifest/log của lượt Colab, không phải đọc lại 24 file ảnh gốc trên máy local.
- Phiên benchmark bắt đầu ghi lúc `2026-11-23T14:45:56+00:00`. Mỗi cấu hình thành công có một warm-up và năm timed runs; V5 dùng mode dual mặc định. Không có phép đo sequential hoặc sidecar Pre-S4 mới trong phiên này.
- CUDA events đo GPU; Total có D2H đã đồng bộ, loại trừ disk I/O theo implementation. Sum duration stage/kernel của V5 có thể overlap, không dùng thay elapsed Total.

## 4. Run all và kiểm chứng đầu ra

Đã xác minh 268/268 checksum, không file thiếu hoặc bị sửa. Notebook có 43 cell, 20 execution counts liên tục 1–20, `cell_errors.json=[]`; log có START/END cho toàn bộ code. Có đủ 10 section/anchor, bảng lịch sử, bảng cùng phiên, cell V5 mới, charts và ảnh gallery embedded. PDF có 12 image objects; exporter ghi 10 biểu thức MathJax và một sơ đồ Mermaid.

Ma trận thực tế là 72 lượt CLI (12 cấu hình × 6 phiên bản):

| Nhóm | Số lượt | Kết quả |
|---|---:|---|
| 9 cấu hình chuẩn × V0–V5 | 54 | Success, panorama và timing đầy đủ |
| challenge/small × V0–V5 | 6 | Success; ảnh vẫn méo, không coi là đạt cảm quan |
| challenge/medium và large × V0–V5 | 12 | NumericalFailure, exit 1; không suy timing hợp lệ |

Mỗi CSV thành công được kiểm lại bằng parser production: đúng 5 runs, Average/Minimum, schema V0 8 cột và GPU 11 cột theo từng version. Summary khớp raw CSV trong dung sai làm tròn. Trên 10 cấu hình có panorama: Config giống nhau giữa phiên bản, H B→A từ log có reprojection drift 0 px trên lưới kiểm 20×20, canvas/offset khớp; file JPEG giống hệt giữa cả sáu phiên bản. Vì vậy decoded JPEG Max RGB = 0. Đây là parity của artifact sau ghi JPEG và H đã in ra log, không thay kiểm uint8_t S6 trước nén hoặc synthetic ground truth.

## 5. Timing cùng phiên mới

Mean Total_ms, tính lại từ năm raw runs, không ghép với APOD lịch sử:

| Cấu hình | V0 | V1 | V2 | V3 | V4 | V5 dual | V4/V5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| site1/small | 1239.426 | 583.414 | 71.699 | 32.507 | 32.481 | 31.954 | 1.0165 |
| site1/medium | 1636.825 | 523.211 | 54.310 | 31.174 | 30.814 | 29.713 | 1.0371 |
| site1/large | 4719.238 | 412.580 | 257.760 | 107.154 | 105.761 | 103.193 | 1.0249 |
| site2/small | 1138.894 | 933.227 | 21.472 | 21.248 | 21.047 | 20.882 | 1.0079 |
| site2/medium | 1820.403 | 865.180 | 27.655 | 27.835 | 27.491 | 30.566 | 0.8994 |
| site2/large | 5822.029 | 503.047 | 80.580 | 62.521 | 62.232 | 58.518 | 1.0635 |
| site3/small | 794.914 | 364.269 | 111.668 | 53.079 | 45.150 | 61.142 | 0.7384 |
| site3/medium | 1360.225 | 388.150 | 141.052 | 55.768 | 55.800 | 54.886 | 1.0166 |
| site3/large | 3910.964 | 407.933 | 251.991 | 100.627 | 100.163 | 97.402 | 1.0283 |

| Version | GM speedup vs V0, 9 ca chuẩn | GM vs phiên bản trước |
|---|---:|---:|
| V1 | 3.801076× | 3.801076× |
| V2 | 23.920055× | 6.292970× |
| V3 | 42.022061× | 1.756771× |
| V4 | 43.052128× | 1.024513× |
| V5 | 42.021313× | 0.976057× |

V4 có GM cao nhất trong phiên mới, nên notebook chọn V4 cho stage breakdown/gallery đúng output. V5 nhanh hơn V4 ở 7/9 cấu hình, nhưng chậm ở site2/medium và site3/small; GM V5/V4 = 0,976057×. Ca chính site2/large vẫn cải thiện: 62,232 → 58,518 ms, khoảng 1,0635×. Không suy nguyên nhân hai ca chậm chỉ từ một batch; thứ tự chạy version cố định, không phải các khối luân phiên hoặc đối chứng sequential/dual mới.

### Tách khỏi P10-T05 lịch sử

Cell V5 đọc bảng report ngày 23/11 ở source `26c8f24`, không dùng timing đó thay phiên mới:

| Metric lịch sử | Tính lại từ bảng report |
|---|---:|
| GM V5/V0 | 49.876178× |
| GM V5/V4 | 1.068633× |
| GM Dual/Sequential | 1.036413× |
| GM Pre-S4 Seq/Dual | 1.256430× |
| Pre-S4 ca chính | 13.700 → 10.971 ms |
| Median 5 paired blocks | 1.066629× |
| Khối có lợi | 3/5 |
| NSYS overlap | 16.6–24.5% |
| Peak VRAM tăng | 64.30 MiB |

Các số này có trong saved output của cell V5 và được đối chiếu lại với report. Pre-S4 GM từ mean làm tròn hơi khác 1,2565× được công bố; raw P10-T05 archive chưa có để kiểm chữ số cuối. T01 share 21,44% vẫn thuộc probe instrumented, không đổi nhãn thành production share. Lượt mới không tái đo paired blocks/NSYS, nên không thay 3/5 bằng việc đếm cấu hình nhanh hơn. Quyết định giữ **V4 production, V5 concurrency case study** vẫn được giữ và có căn cứ về độ ổn định. [Phân tích V5](p10-t06-v5-analysis.md)

## 6. Gallery, Mermaid và PDF

Đã xem gallery nguyên ảnh: site1/medium cảnh ngoài trời, site2/medium bãi xe, site3/medium trong nhà; nhãn A/B/V4 phù hợp ảnh. Các vùng đen ngoài biên projective là canvas không được phủ; vẫn có giới hạn seam/thị sai cục bộ. Challenge/small có biến dạng và lan can lặp; medium hiển thị rõ panel NumericalFailure thay panorama. Không coi file tồn tại hoặc parity là bằng chứng căn chỉnh hoàn hảo.

Không tìm thấy cặp mẫu do môn học cung cấp trong checkout hoặc gallery; lead cần xác nhận có asset áp dụng hay bổ sung trước đóng gói bài nộp. Mermaid còn nguyên source trong notebook; PDF page 5 hiển thị sơ đồ thật. Không có ảnh chụp Colab UI để xác nhận renderer Mermaid của giao diện đó, nên mục này chờ nhóm xác nhận.

PDF đã được exporter hiện có tạo từ chính notebook output có hash trên. Lỗi QA do pypdf trích thành `Gi ớ i thi ệ u`, `K ế t lu ậ n`; validator cũ so chuỗi có khoảng trắng nên báo thiếu 9 tiêu đề. Bản sửa chỉ bỏ whitespace khi tìm heading và vẫn giữ dấu/ký tự, có test bắt tiêu đề thực sự thiếu. Không bỏ kiểm heading, không xóa diagram và không thay nội dung PDF.

Đã render và xem **59/59 trang**: có đủ 10 mục, tiếng Việt, công thức, Mermaid, bảng, plots, gallery và references; không thấy chữ/hình bị cắt hoặc glyph hỏng. Một số bảng kéo qua trang và trang cuối chỉ có khai báo AI, nhưng không có trang trắng. PDF và notebook bàn giao là bản byte-identical từ Colab, không chỉnh output hoặc chạy kernel lại local.

## 7. Artifact và cách tái kiểm

| Artifact local | Vai trò |
|---|---|
| `results/20261123T144350Z-25b763c7/` | Evidence gốc, gồm failed summary/log, giữ nguyên |
| `build/Group16_P11_T06_Submission/Group16_Final.ipynb` | Bản nộp có toàn bộ output thật |
| `build/Group16_P11_T06_Submission/Group16_Final.pdf` | PDF 59 trang, cùng hash bản Colab |
| `build/Group16_P11_T06_Submission/verification.json` | Kiểm tự động mới, tách verdict gốc |
| `build/Group16_P11_T06_Submission/manual_review.json` | Các trang/hình đã xem và giới hạn |
| `build/Group16_P11_T06_T4_20261123_cd5ee9d_Evidence.zip` | Gói original + submission, 275 file |

ZIP SHA-256: `1767ee60145df7ad5e38d47cd5b5cb924b5339ca70be372d408928ed150d4d8b` (158.108.634 byte). ZIP/JSON/PDF/output không commit Git theo quy ước nhóm; upload gói lên kho evidence chung khi bàn giao. Notebook source ở gốc repo giữ output-free; bản nộp có output nằm trong gói trên. Snapshot có runtime paths của phiên Colab; dùng [workflow nghiệm thu](p11-t06-colab-runbook.md) để tái tạo các path trong phiên mới, không clear output snapshot.

```powershell
$env:MPLBACKEND='Agg'
python scripts/review_notebook_evidence.py results/20261123T144350Z-25b763c7 --tooling-ref 497b08ced5ffb26f69afbe5f8e0ed83971df7ffa --pdf-copy build/Group16_P11_T06_Submission/Group16_Final.pdf --output build/p11-t06-returned-review/recheck.json
python tests/run_tests.py --group python
```

Lệnh audit không sửa evidence gốc. Kết quả mới là `automatic_review_passed_manual_review_required`; original execution_summary vẫn failed vì QA cũ. Không gọi validate_artifacts cũ để sửa hoặc che failure. Các test parser/recovery/checksum không cần GPU; local không thực thi CUDA mới.

## 8. Bàn giao và việc còn lại

- Chờ review/merge PR của Chương; chỉ chuyển Xong theo quy ước sau khi được chấp nhận.
- Tuấn xác nhận source freeze sau host-validation change; full regression/memcheck mới không có trong gói này.
- Nhóm xác nhận Mermaid trên Colab UI và tình trạng cặp mẫu môn học; không ghi đã có nếu thiếu asset.
- P12-T05 của Chương: quay khoảng 5 phút về S6 V4, dispatcher V5 và bài học; dùng script/slide đã thống nhất, hạn 26/11.
- P13: Thành/Chương đưa video YouTube Unlisted vào notebook/README và cập nhật PDF; tổng hợp khai báo AI của các thành viên trước nộp.

**P11-T06 READY FOR REVIEW**
