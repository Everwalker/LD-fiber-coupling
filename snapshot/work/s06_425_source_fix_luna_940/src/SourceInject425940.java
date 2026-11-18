import com.comsol.model.Model;
import com.comsol.model.util.ModelUtil;
import java.util.Arrays;
import java.util.Collections;
import java.util.Set;
import java.util.TreeSet;

/**
 * Offline-prepared S06 source-injection candidate for the existing 425 BASE model.
 * Run only after non-author review, real G03a/G03b/G17 evidence, and live
 * license/resource/model-lock/single-writer checks. At runtime it changes only
 * source variables and sheet currents, then saves one relative file in the
 * caller's exclusive job working directory. It does not validate direction.
 */
public final class SourceInject425940 {
  private static final String INPUT =
      "<LOCAL_PATH>";
  private static final String COMPONENT = "device3d";
  private static final String GEOMETRY = "gdev";
  private static final String PHYSICS = "ewfd";
  private static final String VARIABLE_TAG = "s06Source940";
  private static final String SOURCE_SELECTION = "sourcePhysicalFaces";
  private static final String SOURCE_PLANE = "sourcePlane";
  private static final String MONITOR_SELECTION = "monitorPhysicalFaces";
  private static final String OUTPUT_MODEL = "ldfiber_s06_source_425_940.mph";

  private SourceInject425940() {}

  public static void main(String[] args) throws Exception {
    if (args.length != 0) throw new IllegalArgumentException("This frozen candidate takes no arguments");
    run();
  }

  public static Model run() throws Exception {
    Model model = ModelUtil.loadCopy("SourceInject425940", INPUT);
    requireNoMeshStudyOrSolution(model);

    double dx = model.param().evaluate("dx_tip");
    double gap = model.param().evaluate("gap_tip");
    double radius = model.param().evaluate("R_tip");
    double alpha = model.param().evaluate("alpha_tip");
    double wavelength = model.param().evaluate("lambdaD");
    double sourceReferenceZ = model.param().evaluate("zSrcRef");
    double numericalAperture = model.param().evaluate("NAD");
    double nClad = model.param().evaluate("nCladD");
    double nCore = model.param().evaluate("nCoreD");

    requireNear("BASE dx_tip", dx, 0.0, 1e-15);
    requireNear("gap_tip", gap, 5.65e-6, 1e-15);
    requireNear("R_tip", radius, 3.25e-6, 1e-15);
    requireNear("alpha_tip", alpha, Math.PI / 4.0, 1e-12);
    requireNear("lambdaD", wavelength, 974e-9, 1e-15);
    requireNear("zSrcRef", sourceReferenceZ, -gap, 1e-15);

    int[] sourceFaces = model.component(COMPONENT).selection(SOURCE_SELECTION).entities(2);
    int[] sourcePlaneFaces = model.component(COMPONENT).selection(SOURCE_PLANE).entities(2);
    int[] magneticFaces = model.component(COMPONENT).physics(PHYSICS)
        .feature("sheetM").selection().entities(2);
    int[] electricFaces = model.component(COMPONENT).physics(PHYSICS)
        .feature("sheetM").feature("sheetJ").selection().entities(2);
    requireOneFace(sourceFaces, SOURCE_SELECTION);
    requireFaceMember(sourceFaces[0], sourcePlaneFaces, SOURCE_PLANE);
    requireSameFaces(sourceFaces, magneticFaces, SOURCE_SELECTION + " vs sheetM");
    requireSameFaces(sourceFaces, electricFaces, SOURCE_SELECTION + " vs sheetJ");

    model.component(COMPONENT).measure().selection().geom(GEOMETRY, 2);
    model.component(COMPONENT).measure().selection().set(sourceFaces);
    double[] sourceBounds = model.component(COMPONENT).measure().getBoundingBox();
    requireBounds(sourceBounds, gap);
    double sourceArea = model.component(COMPONENT).measure().getArea();

    Set<Integer> air = domains(model, "airDomains");
    Set<Integer> core = domains(model, "gdev_coreShaped_dom");
    Set<Integer> clad = domains(model, "gdev_cladShaped_dom");
    Set<Integer> inner = domains(model, "gdev_innerPhysical_dom");
    Set<Integer> pml = domains(model, "pmlDomains");
    verifySourceAdjacency(model, sourceFaces, air, inner, pml);
    requireDisjoint(air, core, clad);
    Set<Integer> materialDomains = new TreeSet<Integer>(air);
    materialDomains.addAll(core);
    materialDomains.addAll(clad);
    Set<Integer> physicalAndPml = new TreeSet<Integer>(inner);
    physicalAndPml.addAll(pml);
    if (!materialDomains.equals(physicalAndPml)
        || materialDomains.size() != model.component(COMPONENT).geom(GEOMETRY).getNDomains())
      throw new IllegalStateException("Material and physical/PML domain partition changed");
    String[] materialReadbacks = new String[] {
      requireMaterial(model, "matAirD", air, "1", "0"),
      requireMaterial(model, "matCoreD", core, "nCoreD", "0"),
      requireMaterial(model, "matCladD", clad, "nCladD", "0")
    };
    requireSameSet(toSet(model.component(COMPONENT).coordSystem("pmlOpticsD")
        .selection().entities(3)), pml, "pmlOpticsD vs pmlDomains");
    String pmlScaling = model.component(COMPONENT).coordSystem("pmlOpticsD").getString("ScalingType");
    if (!"Cartesian".equals(pmlScaling))
      throw new IllegalStateException("Unexpected PML scaling: " + pmlScaling);

    int[] monitorFaces = model.component(COMPONENT).selection(MONITOR_SELECTION).entities(2);
    requireNonempty(monitorFaces, MONITOR_SELECTION);
    String[] portReadbacks = new String[2];
    for (int i = 0; i < 2; i++) {
      String tag = i == 0 ? "port1" : "port2";
      String expectedName = Integer.toString(i + 1);
      if (!"Numeric".equals(model.component(COMPONENT).physics(PHYSICS).feature(tag).getString("PortType"))
          || !"off".equals(model.component(COMPONENT).physics(PHYSICS).feature(tag).getString("PortExcitation"))
          || !model.component(COMPONENT).physics(PHYSICS).feature(tag).getBoolean("PortSlit")
          || !expectedName.equals(model.component(COMPONENT).physics(PHYSICS).feature(tag).getString("PortName")))
        throw new IllegalStateException("Existing passive Numeric slit port changed: " + tag);
      requireSameFaces(monitorFaces,
          model.component(COMPONENT).physics(PHYSICS).feature(tag).selection().entities(2),
          tag + " vs " + MONITOR_SELECTION);
      String orientation = model.component(COMPONENT).physics(PHYSICS).feature(tag)
          .getString("PortOrientation");
      portReadbacks[i] = tag + ":name=" + expectedName + ",orientation_observed_only=" + orientation
          + ",faces=" + Arrays.toString(model.component(COMPONENT).physics(PHYSICS)
              .feature(tag).selection().entities(2));
    }

    String[] zeroJms = new String[] {"0", "0", "0"};
    String[] zeroJs = new String[] {"0", "0", "0"};
    String[] initialJms = model.component(COMPONENT).physics(PHYSICS)
        .feature("sheetM").getStringArray("Jms0");
    String[] initialJs = model.component(COMPONENT).physics(PHYSICS)
        .feature("sheetM").feature("sheetJ").getStringArray("Js0");
    if (!Arrays.equals(zeroJms, initialJms) || !Arrays.equals(zeroJs, initialJs))
      throw new IllegalStateException("425 BASE source is not the expected zero-current preparation");
    String side = model.component(COMPONENT).physics(PHYSICS)
        .feature("sheetM").feature("sheetJ").getString("side");

    String[] existingVariableFeatures = model.component(COMPONENT).variable().tags();
    if (existingVariableFeatures.length != 0)
      throw new IllegalStateException("BASE variable namespace needs review before source insertion: "
          + Arrays.toString(existingVariableFeatures));
    SourcePweVars701.define(model, COMPONENT, VARIABLE_TAG);
    String[] jms = new String[] {"ld_s355_jms_x", "ld_s355_jms_y", "ld_s355_jms_z"};
    String[] js = new String[] {"ld_s355_js_x", "ld_s355_js_y", "ld_s355_js_z"};
    model.component(COMPONENT).physics(PHYSICS).feature("sheetM").set("Jms0", jms);
    model.component(COMPONENT).physics(PHYSICS).feature("sheetM").feature("sheetJ").set("Js0", js);
    String[] actualJms = model.component(COMPONENT).physics(PHYSICS)
        .feature("sheetM").getStringArray("Jms0");
    String[] actualJs = model.component(COMPONENT).physics(PHYSICS)
        .feature("sheetM").feature("sheetJ").getStringArray("Js0");
    if (!Arrays.equals(jms, actualJms) || !Arrays.equals(js, actualJs))
      throw new IllegalStateException("Surface-current property readback mismatch");

    System.out.println("S06_940_MODEL=425_BASE_COPY");
    System.out.println("S06_940_PARAMS=dx_tip:" + dx + ",gap_tip:" + gap + ",R_tip:" + radius
        + ",alpha_tip:" + alpha + ",lambdaD:" + wavelength + ",zSrcRef:" + sourceReferenceZ
        + ",NAD:" + numericalAperture + ",nCladD:" + nClad + ",nCoreD:" + nCore);
    System.out.println("S06_940_SOURCE_FACE=selection:" + SOURCE_SELECTION + ",entities:"
        + Arrays.toString(sourceFaces) + ",bbox:" + Arrays.toString(sourceBounds)
        + ",area_m2:" + sourceArea + ",z_expected_m:" + (-gap));
    System.out.println("S06_940_DOMAINS=air:" + air.size() + ",core:" + core.size()
        + ",clad:" + clad.size() + ",pml:" + pml.size() + ",total:" + materialDomains.size());
    System.out.println("S06_940_MATERIALS=" + Arrays.toString(materialReadbacks));
    System.out.println("S06_940_PORTS=" + Arrays.toString(portReadbacks));
    System.out.println("S06_940_VARIABLE_NAMESPACE=NO_PREEXISTING_COMPONENT_VARIABLE_FEATURES");
    System.out.println("S06_940_SIDE_OBSERVED_ONLY=" + side);
    System.out.println("S06_940_NORMAL_AND_DIRECTION_NOT_VALIDATED;G03a_G03b_G17_AND_S05_EVIDENCE_REQUIRED");
    System.out.println("S06_940_JMS0=" + Arrays.toString(actualJms));
    System.out.println("S06_940_JS0=" + Arrays.toString(actualJs));
    System.out.println("S06_940_EXECUTION_SCOPE=SOURCE_ONLY_NO_MESH_NO_STUDY_NO_SOLVE");
    model.save(OUTPUT_MODEL);
    System.out.println("S06_940_SAVED=" + OUTPUT_MODEL + ",SOURCE_ONLY");
    System.out.println("S06_940_COMPLETE=SOURCE_INJECTION_SAVED_NO_MESH_STUDY_OR_SOLVE");
    return model;
  }

  private static void requireNoMeshStudyOrSolution(Model model) {
    if (model.study().tags().length != 0 || model.sol().tags().length != 0
        || model.component(COMPONENT).mesh().tags().length != 0)
      throw new IllegalStateException("Expected the 425 preparation model without mesh, study, or solution");
  }

  private static void requireNear(String name, double actual, double expected, double tolerance) {
    if (Math.abs(actual - expected) > tolerance)
      throw new IllegalStateException(name + " readback mismatch: " + actual + " != " + expected);
  }

  private static void requireBounds(double[] bounds, double gap) {
    if (bounds == null || bounds.length != 6
        || Math.abs(bounds[4] + gap) > 1e-10 || Math.abs(bounds[5] + gap) > 1e-10)
      throw new IllegalStateException("sourcePhysicalFaces must lie on z=-gap_tip; bbox="
          + Arrays.toString(bounds));
  }

  private static void requireFaceMember(int face, int[] candidates, String label) {
    requireNonempty(candidates, label);
    for (int candidate : candidates) if (candidate == face) return;
    throw new IllegalStateException("Explicit source face is not in semantic selection " + label
        + ": face=" + face + ", candidates=" + Arrays.toString(candidates));
  }

  private static void verifySourceAdjacency(Model model, int[] sourceFaces,
      Set<Integer> air, Set<Integer> inner, Set<Integer> pml) {
    for (int face : sourceFaces) {
      int[] adjacentDomains = model.component(COMPONENT).geom(GEOMETRY).getAdj(2, 3, face);
      if (adjacentDomains == null || adjacentDomains.length != 2)
        throw new IllegalStateException("Expected two actual adjacent domains at source face "
            + face + ": " + Arrays.toString(adjacentDomains));
      for (int domain : adjacentDomains) {
        if (!air.contains(domain) || !inner.contains(domain) || pml.contains(domain))
          throw new IllegalStateException("Source face is not bounded by physical air domains: face="
              + face + ", adjacent=" + Arrays.toString(adjacentDomains));
      }
      System.out.println("S06_940_SOURCE_ADJACENCY=face=" + face + ",adj="
          + Arrays.toString(adjacentDomains)
          + ",air_and_gdev_innerPhysical_dom=true,pml_excluded=true,normal_direction=NOT_INFERRED");
    }
  }

  private static void requireOneFace(int[] faces, String label) {
    requireNonempty(faces, label);
    if (faces.length != 1)
      throw new IllegalStateException(label + " must resolve to one actual face; found " + Arrays.toString(faces));
  }

  private static void requireNonempty(int[] values, String label) {
    if (values == null || values.length == 0)
      throw new IllegalStateException("Empty selection: " + label);
  }

  private static void requireSameFaces(int[] first, int[] second, String label) {
    requireNonempty(first, label + " first");
    requireNonempty(second, label + " second");
    int[] a = first.clone();
    int[] b = second.clone();
    Arrays.sort(a);
    Arrays.sort(b);
    if (!Arrays.equals(a, b))
      throw new IllegalStateException(label + " mismatch: " + Arrays.toString(a) + " vs " + Arrays.toString(b));
  }

  private static Set<Integer> domains(Model model, String selectionTag) {
    Set<Integer> values = toSet(model.component(COMPONENT).selection(selectionTag).entities(3));
    if (values.isEmpty()) throw new IllegalStateException("Empty domain selection: " + selectionTag);
    return values;
  }

  private static Set<Integer> toSet(int[] values) {
    Set<Integer> result = new TreeSet<Integer>();
    for (int value : values) result.add(value);
    return result;
  }

  private static void requireDisjoint(Set<Integer> air, Set<Integer> core, Set<Integer> clad) {
    if (!Collections.disjoint(air, core) || !Collections.disjoint(air, clad)
        || !Collections.disjoint(core, clad))
      throw new IllegalStateException("Air/core/cladding domains overlap");
  }

  private static String requireMaterial(Model model, String materialTag, Set<Integer> expected,
      String expectedN, String expectedKi) {
    Set<Integer> actual = toSet(model.component(COMPONENT).material(materialTag).selection().entities(3));
    if (!expected.equals(actual))
      throw new IllegalStateException("Material selection mismatch: " + materialTag);
    String[] n = model.component(COMPONENT).material(materialTag)
        .propertyGroup("RefractiveIndex").getStringArray("n");
    String[] ki = model.component(COMPONENT).material(materialTag)
        .propertyGroup("RefractiveIndex").getStringArray("ki");
    if (!Arrays.equals(n, new String[] {expectedN}) || !Arrays.equals(ki, new String[] {expectedKi}))
      throw new IllegalStateException("Material refractive-index readback mismatch: " + materialTag
          + ",n=" + Arrays.toString(n) + ",ki=" + Arrays.toString(ki));
    return materialTag + ":n=" + Arrays.toString(n) + ",ki=" + Arrays.toString(ki);
  }

  private static void requireSameSet(Set<Integer> actual, Set<Integer> expected, String label) {
    if (!expected.equals(actual)) throw new IllegalStateException(label + " mismatch: " + actual + " vs " + expected);
  }
}
