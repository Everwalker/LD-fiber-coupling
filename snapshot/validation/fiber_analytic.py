"""Weak-guidance analytic fiber estimates at the 974 nm baseline.

Recomputable estimates (Malitson index, V number and LP11 weak-guidance
cutoff). These are ANALYTIC APPROXIMATIONS, never COMSOL mode solves or
measurements.
"""
from __future__ import annotations
import math

VC = 2.404825557695773

def malitson_n(lambda_m: float) -> float:
    u = float(lambda_m)/1e-6
    if not math.isfinite(u) or not 0.21 <= u <= 3.71:
        raise ValueError('outside the Malitson fused-silica reference interval')
    n2 = 1.0 + sum(B*u*u/(u*u-C*C) for B, C in
        [(0.6961663, 0.0684043), (0.4079426, 0.1162414), (0.8974794, 9.896161)])
    return math.sqrt(n2)

def fiber_analytic_at(wavelength_nm: float, fiber_cfg: dict) -> dict:
    lam = float(wavelength_nm)
    if not math.isfinite(lam) or lam <= 0:
        raise ValueError('wavelength_nm must be finite positive')
    a_um = float(fiber_cfg['nominal_core_diameter_um'])/2.0
    na = float(fiber_cfg['nominal_NA'])
    if not (math.isfinite(a_um) and a_um > 0 and math.isfinite(na) and na > 0):
        raise ValueError('fiber nominal core radius and NA must be finite positive')
    c = fiber_cfg['cutoff_nm']
    cut_lo = float(c['center']) - float(c['half_range'])
    cut_hi = float(c['center']) + float(c['half_range'])
    two_pi_a = 2.0*math.pi*a_um*1e-6
    v_nom = two_pi_a*na/(lam*1e-9)
    lam_c_nom_nm = two_pi_a*na/VC*1e9
    # Spec-cutoff branch: NA implied by the U2 cutoff upper bound (970 nm).
    na_fit_hi = VC*(cut_hi*1e-9)/(two_pi_a)
    v_spec = two_pi_a*na_fit_hi/(lam*1e-9)  # = VC*cut_hi/lam
    above_reported_cutoff = lam > cut_hi
    above_nominal_estimate = v_nom >= VC
    return {
        'record_type': 'FIBER_ANALYTIC_ESTIMATE',
        'comsol_executed': False,
        'scope': 'weak-guidance analytic estimate; NOT a COMSOL mode solve (S02 pending)',
        'wavelength_nm': lam,
        'n_silica_malitson': malitson_n(lam*1e-9),
        'nominal_core_radius_um': a_um, 'nominal_NA': na,
        'V_nominal': v_nom,
        'cutoff_nm_weak_guidance_from_nominal_NA': lam_c_nom_nm,
        'spec_cutoff_envelope_nm': [cut_lo, cut_hi],
        'wavelength_above_reported_cutoff_upper_bound': above_reported_cutoff,
        'nominal_estimate_at_or_above_LP11_cutoff': above_nominal_estimate,
        'V_spec_cutoff_branch': v_spec,
        'mfd_estimate_um': None,
        'mfd_estimate_reason': (
            f'No MFD estimate is available; an actual numerical mode calculation '
            f'at {lam:g} nm is required.'),
        'interpretation': (
            f'Wavelength {lam:g} nm is '
            f'{"above" if above_reported_cutoff else "at or below"} the reported '
            f'U2 cutoff upper bound {cut_hi:g} nm. The nominal core-diameter/NA '
            f'weak-guidance cutoff estimate is {lam_c_nom_nm:.3f} nm. At the '
            '974 nm baseline this nominal estimate is near cutoff, and 974 nm '
            'is below the manufacturer\'s stated operating range of >980 nm. '
            'These comparisons do not establish the actual mode structure; '
            'numerical mode analysis is required.'),
    }
