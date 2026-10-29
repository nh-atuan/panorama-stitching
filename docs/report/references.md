# Nguồn tham khảo báo cáo

## S1 - Tuấn

Người tổng hợp: Tuấn (23120185). Code S1 do Nhóm tự viết, không chép từ nguồn ngoài.

| Nguồn | Ngày truy cập | Dùng cho phần nào |
|---|---|---|
| [Đề cuối kỳ](../specs/CSC14120_2026_Final%20Project.md), mục 2.1, 2.2 và phần tối ưu ở mức pipeline | 07/10, 21/10 | Mô tả S1; ý tưởng gộp grayscale với blur, pinned memory, CUDA stream ở mục 6.3 tài liệu S1 |
| [ITU-R Recommendation BT.601-7 (03/2011)](https://www.itu.int/rec/R-REC-BT.601) | 21/10 | Hệ số đổi ảnh xám 0.299, 0.587, 0.114 |
| [NVIDIA CUDA C++ Best Practices Guide 13.0](https://docs.nvidia.com/cuda/archive/13.0.0/cuda-c-best-practices-guide/index.html), mục 9.1.2, 10.1.1, 10.1.2, 10.2.1, 10.2.3, 10.2.6, 11.3 | 21/10 | Mục 6 tài liệu S1: CUDA events, pinned memory, chồng truyền dữ liệu với tính toán, coalescing, shared memory, constant memory, kích thước block |
| Benchmark V0 ngày 20/10 của Thành: `results/p3-t04/benchmark/summary.csv` trên nhánh `thanh/p3-results` | 21/10 | Thời gian và tỷ trọng S1 ở mục 6.1 tài liệu S1 |

## S4/S5 - Đế

Người tổng hợp: Đế (23120232). Ngày truy cập các nguồn dưới đây: 13/10/2026. Phần này phục vụ thiết kế/cài V0 S4/S5 và việc chuyển nội dung sang notebook. Các file code ghi tác giả, nguồn ý tưởng và phần Nhóm tự cài; SplitMix64 reference được ghi nguồn trong module sampling. Không dùng trọng số hoặc implementation learned matcher, không link OpenCV/Eigen/LAPACK.

| Nguồn | Dùng cho phần nào | Phạm vi đã đọc/kiểm chứng |
|---|---|---|
| [Đề cuối kỳ](../specs/CSC14120_2026_Final%20Project.md), [đề giữa kỳ](../specs/CSC14120_2026_Final%20Project_MidTerm.md) | Yêu cầu pipeline, sequential, GPU, fairness, synthetic và báo cáo | Đọc bản Markdown local; repo không có PDF gốc để đối chiếu |
| [Kế hoạch Nhóm](../archive/midterm-plan.md), [bảng công việc](../task-board.md), [interface](../interface.md), [common.h](../../src/common.h) | Phạm vi task, thư viện, quy ước dữ liệu và nghiệm thu | Đọc local; P0-T04 chưa ghi hoàn thành |
| [Lowe, D. G. (2004). Distinctive Image Features from Scale-Invariant Keypoints](https://www.cs.ubc.ca/~lowe/papers/ijcv04.pdf), IJCV 60(2), 91–110 | S4: ý tưởng ratio test, nguồn ngưỡng khảo sát | Đọc mục 7.1–7.2 qua PDF tác giả; thí nghiệm dùng SIFT, không chuyển kết luận chất lượng sang binary descriptor |
| [OpenCV 4.13.0: Feature Matching](https://docs.opencv.org/4.13.0/dc/dc3/tutorial_py_matcher.html) | S4: Hamming/L2, exact search, ratio và cross-check | Đọc tài liệu chính thức; không thêm OpenCV vào chương trình |
| [OpenCV 4.13.0: BFMatcher, create](https://docs.opencv.org/4.13.0/d3/da1/classcv_1_1BFMatcher.html) | S4: Hamming cho ORB/BRISK/BRIEF; cross-check là alternative cho ratio, không bắt buộc | Đọc trực tiếp mục create; phân biệt Hamming và Hamming2 cho ORB WTA_K=3/4 |
| [OpenCV 4.13.0: USAC](https://docs.opencv.org/4.13.0/de/d3e/tutorial_usac.html) | S5: uniform sampling, MSAC score, reprojection error, homography collinearity, standard stopping và all-inlier fitting | Đọc trực tiếp tutorial; không đồng nhất minimal solver hoặc mọi policy của OpenCV với normalized DLT/prefix deterministic của Nhóm |
| [OpenCV 4.13.0: Feature Matching with FLANN](https://docs.opencv.org/4.13.0/d5/d6f/tutorial_feature_flann_matcher.html) | S4: hướng approximate nearest-neighbor và binary matching | Đọc tài liệu chính thức; không dùng implementation làm dependency |
| [OpenCV: lsh_index.h](https://github.com/opencv/opencv/blob/4.x/modules/flann/include/opencv2/flann/lsh_index.h), nhánh 4.x | S4: ví dụ LSH index cho phương án ANN | Kiểm tra nguồn chính thức cho LSH index; chưa khảo sát đầy đủ implementation và không chép code |
| [Lindenberger, P., Sarlin, P.-E., Pollefeys, M. (2023). LightGlue: Local Feature Matching at Light Speed](https://openaccess.thecvf.com/content/ICCV2023/html/Lindenberger_LightGlue_Local_Feature_Matching_at_Light_Speed_ICCV_2023_paper.html), ICCV | S4: learned sparse matcher | Metadata/abstract từ CVF qua kết quả tìm kiếm; không benchmark tại Nhóm |
| [Wang, Y. et al. (2024). Efficient LoFTR: Semi-Dense Local Feature Matching with Sparse-Like Speed](https://openaccess.thecvf.com/content/CVPR2024/html/Wang_Efficient_LoFTR_Semi-Dense_Local_Feature_Matching_with_Sparse-Like_Speed_CVPR_2024_paper.html), CVPR | S4: learned semi-dense matching | Metadata/abstract và đoạn phương pháp từ PDF được CVF lập chỉ mục |
| [Li, X., Rao, T., Pan, C. (2025). EDM: Efficient Deep Feature Matching](https://openaccess.thecvf.com/content/ICCV2025/html/Li_EDM_Efficient_Deep_Feature_Matching_ICCV_2025_paper.html), ICCV | S4: detector-free matching gần đây | Metadata/abstract từ CVF qua kết quả tìm kiếm |
| [Edstedt, J. et al. RoMa v2: Harder Better Faster Denser Feature Matching](https://arxiv.org/abs/2511.15706), preprint 2025, v3 cập nhật 06/07/2026 | S4: learned dense matching gần đây | Đọc trang arXiv/abstract; truy cập bản HTML, không tuyên bố đã đọc trọn paper |
| [Lee, J., Kang, S., Yoo, S. (2026). MV-RoMa: From Pairwise Matching into Multi-View Track Reconstruction](https://arxiv.org/abs/2603.27542), preprint | S4: phân biệt hai ảnh và nhiều view | Đọc metadata/abstract arXiv |
| [Brown, M., Lowe, D. G. (2007). Automatic Panoramic Image Stitching using Invariant Features](https://www.cs.ubc.ca/~lowe/papers/07brown.pdf), IJCV 74, 59–73 | S5: RANSAC với mẫu 4 correspondence, DLT và consensus | Đọc mục 3.1 qua PDF tác giả; không dùng tham số paper như cấu hình đã chốt của Nhóm |
| [Harker, M., O'Leary, P. (2005). Computation of Homographies](https://www.robots.ox.ac.uk/~phst/BMVC2005/papers/190/paper190.pdf), BMVC | S5: centering/RMS normalization và homogeneous DLT | Đọc mục 2.3 và đoạn DLT/nullspace; không chọn phương pháp residualization cải tiến của paper |
| [Drmac, Z., Veselic, K. New Fast and Accurate Jacobi SVD Algorithm: II, LAPACK Working Note 170](https://www.netlib.org/lapack/lawnspdf/lawn170.pdf) | S5: cơ sở one-sided Jacobi SVD và stopping theo orthogonality | Đọc phần giới thiệu và cyclic rotation/stopping; tự cài core unpreconditioned cho 9 cột, không sao chép/link LAPACK hoặc áp dụng toàn bộ preconditioned algorithm của paper |
| [Vigna, S. (2015). SplitMix64 reference](https://prng.di.unimi.it/splitmix64.c) | S5: mixer/next-state trong mã giả RNG deterministic | Đọc toàn bộ nguồn reference/public-domain notice; stream initialization và bounded sampling là policy của Nhóm |
| [Fowler/Noll/Vo: FNV Hash](https://www.isthe.com/chongo/tech/comp/fnv/index.html) | S5: fingerprint chẩn đoán thứ tự sample | Đọc công thức FNV-1a và hằng số 64-bit; biến thể local XOR toàn bộ chỉ số rồi nhân, không phải FNV-1a trên byte stream và không tham gia chọn homography |
| [Chum, O., Matas, J. (2005). Matching with PROSAC – Progressive Sample Consensus](https://cmp.felk.cvut.cz/~matas/papers/chum-prosac-cvpr05.pdf), CVPR | S5: phương án sampling dựa trên ranking | Đọc abstract và mục thuật toán qua PDF tác giả |
| [Barath, D. et al. (2020). MAGSAC++, a Fast, Reliable and Accurate Robust Estimator](https://openaccess.thecvf.com/content_CVPR_2020/html/Barath_MAGSAC_a_Fast_Reliable_and_Accurate_Robust_Estimator_CVPR_2020_paper.html), CVPR | S5: robust estimation và weighted refinement | Abstract và đoạn phương pháp/thí nghiệm từ CVF được tìm kiếm trả về; mở trang trực tiếp gặp lỗi |
| [Ivashechkin, M., Barath, D., Matas, J. (2021). VSAC: Efficient and Accurate Estimator for H and F](https://openaccess.thecvf.com/content/ICCV2021/html/Ivashechkin_VSAC_Efficient_and_Accurate_Estimator_for_H_and_F_ICCV_2021_paper.html), ICCV | S5: alternative RANSAC-type không chọn | Metadata/abstract và đoạn mô tả verification/failure từ CVF được tìm kiếm trả về; không chuyển số đo paper sang Nhóm |

Tra cứu có mục tiêu, không phải khảo sát đầy đủ mọi công bố đến năm 2026. Các đánh giá về mức phù hợp với C++/CUDA của đồ án là suy luận từ yêu cầu và contract hiện có. Mọi kết luận chất lượng/hiệu năng trên dataset Nhóm cần kết quả chạy thực tế.

### Bổ sung cho P3-T08 — mapping GPU

Đế bổ sung ngày 21/10/2026, dùng cho mục 6 của S4/S5 và nội dung GPU trong báo cáo. Đây là nguồn thiết kế, không cung cấp số đo speedup của nhóm.

| Nguồn | Dùng cho phần nào | Phạm vi đã đọc/kiểm chứng |
|---|---|---|
| [NVIDIA CUDA Math API 13.0 — Integer Intrinsics](https://docs.nvidia.com/cuda/archive/13.0.0/cuda-math-api/cuda_math_api/group__CUDA__MATH__INTRINSIC__INT.html) | S4: `__popc` trên word 32 bit ở Device | Mục khai báo và ý nghĩa `__popc` |
| [NVIDIA CUDA C++ Best Practices Guide 13.0](https://docs.nvidia.com/cuda/archive/13.0.0/cuda-c-best-practices-guide/index.html) | S4/S5: profiling, bố trí bộ nhớ, truyền Host–Device, timing và giới hạn Amdahl | Các mục Assess, Timing, Memory Optimizations và Data Transfer; mapping block/thread và prefix deterministic là thiết kế của nhóm |
| Benchmark V0 scalar ngày 20/10/2026: `results/p3-t04/benchmark/summary.csv`, CSV/log từng site và `environment.json` | Căn cứ hiệu năng cho mapping S4/S5 | Đối chiếu chín hàng average với 45 lần đo gốc; các file kết quả được lưu riêng, không commit vào repo |

## S2/S3 - Thành

Người tổng hợp: Thành (23120166). Ngày truy cập: 16/10/2026. Không dùng code hay bảng pattern của OpenCV; pattern BRIEF do Nhóm tự sinh bằng `tests/tool_gen_brief_pattern.py`.

| Nguồn | Dùng cho phần nào | Phạm vi đã đọc/kiểm chứng |
|---|---|---|
| [Rosten, E., Drummond, T. (2006). Machine learning for high-speed corner detection](https://www.edwardrosten.com/work/rosten_2006_machine.pdf), ECCV | S2: segment test, vòng tròn 16 điểm, score V | Mục segment test và score V; không dùng cây quyết định học máy |
| [Rosten, E., Porter, R., Drummond, T. (2010). Faster and better: a machine learning approach to corner detection](https://arxiv.org/abs/0810.2434), IEEE TPAMI | S2: so sánh độ lặp lại theo số điểm liên tiếp n | Trang arXiv và phần đánh giá độ lặp lại |
| [Calonder, M., Lepetit, V., Strecha, C., Fua, P. (2010). BRIEF: Binary Robust Independent Elementary Features](https://www.cs.ubc.ca/~lowe/525/papers/calonder_eccv10.pdf), ECCV | S3: test nhị phân, làm mượt σ = 2 trên cửa sổ 9×9, cách lấy mẫu G II | Đọc mục 3.1-3.3 |
| [Rublee, E., Rabaud, V., Konolige, K., Bradski, G. (2011). ORB: an efficient alternative to SIFT or SURF](https://doi.org/10.1109/ICCV.2011.6126544), ICCV | S2/S3: phương án xếp hạng Harris và rotated BRIEF, patch 31×31 | Dùng cho phần phương án đã cân nhắc |
| [NVIDIA CUDA C++ Best Practices Guide 13.0](https://docs.nvidia.com/cuda/archive/13.0.0/cuda-c-best-practices-guide/index.html) | S2/S3 mục 6: CUDA events, coalescing, shared memory, constant memory, kích thước block | Mục 9.1.2, 10.2.1, 10.2.3, 10.2.6, 11.3; truy cập 21/10/2026 |
| [NVIDIA CUDA Programming Guide, mục 5.4.6.2 Warp Vote Functions](https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/cpp-language-extensions.html#warp-vote-functions) | S3 mục 6.3: ghép bit descriptor bằng `__ballot_sync` | Mô tả `__ballot_sync`; truy cập 21/10/2026 |
| Benchmark V0 ngày 20/10/2026: `results/p3-t04/benchmark/summary.csv` và log `--debug` trên nhánh `thanh/p3-results` | S2/S3 mục 6.1, báo cáo 3.5 timing | Hàng average, minimum và số keypoint, match, canvas trong log |
| [OpenCV 4.x, `features2d.hpp`](https://github.com/opencv/opencv/blob/4.x/modules/features2d/include/opencv2/features2d.hpp) và [`orb.cpp`](https://github.com/opencv/opencv/blob/4.x/modules/features2d/src/orb.cpp) | S2: ngưỡng FAST mặc định 10 (FAST) và 20 (ORB); S3: ORB làm mượt Gaussian 7×7, σ = 2 | Đọc khai báo `create` và dòng `GaussianBlur`; không thêm OpenCV vào chương trình |
| [Vigna, S. SplitMix64 reference](https://prng.di.unimi.it/splitmix64.c) | S3: bộ sinh số ngẫu nhiên cho pattern | Chuyển sang Python trong công cụ sinh pattern |

## S6 - Chương

Người tổng hợp: Chương (23120195). Code S6 (`src/v0_warp_blend.cpp`) do Nhóm tự viết từ contract và mã giả trong tài liệu S6, không chép code ngoài. Danh mục đầy đủ và mức kiểm chứng của từng nguồn nằm ở mục 9 [tài liệu S6](../stages/s6-warp-blend.md#9-nguồn-tham-khảo).

| Nguồn | Dùng cho phần nào | Phạm vi đã đọc/kiểm chứng |
|---|---|---|
| [Szeliski, R. Image alignment and stitching: A tutorial](https://doi.org/10.1561/0600000009), Foundations and Trends in Computer Graphics and Vision 2(1) | S6: hệ quy chiếu, resampling, compositing | Mục 6 bản technical report; truy cập 12/10/2026 |
| [Brown, M., Lowe, D. G. (2007). Automatic panoramic image stitching using invariant features](https://www.cs.ubc.ca/~lowe/papers/07brown.pdf), IJCV 74 | S6: so sánh linear blending và multi-band, giới hạn khi có vật chuyển động | Mục 6–7 và 9; truy cập 12/10/2026 |
| [Burt, P. J., Adelson, E. H. (1983). A multiresolution spline with application to image mosaics](https://doi.org/10.1145/245.247), ACM TOG 2(4) | S6: nguồn gốc multi-band blending (phương án không chọn) | Tên và abstract; chưa đọc toàn văn |
| [NVIDIA CUDA C Programming Guide 12.5, texture fetching](https://docs.nvidia.com/cuda/archive/12.5.0/cuda-c-programming-guide/index.html#texture-fetching) | S6 mục 6: giới hạn độ chính xác của bilinear phần cứng | Mục 15.1–15.2; truy cập 12/10/2026 |
| [NVIDIA CUDA C++ Best Practices Guide 13.0](https://docs.nvidia.com/cuda/archive/13.0.0/cuda-c-best-practices-guide/index.html) | S6 mục 6: throughput phép tính 64 bit trên compute capability 7.5, pinned memory, CUDA events | Mục 12.1.1 (bảng 5), 10.1.1–10.1.2, 9.1.2; truy cập 21/10/2026 |
| Benchmark V0 ngày 20/10/2026 (`results/p3-t04/` trên nhánh `thanh/p3-results`) và lần Run all notebook ngày 21/10/2026 | S6 mục 6.1, báo cáo 3.5 panorama | Thời gian S6, kích thước canvas, panorama và crop |
