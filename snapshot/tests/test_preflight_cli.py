import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from validation.preflight_v3 import run, scan_for_forbidden_claims

ROOT = Path(__file__).resolve().parents[1]

class PreflightEndToEndTests(unittest.TestCase):
    def test_full_run_passes_and_claims_nothing(self):
        result = run(ROOT)
        self.assertEqual(result['overall_status'], 'SOFTWARE_CHECKS_PASS')
        self.assertEqual(result['case_id'], 'LD974-WEDGE-BASE-001')
        self.assertNotIn('job_id', result)
        self.assertIs(result['comsol_executed'], False)
        self.assertEqual(result['model_artifact'], 'NOT_IMPLEMENTED_IN_THIS_STAGE')
        for name, check in result['checks'].items():
            self.assertEqual(check['status'], 'PASS', name)
        self.assertEqual(result['checks']['gate_classification']['statuses'].get('G16'), 'NOT_RUN')
        self.assertEqual(result['checks']['gate_classification']['statuses'].get('G07b'), 'DEFERRED')
        self.assertEqual(result['checks']['gate_classification']['statuses'].get('G10'), 'NOT_APPLICABLE')
        self.assertEqual(result['checks']['gate_classification']['counts']['deferred'], 5)
        self.assertEqual(result['checks']['gate_classification']['counts']['not_applicable'], 3)
        self.assertEqual(result['checks']['gate_classification']['counts']['conditional'], 0)
        self.assertEqual(result['checks']['gate_classification']['counts']['applicable'], 20)
        self.assertEqual(scan_for_forbidden_claims(result), [])
        rec = result['checks']['source_math_974']['record']
        self.assertAlmostEqual(rec['wavelength_m'], 974e-9, delta=1e-20)
        self.assertIs(rec['comsol_executed'], False)
        self.assertEqual(rec['target_fwhm_deg'], {'x': 6.0, 'y': 30.0})
        self.assertIn('discrete Parseval identity', rec['periodic_grid_flux_scope'])
        fiber = result['checks']['fiber_analytic_974']
        self.assertEqual(fiber['mode_risk'], 'MODE_ANALYSIS_REQUIRED')
        self.assertIsNone(fiber['record']['mfd_estimate_um'])

    def test_cli_exit_zero_on_pass(self):
        proc = subprocess.run([sys.executable, '-m', 'tools.preflight'], cwd=ROOT,
                              capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(proc.returncode, 0, proc.stderr[-800:])
        payload = json.loads(proc.stdout)
        self.assertEqual(payload['overall_status'], 'SOFTWARE_CHECKS_PASS')
        self.assertEqual(payload['case_id'], 'LD974-WEDGE-BASE-001')
        self.assertNotIn('job_id', payload)

    def test_cli_exit_one_on_policy_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT/'configs', root/'configs')
            shutil.copytree(ROOT/'inputs', root/'inputs')
            cfg_path = root/'configs/parameters.json'
            cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
            cfg['simulation']['wavelength_nm'] = 970
            cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding='utf-8')
            result = run(root)
            self.assertEqual(result['overall_status'], 'SOFTWARE_CHECKS_FAIL')
            self.assertEqual(result['checks']['parameter_policy']['status'], 'FAIL')
            self.assertIn('a different wavelength requires a new case and ADR',
                          result['checks']['parameter_policy']['errors'][0])
            proc = subprocess.run([sys.executable, '-m', 'tools.preflight', '--root', str(root)],
                                  cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(proc.returncode, 1)

    def test_cli_save_source_is_math_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'source_math_974.json'
            proc = subprocess.run([sys.executable, '-m', 'tools.preflight',
                                   '--save-source', str(out)], cwd=ROOT,
                                  capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(proc.returncode, 0)
            rec = json.loads(out.read_text(encoding='utf-8'))
            self.assertEqual(rec['record_type'], 'MATHEMATICAL_SOURCE')
            self.assertAlmostEqual(rec['wavelength_m'], 974e-9, delta=1e-20)
            self.assertIs(rec['comsol_executed'], False)

if __name__ == '__main__':
    unittest.main()
