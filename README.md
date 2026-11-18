# 974 nm LD-to-lensed-fiber COMSOL handoff

**Status: in progress. There is no validated full-device solution or coupling-efficiency result yet.**

The continuation snapshot is maintained on the [`handoff/ld974-progress-20261118` branch](https://github.com/Everwalker/LD-fiber-coupling/tree/handoff/ld974-progress-20261118). Start with [`PUBLICATION.md`](https://github.com/Everwalker/LD-fiber-coupling/blob/handoff/ld974-progress-20261118/PUBLICATION.md) for source files, selected evidence summaries, missing dependencies, and next steps. This default-branch file is an entry point, not a completed simulation deliverable.

The requested model is one parameterized three-dimensional COMSOL 6.4 Wave Optics model of an equivalent 974 nm laser-diode radiation field crossing air into a lens integrated with the end of a HI1060 FLEX fiber. The main efficiency denominator is the original forward source power, normalized to 1 W. Two HE11 polarization components must be identified and projected from complex fields; total cross-sectional flux is not the HE11 efficiency. A complete power balance must account for reflected, radiated, and mismatched power without double-counting PML flux.

On 18 November 2026, a short local diagnostic established COMSOL 6.4.0.293 and a successful Wave Optics checkout; future availability must be checked again. An auxiliary fiber cross-section mode study was actually solved and reopened with limitations, but HE11 identification and its convergence gates remain open. The complete 3D device, its field, two-polarization coupling efficiency, loss ledger, mesh/open-boundary checks, and clean-solution BASE/LAT1 recomputations have not been completed. Experimental validation was not performed.

The user explicitly authorized the official COMSOL Java API/batch path after the MCP isolation check was blocked. The MCP capability gate remains unverified; Java diagnostic results do not count as an MCP pass. Preserve the single-writer rule and use only a separate session and copies of source models.

The 45° wedge half-angle, 3.25 µm tip radius, and 5.65 µm axial gap are literature-based starting assumptions, not measured device specifications or optimized values. The 974 nm operating point is user-selected, and the 30° fast-axis divergence is an assumption. Tolerance scans, broadband scans, design comparisons, and optimization are deferred.

The source specification lists nominal center wavelengths of 967/970/973 nm, while the fiber's documented recommendation is above 980 nm. Therefore, 974 nm is outside those nominal stated conditions and must be treated as an extrapolated simulation case. Near cutoff, higher-order modes must not be assumed absent.

To protect private data, this public handoff does not include the original U1/U2 source documents, proprietary licenses, installation packages, machine identifiers, or unreviewed binary models. Access to the excluded local inputs and intermediate models requires separate authorization. Accordingly, this repository alone may not reproduce the historical COMSOL runs; the handoff guide identifies what a new contributor must obtain or rebuild.
