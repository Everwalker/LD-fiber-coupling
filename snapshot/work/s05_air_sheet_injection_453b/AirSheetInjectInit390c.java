import com.comsol.model.*;
import com.comsol.model.util.*;
import java.util.*;

/** Step 390c: load 390b, create stud390 Frequency step, create the auto solver sequence, run only the Variables initialization feature, read back the actual source-face nx/nz/unz/dnz and set sheet side from that read-back, then clear the initialization solution. No frequency solve. */
public class AirSheetInjectInit390c {
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
    Model m=ModelUtil.loadCopy("AirSheetInjectInit390c",MPH+"\\air_sheet_inject_390b.mph");
    geometryGuard(m);
    for(String p:new String[]{"gap_tip","lambda0","hmaxAir","hminAir","aperR","gridN","resNative"})par(m,p);
    int ne=m.component(COMP).mesh("mesh390").getNumElem();if(ne<=0)throw new IllegalStateException("mesh390 has no elements");
    System.out.println("LD_390C_ELEMENTS="+ne);
    if(m.study().tags().length!=0)throw new IllegalStateException("a study already exists in the 390b copy: "+Arrays.toString(m.study().tags()));
    System.out.println("LD_390C_SHEET_ENTER_JMS0="+Arrays.toString(m.component(COMP).physics("ewfd").feature("sheetM").getStringArray("Jms0"))
      +",JS0="+Arrays.toString(m.component(COMP).physics("ewfd").feature("sheetM").feature("sheetJ").getStringArray("Js0"))
      +",SIDE="+m.component(COMP).physics("ewfd").feature("sheetM").feature("sheetJ").getString("side"));
    m.study().create("stud390");m.study("stud390").create("freq","Frequency");
    m.study("stud390").feature("freq").set("plist","c_const/lambda0");
    printPlist("LD_390C_PLIST",m);
    m.study("stud390").createAutoSequences("all");
    System.out.println("LD_390C_SOLVERS="+Arrays.toString(m.sol().tags()));
    String vtag=null;
    for(String t:m.sol("sol1").feature().tags())System.out.println("LD_390C_SOL_FEATURE="+t+","+m.sol("sol1").feature(t).getType());
    for(String t:m.sol("sol1").feature().tags())if(m.sol("sol1").feature(t).getType().equals("Variables")){
      if(vtag!=null)throw new IllegalStateException("two Variables initialization features: "+vtag+" and "+t);vtag=t;}
    if(vtag==null)throw new IllegalStateException("no Variables initialization feature found; refusing to guess a solver tag");
    System.out.println("LD_390C_INIT_FEATURE="+vtag+",SCOPE=VARIABLES_ONLY_NO_STATIONARY_RUN");
    m.sol("sol1").run(vtag);
    String d=dset(m);
    System.out.println("LD_390C_DATASET="+d+",ALL_DATASETS="+Arrays.toString(m.result().dataset().tags()));
    normals("source390c",m,d,ents(m,SRCF,2));
    normals("monitor390c",m,d,ents(m,MON,2));
    double[][] rows=m.result().numerical("source390c").getReal();
    double unz=rows[5][0],dnz=rows[8][0],nz=rows[2][0];
    if(Math.abs(Math.abs(unz)-1)>1e-8||Math.abs(unz+dnz)>1e-8)
      throw new IllegalStateException("source face up/down normals are not an opposed unit pair: nz="+nz+",unz="+unz+",dnz="+dnz);
    String side=unz<0?"up":"down";

    if(Math.abs(nz-1)>1e-8)
      throw new IllegalStateException("BLOCK_SIGN_CONVENTION: source face geometric normal nz="+nz+" is not +1. The frozen 355/355b Jms=(Ey,-Ex,0), Js=(-Hy,Hx,0) convention was verified only for a +z normal face (355 direction_basis.validity), so the signs must be re-derived from the read-back, never guessed.");
    m.component(COMP).physics("ewfd").feature("sheetM").feature("sheetJ").set("side",side);
    System.out.println("LD_390C_NORMAL_READBACK=nz,"+nz+",unz,"+unz+",dnz,"+dnz);
    System.out.println("LD_390C_SIDE_SET="+side+",READBACK="+m.component(COMP).physics("ewfd").feature("sheetM").feature("sheetJ").getString("side")
      +",ALLOWED="+Arrays.toString(m.component(COMP).physics("ewfd").feature("sheetM").feature("sheetJ").getAllowedPropertyValues("side")));
    System.out.println("LD_390C_SHEET_LEAVE_JMS0_UNCHANGED="+Arrays.toString(m.component(COMP).physics("ewfd").feature("sheetM").getStringArray("Jms0"))
      +",JS0="+Arrays.toString(m.component(COMP).physics("ewfd").feature("sheetM").feature("sheetJ").getStringArray("Js0")));
    for(String s:m.sol().tags())m.sol(s).clearSolutionData();
    for(String s:m.sol().tags())if(!m.sol(s).isEmpty())throw new IllegalStateException("failed to clear the initialization solution in "+s);
    System.out.println("LD_390C_CLEARED_INITIALIZATION=YES");
    inventory("390C",m);
    m.save(MPH+"\\air_sheet_inject_390c.mph");
    System.out.println("LD_390C_MPH="+MPH+"\\air_sheet_inject_390c.mph");
    System.out.println("LD_390C_COMPLETE=STUDY_CONFIG_AND_NORMAL_READBACK_NO_FREQUENCY_SOLVE");return m;
  }
}
