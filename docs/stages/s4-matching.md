<!-- Authors: Le Thuong De (23120232), Nguyen Ho Anh Tuan (23120185). External source: none. -->

# S4 - Matching

Người phụ trách: Đế (23120232). Cập nhật lần cuối: 31/10/2026; implementation V1 và kiểm chứng P5-T10 nằm ở mục 11. Tuấn (23120185) đã bổ sung kết quả V0 trên Colab T4 ngày 18/10.

Task: P0-T11 (phương pháp, đầu vào/đầu ra), P1-T11 (tham số, thuật toán, trường hợp biên), P5-T10 (V1 và kiểm chứng).

**Trạng thái: đã cài V0 và gộp file ngày 13/10/2026.** Dùng nhất quán method đã chốt từ V0 đến Final, chỉ tối ưu implementation. Ngày 18/10/2026 bản trên `main` đạt 66 checks S4 trên Colab T4 bằng nvcc và chạy trong pipeline V0 trên cả 4 cặp của dataset (mục 5, 7). Interface đã chốt ở P0-T04.

## 1. Phương pháp đã chọn và các phương án đã cân nhắc

### 1.1. Yêu cầu và phương pháp đã chốt

[Đề cuối kỳ](../specs/CSC14120_2026_Final%20Project.md), mục 2.2 cho phép tự chọn phương pháp và gợi ý brute-force nearest neighbor, Hamming/L2, ratio test, cross-check. Mục 3 yêu cầu V0 đơn luồng C/C++, V1 đưa mọi stage lên GPU và các phiên bản dùng cùng phương pháp, tham số. [Đề giữa kỳ](../specs/CSC14120_2026_Final%20Project_MidTerm.md), mục 3.3–3.7 yêu cầu giải thích lựa chọn, baseline tuần tự, chất lượng, profiling và kế hoạch GPU; không yêu cầu thuật toán mới nhất.

Phương pháp đã chốt: **exact brute-force 2-NN Hamming trên descriptor binary 256 bit, từ A sang B; Lowe ratio test với threshold 0.80; cross-check tắt; output tăng theo `indexA`**. Residual geometric outliers được giao cho S5 xử lý bằng RANSAC/MSAC. Không chạy tìm nearest neighbor chiều ngược trong phương pháp này.

Hamming đếm số bit khác nhau, là metric tự nhiên cho các test nhị phân BRIEF/rotated BRIEF. [OpenCV BFMatcher](https://docs.opencv.org/4.13.0/d3/da1/classcv_1_1BFMatcher.html), mục `create`, chỉ định Hamming cho ORB/BRISK/BRIEF và mô tả cross-check là alternative của ratio test. Contract hiện tại dùng một bit/test, không dùng ORB WTA_K=3/4 cần Hamming2. Exact search tránh approximation error ở hai láng giềng; ratio test loại các descriptor không phân biệt rõ best với second-best.

Đây là lựa chọn cân bằng giữa panorama quality, correctness, khả năng tự cài, GPU parallelism và fair CPU–GPU comparison; không gọi là SOTA. Việc tắt cross-check bỏ điều kiện tương hỗ bổ sung để giữ correspondence qua ratio cho S5, nhưng cũng có thể giữ thêm outlier. Tác động chất lượng trên ảnh Nhóm là giả thuyết cần kiểm thử. Bản nhóm tự cài theo [kế hoạch](../archive/midterm-plan.md), mục 9, không thêm OpenCV vào `src/`.

### 1.2. Các phương án matching

| Phương án | Chất lượng và giới hạn | Chi phí, triển khai | Mức phù hợp với đồ án |
|---|---|---|---|
| **Exact brute-force 2-NN Hamming + ratio, cross-check=false (đã chọn)** | Exact neighbors; ratio loại mơ hồ, S5 xử lý outlier hình học còn lại | Duyệt mọi cặp, top-two mỗi A; không dựng index hoặc huấn luyện | Giữ descriptor/interface, dễ đối chiếu CPU–GPU |
| Cross-check riêng hoặc ratio + cross-check (đã cân nhắc, không chọn) | Kiểm tra nearest neighbor tương hỗ, có thể lọc thêm outlier nhưng cũng mất correspondence | Cần tìm NN chiều ngược, reduction/bookkeeping bổ sung | Không thuộc method đã chốt; không bật riêng ở V1 hoặc bản tối ưu |
| Approximate nearest neighbor cho binary descriptor, ví dụ LSH | Có thể bỏ lỡ nearest neighbors thật, ảnh hưởng cả best/second-best và ratio | Thêm hash tables, chi phí dựng index và tham số tìm kiếm; hiệu quả phụ thuộc dữ liệu | Khảo sát khi số descriptor lớn; baseline exact dễ kiểm chứng hơn. Xem [LSH index trong repo OpenCV](https://github.com/opencv/opencv/blob/4.x/modules/flann/include/opencv2/flann/lsh_index.h) |
| Brute-force L2 hoặc index cho descriptor float | Hợp với mô tả gradient số thực; không thay Hamming trên payload binary hiện tại | Chi phí và layout phụ thuộc descriptor | Chỉ xem xét nếu Thành và cả Nhóm đổi S3/interface; S4 không tự quyết thay S3 |
| Learned sparse matching, ví dụ LightGlue | Dùng ngữ cảnh giữa các đặc trưng; có cơ chế thích nghi độ khó | Cần mô hình, trọng số và các phép inference | Phạm vi cài đơn luồng và CUDA thủ công lớn hơn phương án hiện tại; không phải thay thế trực tiếp Hamming |
| Learned detector-free/semi-dense hoặc dense matching | Ước lượng correspondence từ ảnh/features học được; có thể hỗ trợ tình huống descriptor cổ điển khó xử lý | Kéo theo backbone và inference, nhiều buffer và phép tính | Tác động cả S2/S3/S4; cần thiết kế lại pipeline nếu chọn |

Ratio test và cross-check là **bộ lọc**, không phải hai thuật toán tìm nearest neighbor thay thế nhau. Cross-check kiểm tra hai chiều; ratio kiểm tra best có đủ khác biệt với second-best hay không.

Đánh giá về độ khó triển khai và mức phù hợp trong bảng là nhận định thiết kế của Nhóm dựa trên giới hạn đồ án; chưa có so sánh thực nghiệm giữa các phương án trên dataset của Nhóm.

### 1.3. Các hướng nghiên cứu gần đây

Tra cứu có mục tiêu ngày 13/10/2026, gồm nguồn cổ điển, paper hội nghị và preprint gần đây. Không coi danh sách này là tổng quan đầy đủ hoặc xếp hạng phương pháp tốt nhất đến ngày tra cứu.

| Phương pháp | Nguồn gốc và nội dung đã kiểm chứng | Quan hệ với S4 hiện tại |
|---|---|---|
| [LightGlue](https://openaccess.thecvf.com/content/ICCV2023/html/Lindenberger_LightGlue_Local_Feature_Matching_at_Light_Speed_ICCV_2023_paper.html), ICCV 2023 | Learned sparse matcher, thiết kế thích nghi độ khó cặp ảnh; đọc abstract từ CVF | Là hướng matching có mô hình; phải xác định feature extractor phù hợp |
| [Efficient LoFTR](https://openaccess.thecvf.com/content/CVPR2024/html/Wang_Efficient_LoFTR_Semi-Dense_Local_Feature_Matching_with_Sparse-Like_Speed_CVPR_2024_paper.html), CVPR 2024 | Semi-dense matching, cải tiến feature extraction/attention và refinement; đọc abstract từ CVF | Không nhận trực tiếp mảng BRIEF để thực hiện Hamming |
| [EDM](https://openaccess.thecvf.com/content/ICCV2025/html/Li_EDM_Efficient_Deep_Feature_Matching_ICCV_2025_paper.html), ICCV 2025 | Cải tiến pipeline detector-free, correlation injection và subpixel refinement; đọc abstract từ CVF | Cần pipeline học sâu thay cho contract descriptor hiện có |
| [RoMa v2](https://arxiv.org/abs/2511.15706), preprint 2025, bản v3 cập nhật 06/07/2026 | Dense matching, thay đổi kiến trúc/loss và feature foundation model; đọc trang tác giả trên arXiv và abstract | Hướng tham khảo mới cho matching khó; chưa đánh giá tại Nhóm |
| [MV-RoMa](https://arxiv.org/abs/2603.27542), preprint 29/03/2026 | Joint dense matching nhiều view và tạo tracks; đọc abstract arXiv | Bài toán nhiều view rộng hơn yêu cầu ghép đúng hai ảnh |

Các abstract và số liệu của paper không chứng minh một phương pháp sẽ tốt hơn trên ảnh của Nhóm. Không chuyển các tuyên bố speedup của tác giả thành kỳ vọng speedup CUDA của đồ án.

### 1.4. Lý do chọn và tính nhất quán giữa version

Phương án tận dụng đúng `Descriptor::data[8]` hiện có. Exhaustive search cho đáp án exact để đối chiếu V1; kết quả lọc có thể kiểm thử bằng descriptor tự tạo, không cần chờ S3. Hai vòng duyệt A/B cung cấp khối lượng song song cho CUDA. S4 không cần giữ toàn bộ ma trận distance trong RAM.

V0 đến Final giữ exact 2-NN, metric, ratio, cross-check=false, tie-break và output order. Không đổi sang LSH/learned matching, không thêm mutual check hoặc cutoff ở một version. Tiling descriptor, `__popc`, coalesced reads, reduction top-two và compaction giữ thứ tự là tối ưu implementation; phải cho cùng match list như V0. Không early-exit distance nếu làm mất second-best hoặc sai tie-break.

## 2. Đầu vào và đầu ra

Theo [`docs/interface.md`](../interface.md), mục 3, 4, 6 và 8, cùng [`src/common.h`](../../src/common.h). Giữ nguyên kiểu chung. `match_cross_check` vẫn là `uint32_t` 0/1; phương pháp này đặt 0 tường minh, không dùng default 1 hiện có.

| Mục | Quy ước |
|---|---|
| Ảnh | A là ảnh trái, B là ảnh phải |
| Input chính | Hai mảng `Descriptor`, số phần tử `countA`, `countB`; mỗi descriptor có 8 word `uint32_t`, 256 bit, 32 byte, căn 16 byte |
| Quan hệ với keypoint | `descriptorsA[i]` tương ứng `keypointsA[i]`, tương tự B; S3 compact đồng bộ trước khi gọi S4 |
| Cấu hình S4 | `match_ratio_threshold`, `match_cross_check` |
| Distance | Tổng số bit 1 của 8 word XOR, số nguyên trong [0, 256] |
| Output | Mảng `Match` và số match hợp lệ; `indexA`, `indexB` là chỉ số trong mảng đã compact; `distance` là Hamming distance |
| Thứ tự output đã chốt | Tăng theo `indexA`; mỗi A có tối đa một match; nhiều A được phép chọn cùng B |
| Hướng dùng tại S5 | Correspondence `keypointsB[indexB]` → `keypointsA[indexA]`; matching A → B không đổi chiều homography B → A |
| Tọa độ | Gốc trái trên, x sang phải, y xuống dưới, tâm pixel nguyên; S4 không đọc hoặc biến đổi tọa độ |
| Lỗi | Trả `ErrorCode` cho caller; không tự gọi `exit`, không đưa output lỗi sang S5 |

API nằm trong `src/v0_match.h`: `v0_match(FeatureView<Descriptor> left, FeatureView<Descriptor> right, std::vector<Match>& output, const Config& config)`. `FeatureView<T>` trong `src/feature_support.h` chứa pointer/count/capacity, chỉ mượn buffer; caller phải khai báo capacity đúng với allocation thật. Stage kiểm tra metadata và alignment, không thể tự xác minh một pointer tùy ý có allocation thật bao nhiêu byte.

Output là vector Host do caller sở hữu, chỉ publish khi thành công; lỗi làm output rỗng. Buffer tạm dùng RAII. Không truyền vector qua Device và không có log trong hàm stage. Validation theo thứ tự: clear output → S4 config → view metadata/alignment → số ứng viên tối thiểu → thuật toán/số match. `configure_v0_features` trong `src/feature_support.h` chuẩn bị cấu hình đã chốt và tau theo kích thước A, giữ các trường của stage khác; config lỗi được giữ nguyên.

## 3. Tham số

**Cấu hình S4 đã chốt, chưa có kết quả hiệu chỉnh trên dataset.** Mọi version dùng cùng cấu hình.

| Tham số | Giá trị đã chốt | Đơn vị | Lý do và ảnh hưởng |
|---|---|---|---|
| Descriptor và distance | Binary 256 bit; Hamming | Bit, distance [0,256] | Đúng payload hiện có; không chuyển sang Hamming2 hoặc L2 |
| k | `2` | Số láng giềng khác indexB | Cần best và second-best cho ratio |
| `match_ratio_threshold` | `0.80f` | Ratio, 0 < r < 1 | Ngưỡng ban đầu đã chốt; giảm r lọc mạnh, tăng r giữ nhiều ứng viên; không đổi giữa version |
| `match_cross_check` | `false`, lưu `0u` | 0/1 | Không áp điều kiện tương hỗ; S5 chịu trách nhiệm với outlier hình học còn lại |

Nguồn của ratio test là [Lowe (2004), mục 7.1](https://www.cs.ubc.ca/~lowe/papers/ijcv04.pdf). Paper dùng ngưỡng 0.8 trong thí nghiệm SIFT của tác giả. **Đó không phải bằng chứng rằng 0.8 tối ưu cho BRIEF/ORB của Nhóm.** Ở đây dùng Hamming không bình phương và bất đẳng thức chặt theo interface, không sao chép tỷ lệ loại sai/giữ đúng của SIFT sang báo cáo Nhóm.

Quy ước thuật toán đã chốt:

- Forward: lấy hai ứng viên khác `indexB`, xếp theo khóa `(distance, indexB)`.
- Ratio: ngưỡng cố định $0.80=\frac45$, kiểm tra chặt `5u * best_distance < 4u * second_distance`; không chia hoặc bình phương distance. Tích tối đa 1280, không tràn uint32.
- Không tìm NN chiều ngược, không cross-check, không áp ratio test chiều ngược và không ép uniqueness B.
- Không thêm cutoff Hamming tuyệt đối hoặc giới hạn top-M ở lượt này.
- Sau lọc, dưới 4 match trả `InsufficientMatches`, đúng yêu cầu chuẩn bị 4-point homography. Có 4 match chưa bảo đảm hình học không suy biến.

Config vẫn lưu `match_ratio_threshold=0.80f`, nhưng method cố định dùng tỷ lệ nguyên $4/5$ cho phép so sánh. Cách này tránh trường hợp chuyển 0.80f sang double làm cặp $d_1=8$, $d_2=10$ đi qua vì sai số biểu diễn threshold; cặp đúng tỷ lệ 0.80 phải bị loại. Không thay kiểu/layout Config. r khác 0.80f hoặc `match_cross_check=1` không hợp lệ cho pipeline đã chốt này. Nếu cần xem xét lại cấu hình sau kiểm thử, báo lại cho cả Nhóm để cùng quyết định, cập nhật đồng thời mọi version và đo lại; không thay đổi riêng bản CUDA hoặc tối ưu.

## 4. Thuật toán chi tiết

### 4.1. Hamming và top-two

V0 tự đếm bit bằng phép toán scalar, ví dụ vòng lặp xóa bit 1 thấp nhất `v &= v - 1`. Không dùng SIMD viết tay hoặc luồng CPU. Distance tối đa là 256; có thể dùng 257 làm sentinel nội bộ, không ghi sentinel vào `Match::distance`.

`keep_two_smallest_distinct` duy trì hai chỉ số B khác nhau, xét khóa `(distance, indexB)`. **Second-best vẫn được giữ khi distance bằng best**, vì đó là bằng chứng mơ hồ; không tìm second-best có distance lớn hơn best.

### 4.2. Mã giả

```text
clear output
validate counts, input buffers and S4 config
if countA < 1 or countB < 2:
    return InsufficientKeypoints

for i = 0 .. countA - 1:
    best = invalid
    second = invalid
    for j = 0 .. countB - 1:
        d = hamming256(descriptorsA[i], descriptorsB[j])
        keep_two_smallest_distinct(best, second, (d, j))
    (d1, j1) = best
    (d2, j2) = second
    if j1 or j2 is invalid:
        continue
    if not (5 * d1 < 4 * d2):
        continue
    append Match(i, j1, d1) to temporary output

if temporary output count < 4:
    discard temporary output
    return InsufficientMatches
publish temporary output
return Success
```

Input null khi count dương, count âm, vượt miền `int32_t` hoặc kích thước buffer không phù hợp trả `InvalidArgument`. Count hợp lệ nhưng không đủ ứng viên trả `InsufficientKeypoints`. r không hữu hạn/khác 0.80f, hoặc cross-check khác 0 trong method đã chốt trả `InvalidConfig`. Thiếu bộ nhớ trả `AllocationFailed` sau cleanup. Thứ tự ưu tiên validation khi có nhiều lỗi sẽ ghi và kiểm thử ở P1-T12.

### 4.3. Độ phức tạp

Với $n_A,n_B$ descriptor, mỗi cặp cần XOR và popcount 8 word. Thời gian tìm kiếm $O(8n_A n_B)$ khi word cố định; vòng popcount scalar có tối đa 32 lượt/word. Lọc output $O(n_A)$. V0 có thể dùng top-two $O(1)$ cho từng A, cộng output tối đa $O(n_A)$; CUDA có thể dùng buffer top-two/keep flags $O(n_A)$. Không cần reverse buffer hoặc ma trận $n_A n_B$.

Độ phân giải ảnh ảnh hưởng gián tiếp qua số keypoint còn lại sau S3; nếu max-keypoints cố định thì $n_A$/$n_B$ không tăng theo toàn bộ số pixel. Phải in số descriptor khi phân tích timing S4.

## 5. Bằng chứng chất lượng

Đã kiểm tra bằng descriptor có đáp án biết trước: hoán vị B, descriptor giống nhau/khác bit cuối, nhiều A cùng chọn B và ratio biên. Chưa đo precision/recall.

Ngày 18/10/2026, `stitch --version 0 --runs 1 --debug` trên Colab T4 với 4 cặp của dataset, cấu hình ratio 0.80, cross-check=false. Số descriptor là số keypoint còn lại sau S3 (A/B), số inlier lấy từ báo cáo S5 (`final_inliers`):

| Cặp | Kích thước | Descriptor A/B | Match S4 | Inlier S5 |
|---|---|---|---:|---:|
| site1 | small / medium / large | 2000/2000 ở cả 3 | 749 / 635 / 390 | 310 / 274 / 109 |
| site2 | small / medium / large | 2000/2000 ở cả 3 | 420 / 383 / 246 | 186 / 153 / 62 |
| site3 | small / medium / large | 1461/1440, 1684/1780, 1458/1779 | 504 / 471 / 297 | 167 / 160 / 85 |
| challenge | small / medium / large | 2000/2000 ở cả 3 | 697 / 614 / 409 | 440 / 391 / 289 |

Cả 12 lần chạy đều ra panorama. Số match giảm khi ảnh lớn hơn vì `max_keypoints` cố định 2000 trải trên diện tích lớn hơn, còn ratio test giữ nguyên. Trên cặp synthetic (mục 5.5 của `docs/stages/s5-homography.md`), S4 cho 699–1132 match, trong đó 622–1069 là inlier của S5.

Để đo precision/recall trên synthetic, nhãn đúng phải lấy từ correspondence hoặc H ground truth với tolerance hình học đã khai báo. Không dùng chính inlier mask của H ước lượng làm ground truth. Log chi tiết/ảnh debug nằm ngoài vùng timing.

## 6. Mức phù hợp với GPU và mapping V1 dự kiến

### 6.1. Căn cứ từ benchmark V0

V0 dùng vòng `bits &= bits - 1` để đếm bit, chạy đơn luồng. Số đo do Thành chạy ngày 20/10/2026 trong một phiên Colab Tesla T4, CPU Intel Xeon @ 2.00GHz; mỗi cấu hình warm-up một lần rồi đo năm lần. Bảng sau lấy hàng `average` của `results/p3-t04/benchmark/summary.csv`, tỷ trọng tính bằng $p_4=T_{S4}/T_{\mathrm{total}}$.

| Site | Kích thước | S4 (ms) | Tỷ trọng trong Total |
|---|---|---:|---:|
| site1 | small | 682.458 | 61.6% |
| site1 | medium | 677.294 | 40.5% |
| site1 | large | 671.092 | 15.0% |
| site2 | small | 673.140 | 60.4% |
| site2 | medium | 668.359 | 41.4% |
| site2 | large | 664.157 | 14.6% |
| site3 | small | 346.234 | 46.4% |
| site3 | medium | 499.615 | 38.0% |
| site3 | large | 430.840 | 12.3% |

Trung bình cộng tỷ trọng trên ba site là 56.2% ở small, 40.0% ở medium và 14.0% ở large. S4 là hot stage ở cả ba site với small/medium; ở large, hot stage chuyển sang S2 tại site1 và S6 tại site2/site3. S4 phù hợp để ưu tiên triển khai CUDA, nhưng cải thiện riêng S4 không giải quyết toàn bộ thời gian ở large. Đây là đầu vào cho quyết định chung P3-T01, không thay quyết định của cả Nhóm.

Ở site1/site2, log ghi S3 giữ 2000 descriptor mỗi ảnh tại cả ba kích thước. Khi đó S4 xét 4 triệu cặp, bất kể số pixel; điều này giải thích thời gian S4 ít thay đổi theo độ phân giải.

### 6.2. Mapping V1 cơ bản

Thiết kế dự kiến dùng **một block cho một descriptor A**, ban đầu 128 thread/block. Số thread là cấu hình triển khai để đo lại khi có kernel, không thay k, ratio hoặc method. Các buffer đầu vào/đầu ra nằm trên Device; Host chỉ cấp phát, launch và nhận metadata/kết quả khi caller cần.

| Bước | Công việc trên GPU | Output |
|---|---|---|
| Khoảng cách | Block `i` xử lý A[i]; thread `t` duyệt B[j] với `j=t, t+blockDim.x, ...`. Mỗi cặp tính tổng tám `__popc(A[i].word XOR B[j].word)` | Hai ứng viên cục bộ của từng thread |
| Top-two | Lưu ứng viên vào shared memory, reduction trong block theo khóa `(distance,indexB)`; mỗi lần merge giữ hai indexB khác nhau, kể cả khi distance bằng nhau | Best, second-best cho A[i] |
| Ratio | Thread 0 dùng $5d_1<4d_2$, ghi flag và ứng viên vào slot i; thread không có ứng viên dùng sentinel 257/index invalid | Mảng flag và match tạm theo indexA |
| Compact | V1 cơ bản có thể dùng một thread Device quét flag theo i tăng dần, ghi prefix exclusive, sau đó kernel scatter ghi match vào prefix[i] | Match list tăng theo indexA và số match |

Không ghi output cuối bằng atomic append: thứ tự block hoàn thành không bảo đảm thứ tự indexA. Prefix được tính trên Device; bước quét tuần tự là phần hạn chế đã biết của V1, sẽ được đo trước khi thay bằng parallel scan. Tail khi số B không chia hết block size được mask; tất cả thread vẫn phải tới các barrier của block.

GPU không cần lưu ma trận distance $n_A\times n_B$: scratch toàn stage gồm top-two/flag/prefix/match theo A, cỡ $O(n_A)$, cộng scratch theo block đang xử lý. Không có lượt reverse search hoặc ràng buộc mỗi B chỉ được nhận một A. Giữ descriptor trên Device sau S3 và bàn giao match cho S5 để hạn chế round-trip; adapter với vector Host của V0 cần được thống nhất khi cài V1, không đổi interface chung trong P3.

### 6.3. Hướng tối ưu V2/V3 và rủi ro

1. **Tái sử dụng descriptor B:** thử tile shared memory cho nhiều A, hoặc bố trí buffer nội bộ theo word để các lane đọc liên tiếp. Đo bandwidth/cache trước; staging có thể thêm barrier và giảm số block cư trú. Payload/interface ngoài stage vẫn giữ nguyên.
2. **Đổi mức phân chia công việc:** so block/A với warp/A, dùng register/shuffle cho top-two nếu profiling chỉ ra chi phí reduction. Merge phải giữ cả second-best khi bằng distance và giữ tie-break indexB.
3. **Parallel scan và tái sử dụng workspace:** thay bước prefix tuần tự bằng scan có thứ tự, giảm allocation/launch khi có bằng chứng chúng chiếm đáng kể. Không đổi thứ tự match để đổi lấy tốc độ.

`__popc` đếm bit 1 của word 32 bit theo [CUDA Math API 13.0](https://docs.nvidia.com/cuda/archive/13.0.0/cuda-math-api/cuda_math_api/group__CUDA__MATH__INTRINSIC__INT.html). Bố trí bộ nhớ, launch và truyền dữ liệu dựa trên [CUDA Best Practices 13.0](https://docs.nvidia.com/cuda/archive/13.0.0/cuda-c-best-practices-guide/index.html); mapping trên là thiết kế của Nhóm, chưa có kernel hoặc speedup đã đo.

### 6.4. Kiểm chứng V1

Đối chiếu chính xác best/second-best, distance, flag, số match và toàn bộ danh sách `(indexA,indexB,distance)` với V0, gồm ties, ratio đúng ranh giới 4/5, input rỗng/ít B, nhiều A chọn cùng B, tail block và lỗi allocation/config. Chạy lại cùng input và đổi block size vẫn phải cùng output. Sau đó chạy S1–S6 và bộ synthetic ở mục 5.5 tài liệu S5.

Đo S4 bằng CUDA events có đồng bộ đúng, gồm reduction/scan/scatter; ghi riêng chi phí truyền dữ liệu và end-to-end để tránh chỉ báo thời gian kernel distance. Trước khi profiling V1, chưa kết luận compute-bound/memory-bound, occupancy hay speedup.

## 7. Kiểm thử

`tests/test_v0_match.cpp`: 66 checks đạt trên Windows/clang 23.1.3 sau khi gộp file và đạt trên Colab T4 ngày 18/10/2026 (kết quả ở cuối mục). Các fixture filter lặp 4 descriptor A để kiểm tra stage thật; đã kiểm tra từ 1–3 match hợp lệ cũng trả `InsufficientMatches` và không publish output một phần. Allocation failure được kiểm tra riêng cùng S5 trong `tests/test_v0_feature_allocation.cpp`. Không dùng output local làm số liệu chính thức.

| Trường hợp | Kết quả mong đợi |
|---|---|
| Hai descriptor giống nhau; một word/bit khác; tất cả bit khác | Distance lần lượt 0, 1, 256 |
| Các descriptor có correspondence duy nhất, hoán vị thứ tự B | Đúng index A/B sau hoán vị, không ghép theo vị trí mảng |
| Ratio 0.80, d1 = 7, d2 = 10 | Qua ratio |
| Ratio 0.80, d1 = 8, d2 = 10; d1 = 9, d2 = 10 | Không qua; case bằng threshold kiểm tra sai số float bằng quy tắc nguyên 4/5 |
| Hai B giống nhau với d1 = d2 = 0 hoặc d1 = d2 > 0 | Không qua ratio; second-best không bị bỏ qua vì bằng distance |
| Chỉ một B, không có B, không có A | `InsufficientKeypoints` |
| A chọn B, qua ratio, nhưng reverse B sẽ chọn A khác | Vẫn giữ; không có bộ lọc tương hỗ |
| Nhiều A chọn cùng B và qua ratio | Giữ theo indexA, không tự ép uniqueness B; S5 kiểm tra sample trùng tọa độ |
| So sánh scalar exhaustive reference và các implementation | Cùng top-two, match list và order, kể cả ties |
| 0–3 match sau lọc | `InsufficientMatches`, output không hợp lệ/rỗng |
| r là 0, 1, NaN/Inf hoặc khác 0.80f; cross-check = 1 hoặc 2 | `InvalidConfig` cho method đã chốt |
| Input null với count dương; count âm; capacity sai | `InvalidArgument` |
| Chạy lại cùng input/config | Output và thứ tự giống nhau |

Build/test chính thức cần chạy trên Colab T4 từ repo root:

```bash
nvidia-smi
mkdir -p build
nvcc -arch=sm_75 -std=c++11 -O2 -Xcompiler=-Wall,-Wextra,-Werror,-ffp-contract=off -Isrc src/feature_support.cpp src/v0_match.cpp tests/test_v0_match.cpp -o build/test_v0_match
./build/test_v0_match
```

Output mong đợi: `PASS S4: 66 checks; ratio=0.80 cross_check=0 seed=16`. Có thể chạy cả suite bằng `python tests/run_v0_features.py --compiler nvcc --require-t4`; lệnh này kiểm tra GPU T4 trước build.

| Ngày | Môi trường | Lệnh | Kết quả |
|---|---|---|---|
| 18/10/2026 | Colab Tesla T4, CUDA 13.0 (V13.0.88), CPU Intel Xeon @ 2.00GHz | `python3 tests/run_v0_features.py --compiler nvcc --require-t4` | `PASS S4: 66 checks; ratio=0.80 cross_check=0 seed=16`; cả runner `PASS suites: 7, total checks: 5673` |
| 18/10/2026 | Cùng phiên, g++ 13.3.0 | `python3 tests/run_v0_features.py --compiler g++ --sanitizers` | `PASS S4: 66 checks ...` với AddressSanitizer và UndefinedBehaviorSanitizer, không có báo lỗi |

## 8. Trường hợp biên và rủi ro

| Trường hợp | Xử lý hoặc tác động |
|---|---|
| Best và second-best cùng distance | Giữ cả hai ứng viên rồi loại qua ratio |
| Second-best bằng 0 | Không qua ratio; tránh chia cho 0 |
| Nhiều texture lặp | Ratio không chứng minh correspondence đúng hình học; S5 xử lý outlier còn lại |
| Blur, thiếu texture, xoay/scale/ánh sáng khác biệt | Có thể thiếu match do S2/S3; phối hợp với Thành, không tự nới r khi đang benchmark |
| Match tập trung ở một vùng/đường thẳng | Có thể đủ số lượng nhưng homography suy biến; S5 phải phát hiện |
| Nhiều A cùng chọn một B | Hợp lệ ở S4; minimal sample S5 phải loại tọa độ trùng, không thêm cross-check để giải quyết riêng một version |
| Dùng default Config | Default cross-check hiện là 1; phải đặt 0 tường minh trước chạy, không sửa common.h chỉ để đổi default |
| Output không có thứ tự cố định trên GPU | Làm khác chuỗi mẫu RANSAC; cần compaction/order nhất quán |
| Ratio đúng ranh giới 0.80 | So sánh nguyên 4/5 ở mọi version; không đổi sang nhân float/double làm khác kết quả |
| Ghi match một phần khi lỗi | Dọn output tạm, không gọi S5 với kết quả thất bại |

## 9. Nguồn tham khảo

Ngày truy cập: 13/10/2026. Danh mục URL và phạm vi đọc nằm trong [`docs/report/references.md`](../report/references.md), mục S4/S5 của Đế. Nguồn web được dẫn ngay tại phần sử dụng; nguồn local là hai đề bài, kế hoạch và interface.

Nguồn OpenCV cung cấp mô tả để đối chiếu, không phải phụ thuộc được thêm vào `src/`. Các nguồn learned matcher được dùng cho khảo sát, chưa dùng code/trọng số của tác giả.

## 10. Lịch sử thay đổi tham số

| Ngày | Thay đổi | Lý do |
|---|---|---|
| 13/10/2026 | Soạn đề xuất exact Hamming + ratio 0.80 + cross-check, thuật toán và trường hợp biên | Chuẩn bị P0-T11/P1-T11 để Đế lựa chọn; chưa có tham số đã chốt |
| 13/10/2026 | Đế chốt exact 2-NN Hamming 256 bit, ratio 0.80, cross-check=false, output tăng theo indexA | Giữ cùng method/cấu hình từ V0 đến Final; cập nhật mã giả, chi phí và test plan |
| 13/10/2026 | Cài V0 S4, view/config helpers và test; 59 checks local đạt | Không đổi method/tham số; chờ kiểm chứng nvcc trên Colab T4 |
| 13/10/2026 | Gộp view/config vào feature_support.h/.cpp, giữ implementation S4 riêng | Thân hàm và test assertions giữ nguyên; 7 suites/5673 assertions local đạt, bản sau gộp cần chạy lại Colab |
| 18/10/2026 | Không đổi tham số. Tuấn ghi kết quả Colab T4 và kết quả trên dataset | Nghiệm thu P1-T12 |
| 21/10/2026 | Giữ phương pháp, tham số và implementation V0 scalar; bổ sung mục 6 cho P3-T08 | Mapping V1 dự kiến và hướng tối ưu dựa trên benchmark ngày 20/10; chưa cài CUDA hoặc công bố speedup |

## 11. Cài đặt V1 trong P5-T10

Mã nguồn nằm trong `src/v1/s4/`, test trong `tests/gpu/test_gpu_s4_match.cu`. `v1_match()` giữ nguyên contract `DeviceWorkspace`, `Config`, `cudaStream_t`; `common.h` không đổi. Mỗi block xử lý một descriptor A với 128 thread mặc định. Kernel dùng `__popc`, reduction top-two theo `(distance,indexB)`, ratio nguyên `5*d1 < 4*d2`, prefix tuần tự trên Device và scatter có thứ tự. Không cấp phát trong stage, không copy descriptor hoặc match về Host.

Caller cấp scratch theo `v1_match_scratch_bytes(descriptor_capacityA)`. Capacity là dung lượng thực, không phải số phần tử hợp lệ; kernel kiểm tra counts trước khi đọc dữ liệu. Return code của hàm bao phản ánh cấu hình, workspace và launch; lỗi thuật toán được ghi vào `d_counts->status`. Caller phải chờ stream/event và đọc status trước khi dùng output. Khi lọc được ít hơn bốn match hoặc output thiếu capacity, `matches` bằng 0 và không scatter kết quả một phần.

Test ngày 31/10/2026 trên Colab Tesla T4, CUDA 13.0.88: `PASS GPU S4: 2387 checks`. Đối chiếu top-two bằng reference vét cạn độc lập và toàn bộ match list bằng V0. Có input rỗng, chỉ một B, ties, ratio đúng ranh giới, nhiều A chọn cùng B, tail 127/128/129, block 32/64/128/256, thiếu scratch và counts vượt capacity. Compute Sanitizer memcheck báo 0 lỗi. Nhãn NVTX gồm `S4.match`, `S4.nearest_two`, `S4.prefix`, `S4.scatter`.

```bash
python3 tests/run_tests.py --group gpu --suite gpu_s4 --compiler nvcc --require-t4
```

Sáu cặp synthetic từ ảnh nguồn đã kiểm tra SHA-256 đạt so sánh match chính xác giữa V0 và V1 trong `tool_gpu_s45`. Driver dùng V0 cho S1–S3/S6, GPU cho S4/S5; đây là kiểm chứng hai stage. Chương trình `stitch --version 1` vẫn là scaffold của P5-T12. Việc nối đủ sáu stage Device-resident và benchmark chính thức thuộc P6.
