import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "bind_job_1003.py"
SPEC = importlib.util.spec_from_file_location("bind_job_1003", MODULE_PATH)
bind_job_1003 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bind_job_1003)


class JobBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.job_id = "source_940_957_20261117T120000Z_9a17e602"
        self.job_dir = self.base / self.job_id
        self.job_dir.mkdir()
        self.artifact_rel = "ldfiber_s06_source_425_940.mph"
        self.artifact = self.job_dir / self.artifact_rel
        self.artifact.write_bytes(b"synthetic fixture; not a COMSOL model")
        self.artifact_sha = hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        self.job_record = {
            "job_id": self.job_id,
            "status": "PROCESS_FINISHED_NEEDS_EXTERNAL_ARTIFACT_REVIEW",
            "output_relative_path": self.artifact_rel,
            "returncode": 0,
        }
        self.job_json = self.job_dir / "job.json"
        self.job_json.write_text(json.dumps(self.job_record), encoding="utf-8")
        self.audit_json = self.base / "artifact-audit.json"
        self.audit_json.write_text(json.dumps({
            "artifact_audit_pass": True,
            "model_result": "NOT_ESTABLISHED",
            "job_id": self.job_id,
            "output_artifact": {
                "path": self.artifact_rel,
                "sha256": self.artifact_sha,
            },
        }), encoding="utf-8")
        self.output = ROOT / "tests" / "generated-binding.properties"

    def tearDown(self):
        self.output.unlink(missing_ok=True)

    def test_binds_explicit_dynamic_job_and_artifact_hash(self):
        binding = bind_job_1003.bind_job(
            self.job_dir, self.audit_json, self.output, self.job_id
        )
        self.assertEqual(binding["job_id"], self.job_id)
        self.assertEqual(binding["artifact_path"], self.artifact.resolve().as_posix())
        self.assertEqual(binding["artifact_sha256"], self.artifact_sha)
        self.assertEqual(binding["artifact_audit_model_result"], "NOT_ESTABLISHED")
        self.assertEqual(binding["solution_established"], "false")

    def test_rejects_job_id_that_does_not_match_directory_and_record(self):
        with self.assertRaisesRegex(ValueError, "job_id"):
            bind_job_1003.bind_job(
                self.job_dir, self.audit_json, self.output, "job_940"
            )

    def test_rejects_artifact_hash_mismatch_in_audit(self):
        audit = json.loads(self.audit_json.read_text(encoding="utf-8"))
        audit["output_artifact"]["sha256"] = "0" * 64
        self.audit_json.write_text(json.dumps(audit), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            bind_job_1003.bind_job(
                self.job_dir, self.audit_json, self.output, self.job_id
            )

    def test_rejects_artifact_path_escape_from_job_directory(self):
        record = dict(self.job_record)
        record["output_relative_path"] = "..\\outside.mph"
        self.job_json.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "inside the job directory"):
            bind_job_1003.bind_job(
                self.job_dir, self.audit_json, self.output, self.job_id
            )


if __name__ == "__main__":
    unittest.main()
