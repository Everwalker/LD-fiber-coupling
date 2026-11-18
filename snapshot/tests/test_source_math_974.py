import unittest
from dataclasses import replace
from unittest.mock import patch
import numpy as np

from src.source.angular_spectrum import fit_source, fwhm, GridSource
from validation.preflight_v3 import check_source

WL_M = 974e-9

class SourceMath974Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = fit_source(WL_M, slow_deg=6.0, fast_deg=30.0, polarization='x')

    def test_974_is_the_actual_computed_wavelength(self):
        self.assertEqual(self.src.wavelength_m, WL_M)
        theta = np.deg2rad(np.linspace(-70, 70, 14001))
        x_fwhm = np.rad2deg(fwhm(theta, self.src.angular_cut(theta, 'x')))
        y_fwhm = np.rad2deg(fwhm(theta, self.src.angular_cut(theta, 'y')))
        self.assertLess(abs(x_fwhm/6.0 - 1), 1e-4)
        self.assertLess(abs(y_fwhm/30.0 - 1), 1e-4)

    def test_waist_axis_ordering(self):
        self.assertLess(self.src.wy_m, self.src.wx_m)

    def test_offline_fast_axis_reference_widths(self):
        # These remain offline source tests, not additional COMSOL cases.
        theta = np.deg2rad(np.linspace(-70, 70, 14001))
        for fast_deg in (20.0, 40.0):
            with self.subTest(fast_deg=fast_deg):
                source = fit_source(WL_M, slow_deg=6.0, fast_deg=fast_deg, polarization='x')
                actual = np.rad2deg(fwhm(theta, source.angular_cut(theta, 'y')))
                self.assertLess(abs(actual / fast_deg - 1), 1e-4)

    def test_fft_plane_flux_conserved(self):
        grid = GridSource(self.src, 256)
        for z in (0.0, 5e-6):
            E, H = grid.plane(z)
            self.assertLess(abs(grid.power(E, H) - 1.0), 1e-9)

    def test_math_record_marked_not_comsol(self):
        rec = self.src.to_math_record()
        self.assertEqual(rec['record_type'], 'MATHEMATICAL_SOURCE')
        self.assertIs(rec['comsol_executed'], False)
        self.assertEqual(rec['wavelength_m'], WL_M)
        self.assertNotIn('model', rec)
        self.assertNotIn('job_id', rec)

    def test_preflight_records_measured_fwhm_separately_from_targets(self):
        # A small perturbation keeps the fit within tolerance but makes the
        # measured value observably different from the requested target.
        source = replace(self.src, wx_m=self.src.wx_m * 1.000001)
        cfg = {'simulation': {'wavelength_nm': 974},
               'laser': {'slow_fwhm_deg': {'typ': 6}},
               'assumptions': {'fast_fwhm_deg': {'value': 30},
                               'source_polarization': {'value': 'x'}}}
        with patch('validation.preflight_v3.fit_source', return_value=source):
            result = check_source(cfg)
        self.assertEqual(result['status'], 'PASS')
        rec = result['record']
        theta = np.deg2rad(np.linspace(-89, 89, 17801))
        actual_x = np.rad2deg(fwhm(theta, source.angular_cut(theta, 'x')))
        self.assertAlmostEqual(rec['fitted_fwhm_deg']['x'], actual_x, delta=1e-12)
        self.assertNotAlmostEqual(rec['fitted_fwhm_deg']['x'], 6.0, places=7)
        self.assertEqual(rec['target_fwhm_deg'], {'x': 6.0, 'y': 30.0})
        self.assertIn('discrete Parseval identity', rec['periodic_grid_flux_scope'])
        self.assertIn('does not establish finite-window capture', rec['periodic_grid_flux_scope'])

if __name__ == '__main__':
    unittest.main()
