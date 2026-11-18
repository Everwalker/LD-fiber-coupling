# Independent review request: 1025 coexistence policy

Please review the exact files and source hashes in `manifest_1025.json`; reviewer must not be the author and must bind `manifest_1025.sha256`.

Review questions:

1. Do the frozen 951 launcher/Java source, manifest, and original independent review prove that the candidate batch avoids the GUI/session/model of other COMSOL projects, or is any interaction path omitted?
2. Are `ModelUtil.loadCopy`, source lock/hash checks, unique job output/claim, and exact 951 PID/start-time/command monitoring enough for safe coexistence? In particular, does the absence of an OS read lock during `loadCopy` require a new blocker or stronger source protection?
3. Do shared license/RAM/disk constraints and 991 monitor limitations require `BLOCKED` even after live preflight and active human observation?
4. Does this policy preserve an unidentified process/project association without inferring user confirmation and without relying on the rejected 1021 process census?
5. What concrete conflict conditions must remain blocking, and is the proposed separate result interface suitable for later composition with the independently authored 1027 process-race repair?

The reviewer must read source artifacts directly, not rely on this summary. A pass would approve only the offline policy proposal; it is not approval to integrate, launch COMSOL, or claim coexistence has been demonstrated. If the evidence is insufficient, record `REJECTED` or `BLOCKED` with the unresolved evidence.
