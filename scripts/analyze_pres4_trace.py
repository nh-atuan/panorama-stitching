# Authors: Le Ha Thanh Chuong (23120195)
# External source: NVIDIA Nsight Systems SQLite export schema.
"""Extract the last (measured) V4 pre-S4 interval from a P10-T01 NSYS export."""
import argparse
import json
from pathlib import Path
import sqlite3


def union_duration(intervals, begin, end):
    merged_end = begin
    total = 0
    for left, right in sorted(intervals):
        left, right = max(left, begin), min(right, end)
        if right > max(left, merged_end):
            total += right - max(left, merged_end)
            merged_end = right
    return total


def extract(path):
    with sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        ranges = list(db.execute(
            "SELECT n.start,n.end,n.globalTid,coalesce(n.text,s.value) AS label "
            "FROM NVTX_EVENTS n LEFT JOIN StringIds s ON n.textId=s.id "
            "WHERE n.end IS NOT NULL ORDER BY n.start"
        ))
        runtime = {r["correlationId"]: dict(r) for r in db.execute(
            "SELECT r.*,s.value AS api FROM CUPTI_ACTIVITY_KIND_RUNTIME r "
            "JOIN StringIds s ON r.nameId=s.id"
        )}
        operations = []
        for table in ("CUPTI_ACTIVITY_KIND_KERNEL", "CUPTI_ACTIVITY_KIND_MEMCPY",
                      "CUPTI_ACTIVITY_KIND_MEMSET"):
            for row in db.execute(f"SELECT * FROM {table}"):
                op = dict(row)
                api = runtime.get(op["correlationId"])
                if api:
                    op.update(api_start=api["start"], api_end=api["end"],
                              tid=api["globalTid"], kind=table)
                    operations.append(op)

        def last_range(label):
            matching = [r for r in ranges if r["label"] == label]
            if len(matching) != 2:
                raise ValueError(f"Expected warm-up and one measured range for {label}")
            return matching[-1]

        def within(op, span):
            return span["start"] <= op["api_start"] <= span["end"] and op["tid"] == span["globalTid"]

        s4 = last_range("S4.match")
        first_s4 = min(op["start"] for op in operations if within(op, s4))
        spans = [last_range(f"S{i}.image_{branch}") for i in (1, 2, 3) for branch in ("a", "b")]
        prefix_ops = [op for op in operations if any(within(op, span) for span in spans)]
        ready = max(op["end"] for op in prefix_ops)
        uploads = sorted(
            (op for op in operations if op.get("copyKind") == 1
             and op.get("bytes", 0) == 3840 * 2160 * 3 and op["api_start"] < s4["start"]),
            key=lambda op: op["api_start"],
        )[-2:]
        if len(uploads) != 2:
            raise ValueError("Cannot identify the two measured large RGB uploads")
        start = uploads[0]["start"]
        if not start < ready <= first_s4:
            raise ValueError("Unexpected stream ordering at S4")
        occupied = union_duration([(op["start"], op["end"]) for op in operations], start, ready)
        result = {
            "GPU_H2D_to_features_ready_ms": (ready - start) / 1e6,
            "GPU_H2D_to_first_S4_ms": (first_s4 - start) / 1e6,
            "GPU_ready_to_first_S4_ms": (first_s4 - ready) / 1e6,
            "Host_H2D_submit_to_S4_submit_ms": (s4["start"] - uploads[0]["api_start"]) / 1e6,
            "GPU_preS4_observed_idle_ms": (ready - start - occupied) / 1e6,
        }
        for branch in ("a", "b"):
            copies = [op for op in prefix_ops if op.get("copyKind") == 2 and op.get("bytes") == 4
                      and within(op, last_range(f"S2.image_{branch}"))]
            if len(copies) != 1:
                raise ValueError("Candidate-count copy cannot be isolated")
            copy = copies[0]
            result[f"CountD2H_{branch.upper()}_API_ms"] = (copy["api_end"] - copy["api_start"]) / 1e6
            result[f"CountD2H_{branch.upper()}_GPU_ms"] = (copy["end"] - copy["start"]) / 1e6
        allocations = {}
        peak = 0
        for row in db.execute(
            "SELECT * FROM CUDA_GPU_MEMORY_USAGE_EVENTS WHERE memKind=2 ORDER BY start"
        ):
            key = row["contextId"], row["address"]
            if row["memoryOperationType"] == 0:
                if key in allocations:
                    raise ValueError("Duplicate live device allocation")
                allocations[key] = row["bytes"]
            elif row["memoryOperationType"] == 1:
                if key not in allocations:
                    raise ValueError("Free without a recorded allocation")
                del allocations[key]
            else:
                raise ValueError("Unsupported allocation event type")
            peak = max(peak, sum(allocations.values()))
        result["Observed_dynamic_device_allocation_peak_bytes"] = peak
        result["Observed_dynamic_device_allocations_remaining_bytes"] = sum(allocations.values())
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = {f"{site}/large": extract(args.evidence / "profiling" / site / "capture.sqlite")
              for site in ("site1", "site2", "site3")}
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
