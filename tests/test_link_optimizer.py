"""
tests/test_link_optimizer.py
============================
Unit tests for link_optimizer.py.
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
from link_optimizer import (
    find_candidate_missing_edges,
    evaluate_single_candidate,
    optimize_microgrid_links,
    calculate_euclidean_distance
)


class TestLinkOptimizer(unittest.TestCase):

    def test_euclidean_distance(self):
        d = calculate_euclidean_distance((0.0, 0.0), (3.0, 4.0))
        self.assertAlmostEqual(d, 5.0)

        # Min distance enforcement
        d_zero = calculate_euclidean_distance((1.0, 1.0), (1.0, 1.0))
        self.assertGreaterEqual(d_zero, 0.1)

    def test_find_candidate_missing_edges(self):
        G = nx.DiGraph()
        G.add_nodes_from(["A", "B", "C"])
        G.add_edge("A", "B")
        candidates = find_candidate_missing_edges(G)

        # Total directed pairs = 3 * 2 = 6. 1 edge exists, so 5 candidates.
        self.assertEqual(len(candidates), 5)
        self.assertNotIn(("A", "B"), candidates)
        self.assertIn(("B", "A"), candidates)
        self.assertIn(("A", "C"), candidates)
        self.assertIn(("C", "A"), candidates)

    def test_optimization_with_left_out_household(self):
        # Graph: H1 is producer (surplus=10, pos=(0,0))
        # H2 is consumer (demand=4, pos=(1,0)), H1 -> H2
        # H3 is consumer (demand=5, pos=(2,0)), completely isolated!
        G = nx.DiGraph()
        G.add_node("H1", home_id="H1", owner_name="Solar Hub", solar_surplus_kw=10.0, demand_kw=1.0, battery_storage_kwh=10.0, pos=(0.0, 0.0), is_producer=True)
        G.add_node("H2", home_id="H2", owner_name="Mid Consumer", solar_surplus_kw=0.0, demand_kw=4.0, battery_storage_kwh=2.0, pos=(1.0, 0.0), is_producer=False)
        G.add_node("H3", home_id="H3", owner_name="Isolated Consumer", solar_surplus_kw=0.0, demand_kw=5.0, battery_storage_kwh=0.0, pos=(2.0, 0.0), is_producer=False)
        G.add_edge("H1", "H2", transfer_capacity_kw=6.0, is_bidirectional=False, line_loss_pct=2.0)

        res = optimize_microgrid_links(G, top_k=3)
        self.assertTrue(res["has_left_out"])
        self.assertIsNotNone(res["best_link"])

        # Candidate H2 -> H3 distance is 1.0, newly serves H3 (5 kW) -> score = (1 * 5) / 1.0 = 5.0
        # Candidate H1 -> H3 distance is 2.0, newly serves H3 (5 kW) -> score = (1 * 5) / 2.0 = 2.5
        # Therefore H2 -> H3 should be ranked #1!
        best = res["best_link"]
        self.assertEqual(best["source"], "H2")
        self.assertEqual(best["target"], "H3")
        self.assertEqual(best["delta_powered_homes"], 1)
        self.assertEqual(best["delta_demand_kw"], 5.0)
        self.assertAlmostEqual(best["score"], 5.0, places=2)

        # DataFrame check
        self.assertIsInstance(res["top_candidates_df"], pd.DataFrame)
        self.assertGreater(len(res["top_candidates_df"]), 0)

    def test_optimization_on_suburban_grid(self):
        G, _ = get_suburban_culdesac()
        res = optimize_microgrid_links(G, top_k=3)
        # In Suburban, 100% connected, so has_left_out is False
        self.assertFalse(res["has_left_out"])
        self.assertIsNotNone(res["best_link"])
        self.assertIn("Microgrid already has 100% solar reachability", res["summary_text"])

    def test_optimization_on_severed_line(self):
        G, _ = get_suburban_culdesac()
        # Sever power to HOME_02 (remove all incoming edges to HOME_02)
        incoming = list(G.predecessors("HOME_02"))
        for u in incoming:
            G.remove_edge(u, "HOME_02")

        res = optimize_microgrid_links(G, top_k=3)
        self.assertTrue(res["has_left_out"])
        # Best link should target HOME_02 to restore its power!
        best = res["best_link"]
        self.assertEqual(best["target"], "HOME_02")
        self.assertGreater(best["delta_powered_homes"], 0)

    def test_optimization_and_reconnection_solves_left_out(self):
        G, _ = get_suburban_culdesac()
        # Sever power to HOME_02
        for u in list(G.predecessors("HOME_02")):
            G.remove_edge(u, "HOME_02")

        # Verify HOME_02 is left out
        res1 = optimize_microgrid_links(G, top_k=3)
        self.assertTrue(res1["has_left_out"])
        best = res1["best_link"]
        self.assertEqual(best["target"], "HOME_02")

        # Connect the AI recommended edge
        G.add_edge(best["source"], best["target"], transfer_capacity_kw=6.0, line_loss_pct=1.8)

        # Re-evaluate: left-out households should now be eliminated!
        res2 = optimize_microgrid_links(G, top_k=3)
        self.assertFalse(res2["has_left_out"])


if __name__ == "__main__":
    unittest.main()
