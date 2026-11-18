# Independent public-release review summary

An independent reviewer checked the frozen local candidate, its file hashes, text contents, and the distinction between completed diagnostics and unfinished device results. The review did not start COMSOL or inspect the original U1/U2 documents. It found no credential or machine-identifier matches in the checked text files.

The review withheld two data-bearing Java sources because the available snapshot did not establish the provenance of their embedded source-field coefficients: `AirSheetInjectPrepare390.java` and `SourcePweVars701.java`. Both were excluded from this public release. The owner may provide them privately, or a contributor may independently reconstruct and validate equivalent source expressions from the documented assumptions. Neither path establishes bytewise or physical equivalence without evidence.

The original local candidate manifest SHA-256 is `7d910b998da089efad22d69c62470b80567882a5f8faa29fd50b52f5682d18ae`. This public release has a separate regenerated manifest reflecting the omissions, documentation corrections, and the nonprivate case-template supplement. The review is not a COMSOL result, a physical gate, or authorization to use an unverified model.
