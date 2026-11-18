import com.comsol.model.*;
import com.comsol.model.util.*;
import java.util.*;

/** Step 390e: load 390d, re-read source normals and verify the side actually used, then export native IntSurface cross-section fluxes (monitor plane, analytic source spectrum, six air-side PML interfaces) and the complex monitor-plane grid; write no model file. */
public class AirSheetInjectExport390e {
  static final String ROOT="<LOCAL_PATH>";
  static final String MPH=ROOT+"\\mph";
  static final String COMP="air3d";
  static final String MON="monitorPhysicalFaces";
  static final String SRCF="sourcePhysicalFaces";
  static final int SRC_FACE=78, SRC_ADJ_A=22, SRC_ADJ_B=23, MON_FACE=81, MON_ADJ_A=23, MON_ADJ_B=24;
  static final String SX="0.5*real(ewfd.Ey*conj(ewfd.Hz)-ewfd.Ez*conj(ewfd.Hy))";
  static final String SY="0.5*real(ewfd.Ez*conj(ewfd.Hx)-ewfd.Ex*conj(ewfd.Hz))";
  static final String SZ="0.5*real(ewfd.Ex*conj(ewfd.Hy)-ewfd.Ey*conj(ewfd.Hx))";

  private static int[] ents(Model m,String tag,int dim){return m.component(COMP).selection(tag).entities(dim);}
  private static boolean has(String[] a,String v){for(String x:a)if(x.equals(v))return true;return false;}
  private static TreeSet<Integer> doms(Model m,String tag){TreeSet<Integer> r=new TreeSet<Integer>();
    for(int d:ents(m,tag,3))r.add(d);if(r.isEmpty())throw new IllegalStateException("Empty domain selection "+tag);return r;}
  private static void expectFace(Model m,String tag,int id,int a,int b){int[] f=ents(m,tag,2);
    if(f.length!=1||f[0]!=id)throw new IllegalStateException("BLOCK_GEOMETRY_REBUILD: named face selection changed for "+tag+": "+Arrays.toString(f)+" expected ["+id+"]");
    int[] adj=m.component(COMP).geom("gAir").getAdj(2,3,id);
    if(adj.length!=2||adj[0]!=a||adj[1]!=b)throw new IllegalStateException("BLOCK_GEOMETRY_REBUILD: adjacency changed for "+tag+" face "+id+": "+Arrays.toString(adj));
    System.out.println("LD_390_FACE_OK="+tag+","+id+",ADJ,"+Arrays.toString(adj));}
  private static void measureFace(Model m,String label,int[] faces,double half,double z){
    m.component(COMP).measure().selection().geom("gAir",2);m.component(COMP).measure().selection().set(faces);
    double area=m.component(COMP).measure().getArea();double[] bb=m.component(COMP).measure().getBoundingBox();
    System.out.println("LD_390_MEASURE_"+label+"=AREA,"+area+",BOUNDING,"+Arrays.toString(bb));
    if(Math.abs(area-4*half*half)>4*half*half*1e-6)throw new IllegalStateException(label+" area mismatch "+area);
    double[] want=new double[]{-half,half,-half,half,z,z};for(int i=0;i<6;i++){if(Math.abs(bb[i]-want[i])>1e-10)throw new IllegalStateException(label+" bound "+i+" mismatch "+bb[i]+" expected "+want[i]);}}
  private static int[] slab(Model m,String tag,String xmin,String xmax,String ymin,String ymax,String zmin,String zmax){
    m.component(COMP).selection().create(tag,"Box");m.component(COMP).selection(tag).set("entitydim",2);
    m.component(COMP).selection(tag).set("xmin",xmin);m.component(COMP).selection(tag).set("xmax",xmax);
    m.component(COMP).selection(tag).set("ymin",ymin);m.component(COMP).selection(tag).set("ymax",ymax);
    m.component(COMP).selection(tag).set("zmin",zmin);m.component(COMP).selection(tag).set("zmax",zmax);
    m.component(COMP).selection(tag).set("condition","inside");
    return m.component(COMP).selection(tag).entities(2);}
  private static void explicit(Model m,String tag,int[] faces){m.component(COMP).selection().create(tag,"Explicit");
    m.component(COMP).selection(tag).geom("gAir",2);m.component(COMP).selection(tag).set(faces);}
  private static String dset(Model m){String[] t=m.result().dataset().tags();if(has(t,"dset1"))return "dset1";
    if(t.length==0)throw new IllegalStateException("No result dataset");return t[0];}
  private static String par(Model m,String name){String v;try{v=m.param().get(name);}catch(Exception e){v="READ_ERROR:"+e;}
    String ev;try{ev=Double.toString(m.param().evaluate(name));}catch(Exception e){ev="EVAL_ERROR:"+e;}
    System.out.println("LD_390_PARAM="+name+","+v+","+ev);return v;}
  private static void printPlist(String label,Model m){
    try{System.out.println(label+"="+m.study("stud390").feature("freq").getString("plist"));}
    catch(Exception e){System.out.println(label+"_READ_ERROR="+e+",NOTE=the plist WRITE is the proven part (368); this read is optional evidence");}}
  private static void inventory(String step,Model m){
    System.out.println("LD_390_INV_"+step+"_STUDIES="+Arrays.toString(m.study().tags()));
    System.out.println("LD_390_INV_"+step+"_SOLS="+Arrays.toString(m.sol().tags()));
    System.out.println("LD_390_INV_"+step+"_DATASETS="+Arrays.toString(m.result().dataset().tags()));
    System.out.println("LD_390_INV_"+step+"_SELECTIONS="+Arrays.toString(m.component(COMP).selection().tags()));
    System.out.println("LD_390_INV_"+step+"_PHYSICS="+Arrays.toString(m.component(COMP).physics().tags()));
    try{System.out.println("LD_390_INV_"+step+"_EWFD="+Arrays.toString(m.component(COMP).physics("ewfd").feature().tags()));}catch(Exception e){System.out.println("LD_390_INV_ERROR_EWFD="+e);}
    System.out.println("LD_390_INV_"+step+"_MATERIALS="+Arrays.toString(m.component(COMP).material().tags()));
    System.out.println("LD_390_INV_"+step+"_COORD="+Arrays.toString(m.component(COMP).coordSystem().tags()));
    System.out.println("LD_390_INV_"+step+"_VARIABLES="+Arrays.toString(m.component(COMP).variable().tags()));
    System.out.println("LD_390_INV_"+step+"_COUPLINGS="+Arrays.toString(m.component(COMP).cpl().tags()));
    System.out.println("LD_390_INV_"+step+"_MESHES="+Arrays.toString(m.component(COMP).mesh().tags()));
    System.out.println("LD_390_INV_"+step+"_GEOMETRY="+Arrays.toString(m.component(COMP).geom().tags()));}
  private static void geometryGuard(Model m){
    TreeSet<Integer> inner=doms(m,"gAir_innerPhysical_dom"),pml=doms(m,"pmlDomains");
    TreeSet<Integer> all=new TreeSet<Integer>(inner);all.addAll(pml);
    if(!Collections.disjoint(inner,pml)||all.size()!=m.component(COMP).geom("gAir").getNDomains())
      throw new IllegalStateException("Physical/PML partition changed: "+inner+" / "+pml);
    System.out.println("LD_390_DOMAINS=PHYSICAL,"+inner+",PML_COUNT,"+pml.size()+",TOTAL,"+all.size());
    expectFace(m,SRCF,SRC_FACE,SRC_ADJ_A,SRC_ADJ_B);expectFace(m,MON,MON_FACE,MON_ADJ_A,MON_ADJ_B);
    double half=m.param().evaluate("halfAir");
    measureFace(m,"SOURCE",ents(m,SRCF,2),half,m.param().evaluate("zAirSource"));
    measureFace(m,"MONITOR",ents(m,MON,2),half,m.param().evaluate("zAirMonitor"));
    System.out.println("LD_390_MATERIAL_N="+Arrays.toString(m.component(COMP).material("air").propertyGroup("RefractiveIndex").getStringArray("n")));
    System.out.println("LD_390_MATERIAL_KI="+Arrays.toString(m.component(COMP).material("air").propertyGroup("RefractiveIndex").getStringArray("ki")));
    System.out.println("LD_390_PML_SCALING="+m.component(COMP).coordSystem("pmlBox").getString("ScalingType"));
    System.out.println("LD_390_PML_SELECTED_COUNT="+m.component(COMP).coordSystem("pmlBox").selection().entities(3).length);}
  private static void normals(String label,Model m,String d,int[] faces){
    m.result().numerical().create(label,"AvSurface");m.result().numerical(label).selection().set(faces);
    m.result().numerical(label).set("data",d);
    m.result().numerical(label).set("expr",new String[]{"nx","ny","nz","unx","uny","unz","dnx","dny","dnz"});
    System.out.println("LD_390_NORMAL_"+label+"="+Arrays.deepToString(m.result().numerical(label).getReal()));}
  private static void nativeFlux(String label,Model m,String d,String ex,String ey,String ez,String flux,int res){
    String p="par"+label,n="int"+label;
    m.result().dataset().create(p,"ParSurface");m.result().dataset(p).set("data",d);
    m.result().dataset(p).set("par1","uu");m.result().dataset(p).set("par2","vv");
    m.result().dataset(p).set("exprx",ex);m.result().dataset(p).set("expry",ey);m.result().dataset(p).set("exprz",ez);
    m.result().dataset(p).set("res",res);
    m.result().numerical().create(n,"IntSurface");m.result().numerical(n).set("data",p);
    m.result().numerical(n).set("expr",new String[]{flux});
    System.out.println("LD_390_NATIVE="+label+",RES,"+res+",VALUE,"+Arrays.deepToString(m.result().numerical(n).getReal())
      +",EXPR,"+flux+",SURFACE,"+ex+"|"+ey+"|"+ez);}
  private static void gridExport(String label,Model m,String d,String[] exprs,double z,int n,double half){
    double[][] c=new double[3][n*n];int p=0;
    for(int j=0;j<n;j++)for(int i=0;i<n;i++){int q=j*n+i;c[0][q]=-half+2*half*(i+0.5)/n;c[1][q]=-half+2*half*(j+0.5)/n;c[2][q]=z;}
    m.result().numerical().create(label,"Interp");m.result().numerical(label).set("data",d);
    m.result().numerical(label).set("expr",exprs);m.result().numerical(label).setInterpolationCoordinates(c);
    double[][][] re=m.result().numerical(label).getData(),im=m.result().numerical(label).getImagData();
    if(re.length!=exprs.length||re[0].length!=1||re[0][0].length!=n*n)throw new IllegalStateException("Unexpected Interp dimensions for "+label);
    System.out.println("LD_390_GRID="+label+",N,"+n+",HALF,"+half+",Z,"+z+",EXPR_COUNT,"+exprs.length+","+Arrays.toString(exprs));
    for(int q=0;q<n*n;q++){StringBuilder r=new StringBuilder("LD_390_GRIDVAL="+label).append(',').append(c[0][q]).append(',').append(c[1][q]).append(',').append(c[2][q]);
      for(int k=0;k<exprs.length;k++)r.append(',').append(re[k][0][q]).append(',').append(im[k][0][q]);System.out.println(r.toString());}}
  public static void main(String[] args) throws Exception { run(); }
  public static Model run() throws Exception {
    Model m=ModelUtil.loadCopy("AirSheetInjectExport390e",MPH+"\\air_sheet_inject_390d.mph");
    if(m.sol("sol1").isEmpty())throw new IllegalStateException("the 390d copy carries no solution to export");
    geometryGuard(m);
    for(String p:new String[]{"gap_tip","lambda0","aperR","gridN","resNative"})par(m,p);
    String d=dset(m);
    System.out.println("LD_390E_DATASET="+d+",ALL_DATASETS="+Arrays.toString(m.result().dataset().tags()));
    normals("source390e",m,d,ents(m,SRCF,2));
    normals("monitor390e",m,d,ents(m,MON,2));
    double[][] rows=m.result().numerical("source390e").getReal();
    double unz=rows[5][0],dnz=rows[8][0];
    String side=m.component(COMP).physics("ewfd").feature("sheetM").feature("sheetJ").getString("side");
    boolean consistent=Math.abs(rows[2][0]-1)<=1e-8&&Math.abs(Math.abs(unz)-1)<=1e-8&&Math.abs(unz+dnz)<=1e-8&&(unz<0?side.equals("up"):side.equals("down"));
    System.out.println("LD_390E_SIDE_USED="+side+",UNZ,"+unz+",DNZ,"+dnz+",CONSISTENT,"+consistent);
    System.out.println("LD_390E_JMS0="+Arrays.toString(m.component(COMP).physics("ewfd").feature("sheetM").getStringArray("Jms0"))
      +",JS0="+Arrays.toString(m.component(COMP).physics("ewfd").feature("sheetM").feature("sheetJ").getStringArray("Js0")));
    int res=(int)m.param().evaluate("resNative");int gridN=(int)m.param().evaluate("gridN");
    double half=m.param().evaluate("halfAir");
    System.out.println("LD_390_APERTURE_RADIUS_PARAM="+m.param().get("aperR")+",METRES,"+m.param().evaluate("aperR"));
    String xw="(-halfAir+2*halfAir*uu)",yw="(-halfAir+2*halfAir*vv)",zspan="(zAirFront+(zAirBack-zAirFront)*vv)";
    nativeFlux("monitorNetZ",m,d,xw,yw,"zAirMonitor",SZ,res);
    nativeFlux("sourceSpectrumZ",m,d,xw,yw,"zAirSource","0.5*real(ld_s355_ex_tot*conj(ld_s355_hy_tot)-ld_s355_ey_tot*conj(ld_s355_hx_tot))",res);
    nativeFlux("exitZBack",m,d,xw,yw,"zAirBack",SZ,res);
    nativeFlux("frontZOut",m,d,xw,yw,"zAirFront","-1*"+SZ,res);
    nativeFlux("xPlusOut",m,d,"halfAir",xw,zspan,SX,res);
    nativeFlux("xMinusOut",m,d,"-halfAir",xw,zspan,"-1*"+SX,res);
    nativeFlux("yPlusOut",m,d,xw,"halfAir",zspan,SY,res);
    nativeFlux("yMinusOut",m,d,xw,"-halfAir",zspan,"-1*"+SY,res);
    String[] gx={"ewfd.Ex","ewfd.Ey","ewfd.Ez","ewfd.Hx","ewfd.Hy","ewfd.Hz",
      "ld_s355_ex_tot","ld_s355_ey_tot","ld_s355_hx_tot","ld_s355_hy_tot"};
    gridExport("monitorGrid",m,d,gx,m.param().evaluate("zAirMonitor"),gridN,half);
    System.out.println("LD_390_NULL_forward_and_backward_split_W=null,reason=net flux only; no verified mode basis, and point-wise E/H ratios are not power (review 347 F-01)");
    System.out.println("LD_390_NULL_pml_absorbed_power_W=null,reason=PML interiors are never integrated; the six signed air-side outflow lines are the only boundary term");
    System.out.println("LD_390_NULL_device_efficiency=null,reason=air-only numerical diagnostic; no source-side power account, no HE11 identification, no gate");
    inventory("390E",m);
    if(!consistent)throw new IllegalStateException("source side does not match the read-back normals; re-run 390c before trusting any export");
    System.out.println("LD_390E_COMPLETE=EXPORT_ONLY_NO_SOLVE_NO_MODEL_SAVE");return m;
  }
}
