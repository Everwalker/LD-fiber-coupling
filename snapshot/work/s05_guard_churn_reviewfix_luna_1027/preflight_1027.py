"""Emit candidate-only checks; never create or impersonate 951 preflight evidence."""
import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE_CANDIDATE = ROOT / "work/s05_air_sweep_property_fix_luna_951"
OUT = HERE / ("preflight_1027_" +
              dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
GIB = 1024 ** 3


class GateFailure(RuntimeError):
    def __init__(self, blocker: str, message: str):
        super().__init__(message)
        self.blocker = blocker


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rooted_path(relative: str, base: Path = ROOT) -> Path:
    path = (base / relative).resolve()
    if path != base.resolve() and base.resolve() not in path.parents:
        raise GateFailure("PATH_OUTSIDE_PACKAGE", "A frozen path escaped the package root")
    return path


def require(condition: bool, blocker: str, message: str) -> None:
    if not condition:
        raise GateFailure(blocker, message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--license-evidence-dir", required=True)
    license_dir = Path(parser.parse_args().license_evidence_dir).resolve()
    record = {
        "observed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "CANDIDATE_ONLY_NOT_951_PREFLIGHT",
        "candidate_gate_status": "BLOCKED",
        "candidate_id": "S05_GUARD_CHURN_REVIEWFIX_LUNA_1027",
        "launch_authorized": False,
        "accepted_by_frozen_951_launcher": False,
        "output_path": OUT.relative_to(ROOT).as_posix(),
        "candidate_manifest_sha256": None,
        "candidate_files_checked": {},
        "source_binding_hashes_checked": {},
        "snapshot_attempt_history": {},
        "blockers": [],
    }
    try:
        manifest_path = HERE / "manifest.json"
        manifest_sha = sha(manifest_path)
        record["candidate_manifest_sha256"] = manifest_sha
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        sidecar = (HERE / "manifest.sha256").read_text(encoding="ascii").strip().lower()
        require(sidecar == manifest_sha, "CANDIDATE_MANIFEST_HASH_MISMATCH",
                "Candidate manifest sidecar mismatch")
        require(manifest.get("candidate_id") == record["candidate_id"],
                "CANDIDATE_ID_MISMATCH", "Candidate identity differs from this preflight")

        candidate_ok = True
        for entry in manifest.get("candidate_files", []):
            path = (HERE / entry["path"]).resolve()
            valid_path = HERE.resolve() in path.parents and path.is_file()
            actual = sha(path) if valid_path else None
            size = path.stat().st_size if valid_path else None
            match = valid_path and actual == entry["sha256"] and size == entry["bytes"]
            record["candidate_files_checked"][entry["path"]] = {
                "bytes": size, "sha256": actual, "matches": bool(match),
            }
            candidate_ok = candidate_ok and bool(match)
        require(candidate_ok and bool(manifest.get("candidate_files")),
                "CANDIDATE_FILE_HASH_MISMATCH", "Candidate file freeze mismatch")
        record.update({
            "candidate_preflight_script_sha256": sha(Path(__file__).resolve()),
            "snapshot_adapter_sha256": sha(HERE / "process_snapshot_adapter_1027.py"),
            "process_guard_adapter_sha256": sha(HERE / "process_guard_churn_1027.py"),
        })

        source_ok = True
        for name, entry in manifest.get("source_bindings", {}).items():
            path = rooted_path(entry["path"])
            actual = sha(path) if path.is_file() else None
            match = actual == entry["sha256"]
            record["source_binding_hashes_checked"][name] = {
                "path": entry["path"], "role": entry["role"],
                "expected_sha256": entry["sha256"], "actual_sha256": actual,
                "matches": match,
            }
            source_ok = source_ok and match
        require(source_ok and bool(manifest.get("source_bindings")),
                "SOURCE_BINDING_HASH_MISMATCH",
                "A frozen source binding is missing or has changed")

        # All code and evidence dependencies are hash-checked before importing
        # the adapter, which imports process_guard_892.py.
        review_path = HERE / "review_1027.json"
        require(review_path.is_file(), "INDEPENDENT_REVIEW_REQUIRED",
                "A non-author review of this exact manifest is required")
        review = json.loads(review_path.read_text(encoding="utf-8"))
        candidate_review = review.get("candidate", {})
        reviewer_id = (review.get("reviewer_agent_id")
                       or review.get("reviewer_scheduler_handle")
                       or review.get("reviewer", {}).get("agent_id"))
        independent = (review.get("independent_of_candidate_author") is True
                       or candidate_review.get("independent_of_author") is True)
        review_manifest_sha = (review.get("binding", {}).get("candidate_manifest_sha256")
                               or candidate_review.get("manifest_sha256"))
        require(review.get("decision") == "APPROVED"
                and independent and review_manifest_sha == manifest_sha
                and reviewer_id
                and reviewer_id != manifest.get("execution", {}).get("agent_id"),
                "INDEPENDENT_REVIEW_REQUIRED", "Review is absent or not bound to this freeze")

        import psutil
        import sys
        sys.path.insert(0, str(HERE))
        import process_snapshot_adapter_1027 as helper  # noqa: E402

        source_manifest = rooted_path(manifest["source_model"]["manifest_path"])
        source_manifest_sha = sha(source_manifest)
        source_doc = json.loads(source_manifest.read_text(encoding="utf-8"))
        source_sidecar = (source_manifest.parent / "manifest.sha256").read_text(
            encoding="ascii").strip().lower()
        require(source_sidecar == source_manifest_sha,
                "951_MANIFEST_HASH_MISMATCH", "Frozen 951 manifest sidecar mismatch")
        require(source_doc.get("candidate_id") == "S05_AIR_SWEEP_PROPERTY_FIX_LUNA_951",
                "951_MANIFEST_ID_MISMATCH", "Source candidate identity differs from 951")

        source_review_path = rooted_path(manifest["source_model"]["source_review_path"])
        source_review = json.loads(source_review_path.read_text(encoding="utf-8"))
        require(source_review.get("decision") == "APPROVED"
                and source_review.get("independent_of_candidate_author") is True
                and source_review.get("binding", {}).get("candidate_manifest_sha256")
                == source_manifest_sha,
                "951_REVIEW_INVALID", "The pinned source candidate review is not valid")
        provenance = source_doc["provenance"]
        require(sha(ROOT / "CHANGELOG.md") == provenance["root_changelog_sha256"],
                "CHANGELOG_HASH_MISMATCH", "Root CHANGELOG changed after 951 freeze")
        require(sha(ROOT / "docs/adr/ADR-096-s05-property-error-correction.md")
                == provenance["adr_096_sha256"],
                "ADR_HASH_MISMATCH", "ADR-096 changed after 951 freeze")

        model_path = rooted_path(manifest["source_model"]["path"])
        model_sha = sha(model_path)
        require(model_sha == manifest["source_model"]["sha256"]
                and model_sha == source_doc["source_model"]["sha256"],
                "SOURCE_MODEL_HASH_MISMATCH", "Pinned 390a model hash differs")

        target_claim = BASE_CANDIDATE / "attempt_claim_951.json"
        source_locks = sorted(str(path.relative_to(ROOT).as_posix())
                              for path in model_path.parent.glob("*.lock") if path.is_file())
        target_locks = sorted(str(path.relative_to(ROOT).as_posix())
                              for path in BASE_CANDIDATE.rglob("*.lock") if path.is_file())
        record["source_lock_paths"] = source_locks
        record["target_lock_paths"] = target_locks
        record["attempt_claim_951_absent"] = not target_claim.exists()
        require(not source_locks and not target_locks and not target_claim.exists(),
                "SOURCE_OR_TARGET_LOCK_PRESENT", "A source/target lock or 951 claim blocks use")

        require(license_dir == ROOT or ROOT in license_dir.parents,
                "LICENSE_EVIDENCE_PATH_INVALID", "License evidence must be inside this package")
        license_job = json.loads((license_dir / "job.json").read_text(encoding="utf-8"))
        finished = dt.datetime.fromisoformat(license_job["finished_utc"])
        age = (dt.datetime.now(dt.timezone.utc) - finished).total_seconds()
        require(str(license_job.get("job_id", "")).startswith("job_license_")
                and license_job.get("kind") == "batch"
                and license_job.get("status") == "PROCESS_FINISHED_NEEDS_LOG_AND_ARTIFACT_REVIEW"
                and license_job.get("returncode") == 0 and 0 <= age <= 900,
                "LICENSE_EVIDENCE_INVALID", "A fresh completed license probe is required")
        stdout = (license_dir / "stdout.log").read_bytes()
        log = (license_dir / "comsol.log").read_bytes()
        for marker in (b"LD_S00_WAVEOPTICS_HAS_PRODUCT=true",
                       b"LD_S00_WAVEOPTICS_CHECKOUT=true"):
            require(marker in stdout, "WAVE_OPTICS_LICENSE_UNVERIFIED",
                    "Wave Optics product/checkout marker is missing")
        smoke_sha = "a36d336e8e04814027c9cb68e1e6a309bacf4293737e36286eb77a793c4660e3"
        require(license_job.get("source_sha256") == smoke_sha
                and sha(license_dir / "SmokeJava001.class") == smoke_sha,
                "LICENSE_PROBE_HASH_MISMATCH", "License probe input class differs")
        build_match = re.search(rb"COMSOL\s+(6\.4(?:\.\d+){1,2})", stdout + log)
        require(build_match is not None and build_match.group(1) in stdout
                and build_match.group(1) in log,
                "COMSOL_64_BUILD_UNVERIFIED", "Actual COMSOL 6.4 build marker is missing")

        target, target_time = helper.collect_clear_snapshot(BASE_CANDIDATE)
        record["snapshot_attempt_history"]["target"] = target["attempt_history"]
        source, source_time = helper.collect_clear_snapshot(model_path.parent)
        record["snapshot_attempt_history"]["source"] = source["attempt_history"]
        checked_at = helper.validate_snapshot_pair(target, source, target_time, source_time, None)

        memory = psutil.virtual_memory()
        disk_free = shutil.disk_usage(ROOT).free
        require(memory.available >= 16 * GIB and memory.total * 0.7 >= 16 * GIB
                and disk_free >= 6 * GIB,
                "RESOURCE_GATE_BLOCKED", "Current RAM or disk is below the frozen plan")
        record.update({
            "candidate_review_sha256": sha(review_path),
            "candidate_preflight_script_sha256": sha(Path(__file__).resolve()),
            "snapshot_adapter_sha256": sha(HERE / "process_snapshot_adapter_1027.py"),
            "process_guard_adapter_sha256": sha(HERE / "process_guard_churn_1027.py"),
            "source_951_manifest_sha256": source_manifest_sha,
            "source_951_review_sha256": sha(source_review_path),
            "source_model_sha256": model_sha,
            "comsol_build": build_match.group(1).decode("ascii"),
            "wave_optics_available": True,
            "license_job": license_job["job_id"],
            "license_artifact_sha256": {
                name: sha(license_dir / name)
                for name in ("job.json", "stdout.log", "comsol.log", "SmokeJava001.class")
            },
            "target_snapshot": target,
            "source_snapshot": source,
            "snapshots_checked_utc": checked_at.isoformat(),
            "ram_total_bytes": memory.total,
            "ram_available_bytes": memory.available,
            "disk_free_bytes": disk_free,
            "planned_memory_bytes": 16 * GIB,
            "checkpoint_estimate_bytes": 2 * GIB,
            "estimate_basis": "Frozen 951 estimate; planning values, not measured job limits.",
        })
    except Exception as exc:
        history = getattr(exc, "attempt_history", None)
        if history is not None:
            record["snapshot_attempt_history"]["blocked"] = history
            record["blockers"].append("PROCESS_SNAPSHOT_BLOCKED")
        elif isinstance(exc, GateFailure):
            record["blockers"].append(exc.blocker)
            record["failure_type"] = type(exc).__name__
        else:
            record["blockers"].append("PREFLIGHT_EXECUTION_ERROR")
            record["failure_type"] = type(exc).__name__
    finally:
        record["blockers"] = sorted(set(record["blockers"]))
        record["candidate_gate_status"] = (
            "BLOCKED" if record["blockers"] else "CHECKS_PASSED_CANDIDATE_ONLY"
        )
        with OUT.open("x", encoding="utf-8") as stream:
            json.dump(record, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        print(json.dumps({"status": record["status"],
                          "candidate_gate_status": record["candidate_gate_status"],
                          "launch_authorized": False,
                          "output": record["output_path"]}, ensure_ascii=False))
    return 0 if not record["blockers"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
