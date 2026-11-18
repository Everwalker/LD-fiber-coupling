# LD_Fiber 974 nm handoff snapshot

This is a sanitized public handoff prepared on 2026-11-18. It is not a runnable COMSOL project. Independent public-release review identified two coefficient-bearing sources with insufficient provenance; they are withheld from this release.

## Start here

1. Read `AGENTS.md`, `REQUIREMENTS.md`, and `PLAN.md` for project boundaries and acceptance criteria.
2. Read `handoff/STATUS_AND_TODO.md` for the verified project state and remaining work.
3. Read `handoff/DEPENDENCIES_AND_AUTHORIZATION.md` before seeking inputs, models, software, or runtime access.
4. Read `handoff/MODEL_INVENTORY_SANITIZED.md` for the limited MPH dependency chain; no models are included or approved for public release.
5. Read `handoff/KEY_JAVA_SOURCE_STATUS.md` for the newly included modeling sources and their exact execution status.
6. Read `STAGE_SCOPE.md` and `manifest.json` to see what is included, omitted, and hashed.
7. Treat candidate review summaries under `evidence/reviews/` as redacted summaries of prior reviews. Those reviews did not review the sanitized files in this stage.

## Current scientific state

The project has historical COMSOL 6.4.0.293 and Wave Optics checkout evidence, plus limited diagnostic and auxiliary S02 solve/reopen evidence. The canonical 3D lensed-fiber model, two-polarization HE11 efficiency, complete power ledger, mesh/PML convergence, clean-solution reruns, and experimental validation are not complete. See the status file for the exact limits.

## Software entry points

After the owner provides the private U1/U2 inputs through an authorized channel, the package-level software commands are:

```powershell
python -m tools.preflight
python -m unittest discover -s tests -v
```

The input files are intentionally absent, so input-hash checks cannot pass in this snapshot. These commands do not launch COMSOL and cannot validate a model or physical gate. Tests were not run while preparing this stage.

## Snapshot status

All copied text is a sanitized derivative. Absolute paths, selected process identifiers, and opaque source filenames were replaced or omitted. Hashes in `manifest.json` describe this released snapshot only; they do not prove identity with an original frozen candidate or review package. The source-stage manifest SHA and omitted coefficient-file hashes are retained for provenance.
