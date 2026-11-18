from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import coexistence_policy_1025 as policy


AUTHOR = "<INTERNAL_AGENT_ID>"
MANIFEST_SHA = "b" * 64


def safe_inputs():
    static = {key: True for key in policy.STATIC_FACTS}
    live = {key: True for key in policy.LIVE_FACTS}
    gui_context = {
        "source_file": "synthetic/fixture.json",
        "pid": 12345,
        "name": "ExampleProcess",
        "user_pid_confirmed": False,
        "user_confirmed_context": "synthetic unrelated context without process-specific confirmation",
        "project_association": "UNKNOWN",
        "parent_name": None,
        "window_or_model_contents_read": False,
    }
    review = {
        "decision": "APPROVED",
        "independent_of_candidate_author": True,
        "reviewer_agent_id": "reviewer-example",
        "candidate_manifest_sha256": MANIFEST_SHA,
    }
    return static, live, gui_context, review


class CoexistencePolicyTests(unittest.TestCase):
    def assess(self, static, live, gui_context, review):
        return policy.assess_coexistence(
            static_facts=static,
            live_facts=live,
            review=review,
            manifest_sha256=MANIFEST_SHA,
            author_agent_id=AUTHOR,
            ambient_gui_context=gui_context,
        )

    def test_isolation_path_does_not_require_pid_confirmation_or_resolve_project(self):
        static, live, gui_context, review = safe_inputs()
        original = copy.deepcopy(gui_context)
        result = self.assess(static, live, gui_context, review)
        self.assertTrue(result["coexistence_eligible"])
        self.assertFalse(result["launch_authorized"])
        self.assertEqual(result["ambient_gui_context_preserved"], original)
        self.assertFalse(result["ambient_gui_owner_or_project_resolved"])
        self.assertFalse(result["user_pid_confirmation_inferred"])
        self.assertFalse(result["process_census_or_1021_result_required"])

    def test_missing_independent_batch_or_loadcopy_fact_blocks(self):
        static, live, gui_context, review = safe_inputs()
        static["modelutil_loadcopy_source"] = None
        result = self.assess(static, live, gui_context, review)
        self.assertFalse(result["coexistence_eligible"])
        self.assertIn("static:modelutil_loadcopy_source", result["blockers"])

    def test_source_lock_hash_or_unique_target_conflict_blocks(self):
        static, live, gui_context, review = safe_inputs()
        live["source_lock_free_at_preflight"] = False
        live["fresh_unique_target_and_exclusive_claim"] = None
        result = self.assess(static, live, gui_context, review)
        self.assertIn("live:source_lock_free_at_preflight", result["blockers"])
        self.assertIn("live:fresh_unique_target_and_exclusive_claim", result["blockers"])

    def test_shared_license_resource_or_monitor_gap_blocks(self):
        static, live, gui_context, review = safe_inputs()
        live["fresh_comsol_64_wave_optics_checkout"] = False
        live["ram_and_disk_admission_clear_at_launch"] = False
        live["monitor_confirmed_exact_951_job"] = False
        live["human_monitoring_monitor_liveness_ram_and_disk"] = False
        result = self.assess(static, live, gui_context, review)
        self.assertIn("live:fresh_comsol_64_wave_optics_checkout", result["blockers"])
        self.assertIn("live:ram_and_disk_admission_clear_at_launch", result["blockers"])
        self.assertIn("live:monitor_confirmed_exact_951_job", result["blockers"])
        self.assertIn("live:human_monitoring_monitor_liveness_ram_and_disk", result["blockers"])

    def test_unbound_or_author_review_blocks(self):
        static, live, gui_context, review = safe_inputs()
        review["reviewer_agent_id"] = AUTHOR
        result = self.assess(static, live, gui_context, review)
        self.assertIn("independent_review_missing_or_unbound", result["blockers"])
        review["reviewer_agent_id"] = "reviewer-example"
        review["candidate_manifest_sha256"] = "c" * 64
        result = self.assess(static, live, gui_context, review)
        self.assertIn("independent_review_missing_or_unbound", result["blockers"])

    def test_pid_churn_is_not_used_as_clearance_or_confirmation(self):
        static, live, gui_context, review = safe_inputs()
        gui_context["new_pid_seen"] = 31415
        gui_context["new_pid_user_confirmed"] = False
        result = self.assess(static, live, gui_context, review)
        self.assertTrue(result["coexistence_eligible"])
        self.assertEqual(result["ambient_gui_context_preserved"]["new_pid_seen"], 31415)
        self.assertFalse(result["user_pid_confirmation_inferred"])


if __name__ == "__main__":
    unittest.main()
