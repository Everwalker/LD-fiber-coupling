"""v3 tip geometry math precheck: arc + wedge profile in (y,z), invariant along x.

Scope: parameter-range validation and C0/C1 tangent continuity of the
closed-form profile. This does NOT create, import, or validate any COMSOL
geometry; every record is marked GEOMETRY_PARAMETER_MATH_PRECHECK.
Coordinates: x=horizontal slow axis (extrusion, invariant), y=vertical fast
axis (profile direction), z=propagation axis.

Profile (engineering-assumed construction of this package; the user scoped a
fiber-tip integrated lens in a single model, but this specific arc+wedge
formula is not a vendor specification nor a user measurement):
  arc    f(y) = R - sqrt(R^2 - y^2),        |y| <= y_t
  tangent y_t = R*cos(alpha), z_t = R*(1 - sin(alpha))
  wedge  f(y) = z_t + cot(alpha)*(|y|-y_t), |y| > y_t
Limits: 0 < alpha < 90 deg, R > 0, gap > 0, all finite.
"""
from __future__ import annotations
import math
import numpy as np

def _finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite real number')
    return float(value)

def _parse(alpha_deg, R_m):
    alpha = math.radians(_finite(alpha_deg, 'wedge_half_angle_deg'))
    R = _finite(R_m, 'tip_radius_m')
    if not 0.0 < alpha < math.pi/2:
        raise ValueError('require 0 < wedge_half_angle_deg < 90')
    if R <= 0:
        raise ValueError('tip radius must be positive and finite')
    return alpha, R

def tangent_point(alpha_deg, R_m):
    alpha, R = _parse(alpha_deg, R_m)
    return R*math.cos(alpha), R*(1.0-math.sin(alpha))

def profile_f(y, alpha_deg, R_m):
    """Surface sag f of the arc+wedge profile at fast-axis coordinate(s) y."""
    alpha, R = _parse(alpha_deg, R_m)
    y_arr = np.asarray(y, dtype=float)
    scalar = y_arr.ndim == 0
    y_arr = np.atleast_1d(y_arr)
    if not np.isfinite(y_arr).all():
        raise ValueError('profile samples must be finite')
    yt = R*math.cos(alpha); zt = R*(1.0-math.sin(alpha))
    cot = math.cos(alpha)/math.sin(alpha)
    ay = np.abs(y_arr)
    f = np.where(ay <= yt, R - np.sqrt(np.maximum(R*R - ay*ay, 0.0)),
                 zt + cot*(ay - yt))
    return float(f[0]) if scalar else f

def validate_head(alpha_deg, R_m, gap_m) -> dict:
    """Return a math-precheck record or raise ValueError on an illegal head."""
    alpha, R = _parse(alpha_deg, R_m)
    gap = _finite(gap_m, 'axial_gap_m')
    if gap <= 0:
        raise ValueError('axial gap must be positive and finite')
    yt = R*math.cos(alpha); zt = R*(1.0-math.sin(alpha))
    cot = math.cos(alpha)/math.sin(alpha)
    # C0 continuity at the tangent point (arc branch vs wedge branch).
    v_arc = R - math.sqrt(max(R*R - yt*yt, 0.0))
    value_gap = abs(v_arc - zt)
    # C1 continuity: arc slope at y_t equals the wedge slope cot(alpha).
    denom = math.sqrt(max(R*R - yt*yt, 0.0))
    slope_arc = yt/denom if denom > 0 else math.inf
    slope_gap = abs(slope_arc - cot)
    # Numerical one-sided symmetric derivative check on the assembled profile.
    eps = max(1e-9*yt, 1e-15)
    fd = (profile_f(yt+eps, alpha_deg, R_m) - profile_f(yt-eps, alpha_deg, R_m))/(2*eps)
    fd_gap = abs(fd - cot)
    # Apex sanity and monotone non-decreasing sag away from the axis.
    apex = profile_f(0.0, alpha_deg, R_m)
    if abs(apex) > 1e-12*max(R, 1e-9):
        raise ValueError('profile apex is not at f(0)=0')
    ys = np.linspace(0.0, 3.0*yt, 401)
    fs = profile_f(ys, alpha_deg, R_m)
    if np.any(np.diff(fs) < -1e-12*max(R, 1e-9)):
        raise ValueError('profile sag must be non-decreasing in |y|')
    return {
        'record_type': 'GEOMETRY_PARAMETER_MATH_PRECHECK',
        'comsol_executed': False,
        'scope': 'closed-form arc+wedge parameter math; NOT an actual COMSOL geometry',
        'wedge_half_angle_deg': _finite(alpha_deg, 'wedge_half_angle_deg'),
        'tip_radius_m': R, 'axial_gap_m': gap,
        'y_t_m': yt, 'z_t_m': zt,
        'value_continuity_abs_m': value_gap,
        'slope_arc_at_tangent': slope_arc, 'slope_wedge': cot,
        'slope_continuity_abs': slope_gap, 'slope_finite_difference_gap': fd_gap,
        'apex_f0_m': apex,
    }
