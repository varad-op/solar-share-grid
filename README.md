# ⚡ Solar Share Grid (Core Graph Theory & Discrete Mathematics Engine)

Peer-to-peer (P2P) rooftop solar energy trading simulator modeled using **Directed Graphs (Digraphs)** and **Binary Relations**.

Built with **Python 3.10+**, **Streamlit**, **NetworkX**, **NumPy**, **Pandas**, and **Plotly**.

---

## 🌟 Overview & Mathematical Model

In a distributed neighborhood microgrid, physical power lines and smart inverter policies define power transfer feasibility between households. This is mathematically modeled as a **Directed Graph** $D = (V, E)$ where:
- Each vertex $v \in V$ represents a **Household**.
- Each directed edge $(u, v) \in E$ indicates that Household $u$ can transfer surplus solar electricity to Household $v$.

### Node Attributes ($V$)
- `home_id` (`str`): Unique identifier (e.g. `'HOME_01'`)
- `owner_name` (`str`): Household/resident name
- `solar_surplus_kw` (`float`): Excess PV solar generation ($kW \ge 0$; $0$ if net consumer)
- `demand_kw` (`float`): Local household power consumption demand ($kW \ge 0$)
- `battery_storage_kwh` (`float`): Local electrochemical battery storage capacity ($kWh$)
- `pos` (`tuple`): Spatial coordinate $(x, y)$ for neighborhood wiring mapping
- `net_balance_kw` (`float`): Derived $\text{Surplus} - \text{Demand}$ ($> 0$ indicates net producer)

### Edge Attributes ($E$)
- `source`, `target` (`str`): Feeder from node $u$ to node $v$
- `transfer_capacity_kw` (`float`): Maximum physical throughput limit of the line
- `is_bidirectional` (`bool`): `True` if bidirectional smart meters allow two-way trading; `False` if restricted to one direction
- `line_loss_pct` (`float`): Ohmic resistance dissipation loss per hop (e.g., $2.0\%$)

---

## 🔁 Warshall's Algorithm from Scratch (`closure_engine.py`)

Computes the **Transitive Closure** $R^+$ (Reachability Matrix) via boolean matrix recurrence without high-level library shortcuts:

$$R^{(k)}[i,j] = R^{(k-1)}[i,j] \lor \left(R^{(k-1)}[i,k] \land R^{(k-1)}[k,j]\right)$$

For each intermediate vertex $k \in \{1, \dots, n\}$:
- A multi-hop trading path exists from $i$ to $j$ if there was already a path ($R^{(k-1)}[i, j] = 1$), OR if $i$ can reach $k$ AND $k$ can reach $j$.
- Tracks intermediate matrices $W^{(0)}, W^{(1)}, \dots, W^{(n)}$ for step-by-step visual exploration.

---

## 📐 Binary Relations Inspector (`closure_engine.py`)

Evaluates the formal discrete math properties of the relation $R \subseteq V \times V$:
- **Reflexivity**: $\forall x \in V, (x, x) \in R$ (Self-consumption & storage recirculation)
- **Irreflexivity**: $\forall x \in V, (x, x) \notin R$ (Inter-home physical wiring)
- **Symmetry**: $\forall x, y \in V, (x, y) \in R \implies (y, x) \in R$ (Bidirectional smart metering)
- **Anti-symmetry**: $\forall x \neq y, (x, y) \in R \implies (y, x) \notin R$ (Strictly unidirectional flow)
- **Transitivity**: $\forall x, y, z \in V, (x, y) \in R \land (y, z) \in R \implies (x, z) \in R$
- **High-Order Classifications**:
  - Equivalence Relations
  - Partial Orders (Posets)
  - Strict Directed Acyclic Graphs (DAGs)
- **Closures**:
  - Reflexive Closure: $R \cup \Delta$
  - Symmetric Closure: $R \cup R^{-1}$
  - Transitive Closure: $R^+$

---

## 📊 Reachability & Coverage Analysis Engine (`reachability_analyzer.py`)

Module 2 provides analytical evaluation of the microgrid's energy sharing capability based on the Transitive Closure $R^+$:

### 1. Producer Reachability Sets $Reach(v)$
For each household $v \in V$ with solar surplus ($\text{surplus}(v) > 0$):
$$\text{Reach}(v) = \{u \in V \mid R^+[v, u] = 1, u \neq v\}$$
Tracks direct line targets, multi-hop indirect targets, reachable consumers, and total reachable downstream demand (kW).

### 2. Consumer Solar Power Availability & "Left-Out" Detection
For each consumer $c \in V$ ($\text{demand}(c) > 0$):
- **Available Solar Power**:
  $$\text{Available Solar}(c) = \sum_{u \in \text{Reach}^{-1}(c), \text{surplus}(u) > 0} \text{surplus}(u)$$
- **Left-Out Households**:
  Households with power demand that have **no incoming directed path from any solar producer**:
  $$\text{Reach}^{-1}(v) \cap \{u \in V \mid \text{surplus}(u) > 0\} = \emptyset$$

### 3. Microgrid KPI Metrics
- **Solar Self-Sufficiency Index**:
  $$\text{Index} = \frac{\sum_{c \in \text{Consumers}} \min(\text{demand}(c), \text{Available Solar}(c))}{\text{Total Neighborhood Demand}} \times 100\%$$
- **Household Isolation Rate**:
  $$\text{Isolation Rate} = \frac{\text{Count of Left-Out Consumers}}{\text{Total Consumers}} \times 100\%$$
- **Topological Bottleneck Penalty**: Difference between theoretical unconstrained copper-plate potential and actual topologically reachable coverage.

### 4. Strongly & Weakly Connected Components (SCCs & WCCs)
- **Strongly Connected Components (SCCs)**: Subgraphs where every home can send power to every other home in the group.
  $$\text{Mutual Trading Equivalence Relation: } u \sim v \iff (R^+[u, v] = 1) \land (R^+[v, u] = 1)$$
  Identifies resilient, bidirectional closed-loop trading rings vs trivial singletons.
- **Weakly Connected Components (WCCs)**: Connected components ignoring line direction, identifying physically severed electrical islands.

---

## 🏡 Neighborhood Presets (Nerul & Navi Mumbai Edition)

1. **"Suburban Cul-de-Sac (Nerul Palm Beach)"**:
   - 10 homes: 3 solar producers (`Palm Beach Greens Villa`, `DY Patil Vidyanagar Solar Array`, `Nerul Gymkhana`) and 7 consumers (`Seawoods Estate`, `Sector 21 Shanti Niketan`, `Jewel of Navi Mumbai`, `Sarsole Lakeview`, `Wonders Park`, etc.).
   - Balanced mesh wiring with ring feeders and a central `Nerul MSEDCL Substation Hub` battery router.
2. **"Asymmetric Hillside (Parsik Hill to Belapur Slopes)"**:
   - 9 homes on the steep Parsik Hill slopes overlooking CBD Belapur and Nerul.
   - Strictly one-way downhill lines from hilltop villas (`Parsik Hilltop Villa East/West`, `Parsik Heights`) to valley commercial floors (`CBD Belapur Towers`, `Thane-Belapur Road Depot`) due to legacy step-down transformers.
   - Demonstrates a strict Directed Acyclic Graph (DAG) with asymmetry and non-transitivity.
3. **"Isolated Islands (Nerul West vs Seawoods East Creek Divide)"**:
   - 10 homes partitioned into two disconnected microgrids: Nerul West Sector (`DY Patil Medical`, `Sector 19A Solar Array`) and Seawoods East (`Seawoods Grand Central`, `NRI Complex`, `Karave Pumping Station`).
   - Simulates an open circuit breaker across the railway/creek divide, demonstrating reachability barriers.
4. **"Custom Matrix Studio (Mumbai Metro Grid)"**:
   - Parser for custom directed adjacency matrices via CSV or JSON.
   - Live matrix validation, interactive editing, sample presets (Nerul 4-node ring, Parsik cascade), and export capabilities.

---

## 💡 AI Line Optimization Engine (`link_optimizer.py`)

Module 4 solves the **Left-Out Household Problem** by determining the single optimal missing directed edge $(u, v) \notin E$ to add to the microgrid:

### Optimization Heuristic
1. Evaluates all non-existent directed edges $(u, v)$ with $u \neq v$.
2. For each candidate edge:
   - Evaluates reachability deltas via Warshall's Transitive Closure on $D' = D \cup \{(u, v)\}$:
     $$\Delta \text{Powered Homes} = \text{Newly Connected Homes in } D' - \text{Connected Homes in } D$$
     $$\Delta \text{Unmet Demand Served} = \text{kW Demand newly connected to solar generators}$$
   - Calculates the spatial line length $\text{dist}(u, v) = \sqrt{(x_u - x_v)^2 + (y_u - y_v)^2}$.
   - Computes Line Efficiency Score:
     $$\text{Score}(u, v) = \frac{\Delta \text{Powered Homes} \times \Delta \text{Unmet Demand Served (kW)}}{\text{dist}(u, v)}$$
3. Ranks candidates and selects the single optimal directed link $(u, v)$.
4. In the Streamlit UI, users can review the Top 3 Candidate comparison table and click **"⚡ Connect This Link"**, dynamically wiring the edge, recalculating reachability in real time, and rendering the newly added line as a bright cyan arrow (`#00f0ff`).

---

## 💰 P2P Trade Settlement & Multi-Hop Transmission Loss Model (`trade_simulator.py`)

Module 5 adds real-world energy trading physics, multi-hop dissipation modeling, and executive report export capabilities:

### 1. Multi-Hop Transmission Loss Model
When energy travels across a directed transmission path $p = (v_0, v_1, \dots, v_k)$ composed of $k$ hops:
$$\text{Delivered Power} = \text{Source Surplus} \times \prod_{i=1}^{k} \left(1 - \text{loss\_rate}_i\right)$$
$$\text{Loss Penalty} = \text{Sent Surplus} - \text{Delivered Power}$$

- Compounding Ohmic Resistance: Each physical power line imposes a distinct line loss percentage (default $2.0\%$).
- Inefficiency Warning: Transfers spanning **more than 3 hops ($k > 3$)** are explicitly flagged in the UI ledger and analytics as inefficient multi-hop feeders.

### 2. Greedy Shortest-Distance Trade Settlement Algorithm
- Matches surplus prosumers with reachable consumers ordered strictly by **shortest topological path length** ($k$ ascending), prioritizing nearest neighbors to minimize transmission dissipation.
- Generates a complete **P2P Transaction Ledger** detailing:
  - Exporter ID & Name, Importer ID & Name, Multi-Hop Routing Chain, Hop Count ($k$), Sent (kW), Delivered (kW), Loss (kW), Transmission Efficiency (%), Simulated Financial Cost Savings ($ and ₹), and Inefficient Status Flag.

### 3. Executive Microgrid Summary Export
Provides a single-click download for an executive-grade consolidated CSV report containing:
1. Executive Microgrid Summary & KPIs (Generation, Demand, Self-Sufficiency %, Isolation Rate, SCC count).
2. Left-Out Households Audit.
3. Warshall Transitive Closure Reachability Matrix ($R^+$).
4. Recommended Infrastructure Expansion Plan (from `link_optimizer.py`).
5. P2P Trade Settlement Transaction Ledger & Loss Analytics.

---

## 🚀 Running the Streamlit Web Application

To start the interactive webapp:

```bash
streamlit run app.py
```

### Running Automated Tests

Run the full test suite (30 unit tests across 4 modules):

```bash
python -m unittest discover tests -v
```
