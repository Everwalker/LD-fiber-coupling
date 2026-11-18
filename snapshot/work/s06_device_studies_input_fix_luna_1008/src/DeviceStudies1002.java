import com.comsol.model.Model;
import com.comsol.model.PropFeature;
import com.comsol.model.util.ModelUtil;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.Locale;
import java.util.regex.Pattern;

/**
 * Offline-prepared S06 study attachment for the future saved output of source
 * injection candidate 940. This class is compiled only during preparation;
 * its COMSOL entry point is intentionally not invoked in this task.
 */
public final class DeviceStudies1002 {
  private static final String OUTPUT_MODEL = "ldfiber_s06_device_studies_1002.mph";
  private static final String SOURCE_MODEL = "ldfiber_s06_source_425_940.mph";
  private static final String SOURCE_JOBS_REL = "work/s06_source_runner_fix_luna_957/jobs";
  private static final String OUTPUT_JOBS_REL =
      "work/s06_device_studies_input_fix_luna_1008/jobs";
  private static final String OUTPUT_CLAIM = ".s06_1002_claim";
  private static final Pattern SOURCE_JOB_ID = Pattern.compile(
      "source_940_957_[0-9]{8}T[0-9]{6}Z_[0-9a-f]{8}");
  private static final Pattern OUTPUT_JOB_ID = Pattern.compile(
      "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}");
  private static final Pattern SHA256 = Pattern.compile("[0-9a-fA-F]{64}");

  private static final String COMPONENT = "device3d";
  private static final String PHYSICS = "ewfd";
  private static final String STUDY = "studyS06Device1002";
  private static final String BMA_PORT_1 = "bmaPort1";
  private static final String BMA_PORT_2 = "bmaPort2";
  private static final String FREQUENCY_974 = "freq974";

  private static final String FREQUENCY_EXPRESSION = "c_const/lambdaD";
  private static final String[] SOURCE_JMS = {
      "ld_s355_jms_x", "ld_s355_jms_y", "ld_s355_jms_z"
  };
  private static final String[] SOURCE_JS = {
      "ld_s355_js_x", "ld_s355_js_y", "ld_s355_js_z"
  };

  private DeviceStudies1002() {}

  public static void main(String[] args) throws Exception {
    if (args.length != 0) {
      throw new IllegalArgumentException("This frozen candidate takes no arguments");
    }
    Path workspace;
    InputBinding input;
    try {
      workspace = Path.of(requiredEnv("S06_1002_WORKSPACE_ROOT"));
      input = bindInput(
          workspace,
          requiredEnv("S06_1002_SOURCE_JOB_ID"),
          requiredEnv("S06_1002_SOURCE_AUDIT_PASS"),
          requiredEnv("S06_1002_SOURCE_MODEL_SHA256"));
    } catch (Exception failure) {
      System.err.println("S06_1002_INPUT_BINDING_FAILURE=" + markerText(failure));
      throw failure;
    }

    Path outputDirectory;
    try {
      outputDirectory = validateOutputDirectory(
          workspace,
          requiredEnv("S06_1002_OUTPUT_JOB_ID"),
          Path.of("").toRealPath());
      claimOutputDirectory(outputDirectory);
    } catch (Exception failure) {
      System.err.println("S06_1002_OUTPUT_DIRECTORY_FAILURE=" + markerText(failure));
      throw failure;
    }

    System.out.println("S06_1002_INPUT_957_AUDIT_PASS=true");
    System.out.println("S06_1002_INPUT_JOB_ID=" + input.jobId);
    System.out.println("S06_1002_INPUT_MODEL=" + input.modelPath);
    System.out.println("S06_1002_INPUT_MODEL_SHA256=" + input.sha256);
    System.out.println("S06_1002_OUTPUT_JOB_ID=" + outputDirectory.getFileName());
    System.out.println("S06_1002_OUTPUT_DIRECTORY=" + outputDirectory);
    prepare(input, outputDirectory);
  }

  static InputBinding bindInput(Path workspaceRoot, String sourceJobId,
      String auditPass, String expectedSha256) throws IOException {
    if (workspaceRoot == null || !"true".equalsIgnoreCase(auditPass)) {
      throw new IllegalArgumentException("957 artifact audit must report artifact_audit_pass=true");
    }
    if (sourceJobId == null || !SOURCE_JOB_ID.matcher(sourceJobId).matches()) {
      throw new IllegalArgumentException("source job id is not a 957 unique job id");
    }
    if (expectedSha256 == null || !SHA256.matcher(expectedSha256).matches()) {
      throw new IllegalArgumentException("957 output artifact SHA-256 is missing or malformed");
    }

    Path workspace = workspaceRoot.toRealPath();
    Path expectedJobsRoot = workspace.resolve(SOURCE_JOBS_REL).normalize();
    Path jobsRoot = expectedJobsRoot.toRealPath();
    if (!jobsRoot.equals(expectedJobsRoot)) {
      throw new IOException("957 jobs root is redirected from its expected workspace path");
    }
    Path jobDirectory = jobsRoot.resolve(sourceJobId).toRealPath();
    if (!jobsRoot.equals(jobDirectory.getParent())
        || !sourceJobId.equals(jobDirectory.getFileName().toString())) {
      throw new IOException("957 source job is not a direct child of the runner jobs directory");
    }
    Path modelPath = jobDirectory.resolve(SOURCE_MODEL).toRealPath();
    if (!jobDirectory.equals(modelPath.getParent())
        || !SOURCE_MODEL.equals(modelPath.getFileName().toString())
        || !Files.isRegularFile(modelPath, LinkOption.NOFOLLOW_LINKS)
        || Files.size(modelPath) == 0) {
      throw new IOException("957 audited source MPH is missing, empty, or outside its job directory");
    }

    String actualSha256 = sha256(modelPath);
    if (!actualSha256.equals(expectedSha256.toLowerCase(Locale.ROOT))) {
      throw new IOException("957 output SHA-256 differs from the supplied artifact-audit SHA-256");
    }
    return new InputBinding(sourceJobId, jobDirectory, modelPath, actualSha256);
  }

  static Path validateOutputDirectory(Path workspaceRoot, String outputJobId,
      Path workingDirectory) throws IOException {
    if (outputJobId == null || !OUTPUT_JOB_ID.matcher(outputJobId).matches()) {
      throw new IllegalArgumentException("output job id must be a UUID directory name");
    }
    Path workspace = workspaceRoot.toRealPath();
    Path expectedJobsRoot = workspace.resolve(OUTPUT_JOBS_REL).normalize();
    Path jobsRoot = expectedJobsRoot.toRealPath();
    if (!jobsRoot.equals(expectedJobsRoot)) {
      throw new IOException("1008 output jobs root is redirected from its expected workspace path");
    }
    Path outputDirectory = jobsRoot.resolve(outputJobId).toRealPath();
    if (!jobsRoot.equals(outputDirectory.getParent())
        || !outputJobId.equalsIgnoreCase(outputDirectory.getFileName().toString())) {
      throw new IOException("output job directory is not a direct child of the 1008 jobs directory");
    }
    if (!outputDirectory.equals(workingDirectory.toRealPath())) {
      throw new IOException("COMSOL batch working directory is not the selected 1008 job directory");
    }
    if (Files.exists(outputDirectory.resolve(OUTPUT_MODEL), LinkOption.NOFOLLOW_LINKS)) {
      throw new IOException("output MPH already exists in this job directory");
    }
    return outputDirectory;
  }

  static void claimOutputDirectory(Path outputDirectory) throws IOException {
    Files.createFile(outputDirectory.resolve(OUTPUT_CLAIM));
  }

  static String sha256(Path file) throws IOException {
    final MessageDigest digest;
    try {
      digest = MessageDigest.getInstance("SHA-256");
    } catch (NoSuchAlgorithmException impossible) {
      throw new IllegalStateException("SHA-256 is unavailable", impossible);
    }
    byte[] buffer = new byte[1024 * 1024];
    try (var input = Files.newInputStream(file)) {
      int count;
      while ((count = input.read(buffer)) >= 0) {
        digest.update(buffer, 0, count);
      }
    }
    StringBuilder result = new StringBuilder(64);
    for (byte value : digest.digest()) {
      result.append(String.format(Locale.ROOT, "%02x", value & 0xff));
    }
    return result.toString();
  }

  private static String requiredEnv(String name) {
    String value = System.getenv(name);
    if (value == null || value.trim().isEmpty()) {
      throw new IllegalArgumentException("required COMSOL batch environment variable is unset: " + name);
    }
    return value.trim();
  }

  private static String markerText(Exception failure) {
    String message = failure.getMessage();
    return (message == null ? failure.getClass().getSimpleName() : message)
        .replace('\r', ' ').replace('\n', ' ');
  }

  private static Model prepare(InputBinding input, Path outputDirectory) throws Exception {
    Model model = ModelUtil.loadCopy("DeviceStudies1002", input.modelPath.toString());
    requireStudyFreeInput(model);
    requireBaseline(model);
    requireSource940(model);

    PortSnapshot port1Before = snapshotPort(model, "port1");
    PortSnapshot port2Before = snapshotPort(model, "port2");
    int[] monitorFaces = model.component(COMPONENT)
        .selection("monitorPhysicalFaces").entities(2);
    requireNonempty(monitorFaces, "monitorPhysicalFaces");
    requireSameFaces(port1Before.faces, monitorFaces, "port1 / monitorPhysicalFaces");
    requireSameFaces(port2Before.faces, monitorFaces, "port2 / monitorPhysicalFaces");
    requirePassiveNumericPort(port1Before, "1");
    requirePassiveNumericPort(port2Before, "2");

    model.study().create(STUDY);
    model.study(STUDY).label("S06 device: candidate port modes and 974 nm frequency");

    model.study(STUDY).create(BMA_PORT_1, "BoundaryModeAnalysis");
    configureBma(model, BMA_PORT_1, "1", "port 1 candidate mode set; S02/G04 classification pending");

    model.study(STUDY).create(BMA_PORT_2, "BoundaryModeAnalysis");
    configureBma(model, BMA_PORT_2, "2", "port 2 candidate mode set; S02/G04 classification pending");

    model.study(STUDY).create(FREQUENCY_974, "Frequency");
    model.study(STUDY).feature(FREQUENCY_974)
        .label("974 nm free-space source; Numeric ports passive");
    model.study(STUDY).feature(FREQUENCY_974).set("plist", FREQUENCY_EXPRESSION);
    // This is the StudyFeature entity active flag, not its physics solve-for activation.
    model.study(STUDY).feature(FREQUENCY_974).active(true);

    String port1Binding = STUDY + "/" + BMA_PORT_1;
    String port2Binding = STUDY + "/" + BMA_PORT_2;
    model.component(COMPONENT).physics(PHYSICS).feature("port1")
        .set("StudyStep", port1Binding);
    model.component(COMPONENT).physics(PHYSICS).feature("port2")
        .set("StudyStep", port2Binding);

    requireStudyReadback(model, BMA_PORT_1, "1");
    requireStudyReadback(model, BMA_PORT_2, "2");
    requirePortUnchangedExceptStudyBinding(model, "port1", port1Before, port1Binding);
    requirePortUnchangedExceptStudyBinding(model, "port2", port2Before, port2Binding);
    requireBaseline(model);
    requireSource940(model);

    // Creates the solver-sequence structure and datasets. It does not run them.
    model.study(STUDY).createAutoSequences("all");
    requireFrequencyReadback(model);
    recordCreatedModelMetadata(model);

    // loadCopy is detached from the input; save only inside the claimed job directory.
    Path outputModel = outputDirectory.resolve(OUTPUT_MODEL);
    try {
      model.save(outputModel.toString());
      Path savedModel = outputModel.toRealPath();
      if (!outputDirectory.equals(savedModel.getParent())
          || !Files.isRegularFile(savedModel, LinkOption.NOFOLLOW_LINKS)
          || Files.size(savedModel) == 0) {
        throw new IOException("saved MPH is empty or outside the claimed job directory");
      }
      System.out.println("S06_1002_OUTPUT_ARTIFACT_PATH=" + savedModel);
      System.out.println("S06_1002_OUTPUT_ARTIFACT_BYTES=" + Files.size(savedModel));
      System.out.println("S06_1002_OUTPUT_ARTIFACT_SHA256=" + sha256(savedModel));
    } catch (Exception failure) {
      System.err.println("S06_1002_OUTPUT_ARTIFACT_FAILURE=" + markerText(failure));
      throw failure;
    }
    System.out.println("S06_1002_SAVED=" + OUTPUT_MODEL + ",STUDIES_ONLY_NO_MESH_NO_SOLVE");
    System.out.println("S06_1002_COMPLETE=PREPARATION_ONLY;NO_GATE_OR_MODE_CLASSIFICATION");
    return model;
  }

  static final class InputBinding {
    final String jobId;
    final Path jobDirectory;
    final Path modelPath;
    final String sha256;

    InputBinding(String jobId, Path jobDirectory, Path modelPath, String sha256) {
      this.jobId = jobId;
      this.jobDirectory = jobDirectory;
      this.modelPath = modelPath;
      this.sha256 = sha256;
    }
  }

  private static void requireStudyFreeInput(Model model) {
    if (model.study().tags().length != 0 || model.sol().tags().length != 0
        || model.component(COMPONENT).mesh().tags().length != 0) {
      throw new IllegalStateException("Expected the 940 source-injected 425 BASE copy with no study, solver, or mesh");
    }
  }

  private static void requireBaseline(Model model) {
    requireNear("lambdaD", model.param().evaluate("lambdaD"), 974e-9, 1e-15);
    requireNear("dx_tip", model.param().evaluate("dx_tip"), 0.0, 1e-15);
    requireNear("gap_tip", model.param().evaluate("gap_tip"), 5.65e-6, 1e-15);
    requireNear("R_tip", model.param().evaluate("R_tip"), 3.25e-6, 1e-15);
    requireNear("alpha_tip", model.param().evaluate("alpha_tip"), Math.PI / 4.0, 1e-12);
  }

  private static void requireSource940(Model model) {
    String[] variableTags = model.component(COMPONENT).variable().tags();
    if (!Arrays.asList(variableTags).contains("s06Source940")) {
      throw new IllegalStateException("The expected 940 source variable feature is absent");
    }
    String[] jms = model.component(COMPONENT).physics(PHYSICS)
        .feature("sheetM").getStringArray("Jms0");
    String[] js = model.component(COMPONENT).physics(PHYSICS)
        .feature("sheetM").feature("sheetJ").getStringArray("Js0");
    if (!Arrays.equals(SOURCE_JMS, jms) || !Arrays.equals(SOURCE_JS, js)) {
      throw new IllegalStateException("The frozen 940 surface-current binding is absent or changed");
    }
    System.out.println("S06_1002_SOURCE=940_VARIABLE=s06Source940,Jms0=" + Arrays.toString(jms)
        + ",Js0=" + Arrays.toString(js) + ",NORMALIZATION_UNCHANGED_BY_THIS_STEP");
  }

  private static PortSnapshot snapshotPort(Model model, String tag) {
    var feature = model.component(COMPONENT).physics(PHYSICS).feature(tag);
    return new PortSnapshot(
        feature.getString("PortName"),
        feature.getString("PortType"),
        feature.getString("PortExcitation"),
        feature.getBoolean("PortSlit"),
        feature.getString("PortOrientation"),
        feature.selection().entities(2),
        feature.label());
  }

  private static void requirePassiveNumericPort(PortSnapshot port, String expectedName) {
    if (!expectedName.equals(port.name) || !"Numeric".equals(port.type)
        || !"off".equals(port.excitation) || !port.slit) {
      throw new IllegalStateException("Expected passive Numeric slit port " + expectedName
          + "; got name=" + port.name + ",type=" + port.type
          + ",excitation=" + port.excitation + ",slit=" + port.slit);
    }
  }

  private static void requirePortUnchangedExceptStudyBinding(
      Model model, String tag, PortSnapshot before, String expectedBinding) {
    var feature = model.component(COMPONENT).physics(PHYSICS).feature(tag);
    PortSnapshot after = snapshotPort(model, tag);
    if (!before.name.equals(after.name) || !before.type.equals(after.type)
        || !before.excitation.equals(after.excitation) || before.slit != after.slit
        || !before.orientation.equals(after.orientation)
        || !before.label.equals(after.label)) {
      throw new IllegalStateException("Port physics/readback changed beyond the study binding: " + tag);
    }
    requireSameFaces(before.faces, after.faces, tag + " preserved boundary selection");
    if (!expectedBinding.equals(feature.getString("StudyStep"))) {
      throw new IllegalStateException("Unexpected BMA binding on " + tag + ": "
          + feature.getString("StudyStep"));
    }
    System.out.println("S06_1002_PORT=" + tag + ",name=" + after.name + ",type=" + after.type
        + ",excitation=" + after.excitation + ",slit=" + after.slit
        + ",orientation_observed_unchanged=" + after.orientation
        + ",faces=" + Arrays.toString(after.faces) + ",label=" + after.label
        + ",StudyStep=" + feature.getString("StudyStep"));
  }

  private static void configureBma(Model model, String tag, String portName, String label) {
    PropFeature step = model.study(STUDY).feature(tag);
    step.label(label);
    step.set("PortName", portName);
    step.set("modeFreq", FREQUENCY_EXPRESSION);
    step.set("neigsactive", true);
    step.set("neigs", 2);
    step.set("shiftactive", true);
    step.set("shift", "nCoreD");
  }

  private static void requireStudyReadback(Model model, String tag, String portName) {
    PropFeature step = model.study(STUDY).feature(tag);
    if (!portName.equals(step.getString("PortName"))
        || !FREQUENCY_EXPRESSION.equals(step.getString("modeFreq"))
        || !step.getBoolean("neigsactive") || step.getInt("neigs") != 2
        || !step.getBoolean("shiftactive") || !"nCoreD".equals(step.getString("shift"))) {
      throw new IllegalStateException("BMA readback mismatch: " + tag);
    }
    System.out.println("S06_1002_BMA=" + tag + ",label=" + step.label()
        + ",PortName=" + step.getString("PortName")
        + ",modeFreq=" + step.getString("modeFreq")
        + ",neigs=" + step.getInt("neigs")
        + ",shift=" + step.getString("shift")
        + ",classification=S02_G04_PENDING");
  }

  private static void requireFrequencyReadback(Model model) {
    PropFeature step = model.study(STUDY).feature(FREQUENCY_974);
    if (!FREQUENCY_EXPRESSION.equals(step.getString("plist"))) {
      throw new IllegalStateException("974 nm frequency readback mismatch");
    }
    boolean active = model.study(STUDY).feature(FREQUENCY_974).isActive();
    if (!active) {
      throw new IllegalStateException("974 nm Frequency study step is inactive after sequence creation");
    }
    System.out.println("S06_1002_FREQUENCY=" + FREQUENCY_974 + ",label=" + step.label()
        + ",plist=" + step.getString("plist") + ",active=" + active
        + ",source=940_sheet_current"
        + ",ports=PASSIVE");
  }

  private static void recordCreatedModelMetadata(Model model) {
    System.out.println("S06_1002_STUDIES=" + Arrays.toString(model.study().tags()));
    System.out.println("S06_1002_STEPS=" + Arrays.toString(model.study(STUDY).feature().tags()));
    for (String tag : model.study(STUDY).feature().tags()) {
      PropFeature step = model.study(STUDY).feature(tag);
      System.out.println("S06_1002_STEP_LABEL=" + tag + "," + step.label());
    }
    String[] solutions = model.sol().tags();
    System.out.println("S06_1002_SOLUTIONS=" + Arrays.toString(solutions));
    for (String tag : solutions) {
      System.out.println("S06_1002_SOLUTION=" + tag + ",label=" + model.sol(tag).label());
    }
    String[] datasets = model.result().dataset().tags();
    System.out.println("S06_1002_DATASETS=" + Arrays.toString(datasets));
    for (String tag : datasets) {
      PropFeature dataset = model.result().dataset(tag);
      System.out.println("S06_1002_DATASET=" + tag + ",label=" + dataset.label()
          + ",solution=" + dataset.getString("solution"));
    }
  }

  private static void requireNear(String name, double actual, double expected, double tolerance) {
    if (Math.abs(actual - expected) > tolerance) {
      throw new IllegalStateException(name + " readback mismatch: " + actual + " != " + expected);
    }
  }

  private static void requireNonempty(int[] values, String name) {
    if (values == null || values.length == 0) {
      throw new IllegalStateException("Empty selection: " + name);
    }
  }

  private static void requireSameFaces(int[] first, int[] second, String name) {
    requireNonempty(first, name + " first");
    requireNonempty(second, name + " second");
    int[] a = first.clone();
    int[] b = second.clone();
    Arrays.sort(a);
    Arrays.sort(b);
    if (!Arrays.equals(a, b)) {
      throw new IllegalStateException(name + " mismatch: "
          + Arrays.toString(a) + " vs " + Arrays.toString(b));
    }
  }

  private static final class PortSnapshot {
    final String name;
    final String type;
    final String excitation;
    final boolean slit;
    final String orientation;
    final int[] faces;
    final String label;

    PortSnapshot(String name, String type, String excitation, boolean slit,
        String orientation, int[] faces, String label) {
      this.name = name;
      this.type = type;
      this.excitation = excitation;
      this.slit = slit;
      this.orientation = orientation;
      this.faces = faces.clone();
      this.label = label;
    }
  }
}
