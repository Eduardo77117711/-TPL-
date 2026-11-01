#!/usr/bin/env python3
"""TPL-5F-P4 — compare the Higgs-mixed nucleon charge with neutron limits.

Primary constraint adopted:
  Nesvizhevsky, Pignol & Protasov, arXiv:0711.2298 / Phys. Rev. D 77, 034020
  Eq. (13): g^2 * lambda^2 <= 0.016 fm^2 at 95% CL, over 1e-12–1e-10 m.

The neutron has scalar charge Q_N. In the source convention, the atom/nucleus
has approximately A unit charges and the neutron has one; for the Higgs-mixed
model this maps to g^2 = Q_N^2 and Q_A ~= A Q_N. This additive-nucleon
approximation is explicit and does not include nuclear binding/composition
corrections or environmental screening.

This module evaluates only the stated bound and its stated range. It does not
combine unrelated exclusions or claim discovery/non-exclusion outside range.
"""
from __future__ import annotations

from math import isfinite

from tpl_5f_p3 import nucleon_scalar_charge, yukawa_range_m

FM_PER_M = 1.0e15
NEUTRON_LIMIT_G2_LAMBDA2_FM2 = 0.016
NEUTRON_LIMIT_CL = 0.95
NEUTRON_RANGE_MIN_M = 1.0e-12
NEUTRON_RANGE_MAX_M = 1.0e-10


def evaluate_neutron_bound(
    scalar_mass_eV: float,
    sin_theta: float = 1.0e-6,
    f_N: float = 0.30,
) -> dict[str, float | str | bool]:
    """Evaluate the neutron-scattering 95% CL constraint at one scalar mass."""
    if isinstance(scalar_mass_eV, bool) or not isinstance(scalar_mass_eV, (int, float)):
        raise TypeError("scalar_mass_eV must be a real number")
    mass = float(scalar_mass_eV)
    if not isfinite(mass) or mass <= 0.0:
        raise ValueError("scalar_mass_eV must be finite and > 0")

    q_n = nucleon_scalar_charge(sin_theta=sin_theta, f_N=f_N)
    lam_m = yukawa_range_m(mass)
    lam_fm = lam_m * FM_PER_M
    g2_lambda2 = q_n * q_n * lam_fm * lam_fm
    in_range = NEUTRON_RANGE_MIN_M <= lam_m <= NEUTRON_RANGE_MAX_M
    ratio = g2_lambda2 / NEUTRON_LIMIT_G2_LAMBDA2_FM2

    if not in_range:
        status = "OUTSIDE_SOURCE_VALIDITY_RANGE"
        excluded_by_this_bound = False
    elif g2_lambda2 > NEUTRON_LIMIT_G2_LAMBDA2_FM2:
        status = "EXCLUDED_BY_NEUTRON_BOUND"
        excluded_by_this_bound = True
    else:
        status = "NOT_EXCLUDED_BY_THIS_NEUTRON_BOUND"
        excluded_by_this_bound = False

    return {
        "scalar_mass_eV": mass,
        "sin_theta": float(sin_theta),
        "f_N": float(f_N),
        "Q_N": q_n,
        "lambda_m": lam_m,
        "lambda_fm": lam_fm,
        "g2_lambda2_fm2": g2_lambda2,
        "limit_g2_lambda2_fm2": NEUTRON_LIMIT_G2_LAMBDA2_FM2,
        "fraction_of_limit": ratio,
        "source_range_min_m": NEUTRON_RANGE_MIN_M,
        "source_range_max_m": NEUTRON_RANGE_MAX_M,
        "within_source_range": in_range,
        "excluded_by_this_bound": excluded_by_this_bound,
        "status": status,
        "confidence_level": NEUTRON_LIMIT_CL,
    }


def reference_points(sin_theta: float = 1.0e-6, f_N: float = 0.30) -> list[dict[str, float | str | bool]]:
    """Three requested points: 10 eV, 10 keV and 10 MeV."""
    return [evaluate_neutron_bound(m, sin_theta, f_N) for m in (10.0, 1.0e4, 1.0e7)]
