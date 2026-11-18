import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class InputHashTests(unittest.TestCase):
    def test_manifest_items_hash_match(self):
        manifest = json.loads((ROOT/'inputs/manifest.json').read_text(encoding='utf-8'))
        ids = {item['id'] for item in manifest['items']}
        self.assertEqual(ids, {'U1', 'U2'})
        for item in manifest['items']:
            path = ROOT/item['path']
            self.assertTrue(path.is_file(), path)
            self.assertGreater(path.stat().st_size, 0)
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(actual, item['sha256'], item['id'])

if __name__ == '__main__':
    unittest.main()
