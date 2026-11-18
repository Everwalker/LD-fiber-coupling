"""Offline tests for the S03 candidate PWE representation.

Verify: spectral coefficients and normalization match the frozen reference
(src.source.angular_spectrum), E/H agree on two z planes (including units and the
H = khat x E / Z0 relation), the representation is spatially differentiable
(analytic derivatives vs central differences), export/import round-trips without
pickle, and window powers are reported without renormalization.

No COMSOL is used; G03a/G03b/G17 are NOT exercised here.
"""
import pathlib

import tempfile
import unittest

import numpy as np

from src.source.plane_wave_source import PlaneWaveSourceField
from src.source.angular_spectrum import GridSource, Z0, fit_source

WL_M = 974e-9
SIZE = 64
STEP_M = .25e-6


class PlaneWaveSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = fit_source(WL_M, slow_deg=6.0, fast_deg=30.0, polarization="x")
        cls.ref = GridSource(cls.src, SIZE, STEP_M)
        cls.pw = PlaneWaveSourceField.from_source(cls.src, SIZE, STEP_M)

    def test_spectral_coefficients_match_reference_bitwise(self):
        full_e = np.zeros((SIZE, SIZE, 3), complex)
        full_h = np.zeros((SIZE, SIZE, 3), complex)
        q = 2 * np.pi * np.fft.fftfreq(SIZE, STEP_M)
        qx, qy = np.meshgrid(q, q, indexing="ij")
        idx = np.argwhere(qx * qx + qy * qy < self.src.k ** 2)
        for j, (a, b) in enumerate(idx):
            full_e[a, b] = self.pw.E_spectral[j]
            full_h[a, b] = self.pw.H_spectral[j]
        mask = qx * qx + qy * qy >= self.src.k ** 2
        self.assertEqual(self.pw.qx.size, int((~mask).sum()))
        np.testing.assert_array_equal(full_e[mask], 0)
        np.testing.assert_array_equal(full_e, self.ref.E)
        np.testing.assert_array_equal(full_h, self.ref.H)

    def test_normalization_is_the_single_reference_factor(self):
        self.assertAlmostEqual(self.pw.raw_power_W, self.ref.raw_power, places=9)
        self.assertEqual(self.pw.factor, self.ref.factor)
        self.assertAlmostEqual(self.pw.power_forward_spectral(), 1.0, places=12)

    def test_fields_match_reference_on_two_planes(self):
        for z in (0.0, 5e-6):
            ref_e, ref_h = self.ref.plane(z)
            pw_e, pw_h = self.pw.evaluate(*np.meshgrid(self.ref.axis, self.ref.axis, indexing="ij"), z)
            scale_e = max(np.max(np.abs(ref_e)), 1e-30)
            scale_h = max(np.max(np.abs(ref_h)), 1e-30)
            self.assertLess(np.max(np.abs(pw_e - ref_e)) / scale_e, 1e-12)
            self.assertLess(np.max(np.abs(pw_h - ref_h)) / scale_h, 1e-12)

    def test_per_wave_units_transversality_and_forward_flux(self):
        khat = np.stack((self.pw.qx / self.pw.k, self.pw.qy / self.pw.k, self.pw.kz / self.pw.k), axis=-1)
        e_abs = np.linalg.norm(self.pw.E_spectral, axis=-1)
        h_abs = np.linalg.norm(self.pw.H_spectral, axis=-1)
        np.testing.assert_allclose(h_abs, e_abs / (Z0 / self.pw.n), rtol=1e-12)
        dot = np.abs(np.sum(self.pw.E_spectral * khat, axis=-1))
        np.testing.assert_allclose(dot, 0, atol=1e-15 * np.max(e_abs))
        sz = 0.5 * np.real(np.cross(self.pw.E_spectral, self.pw.H_spectral.conj())[..., 2])
        self.assertGreater(np.min(sz), 0.0)

    def test_analytic_derivatives_match_central_differences(self):
        rng = np.random.default_rng(7)
        x, y, z = (rng.normal(0, 2e-6, 12), rng.normal(0, 2e-6, 12), rng.normal(2e-6, 1e-6, 12))
        h = 2e-10
        for axis in range(3):
            d = [0, 0, 0]
            d[axis] = 1
            off = np.zeros(3)
            off[axis] = h
            e_plus, _ = self.pw.evaluate(x + off[0], y + off[1], z + off[2])
            e_minus, _ = self.pw.evaluate(x - off[0], y - off[1], z - off[2])
            numeric = (e_plus - e_minus) / (2 * h)
            analytic, _ = self.pw.evaluate(x, y, z, *d)
            rel = np.max(np.abs(numeric - analytic)) / np.max(np.abs(analytic))
            self.assertLess(rel, 1e-5)
        e_xx, _ = self.pw.evaluate(x, y, z, 2, 0, 0)
        e_p, _ = self.pw.evaluate(x + h, y, z)
        e_0, _ = self.pw.evaluate(x, y, z)
        e_m, _ = self.pw.evaluate(x - h, y, z)
        numeric2 = (e_p - 2 * e_0 + e_m) / h ** 2
        self.assertLess(np.max(np.abs(numeric2 - e_xx)) / np.max(np.abs(e_xx)), 1e-4)

    def test_two_plane_power_lossless_consistency(self):
        p0 = self.pw.plane_power(0.0)
        p1 = self.pw.plane_power(5e-6)
        self.assertLess(abs(p0 - p1), 0.005)

    def test_window_capture_reported_without_renormalization(self):
        ref_full = self.ref.power(*self.ref.plane(0.0))
        self.assertAlmostEqual(self.pw.plane_power(0.0), ref_full, delta=1e-9)
        narrow = self.pw.plane_power(0.0, halfwidth_m=3e-6)
        self.assertLess(narrow, self.pw.plane_power(0.0))
        self.assertEqual(self.pw.factor, 1.0 / np.sqrt(self.pw.raw_power_W))

    def test_export_import_roundtrip_is_pickle_free(self):
        with tempfile.TemporaryDirectory() as td:
            stem = str(pathlib.Path(td) / "pw_source")
            npz, meta = self.pw.export(stem)
            with np.load(npz, allow_pickle=False) as data:
                self.assertEqual(sorted(data.files),
                                 ["E_spectral", "H_spectral", "kz", "qx", "qy"])
            pw2 = PlaneWaveSourceField.from_export(npz, meta)
            pts = (np.array([0.0, 1.5e-6, -2e-6]), np.array([0.0, -0.8e-6, 1.2e-6]),
                   np.array([0.0, 3e-6, -4e-6]))
            e1, h1 = self.pw.evaluate(*pts)
            e2, h2 = pw2.evaluate(*pts)
            np.testing.assert_array_equal(e1, e2)
            np.testing.assert_array_equal(h1, h2)
            import json
            with open(meta, encoding="utf-8") as fh:
                m = json.load(fh)
            self.assertEqual(m["units"]["E"], "V/m")
            self.assertEqual(m["units"]["H"], "A/m")
            self.assertEqual(m["conventions"]["phasor"], "exp(+i*omega*t)")
            self.assertEqual(m["conventions"]["plane_wave_factor"],
                             "exp(-i*(qx*x + qy*y + kz*z))")
            self.assertEqual(m["normalization"]["target_forward_power_W"], 1.0)
            self.assertIs(m["comsol_executed"], False)
            self.assertIn("NOT_RUN", m["scope"])
            self.assertEqual(m["wavelength_m"], WL_M)

    def test_rejects_grid_without_propagating_disk(self):
        with self.assertRaises(ValueError):
            PlaneWaveSourceField.from_source(self.src, 16, 5e-6)


if __name__ == "__main__":
    unittest.main()
