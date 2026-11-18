# Stage contents and exclusions

## Included

- Sanitized project instructions, v3 requirements, plan, baseline ADR, and the implementation/physics/validation documents needed to continue the one-baseline work.
- Shareable parameter, gate, sampling, and schema files; analytic/source software; package preflight; and the existing unit-test sources.
- Selected 1025, 1026, and 1027 candidate source, templates, and tests at their original relative paths.
- Selected S05/S06 Java source: 453b air-sheet mesh/solve/export steps, 951 mesh candidate/helper, 425 geometry setup, 940 injection candidate, and 1008 study-input candidate with its synthetic binding test. Two coefficient-bearing preparation/helper sources are withheld as described below.
- `handoff/MODEL_INVENTORY_SANITIZED.md`: selected model paths, sizes, SHA-256 values, and dependency chain from the read-only 1032 inventory, with corrected S02/mesh-budget interpretation. No MPH bytes are included.
- `handoff/KEY_JAVA_SOURCE_STATUS.md`: execution and review boundaries for each included Java branch and the two withheld coefficient-bearing sources.
- Redacted summaries of the 1025 and 1026 independent reviews and the completed-but-BLOCKED 1027 independent review.
- A reduced `inputs/manifest.json` containing only logical U1/U2 labels, expected SHA-256 values, and permission status. It does not contain the source files or their opaque original filenames.
- A generated `manifest.json` and `MANIFEST.sha256` for this stage's actual files.

## Excluded

- `inputs/private_originals/**` (U1 screenshot and U2 PDF): publication permission is not established.
- `AirSheetInjectPrepare390.java` and `SourcePweVars701.java`: independent public-release review could not establish the provenance of their embedded source-field coefficients from the available snapshot.
- Every `.mph` file, including S00/S02/S04 diagnostic models. The canonical lensed-fiber model has not been created.
- Raw run logs, process/license/resource snapshots, screenshots, environment dumps, job records, raw review JSON, frozen candidate manifests, and raw input evidence.
- COMSOL or Java binaries/classes, API JARs, installers, license files, license identifiers, keys, credentials, and machine-specific names, addresses, or absolute user paths.
- The 951 launcher and unreviewed runtime evidence. No passing 951 preflight, claim, or mesh job exists.
- `PROJECT_STATE.json`, the full `NEXT.md`, and the historical `CHANGELOG.md`; they contain large amounts of machine-specific operational history. Their relevant current state is summarized in `handoff/STATUS_AND_TODO.md`.

## Hash and review meaning

The sanitizer may change file bytes, line endings, path literals, synthetic PID examples, and opaque identifiers. The hashes in this stage are newly computed from the staged bytes. They are not the original frozen-file hashes and do not make a sanitized candidate an approved or runnable freeze.

The 1025/1026/1027 review summaries describe findings against their original local frozen candidates. Those source candidates, manifests, and raw reviews are not included. The summaries are not substitute review evidence. The original 1027 review is `BLOCKED`: helper fixes and 13 synthetic tests do not validate the complete collector path or grant a live gate. The added 453b/425/940/1008 source branches are also not completed device results. Independent public-release review of the earlier candidate identified two coefficient-bearing sources that are withheld from this release.

## Workspace and remote boundary

The source workspace did not expose Git metadata (`git status` reported that it is not a repository). The owner selected a public repository; see its Git history for the publication state of this sanitized snapshot.
