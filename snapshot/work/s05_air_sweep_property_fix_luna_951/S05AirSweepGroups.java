import java.util.Arrays;
import java.util.TreeSet;

/** Pure selection and axial-end grouping used by the S05 runtime candidate. */
final class S05AirSweepGroups {
  private S05AirSweepGroups() {}

  static int[] chainDomains(int[] sourceAdjacent, int[] monitorAdjacent, int[] physicalDomains) {
    TreeSet<Integer> source = set(sourceAdjacent);
    TreeSet<Integer> monitor = set(monitorAdjacent);
    TreeSet<Integer> physical = set(physicalDomains);
    if (source.size() != 2 || monitor.size() != 2 || physical.size() != 3) {
      throw new IllegalArgumentException("expected two adjacent domains per cut and three physical domains");
    }
    TreeSet<Integer> common = new TreeSet<Integer>(source);
    common.retainAll(monitor);
    TreeSet<Integer> sourceOnly = new TreeSet<Integer>(source);
    sourceOnly.removeAll(common);
    TreeSet<Integer> monitorOnly = new TreeSet<Integer>(monitor);
    monitorOnly.removeAll(common);
    TreeSet<Integer> chain = new TreeSet<Integer>(source);
    chain.addAll(monitor);
    if (common.size() != 1 || sourceOnly.size() != 1 || monitorOnly.size() != 1 || !chain.equals(physical)) {
      throw new IllegalArgumentException("source/monitor adjacency does not form the complete three-domain chain: "
        + Arrays.toString(sourceAdjacent) + " / " + Arrays.toString(monitorAdjacent)
        + " versus " + Arrays.toString(physicalDomains));
    }
    return new int[] {sourceOnly.first().intValue(), common.first().intValue(), monitorOnly.first().intValue()};
  }

  static int[] planeFaces(int[] faceIds, double[][] bounds, double z, double tolerance) {
    if (faceIds.length != bounds.length) {
      throw new IllegalArgumentException("face ID and bounding-box counts differ");
    }
    TreeSet<Integer> result = new TreeSet<Integer>();
    for (int i = 0; i < faceIds.length; i++) {
      double[] box = bounds[i];
      if (box == null || box.length < 6) {
        throw new IllegalArgumentException("face bounding box is unavailable for entity " + faceIds[i]);
      }
      if (Math.abs(box[4] - z) <= tolerance && Math.abs(box[5] - z) <= tolerance) {
        result.add(Integer.valueOf(faceIds[i]));
      }
    }
    return toArray(result);
  }

  static double oppositeEnd(double zmin, double zmax, double anchorZ, double tolerance) {
    boolean atMin = Math.abs(anchorZ - zmin) <= tolerance;
    boolean atMax = Math.abs(anchorZ - zmax) <= tolerance;
    if (atMin == atMax || !(zmin < zmax)) {
      throw new IllegalArgumentException("anchor is not on exactly one distinct axial endpoint");
    }
    return atMin ? zmax : zmin;
  }

  static int layerCount(double axialLength, double hmax) {
    if (!(axialLength > 0.0) || !(hmax > 0.0)) {
      throw new IllegalArgumentException("axial length and hmax must be positive");
    }
    double count = Math.ceil(axialLength / hmax);
    if (count > Integer.MAX_VALUE) {
      throw new IllegalArgumentException("requested axial layer count exceeds Java integer range");
    }
    return Math.max(1, (int) count);
  }

  private static TreeSet<Integer> set(int[] values) {
    TreeSet<Integer> result = new TreeSet<Integer>();
    for (int value : values) result.add(Integer.valueOf(value));
    return result;
  }

  private static int[] toArray(TreeSet<Integer> values) {
    int[] result = new int[values.size()];
    int i = 0;
    for (Integer value : values) result[i++] = value.intValue();
    return result;
  }
}
