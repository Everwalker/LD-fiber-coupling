"""S05 process snapshot adapter: reconcile unrelated churn by process identity.

The classifier and identity rules are reused from process_guard_892.py. This
collector changes only its all-PID stability rule: every PID still live at the
end must be enumerated or individually identified; newly observed processes
must also be proven unrelated before they can be ignored.
"""
from __future__ import annotations

import os
import hashlib
from pathlib import Path
import sys
import time

import psutil


ROOT = Path(__file__).resolve().parents[2]
GUARD_DIR = ROOT / "work/s06_multi_user_gui_luna_892"
GUARD_PATH = GUARD_DIR / "process_guard_892.py"
EXPECTED_GUARD_SHA256 = "9128c61f88dd88b35a738179f31b60225610763e9746efa12151822a3d72f03c"
guard_digest = hashlib.sha256(GUARD_PATH.read_bytes()).hexdigest()
if guard_digest != EXPECTED_GUARD_SHA256:
    raise RuntimeError("Frozen 892 process guard SHA-256 mismatch")
if str(GUARD_DIR) not in sys.path:
    sys.path.insert(0, str(GUARD_DIR))
import process_guard_892 as base_guard  # noqa: E402


def _incomplete_row(pid: int, created_utc: str | None = None, name: str | None = None) -> dict:
    return {
        "pid": pid,
        "name": name,
        "created_utc": created_utc,
        "identity_readable": {
            "pid": True,
            "name": isinstance(name, str) and bool(name),
            "creation_time": created_utc is not None,
        },
    }


def _read_identity_row(pid: int, visible_pids: set[int]) -> tuple[dict, bool]:
    """Read one live PID without returning raw paths or command lines."""
    row = _incomplete_row(pid)
    flags = {field: False for field in base_guard.READABLE_FIELDS}
    flags["pid"] = True
    created_before = None
    name = None
    try:
        proc = psutil.Process(pid)
        with proc.oneshot():
            created_before = float(proc.create_time())
            try:
                name = proc.name()
            except (psutil.Error, OSError):
                name = None
            try:
                parent_pid = int(proc.ppid())
            except (psutil.Error, OSError, TypeError, ValueError):
                parent_pid = None
            try:
                executable = proc.exe()
                executable_sha256 = base_guard._hash_file(executable)
                flags["executable_path"] = bool(executable)
            except (psutil.Error, OSError, TypeError, ValueError):
                executable = None
                executable_sha256 = None
            try:
                command_line = proc.cmdline()
                flags["command_line"] = bool(command_line)
            except (psutil.Error, OSError):
                command_line = None
            try:
                cwd = proc.cwd()
                flags["cwd"] = bool(cwd)
            except (psutil.Error, OSError):
                cwd = None
        # A fresh Process object avoids reusing a cached create_time if Windows
        # recycled this PID while the rest of its identity was being read.
        created_after = float(psutil.Process(pid).create_time())
        if created_after != created_before:
            raise RuntimeError("PID identity changed during read")
    except (psutil.Error, OSError, TypeError, ValueError, RuntimeError):
        if created_before is not None:
            row = _incomplete_row(pid, base_guard._utc(created_before), name)
        return row, False

    created_utc = base_guard._utc(created_before)
    flags["creation_time"] = True
    flags["name"] = isinstance(name, str) and bool(name)
    if not flags["name"]:
        try:
            cim = base_guard._query_process_name_cim(pid)
            pdh = base_guard._query_process_identity_get_counter(pid)
            verification = base_guard._build_name_fallback(
                {"pid": pid, "created_utc": created_utc,
                 "identity_readable": {"pid": True, "creation_time": True}},
                cim, pdh,
            )
        except Exception:
            verification = None
        if isinstance(verification, dict):
            name = verification["name"]
            flags["name"] = True
        else:
            verification = None
    else:
        verification = None

    row.update({
        "name": name,
        "created_utc": created_utc,
        "parent_pid": parent_pid,
        "executable_path": executable,
        "executable_sha256": executable_sha256,
        "command_line_args": command_line,
        "cwd": cwd,
        "identity_readable": flags,
    })
    if verification is not None:
        row["name_source"] = base_guard.FALLBACK_NAME_SOURCE
        row["name_verification"] = verification
    try:
        chain, chain_ok = base_guard._parent_chain(parent_pid, created_before)
    except (psutil.Error, OSError, TypeError, ValueError):
        chain, chain_ok = [], False
    row["parent_chain"] = chain
    row["parent_chain_complete"] = chain_ok
    flags["parent_chain"] = chain_ok
    if isinstance(name, str) and base_guard.COMSOL_RE.search(name):
        row["main_window_visible"] = pid in visible_pids
        try:
            row["file_version"] = base_guard._file_version(executable)
        except (OSError, TypeError, ValueError):
            row["file_version"] = None
            flags["executable_path"] = False
    return row, base_guard._complete_identity(row)


def classify_churn_process(row: dict, target_path: str, resolve_path=None) -> dict:
    """Classify a process observed during the scan; unknown is always blocking."""
    pid = row.get("pid") if isinstance(row, dict) else None
    name = row.get("name") if isinstance(row, dict) else None
    created = row.get("created_utc") if isinstance(row, dict) else None
    if not isinstance(row, dict) or not base_guard._complete_identity(row):
        return {
            "allowed": False,
            "blocker": "PROCESS_IDENTITY_UNREADABLE",
            "record": {"pid": pid, "name": name, "created_utc": created,
                       "classification": "UNKNOWN_IDENTITY_BLOCKED"},
        }
    if base_guard.COMSOL_RE.search(name) or base_guard.WORKER_RE.fullmatch(name):
        return {
            "allowed": False,
            "blocker": "NEW_COMSOL_OR_WORKER_DURING_SCAN",
            "record": {"pid": pid, "name": name.casefold(), "created_utc": created,
                       "classification": "NEW_COMSOL_OR_WORKER_BLOCKED"},
        }
    if any(base_guard.COMSOL_RE.search(str(parent.get("name") or ""))
           or base_guard.WORKER_RE.fullmatch(str(parent.get("name") or ""))
           for parent in row["parent_chain"]):
        return {
            "allowed": False,
            "blocker": "NEW_PROCESS_PARENT_OWNERSHIP_UNKNOWN",
            "record": {"pid": pid, "name": name.casefold(), "created_utc": created,
                       "classification": "WORKER_OR_COMSOL_PARENT_BLOCKED"},
        }
    resolver = resolve_path or base_guard.resolve_windows_path
    try:
        target_id = resolver(target_path, None)
        relation, executable_id, cwd_id, _error = base_guard._path_facts(
            row, target_path, target_id, resolver,
        )
    except Exception:
        relation, executable_id, cwd_id = "UNKNOWN", "", ""
    if relation != "UNRELATED":
        return {
            "allowed": False,
            "blocker": "NEW_PROCESS_PATH_NOT_PROVEN_UNRELATED",
            "record": {"pid": pid, "name": name.casefold(), "created_utc": created,
                       "classification": "PATH_RELATION_" + relation + "_BLOCKED"},
        }
    identity = base_guard._identity_payload(
        row, executable_id, cwd_id, row["command_line_args"],
        "VERIFIED_UNRELATED_PROCESS_CHURN",
    )
    return {
        "allowed": True,
        "blocker": None,
        "record": {"pid": pid, "name": name.casefold(), "created_utc": created,
                   "classification": "VERIFIED_UNRELATED_PROCESS_CHURN",
                   "identity": identity,
                   "identity_sha256": base_guard._json_sha(identity)},
    }


def _same_creation_epoch(left, right) -> bool:
    return (isinstance(left, (int, float)) and not isinstance(left, bool)
            and isinstance(right, (int, float)) and not isinstance(right, bool)
            and abs(float(left) - float(right)) <= 0.000001)


def _identity_key(pid: int, created) -> tuple[int, float]:
    return pid, round(float(created), 6)


def _row_matches_creation(row: dict, expected) -> bool:
    return _same_creation_epoch(base_guard._created_epoch(row.get("created_utc")), expected)


def _creation_map(pids: set[int]) -> dict[int, float | None]:
    identities = {}
    for pid in pids:
        try:
            created = float(psutil.Process(pid).create_time())
        except (psutil.Error, OSError, TypeError, ValueError):
            created = None
        identities[pid] = created
    return identities


def identity_change_events(pids_before, creation_before, creation_seen,
                           pids_after, creation_after, scan_started):
    """Return every new/reused identity and any unresolvable PID observation."""
    stages = (
        ("before", pids_before, creation_before),
        ("seen", set(creation_seen), creation_seen),
        ("after", pids_after, creation_after),
    )
    events = {}
    blockers = set()
    for stage, pids, identities in stages:
        if not isinstance(pids, (set, frozenset)) or not isinstance(identities, dict):
            return [], ["PROCESS_IDENTITY_UNREADABLE"]
        for pid in pids:
            if type(pid) is not int or pid <= 0:
                blockers.add("PROCESS_IDENTITY_UNREADABLE")
                continue
            created = identities.get(pid)
            if not isinstance(created, (int, float)) or isinstance(created, bool):
                blockers.add("PROCESS_IDENTITY_UNREADABLE")
                key = (pid, None)
                events.setdefault(key, {"pid": pid, "created_epoch": None,
                                        "observed_stages": set()})["observed_stages"].add(stage)
                continue
            before = creation_before.get(pid) if pid in pids_before else None
            is_new = (pid not in pids_before or not _same_creation_epoch(created, before)
                      or float(created) >= float(scan_started))
            if is_new:
                key = _identity_key(pid, created)
                events.setdefault(key, {"pid": pid, "created_epoch": float(created),
                                        "observed_stages": set()})["observed_stages"].add(stage)
    ordered = []
    for event in events.values():
        event["observed_stages"] = sorted(event["observed_stages"])
        event["created_utc"] = (base_guard._utc(event["created_epoch"])
                                if event["created_epoch"] is not None else None)
        ordered.append(event)
    ordered.sort(key=lambda event: (event["pid"], event["created_epoch"] or -1))
    return ordered, sorted(blockers)


def census_complete_after_reconciliation(pids_after, creation_seen,
                                         creation_after, reconciled_creation) -> bool:
    """Require the live after identity to match an observed or full-read identity."""
    if (not isinstance(pids_after, (set, frozenset))
            or not all(isinstance(items, dict)
                       for items in (creation_seen, creation_after, reconciled_creation))):
        return False
    for pid in pids_after:
        if type(pid) is not int or pid <= 0:
            return False
        created = creation_after.get(pid)
        if not isinstance(created, (int, float)) or isinstance(created, bool):
            return False
        if (_same_creation_epoch(creation_seen.get(pid), created)
                or _same_creation_epoch(reconciled_creation.get(pid), created)):
            continue
        return False
    return True


def classify_identity_event(event: dict, row: dict | None, target_path: str,
                            resolve_path=None) -> dict:
    """Classify and retain one observed identity, including already-exited PIDs."""
    pid = event.get("pid")
    created = event.get("created_utc")
    name = row.get("name") if isinstance(row, dict) else None
    worker_or_comsol = (isinstance(name, str)
                        and (base_guard.COMSOL_RE.search(name)
                             or base_guard.WORKER_RE.fullmatch(name)))
    if (event.get("created_epoch") is None or not isinstance(row, dict)
            or not base_guard._complete_identity(row)
            or row.get("pid") != pid
            or not _row_matches_creation(row, event.get("created_epoch"))):
        blocker = ("NEW_COMSOL_OR_WORKER_DURING_SCAN" if worker_or_comsol
                   else "PROCESS_IDENTITY_UNREADABLE")
        classification = ("NEW_COMSOL_OR_WORKER_BLOCKED" if worker_or_comsol
                          else "UNKNOWN_IDENTITY_BLOCKED")
        return {"allowed": False, "blocker": blocker,
                "record": {"pid": pid, "name": str(name or "").casefold() or None,
                           "created_utc": created, "classification": classification}}
    return classify_churn_process(row, target_path, resolve_path)


def collect_snapshot(target_job: str) -> dict:
    """Take a fresh inventory; reconcile live additions by identity, not PID count."""
    if os.name != "nt":
        return {"status": "BLOCKED", "blockers": ["WINDOWS_ONLY"],
                "enumeration_complete": False, "process_count": 0,
                "process_identity_records": [], "process_churn": [],
                "workers": [], "gui_identities": [], "identity_set_sha256": None,
                "target_job_path_identity_sha256": None}
    scan_started = None
    pids_before: set[int] = set()
    pids_after: set[int] = set()
    seen_pids: set[int] = set()
    rows_by_identity: dict[tuple[int, float], dict] = {}
    churn_records: list[dict] = []
    enumeration_errors = 0
    try:
        if hasattr(psutil.process_iter, "cache_clear"):
            psutil.process_iter.cache_clear()
        scan_started = time.time()
        pids_before = set(psutil.pids()) - {0}
        creation_before = _creation_map(pids_before)
        visible_pids = base_guard._visible_window_pids()
        seen_pids = set()
        creation_seen: dict[int, float | None] = {}
        rows_by_identity = {}
        for proc in psutil.process_iter(["pid", "name", "ppid", "create_time"]):
            try:
                info = proc.info
                pid = int(info["pid"])
                if pid == 0:
                    continue
                seen_pids.add(pid)
                created_value = info.get("create_time")
                try:
                    created = float(created_value)
                except (TypeError, ValueError):
                    created = None
                creation_seen[pid] = created
                if pid == os.getpid():
                    continue
                name = info.get("name")
                is_new = (created is None or pid not in pids_before
                          or not _same_creation_epoch(created, creation_before.get(pid))
                          or created >= scan_started)
                relevant = (not isinstance(name, str) or not name
                            or base_guard.COMSOL_RE.search(name)
                            or base_guard.WORKER_RE.fullmatch(name))
                if is_new or relevant:
                    row, _complete = _read_identity_row(pid, visible_pids)
                    row_created = base_guard._created_epoch(row.get("created_utc"))
                    if (created is not None and _row_matches_creation(row, created)):
                        rows_by_identity[_identity_key(pid, created)] = row
                    else:
                        # Keep the process_iter observation even if the PID vanished
                        # or was reused before its full identity could be read.
                        stub = _incomplete_row(
                            pid, base_guard._utc(created) if created is not None else None,
                            name if isinstance(name, str) else None,
                        )
                        rows_by_identity[(pid, round(created, 6) if created is not None else -1.0)] = stub
                        if row_created is not None:
                            rows_by_identity[_identity_key(pid, row_created)] = row
            except (psutil.Error, OSError, TypeError, ValueError):
                enumeration_errors += 1
                try:
                    pid = int(proc.pid)
                    if pid > 0:
                        seen_pids.add(pid)
                        creation_seen[pid] = None
                except (psutil.Error, OSError, TypeError, ValueError):
                    pass

        pids_after = set(psutil.pids()) - {0}
        creation_after = _creation_map(pids_after)
        events, identity_blockers = identity_change_events(
            pids_before, creation_before, creation_seen,
            pids_after, creation_after, scan_started,
        )
        reconciled_creation: dict[int, float] = {}
        churn_blockers = list(identity_blockers)

        for pid in sorted(pids_after):
            created = creation_after.get(pid)
            if not isinstance(created, (int, float)):
                continue
            if _same_creation_epoch(creation_seen.get(pid), created):
                continue
            row, complete = _read_identity_row(pid, visible_pids)
            row_created = base_guard._created_epoch(row.get("created_utc"))
            if complete and _row_matches_creation(row, created):
                rows_by_identity[_identity_key(pid, created)] = row
                reconciled_creation[pid] = created
            else:
                rows_by_identity[_identity_key(pid, created)] = _incomplete_row(
                    pid, base_guard._utc(created), row.get("name")
                )
                churn_blockers.append("PROCESS_IDENTITY_UNREADABLE")

        # A fresh identity read can catch PID reuse between process_iter and
        # the read itself. Retain that identity even if it exits before census.
        event_map = {(event["pid"], round(event["created_epoch"], 6)
                      if event["created_epoch"] is not None else -1.0): event
                     for event in events}
        for (pid, created), row in rows_by_identity.items():
            if (created >= 0 and (pid not in pids_before
                    or not _same_creation_epoch(created, creation_before.get(pid))
                    or created >= scan_started)):
                event_map.setdefault((pid, round(created, 6)), {
                    "pid": pid, "created_epoch": created,
                    "created_utc": row.get("created_utc"),
                    "observed_stages": ["identity_read"],
                })
        events = sorted(event_map.values(),
                        key=lambda event: (event["pid"], event["created_epoch"] or -1))

        event_keys = set()
        for event in events:
            pid, created = event["pid"], event["created_epoch"]
            if created is None:
                row = rows_by_identity.get((pid, -1.0))
            else:
                key = _identity_key(pid, created)
                row = rows_by_identity.get(key)
                if row is None:
                    row, complete = _read_identity_row(pid, visible_pids)
                    row_created = base_guard._created_epoch(row.get("created_utc"))
                    if complete and _row_matches_creation(row, created):
                        rows_by_identity[key] = row
                    else:
                        row = _incomplete_row(
                            pid, event.get("created_utc"), row.get("name")
                        )
                        rows_by_identity[key] = row
            decision = classify_identity_event(event, row, target_job)
            record = dict(decision["record"])
            record["observed_stages"] = event["observed_stages"]
            record["live_after"] = (created is not None and pid in pids_after
                                     and _same_creation_epoch(creation_after.get(pid), created))
            churn_records.append(record)
            event_keys.add(_identity_key(pid, created) if created is not None else (pid, -1.0))
            if not decision["allowed"]:
                churn_blockers.append(decision["blocker"])

        # A COMSOL/worker seen during enumeration must remain in evidence when
        # it exits or its PID is reused before the ending census.
        for (pid, created), row in rows_by_identity.items():
            name = str(row.get("name") or "")
            if not (base_guard.COMSOL_RE.search(name)
                    or base_guard.WORKER_RE.fullmatch(name)):
                continue
            still_same = (pid in pids_after
                          and _same_creation_epoch(creation_after.get(pid), created))
            if still_same or _identity_key(pid, created) in event_keys:
                continue
            churn_records.append({
                "pid": pid, "name": name.casefold(),
                "created_utc": row.get("created_utc"),
                "classification": "OBSERVED_COMSOL_OR_WORKER_EXITED_DURING_SCAN",
                "observed_stages": ["seen"], "live_after": False,
            })
            churn_blockers.append("PROCESS_IDENTITY_CHANGED_DURING_SCAN")

        active_rows = [
            row for (pid, created), row in rows_by_identity.items()
            if pid in pids_after and created >= 0
            and _same_creation_epoch(creation_after.get(pid), created)
        ]
        inventory_complete = census_complete_after_reconciliation(
            pids_after, creation_seen, creation_after, reconciled_creation
        )
        if enumeration_errors:
            inventory_complete = False
            churn_blockers.append("PROCESS_ENUMERATION_INCOMPLETE")
        classified = base_guard.classify_snapshot(
            {"enumeration_complete": inventory_complete, "processes": active_rows}, target_job,
        )
        blockers = sorted(set(classified["blockers"] + churn_blockers))
        status = "BLOCKED" if blockers else "CLEAR"
        collector_exclusion = base_guard._collector_exclusion()
        return {
            "status": status,
            "blockers": blockers,
            "enumeration_complete": inventory_complete,
            "process_count": len(classified["process_identity_records"]),
            "gui_identity": classified["gui_identity"],
            "gui_identities": classified["gui_identities"],
            "workers": classified["workers"],
            "process_identity_records": classified["process_identity_records"],
            "identity_set_sha256": classified["identity_set_sha256"],
            "collector_exclusion": collector_exclusion,
            "target_job_path_identity_sha256": classified["target_job_path_identity_sha256"],
            "process_churn": churn_records,
            "identity_census": {
                "before_count": len(pids_before), "seen_count": len(seen_pids),
                "after_count": len(pids_after),
                "identity_events": len(events),
                "reconciled_after_count": len(reconciled_creation),
                "enumeration_errors": enumeration_errors,
            },
        }
    except Exception:
        retained = list(churn_records)
        retained_keys = {(event.get("pid"), event.get("created_utc"))
                         for event in retained if isinstance(event, dict)}
        for (pid, _created), row in rows_by_identity.items():
            created_utc = row.get("created_utc")
            if (pid, created_utc) in retained_keys:
                continue
            name = row.get("name")
            retained.append({
                "pid": pid, "name": str(name or "").casefold() or None,
                "created_utc": created_utc,
                "classification": "SCAN_ABORTED_OBSERVATION_RETAINED",
                "observed_stages": ["seen"], "live_after": None,
            })
        blockers = ["SNAPSHOT_COLLECTION_FAILED", "PROCESS_ENUMERATION_INCOMPLETE"]
        if retained:
            blockers.append("PROCESS_IDENTITY_UNREADABLE")
        return {"status": "BLOCKED", "blockers": sorted(set(blockers)),
                "enumeration_complete": False, "process_count": 0,
                "process_identity_records": [],
                "workers": [], "gui_identities": [], "identity_set_sha256": None,
                "target_job_path_identity_sha256": None,
                "process_churn": retained,
                "identity_census": {
                    "before_count": len(pids_before), "seen_count": len(seen_pids),
                    "after_count": len(pids_after), "identity_events": len(retained),
                    "reconciled_after_count": 0,
                    "enumeration_errors": enumeration_errors,
                }}
