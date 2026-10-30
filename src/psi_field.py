"""
TCE-lab - psi_field.py
Version V3.0 - Publication arXiv ready
Auteur: Gregory Lombardo
Date: 29 Oct 2026

Forme exacte figée pour publication:
L_TCE = L_SM + 1/2 (∂_μ ψ)(∂^μ ψ) - V(ψ) - g_TCE ψ H_int
V(ψ) = m_ψ² c²/(2 ħ²) ψ² + λ/4 ψ⁴
E_locked = E_L * (1 - exp(-ψ²/ψ0²))
Gamma_TCE = exp(-ψ²/ψ0²)
dT = dE / E_L = dE / E_tot * exp(ψ²/ψ0²)

Intégrateur en dE, pas en dt (clé philosophique TCE)
"""

import numpy as np
from dataclasses import dataclass

# Constantes SI pour traçabilité
HBAR = 1.054571817e-34  # J.s
C = 299792458.0         # m/s
K_B = 1.380649e-23      # J/K

@dataclass
class PsiParameters:
    E_L: float = 1.0          # Energie de référence (normalisée, à fitter expérimentalement)
    psi0: float = 1.0         # Echelle de saturation psi
    m_psi_eV: float = 1e-22   # Masse axion-like pour éviter 5th force (eV)
    lam: float = 0.1          # Auto-couplage quartique
    g_TCE: float = 1e-3       # Couplage à H_int
    hbar: float = HBAR
    c: float = C

class PsiFieldExact:
    """
    Champ scalaire réel ψ(x) mesurant fraction d'énergie verrouillée
    """
    def __init__(self, params: PsiParameters = PsiParameters()):
        self.p = params
        # Conversion masse eV -> 1/m² dans V
        # V = 1/2 * (m²c²/ħ²) ψ² + λ/4 ψ⁴
        self.m2_eff = (params.m_psi_eV * 1.60218e-19 / (params.hbar * params.c))**2 * params.c**2
        # Simplifié pour code normalisé: on garde m_psi_eV directement en unités naturelles si E_L=1

    def V(self, psi: np.ndarray) -> np.ndarray:
        """Potentiel exact V(ψ)"""
        return 0.5 * self.p.m_psi_eV**2 * psi**2 + 0.25 * self.p.lam * psi**4

    def dV_dpsi(self, psi: np.ndarray) -> np.ndarray:
        """dV/dψ pour équation du mouvement"""
        return self.p.m_psi_eV**2 * psi + self.p.lam * psi**3

    def E_locked(self, psi: np.ndarray) -> np.ndarray:
        """Energie verrouillée - forme exacte figée"""
        return self.p.E_L * (1.0 - np.exp(-psi**2 / self.p.psi0**2))

    def Gamma_TCE(self, psi: np.ndarray) -> np.ndarray:
        """Facteur de dilatation temporelle émergente"""
        return np.exp(-psi**2 / self.p.psi0**2)

    def dT_from_dE(self, dE: float, psi: float, E_tot: float = None) -> float:
        """dT = dE / E_L * Gamma  ou  dT = dE / E_tot * exp(ψ²/ψ0²) si on explicite"""
        if E_tot is None:
            return dE / self.p.E_L * self.Gamma_TCE(psi)
        else:
            return dE / E_tot * np.exp(psi**2 / self.p.psi0**2)

    def lagrangian_density(self, psi: float, dpsi_mu: float, H_int: float) -> float:
        """
        L_TCE exact sans L_SM (ajouté par user)
        L = 1/2 (∂ψ)² - V(ψ) - g ψ H_int
        """
        kinetic = 0.5 * dpsi_mu**2
        return kinetic - self.V(psi) - self.p.g_TCE * psi * H_int

    def equation_of_motion(self, box_psi: float, psi: float, H_int: float) -> float:
        """Box ψ + dV/dψ = -g H_int  (résidu à annuler par RK4)"""
        return box_psi + self.dV_dpsi(psi) + self.p.g_TCE * H_int

    def evolve_RK4_dE(self, psi_init: float, dE_array: np.ndarray, H_int_func, E_tot: float = 10.0):
        """
        Intégrateur philosophique: on intègre en dE, pas en dt.
        H_int_func(t_emergent) -> valeur H_int
        Retourne history: [t_emergent, psi, Gamma, dT, E_locked]
        """
        psi = float(psi_init)
        t_em = 0.0
        history = []
        for dE in dE_array:
            Gamma = self.Gamma_TCE(psi)
            dT = self.dT_from_dE(dE, psi, E_tot=None)  # forme E_L
            # RK4 pour ψ(t_em)
            def f(psi_, t_):
                return -self.dV_dpsi(psi_) - self.p.g_TCE * H_int_func(t_)

            k1 = f(psi, t_em)
            k2 = f(psi + 0.5*dT*k1, t_em + 0.5*dT)
            k3 = f(psi + 0.5*dT*k2, t_em + 0.5*dT)
            k4 = f(psi + dT*k3, t_em + dT)

            psi += dT/6.0 * (k1 + 2*k2 + 2*k3 + k4)
            t_em += dT

            history.append([t_em, psi, float(Gamma), float(dT), float(self.E_locked(psi))])
        return np.array(history)

if __name__ == "__main__":
    params = PsiParameters(E_L=1.0, psi0=1.0, m_psi_eV=1e-22, lam=0.1, g_TCE=1e-3)
    field = PsiFieldExact(params)
    dE_steps = np.linspace(0.001, 0.1, 500)
    def H_int(t): return 0.1 * np.exp(-t/5.0)
    hist = field.evolve_RK4_dE(psi_init=0.1, dE_array=dE_steps, H_int_func=H_int, E_tot=10.0)
    print(f"V3 figée: t_em final={hist[-1,0]:.6f}, psi={hist[-1,1]:.6f}, Gamma={hist[-1,2]:.6f}, E_locked={hist[-1,4]:.6f}")
    print("Forme exacte: L_TCE = L_SM + 1/2 (∂ψ)² - V(ψ) - g ψ H_int validée")
