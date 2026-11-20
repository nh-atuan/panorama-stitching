# Authors: Le Ha Thanh Chuong (23120195)
# External source: none
"""Build an isolated, instrumented copy of the production V4 source path."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f"Production instrumentation anchor changed: {old[:100]!r}")
    return source.replace(old, new, 1)


def overlay_sources(destination):
    files = {}
    names = ("src/main.cu", "src/v1/v1_pipeline.cu",
             "src/v1/s1/v1_preprocess.cu", "src/v1/s2/v1_detect.cu",
             "src/v1/s3/v1_describe.cu")
    for name in names:
        source = (ROOT / name).read_text(encoding="utf-8")
        source = '#include "p10_pres4_probe.cuh"\n' + source
        if name.endswith("main.cu"):
            source = replace_once(source, "    V1DeviceOwner owner;",
                                  "    panorama::pres4::environment(left, right, config);\n"
                                  "    V1DeviceOwner owner;")
            source = replace_once(source, "    using Clock = std::chrono::steady_clock;",
                                  "    panorama::pres4::Context probe(measure);\n"
                                  "    using Clock = std::chrono::steady_clock;")
            source = replace_once(source, "    if (measure) events.h2d_start.record(stream);",
                                  "    probe.begin(stream);\n"
                                  "    if (measure) events.h2d_start.record(stream);\n"
                                  "    { panorama::pres4::Span upload(panorama::pres4::UploadA, stream);")
            source = replace_once(source, "    CUDA_CHECK(cudaMemcpy2DAsync(workspace.d_imageB",
                                  "    }\n    { panorama::pres4::Span upload(panorama::pres4::UploadB, stream);\n"
                                  "    CUDA_CHECK(cudaMemcpy2DAsync(workspace.d_imageB")
            source = replace_once(source, "    if (measure) events.h2d_stop.record(stream);",
                                  "    }\n    if (measure) events.h2d_stop.record(stream);")
            source = replace_once(source, "    return timing;\n}", "    probe.write(timing, workspace);\n    return timing;\n}")
        elif name.endswith("v1_pipeline.cu"):
            source = replace_once(source, "        const Stage stage = static_cast<Stage>(i);",
                                  "        const Stage stage = static_cast<Stage>(i);\n"
                                  "        if (stage == Stage::Match) pres4::before_s4(stream);")
        elif name.endswith("v1_preprocess.cu"):
            for suffix, slot in (("a", "S1A"), ("b", "S1B")):
                anchor = f'V1NvtxRange range("S1.image_{suffix}");'
                source = replace_once(source, anchor, anchor + f"\n    pres4::Span probe(pres4::{slot}, stream);")
        elif name.endswith("v1_detect.cu"):
            for suffix, slot in (("a", "S2A"), ("b", "S2B")):
                anchor = f'V1NvtxRange range("S2.image_{suffix}");'
                source = replace_once(source, anchor, anchor +
                    f"\n    pres4::set_branch({'true' if suffix == 'a' else 'false'});\n"
                    f"    pres4::Span probe(pres4::{slot}, stream);")
            source = replace_once(source, "            if (cudaPeekAtLastError() != cudaSuccess ||",
                                  "            { pres4::Span count_copy(pres4::count_slot(), stream);\n"
                                  "            if (cudaPeekAtLastError() != cudaSuccess ||")
            source = replace_once(source, "                    cudaSuccess ||\n                cudaStreamSynchronize(stream) != cudaSuccess)",
                                  "                    cudaSuccess) { return ErrorCode::CudaFailure; }\n"
                                  "            }\n"
                                  "            if (pres4::wait(stream) != cudaSuccess)")
        else:
            anchor = 'V1NvtxRange range(job.image_a ? "S3.image_a" : "S3.image_b");'
            source = replace_once(source, anchor, anchor +
                "\n        pres4::Span probe(job.image_a ? pres4::S3A : pres4::S3B, stream);")
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
        files[name] = str(target)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "build/pres4")
    parser.add_argument("--overlay-only", action="store_true")
    args = parser.parse_args()
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    mapping = overlay_sources(out / "overlay")
    from build import compiler_flags, discover_stitch_sources, STB_SOURCE
    command = ["nvcc", *compiler_flags(True, False, True), "-Isrc",
               "-Itests/tools", *[mapping.get(s, s) for s in discover_stitch_sources()],
               STB_SOURCE, "-ldl", "-o", str(out / "stitch")]
    # stb is built by the production builder without strict warnings.
    stb = out / "stb_impl.o"
    stb_command = ["nvcc", *compiler_flags(True, False, False), "-Isrc", "-c",
                   STB_SOURCE, "-o", str(stb)]
    command[command.index(STB_SOURCE)] = str(stb)
    (out / "build_commands.json").write_text(json.dumps(
        [stb_command, command], indent=2) + "\n", encoding="utf-8")
    if not args.overlay_only:
        for cmd in (stb_command, command):
            subprocess.run(cmd, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
