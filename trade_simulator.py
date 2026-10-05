"""
trade_simulator.py
==================
Energy Trade Simulation & Multi-Hop Transmission Loss Engine for Solar Share Grid.

Discrete Mathematical Model:
1. Multi-Hop Transmission Loss Model:
   When power travels across a directed path p = (v_0, v_1, ..., v_k) of length k:
       Delivered Power = Sent Power * prod_{i=1}^k (1 - loss_rate_i)
   where loss_rate_i is the fractional dissipation on edge (v_{i-1}, v_i).
   Paths with k > 3 hops are flagged as inefficient multi-hop transfers.

2. Greedy Shortest-Path Trade Settlement Algorithm:
   Matches active solar surplus nodes to reachable consumer nodes ordered by
   shortest topological distance (hop count k ascending) to minimize ohmic losses.

3. Transaction Ledger & Economic Savings:
   Tracks Sent (kW), Delivered (kW), Loss (kW), Transmission Efficiency (%),
   and simulated financial cost savings ($ / ₹) relative to baseline utility tariffs.
"""

from typing import Dict, List, Tuple, Any, Optional
import io
import networkx as nx
import numpy as np
import pandas as pd

from closure_engine import compute_transitive_closure
from grid_presets import graph_to_adjacency_matrix


# Default tariff rates (standardized for Navi Mumbai / MSEDCL INR and USD)
DEFAULT_UTILITY_TARIFF_INR = 10.00  # ₹ / kWh baseline MSEDCL grid rate in Navi Mumbai
DEFAULT_P2P_TARIFF_INR = 5.00       # ₹ / kWh peer-to-peer microgrid rate
DEFAULT_UTILITY_TARIFF_USD = 0.12   # $ / kWh baseline grid rate (~ ₹10.00/kWh)
DEFAULT_P2P_TARIFF_USD = 0.06       # $ / kWh peer-to-peer microgrid rate (~ ₹5.00/kWh)
USD_TO_INR_RATE = 83.50             # Currency multiplier for conversion


def calculate_path_loss(
    G: nx.DiGraph,
    path: List[str]
) -> Dict[str, Any]:
    """
    Computes multi-hop transmission dissipation across a directed path.

    Parameters
    ----------
    G : nx.DiGraph
        Directed microgrid graph with edge attribute 'line_loss_pct'.
    path : list of str
        Ordered sequence of vertices [v_0, v_1, ..., v_k].

    Returns
    -------
    dict containing:
        - 'hops': int (k = len(path) - 1)
        - 'efficiency_multiplier': float (prod_{i=1}^k (1 - loss_rate_i))
        - 'total_loss_pct': float (cumulative percentage loss)
        - 'is_inefficient': bool (True if hops > 3)
        - 'edge_losses': list of float (loss per individual hop)
    """
    if len(path) <= 1:
        return {
            "hops": 0,
            "efficiency_multiplier": 1.0,
            "total_loss_pct": 0.0,
            "is_inefficient": False,
            "edge_losses": []
        }

    k = len(path) - 1
    multiplier = 1.0
    edge_losses = []

    for i in range(k):
        u, v = path[i], path[i + 1]
        edge_data = G.get_edge_data(u, v, default={})
        loss_pct = float(edge_data.get("line_loss_pct", 2.0))
        loss_rate = loss_pct / 100.0
        # Bound loss rate strictly in [0, 1)
        loss_rate = min(max(loss_rate, 0.0), 0.99)
        multiplier *= (1.0 - loss_rate)
        edge_losses.append(loss_pct)

    total_loss_pct = round((1.0 - multiplier) * 100.0, 3)

    return {
        "hops": k,
        "efficiency_multiplier": multiplier,
        "total_loss_pct": total_loss_pct,
        "is_inefficient": k > 3,
        "edge_losses": edge_losses
    }


def simulate_p2p_trade_cycle(
    G: nx.DiGraph,
    utility_rate_inr: float = DEFAULT_UTILITY_TARIFF_INR,
    p2p_rate_inr: float = DEFAULT_P2P_TARIFF_INR,
    utility_rate_usd: Optional[float] = None,
    p2p_rate_usd: Optional[float] = None
) -> Dict[str, Any]:
    """
    Simulates a peer-to-peer rooftop solar trade cycle across the microgrid.

    Greedy Shortest-Path Allocation:
    1. Identifies all producers with surplus S(u) > 0 and consumers with demand D(v) > 0.
    2. Computes the shortest directed path p = (u, ..., v) for each reachable pair.
    3. Orders candidate trades by shortest topological distance (hop count k ascending).
    4. Greedily allocates available solar surplus to meet consumer demand, factoring
       in compound line losses along the transmission path.
    5. Records each transaction in an audited P2P transaction ledger.

    Returns
    -------
    dict containing:
        - 'ledger_df': pd.DataFrame with transaction records
        - 'transactions': list of transaction dicts
        - 'total_sent_kw': float
        - 'total_delivered_kw': float
        - 'total_loss_kw': float
        - 'grid_efficiency_pct': float
        - 'total_savings_usd': float
        - 'total_savings_inr': float
        - 'inefficient_transfers_count': int (transfers with > 3 hops)
        - 'remaining_surplus': dict of {home_id: remaining_kw}
        - 'remaining_demand': dict of {home_id: unmet_kw}
    """
    # Initialize working balances
    remaining_surplus = {
        node: float(data.get("solar_surplus_kw", 0.0))
        for node, data in G.nodes(data=True)
    }
    remaining_demand = {
        node: float(data.get("demand_kw", 0.0))
        for node, data in G.nodes(data=True)
    }

    producers = [n for n, s in remaining_surplus.items() if s > 0.01]
    consumers = [n for n, d in remaining_demand.items() if d > 0.01]

    # Precompute Warshall reachability matrix to instantly filter reachable pairs
    adj_matrix, node_labels = graph_to_adjacency_matrix(G)
    node_to_idx = {n: i for i, n in enumerate(node_labels)}
    R, _ = compute_transitive_closure(adj_matrix, node_labels)

    candidate_pairs = []
    for u in producers:
        u_idx = node_to_idx[u]
        for v in consumers:
            if u == v:
                continue
            v_idx = node_to_idx[v]
            # Verify directed path exists via Warshall Transitive Closure
            if R[u_idx, v_idx]:
                try:
                    path = nx.shortest_path(G, source=u, target=v)
                    loss_info = calculate_path_loss(G, path)
                    candidate_pairs.append({
                        "source": u,
                        "target": v,
                        "path": path,
                        "hops": loss_info["hops"],
                        "efficiency_multiplier": loss_info["efficiency_multiplier"],
                        "total_loss_pct": loss_info["total_loss_pct"],
                        "is_inefficient": loss_info["is_inefficient"]
                    })
                except nx.NetworkXNoPath:
                    continue

    # Order candidate pairs by:
    # 1. Shortest topological distance (hop count ascending)
    # 2. Highest transmission efficiency (multiplier descending)
    candidate_pairs.sort(
        key=lambda item: (item["hops"], -item["efficiency_multiplier"])
    )

    transactions = []
    txn_id_counter = 1

    # Handle backward-compatibility for USD parameters if passed
    if utility_rate_usd is not None and utility_rate_inr == DEFAULT_UTILITY_TARIFF_INR:
        utility_rate_inr = utility_rate_usd * USD_TO_INR_RATE
    if p2p_rate_usd is not None and p2p_rate_inr == DEFAULT_P2P_TARIFF_INR:
        p2p_rate_inr = p2p_rate_usd * USD_TO_INR_RATE

    unit_savings_inr = max(utility_rate_inr - p2p_rate_inr, 0.0)
    unit_savings_usd = unit_savings_inr / USD_TO_INR_RATE

    for cand in candidate_pairs:
        u = cand["source"]
        v = cand["target"]
        avail_surplus = remaining_surplus[u]
        needed_demand = remaining_demand[v]

        if avail_surplus <= 0.001 or needed_demand <= 0.001:
            continue

        eta = cand["efficiency_multiplier"]
        if eta <= 0.0:
            continue

        # Power required to be dispatched by u to satisfy needed_demand at v
        req_sent = needed_demand / eta

        if avail_surplus >= req_sent:
            sent_kw = req_sent
            delivered_kw = needed_demand
        else:
            sent_kw = avail_surplus
            delivered_kw = sent_kw * eta

        loss_kw = sent_kw - delivered_kw

        # Update remaining states
        remaining_surplus[u] = max(0.0, remaining_surplus[u] - sent_kw)
        remaining_demand[v] = max(0.0, remaining_demand[v] - delivered_kw)

        # Economic savings for delivered clean energy in Rupees (₹)
        savings_inr = delivered_kw * unit_savings_inr
        savings_usd = delivered_kw * unit_savings_usd

        path_str = " ➔ ".join(cand["path"])
        status = "⚠️ Inefficient (>3 hops)" if cand["is_inefficient"] else "✅ Optimal"

        txn_record = {
            "Txn ID": f"TXN_{txn_id_counter:03d}",
            "Exporter ID": u,
            "Exporter Name": G.nodes[u].get("owner_name", u),
            "Importer ID": v,
            "Importer Name": G.nodes[v].get("owner_name", v),
            "Routing Path": path_str,
            "Hops": cand["hops"],
            "Sent (kW)": round(sent_kw, 2),
            "Delivered (kW)": round(delivered_kw, 2),
            "Loss (kW)": round(loss_kw, 2),
            "Efficiency (%)": round(eta * 100.0, 1),
            "Cost Savings (₹)": round(savings_inr, 2),
            "Cost Savings ($)": round(savings_usd, 2),
            "Status": status,
            "is_inefficient": cand["is_inefficient"]
        }
        transactions.append(txn_record)
        txn_id_counter += 1

    # Ledger DataFrame
    if transactions:
        ledger_df = pd.DataFrame(transactions)
    else:
        ledger_df = pd.DataFrame(columns=[
            "Txn ID", "Exporter ID", "Exporter Name", "Importer ID", "Importer Name",
            "Routing Path", "Hops", "Sent (kW)", "Delivered (kW)", "Loss (kW)",
            "Efficiency (%)", "Cost Savings (₹)", "Cost Savings ($)", "Status"
        ])

    total_sent_kw = round(sum(t["Sent (kW)"] for t in transactions), 2)
    total_delivered_kw = round(sum(t["Delivered (kW)"] for t in transactions), 2)
    total_loss_kw = round(sum(t["Loss (kW)"] for t in transactions), 2)
    grid_efficiency = round((total_delivered_kw / total_sent_kw) * 100.0, 1) if total_sent_kw > 0 else 100.0
    total_savings_usd = round(sum(t["Cost Savings ($)"] for t in transactions), 2)
    total_savings_inr = round(sum(t["Cost Savings (₹)"] for t in transactions), 2)
    inefficient_count = sum(1 for t in transactions if t.get("is_inefficient", False))

    return {
        "ledger_df": ledger_df,
        "transactions": transactions,
        "total_sent_kw": total_sent_kw,
        "total_delivered_kw": total_delivered_kw,
        "total_loss_kw": total_loss_kw,
        "grid_efficiency_pct": grid_efficiency,
        "total_savings_usd": total_savings_usd,
        "total_savings_inr": total_savings_inr,
        "inefficient_transfers_count": inefficient_count,
        "remaining_surplus": {k: round(v, 2) for k, v in remaining_surplus.items()},
        "remaining_demand": {k: round(v, 2) for k, v in remaining_demand.items()}
    }


def generate_executive_report_bundle(
    G: nx.DiGraph,
    coverage_data: Dict[str, Any],
    microgrid_metrics: Dict[str, Any],
    transitive_closure_matrix: np.ndarray,
    node_labels: List[str],
    optimization_results: Optional[Dict[str, Any]] = None,
    trade_results: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generates a structured, consolidated Executive Microgrid Summary Report (CSV format).

    Includes:
    1. Executive Summary & Microgrid Reachability Metrics.
    2. Left-Out Households Audit.
    3. Warshall Transitive Closure Reachability Matrix (R+).
    4. Recommended Infrastructure Expansion Plan (from link_optimizer).
    5. P2P Trade Settlement Transaction Ledger & Loss Analytics.
    """
    buffer = io.StringIO()

    # Section 1: Executive Microgrid Summary & Key Performance Indicators
    buffer.write("=== SECTION 1: EXECUTIVE MICROGRID SUMMARY & METRICS ===\n")
    buffer.write("Metric,Value,Unit,Description\n")
    buffer.write(f"Total Households (Vertices),{len(node_labels)},count,Total microgrid network nodes\n")
    buffer.write(f"Total Physical Lines (Edges),{G.number_of_edges()},count,Direct physical transmission lines\n")
    buffer.write(f"Total Solar Generation,{microgrid_metrics.get('total_solar_generation_kw', 0.0)},kW,Cumulative rooftop solar surplus\n")
    buffer.write(f"Total Neighborhood Demand,{microgrid_metrics.get('total_neighborhood_demand_kw', 0.0)},kW,Cumulative household power demand\n")
    buffer.write(f"Solar Self-Sufficiency Index,{microgrid_metrics.get('solar_self_sufficiency_index_pct', 0.0)},%,Percentage of neighborhood demand met by solar\n")
    buffer.write(f"Household Isolation Rate,{microgrid_metrics.get('household_isolation_rate_pct', 0.0)},%,Percentage of consumer homes with zero solar access\n")
    buffer.write(f"Left-Out Households Count,{coverage_data.get('left_out_count', 0)},count,Households completely severed from solar generation\n")
    buffer.write(f"Topological Bottleneck Penalty,{microgrid_metrics.get('topological_bottleneck_penalty_kw', 0.0)},kW,Unused solar generation due to digraph routing gaps\n\n")

    # Section 2: Left-Out Households Audit
    buffer.write("=== SECTION 2: LEFT-OUT HOUSEHOLDS AUDIT ===\n")
    left_out_list = coverage_data.get("left_out_households", [])
    if left_out_list:
        buffer.write("Household ID,Resident / Facility,Unmet Demand (kW),Nearest Solar Producer,Physical Distance (Units),Hops\n")
        for h in left_out_list:
            buffer.write(f"{h.get('home_id')},{h.get('owner_name')},{h.get('demand_kw')},{h.get('nearest_producer_id')},{h.get('distance_euclidean', 'N/A')},{h.get('distance_hops', 'N/A')}\n")
    else:
        buffer.write("Status,Message\n")
        buffer.write("100% Inclusivity,Zero households are left out. All consumer nodes have directed paths to solar producers.\n")
    buffer.write("\n")

    # Section 3: Warshall Transitive Closure Reachability Matrix (R+)
    buffer.write("=== SECTION 3: WARSHALL TRANSITIVE CLOSURE MATRIX (R+) ===\n")
    buffer.write("Source \\ Target," + ",".join(node_labels) + "\n")
    for i, src in enumerate(node_labels):
        row_vals = [str(int(transitive_closure_matrix[i, j])) for j in range(len(node_labels))]
        buffer.write(f"{src}," + ",".join(row_vals) + "\n")
    buffer.write("\n")

    # Section 4: Recommended Infrastructure Expansion Plan
    buffer.write("=== SECTION 4: RECOMMENDED INFRASTRUCTURE EXPANSION PLAN ===\n")
    if optimization_results and optimization_results.get("top_candidates"):
        buffer.write("Rank,Proposed Edge,Source,Target,Delta Powered Homes,Delta Unmet Demand (kW),Distance (Units),Efficiency Score,Newly Powered Homes\n")
        for rank, cand in enumerate(optimization_results["top_candidates"], start=1):
            new_homes = "; ".join(cand.get("newly_connected_homes", [])) if cand.get("newly_connected_homes") else "Redundancy"
            buffer.write(
                f"#{rank},{cand.get('source')} -> {cand.get('target')},"
                f"{cand.get('source_name')},{cand.get('target_name')},"
                f"{cand.get('delta_powered_homes')},{cand.get('delta_demand_kw')},"
                f"{cand.get('euclidean_distance')},{cand.get('score')},{new_homes}\n"
            )
    else:
        buffer.write("Status,Message\n")
        buffer.write("Network Complete,Grid is fully transitively connected or no missing candidate links.\n")
    buffer.write("\n")

    # Section 5: P2P Trade Settlement Transaction Ledger
    buffer.write("=== SECTION 5: P2P TRADE SETTLEMENT TRANSACTION LEDGER ===\n")
    if trade_results and trade_results.get("transactions"):
        buffer.write(f"Summary: Total Traded: {trade_results.get('total_sent_kw', 0)} kW | Total Delivered: {trade_results.get('total_delivered_kw', 0)} kW | Total Losses: {trade_results.get('total_loss_kw', 0)} kW | Efficiency: {trade_results.get('grid_efficiency_pct', 0)}% | Total Savings: INR {trade_results.get('total_savings_inr', 0)} (USD {trade_results.get('total_savings_usd', 0)})\n")
        buffer.write("Txn ID,Exporter ID,Exporter Name,Importer ID,Importer Name,Routing Path,Hops,Sent (kW),Delivered (kW),Loss (kW),Efficiency (%),Cost Savings (INR),Cost Savings (USD),Status\n")
        for txn in trade_results["transactions"]:
            buffer.write(
                f"{txn['Txn ID']},{txn['Exporter ID']},{txn['Exporter Name']},"
                f"{txn['Importer ID']},{txn['Importer Name']},{txn['Routing Path']},"
                f"{txn['Hops']},{txn['Sent (kW)']},{txn['Delivered (kW)']},"
                f"{txn['Loss (kW)']},{txn['Efficiency (%)']},{txn['Cost Savings (₹)']},"
                f"{txn['Cost Savings ($)']},{txn['Status']}\n"
            )
    else:
        buffer.write("Status,Message\n")
        buffer.write("Not Simulated,Run 'Simulate Trade Cycle' in the web app to generate live trade settlements.\n")

    return buffer.getvalue()
