"""
closure_engine.py
=================
Core Discrete Mathematics Module for Solar Share Grid.

Implements:
1. Warshall's Algorithm from scratch using NumPy boolean matrices to compute
   the Transitive Closure R+ (Reachability Matrix):
   R^(k)[i,j] = R^(k-1)[i,j] OR (R^(k-1)[i,k] AND R^(k-1)[k,j])
2. Step-by-step recording of intermediate matrices W^(0) -> W^(n) for pedagogical display.
3. Binary relation properties analyzer (Reflexive, Irreflexive, Symmetric,
   Anti-symmetric, Asymmetric, Transitive, Equivalence Relation, Poset, DAG)
   with precise counterexamples.
4. Closures: Reflexive closure (R union Delta), Symmetric closure (R union R^-1),
   and Transitive closure (R^+).
"""

from typing import Dict, List, Tuple, Any, Optional, Union
import numpy as np
import networkx as nx


def compute_transitive_closure(
    adj_matrix: Union[np.ndarray, List[List[Union[int, bool]]]],
    node_labels: Optional[List[str]] = None,
    return_steps: bool = False
) -> Union[Tuple[np.ndarray, Dict[str, List[str]]], Tuple[np.ndarray, Dict[str, List[str]], List[Dict[str, Any]]]]:
    """
    Computes the Transitive Closure R+ (Reachability Matrix) of a directed graph
    using Warshall's Algorithm from scratch with boolean matrices.

    Recurrence relation:
        R^(k)[i, j] = R^(k-1)[i, j] OR (R^(k-1)[i, k] AND R^(k-1)[k, j])

    Parameters
    ----------
    adj_matrix : np.ndarray or list of lists
        Adjacency matrix of the directed graph (n x n).
    node_labels : list of str, optional
        Names/IDs corresponding to rows and columns. Defaults to ['0', '1', ..., 'n-1'].
    return_steps : bool, default=False
        If True, returns a list of step dictionaries detailing the intermediate
        state at each pivot k for pedagogical visualization.

    Returns
    -------
    reachability_matrix : np.ndarray of bool
        Boolean n x n reachability matrix R+.
    reachability_map : dict
        Mapping from each node label to the list of downstream node labels it can reach.
    steps : list of dict (only if return_steps is True)
        Step-by-step history:
        - 'step': int (0 to n)
        - 'pivot_index': int or None (for step 0)
        - 'pivot_label': str or None
        - 'matrix': np.ndarray (bool copy)
        - 'newly_reachable': list of tuple (source_label, target_label)
        - 'formula_note': explanation string
    """
    arr = np.array(adj_matrix, dtype=bool)
    if arr.ndim != 2 or arr.shape[0] != arr.shape[1]:
        raise ValueError(f"Adjacency matrix must be square (n x n), got shape {arr.shape}.")

    n = arr.shape[0]
    if node_labels is None:
        labels = [str(i) for i in range(n)]
    else:
        if len(node_labels) != n:
            raise ValueError(f"Length of node_labels ({len(node_labels)}) must match matrix dimension ({n}).")
        labels = list(node_labels)

    # Initial state W^(0) is a copy of the input adjacency matrix
    R = arr.copy()

    steps: List[Dict[str, Any]] = []
    if return_steps:
        steps.append({
            "step": 0,
            "pivot_index": None,
            "pivot_label": None,
            "matrix": R.copy(),
            "newly_reachable": [],
            "formula_note": "Initial Adjacency Matrix W^(0) = Direct Connections."
        })

    # Warshall's Algorithm: Outer loop iterates over each pivot node k (0 to n-1)
    for k in range(n):
        R_prev = R.copy()
        pivot_label = labels[k]

        # Vectorized outer boolean product:
        # Col k indicates which nodes i can reach k: shape (n, 1)
        # Row k indicates which nodes j can be reached from k: shape (1, n)
        # Through-k path exists if R[i, k] == True and R[k, j] == True
        col_k = R_prev[:, k : k + 1]  # shape (n, 1)
        row_k = R_prev[k : k + 1, :]  # shape (1, n)
        through_k = col_k & row_k     # shape (n, n) boolean broadcasting

        # Update step: R^(k)[i, j] = R^(k-1)[i, j] OR (R^(k-1)[i, k] AND R^(k-1)[k, j])
        R = R_prev | through_k

        if return_steps:
            # Detect which pairs became reachable in this exact iteration
            new_mask = R & (~R_prev)
            new_pairs_idx = np.argwhere(new_mask)
            newly_reachable = [(labels[i], labels[j]) for i, j in new_pairs_idx]

            steps.append({
                "step": k + 1,
                "pivot_index": k,
                "pivot_label": pivot_label,
                "matrix": R.copy(),
                "newly_reachable": newly_reachable,
                "formula_note": (
                    f"Pivot node {pivot_label} (k={k}): checked paths i -> {pivot_label} -> j. "
                    f"Added {len(newly_reachable)} new reachability link(s)."
                )
            })

    # Build downstream reachability dictionary
    reachability_map: Dict[str, List[str]] = {}
    for i in range(n):
        src_label = labels[i]
        # Nodes j where R[i, j] is True
        reachable_targets = [labels[j] for j in range(n) if R[i, j]]
        reachability_map[src_label] = reachable_targets

    if return_steps:
        return R, reachability_map, steps
    return R, reachability_map


def extract_binary_relations(
    graph_or_adj: Union[nx.DiGraph, np.ndarray, List[List[Union[int, bool]]]],
    node_labels: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Extracts and evaluates the mathematical properties of the binary relation R
    defined by the directed graph edges on the set of nodes V:
        (u, v) in R <=> u can send power to v.

    Evaluates:
    - Reflexivity: forall x, (x, x) in R
    - Irreflexivity: forall x, (x, x) not in R
    - Symmetry: forall x, y, (x, y) in R => (y, x) in R
    - Anti-symmetry: forall x != y, (x, y) in R => (y, x) not in R
    - Asymmetry: forall x, y, (x, y) in R => (y, x) not in R (implies irreflexive and anti-symmetric)
    - Transitivity: forall x, y, z, ((x, y) in R and (y, z) in R) => (x, z) in R
    - Higher classifications:
      * Equivalence Relation: Reflexive, Symmetric, and Transitive
      * Partial Order (Poset): Reflexive, Anti-symmetric, and Transitive
      * Strict Partial Order: Irreflexive, Asymmetric, and Transitive
      * Directed Acyclic Graph (DAG)

    Also computes closures:
    - Reflexive Closure: R union Delta
    - Symmetric Closure: R union R^(-1)
    - Transitive Closure: R^+ (via Warshall)

    Returns
    -------
    dict containing boolean flags, detailed explanations, counterexamples,
    and closure matrices.
    """
    if isinstance(graph_or_adj, nx.DiGraph):
        nodes = list(graph_or_adj.nodes())
        labels = nodes
        n = len(nodes)
        node_to_idx = {node: i for i, node in enumerate(nodes)}
        R = np.zeros((n, n), dtype=bool)
        for u, v in graph_or_adj.edges():
            R[node_to_idx[u], node_to_idx[v]] = True
    else:
        R = np.array(graph_or_adj, dtype=bool)
        n = R.shape[0]
        if node_labels is None:
            labels = [f"HOME_{i+1:02d}" for i in range(n)]
        else:
            labels = list(node_labels)

    # 1. Reflexivity: diagonal elements must all be True
    diag = np.diag(R)
    is_reflexive = bool(np.all(diag))
    is_irreflexive = bool(not np.any(diag))
    reflexive_violations = [labels[i] for i in range(n) if not R[i, i]]
    irreflexive_violations = [labels[i] for i in range(n) if R[i, i]]

    # 2. Symmetry: R == R.T
    R_transpose = R.T
    is_symmetric = bool(np.array_equal(R, R_transpose))
    symmetric_violations = []
    for i in range(n):
        for j in range(n):
            if R[i, j] and not R[j, i]:
                symmetric_violations.append((labels[i], labels[j]))

    # 3. Anti-symmetry: If (x, y) in R and (y, x) in R, then x == y.
    # Off-diagonal elements cannot both be True.
    off_diag_sym = (R & R_transpose)
    np.fill_diagonal(off_diag_sym, False)
    is_antisymmetric = bool(not np.any(off_diag_sym))
    antisymmetric_violations = []
    visited_pairs = set()
    for i in range(n):
        for j in range(n):
            if i != j and off_diag_sym[i, j]:
                pair_key = tuple(sorted([labels[i], labels[j]]))
                if pair_key not in visited_pairs:
                    visited_pairs.add(pair_key)
                    antisymmetric_violations.append((labels[i], labels[j]))

    # 4. Asymmetry: (x, y) in R => (y, x) not in R for all x, y (including x==y)
    is_asymmetric = bool(is_irreflexive and is_antisymmetric)

    # 5. Transitivity: R^2 subseteq R
    # (R compose R)[i, j] = OR_k (R[i, k] AND R[k, j])
    R_composed = (R[:, :, None] & R[None, :, :]).any(axis=1)  # shape (n, n)
    # Violation occurs when R_composed is True but R is False
    transitive_violations_mask = R_composed & (~R)
    is_transitive = bool(not np.any(transitive_violations_mask))
    transitive_violations = []
    for i in range(n):
        for j in range(n):
            if transitive_violations_mask[i, j]:
                # Find intermediate nodes k such that i->k and k->j
                intermediates = [labels[k] for k in range(n) if R[i, k] and R[k, j]]
                transitive_violations.append({
                    "from": labels[i],
                    "to": labels[j],
                    "via": intermediates
                })

    # Closures
    # Reflexive closure: R | I
    reflexive_closure = R.copy()
    np.fill_diagonal(reflexive_closure, True)

    # Symmetric closure: R | R^T
    symmetric_closure = R | R_transpose

    # Transitive closure: R^+ (via Warshall)
    transitive_closure, reachability_dict = compute_transitive_closure(R, node_labels=labels)

    # Equivalence and Order Classifications
    is_equivalence_relation = is_reflexive and is_symmetric and is_transitive
    is_partial_order = is_reflexive and is_antisymmetric and is_transitive
    is_strict_partial_order = is_irreflexive and is_asymmetric and is_transitive

    # Check for Directed Acyclic Graph (DAG)
    # A graph is a DAG iff its transitive closure has no diagonal elements (cycles).
    # Specifically, self-reachability R^+[i, i] == True implies a directed cycle exists.
    has_cycles = bool(np.any(np.diag(transitive_closure)))
    is_dag = not has_cycles

    # Calculate graph connectivity metrics
    total_possible_edges = n * (n - 1) if n > 1 else 1
    actual_edges = int(np.sum(R) - np.sum(diag))
    density = float(actual_edges / total_possible_edges) if total_possible_edges > 0 else 0.0

    return {
        "node_labels": labels,
        "n_nodes": n,
        "edge_count": actual_edges,
        "density": density,
        "matrix": R,
        # Reflexive
        "is_reflexive": is_reflexive,
        "reflexive_violations": reflexive_violations,
        "is_irreflexive": is_irreflexive,
        "irreflexive_violations": irreflexive_violations,
        # Symmetric
        "is_symmetric": is_symmetric,
        "symmetric_violations": symmetric_violations,
        # Anti-symmetric & Asymmetric
        "is_antisymmetric": is_antisymmetric,
        "antisymmetric_violations": antisymmetric_violations,
        "is_asymmetric": is_asymmetric,
        # Transitive
        "is_transitive": is_transitive,
        "transitive_violations": transitive_violations,
        # Higher types
        "is_equivalence_relation": is_equivalence_relation,
        "is_partial_order": is_partial_order,
        "is_strict_partial_order": is_strict_partial_order,
        "is_dag": is_dag,
        "has_cycles": has_cycles,
        # Closures
        "reflexive_closure": reflexive_closure,
        "symmetric_closure": symmetric_closure,
        "transitive_closure": transitive_closure,
        "reachability_dict": reachability_dict,
    }


def find_power_trading_paths(
    reachability_matrix: np.ndarray,
    node_labels: List[str],
    source_home: str
) -> Dict[str, Any]:
    """
    Given a reachability matrix R+ and a source solar home, returns:
    - directly reachable homes
    - indirectly reachable homes (multi-hop)
    - unreachable homes (blackout / cutoff)
    """
    if source_home not in node_labels:
        raise ValueError(f"Home '{source_home}' not found in node labels.")

    idx = node_labels.index(source_home)
    n = len(node_labels)

    reachable_indices = [j for j in range(n) if reachability_matrix[idx, j] and j != idx]
    unreachable_indices = [j for j in range(n) if not reachability_matrix[idx, j] and j != idx]

    return {
        "source": source_home,
        "reachable_homes": [node_labels[j] for j in reachable_indices],
        "unreachable_homes": [node_labels[j] for j in unreachable_indices],
        "can_self_power": bool(reachability_matrix[idx, idx]),
        "reachability_percentage": float(len(reachable_indices) / (n - 1) * 100.0) if n > 1 else 100.0
    }
