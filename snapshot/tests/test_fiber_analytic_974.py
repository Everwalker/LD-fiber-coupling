import copy
import math
import unittest

from validation.fiber_analytic import fiber_analytic_at, malitson_n
from validation.preflight_v3 import check_fiber

FIBER = {'nominal_NA': 0.22, 'nominal_core_diameter_um': 3.4,
         'cutoff_nm': {'center': 930, 'half_range': 40}}

class FiberAnalyticTests(unittest.TestCase):
    def setUp(self):
        self.rec = fiber_analytic_at(974, FIBER)

    def test_recomputable_cutoff_matches_formula(self):
        expected = 2*math.pi*1.7e-6*0.22/2.404825557695773*1e9
        self.assertLess(abs(self.rec['cutoff_nm_weak_guidance_from_nominal_NA'] - expected), 1e-9)
        self.assertLess(abs(self.rec['cutoff_nm_weak_guidance_from_nominal_NA'] - 977.164974550909), 1e-6)

    def test_974_near_nominal_cutoff_flagged(self):
        self.assertGreater(self.rec['V_nominal'], 2.404825557695773)
        self.assertIs(self.rec['nominal_estimate_at_or_above_LP11_cutoff'], True)
        self.assertIs(self.rec['wavelength_above_reported_cutoff_upper_bound'], True)
        self.assertNotIn('single_mode_per_spec_cutoff_envelope', self.rec)
        self.assertIn('>980 nm', self.rec['interpretation'])
        self.assertIn('numerical mode analysis is required', self.rec['interpretation'])

    def test_mfd_requires_numerical_mode(self):
        self.assertIsNone(self.rec['mfd_estimate_um'])
        self.assertIn('numerical mode', self.rec['mfd_estimate_reason'])
        self.assertIn('974 nm', self.rec['mfd_estimate_reason'])
        self.assertFalse(any('marcuse' in key.lower() for key in self.rec))

    def test_at_and_below_reported_cutoff_are_risks_not_invalid_inputs(self):
        for wavelength in (970, 900):
            with self.subTest(wavelength=wavelength):
                rec = fiber_analytic_at(wavelength, FIBER)
                self.assertIs(rec['wavelength_above_reported_cutoff_upper_bound'], False)
                cfg = {'simulation': {'wavelength_nm': wavelength}, 'fiber': copy.deepcopy(FIBER)}
                result = check_fiber(cfg)
                self.assertEqual(result['status'], 'PASS')
                self.assertEqual(result['errors'], [])
                self.assertEqual(result['mode_risk'], 'MODE_ANALYSIS_REQUIRED')
                self.assertIn('numerical mode', result['record']['mfd_estimate_reason'])

    def test_record_is_analytic_not_comsol(self):
        self.assertEqual(self.rec['record_type'], 'FIBER_ANALYTIC_ESTIMATE')
        self.assertIs(self.rec['comsol_executed'], False)

    def test_malitson_known_value(self):
        self.assertLess(abs(malitson_n(970e-9) - 1.4508017923282956), 1e-12)
        with self.assertRaises(ValueError):
            malitson_n(10e-6)

if __name__ == '__main__':
    unittest.main()
