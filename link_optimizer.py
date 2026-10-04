"""
link_optimizer.py
=================
AI Line Optimization Engine for Solar Share Grid.

Solves the "Left-Out Household" problem by finding the single best missing
directed line (u, v) not in E to add to the microgrid.

Mathematical Model:
1. Candidate Missing Edges:
   All ordered pairs (u, v) not in E where u != v.
2. Reachability Delta:
   For candidate edge (u, v), construct D' = D union {(u, v)} and re-run
   Warshall's Transitive Closure:
   - Delta Powered Homes = Newly Connected Homes in D' - Connected Homes in D
   - Delta Unmet Demand Served = kW Demand of newly powered households
3. Line Efficiency Score:
   Score(u, v) = (Delta Powered Homes * Newly Served kW) / Euclidean_Distance(u, v)
4. Optimal Recommendation:
   Ranks candidate edges and selects the SINGLE best directed link (u, v)
   that maximizes newly served consumers per meter of line required.
"""

from typing import Dict, List, Tuple, Any, Optional, Set
import numpy as np
import pandas as pd
import networkx as nx

from closure_engine import compute_transitive_closure
from grid_presets import graph_to_adjacency_matrix
from reachability_analyzer import analyze_solar_coverage


def calculate_euclidean_distance(
    pos_u: Tuple[float, float],
    pos_v: Tuple[float, float]
) -> float:
    """
    Computes Euclidean distance between spatial positions of two households.
    Enforces a small positive minimum to prevent division by zero.
    """
    dx = pos_u[0] - pos_v[0]
    dy = pos_u[1] - pos_v[1]
    dist = float(np.hypot(dx, dy))
    return max(dist, 0.1)


def find_candidate_missing_edges(G: nx.DiGraph) -> List[Tuple[str, str]]:
    """
    Identifies all directed candidate pairs (u, v) where u != v and (u, v) not in G.edges.
    """
    nodes = list(G.nodes())
    existing_edges = set(G.edges())
    candidates = []

    for u in nodes:
        for v in nodes:
            if u != v and (u, v) not in existing_edges:
                candidates.append((u, v))
    return candidates


def evaluate_single_candidate(
    G: nx.DiGraph,
    u: str,
    v: str,
    base_left_out_ids: Set[str],
    producers: List[str],
    node_labels: List[str],
    node_to_idx: Dict[str, int],
    base_adj: np.ndarray
) -> Dict[str, Any]:
    """
    Evaluates the reachability delta and efficiency score of adding directed edge (u, v).
    """
    n = len(node_labels)
    u_idx = node_to_idx[u]
    v_idx = node_to_idx[v]

    # Create temporary adjacency matrix for D' = D union {(u, v)}
    temp_adj = base_adj.copy()
    temp_adj[u_idx, v_idx] = True

    # Compute Transitive Closure on D'
    R_prime, _ = compute_transitive_closure(temp_adj, node_labels)

    # Check which of the base_left_out_ids are now reached by at least one producer in D'
    newly_connected_homes = []
    delta_demand_kw = 0.0

    for left_id in base_left_out_ids:
        left_idx = node_to_idx[left_id]
        # Does any producer p reach left_id in D'?
        is_now_reached = any(R_prime[node_to_idx[p], left_idx] for p in producers if p != left_id)
        if is_now_reached:
            newly_connected_homes.append(left_id)
            delta_demand_kw += float(G.nodes[left_id].get("demand_kw", 0.0))

    delta_powered_homes = len(newly_connected_homes)
    delta_demand_kw = round(delta_demand_kw, 2)

    # Also compute overall multi-hop reachability expansion (useful when delta_powered_homes == 0)
    # Total producer-to-consumer pairs in D' vs D
    producer_indices = [node_to_idx[p] for p in producers]
    total_reach_count = int(np.sum(R_prime[producer_indices, :])) if producer_indices else 0

    # Euclidean distance between nodes u and v
    pos_u = G.nodes[u].get("pos", (0.0, 0.0))
    pos_v = G.nodes[v].get("pos", (0.0, 0.0))
    dist = calculate_euclidean_distance(pos_u, pos_v)

    # Primary Score: (Delta Powered Homes * Newly Served kW) / Distance
    if delta_powered_homes > 0:
        score = round((delta_powered_homes * delta_demand_kw) / dist, 4)
    else:
        # Fallback score if no unserved homes exist: measures reachability expansion per unit distance
        score = round(total_reach_count / (dist * 10.0), 4)

    return {
        "source": u,
        "target": v,
        "edge_tuple": (u, v),
        "source_name": G.nodes[u].get("owner_name", u),
        "target_name": G.nodes[v].get("owner_name", v),
        "delta_powered_homes": delta_powered_homes,
        "delta_demand_kw": delta_demand_kw,
        "newly_connected_homes": newly_connected_homes,
        "euclidean_distance": round(dist, 2),
        "score": score,
        "total_reach_count": total_reach_count
    }


def optimize_microgrid_links(
    G: nx.DiGraph,
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Ranks all candidate missing directed edges (u, v) not in E and selects
    the SINGLE best directed link to solve left-out households.

    Parameters
    ----------
    G : nx.DiGraph
        Current directed microgrid graph.
    top_k : int, default=5
        Number of top candidate links to return in the comparison table.

    Returns
    -------
    dict containing:
        - 'has_left_out': bool
        - 'best_link': dict or None
        - 'top_candidates': list of dicts
        - 'top_candidates_df': pd.DataFrame for UI display
        - 'summary_text': human-readable recommendation
    """
    base_adj, node_labels = graph_to_adjacency_matrix(G)
    node_to_idx = {n: i for i, n in enumerate(node_labels)}

    # Run baseline coverage analysis
    coverage = analyze_solar_coverage(G)
    left_out_households = coverage["left_out_households"]
    base_left_out_ids = {h["home_id"] for h in left_out_households}
    has_left_out = len(base_left_out_ids) > 0

    producers = [
        n for n in node_labels if float(G.nodes[n].get("solar_surplus_kw", 0.0)) > 0
    ]

    candidates = find_candidate_missing_edges(G)
    if not candidates:
        return {
            "has_left_out": has_left_out,
            "best_link": None,
            "top_candidates": [],
            "top_candidates_df": pd.DataFrame(),
            "summary_text": "Graph is already a complete directed network. No missing links to add."
        }

    evaluated = []
    for u, v in candidates:
        eval_res = evaluate_single_candidate(
            G=G,
            u=u,
            v=v,
            base_left_out_ids=base_left_out_ids,
            producers=producers,
            node_labels=node_labels,
            node_to_idx=node_to_idx,
            base_adj=base_adj
        )
        evaluated.append(eval_res)

    # Sorting Logic:
    # 1. Primary: score descending
    # 2. Secondary: delta_powered_homes descending
    # 3. Tertiary: delta_demand_kw descending
    # 4. Quaternary: euclidean_distance ascending
    evaluated.sort(
        key=lambda item: (
            item["score"],
            item["delta_powered_homes"],
            item["delta_demand_kw"],
            -item["euclidean_distance"]
        ),
        reverse=True
    )

    top_candidates = evaluated[:top_k]
    best_link = top_candidates[0] if top_candidates else None

    # Construct DataFrame for UI
    df_rows = []
    for rank, item in enumerate(top_candidates, start=1):
        df_rows.append({
            "Rank": f"#{rank}",
            "Recommended Edge": f"{item['source']} ➔ {item['target']}",
            "Source Home": f"{item['source']} ({item['source_name']})",
            "Target Home": f"{item['target']} ({item['target_name']})",
            "Δ Powered Homes": f"+{item['delta_powered_homes']} home(s)",
            "Δ Unmet Demand (kW)": f"+{item['delta_demand_kw']:.1f} kW",
            "Distance (Units)": f"{item['euclidean_distance']:.2f}",
            "Efficiency Score": item["score"],
            "Newly Powered List": ", ".join(item["newly_connected_homes"]) if item["newly_connected_homes"] else "(Redundancy)"
        })

    top_candidates_df = pd.DataFrame(df_rows) if df_rows else pd.DataFrame()

    # Formulate human-readable recommendation summary
    if best_link and best_link["delta_powered_homes"] > 0:
        summary_text = (
            f"Add 1-way feeder line from {best_link['source']} ({best_link['source_name']}) "
            f"to {best_link['target']} ({best_link['target_name']}). "
            f"Directly connects +{best_link['delta_powered_homes']} previously isolated household(s), "
            f"delivering +{best_link['delta_demand_kw']:.1f} kW of clean rooftop solar power "
            f"over a distance of {best_link['euclidean_distance']:.2f} units."
        )
    elif best_link:
        summary_text = (
            f"Microgrid already has 100% solar reachability. Top recommended reinforcement line is "
            f"{best_link['source']} ➔ {best_link['target']} to maximize network redundancy and mutual trading capacity."
        )
    else:
        summary_text = "No candidate link available."

    return {
        "has_left_out": has_left_out,
        "best_link": best_link,
        "top_candidates": top_candidates,
        "top_candidates_df": top_candidates_df,
        "summary_text": summary_text
    }
