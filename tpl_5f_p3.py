#!/usr/bin/env python3
"""TPL-5F-P3 — Yukawa potential, force, range and dimensionless strength.

P3 consumes (does not recompute) the scalar mass m_S and Higgs-mixing angle
from the existing Phi_Omega P1/P2 work. It models pointlike fermion couplings
at tree level. Composite macroscopic bodies require independently justified
scalar charges (including nucleon matrix elements, binding effects and
composition); screening mechanisms are outside this module.

Conventions:
- SI units for r, V and F.
- Fermion masses and vev are supplied in GeV.
- Scalar mass is supplied in eV (or GeV via the explicit converter).
- Scalar charges are dimensionless. For a point fermion,
  g_Sf = sin(theta) * m_f / v.

This is a calculation module, not evidence that a fifth force exists.
"""
from __future__ import annotations

from math import exp, isfinite, pi, sqrt

HBAR_J_S = 1.054571817e-34
C_M_S = 299_792_458.0
EV_J = 1.602176634e-19
HBAR_C_EV_M = HBAR_J_S * C_M_S / EV_J
G_NEWTON = 6.67430e-11
V_HIGGS_GEV = 246.22


def _finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _positive(value: float, name: str) -> float:
    result = _finite(value, name)
    if result <= 0.0:
        raise ValueError(f"{name} must be > 0")
    return result


def scalar_mass_gev_to_ev(mass_gev: float) -> float:
    """Convert a positive scalar mass from GeV to eV."""
    return _positive(mass_gev, "mass_gev") * 1.0e9


def yukawa_range_m(mass_eV: float) -> float:
    """Compton range lambda_5 = hbar/(m_S*c), with m_S expressed in eV."""
    return HBAR_C_EV_M / _positive(mass_eV, "mass_eV")


def abs_sin_theta_from_p2_higgs_fraction(new_scalar_higgs_fraction: float) -> float:
    """Recover |sin(theta)| from P2's Higgs fraction for the new scalar S.

    The existing P2 portal script reports the new-state Higgs fraction as
    (component along h)^2 = sin(theta)^2. The sign of the mixing eigenvector
    is a field-redefinition convention and is not fixed by this fraction.
    """
    fraction = _finite(new_scalar_higgs_fraction, "new_scalar_higgs_fraction")
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("new_scalar_higgs_fraction must lie in [0, 1]")
    return sqrt(fraction)


def fermion_scalar_coupling(
    fermion_mass_gev: float,
    sin_theta: float,
    vev_gev: float = V_HIGGS_GEV,
) -> float:
    """Tree-level scalar coupling g_Sf = sin(theta) * m_f / v."""
    mf = _positive(fermion_mass_gev, "fermion_mass_gev")
    st = _finite(sin_theta, "sin_theta")
    if abs(st) > 1.0:
        raise ValueError("sin_theta must lie in [-1, 1]")
    vev = _positive(vev_gev, "vev_gev")
    return st * mf / vev


def nucleon_scalar_charge(
    sin_theta: float,
    f_N: float = 0.30,
    nucleon_mass_gev: float = 0.939,
    vev_gev: float = V_HIGGS_GEV,
) -> float:
    """Higgs-mixed scalar charge of a nucleon: Q_N = sin(theta)*f_N*m_N/v.

    This is a nucleon-level effective coupling. It does not by itself provide
    the full scalar charge of a macroscopic body; nuclear binding, proton/neutron
    composition and isotope-dependent matrix elements may also be required.
    """
    st = _finite(sin_theta, "sin_theta")
    if abs(st) > 1.0:
        raise ValueError("sin_theta must lie in [-1, 1]")
    fn = _finite(f_N, "f_N")
    if not 0.0 <= fn <= 1.0:
        raise ValueError("f_N must lie in [0, 1]")
    mn = _positive(nucleon_mass_gev, "nucleon_mass_gev")
    vev = _positive(vev_gev, "vev_gev")
    return st * fn * mn / vev


def yukawa_potential_j(
    distance_m: float,
    scalar_mass_eV: float,
    charge_a: float,
    charge_b: float,
) -> float:
    """V_5(r) = -hbar*c*Q_A*Q_B/(4*pi*r)*exp(-r/lambda), in joules."""
    r = _positive(distance_m, "distance_m")
    lam = yukawa_range_m(scalar_mass_eV)
    qa = _finite(charge_a, "charge_a")
    qb = _finite(charge_b, "charge_b")
    return -(HBAR_J_S * C_M_S) * qa * qb / (4.0 * pi * r) * exp(-r / lam)


def yukawa_radial_force_n(
    distance_m: float,
    scalar_mass_eV: float,
    charge_a: float,
    charge_b: float,
) -> float:
    """Signed radial force in newtons; negative means attractive/inward."""
    r = _positive(distance_m, "distance_m")
    lam = yukawa_range_m(scalar_mass_eV)
    qa = _finite(charge_a, "charge_a")
    qb = _finite(charge_b, "charge_b")
    prefactor = -(HBAR_J_S * C_M_S) * qa * qb / (4.0 * pi)
    return prefactor * exp(-r / lam) * (1.0 / (r * r) + 1.0 / (lam * r))


def yukawa_alpha_relative(
    charge_a: float,
    charge_b: float,
    mass_a_kg: float,
    mass_b_kg: float,
) -> float:
    """Relative Yukawa strength alpha_5 in the usual gravity-normalized form.

    V_5/V_Newton = alpha_5 * exp(-r/lambda_5), for point sources with
    Newtonian masses mass_a_kg and mass_b_kg and scalar charges charge_a/b.
    """
    qa = _finite(charge_a, "charge_a")
    qb = _finite(charge_b, "charge_b")
    ma = _positive(mass_a_kg, "mass_a_kg")
    mb = _positive(mass_b_kg, "mass_b_kg")
    return (HBAR_J_S * C_M_S * qa * qb) / (4.0 * pi * G_NEWTON * ma * mb)


def mass_window_table() -> dict[str, list[dict[str, float]]]:
    """Reference Compton ranges for the two proposed mass windows."""
    collider_gev = (30.0, 50.0, 200.0, 500.0)
    lab_eV = (10.0, 1.0e7)  # 10 eV to 10 MeV; exploratory band, not a limit.
    return {
        "collider_band_30_to_500_GeV": [
            {"mass_GeV": m, "range_m": yukawa_range_m(scalar_mass_gev_to_ev(m))}
            for m in collider_gev
        ],
        "low_mass_exploratory_band_10_eV_to_10_MeV": [
            {"mass_eV": m, "range_m": yukawa_range_m(m)} for m in lab_eV
        ],
    }
