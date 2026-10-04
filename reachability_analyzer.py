"""
reachability_analyzer.py
========================
Reachability & Coverage Analysis Engine for Solar Share Grid.

Module 2 Analysis Engine implementing:
1. Reachability & Coverage Analysis:
   - Reachability set Reach(v) for every solar producer (solar_surplus_kw > 0).
   - Total reachable solar power available to each consumer household.
   - Left-out household identification: households with demand_kw > 0 that
     have no incoming directed path from ANY solar producer:
     Reach^-1(v) \\cap {u | surplus(u) > 0} = empty set.
2. Microgrid Metrics:
   - Total Solar Generation Available (kW).
   - Total Neighborhood Power Demand (kW).
   - Solar Self-Sufficiency Index (% of neighborhood demand satisfied by connected solar).
   - Household Isolation Rate (% of consumer households with zero access to solar energy).
3. Strongly & Weakly Connected Components:
   - Strongly Connected Components (SCCs): mutual energy trading clusters where
     every household can send power to every other household in the group.
   - Weakly Connected Components (WCCs): isolated sub-microgrids ignoring line direction.
4. Clean Python dictionaries and Pandas DataFrames ready for UI rendering.
"""

from typing import Dict, List, Tuple, Any, Optional, Set
import numpy as np
import pandas as pd
import networkx as nx

from closure_engine import compute_transitive_closure
from grid_presets import graph_to_adjacency_matrix


def analyze_solar_coverage(
    G: nx.DiGraph,
    reachability_matrix: Optional[np.ndarray] = None,
    node_labels: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Performs comprehensive solar reachability and consumer coverage analysis.

    Parameters
    ----------
    G : nx.DiGraph
        Directed microgrid graph with household node attributes.
    reachability_matrix : np.ndarray, optional
        Precomputed transitive closure boolean matrix. If None, computed via Warshall.
    node_labels : list of str, optional
        Ordered node labels corresponding to the matrix rows/columns.

    Returns
    -------
    dict containing:
        - 'producers_reachability': dict of producer_id -> details
        - 'consumers_coverage': dict of consumer_id -> details
        - 'left_out_households': list of dicts for consumers with zero solar access
        - 'producers_df': pd.DataFrame for UI display
        - 'consumers_df': pd.DataFrame for UI display
        - 'left_out_df': pd.DataFrame for UI display
    """
    if reachability_matrix is None or node_labels is None:
        adj, labels = graph_to_adjacency_matrix(G)
        R, _ = compute_transitive_closure(adj, labels)
    else:
        R = np.array(reachability_matrix, dtype=bool)
        labels = list(node_labels)

    node_to_idx = {node: i for i, node in enumerate(labels)}
    n = len(labels)

    # 1. Classify Producers and Consumers
    producers = []
    consumers = []
    for node in labels:
        data = G.nodes[node]
        surplus = float(data.get("solar_surplus_kw", 0.0))
        demand = float(data.get("demand_kw", 0.0))
        if surplus > 0:
            producers.append(node)
        if demand > 0:
            consumers.append(node)

    producer_set = set(producers)

    # 2. Producer Reachability Analysis: Reach(v)
    producers_reachability: Dict[str, Dict[str, Any]] = {}
    producer_rows = []

    for p in producers:
        p_idx = node_to_idx[p]
        p_data = G.nodes[p]
        p_surplus = float(p_data.get("solar_surplus_kw", 0.0))

        # Reach(p): all nodes j where R[p_idx, j] is True and j != p_idx
        reachable_indices = [j for j in range(n) if R[p_idx, j] and j != p_idx]
        reachable_homes = [labels[j] for j in reachable_indices]
        reachable_consumers = [h for h in reachable_homes if h in consumers]

        # Calculate total downstream demand that this producer can reach
        reachable_demand = sum(float(G.nodes[h].get("demand_kw", 0.0)) for h in reachable_homes)

        # Direct vs Indirect Reach
        direct_targets = list(G.successors(p))
        indirect_targets = [h for h in reachable_homes if h not in direct_targets]

        producers_reachability[p] = {
            "home_id": p,
            "owner_name": p_data.get("owner_name", p),
            "solar_surplus_kw": p_surplus,
            "reach_set": reachable_homes,
            "reachable_consumers": reachable_consumers,
            "reachable_count": len(reachable_homes),
            "reachable_demand_kw": round(reachable_demand, 2),
            "direct_targets": direct_targets,
            "indirect_targets": indirect_targets,
            "coverage_efficiency": (
                round(min(1.0, reachable_demand / p_surplus) * 100.0, 1) if p_surplus > 0 else 0.0
            )
        }

        producer_rows.append({
            "Producer ID": p,
            "Household / Facility": p_data.get("owner_name", p),
            "Surplus Solar (kW)": p_surplus,
            "Direct Feeder Lines": len(direct_targets),
            "Total Reachable Homes |Reach(v)|": len(reachable_homes),
            "Reachable Consumers": len(reachable_consumers),
            "Downstream Demand (kW)": round(reachable_demand, 2),
            "Reachable Homes List": ", ".join(reachable_homes) if reachable_homes else "(None)"
        })

    # 3. Consumer Solar Access & Total Reachable Solar Power
    consumers_coverage: Dict[str, Dict[str, Any]] = {}
    consumer_rows = []
    left_out_households: List[Dict[str, Any]] = []
    left_out_rows = []

    for c in consumers:
        c_idx = node_to_idx[c]
        c_data = G.nodes[c]
        c_demand = float(c_data.get("demand_kw", 0.0))
        c_surplus = float(c_data.get("solar_surplus_kw", 0.0))

        # Reach^-1(c) \cap Producers: All producers u that can reach c (R[u_idx, c_idx] is True)
        # Note: If c is itself a producer, its own surplus is self-consumed
        incoming_producers = []
        total_reachable_solar = 0.0

        for p in producers:
            p_idx = node_to_idx[p]
            # Can producer p reach consumer c?
            if R[p_idx, c_idx] and p != c:
                incoming_producers.append(p)
                total_reachable_solar += float(G.nodes[p].get("solar_surplus_kw", 0.0))

        # Self-generation bonus if consumer also has some solar
        if c_surplus > 0:
            total_reachable_solar += c_surplus

        has_solar_access = len(incoming_producers) > 0 or c_surplus > 0
        coverage_ratio = (
            min(1.0, total_reachable_solar / c_demand) if c_demand > 0 else 1.0
        )

        consumers_coverage[c] = {
            "home_id": c,
            "owner_name": c_data.get("owner_name", c),
            "demand_kw": c_demand,
            "local_surplus_kw": c_surplus,
            "incoming_producers": incoming_producers,
            "incoming_producers_count": len(incoming_producers),
            "total_reachable_solar_kw": round(total_reachable_solar, 2),
            "has_solar_access": has_solar_access,
            "coverage_pct": round(coverage_ratio * 100.0, 1),
            "is_left_out": not has_solar_access
        }

        consumer_rows.append({
            "Consumer ID": c,
            "Household / Facility": c_data.get("owner_name", c),
            "Demand (kW)": c_demand,
            "Incoming Solar Sources": len(incoming_producers),
            "Total Available Solar (kW)": round(total_reachable_solar, 2),
            "Coverage %": f"{round(coverage_ratio * 100.0, 1)}%",
            "Access Status": "🟢 Connected" if has_solar_access else "🔴 Left-Out (Isolated)",
            "Supplying Producers": ", ".join(incoming_producers) if incoming_producers else "(None)"
        })

        # Identify Left-Out Households
        if not has_solar_access:
            # Calculate distance to nearest solar producer
            nearest_p = None
            min_hops = float("inf")
            min_dist = float("inf")
            G_undir = G.to_undirected()
            c_pos = c_data.get("pos", (0.0, 0.0))

            for p in producers:
                # 1. Physical wiring hops (undirected infrastructure)
                if nx.has_path(G_undir, p, c):
                    hops = nx.shortest_path_length(G_undir, p, c)
                    if hops < min_hops:
                        min_hops = hops
                        nearest_p = p

                # 2. Euclidean spatial distance
                p_pos = G.nodes[p].get("pos", (0.0, 0.0))
                dist = float(np.hypot(p_pos[0] - c_pos[0], p_pos[1] - c_pos[1]))
                if dist < min_dist:
                    min_dist = dist
                    if nearest_p is None:
                        nearest_p = p

            hops_str = f"{min_hops} hop(s)" if min_hops != float("inf") else "∞ (No Line)"
            dist_str = f"{round(min_dist, 2)} units" if min_dist != float("inf") else "N/A"
            nearest_name = G.nodes[nearest_p].get("owner_name", nearest_p) if nearest_p else "None"

            left_out_info = {
                "home_id": c,
                "owner_name": c_data.get("owner_name", c),
                "demand_kw": c_demand,
                "power_deficit_kw": c_demand,
                "battery_storage_kwh": float(c_data.get("battery_storage_kwh", 0.0)),
                "pos": c_pos,
                "nearest_producer_id": nearest_p,
                "nearest_producer_name": nearest_name,
                "distance_hops": hops_str,
                "euclidean_distance": round(min_dist, 2) if min_dist != float("inf") else None,
                "reason": (
                    "No directed incoming path exists from any surplus solar generator due to "
                    "one-way smart meter limits, topology breaks, or disconnected islanding."
                )
            }
            left_out_households.append(left_out_info)
            left_out_rows.append({
                "Home ID": c,
                "Household Name": c_data.get("owner_name", c),
                "Power Deficit (kW)": c_demand,
                "Nearest Solar Producer": f"{nearest_p} ({nearest_name})",
                "Distance (Wiring Hops)": hops_str,
                "Spatial Distance": dist_str,
                "Battery Reserve (kWh)": float(c_data.get("battery_storage_kwh", 0.0)),
                "Root Cause": left_out_info["reason"]
            })

    # Convert to DataFrames
    producers_df = pd.DataFrame(producer_rows) if producer_rows else pd.DataFrame()
    consumers_df = pd.DataFrame(consumer_rows) if consumer_rows else pd.DataFrame()
    left_out_df = pd.DataFrame(left_out_rows) if left_out_rows else pd.DataFrame()

    return {
        "producers_reachability": producers_reachability,
        "consumers_coverage": consumers_coverage,
        "left_out_households": left_out_households,
        "producers_count": len(producers),
        "consumers_count": len(consumers),
        "left_out_count": len(left_out_households),
        "producers_df": producers_df,
        "consumers_df": consumers_df,
        "left_out_df": left_out_df
    }


def compute_microgrid_metrics(
    G: nx.DiGraph,
    coverage_analysis: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Computes global discrete mathematical and electrical microgrid KPI metrics:
    - Total Solar Generation Available (kW).
    - Total Neighborhood Power Demand (kW).
    - Solar Self-Sufficiency Index (% of total neighborhood demand met by connected solar surplus).
    - Household Isolation Rate (% of consumer households with zero access to solar energy).
    - Topological Bottleneck Penalty (% loss of potential solar trading due to digraph constraints).
    """
    if coverage_analysis is None:
        coverage_analysis = analyze_solar_coverage(G)

    # 1. Total Solar and Demand
    total_solar_kw = round(sum(
        float(data.get("solar_surplus_kw", 0.0)) for _, data in G.nodes(data=True)
    ), 2)
    total_demand_kw = round(sum(
        float(data.get("demand_kw", 0.0)) for _, data in G.nodes(data=True)
    ), 2)
    net_grid_balance_kw = round(total_solar_kw - total_demand_kw, 2)

    consumers_coverage = coverage_analysis["consumers_coverage"]
    total_consumers = len(consumers_coverage)
    left_out_count = len(coverage_analysis["left_out_households"])

    # 2. Household Isolation Rate (%)
    # Percentage of households with demand > 0 that have 0 incoming solar reachability
    if total_consumers > 0:
        household_isolation_rate_pct = round((left_out_count / total_consumers) * 100.0, 2)
    else:
        household_isolation_rate_pct = 0.0

    # 3. Solar Self-Sufficiency Index (%)
    # Calculates how much consumer demand is theoretically reachable and serviceable
    # by connected upstream solar generators taking digraph topology into account.
    connected_demand_serviced_kw = 0.0
    for c_id, c_info in consumers_coverage.items():
        c_demand = c_info["demand_kw"]
        available_solar = c_info["total_reachable_solar_kw"]
        # Demand that can be satisfied by connected power lines
        serviced = min(c_demand, available_solar)
        connected_demand_serviced_kw += serviced

    connected_demand_serviced_kw = round(connected_demand_serviced_kw, 2)

    if total_demand_kw > 0:
        # Self-Sufficiency constrained by directed graph topology
        solar_self_sufficiency_index_pct = round(
            (connected_demand_serviced_kw / total_demand_kw) * 100.0, 2
        )
        # Unconstrained theoretical maximum (copper-plate grid assumption)
        unconstrained_self_sufficiency_pct = round(
            min(100.0, (total_solar_kw / total_demand_kw) * 100.0), 2
        )
    else:
        solar_self_sufficiency_index_pct = 100.0
        unconstrained_self_sufficiency_pct = 100.0

    # Topological Bottleneck: Gap between unconstrained potential and actual reachable coverage
    topological_penalty_pct = round(
        max(0.0, unconstrained_self_sufficiency_pct - solar_self_sufficiency_index_pct), 2
    )

    return {
        "total_solar_generation_kw": total_solar_kw,
        "total_neighborhood_demand_kw": total_demand_kw,
        "net_grid_balance_kw": net_grid_balance_kw,
        "connected_demand_serviced_kw": connected_demand_serviced_kw,
        "solar_self_sufficiency_index_pct": solar_self_sufficiency_index_pct,
        "unconstrained_self_sufficiency_pct": unconstrained_self_sufficiency_pct,
        "topological_penalty_pct": topological_penalty_pct,
        "total_consumers_count": total_consumers,
        "isolated_consumers_count": left_out_count,
        "connected_consumers_count": total_consumers - left_out_count,
        "household_isolation_rate_pct": household_isolation_rate_pct,
        "is_microgrid_islanded": left_out_count > 0
    }


def analyze_connectivity_components(G: nx.DiGraph) -> Dict[str, Any]:
    """
    Computes Strongly Connected Components (SCCs) and Weakly Connected Components (WCCs).

    Strongly Connected Components (SCCs):
    - Subgraphs where every household can send power to every other household in the group.
    - Represents "Mutual Trading Energy Rings" where power can circulate in closed loops.
    - Mathematically corresponds to equivalence classes of the mutual reachability relation:
      u ~ v <=> R^+[u, v] AND R^+[v, u].

    Weakly Connected Components (WCCs):
    - Sub-microgrids connected when edge directions are disregarded.
    - Indicates completely cut-off islands or isolated physical wiring networks.

    Returns
    -------
    dict containing:
        - 'scc_list': list of SCC component dictionaries
        - 'wcc_list': list of WCC component dictionaries
        - 'scc_count': int
        - 'wcc_count': int
        - 'scc_df': pd.DataFrame
        - 'wcc_df': pd.DataFrame
    """
    # 1. Strongly Connected Components
    raw_sccs = list(nx.strongly_connected_components(G))
    # Sort SCCs by size descending
    raw_sccs.sort(key=len, reverse=True)

    scc_list = []
    scc_rows = []

    for i, scc_set in enumerate(raw_sccs, start=1):
        members = sorted(list(scc_set))
        size = len(members)
        is_trivial = (size == 1)

        # Aggregate metrics within this SCC
        scc_solar = round(sum(float(G.nodes[n].get("solar_surplus_kw", 0.0)) for n in members), 2)
        scc_demand = round(sum(float(G.nodes[n].get("demand_kw", 0.0)) for n in members), 2)
        scc_battery = round(sum(float(G.nodes[n].get("battery_storage_kwh", 0.0)) for n in members), 2)
        scc_balance = round(scc_solar - scc_demand, 2)

        scc_info = {
            "component_id": f"SCC_{i:02d}",
            "members": members,
            "size": size,
            "is_mutual_trading_ring": not is_trivial,
            "total_solar_kw": scc_solar,
            "total_demand_kw": scc_demand,
            "net_balance_kw": scc_balance,
            "battery_storage_kwh": scc_battery,
        }
        scc_list.append(scc_info)

        scc_rows.append({
            "Cluster ID": f"SCC_{i:02d}",
            "Trading Type": "🔄 Mutual Trading Ring" if not is_trivial else "▪ Singleton Node",
            "Homes Count": size,
            "Total Solar (kW)": scc_solar,
            "Total Demand (kW)": scc_demand,
            "Net Balance (kW)": scc_balance,
            "Battery Reserve (kWh)": scc_battery,
            "Member Households": ", ".join(members)
        })

    # 2. Weakly Connected Components
    raw_wccs = list(nx.weakly_connected_components(G))
    raw_wccs.sort(key=len, reverse=True)

    wcc_list = []
    wcc_rows = []

    for i, wcc_set in enumerate(raw_wccs, start=1):
        members = sorted(list(wcc_set))
        size = len(members)
        wcc_solar = round(sum(float(G.nodes[n].get("solar_surplus_kw", 0.0)) for n in members), 2)
        wcc_demand = round(sum(float(G.nodes[n].get("demand_kw", 0.0)) for n in members), 2)
        wcc_balance = round(wcc_solar - wcc_demand, 2)
        is_self_sufficient = wcc_solar >= wcc_demand

        wcc_info = {
            "component_id": f"Island_{i:02d}",
            "members": members,
            "size": size,
            "total_solar_kw": wcc_solar,
            "total_demand_kw": wcc_demand,
            "net_balance_kw": wcc_balance,
            "is_self_sufficient": is_self_sufficient
        }
        wcc_list.append(wcc_info)

        wcc_rows.append({
            "Island ID": f"Sub-Grid Island {i:02d}",
            "Homes Count": size,
            "Total Solar (kW)": wcc_solar,
            "Total Demand (kW)": wcc_demand,
            "Net Balance (kW)": wcc_balance,
            "Island Sufficiency": "🟢 Self-Sufficient" if is_self_sufficient else "🔴 Power Deficit",
            "Island Households": ", ".join(members)
        })

    scc_df = pd.DataFrame(scc_rows) if scc_rows else pd.DataFrame()
    wcc_df = pd.DataFrame(wcc_rows) if wcc_rows else pd.DataFrame()

    return {
        "scc_list": scc_list,
        "wcc_list": wcc_list,
        "scc_count": len(scc_list),
        "wcc_count": len(wcc_list),
        "mutual_trading_rings_count": sum(1 for s in scc_list if s["is_mutual_trading_ring"]),
        "is_strongly_connected": len(scc_list) == 1,
        "is_weakly_connected": len(wcc_list) == 1,
        "scc_df": scc_df,
        "wcc_df": wcc_df
    }


def run_full_reachability_audit(G: nx.DiGraph) -> Dict[str, Any]:
    """
    Convenience orchestrator executing all Module 2 analytical functions:
    - Coverage & reachability analysis
    - Global microgrid KPIs
    - SCC & WCC connectivity structures

    Returns a comprehensive dictionary with Python primitives and DataFrames.
    """
    adj, labels = graph_to_adjacency_matrix(G)
    reach_matrix, _ = compute_transitive_closure(adj, labels)

    coverage = analyze_solar_coverage(G, reach_matrix, labels)
    metrics = compute_microgrid_metrics(G, coverage)
    connectivity = analyze_connectivity_components(G)

    return {
        "coverage": coverage,
        "metrics": metrics,
        "connectivity": connectivity,
        "node_labels": labels,
        "reachability_matrix": reach_matrix
    }
