# S05 other COMSOL GUI coexistence assessment 1025

> Sanitized derivative of candidate-era notes; not the frozen candidate or its review input. Current independent review verdict is BLOCKED; see `evidence/reviews/S05_GUI_COEXIST_1025_LUNA/REVIEW_SUMMARY_SANITIZED.md` in the stage root.

Status: `BLOCKED_OFFLINE_CANDIDATE_REVIEWED_NOT_INTEGRATED`.

## Purpose and limits

This candidate tests whether 951 can use a narrowly scoped, noninteractive batch path while other COMSOL 6.4 GUI projects remain open. It does not launch/connect COMSOL, enumerate/control processes, inspect windows or MPH contents, modify 951/1021, or write outside this directory. `coexistence_policy_1025.py` is pure-data code; it does not grant launch authorization.

The policy does not need an ambient GUI PID, ownership claim, project association, or process-census result. It carries any supplied GUI context unchanged and keeps those fields unknown. The 1021 independent review is bound as a rejected prior finding only; 1025 neither imports nor depends on 1021 passing. The exact rejected review SHA-256 is `f404cc6a8a375077f6d5d6b66946dc27a9db839ab6530a80d839c266f0888ef9`.

## What the frozen 951 sources establish

Source paths and hashes are in `manifest_1025.json`.

- The launcher starts a separate `comsolbatch.exe` with a fresh job directory. It gives COMSOL job-specific preference, temporary, configuration, data, and recovery directories. The Java source has no GUI/server attach call and loads the frozen 390a model through `ModelUtil.loadCopy`.
- The Java source writes the diagnostic only to the relative job output. The launcher uses a unique job directory, an exclusive candidate claim and a job-local claim, refuses an existing claim/output, and preserves no-retry/manual-reconciliation semantics after claim.
- The preflight checks the source-model SHA-256 and absence of source-directory `*.lock`; the launcher rechecks the source hash before starting and after completion. The Java source does not save the 390a source. This is a source-code no-write contract, not an OS read-only ACL or an interprocess file lock held during `loadCopy`.
- Fresh COMSOL 6.4/Wave Optics checkout, source lock/hash, 16 GiB/70%-RAM admission and at least 6 GiB free disk are required by the frozen procedure. These are preflight conditions; they do not prove current host state.
- Monitor 991 has an independent `LIMITED_MONITOR_SOURCE_ONLY` approval. It binds the exact 951 job/PID/start time/command and samples the job tree. Its review explicitly says it is not a hard memory cap, does not automatically stop on low system-available RAM or disk use, terminates only the revalidated main process, and cannot confirm descendants after a stop/end. Human monitoring and descendant reconciliation remain necessary. The 991 review does not authorize a live monitor or COMSOL run.

These facts support a **candidate-specific no-GUI-session-interaction design**: the batch code uses its own process, model copy, state directories, output, and claim. They do not prove current license capacity, source lock/hash state, resources, monitor liveness, or complete protection from concurrent writes to the source. Shared licensing, RAM, disk, and CPU remain real contention paths.

## Proposed independent admission rule

The pure policy prototype returns eligibility only after a non-author review binds this manifest and all required source and live facts are explicitly `true`. In particular, the live gate requires:

- a fresh COMSOL 6.4 and Wave Optics checkout;
- current source-lock-free and source-hash matches, plus a fresh unique target/claim;
- the 951 RAM/disk admission gates;
- monitor 991 armed before the batch starts and a confirmation bound to the exact 951 job;
- an active human observer for monitor liveness, available RAM, and disk headroom.

The last point is necessary because the reviewed 991 monitor does not enforce a low-available-RAM or runtime-disk threshold. Any monitor `UNKNOWN`, early exit, memory stop, or unconfirmed descendant leaves the job state unresolved. A later runtime source-hash mismatch, lock conflict, claim/output collision, failed license checkout, resource threshold, or 951 PID/start-time/command mismatch blocks or invalidates the run.

A process appearing in the OS is **not itself** evidence of user approval. A concrete conflict is blocking: a source lock/hash change, target/output/claim collision, batch-to-GUI/server attach, failed shared license/resource gate, or loss of exact 951 job/monitor binding. A new COMSOL project/job or worker started after fresh preflight is outside this candidate's incumbent-GUI allowance; it remains unresolved until the separate process-race gate is independently repaired/reviewed (1027) and its evidence is available. A new PID is never treated as user confirmation. This rule avoids using the rejected 1021 census to decide whether the already-open GUI project is safe; its adequacy is a question for the independent reviewer. If source lock/hash and resource/monitor gates cannot detect a material conflict, the reviewer must leave the candidate blocked.

## Relationship to existing gates and 1027

The frozen 951 preflight/launcher still has its `OtherComsolGuisIdentified` and task-ownership attestations. This candidate does not clear or rewrite them. Any future use needs a newly frozen launcher/preflight integration reviewed against this policy; the 951 review only approved the old conditions.

1021's independent review R2 is `REJECTED`. It identifies PID-reuse and short-lived worker races and says to retain the current GUI blocker. 1025 therefore makes no claim about global process-census safety and does not use 1021 output. Agent 1027 is separately repairing the process race. Suggested composition: retain 1025's candidate-specific isolation/resource result and 1027's process-race result as separate fields in a future manifest; neither field rewrites the other's evidence. A future launcher must bind the 951 child by job ID, PID, creation time, and command. The separate 1027 result should cover new-process/PID-reuse races without requiring per-PID confirmation that an incumbent GUI belongs to another user's project. A 1027 pass must never be interpreted as user confirmation of any ambient process; a 1027 failure or missing result leaves the final invocation blocked.

## Current decision: BLOCKED

Historical diagnostics left a process identity unresolved. The exact identifier, process name, window handle, and machine observation are intentionally omitted from this stage. A general statement about an existing window was not treated as process-specific confirmation.

No fresh launch preflight, license checkout, source lock/hash check, resource sample, or monitor binding was performed. The historical monitor source approval is not a live monitor. A later independent static review returned BLOCKED; the current evidence does not satisfy live facts, and the original 951 GUI blocker remains in force. This is not an authorization to launch or a claim that coexistence has been demonstrated.

The 951 source has a possible gap that must be judged in review: `ModelUtil.loadCopy` and before/after hashes establish intended copy/no-write behavior, but the runner does not hold an OS read lock over the copy operation or continuously monitor the source hash. If that gap matters, the safe decision is `BLOCKED` until a separately reviewed source-protection change exists.

## Independent review handoff

The author did not self-review and no subagent was dispatched. Ask a non-author to read the exact frozen code, tests, this analysis, and every source binding in `manifest_1025.json`; review must bind its SHA-256. Approval would cover only this offline policy proposal. The current live gate remains blocked, and integration requires a new candidate and the required ADR/CHANGELOG update; shared files were outside this write scope.

Execution record: scheduler-assigned `agent_id=<INTERNAL_AGENT_ID>`; requested model `gpt-6-luna/max`; backend route not returned, therefore unverified; no subagents used.
