"""Power-normalized projection onto lossless reciprocal forward modes.

B(u,v) is linear in u, conjugate-linear in v.  G_ij=B(mode_j,mode_i).
This module is not a general non-Hermitian/leaky-mode projector.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np

def _field(a, name: str) -> np.ndarray:
    x=np.asarray(a,dtype=np.complex128)
    if x.ndim!=2 or x.shape[1]!=3 or not len(x) or not np.isfinite(x).all():
        raise ValueError(f'{name}: expected finite complex (N,3)')
    return x

def _quadrature(w, n, count):
    w=np.asarray(w,dtype=float); n=np.asarray(n,dtype=float)
    if w.shape!=(count,) or not np.isfinite(w).all() or np.any(w<=0):
        raise ValueError('weights_m2 must be finite positive (N,)')
    if n.shape!=(3,) or not np.isfinite(n).all() or abs(np.linalg.norm(n)-1)>1e-8:
        raise ValueError('normal must be a finite unit 3-vector')
    return w,n

def inner(Eu,Hu,Ev,Hv,weights_m2,normal) -> complex:
    Eu,Hu,Ev,Hv=[_field(a,n) for a,n in [(Eu,'Eu'),(Hu,'Hu'),(Ev,'Ev'),(Hv,'Hv')]]
    if not Eu.shape==Hu.shape==Ev.shape==Hv.shape:
        raise ValueError('Fields must share quadrature coordinates and shape')
    w,n=_quadrature(weights_m2,normal,len(Eu))
    integrand=np.cross(Eu,Hv.conj())+np.cross(Ev.conj(),Hu)
    return complex(.25*np.sum(w*(integrand@n)))

def flux(E,H,weights_m2,normal) -> float:
    return float(inner(E,H,E,H,weights_m2,normal).real)

def project(E,H,Em,Hm,weights_m2,normal,condition_limit:float=1e10) -> dict:
    E,H=_field(E,'E'),_field(H,'H')
    Em,Hm=np.asarray(Em,dtype=complex),np.asarray(Hm,dtype=complex)
    if Em.ndim==2: Em=Em[None,...]
    if Hm.ndim==2: Hm=Hm[None,...]
    if Em.shape!=Hm.shape or Em.ndim!=3 or Em.shape[1:]!=E.shape or E.shape!=H.shape:
        raise ValueError('Mode arrays must be (M,N,3), all fields at identical nodes')
    if not len(Em) or not np.isfinite(Em).all() or not np.isfinite(Hm).all():
        raise ValueError('Empty or nonfinite target modes')
    m=len(Em)
    G=np.array([[inner(Em[j],Hm[j],Em[i],Hm[i],weights_m2,normal) for j in range(m)] for i in range(m)])
    norm=np.linalg.norm(G)
    if norm==0 or np.linalg.norm(G-G.conj().T)/norm>1e-8:
        raise ValueError('Power Gram matrix is zero or non-Hermitian')
    eig=np.linalg.eigvalsh(G)
    if eig[0]<=0 or eig[-1]/eig[0]>condition_limit:
        raise ValueError('Non-positive, duplicated, reversed, or ill-conditioned target modes')
    b=np.array([inner(E,H,Em[i],Hm[i],weights_m2,normal) for i in range(m)])
    c=np.linalg.solve(G,b)
    power=complex(np.vdot(c,G@c))
    if abs(power.imag)>max(1e-12,1e-9*abs(power.real)) or power.real < -1e-12:
        raise ValueError('Invalid projected power; inspect mode assumptions')
    return {'record_type':'POWER_PROJECTION','target_power_W':float(power.real),
            'net_field_flux_W':flux(E,H,weights_m2,normal),
            'gram_condition':float(eig[-1]/eig[0]),
            'gram_W_real':G.real.tolist(),'gram_W_imag':G.imag.tolist(),
            'coefficients_real':c.real.tolist(),'coefficients_imag':c.imag.tolist(),
            'scope':'lossless reciprocal forward target subspace; no experimental validation'}

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True,type=Path)
    p.add_argument('--meta',required=True,type=Path);p.add_argument('--out',type=Path);args=p.parse_args()
    meta=json.loads(args.meta.read_text(encoding='utf-8'))
    for k,v in {'quantity_kind':'FULL_PHYSICAL_COMPLEX_FIELD','phasor':'exp(+i*omega*t)',
                'projection_assumptions':'LOSSLESS_RECIPROCAL_FORWARD_MODES'}.items():
        if meta.get(k)!=v: raise ValueError(f'Metadata {k} must equal {v}')
    if meta.get('units')!={'coords':'m','E':'V/m','H':'A/m','weights':'m^2'}:
        raise ValueError('Expected explicit SI unit metadata')
    with np.load(args.input,allow_pickle=False) as f:
        coords=np.asarray(f['coords_m'])
        if coords.shape!=f['E'].shape or not np.isfinite(coords).all():
            raise ValueError('Invalid coords_m')
        n=f['normal']
        if np.ptp(coords@n)>1e-10*max(np.ptp(coords,axis=0).max(),1e-9):
            raise ValueError('Quadrature nodes do not lie on a single normal plane')
        result=project(f['E'],f['H'],f['Em'],f['Hm'],f['weights_m2'],n)
    power=meta.get('source_power_W')
    if isinstance(power,bool) or not isinstance(power,(int,float)) or not np.isfinite(power) or power<=0:
        raise ValueError('source_power_W must be an explicit positive reference')
    result['eta_target']=result['target_power_W']/power
    result['source_power_W']=power
    text=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
    if args.out: args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(text,encoding='utf-8')
    else: print(text,end='')
    return 0
if __name__=='__main__': raise SystemExit(main())
