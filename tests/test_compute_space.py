"""Tests for scripts/pipeline/compute_space.py (Occupation/Job Space)."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.pipeline import compute_space as cs  # noqa: E402


@pytest.fixture
def nested_matrix():
    """Nested location x product matrix (classic complexity toy example).

    Location i makes products 0..i, so product 0 is ubiquitous and the
    last product is made only by the most diverse location.
    """
    n = 8
    M = np.tril(np.ones((n, n)))
    # add a little noise so eigenvectors are well defined
    M[2, 5] = 1
    M[6, 7] = 0
    return M


def test_rca_balassa():
    X = np.array([[10, 0], [5, 5]], dtype=float)
    rca = cs.calc_rca(X)
    # location 0: share of product 0 = 1.0; world share = 15/20
    assert rca[0, 0] == pytest.approx(1.0 / 0.75)
    assert rca[0, 1] == 0
    assert rca[1, 1] == pytest.approx(0.5 / 0.25)


def test_proximity_symmetric_bounded(nested_matrix):
    phi = cs.min_cond_proximity(nested_matrix)
    assert np.allclose(phi, phi.T)
    assert phi.min() >= 0 and phi.max() <= 1
    assert np.all(np.diag(phi) == 0)


def test_proximity_min_conditional():
    # product a made in 4 places, b in 2 of those -> P(a|b)=1, P(b|a)=0.5
    M = np.array([[1, 1], [1, 1], [1, 0], [1, 0]], dtype=float)
    phi = cs.min_cond_proximity(M)
    assert phi[0, 1] == pytest.approx(0.5)


def test_eci_correlates_with_diversity(nested_matrix):
    eci, pci = cs.eci_pci(nested_matrix)
    diversity = nested_matrix.sum(axis=1)
    assert np.corrcoef(diversity, eci)[0, 1] > 0.9
    # ubiquitous product 0 is the least complex
    assert pci.argmin() == 0
    assert eci.mean() == pytest.approx(0, abs=1e-9)


def test_eci_pci_matches_py_ecomplexity(nested_matrix):
    ecomplexity = pytest.importorskip("ecomplexity")
    import pandas as pd

    rows = [{"t": 2024, "loc": f"c{i}", "prod": f"p{j}", "val": v}
            for i, row in enumerate(nested_matrix) for j, v in enumerate(row)]
    df = pd.DataFrame(rows)
    # value matrix chosen so RCA >= 1 reproduces M exactly
    df["val"] = df["val"] * 1.0
    out = ecomplexity.ecomplexity(
        df, {"time": "t", "loc": "loc", "prod": "prod", "val": "val"},
        presence_test="manual")
    eci_ref = out.groupby("loc")["eci"].first().reindex(
        [f"c{i}" for i in range(len(nested_matrix))]).values
    eci, _ = cs.eci_pci(nested_matrix)
    assert abs(np.corrcoef(eci, eci_ref)[0, 1]) > 0.999


def test_wage_seeded_jci_positive_and_ordered():
    # 3 jobs x 4 tasks; job 2 does the tasks of the high-wage job
    M = np.array([[1, 1, 0, 0],
                  [0, 1, 1, 0],
                  [0, 0, 1, 1]], dtype=float)
    wages = np.array([30_000, 60_000, 120_000])
    jci, tci, hist = cs.wage_seeded_jci(M, wages, n_iter=5)
    assert np.all(jci > 0) and np.all(tci > 0)
    assert jci.std() > 0                       # not constant (old bug)
    assert jci.argmax() == 2 and jci.argmin() == 0
    assert len(hist) == 6
    # averaging operator shrinks dispersion each iteration
    assert all(b <= a + 1e-12 for a, b in zip(hist, hist[1:]))


def test_backbone_connected_and_degree(nested_matrix):
    rng = np.random.default_rng(0)
    M = (rng.random((60, 40)) > 0.6).astype(float)
    phi = cs.min_cond_proximity(M)
    edges, k, cutoff, mst = cs.backbone(phi, target_avg_degree=4.0)
    assert len(mst) == phi.shape[0] - 1
    assert 2 * len(edges) / phi.shape[0] >= 4.0
    import networkx as nx
    G = nx.Graph()
    G.add_edges_from((i, j) for i, j, _ in edges)
    assert nx.is_connected(G)


def test_layout_and_clusters_deterministic():
    rng = np.random.default_rng(1)
    M = (rng.random((50, 30)) > 0.55).astype(float)
    phi = cs.min_cond_proximity(M)
    edges, _, _, mst = cs.backbone(phi)
    xy1 = cs.layout(30, edges, mst, seed=7)
    xy2 = cs.layout(30, edges, mst, seed=7)
    assert np.allclose(xy1, xy2)
    assert xy1[:, 0].min() == pytest.approx(0) and xy1[:, 0].max() == pytest.approx(1000)
    cont, country = cs.clusters(30, edges, seed=7)
    # countries nest inside continents
    for c in np.unique(country):
        assert len(np.unique(cont[country == c])) == 1


def test_hull_contains_points():
    from matplotlib.path import Path as MPath
    pts = np.array([[0, 0], [10, 0], [5, 8], [5, 3]])
    poly = cs.hull(pts, pad=2)
    path = MPath(np.array(poly))
    assert all(path.contains_point(p) for p in pts)
