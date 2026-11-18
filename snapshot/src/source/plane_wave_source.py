"""S03 candidate: differentiable finite plane-wave (PWE) 3D source representation.

Offline increment for S03 step 5 only. Not connected to COMSOL. This file makes no
claim that G03a, G03b, or G17 passed; those gates are NOT_RUN here and spatial
injection-residual validation belongs to S05/S06 per docs/stages/S03_SOURCE.md.

Conventions are inherited unchanged from the frozen package reference
(src/source/angular_spectrum.py) and docs/PHYSICS.md section 5:
  coordinates: x = horizontal slow axis, y = vertical fast axis, z = forward;
  carrier: exp(+i omega t); forward plane-wave factor exp(-i(qx*x + qy*y + kz*z));
  synthesis: E(r) = sum_q Etilde(q) exp(-i(qx*x + qy*y + kz*z)) * dqx*dqy/(2*pi)^2;
  H = khat x E / (Z0/n), Z0 = 376.730313668;
  normalization: one global factor = 1/sqrt(raw discrete Parseval forward power),
  full spectral grid is exactly 1 W; finite windows are reported, never renormalized.

Spectral truncation: only the propagating disk qx^2+qy^2 < k^2 is kept (evanescent
coefficients are identically zero in the reference spectrum). A finite PWE sum is an
entire function of (x,y,z): spatial differentiability is exact; the representable
error budget is discretization plus the disk truncation of the assumed Gaussian
radiative-equivalent spectrum, and must not be hidden by renormalization.

Import note: run from the package root (or with the package root on sys.path);
this module imports Z0 from the frozen reference so the impedance is single-sourced.
"""
import hashlib
import json

import numpy as np

from src.source.angular_spectrum import Z0

SCHEMA_VERSION = 1


def _module_sha256():
    with open(__file__, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class PlaneWaveSourceField:
    """Explicit spectral coefficients + conventions for a differentiable 3D field.

    Coefficients are stored raw (as produced by Source.spectrum). The synthesis
    measure dqx*dqy/(2*pi)^2 and the single normalization factor are applied in
    evaluate(), and both scalars are preserved in every export so downstream code
    can recompute E/H/bit-identically or keep the unnormalized form.
    """

    def __init__(self, wavelength_m, n, size, step_m, qx, qy, kz,
                 e_spectral, h_spectral, raw_power_W, source_params):
        self.wavelength_m = float(wavelength_m)
        self.n = float(n)
        self.size = int(size)
        self.step_m = float(step_m)
        self.k = 2 * np.pi * self.n / self.wavelength_m
        self.qx = qx
        self.qy = qy
        self.kz = kz
        self.E_spectral = e_spectral
        self.H_spectral = h_spectral
        self.raw_power_W = float(raw_power_W)
        self.source_params = dict(source_params)
        self.dq = 2 * np.pi / (self.size * self.step_m)
        self.factor = 1.0 / np.sqrt(self.raw_power_W)

    @classmethod
    def from_source(cls, source, size=512, step_m=.125e-6):
        if not isinstance(size, int) or size < 16 or size % 2:
            raise ValueError("positive even grid size >= 16 required")
        if not np.isfinite(step_m) or step_m <= 0:
            raise ValueError("finite positive step required")
        if np.pi / step_m < source.k:
            raise ValueError("grid must contain entire propagating disk")
        q = 2 * np.pi * np.fft.fftfreq(size, step_m)
        qx, qy = np.meshgrid(q, q, indexing="ij")
        e, h, kz = source.spectrum(qx, qy)
        mask = qx * qx + qy * qy < source.k ** 2
        flat = lambda a: a[mask].copy()
        flux_density = 0.5 * np.real(np.cross(e, h.conj())[..., 2])
        raw_power = float(np.sum(flux_density) * (2 * np.pi / (size * step_m)) ** 2 / (2 * np.pi) ** 2)
        if raw_power <= 0:
            raise ValueError("zero source power")
        params = dict(source.to_math_record())
        params.pop("record_type", None)
        params.pop("scope", None)
        return cls(source.wavelength_m, source.n, size, step_m,
                   flat(qx), flat(qy), flat(kz), flat(e), flat(h), raw_power, params)

    def _synth_weights(self, dx=0, dy=0, dz=0):
        mult = ((-1j * self.qx) ** dx) * ((-1j * self.qy) ** dy) * ((-1j * self.kz) ** dz)
        scale = self.factor * self.dq ** 2 / (2 * np.pi) ** 2
        return (self.E_spectral * mult[:, None]) * scale, (self.H_spectral * mult[:, None]) * scale

    def evaluate(self, x, y, z, dx=0, dy=0, dz=0, normalized=True, chunk_points=4096):
        """E, H (and requested spatial partial derivatives) at arbitrary points.

        dx/dy/dz select partial derivative orders; the derivative acts on the
        analytic plane-wave factor, so it is exact, not a difference scheme.
        normalized=False drops the single 1 W factor but keeps the synthesis measure.
        """
        if min(dx, dy, dz) < 0 or max(dx, dy, dz) > 3:
            raise ValueError("derivative orders 0..3 supported")
        xv, yv, zv = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float), np.asarray(z, float))
        pts = np.stack((xv.ravel(), yv.ravel(), zv.ravel()), axis=-1)
        e_w, h_w = self._synth_weights(dx, dy, dz)
        if not normalized:
            e_w = e_w / self.factor
            h_w = h_w / self.factor
        e_out = np.empty((pts.shape[0], 3), complex)
        h_out = np.empty((pts.shape[0], 3), complex)
        for s in range(0, pts.shape[0], chunk_points):
            block = pts[s:s + chunk_points]
            phase = np.exp(-1j * (block[:, 0:1] * self.qx[None, :]
                                  + block[:, 1:2] * self.qy[None, :]
                                  + block[:, 2:3] * self.kz[None, :]))
            e_out[s:s + chunk_points] = phase @ e_w
            h_out[s:s + chunk_points] = phase @ h_w
        shape = xv.shape + (3,)
        return e_out.reshape(shape), h_out.reshape(shape)

    def axis(self):
        return (np.arange(self.size) - self.size // 2) * self.step_m

    def plane_arrays(self, z):
        ax = self.axis()
        x, y = np.meshgrid(ax, ax, indexing="ij")
        e, h = self.evaluate(x, y, z)
        return ax, e, h

    def power_forward_spectral(self):
        """Discrete Parseval forward power (W). Equals 1.0 by the single factor;
        it does not establish finite-window capture or physical convergence."""
        flux = 0.5 * np.real(np.cross(self.E_spectral, self.H_spectral.conj())[..., 2])
        return float(np.sum(flux) * self.factor ** 2 * self.dq ** 2 / (2 * np.pi) ** 2)

    def plane_power(self, z, halfwidth_m=None):
        ax, e, h = self.plane_arrays(z)
        flux = 0.5 * np.real(np.cross(e, h.conj())[..., 2])
        if halfwidth_m is None:
            return float(flux.sum() * self.step_m ** 2)
        wm = np.abs(ax) < halfwidth_m
        return float(flux[np.ix_(wm, wm)].sum() * self.step_m ** 2)

    def conventions(self):
        return {
            "phasor": "exp(+i*omega*t)",
            "plane_wave_factor": "exp(-i*(qx*x + qy*y + kz*z))",
            "synthesis_measure": "dqx*dqy/(2*pi)^2",
            "coordinates": "x=horizontal slow axis, y=vertical fast axis, z=propagation direction",
            "h_relation": "H = khat x E / (Z0/n)",
            "Z0": Z0,
        }

    def units(self):
        return {
            "E": "V/m", "H": "A/m", "q": "rad/m", "length": "m", "power": "W",
            "E_spectral": "V/m per (rad/m)^2 of spectral density; multiplied by "
                          "dqx*dqy/(2*pi)^2 and factor during synthesis",
        }

    def export(self, path_stem):
        """Write <stem>.npz (arrays only, no pickle) plus <stem>.meta.json."""
        npz_path, meta_path = path_stem + ".npz", path_stem + ".meta.json"
        np.savez(npz_path, qx=self.qx, qy=self.qy, kz=self.kz,
                 E_spectral=self.E_spectral, H_spectral=self.H_spectral)
        meta = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "S03_CANDIDATE_PWE_MATHEMATICAL_REPRESENTATION",
            "status": "S03_CANDIDATE_NOT_REVIEWED",
            "comsol_executed": False,
            "scope": "analytic finite plane-wave sum (PWE); not a COMSOL source feature, "
                     "solution, or gate result; G03a/G03b/G17 are NOT_RUN by this artifact",
            "wavelength_m": self.wavelength_m,
            "n": self.n,
            "k_rad_per_m": self.k,
            "sampling": {"size": self.size, "step_m": self.step_m, "dq_rad_per_m": self.dq,
                         "propagating_point_count": int(self.qx.size),
                         "spectral_support": "propagating disk qx^2+qy^2 < k^2 only"},
            "normalization": {"policy": "single global factor; windows reported, never renormalized",
                              "raw_power_W_before_factor": self.raw_power_W,
                              "factor": self.factor,
                              "target_forward_power_W": 1.0,
                              "full_grid_discrete_parseval_forward_power_W": self.power_forward_spectral()},
            "conventions": self.conventions(),
            "units": self.units(),
            "source_params": self.source_params,
            "generator_version_sha256": _module_sha256(),
        }
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2, sort_keys=True)
        return npz_path, meta_path

    @classmethod
    def from_export(cls, npz_path, meta_path):
        with np.load(npz_path, allow_pickle=False) as data:
            qx, qy, kz = data["qx"], data["qy"], data["kz"]
            e, h = data["E_spectral"], data["H_spectral"]
        with open(meta_path, encoding="utf-8") as fh:
            meta = json.load(fh)
        if meta["schema_version"] != SCHEMA_VERSION:
            raise ValueError("unsupported export schema_version")
        obj = cls(meta["wavelength_m"], meta["n"], meta["sampling"]["size"],
                  meta["sampling"]["step_m"], qx, qy, kz, e, h,
                  meta["normalization"]["raw_power_W_before_factor"],
                  meta["source_params"])
        if abs(obj.dq - meta["sampling"]["dq_rad_per_m"]) > 1e-9 * obj.dq:
            raise ValueError("export dq inconsistent with sampling parameters")
        return obj
