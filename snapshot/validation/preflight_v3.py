"""v3 software preflight: inputs, parameter policy, geometry/fiber/source math, gates.

Never starts or queries COMSOL. The output deliberately carries no field that
could read as a COMSOL pass; fixed markers comsol_executed=false and
model_artifact='NOT_IMPLEMENTED_IN_THIS_STAGE' are enforced by self-scan.
"""
from __future__ import annotations
import hashlib
import json
import math
import re
from pathlib import Path
import numpy as np

from src.source.angular_spectrum import GridSource, fit_source, fwhm
from validation.fiber_analytic import fiber_analytic_at
from validation.geometry_v3 import validate_head

V2_LASER_CENTER = {'min': 967, 'typ': 970, 'max': 973}
V2_GATE_FROZEN = {
    'G01': ('boolean', 1, 'S01'), 'G02': ('boolean', 1, 'S01'),
    'G03a': ('max', 0.001, 'S03'), 'G03b': ('max', 0.01, 'S03'),
    'G04a': ('max', 1e-05, 'S02'), 'G04b': ('min', 0.999, 'S02'),
    'G05a': ('max', 0.001, 'S04'), 'G05b': ('max', 0.001, 'S04'),
    'G06a': ('max', 0.005, 'S04'), 'G06b': ('max', 0.001, 'S04'),
    'G07a': ('max', 0.005, 'S06'), 'G07b': ('max', 0.01, 'S08'),
    'G08': ('max', 0.005, 'S09'), 'G09': ('max', 0.003, 'S09'),
    'G10': ('max', 0.01, 'S05'), 'G11a': ('max', 0.005, 'S05'), 'G11b': ('max', 0.01, 'S05'),
    'G12a': ('min', 0.999, 'S08'), 'G12b': ('max', 0.003, 'S08'), 'G13': ('boolean', 1, 'S08'),
    'G14': ('boolean', 1, 'S06'), 'G15': ('max', 0.001, 'S09'), 'G16': ('boolean', 1, 'S00'),
    'G17': ('boolean', 1, 'S05'), 'G18': ('boolean', 1, 'S09'), 'G19': ('boolean', 1, 'S09'),
    'G20': ('boolean', 1, 'S09'), 'G21': ('boolean', 1, 'S07'),
}
V2_GATE_NAMES = {
    'G18': '全部强制情景的非法参数拦截和合法重建回归通过',
    'G20': '四模型与复场制品可取回哈希一致',
}
APPLICABILITY = {'applicable', 'deferred', 'not_applicable', 'conditional'}
FORBIDDEN_KEY = re.compile(r'(comsol|solve|model).{0,20}(pass|success|ok)|(?:^|_)(?:passed|verified)(?:$|_)', re.I)

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def check_inputs(root: Path) -> dict:
    errors = []
    items = json.loads((root/'inputs/manifest.json').read_text(encoding='utf-8'))['items']
    seen = set()
    for item in items:
        seen.add(item['id'])
        path = (root/item['path']).resolve()
        if not path.is_file():
            errors.append(f"{item['id']}: missing file {item['path']}")
            continue
        actual = sha256_file(path)
        if actual != item['sha256']:
            errors.append(f"{item['id']}: sha256 mismatch actual={actual}")
    if seen != {'U1', 'U2'}:
        errors.append(f"manifest ids must be exactly U1,U2; got {sorted(seen)}")
    return {'status': 'PASS' if not errors else 'FAIL', 'items': len(items), 'errors': errors}

def check_parameters(cfg: dict) -> dict:
    errors = []
    if cfg.get('schema_version') != 3:
        errors.append('parameters schema_version must be 3')
    center = cfg['laser']['center_nm']
    if {k: center[k] for k in ('min', 'typ', 'max')} != V2_LASER_CENTER:
        errors.append('laser.center_nm must remain the frozen 967/970/973 band')
    sim = cfg['simulation']
    if sim.get('case_id') != 'LD974-WEDGE-BASE-001':
        errors.append('the frozen v3 baseline case_id must be LD974-WEDGE-BASE-001')
    wl = sim['wavelength_nm']
    if isinstance(wl, bool) or not isinstance(wl, (int, float)) or not math.isfinite(float(wl)) or float(wl) <= 0:
        errors.append('simulation.wavelength_nm must be finite positive nm')
    elif float(wl) != 974.0:
        errors.append('the frozen v3 baseline must be 974 nm; a different wavelength requires a new case and ADR')
    power = cfg['laser']['power_W']; denom = sim['denominator_W']['value']
    if not (isinstance(power, (int, float)) and math.isfinite(power) and 0 < power):
        errors.append('laser.power_W must be finite positive')
    if float(denom) != float(cfg['laser']['calculation_power_W']) or float(denom) != 1.0:
        errors.append('fixed calculation denominator must remain 1.0 W')
    c = cfg['fiber']['cutoff_nm']
    if (c['center'], c['half_range']) != (930, 40):
        errors.append('fiber cutoff must remain the U2 930±40 envelope')
    if cfg['fiber']['operating_nm'] != 'greater_than_980':
        errors.append('fiber operating_nm must remain greater_than_980')
    fa = cfg['assumptions']['fast_fwhm_deg']
    if float(fa['value']) != 30 or fa['grade'] != 'A':
        errors.append('fast axis 30 deg must stay an explicit grade-A assumption')
    head = cfg['head_design_v3']
    for key in ('wedge_half_angle_deg', 'tip_radius_um', 'axial_gap_um'):
        if head[key].get('grade') != 'L980_INIT':
            errors.append(f'head {key} must carry provenance grade L980_INIT')
    if cfg['two_lens_v2']['active']:
        errors.append('legacy two-lens configuration must stay inactive')
    return {'status': 'PASS' if not errors else 'FAIL', 'errors': errors}

def check_head(cfg: dict) -> dict:
    head = cfg['head_design_v3']
    alpha = float(head['wedge_half_angle_deg']['value'])
    R = float(head['tip_radius_um']['value'])*1e-6
    gap = float(head['axial_gap_um']['value'])*1e-6
    try:
        record = validate_head(alpha, R, gap)
    except ValueError as exc:
        return {'status': 'FAIL', 'errors': [str(exc)]}
    errors = []
    limits = head['limits']
    def in_limits(value, spec, name):
        lo = spec.get('exclusive_min'); hi = spec.get('exclusive_max')
        if lo is not None and not value > lo: errors.append(f'{name} below exclusive_min')
        if hi is not None and not value < hi: errors.append(f'{name} at/above exclusive_max')
    in_limits(alpha, limits['wedge_half_angle_deg'], 'wedge_half_angle_deg')
    in_limits(R*1e6, limits['tip_radius_um'], 'tip_radius_um')
    in_limits(gap*1e6, limits['axial_gap_um'], 'axial_gap_um')
    if record['value_continuity_abs_m'] > 1e-15*max(R, 1e-9) or record['slope_continuity_abs'] > 1e-12 or record['slope_finite_difference_gap'] > 1e-5:
        errors.append('arc/wedge tangent continuity violated')
    return ({'status': 'PASS' if not errors else 'FAIL', 'errors': errors, 'record': record}
            if not errors else {'status': 'FAIL', 'errors': errors, 'record': record})

def check_fiber(cfg: dict) -> dict:
    record = fiber_analytic_at(cfg['simulation']['wavelength_nm'], cfg['fiber'])
    return {'status': 'PASS', 'errors': [],
            'mode_risk': 'MODE_ANALYSIS_REQUIRED',
            'near_nominal_cutoff_estimate_flag': record['nominal_estimate_at_or_above_LP11_cutoff'],
            'record': record}

def check_source(cfg: dict) -> dict:
    wl_nm = float(cfg['simulation']['wavelength_nm'])
    wl_m = wl_nm*1e-9
    slow = float(cfg['laser']['slow_fwhm_deg']['typ'])
    fast = float(cfg['assumptions']['fast_fwhm_deg']['value'])
    pol = cfg['assumptions']['source_polarization']['value']
    src = fit_source(wl_m, slow_deg=slow, fast_deg=fast, polarization=pol)
    theta = np.deg2rad(np.linspace(-89, 89, 17801))
    errors = []
    measured_fwhm = {}
    for axis, target in (('x', slow), ('y', fast)):
        measured = float(np.rad2deg(fwhm(theta, src.angular_cut(theta, axis))))
        measured_fwhm[axis] = measured
        if abs(measured/target - 1) > 1e-5:
            errors.append(f'{axis}-axis fitted FWHM {measured:.6g} deg deviates from {target}')
    grid = GridSource(src, 256)
    periodic_flux = {}
    for z in (0.0, 5e-6):
        E, H = grid.plane(z)
        p = grid.power(E, H)
        periodic_flux[str(z)] = p
        if abs(p - 1) > 1e-9:
            errors.append(f'FFT-plane flux at z={z} deviates by {p-1:.3g}')
    record = src.to_math_record()
    record['raw_power_W'] = grid.raw_power
    record['fitted_fwhm_deg'] = measured_fwhm
    record['target_fwhm_deg'] = {'x': slow, 'y': fast}
    record['periodic_grid_flux_W'] = periodic_flux
    record['periodic_grid_flux_scope'] = (
        'Full-period FFT flux conservation is a discrete Parseval identity; '
        'it does not establish finite-window capture or physical convergence.')
    return {'status': 'PASS' if not errors else 'FAIL', 'errors': errors, 'record': record}

def check_gates(doc: dict) -> dict:
    errors = []
    gates = doc['gates']
    ids = [g['id'] for g in gates]
    if len(ids) != len(set(ids)):
        errors.append('duplicate gate ids')
    if set(ids) != set(V2_GATE_FROZEN):
        errors.append(f'gate id set changed: {sorted(set(ids) ^ set(V2_GATE_FROZEN))}')
    counts = {k: 0 for k in APPLICABILITY}
    for gate in gates:
        g = V2_GATE_FROZEN.get(gate['id'])
        if g is None:
            continue
        if (gate['operation'], float(gate['limit']), gate['stage_v2']) != g:
            errors.append(f"{gate['id']}: original operation/limit/stage_v2 must be preserved")
        app = gate.get('applicability')
        if app not in APPLICABILITY:
            errors.append(f"{gate['id']}: applicability must be one of {sorted(APPLICABILITY)}")
        else:
            counts[app] += 1
        reason = gate.get('reason')
        if not isinstance(reason, str) or not reason.strip():
            errors.append(f"{gate['id']}: classification requires a nonempty reason")
        if gate['id'] == 'G17' and app != 'applicable':
            errors.append('G17 controlled source-injection evidence must stay applicable in v3')
        if gate['id'] == 'G17' and gate.get('stage_v3') != 'S05':
            errors.append('G17 stage_v3 must be S05')
        if gate['id'] in ('G10', 'G11a', 'G11b'):
            if app != 'not_applicable':
                errors.append(f"{gate['id']} is not_applicable for single-domain v3 unless controlled segmentation is adopted")
            elif '受控分段' not in gate['reason']:
                errors.append(f"{gate['id']} reason must record the controlled-segmentation activation condition")
        if gate['id'] == 'G15' and 'LAT1' not in gate['reason']:
            errors.append('G15 reason must scope the two clean-recompute points (BASE and one legal LAT1 regression point)')
        if gate['id'] == 'G20':
            if gate['name'] == V2_GATE_NAMES['G20']:
                errors.append('G20 must be rewritten for the single-model deliverable')
            if '单模型' not in gate['name'] and '单一模型' not in gate['name']:
                errors.append('G20 v3 name must state the single-model artifact criterion')
        if gate['id'] == 'G18' and '首版' not in gate['name']:
            errors.append('G18 v3 name must scope the rebuild to the first-version case')
    statuses = {
        g['id']: {'deferred': 'DEFERRED', 'not_applicable': 'NOT_APPLICABLE'}
                 .get(g.get('applicability'), 'NOT_RUN')
        for g in gates
    }
    return {'status': 'PASS' if not errors else 'FAIL', 'errors': errors,
            'counts': counts, 'statuses': statuses}

def scan_for_forbidden_claims(obj, path='root') -> list:
    hits = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if FORBIDDEN_KEY.search(str(key)) and value not in (False, None, 'false'):
                hits.append(f'{path}.{key}')
            hits.extend(scan_for_forbidden_claims(value, f'{path}.{key}'))
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            hits.extend(scan_for_forbidden_claims(value, f'{path}[{i}]'))
    return hits

def run(root: Path) -> dict:
    cfg = json.loads((root/'configs/parameters.json').read_text(encoding='utf-8'))
    gates_doc = json.loads((root/'configs/gates.json').read_text(encoding='utf-8'))
    checks = {
        'input_sha256': check_inputs(root),
        'parameter_policy': check_parameters(cfg),
        'head_geometry_math': check_head(cfg),
        'fiber_analytic_974': check_fiber(cfg),
        'source_math_974': check_source(cfg),
        'gate_classification': check_gates(gates_doc),
    }
    overall = 'SOFTWARE_CHECKS_PASS' if all(c['status'] == 'PASS' for c in checks.values()) else 'SOFTWARE_CHECKS_FAIL'
    result = {
        'record_type': 'PREFLIGHT_V3',
        'case_id': cfg['simulation'].get('case_id'),
        'overall_status': overall,
        'comsol_executed': False,
        'comsol_status': 'NOT_EXECUTED_BY_PREFLIGHT',
        'model_artifact': 'NOT_IMPLEMENTED_IN_THIS_STAGE',
        'claims_not_made': [
            'no COMSOL model was created, opened, or solved',
            'geometry and fiber records are math prechecks, not COMSOL state',
            'applicable gates remain NOT_RUN; deferred and inapplicable gates are classified separately',
        ],
        'config_file_sha256': {
            'configs/parameters.json': sha256_file(root/'configs/parameters.json'),
            'configs/gates.json': sha256_file(root/'configs/gates.json'),
        },
        'checks': checks,
    }
    forbidden = scan_for_forbidden_claims(result)
    if forbidden:
        raise RuntimeError(f'preflight output would claim: {forbidden}')
    if result['comsol_executed'] is not False:
        raise RuntimeError('preflight must assert comsol_executed=false')
    return result
