import ntpath
from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import process_guard_churn_1027 as candidate  # noqa: E402
import process_snapshot_adapter_1027 as adapter  # noqa: E402


TARGET = r"X:\PROJECT_ROOT\work\s05_air_sweep_property_fix_luna_951"
UNRELATED_EXE = r"X:\SYSTEM_ROOT\python.exe"


def resolve(path, _cwd=None):
    if path == "<unreadable>":
        raise OSError("synthetic unreadable path")
    return ntpath.normcase(ntpath.normpath(path))


def row(name="notepad.exe", cwd=r"<LOCAL_ABSOLUTE_PATH>", exe=UNRELATED_EXE):
    return {
        "pid": 4401,
        "name": name,
        "created_utc": "2026-11-18T00:00:00+00:00",
        "parent_pid": 4,
        "executable_path": exe,
        "executable_sha256": "a" * 64,
        "command_line_args": [exe],
        "cwd": cwd,
        "parent_chain": [{
            "pid": 4,
            "name": "System",
            "created_utc": "2020-01-01T00:00:00+00:00",
            "parent_pid": 0,
            "executable_sha256": None,
        }],
        "parent_chain_complete": True,
        "identity_readable": {
            "pid": True,
            "name": True,
            "creation_time": True,
            "executable_path": True,
            "command_line": True,
            "cwd": True,
            "parent_chain": True,
        },
    }


class ChurnPolicyTests(unittest.TestCase):
    def test_fully_identified_unrelated_nonworker_is_permitted(self):
        result = candidate.classify_churn_process(row(), TARGET, resolve)
        self.assertTrue(result["allowed"])
        self.assertEqual(result["record"]["classification"],
                         "VERIFIED_UNRELATED_PROCESS_CHURN")
        self.assertNotIn("executable_path", result["record"])

    def test_unreadable_process_name_blocks(self):
        item = row(name=None)
        item["identity_readable"]["name"] = False
        result = candidate.classify_churn_process(item, TARGET, resolve)
        self.assertFalse(result["allowed"])
        self.assertEqual(result["blocker"], "PROCESS_IDENTITY_UNREADABLE")

    def test_new_python_worker_blocks_even_with_unrelated_paths(self):
        result = candidate.classify_churn_process(row(name="python.exe"), TARGET, resolve)
        self.assertFalse(result["allowed"])
        self.assertEqual(result["blocker"], "NEW_COMSOL_OR_WORKER_DURING_SCAN")

    def test_target_path_association_blocks(self):
        result = candidate.classify_churn_process(
            row(cwd=TARGET + r"\job_runs"), TARGET, resolve
        )
        self.assertFalse(result["allowed"])
        self.assertEqual(result["blocker"], "NEW_PROCESS_PATH_NOT_PROVEN_UNRELATED")

    def test_unreadable_path_blocks(self):
        result = candidate.classify_churn_process(
            row(exe="<unreadable>"), TARGET, resolve
        )
        self.assertFalse(result["allowed"])
        self.assertEqual(result["blocker"], "NEW_PROCESS_PATH_NOT_PROVEN_UNRELATED")

    def test_changed_pid_set_is_complete_only_after_identity_reconciliation(self):
        after = {101, 102}
        seen = {101: 10.0}
        after_identity = {101: 10.0, 102: 20.0}
        self.assertFalse(candidate.census_complete_after_reconciliation(
            after, seen, after_identity, {}
        ))
        self.assertTrue(candidate.census_complete_after_reconciliation(
            after, seen, after_identity, {102: 20.0}
        ))

    def test_same_pid_reuse_at_after_census_is_a_new_identity(self):
        new_created = candidate.base_guard._created_epoch(row()["created_utc"])
        old_created = new_created - 10.0
        events, blockers = candidate.identity_change_events(
            {4401}, {4401: old_created}, {4401: old_created},
            {4401}, {4401: new_created}, new_created - 5.0
        )
        self.assertEqual(blockers, [])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["pid"], 4401)
        self.assertEqual(events[0]["created_epoch"], new_created)
        self.assertEqual(events[0]["observed_stages"], ["after"])
        reused = row(name="python.exe")
        reused["pid"] = 4401
        reused["created_utc"] = candidate.base_guard._utc(new_created)
        decision = candidate.classify_identity_event(events[0], reused, TARGET, resolve)
        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["blocker"], "NEW_COMSOL_OR_WORKER_DURING_SCAN")

    def test_observed_worker_exit_before_after_census_is_retained_and_blocked(self):
        worker_created = candidate.base_guard._created_epoch(row()["created_utc"])
        events, blockers = candidate.identity_change_events(
            set(), {}, {4401: worker_created}, set(), {}, worker_created - 5.0
        )
        self.assertEqual(blockers, [])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["observed_stages"], ["seen"])
        worker = row(name="java.exe")
        worker["pid"] = 4401
        worker["created_utc"] = candidate.base_guard._utc(worker_created)
        decision = candidate.classify_identity_event(events[0], worker, TARGET, resolve)
        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["blocker"], "NEW_COMSOL_OR_WORKER_DURING_SCAN")
        retained = dict(decision["record"], observed_stages=events[0]["observed_stages"],
                        live_after=False)
        self.assertEqual(retained["name"], "java.exe")
        self.assertEqual(retained["observed_stages"], ["seen"])
        self.assertFalse(retained["live_after"])

    def test_unreadable_identity_cannot_be_erased_by_later_retry(self):
        calls = []
        snapshots = [
            {"status": "BLOCKED", "blockers": ["PROCESS_IDENTITY_UNREADABLE"],
             "enumeration_complete": False},
            {"status": "CLEAR", "blockers": [], "enumeration_complete": True},
        ]

        def collector(_target):
            calls.append(True)
            return snapshots[len(calls) - 1]

        with self.assertRaisesRegex(RuntimeError, "cannot erase"):
            adapter.collect_clear_snapshot(TARGET, collector)
        self.assertEqual(len(calls), 1)

    def test_unknown_comsol_gui_cannot_be_erased_by_later_retry(self):
        calls = []
        snapshots = [
            {"status": "BLOCKED", "blockers": ["UNKNOWN_COMSOL_PROCESS"],
             "enumeration_complete": True},
            {"status": "CLEAR", "blockers": [], "enumeration_complete": True},
        ]

        def collector(_target):
            calls.append(True)
            return snapshots[len(calls) - 1]

        with self.assertRaisesRegex(RuntimeError, "UNKNOWN_COMSOL_PROCESS"):
            adapter.collect_clear_snapshot(TARGET, collector)
        self.assertEqual(len(calls), 1)

    def test_incomplete_attempt_history_survives_a_benign_retry(self):
        calls = []
        snapshots = [
            {"status": "BLOCKED", "blockers": ["PROCESS_ENUMERATION_INCOMPLETE"],
             "enumeration_complete": False, "process_churn": [],
             "identity_census": {"before_count": 5}},
            {"status": "CLEAR", "blockers": [], "enumeration_complete": True,
             "process_churn": [], "identity_census": {"before_count": 5}},
        ]

        def collector(_target):
            calls.append(True)
            return snapshots[len(calls) - 1]

        result, _collected = adapter.collect_clear_snapshot(TARGET, collector)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(result["attempt_history"]), 2)
        self.assertEqual(result["attempt_history"][0]["blockers"],
                         ["PROCESS_ENUMERATION_INCOMPLETE"])
        self.assertEqual(result["attempt_history"][0]["identity_census"],
                         {"before_count": 5})

    def test_synthetic_visible_comsolui_remains_unknown_under_reused_gui_rule(self):
        result = adapter.base_guard.classify_snapshot(
            {"enumeration_complete": True, "processes": [{
                "pid": 12345,
                "name": "ComsolUI",
                "created_utc": "2020-01-02T03:04:05+00:00",
                "main_window_visible": True,
                "file_version": "6.4.0.293",
            }]},
            TARGET,
            resolve_path=resolve,
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("UNKNOWN_COMSOL_PROCESS", result["blockers"])

    def test_nonworker_set_change_needs_matching_unrelated_path_proof(self):
        record = {"pid": 4401, "name": "unknown.exe",
                  "created_utc": "2026-11-18T00:00:00+00:00",
                  "classification": "VERIFIED_NON_WORKER_PROCESS"}
        snapshot = {"process_churn": []}
        self.assertFalse(adapter._proven_unrelated_nonworker(record, snapshot))
        identity = {
            "pid": 4401, "name": "unknown.exe",
            "created_utc": record["created_utc"],
            "classification": "VERIFIED_UNRELATED_PROCESS_CHURN",
        }
        snapshot["process_churn"] = [{
            "pid": 4401, "name": "unknown.exe",
            "created_utc": record["created_utc"],
            "classification": "VERIFIED_UNRELATED_PROCESS_CHURN",
            "identity": identity,
            "identity_sha256": adapter.base_guard._json_sha(identity),
        }]
        self.assertTrue(adapter._proven_unrelated_nonworker(record, snapshot))


if __name__ == "__main__":
    unittest.main()
