import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT.parent / "s06_power_ledger_luna_861" / "power_ledger.py"
SPEC = importlib.util.spec_from_file_location("power_ledger_861_contract", LEDGER)
power_ledger_861 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(power_ledger_861)


class Strict861NullContractTests(unittest.TestCase):
    def test_unknown_source_field_hash_with_reason_is_not_861_provenance(self):
        provenance = {
            "lambda_m": 974e-9,
            "model_sha256": "a" * 64,
            "config_sha256": "b" * 64,
            "source_field_sha256": None,
            "field_data_sha256": "c" * 64,
            "study_tag": "synthetic_study",
            "dataset_tag": "synthetic_dataset",
            "solution_index": 1,
        }
        with self.assertRaisesRegex(ValueError, "provenance.source_field_sha256 must be a SHA-256 hex digest"):
            power_ledger_861._provenance(provenance)

    def test_unknown_partition_artifact_hash_with_reason_is_not_861_evidence(self):
        evidence = {"artifact_sha256": None, "lambda_m": 974e-9,
                    "case_id": "LD974-WEDGE-BASE-001"}
        with self.assertRaisesRegex(ValueError, "partition_evidence.artifact_sha256 must be a SHA-256 hex digest"):
            power_ledger_861._evidence(evidence, "partition_evidence", evidence["case_id"])


if __name__ == "__main__":
    unittest.main()
