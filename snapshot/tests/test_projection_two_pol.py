import unittest
import numpy as np

from validation.field_projection import project, flux
from src.source.angular_spectrum import Z0

def _plane_gaussian_modes():
    xs = np.linspace(-14e-6, 14e-6, 48)
    X, Y = np.meshgrid(xs, xs, indexing='ij')
    w = 2.1e-6
    g = np.exp(-((X*X + Y*Y)/w/w)).ravel().astype(complex)
    zero = np.zeros_like(g)
    dx = xs[1]-xs[0]
    weights = np.full(g.size, dx*dx, dtype=float)
    normal = np.array([0.0, 0.0, 1.0])
    E_x = np.stack([g, zero, zero], axis=-1)
    H_x = np.stack([zero, g/Z0, zero], axis=-1)
    E_y = np.stack([zero, g, zero], axis=-1)
    H_y = np.stack([-g/Z0, zero, zero], axis=-1)
    return (E_x, H_x, E_y, H_y, weights, normal)

class ProjectionPolarizationTests(unittest.TestCase):
    def setUp(self):
        (self.Ex, self.Hx, self.Ey, self.Hy, self.w, self.n) = _plane_gaussian_modes()

    def test_two_polarization_projection_is_additive_no_double_count(self):
        E = 0.7*self.Ex + 0.3*self.Ey
        H = 0.7*self.Hx + 0.3*self.Hy
        both = project(E, H, np.stack([self.Ex, self.Ey]),
                       np.stack([self.Hx, self.Hy]), self.w, self.n)
        px = project(E, H, self.Ex, self.Hx, self.w, self.n)
        py = project(E, H, self.Ey, self.Hy, self.w, self.n)
        scale = max(abs(both['target_power_W']), 1e-300)
        self.assertLess(abs(both['target_power_W'] - (px['target_power_W'] + py['target_power_W'])),
                        1e-9*scale)
        self.assertLess(abs(both['net_field_flux_W'] - both['target_power_W']), 1e-9*scale)
        gram = np.array(both['gram_W_real'])
        self.assertLess(abs(gram[0, 1])/gram[0, 0], 1e-12)
        self.assertLess(both['gram_condition'], 10.0)

    def test_orthogonal_polarization_couples_nothing(self):
        res = project(self.Ex, self.Hx, self.Ey, self.Hy, self.w, self.n)
        self.assertAlmostEqual(res['target_power_W'], 0.0, places=30)
        p_x = flux(self.Ex, self.Hx, self.w, self.n)
        self.assertGreater(p_x, 0)

    def test_duplicated_modes_rejected(self):
        E = self.Ex + self.Ey
        H = self.Hx + self.Hy
        with self.assertRaisesRegex(ValueError, 'duplicated'):
            project(E, H, np.stack([self.Ex, self.Ex]),
                    np.stack([self.Hx, self.Hx]), self.w, self.n)

    def test_full_mode_matched_projection_recovers_flux(self):
        res = project(self.Ex, self.Hx, self.Ex, self.Hx, self.w, self.n)
        direct = flux(self.Ex, self.Hx, self.w, self.n)
        self.assertLess(abs(res['target_power_W'] - direct)/direct, 1e-12)

if __name__ == '__main__':
    unittest.main()
