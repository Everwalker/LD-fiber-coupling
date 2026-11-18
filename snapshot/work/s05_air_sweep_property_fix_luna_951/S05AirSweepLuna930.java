import com.comsol.model.MeshFeature;
import com.comsol.model.Model;
import com.comsol.model.util.ModelUtil;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;
import java.util.TreeSet;

/**
 * S05 mesh-only candidate. Run with this directory as the process working directory.
 * It loads the frozen 390a model by copy, changes only a new mesh sequence, and saves
 * the diagnostic model to a new relative path. It creates no study and solves nothing.
 */
public final class S05AirSweepLuna930 {
  private static final String INPUT = "<LOCAL_PATH>";
  private static final String OUTPUT = "s05_air_sweep_luna_930.mph";
  private static final String COMPONENT = "air3d";
  private static final String GEOMETRY = "gAir";
  private static final String NEW_MESH = "mesh930";
  private static final double GEOMETRY_TOLERANCE_M = 1e-12;

  private static final class Segment {
    final String name;
    final int domain;
    final int[] sourceFaces;
    final int[] targetFaces;
    final double sourceZ;
    final double targetZ;
    final int layers;

    Segment(String name, int domain, int[] sourceFaces, int[] targetFaces,
            double sourceZ, double targetZ, int layers) {
      this.name = name;
      this.domain = domain;
      this.sourceFaces = sourceFaces;
      this.targetFaces = targetFaces;
      this.sourceZ = sourceZ;
      this.targetZ = targetZ;
      this.layers = layers;
    }
  }

  private S05AirSweepLuna930() {}

  public static void main(String[] args) throws Exception {
    try {
      String jobId = System.getenv("LD_S05_JOB_ID");
      if (jobId == null || !jobId.matches("job_run_951_[0-9]{8}T[0-9]{9}Z_[0-9a-f]{8}")) {
        throw new IllegalStateException("a fresh 951 runtime job ID is required");
      }
      run(jobId);
    } catch (Exception e) {
      System.out.println("LD_S05_BLOCKED=" + e);
      throw e;
    }
  }

  private static void run(String jobId) throws Exception {
    Model model = ModelUtil.loadCopy("S05AirSweepLuna930", INPUT);
    if (model.study().tags().length != 0 || model.sol().tags().length != 0) {
      throw new IllegalStateException("input is not the expected study-free/solution-free 390a model");
    }
    if (!contains(model.component(COMPONENT).mesh().tags(), "mesh390")) {
      throw new IllegalStateException("the original mesh390 node is missing");
    }
    if (contains(model.component(COMPONENT).mesh().tags(), NEW_MESH)) {
      throw new IllegalStateException("new mesh tag already exists in the input model");
    }
    int originalMeshElements = model.component(COMPONENT).mesh("mesh390").getNumElem();
    if (originalMeshElements != 0) {
      throw new IllegalStateException("mesh390 is expected to remain unbuilt; found " + originalMeshElements);
    }
    System.out.println("LD_S05_INPUT=" + INPUT + ",LOAD_COPY=YES,ORIGINAL_MESH390_ELEMENTS=" + originalMeshElements);

    double lambda = parameter(model, "lambda0");
    double hmax = parameter(model, "hmaxAir");
    parameter(model, "hminAir");
    double budget = parameter(model, "meshElemMax");
    parameter(model, "gap_tip");
    if (Math.abs(lambda - 974e-9) > 1e-15 || Math.abs(hmax - 0.15e-6) > 1e-18
        || Math.abs(model.param().evaluate("hminAir") - 0.025e-6) > 1e-18
        || Math.abs(model.param().evaluate("gap_tip") - 5.65e-6) > 1e-18) {
      throw new IllegalStateException("frozen wavelength, air size, or source gap differs from 390a");
    }
    System.out.println("LD_S05_MESH_SIZE=" + "hmaxAir=" + hmax + ",hminAir="
      + model.param().evaluate("hminAir") + ",BUDGET=" + budget + ",BUDGET_SCOPE=ONE_MESH_DIAGNOSTIC");

    int[] physical = entities(model, "gAir_innerPhysical_dom", 3);
    int[] pml = entities(model, "pmlDomains", 3);
    Set<Integer> physicalSet = intSet(physical);
    Set<Integer> pmlSet = intSet(pml);
    TreeSet<Integer> partition = new TreeSet<Integer>(physicalSet);
    if (!Collections.disjoint(physicalSet, pmlSet)) {
      throw new IllegalStateException("physical-air and PML domain selections overlap");
    }
    partition.addAll(pmlSet);
    if (physical.length != 3 || pml.length != 42
        || partition.size() != model.component(COMPONENT).geom(GEOMETRY).getNDomains()) {
      throw new IllegalStateException("named physical/PML selections do not partition the 45-domain 390a geometry");
    }
    int[] pmlCoordinateDomains = model.component(COMPONENT).coordSystem("pmlBox").selection().entities(3);
    Arrays.sort(pmlCoordinateDomains);
    if (!Arrays.equals(pml, pmlCoordinateDomains)) {
      throw new IllegalStateException("pmlDomains and pmlBox coordinate-system domains differ");
    }
    System.out.println("LD_S05_DOMAINS=PHYSICAL," + Arrays.toString(physical)
      + ",PML," + Arrays.toString(pml) + ",TOTAL," + partition.size()
      + ",PML_SCALING," + model.component(COMPONENT).coordSystem("pmlBox").getString("ScalingType"));
    System.out.println("LD_S05_MATERIAL_AIR_N=" + Arrays.toString(model.component(COMPONENT)
      .material("air").propertyGroup("RefractiveIndex").getStringArray("n"))
      + ",KI=" + Arrays.toString(model.component(COMPONENT)
      .material("air").propertyGroup("RefractiveIndex").getStringArray("ki")));

    int[] sourceFaces = entities(model, "sourcePhysicalFaces", 2);
    int[] monitorFaces = entities(model, "monitorPhysicalFaces", 2);
    if (sourceFaces.length != 1 || monitorFaces.length != 1) {
      throw new IllegalStateException("expected one named source face and one named monitor face; found "
        + sourceFaces.length + " and " + monitorFaces.length);
    }
    int[] sourceAdjacent = model.component(COMPONENT).geom(GEOMETRY).getAdj(2, 3, sourceFaces[0]);
    int[] monitorAdjacent = model.component(COMPONENT).geom(GEOMETRY).getAdj(2, 3, monitorFaces[0]);
    int[] chain = S05AirSweepGroups.chainDomains(sourceAdjacent, monitorAdjacent, physical);
    System.out.println("LD_S05_NAMED_FACES=SOURCE," + Arrays.toString(sourceFaces)
      + ",SOURCE_ADJ," + Arrays.toString(sourceAdjacent) + ",MONITOR," + Arrays.toString(monitorFaces)
      + ",MONITOR_ADJ," + Arrays.toString(monitorAdjacent));
    System.out.println("LD_S05_DYNAMIC_AIR_CHAIN=SOURCE_SIDE," + chain[0]
      + ",SOURCE_TO_MONITOR," + chain[1] + ",MONITOR_SIDE," + chain[2]);
    printFace(model, "SOURCE", sourceFaces);
    printFace(model, "MONITOR", monitorFaces);

    int[] interfaceFaces = entities(model, "airPmlInterfaces", 2);
    int[] derivedInterfaceFaces = deriveAirPmlInterfaces(model, physicalSet, pmlSet);
    if (!Arrays.equals(interfaceFaces, derivedInterfaceFaces)) {
      System.out.println("LD_S05_AIR_PML_INTERFACE_SELECTION_MISMATCH=NAMED," + Arrays.toString(interfaceFaces)
        + ",DERIVED_GETADJ," + Arrays.toString(derivedInterfaceFaces));
      throw new IllegalStateException("airPmlInterfaces does not cover the dynamically derived physical/PML interface set");
    }
    System.out.println("LD_S05_AIR_PML_INTERFACE_SELECTION_MATCH=YES,GETADJ," + Arrays.toString(derivedInterfaceFaces));
    for (int face : interfaceFaces) {
      int[] adjacent = model.component(COMPONENT).geom(GEOMETRY).getAdj(2, 3, face);
      if (adjacent.length != 2 || !isAirPmlPair(adjacent, physicalSet, pmlSet)) {
        throw new IllegalStateException("airPmlInterfaces contains a face without one physical and one PML neighbor: "
          + face + " adjacent=" + Arrays.toString(adjacent));
      }
      System.out.println("LD_S05_AIR_PML_FACE=" + face + ",ADJ=" + Arrays.toString(adjacent));
    }
    System.out.println("LD_S05_AIR_PML_INTERFACE_FACE_COUNT=" + interfaceFaces.length);

    double sourceZ = planarZ(model, sourceFaces[0], "source");
    double monitorZ = planarZ(model, monitorFaces[0], "monitor");
    if (Math.abs(sourceZ - monitorZ) <= GEOMETRY_TOLERANCE_M) {
      throw new IllegalStateException("source and monitor planes are not axially separated");
    }
    Segment sourceSide = makeSegment(model, "source-side", chain[0], sourceFaces,
      null, hmax);
    Segment core = makeSegment(model, "source-to-monitor", chain[1], sourceFaces,
      monitorFaces, hmax);
    Segment monitorSide = makeSegment(model, "monitor-side", chain[2], monitorFaces,
      null, hmax);
    if (!Arrays.equals(core.targetFaces, monitorFaces)) {
      throw new IllegalStateException("the dynamically found middle-domain endpoint differs from monitorPhysicalFaces: "
        + Arrays.toString(core.targetFaces) + " versus " + Arrays.toString(monitorFaces));
    }
    Segment[] segments = new Segment[] {sourceSide, core, monitorSide};
    for (Segment segment : segments) printSegment(model, segment);
    System.out.println("LD_S05_CROSS_SECTION_TOPOLOGY=UNKNOWN_BEFORE_BUILD,"
      + "BOUNDING_BOX_AND_ADJACENCY_ONLY,SWEEP_BUILD_IS_AUTHORITATIVE_NO_FALLBACK");

    model.component(COMPONENT).mesh().create(NEW_MESH);
    model.component(COMPONENT).mesh(NEW_MESH).automatic(false);
    String[] initialFeatures = model.component(COMPONENT).mesh(NEW_MESH).feature().tags();
    for (int i = initialFeatures.length - 1; i >= 0; i--) {
      if (!initialFeatures[i].equals("size")) {
        model.component(COMPONENT).mesh(NEW_MESH).feature().remove(initialFeatures[i]);
      }
    }
    model.component(COMPONENT).mesh(NEW_MESH).feature("size").set("custom", "on");
    model.component(COMPONENT).mesh(NEW_MESH).feature("size").set("hmax", "hmaxAir");
    model.component(COMPONENT).mesh(NEW_MESH).feature("size").set("hmin", "hminAir");

    MeshFeature sourceTri = model.component(COMPONENT).mesh(NEW_MESH).create("sourceTri", "FreeTri");
    sourceTri.selection().geom(GEOMETRY, 2);
    sourceTri.selection().set(sourceFaces);
    System.out.println("LD_S05_FREETRI_SOURCE_FACE=" + Arrays.toString(sourceFaces));

    addSweep(model, sourceSide);
    addSweep(model, core);
    addSweep(model, monitorSide);

    MeshFeature pmlTet = model.component(COMPONENT).mesh(NEW_MESH).create("pmlTet", "FreeTet");
    pmlTet.selection().geom(GEOMETRY, 3);
    pmlTet.selection().set(pml);
    System.out.println("LD_S05_PML_FREETET_DOMAINS=" + Arrays.toString(pml));

    System.out.println("LD_S05_MESH_RUN=START,MESH_ONLY=YES");
    model.component(COMPONENT).mesh(NEW_MESH).run();
    int totalElements = model.component(COMPONENT).mesh(NEW_MESH).getNumElem();
    if (totalElements <= 0) throw new IllegalStateException("mesh run returned no elements");
    System.out.println("LD_S05_MESH_ELEMENTS_TOTAL=" + totalElements);
    System.out.println("LD_S05_ELEMENT_TYPES=" + Arrays.toString(model.component(COMPONENT).mesh(NEW_MESH).getTypes()));
    reportDomainElements(model, physical, pml);
    reportBoundaryTriangles(model, sourceFaces, monitorFaces, interfaceFaces);
    reportQuality(model);
    System.out.println("LD_S05_ACTUAL_MIN_MAX_ELEMENT_EDGE=UNKNOWN,"
      + "REASON=diagnostic records planned axial distribution and mesh quality only");
    System.out.println("LD_S05_ACTUAL_FACE_MESH_SIZE=UNKNOWN,"
      + "REASON=mesh size bounds are inputs and are not a measured maximum edge length");

    model.save(OUTPUT);
    Path outputPath = Paths.get(OUTPUT);
    if (!Files.isRegularFile(outputPath) || Files.size(outputPath) <= 0) {
      throw new IllegalStateException("explicitly saved model is missing or empty");
    }
    String modelSha256 = sha256(outputPath);
    String successMarker = "LD_S05_MODEL_SUCCESS=YES|CANDIDATE=S05_AIR_SWEEP_PROPERTY_FIX_LUNA_951"
      + "|JOB=" + jobId + "|OUTPUT=" + OUTPUT + "|SHA256=" + modelSha256;
    Files.write(Paths.get("model_success_951.marker"),
      (successMarker + "\n").getBytes(StandardCharsets.UTF_8),
      StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
    System.out.println(successMarker);
    System.out.println("LD_S05_OUTPUT=" + OUTPUT + ",SAVED_AFTER_MESH_ONLY=YES");
    System.out.println(totalElements > budget
      ? "LD_S05_BUDGET=OVER_DIAGNOSTIC_ONLY_NO_PHYSICS_GATE"
      : "LD_S05_BUDGET=WITHIN_THIS_ATTEMPT_ONLY_NO_PHYSICS_GATE");
    System.out.println("LD_S05_COMPLETE=MESH_ONLY_NO_STUDY_NO_SOLVE_NO_PHYSICS_CHANGE");
  }

  private static Segment makeSegment(Model model, String name, int domain, int[] sourceFaces,
                                     int[] requiredTargetFaces, double hmax) {
    double[] domainBox = boundingBox(model, 3, domain);
    double sourceZ = planarZ(model, sourceFaces[0], name + " source");
    double targetZ = S05AirSweepGroups.oppositeEnd(
      domainBox[4], domainBox[5], sourceZ, GEOMETRY_TOLERANCE_M);
    int[] adjacentFaces = model.component(COMPONENT).geom(GEOMETRY).getAdj(3, 2, domain);
    for (int face : adjacentFaces) {
      System.out.println("LD_S05_DOMAIN_FACE_BBOX=SEGMENT," + name + ",DOMAIN," + domain
        + ",FACE," + face + ",BBOX," + Arrays.toString(boundingBox(model, 2, face)));
    }
    int[] targetFaces = planarFacesAt(model, adjacentFaces, targetZ);
    System.out.println("LD_S05_ENDPOINT_FACE_GROUP=SEGMENT," + name + ",DOMAIN," + domain
      + ",SOURCE," + Arrays.toString(sourceFaces) + ",TARGET_Z," + targetZ
      + ",ADJACENT_FACES," + Arrays.toString(adjacentFaces)
      + ",PLANAR_TARGETS," + Arrays.toString(targetFaces));
    if (targetFaces.length == 0) {
      throw new IllegalStateException(name + " domain " + domain
        + " has no adjacent planar target faces at z=" + targetZ);
    }
    if (requiredTargetFaces != null && !Arrays.equals(targetFaces, requiredTargetFaces)) {
      throw new IllegalStateException(name + " target differs from its required named selection: "
        + Arrays.toString(targetFaces) + " versus " + Arrays.toString(requiredTargetFaces));
    }
    double length = Math.abs(targetZ - sourceZ);
    int layers = S05AirSweepGroups.layerCount(length, hmax);
    return new Segment(name, domain, sourceFaces, targetFaces, sourceZ, targetZ, layers);
  }

  private static void addSweep(Model model, Segment segment) {
    String tag = segment.name.equals("source-side") ? "sweepSourceSide"
      : segment.name.equals("source-to-monitor") ? "sweepCore" : "sweepMonitorSide";
    MeshFeature sweep = model.component(COMPONENT).mesh(NEW_MESH).create(tag, "Sweep");
    sweep.selection().geom(GEOMETRY, 3);
    sweep.selection().set(new int[] {segment.domain});
    sweep.selection("sourceface").geom(GEOMETRY, 2);
    sweep.selection("sourceface").set(segment.sourceFaces);
    sweep.selection("targetface").geom(GEOMETRY, 2);
    sweep.selection("targetface").set(segment.targetFaces);
    sweep.set("sweeppath", "straight");
    MeshFeature distribution = sweep.create("axialDistribution", "Distribution");
    distribution.selection().geom(GEOMETRY, 3);
    distribution.selection().set(new int[] {segment.domain});
    distribution.set("numelem", segment.layers);
    System.out.println("LD_S05_SWEEP_FEATURE=" + tag + ",DOMAIN," + segment.domain
      + ",SOURCE," + Arrays.toString(segment.sourceFaces) + ",TARGET," + Arrays.toString(segment.targetFaces)
      + ",PATH,straight,LAYERS," + segment.layers);
  }

  private static String sha256(Path path) throws Exception {
    MessageDigest digest = MessageDigest.getInstance("SHA-256");
    try (InputStream input = Files.newInputStream(path)) {
      byte[] buffer = new byte[65536];
      int read;
      while ((read = input.read(buffer)) != -1) digest.update(buffer, 0, read);
    }
    byte[] hash = digest.digest();
    char[] hex = "0123456789abcdef".toCharArray();
    StringBuilder value = new StringBuilder(hash.length * 2);
    for (byte item : hash) {
      value.append(hex[(item >>> 4) & 0x0f]);
      value.append(hex[item & 0x0f]);
    }
    return value.toString();
  }

  private static void reportDomainElements(Model model, int[] physical, int[] pml) {
    int[] all = new int[physical.length + pml.length];
    System.arraycopy(physical, 0, all, 0, physical.length);
    System.arraycopy(pml, 0, all, physical.length, pml.length);
    String[] types = model.component(COMPONENT).mesh(NEW_MESH).getTypes();
    if (types.length == 0) throw new IllegalStateException("mesh type list is empty after mesh generation");
    for (int domain : all) {
      StringBuilder counts = new StringBuilder();
      int domainElements = 0;
      for (String type : types) {
        try {
          int[][] elems = model.component(COMPONENT).mesh(NEW_MESH).getElem(type, 3, domain);
          int count = elems.length == 0 ? 0 : elems[0].length;
          if (count > 0) {
            counts.append(type).append(':').append(count).append(';');
            domainElements += count;
          }
        } catch (Exception e) {
          counts.append(type).append(":UNKNOWN(").append(e.getClass().getSimpleName()).append(");");
        }
      }
      System.out.println("LD_S05_DOMAIN_ELEMENTS=" + domain + "," + counts);
      if (domainElements == 0) {
        throw new IllegalStateException("no volume elements were read for selected domain " + domain);
      }
    }
  }

  private static void reportBoundaryTriangles(Model model, int[] sourceFaces, int[] monitorFaces,
                                              int[] interfaceFaces) {
    for (int face : sourceFaces) requireTriangles(model, "SOURCE", face);
    for (int face : monitorFaces) requireTriangles(model, "MONITOR", face);
    boolean allReadable = true;
    for (int face : interfaceFaces) {
      int count = reportTriangles(model, "AIR_PML", face);
      if (count == 0) throw new IllegalStateException("no surface triangles on air/PML interface face " + face);
      if (count < 0) allReadable = false;
    }
    System.out.println("LD_S05_AIR_PML_CONFORMITY=" + (allReadable
      ? "SHARED_GEOMETRIC_INTERFACE_MESH_READBACK_PRESENT"
      : "UNKNOWN_FOR_UNREADABLE_FACE_MESH_QUERY"));
  }

  private static void requireTriangles(Model model, String role, int face) {
    int count = reportTriangles(model, role, face);
    if (count == 0) throw new IllegalStateException("no surface triangles on " + role + " face " + face);
  }

  private static int reportTriangles(Model model, String role, int face) {
    try {
      int[][] triangles = model.component(COMPONENT).mesh(NEW_MESH).getElem("tri", 2, face);
      int count = triangles.length == 0 ? 0 : triangles[0].length;
      System.out.println("LD_S05_FACE_TRIANGLES=" + role + ",FACE," + face + ",COUNT," + count);
      return count;
    } catch (Exception e) {
      System.out.println("LD_S05_FACE_TRIANGLES=UNKNOWN," + role + ",FACE," + face
        + ",REASON," + e.getClass().getSimpleName());
      return -1;
    }
  }

  private static void reportQuality(Model model) {
    try {
      System.out.println("LD_S05_MESH_QUALITY=MIN," + model.component(COMPONENT).mesh(NEW_MESH).getMinQuality()
        + ",MEAN," + model.component(COMPONENT).mesh(NEW_MESH).getMeanQuality());
    } catch (Exception e) {
      System.out.println("LD_S05_MESH_QUALITY=UNKNOWN,REASON," + e.getClass().getSimpleName());
    }
    try {
      System.out.println("LD_S05_MESH_QUALITY_DISTR_10="
        + Arrays.toString(model.component(COMPONENT).mesh(NEW_MESH).getQualityDistr(10)));
    } catch (Exception e) {
      System.out.println("LD_S05_MESH_QUALITY_DISTR_10=UNKNOWN,REASON," + e.getClass().getSimpleName());
    }
  }

  private static double parameter(Model model, String name) {
    String expression = model.param().get(name);
    double value = model.param().evaluate(name);
    System.out.println("LD_S05_PARAM=" + name + ",EXPR," + expression + ",VALUE," + value);
    return value;
  }

  private static int[] entities(Model model, String selection, int dimension) {
    int[] values = model.component(COMPONENT).selection(selection).entities(dimension);
    Arrays.sort(values);
    if (values.length == 0) throw new IllegalStateException("empty named selection " + selection);
    System.out.println("LD_S05_SELECTION=" + selection + ",DIM," + dimension + ",ENTITIES," + Arrays.toString(values));
    return values;
  }

  private static void printFace(Model model, String role, int[] faces) {
    for (int face : faces) {
      System.out.println("LD_S05_FACE_GEOMETRY=" + role + ",FACE," + face
        + ",ADJ," + Arrays.toString(model.component(COMPONENT).geom(GEOMETRY).getAdj(2, 3, face))
        + ",AREA," + area(model, new int[] {face}) + ",BBOX," + Arrays.toString(boundingBox(model, 2, face)));
    }
  }

  private static double planarZ(Model model, int face, String role) {
    double[] box = boundingBox(model, 2, face);
    if (Math.abs(box[5] - box[4]) > GEOMETRY_TOLERANCE_M) {
      throw new IllegalStateException(role + " face " + face + " is not an axial plane: " + Arrays.toString(box));
    }
    return (box[4] + box[5]) / 2.0;
  }

  private static int[] planarFacesAt(Model model, int[] faces, double z) {
    double[][] boxes = new double[faces.length][];
    for (int i = 0; i < faces.length; i++) boxes[i] = boundingBox(model, 2, faces[i]);
    return S05AirSweepGroups.planeFaces(faces, boxes, z, GEOMETRY_TOLERANCE_M);
  }

  private static double[] boundingBox(Model model, int dimension, int entity) {
    model.component(COMPONENT).measure().selection().geom(GEOMETRY, dimension);
    model.component(COMPONENT).measure().selection().set(new int[] {entity});
    return model.component(COMPONENT).measure().getBoundingBox();
  }

  private static double area(Model model, int[] faces) {
    model.component(COMPONENT).measure().selection().geom(GEOMETRY, 2);
    model.component(COMPONENT).measure().selection().set(faces);
    return model.component(COMPONENT).measure().getArea();
  }

  private static boolean isAirPmlPair(int[] adjacent, Set<Integer> physical, Set<Integer> pml) {
    return (physical.contains(Integer.valueOf(adjacent[0])) && pml.contains(Integer.valueOf(adjacent[1])))
      || (pml.contains(Integer.valueOf(adjacent[0])) && physical.contains(Integer.valueOf(adjacent[1])));
  }

  private static int[] deriveAirPmlInterfaces(Model model, Set<Integer> physical, Set<Integer> pml) {
    TreeSet<Integer> result = new TreeSet<Integer>();
    int faceCount = model.component(COMPONENT).geom(GEOMETRY).getNFaces();
    for (int face = 1; face <= faceCount; face++) {
      int[] adjacent = model.component(COMPONENT).geom(GEOMETRY).getAdj(2, 3, face);
      if (adjacent.length == 2 && isAirPmlPair(adjacent, physical, pml)) {
        result.add(Integer.valueOf(face));
      }
    }
    int[] faces = new int[result.size()];
    int i = 0;
    for (Integer face : result) faces[i++] = face.intValue();
    return faces;
  }

  private static Set<Integer> intSet(int[] values) {
    Set<Integer> result = new HashSet<Integer>();
    for (int value : values) result.add(Integer.valueOf(value));
    return result;
  }

  private static boolean contains(String[] values, String wanted) {
    for (String value : values) if (value.equals(wanted)) return true;
    return false;
  }

  private static void printSegment(Model model, Segment segment) {
    System.out.println("LD_S05_SEGMENT=" + segment.name + ",DOMAIN," + segment.domain
      + ",SOURCE," + Arrays.toString(segment.sourceFaces) + ",TARGET," + Arrays.toString(segment.targetFaces)
      + ",Z_M," + segment.sourceZ + "," + segment.targetZ
      + ",LENGTH_M," + Math.abs(segment.targetZ - segment.sourceZ)
      + ",PLANNED_LAYERS," + segment.layers
      + ",PLANNED_DZ_M," + (Math.abs(segment.targetZ - segment.sourceZ) / segment.layers)
      + ",SOURCE_AREA_M2," + area(model, segment.sourceFaces)
      + ",TARGET_AREA_M2," + area(model, segment.targetFaces)
      + ",SOURCE_BBOX," + Arrays.toString(boundingBox(model, 2, segment.sourceFaces))
      + ",TARGET_BBOX," + Arrays.toString(boundingBox(model, 2, segment.targetFaces)));
  }

  private static double[] boundingBox(Model model, int dimension, int[] entities) {
    model.component(COMPONENT).measure().selection().geom(GEOMETRY, dimension);
    model.component(COMPONENT).measure().selection().set(entities);
    return model.component(COMPONENT).measure().getBoundingBox();
  }
}
