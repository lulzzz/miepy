"""
beam sources
"""

import numpy as np
import miepy
from miepy.sources.source_base import source, combined_source
from math import factorial
from scipy.special import eval_genlaguerre, eval_hermite, erfc

def zr(w0, wav):
    return np.pi*w0**2/wav

def w(z, w0, wav):
    return w0*np.sqrt(1 + (z/zr(w0,wav))**2)
    
def Rinv(z, w0, wav):
    return z/(z**2 + zr(w0,wav)**2)

def gouy(z, w0, wav):
    return np.arctan2(z, zr(w0,wav))

class beam(source):
    def __init__(self, width, polarization, amplitude=1, center=np.zeros(3)):
        super().__init__(amplitude)
        self.width = width
        polarization = np.asarray(polarization, dtype=np.complex)
        self.polarization = polarization
        self.polarization /= np.linalg.norm(polarization)
        self.center = np.asarray(center)

    def scalar_potenital(self, x, y, z, k): pass

    def scalar_potenital_ingoing(self, theta, phi, k): pass

    def is_paraxial(self, x, y, z, k): pass

    def E_field(self, x, y, z, k):
        U = self.scalar_potenital(x, y, z, k)
        E = np.zeros((3,) + U.shape, dtype=complex)
        E[0] = U*self.polarization[0]
        E[1] = U*self.polarization[1]

        return E

    def H_field(self, x, y, z, k):
        U = self.scalar_potenital(x, y, z, k)
        H = np.zeros((3,) + U.shape, dtype=complex)
        H[0] = -U*self.polarization[1]
        H[1] = U*self.polarization[0]

        return H

    def spherical_ingoing(self, theta, phi, k):
        """Determine far-field spherical fields from the scalar potential.
        Returns E[2,...], the theta & phi components"""
        U = self.scalar_potenital_ingoing(theta, phi, k)
        Esph = np.zeros((2,) + U.shape, dtype=complex)

        Ex = U*self.polarization[0]
        Ey = U*self.polarization[1]
        Esph[0] = -Ex*np.cos(phi) - Ey*np.sin(phi)
        Esph[1] = -Ex*np.sin(phi) + Ey*np.cos(phi)

        return Esph

    def structure(self, position, k, Lmax, radius):
        sampling = miepy.vsh.decomposition.sampling_from_Lmax(Lmax)

        if self.is_paraxial(k):
            return miepy.vsh.decomposition.near_field_point_matching(self, 
                              position, 2*radius, k, Lmax, sampling)
        else:
            r = 1e6*(2*np.pi/k)
            return miepy.vsh.decomposition.far_field_point_matching(self, 
                              position, r, k, Lmax, sampling)

class gaussian_beam(beam):
    def __init__(self, width, polarization, amplitude=1, center=np.zeros(3)):
        super().__init__(width, polarization, amplitude, center)
    
    def scalar_potenital(self, x, y, z, k):
        rp = np.array([x - self.center[0], y - self.center[1], z - self.center[2]])
        rho_sq = rp[0]**2 + rp[1]**2
        wav = 2*np.pi/k
        amp = self.amplitude*self.width/w(rp[2], self.width, wav) * np.exp(-rho_sq/w(rp[2],self.width,wav)**2)
        phase = k*rp[2] + k*rho_sq*Rinv(rp[2],self.width,wav)/2 - gouy(rp[2],self.width,wav)

        return amp*np.exp(1j*phase)

    def scalar_potenital_ingoing(self, theta, phi, k):
        wav = 2*np.pi/k
        c = 0.5*(k*self.width)**2
        power = 1e-12
        factor = np.sqrt(power/(np.pi*(1 - np.sqrt(np.pi*c)*np.exp(c)*erfc(np.sqrt(c)))))
        U = factor*np.exp(-(k*self.width*np.tan(theta)/2)**2)

        return U

    def is_paraxial(self, k):
        return 2*np.pi/k < self.width

class hermite_gaussian_beam(beam):
    def __init__(self, l, m, width, polarization, amplitude=1, center=np.zeros(3)):
        super().__init__(width, polarization, amplitude, center)
        self.l = l
        self.m = m
    
    def scalar_potenital(self, x, y, z, k):
        rp = np.array([x - self.center[0], y - self.center[1], z - self.center[2]])
        rho_sq = rp[0]**2 + rp[1]**2
        wav = 2*np.pi/k

        wz = w(rp[2], self.width, wav)
        HG_l = eval_hermite(self.l, np.sqrt(2)*rp[0]/wz)
        HG_m = eval_hermite(self.m, np.sqrt(2)*rp[1]/wz)
        N = self.l + self.m

        amp = self.amplitude*self.width/wz * HG_l * HG_m * np.exp(-rho_sq/wz**2)
        phase = k*rp[2] + k*rho_sq*Rinv(rp[2],self.width,wav)/2 - (N+1)*gouy(rp[2],self.width,wav)

        return amp*np.exp(1j*phase)

    def scalar_potenital_ingoing(self, theta, phi, k):
        wav = 2*np.pi/k
        r = 1e6*wav
        x, y, z = miepy.coordinates.sph_to_cart(r, theta, phi)
        
        rp = np.array([x - self.center[0], y - self.center[1], z - self.center[2]])
        rho_sq = rp[0]**2 + rp[1]**2

        wz = w(rp[2], self.width, wav)
        HG_l = eval_hermite(self.l, np.sqrt(2)*rp[0]/wz)
        HG_m = eval_hermite(self.m, np.sqrt(2)*rp[1]/wz)
        N = self.l + self.m

        amp = self.amplitude*self.width/wz * HG_l * HG_m * np.exp(-rho_sq/wz**2)

        return amp

    def is_paraxial(self, k):
        return 2*np.pi/k < self.width

class laguerre_gaussian_beam(beam):
    def __init__(self, p, l, width, polarization, amplitude=1, center=np.zeros(3)):
        super().__init__(width, polarization, amplitude, center)
        self.p = p
        self.l = l
    
    def scalar_potenital(self, x, y, z, k):
        rp = np.array([x - self.center[0], y - self.center[1], z - self.center[2]])
        rho_sq = rp[0]**2 + rp[1]**2
        phi = np.arctan2(rp[1], rp[0])
        wav = 2*np.pi/k

        C = np.sqrt(2*factorial(self.p)/(np.pi*factorial(self.p + abs(self.l))))
        wz = w(rp[2], self.width, wav)

        Lpl = eval_genlaguerre(self.p, abs(self.l), 2*rho_sq/wz**2)
        N = abs(self.l) + 2*self.p

        amp = self.amplitude*C/wz * np.exp(-rho_sq/wz**2) * ((2*rho_sq)**0.5/wz)**abs(self.l) * Lpl
        phase = self.l*phi + k*rp[2] + k*rho_sq*Rinv(rp[2],self.width,wav)/2 - (N+1)*gouy(rp[2],self.width,wav)

        return amp*np.exp(1j*phase)

    def scalar_potenital_ingoing(self, theta, phi, k):
        wav = 2*np.pi/k
        r = 1e6*wav
        x, y, z = miepy.coordinates.sph_to_cart(r, theta, phi)

        rp = np.array([x - self.center[0], y - self.center[1], z - self.center[2]])
        rho_sq = rp[0]**2 + rp[1]**2
        phi = np.arctan2(rp[1], rp[0])

        C = np.sqrt(2*factorial(self.p)/(np.pi*factorial(self.p + abs(self.l))))
        wz = w(rp[2], self.width, wav)

        Lpl = eval_genlaguerre(self.p, abs(self.l), 2*rho_sq/wz**2)
        N = abs(self.l) + 2*self.p

        amp = self.amplitude*C/wz * np.exp(-rho_sq/wz**2) * ((2*rho_sq)**0.5/wz)**abs(self.l) * Lpl
        phase = self.l*phi

        return amp*np.exp(1j*phase)

    def is_paraxial(self, k):
        return 2*np.pi/k < self.width

def azimuthal_beam(width, amplitude=1, center=np.zeros(3)):
    """azimuthally polarized beam"""
    HG_1 = hermite_gaussian_beam(1, 0, width, [0,1], amplitude, center)
    HG_2 = hermite_gaussian_beam(0, 1, width, [-1,0], amplitude, center)
    return HG_1 + HG_2

def radial_beam(width, amplitude=1, center=np.zeros(3)):
    """radially polarized beam"""
    HG_1 = hermite_gaussian_beam(1, 0, width, [1,0], amplitude, center)
    HG_2 = hermite_gaussian_beam(0, 1, width, [0,1], amplitude, center)
    return HG_1 + HG_2

def shear_beam(width, amplitude=1, center=np.zeros(3)):
    """shear polarized beam"""
    HG_1 = hermite_gaussian_beam(1, 0, width, [0,1], amplitude, center)
    HG_2 = hermite_gaussian_beam(0, 1, width, [1,0], amplitude, center)
    return HG_1 + HG_2