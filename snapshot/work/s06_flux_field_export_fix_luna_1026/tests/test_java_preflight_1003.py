import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
CLASSES = ROOT / "compile" / "classes"
JAVA = Path(r"X:\JDK_ROOT\bin\java.exe")
JAVAC = Path(r"X:\JDK_ROOT\bin\javac.exe")
MODEL_JAR = Path(r"X:\COMSOL_ROOT\plugins\com.comsol.model_1.0.0.jar")
API_JAR = Path(r"X:\COMSOL_ROOT\plugins\com.comsol.api_1.0.0.jar")
SOURCE = ROOT / "src" / "S06FluxExport1003.java"
BINDER = ROOT / "tools" / "bind_job_1003.py"
MEMBERSHIP_TEST = ROOT / "tests" / "S06FluxExportMembershipSelfTest.java"
SPEC = importlib.util.spec_from_file_location("bind_job_1003", BINDER)
bind_job_1003 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bind_job_1003)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_properties(path, values):
    Path(path).write_text(
        "".join(f"{key}={value}\n" for key, value in sorted(values.items())),
        encoding="ascii",
    )


def read_properties(path):
    return dict(line.split("=", 1) for line in Path(path).read_text(encoding="ascii").splitlines())


class JavaPreflightTests(unittest.TestCase):
    def setUp(self):
        if not JAVA.is_file() or not JAVAC.is_file() or not all(p.is_file() for p in (MODEL_JAR, API_JAR)):
            self.skipTest("JDK 21 or local COMSOL 6.4 compile-time API JAR is unavailable")
        if not (CLASSES / "S06FluxExport1003.class").is_file():
            self.skipTest("offline-compiled bridge class is not present")
        self.temp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.workspace = self.base / "workspace"
        self.workspace.mkdir()

    def _make_job(self, job_id, artifact_bytes, audit_name, input_sha=""):
        job_dir = self.workspace / job_id
        job_dir.mkdir()
        artifact_rel = "solved-copy.mph"
        artifact = job_dir / artifact_rel
        artifact.write_bytes(artifact_bytes)
        record = {
            "job_id": job_id,
            "status": "PROCESS_FINISHED_NEEDS_EXTERNAL_ARTIFACT_REVIEW",
            "output_relative_path": artifact_rel,
            "input_model_sha256_before": input_sha,
            "input_model_path": "upstream artifact",
        }
        (job_dir / "job.json").write_text(json.dumps(record), encoding="utf-8")
        audit = self.base / audit_name
        audit.write_text(json.dumps({
            "artifact_audit_pass": True,
            "model_result": "NOT_ESTABLISHED",
            "job_id": job_id,
            "output_artifact": {
                "path": artifact_rel,
                "sha256": digest(artifact),
            },
        }), encoding="utf-8")
        binding = self.base / (job_id + ".properties")
        bind_job_1003.bind_job(job_dir, audit, binding, job_id)
        return job_dir, artifact, binding

    def _invoke_preflight(self, job_binding, model_binding):
        classpath = os.pathsep.join((str(CLASSES), str(MODEL_JAR), str(API_JAR)))
        env = os.environ.copy()
        env["S06_FLUX_EXPORT_JOB_BINDING"] = str(job_binding)
        env["S06_FLUX_EXPORT_MODEL_BINDING"] = str(model_binding)
        return subprocess.run(
            [str(JAVA), "-cp", classpath, "S06FluxExport1003", "--preflight-only"],
            cwd=WORKSPACE,
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )

    def _make_model_binding(self):
        upstream_id = "source_957_20261117T120000Z_a1739b20"
        current_id = "drive_1003_20261117T130000Z_f6250d12"
        upstream_dir, upstream_artifact, upstream_binding = self._make_job(
            upstream_id, b"synthetic upstream artifact", "upstream-audit.json"
        )
        current_dir, current_artifact, current_binding = self._make_job(
            current_id, b"synthetic current artifact", "current-audit.json", digest(upstream_artifact)
        )
        evidence = self.base / "evidence.txt"
        evidence.write_text("synthetic evidence for offline binding tests\n", encoding="ascii")
        review = self.base / "review.json"
        review.write_text(json.dumps({"review": "synthetic offline preflight fixture"}), encoding="utf-8")
        release = self.base / "release.properties"
        release_values = {
            "status": "PASS",
            "review.author_id": "synthetic-author",
            "review.reviewer_id": "synthetic-non-author",
            "review.path": review.as_posix(),
            "review.sha256": digest(review),
            "review.source_sha256": digest(SOURCE),
            "review.binder_sha256": digest(BINDER),
            "review.class_sha256": digest(CLASSES / "S06FluxExport1003.class"),
            "review.binding_class_sha256": digest(CLASSES / "S06FluxExport1003$Binding.class"),
            "review.sample_class_sha256": digest(CLASSES / "S06FluxExport1003$Sample.class"),
        }
        gates = ("S04", "S05", "G03a", "G03b", "G17", "source_direction", "resources", "comsol64", "wave_optics")
        for gate in gates:
            release_values[f"gate.{gate}.status"] = "PASS"
            release_values[f"gate.{gate}.evidence_path"] = evidence.as_posix()
            release_values[f"gate.{gate}.evidence_sha256"] = digest(evidence)
        write_properties(release, release_values)

        grid = self.base / "field_grid.tsv"
        grid.write_text("x_m\ty_m\tz_m\tweight_m2\n0\t0\t0\t\n", encoding="ascii")
        model = self.base / "model.properties"
        model_values = {
            "upstream_job_binding_path": upstream_binding.as_posix(),
            "upstream_job_binding_sha256": digest(upstream_binding),
            "upstream_source_job_id": upstream_id,
            "upstream_source_model_sha256": digest(upstream_artifact),
            "case_id": "LD974-WEDGE-BASE-001",
            "lambda_m": "9.74E-7",
            "model_sha256": digest(current_artifact),
            "component_tag": "device3d",
            "geometry_tag": "gdev",
            "physics_tag": "ewfd",
            "study_tag": "synthetic_study",
            "solution_tag": "synthetic_solution",
            "dataset_tag": "synthetic_dataset",
            "solution_index": "1",
            "geometry_tolerance_m": "1E-12",
            "field_grid_path": grid.as_posix(),
            "field_grid_sha256": digest(grid),
            "source_field_sha256": "null",
            "source_field_sha256_reason": "synthetic test fixture leaves source field unknown",
            "partition_evidence_path": "null",
            "partition_evidence_sha256": "null",
            "partition_evidence_sha256_reason": "synthetic fixture has no physical partition evidence",
            "release_record_path": release.as_posix(),
            "release_record_sha256": digest(release),
            "candidate_source_path": SOURCE.as_posix(),
            "candidate_source_sha256": digest(SOURCE),
            "candidate_binder_path": BINDER.as_posix(),
            "candidate_binder_sha256": digest(BINDER),
            "output_subdir": "s06_flux_export_1003",
        }
        for name in ("dx_tip", "gap_tip", "R_tip", "alpha_tip", "lambdaD", "zSrcRef"):
            model_values[f"parameter.{name}.expected"] = "synthetic-exact-readback"
        write_properties(model, model_values)
        return current_binding, model, current_artifact

    def test_selected_face_membership_rejects_aabb_only_point(self):
        with tempfile.TemporaryDirectory() as temp:
            cp = os.pathsep.join((str(CLASSES), str(API_JAR), str(MODEL_JAR)))
            compile_result = subprocess.run(
                [str(JAVAC), "--release", "11", "-encoding", "UTF-8", "-proc:none",
                 "-classpath", cp, "-d", temp, str(MEMBERSHIP_TEST)],
                capture_output=True, text=True,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            run_cp = os.pathsep.join((temp, cp))
            result = subprocess.run(
                [str(JAVA), "-classpath", run_cp, "S06FluxExportMembershipSelfTest"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PASS_SYNTHETIC_GEOMETRY_ONLY", result.stdout)

    def test_offline_preflight_accepts_dynamic_job_and_exact_hash_chain(self):
        job, model, _ = self._make_model_binding()
        result = self._invoke_preflight(job, model)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("S06_1003_PREFLIGHT=PASS_BINDINGS_ONLY_NO_COMSOL", result.stdout)

    def test_offline_preflight_rejects_model_bytes_changed_after_binding(self):
        job, model, artifact = self._make_model_binding()
        artifact.write_bytes(b"changed after job binding")
        result = self._invoke_preflight(job, model)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("model artifact SHA-256 mismatch", result.stderr)

    def test_offline_preflight_hashes_known_source_and_partition_artifacts(self):
        job, model, _ = self._make_model_binding()
        values = read_properties(model)
        source = self.base / "synthetic_source_field.csv"
        source.write_text("synthetic field evidence; no COMSOL result\n", encoding="ascii")
        partition = self.base / "synthetic_partition_evidence.json"
        partition.write_text('{"synthetic":true,"physical_result":false}\n', encoding="ascii")
        values["source_field_path"] = source.as_posix()
        values["source_field_sha256"] = digest(source)
        values["partition_evidence_path"] = partition.as_posix()
        values["partition_evidence_sha256"] = digest(partition)
        write_properties(model, values)
        result = self._invoke_preflight(job, model)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_offline_preflight_rejects_release_record_as_partition_evidence(self):
        job, model, _ = self._make_model_binding()
        values = read_properties(model)
        values["partition_evidence_path"] = values["release_record_path"]
        values["partition_evidence_sha256"] = values["release_record_sha256"]
        write_properties(model, values)
        result = self._invoke_preflight(job, model)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not be the release record", result.stderr)


if __name__ == "__main__":
    unittest.main()
