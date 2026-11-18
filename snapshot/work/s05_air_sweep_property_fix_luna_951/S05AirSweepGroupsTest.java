import java.util.Arrays;

public final class S05AirSweepGroupsTest {
  private static void require(boolean condition, String message) {
    if (!condition) throw new AssertionError(message);
  }

  private static void requireThrows(Runnable action, String message) {
    try {
      action.run();
    } catch (IllegalArgumentException expected) {
      return;
    }
    throw new AssertionError(message);
  }

  public static void main(String[] args) {
    int[] chain = S05AirSweepGroups.chainDomains(
      new int[] {22, 23}, new int[] {23, 24}, new int[] {24, 22, 23});
    require(Arrays.equals(chain, new int[] {22, 23, 24}),
      "source/shared/monitor air-domain grouping changed");

    double[][] boxes = new double[][] {
      {-8e-6, 8e-6, -8e-6, 8e-6, -5.65e-6, -5.65e-6},
      {-8e-6, 8e-6, -8e-6, 8e-6, 0.0, 0.0},
      {-8e-6, 8e-6, -8e-6, 8e-6, -1e-6, 1e-6}
    };
    require(Arrays.equals(
        S05AirSweepGroups.planeFaces(new int[] {78, 81, 92}, boxes, -5.65e-6, 1e-12),
        new int[] {78}),
      "only the planar source-end face should be grouped");

    require(S05AirSweepGroups.oppositeEnd(-8e-6, -5.65e-6, -5.65e-6, 1e-12) == -8e-6,
      "reverse-oriented source-side segment should target its opposite end");
    require(S05AirSweepGroups.oppositeEnd(0.0, 3e-6, 0.0, 1e-12) == 3e-6,
      "forward-oriented monitor-side segment should target its opposite end");
    require(S05AirSweepGroups.layerCount(5.65e-6, 0.15e-6) == 38,
      "axial layer count must round up to keep planned spacing within hmax");

    requireThrows(() -> S05AirSweepGroups.chainDomains(
      new int[] {22, 23}, new int[] {23, 25}, new int[] {22, 23, 24}),
      "branched/mismatched physical-domain selections must be rejected");
    requireThrows(() -> S05AirSweepGroups.oppositeEnd(-8e-6, -5.65e-6, -7e-6, 1e-12),
      "an anchor face inside a domain must not be treated as an endpoint");
    System.out.println("S05_AIR_SWEEP_GROUPS_TEST=PASS");
  }
}
