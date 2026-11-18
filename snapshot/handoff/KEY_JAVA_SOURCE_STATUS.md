# Selected Java sources and candidate status

The files below were selected because they provide a direct next step in the S05/S06 modeling chain. They are path-sanitized copies for review, not original freeze artifacts. Their stage hashes are in `manifest.json`; original source/freeze hashes and freeze-manifest references are recorded in the generated source-lineage section of that manifest. Any `<LOCAL_PATH>` must be replaced only inside an authorized execution environment before use.

## S05 air-sheet injection and mesh chain — 453b

Staged at `work/s05_air_sheet_injection_453b/`:

- `AirSheetInjectMesh390b.java`
- `AirSheetInjectInit390c.java`
- `AirSheetInjectSolve390d.java`
- `AirSheetInjectExport390e.java`

These are sequential source steps because the mesh, initialization, solve, and export classes consume the preceding model. The 453b candidate reports offline compilation, has status `NEEDS_INDEPENDENT_REVIEW`, `comsol_model_executed=false`, and grants no gates. The 381 geometry model is absent. The data-bearing `AirSheetInjectPrepare390.java` is also withheld: independent public-release review could not establish the provenance of its embedded plane-wave coefficients from the public snapshot. Request it privately from the owner or independently reconstruct and validate the source from the specified assumptions; do not claim exact identity without evidence. The raw 381/355/390 MPH and expression artifacts are not included. The 390b output was a 522 mesh-only over-budget diagnostic, not a valid 951 output.

## S05 951 mesh candidate — not run

Staged at `work/s05_air_sweep_property_fix_luna_951/`:

- `S05AirSweepLuna930.java`
- `S05AirSweepGroups.java`
- `S05AirSweepGroupsTest.java` (synthetic helper test)

The original 951 candidate passed a conditional independent offline review for one controlled mesh-only attempt; the sanitized copy in this snapshot is not the reviewed artifact. No 951 preflight, claim, COMSOL job, mesh or output model exists. The separate 1025 GUI coexistence review is `BLOCKED`, and the 1027 guard review is `BLOCKED`; do not run its preflight or launch COMSOL from this snapshot.

## S06 tip geometry preparation — 425

Staged at `work/s06_device_tip_setup_425/DeviceTipSetup425.java`. This source prepares BASE/LAT1 tip geometry and has a separate readback history; it does not create a mesh, study, optical solution, field, HE11 efficiency or loss ledger. It is not a completed device model. Its input 365 geometry MPH files are not staged.

## S06 source injection — 940; helper 701 withheld

Staged at:

- `work/s06_425_source_fix_luna_940/src/SourceInject425940.java`

940 is `OFFLINE_SOURCE_CANDIDATE_COMPILED_PENDING_NONAUTHOR_REVIEW_NOT_RUN`; G03a/G03b/G17, source-face normal/side mapping, live license/resource/lock checks, and actual injection are unverified. The data-bearing `SourcePweVars701.java` helper and its source expression table are withheld because their coefficient provenance was not established for public release. They must be obtained privately from the owner or rebuilt and independently validated from the stated source assumptions before use. No bitwise or physical equivalence to the withheld helper is claimed.

The original `tests/test_source_fix_940.py` is intentionally omitted: its exact-equivalence test reads the excluded expression table and predecessor manifest, so it is not self-contained in this snapshot. The 940 verifier and original compile/test logs are also omitted; their source-workspace paths and execution evidence are not portable stage artifacts.

## S06 device studies input candidate — 1008

Staged at `work/s06_device_studies_input_fix_luna_1008/src/DeviceStudies1002.java` and its synthetic binding test. The original 1008 candidate passed an independent offline source review; execution is still blocked, and the sanitized copy is not the reviewed artifact. The recorded compile and nine-method/twelve-assertion test used synthetic bytes; no Java main, COMSOL, model load/save/reopen, frequency readback or physical gate ran. Upstream S04/S05, source normalization, port identity, HE11 identity and G17 remain open.

## Meaning of path-redacted hashes

For any source containing an absolute local path, the staged text substitutes `<LOCAL_PATH>`; its stage SHA-256 therefore differs from the original frozen source SHA-256. Files with no machine-specific path that required replacement may retain their original source hash. The manifest records both and whether the original bytes match their candidate freeze. The prior offline compile/test statements refer to original candidates, not this redacted stage; these staged copies were not compiled or tested here.

No `.mph`, generated NPZ, raw `expressions_sheet_355.json`, compiled `.class`, JAR, COMSOL/JDK installation file, original run log, or machine-specific path is included. `DeviceStudies1002BindingTest.java` and `S05AirSweepGroupsTest.java` are source-only synthetic tests; their historical passing results belong to the original candidates, and this snapshot did not rerun them. The two data-bearing coefficient sources were withheld following independent public-release review.
