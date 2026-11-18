import com.comsol.model.*;
import com.comsol.model.util.*;
import java.util.*;

/** ADR-064: geometry-linked materials, PML and zero/passive nodes only. */
public class DeviceTipSetup425 {
  public static void main(String[] args) throws Exception { run(); }
  public static Model run() throws Exception {
    String dir="<LOCAL_PATH>";
    for(String id:new String[]{"base","lat1"}){
      String tag="DeviceTipSetup"+id;
      Model m=ModelUtil.loadCopy(tag,dir+"device_partition_"+id+"_365.mph");
      if(m.study().tags().length!=0||m.sol().tags().length!=0||m.component("device3d").physics().tags().length!=0||m.component("device3d").mesh().tags().length!=0)
        throw new IllegalStateException("Expected unmeshed geometry-only model: "+id);
      Set<Integer> core=domains(m,"gdev_coreShaped_dom"),clad=domains(m,"gdev_cladShaped_dom"),air=domains(m,"airDomains"),
        inner=domains(m,"gdev_innerPhysical_dom"),pml=domains(m,"pmlDomains");
      if(!Collections.disjoint(core,clad)||!Collections.disjoint(core,air)||!Collections.disjoint(clad,air)||!Collections.disjoint(inner,pml))
        throw new IllegalStateException("Material or PML overlap");
      Set<Integer> mats=new TreeSet<Integer>(air);mats.addAll(core);mats.addAll(clad);
      Set<Integer> region=new TreeSet<Integer>(inner);region.addAll(pml);
      if(!mats.equals(region)||mats.size()!=m.component("device3d").geom("gdev").getNDomains())
        throw new IllegalStateException("Incomplete material or PML partition");
      checkFaces(m,"sourcePhysicalFaces",air,inner);checkFaces(m,"monitorCoreFaces",core,inner);checkFaces(m,"monitorCladFaces",clad,inner);
      int[] source=m.component("device3d").selection("sourcePhysicalFaces").entities(2);
      int[] monitor=m.component("device3d").selection("monitorPhysicalFaces").entities(2);
      Set<Integer> allMonitor=new TreeSet<Integer>();for(int x:monitor)allMonitor.add(x);
      Set<Integer> want=new TreeSet<Integer>();for(int x:m.component("device3d").selection("monitorCoreFaces").entities(2))want.add(x);
      for(int x:m.component("device3d").selection("monitorCladFaces").entities(2))want.add(x);
      if(source.length!=1||monitor.length!=2||!allMonitor.equals(want))throw new IllegalStateException("Source or monitor selection mismatch");
      m.param().set("lambdaD","974[nm]","User-specified 974 nm baseline");
      m.param().set("NAD","0.22","Nominal NA, equivalent step-index assumption");
      m.param().set("uD","lambdaD/1[um]");
      m.param().set("nCladD","sqrt(1+0.6961663*uD^2/(uD^2-0.0684043^2)+0.4079426*uD^2/(uD^2-0.1162414^2)+0.8974794*uD^2/(uD^2-9.896161^2))");
      m.param().set("nCoreD","sqrt(nCladD^2+NAD^2)");
      double nc=m.param().evaluate("nCladD"),nn=m.param().evaluate("nCoreD");
      if(!(nn>nc&&nc>1&&Math.abs(nc-1.450749841198138)<1e-10))throw new IllegalStateException("Invalid index assumption");
      material(m,"matAirD","airDomains","1");material(m,"matCladD","gdev_cladShaped_dom","nCladD");material(m,"matCoreD","gdev_coreShaped_dom","nCoreD");
      checkMaterial(m,"matAirD",air);checkMaterial(m,"matCladD",clad);checkMaterial(m,"matCoreD",core);
      m.component("device3d").coordSystem().create("pmlOpticsD","PML");
      m.component("device3d").coordSystem("pmlOpticsD").selection().named("pmlDomains");
      m.component("device3d").coordSystem("pmlOpticsD").set("ScalingType","Cartesian");
      m.component("device3d").physics().create("ewfd","ElectromagneticWavesFrequencyDomain","gdev");
      m.component("device3d").physics("ewfd").create("sheetM","SurfaceMagneticCurrentDensity",2);
      m.component("device3d").physics("ewfd").feature("sheetM").selection().named("sourcePhysicalFaces");
      m.component("device3d").physics("ewfd").feature("sheetM").create("sheetJ","SurfaceCurrentDensity",2);
      m.component("device3d").physics("ewfd").create("port1","Port",2);
      m.component("device3d").physics("ewfd").feature("port1").selection().named("monitorPhysicalFaces");
      m.component("device3d").physics("ewfd").feature("port1").set("PortType","Numeric");
      m.component("device3d").physics("ewfd").feature("port1").set("PortSlit",true);
      m.component("device3d").physics("ewfd").feature("port1").set("PortName","1");
      m.component("device3d").physics("ewfd").feature("port1").set("PortExcitation","off");
      m.component("device3d").physics("ewfd").feature().duplicate("port2","port1");
      m.component("device3d").physics("ewfd").feature("port2").set("PortName","2");
      m.component("device3d").physics("ewfd").feature("port2").set("PortExcitation","off");
      String[] jm=m.component("device3d").physics("ewfd").feature("sheetM").getStringArray("Jms0");
      String[] je=m.component("device3d").physics("ewfd").feature("sheetM").feature("sheetJ").getStringArray("Js0");
      if(!Arrays.equals(jm,new String[]{"0","0","0"})||!Arrays.equals(je,new String[]{"0","0","0"}))
        throw new IllegalStateException("Expected zero source");
      Set<Integer> selectedPml=new TreeSet<Integer>();
      for(int d:m.component("device3d").coordSystem("pmlOpticsD").selection().entities(3))selectedPml.add(d);
      if(!selectedPml.equals(pml))throw new IllegalStateException("PML selection mismatch");
      for(String port:new String[]{"port1","port2"}){
        int[] selected=m.component("device3d").physics("ewfd").feature(port).selection().entities(2);
        if(!Arrays.equals(selected,monitor)||!m.component("device3d").physics("ewfd").feature(port).getString("PortExcitation").equals("off"))
          throw new IllegalStateException("Port selection or excitation mismatch: "+port);
        System.out.println("LD_TIP425_PORT="+id+","+port+",NAME="+m.component("device3d").physics("ewfd").feature(port).getString("PortName")+
          ",TYPE="+m.component("device3d").physics("ewfd").feature(port).getString("PortType")+
          ",SLIT="+m.component("device3d").physics("ewfd").feature(port).getBoolean("PortSlit")+
          ",EXCITATION="+m.component("device3d").physics("ewfd").feature(port).getString("PortExcitation")+
          ",ORIENTATION_DEFAULT="+m.component("device3d").physics("ewfd").feature(port).getString("PortOrientation")+
          ",FACES="+Arrays.toString(selected));
      }
      int[] coreIds=m.component("device3d").selection("gdev_coreShaped_dom").entities(3);
      m.component("device3d").measure().selection().geom("gdev",3);m.component("device3d").measure().selection().set(coreIds);
      double[] bb=m.component("device3d").measure().getBoundingBox();double xc=(bb[0]+bb[1])/2;
      double dx=m.param().evaluate("dx_tip"),gap=m.param().evaluate("gap_tip"),radius=m.param().evaluate("R_tip");
      if(Math.abs(xc-dx)>1e-10)throw new IllegalStateException("Core x center mismatch");
      System.out.println("LD_TIP425_PARAMS="+id+",DX_M="+dx+",CORE_X_M="+xc+",GAP_M="+gap+",TIP_RADIUS_M="+radius+
        ",ALPHA_RAD="+m.param().evaluate("alpha_tip")+",LAMBDA_M="+m.param().evaluate("lambdaD")+",NCLAD="+nc+",NCORE="+nn);
      System.out.println("LD_TIP425_DOMAINS="+id+",AIR="+air+",CORE="+core+",CLAD="+clad+",PML="+pml);
      System.out.println("LD_TIP425_SHEET="+id+",JMS="+Arrays.toString(m.component("device3d").physics("ewfd").feature("sheetM").getStringArray("Jms0"))+
        ",JS="+Arrays.toString(m.component("device3d").physics("ewfd").feature("sheetM").feature("sheetJ").getStringArray("Js0"))+
        ",SIDE_DEFAULT="+m.component("device3d").physics("ewfd").feature("sheetM").feature("sheetJ").getString("side"));
      System.out.println("LD_TIP425_PML="+id+",SCALING="+m.component("device3d").coordSystem("pmlOpticsD").getString("ScalingType")+
        ",DOMAINS="+Arrays.toString(m.component("device3d").coordSystem("pmlOpticsD").selection().entities(3)));
      System.out.println("LD_TIP425_STUDIES="+id+","+Arrays.toString(m.study().tags())+",MESHES="+Arrays.toString(m.component("device3d").mesh().tags()));
      m.save("device_tip_setup_"+id+"_425.mph");System.out.println("LD_TIP425_SAVED="+id+",NO_MESH_NO_STUDY_NO_SOLVE");
      ModelUtil.remove(tag);
    }
    System.out.println("LD_TIP425_COMPLETE=PREPARATION_ONLY");return null;
  }
  private static Set<Integer> domains(Model m,String tag){Set<Integer> out=new TreeSet<Integer>();
    for(int i:m.component("device3d").selection(tag).entities(3))out.add(i);if(out.isEmpty())throw new IllegalStateException("Empty "+tag);return out;}
  private static void checkFaces(Model m,String tag,Set<Integer> material,Set<Integer> inner){
    int[] faces=m.component("device3d").selection(tag).entities(2);if(faces.length==0)throw new IllegalStateException("Empty "+tag);
    for(int f:faces){int[] a=m.component("device3d").geom("gdev").getAdj(2,3,f);
      if(a.length!=2||!material.contains(a[0])||!material.contains(a[1])||!inner.contains(a[0])||!inner.contains(a[1]))
        throw new IllegalStateException("Bad face "+tag+" "+f+" "+Arrays.toString(a));
      System.out.println("LD_TIP425_FACE="+tag+","+f+",ADJ="+Arrays.toString(a));}}
  private static void material(Model m,String tag,String sel,String n){
    m.component("device3d").material().create(tag,"Common");m.component("device3d").material(tag).selection().named(sel);
    m.component("device3d").material(tag).propertyGroup().create("RefractiveIndex","RefractiveIndex","Refractive index");
    m.component("device3d").material(tag).propertyGroup("RefractiveIndex").set("n",new String[]{n});
    m.component("device3d").material(tag).propertyGroup("RefractiveIndex").set("ki",new String[]{"0"});}
  private static void checkMaterial(Model m,String tag,Set<Integer> expected){Set<Integer> got=new TreeSet<Integer>();
    for(int i:m.component("device3d").material(tag).selection().entities(3))got.add(i);
    if(!got.equals(expected))throw new IllegalStateException("Material selection mismatch "+tag);}
}
