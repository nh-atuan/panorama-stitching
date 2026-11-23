# Authors: Le Ha Thanh Chuong (23120195)
# External source: none

"""Validate committed P10 tables; derived statistics do not certify raw GPU evidence."""

import hashlib
import math
from pathlib import Path
import re
import statistics
import unicodedata

STANDARD_CASES = {(site, size) for site in ("site1", "site2", "site3")
                  for size in ("small", "medium", "large")}
PRIMARY_CASE = ("site2", "large")
MIN_PAIRED_MEDIAN = 1.05
MIN_BENEFICIAL_BLOCKS = 4
BENCHMARK = ("Cấu hình", "Độ phân giải", "V0 CPU (ms)", "V4 Production (ms)",
             "V5 Sequential (ms)", "V5 DualStream (ms)")
PRES4 = ("Cấu hình", "Độ phân giải", "Pre-S4 Seq (ms)", "Pre-S4 Dual (ms)",
         "Host Pre-S4 Dual (ms)", "CountWait A (ms)", "CountWait B (ms)")
PAIRED = ("Khối", "Thứ tự chạy", "V4 Total (ms)", "V5 Dual Total (ms)",
          "V5 Dual Pre-S4 (ms)")
PROFILE = ("Ca (`large`)", "Chế độ", "`H2D → S4 start` (ms)",
           "Thời lượng chồng lấn (ms)", "Tỷ lệ chồng lấn (%)",
           "Số stream hoạt động trước S4", "Peak VRAM (MiB)", "VRAM còn lại (B)")


def clean(value):
    return " ".join(unicodedata.normalize("NFKC", str(value)).replace("**", "")
                    .replace("`", "").replace("\u00a0", " ").split())


def read_table(path, first_headers, required=(), context=None):
    """Select a unique Markdown table by leading headers and validate every row."""
    path = Path(path)
    prefix = tuple(map(clean, first_headers))
    matches = []
    lines = path.read_text(encoding="utf-8").splitlines()
    split = lambda line: [part.strip() for part in line.strip().strip("|").split("|")]
    heading = ""
    for i, line in enumerate(lines):
        if line.lstrip().startswith("#"):
            heading = clean(line)
        if not line.lstrip().startswith("|"):
            continue
        header = split(line)
        normalized = list(map(clean, header))
        if tuple(normalized[:len(prefix)]) != prefix:
            continue
        if context and context not in heading:
            raise ValueError(f"{path}: table {prefix} must identify {context} in its section heading")
        if len(set(normalized)) != len(header):
            raise ValueError(f"{path}: duplicated headers in table {prefix}")
        missing = set(map(clean, required)) - set(normalized)
        if missing:
            raise ValueError(f"{path}: table {prefix} missing required fields: {sorted(missing)}")
        if i + 1 >= len(lines) or not all(re.fullmatch(r":?-{3,}:?", p)
                                             for p in split(lines[i + 1])):
            raise ValueError(f"{path}: table {prefix} has no Markdown separator")
        if len(split(lines[i + 1])) != len(header):
            raise ValueError(f"{path}: table {prefix} separator width differs from header")
        rows = []
        for line_number, record in enumerate(lines[i + 2:], i + 3):
            if not record.lstrip().startswith("|"):
                break
            values = split(record)
            if len(values) != len(header) or any(not clean(v) for v in values):
                raise ValueError(f"{path}:{line_number}: malformed row in table {prefix}")
            rows.append(dict(zip(header, values)))
        if not rows:
            raise ValueError(f"{path}: empty table {prefix}")
        matches.append(rows)
    if len(matches) != 1:
        raise ValueError(f"{path}: expected one table with headers {prefix}; found {len(matches)}")
    return matches[0]


def number(value, field, unit="", positive=True, integer=False):
    """Accept decimal comma OR decimal point, optional explicit unit, never NaN/defaults."""
    value = clean(value)
    pattern = r"([+-]?(?:\d+(?:[.,]\d+)?)(?:[eE][+-]?\d+)?)\s*(.*?)"
    match = re.fullmatch(pattern, value)
    if not match or match[2] not in ("", unit):
        raise ValueError(f"{field}: invalid numeric value {value!r}; expected {unit or 'number'}")
    result = float(match[1].replace(",", "."))
    if not math.isfinite(result) or (result <= 0 if positive else result < 0):
        raise ValueError(f"{field}: expected finite {'positive' if positive else 'nonnegative'} value")
    if integer and result != int(result):
        raise ValueError(f"{field}: expected an integer, got {value!r}")
    return int(result) if integer else result


def table(path, schema):
    prefix = schema[:3] if schema in (BENCHMARK, PRES4) else schema[:2]
    rows = read_table(path, prefix, required=schema,
                      context="site2/large" if schema == PAIRED else None)
    # Header emphasis/whitespace is presentation, not part of the machine schema.
    return [{clean(k): v for k, v in row.items()} for row in rows]


def timed_cases(rows, columns, label, allow_challenge=False):
    result, challenge = {}, {}
    for row in rows:
        case = (clean(row["Cấu hình"]), clean(row["Độ phân giải"]))
        destination = result if case in STANDARD_CASES else challenge
        if case not in STANDARD_CASES and not (allow_challenge and case[0] == "challenge"
                                               and case[1] in ("small", "medium", "large")):
            raise ValueError(f"{label}: unexpected configuration {case}")
        if case in destination:
            raise ValueError(f"{label}: duplicated configuration {case}")
        destination[case] = {key: number(row[key], f"{label}/{case}/{key}", "ms",
                                       positive=not key.startswith("CountWait")) for key in columns}
    if set(result) != STANDARD_CASES:
        raise ValueError(f"{label}: expected nine standard configurations; missing {sorted(STANDARD_CASES - result.keys())}")
    return result, challenge


def geomean(values):
    values = list(values)
    return math.exp(math.fsum(map(math.log, values)) / len(values))


def provenance(path, root=None):
    text = Path(path).read_text(encoding="utf-8")
    fields = {}
    for line in text.splitlines():
        normalized = clean(line)
        if normalized.startswith("- ") and ":" in normalized:
            key, value = normalized[2:].split(":", 1)
            fields[key] = value.strip().rstrip(".")
    required = ("Môi trường", "Thời điểm hoàn tất", "Commit SHA kiểm chứng", "Gói bằng chứng")
    for field in required:
        if field not in fields:
            raise ValueError(f"{path}: missing provenance field {field!r}")
    sha = fields["Commit SHA kiểm chứng"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError(f"{path}: invalid measurement source SHA {sha!r}")
    archive = re.search(r"results/[^\s()]+\.zip", fields["Gói bằng chứng"])
    digest = re.search(r"\b[0-9a-f]{64}\b", fields["Gói bằng chứng"])
    if not archive or not digest:
        raise ValueError(f"{path}: evidence archive path or SHA-256 is missing")
    raw = Path(root) / archive[0] if root else None
    present = raw is not None and raw.is_file()
    return dict(report=str(path), report_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                measurement_source_sha=sha, measured_at=fields["Thời điểm hoàn tất"],
                environment=fields["Môi trường"], archive_reference=archive[0],
                archive_reported_sha256=digest[0], raw_archive_present=present,
                raw_independently_verified=False,
                basis="Committed report tables, rounded milliseconds; raw CSV/SQLite not independently verified")


def adoption(text):
    """Read explicit decision labels, without deriving the group's choice from timing."""
    selected = {}
    in_decision = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_decision = "APOD" in line and "quyết định" in line.lower()
        if not in_decision:
            continue
        value = clean(line)
        for field, label in (("production", "production baseline"), ("case_study", "concurrency case study")):
            if label in value.lower():
                versions = set(re.findall(r"\bV[0-5]\b", value))
                if len(versions) != 1 or field in selected:
                    raise ValueError(f"APOD decision: ambiguous {label} version")
                selected[field] = versions.pop()
    if set(selected) != {"production", "case_study"}:
        raise ValueError("APOD decision: missing explicit production/case-study labels")
    return selected


def analyze(path, root=None):
    """Keep timing sessions separate; ignore rounded speedup columns when deriving ratios."""
    path = Path(path)
    benchmark_rows = table(path, BENCHMARK)
    benchmark, challenge = timed_cases(benchmark_rows, BENCHMARK[2:], "benchmark", True)
    pres4_rows = table(path, PRES4)
    pres4, _ = timed_cases(pres4_rows, PRES4[2:], "pre-S4")
    ratios = lambda numerator, denominator: [r[numerator] / r[denominator] for r in benchmark.values()]
    v4_dual = ratios(BENCHMARK[3], BENCHMARK[5])
    primary = benchmark[PRIMARY_CASE]
    metrics = dict(geomean_nine=geomean(v4_dual),
        geomean_v5_v0=geomean(ratios(BENCHMARK[2], BENCHMARK[5])),
        geomean_dual_seq=geomean(ratios(BENCHMARK[4], BENCHMARK[5])),
        geomean_medium_large=geomean(r[BENCHMARK[3]] / r[BENCHMARK[5]]
                                    for case, r in benchmark.items() if case[1] != "small"),
        arithmetic_mean=statistics.mean(v4_dual),
        ratio_of_sums=sum(r[BENCHMARK[3]] for r in benchmark.values()) /
                      sum(r[BENCHMARK[5]] for r in benchmark.values()),
        primary_case=primary[BENCHMARK[3]] / primary[BENCHMARK[5]],
        geomean_pres4=geomean(r[PRES4[2]] / r[PRES4[3]] for r in pres4.values()),
        faster_cases=sum(r > 1 for r in v4_dual))
    paired_rows = table(path, PAIRED)
    paired = {}
    for row in paired_rows:
        block = number(row[PAIRED[0]], "paired block", integer=True)
        order = clean(row[PAIRED[1]])
        expected = "v4 → v5_dual" if block % 2 else "v5_dual → v4"
        if order != expected or block in paired:
            raise ValueError(f"paired block {block}: expected unique alternating order {expected!r}")
        values = {key: number(row[key], f"block {block}/{key}", "ms") for key in PAIRED[2:]}
        paired[block] = values[PAIRED[2]] / values[PAIRED[3]]
    if set(paired) != set(range(1, 6)):
        raise ValueError("paired blocks: expected exactly blocks 1..5")
    metrics.update(paired_median=statistics.median(paired.values()),
                   beneficial_blocks=sum(r > 1 for r in paired.values()))
    profile_rows = table(path, PROFILE)
    profile = {}
    for row in profile_rows:
        site, mode = clean(row[clean(PROFILE[0])]), clean(row[PROFILE[1]])
        case = (site, mode)
        if site not in ("site1/large", "site2/large", "site3/large") or mode not in ("V4 Prod", "V5 Seq", "V5 Dual") or case in profile:
            raise ValueError(f"NSYS: unexpected or duplicated configuration {case}")
        value = {key: number(row[clean(key)], f"NSYS/{case}/{key}", unit,
                            positive=False, integer=integer)
                 for key, unit, integer in zip(PROFILE[2:], ("ms", "ms", "%", "", "MiB", "B"),
                                               (False, False, False, True, False, True))}
        if value[PROFILE[4]] > 100:
            raise ValueError(f"NSYS/{case}: overlap percentage exceeds 100")
        profile[case] = value
    expected = {(f"site{i}/large", mode) for i in (1, 2, 3) for mode in ("V4 Prod", "V5 Seq", "V5 Dual")}
    if set(profile) != expected:
        raise ValueError("NSYS: expected nine large configurations (three sites x three modes)")
    dual = [profile[(f"site{i}/large", "V5 Dual")] for i in (1, 2, 3)]
    metrics.update(overlap_min=min(r[PROFILE[4]] for r in dual),
                   overlap_max=max(r[PROFILE[4]] for r in dual),
                   vram_increases_mib=[profile[(f"site{i}/large", "V5 Dual")][PROFILE[6]] -
                                       profile[(f"site{i}/large", "V4 Prod")][PROFILE[6]] for i in (1, 2, 3)])
    # Record the published decision; the two paired gates are computed independently.
    decision = adoption(path.read_text(encoding="utf-8"))
    return dict(benchmark_rows=benchmark_rows, benchmark=benchmark, challenge=challenge,
                pres4_rows=pres4_rows, pres4=pres4, paired_rows=paired_rows, paired=paired,
                profile_rows=profile_rows, metrics=metrics, provenance=provenance(path, root),
                decision=dict(**decision,
                              median_gate=metrics["paired_median"] >= MIN_PAIRED_MEDIAN,
                              consistency_gate=metrics["beneficial_blocks"] >= MIN_BENEFICIAL_BLOCKS,
                              thresholds=dict(median=MIN_PAIRED_MEDIAN, beneficial_blocks=MIN_BENEFICIAL_BLOCKS)))
