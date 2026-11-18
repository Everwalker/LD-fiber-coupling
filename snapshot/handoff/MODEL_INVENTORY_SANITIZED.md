# Relevant model-artifact inventory — sanitized summary

Derived from the read-only 1032 inventory report. The report itself and every MPH binary are excluded. Paths below are package-relative; sizes and SHA-256 values identify original local artifacts, not files in this stage. None of these models is approved for public release.

The inventory counted 135 MPH paths under `work/`, not 135 deliverable models. No canonical `ld974_lensfiber_ewfd.mph` was found. This stage contains no MPH files.

## S02 mode branch

| Role | Package-relative path | Bytes | SHA-256 | Dependency and state |
|---|---|---:|---|---|
| Input to 886 | `work/java_s02_convergence_062/job_batch_078/s02_near_cutoff_expanded_078.mph` | 313,222,321 | `062547659f95f98d68105cd60fb2b9c6458a9e2335dbb3de6d88a6db9fdcb184` | Direct input to the later 886 run. Not included. |
| 886 output | `work/s02_modes_fsfix_luna_886/job_batch_886/s02_near_cutoff_r25_886.mph` | 471,310,682 | `ebd7e84f9cd16989cc335e5f1a753a6eefba8257c2e304482f2da5c3109ae12b` | Independent review `evidence/reviews/S02_886_REOPEN_925_LUNA/review.json` verdict: `SOLVED_REOPENED_WITH_LIMITATIONS`. The 925 readback agrees with the saved model. `.class.status=Error` is not independently discriminative; the ADR-004 success/intentional-failure comparison was considered. Two expected CSVs are absent; HE11 identity, G04 and convergence remain incomplete. Not included. |

## S05 air-sheet / mesh branch

| Role | Package-relative path | Bytes | SHA-256 | Dependency and state |
|---|---|---:|---|---|
| Upstream geometry | `work/s05_air_sheet_geometry_381/job_batch_381/air_sheet_geometry_381.mph` | 428,938 | `b27ab443d0ab70cda1dd6fe8d73ab91178be74d85e95f161af6c7f38d9075506` | Input to the 453b Prepare390 source. Not included. |
| 390a input model | `work/s05_air_sheet_injection_453b/mph/air_sheet_inject_390a.mph` | 8,409,441 | `976cb34ab7d36bb428477e34cd01029b1b93ffddab54a6b438bb2308e7cc6388` | Produced from 381 plus Prepare390; later used by 522 and referenced by the 941/951 branches. Not included. |
| 390b mesh-only output | `work/s05_air_sheet_injection_453b/mph/air_sheet_inject_390b.mph` | 607,370,216 | `3576257b1fcbabc016ec793a10d1152a9023c38b3e0c509c35c5f9bb3e2c9958` | The 522 attempt generated 22,527,099 elements and no study/solution/dataset. It exceeded the 1,500,000-element local engineering budget used for that attempt. ADR-095 explicitly says this is not a universal mesh limit. This 390b artifact is not a qualified 951 input/output. Not included. |
| 941 failed-path output | `work/s05_air_sweep_fix_luna_941/job_runs/job_run_941_20261117T074753428Z_396bc96c/S05AirSweepLuna930_S05AirSweepLuna930.mph` | 8,435,085 | `7d85a78af80dd5adfa099e60396319794843659ae9ad87cd57010ad88aaa2bda` | 941 failed before mesh generation on `Unknown property: remeshsourceface`; failure artifact only. Not a valid sweep output and not included. |

**951 status:** the staged Java is an offline mesh-only candidate source. No successful 951 preflight, attempt claim, COMSOL run, mesh, or output model exists. Do not substitute 390b or the 941 failure artifact for a 951 result.

## S06 tip geometry branch

| Role | Package-relative path | Bytes | SHA-256 | Dependency and state |
|---|---|---:|---|---|
| BASE geometry input | `work/s06_partitioned_geometry_364/job_batch_365/device_partition_base_365.mph` | 588,291 | `83d77ba94ac9ad31474f0aa5098524e39e6c49f6a49dc47275050260937eb14d` | Direct input to the 425 BASE tip preparation. Not included. |
| LAT1 geometry input | `work/s06_partitioned_geometry_364/job_batch_365/device_partition_lat1_365.mph` | 596,141 | `8c97d5814593d43a0d043f2e4137bc539f108e631be03a20f73118d1c9bd4174` | Direct input to the 425 LAT1 tip preparation. Not included. |
| 425 BASE geometry | `work/s06_device_tip_setup_425/job_batch_425/device_tip_setup_base_425.mph` | 681,428 | `af7fd4d829018a6ffc2dd5e2dc1b1984844a3ccd3b878ee55f423193e163143a` | Used by later source-injection candidates and 458 reconstruction. Geometry preparation only; no mesh, study or solve. Not included. |
| 425 LAT1 geometry | `work/s06_device_tip_setup_425/job_batch_425/device_tip_setup_lat1_425.mph` | 689,253 | `78889dee70725da2a3c5da5f3176b02a300e09f18547a4e518df7c11a0bbdab9` | Derived from the 365 LAT1 geometry input. No mesh, study or solve. Not included. |
| 458 rebuilt LAT1 | `work/s06_tip_rebuild_physics_458/job_batch_458/device_tip_rebuilt_lat1_458.mph` | 692,658 | `666756b2b5157456221f8e440ea5763c239059aad705c1a45bd04c3ea520855d` | Rebuilt from 425 BASE; 459 is readback only. Still no mesh/study/solve. Not included. |

## Dependency summary

- S02: 078 input → 886 solve/output → 925 read-only reopen. The review accepts only limited mode-solve/readback evidence; CSVs, HE11 and G04 remain open.
- S05: 381 geometry → 453b Prepare390 → 390a → 522 mesh-only 390b. Separately, 941 failed before mesh; 951 has no run/output. The local 1,500,000-element budget belongs to the 522 experiment only.
- S06: 365 BASE/LAT1 → 425 BASE/LAT1 geometry-only preparations → 458 LAT1 rebuild → 459 readback. 940 is an offline source-injection candidate against 425 BASE; 1008 is an offline study-input candidate with upstream gates blocked.

The source 1032 report stated that no MPH was directly suitable for public release. This stage retains that disposition and adds no model. Size limits or metadata-only inspection do not establish public-release permission or safety of model contents.
