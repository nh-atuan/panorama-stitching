# Khuôn mẫu quy tắc cho AI agent của thành viên

File này là bộ quy tắc **tối thiểu** mà agent của mỗi thành viên phải tuân thủ khi làm đồ án CSC14120 của Nhóm 16. File được cập nhật thường xuyên trên nhánh `main`.

## Cách sử dụng

1. Sao chép toàn bộ nội dung file này thành file hướng dẫn agent của riêng bạn ở thư mục gốc repo. Tên file theo công cụ đang dùng, ví dụ `AGENTS.md` (Codex và các agent đọc `AGENTS.md`) hoặc `CLAUDE.md` (Claude Code).
2. Bạn được thêm, sửa hoặc sắp xếp lại nội dung trong file của mình cho phù hợp với cách làm việc riêng, nhưng **phải giữ ít nhất toàn bộ nội dung của khuôn mẫu này**. Nếu quy tắc riêng mâu thuẫn với khuôn mẫu, khuôn mẫu được ưu tiên.
3. **Tuyệt đối không commit** file hướng dẫn agent của riêng bạn. Các tên file này đã có trong `.gitignore`.
4. Mỗi khi kéo code mới về (`git pull`), kiểm tra xem `AGENTS_TEMPLATE.md` có thay đổi không (ví dụ bằng `git log -p -- AGENTS_TEMPLATE.md`). Nếu có, cập nhật file của bạn cho đầy đủ trước khi giao việc tiếp cho agent.
5. Ghi họ tên và MSSV của bạn vào file hướng dẫn agent cá nhân theo mẫu sau để agent điền vào comment đầu file theo mục 4:

    ```text
    Họ tên (viết không dấu trong code): <Full name>
    MSSV: <Student ID>
    ```

6. Gợi ý, không bắt buộc: kết nối cho agent một công cụ chạy được Colab, ví dụ [Colab MCP server](https://github.com/googlecolab/colab-mcp) của Google hoặc một MCP server, plugin tương đương. Khi đó agent tự build và chạy test trên Colab T4, bạn không phải tải notebook và source code lên Colab sau mỗi lần sửa code.

Phần dưới đây là nội dung dành cho agent.

## 1. Nguồn yêu cầu và thứ tự ưu tiên

Agent phải đọc và tuân thủ các nguồn sau, theo thứ tự ưu tiên giảm dần:

1. Yêu cầu hiện tại của người dùng, trong phạm vi đề bài cho phép.
2. Đề bài chính thức của môn học trong `docs/specs/`: `CSC14120_2026_Final Project_MidTerm.md` (đề giữa kỳ) và `CSC14120_2026_Final Project.md` (đề cuối kỳ). Đây là bản chép nguyên văn từ hai file PDF cùng tên. Các file PDF không được commit, mỗi thành viên tự đặt vào `docs/specs/`. Khi có khác biệt, PDF là chuẩn.
3. Quy định của Nhóm trong `docs/final-plan.md` (giai đoạn cuối kỳ) và `docs/archive/midterm-plan.md` (nền tảng V0 giữa kỳ).
4. Task đang làm trong `docs/task-board.md`, được xác định bằng mã task dạng `P<số giai đoạn>-T<số thứ tự>`.
5. Các tài liệu liên quan khác trong `docs/`: `dataset.md`, `interface.md` và `docs/stages/*.md` khi đã có.
6. Khuôn mẫu này và các quy tắc riêng của thành viên.

Nếu các nguồn mâu thuẫn nhau, agent phải dừng phần việc bị ảnh hưởng, chỉ ra chỗ mâu thuẫn kèm trích dẫn cụ thể và hỏi người dùng.

## 2. Không tự quyết

1. **Tuyệt đối không tự quyết** bất kỳ điều gì chưa được đề bài, tài liệu của Nhóm hoặc người dùng quy định rõ. Agent chỉ được đề xuất các phương án (kèm ưu, nhược điểm và khuyến nghị), sau đó chờ người dùng chọn.
2. Những việc luôn phải hỏi trước khi làm:
    - chọn hoặc đổi phương pháp, tham số, cấu hình của một stage;
    - thay đổi contract chung (`src/common/common.h`, contract workspace GPU, quy ước dữ liệu trong `docs/interface.md`);
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
6. Không tự ý làm việc người dùng chưa yêu cầu, kể cả sửa file, commit hay push. Khi người dùng chỉ hỏi ý kiến hoặc nhờ đề xuất, chỉ trả lời và đề xuất; chờ người dùng yêu cầu rõ rồi mới thực hiện.

## 3. Trước khi thực hiện

1. Xác định mã task, đọc mô tả, phụ thuộc và tiêu chí xong của task, cùng hạn của giai đoạn chứa task, trong `docs/task-board.md`.
2. Đọc phần đề bài và quy định của Nhóm liên quan tới task.
3. Khảo sát trạng thái hiện tại bằng thao tác chỉ đọc: cấu trúc repo, `git status`, nhánh hiện tại và mức đồng bộ với `main`, code, test và tài liệu liên quan. Nếu nhánh đang thiếu thay đổi mới của `main`, hỏi người dùng có muốn kéo `main` về trước khi làm không.
4. Tóm tắt cho người dùng: mục tiêu, phạm vi, tiêu chí nghiệm thu, các giả định và các câu hỏi còn mở. Chỉ bắt đầu sửa đổi khi người dùng đã xác nhận.
5. **Kiểm tra công cụ để tự kiểm chứng.** Liệt kê các tool, MCP server, skill hoặc plugin cần dùng để build, chạy test và rà soát (ví dụ shell, `git`, `nvcc`, Python, trình chạy notebook, quyền đọc/ghi file). Nếu thiếu công cụ hoặc thiếu quyền, phải báo rõ cho người dùng là cần cấp gì, và không được bắt đầu phần việc cần kiểm chứng khi chưa có đủ. Nếu chưa có công cụ nào để tự chạy trên Colab T4, gợi ý người dùng kết nối một công cụ như ở bước 5 của mục "Cách sử dụng".
6. Làm việc trên đúng nhánh theo loại thay đổi (mục 8.1 của `docs/final-plan.md` và mục 10 của `docs/archive/midterm-plan.md`):
    - code và test của stage mình: nhánh giai đoạn `<tên thành viên>/p<số giai đoạn>`, ví dụ `de/p5`;
    - file dùng chung (`src/main.cu`, `src/versions.h`, `src/common/*`, contract workspace dùng chung, `docs/interface.md`, runner và script hạ tầng dùng chung): nhánh riêng `<tên thành viên>/shared-<mô tả ngắn>` và một pull request riêng, nhỏ;
    - tài liệu trong phạm vi của mình (trạng thái task, bảng trong `docs/dataset.md`, tài liệu stage và phần báo cáo của mình): commit thẳng lên `main`.

    Nếu đang ở nhánh không đúng với loại thay đổi, hỏi người dùng trước khi tạo hoặc chuyển nhánh.

## 4. Trong khi thực hiện

1. Chỉ làm đúng phạm vi task. Thay đổi nhỏ, tập trung, nhất quán với code hiện có; không tự sửa định dạng, đổi tên hoặc tái cấu trúc phần không liên quan.
2. Giữ nguyên các thay đổi sẵn có của người dùng. Nếu phát hiện xung đột hoặc thay đổi ngoài dự kiến, dừng phần bị ảnh hưởng, đưa bằng chứng và hỏi cách xử lý.
3. Tuân thủ quy định viết code trong `docs/final-plan.md` và `docs/archive/midterm-plan.md`, đặc biệt:
    - comment đầu file ở mọi file được viết hoặc sửa, trừ notebook (`.ipynb`), theo đúng mẫu ở mục 9 của `docs/archive/midterm-plan.md` (đề bài yêu cầu ghi tác giả và nguồn bên ngoài nếu có): dòng `Authors:` gồm họ tên đầy đủ kèm MSSV của người viết hoặc sửa (lấy từ file hướng dẫn agent cá nhân), dòng `External source:` ghi `none` hoặc dòng `Adapted from:` kèm tên nguồn, URL, ngày truy cập và dòng `Changes:` mô tả phần Nhóm đã thay đổi so với nguồn;
    - giữ đóng băng `src/v0/` hoàn toàn tuần tự: không tự ý sửa thuật toán hay tham số `V0`, không đưa OpenMP, `std::thread`, `std::async`, `std::execution`, intrinsics SIMD hay cờ `-fopenmp` vào `src/v0/`;
    - trong `src/` chỉ dùng thư viện chuẩn C/C++, `stb`, CUDA Runtime API cơ bản và intrinsics phần cứng (`__popc`, `__shfl_*`, phép toán atomic...) kèm nhãn NVTX khi profiling; không dùng các thư viện thuật toán đóng gói sẵn như `Thrust`, `CUB`, `cuBLAS`, `cuSOLVER`, `NPP` khi chưa được cả Nhóm thống nhất và giảng viên cho phép;
    - dùng một gốc `-Isrc` (thêm `-Itests` cho test) và ghi rõ thư mục con trong mọi lệnh `#include` nội bộ (ví dụ `#include "common/common.h"`);
    - mọi yếu tố ngẫu nhiên dùng seed cố định;
    - ảnh debug và log chi tiết nằm ngoài vùng đo thời gian;
    - build bằng `nvcc -arch=sm_75` (qua `scripts/build.py` và `tests/run_tests.py`).
4. Code hoặc ý tưởng lấy từ bên ngoài phải ghi nguồn ở đầu file và trong `docs/report/references.md`.
5. Xử lý lỗi ở nguyên nhân gốc. Không vô hiệu hóa test, không bỏ qua cảnh báo quan trọng, không nới lỏng điều kiện kiểm tra để cho qua.
6. Báo tiến độ ngắn gọn khi việc kéo dài, khi cần quyết định hoặc khi gặp trở ngại. Không tuyên bố đã xong khi chưa kiểm chứng.
7. Không bịa đặt kết quả, số đo, trạng thái test hoặc mức độ hoàn thành. Luôn phân biệt rõ điều đã kiểm chứng, điều suy luận và điều chưa kiểm tra được.
8. Không tiết lộ bí mật như token hay mật khẩu, không ghi chúng vào code, output hoặc commit.
9. **Chia nhỏ phần việc thành nhiều file, hàm và module.** Không gộp toàn bộ vào một file hay một hàm lớn. Module hóa stage và task của mình ở mức nhỏ nhất có thể, mỗi đơn vị làm một việc rõ ràng, để agent dễ đọc, dễ sửa, dễ viết test và kiểm chứng riêng từng phần, và dễ khoanh vùng khi debug. Đặt file đúng cấu trúc thư mục con trong `src/` (`src/common/`, `src/v0/`, `src/v1/`, `src/v2/`, `src/v3/`) và `tests/` (`tests/v0/`, `tests/gpu/`, `tests/support/`, `tests/python/`, `tests/tools/`) theo `docs/final-plan.md`, `src/README.md` và `tests/README.md` (ở `v2/`, `v3/` chỉ tạo file cho stage/module có thay đổi, các stage giữ nguyên gọi lại hàm phiên bản trước); không tạo thêm file ngoài phạm vi task mà chưa hỏi theo mục 2.

## 5. Kiểm chứng và nghiệm thu

1. **Mọi test liên quan phải pass trước khi coi là xong**, gồm test có sẵn trong repo và test agent tự viết cho task. Nếu có test fail, task chưa xong: phải sửa và chạy lại cho tới khi pass, hoặc báo rõ lý do bị chặn.
2. Viết test bám theo tiêu chí xong của task và mục kiểm thử trong tài liệu thiết kế stage. Bao gồm cả trường hợp biên.
3. Môi trường kiểm chứng chính thức là **Google Colab với GPU Tesla T4**. Nếu agent không chạy được trên Colab T4, phải nói rõ kết quả chưa được kiểm chứng trên môi trường này, đồng thời đưa cho người dùng lệnh cụ thể và output mong đợi để người dùng tự chạy.
4. Rà soát lại **toàn bộ** thay đổi trước khi bàn giao:
    - diff chỉ chứa thay đổi thuộc task; không có file tạm, output sinh tự động ngoài ý muốn hay bí mật;
    - không có cấu trúc bị cấm trong `src/v0/` (tìm bằng `grep` các từ khóa như `omp`, `thread`, `async`, `execution`, `immintrin`) và không dùng thư viện GPU ngoài phạm vi cho phép (`thrust`, `cub`, `cublas`, `cusolver`, `npp`) trong `src/`;
    - mọi file mới hoặc đã sửa, trừ notebook, có comment tác giả và nguồn;
    - tài liệu liên quan (tài liệu thiết kế stage, `docs/interface.md`) đã được cập nhật nếu hành vi, ngưỡng kiểm chứng hoặc contract thay đổi;
    - `git diff --check` không báo lỗi.
5. Đối chiếu từng tiêu chí xong của task trong `docs/task-board.md` và mục "Tiêu chí hoàn thành một task" trong `docs/final-plan.md` (hoặc `docs/archive/midterm-plan.md` với V0). Tiêu chí nào chưa đạt phải được nêu rõ.
6. Không sửa lỗi không liên quan nếu việc sửa có thể làm tăng phạm vi hoặc rủi ro. Ghi nhận ngắn gọn để người dùng quyết định.

## 6. Sau khi thực hiện

1. Báo cáo ngắn gọn cho người dùng:
    - đã thay đổi gì, ở file nào;
    - đã chạy test và kiểm tra nào, kết quả ra sao;
    - kiểm tra nào chưa chạy được, lý do và rủi ro còn lại;
    - tiêu chí nghiệm thu nào đã đạt, tiêu chí nào chưa;
    - trạng thái working tree.
2. Chỉ commit, push hoặc tạo pull request khi người dùng yêu cầu. Khi làm thì tuân thủ:
    - commit message bằng tiếng Anh theo Conventional Commits, dùng mã task làm scope, ví dụ `feat(p5-t10): implement basic CUDA Hamming matcher`;
    - không thêm dòng `Co-Authored-By` của AI vào commit message, không thêm dòng ghi công AI (như "Generated with Claude Code") vào mô tả pull request;
    - chỉ stage các file thuộc task và xem lại nội dung đã stage trước khi commit;
    - sau khi commit, kiểm tra bằng `git show --check --oneline HEAD`;
    - trước khi mở pull request, nhánh phải build và chạy test đạt trên Colab T4; pull request ghi các mã task đã làm, mô tả thay đổi và output build/test;
    - không force-push lên `main`, không sửa lịch sử hay amend commit của người khác;
    - không commit file hướng dẫn agent cá nhân, dataset, output, token hoặc PDF;
    - **tuyệt đối không commit output của notebook** để tránh conflict khi merge. Vẫn phải chạy notebook trước để biết nó chạy được hay không; chỉ khi commit mới xóa toàn bộ output (nút "Clear All Outputs" hoặc `jupyter nbconvert --clear-output --inplace <file>.ipynb`), rồi kiểm tra lại bằng `git diff --staged` rằng notebook không còn output (trừ notebook nộp bài nếu đề bài yêu cầu kèm output).
3. Nếu bị chặn, nêu nguyên nhân cụ thể, những gì đã thử, và thông tin hoặc quyền cần người dùng bổ sung.

## 7. Quy ước tài liệu và ngôn ngữ

1. Nội dung báo cáo, markdown trong notebook, tài liệu `.md`, phần giải thích lựa chọn và phân tích kết quả viết bằng **tiếng Việt**. Giữ nguyên thuật ngữ tiếng Anh khi không nên dịch hoặc bản dịch không phổ biến (keypoint, descriptor, homography, kernel, thread, warp, block, speedup, contract...).
2. Tên file, tên thư mục, tên nhánh, code, tên biến, tên hàm, comment trong code và commit message viết bằng **tiếng Anh**. Ngoại lệ là tên riêng như tên thành viên và tên địa điểm chụp; khi dùng trong tên file hoặc thư mục thì viết không dấu.
3. Không dùng blockquote Markdown (dòng bắt đầu bằng `>`). Mọi sơ đồ trong Markdown viết bằng Mermaid trong code fence `mermaid`.
4. Gọi thành viên bằng tên, không dùng ký hiệu chữ cái thay cho tên.
5. Hạn chót ghi bằng mốc ngày cụ thể dạng `dd/mm (Thứ n)` (ví dụ `06/10 (Thứ 3)`), viết đầy đủ, không viết tắt như T3; không ghi giờ, không ghi theo khoảng ngày. Không đặt thêm các loại hạn như "hạn nội bộ" hay "hạn của nhóm" ngoài hạn nộp chính thức. Không ghi hạn ở cuối tiêu đề mục; hạn chỉ được quản lý trong bảng công việc.
6. Trong bảng công việc, hạn chỉ ghi cho cả giai đoạn, không ghi cho từng task. Task được nhóm theo thành viên (theo thứ tự stage phụ trách), các ô tên liên tiếp của cùng một người được gộp lại bằng bảng HTML có `rowspan`.
7. Kế hoạch được lập cuốn chiếu: chỉ ghi nội dung và hạn chi tiết cho giai đoạn hiện tại cùng mốc nộp bài; các giai đoạn sau chỉ ghi tên và được lập chi tiết khi giai đoạn trước hoàn thành.
8. Cột "Phần việc chung" trong bảng phân vai chỉ ghi các phần việc chung đã có task đến giai đoạn hiện tại; không ghi trước phần việc của các giai đoạn sau hay của V1-V3. Mỗi ô ghi ngắn gọn theo mảng việc, không kèm mã task và không liệt kê chi tiết như tên file. Không ghi vào cột này các việc thuộc stage của chính người đó (ví dụ công cụ kiểm thử của stage); thành viên không có phần việc chung thì để trống.
9. Không chỉ định người duyệt hay quy trình duyệt trong tài liệu của Nhóm. Với vấn đề cần quyết định chung, ghi "báo lại cho cả Nhóm để cùng quyết định".
10. Không đưa quy định về việc sử dụng công cụ AI vào tài liệu quản lý dự án của Nhóm.
11. Mọi con số trong lời văn của notebook phải xuất hiện trong output của notebook. Notebook build từ chính `src/`, không chép code vào cell bằng `%%writefile`.
12. Khi dùng agent để viết báo cáo, file markdown hoặc cell markdown trong notebook, agent phải đọc trước trang [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) và tránh các dấu hiệu được liệt kê ở đó, để câu chữ tự nhiên như người viết. Sau khi viết xong, agent rà lại văn bản theo trang này và sửa các chỗ còn dấu hiệu.
