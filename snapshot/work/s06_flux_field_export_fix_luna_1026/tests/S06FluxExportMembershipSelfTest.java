import com.comsol.model.GeomSequence;

import java.lang.reflect.Proxy;

/** Offline regression for a point inside a face AABB but outside its mapped face. */
public final class S06FluxExportMembershipSelfTest {
  private S06FluxExportMembershipSelfTest() {}

  public static void main(String[] args) {
    GeomSequence triangle = (GeomSequence) Proxy.newProxyInstance(
        GeomSequence.class.getClassLoader(), new Class<?>[] {GeomSequence.class}, (proxy, method, values) -> {
          if ("faceParamRange".equals(method.getName())) return new double[] {0.0, 1.0, 0.0, 1.0};
          if ("faceX".equals(method.getName())) {
            double[][] param = (double[][]) values[1];
            double[][] result = new double[param.length][3];
            for (int i = 0; i < param.length; i++) {
              double u = param[i][0], v = param[i][1];
              result[i][0] = u;
              result[i][1] = (1.0 - u) * v;
              result[i][2] = 0.0;
            }
            return result;
          }
          throw new UnsupportedOperationException(method.getName());
        });

    S06FluxExport1003.Sample inside = new S06FluxExport1003.Sample(0.2, 0.2, 0.0);
    if (!S06FluxExport1003.findMatchingFace(triangle, new int[] {137}, inside, 1e-10)
        || inside.faceEntity != 137 || inside.faceResidual > 1e-10) {
      throw new AssertionError("a point mapped onto the selected face was not accepted");
    }

    S06FluxExport1003.Sample inBoundsOutsideFace = new S06FluxExport1003.Sample(0.9, 0.9, 0.0);
    if (S06FluxExport1003.findMatchingFace(triangle, new int[] {137}, inBoundsOutsideFace, 1e-10)) {
      throw new AssertionError("an AABB-only point outside the selected face was accepted");
    }
    System.out.println("S06_FACE_MEMBERSHIP_SELF_TEST=PASS_SYNTHETIC_GEOMETRY_ONLY");
  }
}
