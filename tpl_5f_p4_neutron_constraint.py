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

A second, independent constraint is also recorded from Fiorillo et al., Phys.
Rev. Lett. 135, 211003 (2025): isolated-neutron-star cooling. The paper gives
a Higgs-portal translation sin(theta) <= 6e-11 for light scalars in the
approximate eV-to-MeV mass domain. Its exact g_N(m) curve is mass-dependent;
this module uses the authors' headline Higgs-portal translation, not a digitized
interpolation of Fig. 1. The paper's convention g_N ~= 8e-4 sin(theta) differs
from the P3 nominal f_N=0.30 coefficient (about 1.144e-3 sin(theta)); both are
retained explicitly rather than silently equated.

Neither constraint is a discovery claim. OUTSIDE_RANGE is not evidence that a
parameter point is experimentally allowed.
"""
from __future__ import annotations

from math import isfinite

from tpl_5f_p3 import nucleon_scalar_charge, yukawa_range_m

FM_PER_M = 1.0e15
NEUTRON_LIMIT_G2_LAMBDA2_FM2 = 0.016
NEUTRON_LIMIT_CL = 0.95
NEUTRON_RANGE_MIN_M = 1.0e-12
NEUTRON_RANGE_MAX_M = 1.0e-10

NS_COOLING_MASS_MIN_EV = 1.0
NS_COOLING_MASS_MAX_EV = 1.0e6
NS_HIGGS_PORTAL_SIN_THETA_LIMIT = 6.0e-11
NS_SOURCE_GN_PER_SIN_THETA = 8.0e-4
NS_SOURCE_GN_LIMIT_BELOW_100_EV = 5.0e-14


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


def evaluate_neutron_star_cooling_bound(
    scalar_mass_eV: float,
    sin_theta: float = 1.0e-6,
) -> dict[str, float | str | bool]:
    """Apply the 2025 neutron-star-cooling Higgs-portal summary bound.

    The publication's detailed 95% CL limit is a mass-dependent curve (Fig. 1).
    This helper applies only its headline Higgs-portal translation
    |sin(theta)| <= 6e-11 over the approximate eV-to-MeV scalar-mass domain;
    it does not digitize/interpolate the full curve. At m < 100 eV the paper
    also states g_N <= 5e-14. The source's g_N ~= 8e-4 sin(theta) convention
    is returned separately from P3's f_N=0.30 convention.
    """
    if isinstance(scalar_mass_eV, bool) or not isinstance(scalar_mass_eV, (int, float)):
        raise TypeError("scalar_mass_eV must be a real number")
    mass = float(scalar_mass_eV)
    if not isfinite(mass) or mass <= 0.0:
        raise ValueError("scalar_mass_eV must be finite and > 0")
    if isinstance(sin_theta, bool) or not isinstance(sin_theta, (int, float)):
        raise TypeError("sin_theta must be a real number")
    st = float(sin_theta)
    if not isfinite(st) or abs(st) > 1.0:
        raise ValueError("sin_theta must be finite and lie in [-1, 1]")

    in_mass_domain = NS_COOLING_MASS_MIN_EV <= mass <= NS_COOLING_MASS_MAX_EV
    source_gn = NS_SOURCE_GN_PER_SIN_THETA * abs(st)
    ratio = abs(st) / NS_HIGGS_PORTAL_SIN_THETA_LIMIT
    if not in_mass_domain:
        status = "OUTSIDE_SOURCE_MASS_DOMAIN"
        excluded = False
    elif ratio > 1.0:
        status = "ABOVE_NEUTRON_STAR_HIGGS_PORTAL_SUMMARY_BOUND"
        excluded = True
    else:
        status = "NOT_EXCLUDED_BY_THIS_SUMMARY_BOUND"
        excluded = False

    explicit_low_mass_gn_limit = None
    low_mass_gn_ratio = None
    if mass < 100.0:
        explicit_low_mass_gn_limit = NS_SOURCE_GN_LIMIT_BELOW_100_EV
        low_mass_gn_ratio = source_gn / explicit_low_mass_gn_limit

    return {
        "scalar_mass_eV": mass,
        "sin_theta": st,
        "source_mass_min_eV_approx": NS_COOLING_MASS_MIN_EV,
        "source_mass_max_eV_approx": NS_COOLING_MASS_MAX_EV,
        "within_source_mass_domain": in_mass_domain,
        "higgs_portal_sin_theta_limit": NS_HIGGS_PORTAL_SIN_THETA_LIMIT,
        "fraction_of_higgs_portal_mixing_limit": ratio,
        "source_g_N_per_sin_theta": NS_SOURCE_GN_PER_SIN_THETA,
        "source_g_N_at_input": source_gn,
        "source_g_N_limit_below_100_eV": explicit_low_mass_gn_limit,
        "fraction_of_explicit_low_mass_g_N_limit": low_mass_gn_ratio,
        "status": status,
        "excluded_by_this_summary_bound": excluded,
        "confidence_level": 0.95,
        "limit_interpretation": "Headline Higgs-portal translation; exact Fig. 1 constraint varies with scalar mass and is not digitized here.",
    }
