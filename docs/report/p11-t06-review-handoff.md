<!-- Authors: Le Ha Thanh Chuong (23120195). External source: repository code, reports and local validation cited below. -->

# P10-T06 / P11-T06 — Review Handoff

## Completed Scope

Nhánh local `chuong/p11-t06-notebook-acceptance`, tiếp tục từ `f6a6eaf`, đã tích hợp main `26c8f24`. Nội dung V5 và kết luận trong [notebook](../../Group16_Final.ipynb) đã hoàn thiện; giữ 43 cell, 20 code cell và toàn bộ anchor. Không thêm kết quả GPU giả hoặc commit output notebook.

Các phần đã hoàn thành:

- Sửa thứ tự V4, candidate-count wait, prefix/suffix V5, events/join và đối chứng sequential từ source thực.
- Giữ phương pháp/downstream S4–S6; tách stage grouping V4 khỏi full branch serialization V5 sequential.
- Tính lại per-case/aggregate từ bảng mean, giữ challenge riêng và không lấy cột speedup đã làm tròn làm input.
- Đưa baseline probe T01 vào output có đúng nhãn; tách số V5 quoted và paired metrics chưa dựng lại được.
- Mục 9 không còn placeholder V5, giữ V4 production/V5 case study cùng giới hạn chất lượng và bằng chứng.
- Ghi rõ bảng/biểu đồ cùng session mới so với bảng lịch sử; sum stage/kernel của V5 có thể overlap và không phải phân chia elapsed Total.
- Sửa lỗi MathJax 3 inline được phát hiện qua PDF smoke: template nbconvert cũ dùng v2 Hub, làm `$H$` còn thô. Exporter nay cấu hình v3 inline/display rõ ràng và có regression test.

## Evidence and Metrics

[Phân tích P10-T06](p10-t06-v5-analysis.md) có công thức, bảng per-case và phạm vi nguồn. Tính lại từ bảng mean P10:

| Statistic | Result |
|---|---:|
| Nine-case geomean V5/V4 | 1.101330× |
| Medium/large geomean V5/V4 | 1.021965× |
| Arithmetic mean V5/V4 | 1.114857× |
| Ratio of summed means | 1.086587× |
| site2/large V5/V4 | 1.028595× |
| Historical geomean V5/V0 | 52.846197× |
| Quoted V5 pre-S4 sequential/dual ratio | 1.207413× |
| Quoted V5 pre-S4 latency reduction | 17.178315% |

APOD gốc vẫn ghi 1,027×/1,039×; aggregation/session chưa thể tái dựng vì thiếu raw V5. Đây là giới hạn provenance của báo cáo lịch sử, được hiển thị trong notebook; không lấy hai số đó làm kết luận hiệu năng đã xác nhận. Không chế median hoặc số khối cùng chiều để chứng minh tiêu chí adoption. Báo cáo APOD/T04 của thành viên khác được giữ nguyên.

Raw probe T01 đã kiểm lại 84/84 checksum; primary mean 15,287987 ms và mean run-share 21,439554% khớp baseline. Không trộn mẫu số với Total production của binary khác hoặc phiên P10-T05.

## Source Revision

Giữ `SOURCE_REF=696fc82c72b2098ea7ca24c7c89efdab9d3452ec`. So Git trees cho thấy src/build khớp freeze `f2837a85b770e6c8bb2eba1bb6de7aee7fa23eb7`; đủ V0–V5, helper, benchmark/dataset utilities và các report notebook đọc. Hai SHA khác nhau vì tooling/tài liệu, không tự suy helper mới đã được nghiệm thu cùng code.

HEAD hiện tại có thay đổi production sau freeze tại `src/v5/v5_image_branch.cu` do upstream; task này không sửa thêm source đó. `freeze_comparison` ghi rõ source thực chạy và freeze ref. Dùng ZIP HEAD thì giữ candidate và nghiệm thu trên SHA mới; không gắn log cũ cho executable mới. [Chi tiết tích hợp](p11-t06-integration.md).

## Validation

Kết quả cuối: **242 test Python, không failures/errors, 2 skip có chủ đích**. `test_final_notebook.py` đạt 20 test; suite mới cho V5 narrative/result cell đạt 4 test, dùng Decimal độc lập với phép tính float trong notebook. Các cell CPU và số kiểm raw là bằng chứng local, không chứng nhận fresh T4.

- Python regression toàn repo và test_final_notebook.py; test mới chạy các cell evidence thực, tính lại bằng Decimal và thử sai tập ca/cột rounded/challenge.
- Nbformat, anchors, code roles, AST, import package và đường dẫn local; notebook Git không output.
- Chạy 9 cell evidence CPU theo thứ tự trên namespace sạch; chạy kernel mới cho PDF smoke có Mermaid/lời văn V5/kết luận và bảng metric.
- Source checks tại pin/freeze, CSV probe/hash, source archive generation/extraction và import từ source đã giải nén.
- PDF smoke mới ở `build/p10-t06-analysis-smoke/export-inline-fixed/`: 5 trang, 1 Mermaid và 1 inline MathJax render được, QA không lỗi/clipping; đã render và xem tất cả trang. Chỉ là smoke, không phải PDF nộp cuối. Bản smoke phát hiện lỗi trước sửa được giữ riêng.
- `git diff --check`; không có binary/dataset/ZIP/outputs sinh tự động staged. Hai mục untracked có từ trước giữ nguyên.

Các kiểm tra còn thiếu thuộc T4 acceptance, không bị che bởi kết quả CPU.

## Merge Readiness and Remaining Acceptance

**Nội dung kỹ thuật P10-T06 và hạ tầng P11-T06 sẵn sàng review/publish.** Không có blocker local đã biết. Giới hạn raw V5 còn thiếu được chặn khỏi các claim thống kê; vì vậy không cần chế dữ liệu để merge phần chuẩn bị. Không đánh P11-T06 Xong.

Trước nghiệm thu cuối vẫn cần chọn source thực chạy, Run all fresh T4, đo V0–V5 cùng phiên, kiểm output/CSV/manifest/geometry evidence phù hợp SHA, gallery/cặp mẫu, từng số trong lời văn và render toàn bộ PDF cuối. Các tài liệu tổng kết raw V5 nếu được bàn giao sau cần cập nhật minh bạch và chạy lại đối chiếu.

Handoff ZIP mới được tạo sau commit cuối tại `build/p11-t06-review/Group16_P11_T06_Source.zip` kèm JSON sidecar. ZIP không được commit. Dùng [notebook điều phối](../../Group16_P11_T06_Acceptance.ipynb) và [runbook](p11-t06-colab-runbook.md); ZIP cũ giữ như lịch sử.

## Proposed Pull Request

Title: `docs(p11-t06): finalize notebook analysis and acceptance tooling`

Base: `main`; head: `chuong/p11-t06-notebook-acceptance`. Body file: [PR description](p11-t06-pr-description.md).

Chỉ người dùng chạy các lệnh dưới khi quyết định công bố; agent chưa push hoặc mở PR:

```bash
git push -u origin chuong/p11-t06-notebook-acceptance
gh pr create --base main --head chuong/p11-t06-notebook-acceptance --title "docs(p11-t06): finalize notebook analysis and acceptance tooling" --body-file docs/report/p11-t06-pr-description.md
```

**READY TO PUSH AND OPEN PR**
