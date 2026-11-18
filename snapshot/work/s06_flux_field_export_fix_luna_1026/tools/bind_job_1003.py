"""Bind one explicit runner job and its audited model artifact for S06-1003."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
HEX64 = re.compile(r"[0-9a-fA-F]{64}\Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {label}: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return value


def _artifact_path(job_dir: Path, relative: object) -> tuple[Path, str]:
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError("job manifest output_relative_path is missing")
    normalized = relative.replace("\\", "/")
    rel = PurePosixPath(normalized)
    if rel.is_absolute() or ".." in rel.parts or (rel.parts and ":" in rel.parts[0]):
        raise ValueError("output artifact path must stay inside the job directory")
    path = (job_dir / Path(*rel.parts)).resolve(strict=True)
    if not path.is_relative_to(job_dir) or not path.is_file():
        raise ValueError("output artifact path must stay inside the job directory")
    return path, rel.as_posix()


def bind_job(job_dir: Path, audit_path: Path, output_path: Path,
             expected_job_id: str) -> dict[str, str]:
    job_dir = job_dir.resolve(strict=True)
    if not job_dir.is_dir() or not expected_job_id or job_dir.name != expected_job_id:
        raise ValueError("job_id must match the explicit job directory name")
    job_manifest_path = job_dir / "job.json"
    job = _load_json(job_manifest_path, "job manifest")
    if job.get("job_id") != expected_job_id:
        raise ValueError("job_id in job manifest does not match the requested job_id")
    artifact, artifact_relative = _artifact_path(job_dir, job.get("output_relative_path"))

    audit_path = audit_path.resolve(strict=True)
    audit = _load_json(audit_path, "artifact audit")
    if audit.get("artifact_audit_pass") is not True:
        raise ValueError("artifact audit did not pass")
    if audit.get("job_id") != expected_job_id:
        raise ValueError("job_id in artifact audit does not match the requested job_id")
    output_audit = audit.get("output_artifact")
    if not isinstance(output_audit, dict):
        raise ValueError("artifact audit has no output_artifact record")
    if output_audit.get("path", "").replace("\\", "/") != artifact_relative:
        raise ValueError("artifact audit path does not match the job manifest")
    actual_sha = sha256(artifact)
    audited_sha = output_audit.get("sha256")
    if not isinstance(audited_sha, str) or not HEX64.fullmatch(audited_sha):
        raise ValueError("artifact audit SHA-256 is missing or malformed")
    if actual_sha.lower() != audited_sha.lower():
        raise ValueError("artifact SHA-256 does not match the artifact audit")

    receipt_path = job_dir / "input_receipt_957.json"
    receipt_sha = ""
    if receipt_path.is_file():
        receipt = _load_json(receipt_path, "957 input receipt")
        if receipt.get("job_id") != expected_job_id:
            raise ValueError("job_id in 957 input receipt does not match the requested job_id")
        if receipt.get("output_relative_path", "").replace("\\", "/") != artifact_relative:
            raise ValueError("957 input receipt output path does not match the job manifest")
        receipt_sha = sha256(receipt_path)

    output_path = output_path.resolve()
    if not output_path.is_relative_to(ROOT) or output_path.exists():
        raise ValueError("binding output must be a new file inside the S06-1003 directory")
    values = {
        "schema_version": "1",
        "job_id": expected_job_id,
        "job_dir": job_dir.as_posix(),
        "job_manifest_path": job_manifest_path.as_posix(),
        "job_manifest_sha256": sha256(job_manifest_path),
        "artifact_relative_path": artifact_relative,
        "artifact_path": artifact.as_posix(),
        "artifact_sha256": actual_sha,
        "artifact_audit_path": audit_path.as_posix(),
        "artifact_audit_sha256": sha256(audit_path),
        "artifact_audit_pass": "true",
        "artifact_audit_model_result": str(audit.get("model_result", "NOT_REPORTED")),
        "solution_established": "false",
        "input_model_path": str(job.get("input_model_path", "")),
        "input_model_sha256_before": str(job.get("input_model_sha256_before", "")),
        "input_receipt_957_path": receipt_path.as_posix() if receipt_sha else "",
        "input_receipt_957_sha256": receipt_sha,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="ascii", newline="\n") as stream:
        for key in sorted(values):
            value = values[key].replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")
            stream.write(f"{key}={value}\n")
        stream.flush()
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-dir", required=True, type=Path)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--artifact-audit", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = bind_job(args.job_dir, args.artifact_audit, args.out, args.job_id)
        print(json.dumps({
            "binding_written": True,
            "job_id": result["job_id"],
            "artifact_sha256": result["artifact_sha256"],
            "solution_established": False,
            "interpretation": "job and artifact identity only; no COMSOL solution claim",
        }, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"binding_written": False, "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
