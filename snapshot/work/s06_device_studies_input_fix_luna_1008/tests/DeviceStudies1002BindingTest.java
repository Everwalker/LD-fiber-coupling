import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.UUID;

/** Path and hash contract tests; fixtures are temporary bytes, never MPH inputs. */
public final class DeviceStudies1002BindingTest {
  private static final String SOURCE_JOB_ID = "source_940_957_20261117T010203Z_0123abcd";
  private static int checks;

  private DeviceStudies1002BindingTest() {}

  public static void main(String[] args) throws Exception {
    testAuditedSourcePathAndShaBind();
    testAuditMustPass();
    testJobIdCannotEscapeRunnerJobs();
    testMissingSourceModelFails();
    testHashMismatchFails();
    testEmptySourceModelFails();
    testOutputDirectoryMustBeExactJobCwd();
    testExistingOutputFails();
    testExclusiveClaimRejectsSecondOwner();
    System.out.println("PASS DeviceStudies1002BindingTest checks=" + checks);
  }

  private static void testAuditedSourcePathAndShaBind() throws Exception {
    Path workspace = Files.createTempDirectory("s06-1008-bind-");
    try {
      Path model = sourceModel(workspace, "957 output fixture, not an MPH");
      String sha = DeviceStudies1002.sha256(model);
      DeviceStudies1002.InputBinding binding = DeviceStudies1002.bindInput(
          workspace, SOURCE_JOB_ID, "true", sha);
      equal(model.toRealPath(), binding.modelPath, "canonical source path");
      equal(SOURCE_JOB_ID, binding.jobId, "audited unique job id");
      equal(sha, binding.sha256, "verified source SHA-256");
    } finally {
      deleteTree(workspace);
    }
  }

  private static void testAuditMustPass() throws Exception {
    Path workspace = Files.createTempDirectory("s06-1008-audit-");
    try {
      Path model = sourceModel(workspace, "fixture");
      fails(() -> DeviceStudies1002.bindInput(workspace, SOURCE_JOB_ID, "false",
          DeviceStudies1002.sha256(model)), "957 artifact audit must pass");
    } finally {
      deleteTree(workspace);
    }
  }

  private static void testJobIdCannotEscapeRunnerJobs() throws Exception {
    Path workspace = Files.createTempDirectory("s06-1008-jobid-");
    try {
      fails(() -> DeviceStudies1002.bindInput(workspace, "../outside", "true", "a".repeat(64)),
          "job id must be a 957 unique-job component");
    } finally {
      deleteTree(workspace);
    }
  }

  private static void testMissingSourceModelFails() throws Exception {
    Path workspace = Files.createTempDirectory("s06-1008-missing-");
    try {
      Path jobs = workspace.resolve("work/s06_source_runner_fix_luna_957/jobs");
      Files.createDirectories(jobs.resolve(SOURCE_JOB_ID));
      fails(() -> DeviceStudies1002.bindInput(workspace, SOURCE_JOB_ID, "true", "a".repeat(64)),
          "missing 957 model must fail");
    } finally {
      deleteTree(workspace);
    }
  }

  private static void testHashMismatchFails() throws Exception {
    Path workspace = Files.createTempDirectory("s06-1008-sha-");
    try {
      sourceModel(workspace, "fixture");
      fails(() -> DeviceStudies1002.bindInput(workspace, SOURCE_JOB_ID, "true", "0".repeat(64)),
          "audit SHA mismatch must fail");
    } finally {
      deleteTree(workspace);
    }
  }

  private static void testEmptySourceModelFails() throws Exception {
    Path workspace = Files.createTempDirectory("s06-1008-empty-");
    try {
      sourceModel(workspace, "");
      Path model = workspace.resolve("work/s06_source_runner_fix_luna_957/jobs")
          .resolve(SOURCE_JOB_ID).resolve("ldfiber_s06_source_425_940.mph");
      fails(() -> DeviceStudies1002.bindInput(workspace, SOURCE_JOB_ID, "true",
          DeviceStudies1002.sha256(model)), "empty source model must fail");
    } finally {
      deleteTree(workspace);
    }
  }

  private static void testOutputDirectoryMustBeExactJobCwd() throws Exception {
    Path workspace = Files.createTempDirectory("s06-1008-output-");
    try {
      String id = UUID.randomUUID().toString();
      Path expected = workspace.resolve("work/s06_device_studies_input_fix_luna_1008/jobs")
          .resolve(id);
      Files.createDirectories(expected);
      equal(expected.toRealPath(), DeviceStudies1002.validateOutputDirectory(
          workspace, id, expected), "isolated output job directory");
      Path wrongCwd = Files.createDirectory(workspace.resolve("wrong-cwd"));
      fails(() -> DeviceStudies1002.validateOutputDirectory(workspace, id, wrongCwd),
          "output CWD mismatch must fail");
    } finally {
      deleteTree(workspace);
    }
  }

  private static void testExistingOutputFails() throws Exception {
    Path workspace = Files.createTempDirectory("s06-1008-existing-");
    try {
      String id = UUID.randomUUID().toString();
      Path output = workspace.resolve("work/s06_device_studies_input_fix_luna_1008/jobs")
          .resolve(id);
      Files.createDirectories(output);
      Files.writeString(output.resolve("ldfiber_s06_device_studies_1002.mph"), "existing",
          StandardCharsets.UTF_8);
      fails(() -> DeviceStudies1002.validateOutputDirectory(workspace, id, output),
          "existing output model must fail");
    } finally {
      deleteTree(workspace);
    }
  }

  private static void testExclusiveClaimRejectsSecondOwner() throws Exception {
    Path directory = Files.createTempDirectory("s06-1008-claim-");
    try {
      DeviceStudies1002.claimOutputDirectory(directory);
      fails(() -> DeviceStudies1002.claimOutputDirectory(directory),
          "output directory claim must be exclusive");
    } finally {
      deleteTree(directory);
    }
  }

  private static Path sourceModel(Path workspace, String bytes) throws IOException {
    Path model = workspace.resolve("work/s06_source_runner_fix_luna_957/jobs")
        .resolve(SOURCE_JOB_ID).resolve("ldfiber_s06_source_425_940.mph");
    Files.createDirectories(model.getParent());
    Files.writeString(model, bytes, StandardCharsets.UTF_8);
    return model;
  }

  private static void equal(Object expected, Object actual, String message) {
    checks++;
    if (!expected.equals(actual)) {
      throw new AssertionError(message + ": expected=" + expected + ", actual=" + actual);
    }
  }

  private static void fails(ThrowingRunnable operation, String message) throws Exception {
    checks++;
    try {
      operation.run();
    } catch (IOException | IllegalArgumentException expected) {
      return;
    }
    throw new AssertionError(message + ": operation unexpectedly succeeded");
  }

  private static void deleteTree(Path root) throws IOException {
    if (!Files.exists(root)) {
      return;
    }
    try (var paths = Files.walk(root)) {
      Path[] reverse = paths.sorted((a, b) -> b.compareTo(a)).toArray(Path[]::new);
      for (Path path : reverse) {
        Files.deleteIfExists(path);
      }
    }
  }

  @FunctionalInterface
  private interface ThrowingRunnable {
    void run() throws Exception;
  }
}
