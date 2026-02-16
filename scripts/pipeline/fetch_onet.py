"""Download O*NET database and extract task complexity data.

Downloads the O*NET database ZIP, extracts Task Ratings and Task Statements
Excel files, and calculates a job complexity index (JCI) for each occupation
using an iterative algorithm based on task-occupation relationships.

Usage:
    from scripts.pipeline.fetch_onet import fetch_and_compute_complexity
    csv_path = fetch_and_compute_complexity()
"""

import csv
import io
import zipfile
from pathlib import Path

import requests

from . import config

# O*NET database URL (latest version)
ONET_DB_URL = f"{config.ONET_BASE_URL}/db_29_3_excel.zip"

# Files we need from the ZIP
TASK_RATINGS_FILE = "Task Ratings.xlsx"
TASK_STATEMENTS_FILE = "Task Statements.xlsx"


def _download_zip(url: str, dest_dir: Path) -> Path:
    """Download a ZIP file and return the local path."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1]
    dest_path = dest_dir / filename

    if dest_path.exists():
        print(f"  Using cached: {dest_path.name}")
        return dest_path

    print(f"  Downloading: {url}")
    resp = requests.get(url, timeout=300)
    resp.raise_for_status()
    dest_path.write_bytes(resp.content)
    print(f"  Saved: {dest_path.name} ({len(resp.content):,} bytes)")
    return dest_path


def _find_file_in_zip(zip_path: Path, target_name: str) -> str:
    """Find a file inside a ZIP by partial name match."""
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if target_name in name:
                return name
    raise FileNotFoundError(f"'{target_name}' not found in {zip_path}")


def _read_xlsx_from_zip(zip_path: Path, target_name: str) -> list[dict]:
    """Read an XLSX file from inside a ZIP."""
    import openpyxl

    inner_path = _find_file_in_zip(zip_path, target_name)
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(inner_path) as f:
            wb = openpyxl.load_workbook(io.BytesIO(f.read()),
                                        read_only=True, data_only=True)
            ws = wb.active
            rows_iter = ws.iter_rows(values_only=True)
            headers = [str(h).strip() if h else "" for h in next(rows_iter)]
            data = []
            for row in rows_iter:
                data.append(dict(zip(headers, row)))
            wb.close()
    return data


def _compute_jci(task_ratings: list[dict]) -> dict[str, float]:
    """Compute Job Complexity Index from O*NET task ratings.

    Uses the iterative method:
    1. Build a binary job-task matrix M[j,t] based on task relevance
    2. Initialize job complexity from mean wage (or use uniform start)
    3. Iterate: JCI_j = avg(TCI of tasks j does), TCI_t = avg(JCI of jobs doing t)
    4. Min-max normalize final JCI to [0, 1]

    Returns dict mapping O*NET SOC code -> complexity_score [0, 1].
    """
    try:
        import numpy as np
    except ImportError:
        print("  WARNING: numpy not available, using simple averaging")
        return _compute_jci_simple(task_ratings)

    # Build job-task relevance matrix
    # Task Ratings has columns: O*NET-SOC Code, Task ID, Scale ID,
    #   Data Value, Category, N, Standard Error, Lower CI Bound, Upper CI Bound,
    #   Recommend Suppress, Not Relevant, Date, Domain Source
    #
    # We use Scale ID == "IM" (Importance) and Data Value > 2.5 as threshold
    job_task_pairs: dict[tuple[str, str], float] = {}
    for row in task_ratings:
        scale_id = str(row.get("Scale ID", "")).strip()
        if scale_id != "IM":
            continue
        suppress = str(row.get("Recommend Suppress", "")).strip()
        if suppress == "Y":
            continue

        soc_code = str(row.get("O*NET-SOC Code", "")).strip()
        task_id = str(row.get("Task ID", "")).strip()
        try:
            data_value = float(row.get("Data Value", 0))
        except (ValueError, TypeError):
            continue

        if data_value > 2.5:
            # Use 6-digit SOC code (strip O*NET suffix like ".00")
            base_soc = soc_code.split(".")[0] if "." in soc_code else soc_code
            # Convert O*NET format (XX-XXXX.XX) to SOC (XX-XXXX)
            if len(base_soc) == 7 and "-" in base_soc:
                job_task_pairs[(base_soc, task_id)] = data_value

    if not job_task_pairs:
        print("  WARNING: No valid task ratings found")
        return {}

    # Get unique jobs and tasks
    jobs = sorted(set(jt[0] for jt in job_task_pairs))
    tasks = sorted(set(jt[1] for jt in job_task_pairs))
    job_idx = {j: i for i, j in enumerate(jobs)}
    task_idx = {t: i for i, t in enumerate(tasks)}

    Nj = len(jobs)
    Nt = len(tasks)
    print(f"  Job-task matrix: {Nj} jobs x {Nt} tasks")

    # Build matrix (binary: 1 if task is relevant to job)
    M = np.zeros((Nj, Nt), dtype=np.float64)
    for (j, t), val in job_task_pairs.items():
        M[job_idx[j], task_idx[t]] = 1.0

    # Tasks per job and jobs per task
    nj = M.sum(axis=1)  # shape (Nj,)
    nt = M.sum(axis=0)  # shape (Nt,)
    nj[nj == 0] = 1
    nt[nt == 0] = 1

    # Initialize JCI uniformly
    jci = np.ones(Nj)
    tci = np.ones(Nt)

    # Iterate 20 times
    for _ in range(20):
        # TCI = average JCI of jobs that do each task
        tci_new = (M.T @ jci) / nt
        # JCI = average TCI of tasks that each job does
        jci_new = (M @ tci) / nj
        jci = jci_new
        tci = tci_new

    # Min-max normalize to [0, 1]
    jci_min, jci_max = jci.min(), jci.max()
    if jci_max > jci_min:
        jci_norm = (jci - jci_min) / (jci_max - jci_min)
    else:
        jci_norm = np.full(Nj, 0.5)

    return {jobs[i]: round(float(jci_norm[i]), 4) for i in range(Nj)}


def _compute_jci_simple(task_ratings: list[dict]) -> dict[str, float]:
    """Simple fallback JCI: count of tasks per occupation, normalized."""
    task_counts: dict[str, int] = {}
    for row in task_ratings:
        scale_id = str(row.get("Scale ID", "")).strip()
        if scale_id != "IM":
            continue
        try:
            data_value = float(row.get("Data Value", 0))
        except (ValueError, TypeError):
            continue
        if data_value <= 2.5:
            continue

        soc_code = str(row.get("O*NET-SOC Code", "")).strip()
        base_soc = soc_code.split(".")[0] if "." in soc_code else soc_code
        if len(base_soc) == 7 and "-" in base_soc:
            task_counts[base_soc] = task_counts.get(base_soc, 0) + 1

    if not task_counts:
        return {}

    min_c = min(task_counts.values())
    max_c = max(task_counts.values())
    rng = max_c - min_c if max_c > min_c else 1

    return {soc: round((cnt - min_c) / rng, 4) for soc, cnt in task_counts.items()}


def fetch_and_compute_complexity(onet_url: str | None = None,
                                  raw_dir: Path | None = None) -> Path:
    """Download O*NET data and compute complexity scores.

    Returns path to onet_complexity.csv with columns:
        occupation_code, complexity_score
    """
    if raw_dir is None:
        raw_dir = config.RAW_DIR
    if onet_url is None:
        onet_url = ONET_DB_URL

    print("Fetching O*NET database...")
    zip_path = _download_zip(onet_url, raw_dir)

    print("Reading Task Ratings...")
    task_ratings = _read_xlsx_from_zip(zip_path, TASK_RATINGS_FILE)
    print(f"  {len(task_ratings)} task rating records")

    print("Computing job complexity index...")
    jci_scores = _compute_jci(task_ratings)
    print(f"  Computed JCI for {len(jci_scores)} occupations")

    # Write output CSV
    csv_path = raw_dir / "onet_complexity.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["occupation_code", "complexity_score"])
        for soc, score in sorted(jci_scores.items()):
            writer.writerow([soc, score])

    print(f"  Wrote: {csv_path.name}")
    return csv_path
