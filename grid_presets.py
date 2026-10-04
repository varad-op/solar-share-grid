"""
grid_presets.py
===============
Neighborhood Microgrid Presets and Data Schema for Solar Share Grid.

Models peer-to-peer (P2P) rooftop solar trading across neighborhood microgrids
using Directed Graphs D = (V, E) and binary relations.

Node Attributes:
- home_id (str): Unique identifier (e.g., 'HOME_01')
- owner_name (str): Household name / resident name
- solar_surplus_kw (float): Surplus solar output (kW, >= 0; 0 if net consumer)
- demand_kw (float): Power demand required by the household (kW, >= 0)
- battery_storage_kwh (float): Local battery capacity (kWh)
- pos (tuple): Spatial (x, y) coordinates for 2D topological mapping

Edge Attributes:
- source (str): Source node ID
- target (str): Target node ID
- transfer_capacity_kw (float): Maximum line throughput (kW)
- is_bidirectional (bool): False if smart meter/inverter limits flow to one direction
- line_loss_pct (float): Resistance loss percentage per hop (e.g., 2.0%)
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Any, Optional, Union
import json
import io
import pandas as pd
import numpy as np
import networkx as nx


@dataclass
class HouseholdNode:
    home_id: str
    owner_name: str
    solar_surplus_kw: float
    demand_kw: float
    battery_storage_kwh: float
    pos: Tuple[float, float]

    @property
    def net_balance_kw(self) -> float:
        """Net energy balance (surplus - demand). Positive means net producer."""
        return round(self.solar_surplus_kw - self.demand_kw, 2)

    @property
    def is_producer(self) -> bool:
        """True if household generates more solar than its current demand."""
        return self.solar_surplus_kw > self.demand_kw

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["net_balance_kw"] = self.net_balance_kw
        d["is_producer"] = self.is_producer
        return d


@dataclass
class PowerLineEdge:
    source: str
    target: str
    transfer_capacity_kw: float
    is_bidirectional: bool
    line_loss_pct: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_networkx_graph(nodes: List[HouseholdNode], edges: List[PowerLineEdge]) -> nx.DiGraph:
    """
    Constructs a NetworkX DiGraph D = (V, E) adhering to the microgrid schema.
    If an edge is marked bidirectional, both (u, v) and (v, u) directed edges
    are added to the digraph.
    """
    G = nx.DiGraph()

    # Add nodes with all rich attributes
    for node in nodes:
        G.add_node(
            node.home_id,
            home_id=node.home_id,
            owner_name=node.owner_name,
            solar_surplus_kw=float(node.solar_surplus_kw),
            demand_kw=float(node.demand_kw),
            battery_storage_kwh=float(node.battery_storage_kwh),
            pos=node.pos,
            net_balance_kw=node.net_balance_kw,
            is_producer=node.is_producer
        )

    # Add edges with attributes
    for edge in edges:
        G.add_edge(
            edge.source,
            edge.target,
            transfer_capacity_kw=float(edge.transfer_capacity_kw),
            is_bidirectional=bool(edge.is_bidirectional),
            line_loss_pct=float(edge.line_loss_pct)
        )
        if edge.is_bidirectional:
            G.add_edge(
                edge.target,
                edge.source,
                transfer_capacity_kw=float(edge.transfer_capacity_kw),
                is_bidirectional=True,
                line_loss_pct=float(edge.line_loss_pct)
            )

    return G


def graph_to_adjacency_matrix(G: nx.DiGraph) -> Tuple[np.ndarray, List[str]]:
    """
    Extracts the binary adjacency matrix and ordered list of node labels from a DiGraph.
    """
    node_labels = list(G.nodes())
    adj = nx.to_numpy_array(G, nodelist=node_labels, dtype=bool)
    return adj, node_labels


# =====================================================================
# Preset 1: "Suburban Cul-de-Sac" (Nerul Palm Beach Enclave)
# 10 homes: 3 solar producers with high generation & 7 consumers.
# Balanced mixed graph with bidirectional loop feeds and radial feeder lines.
# =====================================================================
def get_suburban_culdesac() -> Tuple[nx.DiGraph, Dict[str, Any]]:
    """
    Preset: Suburban Cul-de-Sac (Nerul Palm Beach Enclave, Navi Mumbai).
    Balanced mixed graph with 3 solar producers (HOME_01, HOME_04, HOME_07)
    and 7 consumers. Arranged in a neighborhood cul-de-sac circle with
    a central distribution tie.
    """
    nodes = [
        # 3 Solar Producers (large PV arrays & battery storage)
        HouseholdNode(
            home_id="HOME_01",
            owner_name="Palm Beach Greens Villa (Nerul Sec 15)",
            solar_surplus_kw=9.5,
            demand_kw=2.1,
            battery_storage_kwh=13.5,
            pos=(1.0, 4.0)
        ),
        HouseholdNode(
            home_id="HOME_04",
            owner_name="DY Patil Vidyanagar Solar Array (Nerul)",
            solar_surplus_kw=8.0,
            demand_kw=1.8,
            battery_storage_kwh=10.0,
            pos=(4.0, 5.0)
        ),
        HouseholdNode(
            home_id="HOME_07",
            owner_name="Nerul Gymkhana Rooftop PV (Sec 28)",
            solar_surplus_kw=11.2,
            demand_kw=3.0,
            battery_storage_kwh=15.0,
            pos=(4.0, 1.0)
        ),
        # 7 Consumers (low or zero solar generation, varied power demands)
        HouseholdNode(
            home_id="HOME_02",
            owner_name="Seawoods Estate Enclave",
            solar_surplus_kw=0.0,
            demand_kw=4.2,
            battery_storage_kwh=3.0,
            pos=(1.5, 2.5)
        ),
        HouseholdNode(
            home_id="HOME_03",
            owner_name="Sector 21 Shanti Niketan CHS",
            solar_surplus_kw=0.5,
            demand_kw=3.8,
            battery_storage_kwh=0.0,
            pos=(2.5, 4.8)
        ),
        HouseholdNode(
            home_id="HOME_05",
            owner_name="Nerul Sector 19A Residency",
            solar_surplus_kw=0.0,
            demand_kw=5.1,
            battery_storage_kwh=5.0,
            pos=(5.0, 3.8)
        ),
        HouseholdNode(
            home_id="HOME_06",
            owner_name="Jewel of Navi Mumbai Promenade Homes",
            solar_surplus_kw=1.0,
            demand_kw=3.5,
            battery_storage_kwh=0.0,
            pos=(5.2, 2.2)
        ),
        HouseholdNode(
            home_id="HOME_08",
            owner_name="Sector 4 Sarsole Lakeview CHS",
            solar_surplus_kw=0.0,
            demand_kw=4.0,
            battery_storage_kwh=2.0,
            pos=(2.8, 0.8)
        ),
        HouseholdNode(
            home_id="HOME_09",
            owner_name="Wonders Park Avenue Apartments",
            solar_surplus_kw=0.0,
            demand_kw=3.2,
            battery_storage_kwh=0.0,
            pos=(1.8, 1.2)
        ),
        HouseholdNode(
            home_id="HOME_10",
            owner_name="Nerul MSEDCL Central Hub & Storage",
            solar_surplus_kw=0.0,
            demand_kw=1.0,
            battery_storage_kwh=20.0,
            pos=(3.0, 3.0)
        ),
    ]

    edges = [
        # Bidirectional backbone around the cul-de-sac ring
        PowerLineEdge("HOME_01", "HOME_03", transfer_capacity_kw=7.0, is_bidirectional=True, line_loss_pct=1.8),
        PowerLineEdge("HOME_03", "HOME_04", transfer_capacity_kw=7.0, is_bidirectional=True, line_loss_pct=1.5),
        PowerLineEdge("HOME_04", "HOME_05", transfer_capacity_kw=6.0, is_bidirectional=True, line_loss_pct=1.9),
        PowerLineEdge("HOME_05", "HOME_06", transfer_capacity_kw=5.0, is_bidirectional=True, line_loss_pct=2.0),
        PowerLineEdge("HOME_06", "HOME_07", transfer_capacity_kw=8.0, is_bidirectional=True, line_loss_pct=1.7),
        PowerLineEdge("HOME_07", "HOME_08", transfer_capacity_kw=6.0, is_bidirectional=True, line_loss_pct=2.1),
        PowerLineEdge("HOME_08", "HOME_09", transfer_capacity_kw=5.0, is_bidirectional=True, line_loss_pct=1.8),
        PowerLineEdge("HOME_09", "HOME_02", transfer_capacity_kw=5.0, is_bidirectional=True, line_loss_pct=2.2),
        PowerLineEdge("HOME_02", "HOME_01", transfer_capacity_kw=6.0, is_bidirectional=True, line_loss_pct=1.6),

        # Central Hub Spokes (HOME_10 acts as neighborhood battery buffer & router)
        PowerLineEdge("HOME_01", "HOME_10", transfer_capacity_kw=8.0, is_bidirectional=True, line_loss_pct=1.2),
        PowerLineEdge("HOME_04", "HOME_10", transfer_capacity_kw=8.0, is_bidirectional=True, line_loss_pct=1.2),
        PowerLineEdge("HOME_07", "HOME_10", transfer_capacity_kw=10.0, is_bidirectional=True, line_loss_pct=1.1),
        PowerLineEdge("HOME_10", "HOME_05", transfer_capacity_kw=6.0, is_bidirectional=False, line_loss_pct=1.3),
        PowerLineEdge("HOME_10", "HOME_08", transfer_capacity_kw=6.0, is_bidirectional=False, line_loss_pct=1.4),
    ]

    G = build_networkx_graph(nodes, edges)
    meta = {
        "name": "Suburban Cul-de-Sac (Nerul Palm Beach)",
        "description": "Balanced Nerul neighborhood microgrid (Palm Beach / Sector 19A-21) with 3 rooftop solar prosumers, 7 consumers, and a central MSEDCL battery hub.",
        "type": "Mixed / Mesh Digraph",
        "nodes_count": len(nodes),
        "producers_count": 3,
        "consumers_count": 7
    }
    return G, meta


# =====================================================================
# Preset 2: "Asymmetric Hillside" (Parsik Hill to CBD Belapur Slopes)
# 9 homes: Heavily directed microgrid with one-way downhill lines due
# to legacy transformer steps and non-export smart meters. Strong DAG.
# =====================================================================
def get_asymmetric_hillside() -> Tuple[nx.DiGraph, Dict[str, Any]]:
    """
    Preset: Asymmetric Hillside (Parsik Hill to Belapur Slopes, Navi Mumbai).
    Steep gradient terrain where solar panels on hilltop homes cascade power
    strictly downhill to mid-hill and valley households.
    Forms a Directed Acyclic Graph (DAG) with asymmetry and transitivity nuances.
    """
    nodes = [
        # Summit / Tier 1 (Apex solar harvest on Parsik Hill Ridge)
        HouseholdNode(
            home_id="HOME_01",
            owner_name="Parsik Hilltop Villa East",
            solar_surplus_kw=14.0,
            demand_kw=1.5,
            battery_storage_kwh=16.0,
            pos=(1.5, 6.0)
        ),
        HouseholdNode(
            home_id="HOME_02",
            owner_name="Parsik Hilltop Villa West",
            solar_surplus_kw=12.5,
            demand_kw=1.8,
            battery_storage_kwh=14.0,
            pos=(4.5, 6.0)
        ),
        # Mid-Slope Upper / Tier 2
        HouseholdNode(
            home_id="HOME_03",
            owner_name="Upper Parsik Terrace Homes A",
            solar_surplus_kw=4.0,
            demand_kw=3.0,
            battery_storage_kwh=5.0,
            pos=(1.0, 4.2)
        ),
        HouseholdNode(
            home_id="HOME_04",
            owner_name="Belapur Hill Slope Retreat",
            solar_surplus_kw=2.0,
            demand_kw=3.5,
            battery_storage_kwh=3.0,
            pos=(3.0, 4.2)
        ),
        HouseholdNode(
            home_id="HOME_05",
            owner_name="Parsik Heights Solar Deck",
            solar_surplus_kw=5.0,
            demand_kw=2.5,
            battery_storage_kwh=6.0,
            pos=(5.0, 4.2)
        ),
        # Mid-Slope Lower / Tier 3
        HouseholdNode(
            home_id="HOME_06",
            owner_name="CBD Belapur Sector 15 Towers",
            solar_surplus_kw=0.0,
            demand_kw=4.5,
            battery_storage_kwh=0.0,
            pos=(2.0, 2.3)
        ),
        HouseholdNode(
            home_id="HOME_07",
            owner_name="Sector 11 Belapur Enclave",
            solar_surplus_kw=0.0,
            demand_kw=5.0,
            battery_storage_kwh=2.0,
            pos=(4.0, 2.3)
        ),
        # Valley Floor / Tier 4 (Pure heavy consumers)
        HouseholdNode(
            home_id="HOME_08",
            owner_name="Thane-Belapur Road Commercial Depot",
            solar_surplus_kw=0.0,
            demand_kw=6.5,
            battery_storage_kwh=0.0,
            pos=(1.5, 0.5)
        ),
        HouseholdNode(
            home_id="HOME_09",
            owner_name="Nerul-Belapur Junction Complex",
            solar_surplus_kw=0.0,
            demand_kw=7.0,
            battery_storage_kwh=0.0,
            pos=(4.5, 0.5)
        ),
    ]

    edges = [
        # Summit to Tier 2 (Strict one-way downhill lines)
        PowerLineEdge("HOME_01", "HOME_03", transfer_capacity_kw=8.0, is_bidirectional=False, line_loss_pct=2.5),
        PowerLineEdge("HOME_01", "HOME_04", transfer_capacity_kw=7.0, is_bidirectional=False, line_loss_pct=2.8),
        PowerLineEdge("HOME_02", "HOME_04", transfer_capacity_kw=7.0, is_bidirectional=False, line_loss_pct=2.8),
        PowerLineEdge("HOME_02", "HOME_05", transfer_capacity_kw=8.0, is_bidirectional=False, line_loss_pct=2.5),

        # Tier 2 to Tier 3 (Downhill distribution)
        PowerLineEdge("HOME_03", "HOME_06", transfer_capacity_kw=5.0, is_bidirectional=False, line_loss_pct=2.2),
        PowerLineEdge("HOME_04", "HOME_06", transfer_capacity_kw=4.5, is_bidirectional=False, line_loss_pct=2.1),
        PowerLineEdge("HOME_04", "HOME_07", transfer_capacity_kw=4.5, is_bidirectional=False, line_loss_pct=2.1),
        PowerLineEdge("HOME_05", "HOME_07", transfer_capacity_kw=5.0, is_bidirectional=False, line_loss_pct=2.2),

        # Tier 3 to Valley Floor
        PowerLineEdge("HOME_06", "HOME_08", transfer_capacity_kw=6.0, is_bidirectional=False, line_loss_pct=3.0),
        PowerLineEdge("HOME_06", "HOME_09", transfer_capacity_kw=4.0, is_bidirectional=False, line_loss_pct=3.2),
        PowerLineEdge("HOME_07", "HOME_09", transfer_capacity_kw=6.0, is_bidirectional=False, line_loss_pct=3.0),

        # Direct express drop bypass (HOME_01 -> HOME_08)
        PowerLineEdge("HOME_01", "HOME_08", transfer_capacity_kw=4.0, is_bidirectional=False, line_loss_pct=4.5),
    ]

    G = build_networkx_graph(nodes, edges)
    meta = {
        "name": "Asymmetric Hillside (Parsik Hill)",
        "description": "Topological downhill microgrid flowing from Parsik Hill summit villas strictly down to Belapur commercial floors via legacy one-way substations. Exhibits strict DAG structure.",
        "type": "Strict Directed Acyclic Graph (DAG)",
        "nodes_count": len(nodes),
        "producers_count": 4,
        "consumers_count": 5
    }
    return G, meta


# =====================================================================
# Preset 3: "Isolated Islands" (Nerul West vs Seawoods East Creek Divide)
# 10 homes: Split microgrid with 2 disconnected sub-graphs.
# Island A (Nerul West Sector, 5 homes) and Island B (Seawoods Sector, 5 homes).
# Demonstrates partial reachability and partitioned equivalence/connectivity.
# =====================================================================
def get_isolated_islands() -> Tuple[nx.DiGraph, Dict[str, Any]]:
    """
    Preset: Isolated Islands (Nerul West vs Seawoods East, Navi Mumbai).
    A microgrid separated into two disconnected components due to an open
    creek tie-line circuit breaker between Nerul West and Seawoods East.
    Households in Seawoods are cut off from solar generators in Nerul West.
    """
    nodes = [
        # Island 1: Nerul West Sector (Homes 01 to 05)
        HouseholdNode(
            home_id="HOME_01",
            owner_name="Nerul West Sector 19A Solar Array",
            solar_surplus_kw=10.0,
            demand_kw=1.5,
            battery_storage_kwh=12.0,
            pos=(1.0, 5.0)
        ),
        HouseholdNode(
            home_id="HOME_02",
            owner_name="Sector 21 Balaji Krupa CHS",
            solar_surplus_kw=0.0,
            demand_kw=3.5,
            battery_storage_kwh=2.0,
            pos=(2.2, 5.8)
        ),
        HouseholdNode(
            home_id="HOME_03",
            owner_name="Nerul Sector 28 CHS",
            solar_surplus_kw=1.2,
            demand_kw=4.0,
            battery_storage_kwh=0.0,
            pos=(3.5, 5.5)
        ),
        HouseholdNode(
            home_id="HOME_04",
            owner_name="Nerul MSEDCL Sector 20 Battery Substation",
            solar_surplus_kw=0.0,
            demand_kw=0.8,
            battery_storage_kwh=25.0,
            pos=(2.5, 4.2)
        ),
        HouseholdNode(
            home_id="HOME_05",
            owner_name="DY Patil Medical & Critical Care (Nerul)",
            solar_surplus_kw=0.0,
            demand_kw=6.0,
            battery_storage_kwh=5.0,
            pos=(1.2, 3.5)
        ),

        # Island 2: Seawoods Sector (Homes 06 to 10) - Disconnected from Nerul West!
        HouseholdNode(
            home_id="HOME_06",
            owner_name="Seawoods Grand Central Solar Plant",
            solar_surplus_kw=13.0,
            demand_kw=2.0,
            battery_storage_kwh=18.0,
            pos=(5.0, 2.0)
        ),
        HouseholdNode(
            home_id="HOME_07",
            owner_name="Darave Sector 42 Commercial Units",
            solar_surplus_kw=0.0,
            demand_kw=5.5,
            battery_storage_kwh=0.0,
            pos=(6.2, 2.8)
        ),
        HouseholdNode(
            home_id="HOME_08",
            owner_name="NRI Complex Seawoods Towers",
            solar_surplus_kw=0.0,
            demand_kw=3.2,
            battery_storage_kwh=1.0,
            pos=(7.5, 2.2)
        ),
        HouseholdNode(
            home_id="HOME_09",
            owner_name="Seawoods Palm Beach Enclave",
            solar_surplus_kw=0.0,
            demand_kw=4.8,
            battery_storage_kwh=4.0,
            pos=(6.8, 0.8)
        ),
        HouseholdNode(
            home_id="HOME_10",
            owner_name="Karave Creek Pumping Station",
            solar_surplus_kw=0.0,
            demand_kw=3.0,
            battery_storage_kwh=0.0,
            pos=(5.2, 0.5)
        ),
    ]

    edges = [
        # Internal wiring within Island 1 (Nerul West Sector)
        PowerLineEdge("HOME_01", "HOME_02", transfer_capacity_kw=6.0, is_bidirectional=True, line_loss_pct=1.5),
        PowerLineEdge("HOME_02", "HOME_03", transfer_capacity_kw=5.0, is_bidirectional=True, line_loss_pct=1.8),
        PowerLineEdge("HOME_01", "HOME_04", transfer_capacity_kw=8.0, is_bidirectional=True, line_loss_pct=1.2),
        PowerLineEdge("HOME_04", "HOME_05", transfer_capacity_kw=7.0, is_bidirectional=False, line_loss_pct=1.4),
        PowerLineEdge("HOME_03", "HOME_04", transfer_capacity_kw=4.0, is_bidirectional=False, line_loss_pct=1.6),

        # Internal wiring within Island 2 (Seawoods Sector)
        PowerLineEdge("HOME_06", "HOME_07", transfer_capacity_kw=7.0, is_bidirectional=True, line_loss_pct=1.7),
        PowerLineEdge("HOME_07", "HOME_08", transfer_capacity_kw=5.0, is_bidirectional=True, line_loss_pct=2.0),
        PowerLineEdge("HOME_08", "HOME_09", transfer_capacity_kw=5.0, is_bidirectional=True, line_loss_pct=1.9),
        PowerLineEdge("HOME_09", "HOME_10", transfer_capacity_kw=6.0, is_bidirectional=True, line_loss_pct=1.6),
        PowerLineEdge("HOME_06", "HOME_10", transfer_capacity_kw=8.0, is_bidirectional=False, line_loss_pct=1.5),
        # NOTE: NO inter-island power lines exist! (Open circuit breaker across railway/creek)
    ]

    G = build_networkx_graph(nodes, edges)
    meta = {
        "name": "Isolated Islands (Nerul West vs Seawoods)",
        "description": "Two isolated microgrid sectors (Nerul West Sector and Seawoods East) completely disconnected by an open tie-breaker over the railway line/creek corridor.",
        "type": "Disconnected Multi-Component Digraph",
        "nodes_count": len(nodes),
        "producers_count": 2,
        "consumers_count": 8
    }
    return G, meta


# =====================================================================
# Preset 4: Custom Matrix Parser (CSV or JSON)
# =====================================================================
def parse_custom_matrix(
    data_input: Union[str, pd.DataFrame, Dict[str, Any]],
    nodes_metadata: Optional[List[Dict[str, Any]]] = None
) -> Tuple[nx.DiGraph, Dict[str, Any]]:
    """
    Parses a user-defined directed adjacency matrix from CSV text, JSON text,
    a pandas DataFrame, or a dictionary.

    Parameters
    ----------
    data_input : str, pd.DataFrame, or dict
        - If CSV string: comma-separated or whitespace-separated square matrix,
          optionally with header and index for node names.
        - If JSON string or dict:
          {"nodes": ["H1", "H2", ...], "matrix": [[0, 1], [0, 0]]} or
          {"edges": [{"source": "H1", "target": "H2", ...}], "nodes": [...]}
    nodes_metadata : list of dict, optional
        Metadata attributes for the households. If not provided, sensible
        defaults will be automatically generated.

    Returns
    -------
    G : nx.DiGraph
    meta : dict
    """
    G = nx.DiGraph()

    # 1. Handle JSON string or dictionary
    if isinstance(data_input, (dict, str)) and (
        isinstance(data_input, dict) or data_input.strip().startswith("{")
    ):
        raw_dict = json.loads(data_input) if isinstance(data_input, str) else data_input

        # Case A: {"nodes": [...], "matrix": [[...]]}
        if "matrix" in raw_dict:
            matrix = np.array(raw_dict["matrix"], dtype=int)
            n = matrix.shape[0]
            if matrix.shape[1] != n:
                raise ValueError(f"Adjacency matrix must be square, got {matrix.shape}.")

            node_labels = raw_dict.get("nodes", [f"HOME_{i+1:02d}" for i in range(n)])
            if len(node_labels) != n:
                raise ValueError(f"Node labels count ({len(node_labels)}) does not match matrix dimension ({n}).")

            # Create default or provided nodes
            nodes_map = {}
            if nodes_metadata:
                for nm in nodes_metadata:
                    nodes_map[nm["home_id"]] = nm

            for i, label in enumerate(node_labels):
                meta_item = nodes_map.get(label, {})
                pos_val = meta_item.get("pos", (float(np.cos(2 * np.pi * i / n) * 3 + 4), float(np.sin(2 * np.pi * i / n) * 3 + 4)))
                G.add_node(
                    label,
                    home_id=label,
                    owner_name=meta_item.get("owner_name", f"Resident of {label}"),
                    solar_surplus_kw=float(meta_item.get("solar_surplus_kw", 5.0 if i % 3 == 0 else 0.0)),
                    demand_kw=float(meta_item.get("demand_kw", 3.0)),
                    battery_storage_kwh=float(meta_item.get("battery_storage_kwh", 10.0 if i % 3 == 0 else 2.0)),
                    pos=tuple(pos_val),
                    is_producer=float(meta_item.get("solar_surplus_kw", 5.0 if i % 3 == 0 else 0.0)) > float(meta_item.get("demand_kw", 3.0))
                )

            for i in range(n):
                for j in range(n):
                    if matrix[i, j] != 0:
                        G.add_edge(
                            node_labels[i],
                            node_labels[j],
                            transfer_capacity_kw=float(raw_dict.get("transfer_capacity_kw", 6.0)),
                            is_bidirectional=bool(matrix[j, i] != 0),
                            line_loss_pct=2.0
                        )

            meta = {
                "name": raw_dict.get("name", "Custom JSON Matrix"),
                "description": "User-defined custom microgrid topology parsed from JSON format.",
                "type": "Custom Digraph",
                "nodes_count": n,
                "edges_count": G.number_of_edges()
            }
            return G, meta

        # Case B: {"nodes": [...], "edges": [...]}
        elif "edges" in raw_dict and "nodes" in raw_dict:
            node_items = []
            for n_data in raw_dict["nodes"]:
                node_items.append(HouseholdNode(
                    home_id=str(n_data["home_id"]),
                    owner_name=str(n_data.get("owner_name", f"Resident {n_data['home_id']}")),
                    solar_surplus_kw=float(n_data.get("solar_surplus_kw", 0.0)),
                    demand_kw=float(n_data.get("demand_kw", 3.0)),
                    battery_storage_kwh=float(n_data.get("battery_storage_kwh", 5.0)),
                    pos=tuple(n_data.get("pos", (0.0, 0.0)))
                ))

            edge_items = []
            for e_data in raw_dict["edges"]:
                edge_items.append(PowerLineEdge(
                    source=str(e_data["source"]),
                    target=str(e_data["target"]),
                    transfer_capacity_kw=float(e_data.get("transfer_capacity_kw", 6.0)),
                    is_bidirectional=bool(e_data.get("is_bidirectional", False)),
                    line_loss_pct=float(e_data.get("line_loss_pct", 2.0))
                ))

            G = build_networkx_graph(node_items, edge_items)
            meta = {
                "name": raw_dict.get("name", "Custom Edge-List Graph"),
                "description": "User-defined custom microgrid parsed from JSON node and edge lists.",
                "type": "Custom Digraph",
                "nodes_count": len(node_items),
                "edges_count": G.number_of_edges()
            }
            return G, meta

    # 2. Handle CSV string or DataFrame
    if isinstance(data_input, str):
        # Clean comment lines or leading blank lines
        clean_lines = [l for l in data_input.strip().splitlines() if l.strip() and not l.strip().startswith("#")]
        if not clean_lines:
            raise ValueError("Provided CSV input is empty.")
        df = pd.read_csv(io.StringIO("\n".join(clean_lines)), header=None)
    elif isinstance(data_input, pd.DataFrame):
        df = data_input.copy()
    else:
        raise TypeError(f"Unsupported data_input type: {type(data_input)}")

    # Check if first row/column contain labels
    first_cell = str(df.iloc[0, 0]).strip()
    has_labels = False
    try:
        float(first_cell)
    except ValueError:
        # Non-numeric header detected
        has_labels = True

    if has_labels:
        df = pd.read_csv(io.StringIO("\n".join(clean_lines)), index_col=0)
        node_labels = [str(c).strip() for c in df.columns]
        matrix = df.values.astype(int)
    else:
        matrix = df.values.astype(int)
        n = matrix.shape[0]
        node_labels = [f"HOME_{i+1:02d}" for i in range(n)]

    n = matrix.shape[0]
    if matrix.shape[1] != n:
        raise ValueError(f"Adjacency matrix must be square (n x n). Parsed shape: {matrix.shape}")

    # Circular default layout for spatial visualization
    for i, label in enumerate(node_labels):
        angle = 2 * np.pi * i / n
        pos_coord = (round(np.cos(angle) * 3 + 4, 2), round(np.sin(angle) * 3 + 4, 2))
        is_prod = (i % 3 == 0)
        surplus = 8.0 if is_prod else 0.0
        demand = 2.0 if is_prod else 4.0
        G.add_node(
            label,
            home_id=label,
            owner_name=f"Household {label}",
            solar_surplus_kw=surplus,
            demand_kw=demand,
            battery_storage_kwh=10.0 if is_prod else 2.0,
            pos=pos_coord,
            net_balance_kw=round(surplus - demand, 2),
            is_producer=is_prod
        )

    for i in range(n):
        for j in range(n):
            if matrix[i, j] != 0:
                G.add_edge(
                    node_labels[i],
                    node_labels[j],
                    transfer_capacity_kw=6.0,
                    is_bidirectional=bool(matrix[j, i] != 0),
                    line_loss_pct=2.0
                )

    meta = {
        "name": "Custom CSV Adjacency Matrix",
        "description": f"Custom {n}x{n} directed adjacency matrix parsed from CSV.",
        "type": "Custom Digraph",
        "nodes_count": n,
        "edges_count": G.number_of_edges()
    }
    return G, meta


def get_preset_by_name(preset_name: str) -> Tuple[nx.DiGraph, Dict[str, Any]]:
    """
    Registry lookup for neighborhood presets, supporting both standard
    and localized Navi Mumbai / Nerul names.
    """
    norm = preset_name.lower()
    if "suburban" in norm or "cul-de-sac" in norm or "nerul" in norm and "palm" in norm:
        return get_suburban_culdesac()
    elif "asymmetric" in norm or "hillside" in norm or "parsik" in norm or "belapur" in norm:
        return get_asymmetric_hillside()
    elif "isolated" in norm or "island" in norm or "seawoods" in norm:
        return get_isolated_islands()
    else:
        raise ValueError(f"Unknown preset name: '{preset_name}'.")
