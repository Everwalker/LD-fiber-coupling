import copy
import dataclasses
import json
import unittest
from pathlib import Path

from validation.preflight_v3 import check_parameters, V2_LASER_CENTER
from src.source.angular_spectrum import Source, fit_source

ROOT = Path(__file__).resolve().parents[1]

class WavelengthPolicyTests(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads((ROOT/'configs/parameters.json').read_text(encoding='utf-8'))

    def test_frozen_center_and_974_baseline(self):
        self.assertEqual({k: self.cfg['laser']['center_nm'][k] for k in ('min', 'typ', 'max')},
                         V2_LASER_CENTER)
        self.assertEqual(self.cfg['simulation']['wavelength_nm'], 974)
        self.assertEqual(self.cfg['simulation']['case_id'], 'LD974-WEDGE-BASE-001')
        self.assertEqual(check_parameters(self.cfg)['errors'], [])

    def test_baseline_case_id_is_frozen(self):
        cfg = copy.deepcopy(self.cfg)
        cfg['simulation']['case_id'] = 'another-case'
        self.assertIn('the frozen v3 baseline case_id must be LD974-WEDGE-BASE-001',
                      check_parameters(cfg)['errors'])

    def test_974_is_outside_frozen_source_band(self):
        band = self.cfg['laser']['center_nm']
        self.assertFalse(band['min'] <= 974 <= band['max'])
        self.assertNotEqual(974, band['typ'])

    def test_alternative_wavelengths_need_new_case_and_adr(self):
        for wavelength in (967, 970, 973, 980, 2000, 2100):
            with self.subTest(wavelength=wavelength):
                cfg = copy.deepcopy(self.cfg)
                cfg['simulation']['wavelength_nm'] = wavelength
                errors = check_parameters(cfg)['errors']
                self.assertEqual(errors, [
                    'the frozen v3 baseline must be 974 nm; a different wavelength requires a new case and ADR'
                ])

    def test_invalid_baseline_wavelength_rejected(self):
        for wavelength in (0, -1, float('nan'), float('inf'), True):
            with self.subTest(wavelength=wavelength):
                cfg = copy.deepcopy(self.cfg)
                cfg['simulation']['wavelength_nm'] = wavelength
                self.assertIn('simulation.wavelength_nm must be finite positive nm',
                              check_parameters(cfg)['errors'])

    def test_974_as_laser_center_is_rejected(self):
        cfg = copy.deepcopy(self.cfg)
        cfg['laser']['center_nm']['typ'] = 974
        errors = check_parameters(cfg)['errors']
        self.assertTrue(any('center_nm' in e for e in errors), errors)

    def test_denominator_and_cutoff_mutations_rejected(self):
        cfg = copy.deepcopy(self.cfg)
        cfg['simulation']['denominator_W']['value'] = 0.5
        self.assertTrue(any('denominator' in e for e in check_parameters(cfg)['errors']))
        cfg = copy.deepcopy(self.cfg)
        cfg['fiber']['cutoff_nm']['half_range'] = 50
        self.assertTrue(any('cutoff' in e for e in check_parameters(cfg)['errors']))

    def test_source_has_no_implicit_970_default(self):
        with self.assertRaises(TypeError):
            Source()
        with self.assertRaises(TypeError):
            Source(wavelength_m=974e-9)
        with self.assertRaises(TypeError):
            Source(wavelength_m=974e-9, wx_m=3e-6)
        with self.assertRaises(TypeError):
            fit_source()
        for name in ('wavelength_m', 'wx_m', 'wy_m'):
            field = next(f for f in dataclasses.fields(Source) if f.name == name)
            self.assertIs(field.default, dataclasses.MISSING)

    def test_explicit_wavelengths_work_in_source_independently_of_baseline(self):
        for wavelength in (970e-9, 2100e-9):
            with self.subTest(wavelength=wavelength):
                source = Source(wavelength_m=wavelength, wx_m=3e-6, wy_m=0.7e-6)
                self.assertEqual(source.wavelength_m, wavelength)
                fitted = fit_source(wavelength)
                self.assertEqual(fitted.wavelength_m, wavelength)

if __name__ == '__main__':
    unittest.main()
