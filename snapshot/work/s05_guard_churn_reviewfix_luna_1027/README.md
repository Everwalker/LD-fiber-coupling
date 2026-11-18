# S05 process guard churn repair 1027

> Sanitized derivative of candidate-era notes; not the frozen candidate or its review input. The later independent static review verdict is BLOCKED; see `evidence/reviews/S05_GUARD_REVIEWFIX_1027_LUNA/REVIEW_SUMMARY_SANITIZED.md` in the stage root.

This is an isolated candidate in `work/s05_guard_churn_reviewfix_luna_1027/`. It does not modify the frozen 951 or 1021 files. No COMSOL process or connection was started, no user window or model was read or operated, and no live process, license artifact, resource sample, or model hash was collected during this repair.

## Repairs

- Before, enumerated, and ending PID observations are bound to process creation time. A reused PID with a changed creation time is reconciled as a new identity; an unreadable identity blocks.
- A COMSOL or worker observed during enumeration is retained in `process_churn` and blocks if it started during the scan, exits before the ending census, or its PID is reused. Unknown identity observations also remain blocking.
- Retries are limited to a blocked census whose only blocker is `PROCESS_ENUMERATION_INCOMPLETE` and whose observed churn is fully proven unrelated. Candidate-only results preserve every attempt's blockers, churn events, and identity census summary.
- The 892 process guard is SHA-256 checked before either adapter imports it. The candidate preflight checks all frozen source bindings first and emits those hashes in its own result.
- Candidate preflight retains the pinned 390a model hash, 951 source-model lock and target-tree lock scans, absence of the existing 951 attempt claim, the 6.4/Wave Optics license evidence requirement, 16 GiB/70-percent RAM gates, and 6 GiB disk minimum. It does not create the shared 951 claim; the frozen 951 launcher remains its sole owner.

## Process provenance

Specific process and window identifiers from local observations are omitted. The candidate did not query or inspect the observed process/window.

## Candidate-only preflight contract

After a non-author review approves the exact `manifest.json`, an operator may run `preflight_1027.py` with the required license-evidence directory. Any output is created only as `preflight_1027_<UTC timestamp>.json` in this directory. Its status is always `CANDIDATE_ONLY_NOT_951_PREFLIGHT`, `launch_authorized` is always false, and the frozen 951 launcher does not accept it as 951 evidence. This preflight was not executed during this repair because doing so would read process/window state, license evidence, and the source model, which this task prohibits.

The target-tree `*.lock` scan supplements the pinned source-model-parent lock scan. The 951 candidate claim, original model SHA, license/build/checkout evidence, memory, disk, and GUI ownership remain separate live gates; none is claimed passed here.

## Validation and review

The tests use synthetic identity rows only. They cover same-PID reuse, a worker observed then exited before the ending PID sample, retry-history retention, and the pre-existing churn policies. They do not call the live collector, inspect a window, hash a model, read license evidence, or start COMSOL.

Requested model: `gpt-6-luna/max`; actual backend route was not echoed and is unverified. The executing agent ID was returned by the main Agent's `spawn_agent`: `<INTERNAL_AGENT_ID>`.

The independent review completed with verdict `BLOCKED`: helper repairs and 13 synthetic tests do not validate the full collector path. No candidate preflight, 951 integration, or launch is authorized.
