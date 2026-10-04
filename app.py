"""
app.py
======
Solar Share Grid - Peer-to-Peer (P2P) Rooftop Solar Microgrid Modeling
Built with Streamlit, NetworkX, NumPy, Pandas, and Plotly.

Localized for Nerul, Navi Mumbai, and Mumbai microgrid topologies.

Key Features (Prompt 3 Integrated):
1. Top KPI Summary Cards:
   - Solar Reachability (% households receiving solar)
   - Unserved Households Count (Red highlight if > 0)
   - Total Available Surplus vs Total Unmet Demand (kW)
   - Strongly Connected Energy Communities (SCC Count)
2. Sidebar Controls:
   - Neighborhood Preset Selector
   - Dynamic Edge Manager: break lines, reverse direction, toggle bidirectional
   - Household Solar Output Sliders (kW)
   - Matrix Toggle: Raw Adjacency Matrix (A) vs Transitive Closure (R+)
3. Main Interactive Digraph Visualizer:
   - One-Way Lines: Distinct dashed orange arrows
   - Two-Way Lines: Solid green double-headed edges
   - Node Color Coding:
     * Gold / Bright Yellow: Solar Power Exporter (surplus > 0)
     * Green: Consumer home successfully connected to solar power
     * Red: Left-Out / Unconnected Home with unmet demand
   - Rich Tooltips: ID, Output, Demand, Battery, Downstream Reachable Homes
4. Lower Tabbed Analytical Panel:
   - Tab 1: "Reachability Matrix"
   - Tab 2: "Left-Out Households"
   - Tab 3: "Relation Properties"
   - Tab 4: "Algorithm Stepper & Components"
   - Tab 5: "Custom Matrix Studio"
"""

import json
from typing import Dict, List, Tuple, Any, Optional, Set
import streamlit as st
import numpy as np
import pandas as pd
import networkx as nx
import plotly.graph_objects as go

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
from reachability_analyzer import (
    analyze_solar_coverage,
    compute_microgrid_metrics,
    analyze_connectivity_components,
    run_full_reachability_audit
)
from link_optimizer import optimize_microgrid_links
from trade_simulator import (
    calculate_path_loss,
    simulate_p2p_trade_cycle,
    generate_executive_report_bundle,
    DEFAULT_UTILITY_TARIFF_USD,
    DEFAULT_P2P_TARIFF_USD
)

# -----------------------------------------------------------------------------
# Streamlit Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Solar Share Grid | Discrete Math & Digraph Microgrids",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling for modern energy-grid aesthetics & discrete math callouts
st.markdown("""
<style>
    .metric-card-container {
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 14px 12px;
        text-align: center;
        min-height: 125px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .metric-card-alert {
        background-color: #1e1b2e;
        border: 2px solid #ef4444;
        border-radius: 10px;
        padding: 14px 12px;
        text-align: center;
        min-height: 125px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        box-shadow: 0 4px 12px rgba(239, 68, 68, 0.2);
    }
    .kpi-title {
        color: #94a3b8;
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    .kpi-val {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f8fafc;
        line-height: 1.2;
    }
    .kpi-sub {
        font-size: 0.78rem;
        color: #64748b;
        margin-top: 4px;
        line-height: 1.3;
    }
    .kpi-val-red {
        color: #ef4444;
        font-size: 1.8rem;
        font-weight: 700;
    }
    .kpi-val-green {
        color: #10b981;
        font-size: 1.8rem;
        font-weight: 700;
    }
    .math-callout {
        background-color: #0f172a;
        border-left: 4px solid #38bdf8;
        padding: 12px 18px;
        border-radius: 0 8px 8px 0;
        margin: 12px 0 16px 0;
        font-size: 0.95rem;
        line-height: 1.5;
    }
    .status-badge-true {
        background-color: #065f46;
        color: #34d399;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
        margin-bottom: 6px;
    }
    .status-badge-false {
        background-color: #7f1d1d;
        color: #f87171;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
        margin-bottom: 6px;
    }
    /* Smooth button styling */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Session State Initialization
# -----------------------------------------------------------------------------
if "custom_csv" not in st.session_state:
    st.session_state["custom_csv"] = """0, 1, 0, 0
0, 0, 1, 0
0, 0, 0, 1
1, 0, 0, 0"""

if "edge_overrides" not in st.session_state:
    st.session_state["edge_overrides"] = {}  # tuple (u, v) -> action

if "solar_overrides" not in st.session_state:
    st.session_state["solar_overrides"] = {}  # node_id -> float surplus_kw

if "ai_added_links" not in st.session_state:
    st.session_state["ai_added_links"] = set()  # set of (u, v) tuples added by optimizer

if "trade_sim_results" not in st.session_state:
    st.session_state["trade_sim_results"] = None  # P2P trade settlement results cache

if "active_preset_name" not in st.session_state:
    st.session_state["active_preset_name"] = "🏡 Nerul Palm Beach Cul-de-Sac (Balanced)"


# -----------------------------------------------------------------------------
# Digraph Plotly Visualizer (Prompt 3 & 4 Specifications)
# -----------------------------------------------------------------------------
def plot_microgrid_digraph(
    G: nx.DiGraph,
    coverage_data: Dict[str, Any],
    reachability_map: Dict[str, List[str]],
    use_preset_coords: bool = True,
    ai_added_links: Optional[Set[Tuple[str, str]]] = None
) -> go.Figure:
    """
    Renders an interactive 2D directed graph map of the microgrid using Plotly.

    Strict Visual Schema:
    - Directed Arrows: Show exact power flow direction along edges.
    - One-Way Lines: Distinct dashed orange arrows (#f97316).
    - Two-Way Lines: Solid green double-headed edges (#10b981).
    - AI Added Lines: Distinct animated bright cyan arrows (#00f0ff).
    - Node Color Coding:
        * Gold / Bright Yellow (#eab308): Solar Power Exporter (surplus > 0).
        * Green (#22c55e): Consumer home successfully connected to solar power.
        * Red (#ef4444): Left-Out / Unconnected Home with unmet demand.
    - Tooltips: Household ID, Solar Output, Demand, Battery Level, Downstream Reachable Homes.
    """
    if use_preset_coords and all("pos" in data for _, data in G.nodes(data=True)):
        pos = {node: data["pos"] for node, data in G.nodes(data=True)}
    else:
        pos = nx.spring_layout(G, seed=42, k=1.2)

    fig = go.Figure()
    ai_links_set = ai_added_links if ai_added_links else set()

    # Track processed edge pairs to avoid duplicate bidirectional rendering
    processed_pairs: Set[Tuple[str, str]] = set()

    for u, v in G.edges():
        pair_key = tuple(sorted([u, v]))
        if pair_key in processed_pairs:
            continue

        x0, y0 = pos[u]
        x1, y1 = pos[v]

        # Check if this edge is an AI-added optimized link
        is_ai_link = (u, v) in ai_links_set or (v, u) in ai_links_set

        if is_ai_link:
            # Render in Animated Bright Cyan (#00f0ff)
            processed_pairs.add(pair_key)
            edge_data = G[u][v]
            cap = edge_data.get("transfer_capacity_kw", 6.0)

            fig.add_trace(go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode="lines",
                line=dict(color="#00f0ff", width=4.5, dash="solid"),
                hoverinfo="text",
                text=f"<b>💡 AI OPTIMIZED LINK:</b> {u} ➔ {v}<br>Capacity: {cap} kW<br>Status: Added by AI Line Optimizer",
                showlegend=False
            ))

            t = 0.65
            xa = x0 + t * (x1 - x0)
            ya = y0 + t * (y1 - y0)
            fig.add_annotation(
                x=xa, y=ya,
                ax=x0 + (t - 0.15) * (x1 - x0),
                ay=y0 + (t - 0.15) * (y1 - y0),
                xref="x", yref="y", axref="x", ayref="y",
                text="", showarrow=True, arrowhead=3, arrowsize=1.8,
                arrowwidth=3, arrowcolor="#00f0ff"
            )
            continue

        # Check if line is bidirectional (both u -> v and v -> u exist in G)
        is_two_way = G.has_edge(u, v) and G.has_edge(v, u)

        if is_two_way:
            processed_pairs.add(pair_key)
            edge_data_uv = G[u][v]
            cap = edge_data_uv.get("transfer_capacity_kw", 6.0)
            loss = edge_data_uv.get("line_loss_pct", 2.0)

            # Draw solid green line
            fig.add_trace(go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode="lines",
                line=dict(color="#10b981", width=3.0, dash="solid"),
                hoverinfo="text",
                text=f"<b>Two-Way Line:</b> {u} ⇄ {v}<br>Capacity: {cap} kW<br>Line Loss: {loss}%<br>Type: Bidirectional Trading",
                showlegend=False
            ))

            # Double-headed arrows
            # Arrow towards v (at 70% distance)
            t1 = 0.70
            xa1 = x0 + t1 * (x1 - x0)
            ya1 = y0 + t1 * (y1 - y0)
            fig.add_annotation(
                x=xa1, y=ya1,
                ax=x0 + (t1 - 0.12) * (x1 - x0),
                ay=y0 + (t1 - 0.12) * (y1 - y0),
                xref="x", yref="y", axref="x", ayref="y",
                text="", showarrow=True, arrowhead=2, arrowsize=1.3,
                arrowwidth=2, arrowcolor="#10b981"
            )
            # Arrow towards u (at 30% distance)
            t2 = 0.30
            xa2 = x0 + t2 * (x1 - x0)
            ya2 = y0 + t2 * (y1 - y0)
            fig.add_annotation(
                x=xa2, y=ya2,
                ax=x0 + (t2 + 0.12) * (x1 - x0),
                ay=y0 + (t2 + 0.12) * (y1 - y0),
                xref="x", yref="y", axref="x", ayref="y",
                text="", showarrow=True, arrowhead=2, arrowsize=1.3,
                arrowwidth=2, arrowcolor="#10b981"
            )
        else:
            # One-Way Line: distinct dashed orange arrow (#f97316)
            edge_data = G[u][v]
            cap = edge_data.get("transfer_capacity_kw", 5.0)
            loss = edge_data.get("line_loss_pct", 2.0)

            fig.add_trace(go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode="lines",
                line=dict(color="#f97316", width=2.2, dash="dash"),
                hoverinfo="text",
                text=f"<b>One-Way Feeder:</b> {u} ➔ {v}<br>Capacity: {cap} kW<br>Line Loss: {loss}%<br>Type: Unidirectional Flow",
                showlegend=False
            ))

            # Arrow pointing towards v (at 65% distance)
            t = 0.65
            xa = x0 + t * (x1 - x0)
            ya = y0 + t * (y1 - y0)
            fig.add_annotation(
                x=xa, y=ya,
                ax=x0 + (t - 0.14) * (x1 - x0),
                ay=y0 + (t - 0.14) * (y1 - y0),
                xref="x", yref="y", axref="x", ayref="y",
                text="", showarrow=True, arrowhead=2, arrowsize=1.3,
                arrowwidth=2, arrowcolor="#f97316"
            )

    # Prepare Node Visuals
    left_out_set = {item["home_id"] for item in coverage_data["left_out_households"]}

    node_x, node_y = [], []
    node_text = []
    node_colors = []
    node_sizes = []
    node_borders = []

    for node, data in G.nodes(data=True):
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)

        owner = data.get("owner_name", node)
        surplus = float(data.get("solar_surplus_kw", 0.0))
        demand = float(data.get("demand_kw", 0.0))
        battery = float(data.get("battery_storage_kwh", 0.0))

        # Downstream reachable homes from Warshall reachability map
        downstream = reachability_map.get(node, [])
        downstream_others = [h for h in downstream if h != node]
        downstream_str = ", ".join(downstream_others) if downstream_others else "(None)"

        # Color Coding Logic (Prompt 3):
        # 1. Gold / Bright Yellow: Solar Power Exporter (surplus > 0)
        # 2. Red: Left-Out / Unconnected Home with unmet demand
        # 3. Green: Consumer home successfully connected to solar power
        if surplus > 0:
            color = "#eab308"  # Gold / Bright Yellow
            role = f"☀️ Solar Exporter (+{surplus} kW)"
            size = 28
            border = dict(color="#fef08a", width=2.5)
        elif node in left_out_set:
            color = "#ef4444"  # Red (Left-Out / Unconnected)
            role = f"🔴 Left-Out / Unconnected ({demand} kW unmet)"
            size = 26
            border = dict(color="#fecaca", width=2.5)
        else:
            color = "#22c55e"  # Green (Connected Consumer)
            role = f"🟢 Connected Consumer ({demand} kW)"
            size = 24
            border = dict(color="#bbf7d0", width=2)

        node_colors.append(color)
        node_sizes.append(size)
        node_borders.append(border)

        # Tooltip Schema (Prompt 3):
        tooltip = (
            f"<b>Household ID: {node}</b><br>"
            f"<b>Resident / Facility:</b> {owner}<br>"
            f"<b>Role:</b> {role}<br>"
            f"<b>Solar Output:</b> {surplus:.1f} kW<br>"
            f"<b>Household Demand:</b> {demand:.1f} kW<br>"
            f"<b>Battery Level:</b> {battery:.1f} kWh<br>"
            f"<b>Downstream Reachable Homes:</b> {downstream_str}"
        )
        node_text.append(tooltip)

    fig.add_trace(go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=list(G.nodes()),
        textposition="top center",
        textfont=dict(size=12, color="#f8fafc", family="sans-serif"),
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=2, color="#ffffff"),
            opacity=0.95
        ),
        hoverinfo="text",
        hovertext=node_text,
        name="Households"
    ))

    # Add Visual Legend Traces (dummy scatters for clean Plotly legend)
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers",
        marker=dict(size=12, color="#eab308"),
        name="Solar Exporter (Surplus > 0)", showlegend=True
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers",
        marker=dict(size=12, color="#22c55e"),
        name="Connected Consumer (Receives Solar)", showlegend=True
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers",
        marker=dict(size=12, color="#ef4444"),
        name="Left-Out Home (Unserved)", showlegend=True
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="lines",
        line=dict(color="#10b981", width=3, dash="solid"),
        name="Two-Way Line (Solid Green)", showlegend=True
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="lines",
        line=dict(color="#f97316", width=2.5, dash="dash"),
        name="One-Way Line (Dashed Orange)", showlegend=True
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="lines",
        line=dict(color="#00f0ff", width=4.5, dash="solid"),
        name="💡 AI-Optimized Link (Cyan)", showlegend=True
    ))

    fig.update_layout(
        paper_bgcolor="rgba(15, 23, 42, 0.5)",
        plot_bgcolor="rgba(15, 23, 42, 0.85)",
        margin=dict(l=20, r=20, t=30, b=70),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=540,
        legend=dict(
            orientation="h",
            yanchor="bottom", y=-0.18,
            xanchor="center", x=0.5,
            font=dict(color="#cbd5e1", size=11),
            bgcolor="rgba(15, 23, 42, 0.8)",
            bordercolor="rgba(51, 65, 85, 0.6)",
            borderwidth=1
        )
    )
    return fig


def plot_matrix_heatmap(
    matrix: np.ndarray,
    labels: List[str],
    title: str,
    highlight_color: str = "#0284c7"
) -> go.Figure:
    """
    Renders an annotated boolean matrix heatmap.
    """
    n = len(labels)
    val_matrix = matrix.astype(int)

    text_matrix = [[str(val_matrix[i, j]) for j in range(n)] for i in range(n)]

    fig = go.Figure(data=go.Heatmap(
        z=val_matrix,
        x=labels,
        y=labels,
        text=text_matrix,
        texttemplate="%{text}",
        textfont={"size": 13, "color": "#f8fafc"},
        colorscale=[
            [0.0, "#0f172a"],        # 0 = No Link (Dark Slate)
            [1.0, highlight_color]   # 1 = Active Link (Green/Blue)
        ],
        showscale=False,
        hoverongaps=False
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#e2e8f0")),
        xaxis=dict(tickmode="array", tickvals=list(range(n)), ticktext=labels, side="top"),
        yaxis=dict(tickmode="array", tickvals=list(range(n)), ticktext=labels, autorange="reversed"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=30, r=30, t=50, b=30),
        height=400,
        autosize=True
    )
    return fig


# -----------------------------------------------------------------------------
# Main Application Header
# -----------------------------------------------------------------------------
st.title("⚡ Solar Share Grid — Discrete Mathematics Microgrid Engine")
st.markdown("##### *Peer-to-Peer Rooftop Solar Trading Digraph Simulation (Navi Mumbai & Mumbai Edition)*")


# -----------------------------------------------------------------------------
# Sidebar: Preset Neighborhood, Dynamic Edge Manager, & Solar Sliders
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("🌐 Microgrid Controls")

    preset_choice = st.selectbox(
        "Choose Neighborhood Preset:",
        [
            "🏡 Suburban Cul-de-Sac (Nerul Palm Beach)",
            "🏔️ Asymmetric Hillside (Parsik Hill Slopes)",
            "🏝️ Isolated Islands (Nerul West vs Seawoods East)",
            "🛠️ Custom Matrix Upload / Studio"
        ],
        index=0
    )

    # Check if preset changed to reset overrides
    if preset_choice != st.session_state["active_preset_name"]:
        st.session_state["active_preset_name"] = preset_choice
        st.session_state["edge_overrides"] = {}
        st.session_state["solar_overrides"] = {}
        st.session_state["ai_added_links"] = set()
        st.session_state["trade_sim_results"] = None

    st.markdown("---")
    st.subheader("🔀 Matrix Display Mode")
    matrix_view_choice = st.radio(
        "Active Matrix View:",
        ["Transitive Closure Matrix (R+)", "Raw Adjacency Matrix (A)"],
        index=0,
        help="Toggle between direct physical wiring (A) and multi-hop reachability computed via Warshall's Algorithm (R+)."
    )

    st.markdown("---")
    st.subheader("⚡ Dynamic Grid Line Manager")
    st.caption("Manually break power lines, toggle directions, or upgrade meters:")


# -----------------------------------------------------------------------------
# Base Graph Instantiation
# -----------------------------------------------------------------------------
if preset_choice == "🏡 Suburban Cul-de-Sac (Nerul Palm Beach)":
    base_G, meta = get_suburban_culdesac()
elif preset_choice == "🏔️ Asymmetric Hillside (Parsik Hill Slopes)":
    base_G, meta = get_asymmetric_hillside()
elif preset_choice == "🏝️ Isolated Islands (Nerul West vs Seawoods East)":
    base_G, meta = get_isolated_islands()
else:
    try:
        base_G, meta = parse_custom_matrix(st.session_state["custom_csv"])
    except Exception as e:
        st.sidebar.error(f"Custom matrix parse error: {e}. Reverting to Suburban.")
        base_G, meta = get_suburban_culdesac()

# Create active mutable copy of graph
G = base_G.copy()

# -----------------------------------------------------------------------------
# Apply Dynamic Edge Overrides & Solar Sliders (Prompt 3 Interactive Controls)
# -----------------------------------------------------------------------------
# Extract all canonical base edges for user dropdown
all_possible_edges = sorted(list(base_G.edges()))
edge_options = [f"{u} ➔ {v}" for u, v in all_possible_edges]

with st.sidebar:
    if edge_options:
        selected_edge_str = st.selectbox("Select Power Line to Modify:", edge_options)
        src_node, tgt_node = selected_edge_str.split(" ➔ ")

        edge_action = st.selectbox(
            "Line Operation:",
            [
                "Default (Preset Wiring)",
                "❌ Break Line (Disconnect Flow)",
                "➔ Force One-Way (u ➔ v only)",
                "⬅ Force One-Way (v ➔ u only)",
                "🔄 Make Bidirectional (u ⇄ v)"
            ],
            index=0
        )

        col_edge_btn1, col_edge_btn2 = st.columns(2)
        with col_edge_btn1:
            if st.button("Apply Line Action", use_container_width=True):
                st.session_state["edge_overrides"][(src_node, tgt_node)] = edge_action
                st.session_state["trade_sim_results"] = None
                st.success(f"Updated {src_node} ➔ {tgt_node}!")
                st.rerun()

        with col_edge_btn2:
            if st.button("Reset All Lines", use_container_width=True):
                st.session_state["edge_overrides"] = {}
                st.session_state["trade_sim_results"] = None
                st.rerun()

    if st.session_state["edge_overrides"]:
        st.caption(f"Active overrides: {len(st.session_state['edge_overrides'])} line(s)")

    st.markdown("---")
    st.subheader("☀️ Household Solar Controller")
    st.caption("Adjust rooftop solar output (kW) to simulate prosumer surges or cloud cover:")

    all_homes = list(G.nodes())
    selected_home_for_solar = st.selectbox("Select Household:", all_homes, index=0)
    current_solar_default = float(base_G.nodes[selected_home_for_solar].get("solar_surplus_kw", 0.0))
    current_solar_active = float(st.session_state["solar_overrides"].get(selected_home_for_solar, current_solar_default))

    new_solar_val = st.slider(
        f"Solar Output for {selected_home_for_solar} (kW):",
        min_value=0.0,
        max_value=25.0,
        value=current_solar_active,
        step=0.5
    )

    if new_solar_val != current_solar_active:
        st.session_state["solar_overrides"][selected_home_for_solar] = new_solar_val
        st.session_state["trade_sim_results"] = None
        st.rerun()

    if st.button("Reset Solar to Preset Defaults", use_container_width=True):
        st.session_state["solar_overrides"] = {}
        st.session_state["trade_sim_results"] = None
        st.rerun()

    st.markdown("---")
    use_spatial_coords = st.checkbox("Use Physical (x, y) Layout", value=True)


# -----------------------------------------------------------------------------
# Mutate Active Graph According to User Overrides
# -----------------------------------------------------------------------------
# 1. Apply Solar Overrides
for node_id, new_val in st.session_state["solar_overrides"].items():
    if node_id in G.nodes:
        G.nodes[node_id]["solar_surplus_kw"] = float(new_val)
        demand = float(G.nodes[node_id].get("demand_kw", 0.0))
        G.nodes[node_id]["is_producer"] = float(new_val) > demand
        G.nodes[node_id]["net_balance_kw"] = round(float(new_val) - demand, 2)

# 2. Apply Edge Overrides
for (u, v), action in st.session_state["edge_overrides"].items():
    if action == "❌ Break Line (Disconnect Flow)":
        if G.has_edge(u, v):
            G.remove_edge(u, v)
        if G.has_edge(v, u):
            G.remove_edge(v, u)
    elif action == "➔ Force One-Way (u ➔ v only)":
        if not G.has_edge(u, v):
            G.add_edge(u, v, transfer_capacity_kw=6.0, line_loss_pct=2.0)
        if G.has_edge(v, u):
            G.remove_edge(v, u)
    elif action == "⬅ Force One-Way (v ➔ u only)":
        if G.has_edge(u, v):
            G.remove_edge(u, v)
        if not G.has_edge(v, u):
            G.add_edge(v, u, transfer_capacity_kw=6.0, line_loss_pct=2.0)
    elif action == "🔄 Make Bidirectional (u ⇄ v)":
        if not G.has_edge(u, v):
            G.add_edge(u, v, transfer_capacity_kw=6.0, line_loss_pct=2.0)
        if not G.has_edge(v, u):
            G.add_edge(v, u, transfer_capacity_kw=6.0, line_loss_pct=2.0)

# 3. Apply AI-Added Optimized Links
for (u, v) in st.session_state["ai_added_links"]:
    if not G.has_edge(u, v):
        G.add_edge(u, v, transfer_capacity_kw=6.0, line_loss_pct=1.8, is_bidirectional=False)


# -----------------------------------------------------------------------------
# Mathematical Matrix Computation & Reachability Analysis (Modules 1 & 2)
# -----------------------------------------------------------------------------
adj_matrix, node_labels = graph_to_adjacency_matrix(G)
transitive_closure_matrix, reachability_dict, warshall_steps = compute_transitive_closure(
    adj_matrix, node_labels=node_labels, return_steps=True
)
relation_properties = extract_binary_relations(adj_matrix, node_labels=node_labels)

# Full analytical audit
audit_results = run_full_reachability_audit(G)
coverage_analysis = audit_results["coverage"]
microgrid_metrics = audit_results["metrics"]
connectivity_analysis = audit_results["connectivity"]


# -----------------------------------------------------------------------------
# 1. TOP KPI SUMMARY CARDS (Prompt 3 Requirements)
# -----------------------------------------------------------------------------
# Metric 1: Microgrid Solar Reachability (% Households receiving solar)
# Metric 2: Unserved Households Count (Red highlight if > 0)
# Metric 3: Total Available Surplus vs Total Unmet Demand (kW)
# Metric 4: Number of Strongly Connected Energy Communities (SCC Count)

total_nodes_count = len(node_labels)
left_out_count = coverage_analysis["left_out_count"]
served_count = total_nodes_count - left_out_count
reachability_rate_pct = round((served_count / total_nodes_count) * 100.0, 1) if total_nodes_count > 0 else 100.0

total_surplus_kw = microgrid_metrics["total_solar_generation_kw"]
total_demand_kw = microgrid_metrics["total_neighborhood_demand_kw"]

# Unmet demand from left-out households
unmet_demand_kw = round(sum(item["demand_kw"] for item in coverage_analysis["left_out_households"]), 2)
scc_count = connectivity_analysis["scc_count"]
rings_count = connectivity_analysis["mutual_trading_rings_count"]

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

with kpi_col1:
    st.markdown("""
    <div class="metric-card-container">
        <div class="kpi-title">Solar Reachability</div>
        <div class="kpi-val kpi-val-green">{:.1f}%</div>
        <div class="kpi-sub">{}/{} Households Receiving Solar</div>
    </div>
    """.format(reachability_rate_pct, served_count, total_nodes_count), unsafe_allow_html=True)

with kpi_col2:
    if left_out_count > 0:
        st.markdown(f"""
        <div class="metric-card-alert">
            <div class="kpi-title" style="color: #fca5a5;">Unserved Households</div>
            <div class="kpi-val kpi-val-red">{left_out_count} CUT OFF</div>
            <div class="kpi-sub" style="color: #f87171;">⚠️ Zero Access to Solar Surplus</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="metric-card-container">
            <div class="kpi-title">Unserved Households</div>
            <div class="kpi-val kpi-val-green">0</div>
            <div class="kpi-sub">✅ 100% Inclusivity (No Isolated Homes)</div>
        </div>
        """, unsafe_allow_html=True)

with kpi_col3:
    st.markdown(f"""
    <div class="metric-card-container">
        <div class="kpi-title">Surplus vs Unmet Demand</div>
        <div class="kpi-val">{total_surplus_kw:.1f} <span style="font-size:1rem;color:#94a3b8;">kW</span></div>
        <div class="kpi-sub">Total Surplus • Unmet Deficit: <span style="color:{'#ef4444' if unmet_demand_kw > 0 else '#10b981'};font-weight:700;">{unmet_demand_kw:.1f} kW</span></div>
    </div>
    """, unsafe_allow_html=True)

with kpi_col4:
    st.markdown(f"""
    <div class="metric-card-container">
        <div class="kpi-title">Energy Communities (SCC)</div>
        <div class="kpi-val">{scc_count}</div>
        <div class="kpi-sub">{rings_count} Mutual Trading Ring(s) Active</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")  # Visual spacer


# -----------------------------------------------------------------------------
# 3. MAIN INTERACTIVE DIGRAPH VISUALIZER (Prompt 3 Requirements)
# -----------------------------------------------------------------------------
st.markdown(f"### 📍 Microgrid Topology: `{meta['name']}`")
st.caption(meta["description"])

fig_digraph = plot_microgrid_digraph(
    G=G,
    coverage_data=coverage_analysis,
    reachability_map=reachability_dict,
    use_preset_coords=use_spatial_coords,
    ai_added_links=st.session_state["ai_added_links"]
)
st.plotly_chart(fig_digraph, use_container_width=True)


# -----------------------------------------------------------------------------
# 4. LOWER TABBED ANALYTICAL PANEL (Prompt 3, 4 & 5 Requirements)
# -----------------------------------------------------------------------------
tab1, tab2, tab_ai, tab_trade, tab3, tab4, tab5 = st.tabs([
    "🔁 Reachability Matrix",
    "🔴 Left-Out Households",
    "💡 AI Line Optimization",
    "💰 P2P Trade & Loss Model",
    "📐 Relation Properties",
    "🔬 Algorithm Stepper & SCCs",
    "🛠️ Studio & Executive Reports"
])


# =============================================================================
# TAB 1: Reachability Matrix (Prompt 3)
# =============================================================================
with tab1:
    st.header("🔁 Reachability Matrix Analysis")
    st.markdown(r"""
    <div class="math-callout">
        <b>Transitive Reachability Matrix \(R^+\)</b><br>
        Computed using <b>Warshall's Algorithm</b> from scratch:
        $$R^{(k)}[i, j] = R^{(k-1)}[i, j] \lor \left(R^{(k-1)}[i, k] \land R^{(k-1)}[k, j]\right)$$
        Entry \((i, j) = 1\) indicates that excess power generated at household \(i\) can reach household \(j\)
        either through a direct power feeder or via multi-hop routing across intermediate homes.
    </div>
    """, unsafe_allow_html=True)

    col_m_view1, col_m_view2 = st.columns([5, 5])

    # Respect the sidebar matrix view toggle
    active_matrix = transitive_closure_matrix if "Transitive" in matrix_view_choice else adj_matrix
    matrix_label = "Transitive Closure Reachability Matrix R+" if "Transitive" in matrix_view_choice else "Raw Adjacency Matrix A (Direct Lines)"
    highlight_col = "#0284c7" if "Transitive" in matrix_view_choice else "#047857"

    with col_m_view1:
        st.subheader(f"📊 Heatmap: {matrix_label}")
        fig_heat = plot_matrix_heatmap(active_matrix, node_labels, matrix_label, highlight_col)
        st.plotly_chart(fig_heat, use_container_width=True)

    with col_m_view2:
        st.subheader("📋 Tabular Matrix Data")
        df_matrix = pd.DataFrame(active_matrix.astype(int), index=node_labels, columns=node_labels)
        st.dataframe(df_matrix, use_container_width=True)

        st.markdown("---")
        st.markdown("**Matrix Statistics:**")
        st.write(f"- Direct Physical Lines ($W^{(0)}$): **{int(np.sum(adj_matrix))}**")
        st.write(f"- Reachable Directed Pairs ($R^+$): **{int(np.sum(transitive_closure_matrix))}**")
        st.write(f"- Multi-Hop Paths Unlocked: **{int(np.sum(transitive_closure_matrix)) - int(np.sum(adj_matrix))}**")

    st.markdown("---")
    st.subheader("📖 Downstream Reachability Directory")
    reach_rows = []
    for home in node_labels:
        reachable = reachability_dict[home]
        reachable_downstream = [h for h in reachable if h != home]
        reach_rows.append({
            "Source Home": home,
            "Resident / Landmark": G.nodes[home].get("owner_name", home),
            "Solar Output (kW)": float(G.nodes[home].get("solar_surplus_kw", 0.0)),
            "Can Self-Power (Cycle)": "Yes" if home in reachable else "No",
            "Downstream Reachable Count": len(reachable_downstream),
            "Downstream Reachable Homes": ", ".join(reachable_downstream) if reachable_downstream else "(None)"
        })
    st.dataframe(pd.DataFrame(reach_rows), use_container_width=True, hide_index=True)


# =============================================================================
# TAB 2: Left-Out Households (Prompt 3)
# =============================================================================
with tab2:
    st.header("🔴 Left-Out Households Analysis")
    st.markdown(r"""
    <div class="math-callout">
        <b>Mathematical Left-Out Criterion</b><br>
        A household \(v \in V\) is classified as <b>Left-Out</b> if it has electricity demand (\(\text{demand}(v) > 0\)),
        yet <b>NO directed path exists from ANY solar power generator</b> in the microgrid:<br>
        $$\text{Reach}^{-1}(v) \cap \{u \in V \mid \text{surplus}(u) > 0\} = \emptyset$$
    </div>
    """, unsafe_allow_html=True)

    if coverage_analysis["left_out_count"] > 0:
        st.error(
            f"🚨 **{coverage_analysis['left_out_count']} Household(s) are Currently Cut Off from Solar Energy!**"
        )
        st.caption(
            "These consumers have active power demand but zero access to neighborhood solar surplus due to one-way smart meters, broken lines, or electrical islanding."
        )

        st.dataframe(coverage_analysis["left_out_df"], use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("🔧 Engineering Diagnostic & Recommendations")
        for item in coverage_analysis["left_out_households"]:
            c_id = item["home_id"]
            name = item["owner_name"]
            deficit = item["demand_kw"]
            nearest_p = item.get("nearest_producer_id", "None")
            hops = item.get("distance_hops", "N/A")

            st.markdown(
                f"- **{c_id} ({name})**: Deficit of `{deficit:.1f} kW`. "
                f"Nearest solar generator is `{nearest_p}`, located `{hops}` away physically. "
                f"*Action:* Upgrade intermediate lines to bidirectional smart metering, or close local tie-breakers."
            )
    else:
        st.success(
            "🎉 **Zero Left-Out Households! 100% Microgrid Inclusivity Achieved.**"
        )
        st.write(
            "Every consumer household in this neighborhood has at least one active, directed transmission route "
            "originating from a surplus rooftop solar generator."
        )

    st.markdown("---")
    st.subheader("🔌 Complete Consumer Solar Access Directory")
    st.dataframe(coverage_analysis["consumers_df"], use_container_width=True, hide_index=True)


# =============================================================================
# TAB AI: AI Line Optimization (Prompt 4 Requirements)
# =============================================================================
with tab_ai:
    st.header("💡 AI Microgrid Line Optimization Engine")
    st.markdown(r"""
    <div class="math-callout">
        <b>Discrete Optimization: The "Left-Out Household" Heuristic</b><br>
        Finds the single optimal missing directed edge \((u, v) \notin E\) that maximizes reachability expansion
        per unit of physical transmission line distance:
        $$\text{Score}(u, v) = \frac{\Delta \text{Powered Homes} \times \Delta \text{Newly Served kW}}{\text{Euclidean Distance}(u, v)}$$
        For every candidate edge, Warshall's transitive closure algorithm is re-evaluated on \(D' = D \cup \{(u, v)\}\)
        to identify newly unlocked downstream transmission paths from surplus solar generators.
    </div>
    """, unsafe_allow_html=True)

    # 1. Active AI Lines Status & Revert controls
    if st.session_state["ai_added_links"]:
        st.markdown(
            f"""
            <div style="background-color: #083344; border: 2px solid #00f0ff; border-radius: 8px; padding: 12px 18px; margin-bottom: 16px;">
                <span style="color: #00f0ff; font-weight: 700; font-size: 1.1rem;">⚡ Active AI-Added Optimization Line(s):</span>
                <span style="color: #e2e8f0; font-size: 0.95rem; margin-left: 8px;">
                    {", ".join([f"<b>{u} ➔ {v}</b>" for u, v in st.session_state['ai_added_links']])}
                </span>
                <div style="color: #94a3b8; font-size: 0.82rem; margin-top: 4px;">
                    Rendered as bright cyan arrows on the microgrid map. Real-time reachability matrices and KPIs reflect these connected lines.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        col_revert, _ = st.columns([3, 7])
        with col_revert:
            if st.button("❌ Disconnect AI-Added Links (Revert Grid)", key="btn_revert_ai"):
                st.session_state["ai_added_links"] = set()
                st.rerun()

    # 2. Run optimization on current active graph G
    opt_results = optimize_microgrid_links(G, top_k=5)
    best_link = opt_results["best_link"]
    has_left_out = opt_results["has_left_out"]

    if best_link is None:
        st.info("Network is complete. No candidate missing lines available.")
    else:
        # If there are left-out households, display prominent callout card for #1 recommendation
        if has_left_out and best_link["delta_powered_homes"] > 0:
            st.subheader("🏆 #1 Recommended Line Addition")

            src = best_link["source"]
            tgt = best_link["target"]
            src_name = best_link["source_name"]
            tgt_name = best_link["target_name"]
            d_homes = best_link["delta_powered_homes"]
            d_kw = best_link["delta_demand_kw"]
            dist = best_link["euclidean_distance"]
            score = best_link["score"]
            new_homes_str = ", ".join(best_link["newly_connected_homes"])

            st.markdown(f"""
            <div style="background-color: #032b30; border: 2px solid #00f0ff; border-radius: 10px; padding: 20px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <span style="font-size: 1.3rem; font-weight: 800; color: #00f0ff;">
                        Proposed Directed Link: {src} ➔ {tgt}
                    </span>
                    <span style="background-color: #083344; color: #38bdf8; padding: 4px 12px; border-radius: 20px; font-weight: 700; font-size: 0.9rem; border: 1px solid #00f0ff;">
                        Efficiency Score: {score:.2f}
                    </span>
                </div>
                <div style="color: #e2e8f0; font-size: 1rem; margin-bottom: 14px; line-height: 1.5;">
                    Connect feeder line from <b>{src} ({src_name})</b> to <b>{tgt} ({tgt_name})</b>.
                </div>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; text-align: center; background-color: #082026; padding: 12px; border-radius: 8px;">
                    <div>
                        <div style="color: #94a3b8; font-size: 0.8rem;">Δ POWERED HOMES</div>
                        <div style="color: #34d399; font-size: 1.5rem; font-weight: 700;">+{d_homes}</div>
                        <div style="color: #64748b; font-size: 0.75rem;">{new_homes_str}</div>
                    </div>
                    <div>
                        <div style="color: #94a3b8; font-size: 0.8rem;">Δ UNMET DEMAND SERVED</div>
                        <div style="color: #38bdf8; font-size: 1.5rem; font-weight: 700;">+{d_kw:.1f} kW</div>
                        <div style="color: #64748b; font-size: 0.75rem;">Clean solar power delivered</div>
                    </div>
                    <div>
                        <div style="color: #94a3b8; font-size: 0.8rem;">EUCLIDEAN DISTANCE</div>
                        <div style="color: #facc15; font-size: 1.5rem; font-weight: 700;">{dist:.2f}</div>
                        <div style="color: #64748b; font-size: 0.75rem;">Spatial line length</div>
                    </div>
                    <div>
                        <div style="color: #94a3b8; font-size: 0.8rem;">OPTIMIZATION SCORE</div>
                        <div style="color: #00f0ff; font-size: 1.5rem; font-weight: 700;">{score:.2f}</div>
                        <div style="color: #64748b; font-size: 0.75rem;">(ΔHomes × ΔkW) / dist</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_btn, _ = st.columns([4, 6])
            with col_btn:
                btn_connect = st.button(
                    f"⚡ Connect This Link: {src} ➔ {tgt}",
                    type="primary",
                    key="btn_connect_best",
                    help="Adds this directed transmission line to the microgrid, updates the Warshall reachability matrix, and renders in bright cyan."
                )
                if btn_connect:
                    st.session_state["ai_added_links"].add((src, tgt))
                    st.success(f"Connected {src} ➔ {tgt}! Microgrid recalculated.")
                    st.rerun()

        elif not has_left_out:
            if st.session_state["ai_added_links"]:
                st.success(
                    "🎉 **Outstanding! All Left-Out Households Have Been Connected by AI Optimization!**"
                )
                st.write(
                    f"The microgrid currently achieves **100% Solar Reachability**. "
                    f"Active AI lines ({', '.join([f'{u}➔{v}' for u, v in st.session_state['ai_added_links']])}) "
                    f"successfully route surplus power to all neighborhood consumers."
                )
            else:
                st.info(
                    "✅ **100% Reachability Already Achieved!** No households are currently cut off. "
                    "The candidate ranking below shows grid reinforcement lines that maximize multi-hop redundancy and mutual trading capacity."
                )

        st.markdown("---")
        # 3. Top Candidates Comparison Table
        st.subheader("📊 Candidate Link Comparison Table (Top Recommendations)")
        st.caption(
            "All candidate missing directed edges $(u, v) \\notin E$ evaluated via Warshall reachability deltas and Euclidean distance:"
        )

        top_df = opt_results["top_candidates_df"]
        if not top_df.empty:
            st.dataframe(top_df, use_container_width=True, hide_index=True)

            # Quick action to connect any of the top candidates
            st.markdown("##### 🔗 Connect Any Candidate Link Directly:")
            c_select, c_action = st.columns([6, 3], vertical_alignment="bottom")
            with c_select:
                candidate_opts = [
                    f"{c['source']} ➔ {c['target']} (Rank #{idx+1}: +{c['delta_powered_homes']} homes, +{c['delta_demand_kw']:.1f} kW, Score: {c['score']:.2f})"
                    for idx, c in enumerate(opt_results["top_candidates"][:5])
                ]
                selected_cand_str = st.selectbox("Select Candidate to Wire:", candidate_opts, key="cand_select_box")
                cand_idx = candidate_opts.index(selected_cand_str)
                chosen_candidate = opt_results["top_candidates"][cand_idx]
            with c_action:
                if st.button("⚡ Wire Selected Link", key="btn_wire_candidate", use_container_width=True):
                    st.session_state["ai_added_links"].add((chosen_candidate["source"], chosen_candidate["target"]))
                    st.session_state["trade_sim_results"] = None
                    st.success(f"Added link {chosen_candidate['source']} ➔ {chosen_candidate['target']}!")
                    st.rerun()


# =============================================================================
# TAB TRADE: P2P Energy Trading & Settlement (Prompt 5 Requirements)
# =============================================================================
with tab_trade:
    st.header("💰 Peer-to-Peer (P2P) Energy Trade Settlement & Loss Simulation")
    st.markdown(r"""
    <div class="math-callout">
        <b>Multi-Hop Transmission Dissipation Model</b><br>
        When energy travels across a directed path \(p = (v_0, v_1, \dots, v_k)\) composed of \(k\) hops:
        $$\text{Delivered Power} = \text{Sent Surplus} \times \prod_{i=1}^{k} \left(1 - \text{loss\_rate}_i\right)$$
        $$\text{Loss Penalty} = \text{Sent Surplus} - \text{Delivered Power} = \text{Sent Surplus} \times \left[1 - \prod_{i=1}^{k} (1 - \text{loss\_rate}_i)\right]$$
        <b>Topological Greedy Matching:</b> The settlement engine pairs surplus prosumers with reachable consumers ordered strictly by
        <b>shortest topological path length</b> (lowest \(k\)) to minimize line dissipation.
        Transfers spanning <b>more than 3 hops (\(k > 3\))</b> are flagged as inefficient feeders.
    </div>
    """, unsafe_allow_html=True)

    st.subheader("⚡ Settlement Engine Parameters & Simulation")
    col_sim_ctrl1, col_sim_ctrl2, col_sim_ctrl3 = st.columns([3.5, 3.5, 3], vertical_alignment="bottom")
    with col_sim_ctrl1:
        utility_rate = st.number_input(
            "Grid Utility Tariff ($/kWh):",
            min_value=0.01, max_value=1.00, value=0.12, step=0.01,
            help="Standard retail electricity cost (~ ₹10.00/kWh in Navi Mumbai/MSEDCL)"
        )
    with col_sim_ctrl2:
        p2p_rate = st.number_input(
            "P2P Microgrid Tariff ($/kWh):",
            min_value=0.01, max_value=1.00, value=0.06, step=0.01,
            help="Community solar trading rate (~ ₹5.00/kWh in Navi Mumbai)"
        )
    with col_sim_ctrl3:
        btn_simulate = st.button("🚀 Simulate Trade Cycle", type="primary", use_container_width=True, key="btn_run_trade_sim")

    # Execute trade simulation if button clicked or if not yet calculated
    if btn_simulate or st.session_state["trade_sim_results"] is None:
        st.session_state["trade_sim_results"] = simulate_p2p_trade_cycle(
            G=G,
            utility_rate_usd=utility_rate,
            p2p_rate_usd=p2p_rate
        )

    trade_res = st.session_state["trade_sim_results"]

    if trade_res:
        # Top Trade Settlement Summary KPI Cards
        st.markdown("---")
        st.subheader("📊 Trade Settlement Summary")

        t_col1, t_col2, t_col3, t_col4, t_col5 = st.columns(5)
        with t_col1:
            st.markdown(f"""
            <div class="metric-card-container">
                <div class="kpi-title">Total Power Dispatched</div>
                <div class="kpi-val">{trade_res['total_sent_kw']:.1f} <span style="font-size:1rem;color:#94a3b8;">kW</span></div>
                <div class="kpi-sub">Clean Solar Sent</div>
            </div>
            """, unsafe_allow_html=True)
        with t_col2:
            st.markdown(f"""
            <div class="metric-card-container">
                <div class="kpi-title">Power Delivered</div>
                <div class="kpi-val kpi-val-green">{trade_res['total_delivered_kw']:.1f} <span style="font-size:1rem;color:#34d399;">kW</span></div>
                <div class="kpi-sub">Served to Consumers</div>
            </div>
            """, unsafe_allow_html=True)
        with t_col3:
            loss_color = "#f87171" if trade_res['total_loss_kw'] > 0 else "#10b981"
            st.markdown(f"""
            <div class="metric-card-container">
                <div class="kpi-title">Transmission Losses</div>
                <div class="kpi-val" style="color: {loss_color};">{trade_res['total_loss_kw']:.2f} <span style="font-size:1rem;color:#94a3b8;">kW</span></div>
                <div class="kpi-sub">Ohmic Dissipation Penalty</div>
            </div>
            """, unsafe_allow_html=True)
        with t_col4:
            st.markdown(f"""
            <div class="metric-card-container">
                <div class="kpi-title">Grid Efficiency</div>
                <div class="kpi-val">{trade_res['grid_efficiency_pct']:.1f}%</div>
                <div class="kpi-sub">Delivered / Dispatched</div>
            </div>
            """, unsafe_allow_html=True)
        with t_col5:
            st.markdown(f"""
            <div class="metric-card-container">
                <div class="kpi-title">Simulated Cost Savings</div>
                <div class="kpi-val" style="color: #38bdf8;">${trade_res['total_savings_usd']:.2f}</div>
                <div class="kpi-sub">₹{trade_res['total_savings_inr']:.2f} (Navi Mumbai)</div>
            </div>
            """, unsafe_allow_html=True)

        # Highlight Inefficient Multi-Hop Transfers (> 3 hops)
        if trade_res["inefficient_transfers_count"] > 0:
            st.warning(
                f"⚠️ **Attention: {trade_res['inefficient_transfers_count']} Transaction(s) Exceed the 3-Hop Efficiency Threshold!** "
                f"Multi-hop routing over 4 or more intermediate lines incurs significant compounding ohmic dissipation losses. "
                f"Consider deploying direct feeder lines (see '💡 AI Line Optimization' tab) to reduce transmission penalties."
            )
        else:
            st.success("✅ **High Transmission Efficiency!** All power transfers resolved in 3 or fewer hops.")

        # P2P Transaction Ledger Table
        st.markdown("---")
        st.subheader("📑 P2P Transaction Ledger")
        st.caption("Detailed transaction audit matching solar surplus exporters to reachable consumer importers via shortest topological paths:")

        ledger_display_df = trade_res["ledger_df"]
        if not ledger_display_df.empty:
            st.dataframe(ledger_display_df, use_container_width=True, hide_index=True)
        else:
            st.info("No P2P trades could be settled. Either no solar surplus exists or all consumers are left-out.")

        # Interactive Multi-Hop Path & Loss Inspector
        if trade_res["transactions"]:
            st.markdown("---")
            st.subheader("🔍 Multi-Hop Path & Dissipation Inspector")
            txn_select_opts = [
                f"{t['Txn ID']}: {t['Exporter ID']} ➔ {t['Importer ID']} ({t['Hops']} hops, {t['Delivered (kW)']} kW delivered, {t['Efficiency (%)']}% eff)"
                for t in trade_res["transactions"]
            ]
            selected_txn_str = st.selectbox("Inspect Transaction Routing:", txn_select_opts, key="inspect_txn_select")
            sel_idx = txn_select_opts.index(selected_txn_str)
            sel_txn = trade_res["transactions"][sel_idx]

            # Re-fetch path loss details
            path_nodes = sel_txn["Routing Path"].split(" ➔ ")
            path_details = calculate_path_loss(G, path_nodes)

            insp_c1, insp_c2 = st.columns([6, 4])
            with insp_c1:
                st.markdown(f"**Routing Chain:** `{sel_txn['Routing Path']}`")
                st.markdown(f"- Topological Hops: **{path_details['hops']}**")
                st.markdown(f"- Cumulative Efficiency Multiplier $\\prod(1 - \\text{{loss}}_i)$: **{path_details['efficiency_multiplier']:.4f}**")
                st.markdown(f"- Total Path Dissipation: **{path_details['total_loss_pct']:.2f}%**")
                st.markdown(f"- Financial Benefit: **${sel_txn['Cost Savings ($)']} (₹{sel_txn['Cost Savings (₹)']})**")
            with insp_c2:
                hop_rows = []
                for h_idx in range(len(path_nodes) - 1):
                    u_h, v_h = path_nodes[h_idx], path_nodes[h_idx + 1]
                    e_loss = path_details["edge_losses"][h_idx]
                    hop_rows.append({
                        "Hop": f"Hop {h_idx + 1}",
                        "Feeder Line": f"{u_h} ➔ {v_h}",
                        "Line Loss Rate": f"{e_loss:.1f}%",
                        "Retention Multiplier": f"{1.0 - (e_loss / 100.0):.4f}"
                    })
                st.dataframe(pd.DataFrame(hop_rows), use_container_width=True, hide_index=True)


# =============================================================================
# TAB 3: Relation Properties (Prompt 3)
# =============================================================================
with tab3:
    st.header("📐 Discrete Mathematics: Binary Relations Analyzer")
    st.markdown(r"""
    Power transmission capability defines a **binary relation** \(R\) on the vertex set of households \(V\):
    $$(u, v) \in R \iff \text{Household } u \text{ can transfer excess power directly to Household } v.$$
    """)

    col_prop1, col_prop2, col_prop3 = st.columns(3)

    with col_prop1:
        st.markdown("#### 1. Reflexivity")
        if relation_properties["is_reflexive"]:
            st.markdown('<span class="status-badge-true">✓ Reflexive</span>', unsafe_allow_html=True)
            st.caption("∀x ∈ V, (x, x) ∈ R. Every home recirculates local battery power.")
        else:
            st.markdown('<span class="status-badge-false">✗ Irreflexive / Non-Reflexive</span>', unsafe_allow_html=True)
            st.caption("∀x ∈ V, (x, x) ∉ R. Transmission lines strictly connect distinct homes.")

    with col_prop2:
        st.markdown("#### 2. Symmetry")
        if relation_properties["is_symmetric"]:
            st.markdown('<span class="status-badge-true">✓ Symmetric</span>', unsafe_allow_html=True)
            st.caption("∀x, y ∈ V, (x, y) ∈ R ⇒ (y, x) ∈ R. All power lines are bidirectional.")
        else:
            st.markdown('<span class="status-badge-false">✗ Non-Symmetric</span>', unsafe_allow_html=True)
            st.caption(f"{len(relation_properties['symmetric_violations'])} directed one-way line(s) exist.")

    with col_prop3:
        st.markdown("#### 3. Transitivity")
        if relation_properties["is_transitive"]:
            st.markdown('<span class="status-badge-true">✓ Transitive</span>', unsafe_allow_html=True)
            st.caption("∀x, y, z, (x, y) ∈ R ∧ (y, z) ∈ R ⇒ (x, z) ∈ R.")
        else:
            st.markdown('<span class="status-badge-false">✗ Non-Transitive</span>', unsafe_allow_html=True)
            st.caption(f"Requires Warshall closure! {len(relation_properties['transitive_violations'])} multi-hop routing gap(s).")

    st.markdown("---")
    st.subheader("🔍 Mathematical Counterexample Diagnostics")

    col_viol1, col_viol2 = st.columns(2)
    with col_viol1:
        st.markdown("**Symmetry Violations (One-Way Feeders):**")
        if relation_properties["symmetric_violations"]:
            for u, v in relation_properties["symmetric_violations"][:6]:
                st.write(f"- `({u}, {v}) ∈ R`, but `({v}, {u}) ∉ R` (Inverter blocks reverse export).")
            if len(relation_properties["symmetric_violations"]) > 6:
                st.caption(f"...and {len(relation_properties['symmetric_violations']) - 6} more.")
        else:
            st.success("None! Power lines are 100% symmetric.")

    with col_viol2:
        st.markdown("**Transitivity Gaps (Multi-Hop Routes without Direct Line):**")
        if relation_properties["transitive_violations"]:
            for item in relation_properties["transitive_violations"][:5]:
                u, v, via = item["from"], item["to"], item["via"]
                st.write(f"- Path `{u}` ➔ `{via[0]}` ➔ `{v}` exists, but direct feeder `({u}, {v}) ∉ R`.")
            if len(relation_properties["transitive_violations"]) > 5:
                st.caption(f"...and {len(relation_properties['transitive_violations']) - 5} more.")
        else:
            st.success("None! The relation is already transitively closed.")

    st.markdown("---")
    st.subheader("✨ Relation Closures Comparison")
    st.markdown(r"""
    - **Reflexive Closure \(R \cup \Delta\)**: Adds self-loops \((x, x)\) (Self-consumption & storage loop).
    - **Symmetric Closure \(R \cup R^{-1}\)**: Upgrades all lines to bidirectional smart meter lines.
    - **Transitive Closure \(R^+\)**: Full reachability routing capability computed via Warshall's Algorithm.
    """)

    c_cl1, c_cl2, c_cl3 = st.columns(3)
    with c_cl1:
        st.markdown(r"##### Reflexive Closure $R \cup \Delta$")
        fig_ref = plot_matrix_heatmap(relation_properties["reflexive_closure"], node_labels, "Reflexive Closure", "#0d9488")
        st.plotly_chart(fig_ref, use_container_width=True)
    with c_cl2:
        st.markdown(r"##### Symmetric Closure $R \cup R^{-1}$")
        fig_sym = plot_matrix_heatmap(relation_properties["symmetric_closure"], node_labels, "Symmetric Closure", "#10b981")
        st.plotly_chart(fig_sym, use_container_width=True)
    with c_cl3:
        st.markdown(r"##### Transitive Closure $R^+$")
        fig_trans = plot_matrix_heatmap(relation_properties["transitive_closure"], node_labels, "Transitive Closure", "#0284c7")
        st.plotly_chart(fig_trans, use_container_width=True)


# =============================================================================
# TAB 4: Algorithm Stepper & Strongly Connected Components
# =============================================================================
with tab4:
    st.header("🔬 Warshall Algorithm Stepper & Component Analysis")

    st.subheader("Interactive Step-by-Step Warshall Algorithm Stepper")
    total_steps = len(warshall_steps) - 1
    selected_step = st.slider(
        "Iteration Step k (0 = Initial Adjacency W^(0), n = Transitive Closure R+):",
        min_value=0, max_value=total_steps, value=0, step=1
    )

    current_step_data = warshall_steps[selected_step]
    step_col1, step_col2 = st.columns([5, 5])
    with step_col1:
        fig_step = plot_matrix_heatmap(
            current_step_data["matrix"],
            node_labels,
            f"Step {selected_step}: Pivot {current_step_data['pivot_label']}",
            "#0284c7"
        )
        st.plotly_chart(fig_step, use_container_width=True)
    with step_col2:
        st.info(current_step_data["formula_note"])
        if current_step_data["newly_reachable"]:
            st.success(f"**🎉 {len(current_step_data['newly_reachable'])} New Reachability Route(s) Unlocked!**")
            new_routes_formatted = [
                f"`{src}` ➔ `[{current_step_data['pivot_label']}]` ➔ `{tgt}`"
                for src, tgt in current_step_data["newly_reachable"]
            ]
            st.write(", ".join(new_routes_formatted))
        elif selected_step > 0:
            st.write(f"No new multi-hop reachability pairs added via pivot `{current_step_data['pivot_label']}`.")

    st.markdown("---")
    st.subheader("🔄 Strongly & Weakly Connected Components")
    scc_c1, scc_c2 = st.columns(2)
    with scc_c1:
        st.markdown(f"**Strongly Connected Components (SCC):** `{connectivity_analysis['scc_count']}`")
        st.dataframe(connectivity_analysis["scc_df"], use_container_width=True, hide_index=True)
    with scc_c2:
        st.markdown(f"**Weakly Connected Components (WCC Islands):** `{connectivity_analysis['wcc_count']}`")
        st.dataframe(connectivity_analysis["wcc_df"], use_container_width=True, hide_index=True)


# =============================================================================
# TAB 5: Custom Matrix Studio & Executive Reports (Prompt 5 Requirements)
# =============================================================================
with tab5:
    st.header("🛠️ Custom Matrix Studio & Executive Reporting")

    col_custom_1, col_custom_2 = st.columns([5, 5])
    with col_custom_1:
        st.subheader("Interactive Adjacency Matrix Studio")
        st.caption("Define or edit your own microgrid adjacency matrix in CSV format:")
        new_csv_input = st.text_area(
            "Square 0/1 Matrix (rows = source, columns = target):",
            value=st.session_state["custom_csv"],
            height=180
        )
        col_c_btn1, col_c_btn2 = st.columns(2)
        with col_c_btn1:
            if st.button("🚀 Apply Custom Matrix", type="primary", use_container_width=True):
                try:
                    test_G, _ = parse_custom_matrix(new_csv_input)
                    st.session_state["custom_csv"] = new_csv_input
                    st.session_state["edge_overrides"] = {}
                    st.session_state["solar_overrides"] = {}
                    st.session_state["ai_added_links"] = set()
                    st.session_state["trade_sim_results"] = None
                    st.success("Custom matrix successfully applied!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Matrix parsing error: {e}")
        with col_c_btn2:
            if st.button("Load 4-Node Ring Sample", use_container_width=True):
                st.session_state["custom_csv"] = """0, 1, 0, 0
0, 0, 1, 0
0, 0, 0, 1
1, 0, 0, 0"""
                st.session_state["edge_overrides"] = {}
                st.session_state["solar_overrides"] = {}
                st.session_state["ai_added_links"] = set()
                st.session_state["trade_sim_results"] = None
                st.rerun()

    with col_custom_2:
        st.subheader("📑 Quick Matrix Downloads")
        adj_df = pd.DataFrame(adj_matrix.astype(int), index=node_labels, columns=node_labels)
        reach_df = pd.DataFrame(transitive_closure_matrix.astype(int), index=node_labels, columns=node_labels)

        st.download_button(
            "📥 Adjacency Matrix (CSV)",
            data=adj_df.to_csv(),
            file_name="microgrid_adjacency_matrix.csv",
            mime="text/csv",
            use_container_width=True
        )
        st.download_button(
            "📥 Transitive Closure Matrix (CSV)",
            data=reach_df.to_csv(),
            file_name="microgrid_transitive_closure_matrix.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.markdown("---")
    # Section 3 requirement: Executive Microgrid Summary Export
    st.subheader("📋 Executive Microgrid Summary Export (Complete Audit Package)")
    st.caption(
        "Export a consolidated executive report containing Microgrid Reachability Metrics, "
        "Left-Out Households Audit, Warshall Transitive Closure Matrix, AI Infrastructure Expansion Plan, "
        "and P2P Energy Trade Settlement Ledger:"
    )

    # Generate consolidated executive report string
    executive_report_csv = generate_executive_report_bundle(
        G=G,
        coverage_data=coverage_analysis,
        microgrid_metrics=microgrid_metrics,
        transitive_closure_matrix=transitive_closure_matrix,
        node_labels=node_labels,
        optimization_results=opt_results,
        trade_results=st.session_state.get("trade_sim_results")
    )

    exp_col1, exp_col2, exp_col3 = st.columns([4, 3, 3], vertical_alignment="bottom")
    with exp_col1:
        st.download_button(
            "📥 Download Complete Executive Report (CSV)",
            data=executive_report_csv,
            file_name=f"executive_microgrid_report_{meta['name'].replace(' ', '_').lower()}.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True,
            help="Contains complete audit: KPIs, Left-Out Homes, Warshall Matrix, Expansion Plan, and Trade Ledger"
        )
    with exp_col2:
        if not coverage_analysis["left_out_df"].empty:
            st.download_button(
                "📥 Left-Out Households Audit (CSV)",
                data=coverage_analysis["left_out_df"].to_csv(index=False),
                file_name="left_out_households_audit.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.button("✅ Left-Out Audit: 100% Inclusivity", disabled=True, use_container_width=True)
    with exp_col3:
        trade_cache = st.session_state.get("trade_sim_results")
        if trade_cache and not trade_cache["ledger_df"].empty:
            st.download_button(
                "📥 P2P Transaction Ledger (CSV)",
                data=trade_cache["ledger_df"].to_csv(index=False),
                file_name="p2p_trade_settlement_ledger.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.button("⚠️ P2P Ledger: Run Trade Sim First", disabled=True, use_container_width=True)

    # Report Preview Collapsible
    with st.expander("👁️ Preview Consolidated Executive Report Text", expanded=False):
        st.code(executive_report_csv, language="csv")


# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #64748b; font-size: 0.85rem;'>"
    "⚡ Solar Share Grid Engine • Discrete Mathematics & Graph Theory Microgrid Simulator • Built with Python & Streamlit"
    "</div>",
    unsafe_allow_html=True
)
