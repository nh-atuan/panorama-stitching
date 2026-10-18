# S5 - Homography estimation

Người phụ trách: Đế (23120232). Cập nhật lần cuối: 18/10/2026; Tuấn (23120185) cài công cụ synthetic (mục 5.5) và ghi kết quả Colab T4 ở mục 7.

Task: P0-T11 (method, input/output, synthetic/metric) và phần thiết kế P1-T13 (tham số, thuật toán, trường hợp biên).

**Trạng thái: đã cài V0 S5 và gộp file ngày 13/10/2026**, giữ method đã chốt từ V0 đến Final. Ngày 18/10/2026 bản trên `main` đạt toàn bộ 7 suites trên Colab T4 bằng nvcc, chạy trong pipeline V0 trên cả 4 cặp của dataset, và có sai số trên cặp synthetic ở mục 5.5. Ngưỡng sai số chung chốt ở P1-T01.

## 1. Phương pháp đã chọn và các phương án đã cân nhắc

### 1.1. Yêu cầu và phương pháp đã chốt

[Đề cuối kỳ](../specs/CSC14120_2026_Final%20Project.md), mục 2.1 yêu cầu H biến đổi **B sang A**, chịu được match sai; mục 2.2 gợi ý RANSAC với 4-point DLT, refinement và PROSAC. Mục 3 yêu cầu cùng phương pháp, tham số giữa các phiên bản. [Đề giữa kỳ](../specs/CSC14120_2026_Final%20Project_MidTerm.md), mục 3.5 yêu cầu sai số homography trên cặp synthetic so với ground truth.

Phương pháp đã chốt: **deterministic uniform 4-point RANSAC sampling; normalized DLT bằng double cho mỗi hypothesis; MSAC-style truncated squared forward reprojection-error score; adaptive termination có upper bound 2000; all-inlier normalized-DLT refit, reclassify một lần và refit thêm nếu tập inlier đổi**. Seed=16, H luôn B → A, threshold scale theo độ phân giải như mục 3. Không chuyển sang PROSAC/MAGSAC++/VSAC ở các version sau.

RANSAC và DLT có vai trò khác nhau: DLT ước lượng H từ các cặp điểm; RANSAC tìm mô hình có nhiều correspondence phù hợp khi input chứa outlier. [Brown và Lowe (2007), mục 3.1](https://www.cs.ubc.ca/~lowe/papers/07brown.pdf) dùng mẫu 4 correspondence và DLT trong RANSAC cho stitching. Tham số và số đo trong paper không được dùng như kết quả của Nhóm.

[OpenCV USAC](https://docs.opencv.org/4.13.0/de/d3e/tutorial_usac.html) mô tả uniform sampling, MSAC truncated squared error, reprojection error cho homography, collinearity checks, standard termination và final all-inlier fitting. Ta chọn các thành phần trên, không sao chép toàn bộ USAC pipeline. Đặc biệt, tài liệu OpenCV dùng solver minimal khác; normalized DLT của Nhóm được xác định riêng tại mục 4.

MSAC là cách chấm điểm tinh hơn binary inlier-count scoring: các inliers có residual khác nhau đóng góp loss khác nhau. Đây là cải tiến lựa chọn mô hình so với plain count, không phải thuật toán mới hoặc một tuyên bố SOTA. Có thể giúp chọn H sát điểm hơn nhưng không bảo đảm nhiều inlier hơn hoặc panorama tốt hơn trên dataset Nhóm; cần kiểm thử.

### 1.2. So sánh phương án

| Phương án | Chất lượng và giới hạn | Chi phí/độ khó | Khả năng đưa lên GPU |
|---|---|---|---|
| DLT trên toàn bộ match, không robust | Hợp khi match đúng; một số outlier có thể làm H lệch | Một lần fit, dễ tạo baseline solver | Các phép gom hệ có thể reduction; không đáp ứng tốt input chứa match sai |
| Plain RANSAC + normalized DLT, score bằng số inlier (không chọn) | Không phân biệt hai mô hình có cùng count nhưng residual khác nhau | Baseline dễ giải thích, cần tie-break bổ sung | Dễ song song nhưng không dùng scorer này riêng ở V0 |
| **Uniform 4-point RANSAC + normalized DLT + MSAC + adaptive stop + all-inlier refit (đã chọn)** | Chấm cả mức sai số trong ngưỡng, vẫn robust với residual lớn bị cắt; phụ thuộc chất lượng match và hình học | Hệ nhỏ, phép chiếu và tổng loss; giữ cấu trúc hypothesize-and-verify | Hypotheses/residual độc lập; score/count cần reduction, stop xử lý theo prefix xác định |
| [PROSAC](https://cmp.felk.cvut.cz/~matas/papers/chum-prosac-cvpr05.pdf), CVPR 2005 | Lấy mẫu ưu tiên correspondence được xếp hạng tốt, mở rộng tập dần | Thêm quy tắc xếp hạng, lịch tăng tập và stopping criterion | Thêm điều phối sampling; lợi ích phụ thuộc ranking đáng tin |
| [MAGSAC++](https://openaccess.thecvf.com/content_CVPR_2020/html/Barath_MAGSAC_a_Fast_Reliable_and_Accurate_Robust_Estimator_CVPR_2020_paper.html), CVPR 2020 | Marginalize noise scale, dùng weighted refinement; không có nghĩa là hết tham số/cấu hình | Phức tạp hơn consensus đếm inlier | Cần cài scoring/weights/refinement và sampler đã chọn cho cả CPU/GPU |
| [VSAC](https://openaccess.thecvf.com/content/ICCV2021/html/Ivashechkin_VSAC_Efficient_and_Accurate_Estimator_for_H_and_F_ICCV_2021_paper.html), ICCV 2021 | Các cải tiến RANSAC-type về verification và nhận diện cấu trúc inlier; paper có đánh giá H/F | Nhiều thành phần cần hiểu, cài và đối chiếu | Không chọn vì thêm độ phức tạp vào baseline và CUDA; kết quả paper không chứng minh ưu thế trên ảnh Nhóm |

Đây là so sánh thiết kế, chưa benchmark trên dữ liệu Nhóm. Các phương án PROSAC/MAGSAC++/VSAC có thể cải thiện robustness hoặc hiệu quả trong điều kiện/benchmark phù hợp, nhưng không bảo đảm luôn tốt hơn. Không chọn vì thêm ranking/sampling schedule, marginalization/weights hoặc verification/local optimization, làm việc tự cài và đối chiếu thuật toán CPU–GPU phức tạp đáng kể. Chúng chỉ nằm trong alternatives considered, không là bước tối ưu tiếp theo của pipeline đã chốt.

### 1.3. Chất lượng, GPU suitability và fairness

S4 không cross-check nên S5 phải chịu được các match hình học sai còn lại. MSAC cắt ảnh hưởng residual lớn và phân biệt mức khớp của inliers; normalized DLT giảm ảnh hưởng thang đo tọa độ khi giải hệ; refit dùng nhiều hơn 4 điểm để ước lượng lại H. Refit tối thiểu hóa algebraic residual, không trực tiếp tối thiểu hóa MSAC/geometric loss nên vẫn phải đo sai số trước/sau, không mặc định tốt hơn.

Mẫu 4 điểm và phép chiếu 3×3 phù hợp C++ tuần tự và CUDA tự viết. Các hypotheses/residual có thể tính đồng thời; MSAC chỉ thêm tổng `min(e², tau²)` cùng count debug. GPU reduction, batching, shared memory và layout là các hướng tối ưu implementation. Mọi version phải giữ sampler, sample prefix, solver normalization, score, stopping/refit rule, precision và threshold rule; không bật SPRT, đổi sampler/scorer hoặc tăng số refit riêng ở bản sau.

Với m match và K hypotheses, phần chấm điểm khoảng `O(K * m)`; không bảo đảm nhanh hoặc chính xác trước khi chạy. Tỷ lệ inlier thấp có thể cần rất nhiều lượt. RANSAC không chữa được parallax, biến dạng lens hoặc cảnh có nhiều chuyển động không cùng một homography.

## 2. Đầu vào và đầu ra

Theo [`docs/interface.md`](../interface.md), mục 3–6 và 8, cùng [`src/common.h`](../../src/common.h). Không thay các kiểu chung.

| Mục | Quy ước |
|---|---|
| Input | Mảng `Keypoint` của A/B, counts tương ứng, mảng `Match` hợp lệ và match count |
| Correspondence | `pB = keypointsB[match.indexB]`, `pA = keypointsA[match.indexA]` |
| Điều kiện tối thiểu | Ít nhất 4 correspondence; mẫu fit phải có đủ ràng buộc độc lập, không có điểm trùng hoặc cấu hình suy biến |
| Tọa độ | Pixel của ảnh đang chạy; gốc trái trên, x sang phải, y xuống dưới, tâm pixel nguyên; không tự cộng 0.5 |
| Cấu hình | `Config.ransac_iters=2000` là upper bound; `ransac_threshold` là tau đã scale; `seed=16`; `homography_epsilon` dùng chung S5/S6 |
| Output chính | `Homography::data[9]`, float32, row-major, biến đổi B → A; chỉ hợp lệ sau `Success` |
| Chuẩn hóa bàn giao | Chia mọi hệ số cho `max(abs(h[i]))`; không buộc `h22 = 1`, cho phép H và −H tương đương |
| Output phụ dự kiến | Inlier mask/count và residual phục vụ kiểm chứng/debug; hợp đồng buffer cụ thể sẽ ghi ở P1-T13/P1-T14 |
| Lỗi | `InsufficientMatches`, `DegenerateHomography`, `NumericalFailure`, lỗi cấu hình/đối số/cấp phát theo interface |

Với vector cột `[xB, yB, 1]`, đặt `u = h00*xB + h01*yB + h02`, `v = h10*xB + h11*yB + h12`, `w = h20*xB + h21*yB + h22`, rồi `pA = (u/w, v/w)`.

API đã cài trong `src/v0_homography.h`: `v0_homography(FeatureView<Keypoint> left, FeatureView<Keypoint> right, FeatureView<Match> matches, Homography& output, const Config& config, HomographyReport* report=nullptr)`. Views mượn pointer/count/capacity theo `src/feature_support.h`; caller khai báo allocation thật. Output H là value của caller, bị reset zero khi gọi và chỉ publish khi thành công. `HomographyReport` là đối tượng Host, chứa counters/loss/sample hash và vector inlier mask; không chuyển nguyên report sang Device.

Stage không làm I/O. `write_homography_report(stream, report)` in seed/cấu hình/diagnostics khi caller gọi **ngoài vùng timing**. Sau lỗi report có thể giữ progress counters, nhưng `success=false`, H zero và inlier mask rỗng; không âm thầm trả identity. Validation theo thứ tự: reset output/report → S5 config → view metadata/alignment → mọi tọa độ x/y A/B hữu hạn → Match indices/distance và indexA tăng chặt → tối thiểu 4 Match. Không kiểm tra score/angle keypoint vì S5 không sử dụng chúng.

Giữ `common.h` và `docs/interface.md` hiện tại. Tên logic `ransac_max_iters` tại S5 là alias của `Config.ransac_iters`, không phải field mới. Threshold được tính một lần khi chuẩn bị Config từ kích thước A đã biết, bằng cùng rule ở mọi version; S5 không cần thêm ảnh/dimensions vào input chỉ để tính tau. Confidence, sampler/scorer/solver và tolerance nội bộ là hằng số thiết kế có tên, dùng chung các implementation. Khi cài, không thêm field hoặc đổi default trong file dùng chung mà không phối hợp với Chương.

Các mục cần cả Nhóm xác nhận ở P0-T04: chiều B → A, index sau compact, H float32/row-major/max-abs normalization, `ransac_iters` được dùng làm cap, cách khởi tạo threshold, epsilon chung và error propagation. Không tuyên bố cả Nhóm đã xác nhận khi mới có quyết định của Đế.

## 3. Tham số

### 3.1. Cấu hình dùng chung từ V0 đến Final

| Tham số/quy tắc | Giá trị thiết kế | Ý nghĩa và ảnh hưởng |
|---|---|---|
| `seed` | `16u` | Tái lập sample generation theo mục 4.1, không chỉ seed một RNG khác nhau ở CPU/GPU |
| `ransac_max_iters` | `2000`, lưu tại `Config.ransac_iters` | Upper bound số sample attempts, gồm cả mẫu bị bỏ; không phải luôn chạy đủ 2000 hypotheses hợp lệ |
| Sample size/sampler | 4 correspondence khác index, uniform không hoàn lại trong một sample | Không ranking hoặc bias theo distance/không gian; các attempts độc lập có thể lặp sample |
| RNG | SplitMix64, stream theo `(seed, hypothesis_id)` | Cùng phép toán unsigned và mapping ID ở CPU/GPU |
| Scorer | MSAC-style `sum(min(e², tau²))`, tối thiểu hóa | Count giữ để report/tie-break/termination, không là primary score |
| Error metric | Forward reprojection B → A, Euclidean squared | Tau đo bằng pixel của A; không đổi sang symmetric error ở một version |
| Solver/precision | Normalized homogeneous DLT, nội bộ double | Nullspace của hệ 2n×9, không buộc h22=1; trả float32 theo interface |
| Adaptive confidence | `0.99` | Tham số stopping equation, không là xác suất chất lượng H đã được chứng minh |
| Refit | Toàn bộ inliers, reclassify một lần, refit lần 2 nếu mask đổi | Tối đa hai lượt all-inlier fit sau best hypothesis; không iterative LO-RANSAC |
| Numerical epsilon | `Config.homography_epsilon`, giá trị làm việc đề nghị `1e-6f` | Tolerance tương đối cho H/denominator, cần Đế và Chương cùng xác nhận; phù hợp cấu hình test S6 hiện có |
| Duplicate/area/rank tolerances | `EPS_DUP=1e-6`, `EPS_AREA=1e-4`, `EPS_RANK=1e-10` | Hằng double trong tọa độ đã normalized/hệ DLT; cần kiểm thử gần suy biến và cả Nhóm xác nhận trước benchmark |

Các method/giá trị chính seed, cap, sampler/scorer/solver/refit đã được Đế chốt. Confidence và numeric tolerances là cấu hình làm việc ghi rõ để cả Nhóm xác nhận khi tích hợp. Chúng không phải kết quả tuning hoặc số đo chất lượng.

`configure_v0_features(config,W_A,H_A)` chuẩn bị baseline seed=16/cap=2000 và threshold rule, giữ tham số của stage khác, chỉ đặt epsilon về 1e-6f nếu caller chưa cấu hình (zero). API S5 validate `0 < cap <= 2000`, threshold/epsilon hữu hạn dương; nó đọc seed/tau/epsilon thực tế từ Config để hỗ trợ fixture/debug. Benchmark V0–Final luôn dùng cùng baseline Config đã chốt, không đổi giá trị riêng một version.

### 3.2. Threshold scale theo độ phân giải

Chọn mốc **tau_ref=3.0 px ở 1920×1080**. Với ảnh A kích thước W_A×H_A:

```text
scale_A = hypot(double(W_A), double(H_A)) / hypot(1920.0, 1080.0)
tau_double = 3.0 * scale_A
Config.ransac_threshold = float(tau_double)
tau = double(Config.ransac_threshold)
inlier if e² < tau²
```

| Độ phân giải A | Scale | Tau |
|---|---|---|
| 1280×720 | 2/3 | 2 px |
| 1920×1080 | 1 | 3 px |
| 3840×2160 | 2 | 6 px |

Đây là rule thiết kế của Nhóm, không phải ngưỡng tối ưu được paper bảo đảm. Giữ cùng phần sai số tương đối theo đường chéo khi cùng cảnh được resize isotropic, không dùng 3 px cố định cho mọi kích thước. Noise/keypoint localization không nhất thiết scale tuyến tính, nên cần kiểm thử rule trên cả ba resolutions và cặp khó. Với ảnh khác tỷ lệ, đây vẫn là threshold scalar theo diagonal, không giả định anisotropic resize bảo toàn mọi residual.

Mọi version dùng cùng W_A/H_A, công thức, cast float và giá trị tau thực tế từ Config. Dùng bất đẳng thức chặt; residual đúng tau là outlier và loss tau². Không scale theo kích thước canvas, ảnh B hoặc theo H đang ước lượng. Tau_ref và confidence phải in cùng cấu hình trước vùng timing. Ngưỡng inlier này khác **ngưỡng nghiệm thu sai số H so với ground truth**, còn thuộc quyết định P1-T01 của cả Nhóm.

## 4. Thuật toán chi tiết

### 4.1. Uniform sampling deterministic

Input Match có thứ tự tăng theo indexA từ S4. Hypothesis ID t chạy 0..1999; mỗi ID có stream riêng, không lấy trạng thái theo thứ tự thread hoàn thành. Dùng phép unsigned uint64 modulo 2^64, logical shifts và [SplitMix64 của Sebastiano Vigna](https://prng.di.unimi.it/splitmix64.c). Mixer và stream mapping dưới đây là quy tắc Nhóm chọn, không thêm thư viện RNG:

```text
mix64(x):
    x = (x XOR (x >> 30)) * 0xbf58476d1ce4e5b9
    x = (x XOR (x >> 27)) * 0x94d049bb133111eb
    return x XOR (x >> 31)

state_t = mix64(uint64(seed) XOR uint64(t))
next64():
    state_t += 0x9e3779b97f4a7c15
    return mix64(state_t)

bounded(m):
    rejection_floor = (uint64(0) - uint64(m)) % uint64(m)
    repeat r = next64() until r >= rejection_floor
    return r % uint64(m)

sample4(seed, t, m):
    initialize state_t
    draw bounded(m), discard indices already in this sample
    stop at 4 distinct indices, preserve draw order
```

Rejection trước modulo tránh modulo bias với nguồn số giả ngẫu nhiên; không sort theo descriptor quality hoặc tọa độ. Match trùng tọa độ vẫn có thể được draw, rồi sample bị loại theo mục 4.2; không âm thầm prefilter để đổi sampling universe. V0/V1 phải kiểm thử cùng tuples cho cùng `(seed,t,m)`, kể cả khi GPU sinh tất cả samples đồng thời. Log sample hash/tuples ngoài vùng timing; sampling thật vẫn thuộc S5, không chuyển toàn bộ sampler sang Host để gọi đó là stage GPU.

### 4.2. Normalized DLT và degeneracy

Chuẩn hóa độc lập cho từng tập A/B: trừ centroid và scale isotropic để **RMS distance tới origin bằng sqrt(2)**. Đây là biến thể normalization được mô tả ở [Harker và O'Leary, Computation of Homographies, mục 2.3](https://www.robots.ox.ac.uk/~phst/BMVC2005/papers/190/paper190.pdf); chỉ dùng normalization/DLT, không chọn solver cải tiến riêng của paper. Dùng cùng RMS convention ở hypothesis và refit trong mọi version.

Với điểm normalized B=(x,y), A=(u,v), thêm hai hàng vào L:

```text
[x, y, 1, 0, 0, 0, -u*x, -u*y, -u]
[0, 0, 0, x, y, 1, -v*x, -v*y, -v]
```

Giải homogeneous DLT: right singular vector của L ứng với singular value nhỏ nhất, nội bộ double, rồi reshape thành H_n. Với sample 4, L là 8×9 và cần **full right nullspace**, không chỉ thin SVD thiếu vector thứ 9. Khi n>4 có noise, L có thể rank 9; không yêu cầu exact nullspace bằng 0. Dùng SVD tự cài bằng chuẩn C++/CUDA khi triển khai, không thêm Eigen/OpenCV hoặc thay thành hệ 8 ẩn khóa h22=1. Không thay bằng normal equations không kiểm chứng vì làm xấu conditioning.

Phép toán hình học, SVD, DLT, ordered reduction, sampling/adaptive termination, MSAC và estimator/refit đã được gộp vào `src/v0_homography.cpp`; mỗi công việc vẫn là hàm riêng, giữ nguyên thân hàm và thứ tự phép tính. `src/v0_homography_internal.h` giữ khai báo helper cho unit tests; `src/v0_homography.h` giữ API stage/report. Views và cấu hình S4/S5 nằm trong `src/feature_support.h/.cpp`. Các file dùng chung của Nhóm và S6 giữ nguyên.

SVD dùng one-sided Jacobi cyclic, full right basis 9×9, tolerance orthogonality `16*epsilon(double)`, tối đa 128 sweeps và relative null-column floor. Đây là lựa chọn implementation của homogeneous DLT; không phải thay sang thuật toán homography khác. Inversion dùng scaled pivot/rcond tolerance 1e-12 như module S6; epsilon trong Config kiểm tra denominator. Gauge bàn giao max-abs=1 và hệ số max-abs đầu tiên có dấu dương để cố định dấu.

Denormalize `H = inverse(T_A) * H_n * T_B`. Chuẩn hóa tọa độ khi fit khác chuẩn hóa max-abs của H khi bàn giao.

Sample bị bỏ nếu:

- Có hai điểm A hoặc hai điểm B trùng/gần trùng: khoảng cách normalized <= EPS_DUP.
- Bất kỳ bộ ba trong bốn điểm A hoặc B có twice-area `abs(cross(pj-pi, pk-pi)) <= EPS_AREA`, hoặc normalization scale không tính được.
- SVD không hội tụ, rank không đủ: với singular values giảm dần, sigma8 <= EPS_RANK*sigma1; sigma1 không dương/hữu hạn. Với refit, điều kiện này vẫn cần để không có nhiều chiều nullspace/near-nullspace.
- H không hữu hạn, ma trận zero, không khả nghịch/không ổn định theo kiểm tra pivot tương đối, hoặc phép chiếu **các điểm sample** có denominator gần 0/non-finite.

Denominator kiểm tra `abs(w) <= epsilon * (abs(h20*x)+abs(h21*y)+abs(h22))`, hoặc scale của denominator bằng 0. Không chỉ dùng `abs(det(H))` với ngưỡng tuyệt đối; không từ chối chỉ vì w âm. Với điểm ngoài sample khi scoring, denominator invalid cho loss tau² và outlier; không bỏ điểm khỏi mẫu số/tổng score để cải thiện kết quả giả.

### 4.3. MSAC scoring và model selection

Với toàn bộ m Match, theo thứ tự input, đặt:

```text
e_j² = (project(H, pB_j).x - pA_j.x)^2
     + (project(H, pB_j).y - pA_j.y)^2
loss_j = min(e_j², tau²)
score(H) = sum(loss_j)
inlier_j = projection valid and e_j² < tau²
```

Loss/score là double, đơn vị px²; điểm chiếu invalid có loss tau² và inlier=false. Chọn model có **score nhỏ nhất**; nếu score bằng nhau, chọn count lớn hơn; nếu vẫn bằng, hypothesis ID nhỏ hơn. Không cộng trọng số descriptor hoặc dùng count làm primary score. Candidate dưới 4 inlier không được nhận làm best.

V0/GPU dùng một thứ tự reduction cố định: leaves theo Match index, pad zero đến power-of-two, cộng từng cặp kề nhau từ dưới lên. Cùng reduction policy cho các tổng của DLT/normalization khi tối ưu. Không dùng atomic sum theo lịch thread để quyết định model. Precision/policy FMA và thứ tự phép toán phải giữ nhất quán; không bật fast-math chỉ ở bản GPU. Không tự đặt epsilon-score tie có tính không bắc cầu; floating-point boundaries vẫn phải được kiểm thử giữa CPU/GPU.

### 4.4. Adaptive termination

Dùng standard stopping equation cho uniform sample size 4, confidence c=0.99, w=count(best)/m:

```text
if no best or w == 0: K_needed = ransac_max_iters
else if w == 1: K_needed = 1
else: K_needed = ceil(log1p(-c) / log1p(-(w^4)))
K_needed = clamp(K_needed, 1, ransac_max_iters)
```

Tính w double, clamp [0,1], guard underflow/non-finite trước cast integer; nếu budget theo công thức vượt 2000, giữ cap 2000. Update khi best MSAC model đổi; nếu best mới có count thấp hơn, K_needed có thể tăng lại trong cap. Không lấy count của một model khác chỉ để làm budget nhỏ hơn. Attempts suy biến vẫn tăng t và tính vào cap; c=0.99 là giả định của stopping heuristic, không bảo đảm xác suất thành công khi samples có suy biến, matches phụ thuộc hoặc w ước lượng sai.

V0 commit kết quả theo t tăng dần, sau mỗi attempt kiểm tra `attempts_done >= K_needed`. GPU được fit/chấm nhiều hypotheses đồng thời nhưng phải replay model selection/budget theo **cùng prefix ID**; chỉ hypotheses trong prefix trước điểm stop được chọn làm best. Không nhận một model tốt hơn từ batch phía sau stop hoặc dừng theo thread hoàn thành đầu tiên. Ghi riêng attempts logical và hypotheses thực tế đã tính nếu GPU speculative batching làm thừa việc; timing tính cả công việc thật.

### 4.5. Refit và bàn giao

1. Lấy I0 từ best hypothesis theo đúng threshold; fit normalized DLT trên **toàn bộ I0**, thành H1.
2. Reclassify toàn bộ Match một lần với H1 thành I1. Nếu I1 khác I0 và có ít nhất 4 điểm đủ rank, refit toàn bộ I1 thành H2; nếu mask không đổi, giữ H1.
3. Refit lỗi/rank failure hoặc I1 dưới 4: trả lỗi phù hợp, không âm thầm bàn giao hypothesis cũ như kết quả all-inlier refit đã thành công. Không lặp refit đến hội tụ.
4. Chuẩn hóa max-abs, cast float32, kiểm tra H sau cast. Đánh giá mask/count/MSAC score của H bàn giao để debug/report; đây là final evaluation, **không kích hoạt thêm refit**. Nếu H sau cast không đủ hợp lệ hoặc dưới 4 inlier, trả lỗi.

Lưu score/count của best, sau H1/H2 và sau cast để phát hiện refit làm geometric fit kém hơn. DLT refit tối ưu algebraic error, không có bảo đảm MSAC loss luôn giảm; policy không tự đổi sang nonlinear refinement hoặc chọn fallback dựa trên thí nghiệm của riêng một version.

### 4.6. Mã giả tổng hợp và chi phí

```text
validate input and config; output H remains invalid
tau = double(config.ransac_threshold)
cap = config.ransac_iters
best = invalid; K_needed = cap
for t = 0 .. cap - 1:
    ids = sample4(config.seed, t, match_count)
    if sample passes degeneracy checks:
        H = normalized_dlt_double(ids)
        if H is valid:
            score, count, mask = msac_evaluate(H, all_matches, tau)
            if count >= 4 and candidate_key_is_better(score, count, t):
                best = candidate
                K_needed = adaptive_budget(best.count, match_count, 0.99, cap)
    if t + 1 >= K_needed:
        break
if best is invalid: return DegenerateHomography
H1 = normalized_dlt_double(best.inliers)
I1 = reclassify_once(H1)
Hfinal = normalized_dlt_double(I1) if I1 != best.inliers else H1
validate, normalize, cast, evaluate final output; propagate failures
return Success
```

Input có dưới 4 Match trả `InsufficientMatches`; index/count/buffer sai trả `InvalidArgument`; tọa độ non-finite trả `NumericalFailure`; config chưa đặt/không hợp lệ trả `InvalidConfig`. Mẫu lỗi cục bộ bị bỏ, không làm cả chương trình dừng ngay. Không tìm model hợp lệ trong cap hoặc refit suy biến trả `DegenerateHomography`; lỗi allocation trả `AllocationFailed` và cleanup.

Với K attempts thực sự xét, scoring là `O(K*m)`; minimal fit có kích thước cố định, mỗi all-inlier DLT thêm việc tuyến tính theo số điểm cho 9 cột và chi phí SVD. V0 giữ best mask/buffer `O(m)`, không cần toàn bộ K×m residual; CUDA có thể batch bounded buffers. Debug/sample logs và ghi ảnh nằm ngoài vùng timing.

## 5. Bằng chứng chất lượng

Mục 5.1–5.4 là phương án synthetic và metric của P0-T11. Công cụ đã cài ở P1-T15, kết quả ở mục 5.5. Số match và inlier trên dataset ở mục 5 của `docs/stages/s4-matching.md`.

### 5.1. Hai lớp kiểm chứng

| Lớp | Cách tạo | Kiểm tra được |
|---|---|---|
| S5 độc lập | Sinh điểm B, tính điểm A bằng H ground truth; thêm noise/outlier có seed và nhãn riêng | Solver/RANSAC không phụ thuộc S2–S4 |
| Cặp ảnh end-to-end | Tạo hai ảnh từ một scene hoặc một ảnh nguồn bằng phép chiếu biết trước | Toàn bộ pipeline tìm correspondence và ước lượng lại H |

Kiểm thử điểm độc lập không thay thế cặp ảnh synthetic mà đề yêu cầu. Khi báo cáo phải ghi rõ sai số của mỗi lớp và cấu hình tạo dữ liệu.

### 5.2. Phương án tạo cặp ảnh

Tạo ảnh nguồn C đủ rộng, có texture và các chi tiết không lặp; hoặc dùng ảnh thật do Nhóm chụp với vùng lấy mẫu hợp lệ. Cố định seed nếu tạo C ngẫu nhiên. A lấy từ C theo hệ tọa độ tham chiếu. B được tạo bằng gather/bilinear tự cài: **`B(xB, yB) = C(project(H_gt, (xB, yB)))`**. Công thức này bảo đảm H_gt là B → A khi hệ C và A cùng gốc.

Case đầu đề xuất là hai crop ngang của C, cùng W×H, B bắt đầu ở `t = round(0.55 * (W - 1))` theo hệ A:

```text
H_gt = [1, 0, t,
        0, 1, 0,
        0, 0, 1]
```

C cần chứa đủ cả hai crop; không kéo giãn hoặc clamp một vùng ngoài ảnh để tạo texture giả. Case này có overlap xấp xỉ 45%, giúp kiểm tra rõ chiều H và index; chưa đủ chứng minh solver projective tổng quát.

Thêm case H có rotation nhẹ và thành phần projective khác 0 để kiểm tra đủ mô hình. Chọn hệ số trong tọa độ chuẩn hóa để các kích thước có cùng hình học, rồi chuyển H về hệ pixel. Công cụ phải lưu H_gt thực tế và xác minh miền lấy mẫu, denominator, overlap trước khi xuất ảnh.

Nếu vùng B nằm ngoài ảnh nguồn, tạo validity mask riêng; không dùng màu đen làm nhãn ngoài ảnh. Loại cả vùng quanh biên mask nơi patch descriptor không có support hợp lệ khi phân tích correspondence. Không dùng S6 hoặc solver H đang kiểm thử làm nguồn ground truth; cần kiểm tra generator bằng điểm/crop biết trước.

Sinh ảnh ưu tiên PNG để không thêm nhiễu JPEG không kiểm soát. Lưu ảnh, H_gt, dimensions, seed, validity và quy ước resampling dưới output/dataset bị Git ignore. Không commit ảnh sinh vào repo.

Với phép resize có ánh xạ tọa độ `S_A`, `S_B`, dùng `H_gt_new = S_A * H_gt * inverse(S_B)`. Nếu resize quy ước half-pixel, S phải có cả translation tương ứng; không chỉ nhân các hệ số translation của H. Ghi đúng phép resize hoặc sinh trực tiếp mỗi cặp ở từng kích thước.

### 5.3. Metric sai số H đề xuất

Không dùng trực tiếp hiệu giữa 9 hệ số H làm metric chính, vì homography xác định đến scale. Đề xuất đo độ lệch của **hai phép chiếu trên cùng một tập điểm kiểm tra độc lập với inliers dùng fit**.

Lấy lưới cố định 20×20 trải trên B; dựa duy nhất vào H_gt và validity để giữ các điểm thuộc overlap hợp lệ trong A. Tập Q được cố định trước khi xét H_est. Ghi số điểm còn lại và phạm vi tọa độ để tránh đánh giá trên một vùng quá nhỏ. Lưới 20×20 là giá trị đề xuất, cần Đế xác nhận.

```text
e(q) = norm(project(H_est, q) - project(H_gt, q))
RMSE_px = sqrt(sum(e(q)^2 for q in Q) / count(Q))
Max_px = max(e(q) for q in Q)
NRMSE = RMSE_px / sqrt(widthA^2 + heightA^2)
```

RMSE và Max có đơn vị pixel của A; NRMSE hỗ trợ đọc sai số tương đối giữa độ phân giải. Có thể báo thêm sai số bốn góc B để thấy extrapolation, nhưng góc nằm ngoài overlap phải được ghi rõ là đánh giá ngoài vùng quan sát.

Nếu Q rỗng hoặc H_est không chiếu hợp lệ bất kỳ điểm nào trong Q, đánh dấu phép đánh giá thất bại; không loại các điểm này rồi tính sai số nhỏ hơn. H_est được đánh giá là ma trận float32 thực sự bàn giao, không chỉ bản double trước cast. Trên kiểm thử điểm, có thể báo thêm reprojection RMSE trên các inlier ground truth, không dùng inliers tự nhận của RANSAC làm nhãn đúng.

Threshold nghiệm thu thuộc **P1-T01 của cả Nhóm**, chưa chốt. Đề nghị kiểm tra noiseless trước, rồi dữ liệu có noise/outlier và cặp ảnh end-to-end; quyết định ngưỡng từ kết quả cùng yêu cầu panorama. Không bịa một ngưỡng đã thống nhất hoặc tuyên bố metric đã đạt khi chưa chạy.

### 5.4. Bằng chứng cần lưu khi có công cụ

Lưu/in H_gt, H_est, seed, kích thước, tau_ref/scale/tau thực tế, confidence, cap, attempts, số sample hợp lệ/bị loại, số match, số inlier, MSAC score trước/sau refit/cast, sample hash, residual và RMSE/Max/NRMSE. Cặp ảnh end-to-end phải đi qua S1–S5 thật; không thay match bằng correspondence ground truth rồi gọi đó là kết quả toàn pipeline. Số liệu chính thức lấy từ output Colab T4.

So cùng scene ở ba resolutions bằng H_gt đã đổi hệ đúng; báo cả error pixel và normalized error. Rule tau scale là cấu hình đã chọn để kiểm thử, không là quality result. Khi đánh giá lựa chọn MSAC, có thể dùng fixture tĩnh so ranking loss/count; không đổi scorer của một version benchmark thành plain RANSAC để tạo bảng speedup.

### 5.5. Kết quả trên cặp synthetic (P1-T15)

Tuấn cài công cụ thay Đế ngày 18/10/2026, theo đúng mục 5.2 và 5.3:

- `scripts/make_synthetic_pair.py` tạo cặp và ghi `<size>_truth.json` gồm H_gt, kích thước, vùng cắt trên ảnh nguồn và tỷ lệ chồng lấn;
- `scripts/homography_error.py` đọc H_gt và dòng `[debug] H(B->A)=` của `stitch --debug`, in RMSE, Max và NRMSE;
- `scripts/homography_common.py` chứa phép chiếu dùng chung, test ở `tests/test_synthetic_scripts.py`.

Ảnh nguồn C là ảnh gốc `raw/tuan/standard1_left.jpg` (8160×6144, SHA-256 `e9fbe7ecfed6344a36610fe50f2c6019bcd1525f4e217c033ed8ded4f90bf1e8`), được cắt và thu nhỏ bằng Lanczos theo từng kích thước, không phóng to. A là một vùng cắt của C. B lấy mẫu C qua H_gt bằng bilinear tự cài. Ảnh lưu dạng PNG trong `results/` (đã ignore). Lần chạy thử đầu dùng ảnh site2 (`tuan-standard2`) làm nguồn, nhưng vùng chồng lấn khi đó rơi vào mảng tường trơn ở giữa ảnh: cặp dịch ngang chỉ có 65–76 inlier, còn cặp phép chiếu cỡ medium thất bại vì S5 chọn H sai với 31 inlier. Vì mục 5.2 yêu cầu C có texture trải đều, ảnh `tuan-standard1` được dùng thay.

| Case | H_gt (B → A) | Tỷ lệ B rơi vào A | Điểm kiểm tra giữ lại |
|---|---|---|---|
| `translation` | Dịch ngang `t = round(0.55 * (W - 1))`: 703, 1055, 2111 px | 45,3% / 45,2% / 45,1% | 180/400 |
| `projective` | Trong tọa độ chia cho `W - 1`: xoay 3° quanh tâm B, thành phần chiếu (0.10, 0.05), dịch (0.55, 0.02) | 43,7% / 43,7% / 43,6% | 165/400 |

Kết quả trên Colab Tesla T4 (CUDA 13.0) ngày 18/10/2026, `stitch --version 0 --runs 1 --debug`, cấu hình V0 như các stage:

| Case | Kích thước | Match S4 | Inlier S5 | RMSE (px) | Max (px) | NRMSE |
|---|---|---:|---:|---:|---:|---:|
| translation | small | 773 | 706 | 0.000008 | 0.000008 | 5.615e-09 |
| translation | medium | 957 | 883 | 0.004717 | 0.016463 | 2.141e-06 |
| translation | large | 1132 | 1065 | 0.000025 | 0.000025 | 5.650e-09 |
| projective | small | 699 | 622 | 0.055234 | 0.143112 | 3.761e-05 |
| projective | medium | 876 | 800 | 0.062535 | 0.208768 | 2.839e-05 |
| projective | large | 1114 | 1069 | 0.100222 | 0.209020 | 2.275e-05 |

Sai số lớn nhất trên cả 6 cặp là 0.209 px. Với case dịch ngang, vùng chồng lấn của A và B trùng nhau từng pixel nên sai số gần như bằng 0. Cả 6 lần chạy đều ra panorama. Cùng bộ cặp cho kết quả giống hệt khi build bằng g++ 13.3 trên WSL. Ngưỡng đạt do cả Nhóm chốt ở P1-T01.

Lệnh tái lập từ gốc repo, sau khi có ảnh gốc ở `raw/` và đã build `stitch`:

```bash
python3 scripts/make_synthetic_pair.py --source raw/tuan/standard1_left.jpg --out results/synthetic
for case in translation projective; do for size in small medium large; do
  d=results/synthetic/$case/$size
  ./stitch ${d}_left.png ${d}_right.png ${d}_pano.png --version 0 --runs 1 --debug > $d.csv 2> $d.log
  python3 scripts/homography_error.py --truth ${d}_truth.json --log $d.log
done; done
```

## 6. Mức phù hợp với GPU và mapping V1 dự kiến

Các hypotheses có thể fit/chấm điểm độc lập; MSAC score/count cần reduction deterministic. Adaptive stopping cần commit theo prefix ID, không phụ thuộc lịch thread; chi phí coordination/speculative work phải được đo. Refit là tối đa hai all-inlier fits với cùng rule. Mapping thread/warp/block và ý tưởng tối ưu sẽ viết ở P3 sau số đo; chưa tuyên bố speedup hoặc double throughput đủ cao trên T4.

## 7. Kiểm thử

Đã chạy lại toàn bộ suite local sau khi gộp file, và chạy trên Colab T4 ngày 18/10/2026 (bảng kết quả sau lệnh kiểm chứng chính thức). Bảng case bên dưới vẫn bao gồm kế hoạch kiểm chứng CPU–GPU và trường hợp cần fixture bổ sung, không tuyên bố toàn bộ test plan đã nghiệm thu.

Module DLT đã được kiểm tra riêng bằng `tests/test_homography_dlt.cpp`: **690 checks local đạt** trên Windows/clang 23.1.3, C++11 warnings-as-errors, không FMA contraction hoặc compiler vectorization. Bao gồm minimal/full-basis, all-point noiseless/noisy, held-out analytic projection, rank/duplicate/near-collinearity, H và -H, h22=0, tọa độ lớn và denominator horizon. Trên Colab T4: `PASS DLT: 690 checks`.

Phần sampling/adaptive termination: **4412 checks local đạt** trong `tests/test_homography_sampling.cpp`, gồm golden tuples độc lập cho seed 16, đảo lịch gọi hypothesis ID, range/uniqueness với m=4 và m không là power-of-two, cùng guarded adaptive budget. Chưa kiểm chứng CPU–GPU thực tế.

Phần MSAC scoring: **12 checks local đạt** trong `tests/test_homography_scoring.cpp`, gồm loss cắt ngưỡng, equality là outlier, projection invalid có penalty, invalid parameters và score/count/ID model selection. Hai model thật cùng count nhưng residual khác nhau được kiểm tra ranking theo MSAC. Đây là kiểm tra công thức/ranking, không chứng minh chất lượng panorama.

Stage `tests/test_v0_homography.cpp`: **174 checks local đạt**, gồm 4-point/many-point estimation, ground-truth noise/outlier labels, repeatability, second refit khi mask đổi, threshold scaling giữa resolutions, validation/cap và tích hợp S4 → S5 → S6 với features cho sẵn. Đây không phải pipeline S1–S6 từ ảnh thật. Allocation fault injection được tách thành binary riêng để không xung đột allocator operators của Windows ASan.

| Suite | Checks/assertions local đạt | Sanitizers đã chạy |
|---|---:|---|
| `test_v0_match.cpp` | 66 | ASan + UBSan |
| `test_homography_dlt.cpp` | 690 | ASan + UBSan |
| `test_homography_sampling.cpp` | 4412 | ASan + UBSan |
| `test_homography_scoring.cpp` | 12 | ASan + UBSan |
| `test_v0_homography.cpp` | 174 | ASan + UBSan |
| `test_v0_feature_allocation.cpp` | 125 | UBSan; riêng allocator fault injection |
| `test_v0_warp_blend.cpp` có sẵn | 194 | UBSan; code S6 còn được gọi trong integration ASan |

Tổng 7 suites: **5673 checks/assertions**, là số lần assertion, không phải 5673 trường hợp độc lập. Cặp synthetic ảnh và panorama thật đã có ở mục 5.5 và ở mục 5 tài liệu S4. Các ca còn cần môi trường/fixture: CUDA schedule/batch parity, các numerical boundaries của CPU–GPU, trường hợp refit tăng loss/rank failure ở stage.

Lệnh local (compiler portable đã được cho phép, nằm trong build/ bị Git ignore):

```powershell
python tests/run_v0_features.py --compiler build/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe
python tests/run_v0_features.py --compiler build/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe --sanitizers
```

Lệnh kiểm chứng chính thức trên Colab, sau khi repo/source/test đã có trong phiên T4:

```bash
python tests/run_v0_features.py --compiler nvcc --require-t4
```

Runner in tên GPU/CPU/compiler, yêu cầu T4 khi bật `--require-t4`, build bằng `nvcc -arch=sm_75 -std=c++11 -O2` và host flags không FMA contraction/vectorization. Output mong đợi là từng dòng PASS của suite và `PASS suites: 7, total checks: 5673`. Tests chạy executable ngoài notebook; không chép code vào cell. Dùng `--suite matching`, `--suite dlt` hoặc suite khác để khoanh vùng lỗi.

| Ngày | Môi trường | Lệnh | Kết quả |
|---|---|---|---|
| 18/10/2026 | Colab Tesla T4, CUDA 13.0 (V13.0.88), CPU Intel Xeon @ 2.00GHz | `python3 tests/run_v0_features.py --compiler nvcc --require-t4` | `PASS S4: 66`, `PASS DLT: 690`, `PASS sampling: 4412`, `PASS MSAC: 12`, `PASS S5: 174`, `PASS allocation: 125`, `PASS: 194 assertions for S6 ...`; `PASS suites: 7, total checks: 5673` |
| 18/10/2026 | Cùng phiên, g++ 13.3.0 | `python3 tests/run_v0_features.py --compiler g++ --sanitizers` | `PASS suites: 7, total checks: 5673`; ASan + UBSan cho 5 suite đầu, UBSan cho allocation và warp như bảng trên, không có báo lỗi |
| 18/10/2026 | Cùng phiên, Python 3.13 | `python3 tests/test_synthetic_scripts.py` | `Ran 18 tests ... OK` |

| Case | Kết quả mong đợi |
|---|---|
| Identity, translation, affine, projective noiseless với 4 và nhiều điểm | H B → A đúng theo metric độc lập, không đảo chiều |
| 4-point 8×9 DLT; H có h22=0 nhưng valid trên miền test | Lấy full nullspace; không giả định h22=1 |
| H và −H, hoặc H nhân scale hữu hạn khác zero | Cùng phép chiếu và metric trong tolerance, không lỗi chỉ vì denominator âm |
| Duplicate A hoặc B, ba điểm thẳng/gần thẳng, sample near-rank-deficient | Sample bị loại; counts/ID vẫn tái lập và attempts không vượt cap |
| Hai model cùng inlier count nhưng residual khác nhau | Chọn MSAC loss thấp hơn, không chọn chỉ theo count |
| Model count lớn hơn nhưng loss cao hơn | Primary score vẫn là loss, count không ghi đè |
| Tau=3, e²=4/9/16; projection invalid | Loss lần lượt 4/9/9/9; chỉ e²=4 là inlier |
| Resize isotropic cùng hình học/noise scale: 720p/1080p/4K | Tau=2/3/6 px; inlier quyết định tương đương ngoài numerical boundaries |
| `sample4(seed=16,t,m)` ở V0/V1, gồm m=4 và m không là power-of-two | Tuples/order giống nhau, mỗi tuple 4 indices khác nhau; không modulo shortcut |
| Cùng seed/input, đổi lịch thread và batch size | Cùng logical prefix/best ID/mask trong numerical policy, không nhận candidate sau stop |
| w=0, w=1, w thấp, budget>2000 | Không log(0)/NaN/overflow; adaptive cap xử lý đúng |
| All-inlier fit mask không đổi/đổi | Một/hai lượt refit đúng rule; final evaluation không gây lượt thứ ba |
| Refit tăng MSAC loss hoặc refit/rank failure | Ghi score thực tế, không tuyên bố luôn cải thiện; failure trả lỗi |
| NaN/Inf input/H, denominator gần 0, thiếu Match/config unset | Đúng error code; output H invalid sau failure |
| H double → float32 tại ranh giới threshold/denominator | Kiểm tra chính H được bàn giao, báo ảnh hưởng cast và CPU–GPU tolerance |

Mỗi case phải có input/config, kết quả mong đợi và output thực tế trên Colab T4. Với synthetic ảnh, kiểm tra độc lập chiều H bằng một vật mốc hoặc correspondence đã biết trước khi đo pipeline.

## 8. Trường hợp biên và rủi ro

| Rủi ro/trường hợp biên | Policy đã ghi |
|---|---|
| Nhiều A chọn cùng B sau S4 không cross-check | Không ép uniqueness tại S4; sample S5 có điểm B trùng/gần trùng bị loại |
| Duplicate, near-collinear, rank/numerical failure | Kiểm tra cả A và B, skip sample theo tolerance normalized; refit failure là lỗi stage |
| Non-finite H hoặc sample denominator gần 0 | Skip hypothesis; input non-finite là lỗi input, không âm thầm loại Match |
| Projection invalid ở Match ngoài sample | Loss tau², outlier; giữ đủ m trong score/ratio |
| Nhiều outlier hoặc nhiều sample suy biến | Có thể hết 2000 attempts; confidence không bảo đảm H tốt, ghi tỷ lệ sample bị loại |
| Inliers tập trung vùng nhỏ/parallax/chuyển động | MSAC vẫn có thể chọn model sai cho panorama; kiểm tra coverage, synthetic và ảnh thật |
| MSAC chọn model ít inlier hơn plain count | Hợp với primary score đã chốt; dùng count để debug, không override scorer |
| Refit làm residual tăng | DLT tối ưu algebraic error; lưu score trước/sau và kiểm thử, không bịa improvement |
| Đồng thời nhiều hypotheses + adaptive stop | Chỉ xét cùng logical prefix, score reduction/tie-break cố định |
| w rất nhỏ/gần 1, log/ceil overflow | Guard theo mục 4.4, clamp budget trước cast |
| Threshold/rank gần ranh giới hoặc cast float32 | Có thể gây CPU–GPU khác mask; giữ precision/FMA policy và kiểm thử boundary, không tự nới epsilon |
| Horizon xuyên toàn ảnh B hoặc canvas không hữu hạn | Sample/scoring checks chưa bảo đảm toàn domain; S6 vẫn kiểm tra H/canvas theo contract |

Epsilon chung được phối hợp với Chương. Không dùng H identity như fallback thành công, không thay `InsufficientMatches`/`DegenerateHomography` bằng panorama thành công. Không coi refit hai lượt là đầy đủ USAC, LO-RANSAC hoặc MAGSAC++.

## 9. Nguồn tham khảo

Ngày truy cập: 13/10/2026. [Brown và Lowe (2007), mục 3.1](https://www.cs.ubc.ca/~lowe/papers/07brown.pdf): RANSAC 4-point DLT trong stitching. [Chum và Matas (2005)](https://cmp.felk.cvut.cz/~matas/papers/chum-prosac-cvpr05.pdf): đọc abstract và thuật toán PROSAC. [Barath et al. (2020)](https://openaccess.thecvf.com/content_CVPR_2020/html/Barath_MAGSAC_a_Fast_Reliable_and_Accurate_Robust_Estimator_CVPR_2020_paper.html): abstract và đoạn phương pháp/thí nghiệm được CVF lập chỉ mục về MAGSAC++.

Nguồn bổ sung: [OpenCV USAC](https://docs.opencv.org/4.13.0/de/d3e/tutorial_usac.html) cho các thành phần robust estimation; [Harker và O'Leary, mục 2.3](https://www.robots.ox.ac.uk/~phst/BMVC2005/papers/190/paper190.pdf) cho RMS normalization và DLT; [SplitMix64](https://prng.di.unimi.it/splitmix64.c) cho các phép RNG. Stream mapping, prefix commit, threshold scale, tie-break, reduction và số lượt refit là policy cụ thể của Nhóm, không gán cho implementation OpenCV. Synthetic/metric đã cài ở P1-T15 (mục 5.5). Danh mục nguồn ở [`docs/report/references.md`](../report/references.md).

## 10. Lịch sử thay đổi tham số

| Ngày | Thay đổi | Lý do |
|---|---|---|
| 13/10/2026 | Đề xuất RANSAC/DLT/refit, contract B → A, synthetic ảnh và metric sai số phép chiếu | Chuẩn bị P0-T11 để Đế lựa chọn; chưa chốt tham số S5 |
| 13/10/2026 | Đế chốt uniform 4-point RANSAC + normalized DLT double + MSAC + adaptive stop cap 2000 + all-inlier refit; seed 16; tau scale từ 3 px tại 1080p | Giữ method/cấu hình từ V0 đến Final, bổ sung determinism, degeneracy và test plan; chờ xác nhận tích hợp/tolerance chung |
| 13/10/2026 | Cài V0 S5 cùng module math/DLT/SVD, sampler, MSAC, report và test runner; 7 suites local đạt | Không đổi method/tham số; chờ Colab T4, generator synthetic ảnh và tích hợp pipeline thật |
| 13/10/2026 | Gộp toàn bộ implementation S5 vào v0_homography.cpp, giữ một header helper cho unit tests | Thân hàm và test assertions giữ nguyên; 7 suites/5673 assertions local đạt, bản sau gộp cần chạy lại Colab |
| 18/10/2026 | Không đổi tham số. Tuấn cài công cụ synthetic, ghi sai số và kết quả Colab T4 | Nghiệm thu P1-T14, P1-T15 |
