# S06 flux and complex-field export candidate fix 1026

> Sanitized derivative of candidate-era notes; not the frozen candidate or its review input. The independent review passed static checks conditionally for runtime only; see `evidence/reviews/S06_FLUX_EXPORT_FIX_1026_LUNA/REVIEW_SUMMARY_SANITIZED.md` in the stage root.

This copy records the 1026 static repair to the 1003 exporter. It does not run COMSOL, open a model, or claim a device result. Raw review files, manifests, and hashes are intentionally omitted; the prior review does not bind the sanitized bytes in this stage.

## Changes

- `partition_evidence.artifact_sha256` is taken only from a separately bound physical partition evidence file whose bytes are hashed and checked. The release-record SHA is never used for that field.
- If the source-field hash or physical partition artifact is unknown, the exporter preserves `null` with a reason in `ledger_861_staging.json` and does not emit `ledger_861_input.json`. The 861 parser requires both values to be 64-character SHA-256 strings; the staging record is deliberately not parser input. The source reference remains the original normalized **1 W**.
- The monitor bounding box remains only a coarse rejection check. Each sample must also map, within the configured geometry tolerance, to at least one entity in `monitorPhysicalFaces` using COMSOL 6.4 `GeomSequence.faceParamRange(int)` and `faceX(int,double[][])`. The matched entity and residual are written beside each field sample. Unsupported geometry or a failed mapping stops export.
- Complex real/imaginary E and H values, signed global-z net flux, the aggregate monitor integral once, and the existing null/reason treatment of HE11, directional power, absorption, and PML are retained.

The local COMSOL 6.4 Java API Javadoc describes `faceParamRange` as returning the two face parameter ranges and `faceX` as evaluating parameter values to coordinates on a geometry face; both are marked unsupported for mesh geometry. The Javadoc is at `doc/help/wtpwebapps/ROOT/doc/com.comsol.help.comsol/api/com/comsol/model/GeomInfo.html` under the installed COMSOL 6.4 directory. Its SHA-256 and the API JAR SHA-256 are frozen in the manifest. This documentation and compilation establish API availability, not membership on the eventual solved device model.

## Offline verification

Compilation uses JDK 21 against the installed COMSOL 6.4 API/model JARs; it does not launch COMSOL:

```powershell
& '<JDK_HOME>\bin\javac.exe' `
  --release 11 -encoding UTF-8 -proc:none `
  -classpath '<COMSOL_HOME>\plugins\com.comsol.api_1.0.0.jar;<COMSOL_HOME>\plugins\com.comsol.model_1.0.0.jar' `
  -d work/s06_flux_field_export_fix_luna_1026/compile/classes `
  work/s06_flux_field_export_fix_luna_1026/src/S06FluxExport1003.java

python -B -m unittest discover -s work/s06_flux_field_export_fix_luna_1026/tests -v
```

The face-membership regression uses a synthetic triangular parameter map to reject a point that lies inside its AABB but outside the mapped face. It does not substitute for a COMSOL run. The candidate remains `REVIEW_BLOCKED` until an independent non-author agent reviews the frozen files; actual 6.4 model selection, face mapping, complex-field export, flux results, and 861 ingestion remain unverified.
