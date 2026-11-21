<!-- Authors: Nguyen Ho Anh Tuan (23120185). External source: none. -->

# Mục lục tài liệu dự án (`docs/`)

Thư mục này chứa toàn bộ tài liệu quản lý, đặc tả kỹ thuật, thiết kế 6 stage, hướng dẫn công cụ và bằng chứng thực nghiệm của Nhóm 16 cho đồ án **CSC14120 - Panorama Stitching**.

Các file trong `docs/report/` được giữ nguyên đường dẫn phẳng để không làm gãy các cell đọc trực tiếp số liệu trong [`Group16_Final.ipynb`](../Group16_Final.ipynb) và các liên kết từ `slides/`. Mục lục bên dưới phân nhóm tài liệu theo vai trò để tra cứu nhanh.

## 1. Đề bài chính thức (`specs/`)

| Tài liệu | Nội dung |
|---|---|
| [Đề cuối kỳ](specs/CSC14120_2026_Final%20Project.md) | Bản chép nguyên văn từ PDF đề bài cuối kỳ (yêu cầu V0–V3+, benchmark, notebook 10 mục, slide và video) |
| [Đề giữa kỳ](specs/CSC14120_2026_Final%20Project_MidTerm.md) | Bản chép nguyên văn từ PDF đề bài giữa kỳ (nền tảng V0) |

## 2. Quản lý dự án và theo dõi tối ưu

| Tài liệu | Nội dung |
|---|---|
| [final-plan.md](final-plan.md) | Kế hoạch cuối kỳ, phân vai thành viên, kiến trúc mã nguồn, chính sách thư viện và checklist nộp bài |
| [task-board.md](task-board.md) | Bảng công việc cuốn chiếu từ P5 đến P14 và nhật ký các quyết định đã chốt |
| [apod-log.md](apod-log.md) | Nhật ký chu trình APOD và tổng hợp speedup các phiên bản V0–V5 trên Colab Tesla T4 |

## 3. Đặc tả kỹ thuật, dữ liệu và công cụ

| Tài liệu | Nội dung |
|---|---|
| [interface.md](interface.md) | Contract dữ liệu chung, cấu trúc `DeviceWorkspace` GPU, quy ước ma trận H và schema CSV |
| [dataset.md](dataset.md) | Quy định chụp ảnh, chuẩn bị bộ ảnh thử nghiệm và cấu hình dataset cuối kỳ |
| [profiling.md](profiling.md) | Hướng dẫn chạy batch profiling (`nsys`, `ncu`) và kiểm chứng sai số synthetic |
| [results-guide.md](results-guide.md) | Quy ước lưu trữ gói kết quả thực nghiệm theo phiên bản trên Google Drive chung |

## 4. Thiết kế 6 stage của pipeline (`stages/`)

| Stage | Tài liệu | Phụ trách |
|---|---|---|
| S1 Preprocessing | [s1-preprocessing.md](stages/s1-preprocessing.md) | Nguyễn Hồ Anh Tuấn |
| S2 Keypoint Detection | [s2-detection.md](stages/s2-detection.md) | Trần Hữu Kim Thành |
| S3 Feature Description | [s3-description.md](stages/s3-description.md) | Trần Hữu Kim Thành |
| S4 Feature Matching | [s4-matching.md](stages/s4-matching.md) | Lê Thượng Đế |
| S5 Homography Estimation | [s5-homography.md](stages/s5-homography.md) | Lê Thượng Đế |
| S6 Warping and Blending | [s6-warp-blend.md](stages/s6-warp-blend.md) | Lê Hà Thanh Chương |

## 5. Báo cáo thực nghiệm, nghiệm thu và tham khảo (`report/`)

Nguồn tham khảo chung cho mã nguồn và báo cáo: [references.md](report/references.md).

### 5.1 Phân tích bottleneck và báo cáo APOD (V1–V5)

| Phiên bản | Tài liệu | Nội dung chính |
|---|---|---|
| V1 | [4.1-v1-profiling-and-bottlenecks.md](report/4.1-v1-profiling-and-bottlenecks.md) | Profiling Nsight V1, phân tích hotspot và ca thất bại `challenge` |
| V2 | [p7-t03-v2-apod.md](report/p7-t03-v2-apod.md) | Benchmark và profiling Nsight sau song song hóa S5 (P7) |
| V3 | [p8-t03-v3-apod.md](report/p8-t03-v3-apod.md) | Benchmark V0–V3 cùng phiên T4 và phân tích vi kiến trúc S5 (P8) |
| V4 | [p9-t05-v4-apod.md](report/p9-t05-v4-apod.md) | Benchmark V0–V4 cùng phiên T4 và phân tích Single-pass Canvas Fusion S6 (P9) |
| V5 | [p10-t05-v5-apod.md](report/p10-t05-v5-apod.md) | Benchmark hai CUDA Stream, trace NSYS và kết luận giữ V4 làm production (P10) |

### 5.2 Báo cáo nghiệm thu correctness và memcheck trên Colab T4

| Giai đoạn | Tài liệu | Phạm vi nghiệm thu |
|---|---|---|
| P5 | [p5-s6-cuda-verification.md](report/p5-s6-cuda-verification.md) | Nghiệm thu độc lập kernel S6 CUDA và memcheck |
| P7 | [p7-v2-verification.md](report/p7-v2-verification.md) | Nghiệm thu pipeline V2 (6 synthetic, 12 ca thật, memcheck) |
| P8 | [p8-v3-verification.md](report/p8-v3-verification.md) | Nghiệm thu pipeline V3, CLI/CSV và memcheck |
| P9 | [p9-v4-verification.md](report/p9-v4-verification.md) | Nghiệm thu pipeline V4, parity V0–V4 và memcheck |
| P10 | [p10-v5-verification.md](report/p10-v5-verification.md) | Nghiệm thu pipeline V5 (dual/sequential) và memcheck |
| P11 | [p11-t02-freeze-verification.md](report/p11-t02-freeze-verification.md) | Tổng duyệt hồi quy toàn bộ V0, GPU V1–V5, Python và đóng băng `src/` |

### 5.3 Kế hoạch thí nghiệm, contract và ghi chú bàn giao nội bộ

- [v4-v5-optimization-plan.md](report/v4-v5-optimization-plan.md): Kế hoạch thiết kế và tiêu chí đánh giá thí nghiệm V4–V5.
- [p9-final-notebook-handoff.md](report/p9-final-notebook-handoff.md): Ghi chú bàn giao khung notebook cuối kỳ sau P9.
- [p10-t01-pres4-baseline.md](report/p10-t01-pres4-baseline.md): Số liệu baseline pre-S4 của V4 trước khi triển khai V5.
- [p10-v5-contract.md](report/p10-v5-contract.md): Contract giao diện tách nhánh ảnh và timing cho V5.
- [p10-t03-v5-handoff.md](report/p10-t03-v5-handoff.md): Ghi chú bàn giao tích hợp dispatcher V5.

### 5.4 Các mục báo cáo nền tảng giữa kỳ (V0)

- Tổng quan và kế hoạch: [3.1-team-plan.md](report/3.1-team-plan.md), [3.2-problem-understanding.md](report/3.2-problem-understanding.md), [3.6-dataset.md](report/3.6-dataset.md), [3.7-gpu-plan.md](report/3.7-gpu-plan.md).
- Phương pháp 6 stage: [3.3-s1-preprocessing.md](report/3.3-s1-preprocessing.md), [3.3-s2-detection.md](report/3.3-s2-detection.md), [3.3-s3-description.md](report/3.3-s3-description.md), [3.3-s4-matching.md](report/3.3-s4-matching.md), [3.3-s5-homography.md](report/3.3-s5-homography.md), [3.3-s6-warp-blend.md](report/3.3-s6-warp-blend.md).
- Kết quả V0: [3.4-sequential-v0.md](report/3.4-sequential-v0.md), [3.5-correctness.md](report/3.5-correctness.md), [3.5-panoramas.md](report/3.5-panoramas.md), [3.5-timing.md](report/3.5-timing.md).

## 6. Lưu trữ các giai đoạn cũ (`archive/`)

| Tài liệu | Nội dung |
|---|---|
| [midterm-plan.md](archive/midterm-plan.md) | Kế hoạch và quy ước nền tảng của giai đoạn giữa kỳ (P0–P4) |
| [midterm-task-board.md](archive/midterm-task-board.md) | Bảng công việc đã hoàn thành của giai đoạn giữa kỳ |
| [notebook-guide.md](archive/notebook-guide.md) | Hướng dẫn chạy và đóng gói notebook giữa kỳ `Group16_Midterm.ipynb` (P3-T09) |
| [s6-colab-guide.md](archive/s6-colab-guide.md) | Hướng dẫn kiểm chứng độc lập S6 CUDA trên Colab (P5-T12/P5-T13) |
