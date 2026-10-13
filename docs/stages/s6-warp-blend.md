# S6 - Warping and blending

Người phụ trách: Chương (23120195). Cập nhật lần cuối: 13/10/2026.

Task hiện tại: **P1-T16 — chốt tham số, viết thuật toán chi tiết và trường hợp biên cho S6** (đã hoàn thành mục 3, 4 và 8). Phương pháp chọn là **inverse warping trên mặt phẳng ảnh A, bilinear interpolation tự tính và feather blending theo khoảng cách đến biên ảnh nguồn**. Giữ phương pháp này cho V0–V3 nếu đạt kiểm chứng chất lượng ở P1. Chưa có code, ảnh kết quả hoặc số đo S6; tài liệu này chưa chứng nhận task P1-T17 đã hoàn thành.

Các quy ước dữ liệu bên dưới là đề xuất ban đầu của S6. P0-T14 đã có [`docs/interface.md`](../interface.md) và `common.h` theo yêu cầu của Chương, gồm Homography float32 và stride byte; bản interface còn cần cả Nhóm góp ý và thống nhất trước khi cài pipeline thật. Dataset đã chụp và chuẩn bị đầy đủ theo xác nhận của Chương; chưa chạy S6 trên dataset đó.

## 1. Phương pháp đã chọn và các phương án đã cân nhắc

### 1.1. Phạm vi và căn cứ lựa chọn

S6 nhận hai ảnh màu gốc A, B và homography từ S5 để tạo panorama. Theo [đề cuối kỳ, mục 2.1 và 4.1](../specs/CSC14120_2026_Final%20Project.md), H đưa B sang hệ A. S6 không tìm lại keypoint, không ước lượng lại H và không thay homography toàn cục bằng optical flow hay local mesh.

Tiêu chí chọn: chất lượng chấp nhận được trên ba site chuẩn; tự cài bằng C/C++ và CUDA trong giới hạn thư viện của Nhóm; kiểm thử riêng được; chuyển cùng công thức lên GPU được; chi phí và bộ nhớ có thể đo, giải thích. Đề mục 3 bắt buộc cùng phương pháp và tham số trong mọi phiên bản. Độ mới của paper là thông tin tham khảo, không tự chứng minh một phương pháp phù hợp với đồ án.

Szeliski trình bày compositing gồm lựa chọn hệ quy chiếu, lựa chọn/đặt trọng số pixel và blending; đây là các vấn đề liên quan nhưng khác nhau [R1, mục 6]. Inverse warping xử lý việc lấy mẫu; blending xử lý sự chuyển tiếp giữa nguồn ảnh. Blending không thay thế căn chỉnh hình học.

### 1.2. So sánh warping và lấy mẫu

| Phương án | Chất lượng và giới hạn | Chi phí / khả năng lên GPU | Quyết định |
|---|---|---|---|
| Forward warp kiểu scatter, làm tròn mỗi pixel nguồn | Có thể bỏ sót pixel đích hoặc ghi đè nhiều lần; không phải mọi forward warp đều có lỗi này, các biến thể splatting/rasterization có thể xử lý | Ghi phân tán, có thể cần giải quyết xung đột | Không chọn biến thể scatter đơn giản |
| Inverse warp + nearest | Mỗi pixel đích chủ động truy vấn nguồn; dễ xuất hiện răng cưa khi tọa độ không nguyên | Một mẫu nguồn, dễ kiểm thử và map thread | Phương án đối chứng lấy mẫu ở P1 |
| **Inverse warp + bilinear tự tính** | Nội suy bốn mẫu, chuyển tiếp mượt hơn nearest; không phải bộ lọc chống aliasing đầy đủ khi ảnh bị thu nhỏ mạnh | Công việc độc lập theo pixel, không cần thư viện thuật toán | **Chọn sơ bộ cho mọi phiên bản** |

Cơ sở về hệ quy chiếu và resampling: [R1, mục 6.1]. Mục tiêu là không tạo lỗ do scatter rời rạc trong vùng có nguồn hợp lệ. Phần canvas ngoài cả hai ảnh vẫn có nền; không hứa phủ kín hình chữ nhật panorama.

### 1.3. So sánh blending

| Phương án | Chất lượng và giới hạn | Chi phí / khả năng lên GPU | Quyết định |
|---|---|---|---|
| Overwrite hoặc average 50/50 | Overwrite có thể lộ đường nối; average dễ tạo ảnh kép khi lệch | O(1) mỗi pixel, ít trạng thái | Chỉ làm đối chứng chất lượng |
| **Feather theo khoảng cách đến biên nguồn** | Chuyển tiếp trọng số theo vị trí; không sửa parallax, vật chuyển động hoặc chênh phơi sáng lớn | O(1) mỗi pixel với công thức biên chữ nhật; không cần graph/pyramid | **Chọn sơ bộ** |
| Seam finding + multi-band | Có thể giảm artifact trong một số tình huống; cần solver, mask và nhiều tầng ảnh; vẫn có giới hạn khi lệch lớn | Nhiều bước, buffer và dependency; phải tự cài cả V0 lẫn GPU | Chưa đưa vào phương pháp chính |
| Adaptive blending rút gọn từ SC-AOF | Có căn cứ để khảo sát; cần định nghĩa đầy đủ trọng số và ablation | Thêm đánh giá màu và hàm phi tuyến; hiệu quả trên dataset chưa biết | Phương án cân nhắc nếu feather không đạt |
| Semantic/optical-flow/neural stitching | Can thiệp sâu vào căn chỉnh hoặc biểu diễn ảnh, vượt phần S6 hiện tại | Cần thêm mô hình, solver hoặc hạ tầng ngoài giới hạn hiện hành | Related work và giới hạn, không cam kết cài |

Brown và Lowe giải thích vì sao linear blending có thể mờ chi tiết khi còn sai số đăng ký; multi-band trộn tần số thấp trên vùng rộng và cao trên vùng hẹp [R2, mục 7]. Paper cũng ghi nhận artifact khi vật thể chuyển động lớn [R2, mục 9]. Điều này hỗ trợ việc ghi rõ giới hạn feather, không bảo đảm multi-band loại bỏ mọi ghosting. Nền tảng multiresolution spline là Burt và Adelson [R3].

### 1.4. Phản biện bản đề xuất A

Bản A là tài liệu đính kèm mở đầu bằng “Chào Chương! Với vai trò Senior Architect/Lead Technical…”, attachment `50f15dad-2a4f-4570-9cb0-0d121bcc70b0`. Điểm hữu ích là lựa chọn inverse warp/bilinear và phân biệt seam với blending. Các điều chỉnh:

| Vị trí trong bản A | Nhận xét | Điều chỉnh trong bản cuối |
|---|---|---|
| Mục 4: V0 feather, V3 multi-band | Đổi phương pháp giữa phiên bản, trái đề mục 3 | Giữ feather ở cả V0–V3; tối ưu cách cài theo profiling |
| Mục 1: không seams/ghosting/mờ; S6 tiêu tốn bộ nhớ lớn nhất | Cam kết vượt bằng chứng; chưa có dataset results hoặc profiling | Đặt mục tiêu có điều kiện, công khai failure case và đo bộ nhớ/thời gian |
| Step 6.1: dùng H nghịch đảo trên canvas | Chưa định nghĩa offset; công thức chỉ đúng nếu tọa độ đã ở hệ A | Bổ sung T và chuỗi H^-1 T^-1 ở mục 2 |
| Step 6.2: graph cut trên ROI, tăng tốc 140–153 lần | Kết quả paper bị mở rộng sang một cấu hình khác | Giữ làm tài liệu tham khảo, không dự báo speedup nhóm |
| Step 6.3: gain compensation và pyramid | Có tên bước nhưng thiếu estimator, mask, biên và quy tắc tái tạo | Không đưa vào pipeline chính khi chưa định nghĩa/cài chung mọi phiên bản |
| Mục 4: streams cho các pyramid levels | Các tầng cùng pyramid phụ thuộc nhau | Nếu khảo sát sau này, chỉ chạy nhánh độc lập đồng thời, giữ dependency giữa levels |

Con số của Kim et al. 2018 là **153× CPU và 140× GPU riêng cho seam-mask estimation**, video 640×480, trung bình 2000 frames, resized-scale 10 [R4, mục 4.2.2, bảng 2]. Đây không phải speedup end-to-end, không phải kết quả CUDA T4 của Nhóm và không chứng minh chọn scale 1/4 sẽ đạt mức đó. Paper sử dụng OpenCV/OpenCL; chỉ tham khảo ý tưởng, không lấy các dependency đó vào `src/`.

Nếu dùng Laplacian pyramid, phép tái tạo phải đưa các mức về cùng kích thước, chẳng hạn S_L=L_L và S_l=L_l+EXPAND(S_(l+1), shape_l). Cách viết tổng các mức với một lần EXPAND mỗi mức trong bản A không đủ chính xác. Đây là sửa lỗi định nghĩa thuật toán, không phải phần S6 sẽ cài ở P0.

### 1.5. Phản biện bản đề xuất B

Bản B là tài liệu đính kèm mở đầu bằng “Cảm ơn Chương! Việc chủ động cập nhật các công trình nghiên cứu mới nhất năm 2024…”, attachment `595e69fa-2c3f-462f-b8bc-6bca7447a063`. Các paper được nêu có tồn tại, nhưng việc kết hợp chúng chưa tạo thành thuật toán đã được kiểm chứng:

| Vị trí trong bản B | Nhận xét | Điều chỉnh trong bản cuối |
|---|---|---|
| Mục IV: V2 thêm seam, V3 thêm multi-band | Cũng đổi phương pháp giữa phiên bản | Không đưa lộ trình này vào benchmark V0–V3 |
| SC-AOF: lambda_d=tanh(c_d * màu sai khác) | Chỉ một hệ số, chưa định nghĩa lambda, beta, norm màu, scale, coefficients hay mask | Không gọi đây là cài đầy đủ SC-AOF; chưa chọn làm baseline |
| Cost seam: màu + gamma * tổng gradient | Là heuristic giản lược của bản đề xuất; chưa có graph, ràng buộc/solver hoặc chứng cứ tương đương Jia | Không gán công thức này cho Jia; để hướng khảo sát |
| Ghép adaptive width với multi-band | Chưa định nghĩa mask theo level hoặc phép phối hợp hai cơ chế | Không khẳng định chất lượng của tổ hợp khi chưa có ablation |
| Neural/inpainting “xử lý triệt để parallax”, “khả thi 100%” | Không có bảo đảm tổng quát hoặc kiểm chứng dự án | Trình bày như phương pháp khác và giới hạn, bỏ cam kết |

SC-AOF định nghĩa alpha=(1-lambda_d)*lambda+lambda_d*beta sau khi tính lambda_d; beta của phương pháp đầy đủ liên quan optical-flow magnitude. Đáng chú ý, tác giả **có gợi ý đặt flow bằng 0** để dùng blending trong phương pháp khác [R5, mục 3.2, công thức 14–18 và phần thảo luận]. Vì vậy bỏ flow không tự thân là sai; thiếu định nghĩa và kiểm chứng mới là điểm yếu của bản B. Sai khác màu cũng không tự phân biệt texture, chuyển động và thay đổi phơi sáng.

Jia dùng local mapping trên superpixels, cost màu/cấu trúc/entropy/ngữ nghĩa, graph và Poisson blending [R6, mục 2]. Đây là framework rộng hơn một kernel gradient-cost. Chen dùng optical flow, lấp vùng thiếu bằng ảnh đích và inpainting [R7, abstract]; NIS dùng Fourier features, blending trong latent space và giải mã RGB [R8, abstract]. Hai hướng này là căn cứ thảo luận phương pháp khác, không phải bằng chứng nâng cấp S6 hiện tại sẽ thành công.

### 1.6. Quyết định sau phản biện

Chọn pipeline nhỏ đủ để kiểm chứng: **canvas/offset → inverse sampling và validity → feather composite**. Không có seam finder, gain compensation, optical flow, adaptive color weight hoặc pyramid trong phương pháp chính hiện tại.

```mermaid
flowchart LR
    A["Ảnh RGB A và B"] --> G["Canvas, offset, kiểm tra H"]
    H["H từ S5: B sang A"] --> G
    G --> W["Inverse warp và bilinear"]
    W --> V["Xác định nguồn hợp lệ"]
    V --> B["Feather composite"]
    B --> P["Panorama RGB"]
```

Đây là lựa chọn kỹ thuật sơ bộ theo phạm vi P0-T13, không phải kết luận feather tốt nhất trên mọi dataset. Nếu kiểm chứng P1 cho thấy không đạt chất lượng, Chương phối hợp với Đế phân biệt lỗi H và lỗi blend. Khi đổi phương pháp, phải cập nhật baseline và các phiên bản cùng phương pháp, chạy lại benchmark; không chỉ thêm thuật toán vào V3.

## 2. Đầu vào và đầu ra

### 2.1. Contract dữ liệu đề xuất

| Thành phần | Quy ước đề xuất | Trạng thái |
|---|---|---|
| Ảnh A, B | Ảnh màu gốc đã đọc bằng stb; RGB interleaved `uint8_t`, miền [0,255], row-major | Cần chốt ở P0-T14 |
| Kích thước | Mỗi ảnh có width/height riêng, đều dương; không giả định luôn bằng nhau | Cần chốt ở P0-T14 |
| Stride | Byte mỗi hàng, có khai báo; trường hợp packed là 3 * width | Cần chốt ở P0-T14 |
| Tọa độ | Gốc trên trái; x sang phải, y xuống dưới; tâm pixel ở tọa độ nguyên | Cần chốt ở P0-T14 |
| Homography H | Ma trận `float[9]` row-major, tác động lên vector cột, chiều B → A; tính toán nội bộ có thể dùng double | Theo yêu cầu mới P0-T14; cả Nhóm cần xác nhận |
| H nghịch đảo | S6 tự tính và kiểm tra từ H; không bắt S5 trả thêm H^-1 | Đề xuất ranh giới trách nhiệm |
| Cấu hình | Các trường S6 trong struct cấu hình chung; không hard-code khác nhau theo version | Giá trị ở P1-T16 |
| Panorama | RGB `uint8_t`, row-major; width/height/stride của canvas và offset A → canvas | Cần chốt ở P0-T14 |
| Lỗi | Trạng thái thất bại thay vì ảnh giả thành công; main xử lý thông báo và exit code | Mã lỗi cụ thể chưa chốt |

Ảnh xám đã blur từ S1 không phải nguồn màu của S6. Không làm thay đổi bộ nhớ ảnh đầu vào. H phải hữu hạn, khả nghịch và đủ ổn định để sử dụng; không mặc định h33 khác 0 trong mọi homography hợp lệ. Quy tắc chuẩn hóa và tolerance do S5/S6 cùng thống nhất.

Panorama có kích thước phụ thuộc H, không buộc bằng ảnh đầu vào hoặc giữ 16:9. Đầu ra không tự crop hay resize sau blend vì làm thay đổi miền kiểm chứng.

### 2.2. Canvas và hệ tọa độ

Đề xuất miền tâm pixel của ảnh kích thước W×H là [0,W-1] × [0,H-1]. Dùng bốn góc của miền này cho canvas; không trộn với quy ước góc ở W,H. Các công thức dưới đây là thiết kế đề xuất của S6, chưa phải interface chung đã được chốt.

1. Kiểm tra H và mẫu số phép chiếu trên miền B. Mẫu số ở các góc phải cùng dấu và cách 0 đủ theo tolerance đã thống nhất. Nếu horizon đi qua miền ảnh, từ chối phép chiếu trước khi lấy bounding box; bốn góc hữu hạn riêng lẻ không bảo đảm toàn miền bị chặn.
2. Chiếu bốn góc B sang hệ A; hợp với bốn góc A để có xmin, xmax, ymin, ymax.
3. Đặt x0=floor(xmin), x1=ceil(xmax), y0=floor(ymin), y1=ceil(ymax).
4. Kích thước canvas: Wc=x1-x0+1, Hc=y1-y0+1. Offset ox=-x0, oy=-y0.

Ma trận đưa A sang canvas:

\[
T=\begin{bmatrix}1&0&o_x\\0&1&o_y\\0&0&1\end{bmatrix}.
\]

Với pixel canvas pC=(xc,yc,1), tọa độ truy vấn nguồn là:

\[
p_A=T^{-1}p_C,\qquad
p_B\sim H^{-1}T^{-1}p_C=(TH)^{-1}p_C.
\]

Sau mỗi phép biến đổi projective, chia hai tọa độ đầu cho thành phần thứ ba; kiểm tra hữu hạn và mẫu số trước khi chia. Thứ tự nhân ma trận không được đảo.

Ví dụ kiểm tra bằng đại số, chưa phải kết quả chạy code: A và B cùng 4×3, H tịnh tiến B theo x=-2, y=0. Miền hợp theo x là [-2,3], canvas 6×3, offset (2,0). Pixel canvas (0,0) ứng với A(-2,0), B(0,0); chỉ B hợp lệ. Identity cho hai ảnh cùng kích thước phải giữ nguyên kích thước canvas.

Kiểm tra tràn số, giới hạn width/height, tích số pixel/byte và ngân sách bộ nhớ trước cấp phát. Công thức bbox cần quy tắc xử lý sai số sát số nguyên để V0 và GPU không khác canvas; quy tắc cụ thể thuộc P1-T16.

### 2.3. Sampling, validity và feather weight đề xuất

Nguồn i hợp lệ nếu tọa độ hữu hạn và nằm trong miền tâm pixel [0,Wi-1] × [0,Hi-1]. Kiểm tra miền trước khi clamp; không kéo dài ảnh ngoài nguồn bằng cách clamp mọi tọa độ truy vấn. Validity được biểu diễn bằng cờ/mask riêng, không suy ra từ RGB bằng 0.

Với một tọa độ hợp lệ (x,y), đặt i=floor(x), j=floor(y), a=x-i, b=y-j. Bilinear cho từng kênh dùng:

\[
C(x,y)=(1-a)(1-b)C_{i,j}+a(1-b)C_{i+1,j}
       +(1-a)bC_{i,j+1}+abC_{i+1,j+1}.
\]

Chỉ số neighbor ở mép phải/dưới được clamp vào pixel cuối **sau khi xác nhận tọa độ hợp lệ**. Vì vậy pixel cuối và ảnh 1×1 vẫn có định nghĩa. Kiểu trung gian và cách round/clamp RGB đầu ra cần chốt ở P1-T16 rồi giữ chung giữa các phiên bản.

Đề xuất trọng số của S6 tại tọa độ nguồn hợp lệ:

\[
d_i=\min(x_i+0.5,\ W_i-0.5-x_i,\ y_i+0.5,\ H_i-0.5-y_i).
\]

Đây là khoảng cách đến biên vật lý hình chữ nhật của nguồn, tính trong **pixel nguồn**, không phải distance transform của mask trên canvas. Cộng 0.5 giúp dương cả tại tâm pixel biên, tránh trường hợp cả hai trọng số bằng 0. Đây là lựa chọn thiết kế đề xuất của Nhóm, không sao chép nguyên hàm trọng số Brown–Lowe. Biến dạng projective có thể làm ý nghĩa khoảng cách khác với đo trong canvas; cần đánh giá artifact ở P1.

| Tình huống | Giá trị composite trước chuyển về `uint8_t` |
|---|---|
| Chỉ A hợp lệ | CA |
| Chỉ B hợp lệ | CB |
| Cả A và B hợp lệ | (dA * CA + dB * CB) / (dA + dB), theo từng kênh |
| Không nguồn hợp lệ | Màu nền quy định trong cấu hình; đề xuất RGB (0,0,0) |

Các cờ hợp lệ có thể tính tại chỗ; không bắt buộc lưu hai mask full-canvas. Ảnh panorama nền đen không có nghĩa mọi pixel đen đều không hợp lệ. Khi debug cần mask phân biệt hai trường hợp.

Đề xuất bản đầu blend trực tiếp giá trị RGB đã giải mã, không hiệu chỉnh gamma/phơi sáng. Đây là đơn giản hóa thiết kế; không tuyên bố tương đương pha trộn ánh sáng tuyến tính. Nếu đổi color space hoặc gain sau này phải đổi chung baseline và các phiên bản.

### 2.4. Ownership và phối hợp

Đề xuất ảnh đầu vào thuộc bên gọi; S6 tạo metadata canvas trước, bên gọi cấp phát/ sở hữu output theo kích thước đã kiểm tra. S6 sở hữu buffer tạm nếu có và giải phóng theo quy ước chung. Cách biểu diễn bằng con trỏ, vector hay view chưa chốt; P0-T13 không áp đặt signature cho `common.h`.

Đế và Chương cần thống nhất chiều/layout H, pixel center, normalization, error contract và chất lượng H. Chương cùng cả Nhóm chốt ảnh/stride, cấu hình, output ownership và timing trong P0-T14/P0-T04.

## 3. Tham số

Các giá trị dưới đây là cấu hình thiết kế cho S6, dùng thống nhất ở V0 và V1. Chưa có kết quả thực nghiệm để xác nhận chất lượng hoặc hiệu năng.

| Tham số | Giá trị | Đơn vị | Lý do chọn | Ảnh hưởng khi tăng/giảm |
|---|---|---|---|---|
| Tâm pixel | Tọa độ nguyên; pixel đầu tiên ở `(0,0)` | Pixel | Thống nhất với keypoint và interface chung | Đổi sang tâm `.5` phải sửa toàn bộ công thức và kiểm thử |
| Kiểu tính toán trung gian | `double` cho transform, inverse, interpolation và blending; H đầu vào vẫn là `float[9]` | — | Giảm sai số tích lũy trước khi chuyển sang chỉ số nguyên | Đổi sang `float` có thể tăng tốc nhưng phải kiểm chứng lại |
| Ngưỡng quy về tọa độ nguyên `EPS_COORD` | `1e-6` | Pixel | Nếu tọa độ cách số nguyên gần nhất không quá ngưỡng này, quy về số nguyên đó trước khi tính bbox hoặc sampling | Tăng làm nhiều điểm bị dịch nhẹ; giảm dễ giữ sai số sát biên |
| Quy tắc bbox | Sau `snap_integer()`: `floor(min)` và `ceil(max)` | Pixel | Bao phủ miền tâm pixel của cả hai ảnh | Dùng cast trực tiếp hoặc `round()` cho bbox có thể cắt mất mép |
| Quy tắc chỉ số bilinear | `floor(x)`, `floor(y)` sau `snap_integer()` | Pixel | Lấy pixel phía trên/trái và giữ phần lẻ làm trọng số | Dùng `round()` làm thay đổi ô nội suy |
| Tolerance mẫu số `EPS_W` | `1e-6`, kiểm tra tương đối: `abs(w) <= EPS_W * s`, với `s = abs(m20*x) + abs(m21*y) + abs(m22)` | Không đơn vị | Phát hiện mẫu số gần 0 do cancellation; không phụ thuộc hệ số scale của ma trận | Tăng từ chối nhiều điểm hơn; giảm cho phép phép chiếu gần horizon và tọa độ lớn |
| Ngưỡng pivot khi nghịch đảo `EPS_PIVOT` | `1e-12`, so với scale hàng | Không đơn vị | Kiểm tra pivot nhỏ trong phép nghịch đảo bằng `double` | Tăng có thể loại ma trận còn dùng được; giảm có thể nhận ma trận mất ổn định |
| Ngưỡng điều kiện nghịch đảo `EPS_RCOND` | `1e-12`; yêu cầu `1 / (normInf(H) * normInf(H_inv)) > EPS_RCOND` | Không đơn vị | Bổ sung kiểm tra độ ổn định, không chỉ dựa vào determinant | Tăng chặt hơn; giảm chấp nhận nhiều ma trận ill-conditioned hơn |
| Màu nền | RGB `(0,0,0)` | Giá trị màu `[0,255]` | Có giá trị xác định khi không nguồn nào hợp lệ | Đổi màu chỉ thay vùng nền |
| Quy tròn màu output | `floor(clamp(C,0,255) + 0.5)` rồi chuyển `uint8_t` | Giá trị màu | Cùng quy tắc làm tròn half-up cho CPU/GPU | Đổi quy tắc có thể làm khác một đơn vị màu |
| Giới hạn chiều canvas | `Wc <= 10,000`, `Hc <= 10,000` | Pixel | Giới hạn tài nguyên và tránh canvas bất thường | Tăng cho phép output lớn hơn nhưng tăng nguy cơ OOM |
| Giới hạn diện tích canvas | `max_canvas_pixels = 100,000,000` | Pixel | Phù hợp giới hạn hai chiều; RGB packed tối đa cần 300,000,000 byte riêng cho output | Tăng cần thêm bộ nhớ; giảm từ chối canvas sớm hơn |

Định nghĩa phép quy về số nguyên:

```cpp
double snap_integer(double t) {
    // Caller must establish that t is finite.
    double nearest = floor(t + 0.5);
    return abs(t - nearest) <= EPS_COORD ? nearest : t;
}
```

`EPS_COORD` là tolerance thiết kế, không bảo đảm mọi phép tính CPU/GPU tự động cho cùng kết quả. V0/V1 phải dùng cùng precision, thứ tự phép toán và chính sách FMA; không bật fast math riêng một phiên bản. Phép nhân ma trận bên dưới dùng FMA tường minh với cùng thứ tự. Vẫn phải kiểm tra canvas, offset và validity giữa hai phiên bản trước khi so màu. [NVIDIA: Floating Point and IEEE 754](https://docs.nvidia.com/cuda/floating-point/index.html).

## 4. Thuật toán chi tiết

Quy ước: **H đưa ảnh B sang hệ A; H⁻¹ đưa tọa độ trong hệ A về ảnh B để lấy mẫu**. Tọa độ canvas phải trừ offset trước khi áp dụng H⁻¹.

Các hàm hỗ trợ trong mã giả:

```cpp
bool project(Mat3 M, double x, double y, Point& p) {
    double u = fma(M[0], x, fma(M[1], y, M[2]));
    double v = fma(M[3], x, fma(M[4], y, M[5]));
    double w = fma(M[6], x, fma(M[7], y, M[8]));

    double s = (abs(M[6] * x) + abs(M[7] * y)) + abs(M[8]);

    if (!finite(u, v, w, s) || s == 0.0 ||
        abs(w) <= EPS_W * s)
        return false;

    p = {u / w, v / w};
    return finite(p.x, p.y);
}

bool source_valid(Point& p, int W, int H) {
    if (!finite(p.x, p.y))
        return false;

    p.x = snap_integer(p.x);
    p.y = snap_integer(p.y);

    return 0.0 <= p.x && p.x <= W - 1 &&
           0.0 <= p.y && p.y <= H - 1;
}
```

`Mat3` và `Point` là ký hiệu mã giả, không yêu cầu thư viện ngoài. `read_rgb()` đọc theo stride byte của `Image`.

### Khối 1: Canvas Bounding Box và Offset

```cpp
ErrorCode prepare_canvas(Image A, Image B, Homography input,
                         Mat3& H, Mat3& H_inv, CanvasInfo& canvas) {
    if (!valid_rgb_view(A) || !valid_rgb_view(B))
        return ErrorCode::InvalidImage;

    H = convert_to_double(input.data);

    if (!all_finite(H))
        return ErrorCode::NumericalFailure;

    double scale = max_abs_coefficient(H);
    if (scale == 0.0)
        return ErrorCode::DegenerateHomography;

    H /= scale;  // Do not assume h22 != 0.

    // Scaled partial pivoting; no OpenCV or Eigen.
    if (!invert_scaled_pivot(H, EPS_PIVOT, H_inv))
        return ErrorCode::DegenerateHomography;

    double condition_product = normInf(H) * normInf(H_inv);
    if (!all_finite(H_inv) || !isfinite(condition_product) ||
        condition_product == 0.0 ||
        1.0 / condition_product <= EPS_RCOND)
        return ErrorCode::DegenerateHomography;

    Point cornersB[4] = {
        {0, 0}, {B.width - 1, 0},
        {0, B.height - 1}, {B.width - 1, B.height - 1}
    };

    Point cornersA[4] = {
        {0, 0}, {A.width - 1, 0},
        {0, A.height - 1}, {A.width - 1, A.height - 1}
    };

    int denominator_sign = 0;
    Point warpedB[4];

    for (int i = 0; i < 4; ++i) {
        double x = cornersB[i].x;
        double y = cornersB[i].y;
        double w = fma(H[6], x, fma(H[7], y, H[8]));
        double s = (abs(H[6] * x) + abs(H[7] * y)) + abs(H[8]);

        if (!finite(w, s) || s == 0.0 || abs(w) <= EPS_W * s)
            return ErrorCode::NumericalFailure;

        int current_sign = w > 0.0 ? +1 : -1;
        if (i == 0)
            denominator_sign = current_sign;
        else if (current_sign != denominator_sign)
            return ErrorCode::NumericalFailure; // Horizon intersects B.

        if (!project(H, x, y, warpedB[i]))
            return ErrorCode::NumericalFailure;

        warpedB[i].x = snap_integer(warpedB[i].x);
        warpedB[i].y = snap_integer(warpedB[i].y);
    }

    double xmin, xmax, ymin, ymax;
    bounds_of_eight_points(cornersA, warpedB, xmin, xmax, ymin, ymax);

    // Check finite values and int64 range BEFORE casting.
    int64_t x0, x1, y0, y1;
    if (!checked_int64(floor(xmin), x0) ||
        !checked_int64(ceil(xmax),  x1) ||
        !checked_int64(floor(ymin), y0) ||
        !checked_int64(ceil(ymax),  y1))
        return ErrorCode::InvalidCanvas;

    int64_t Wc, Hc, Offset_X, Offset_Y;
    if (!checked_subtract_add(x1, x0, 1, Wc) ||
        !checked_subtract_add(y1, y0, 1, Hc) ||
        !checked_negate(x0, Offset_X) ||
        !checked_negate(y0, Offset_Y))
        return ErrorCode::InvalidCanvas;

    if (Wc <= 0 || Hc <= 0 || Wc > 10000 || Hc > 10000 ||
        !fits_int32(Offset_X) || !fits_int32(Offset_Y))
        return ErrorCode::InvalidCanvas;

    size_t pixels, row_bytes, bytes;
    if (!checked_multiply(Wc, Hc, pixels) ||
        pixels > 100000000 ||
        !checked_multiply(Wc, 3, row_bytes) ||
        !checked_multiply(row_bytes, Hc, bytes))
        return ErrorCode::InvalidCanvas;

    canvas = {Wc, Hc, Offset_X, Offset_Y, row_bytes, bytes};
    return ErrorCode::Success;
}
```

Công thức khung:

\[
W_c=\lceil x_{\max}\rceil-\lfloor x_{\min}\rfloor+1,\qquad
H_c=\lceil y_{\max}\rceil-\lfloor y_{\min}\rfloor+1
\]

\[
Offset_X=-\lfloor x_{\min}\rfloor,\qquad
Offset_Y=-\lfloor y_{\min}\rfloor.
\]

Các extrema đã được `snap_integer()` theo quy tắc thống nhất. Kiểm tra dấu mẫu số ở bốn góc có ý nghĩa vì mẫu số là hàm affine trên miền chữ nhật: khi cùng dấu và không gần 0 tại các góc, horizon không cắt miền đó.

### Khối 2: Inverse Warping và Bilinear Interpolation

```cpp
RGB bilinear(Image image, Point p) {
    // Precondition: source_valid(p, width, height) == true.
    int x0 = int(floor(p.x));
    int y0 = int(floor(p.y));
    int x1 = min(x0 + 1, image.width  - 1);
    int y1 = min(y0 + 1, image.height - 1);

    double ax = p.x - x0;
    double ay = p.y - y0;

    RGB C00 = read_rgb(image, x0, y0);
    RGB C10 = read_rgb(image, x1, y0);
    RGB C01 = read_rgb(image, x0, y1);
    RGB C11 = read_rgb(image, x1, y1);

    RGB result;
    for (int c = 0; c < 3; ++c) {
        double top    = (1.0 - ax) * C00[c] + ax * C10[c];
        double bottom = (1.0 - ax) * C01[c] + ax * C11[c];
        result[c] = (1.0 - ay) * top + ay * bottom;
    }
    return result; // Keep double; do not round each sample to uint8.
}

for (int yc = 0; yc < Hc; ++yc) {
    for (int xc = 0; xc < Wc; ++xc) {
        Point pA = {
            double(xc) - Offset_X,
            double(yc) - Offset_Y
        };

        Point pB;
        bool projectedB = project(H_inv, pA.x, pA.y, pB);

        bool validA = source_valid(pA, A.width, A.height);
        bool validB = projectedB &&
                      source_valid(pB, B.width, B.height);

        RGB Ca, Cb;
        if (validA) Ca = bilinear(A, pA);
        if (validB) Cb = bilinear(B, pB);

        // Apply Block 3 and store one output pixel.
    }
}
```

Chỉ clamp **chỉ số neighbor** sau khi tọa độ được xác nhận hợp lệ. Không clamp mọi tọa độ ngoài ảnh về mép nguồn. Quy tắc này hỗ trợ cả pixel cuối và ảnh `1×1`.

Nếu H⁻¹ không chiếu được một pixel canvas, pixel đó không có nguồn B hợp lệ. Đây không tự động là lỗi toàn S6: điểm canvas có thể nằm ngoài footprint của B; nguồn A vẫn được sử dụng nếu hợp lệ.

### Khối 3: Feather Blending Composite

Với tâm pixel nguyên, biên vật lý của nguồn nằm tại `-0.5` và `W-0.5`, `H-0.5`:

```cpp
double distance_weight(Point p, int W, int H) {
    // Precondition: p is a valid source coordinate.
    return min(
        min(p.x + 0.5, W - 0.5 - p.x),
        min(p.y + 0.5, H - 0.5 - p.y)
    );
}

RGB composite = {0.0, 0.0, 0.0};

if (validA && validB) {
    double da = distance_weight(pA, A.width, A.height);
    double db = distance_weight(pB, B.width, B.height);
    double denominator = da + db; // Strictly positive for valid coordinates.

    for (int c = 0; c < 3; ++c)
        composite[c] = (da * Ca[c] + db * Cb[c]) / denominator;

} else if (validA) {
    composite = Ca;

} else if (validB) {
    composite = Cb;

// Otherwise retain RGB (0,0,0).
}

if (!all_finite(composite))
    return ErrorCode::NumericalFailure;

for (int c = 0; c < 3; ++c)
    output(xc, yc, c) =
        uint8_t(floor(clamp(composite[c], 0.0, 255.0) + 0.5));
```

Trọng số được đo trong **pixel nguồn**, không phải khoảng cách trên canvas. Với tọa độ hợp lệ, mỗi trọng số ít nhất `0.5`, nên không cần cộng epsilon tùy ý vào mẫu số blending. Pixel RGB đen vẫn là dữ liệu hợp lệ; validity không suy ra từ màu.

Với `P = Wc × Hc`, render có thời gian `O(P)`, bộ nhớ output `O(P)` và không cần lưu hai ảnh đã warp đầy đủ. Đây là phân tích thuật toán, chưa phải kết quả profiling.

## 5. Bằng chứng chất lượng

Chưa có. P1-T17 phải bổ sung ảnh output, mask/debug phù hợp, kết quả tests, môi trường và số đo thật. Tách lỗi sampling/blend của S6 với sai số H do pipeline S2–S5 bằng thử H biết trước.

Chất lượng dataset cần xem cả panorama và crop overlap ở độ phân giải đủ thấy cạnh/ảnh kép. Nếu feather không đạt trên site chuẩn, ghi thất bại và xử lý trước benchmark cuối; không coi độ đơn giản là bằng chứng chất lượng.

## 6. Mức phù hợp với GPU và mapping V1 dự kiến

Định hướng P0: một thread xử lý một pixel canvas; các pixel không cần ghi chung vị trí. V1 dùng global memory và bilinear tự tính theo cùng công thức V0. Mapping chi tiết được viết ở P3 sau khi có số đo theo [bảng task](../task-board.md).

Phần tính canvas/inverse và kiểm tra H cũng phải được tính đến trong thiết kế V1 để đáp ứng yêu cầu các stage chạy trên GPU. Không chỉ chuyển vòng lặp lớn rồi mô tả toàn bộ S6 đã chạy GPU; nếu có host allocation/đọc metadata phải nêu rõ và đo phần liên quan. Phân chia kernel/setup cụ thể chưa chốt.

| Ý tưởng có thể khảo sát sau profiling | Bằng chứng cần có trước khi chọn | Điều kiện giữ correctness |
|---|---|---|
| Fusion warp/validity/blend nếu V1 lưu buffer trung gian | Chi phí launch hoặc đọc/ghi intermediate chiếm đáng kể | Giữ cùng mẫu, trọng số và round |
| Texture point fetch + bilinear tự tính | Gather/source access là bottleneck | Giữ quy ước tọa độ và layout, tính cả chi phí packing/copy |
| Đổi block shape hoặc work-per-thread | Register/occupancy/throughput cho thấy hạn chế cụ thể | Không bỏ pixel, không thay precision tùy tiện |

Không gán trước ý tưởng nào vào V2/V3 của toàn pipeline; đề yêu cầu mỗi phiên bản có một ý tưởng chính đo được. Shared memory không mặc nhiên giúp gather projective vì vùng nguồn có thể không khớp tile.

Hardware texture bilinear chỉ là ứng viên có điều kiện: NVIDIA nêu trọng số nội suy có 8 bit phần lẻ và quy ước tọa độ x-0.5, y-0.5 [R9, mục 15.2]. Với tâm pixel nguyên của S6, texture không normalized cần chuyển đúng half-texel. Không hứa kết quả bit-identical với bilinear số thực tự tính. Nếu dùng, cần ngưỡng consistency đã chốt, kiểm thử mask/biên và tính chi phí tài nguyên; không tự dùng `--use_fast_math` như thay thế miễn phí.

## 7. Kiểm thử

Kế hoạch đề xuất cho P1-T17; toàn bộ kết quả thực tế trên Colab T4 hiện là **chưa chạy**.

| Test | Đầu vào | Kết quả mong đợi |
|---|---|---|
| Identity | Hai ảnh giống nhau, H=I | Canvas bằng nguồn, màu giữ nguyên theo quy tắc sampling/round |
| Tịnh tiến nguyên | Pattern có marker, H biết trước | Marker đúng vị trí, vùng chỉ một nguồn giữ màu |
| Offset âm | Ví dụ 4×3 và x=-2 ở mục 2.2 | Canvas 6×3, offset (2,0), không cắt mất vùng B |
| Tịnh tiến phân số | Ramp màu có đáp án nội suy | Giá trị tại điểm bên trong khớp bilinear tính tay |
| Pixel đen | Ảnh có vùng RGB=0 hợp lệ | Vẫn tham gia blend theo validity |
| Biên nguồn | Tọa độ pixel cuối, kích thước 1×1 | Không đọc ngoài buffer, đúng quy tắc neighbor |
| Bốn trường hợp validity | H có overlap và vùng nền | Composite đúng từng nhánh ở mục 2.3 |
| Projective hợp lệ | H biết trước, horizon ngoài ảnh | Corner/canvas/map đúng, tọa độ hữu hạn |
| H lỗi | Singular, NaN/Inf hoặc horizon qua miền B | Trả lỗi theo contract, không cấp phát canvas giả |
| Canvas quá lớn | H tạo bounds vượt ngân sách | Phát hiện trước allocation, không tràn số |
| Dataset thật | Ba cặp chuẩn và cặp khó đã chuẩn bị | Lưu panorama/crop, ghi giới hạn; không mặc định đạt |

Đáp án synthetic phải tính độc lập với hàm đang kiểm thử. Công cụ sai số homography toàn pipeline thuộc phần phối hợp với Đế; không thay bằng việc S6 chạy đúng với H cho sẵn. Các test CPU/GPU sau này so dimensions/offset/validity trước, rồi mới so màu; metric và tolerance chốt trước khi công bố kết quả.

## 8. Trường hợp biên và rủi ro

S6 trả `ErrorCode` cho bên gọi; không tự gọi `exit()` trong thuật toán. Bên gọi chỉ ghi output khi nhận `Success`, giải phóng tài nguyên và xử lý lỗi cấp chương trình.

| Trường hợp | Phát hiện và xử lý | Trạng thái |
|---|---|---|
| Input không hợp lệ | Null buffer, kích thước/channel/stride sai hoặc byte size tràn | `InvalidImage` |
| H toàn 0 hoặc nghịch đảo thất bại | Kiểm tra scaled pivot, khả nghịch và reciprocal condition estimate | `DegenerateHomography` |
| H có NaN/Inf | Từ chối trước khi tính bbox | `NumericalFailure` |
| Horizon cắt hoặc chạm miền ảnh B | Mẫu số tại góc gần 0, hoặc các góc khác dấu; không lấy bbox từ các góc hữu hạn rồi tiếp tục | `NumericalFailure` |
| Mẫu số âm tại toàn bộ bốn góc B | Không coi là lỗi chỉ vì âm; H và −H biểu diễn cùng phép chiếu | Tiếp tục nếu các kiểm tra khác đạt |
| Corner projection không hữu hạn | Không chuyển NaN/Inf thành chỉ số nguyên | `NumericalFailure` |
| Canvas quá lớn hoặc phép tính kích thước tràn | Kiểm tra trước cấp phát; từ chối khi một chiều >10,000 hoặc diện tích >100,000,000 pixel | `InvalidCanvas` |
| Allocation thất bại dù canvas trong giới hạn | Bắt `std::bad_alloc` từ `new uint8_t[]`; giải phóng tài nguyên đã cấp phát | `AllocationFailed` |
| Allocation Device thất bại ở V1 | `cudaErrorMemoryAllocation` ánh xạ sang lỗi bộ nhớ; lỗi CUDA khác giữ mã riêng | `AllocationFailed` hoặc `CudaFailure` |
| Một pixel không chiếu được về B | Đánh dấu `validB=false`; dùng A nếu hợp lệ, nếu không dùng nền | Không lỗi toàn stage |
| Pixel nằm ngoài cả hai nguồn | Ghi nền RGB `(0,0,0)` | Không lỗi toàn stage |
| Không có overlap | Không chia trọng số cho vùng không có hai nguồn; giữ từng nguồn hợp lệ | `Success` ở S6; báo riêng giới hạn chất lượng |
| Parallax, vật chuyển động hoặc chênh phơi sáng | Feather có thể tạo ghosting hoặc đường chuyển tiếp; không sửa được H sai | Có thể `Success` về thực thi nhưng không đạt kiểm chứng chất lượng |

**Determinant gần 0:** không dùng riêng điều kiện `abs(det(H)) < 1e-6` để kết luận suy biến. Homography thay đổi theo hệ số scale, và determinant nhỏ chưa đủ xác định độ ổn định. S6 dùng kiểm tra pivot có scale và reciprocal condition estimate như mục 4.

**Horizon:** `w <= 0` không phải tiêu chí lỗi tổng quát. Nguy hiểm là `w` đi qua 0 trong miền B hoặc gần 0 theo tolerance. Mẫu số âm toàn miền vẫn biểu diễn một phép chiếu hợp lệ.

**OOM:** giới hạn kích thước chỉ là bước phòng ngừa; canvas trong giới hạn vẫn có thể thiếu RAM/VRAM do các buffer khác. RGB packed `10,000×10,000` cần khoảng 300 MB riêng cho output. Ownership thuộc bên gọi; nếu bên gọi cấp phát sau bước chuẩn bị canvas, bên gọi bắt allocation failure và không tiếp tục render.

Khi lỗi, output phải được đánh dấu không hợp lệ và không được ghi thành panorama thành công. Các giới hạn số học cần kiểm thử với identity, tịnh tiến âm/phân số, H và −H, horizon xuyên ảnh, H suy biến, pixel biên và canvas vượt ngân sách trước khi nghiệm thu V0/V1.

## 9. Nguồn tham khảo

### 9.1. Phạm vi tra cứu và mức kiểm chứng

Tra cứu có mục tiêu vào 12/10/2026: tên paper trong hai bản đề xuất; compositing/feather/multi-band; SC-AOF equations; ROI seam speedup; CUDA texture precision. Chọn đề bài, paper gốc, trang hội nghị/nhà xuất bản, bản tác giả hoặc bản toàn văn lưu tại PMC. Không thực hiện systematic review hoặc tuyên bố đã bao quát toàn bộ nghiên cứu mới nhất đến 2026.

Nhận xét chất lượng/hiệu năng từ paper được giữ trong bối cảnh paper đó. Công thức canvas, validity và distance-weight trong mục 2 là thiết kế đề xuất, không phải kết quả thực nghiệm. Review gồm khảo sát nguồn và một lượt phản biện riêng trong cùng model family; không phải hội đồng peer review độc lập hay chứng nhận học thuật. Hai bản đính kèm được đọc để đánh giá, không dùng làm bằng chứng khoa học cho chính các khẳng định của chúng.

| Mã | Nguồn và ngày truy cập | Phần đã dùng / mức kiểm chứng |
|---|---|---|
| R0 | [Đề cuối kỳ](../specs/CSC14120_2026_Final%20Project.md), [đề giữa kỳ](../specs/CSC14120_2026_Final%20Project_MidTerm.md), [kế hoạch](../midterm-plan.md), [bảng task](../task-board.md). 12/10/2026 | Đọc tài liệu local; xác định scope, version fairness, interface và nghiệm thu |
| R1 | Szeliski, R. (2006 theo bản PDF). *Image alignment and stitching: A tutorial*. Foundations and Trends in Computer Graphics and Vision, 2(1), 1–104. [DOI](https://doi.org/10.1561/0600000009), [PDF](https://pages.cs.wisc.edu/~dyer/cs534/papers/szeliski-alignment-tutorial.pdf), [technical-report PDF đã đọc mục 6](https://pages.cs.wisc.edu/~dyer/ai-qual/szeliski-tr06.pdf). 12/10/2026 | Đọc mục compositing/resampling trong technical report; xác minh PDF journal/DOI. Trang nhà xuất bản hiện ghi ngày phát hành 2007, PDF ghi 2006; không đồng nhất numbering giữa hai bản |
| R2 | Brown, M., & Lowe, D. G. (2007). *Automatic panoramic image stitching using invariant features*. IJCV, 74, 59–73. [Author PDF](https://www.cs.ubc.ca/~lowe/papers/07brown.pdf), [DOI](https://doi.org/10.1007/s11263-006-0002-3). 12/10/2026 | Đọc mục 6–7 và 9; weight/blending, gain và giới hạn chuyển động |
| R3 | Burt, P. J., & Adelson, E. H. (1983). *A multiresolution spline with application to image mosaics*. ACM TOG, 2(4), 217–236. [DOI](https://doi.org/10.1145/245.247), [author-lab PDF](https://persci.mit.edu/pub_pdfs/spline83.pdf). 12/10/2026 | Xác minh tên/abstract qua nguồn MIT được lập chỉ mục và trích dẫn của R2; mở toàn văn PDF thất bại. Dùng cho nguồn gốc multi-band, không tuyên bố đã đọc toàn bài |
| R4 | Kim, D. T., et al. (2018). *Speed improvement in image stitching for panoramic dynamic images during minimally invasive surgery*. Journal of Healthcare Engineering, 2018, 3654210. [Full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC6304838/), [DOI](https://doi.org/10.1155/2018/3654210). 12/10/2026 | Đọc mục 4, đặc biệt 4.2.2/bảng 2; chỉ dùng số đo trong đúng bối cảnh paper |
| R5 | Chang, J., et al. (2024). *SC-AOF: A sliding camera and asymmetric optical-flow-based blending method for image stitching*. Sensors, 24(13), 4035. [Publisher](https://www.mdpi.com/1424-8220/24/13/4035), [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11244014/), [PubMed](https://pubmed.ncbi.nlm.nih.gov/39000817/), [DOI](https://doi.org/10.3390/s24134035). 12/10/2026 | Xác minh metadata; đọc đoạn equations 15–18/thảo luận qua nội dung primary publisher/PMC được search trả về. Mở full text gặp 429/reCAPTCHA; không tuyên bố đọc trọn bài |
| R6 | Jia, Y., Li, Z., Zhang, L., Song, B., & Song, R. (2024). *Semantic aware stitching for panorama*. Sensors, 24(11), 3512. [Publisher](https://www.mdpi.com/1424-8220/24/11/3512), [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11174851/), [DOI](https://doi.org/10.3390/s24113512). 12/10/2026 | Đọc abstract, mục 2 và đoạn cost/Poisson qua primary text được search trả về; mở full text gặp giới hạn truy cập. Không gán pixel heuristic của bản B cho paper |
| R7 | Chen, KuanYan, Garg, Atik, & Wang, Yu-Shuen. (2024). *Seamless-through-breaking: Rethinking image stitching for optimal alignment*. ACCV, 4352–4367. [CVF](https://openaccess.thecvf.com/content/ACCV2024/html/Chen_Seamless-Through-Breaking_Rethinking_Image_Stitching_for_Optimal_Alignment_ACCV_2024_paper.html). 12/10/2026 | Metadata/abstract từ CVF; tham khảo để phân biệt optical-flow/inpainting với global H, không chuyển số đo hay cam kết của phương pháp sang Nhóm |
| R8 | Kim, Minsu, Lee, Jaewon, Lee, Byeonghun, Im, Sunghoon, & Jin, Kyong Hwan. (2024). *Implicit neural image stitching with enhanced and blended feature reconstruction*. WACV, 4087–4096. [CVF](https://openaccess.thecvf.com/content/WACV2024/html/Kim_Implicit_Neural_Image_Stitching_With_Enhanced_and_Blended_Feature_Reconstruction_WACV_2024_paper.html). 12/10/2026 | Đọc metadata/abstract và phần phương pháp được primary PDF search trả về; related work, không triển khai mô hình |
| R9 | NVIDIA. *CUDA C Programming Guide*, CUDA 12.5, mục 15.1–15.2. [Texture fetching](https://docs.nvidia.com/cuda/archive/12.5.0/cuda-c-programming-guide/index.html#texture-fetching). 12/10/2026 | Đọc quy tắc point/linear filtering, half-texel và độ chính xác weights. Phiên bản toolkit thực tế trên Colab cần in khi triển khai |

### 9.2. Trích dẫn chưa dùng làm căn cứ trực tiếp

Bản A nêu Davis (1998), *Mosaics of scenes with moving objects*. Trong lượt này chưa đọc/xác minh trực tiếp toàn văn paper gốc, nên không dùng nó để gán thuật toán graph-cut cụ thể hoặc chứng minh loại bỏ ghosting. Phần so sánh seam/blend dựa vào nguồn đã có locator ở trên. Khi cần cài seam finder, phải đọc paper/solver phù hợp trước.

Nguồn tham khảo dùng trong code sau này cần ghi ở đầu file code và chuyển vào References của notebook theo quy định Nhóm. Tài liệu này chỉ tạo đầu ra P0-T13; không tự sửa report chung hay bảng task.

## 10. Lịch sử thay đổi tham số

Chưa có tham số triển khai được chốt hoặc thay đổi. Lượt 12/10/2026 chọn phương pháp sơ bộ và đề xuất contract dữ liệu sau phản biện A/B; không có số đo để kết luận cải thiện chất lượng hoặc speedup.

| Ngày | Thay đổi | Lý do |
|---|---|---|
