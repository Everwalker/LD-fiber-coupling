import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from validation.gate_evidence import verify_pass_evidence

try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / 'schemas/gate_result.schema.json').read_text(encoding='utf-8'))


class GateSchemaShapeTests(unittest.TestCase):
    def test_schema_defines_status_and_conditional_requirements(self):
        self.assertTrue({'NOT_RUN', 'NOT_APPLICABLE', 'DEFERRED', 'PASS'} <=
                        set(SCHEMA['properties']['status']['enum']))
        rules = SCHEMA['allOf']
        unresolved = next(r['then'] for r in rules
                          if set(r['if']['properties']['status'].get('enum', [])) ==
                          {'NOT_RUN', 'NOT_APPLICABLE', 'DEFERRED'})
        self.assertIn('reason', unresolved['required'])
        self.assertEqual(unresolved['properties']['value']['type'], 'null')
        passed = next(r['then'] for r in rules
                      if r['if']['properties']['status'].get('const') == 'PASS')
        self.assertEqual(passed['properties']['evidence_ids']['minItems'], 1)

    def test_case_template_keeps_unknowns_and_statuses_explicit(self):
        case = json.loads((ROOT / 'templates/case.template.json').read_text(encoding='utf-8'))
        for key in ('input_sha256', 'code_sha256', 'model_sha256', 'comsol_build',
                    'started_at_utc', 'finished_at_utc', 'mcp_call_log_artifact_id'):
            with self.subTest(field=key):
                self.assertIsNone(case[key])
                self.assertTrue(case['unknown_reasons'][key].strip())
        for key in ('independent_review', 'sync'):
            self.assertEqual(case[key]['status'], 'NOT_RUN')
            self.assertTrue(case[key]['reason'].strip())
        artifact_schema = json.loads((ROOT / 'schemas/artifact.schema.json').read_text(encoding='utf-8'))
        self.assertIn('mcp_call_log', artifact_schema['properties']['role']['enum'])


@unittest.skipUnless(Draft202012Validator is not None, 'optional jsonschema validator is not installed')
class GateSchemaBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Draft202012Validator.check_schema(SCHEMA)
        cls.validator = Draft202012Validator(SCHEMA)

    def test_unresolved_states_require_null_value_and_nonblank_reason(self):
        for status in ('NOT_RUN', 'NOT_APPLICABLE', 'DEFERRED'):
            with self.subTest(status=status):
                result = {'id': 'G10', 'status': status, 'value': None,
                          'evidence_ids': [], 'reason': 'No applicable result'}
                self.assertTrue(self.validator.is_valid(result))
                for invalid_value in (0, False, 1.2):
                    invalid = dict(result, value=invalid_value)
                    self.assertFalse(self.validator.is_valid(invalid), invalid)
                for reason in ('', '  ', None):
                    invalid = dict(result, reason=reason)
                    self.assertFalse(self.validator.is_valid(invalid), invalid)
                invalid = dict(result)
                del invalid['reason']
                self.assertFalse(self.validator.is_valid(invalid))

    def test_pass_requires_value_and_nonblank_evidence_id(self):
        result = {'id': 'G01', 'status': 'PASS', 'value': True,
                  'evidence_ids': ['input-hash-record']}
        self.assertTrue(self.validator.is_valid(result))
        for ids in ([], [''], ['   ']):
            self.assertFalse(self.validator.is_valid(dict(result, evidence_ids=ids)))
        self.assertFalse(self.validator.is_valid(dict(result, value=None)))


class GateEvidenceTests(unittest.TestCase):
    def test_pass_evidence_resolves_and_checks_actual_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'evidence.txt'
            path.write_bytes(b'actual evidence')
            artifact = {
                'id': 'e1', 'path': 'evidence.txt', 'size_bytes': path.stat().st_size,
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            gate = {'status': 'PASS', 'evidence_ids': ['e1']}
            self.assertEqual(verify_pass_evidence(gate, {'e1': artifact}, root), ['e1'])
            with self.assertRaisesRegex(ValueError, 'matching artifact'):
                verify_pass_evidence(gate, {}, root)
            with self.assertRaisesRegex(ValueError, 'nonblank evidence'):
                verify_pass_evidence({'status': 'PASS', 'evidence_ids': []}, {}, root)
            bad = copy.deepcopy(artifact)
            bad['sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                verify_pass_evidence(gate, {'e1': bad}, root)
            path.unlink()
            with self.assertRaisesRegex(ValueError, 'missing'):
                verify_pass_evidence(gate, {'e1': artifact}, root)


if __name__ == '__main__':
    unittest.main()
