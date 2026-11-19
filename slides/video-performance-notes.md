# P9-T06 — Lời dẫn và tư liệu phần hiệu năng

Đế trình bày phần hiệu năng trong **5 phút (07:00–12:00)**. Ba phút cuối dành cho tối ưu và bài học, do Đế, Chương và Tuấn chia nhau trình bày. [Kịch bản chung](video-outline.md)

| Mốc | Tư liệu | Lời dẫn chính |
|---|---|---|
| 07:00–07:40 | Slide điều kiện đo và bảng V0–V4 | Cùng một phiên Tesla T4, binary, dataset và cấu hình. Mỗi ca thành công có một warm-up và năm run. Trung bình nhân tính trên chín ca chuẩn. |
| 07:40–08:40 | Bảng V0–V4 và dẫn chứng P6–P8 | V2 và V3 giảm chi phí S5. Sau V3, S6 chiếm khoảng 46% tổng thời gian tại site2/large, nên nhóm chọn đây làm ca chính cho fusion. |
| 08:40–09:40 | Bảng P9 và số đo theo khối | V4/V3 đạt 1,0357× ở S6 và 1,0086× toàn pipeline theo trung bình nhân. Tại site2/large, S6 giảm 28,712 → 28,190 ms. Median năm khối ở ca chính đạt 1,0270×. |
| 09:40–10:35 | Timeline NSYS site2/large | Chỉ ba thao tác của V3 và một renderer V4. Trace có một warm-up và một run. Dùng bảng benchmark năm run để nói về tốc độ chính thức. |
| 10:35–11:35 | Biểu đồ DRAM NCU | Tại site2/large, tổng đọc và ghi của các kernel lấy mẫu tăng 26,0%. Memset V3 nằm ngoài phạm vi counter, nên tổng DRAM toàn S6 vẫn chưa xác định. |
| 11:35–12:00 | Bằng chứng P9-T02 | Tóm tắt parity, trạng thái challenge và memcheck trước khi chuyển sang phần tối ưu và bài học. |

Trong phần 12:00–15:00, dùng khoảng một phút cho V2/V3, một phút cho fusion V4 và một phút để tổng kết bài học về hotspot, cách đo và kiểm chứng.

## Danh mục hiện vật

- `Group16_P9_T05_Benchmark_Profiling.ipynb`: notebook nguồn, điều kiện đo và output.
- Drive `v4/benchmark/`: CSV từng run, summary, speedup, variability và biểu đồ.
- Drive `v4/profiling/`: `.nsys-rep`, `.ncu-rep`, CSV export, log lệnh và ảnh chụp giao diện tại `v4/profiling/screenshots/`.
- `slides/generated/v4-table.tex`: bảng P9 trích từ CSV cùng phiên, ghi rõ ngày và source.
- `slides/generated/nsys-v4.png`, `slides/generated/ncu-v4.png`: hình dựng từ SQLite NSYS và CSV NCU, có cả đối chứng V3.
- `docs/report/p9-v4-verification.md`: căn cứ correctness và an toàn bộ nhớ.
- `docs/report/p9-t05-v4-apod.md`: phân tích hiệu năng, số liệu profiler và giới hạn.

Khi quay, mở sẵn trace hoặc ảnh, phóng to nhãn/metric đủ đọc, giữ đơn vị ms/byte/% trên màn hình. Link nguồn số liệu phải truy ngược được tới CSV/report gốc. Không cần quay lại toàn bộ thời gian chờ benchmark; phần live demo của nhóm dùng kịch bản chung.
