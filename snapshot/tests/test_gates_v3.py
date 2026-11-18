import json
import unittest
from pathlib import Path

from validation.preflight_v3 import V2_GATE_FROZEN, V2_GATE_NAMES, check_gates

ROOT = Path(__file__).resolve().parents[1]

class GateClassificationTests(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads((ROOT/'configs/gates.json').read_text(encoding='utf-8'))
        self.gates = {g['id']: g for g in self.doc['gates']}

    def test_28_original_ids_preserved(self):
        self.assertEqual(len(self.doc['gates']), 28)
        self.assertEqual(set(self.gates), set(V2_GATE_FROZEN))

    def test_all_original_thresholds_preserved(self):
        for gate_id, gate in self.gates.items():
            op, limit, stage = V2_GATE_FROZEN[gate_id]
            self.assertEqual((gate['operation'], float(gate['limit']), gate['stage_v2']),
                             (op, limit, stage), gate_id)
            self.assertIs(gate['mandatory'], True)
        self.assertEqual(check_gates(self.doc)['errors'], [])

    def test_classification_sets(self):
        expected = {
            'not_applicable': {'G10', 'G11a', 'G11b'},
            'deferred': {'G07b', 'G12a', 'G12b', 'G13', 'G21'},
            'conditional': set(),
        }
        for kind, ids in expected.items():
            actual = {g for g, gate in self.gates.items() if gate['applicability'] == kind}
            self.assertEqual(actual, ids, kind)
        applicable = {g for g, gate in self.gates.items() if gate['applicability'] == 'applicable'}
        self.assertEqual(applicable, set(V2_GATE_FROZEN) - set().union(*expected.values()))

    def test_every_gate_has_nonempty_reason(self):
        for gate_id, gate in self.gates.items():
            self.assertTrue(gate['reason'].strip(), gate_id)

    def test_rewritten_gate_names(self):
        self.assertNotEqual(self.gates['G20']['name'], V2_GATE_NAMES['G20'])
        self.assertIn('模型', self.gates['G20']['name'])
        self.assertIn('可取回', self.gates['G20']['name'])
        self.assertIn('首版', self.gates['G18']['name'])
        self.assertEqual(self.gates['G17']['applicability'], 'applicable')
        self.assertEqual(self.gates['G17']['stage_v3'], 'S05')
        self.assertIn('平面', self.gates['G05a']['reason'])
        self.assertIn('不代表楔形透镜总反射', self.gates['G05a']['reason'])
        self.assertIn('受控分段', self.gates['G10']['reason'])
        self.assertIn('LAT1', self.gates['G15']['reason'])

    def test_classification_tampering_detected(self):
        doc = json.loads((ROOT/'configs/gates.json').read_text(encoding='utf-8'))
        doc['gates'][0]['limit'] = 0.5
        self.assertTrue(any('preserved' in e for e in check_gates(doc)['errors']))
        doc = json.loads((ROOT/'configs/gates.json').read_text(encoding='utf-8'))
        for gate in doc['gates']:
            if gate['id'] == 'G21':
                gate['applicability'] = 'waived'
        self.assertTrue(any('applicability' in e for e in check_gates(doc)['errors']))
        doc = json.loads((ROOT/'configs/gates.json').read_text(encoding='utf-8'))
        for gate in doc['gates']:
            if gate['id'] == 'G17':
                gate['stage_v3'] = 'S03'
        self.assertTrue(any('G17 stage_v3 must be S05' in e for e in check_gates(doc)['errors']))

if __name__ == '__main__':
    unittest.main()
