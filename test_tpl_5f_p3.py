import math
import unittest

from tpl_5f_p3 import (
    nucleon_scalar_charge,
    abs_sin_theta_from_p2_higgs_fraction,
    fermion_scalar_coupling,
    mass_window_table,
    scalar_mass_gev_to_ev,
    yukawa_alpha_relative,
    yukawa_potential_j,
    yukawa_range_m,
    yukawa_radial_force_n,
)


class TestTPL5FP3(unittest.TestCase):
    def test_range_30_gev(self):
        self.assertAlmostEqual(yukawa_range_m(scalar_mass_gev_to_ev(30)), 6.577566e-18, delta=1e-23)

    def test_range_50_gev(self):
        self.assertAlmostEqual(yukawa_range_m(scalar_mass_gev_to_ev(50)), 3.946540e-18, delta=1e-23)

    def test_range_200_gev(self):
        self.assertAlmostEqual(yukawa_range_m(scalar_mass_gev_to_ev(200)), 9.866349e-19, delta=1e-23)

    def test_range_500_gev(self):
        self.assertAlmostEqual(yukawa_range_m(scalar_mass_gev_to_ev(500)), 3.946540e-19, delta=1e-23)

    def test_low_mass_10_ev_range(self):
        self.assertAlmostEqual(yukawa_range_m(10), 1.973270e-8, delta=1e-14)

    def test_low_mass_10_mev_range(self):
        self.assertAlmostEqual(yukawa_range_m(1e7), 1.973270e-14, delta=1e-20)

    def test_p2_fraction_maps_to_mixing_magnitude(self):
        self.assertAlmostEqual(abs_sin_theta_from_p2_higgs_fraction(0.04), 0.2)

    def test_p2_zero_fraction_means_no_mixing(self):
        self.assertEqual(abs_sin_theta_from_p2_higgs_fraction(0.0), 0.0)

    def test_p2_invalid_fraction_blocked(self):
        with self.assertRaises(ValueError):
            abs_sin_theta_from_p2_higgs_fraction(1.01)

    def test_zero_mixing_gives_zero_fermion_coupling(self):
        self.assertEqual(fermion_scalar_coupling(0.105658, 0.0), 0.0)

    def test_coupling_uses_higgs_component(self):
        self.assertAlmostEqual(fermion_scalar_coupling(0.105658, 0.1), 0.1 * 0.105658 / 246.22)

    def test_zero_scalar_charge_gives_zero_potential(self):
        self.assertEqual(yukawa_potential_j(1e-6, 1e4, 0.0, 0.5), 0.0)

    def test_potential_and_force_consistent(self):
        r, m, qa, qb = 1e-8, 10.0, 0.2, 0.3
        step = r * 1e-5
        derivative = (yukawa_potential_j(r + step, m, qa, qb) -
                      yukawa_potential_j(r - step, m, qa, qb)) / (2 * step)
        force = yukawa_radial_force_n(r, m, qa, qb)
        self.assertAlmostEqual(force, -derivative, delta=abs(force) * 1e-8)

    def test_alpha_relative_zero_when_charge_zero(self):
        self.assertEqual(yukawa_alpha_relative(0.0, 1.0, 1.0, 1.0), 0.0)

    def test_invalid_mass_blocked(self):
        with self.assertRaises(ValueError):
            yukawa_range_m(0.0)

    def test_invalid_distance_blocked(self):
        with self.assertRaises(ValueError):
            yukawa_potential_j(0.0, 10.0, 1.0, 1.0)

    def test_invalid_mixing_blocked(self):
        with self.assertRaises(ValueError):
            fermion_scalar_coupling(1.0, 1.01)

    def test_mass_windows_are_separate(self):
        table = mass_window_table()
        self.assertEqual(len(table["collider_band_30_to_500_GeV"]), 4)
        self.assertEqual(len(table["low_mass_exploratory_band_10_eV_to_10_MeV"]), 2)
        self.assertGreater(table["low_mass_exploratory_band_10_eV_to_10_MeV"][0]["range_m"],
                           table["collider_band_30_to_500_GeV"][0]["range_m"])

    def test_nucleon_charge_uses_higgs_nucleon_form_factor(self):
        expected = 1e-6 * 0.30 * 0.939 / 246.22
        self.assertAlmostEqual(nucleon_scalar_charge(1e-6), expected, places=24)

    def test_nucleon_charge_zero_when_mixing_zero(self):
        self.assertEqual(nucleon_scalar_charge(0.0), 0.0)

    def test_nucleon_charge_zero_when_form_factor_zero(self):
        self.assertEqual(nucleon_scalar_charge(1e-6, f_N=0.0), 0.0)

    def test_nucleon_charge_rejects_form_factor_outside_unit_interval(self):
        with self.assertRaises(ValueError):
            nucleon_scalar_charge(1e-6, f_N=1.01)

    def test_nucleon_charge_rejects_invalid_mixing(self):
        with self.assertRaises(ValueError):
            nucleon_scalar_charge(1.01)


if __name__ == "__main__":
    unittest.main(verbosity=2)
