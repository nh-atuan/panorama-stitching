# P9 Final Notebook Handoff

Chương (P9-T07) supplies the ten-section report, technical narrative, source excerpts, and executable summaries of the verified V0–V3 evidence. Thành (P9-T03) owns live data acquisition and loading, tables and charts, and the results gallery. Đế supplies V4 benchmark and profiling evidence (P9-T05). Tuấn supplies integrated V4 acceptance and memcheck evidence (P9-T02).

## Thanh integration points

Use the cell IDs in `Group16_Final.ipynb` as insertion points. Keep the data producer and loader ahead of every view. The historical evidence cells read versioned Markdown directly and run independently of the final benchmark.

| Section and anchor cell | Thành's output | Inputs and dependencies |
| --- | --- | --- |
| 1 · after `thanh-data-setup` | Dataset acquisition, build and one same-session benchmark, then the common loader | Runtime cell provides `REPO_ROOT`, `DATASET_DIR`, `BENCHMARK_DIR`, `BASELINE_VERSIONS`, and `TIMED_RUNS`. Publish `run_versions`, the resolved paths and the loaded objects defined below. |
| 4 · after `thanh-v0-view` | V0 per-stage table, dominant stage and one standard panorama | Filter the shared averages to V0. Use a panorama from the same artifact root. |
| 5 · after `thanh-v1-view` | V1 timing, transfer and kernel breakdown, V1/V0 ratios and acceptance reference | Filter shared averages and speedups to V1. Link the appropriate correctness evidence. |
| 6 · after `v4-artifact-status` | V4 result table and profiler evidence after integrated acceptance | Use the common loader plus Đế's P9-T05 and Tuấn's P9-T02 outputs. Keep the pending message if unavailable. |
| 7 · after `comparison` | Cross-version table, speedup charts and best-version per-stage breakdown | Use the common loader. Group by site and size. Use the actual GPU from `environment.json`. Treat failed runs as statuses. |
| 8 · after `gallery`, before `challenge-status` | Input pair, panorama and failure gallery | Use the dataset paths and benchmark panoramas below. Keep a visible label when a panorama or the course-provided sample is unavailable in the development run. |

### Producer and dataset

- Use the [final dataset ZIP](https://drive.google.com/drive/folders/1_J_q5q-K1g7ZNnczTWvXBzwpOsof9ghL), or a supplied copy of the same archive. Verify the extracted `manifest.csv` and file hashes with `validate_dataset()` in [`scripts/midterm_notebook.py`](../../scripts/midterm_notebook.py). The final mapping is `site1=thanh-standard1`, `site2=thanh-standard2`, `site3=de-standard2`, and `challenge=de-challenge1`. Input files are `<dataset>/<site>/<size>_{left,right}.jpg`, with `small`, `medium` and `large`. [Dataset specification](../dataset.md)
- Build the integrated source with the repository script. Capture the production Git SHA and dataset manifest SHA-256 with the run. Run every accepted version together, writing into one fresh results directory. V4 joins `run_versions` after the integrated CLI and acceptance evidence are available. The pinned P9 documentation snapshot does not expose production `--version 4`.

```bash
python scripts/build.py --compiler nvcc --require-t4 --out-dir build
python scripts/run_benchmark.py --stitch build/stitch --dataset dataset --runs 5 \
  --out results/final --versions 0 1 2 3 --include-challenge
```

- The [Drive archive](https://drive.google.com/drive/folders/1uJ-4_kgVONvIt5NQIPzdEWTIPrg8Sue1) supplies historical provenance and profiler artifacts. Generate Section 7 from the fresh common benchmark directory. The course-provided sample is a separate optional input during P9 development. Pin its source and stage its images and panorama outside the standard benchmark dataset for the final gallery. No course sample asset was identified in this checkout.

### Loader inputs and outputs

Use the canonical schemas in [`scripts/run_benchmark.py`](../../scripts/run_benchmark.py). Read each file once. A DataFrame implementation can use the following notebook variables.

| Object | Source | Required contract |
| --- | --- | --- |
| `benchmark_summary` | `BENCHMARK_DIR/v<k>/summary.csv` for each `k` in `run_versions` | One row per `version,site,size,stat`, using `SUMMARY_COLUMNS`. Preserve `S1_ms` through `S6_ms`, `Total_ms`, `H2D_ms`, `D2H_ms`, `Total_Kernel_ms`, stage share columns and `hot_stage`. `stat` is `average` or `minimum`. CPU transfer and kernel cells may be blank. |
| `benchmark_speedup` | `BENCHMARK_DIR/speedup.csv` | One successful row per `site,size,version`, using `SPEEDUP_COLUMNS`. Keep `Total_ms`, `Total_Kernel_ms`, `speedup_vs_v0`, `speedup_vs_prev`, `kernel_speedup_vs_v0`, and the per-stage ratio fields. The runner compares the first version to itself for the previous-version ratio. Its V0 kernel field uses CPU total as the reference for kernel speedups. Empty ratios stay empty if a comparison input failed. |
| `benchmark_failures` | `BENCHMARK_DIR/v<k>/failures.csv` for each challenged version | Concatenate rows with `version,site,size,exit_code,error` from `FAILURE_COLUMNS`. Header-only is a valid result. Retain matching `v<k>/<site>/<size>.log` for the gallery. |
| `benchmark_environment` | `BENCHMARK_DIR/environment.json` | Mapping with `gpu`, `cpu`, `time_utc`, `runs`, `versions`, `include_challenge`, `stitch_sha256`, `python` and `commands`. Use it to label the run and validate its scope. |

The per-configuration CSVs are under `v<k>/<site>/<size>.csv`. If a view needs run-level traces, use the existing `version_columns(k)` and `parse_version_csv()` rather than assuming one header across versions. V0 has `Run_Index,S1_ms,…,S6_ms,Total_ms`. V2 places `H2D_ms,D2H_ms,Total_Kernel_ms` before `Total_ms`, while V1 and V3 use version-tagged stage names and put `Total_ms` before those transfer/kernel fields. Consume the normalized summary columns for cross-version plots.

Successful benchmark panoramas are `v<k>/<site>/<size>_panorama.jpg`. Read input A and B from `DATASET_DIR` only in the gallery or when a view needs them. For an expected challenge failure, use the status and log in place of output imagery. Keep missing V4 files explicit during P9. During final submission, missing standard data for a requested version is an error. Report V4 comparison data only when the artifacts and matching production acceptance evidence are present.

## P10 submission checks

Pin the release source, integrate the live cells, and run the notebook top to bottom in a fresh Colab Tesla T4 session. Check that every timing number in the narrative is reproduced by an output cell, then save the executed notebook and export it to PDF. Complete the course-provided and own-image gallery with a failure example. Add the unlisted video link to the notebook and README, consolidate the team AI declaration, and verify the source archive and slides against the [assignment](../specs/CSC14120_2026_Final%20Project.md).
