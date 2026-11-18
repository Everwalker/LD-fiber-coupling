"""Verify the actual local evidence referenced by a PASS gate.

JSON Schema checks the shape of IDs; it cannot verify file contents. Call this
function as well before accepting a PASS result. It performs read-only checks
against an artifact index and its package-relative files.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path


def verify_pass_evidence(result: dict, artifacts: dict, root: Path) -> list[str]:
    """Return verified evidence IDs or raise ValueError for missing/stale evidence.

    artifacts maps each evidence ID to an artifact.schema.json-style record.
    """
    if result.get('status') != 'PASS':
        raise ValueError('evidence verification requires a PASS gate result')
    ids = result.get('evidence_ids')
    if (not isinstance(ids, list) or not ids
            or any(not isinstance(item, str) or not item.strip() for item in ids)):
        raise ValueError('PASS requires nonblank evidence IDs')
    base = Path(root).resolve()
    for evidence_id in ids:
        artifact = artifacts.get(evidence_id)
        if not isinstance(artifact, dict) or artifact.get('id') != evidence_id:
            raise ValueError(f'evidence {evidence_id!r} has no matching artifact record')
        relative = artifact.get('path')
        expected = artifact.get('sha256')
        size = artifact.get('size_bytes')
        if not isinstance(relative, str) or not relative.strip() or Path(relative).is_absolute():
            raise ValueError(f'evidence {evidence_id!r} requires a package-relative path')
        path = (base / relative).resolve()
        if not path.is_relative_to(base) or not path.is_file():
            raise ValueError(f'evidence {evidence_id!r} file is missing or outside the package')
        if (not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected)
                or isinstance(size, bool) or not isinstance(size, int) or size <= 0):
            raise ValueError(f'evidence {evidence_id!r} requires a SHA-256 and positive size')
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        if path.stat().st_size != size or digest.hexdigest() != expected:
            raise ValueError(f'evidence {evidence_id!r} size or SHA-256 mismatch')
    return ids.copy()
