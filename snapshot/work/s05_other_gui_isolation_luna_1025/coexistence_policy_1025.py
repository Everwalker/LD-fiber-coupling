"""Pure-data policy prototype for an independently isolated COMSOL batch job.

This module performs no process, window, file, COMSOL, or network I/O. It is
not connected to the frozen 951 launcher and never authorizes a launch itself.
"""

from __future__ import annotations

from copy import deepcopy
import re


STATIC_FACTS = (
    "separate_comsolbatch_process",
    "no_gui_or_comsol_server_attach_call",
    "modelutil_loadcopy_source",
    "java_writes_only_job_output",
    "job_scoped_comsol_state_directories",
    "source_lock_and_hash_contract",
    "unique_job_output_and_exclusive_no_retry_claim",
    "ram_disk_admission_contract",
    "independently_reviewed_monitor_source_available",
)

LIVE_FACTS = (
    "fresh_comsol_64_wave_optics_checkout",
    "source_lock_free_at_preflight",
    "source_hash_matches_before_launch",
    "fresh_unique_target_and_exclusive_claim",
    "ram_and_disk_admission_clear_at_launch",
    "monitor_991_armed_before_launch",
    "monitor_confirmed_exact_951_job",
    "human_monitoring_monitor_liveness_ram_and_disk",
)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z", re.IGNORECASE)


def _check_facts(facts: dict, required: tuple[str, ...], prefix: str, blockers: list[str]) -> None:
    if not isinstance(facts, dict):
        blockers.append(f"{prefix}:record_missing")
        return
    for key in required:
        if facts.get(key) is not True:
            blockers.append(f"{prefix}:{key}")


def _review_valid(review: dict, manifest_sha256: str, author_agent_id: str) -> bool:
    return (
        isinstance(review, dict)
        and review.get("decision") == "APPROVED"
        and review.get("independent_of_candidate_author") is True
        and isinstance(review.get("reviewer_agent_id"), str)
        and bool(review["reviewer_agent_id"])
        and review["reviewer_agent_id"] != author_agent_id
        and review.get("candidate_manifest_sha256") == manifest_sha256
        and isinstance(manifest_sha256, str)
        and bool(_SHA256.fullmatch(manifest_sha256))
    )


def assess_coexistence(
    *,
    static_facts: dict,
    live_facts: dict,
    review: dict,
    manifest_sha256: str,
    author_agent_id: str,
    ambient_gui_context: dict | None = None,
) -> dict:
    """Assess the 951 job's own isolation gates without enumerating other PIDs.

    `ambient_gui_context` is opaque provenance carried through unchanged. Its
    PID, user ownership, project association, and contents do not affect this
    decision. A future launcher must still enforce the factual gates here and
    bind the one 951 child by job ID, PID, creation time, and command.
    """
    blockers: list[str] = []
    _check_facts(static_facts, STATIC_FACTS, "static", blockers)
    _check_facts(live_facts, LIVE_FACTS, "live", blockers)
    if not _review_valid(review, manifest_sha256, author_agent_id):
        blockers.append("independent_review_missing_or_unbound")

    blockers = sorted(set(blockers))
    eligible = not blockers
    return {
        "status": "ELIGIBLE_FOR_REVIEWED_ISOLATED_BATCH_COEXISTENCE" if eligible else "BLOCKED",
        "coexistence_eligible": eligible,
        "launch_authorized": False,
        "scope": "951 candidate-specific batch and shared-resource gates only",
        "ambient_gui_context_preserved": deepcopy(ambient_gui_context),
        "ambient_gui_owner_or_project_resolved": False,
        "user_pid_confirmation_inferred": False,
        "other_gui_or_model_contents_read_by_policy": False,
        "process_census_or_1021_result_required": False,
        "blockers": blockers,
    }
