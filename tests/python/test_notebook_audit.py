#!/usr/bin/env python3
# Authors: Le Ha Thanh Chuong (23120195)
# External source: none

"""Exercise preflight failure detection without GPU or network access."""

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import audit_final_notebook as audit
import run_benchmark as rb


class NotebookAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "report.ipynb"
        self.pin = "a" * 40
        cells = [dict(cell_type="markdown", id=f"section-{i}", metadata={},
                      source=f'<a id="{audit.ANCHORS[i-1]}"></a>\n## {i}. {title}\n\nSubstantive fixture content for this section.') for i, title in enumerate(audit.SECTIONS, 1)]
        cells.insert(1, dict(cell_type="code", id="runtime-setup", metadata={}, execution_count=1,
                             outputs=[dict(output_type="stream", name="stdout", text="ok\n")],
                             source=f'SOURCE_REF = "{self.pin}"\nREPO_URL="https://example.org"\n'
                                    'BASELINE_VERSIONS=(0,1,2,3,4)\nTIMED_RUNS=5\nprint("ok")'))
        cells.extend(dict(cell_type="code", id=role, metadata={}, execution_count=1,
                          outputs=[], source="value = 1") for role in audit.CODE_ROLES if role != "runtime-setup")
        self.data = dict(nbformat=4, nbformat_minor=5, metadata={}, cells=cells)

    def run_audit(self, data=None, missing_file=None):
        self.path.write_text(json.dumps(data or self.data), encoding="utf-8")

        def fake_git(root, *args):
            if args[0] == "show":
                return 0, "CANDIDATE_VERSIONS=(0,1,2,3,4,5)"
            return (1, "") if missing_file and args[-1].endswith(":" + missing_file) else (0, self.pin)

        with patch.object(audit, "git", side_effect=fake_git):
            return audit.audit(self.path, self.root, self.pin)

    @staticmethod
    def codes(result):
        return {f["code"] for f in result["findings"]}

    def test_valid_structure_and_source_inventory(self):
        result = self.run_audit()
        self.assertNotIn("SECTION_ORDER", self.codes(result))
        self.assertEqual(set(result["pin_files"]), set(audit.PIN_FILES))
        self.assertNotIn("MISSING_OUTPUT", self.codes(result))
        self.assertNotIn("LOCAL_MACHINE_PATH", self.codes(result))

    def test_missing_production_source_blocks_pin(self):
        self.assertIn("PIN_MISSING_FILE", self.codes(self.run_audit(
            missing_file="src/v5/v5_image_branch.cu")))

    def test_wrong_section_order(self):
        data = copy.deepcopy(self.data)
        data["cells"][2], data["cells"][3] = data["cells"][3], data["cells"][2]
        self.assertIn("SECTION_ORDER", self.codes(self.run_audit(data)))

    def test_titles_can_change_but_anchors_and_roles_cannot(self):
        data = copy.deepcopy(self.data)
        data["cells"][0]["source"] = data["cells"][0]["source"].replace(audit.SECTIONS[0], "Team Information")
        self.assertNotIn("SECTION_ORDER", self.codes(self.run_audit(data)))
        data["cells"][0]["source"] = data["cells"][0]["source"].replace('id="team-information"', 'id="broken"')
        self.assertIn("SECTION_ORDER", self.codes(self.run_audit(data)))
        self.assertTrue(audit.section_structure(self.data["cells"][:-1])[1])

    def test_syntax_and_unsaved_execution_are_distinct(self):
        data = copy.deepcopy(self.data)
        data["cells"][1].update(source="print(", execution_count=None, outputs=[])
        codes = self.codes(self.run_audit(data))
        self.assertTrue({"PYTHON_SYNTAX", "UNEXECUTED_CELLS", "MISSING_OUTPUT"} <= codes)

    def test_links_placeholders_and_local_paths(self):
        data = copy.deepcopy(self.data)
        data["cells"][0]["source"] += '\nTODO [missing](missing%20report.md) C:/Users/student/data'
        codes = self.codes(self.run_audit(data))
        self.assertTrue({"PLACEHOLDER", "BROKEN_LOCAL_LINK", "LOCAL_MACHINE_PATH"} <= codes)

    def test_no_execution_of_notebook_code(self):
        source = 'SOURCE_REF = "abc"\nraise RuntimeError("must not execute")'
        self.assertEqual(audit.constants(source), {"SOURCE_REF": "abc"})

    def test_schema_error_is_rejected(self):
        self.path.write_text('{"nbformat":3,"cells":[]}', encoding="utf-8")
        with self.assertRaises(ValueError):
            audit.audit(self.path, self.root)

    def test_apod_requires_nine_unique_cases_and_excludes_challenge(self):
        table = []
        for site in ("site1", "site2", "site3"):
            for size in ("small", "medium", "large"):
                table.append(f"| {site} | {size} | 100,0 | 20,0 | 10,0 | 10 | 2 |")
        table.append("| challenge | small | 100,0 | 1,0 | 999,0 | 0 | 0 |")
        self.path.write_text("\n".join(table), encoding="utf-8")
        result = audit.reconcile_apod(self.path)
        self.assertEqual(result["arithmetic_mean"], 2)
        self.assertAlmostEqual(result["geometric_mean"], 2)
        self.assertIsNone(result["median_paired_run_speedup"])
        self.path.write_text("\n".join(table[:-2]), encoding="utf-8")
        with self.assertRaises(ValueError):
            audit.reconcile_apod(self.path)

    def test_probe_mean_share_differs_from_ratio_of_means(self):
        self.path.write_text("case,PreS4_ms,Total_ms\nsite2/large,1,2\nsite2/large,1,10\n", encoding="utf-8")
        result = audit.reconcile_pres4(self.path)["site2/large"]
        self.assertAlmostEqual(result["mean_run_share"], 0.3)
        self.assertAlmostEqual(result["ratio_of_means"], 1 / 6)

    def test_csv_uses_version_schema_and_checks_summaries(self):
        header = rb.version_columns(2)
        values = ["1"] * (len(header) - 1)
        # The sum of stage intervals must not exceed Total_ms.
        values[-1] = "10"
        lines = [",".join(header)]
        lines += [f"{i}," + ",".join(values) for i in range(1, 6)]
        lines += [label + "," + ",".join(values) for label in ("Average", "Minimum")]
        self.path.write_text("\n".join(lines), encoding="utf-8")
        self.assertEqual(len(audit.check_csv(self.path, 2, 5)["runs"]), 5)
        self.path.write_text("\n".join(lines[:-1] + [lines[-1].replace("10", "11")]), encoding="utf-8")
        with self.assertRaises(ValueError):
            audit.check_csv(self.path, 2, 5)

    def test_gpu_csv_versions_are_not_interchangeable(self):
        self.path.write_text(",".join(rb.version_columns(4)), encoding="utf-8")
        with self.assertRaises(ValueError):
            audit.check_csv(self.path, 2, 5)

    def test_source_freeze_and_invalid_pin(self):
        data = copy.deepcopy(self.data)
        data["cells"][1]["source"] = 'TIMED_RUNS=0\nSOURCE_REF="main"'
        codes = self.codes(self.run_audit(data))
        self.assertTrue({"INVALID_SOURCE_PIN", "FREEZE_MISMATCH", "TIMED_RUNS", "MISSING_CONFIG"} <= codes)

    def test_saved_error_is_not_accepted(self):
        data = copy.deepcopy(self.data)
        data["cells"][1]["outputs"] = [dict(output_type="error", ename="RuntimeError",
                                           evalue="GPU failure", traceback=[])]
        self.assertIn("SAVED_EXECUTION_ERROR", self.codes(self.run_audit(data)))


if __name__ == "__main__":
    unittest.main()
