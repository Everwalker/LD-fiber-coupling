# Dependencies, inputs, and authorization boundaries

This file describes what a recipient needs to continue and what this snapshot intentionally does not supply.

## U1 and U2 source inputs

- U1 is the user-provided specification image; U2 is the specified Corning HI1060 FLEX document version. Neither source file is included.
- `inputs/manifest.json` retains the expected SHA-256 values and logical filenames for later verification. It marks publication permission as `NOT_ESTABLISHED`.
- The recipient must obtain explicit authorization from the data owner and receive the files privately. The hashes are for byte verification; they are not permission to publish, redistribute, or infer additional product specifications.
- If the files are unavailable, continue only with clearly labeled assumptions and public/derived software work. Do not claim S01 input verification, use other literature values as project measurements, or report a complete physical result.

## COMSOL and execution environment

- Required modeling environment: COMSOL 6.4, with the exact build checked at runtime; the current project has historical evidence for build 6.4.0.293.
- Wave Optics availability and checkout must be confirmed on the recipient's own authorized installation. License files, identifiers, installers, and entitlements are not included or transferable through this snapshot.
- MCP is the project default. MCP tool schemas, live server health, model read/write/reopen behavior, and complex-field export must be checked in the actual recipient environment; this stage does not establish them. G16 is not passed.
- Any alternate Java/MATLAB/CLI path requires the project owner's current authorization and a recorded decision under the project rules. Authorization observed in the original environment must not be assumed to transfer to a new operator or machine.
- Freshly check RAM, available disk, model/job identity, and locks before any authorized model run. No machine name, IP address, process snapshot, or license evidence is supplied.

## Models and implementation dependencies

- No `.mph` model is included or approved for public release. The 1032 sanitized inventory summary records package-relative paths, sizes, SHA-256 values, and dependency links without copying the inventory report or model bytes. The S00/S02/S04 diagnostic artifacts and the 381/390a/390b, 365/425, 458, and 941 artifacts remain private local dependencies. The canonical 3D lensed-fiber model has not been created.
- The staged Java code does not make its referenced models available. In particular, the 453b air-sheet chain depends on the 381 geometry and intermediate 390a model; 951 depends on a reviewed and qualified input model; 425 geometry preparation depends on the 365 BASE/LAT1 models; 940 requires the 425 BASE model; and 1008 requires a hash-audited 940 output from the 957 runner. If an artifact is needed, obtain it privately from its owner with explicit authorization, verify its expected hash in the authorized environment, and keep it out of any public snapshot. If authorization or the bytes are unavailable, stop that dependent runtime branch and continue only with source review or independent software work.
- Two Java files embed generated numerical plane-wave expressions: the 453b preparation source and the 701 source helper. They are withheld because independent public-release review could not establish the provenance of their embedded coefficients from the available snapshot. Obtain authorized private copies or independently reconstruct and validate equivalent expressions; the raw expression JSON and NPZ files are also excluded.
- The staged Java exporter is source only; COMSOL/JDK binaries, API JARs, licenses, installers, and compiled classes are omitted. Path literals changed to `<LOCAL_PATH>` are placeholders: an authorized operator must bind the correct private model path in a separately reviewed working copy. The staged hashes therefore differ from the original frozen source for those files.
- The 1026 exporter depends on a COMSOL 6.4 Java API and a bound model/job/field artifact at runtime. Its tests are static or synthetic and do not supply such artifacts.
- The 1027 guard candidate's non-author static review verdict is `BLOCKED`. It confirmed the PID-race helper changes and 13 synthetic tests but did not validate the complete collector path. Its live preflight reads sensitive process/resource/model/license state and was not executed. Do not run candidate preflight or launch COMSOL while these blockers remain.
- The package preflight and unit tests are software-only. The staged input-hash check is expected to fail until the omitted U1/U2 bytes arrive privately and match the manifest.

## Safe continuation when a dependency is missing

- Missing U1/U2: request an owner-authorized private transfer; otherwise stop claims requiring source-input provenance.
- Missing 6.4/Wave Optics entitlement: stop COMSOL execution and ask the owner to provide an authorized execution environment; do not copy a license or installer into the stage.
- Missing MCP/schema/field-export capability: record the capability as blocked and request an approved route. Do not treat static source inspection as a passed runtime gate.
- Missing model artifact or missing authorization: do not retrieve or publish it through this stage. Request a private, owner-authorized transfer; verify its recorded hash in that private environment. If it remains unavailable, do source/static work only and leave the model-dependent status blocked. Reconstruct from reviewed source/configuration only after prerequisites and reviews pass. Do not substitute a diagnostic `.mph`, 390b mesh-only artifact, literature model, or cached output for a qualified branch result or canonical model.
- Missing independent reviewer: retain `REVIEW_BLOCKED`; do not self-review a candidate or launch it.
