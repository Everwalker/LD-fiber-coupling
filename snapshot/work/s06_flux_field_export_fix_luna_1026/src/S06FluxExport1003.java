import com.comsol.model.Model;
import com.comsol.model.GeomSequence;
import com.comsol.model.util.ModelUtil;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Properties;
import java.util.regex.Pattern;

/** Read-only S06 export bound to one explicit solved-job artifact and solution. */
public final class S06FluxExport1003 {
  private static final String JOB_ENV = "S06_FLUX_EXPORT_JOB_BINDING";
  private static final String MODEL_ENV = "S06_FLUX_EXPORT_MODEL_BINDING";
  private static final String SHA256 = "[0-9a-fA-F]{64}";
  private static final String[] PARAMS = {"dx_tip", "gap_tip", "R_tip", "alpha_tip", "lambdaD", "zSrcRef"};
  private static final String[] FIELDS = {"Ex", "Ey", "Ez", "Hx", "Hy", "Hz"};
  private static final String[] CHANNELS = {
      "source_clipped", "source_return", "he11_subspace", "other_guided",
      "unclassified_downstream", "other_escape", "material_absorption"
  };

  private S06FluxExport1003() {}

  public static void main(String[] args) throws Exception {
    boolean preflightOnly = args.length == 1 && "--preflight-only".equals(args[0]);
    if (args.length != 0 && !preflightOnly) {
      throw new IllegalArgumentException("Use no arguments, or --preflight-only for offline binding validation");
    }
    Binding b = readBinding();
    if (preflightOnly) {
      System.out.println("S06_1003_PREFLIGHT=PASS_BINDINGS_ONLY_NO_COMSOL");
      System.out.println("S06_1003_JOB=" + b.jobId + ",MODEL_SHA256=" + b.modelSha);
      return;
    }

    Model model = ModelUtil.loadCopy("S06FluxExport1003", b.artifact.toString());
    validateModel(model, b);
    int[] sourceFaces = exactSelection(model, b, "sourcePhysicalFaces", new int[] {93});
    int[] monitorCore = exactSelection(model, b, "monitorCoreFaces", new int[] {137});
    int[] monitorClad = exactSelection(model, b, "monitorCladFaces", new int[] {99});
    int[] monitorFaces = exactSelection(model, b, "monitorPhysicalFaces", new int[] {99, 137});
    if (!sameIds(concat(monitorCore, monitorClad), monitorFaces)) {
      throw new IllegalStateException("monitorPhysicalFaces does not equal monitorCoreFaces union monitorCladFaces");
    }

    double[] sourceBox = measureBounds(model, b, sourceFaces);
    double[] monitorBox = measureBounds(model, b, monitorFaces);
    requireFlatZ("sourcePhysicalFaces", sourceBox, b.geometryTolerance);
    requireFlatZ("monitorPhysicalFaces", monitorBox, b.geometryTolerance);
    if (!(sourceBox[5] < monitorBox[4])) {
      throw new IllegalStateException("source/monitor geometry order is not source z < monitor z");
    }

    final GeomSequence geometry = model.component(b.componentTag).geom(b.geometryTag);
    List<Sample> samples = readSamples(b, monitorBox, monitorFaces, geometry);
    double[][] coordinates = new double[3][samples.size()];
    for (int i = 0; i < samples.size(); i++) {
      coordinates[0][i] = samples.get(i).x;
      coordinates[1][i] = samples.get(i).y;
      coordinates[2][i] = samples.get(i).z;
    }
    String[] expressions = new String[FIELDS.length];
    for (int i = 0; i < FIELDS.length; i++) expressions[i] = b.physicsTag + "." + FIELDS[i];

    String interpTag = "s06fxFields1003";
    requireUnusedNumericalTag(model, interpTag);
    model.result().numerical().create(interpTag, "Interp");
    model.result().numerical(interpTag).set("data", b.datasetTag);
    model.result().numerical(interpTag).set("solnum", new int[] {b.solutionIndex});
    model.result().numerical(interpTag).set("expr", expressions);
    model.result().numerical(interpTag).setInterpolationCoordinates(coordinates);
    double[][][] real = model.result().numerical(interpTag).getData();
    double[][][] imag = model.result().numerical(interpTag).getImagData();
    validateFieldData(real, samples.size(), "real");
    validateFieldData(imag, samples.size(), "imaginary");

    String szExpression = "0.5*real(" + b.physicsTag + ".Ex*conj(" + b.physicsTag
        + ".Hy)-" + b.physicsTag + ".Ey*conj(" + b.physicsTag + ".Hx))";
    double sourceNetZ = integrateZ(model, b, sourceFaces, "s06fxSourceInt1003", szExpression);
    double monitorNetZ = integrateZ(model, b, monitorFaces, "s06fxMonitorInt1003", szExpression);

    Path outputDir = createOutputDirectory(b);
    Path fieldPath = outputDir.resolve("monitor_complex_fields.csv");
    writeFields(fieldPath, samples, real, imag);
    String fieldSha = sha256(fieldPath);
    Path rawPath = outputDir.resolve("raw_record.json");
    writeRawRecord(rawPath, b, sourceBox, monitorBox, samples.size(),
        sourceNetZ, monitorNetZ, fieldSha, szExpression);
    String rawSha = sha256(rawPath);
    boolean ledgerInputAllowed = b.sourceFieldSha != null && b.partitionEvidenceSha != null;
    Path ledgerPath = outputDir.resolve(ledgerInputAllowed
        ? "ledger_861_input.json" : "ledger_861_staging.json");
    if (ledgerInputAllowed) writeLedgerInput(ledgerPath, b, fieldSha);
    else writeLedgerStaging(ledgerPath, b, fieldSha);
    writeLedgerStatus(outputDir.resolve("ledger_861_status.json"), b, rawSha,
        ledgerPath, fieldSha, ledgerInputAllowed);

    System.out.println("S06_1003_EXPORT_COMPLETE=" + b.jobId
        + ",MODEL_SHA256=" + b.modelSha + ",FIELD_SHA256=" + fieldSha
        + ",RAW_RECORD_SHA256=" + rawSha + ",PHYSICAL_LEDGER=INCOMPLETE");
  }

  private static Binding readBinding() throws Exception {
    Path jobFile = envPath(JOB_ENV);
    Path modelFile = envPath(MODEL_ENV);
    Properties job = readProperties(jobFile);
    Properties model = readProperties(modelFile);
    Binding b = new Binding();
    b.jobFile = jobFile;
    b.modelFile = modelFile;
    b.jobId = required(job, "job_id");
    b.jobDir = realPath(required(job, "job_dir"));
    b.jobManifest = realPath(required(job, "job_manifest_path"));
    b.artifact = realPath(required(job, "artifact_path"));
    b.artifactAudit = realPath(required(job, "artifact_audit_path"));
    b.modelSha = requiredSha(job, "artifact_sha256");
    b.upstreamBinding = realPath(required(model, "upstream_job_binding_path"));
    b.upstreamBindingSha = requiredSha(model, "upstream_job_binding_sha256");
    b.caseId = required(model, "case_id");
    b.lambdaM = requiredDouble(model, "lambda_m");
    b.componentTag = required(model, "component_tag");
    b.geometryTag = required(model, "geometry_tag");
    b.physicsTag = required(model, "physics_tag");
    b.studyTag = required(model, "study_tag");
    b.solutionTag = required(model, "solution_tag");
    b.datasetTag = required(model, "dataset_tag");
    b.solutionIndex = requiredPositiveInt(model, "solution_index");
    b.geometryTolerance = requiredDouble(model, "geometry_tolerance_m");
    b.gridPath = realPath(required(model, "field_grid_path"));
    b.gridSha = requiredSha(model, "field_grid_sha256");
    b.sourceJobId = required(model, "upstream_source_job_id");
    b.sourceModelSha = requiredSha(model, "upstream_source_model_sha256");
    b.releasePath = realPath(required(model, "release_record_path"));
    b.releaseSha = requiredSha(model, "release_record_sha256");
    b.sourceFieldSha = optionalSha(model, "source_field_sha256", "source_field_sha256_reason");
    b.sourceFieldPath = optionalEvidencePath(model, "source_field_path", b.sourceFieldSha,
        "source field evidence");
    b.sourceFieldReason = b.sourceFieldSha == null
        ? required(model, "source_field_sha256_reason") : null;
    b.partitionEvidenceSha = optionalSha(model, "partition_evidence_sha256",
        "partition_evidence_sha256_reason");
    b.partitionEvidencePath = optionalEvidencePath(model, "partition_evidence_path",
        b.partitionEvidenceSha, "physical partition evidence");
    b.partitionEvidenceReason = b.partitionEvidenceSha == null
        ? required(model, "partition_evidence_sha256_reason") : null;
    b.job = job;
    b.model = model;
    if (!("LD974-WEDGE-BASE-001".equals(b.caseId) || "LD974-WEDGE-LAT1-001".equals(b.caseId))) {
      throw new IllegalArgumentException("case_id must be the frozen BASE or LAT1 identifier");
    }
    if (Math.abs(b.lambdaM - 974e-9) > 1e-15 || b.geometryTolerance <= 0) {
      throw new IllegalArgumentException("974 nm and a positive geometry tolerance are required");
    }
    if (!"true".equalsIgnoreCase(required(job, "artifact_audit_pass"))
        || !"false".equalsIgnoreCase(required(job, "solution_established"))) {
      throw new IllegalArgumentException("job audit is identity evidence only and must not claim a solution");
    }
    verifyJobChain(b);
    verifyFiles(b);
    verifyReleaseRecord(b);
    for (String parameter : PARAMS) required(model, "parameter." + parameter + ".expected");
    return b;
  }

  private static void verifyJobChain(Binding b) throws Exception {
    if (!b.jobDir.getFileName().toString().equals(b.jobId)) {
      throw new IllegalArgumentException("job_id does not match the dynamic job directory");
    }
    requireInside(b.jobManifest, b.jobDir, "job manifest");
    requireInside(b.artifact, b.jobDir, "model artifact");
    String relative = required(b.job, "artifact_relative_path").replace('\\', '/');
    Path expected = b.jobDir.resolve(relative).normalize().toRealPath();
    if (!expected.equals(b.artifact)) {
      throw new IllegalArgumentException("job output path and bound artifact path differ");
    }
    requireSha(b.jobManifest, requiredSha(b.job, "job_manifest_sha256"), "job manifest");
    requireSha(b.artifactAudit, requiredSha(b.job, "artifact_audit_sha256"), "artifact audit");
    requireSha(b.artifact, b.modelSha, "model artifact");

    requireSha(b.upstreamBinding, b.upstreamBindingSha, "upstream job binding");
    Properties upstream = readProperties(b.upstreamBinding);
    if (!b.sourceJobId.equals(required(upstream, "job_id"))) {
      throw new IllegalArgumentException("upstream job id does not match the declared lineage");
    }
    Path upstreamDir = realPath(required(upstream, "job_dir"));
    Path upstreamModel = realPath(required(upstream, "artifact_path"));
    if (!upstreamDir.getFileName().toString().equals(b.sourceJobId)) {
      throw new IllegalArgumentException("upstream job id does not match its actual directory");
    }
    requireInside(upstreamModel, upstreamDir, "upstream artifact");
    requireSha(upstreamModel, b.sourceModelSha, "upstream artifact");
    if (!requiredSha(b.job, "input_model_sha256_before").equalsIgnoreCase(b.sourceModelSha)) {
      throw new IllegalArgumentException("current job input SHA does not match the upstream job artifact");
    }
  }

  private static void verifyFiles(Binding b) throws Exception {
    requireSha(b.gridPath, b.gridSha, "field sampling coordinates");
    if (!requiredSha(b.model, "model_sha256").equalsIgnoreCase(b.modelSha)) {
      throw new IllegalArgumentException("model binding SHA does not match the actual job artifact");
    }
    if (b.sourceFieldSha != null) requireSha(b.sourceFieldPath, b.sourceFieldSha, "source field evidence");
    if (b.partitionEvidenceSha != null) {
      if (b.partitionEvidencePath.equals(b.releasePath)
          || b.partitionEvidenceSha.equalsIgnoreCase(b.releaseSha)) {
        throw new IllegalArgumentException("physical partition evidence must not be the release record or its SHA-256");
      }
      requireSha(b.partitionEvidencePath, b.partitionEvidenceSha, "physical partition evidence");
    }
    requireSha(b.releasePath, b.releaseSha, "release record");
  }

  private static void verifyReleaseRecord(Binding b) throws Exception {
    Properties release = readProperties(b.releasePath);
    if (!"PASS".equals(required(release, "status"))) throw new IllegalArgumentException("release record is not PASS");
    for (String gate : new String[] {"S04", "S05", "G03a", "G03b", "G17", "source_direction", "resources", "comsol64", "wave_optics"}) {
      if (!"PASS".equals(required(release, "gate." + gate + ".status"))) {
        throw new IllegalArgumentException("execution release gate is not PASS: " + gate);
      }
      requireSha(realPath(required(release, "gate." + gate + ".evidence_path")),
          requiredSha(release, "gate." + gate + ".evidence_sha256"), gate + " evidence");
    }
    if (required(release, "review.author_id").equals(required(release, "review.reviewer_id"))) {
      throw new IllegalArgumentException("reviewer must be independent from the author");
    }
    requireSha(realPath(required(release, "review.path")), requiredSha(release, "review.sha256"), "independent review");
    Path source = realPath(required(b.model, "candidate_source_path"));
    String sourceSha = requiredSha(b.model, "candidate_source_sha256");
    requireSha(source, sourceSha, "candidate source");
    if (!sourceSha.equalsIgnoreCase(requiredSha(release, "review.source_sha256"))) {
      throw new IllegalArgumentException("independent review does not bind this source SHA-256");
    }
    Path binder = realPath(required(b.model, "candidate_binder_path"));
    String binderSha = requiredSha(b.model, "candidate_binder_sha256");
    requireSha(binder, binderSha, "job binding utility");
    if (!binderSha.equalsIgnoreCase(requiredSha(release, "review.binder_sha256"))) {
      throw new IllegalArgumentException("independent review does not bind the job binding utility SHA-256");
    }
    if (!classResourceSha256("S06FluxExport1003.class").equalsIgnoreCase(requiredSha(release, "review.class_sha256"))
        || !classResourceSha256("S06FluxExport1003$Binding.class").equalsIgnoreCase(requiredSha(release, "review.binding_class_sha256"))
        || !classResourceSha256("S06FluxExport1003$Sample.class").equalsIgnoreCase(requiredSha(release, "review.sample_class_sha256"))) {
      throw new IllegalArgumentException("independent review does not bind the complete compiled class set");
    }
  }

  private static void validateModel(Model model, Binding b) {
    requireContains(model.component().tags(), b.componentTag, "component");
    requireContains(model.component(b.componentTag).geom().tags(), b.geometryTag, "geometry");
    requireContains(model.component(b.componentTag).physics().tags(), b.physicsTag, "physics");
    requireContains(model.study().tags(), b.studyTag, "study");
    requireContains(model.sol().tags(), b.solutionTag, "solution");
    if (model.sol(b.solutionTag).isEmpty()) throw new IllegalStateException("bound solution is empty");
    if (!b.studyTag.equals(model.sol(b.solutionTag).study())) {
      throw new IllegalStateException("solution is not attached to the explicitly bound study");
    }
    requireContains(model.result().dataset().tags(), b.datasetTag, "dataset");
    if (!b.solutionTag.equals(model.result().dataset(b.datasetTag).getString("solution"))) {
      throw new IllegalStateException("dataset is not bound to the explicitly selected solution");
    }
    for (String parameter : PARAMS) {
      String expected = required(b.model, "parameter." + parameter + ".expected");
      String actual = model.param().get(parameter);
      if (actual == null || !expected.equals(actual.trim())) {
        throw new IllegalStateException("exact parameter readback mismatch: " + parameter);
      }
      if (b.parameterReadbacks == null) b.parameterReadbacks = new Properties();
      b.parameterReadbacks.setProperty(parameter, actual.trim());
    }
    double dx = model.param().evaluate("dx_tip");
    near("dx_tip", dx, "LD974-WEDGE-BASE-001".equals(b.caseId) ? 0.0 : 1e-6, 1e-15);
    near("gap_tip", model.param().evaluate("gap_tip"), 5.65e-6, 1e-15);
    near("R_tip", model.param().evaluate("R_tip"), 3.25e-6, 1e-15);
    near("alpha_tip", model.param().evaluate("alpha_tip"), Math.PI / 4.0, 1e-12);
    near("lambdaD", model.param().evaluate("lambdaD"), 974e-9, 1e-15);
    near("zSrcRef", model.param().evaluate("zSrcRef"), -5.65e-6, 1e-15);
    System.out.println("S06_1003_BINDING=" + b.studyTag + "->" + b.solutionTag + "->"
        + b.datasetTag + ",SOLNUM=" + b.solutionIndex + ",CASE=" + b.caseId);
  }

  private static int[] exactSelection(Model model, Binding b, String tag, int[] expected) {
    int[] actual = model.component(b.componentTag).selection(tag).entities(2);
    if (!sameIds(actual, expected)) {
      throw new IllegalStateException("selection changed or is not the logged 425/458 selection: " + tag);
    }
    return actual;
  }

  private static double[] measureBounds(Model model, Binding b, int[] faces) {
    model.component(b.componentTag).measure().selection().geom(b.geometryTag, 2);
    model.component(b.componentTag).measure().selection().set(faces);
    double area = model.component(b.componentTag).measure().getArea();
    double[] bounds = model.component(b.componentTag).measure().getBoundingBox();
    if (!Double.isFinite(area) || area <= 0 || bounds == null || bounds.length != 6) {
      throw new IllegalStateException("selected semantic surface has no finite area/bounds");
    }
    return bounds;
  }

  private static void requireFlatZ(String label, double[] bounds, double tolerance) {
    if (!Double.isFinite(bounds[4]) || !Double.isFinite(bounds[5])
        || Math.abs(bounds[5] - bounds[4]) > tolerance) {
      throw new IllegalStateException(label + " is not an explicitly verified z-normal plane");
    }
  }

  private static List<Sample> readSamples(Binding b, double[] bounds, int[] monitorFaces,
                                         GeomSequence geometry) throws IOException {
    List<Sample> samples = new ArrayList<Sample>();
    boolean anyWeight = false;
    boolean allWeights = true;
    try (BufferedReader reader = Files.newBufferedReader(b.gridPath, StandardCharsets.UTF_8)) {
      String header = reader.readLine();
      if (!"x_m\ty_m\tz_m\tweight_m2".equals(header)) {
        throw new IllegalArgumentException("grid header must be x_m, y_m, z_m, weight_m2");
      }
      String line;
      int row = 1;
      while ((line = reader.readLine()) != null) {
        row++;
        String[] v = line.split("\t", -1);
        if (v.length != 4) throw new IllegalArgumentException("grid row must have four columns at line " + row);
        Sample s = new Sample(number(v[0], "x_m", row), number(v[1], "y_m", row), number(v[2], "z_m", row));
        if (!v[3].trim().isEmpty()) {
          s.weight = number(v[3], "weight_m2", row);
          if (s.weight <= 0) throw new IllegalArgumentException("weight_m2 must be positive when provided");
          anyWeight = true;
        } else {
          allWeights = false;
        }
        if (s.x < bounds[0] || s.x > bounds[1] || s.y < bounds[2] || s.y > bounds[3]
            || Math.abs(s.z - bounds[4]) > b.geometryTolerance) {
          throw new IllegalArgumentException("sample point is outside monitorPhysicalFaces at line " + row);
        }
        if (!findMatchingFace(geometry, monitorFaces, s, b.geometryTolerance)) {
          throw new IllegalArgumentException("sample point is inside the monitor AABB but is not proven on a selected monitor face at line " + row);
        }
        samples.add(s);
      }
    }
    if (samples.isEmpty()) throw new IllegalArgumentException("field sampling coordinate list is empty");
    if (anyWeight && !allWeights) throw new IllegalArgumentException("quadrature weights must be supplied for every sample or for none");
    b.weightsProvided = anyWeight && allWeights;
    return samples;
  }

  static boolean findMatchingFace(GeomSequence geometry, int[] faces, Sample sample,
                                  double tolerance) {
    int bestFace = 0;
    double bestResidual = Double.POSITIVE_INFINITY;
    for (int face : faces) {
      double[] range = geometry.faceParamRange(face);
      if (range == null || range.length != 4 || !finite(range)
          || !(range[1] > range[0]) || !(range[3] > range[2])) {
        throw new IllegalStateException("COMSOL returned an invalid parameter range for selected face " + face);
      }
      for (double uFraction : new double[] {0.1, 0.5, 0.9}) {
        for (double vFraction : new double[] {0.1, 0.5, 0.9}) {
          double u = range[0] + uFraction * (range[1] - range[0]);
          double v = range[2] + vFraction * (range[3] - range[2]);
          double[] uv = minimizeFaceDistance(geometry, face, range, sample.x, sample.y, sample.z,
              tolerance, u, v);
          if (uv == null) continue;
          double residual = distance(facePoint(geometry, face, uv[0], uv[1]), sample.x, sample.y, sample.z);
          if (residual < bestResidual) {
            bestFace = face;
            bestResidual = residual;
          }
        }
      }
    }
    if (bestFace == 0 || bestResidual > tolerance) return false;
    sample.faceEntity = bestFace;
    sample.faceResidual = bestResidual;
    return true;
  }

  private static double[] minimizeFaceDistance(GeomSequence geometry, int face, double[] range,
                                                double x, double y, double z,
                                                double tolerance, double startU, double startV) {
    double u = startU, v = startV;
    for (int iteration = 0; iteration < 40; iteration++) {
      double[] point = facePoint(geometry, face, u, v);
      double[] residual = {point[0] - x, point[1] - y, point[2] - z};
      double norm2 = dot(residual, residual);
      if (norm2 <= tolerance * tolerance) return new double[] {u, v};
      double[] du = faceDerivative(geometry, face, range, u, v, true);
      double[] dv = faceDerivative(geometry, face, range, u, v, false);
      double aa = dot(du, du), ab = dot(du, dv), bb = dot(dv, dv);
      double ar = dot(du, residual), br = dot(dv, residual);
      double determinant = aa * bb - ab * ab;
      if (!Double.isFinite(determinant) || !(determinant > 1e-14 * aa * bb)) return null;
      double stepU = (bb * ar - ab * br) / determinant;
      double stepV = (aa * br - ab * ar) / determinant;
      boolean improved = false;
      for (double alpha = 1.0; alpha >= 1.0 / 1024.0; alpha *= 0.5) {
        double nextU = clamp(u - alpha * stepU, range[0], range[1]);
        double nextV = clamp(v - alpha * stepV, range[2], range[3]);
        if (nextU == u && nextV == v) continue;
        double nextNorm2 = distanceSquared(facePoint(geometry, face, nextU, nextV), x, y, z);
        if (nextNorm2 < norm2) {
          u = nextU;
          v = nextV;
          improved = true;
          break;
        }
      }
      if (!improved) return null;
    }
    return null;
  }

  private static double[] faceDerivative(GeomSequence geometry, int face, double[] range,
                                         double u, double v, boolean first) {
    double min = first ? range[0] : range[2];
    double max = first ? range[1] : range[3];
    double parameter = first ? u : v;
    double h = Math.min(Math.max((max - min) * 1e-6,
        Math.ulp(Math.max(1.0, Math.abs(parameter))) * 16.0), (max - min) * 0.25);
    double before = Math.max(min, parameter - h);
    double after = Math.min(max, parameter + h);
    if (!(after > before)) return new double[] {Double.NaN, Double.NaN, Double.NaN};
    double[] left = facePoint(geometry, face, first ? before : u, first ? v : before);
    double[] right = facePoint(geometry, face, first ? after : u, first ? v : after);
    return new double[] {(right[0] - left[0]) / (after - before),
        (right[1] - left[1]) / (after - before), (right[2] - left[2]) / (after - before)};
  }

  private static double[] facePoint(GeomSequence geometry, int face, double u, double v) {
    double[][] coordinates = geometry.faceX(face, new double[][] {{u, v}});
    if (coordinates == null || coordinates.length != 1 || coordinates[0].length != 3
        || !finite(coordinates[0])) {
      throw new IllegalStateException("COMSOL faceX returned invalid 3D coordinates for selected face " + face);
    }
    return coordinates[0];
  }

  private static double distance(double[] point, double x, double y, double z) {
    return Math.sqrt(distanceSquared(point, x, y, z));
  }

  private static double distanceSquared(double[] point, double x, double y, double z) {
    double dx = point[0] - x, dy = point[1] - y, dz = point[2] - z;
    return dx * dx + dy * dy + dz * dz;
  }

  private static double dot(double[] a, double[] b) {
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  }

  private static double clamp(double value, double min, double max) {
    return Math.max(min, Math.min(max, value));
  }

  private static boolean finite(double[] values) {
    if (values == null) return false;
    for (double value : values) if (!Double.isFinite(value)) return false;
    return true;
  }

  private static double integrateZ(Model model, Binding b, int[] faces, String tag, String expression) {
    requireUnusedNumericalTag(model, tag);
    model.result().numerical().create(tag, "IntSurface");
    model.result().numerical(tag).selection().set(faces);
    model.result().numerical(tag).set("data", b.datasetTag);
    model.result().numerical(tag).set("solnum", new int[] {b.solutionIndex});
    model.result().numerical(tag).set("expr", new String[] {expression});
    double[][] values = model.result().numerical(tag).getReal();
    if (values.length != 1 || values[0].length != 1 || !Double.isFinite(values[0][0])) {
      throw new IllegalStateException("IntSurface returned no unique finite signed z-flux value for " + tag);
    }
    return values[0][0];
  }

  private static void validateFieldData(double[][][] values, int points, String part) {
    if (values.length != FIELDS.length) throw new IllegalStateException("Interp " + part + " expression count mismatch");
    for (int i = 0; i < FIELDS.length; i++) {
      if (values[i].length != 1 || values[i][0].length != points) {
        throw new IllegalStateException("Interp " + part + " dimensions mismatch for " + FIELDS[i]);
      }
      for (double value : values[i][0]) {
        if (!Double.isFinite(value)) throw new IllegalStateException("Interp returned nonfinite " + part + " field values");
      }
    }
  }

  private static void writeFields(Path path, List<Sample> samples,
                                  double[][][] real, double[][][] imag) throws IOException {
    Path temp = path.resolveSibling(path.getFileName().toString() + ".tmp");
    try (BufferedWriter w = Files.newBufferedWriter(temp, StandardCharsets.UTF_8)) {
      w.write("sample_index,x_m,y_m,z_m,monitor_face_entity,monitor_face_residual_m,weight_m2,weight_reason,Ex_real,Ex_imag,Ey_real,Ey_imag,Ez_real,Ez_imag,Hx_real,Hx_imag,Hy_real,Hy_imag,Hz_real,Hz_imag");
      w.newLine();
      for (int point = 0; point < samples.size(); point++) {
        Sample s = samples.get(point);
        w.write(point + "," + d(s.x) + "," + d(s.y) + "," + d(s.z) + ","
            + s.faceEntity + "," + d(s.faceResidual) + ","
            + (s.weight == null ? "" : d(s.weight)) + ","
            + csv(s.weight == null ? "quadrature weight not supplied; projection input unavailable" : ""));
        for (int field = 0; field < FIELDS.length; field++) {
          w.write("," + d(real[field][0][point]) + "," + d(imag[field][0][point]));
        }
        w.newLine();
      }
    }
    Files.move(temp, path, StandardCopyOption.ATOMIC_MOVE);
  }

  private static void writeRawRecord(Path path, Binding b, double[] sourceBox, double[] monitorBox,
                                     int count, double sourceNetZ, double monitorNetZ,
                                     String fieldSha, String expression) throws IOException {
    String sourceFieldReason = b.sourceFieldReason;
    boolean weightsProvided = b.weightsProvided;
    String json = "{\n"
        + "  \"schema\":\"S06_FLUX_FIELD_EXPORT_1003_FIX_1026\",\n"
        + "  \"status\":\"RAW_EXPORT_ONLY_POWER_LEDGER_INCOMPLETE\",\n"
        + "  \"case_id\":" + q(b.caseId) + ",\n"
        + "  \"lambda_m\":" + d(b.lambdaM) + ",\n"
        + "  \"provenance\":{\"job_id\":" + q(b.jobId)
        + ",\"job_manifest_sha256\":" + q(required(b.job, "job_manifest_sha256"))
        + ",\"artifact_relative_path\":" + q(required(b.job, "artifact_relative_path"))
        + ",\"model_sha256\":" + q(b.modelSha)
        + ",\"config_sha256\":" + q(sha256(b.modelFile))
        + ",\"source_field_sha256\":" + nullableSha(b.sourceFieldSha)
        + ",\"source_field_sha256_reason\":" + (sourceFieldReason == null ? "null" : q(sourceFieldReason))
        + ",\"field_data_sha256\":" + q(fieldSha)
        + ",\"upstream_source_job_id\":" + q(b.sourceJobId)
        + ",\"upstream_source_model_sha256\":" + q(b.sourceModelSha)
        + ",\"study_tag\":" + q(b.studyTag) + ",\"solution_tag\":" + q(b.solutionTag)
        + ",\"dataset_tag\":" + q(b.datasetTag) + ",\"solution_index\":" + b.solutionIndex
        + ",\"component_tag\":" + q(b.componentTag) + ",\"physics_tag\":" + q(b.physicsTag)
        + ",\"field_grid_sha256\":" + q(b.gridSha) + "},\n"
        + "  \"parameter_readbacks\":{" + parameterJson(b.parameterReadbacks) + "},\n"
        + "  \"selection_evidence\":{\"sourcePhysicalFaces\":[93],\"monitorCoreFaces\":[137],\"monitorCladFaces\":[99],\"monitorPhysicalFaces\":[99,137]},\n"
        + "  \"monitor_sample_membership\":{\"method\":\"COMSOL 6.4 GeomInfo.faceParamRange+faceX on selected geometry faces\",\"sample_count\":" + count
        + ",\"residual_tolerance_m\":" + d(b.geometryTolerance) + "},\n"
        + "  \"partition_evidence\":{\"artifact_sha256\":" + nullableSha(b.partitionEvidenceSha)
        + ",\"reason\":" + (b.partitionEvidenceSha == null ? q(b.partitionEvidenceReason) : "null") + "},\n"
        + "  \"source_plane_bounds_m\":" + array(sourceBox) + ",\n"
        + "  \"monitor_plane_bounds_m\":" + array(monitorBox) + ",\n"
        + "  \"field_export\":{\"path\":\"monitor_complex_fields.csv\",\"sha256\":" + q(fieldSha)
        + ",\"sample_count\":" + count + ",\"complex_E_H\":true,\"weights_provided\":" + weightsProvided
        + ",\"weights_reason\":" + (weightsProvided ? "null" : q("No reviewed quadrature weights supplied; field projection is unavailable")) + "},\n"
        + "  \"signed_global_z_net_flux\":["
        + "{\"selection\":\"sourcePhysicalFaces\",\"expression\":" + q(expression)
        + ",\"net_flux_W\":" + d(sourceNetZ)
        + ",\"forward_W\":null,\"forward_reason\":\"source propagation side/direction is not validated\""
        + ",\"backward_W\":null,\"backward_reason\":\"no validated directional decomposition\"},"
        + "{\"selection\":\"monitorPhysicalFaces\",\"expression\":" + q(expression)
        + ",\"net_flux_W\":" + d(monitorNetZ)
        + ",\"forward_W\":null,\"forward_reason\":\"net flux does not separate forward/backward power\""
        + ",\"backward_W\":null,\"backward_reason\":\"net flux does not separate forward/backward power\"}],\n"
        + "  \"unavailable\":{\"he11_subspace_W\":null,\"he11_reason\":\"total monitor cross-section flux is not HE11; formal modal projection is unavailable\""
        + ",\"material_absorption_W\":null,\"material_absorption_reason\":\"native surface flux is not material absorption; no material loss integral is bound\""
        + ",\"pml_numerical_flux_W\":null,\"pml_reason\":\"no PML interface selection is bound in the 425/458 evidence\""
        + ",\"device_coupling_efficiency\":null,\"efficiency_reason\":\"HE11 identity and physical power partition remain unvalidated\"}\n}\n";
    Files.write(path, json.getBytes(StandardCharsets.UTF_8));
  }

  private static void writeLedgerInput(Path path, Binding b, String fieldSha) throws IOException {
    if (b.sourceFieldSha == null || b.partitionEvidenceSha == null) {
      throw new IllegalStateException("strict 861 input requires verified source-field and physical partition evidence SHA-256 values");
    }
    StringBuilder json = new StringBuilder(3000);
    json.append("{\n  \"case_id\":").append(q(b.caseId)).append(",\n")
        .append("  \"source_reference_W\":1,\n  \"channels\":{\n");
    for (int i = 0; i < CHANNELS.length; i++) {
      String channel = CHANNELS[i];
      json.append("    ").append(q(channel)).append(":{\"power_W\":null,\"reason\":")
          .append(q(channelReason(channel))).append(",\"evidence\":null}")
          .append(i + 1 == CHANNELS.length ? "\n" : ",\n");
    }
    json.append("  },\n  \"partition_evidence\":{\"artifact_sha256\":")
        .append(q(b.partitionEvidenceSha)).append(",\"lambda_m\":").append(d(b.lambdaM))
        .append(",\"case_id\":").append(q(b.caseId)).append("},\n")
        .append("  \"polarization_basis\":null,\"polarization_powers_W\":null,\n")
        .append("  \"polarization_unavailable_reason\":\"HE11 polarization basis is not identified\",\n")
        .append("  \"provenance\":{\"lambda_m\":").append(d(b.lambdaM))
        .append(",\"model_sha256\":").append(q(b.modelSha))
        .append(",\"config_sha256\":").append(q(sha256(b.modelFile)))
        .append(",\"source_field_sha256\":").append(q(b.sourceFieldSha))
        .append(",\"field_data_sha256\":").append(q(fieldSha))
        .append(",\"study_tag\":").append(q(b.studyTag))
        .append(",\"dataset_tag\":").append(q(b.datasetTag))
        .append(",\"solution_index\":").append(b.solutionIndex).append("}\n}\n");
    Files.write(path, json.toString().getBytes(StandardCharsets.UTF_8));
  }

  private static void writeLedgerStaging(Path path, Binding b, String fieldSha) throws IOException {
    String json = "{\n  \"schema\":\"S06_FLUX_FIELD_EXPORT_1003_BLOCKED_STAGING\",\n"
        + "  \"status\":\"NOT_AN_861_INPUT\",\n"
        + "  \"case_id\":" + q(b.caseId) + ",\n"
        + "  \"source_reference_W\":1,\n"
        + "  \"source_field_sha256\":" + nullableSha(b.sourceFieldSha) + ",\n"
        + "  \"source_field_sha256_reason\":"
        + (b.sourceFieldReason == null ? "null" : q(b.sourceFieldReason)) + ",\n"
        + "  \"partition_evidence\":{\"artifact_sha256\":"
        + nullableSha(b.partitionEvidenceSha) + ",\"reason\":"
        + (b.partitionEvidenceReason == null ? "null" : q(b.partitionEvidenceReason)) + "},\n"
        + "  \"field_data_sha256\":" + q(fieldSha) + "\n}\n";
    Files.write(path, json.getBytes(StandardCharsets.UTF_8));
  }

  private static void writeLedgerStatus(Path path, Binding b, String rawSha,
                                       Path ledgerPath, String fieldSha,
                                       boolean ledgerInputAllowed) throws IOException {
    String reason = ledgerInputAllowed
        ? "physical channels remain null pending partition classification and independent review"
        : "source-field or physical partition evidence is unknown; staging record is rejected by the strict 861 parser";
    String json = "{\n  \"ready_for_861\":false,\n"
        + "  \"reason\":" + q(reason) + ",\n"
        + "  \"record_kind\":" + q(ledgerInputAllowed ? "STRICT_861_INPUT" : "BLOCKED_STAGING_ONLY") + ",\n"
        + "  \"record_sha256\":" + q(sha256(ledgerPath)) + ",\n"
        + "  \"raw_record_sha256\":" + q(rawSha) + ",\n"
        + "  \"field_data_sha256\":" + q(fieldSha)
        + ",\n  \"G07a_status\":\"NOT_ASSESSED_PHYSICAL_PARTITION_AND_REVIEW_REQUIRED\"\n}\n";
    Files.write(path, json.getBytes(StandardCharsets.UTF_8));
  }

  private static Path createOutputDirectory(Binding b) throws IOException {
    String name = required(b.model, "output_subdir");
    if (name.contains("/") || name.contains("\\") || ".".equals(name) || "..".equals(name)) {
      throw new IllegalArgumentException("output_subdir must be one new name inside this unique job directory");
    }
    Path out = b.jobDir.resolve(name).normalize();
    if (!out.startsWith(b.jobDir) || out.equals(b.jobDir) || Files.exists(out)) {
      throw new IllegalArgumentException("export directory must be new and inside the bound job directory");
    }
    Files.createDirectory(out);
    return out;
  }

  private static void requireUnusedNumericalTag(Model model, String tag) {
    if (Arrays.asList(model.result().numerical().tags()).contains(tag)) {
      throw new IllegalStateException("temporary result tag already exists: " + tag);
    }
  }

  private static void requireContains(String[] tags, String expected, String kind) {
    if (!Arrays.asList(tags).contains(expected)) throw new IllegalStateException("bound " + kind + " tag missing: " + expected);
  }

  private static void near(String label, double value, double expected, double tol) {
    if (!Double.isFinite(value) || Math.abs(value - expected) > tol) {
      throw new IllegalStateException(label + " does not match frozen S06 parameters");
    }
  }

  private static boolean sameIds(int[] a, int[] b) {
    int[] x = a.clone(), y = b.clone();
    Arrays.sort(x); Arrays.sort(y);
    return Arrays.equals(x, y);
  }

  private static int[] concat(int[] a, int[] b) {
    int[] result = Arrays.copyOf(a, a.length + b.length);
    System.arraycopy(b, 0, result, a.length, b.length);
    return result;
  }

  private static double number(String text, String name, int row) {
    if (text == null || text.trim().isEmpty()) throw new IllegalArgumentException(name + " missing at grid row " + row);
    double value;
    try { value = Double.parseDouble(text.trim()); }
    catch (NumberFormatException exc) { throw new IllegalArgumentException(name + " invalid at grid row " + row, exc); }
    if (!Double.isFinite(value)) throw new IllegalArgumentException(name + " nonfinite at grid row " + row);
    return value;
  }

  private static Properties readProperties(Path path) throws IOException {
    Properties p = new Properties();
    try (InputStream in = Files.newInputStream(path)) { p.load(in); }
    return p;
  }

  private static Path envPath(String key) throws IOException {
    String value = System.getenv(key);
    if (value == null || value.trim().isEmpty()) throw new IllegalArgumentException("missing environment binding: " + key);
    return realPath(value.trim());
  }

  private static Path realPath(String value) throws IOException {
    if (value == null || value.trim().isEmpty() || "null".equalsIgnoreCase(value.trim())) {
      throw new IllegalArgumentException("required path is missing or null");
    }
    return Paths.get(value.trim()).toRealPath();
  }

  private static String required(Properties p, String key) {
    String value = p.getProperty(key);
    if (value == null || value.trim().isEmpty() || "null".equalsIgnoreCase(value.trim())) {
      throw new IllegalArgumentException("required binding missing or null: " + key);
    }
    return value.trim();
  }

  private static String requiredSha(Properties p, String key) {
    String value = required(p, key);
    if (!Pattern.matches(SHA256, value)) throw new IllegalArgumentException("invalid SHA-256 binding: " + key);
    return value.toLowerCase();
  }

  private static String optionalSha(Properties p, String key, String reasonKey) {
    String value = p.getProperty(key, "null").trim();
    if ("null".equalsIgnoreCase(value)) {
      required(p, reasonKey);
      return null;
    }
    if (!Pattern.matches(SHA256, value)) throw new IllegalArgumentException("invalid optional SHA-256 binding: " + key);
    return value.toLowerCase();
  }

  private static Path optionalEvidencePath(Properties p, String key, String sha, String label) throws IOException {
    String value = p.getProperty(key, "null").trim();
    boolean pathUnknown = "null".equalsIgnoreCase(value);
    if (pathUnknown != (sha == null)) {
      throw new IllegalArgumentException(label + " path and SHA-256 must both be known or both null");
    }
    return sha == null ? null : realPath(value);
  }

  private static double requiredDouble(Properties p, String key) {
    double value;
    try { value = Double.parseDouble(required(p, key)); }
    catch (NumberFormatException exc) { throw new IllegalArgumentException("invalid numeric binding: " + key, exc); }
    if (!Double.isFinite(value)) throw new IllegalArgumentException("nonfinite numeric binding: " + key);
    return value;
  }

  private static int requiredPositiveInt(Properties p, String key) {
    int value;
    try { value = Integer.parseInt(required(p, key)); }
    catch (NumberFormatException exc) { throw new IllegalArgumentException("invalid positive integer: " + key, exc); }
    if (value < 1) throw new IllegalArgumentException("invalid positive integer: " + key);
    return value;
  }

  private static void requireInside(Path file, Path dir, String label) throws IOException {
    Path realFile = file.toRealPath();
    Path realDir = dir.toRealPath();
    if (!realFile.startsWith(realDir) || realFile.equals(realDir)) throw new IllegalArgumentException(label + " is outside its job directory");
  }

  private static String sha256(Path path) throws IOException {
    try {
      MessageDigest digest = MessageDigest.getInstance("SHA-256");
      try (InputStream in = Files.newInputStream(path)) {
        byte[] buffer = new byte[1024 * 1024];
        int n;
        while ((n = in.read(buffer)) >= 0) digest.update(buffer, 0, n);
      }
      StringBuilder out = new StringBuilder(64);
      for (byte value : digest.digest()) out.append(String.format("%02x", value & 255));
      return out.toString();
    } catch (java.security.NoSuchAlgorithmException impossible) {
      throw new IllegalStateException("SHA-256 unavailable", impossible);
    }
  }

  private static void requireSha(Path path, String expected, String label) throws IOException {
    String actual = sha256(path);
    if (!actual.equalsIgnoreCase(expected)) throw new IllegalArgumentException(label + " SHA-256 mismatch");
  }

  private static String classResourceSha256(String resource) throws IOException {
    InputStream raw = S06FluxExport1003.class.getResourceAsStream("/" + resource);
    if (raw == null) throw new IllegalStateException("loaded class bytes unavailable for review binding: " + resource);
    try (InputStream in = raw) {
      try {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] buffer = new byte[16384];
        int n;
        while ((n = in.read(buffer)) >= 0) digest.update(buffer, 0, n);
        StringBuilder out = new StringBuilder(64);
        for (byte value : digest.digest()) out.append(String.format("%02x", value & 255));
        return out.toString();
      } catch (java.security.NoSuchAlgorithmException impossible) {
        throw new IllegalStateException("SHA-256 unavailable", impossible);
      }
    }
  }

  private static String d(double value) {
    if (!Double.isFinite(value)) throw new IllegalArgumentException("cannot serialize nonfinite value");
    return Double.toString(value);
  }

  private static String q(String value) {
    if (value == null) return "null";
    StringBuilder out = new StringBuilder("\"");
    for (int i = 0; i < value.length(); i++) {
      char c = value.charAt(i);
      if (c == '\\') out.append("\\\\");
      else if (c == '"') out.append("\\\"");
      else if (c == '\n') out.append("\\n");
      else if (c == '\r') out.append("\\r");
      else if (c == '\t') out.append("\\t");
      else out.append(c);
    }
    return out.append('"').toString();
  }

  private static String nullableSha(String value) {
    return value == null || "null".equalsIgnoreCase(value) ? "null" : q(value);
  }

  private static String array(double[] values) {
    StringBuilder out = new StringBuilder("[");
    for (int i = 0; i < values.length; i++) {
      if (i > 0) out.append(',');
      out.append(d(values[i]));
    }
    return out.append(']').toString();
  }

  private static String parameterJson(Properties values) {
    StringBuilder out = new StringBuilder();
    for (int i = 0; i < PARAMS.length; i++) {
      if (i > 0) out.append(',');
      out.append(q(PARAMS[i])).append(':').append(q(values.getProperty(PARAMS[i])));
    }
    return out.toString();
  }

  private static String csv(String value) { return "\"" + value.replace("\"", "\"\"") + "\""; }

  private static String channelReason(String channel) {
    if ("source_clipped".equals(channel)) return "source clipping is not resolved by the source-plane net flux";
    if ("source_return".equals(channel)) return "source propagation direction and forward/backward decomposition are unvalidated";
    if ("he11_subspace".equals(channel)) return "total monitor flux is not HE11; no formal two-polarization projection is bound";
    if ("other_guided".equals(channel)) return "other guided modes have not been classified";
    if ("unclassified_downstream".equals(channel)) return "monitor total cannot be separated into disjoint downstream modes/channels";
    if ("other_escape".equals(channel)) return "no unique external/PML boundary partition is bound; no duplicate flux is counted";
    return "no material-loss integral is bound; PML is numerical flux, not material absorption";
  }

  private static final class Binding {
    Path jobFile, modelFile, jobDir, jobManifest, artifact, artifactAudit, upstreamBinding;
    Path gridPath, releasePath, sourceFieldPath, partitionEvidencePath;
    Properties job, model;
    Properties parameterReadbacks;
    String jobId, modelSha, upstreamBindingSha, sourceJobId, sourceModelSha;
    String caseId, componentTag, geometryTag, physicsTag, studyTag, solutionTag, datasetTag;
    String gridSha, releaseSha, sourceFieldSha, sourceFieldReason;
    String partitionEvidenceSha, partitionEvidenceReason;
    int solutionIndex;
    double lambdaM, geometryTolerance;
    boolean weightsProvided;
  }

  static final class Sample {
    final double x, y, z;
    int faceEntity;
    double faceResidual;
    Double weight;
    Sample(double x, double y, double z) { this.x=x; this.y=y; this.z=z; }
  }
}
