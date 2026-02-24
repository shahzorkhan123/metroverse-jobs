"""Import India PLFS data from published tables and optional microdata.

Data sources:
    - Table 25: NCO 1-3 digit percentage distribution of workers (PLFS 2023-24)
    - Table 50: Average monthly wages by 1-digit NCO division (PLFS 2023-24)
    - PLFS microdata extract CSV (optional): weighted state/city aggregates
"""

import csv
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

from . import config, db

STATE_NAME_CANDIDATES = [
    "st_name", "state_name", "state", "state_ut", "state_ut_name", "st",
    "state_ut_code",
]
CITY_NAME_CANDIDATES = [
    "city_name", "city", "district_name", "district", "district_code",
    "town_name", "town",
]
WEIGHT_CANDIDATES = [
    "mult", "weight", "wt", "survey_weight", "subsample_multiplier",
]
WAGE_CANDIDATES = [
    "ern_reg", "monthly_wage", "wage", "earnings", "wage_monthly",
    "cws_earnings_salaried", "cws_earnings_selfemployed",
]
OCC_CODE_CANDIDATES = [
    "ocu_pas", "occupation_code", "nco_code", "nco", "occ_code",
    "principal_occupation_code", "cws_occupation_code",
]
OCC_TITLE_CANDIDATES = ["occupation_name", "occ_title", "ocu_name", "nco_name"]


def _read_table25(csv_path: Path) -> list[dict]:
    """Read NCO distribution CSV (Table 25).

    Returns list of dicts with keys: nco_code, name, pct
    """
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "nco_code": row["nco_code"].strip(),
                "name": row["name"].strip(),
                "pct": float(row["pct_rural_urban_person"]),
            })
    return rows


def _read_table50(csv_path: Path) -> dict[str, int]:
    """Read NCO wages CSV (Table 50).

    Returns dict mapping 1-digit NCO division -> monthly wage (Rs.)
    """
    wages = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            div = row["nco_division"].strip()
            wages[div] = int(row["avg_monthly_wage_rural_urban_person"])
    return wages


def _nco_level(code: str) -> int:
    """NCO hierarchy: level = number of digits."""
    return len(code.strip())


def _nco_division(code: str) -> str:
    """Get the 1-digit division for any NCO code."""
    return code[0]


def _to_float(value: str | None) -> float | None:
    """Parse numeric string safely; returns None for invalid/empty values."""
    if value is None:
        return None
    raw = str(value).strip().replace(",", "")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _detect_column(fieldnames: list[str],
                   candidates: list[str],
                   required: bool = True) -> str | None:
    """Return first matching column from candidates (case-insensitive)."""
    lower = {f.lower(): f for f in fieldnames}
    for c in candidates:
        if c.lower() in lower:
            return lower[c.lower()]
    if required:
        raise ValueError(
            f"Missing required column. Tried: {', '.join(candidates)}. "
            f"Available: {', '.join(fieldnames)}"
        )
    return None


def _normalize_nco_code(raw_code: str | None) -> str:
    """Normalize occupation code to digits only (supports 1-4 digits)."""
    if raw_code is None:
        return ""
    code = re.sub(r"[^0-9]", "", str(raw_code))
    if not code:
        return ""
    if len(code) > 4:
        return code[:4]
    return code


def _default_nco_title(code: str) -> str:
    """Fallback display title when no official label mapping is available."""
    if len(code) == 1:
        return f"Division {code}"
    if len(code) == 2:
        return f"Sub-Division {code}"
    if len(code) == 3:
        return f"Group {code}"
    if len(code) == 4:
        return f"Unit Group {code}"
    return f"NCO {code}"


def _load_nco_label_map(csv_path: Path) -> dict[str, str]:
    """Load optional NCO code->title map CSV.

    Accepts any header with a code column (nco_code/code/occupation_code)
    and a label column (name/title/occupation_title).
    """
    if not csv_path.exists():
        return {}

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return {}
        code_col = _detect_column(
            reader.fieldnames,
            ["nco_code", "code", "occupation_code", "occ_code"],
            required=False,
        )
        name_col = _detect_column(
            reader.fieldnames,
            ["name", "title", "occupation_title", "label"],
            required=False,
        )
        if not code_col or not name_col:
            return {}

        mapping: dict[str, str] = {}
        for row in reader:
            code = _normalize_nco_code(row.get(code_col))
            label = str(row.get(name_col, "")).strip()
            if code and label:
                mapping[code] = label
        return mapping


def _load_district_label_map(csv_path: Path) -> dict[tuple[str, str], str]:
    """Load optional district label map CSV.

    Expected columns (case-insensitive):
      - state code: state_code / state_ut_code / st
      - district code: district_code / district
      - name: district_name / city_name / name
    """
    if not csv_path.exists():
        return {}

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return {}

        state_col = _detect_column(
            reader.fieldnames,
            ["state_code", "state_ut_code", "st"],
            required=False,
        )
        district_col = _detect_column(
            reader.fieldnames,
            ["district_code", "district"],
            required=False,
        )
        name_col = _detect_column(
            reader.fieldnames,
            ["district_name", "city_name", "name"],
            required=False,
        )
        if not state_col or not district_col or not name_col:
            return {}

        mapping: dict[tuple[str, str], str] = {}
        for row in reader:
            state_code = re.sub(r"\D", "", str(row.get(state_col, ""))).zfill(2)
            district_code = re.sub(r"\D", "", str(row.get(district_col, ""))).zfill(2)
            name = str(row.get(name_col, "")).strip()
            if state_code and district_code and name:
                mapping[(state_code, district_code)] = name
        return mapping


def _state_code_from_row(row: dict, state_col: str) -> str | None:
    """Extract normalized 2-digit state code when state column is coded."""
    value = str(row.get(state_col, "")).strip()
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    if not digits:
        return None
    return digits.zfill(2)


def _expand_nco_code_levels(code: str, levels: list[int]) -> list[str]:
    """Roll up an NCO code to requested hierarchy levels via prefixes."""
    out = []
    for lvl in sorted(set(levels)):
        if 1 <= lvl <= len(code):
            out.append(code[:lvl])
    return out


def _state_name_from_row(row: dict, state_col: str) -> str:
    """Derive clean state name for region records."""
    value = str(row.get(state_col, "")).strip()
    if value:
        if value.isdigit():
            code = value.zfill(2)
            mapped = config.INDIA_STATE_CODE_TO_NAME.get(code)
            if mapped:
                return mapped
            return f"State {code}"
        return value
    return "Unknown State"


def _city_name_from_row(row: dict,
                        city_col: str | None,
                        state_code: str | None = None,
                        state_name: str | None = None,
                        district_labels: dict[tuple[str, str], str] | None = None) -> str | None:
    """Derive city/district name if a city-like column exists."""
    if not city_col:
        return None
    value = str(row.get(city_col, "")).strip()
    if not value:
        return None
    normalized_city_col = city_col.lower()
    if normalized_city_col == "district_code" and value.isdigit():
        district_code = value.zfill(2)
        if state_code and district_labels:
            mapped = district_labels.get((state_code, district_code))
            if mapped:
                if state_name and "," not in mapped:
                    return f"{mapped}, {state_name}"
                return mapped
        district_name = f"District {district_code}"
        if state_name:
            return f"{district_name}, {state_name}"
        return district_name
    if normalized_city_col in {"district", "district_name"} and state_name and "," not in value:
        return f"{value}, {state_name}"
    return value


def _normalize_annual_wage(raw_wage: float | None,
                           wage_col: str | None) -> float | None:
    """Normalize source wage to annual INR.

    Conversion rules:
      - CWS earnings fields: weekly -> annual (x52)
      - Monthly wage-like fields: monthly -> annual (x12)
      - Otherwise: assume already annual
    """
    if raw_wage is None or raw_wage <= 0:
        return None
    if not wage_col:
        return raw_wage
    col = wage_col.lower()
    if col.startswith("cws_earnings"):
        return raw_wage * 52.0
    if ("monthly" in col
            or col in {"ern_reg", "wage_monthly", "monthly_wage"}):
        return raw_wage * 12.0
    return raw_wage


def _normalize_person_weight(raw_weight: float | None,
                             weight_col: str | None) -> float | None:
    """Normalize PLFS person-weight fields to estimated headcount.

    In PLFS microdata extracts, `Subsample_Multiplier` is often stored with an
    implicit 1e3 scale. Convert it to person units before aggregation.
    """
    if raw_weight is None or raw_weight <= 0:
        return None
    if not weight_col:
        return raw_weight

    col = weight_col.lower()
    if col == "subsample_multiplier":
        return raw_weight / 1000.0
    return raw_weight


def import_india_national(conn: sqlite3.Connection, year: int = 2024) -> int:
    """Import India national data from Table 25 + Table 50 CSVs.

    Table 50 values are monthly wages; this importer stores annual wages
    to align with US BLS `A_MEAN` semantics used across the pipeline.
    """
    ind_config = config.COUNTRIES["IND"]
    table25_path = ind_config["table25_csv"]
    table50_path = ind_config["table50_csv"]
    total_workers = ind_config["total_workers"]

    if not table25_path.exists():
        raise FileNotFoundError(f"Table 25 CSV not found: {table25_path}")
    if not table50_path.exists():
        raise FileNotFoundError(f"Table 50 CSV not found: {table50_path}")

    distributions = _read_table25(table25_path)
    wages = _read_table50(table50_path)
    labels = _load_nco_label_map(ind_config.get("nco_labels_csv", Path("")))

    country_id = db.ensure_country(conn, "IND", "India", "NCO", "INR")
    region_id = db.ensure_region(conn, country_id, "India", "National")

    count = 0
    for dist in distributions:
        code = dist["nco_code"]
        name = labels.get(dist["nco_code"], dist["name"])
        pct = dist["pct"]

        employment = round(total_workers * pct / 100.0)
        if employment <= 0:
            continue

        division = _nco_division(code)
        annual_wage = wages.get(division, 0) * 12
        major_group_name = config.NCO_MAJOR_GROUPS.get(division, f"Division {division}")
        gdp = employment * annual_wage

        conn.execute(
            "INSERT OR REPLACE INTO occupations "
            "(year, region_id, occupation_code, occupation_title, "
            "major_group_name, employment, mean_annual_wage, gdp, complexity_score) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.5)",
            (year, region_id, code, name,
             major_group_name, employment, annual_wage, gdp),
        )
        count += 1

    conn.commit()
    return count


def import_india_subnational_from_microdata(
    conn: sqlite3.Connection,
    year: int = 2024,
    micro_csv_path: Path | None = None,
    state_levels: list[int] | None = None,
    city_levels: list[int] | None = None,
    national_levels: list[int] | None = None,
    min_obs_state: int | None = 30,
    min_obs_city: int | None = 30,
    city_region_type: str = "Metro",
    district_top_n: int | None = None,
    district_population_min: float | None = None,
) -> dict[str, int]:
    """Import weighted state/city aggregates from PLFS person-level microdata CSV.

    Required columns (case-insensitive):
      - state: one of STATE_NAME_CANDIDATES
      - occupation code: one of OCC_CODE_CANDIDATES
      - survey weight: one of WEIGHT_CANDIDATES

        Optional columns:
    - wage: one of WAGE_CANDIDATES (auto-normalized to annual INR)
      - city/district: one of CITY_NAME_CANDIDATES
      - occupation title: one of OCC_TITLE_CANDIDATES

        District inclusion for city-level output is population-based (weighted),
        not occupation-cell sample-size based:
            - rank districts by weighted population proxy from microdata weights
            - keep top N districts (default from config: 400)
            - optional minimum weighted population cutoff
    """
    ind_config = config.COUNTRIES["IND"]
    path = micro_csv_path or ind_config.get("plfs_micro_csv")
    if path is None or not Path(path).exists():
        return {"national": 0, "state": 0, "city": 0}

    state_levels = state_levels or ind_config.get("state_levels", [1, 2])
    city_levels = city_levels or ind_config.get("city_levels", [1])
    national_levels = national_levels or ind_config.get("national_levels", [1, 2, 3])
    if min_obs_state is None:
        min_obs_state = int(ind_config.get("min_obs_state", 30))
    # City/district filtering is population-based; min_obs_city is ignored.
    if district_top_n is None:
        district_top_n = int(ind_config.get("district_top_n", 400) or 0)
    if district_population_min is None:
        district_population_min = float(ind_config.get("district_population_min", 0) or 0)

    country_cfg = config.COUNTRIES["IND"]
    country_id = db.ensure_country(
        conn,
        "IND",
        country_cfg["name"],
        country_cfg["code_system"],
        country_cfg["currency"],
    )

    # Seed titles from optional labels map + table 25 if available.
    title_by_code: dict[str, str] = {}
    labels_map_path = country_cfg.get("nco_labels_csv")
    if labels_map_path:
        title_by_code.update(_load_nco_label_map(Path(labels_map_path)))

    table25_path = country_cfg.get("table25_csv")
    if table25_path and Path(table25_path).exists():
        for row in _read_table25(Path(table25_path)):
            title_by_code[row["nco_code"]] = row["name"]

    district_labels: dict[tuple[str, str], str] = {}
    district_labels_path = country_cfg.get("district_labels_csv")
    if district_labels_path:
        district_labels = _load_district_label_map(Path(district_labels_path))

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"Microdata CSV has no header: {path}")

        state_col = _detect_column(reader.fieldnames, STATE_NAME_CANDIDATES)
        occ_col = _detect_column(reader.fieldnames, OCC_CODE_CANDIDATES)
        wt_col = _detect_column(reader.fieldnames, WEIGHT_CANDIDATES)
        wage_col = _detect_column(reader.fieldnames, WAGE_CANDIDATES, required=False)
        city_col = _detect_column(reader.fieldnames, CITY_NAME_CANDIDATES, required=False)
        occ_title_col = _detect_column(reader.fieldnames, OCC_TITLE_CANDIDATES, required=False)

        # (region_type, region_name, occ_code) -> stats
        accum = defaultdict(lambda: {
            "emp_weight": 0.0,
            "wage_weighted_sum": 0.0,
            "wage_weight_den": 0.0,
            "obs_n": 0,
        })
        district_population = defaultdict(float)

        for row in reader:
            weight = _normalize_person_weight(_to_float(row.get(wt_col)), wt_col)
            if weight is None or weight <= 0:
                continue

            state_name = _state_name_from_row(row, state_col)
            state_code = _state_code_from_row(row, state_col)
            city_name = _city_name_from_row(
                row,
                city_col,
                state_code=state_code,
                state_name=state_name,
                district_labels=district_labels,
            )
            if city_name:
                district_population[city_name] += weight

            code = _normalize_nco_code(row.get(occ_col))
            if not code:
                continue

            raw_wage = _to_float(row.get(wage_col)) if wage_col else None
            wage = _normalize_annual_wage(raw_wage, wage_col)

            if occ_title_col:
                maybe_title = str(row.get(occ_title_col, "")).strip()
                if maybe_title and code not in title_by_code:
                    title_by_code[code] = maybe_title

            for lvl_code in _expand_nco_code_levels(code, national_levels):
                key = ("National", country_cfg.get("national_region_name", "India"), lvl_code)
                slot = accum[key]
                slot["emp_weight"] += weight
                slot["obs_n"] += 1
                if wage is not None:
                    slot["wage_weighted_sum"] += wage * weight
                    slot["wage_weight_den"] += weight

            for lvl_code in _expand_nco_code_levels(code, state_levels):
                key = ("State", state_name, lvl_code)
                slot = accum[key]
                slot["emp_weight"] += weight
                slot["obs_n"] += 1
                if wage is not None:
                    slot["wage_weighted_sum"] += wage * weight
                    slot["wage_weight_den"] += weight

            if city_name:
                for lvl_code in _expand_nco_code_levels(code, city_levels):
                    key = (city_region_type, city_name, lvl_code)
                    slot = accum[key]
                    slot["emp_weight"] += weight
                    slot["obs_n"] += 1
                    if wage is not None:
                        slot["wage_weighted_sum"] += wage * weight
                        slot["wage_weight_den"] += weight

    district_items = sorted(
        district_population.items(),
        key=lambda item: item[1],
        reverse=True,
    )
    if district_population_min > 0:
        district_items = [
            (name, pop_weight) for name, pop_weight in district_items
            if pop_weight >= district_population_min
        ]
    if district_top_n > 0:
        district_items = district_items[:district_top_n]
    allowed_city_names = {name for name, _pop_weight in district_items}

    national_count = 0
    state_count = 0
    city_count = 0
    region_cache: dict[tuple[str, str], int] = {}

    for (region_type, region_name, occ_code), stats in accum.items():
        obs_n = int(stats["obs_n"])
        if region_type == "State" and obs_n < min_obs_state:
            continue
        if region_type == city_region_type and region_name not in allowed_city_names:
            continue

        employment = int(round(stats["emp_weight"]))
        if employment <= 0:
            continue

        if stats["wage_weight_den"] > 0:
            annual_wage = int(round(stats["wage_weighted_sum"] / stats["wage_weight_den"]))
        else:
            annual_wage = 0

        major_id = _nco_division(occ_code)
        major_group_name = config.NCO_MAJOR_GROUPS.get(major_id, f"Division {major_id}")
        occ_title = title_by_code.get(occ_code, _default_nco_title(occ_code))
        gdp = employment * annual_wage

        region_key = (region_type, region_name)
        if region_key not in region_cache:
            region_cache[region_key] = db.ensure_region(
                conn, country_id, region_name, region_type
            )
        region_id = region_cache[region_key]

        conn.execute(
            "INSERT OR REPLACE INTO occupations "
            "(year, region_id, occupation_code, occupation_title, "
            "major_group_name, employment, mean_annual_wage, gdp, complexity_score) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.5)",
            (
                year,
                region_id,
                occ_code,
                occ_title,
                major_group_name,
                employment,
                annual_wage,
                gdp,
            ),
        )

        if region_type == "National":
            national_count += 1
        elif region_type == "State":
            state_count += 1
        elif region_type == city_region_type:
            city_count += 1

    conn.commit()
    return {"national": national_count, "state": state_count, "city": city_count}


def import_all_india(conn: sqlite3.Connection, year: int = 2024) -> int:
    """Orchestrate India data import.

    Returns total records imported.
    """
    print(f"Importing India PLFS data for year {year}...")

    count = 0

    ind_config = config.COUNTRIES["IND"]
    table25_path = ind_config["table25_csv"]
    table50_path = ind_config["table50_csv"]
    if table25_path.exists() and table50_path.exists():
        national_count = import_india_national(conn, year)
        count += national_count
        print(f"  National: {national_count} occupation records")
    else:
        print("  National tables not found; skipping published-table import")

    sub_counts = import_india_subnational_from_microdata(conn, year)
    if sub_counts.get("national", 0) > 0 or sub_counts["state"] > 0 or sub_counts["city"] > 0:
        if sub_counts.get("national", 0) > 0:
            print(f"  National (microdata): {sub_counts['national']} occupation records")
        print(f"  State: {sub_counts['state']} occupation records")
        print(f"  City: {sub_counts['city']} occupation records")
        count += sub_counts.get("national", 0) + sub_counts["state"] + sub_counts["city"]
    else:
        print("  Subnational microdata not found or empty; skipping state/city import")

    # Compute complexity scores (min-max normalized GDP per region)
    print("  Computing complexity scores...")
    db.compute_complexity_scores(conn)

    return count
