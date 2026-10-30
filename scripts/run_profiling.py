#!/usr/bin/env python3
# Authors: Le Thuong De (23120232)
# External source: none
"""Collect batch profiling and synthetic accuracy; never calculate official speedup."""
import argparse
from pathlib import Path
import sys
from profiler_batch import collect
from profiling_common import BatchError, inspect_environment, write_json
from synthetic_batch import check_case, inputs, write_summary


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stitch", type=Path, help="stitch or explicitly scoped stage driver")
    parser.add_argument("--versions", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--synthetic", type=Path, help="six pairs from make_synthetic_pair.py")
    parser.add_argument("--dataset", type=Path, help="prepared site1/site2/site3 dataset")
    parser.add_argument("--sites", nargs="+", choices=["site1", "site2", "site3", "challenge"], default=["site1", "site2", "site3"])
    parser.add_argument("--sizes", nargs="+", choices=["small", "medium", "large"], default=["small", "medium", "large"])
    parser.add_argument("--profilers", nargs="+", choices=["nsys", "ncu"], default=["nsys", "ncu"])
    parser.add_argument("--profile-command", nargs=argparse.REMAINDER, help="standalone executable and arguments; put last")
    parser.add_argument("--scope", choices=["pipeline", "s45"], default="pipeline")
    parser.add_argument("--kernel-regex", help="Nsight Compute kernel name regex")
    parser.add_argument("--launch-count", type=int, default=1, help="Nsight Compute launches per invocation")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--require-t4", action="store_true")
    args = parser.parse_args(argv)
    if any(v < 0 for v in args.versions) or len(set(args.versions)) != len(args.versions):
        parser.error("--versions must contain unique nonnegative integers")
    if args.launch_count < 1:
        parser.error("--launch-count must be positive")
    if not (args.synthetic or args.dataset or args.profile_command):
        parser.error("provide --synthetic, --dataset or --profile-command")
    if (args.synthetic or args.dataset) and not args.stitch:
        parser.error("--stitch is required for image batches")
    if args.profile_command and (args.synthetic or args.dataset):
        parser.error("run standalone profiling separately from image batches")
    return args


def main(argv=None):
    args = parse_args(argv)
    # Validate all inputs before launching any expensive job.
    pairs = inputs(args.synthetic.resolve()) if args.synthetic else []
    commands = []
    binary = args.stitch.resolve() if args.stitch else None
    if args.dataset:
        for version in args.versions:
            for site in args.sites:
                for size in args.sizes:
                    left = (args.dataset / site / f"{size}_left.jpg").resolve()
                    right = (args.dataset / site / f"{size}_right.jpg").resolve()
                    if not left.is_file() or not right.is_file():
                        raise BatchError(f"Dataset pair missing: {site}/{size}")
                    label = f"v{version}/{site}/{size}"
                    commands.append((label, [str(binary), str(left), str(right),
                        str((args.out / label / "panorama.png").resolve()), "--version", str(version), "--runs", "1", "--debug"]))
    if args.profile_command:
        commands.append(("standalone", args.profile_command))
    environment = inspect_environment(binary or (args.profile_command[0] if args.profile_command else None), args.require_t4)
    if args.out.exists() and any(args.out.iterdir()):
        raise BatchError("Output directory must be empty; preserve previous evidence")
    args.out.mkdir(parents=True, exist_ok=True)
    write_json(args.out / "environment.json", environment)
    rows = [check_case(binary, version, pair, args.out / "synthetic", args.scope)
            for version in args.versions for pair in pairs]
    if rows:
        write_summary(args.out, rows)
    profiles = []
    for label, command in commands:
        (args.out / label).mkdir(parents=True, exist_ok=True)
        for profiler in args.profilers:
            result = collect(profiler, command, (args.out / label / profiler).resolve(), args.kernel_regex, args.launch_count,
                             "standalone" if args.profile_command else args.scope)
            result.update(label=label, scope="standalone" if args.profile_command else args.scope)
            profiles.append(result)
    summary = {"scope": "standalone" if args.profile_command else args.scope, "synthetic": rows, "profiling": profiles,
               "note": "Profiling is diagnostic; these runs are not official benchmark timing."}
    write_json(args.out / "summary.json", summary)
    failures = sum(row["status"] != "ok" for row in [*rows, *profiles])
    print(f"Batch: synthetic={len(rows)} profiling={len(profiles)} failures={failures}")
    return int(failures != 0)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, BatchError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
