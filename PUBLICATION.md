# How to use this checkpoint

The `snapshot/` directory contains a sanitized handoff derived from a frozen local candidate. Start with [`snapshot/handoff/STATUS_AND_TODO.md`](snapshot/handoff/STATUS_AND_TODO.md), then consult `snapshot/REQUIREMENTS.md`, `snapshot/PLAN.md`, and `snapshot/handoff/DEPENDENCIES_AND_AUTHORIZATION.md`.

One nonprivate file, `snapshot/templates/case.template.json`, was added after the local candidate was frozen because its absence caused a software test error. Its SHA-256 is `9532b5213209e93879bc4c3960434c042b347e6774a61ed65a22b4244a3047c7`. The public snapshot manifest covers the current release, including this supplement.

An independent public-release review of the local candidate could not establish the provenance of two coefficient-bearing Java sources. They were withheld, and the public manifest was regenerated; it records the original candidate manifest hash and the withheld paths. Historical candidate-era review statements in other files describe their state when written and do not grant approval to run the sanitized copies.

No original U1/U2 input, `.mph` model, license file, installer, credential, raw operational log, or user machine identity is included. The historical COMSOL runs cannot be reproduced from this repository alone: obtain the missing inputs and intermediate models privately from their owner, or rebuild suitable copies after confirming the documented prerequisites. The included source files with path substitutions are sanitized derivatives; their hashes do not certify identity with the original reviewed files.

Nothing in this checkpoint establishes a solved complete 3D device, HE11 coupling efficiency, a complete loss ledger, convergence, experimental validation, or a passed MCP capability gate.

## Software checks on the public snapshot

An initial run of the 57 package tests reported four failures because the private U1/U2 originals are intentionally absent, plus one error from the missing case template. After adding the template, the five gate-contract tests passed. The full suite was not rerun after that addition. `python -B -m tools.preflight` still returns `SOFTWARE_CHECKS_FAIL`: its input-hash check fails because U1/U2 are absent, while its other five software checks pass. These checks do not start COMSOL or establish any physical result. After receiving the authorized originals privately, use the logical input filenames and verify the recorded hashes before rerunning the full suite.
