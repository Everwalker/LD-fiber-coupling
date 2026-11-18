# Project status and continuation tasks

Status snapshot date: 2026-11-18. This is a derived summary of the local project state, recent handoffs, and review records. No raw operational evidence is copied here.

## Verified progress and limits

- Historical runtime evidence confirms actual COMSOL **6.4.0.293** and a completed Wave Optics checkout for the recorded job. The checkout was real and used; it does not establish a seat for a new operator now.
- The source package's recorded software-only check was `preflight PASS` with `57` unit tests passing; COMSOL was not run for that check. These historical results were not re-run on this sanitized stage.
- The first minimal geometry smoke attempt failed during geometry execution on a native dependency after creating a partial diagnostic feature. A later geometry diagnostic was repaired and saved/reopened. Separately, a 974 nm 3D dielectric-sphere diagnostic was solved, reopened, recomputed, and had complex E/H readback. These bounded diagnostics do not pass G16 or establish target-device physics.
- S02 job 886 was solved and independently reopened/read back by job 925. The independent verdict is `SOLVED_REOPENED_WITH_LIMITATIONS`: `.class.status=Error` is not independently decisive because ADR-004's successful and deliberate-failure controls share that marker. Two expected CSVs are missing; both HE11 identities, G04, and convergence remain incomplete. See `handoff/MODEL_INVENTORY_SANITIZED.md` for the model chain and source hashes.
- S04 feasibility history includes a backed B3 solve of about 2.13 million DOF that diverged after roughly 44,446 seconds and produced no frequency-domain solution. A separate roughly 0.30 million DOF unbacked single-mode OOC run succeeded, but is too limited to predict full-model resources or convergence. Neither is the canonical lensed-fiber model.
- `PROJECT_STATE.json` reports scientific status `NOT_RUN`, no canonical model file, and experimental validation `NOT_PERFORMED`.
- The canonical 3D device model, two-polarization HE11 projection/efficiency, complete loss ledger, verified source injection, mesh/domain/PML convergence, and BASE/LAT1 clean-solution reruns are unfinished.
- S07 tolerance work and S08 spectrum work are deferred by scope. Do not run them without a new recorded scope decision.
- 951 was not run: it has no successful preflight, attempt claim, COMSOL job, mesh, or output. The 1,500,000-element budget is specific to the 522 attempt under ADR-095; it is not a general mesh limit. The 390b artifact is mesh-only and cannot qualify as a 951 result. MCP/G16 has not passed. Java/batch authorization in the original project does not establish runtime readiness in a recipient's environment.

## Review/candidate status

- **1025 GUI coexistence policy: BLOCKED.** Do not integrate or use it to authorize a launch.
- **1026 flux export repair: REVIEW_PASS_STATIC_CONDITIONAL_RUNTIME.** Static checks and 11 synthetic tests passed against the original frozen candidate; no device model, actual face mapping, COMSOL export, or physical gate was verified.
- **1027 process-churn repair: BLOCKED / STATIC_REPAIR_REVIEWED_NOT_RELEASED.** The non-author static review confirmed the PID-race helper fixes and the original 13-test synthetic suite. The full collector path was not exercised; the 1025 GUI coexistence review remains blocked; no live process, resource, license, model, or lock gates were checked. No candidate preflight or COMSOL launch is currently authorized. It is not integrated and does not authorize 951.

The sanitized copies in this stage are not the exact frozen candidates reviewed in those prior records. See the individual redacted summaries and `handoff/KEY_JAVA_SOURCE_STATUS.md`; the Java branches there are offline candidates or geometry preparation, not completed device solutions.

## Ordered continuation checklist

1. **Independent security review of this stage:** inspect every staged file, confirm the manifest matches the directory, and check for secrets, private source material, identifiers, absolute paths, binaries, and unexpected files. Decide separately whether the sanitized source is suitable for later public release.
2. **Authorized inputs:** obtain U1/U2 through a private, owner-approved channel; place the exact bytes at the logical paths in `inputs/manifest.json`; verify SHA-256 locally. Do not commit the originals.
3. **Runtime prerequisites:** on the authorized execution environment, freshly confirm COMSOL 6.4.0.293, Wave Optics availability/checkout, RAM/disk limits, actual MCP schemas and live connection, and complex-field export behavior. Record current evidence without exposing machine identity or license details.
4. **Resolve runtime-control blockers:** address the 1027 full-collector coverage gap and the 1025 coexistence blockers in new isolated candidates, then obtain fresh non-author review. Do not run candidate preflight or launch COMSOL while the current BLOCKED findings remain. Keep 1026 conditional until its device-bound mapping and export behavior are exercised and reviewed.
5. **Complete S01–S03:** reconcile authorized source inputs, preserve the 974 nm limitations, identify the two HE11 polarizations and near-cutoff candidates, and validate the vector source under the frozen thresholds.
6. **Complete S04–S06:** establish local receiver physics and a verified source-injection path, then build the single canonical 3D wedge/rounded-tip fiber model. A diagnostic sphere or an unbacked/single-mode proxy cannot substitute.
7. **Complete S09:** BASE and LAT1 gates, three-grid/domain/PML checks, source/return/mismatch/radiation/absorption accounting, clean-solution reruns, independent review, and a reopened/retrievable 6.4 model artifact.
8. Keep experimental validation `NOT_PERFORMED` until actual authorized experiments are performed and separately documented. Keep S07/S08 deferred.

Do not infer a numerical gate from software tests, a static review, a diagnostic solve, a candidate-only preflight, or a historical cached artifact.
