"""SQLite database schema, CRUD operations, and complexity computation."""

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS countries (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    code_system TEXT NOT NULL,
    currency TEXT DEFAULT 'USD'
);

CREATE TABLE IF NOT EXISTS regions (
    id INTEGER PRIMARY KEY,
    country_id INTEGER NOT NULL REFERENCES countries(id),
    name TEXT NOT NULL,
    region_type TEXT NOT NULL,
    UNIQUE(country_id, name, region_type)
);

CREATE TABLE IF NOT EXISTS occupations (
    id INTEGER PRIMARY KEY,
    year INTEGER NOT NULL,
    region_id INTEGER NOT NULL REFERENCES regions(id),
    occupation_code TEXT NOT NULL,
    occupation_title TEXT NOT NULL,
    major_group_name TEXT NOT NULL,
    employment INTEGER NOT NULL,
    mean_annual_wage INTEGER NOT NULL,
    gdp BIGINT NOT NULL,
    complexity_score REAL NOT NULL DEFAULT 0.5,
    UNIQUE(year, region_id, occupation_code)
);

CREATE INDEX IF NOT EXISTS idx_occ_year ON occupations(year);
CREATE INDEX IF NOT EXISTS idx_occ_region ON occupations(region_id);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    """Open (or create) the SQLite database and return a connection."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    """Create all tables and indexes if they don't exist."""
    conn.executescript(SCHEMA_SQL)


def drop_all(conn: sqlite3.Connection) -> None:
    """Drop all tables (for --fresh rebuilds)."""
    conn.executescript("""
        DROP TABLE IF EXISTS occupations;
        DROP TABLE IF EXISTS regions;
        DROP TABLE IF EXISTS countries;
    """)


def ensure_country(conn: sqlite3.Connection, code: str, name: str,
                   code_system: str, currency: str = "USD") -> int:
    """Insert country if not exists, return its id."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO countries (code, name, code_system, currency) "
        "VALUES (?, ?, ?, ?)",
        (code, name, code_system, currency),
    )
    if cur.lastrowid and cur.rowcount > 0:
        return cur.lastrowid
    row = conn.execute(
        "SELECT id FROM countries WHERE code = ?", (code,)
    ).fetchone()
    return row[0]


def ensure_region(conn: sqlite3.Connection, country_id: int,
                  name: str, region_type: str) -> int:
    """Insert region if not exists, return its id."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO regions (country_id, name, region_type) "
        "VALUES (?, ?, ?)",
        (country_id, name, region_type),
    )
    if cur.lastrowid and cur.rowcount > 0:
        return cur.lastrowid
    row = conn.execute(
        "SELECT id FROM regions WHERE country_id = ? AND name = ? AND region_type = ?",
        (country_id, name, region_type),
    ).fetchone()
    return row[0]


def insert_occupation(conn: sqlite3.Connection, year: int, region_id: int,
                      occupation_code: str, occupation_title: str,
                      major_group_name: str, employment: int,
                      mean_annual_wage: int) -> None:
    """Insert one occupation record. GDP is auto-calculated."""
    gdp = employment * mean_annual_wage
    conn.execute(
        "INSERT OR REPLACE INTO occupations "
        "(year, region_id, occupation_code, occupation_title, "
        "major_group_name, employment, mean_annual_wage, gdp, complexity_score) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.5)",
        (year, region_id, occupation_code, occupation_title,
         major_group_name, employment, mean_annual_wage, gdp),
    )


def compute_complexity_scores(conn: sqlite3.Connection) -> None:
    """Set complexity_score = min-max normalized GDP per (year, region).

    Per-region normalization ensures each treemap view gets full 0-1 color range.
    If all GDPs equal in a region, set 0.5.
    """
    rows = conn.execute("""
        SELECT year, region_id, MIN(gdp), MAX(gdp)
        FROM occupations
        GROUP BY year, region_id
    """).fetchall()

    for year, region_id, min_gdp, max_gdp in rows:
        gdp_range = max_gdp - min_gdp
        if gdp_range == 0:
            conn.execute(
                "UPDATE occupations SET complexity_score = 0.5 "
                "WHERE year = ? AND region_id = ?",
                (year, region_id),
            )
        else:
            conn.execute(
                "UPDATE occupations SET complexity_score = "
                "ROUND(CAST(gdp - ? AS REAL) / ?, 4) "
                "WHERE year = ? AND region_id = ?",
                (min_gdp, gdp_range, year, region_id),
            )
    conn.commit()


def get_record_count(conn: sqlite3.Connection) -> int:
    """Return total number of occupation records."""
    return conn.execute("SELECT COUNT(*) FROM occupations").fetchone()[0]


def get_summary(conn: sqlite3.Connection) -> list[dict]:
    """Return summary counts by country and region type."""
    rows = conn.execute("""
        SELECT c.code, c.name, r.region_type, COUNT(o.id) as record_count
        FROM occupations o
        JOIN regions r ON o.region_id = r.id
        JOIN countries c ON r.country_id = c.id
        GROUP BY c.code, r.region_type
        ORDER BY c.code, r.region_type
    """).fetchall()
    return [
        {"country_code": r[0], "country_name": r[1],
         "region_type": r[2], "record_count": r[3]}
        for r in rows
    ]
