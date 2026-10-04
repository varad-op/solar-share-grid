"""
tests/test_trade_simulator.py
=============================
Unit tests for trade_simulator.py.
"""

import unittest
import networkx as nx
import pandas as pd

from grid_presets import get_suburban_culdesac, get_asymmetric_hillside, get_isolated_islands
from trade_simulator import (
    calculate_path_loss,
    simulate_p2p_trade_cycle,
    generate_executive_report_bundle
)
from reachability_analyzer import run_full_reachability_audit
from link_optimizer import optimize_microgrid_links


class TestTradeSimulator(unittest.TestCase):

    def setUp(self):
        # Create a simple chain graph: S -> M1 -> M2 -> M3 -> C
        self.G_chain = nx.DiGraph()
        self.G_chain.add_node("S", home_id="S", owner_name="Solar Producer", solar_surplus_kw=10.0, demand_kw=0.0)
        self.G_chain.add_node("M1", home_id="M1", owner_name="Relay 1", solar_surplus_kw=0.0, demand_kw=0.0)
        self.G_chain.add_node("M2", home_id="M2", owner_name="Relay 2", solar_surplus_kw=0.0, demand_kw=0.0)
        self.G_chain.add_node("M3", home_id="M3", owner_name="Relay 3", solar_surplus_kw=0.0, demand_kw=0.0)
        self.G_chain.add_node("C", home_id="C", owner_name="Consumer", solar_surplus_kw=0.0, demand_kw=5.0)

        # 4 edges with 2.0% loss each
        self.G_chain.add_edge("S", "M1", line_loss_pct=2.0)
        self.G_chain.add_edge("M1", "M2", line_loss_pct=2.0)
        self.G_chain.add_edge("M2", "M3", line_loss_pct=2.0)
        self.G_chain.add_edge("M3", "C", line_loss_pct=2.0)

    def test_calculate_path_loss_single_hop(self):
        res = calculate_path_loss(self.G_chain, ["S", "M1"])
        self.assertEqual(res["hops"], 1)
        self.assertAlmostEqual(res["efficiency_multiplier"], 0.98, places=3)
        self.assertAlmostEqual(res["total_loss_pct"], 2.0, places=2)
        self.assertFalse(res["is_inefficient"])

    def test_calculate_path_loss_multi_hop_compounding(self):
        # 4 hops: (1 - 0.02)^4 = 0.98^4 = 0.92236816
        res = calculate_path_loss(self.G_chain, ["S", "M1", "M2", "M3", "C"])
        self.assertEqual(res["hops"], 4)
        expected_mult = (0.98) ** 4
        self.assertAlmostEqual(res["efficiency_multiplier"], expected_mult, places=4)
        # Should be flagged as inefficient because hops > 3
        self.assertTrue(res["is_inefficient"])

    def test_simulate_p2p_trade_cycle_chain(self):
        res = simulate_p2p_trade_cycle(self.G_chain)
        self.assertGreater(len(res["transactions"]), 0)
        txn = res["transactions"][0]

        # Verify conservation of energy: Sent = Delivered + Loss
        self.assertAlmostEqual(txn["Sent (kW)"], txn["Delivered (kW)"] + txn["Loss (kW)"], places=2)
        # Check consumer demand was met
        self.assertAlmostEqual(txn["Delivered (kW)"], 5.0, places=2)
        # Check 4-hop transfer flagged
        self.assertTrue(txn["is_inefficient"])
        self.assertIn("Inefficient", txn["Status"])

        # Grid summary
        self.assertAlmostEqual(res["total_delivered_kw"], 5.0, places=2)
        self.assertGreater(res["total_loss_kw"], 0.0)
        self.assertEqual(res["inefficient_transfers_count"], 1)
        self.assertGreater(res["total_savings_usd"], 0.0)
        self.assertGreater(res["total_savings_inr"], 0.0)

    def test_greedy_shortest_distance_matching(self):
        # Graph with 1 producer S and 2 consumers: Near (1 hop) and Far (2 hops)
        G = nx.DiGraph()
        G.add_node("S", home_id="S", solar_surplus_kw=5.0, demand_kw=0.0)
        G.add_node("Near", home_id="Near", solar_surplus_kw=0.0, demand_kw=5.0)
        G.add_node("Far", home_id="Far", solar_surplus_kw=0.0, demand_kw=5.0)
        G.add_edge("S", "Near", line_loss_pct=2.0)
        G.add_edge("Near", "Far", line_loss_pct=2.0)

        # Producer has 5.0 kW, Near needs 5.0 kW, Far needs 5.0 kW
        # Greedy algorithm MUST serve Near first due to shortest path (1 hop vs 2 hops)
        res = simulate_p2p_trade_cycle(G)
        self.assertGreater(len(res["transactions"]), 0)
        first_txn = res["transactions"][0]
        self.assertEqual(first_txn["Importer ID"], "Near")
        self.assertEqual(first_txn["Hops"], 1)

    def test_trade_simulation_on_suburban_preset(self):
        G, _ = get_suburban_culdesac()
        res = simulate_p2p_trade_cycle(G)
        self.assertIsInstance(res["ledger_df"], pd.DataFrame)
        self.assertGreater(res["total_sent_kw"], 0.0)
        self.assertGreater(res["total_delivered_kw"], 0.0)
        self.assertGreaterEqual(res["grid_efficiency_pct"], 90.0)

    def test_executive_report_bundle(self):
        G, _ = get_suburban_culdesac()
        audit = run_full_reachability_audit(G)
        opt = optimize_microgrid_links(G, top_k=3)
        trade = simulate_p2p_trade_cycle(G)

        report_csv = generate_executive_report_bundle(
            G=G,
            coverage_data=audit["coverage"],
            microgrid_metrics=audit["metrics"],
            transitive_closure_matrix=audit["reachability_matrix"],
            node_labels=audit["node_labels"],
            optimization_results=opt,
            trade_results=trade
        )

        self.assertIn("=== SECTION 1: EXECUTIVE MICROGRID SUMMARY & METRICS ===", report_csv)
        self.assertIn("=== SECTION 2: LEFT-OUT HOUSEHOLDS AUDIT ===", report_csv)
        self.assertIn("=== SECTION 3: WARSHALL TRANSITIVE CLOSURE MATRIX (R+) ===", report_csv)
        self.assertIn("=== SECTION 4: RECOMMENDED INFRASTRUCTURE EXPANSION PLAN ===", report_csv)
        self.assertIn("=== SECTION 5: P2P TRADE SETTLEMENT TRANSACTION LEDGER ===", report_csv)


if __name__ == "__main__":
    unittest.main()
