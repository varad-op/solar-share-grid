"""
tests/test_closure.py
=====================
Unit tests for Solar Share Grid discrete mathematics and graph theory engine.
"""

import unittest
import numpy as np
import networkx as nx

from closure_engine import (
    compute_transitive_closure,
    extract_binary_relations,
    find_power_trading_paths
)
from grid_presets import (
    get_suburban_culdesac,
    get_asymmetric_hillside,
    get_isolated_islands,
    parse_custom_matrix,
    graph_to_adjacency_matrix
)


class TestClosureEngine(unittest.TestCase):

    def test_warshall_algorithm_basic_chain(self):
        # Directed chain: 0 -> 1 -> 2 -> 3
        # Expected reachability:
        # 0 -> 1, 2, 3
        # 1 -> 2, 3
        # 2 -> 3
        # 3 -> none
        adj = np.array([
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
            [0, 0, 0, 0],
        ], dtype=bool)

        R, reach_map = compute_transitive_closure(adj, node_labels=["A", "B", "C", "D"])
        expected_R = np.array([
            [0, 1, 1, 1],
            [0, 0, 1, 1],
            [0, 0, 0, 1],
            [0, 0, 0, 0],
        ], dtype=bool)

        np.testing.assert_array_equal(R, expected_R)
        self.assertEqual(reach_map["A"], ["B", "C", "D"])
        self.assertEqual(reach_map["B"], ["C", "D"])
        self.assertEqual(reach_map["C"], ["D"])
        self.assertEqual(reach_map["D"], [])

    def test_warshall_algorithm_with_steps(self):
        adj = np.array([
            [0, 1, 0],
            [0, 0, 1],
            [0, 0, 0],
        ], dtype=bool)

        R, reach_map, steps = compute_transitive_closure(
            adj, node_labels=["H1", "H2", "H3"], return_steps=True
        )

        self.assertEqual(len(steps), 4)  # Step 0 (initial) + 3 pivots
        self.assertEqual(steps[0]["step"], 0)
        self.assertEqual(steps[1]["pivot_label"], "H1")
        self.assertEqual(steps[2]["pivot_label"], "H2")
        # In step 2 (pivot H2), pair H1 -> H3 should be discovered!
        self.assertIn(("H1", "H3"), steps[2]["newly_reachable"])
        self.assertTrue(R[0, 2])

    def test_warshall_against_networkx(self):
        # Random directed graph with 6 nodes
        G = nx.erdos_renyi_graph(6, 0.35, directed=True, seed=42)
        nodelist = list(G.nodes())
        adj = nx.to_numpy_array(G, nodelist=nodelist, dtype=bool)

        R_warshall, _ = compute_transitive_closure(adj, node_labels=[str(n) for n in nodelist])

        # NetworkX transitive closure
        TC_nx = nx.transitive_closure(G)
        R_nx = nx.to_numpy_array(TC_nx, nodelist=nodelist, dtype=bool)

        # Note: NetworkX transitive closure maintains non-reflexive edges unless cycle exists
        np.testing.assert_array_equal(R_warshall, R_nx)

    def test_binary_relations_properties(self):
        # 1. Equivalence relation on 3 elements: partition {{1, 2}, {3}}
        # Has self loops and symmetric edges between 1 and 2
        adj_equiv = np.array([
            [1, 1, 0],
            [1, 1, 0],
            [0, 0, 1]
        ], dtype=bool)
        res_equiv = extract_binary_relations(adj_equiv, ["H1", "H2", "H3"])
        self.assertTrue(res_equiv["is_reflexive"])
        self.assertTrue(res_equiv["is_symmetric"])
        self.assertTrue(res_equiv["is_transitive"])
        self.assertTrue(res_equiv["is_equivalence_relation"])
        self.assertFalse(res_equiv["is_antisymmetric"])

        # 2. Strict DAG (Anti-symmetric, Irreflexive, Transitive before or after closure)
        adj_dag = np.array([
            [0, 1, 1],
            [0, 0, 1],
            [0, 0, 0]
        ], dtype=bool)
        res_dag = extract_binary_relations(adj_dag, ["H1", "H2", "H3"])
        self.assertFalse(res_dag["is_reflexive"])
        self.assertTrue(res_dag["is_irreflexive"])
        self.assertFalse(res_dag["is_symmetric"])
        self.assertTrue(res_dag["is_antisymmetric"])
        self.assertTrue(res_dag["is_transitive"])
        self.assertTrue(res_dag["is_dag"])

    def test_trading_paths_finder(self):
        adj = np.array([
            [0, 1, 0],
            [0, 0, 1],
            [0, 0, 0]
        ], dtype=bool)
        R, _ = compute_transitive_closure(adj, ["H1", "H2", "H3"])
        paths = find_power_trading_paths(R, ["H1", "H2", "H3"], "H1")
        self.assertEqual(paths["reachable_homes"], ["H2", "H3"])
        self.assertEqual(paths["unreachable_homes"], [])


class TestNeighborhoodPresets(unittest.TestCase):

    def test_suburban_culdesac_schema(self):
        G, meta = get_suburban_culdesac()
        self.assertEqual(G.number_of_nodes(), 10)
        self.assertEqual(meta["producers_count"], 3)
        self.assertEqual(meta["consumers_count"], 7)

        # Verify node attributes exist and are correct types
        for node, data in G.nodes(data=True):
            self.assertIn("home_id", data)
            self.assertEqual(data["home_id"], node)
            self.assertIn("owner_name", data)
            self.assertIsInstance(data["solar_surplus_kw"], float)
            self.assertIsInstance(data["demand_kw"], float)
            self.assertIsInstance(data["battery_storage_kwh"], float)
            self.assertIsInstance(data["pos"], tuple)
            self.assertEqual(len(data["pos"]), 2)

        # Verify edge attributes
        for u, v, data in G.edges(data=True):
            self.assertIn("transfer_capacity_kw", data)
            self.assertIn("is_bidirectional", data)
            self.assertIn("line_loss_pct", data)

    def test_asymmetric_hillside_is_dag(self):
        G, meta = get_asymmetric_hillside()
        self.assertEqual(G.number_of_nodes(), 9)
        self.assertTrue(nx.is_directed_acyclic_graph(G))

        adj, labels = graph_to_adjacency_matrix(G)
        rel = extract_binary_relations(adj, labels)
        self.assertTrue(rel["is_dag"])
        self.assertFalse(rel["has_cycles"])
        self.assertFalse(rel["is_symmetric"])

    def test_isolated_islands_partition(self):
        G, meta = get_isolated_islands()
        self.assertEqual(G.number_of_nodes(), 10)
        adj, labels = graph_to_adjacency_matrix(G)
        R, reach_map = compute_transitive_closure(adj, labels)

        # HOME_01 (Island 1) should NEVER reach HOME_06 to HOME_10 (Island 2)
        island_1_nodes = ["HOME_01", "HOME_02", "HOME_03", "HOME_04", "HOME_05"]
        island_2_nodes = ["HOME_06", "HOME_07", "HOME_08", "HOME_09", "HOME_10"]

        for n1 in island_1_nodes:
            for n2 in island_2_nodes:
                self.assertNotIn(n2, reach_map[n1])
                self.assertNotIn(n1, reach_map[n2])

    def test_custom_matrix_parser_csv(self):
        csv_text = """0, 1, 0
0, 0, 1
1, 0, 0"""
        G, meta = parse_custom_matrix(csv_text)
        self.assertEqual(G.number_of_nodes(), 3)
        self.assertEqual(G.number_of_edges(), 3)
        self.assertTrue(nx.is_strongly_connected(G))

    def test_custom_matrix_parser_json(self):
        json_text = '{"nodes": ["A", "B"], "matrix": [[0, 1], [0, 0]]}'
        G, meta = parse_custom_matrix(json_text)
        self.assertEqual(G.number_of_nodes(), 2)
        self.assertTrue(G.has_edge("A", "B"))
        self.assertFalse(G.has_edge("B", "A"))


if __name__ == "__main__":
    unittest.main()
