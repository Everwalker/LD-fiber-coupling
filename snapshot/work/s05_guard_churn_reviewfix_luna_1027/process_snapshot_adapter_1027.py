"""Preflight bridge retaining 951's clear/fresh snapshot contract."""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
GUARD_DIR = ROOT / "work/s06_multi_user_gui_luna_892"
GUARD_PATH = GUARD_DIR / "process_guard_892.py"
EXPECTED_GUARD_SHA256 = "9128c61f88dd88b35a738179f31b60225610763e9746efa12151822a3d72f03c"
if hashlib.sha256(GUARD_PATH.read_bytes()).hexdigest() != EXPECTED_GUARD_SHA256:
    raise RuntimeError("Frozen 892 process guard SHA-256 mismatch")
for path in (HERE, GUARD_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import process_guard_892 as base_guard  # noqa: E402
import process_guard_churn_1027 as churn_guard  # noqa: E402


SNAPSHOT_ATTEMPTS = 3
MAX_SNAPSHOT_AGE_SECONDS = 900


class SnapshotBlocked(RuntimeError):
    def __init__(self, message: str, attempt_history: list[dict]):
        super().__init__(message)
        self.attempt_history = attempt_history


def collect_clear_snapshot(target_job, collector=churn_guard.collect_snapshot):
    attempt_history = []
    last = {}
    for attempt in range(1, SNAPSHOT_ATTEMPTS + 1):
        try:
            snapshot = collector(str(target_job))
        except Exception as exc:
            attempt_history.append({
                "attempt": attempt,
                "status": "BLOCKED",
                "blockers": ["SNAPSHOT_COLLECTION_FAILED"],
                "enumeration_complete": False,
                "process_churn": [],
                "identity_census": None,
                "collector_error_type": type(exc).__name__,
            })
            raise SnapshotBlocked(
                "process snapshot collection failed; the attempt is retained",
                attempt_history,
            ) from exc
        collected_utc = dt.datetime.now(dt.timezone.utc).isoformat()
        last = snapshot if isinstance(snapshot, dict) else {}
        blockers = set(last.get("blockers", []))
        churn = last.get("process_churn", [])
        attempt_history.append({
            "attempt": attempt,
            "status": last.get("status"),
            "blockers": sorted(blockers),
            "enumeration_complete": last.get("enumeration_complete") is True,
            "process_churn": copy.deepcopy(churn) if isinstance(churn, list) else [],
            "identity_census": copy.deepcopy(last.get("identity_census")),
        })
        if (isinstance(snapshot, dict) and snapshot.get("status") == "CLEAR"
                and snapshot.get("blockers") == []
                and snapshot.get("enumeration_complete") is True):
            result = copy.deepcopy(snapshot)
            result["attempt_history"] = attempt_history
            return result, collected_utc
        benign_churn = all(
            isinstance(event, dict)
            and event.get("classification") == "VERIFIED_UNRELATED_PROCESS_CHURN"
            and isinstance(event.get("identity_sha256"), str)
            for event in churn
        ) if isinstance(churn, list) else False
        retry_allowed = (last.get("status") == "BLOCKED"
                         and blockers == {"PROCESS_ENUMERATION_INCOMPLETE"}
                         and benign_churn)
        if not retry_allowed:
            raise SnapshotBlocked(
                "process identity or conflict gate is blocked; a later retry cannot erase "
                f"that observation: blockers={sorted(blockers)} "
                f"process_churn_count={len(churn) if isinstance(churn, list) else 'invalid'}",
                attempt_history,
            )
    raise SnapshotBlocked(
        "process snapshot did not reach complete CLEAR after "
        f"{SNAPSHOT_ATTEMPTS} attempts: status={last.get('status')} "
        f"blockers={last.get('blockers')}", attempt_history,
    )


def _proven_unrelated_nonworker(record: dict, snapshot: dict) -> bool:
    if record.get("classification") != base_guard.VERIFIED_NON_WORKER:
        return False
    pid, name, created = record.get("pid"), record.get("name"), record.get("created_utc")
    for event in snapshot.get("process_churn", []):
        if not isinstance(event, dict):
            continue
        identity = event.get("identity")
        if (event.get("pid") == pid and event.get("name") == name
                and event.get("created_utc") == created
                and event.get("classification") == "VERIFIED_UNRELATED_PROCESS_CHURN"
                and isinstance(identity, dict)
                and identity.get("pid") == pid and identity.get("name") == name
                and identity.get("created_utc") == created
                and identity.get("classification") == "VERIFIED_UNRELATED_PROCESS_CHURN"
                and event.get("identity_sha256") == base_guard._json_sha(identity)):
            return True
    return False


def _relevant_snapshot(snapshot: dict) -> dict:
    """Validate all records; omit only non-workers with an unrelated-path proof."""
    base_guard.compare_snapshot_identity(snapshot, snapshot)
    relevant = copy.deepcopy(snapshot)
    relevant["process_identity_records"] = [
        record for record in snapshot["process_identity_records"]
        if not _proven_unrelated_nonworker(record, snapshot)
    ]
    relevant["process_count"] = len(relevant["process_identity_records"])
    relevant["identity_set_sha256"] = base_guard._json_sha(
        relevant["process_identity_records"]
    )
    return relevant


def compare_snapshot_identity_allowing_unrelated_churn(before: dict, after: dict) -> None:
    """Keep GUI/worker identities exact; permit verified non-worker set changes."""
    base_guard.compare_snapshot_identity(
        _relevant_snapshot(before), _relevant_snapshot(after)
    )


def _parse_utc(value) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise RuntimeError("process snapshot timestamp has no timezone")
    return parsed.astimezone(dt.timezone.utc)


def validate_snapshot_pair(target, source, target_collected_utc, source_collected_utc, now):
    compare_snapshot_identity_allowing_unrelated_churn(target, source)
    checked_at = now or dt.datetime.now(dt.timezone.utc)
    if checked_at.tzinfo is None:
        raise RuntimeError("snapshot check time has no timezone")
    checked_at = checked_at.astimezone(dt.timezone.utc)
    for label, collected in (("target", target_collected_utc),
                             ("source", source_collected_utc)):
        age = (checked_at - _parse_utc(collected)).total_seconds()
        if not 0 <= age <= MAX_SNAPSHOT_AGE_SECONDS:
            raise RuntimeError(f"{label} process snapshot is stale or from the future")
    return checked_at
