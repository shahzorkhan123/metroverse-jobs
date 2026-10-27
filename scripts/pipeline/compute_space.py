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


# SOC 2018 User Guide, tables 5 and 6: official aggregations above the major
# groups (military group 55 omitted -- OES has no military occupations).
SOC_INTERMEDIATE = {
    "1": ("Management, Business & Financial", ["11", "13"]),
    "2": ("Computer, Engineering & Science", ["15", "17", "19"]),
    "3": ("Education, Legal, Community Service, Arts & Media", ["21", "23", "25", "27"]),
    "4": ("Healthcare Practitioners & Technical", ["29"]),
    "5": ("Service", ["31", "33", "35", "37", "39"]),
    "6": ("Sales", ["41"]),
    "7": ("Office & Administrative Support", ["43"]),
    "8": ("Farming, Fishing & Forestry", ["45"]),
    "9": ("Construction & Extraction", ["47"]),
    "10": ("Installation, Maintenance & Repair", ["49"]),
    "11": ("Production", ["51"]),
    "12": ("Transportation & Material Moving", ["53"]),
}
SOC_HIGH = {
    "1": ("Management, Business, Science & Arts", ["1", "2", "3", "4"]),
    "2": ("Service", ["5"]),
    "3": ("Sales & Office", ["6", "7"]),
    "4": ("Natural Resources, Construction & Maintenance", ["8", "9", "10"]),
    "5": ("Production, Transportation & Material Moving", ["11", "12"]),
}
SOC_LEVELS = ["high", "intermediate", "major", "minor"]
_PREFIX = {"high": "h", "intermediate": "i", "major": "m", "minor": "n"}


def load_soc_hierarchy(data_dir: Path, country: str = "us", year: int = 2024):
    """SOC group ids and names for every detailed occupation.

    Returns (groups, names): groups[code] = {level: group id} for the four
    levels in SOC_LEVELS; names[group id] = title.  Ids are prefixed by level
    ("h1", "i5", "m29", "n29-1100") so they are unique across levels.
    Minor groups come from the level-3 parent chain in the published JSON.
    """
    def read(suffix):
        with open(data_dir / f"bls-data-{country}-{year}{suffix}.json", encoding="utf-8") as f:
            return json.load(f)["occupations"]

    occ = {o["socCode"]: o for o in read("") + read("-3") + read("-4")}
    inter_of = {mg: i for i, (_, mgs) in SOC_INTERMEDIATE.items() for mg in mgs}
    high_of = {i: h for h, (_, ints) in SOC_HIGH.items() for i in ints}
    names = {f"h{h}": t for h, (t, _) in SOC_HIGH.items()}
    names.update({f"i{i}": t for i, (t, _) in SOC_INTERMEDIATE.items()})
    groups = {}
    for code, o in occ.items():
        if o["level"] != 4 or o["majorGroupId"] not in inter_of:
            continue
        broad = occ.get(o["parentCode"] or "")
        # Published parentCodes miss the renumbered minor groups (15-1200,
        # 31-1100, 51-5100: broad 15-1250 points at a non-existent 15-1000),
        # so fall back to the XX-XX00 and XX-X000 patterns that do exist.
        candidates = [broad.get("parentCode") if broad else None,
                      code[:5] + "00", code[:4] + "000"]
        minor = next((m for m in candidates if m and m in occ and occ[m]["level"] == 2),
                     code[:4] + "000")
        mg = o["majorGroupId"]
        inter = inter_of[mg]
        groups[code] = {"high": f"h{high_of[inter]}", "intermediate": f"i{inter}",
                        "major": f"m{mg}", "minor": f"n{minor}"}
        names[f"m{mg}"] = SHORT_GROUP_NAMES.get(o["majorGroupName"], o["majorGroupName"])
        if minor in occ:
            names[f"n{minor}"] = occ[minor]["name"]
    return groups, names


def _leaf_layout(phi_sub: np.ndarray) -> np.ndarray:
    """Kamada-Kawai positions (unit disc) for a small group, distance 1 - phi."""
    import networkx as nx

    m = phi_sub.shape[0]
    if m == 1:
        return np.zeros((1, 2))
    G = nx.Graph()
    G.add_nodes_from(range(m))
    for a in range(m):
        for b in range(a + 1, m):
            G.add_edge(a, b, d=1.05 - phi_sub[a, b])
    pos = nx.kamada_kawai_layout(G, weight="d")
    xy = np.array([pos[a] for a in range(m)])
    xy -= xy.mean(axis=0)
    r = np.linalg.norm(xy, axis=1).max()
    return xy / r if r > 0 else xy


def _pack_discs(radii, affinity: np.ndarray, seed: int) -> np.ndarray:
    """Centres for non-overlapping discs, related discs placed close together.

    Start from a spring layout of the groups weighted by affinity, then
    push overlapping discs apart while a weak pull keeps the pack compact.
    """
    import networkx as nx

    r = np.asarray(radii, dtype=float)
    c = len(r)
    if c == 1:
        return np.zeros((1, 2))
    G = nx.Graph()
    G.add_nodes_from(range(c))
    for a in range(c):
        for b in range(a + 1, c):
            if affinity[a, b] > 0:
                G.add_edge(a, b, weight=affinity[a, b])
    pos = nx.spring_layout(G, weight="weight", seed=seed, iterations=200)
    p = np.array([pos[a] for a in range(c)]) * r.sum()
    gap = 0.02 * r.mean()

    def separate(pull: float) -> bool:
        moved = False
        for a in range(c):
            for b in range(a + 1, c):
                d = p[b] - p[a]
                dist = np.linalg.norm(d) + 1e-9
                need = r[a] + r[b] + gap
                if dist < need:
                    push = (need - dist) / 2 * d / dist
                    p[a] -= push
                    p[b] += push
                    moved = True
        if pull:
            p[:] += pull * ((p * r[:, None] ** 2).sum(0) / (r ** 2).sum() - p)
        return moved

    for it in range(400):
        if not separate(0.02) and it > 50:
            break
    for _ in range(2000):          # strict pass: no pull, no overlap left
        if not separate(0.0):
            break
    return p - (p * r[:, None] ** 2).sum(0) / (r ** 2).sum()


def nested_layout(phi: np.ndarray, labels: list, seed: int = 42) -> np.ndarray:
    """Group-in-a-disc layout following a label hierarchy.

    labels[i] is a tuple of group ids from the coarsest to the finest level.
    Occupations are laid out by phi inside their finest group; each group is a
    disc, and sibling discs are packed so that groups with higher mean phi
    sit closer.  Every group at every level is therefore one contiguous
    region and hulls never overlap.  Returns (n, 2) scaled to 1000 x 750.
    """
    depth_max = len(labels[0])

    def place(idx, depth):
        if depth == depth_max:
            rad = max(np.sqrt(len(idx)), 0.6)
            return _leaf_layout(phi[np.ix_(idx, idx)]) * rad, rad
        keys = sorted({labels[i][depth] for i in idx})
        parts = [[i for i in idx if labels[i][depth] == k] for k in keys]
        subs = [place(part, depth + 1) for part in parts]
        aff = np.zeros((len(parts), len(parts)))
        for a in range(len(parts)):
            for b in range(a + 1, len(parts)):
                aff[a, b] = aff[b, a] = phi[np.ix_(parts[a], parts[b])].mean()
        centres = _pack_discs([s[1] for s in subs], aff, seed)
        pos = {}
        for part, (xy, _), cen in zip(parts, subs, centres):
            for i, v in zip(part, xy):
                pos[i] = v + cen
        radius = max(np.linalg.norm(cen) + s[1] for cen, s in zip(centres, subs))
        return np.array([pos[i] for i in idx]), radius

    xy, _ = place(list(range(len(labels))), 0)
    xy -= xy.min(axis=0)
    span = xy.max(axis=0)
    span[span == 0] = 1
    xy = xy / span
    return np.column_stack([xy[:, 0] * 1000, xy[:, 1] * 750])


def _phi_fidelity(xy: np.ndarray, edges) -> float:
    """Spearman correlation of map distance with phi on backbone links (< 0 is good)."""
    from scipy.stats import spearmanr

    d = [float(np.linalg.norm(xy[i] - xy[j])) for i, j, _ in edges]
    return float(spearmanr(d, [w for _, _, w in edges]).correlation)


def _cluster_profiles(members: dict, oes: dict, pci: dict | None,
                      min_metro_emp: int = 100_000, top: int = 5):
    """Per-group summary: where it concentrates and what it is made of.

    members[group id] = list of SOC codes.  topRegions ranks metros with at
    least min_metro_emp jobs by the group's RCA (share of the metro's jobs
    in the group / national share).
    """
    nat = oes["emp"][oes["national_id"]]
    nat_total = sum(nat.values())
    metros = [rid for rid, r in oes["regions"].items()
              if r["regionType"] == "Metro"
              and sum(oes["emp"].get(rid, {}).values()) >= min_metro_emp]
    metro_total = {rid: sum(oes["emp"][rid].values()) for rid in metros}
    out = {}
    for gid, codes in members.items():
        g_nat = sum(nat.get(c, 0) for c in codes)
        share_nat = g_nat / nat_total if nat_total else 0
        rca = []
        if share_nat > 0:
            for rid in metros:
                e = oes["emp"][rid]
                rca.append((sum(e.get(c, 0) for c in codes) / metro_total[rid] / share_nat, rid))
        rca.sort(reverse=True)
        largest = sorted(codes, key=lambda c: -nat.get(c, 0))[:top]
        pcis = [pci[c] for c in codes if pci and c in pci]
        out[gid] = {
            "empShare": round(100 * share_nat, 2),
            "meanPci": round(float(np.mean(pcis)), 3) if pcis else None,
            "topRegions": [{"id": rid, "name": oes["regions"][rid]["name"], "rca": round(v, 2)}
                           for v, rid in rca[:top]],
            "topOccupations": [{"id": c, "name": oes["occupations"][c]["name"]} for c in largest],
        }
    return out


def space_to_layout_json(space: dict, oes: dict, kind: str, hierarchy: tuple,
                         pci: dict | None = None, n_neighbors: int = 10,
                         target_avg_degree: float = 4.0, seed: int = 42):
    """Build the renderer JSON: nodes with x/y, backbone links, SOC group hulls.

    hierarchy = load_soc_hierarchy(...).  Groups (hulls) are the official
    SOC 2018 levels -- high-level, intermediate, major, minor -- as the
    Atlas colours products by HS sector; phi only decides the arrangement
    (nested_layout).  The frontend shows one level as "continents" and the
    next as "countries" (Division level setting).
    """
    soc_groups, soc_names = hierarchy
    codes = [c for c in space["codes"] if c in soc_groups]
    keep = [i for i, c in enumerate(space["codes"]) if c in soc_groups]
    phi = space["phi"][np.ix_(keep, keep)]
    n = len(codes)
    edges, k, cutoff, _ = backbone(phi, target_avg_degree)
    labels = [tuple(soc_groups[c][lvl] for lvl in SOC_LEVELS) for c in codes]
    xy = nested_layout(phi, labels, seed=seed)

    levels = {}
    for d, lvl in enumerate(SOC_LEVELS):
        members: dict = {}
        for c, lab in zip(codes, labels):
            members.setdefault(lab[d], []).append(c)
        profiles = _cluster_profiles(members, oes, pci)
        idx_of = {c: i for i, c in enumerate(codes)}
        out = []
        for gid in sorted(members, key=lambda g: (len(g), g)):
            idx = [idx_of[c] for c in members[gid]]
            parent = labels[idx[0]][d - 1] if d > 0 else None
            out.append({
                "clusterId": gid,
                "clusterCode": len(out),
                "name": soc_names.get(gid, gid),
                "parentId": parent,
                "center": [round(float(v), 1) for v in xy[idx].mean(axis=0)],
                "polygon": hull(xy[idx], pad=(14.0, 10.0, 7.0, 5.0)[d]),
                "color": "#dfdfdf" if d % 2 == 0 else "#cfcfcf",
                "size": len(idx),
                "profile": profiles[gid],
            })
        levels[lvl] = out

    order = np.argsort(-phi, axis=1)
    links = [[codes[i], codes[j], round(w, 4)] for i, j, w in edges]
    nodes = []
    for i, c in enumerate(codes):
        nbrs = [j for j in order[i, :n_neighbors] if phi[i, j] > 0]
        nodes.append({
            "id": c,
            "x": round(float(xy[i, 0]), 2),
            "y": round(float(xy[i, 1]), 2),
            "groups": dict(zip(SOC_LEVELS, labels[i])),
            "edges": [{"trg": codes[j], "proximity": round(float(phi[i, j]), 4)}
                      for j in nbrs],
        })

    return {
        "kind": kind,
        "nodes": nodes,
        "links": links,
        "clusters": {"levels": levels},
        "stats": {
            "nNodes": n,
            "nLinks": len(edges),
            "avgDegree": round(2 * len(edges) / n, 2),
            "topK": int(k),
            "phiCutoff": round(cutoff, 4),
            "layout": "soc_nested",
            "phiFidelity": round(_phi_fidelity(xy, edges), 3),
            "nGroups": {lvl: len(v) for lvl, v in levels.items()},
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

    hierarchy = load_soc_hierarchy(data_dir, country, year)
    summary = {}
    for kind, space in (("occupation", occ_space), ("job", job_space)):
        print(f"  Layout + SOC groups: {kind} space...")
        lay = space_to_layout_json(space, oes, kind, hierarchy,
                                   pci=occ_space["pci"], seed=seed)
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
