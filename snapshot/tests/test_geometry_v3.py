import math
import unittest
import numpy as np

from validation.geometry_v3 import validate_head, profile_f, tangent_point

class GeometryMathTests(unittest.TestCase):
    def test_baseline_head_record(self):
        rec = validate_head(45.0, 3.25e-6, 5.65e-6)
        self.assertEqual(rec['record_type'], 'GEOMETRY_PARAMETER_MATH_PRECHECK')
        self.assertIs(rec['comsol_executed'], False)
        R = 3.25e-6
        y_t, z_t = tangent_point(45.0, R)
        self.assertAlmostEqual(y_t, R*math.cos(math.radians(45)), places=18)
        self.assertAlmostEqual(z_t, R*(1-math.sin(math.radians(45))), places=18)
        self.assertLess(rec['value_continuity_abs_m'], 1e-18)
        self.assertLess(rec['slope_continuity_abs'], 1e-12)
        self.assertLess(rec['slope_finite_difference_gap'], 1e-5)
        self.assertAlmostEqual(rec['slope_wedge'], 1.0, places=12)

    def test_profile_formula_values(self):
        a, R = 45.0, 3.25e-6
        y_t, z_t = tangent_point(a, R)
        self.assertAlmostEqual(profile_f(0.0, a, R), 0.0, places=18)
        self.assertAlmostEqual(profile_f(y_t, a, R), z_t, places=18)
        self.assertAlmostEqual(profile_f(-y_t, a, R), z_t, places=18)
        slope = (profile_f(2*y_t, a, R) - profile_f(y_t, a, R))/y_t
        self.assertAlmostEqual(slope, 1.0, places=9)

    def test_illegal_half_angle_rejected(self):
        for alpha in (0.0, 90.0, 91.0, -45.0, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                validate_head(alpha, 3.25e-6, 5.65e-6)

    def test_illegal_radius_rejected(self):
        for radius in (0.0, -3.25e-6, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                validate_head(45.0, radius, 5.65e-6)

    def test_illegal_gap_rejected(self):
        for gap in (0.0, -5.65e-6, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                validate_head(45.0, 3.25e-6, gap)

    def test_profile_even_and_monotone(self):
        ys = np.linspace(0.0, 9e-6, 200)
        fs = profile_f(ys, 45.0, 3.25e-6)
        self.assertTrue(np.all(np.diff(fs) >= 0))
        np.testing.assert_allclose(profile_f(-ys, 45.0, 3.25e-6), fs)

    def test_profile_rejects_nonfinite_samples(self):
        with self.assertRaises(ValueError):
            profile_f([1e-6, float('nan')], 45.0, 3.25e-6)

if __name__ == '__main__':
    unittest.main()
