"""Occupation Space + Job Space (propensity graph) computation.

Two networks over detailed (level 4) SOC occupations:

* **Occupation Space** -- Atlas Product Space / Metroverse Industry Space
  equivalent.  Occupations are related when they are co-specialised
  (RCA >= 1) in the same US metro areas (BLS OES employment).
  Also yields PCI (occupation complexity) and ECI (region complexity)
  via the method of reflections (Hidalgo & Hausmann 2009).

* **Job Space** -- task-based "propensity" graph from the Jobs & Tasks
  research (D:/Projects/JobsAndTasks).  Jobs are related when they share
  O*NET Detailed Work Activities (DWAs).  Also yields the wage-seeded
  Job Complexity Index (JCI) and Task Complexity Index (TCI).

Both use the min-conditional-probability proximity of Hidalgo et al. 2007:
    phi(a, b) = |S_a & S_b| / max(|S_a|, |S_b|)
and the same readable layout: maximum spanning tree backbone + top-k
neighbour edges, Kamada-Kawai layout, Louvain clusters, convex hulls.

Inputs come from the published JSON files (public/data/) and the O*NET
ZIP, so this module runs identically in the pipeline and in the Colab
notebook (notebooks/task-complexity-analysis/).

Usage:
    python scripts/pipeline/run_pipeline.py --year 2024 --country us --space
"""

import io
import json
import zipfile
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_oes_level4(data_dir: Path, country: str = "us", year: int = 2024):
    """Load level-4 OES employment + wages from the published JSON files.

    Returns dict with:
        occupations: {socCode: {name, majorGroupId, majorGroupName}}
        regions:     {regionId: {name, regionType}}
        emp:         {regionId: {socCode: totEmp}}
        wage:        {socCode: national aMean}
        national_id: regionId of the national region
    """
    files = [
        data_dir / f"bls-data-{country}-{year}-4.json",
        data_dir / f"bls-data-{country}-{year}-4-metro.json",
    ]
    occupations: dict = {}
    regions: dict = {}
    emp: dict = {}
    wage: dict = {}
    for path in files:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        for o in d["occupations"]:
            if o.get("level") == 4:
                occupations[o["socCode"]] = {
                    "name": o["name"],
                    "majorGroupId": o["majorGroupId"],
                    "majorGroupName": o["majorGroupName"],
                }
        for r in d["regions"]:
            regions[r["regionId"]] = {"name": r["name"],
                                      "regionType": r["regionType"]}
        for rid, by_year in d["regionData"].items():
            recs = by_year.get(str(year), [])
            target = emp.setdefault(rid, {})
            for rec in recs:
                target[rec["socCode"]] = rec["totEmp"]
    national_id = next(rid for rid, r in regions.items()
                       if r["regionType"] == "National")
    nat_file = files[0]
    with open(nat_file, encoding="utf-8") as f:
        d = json.load(f)
    for rec in d["regionData"][national_id][str(year)]:
        if rec["socCode"] in occupations and rec.get("aMean"):
            wage[rec["socCode"]] = rec["aMean"]
    return {
        "occupations": occupations,
        "regions": regions,
        "emp": emp,
        "wage": wage,
        "national_id": national_id,
    }


def load_onet_job_dwa(zip_path: Path):
    """Read O*NET 'Tasks to DWAs' and collapse O*NET-SOC to 6-digit SOC.

    Returns (pairs, dwa_titles):
        pairs:      set of (socCode, dwaId) -- union of DWAs across
                    O*NET-SOC detail codes (XX-XXXX.YY -> XX-XXXX)
        dwa_titles: {dwaId: title}
    """
    import openpyxl

    def read(name):
        with zipfile.ZipFile(zip_path) as zf:
            inner = next(n for n in zf.namelist() if n.endswith(name))
            wb = openpyxl.load_workbook(io.BytesIO(zf.read(inner)),
                                        read_only=True, data_only=True)
            rows = wb.active.iter_rows(values_only=True)
            headers = [str(h).strip() for h in next(rows)]
            out = [dict(zip(headers, r)) for r in rows]
            wb.close()
            return out

    pairs = set()
    titles = {}
    for row in read("Tasks to DWAs.xlsx"):
        code = str(row["O*NET-SOC Code"]).strip()
        dwa = str(row["DWA ID"]).strip()
        pairs.add((code[:7], dwa))
        titles[dwa] = str(row["DWA Title"]).strip()
    return pairs, titles


# ---------------------------------------------------------------------------
# Economic complexity primitives
# ---------------------------------------------------------------------------


def calc_rca(X: np.ndarray) -> np.ndarray:
    """Balassa RCA for a (locations x products) value matrix."""
    X = np.asarray(X, dtype=float)
    loc_tot = X.sum(axis=1, keepdims=True)
    prod_tot = X.sum(axis=0, keepdims=True)
    total = X.sum()
    with np.errstate(divide="ignore", invalid="ignore"):
        rca = (X / loc_tot) / (prod_tot / total)
    return np.nan_to_num(rca, nan=0.0, posinf=0.0)


def min_cond_proximity(M: np.ndarray) -> np.ndarray:
    """phi_ab = sum_c M_ca M_cb / max(k_a, k_b) for binary M (rows = sets).

    Columns of M are the nodes. Diagonal is set to 0.
    """
    M = np.asarray(M, dtype=float)
    co = M.T @ M
    k = np.diag(co).copy()
    denom = np.maximum.outer(k, k)
    with np.errstate(divide="ignore", invalid="ignore"):
        phi = np.where(denom > 0, co / denom, 0.0)
    np.fill_diagonal(phi, 0.0)
    return phi


def eci_pci(M: np.ndarray):
    """ECI/PCI via the eigenvector form of the method of reflections.

    M: binary (locations x products) with no all-zero rows/cols.
    Follows py-ecomplexity conventions: ECI sign chosen so ECI correlates
    positively with diversity; PCI sign so that ECI ~ mean PCI of a
    location's products; both z-scored with ECI's mean/std.
    """
    M = np.asarray(M, dtype=float)
    kc = M.sum(axis=1)
    kp = M.sum(axis=0)
    Mcc = (M / kc[:, None]) @ (M / kp[None, :]).T
    Mpp = (M.T / kp[:, None]) @ (M / kc[:, None])

    def second_eigvec(A):
        vals, vecs = np.linalg.eig(A)
        order = np.argsort(-vals.real)
        return vecs[:, order[1]].real

    eci = second_eigvec(Mcc)
    pci = second_eigvec(Mpp)
    if np.corrcoef(kc, eci)[0, 1] < 0:
        eci = -eci
    implied = (M @ pci) / kc
    if np.corrcoef(implied, eci)[0, 1] < 0:
        pci = -pci
    mu, sd = eci.mean(), eci.std()
    return (eci - mu) / sd, (pci - mu) / sd


def wage_seeded_jci(M: np.ndarray, wages: np.ndarray, n_iter: int = 20):
    """Job/Task Complexity Index from Jobs & Tasks research (Final.Rmd 4.1.3).

    M: binary (jobs x tasks).  wages: national mean annual wage per job.
        K_J,1 = w_J
        K_T,1 = D_T^-1 M' w_J                (average wage of jobs doing T)
        M~_JJ = D_J^-1 M D_T^-1 M'
        M~_TT = D_T^-1 M' D_J^-1 M
        JCI = M~_JJ^n K_J,1 ,  TCI = M~_TT^n K_T,1
    Each step averages over the bipartite neighbourhood, so values stay
    in dollars (always > 0) -- unlike the eigenvector solution, which can
    go negative.  Returns (jci, tci, history) where history[i] is the
    coefficient of variation of JCI after i iterations (for convergence
    plots).
    """
    M = np.asarray(M, dtype=float)
    nj = M.sum(axis=1)
    nt = M.sum(axis=0)
    A = M / nj[:, None]           # D_J^-1 M
    B = M.T / nt[:, None]         # D_T^-1 M'
    Mjj = A @ B
    Mtt = B @ A
    kj = np.asarray(wages, dtype=float)
    kt = B @ kj
    history = [kj.std() / kj.mean()]
    for _ in range(n_iter):
        kj = Mjj @ kj
        kt = Mtt @ kt
        history.append(kj.std() / kj.mean())
    return kj, kt, history


# ---------------------------------------------------------------------------
# Readable network: backbone, layout, clusters
# ---------------------------------------------------------------------------


def backbone(phi: np.ndarray, target_avg_degree: float = 4.0, max_k: int = 10):
    """Maximum spanning tree + each node's top-k strongest links.

    k is the smallest value giving average degree >= target.  Returns
    (edges, k, phi_cutoff) where edges is a sorted list of (i, j, phi)
    with i < j and phi_cutoff is the weakest phi among non-MST edges.
    """
    from scipy.sparse.csgraph import minimum_spanning_tree

    n = phi.shape[0]
    dist = np.where(phi > 0, 1.0 + 1e-9 - phi, 0.0)
    mst = minimum_spanning_tree(dist).tocoo()
    mst_edges = {(min(i, j), max(i, j)) for i, j in zip(mst.row, mst.col)}
    order = np.argsort(-phi, axis=1)

    chosen_k = max_k
    edges = set(mst_edges)
    for k in range(1, max_k + 1):
        cand = set(mst_edges)
        for i in range(n):
            for j in order[i, :k]:
                if phi[i, j] > 0:
                    cand.add((min(i, j), max(i, j)))
        if 2 * len(cand) / n >= target_avg_degree:
            chosen_k, edges = k, cand
            break
        edges = cand
    extra = [phi[i, j] for i, j in edges if (i, j) not in mst_edges]
    cutoff = float(min(extra)) if extra else 0.0
    out = sorted((i, j, float(phi[i, j])) for i, j in edges)
    return out, chosen_k, cutoff, mst_edges


def layout(n: int, edges, mst_edges, seed: int = 42, method: str = "kk_spring"):
    """Kamada-Kawai on the MST, refined by a force layout on the backbone.

    Mirrors Job-Task Assignment4.Rmd (layout_with_kk(gmst) then
    layout_with_kk(vizgraph, coords=...)).  method:
        "kk_spring" -- Fruchterman-Reingold refinement (default)
        "kk_fa2"    -- ForceAtlas2 (linlog) refinement; separates clusters
                       more but flings weakly-tied nodes outward
    Returns (n, 2) array scaled to [0, 1000] x [0, 750] (4:3, matching the
    renderer's aspect ratio).
    """
    import networkx as nx

    T = nx.Graph()
    T.add_nodes_from(range(n))
    T.add_edges_from(mst_edges)
    pos = nx.kamada_kawai_layout(T)
    G = nx.Graph()
    G.add_nodes_from(range(n))
    for i, j, w in edges:
        G.add_edge(i, j, weight=w)
    if method == "kk_fa2":
        pos = nx.forceatlas2_layout(G, pos=pos, weight="weight", max_iter=300,
                                    seed=seed, linlog=True, scaling_ratio=2.0,
                                    gravity=1.0)
    else:
        pos = nx.spring_layout(G, pos=pos, weight="weight", iterations=60,
                               k=1.2 / np.sqrt(n), seed=seed)
    xy = np.array([pos[i] for i in range(n)])
    # Pull the few far-flung nodes in so the dense core uses the canvas
    lo, hi = np.percentile(xy, 1, axis=0), np.percentile(xy, 99, axis=0)
    xy = np.clip(xy, lo, hi)
    xy -= xy.min(axis=0)
    span = xy.max(axis=0)
    span[span == 0] = 1
    xy = xy / span
    return np.column_stack([xy[:, 0] * 1000, xy[:, 1] * 750])


def _merge_small(G, communities, min_size: int):
    """Fold communities smaller than min_size into their most-linked neighbour."""
    comms = [set(c) for c in sorted(communities, key=len, reverse=True)]
    while True:
        small = [i for i, c in enumerate(comms) if len(c) < min_size]
        if not small or len(comms) == 1:
            return comms
        i = small[-1]
        label = {m: k for k, c in enumerate(comms) for m in c}
        weight: dict = {}
        for m in comms[i]:
            for nb, attrs in G[m].items():
                k = label[nb]
                if k != i:
                    weight[k] = weight.get(k, 0) + attrs.get("weight", 1)
        if not weight:          # isolated: attach to the largest community
            weight = {0 if i != 0 else 1: 1}
        target = max(weight, key=weight.get)
        comms[target] |= comms[i]
        del comms[i]
        comms.sort(key=len, reverse=True)


def clusters(n: int, edges, seed: int = 42, res_high: float = 0.6,
             res_low: float = 1.0, min_continent: int = 20):
    """Two-level Louvain communities on the backbone graph.

    Returns (continent_of, country_of) integer labels.  Countries are found
    within each continent's subgraph so the hierarchy nests.  Continents
    smaller than min_continent nodes are merged into the neighbour they
    share most link weight with, so high-level labels stay readable.
    """
    import networkx as nx

    G = nx.Graph()
    G.add_nodes_from(range(n))
    for i, j, w in edges:
        G.add_edge(i, j, weight=w)
    cont = nx.community.louvain_communities(G, weight="weight",
                                            resolution=res_high, seed=seed)
    cont = _merge_small(G, cont, min_continent)
    continent_of = np.zeros(n, dtype=int)
    country_of = np.zeros(n, dtype=int)
    next_country = 0
    for ci, members in enumerate(cont):
        for m in members:
            continent_of[m] = ci
        sub = G.subgraph(members)
        if sub.number_of_edges() == 0:
            parts = [set(members)]
        else:
            parts = nx.community.louvain_communities(
                sub, weight="weight", resolution=res_low, seed=seed)
        for part in sorted(parts, key=len, reverse=True):
            for m in part:
                country_of[m] = next_country
            next_country += 1
    return continent_of, country_of


def hull(points: np.ndarray, pad: float = 6.0):
    """Padded convex hull polygon for a set of 2-D points."""
    from scipy.spatial import ConvexHull, QhullError

    pts = np.asarray(points, dtype=float)
    # Ring of padding points around every node guarantees a valid hull
    angles = np.linspace(0, 2 * np.pi, 8, endpoint=False)
    ring = np.column_stack([np.cos(angles), np.sin(angles)]) * pad
    padded = (pts[:, None, :] + ring[None, :, :]).reshape(-1, 2)
    try:
        h = ConvexHull(padded)
        poly = padded[h.vertices]
    except QhullError:
        poly = padded
    return [[round(float(x), 1), round(float(y), 1)] for x, y in poly]


# ---------------------------------------------------------------------------
# Building the two spaces
# ---------------------------------------------------------------------------


def build_occupation_space(oes: dict, min_region_emp: int = 1000):
    """Metro x occupation RCA -> M -> phi, ECI/PCI.

    Uses Metro + Nonmetro areas (regionType 'Metro'/'Nonmetro'); BLS
    suppressed cells count as 0.  Returns dict with codes, phi, M, rca,
    eci (by region id), pci (by code), region_ids.
    """
    region_ids = sorted(rid for rid, r in oes["regions"].items()
                        if r["regionType"] in ("Metro", "Nonmetro"))
    codes = sorted(oes["occupations"])
    X = np.array([[oes["emp"].get(rid, {}).get(c, 0) for c in codes]
                  for rid in region_ids], dtype=float)
    keep_r = X.sum(axis=1) >= min_region_emp
    X = X[keep_r]
    region_ids = [r for r, k in zip(region_ids, keep_r) if k]
    rca = calc_rca(X)
    M = (rca >= 1).astype(float)
    keep_p = M.sum(axis=0) > 0
    keep_r2 = M.sum(axis=1) > 0
    M = M[keep_r2][:, keep_p]
    rca = rca[keep_r2][:, keep_p]
    codes = [c for c, k in zip(codes, keep_p) if k]
    region_ids = [r for r, k in zip(region_ids, keep_r2) if k]
    phi = min_cond_proximity(M)
    eci, pci = eci_pci(M)
    return {
        "codes": codes,
        "region_ids": region_ids,
        "M": M,
        "phi": phi,
        "eci": dict(zip(region_ids, eci.tolist())),
        "pci": dict(zip(codes, pci.tolist())),
        "diversity": dict(zip(region_ids, M.sum(axis=1).astype(int).tolist())),
        "ubiquity": dict(zip(codes, M.sum(axis=0).astype(int).tolist())),
    }


def build_job_space(oes: dict, pairs: set, n_iter: int = 20):
    """Job x DWA binary matrix -> phi (shared tasks), wage-seeded JCI/TCI.

    Jobs = level-4 SOC codes present in both OES (with a national wage)
    and O*NET.
    """
    jobs = sorted({j for j, _ in pairs}
                  & set(oes["occupations"]) & set(oes["wage"]))
    job_idx = {j: i for i, j in enumerate(jobs)}
    tasks = sorted({t for j, t in pairs if j in job_idx})
    task_idx = {t: i for i, t in enumerate(tasks)}
    M = np.zeros((len(jobs), len(tasks)))
    for j, t in pairs:
        if j in job_idx:
            M[job_idx[j], task_idx[t]] = 1.0
    wages = np.array([oes["wage"][j] for j in jobs], dtype=float)
    jci, tci, history = wage_seeded_jci(M, wages, n_iter=n_iter)
    phi = min_cond_proximity(M.T)   # columns = jobs
    return {
        "codes": jobs,
        "tasks": tasks,
        "M": M,
        "phi": phi,
        "wages": wages,
        "jci": dict(zip(jobs, jci.tolist())),
        "tci": dict(zip(tasks, tci.tolist())),
        "history": history,
    }


SHORT_GROUP_NAMES = {
    "Management": "Management",
    "Business and Financial Operations": "Business",
    "Computer and Mathematical": "Computing",
    "Architecture and Engineering": "Engineering",
    "Life, Physical, and Social Science": "Science",
    "Community and Social Service": "Social Service",
    "Legal": "Legal",
    "Educational Instruction and Library": "Education",
    "Arts, Design, Entertainment, Sports, and Media": "Arts & Media",
    "Healthcare Practitioners and Technical": "Health Care",
    "Healthcare Support": "Health Support",
    "Protective Service": "Protective Service",
    "Food Preparation and Serving Related": "Food Service",
    "Building and Grounds Cleaning and Maintenance": "Building Upkeep",
    "Personal Care and Service": "Personal Care",
    "Sales and Related": "Sales",
    "Office and Administrative Support": "Office",
    "Farming, Fishing, and Forestry": "Farming",
    "Construction and Extraction": "Construction",
    "Installation, Maintenance, and Repair": "Repair",
    "Production": "Production",
    "Transportation and Material Moving": "Transportation",
}


def _cluster_names(labels, codes, occupations, nat_emp):
    """Return {label: (group label, largest occupation name)}.

    The group label is the most common SOC major group among the cluster's
    occupations (short form), or the top two joined with "&" when no
    group holds a majority -- Occupation Space clusters often mix families.
    """
    names = {}
    for lab in sorted(set(labels.tolist())):
        idx = [i for i, l in enumerate(labels) if l == lab]
        by_group: dict = {}
        for i in idx:
            g = occupations[codes[i]]["majorGroupName"]
            by_group[g] = by_group.get(g, 0) + 1
        ranked = sorted(by_group, key=lambda g: -by_group[g])
        short = [SHORT_GROUP_NAMES.get(g, g) for g in ranked]
        if by_group[ranked[0]] / len(idx) >= 0.5 or len(ranked) == 1:
            group_label = short[0]
        else:
            group_label = f"{short[0]} / {short[1]}"
        top_occ = max(idx, key=lambda i: nat_emp.get(codes[i], 0))
        occ_name = occupations[codes[top_occ]]["name"]
        names[lab] = (group_label, occ_name)
    return names


def space_to_layout_json(space: dict, oes: dict, kind: str,
                         n_neighbors: int = 10, target_avg_degree: float = 4.0,
                         seed: int = 42):
    """Build the renderer JSON (nodes with x/y + clusters with polygons)."""
    codes = space["codes"]
    phi = space["phi"]
    n = len(codes)
    edges, k, cutoff, mst_edges = backbone(phi, target_avg_degree)
    xy = layout(n, edges, mst_edges, seed=seed)
    cont_of, country_of = clusters(n, edges, seed=seed)
    nat_emp = oes["emp"][oes["national_id"]]
    occ = oes["occupations"]

    cont_names = _cluster_names(cont_of, codes, occ, nat_emp)
    country_names = _cluster_names(country_of, codes, occ, nat_emp)

    # Short continent names; number them when a major group repeats
    group_counts: dict = {}
    for g, _ in cont_names.values():
        group_counts[g] = group_counts.get(g, 0) + 1
    group_seen: dict = {}
    continents = []
    for lab in sorted(cont_names):
        g, top = cont_names[lab]
        group_seen[g] = group_seen.get(g, 0) + 1
        name = g if group_counts[g] == 1 else f"{g} ({group_seen[g]})"
        idx = np.where(cont_of == lab)[0]
        continents.append({
            "clusterId": str(lab + 1),
            "clusterCode": int(lab),
            "name": name,
            "center": [round(float(v), 1) for v in xy[idx].mean(axis=0)],
            "polygon": hull(xy[idx], pad=10.0),
            "color": "#dfdfdf",
            "size": int(len(idx)),
        })
    countries = []
    for lab in sorted(country_names):
        _, top = country_names[lab]
        idx = np.where(country_of == lab)[0]
        countries.append({
            "clusterId": str(101 + lab),
            "clusterCode": int(lab),
            # Named after its largest occupation, trimmed for map labels
            "name": top.split(",")[0][:40],
            "continent": str(int(cont_of[idx[0]]) + 1),
            "center": [round(float(v), 1) for v in xy[idx].mean(axis=0)],
            "polygon": hull(xy[idx], pad=5.0),
            "color": "#cfcfcf",
            "size": int(len(idx)),
        })

    order = np.argsort(-phi, axis=1)
    links = [[codes[i], codes[j], round(w, 4)] for i, j, w in edges]
    nodes = []
    for i, c in enumerate(codes):
        nbrs = [j for j in order[i, :n_neighbors] if phi[i, j] > 0]
        nodes.append({
            "id": c,
            "x": round(float(xy[i, 0]), 2),
            "y": round(float(xy[i, 1]), 2),
            "continent": str(int(cont_of[i]) + 1),
            "country": str(101 + int(country_of[i])),
            "edges": [{"trg": codes[j], "proximity": round(float(phi[i, j]), 4)}
                      for j in nbrs],
        })

    degrees = 2 * len(edges) / n
    return {
        "kind": kind,
        "nodes": nodes,
        "links": links,
        "clusters": {"continents": continents, "countries": countries},
        "stats": {
            "nNodes": n,
            "nLinks": len(edges),
            "avgDegree": round(degrees, 2),
            "topK": int(k),
            "phiCutoff": round(cutoff, 4),
            "nContinents": len(continents),
            "nCountries": len(countries),
        },
    }


def _dump_like(data: dict, path: Path) -> None:
    """Rewrite a JSON file keeping its original formatting (indent or compact)."""
    with open(path, "rb") as f:
        head = f.read(3)
    indent = 2 if head[1:2] in (b"\n", b"\r") else None
    with open(path, "w", encoding="utf-8") as f:
        if indent:
            json.dump(data, f, indent=indent)
        else:
            json.dump(data, f, separators=(",", ":"))


def apply_complexity_to_json(data_dir: Path, complexity: dict,
                             country: str = "us", year: int = 2024):
    """Replace the GDP-placeholder `complexity` field with PCI-based scores.

    Level 4: PCI min-max scaled to [0, 1].  Levels 1-3: national
    employment-weighted mean of their level-4 descendants.  The value is
    an occupation property, so it is the same in every region.  Also
    refreshes aggregates[year].byOccupation[*].avgComplexity and the
    complexity entries of minMaxStats.  Returns number of files updated.
    """
    paths = sorted(data_dir.glob(f"bls-data-{country}-{year}*.json"))
    files = {}
    parent: dict = {}
    for p in paths:
        with open(p, encoding="utf-8") as f:
            files[p] = json.load(f)
        for o in files[p]["occupations"]:
            parent[o["socCode"]] = o.get("parentCode")

    pci = complexity["pci"]
    lo, hi = min(pci.values()), max(pci.values())
    score = {c: (v - lo) / (hi - lo) for c, v in pci.items()}

    nat = {}
    for d in files.values():
        for rid, by_year in d["regionData"].items():
            if rid.startswith("national-"):
                for rec in by_year.get(str(year), []):
                    nat[rec["socCode"]] = rec["totEmp"]
    sums: dict = {}
    for code, s in score.items():
        w = nat.get(code, 0) or 1
        anc = parent.get(code)
        seen = set()
        while anc and anc not in seen:
            seen.add(anc)
            acc = sums.setdefault(anc, [0.0, 0.0])
            acc[0] += s * w
            acc[1] += w
            anc = parent.get(anc)
    for code, (num, den) in sums.items():
        score.setdefault(code, num / den)
    score = {c: round(v, 4) for c, v in score.items()}

    for p, d in files.items():
        for by_year in d["regionData"].values():
            for rec in by_year.get(str(year), []):
                if rec["socCode"] in score:
                    rec["complexity"] = score[rec["socCode"]]
        agg = d.get("aggregates", {}).get(str(year))
        if agg:
            for code, a in agg["byOccupation"].items():
                if code in score:
                    a["avgComplexity"] = score[code]
            vals = sorted(a["avgComplexity"] for a in agg["byOccupation"].values())
            if vals and "minMaxStats" in agg:
                agg["minMaxStats"]["minComplexity"] = vals[0]
                agg["minMaxStats"]["maxComplexity"] = vals[-1]
                agg["minMaxStats"]["medianComplexity"] = vals[len(vals) // 2]
        if "metadata" in d:
            d["metadata"]["complexity"] = "PCI (occupation space, method of reflections)"
        _dump_like(d, p)
    return len(files)


def register_space_files(data_dir: Path, country: str = "us", year: int = 2024):
    """Add spaceFiles[country][year] to the bls-data.json meta catalog."""
    meta_path = data_dir / "bls-data.json"
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    meta.setdefault("spaceFiles", {}).setdefault(country, {})[str(year)] = {
        "occupation": f"space-{country}-{year}-occupation.json",
        "job": f"space-{country}-{year}-job.json",
        "complexity": f"complexity-{country}-{year}.json",
    }
    _dump_like(meta, meta_path)


def compute_all(data_dir: Path, onet_zip: Path, country: str = "us",
                year: int = 2024, out_dir: Path | None = None,
                seed: int = 42):
    """Compute both spaces + complexity and write the JSON outputs.

    Writes:
        space-{country}-{year}-occupation.json
        space-{country}-{year}-job.json
        complexity-{country}-{year}.json
    Returns dict of summary stats.
    """
    out_dir = out_dir or data_dir
    print("  Loading OES level-4 data...")
    oes = load_oes_level4(data_dir, country, year)
    print(f"    {len(oes['occupations'])} occupations, "
          f"{len(oes['regions'])} regions")

    print("  Occupation Space (metro co-specialisation)...")
    occ_space = build_occupation_space(oes)
    print(f"    {len(occ_space['codes'])} occupations x "
          f"{len(occ_space['region_ids'])} metro/nonmetro areas")

    print("  Job Space (shared O*NET tasks)...")
    pairs, dwa_titles = load_onet_job_dwa(onet_zip)
    job_space = build_job_space(oes, pairs)
    print(f"    {len(job_space['codes'])} jobs x "
          f"{len(job_space['tasks'])} DWAs")

    summary = {}
    for kind, space in (("occupation", occ_space), ("job", job_space)):
        print(f"  Layout + clusters: {kind} space...")
        lay = space_to_layout_json(space, oes, kind, seed=seed)
        path = out_dir / f"space-{country}-{year}-{kind}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(lay, f, indent=2)
        print(f"    {path.name}: {lay['stats']}")
        summary[kind] = lay["stats"]

    # Complexity file: PCI/JCI per occupation, ECI per region, top TCI tasks
    wage = oes["wage"]
    pci_codes = [c for c in occ_space["pci"] if c in wage]
    corr_pci_wage = float(np.corrcoef(
        [occ_space["pci"][c] for c in pci_codes],
        [np.log(wage[c]) for c in pci_codes])[0, 1])
    jci_codes = list(job_space["jci"])
    corr_jci_wage = float(np.corrcoef(
        [job_space["jci"][c] for c in jci_codes],
        [np.log(wage[c]) for c in jci_codes])[0, 1])
    tci_sorted = sorted(job_space["tci"].items(), key=lambda kv: -kv[1])
    complexity = {
        "year": year,
        "pci": {c: round(v, 4) for c, v in occ_space["pci"].items()},
        "jci": {c: round(v, 1) for c, v in job_space["jci"].items()},
        "eci": {r: round(v, 4) for r, v in occ_space["eci"].items()},
        "diversity": occ_space["diversity"],
        "ubiquity": occ_space["ubiquity"],
        "tciTop": [{"id": t, "name": dwa_titles.get(t, t), "tci": round(v, 1)}
                   for t, v in tci_sorted[:50]],
        "stats": {
            "corrPciLogWage": round(corr_pci_wage, 3),
            "corrJciLogWage": round(corr_jci_wage, 3),
            "nPci": len(occ_space["pci"]),
            "nJci": len(job_space["jci"]),
            "nRegionsEci": len(occ_space["eci"]),
            "nDwa": len(job_space["tasks"]),
        },
    }
    path = out_dir / f"complexity-{country}-{year}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(complexity, f, indent=2)
    print(f"    {path.name}: {complexity['stats']}")
    summary["complexity"] = complexity["stats"]
    return summary
