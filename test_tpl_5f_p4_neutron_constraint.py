import unittest

from tpl_5f_p4_neutron_constraint import evaluate_neutron_bound, reference_points


class TestTPL5FP4Neutron(unittest.TestCase):
    def test_10ev_outside_upper_range(self):
        r = evaluate_neutron_bound(10.0)
        self.assertFalse(r["within_source_range"])
        self.assertEqual(r["status"], "OUTSIDE_SOURCE_VALIDITY_RANGE")

    def test_10kev_inside_range_and_below_limit(self):
        r = evaluate_neutron_bound(1.0e4)
        self.assertTrue(r["within_source_range"])
        self.assertLess(r["g2_lambda2_fm2"], r["limit_g2_lambda2_fm2"])
        self.assertEqual(r["status"], "NOT_EXCLUDED_BY_THIS_NEUTRON_BOUND")

    def test_10mev_outside_lower_range(self):
        r = evaluate_neutron_bound(1.0e7)
        self.assertFalse(r["within_source_range"])
        self.assertEqual(r["status"], "OUTSIDE_SOURCE_VALIDITY_RANGE")

    def test_smaller_mixing_reduces_coupling_product(self):
        high = evaluate_neutron_bound(1.0e4, sin_theta=1.0e-6)
        low = evaluate_neutron_bound(1.0e4, sin_theta=5.0e-7)
        self.assertAlmostEqual(low["g2_lambda2_fm2"], high["g2_lambda2_fm2"] / 4.0)

    def test_default_reference_points_order(self):
        rows = reference_points()
        self.assertEqual([r["scalar_mass_eV"] for r in rows], [10.0, 1.0e4, 1.0e7])

    def test_invalid_zero_mass_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_neutron_bound(0.0)

    def test_bool_mass_rejected(self):
        with self.assertRaises(TypeError):
            evaluate_neutron_bound(True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
