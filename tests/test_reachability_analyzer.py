"""
tests/test_reachability_analyzer.py
===================================
Unit tests for reachability_analyzer.py.
"""

import unittest
import pandas as pd
import networkx as nx

from grid_presets import (
    get_suburban_culdesac,
    get_asymmetric_hillside,
    get_isolated_islands,
    parse_custom_matrix
)
from reachability_analyzer import (
    analyze_solar_coverage,
    compute_microgrid_metrics,
    analyze_connectivity_components,
    run_full_reachability_audit
)


class TestReachabilityAnalyzer(unittest.TestCase):

    def setUp(self):
        self.culdesac_G, _ = get_suburban_culdesac()
        self.hillside_G, _ = get_asymmetric_hillside()
        self.islands_G, _ = get_isolated_islands()

    def test_coverage_suburban_culdesac(self):
        # Suburban culdesac has 5 homes with solar_surplus_kw > 0 (3 major prosumers + 2 partial)
        cov = analyze_solar_coverage(self.culdesac_G)
        self.assertEqual(cov["producers_count"], 5)
        self.assertEqual(cov["consumers_count"], 10)  # All homes have demand > 0
        self.assertEqual(cov["left_out_count"], 0)   # Well connected, 0 left out

        # DataFrames check
        self.assertIsInstance(cov["producers_df"], pd.DataFrame)
        self.assertIsInstance(cov["consumers_df"], pd.DataFrame)
        self.assertEqual(len(cov["producers_df"]), 5)
        self.assertEqual(len(cov["consumers_df"]), 10)

        # Check HOME_01 reachability set
        reach_p1 = cov["producers_reachability"]["HOME_01"]["reach_set"]
        self.assertGreater(len(reach_p1), 5)

    def test_left_out_households_in_isolated_islands(self):
        cov = analyze_solar_coverage(self.islands_G)
        # In Isolated Islands, Island 1 (Nerul) has HOME_01 (10 kW)
        # Island 2 (Seawoods) has HOME_06 (13 kW)
        # Within each island, homes can reach internal consumers
        # Let's verify incoming producers for HOME_08 (Island 2)
        c_h8 = cov["consumers_coverage"]["HOME_08"]
        self.assertIn("HOME_06", c_h8["incoming_producers"])
        self.assertNotIn("HOME_01", c_h8["incoming_producers"])

    def test_left_out_detection_synthetic_disconnected_node(self):
        # Create a graph with an isolated consumer having NO solar connection
        # Matrix: H1 -> H2, H3 is completely isolated
        csv_data = """0, 1, 0
0, 0, 0
0, 0, 0"""
        G, _ = parse_custom_matrix(csv_data)
        # HOME_01 has surplus=8, HOME_03 has demand=4, surplus=0
        cov = analyze_solar_coverage(G)
        self.assertEqual(cov["left_out_count"], 1)
        self.assertEqual(cov["left_out_households"][0]["home_id"], "HOME_03")

        metrics = compute_microgrid_metrics(G, cov)
        # 2 consumers (HOME_02 and HOME_03), 1 is isolated
        self.assertEqual(metrics["isolated_consumers_count"], 1)
        self.assertGreater(metrics["household_isolation_rate_pct"], 0.0)

    def test_microgrid_metrics_culdesac(self):
        metrics = compute_microgrid_metrics(self.culdesac_G)
        self.assertGreater(metrics["total_solar_generation_kw"], 20.0)
        self.assertGreater(metrics["total_neighborhood_demand_kw"], 20.0)
        self.assertEqual(metrics["household_isolation_rate_pct"], 0.0)
        self.assertGreater(metrics["solar_self_sufficiency_index_pct"], 50.0)

    def test_connectivity_components_culdesac(self):
        conn = analyze_connectivity_components(self.culdesac_G)
        self.assertIsInstance(conn["scc_df"], pd.DataFrame)
        self.assertIsInstance(conn["wcc_df"], pd.DataFrame)
        # In Suburban Cul-de-sac, it's 1 weakly connected component
        self.assertEqual(conn["wcc_count"], 1)
        self.assertTrue(conn["is_weakly_connected"])
        # Should have at least one large mutual trading ring (SCC)
        self.assertGreaterEqual(conn["mutual_trading_rings_count"], 1)

    def test_connectivity_components_hillside_dag(self):
        # A Directed Acyclic Graph (DAG) has only trivial SCCs of size 1!
        conn = analyze_connectivity_components(self.hillside_G)
        self.assertEqual(conn["scc_count"], 9)  # 9 nodes, each in its own SCC
        self.assertEqual(conn["mutual_trading_rings_count"], 0)
        self.assertEqual(conn["wcc_count"], 1)  # 1 connected physical topology

    def test_connectivity_components_isolated_islands(self):
        # Isolated Islands has 2 separate physical components (WCCs)
        conn = analyze_connectivity_components(self.islands_G)
        self.assertEqual(conn["wcc_count"], 2)
        self.assertFalse(conn["is_weakly_connected"])
        # Island 1 (5 nodes) and Island 2 (5 nodes)
        self.assertEqual(conn["wcc_list"][0]["size"], 5)
        self.assertEqual(conn["wcc_list"][1]["size"], 5)

    def test_run_full_reachability_audit(self):
        audit = run_full_reachability_audit(self.culdesac_G)
        self.assertIn("coverage", audit)
        self.assertIn("metrics", audit)
        self.assertIn("connectivity", audit)
        self.assertIn("reachability_matrix", audit)


if __name__ == "__main__":
    unittest.main()
