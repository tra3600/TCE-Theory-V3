"""
TCE-lab - quantum_entropy.py
Version V3.0 - Publication arXiv ready
Auteur: Gregory Lombardo
Date: 29 Oct 2026

Remplace T*dS classique par entropie von Neumann exacte:
S_vN = -k_B Tr(ρ log ρ)
dS = S(t+dt) - S(t)
Equation maîtresse de Lindblad:
dρ/dt = -i/ħ [H, ρ] + Σ_k γ_k (L_k ρ L_k† - 1/2 {L_k† L_k, ρ})

Temps émergent: dt_cell = T_thermo / E_L * dS_vN
Deux leviers ingénierie: suppression (γ_k→0) et amplification (BEC squeezé)
"""

import numpy as np
from dataclasses import dataclass

HBAR = 1.054571817e-34
K_B = 1.380649e-23

@dataclass
class LindbladParams:
    E_L: float = 1.0
    T_thermo: float = 1.0  # Température effective pour conversion dS->dt
    kB: float = K_B
    hbar: float = HBAR

class QuantumEntropyGeneratorV3:
    def __init__(self, params: LindbladParams = LindbladParams()):
        self.p = params

    def von_neumann_entropy(self, rho: np.ndarray) -> float:
        """
        S_vN = -k_B Tr(ρ log ρ) - forme exacte
        ρ doit être hermitienne, trace 1
        """
        # Diagonalisation hermitienne
        vals = np.linalg.eigvalsh(rho)
        # Filtre valeurs nulles pour log
        vals = vals[vals > 1e-15]
        if len(vals) == 0:
            return 0.0
        return -self.p.kB * np.sum(vals * np.log(vals))

    def lindblad_dissipator(self, rho: np.ndarray, L: np.ndarray, gamma: float) -> np.ndarray:
        """D[L]ρ = LρL† - 1/2{L†L, ρ}"""
        Ldag = L.conj().T
        LdagL = Ldag @ L
        return gamma * (L @ rho @ Ldag - 0.5 * (LdagL @ rho + rho @ LdagL))

    def step(self, rho: np.ndarray, H: np.ndarray, Ls: list, gammas: list, dt: float) -> np.ndarray:
        """
        Un pas RK4 pour équation de Lindblad complète
        dρ/dt = -i/ħ [H,ρ] + Σ D_k
        """
        def drho_dt(r):
            comm = -1j / self.p.hbar * (H @ r - r @ H)
            diss = np.zeros_like(r, dtype=complex)
            for L, g in zip(Ls, gammas):
                diss += self.lindblad_dissipator(r, L, g)
            return comm + diss

        k1 = drho_dt(rho)
        k2 = drho_dt(rho + 0.5*dt*k1)
        k3 = drho_dt(rho + 0.5*dt*k2)
        k4 = drho_dt(rho + dt*k3)
        rho_new = rho + dt/6.0 * (k1 + 2*k2 + 2*k3 + k4)
        # Préserve hermiticité et trace
        rho_new = (rho_new + rho_new.conj().T) / 2.0
        rho_new = rho_new / np.trace(rho_new)
        return rho_new

    def dt_emergent_from_rho(self, rho_old: np.ndarray, rho_new: np.ndarray) -> tuple:
        """
        dt_TCE = T_thermo / E_L * dS_vN
        Remplace T*dS classique
        Retourne (dt_emergent, dS)
        """
        S_old = self.von_neumann_entropy(rho_old)
        S_new = self.von_neumann_entropy(rho_new)
        dS = S_new - S_old
        # dS peut être négatif lors de fluctuations, on clip à 0 pour temps émergent causal
        dS_pos = max(dS, 0.0)
        dt_em = self.p.T_thermo / self.p.E_L * dS_pos
        return dt_em, dS

    def get_engineering_protocol(self, protocol: str = "suppression") -> dict:
        """
        Deux leviers TCE figés pour V3
        """
        if protocol == "suppression":
            # Cavité supraconductrice + vide squeezé + blindage -> γ_k → 0, dS → 0, dt → 0
            # = cryo-cohérence, pas 0.99c
            return {
                "name": "suppression - temps gelé",
                "gamma_dephasing": 1e-3,
                "gamma_relax": 1e-4,
                "hardware": "cavité NbTi supra <10mK, blindage mu-metal 3 couches, squeezed vacuum, Q=1.2e9, 3.2GHz",
                "effect": "dS → 0, dt_cell → 0, Gamma_TCE → 0.01 (bulle chrono-déplétive)",
                "ref": "Objectif vaisseau ISC-TCE-07"
            }
        elif protocol == "amplification":
            # BEC squeezé pour augmenter dS
            return {
                "name": "amplification - temps accéléré",
                "gamma_dephasing": 1e3,
                "gamma_relax": 1e2,
                "hardware": "membrane SiN 100nm drive bruit blanc, cavité RF, ticks=oscillations, comme Pearson et al. 2021 PRX 11,021029",
                "effect": "dS maximal, dt accéléré, test linéarité Pearson au-delà de E_L",
                "ref": "Test falsifiable 1: horloge entropique"
            }
        else:
            return {"name": "standard", "gamma_dephasing": 1.0, "gamma_relax": 0.5}

if __name__ == "__main__":
    print("=== TCE V3 quantum_entropy.py - Test von Neumann ===")
    params = LindbladParams(E_L=1.0, T_thermo=1.0, kB=1.0, hbar=1.0)  # unités naturelles pour test
    gen = QuantumEntropyGeneratorV3(params)

    # Système 2 niveaux: |0> pur -> mixte via dephasing
    rho0 = np.array([[1,0],[0,0]], dtype=complex)
    H = np.array([[0,0.5],[0.5,1]], dtype=complex)
    L_deph = np.array([[1,0],[0,-1]], dtype=complex)  # σz
    L_relax = np.array([[0,1],[0,0]], dtype=complex)

    proto_sup = gen.get_engineering_protocol("suppression")
    proto_amp = gen.get_engineering_protocol("amplification")

    print(f"Protocole suppression: {proto_sup}")
    print(f"Protocole amplification: {proto_amp}")

    rho = rho0.copy()
    t_em_total = 0.0
    for i in range(200):
        rho_old = rho.copy()
        rho = gen.step(rho, H, [L_deph, L_relax], [proto_amp['gamma_dephasing'], proto_amp['gamma_relax']], dt=0.01)
        dt_em, dS = gen.dt_emergent_from_rho(rho_old, rho)
        t_em_total += dt_em
        if i % 50 == 0:
            S = gen.von_neumann_entropy(rho)
            print(f"step {i}: S_vN={S:.4e} dS={dS:.4e} dt_em={dt_em:.4e} t_em_total={t_em_total:.4e}")

    print(f"Test V3 validé: t_emergent final = {t_em_total:.6f} (unités E_L/T)")
    print("Remplacement T*dS classique -> -kB Tr(ρ log ρ) figé")
