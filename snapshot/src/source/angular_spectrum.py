"""Radiative vector source, SI units, exp(+i omega t); no COMSOL claims.

v3: wavelength_m, wx_m and wy_m are REQUIRED constructor arguments. There is
no implicit wavelength or waist radius from the historical 970 nm case.

E(r)=integral Etilde(q) exp(-i k.r) dqx dqy/(2*pi)^2.
dP/dOmega is proportional to kz**2 |Etilde|**2 (stationary phase).
FFT samples are periodic midpoint cells, not endpoint trapezoid samples.
Coordinates: x=horizontal slow axis, y=vertical fast axis, z=propagation.
"""
from dataclasses import dataclass, replace
import numpy as np

Z0 = 376.730313668

@dataclass(frozen=True)
class Source:
    wavelength_m: float
    wx_m: float
    wy_m: float
    polarization: str = 'x'
    zx_m: float = 0.
    zy_m: float = 0.
    n: float = 1.

    def __post_init__(self):
        vals = (self.wavelength_m, self.wx_m, self.wy_m, self.n)
        if not all(np.isfinite(v) and v > 0 for v in vals):
            raise ValueError('wavelength, radii and index must be finite positive')
        if self.polarization not in ('x', 'y') or not np.isfinite([self.zx_m, self.zy_m]).all():
            raise ValueError('invalid polarization or waist phase offset')

    @property
    def k(self): return 2*np.pi*self.n/self.wavelength_m

    def spectrum(self, qx, qy):
        qx, qy = np.broadcast_arrays(qx, qy)
        mask = qx*qx + qy*qy < self.k**2
        kz = np.sqrt(np.maximum(self.k**2-qx*qx-qy*qy, 0))
        kh = np.stack((qx/self.k, qy/self.k, kz/self.k), axis=-1)
        p = np.eye(3)[0 if self.polarization == 'x' else 1]
        u = p-kh*np.sum(kh*p, axis=-1)[..., None]
        # Separately shifted 1D Helmholtz phases; actual vector-field waist
        # locations are measured, not asserted equal to these phase parameters.
        phi = ((np.sqrt(np.maximum(self.k**2-qx*qx, 0))-self.k)*self.zx_m
               +(np.sqrt(np.maximum(self.k**2-qy*qy, 0))-self.k)*self.zy_m)
        a = np.exp(-.25*((self.wx_m*qx)**2+(self.wy_m*qy)**2)+1j*phi)*mask
        E = a[..., None]*u
        H = np.cross(kh, E)/(Z0/self.n)
        return E, H, kz

    def angular_cut(self, theta, axis):
        if axis not in ('x', 'y'): raise ValueError('axis must be x or y')
        theta = np.asarray(theta)
        if np.any(abs(theta) >= np.pi/2): raise ValueError('forward hemisphere only')
        q = self.k*np.sin(theta)
        E, _, kz = self.spectrum(q if axis=='x' else np.zeros_like(q),
                                 q if axis=='y' else np.zeros_like(q))
        return kz**2*np.sum(abs(E)**2, axis=-1)

    def at_wavelength(self, wavelength_m):
        """Main spectral branch: keep physical source radii and phase offsets."""
        return replace(self, wavelength_m=wavelength_m)

    def to_math_record(self):
        """Serializable record of the MATHEMATICAL source only.

        This is not a COMSOL model, source feature, or solution.
        """
        return {'record_type': 'MATHEMATICAL_SOURCE',
                'comsol_executed': False,
                'scope': 'analytic radiative angular spectrum; not a COMSOL result',
                'wavelength_m': self.wavelength_m, 'wx_m': self.wx_m, 'wy_m': self.wy_m,
                'polarization': self.polarization, 'zx_m': self.zx_m, 'zy_m': self.zy_m,
                'n': self.n, 'phasor': 'exp(+i*omega*t)'}

def fwhm(theta, density):
    theta, density = np.asarray(theta), np.asarray(density)
    if theta.ndim != 1 or density.shape != theta.shape or not np.isfinite(density).all():
        raise ValueError('invalid angular samples')
    if np.any(np.diff(theta)<=0) or len(theta)<5 or density.max()<=0:
        raise ValueError('ordered positive angular cut required')
    peak = int(np.argmax(density)); half = density[peak]/2
    left = np.flatnonzero(density[:peak]<half)
    right = np.flatnonzero(density[peak+1:]<half)+peak+1
    if not len(left) or not len(right): raise ValueError('half-maximum not bracketed')
    l, r = left[-1], right[0]
    a = theta[l]+(half-density[l])*(theta[l+1]-theta[l])/(density[l+1]-density[l])
    b = theta[r-1]+(half-density[r-1])*(theta[r]-theta[r-1])/(density[r]-density[r-1])
    return float(b-a)

def fit_source(wavelength_m, slow_deg=6., fast_deg=30., polarization='x'):
    """Fit physical waists at an explicit wavelength; no implicit default."""
    for target in (slow_deg, fast_deg):
        if not 0 < target <= 40:
            raise ValueError('supported fitted widths are (0,40] degrees')
    # Initial radii depend on the actual wavelength, never on a historic case.
    s = Source(wavelength_m=wavelength_m, wx_m=wavelength_m, wy_m=wavelength_m,
               polarization=polarization)
    theta = np.deg2rad(np.linspace(-89, 89, 17801))
    for axis, target in [('x', slow_deg), ('y', fast_deg)]:
        lo, hi = .01e-6, 100e-6
        for _ in range(50):
            w = (lo+hi)/2
            test = replace(s, **{f'w{axis}_m': w})
            measured = np.rad2deg(fwhm(theta, test.angular_cut(theta, axis)))
            if measured > target: lo = w
            else: hi = w
        s = replace(s, **{f'w{axis}_m': (lo+hi)/2})
    return s

class GridSource:
    """Periodic FFT source grid; full-grid power checks are discrete Parseval checks.

    They do not establish finite-window capture or physical convergence.
    """
    def __init__(self, source, size=512, step_m=.125e-6):
        if not isinstance(size, int) or size < 16 or size % 2 or not np.isfinite(step_m) or step_m <= 0:
            raise ValueError('positive even grid size and finite positive step required')
        if np.pi/step_m < source.k: raise ValueError('grid must contain entire propagating disk')
        self.source, self.size, self.step_m = source, size, step_m
        self.axis = (np.arange(size)-size//2)*step_m
        q = 2*np.pi*np.fft.fftfreq(size, step_m)
        self.qx, self.qy = np.meshgrid(q, q, indexing='ij')
        self.E, self.H, self.kz = source.spectrum(self.qx, self.qy)
        self.dq = 2*np.pi/(size*step_m)
        self.raw_power = float(np.sum(.5*np.real(np.cross(self.E, self.H.conj())[..., 2]))*self.dq**2/(2*np.pi)**2)
        if self.raw_power <= 0: raise ValueError('zero source power')
        # One factor from all-plane spectral Parseval power. Never normalize crops.
        self.factor = 1/np.sqrt(self.raw_power)

    def plane(self, z):
        if not np.isfinite(z): raise ValueError('finite plane position required')
        phase = np.exp(-1j*self.kz*z)[..., None]
        scale = self.factor*self.dq**2/(2*np.pi)**2
        E = np.fft.fftshift(np.fft.fft2(self.E*phase, axes=(0, 1)), axes=(0, 1))*scale
        H = np.fft.fftshift(np.fft.fft2(self.H*phase, axes=(0, 1)), axes=(0, 1))*scale
        return E, H

    def power(self, E, H, halfwidth_m=None):
        flux = .5*np.real(np.cross(E, H.conj())[..., 2])
        if halfwidth_m is not None:
            mask = (abs(self.axis) < halfwidth_m)
            flux = flux[np.ix_(mask, mask)]
        return float(flux.sum()*self.step_m**2)

    def widths(self, E):
        # Positive |E|^2 second moments for waist localization (not flux widths).
        density = np.sum(abs(E)**2, axis=-1)
        return tuple(float(np.sqrt(np.sum(density*self.axis.reshape(shape)**2)/density.sum()))
                     for shape in ((-1, 1), (1, -1)))
