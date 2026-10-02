# Khuôn mẫu quy tắc cho AI agent của thành viên

File này là bộ quy tắc **tối thiểu** mà agent của mỗi thành viên phải tuân thủ khi làm đồ án CSC14120 của Nhóm 16. File được cập nhật thường xuyên trên nhánh `main`.

## Cách sử dụng

1. Sao chép toàn bộ nội dung file này thành file hướng dẫn agent của riêng bạn ở thư mục gốc repo. Tên file theo công cụ đang dùng, ví dụ `AGENTS.md` (Codex và các agent đọc `AGENTS.md`) hoặc `CLAUDE.md` (Claude Code).
2. Bạn được thêm, sửa hoặc sắp xếp lại nội dung trong file của mình cho phù hợp với cách làm việc riêng, nhưng **phải giữ ít nhất toàn bộ nội dung của khuôn mẫu này**. Nếu quy tắc riêng mâu thuẫn với khuôn mẫu, khuôn mẫu được ưu tiên.
3. **Tuyệt đối không commit** file hướng dẫn agent của riêng bạn. Các tên file này đã có trong `.gitignore`.
4. Mỗi khi kéo code mới về (`git pull`), kiểm tra xem `AGENTS_TEMPLATE.md` có thay đổi không (ví dụ bằng `git log -p -- AGENTS_TEMPLATE.md`). Nếu có, cập nhật file của bạn cho đầy đủ trước khi giao việc tiếp cho agent.

Phần dưới đây là nội dung dành cho agent.

## 1. Nguồn yêu cầu và thứ tự ưu tiên

Agent phải đọc và tuân thủ các nguồn sau, theo thứ tự ưu tiên giảm dần:

1. Yêu cầu hiện tại của người dùng, trong phạm vi đề bài cho phép.
2. Đề bài chính thức của môn học: đặc tả giữa kỳ và cuối kỳ (PDF). Hai file giải thích `docs/midterm-spec-explanation.md` và `docs/final-spec-explanation.md` chỉ là bản diễn giải; khi có khác biệt, PDF là chuẩn.
3. Quy định của Nhóm trong `docs/midterm-plan.md`.
4. Task đang làm trong `docs/task-board.md`, được xác định bằng mã task dạng `P<số giai đoạn>-T<số thứ tự>`.
5. Các tài liệu liên quan khác trong `docs/`: `dataset.md`, `interface.md` và `docs/stages/*.md` khi đã có.
6. Khuôn mẫu này và các quy tắc riêng của thành viên.

Nếu các nguồn mâu thuẫn nhau, agent phải dừng phần việc bị ảnh hưởng, chỉ ra chỗ mâu thuẫn kèm trích dẫn cụ thể và hỏi người dùng.

## 2. Không tự quyết

1. **Tuyệt đối không tự quyết** bất kỳ điều gì chưa được đề bài, tài liệu của Nhóm hoặc người dùng quy định rõ. Agent chỉ được đề xuất các phương án (kèm ưu, nhược điểm và khuyến nghị), sau đó chờ người dùng chọn.
2. Những việc luôn phải hỏi trước khi làm:
    - chọn hoặc đổi phương pháp, tham số, cấu hình của một stage;
    - thay đổi interface chung (`common.h`, quy ước dữ liệu trong `docs/interface.md`);
    - sửa file thuộc phần phụ trách của thành viên khác hoặc file dùng chung;
    - thêm thư viện, công cụ hoặc phụ thuộc mới;
    - tạo, đổi tên, di chuyển hoặc xóa file và thư mục ngoài phạm vi task;
    - commit, push, tạo pull request, merge, hoặc bất kỳ thao tác nào ảnh hưởng ra bên ngoài máy của người dùng;
    - mọi thao tác khó hoàn tác.
3. Nếu yêu cầu còn thiếu, mơ hồ hoặc có nhiều cách hiểu, agent phải **hỏi lại người dùng** trước khi làm phần bị ảnh hưởng. Câu hỏi phải ngắn gọn, cụ thể và nói rõ mỗi lựa chọn dẫn tới kết quả khác nhau thế nào. Agent được tiếp tục các bước khảo sát chỉ đọc không phụ thuộc vào câu trả lời.
4. Nếu người dùng cũng chưa chắc, agent phải:
    - đọc lại đề bài và tài liệu của Nhóm, rồi trích dẫn những đoạn liên quan cho người dùng;
    - nếu tài liệu vẫn không trả lời được, đề nghị người dùng báo lại cho cả Nhóm để cùng quyết định, và tạm dừng phần việc đó cho đến khi có kết quả.
5. Agent không được thay Nhóm đưa ra quyết định chung, kể cả khi người dùng bảo "cứ làm đại".

## 3. Trước khi thực hiện

1. Xác định mã task, đọc mô tả, hạn, phụ thuộc và tiêu chí xong của task trong `docs/task-board.md`.
2. Đọc phần đề bài và quy định của Nhóm liên quan tới task.
3. Khảo sát trạng thái hiện tại bằng thao tác chỉ đọc: cấu trúc repo, `git status`, nhánh hiện tại, code, test và tài liệu liên quan.
4. Tóm tắt cho người dùng: mục tiêu, phạm vi, tiêu chí nghiệm thu, các giả định và các câu hỏi còn mở. Chỉ bắt đầu sửa đổi khi người dùng đã xác nhận.
5. **Kiểm tra công cụ để tự kiểm chứng.** Liệt kê các tool, MCP server, skill hoặc plugin cần dùng để build, chạy test và rà soát (ví dụ shell, `git`, `nvcc`, Python, trình chạy notebook, quyền đọc/ghi file). Nếu thiếu công cụ hoặc thiếu quyền, phải báo rõ cho người dùng là cần cấp gì, và không được bắt đầu phần việc cần kiểm chứng khi chưa có đủ.
6. Làm việc trên đúng nhánh theo quy định: `<tên thành viên>/<mã task viết thường>-<mô tả ngắn>`, ví dụ `de/p1-t05-ransac`. Nếu đang ở `main` hoặc ở nhánh khác, hỏi người dùng trước khi tạo hoặc chuyển nhánh.

## 4. Trong khi thực hiện

1. Chỉ làm đúng phạm vi task. Thay đổi nhỏ, tập trung, nhất quán với code hiện có; không tự sửa định dạng, đổi tên hoặc tái cấu trúc phần không liên quan.
2. Giữ nguyên các thay đổi sẵn có của người dùng. Nếu phát hiện xung đột hoặc thay đổi ngoài dự kiến, dừng phần bị ảnh hưởng, đưa bằng chứng và hỏi cách xử lý.
3. Tuân thủ quy định viết code trong `docs/midterm-plan.md`, đặc biệt:
    - comment đầu file ghi tác giả và nguồn bên ngoài (nếu có) ở mọi file được viết hoặc sửa;
    - V0 hoàn toàn tuần tự: không OpenMP, không `std::thread`, `std::async`, `std::execution`, không intrinsics SIMD, không cờ `-fopenmp`;
    - trong `src/` chỉ dùng thư viện chuẩn C/C++ và stb;
    - mọi yếu tố ngẫu nhiên dùng seed cố định;
    - ảnh debug và log chi tiết nằm ngoài vùng đo thời gian;
    - build bằng `nvcc -arch=sm_75`.
4. Code hoặc ý tưởng lấy từ bên ngoài phải ghi nguồn ở đầu file và trong `docs/report/references.md`.
5. Xử lý lỗi ở nguyên nhân gốc. Không vô hiệu hóa test, không bỏ qua cảnh báo quan trọng, không nới lỏng điều kiện kiểm tra để cho qua.
6. Báo tiến độ ngắn gọn khi việc kéo dài, khi cần quyết định hoặc khi gặp trở ngại. Không tuyên bố đã xong khi chưa kiểm chứng.
7. Không bịa đặt kết quả, số đo, trạng thái test hoặc mức độ hoàn thành. Luôn phân biệt rõ điều đã kiểm chứng, điều suy luận và điều chưa kiểm tra được.
8. Không tiết lộ bí mật như token hay mật khẩu, không ghi chúng vào code, output hoặc commit.

## 5. Kiểm chứng và nghiệm thu

1. **Mọi test liên quan phải pass trước khi coi là xong**, gồm test có sẵn trong repo và test agent tự viết cho task. Nếu có test fail, task chưa xong: phải sửa và chạy lại cho tới khi pass, hoặc báo rõ lý do bị chặn.
2. Viết test bám theo tiêu chí xong của task và mục kiểm thử trong tài liệu thiết kế stage. Bao gồm cả trường hợp biên.
3. Môi trường kiểm chứng chính thức là **Google Colab với GPU Tesla T4**. Nếu agent không chạy được trên Colab T4, phải nói rõ kết quả chưa được kiểm chứng trên môi trường này, đồng thời đưa cho người dùng lệnh cụ thể và output mong đợi để người dùng tự chạy.
4. Rà soát lại **toàn bộ** thay đổi trước khi bàn giao:
    - diff chỉ chứa thay đổi thuộc task; không có file tạm, output sinh tự động ngoài ý muốn hay bí mật;
    - không có cấu trúc bị cấm trong V0 (tìm bằng `grep` các từ khóa như `omp`, `thread`, `async`, `execution`, `immintrin`);
    - mọi file mới hoặc đã sửa có comment tác giả và nguồn;
    - tài liệu liên quan (tài liệu thiết kế stage, `docs/interface.md`) đã được cập nhật nếu hành vi hoặc interface thay đổi;
    - `git diff --check` không báo lỗi.
5. Đối chiếu từng tiêu chí xong của task trong `docs/task-board.md` và mục "Tiêu chí hoàn thành một task" trong `docs/midterm-plan.md`. Tiêu chí nào chưa đạt phải được nêu rõ.

## 6. Sau khi thực hiện

1. Báo cáo ngắn gọn cho người dùng:
    - đã thay đổi gì, ở file nào;
    - đã chạy test và kiểm tra nào, kết quả ra sao;
    - kiểm tra nào chưa chạy được, lý do và rủi ro còn lại;
    - tiêu chí nghiệm thu nào đã đạt, tiêu chí nào chưa;
    - trạng thái working tree.
2. Chỉ commit, push hoặc tạo pull request khi người dùng yêu cầu. Khi làm thì tuân thủ:
    - commit message bằng tiếng Anh theo Conventional Commits, có thể dùng mã task làm scope, ví dụ `feat(p1-t05): add RANSAC hypothesis loop`;
    - chỉ stage các file thuộc task và xem lại nội dung đã stage trước khi commit;
    - pull request ghi mã task, mô tả thay đổi và output build/test trên Colab T4;
    - không force-push lên `main`, không sửa lịch sử hay amend commit của người khác;
    - không commit file hướng dẫn agent cá nhân, dataset, output, token, PDF hoặc notebook còn output (trừ notebook nộp bài).
3. Nếu bị chặn, nêu nguyên nhân cụ thể, những gì đã thử, và thông tin hoặc quyền cần người dùng bổ sung.

## 7. Quy ước tài liệu và ngôn ngữ

1. Nội dung báo cáo, markdown trong notebook, tài liệu `.md`, phần giải thích lựa chọn và phân tích kết quả viết bằng **tiếng Việt**. Giữ nguyên thuật ngữ tiếng Anh khi không nên dịch hoặc bản dịch không phổ biến (keypoint, descriptor, homography, kernel, thread, warp, block, speedup...).
2. Tên file, tên thư mục, tên nhánh, code, tên biến, tên hàm, comment trong code và commit message viết bằng **tiếng Anh**. Ngoại lệ là tên riêng như tên thành viên và tên địa điểm chụp; khi dùng trong tên file hoặc thư mục thì viết không dấu.
3. Không dùng blockquote Markdown (dòng bắt đầu bằng `>`). Mọi sơ đồ trong Markdown viết bằng Mermaid trong code fence `mermaid`.
4. Gọi thành viên bằng tên. Hạn ghi theo dạng `dd/mm (thứ)`, không ghi giờ, không ghi theo khoảng ngày.
5. Không chỉ định người duyệt trong tài liệu của Nhóm. Với vấn đề cần quyết định chung, ghi "báo lại cho cả Nhóm để cùng quyết định".
6. Mọi con số trong lời văn của notebook phải xuất hiện trong output của notebook. Notebook build từ chính `src/`, không chép code vào cell bằng `%%writefile`.

## 8. Các mục sẽ bổ sung

Nhóm sẽ bổ sung dần các mục sau vào khuôn mẫu. Khi chúng xuất hiện trên `main`, hãy cập nhật vào file của bạn:

- quy tắc viết markdown trong notebook sao cho tự nhiên như người viết;
- quy tắc viết comment trong code.
