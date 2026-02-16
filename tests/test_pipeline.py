"""Tests for the data pipeline."""

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from scripts.pipeline import config, db, import_csv, export_csv, export_json, export_jsonp, export_split, validate


@pytest.fixture
def tmp_db():
    """Create a temporary SQLite database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    conn = db.connect(db_path)
    db.create_schema(conn)
    yield conn
    conn.close()
    db_path.unlink(missing_ok=True)


@pytest.fixture
def seeded_db(tmp_db):
    """Create a database with synthetic test data."""
    cid = db.ensure_country(tmp_db, "USA", "United States", "SOC", "USD")

    # National region with 5 occupations (various levels)
    nat_id = db.ensure_region(tmp_db, cid, "United States", "National")
    test_occs = [
        ("11-0000", "Management Occupations", "Management", 9270000, 126480),
        ("11-1000", "Top Executives", "Management", 3000000, 200000),
        ("11-1011", "Chief Executives", "Management", 200000, 200000),
        ("15-1252", "Software Developers", "Computer and Mathematical", 1500000, 130000),
        ("29-1141", "Registered Nurses", "Healthcare Practitioners and Technical", 3000000, 80000),
        ("35-2014", "Cooks, Restaurant", "Food Preparation and Serving Related", 1300000, 32000),
        ("53-3032", "Heavy Truck Drivers", "Transportation and Material Moving", 2000000, 50000),
    ]
    for occ_code, occ_title, major_group, emp, wage in test_occs:
        db.insert_occupation(tmp_db, 2024, nat_id, occ_code, occ_title,
                             major_group, emp, wage)

    # One state with same occupations
    ca_id = db.ensure_region(tmp_db, cid, "California", "State")
    for occ_code, occ_title, major_group, emp, wage in test_occs:
        db.insert_occupation(tmp_db, 2024, ca_id, occ_code, occ_title,
                             major_group, int(emp * 0.12), wage)

    # One metro
    sf_id = db.ensure_region(tmp_db, cid,
                             "San Francisco-Oakland-Berkeley, CA", "Metro")
    for occ_code, occ_title, major_group, emp, wage in test_occs:
        db.insert_occupation(tmp_db, 2024, sf_id, occ_code, occ_title,
                             major_group, int(emp * 0.03), wage)

    tmp_db.commit()
    db.compute_complexity_scores(tmp_db)
    return tmp_db


class TestConfig:
    """Test configuration module."""

    def test_countries_defined(self):
        assert "USA" in config.COUNTRIES
        assert config.COUNTRIES["USA"]["code_system"] == "SOC"

    def test_metro_stem(self):
        result = config.metro_stem("new_york_newark_jersey_city_occupational_data.csv")
        assert result == "new_york_newark_jersey_city"

    def test_country_for_us_metro(self):
        assert config.country_for_metro("chicago_naperville_elgin") == "USA"

    def test_country_for_international_metro(self):
        assert config.country_for_metro("london") == "GBR"
        assert config.country_for_metro("mumbai") == "IND"
        assert config.country_for_metro("cairo") == "EGY"

    def test_display_name_for_state(self):
        assert config.display_name_for_state("california") == "California"
        assert config.display_name_for_state("new_york") == "New York"

    def test_display_name_for_metro(self):
        name = config.display_name_for_metro("new_york_newark_jersey_city")
        assert "New York" in name

    def test_json_level_path(self):
        path = config.json_level_path(2)
        assert path.name == "bls-data-level-2.json"
        assert "public" in str(path)

    def test_soc_major_group_colors(self):
        assert "11" in config.SOC_MAJOR_GROUP_COLORS
        assert len(config.SOC_MAJOR_GROUP_COLORS) == 22

    def test_country_short(self):
        assert config.country_short("USA") == "us"
        assert config.country_short("GBR") == "gb"
        assert config.country_short("IND") == "in"

    def test_json_country_year_path(self):
        path = config.json_country_year_path("us", 2024)
        assert path.name == "bls-data-us-2024.json"

    def test_json_country_year_level_path(self):
        path = config.json_country_year_level_path("us", 2024, 3)
        assert path.name == "bls-data-us-2024-3.json"

    def test_json_meta_path(self):
        path = config.json_meta_path()
        assert path.name == "bls-data.json"


class TestCodeDetection:
    """Test occupation code system detection."""

    def test_soc_detection(self):
        assert import_csv.detect_code_system("11-0000") == "SOC"
        assert import_csv.detect_code_system("53-7062") == "SOC"

    def test_isco_detection(self):
        assert import_csv.detect_code_system("OC1") == "ISCO"
        assert import_csv.detect_code_system("OC9") == "ISCO"

    def test_unknown_code_raises(self):
        with pytest.raises(ValueError):
            import_csv.detect_code_system("INVALID")


class TestMajorGroupDerivation:
    """Test major group name derivation."""

    def test_soc_major_group(self):
        result = import_csv.derive_major_group("11-0000", "Management", "SOC")
        assert result == "Management"

    def test_soc_lookup(self):
        result = import_csv.derive_major_group("15-1234", "Software Dev", "SOC")
        assert result == "Computer and Mathematical"

    def test_isco_uses_title(self):
        result = import_csv.derive_major_group("OC1", "Managers", "ISCO")
        assert result == "Managers"


class TestDatabase:
    """Test database operations."""

    def test_schema_creation(self, tmp_db):
        tables = tmp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = [t[0] for t in tables]
        assert "countries" in table_names
        assert "regions" in table_names
        assert "occupations" in table_names

    def test_ensure_country(self, tmp_db):
        cid = db.ensure_country(tmp_db, "USA", "United States", "SOC", "USD")
        assert cid > 0
        # Calling again should return same id
        cid2 = db.ensure_country(tmp_db, "USA", "United States", "SOC", "USD")
        assert cid == cid2

    def test_ensure_region(self, tmp_db):
        cid = db.ensure_country(tmp_db, "USA", "United States", "SOC")
        rid = db.ensure_region(tmp_db, cid, "California", "State")
        assert rid > 0

    def test_insert_occupation(self, tmp_db):
        cid = db.ensure_country(tmp_db, "USA", "United States", "SOC")
        rid = db.ensure_region(tmp_db, cid, "United States", "National")
        db.insert_occupation(
            tmp_db, 2024, rid, "11-0000", "Management",
            "Management", 9270, 126480,
        )
        tmp_db.commit()
        row = tmp_db.execute("SELECT gdp FROM occupations").fetchone()
        assert row[0] == 9270 * 126480

    def test_complexity_computation(self, tmp_db):
        cid = db.ensure_country(tmp_db, "USA", "United States", "SOC")
        rid = db.ensure_region(tmp_db, cid, "United States", "National")
        # Insert two records with different GDPs
        db.insert_occupation(tmp_db, 2024, rid, "11-0000", "Mgmt", "Mgmt", 100, 100)
        db.insert_occupation(tmp_db, 2024, rid, "13-0000", "Biz", "Biz", 200, 200)
        tmp_db.commit()
        db.compute_complexity_scores(tmp_db)
        rows = tmp_db.execute(
            "SELECT occupation_code, complexity_score FROM occupations "
            "ORDER BY occupation_code"
        ).fetchall()
        # 11-0000: gdp=10000 (min) -> 0.0
        # 13-0000: gdp=40000 (max) -> 1.0
        assert rows[0][1] == 0.0
        assert rows[1][1] == 1.0


class TestValidation:
    """Test validation checks."""

    def test_validate_db_passes(self, seeded_db):
        errors = validate.validate_db(seeded_db)
        assert errors == []

    def test_validate_db_catches_empty(self, tmp_db):
        db.create_schema(tmp_db)
        errors = validate.validate_db(tmp_db)
        assert any("No occupation records" in e for e in errors)


class TestExportJson:
    """Test frontend JSON export (legacy single-file API)."""

    def test_export_json_creates_file(self, seeded_db):
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            out_path = Path(f.name)

        try:
            count = export_json.export_json(seeded_db, ["USA"], out_path)
            assert count == 21  # 7 occupations * 3 regions

            data = json.loads(out_path.read_text(encoding="utf-8"))
            assert "metadata" in data
            assert "regions" in data
            assert "occupations" in data
            assert "majorGroups" in data
            assert "regionData" in data
            assert "aggregates" in data

            assert data["metadata"]["years"] == [2024]
            assert len(data["regions"]) == 3
            assert len(data["occupations"]) == 7
        finally:
            out_path.unlink(missing_ok=True)

    def test_export_json_occupation_levels(self, seeded_db):
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            out_path = Path(f.name)

        try:
            export_json.export_json(seeded_db, ["USA"], out_path)
            data = json.loads(out_path.read_text(encoding="utf-8"))

            # Check that occupations have correct levels
            for occ in data["occupations"]:
                assert "level" in occ
                assert occ["level"] in [1, 2, 3, 4, 5]
        finally:
            out_path.unlink(missing_ok=True)

    def test_export_json_region_data_structure(self, seeded_db):
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            out_path = Path(f.name)

        try:
            export_json.export_json(seeded_db, ["USA"], out_path)
            data = json.loads(out_path.read_text(encoding="utf-8"))

            # Check regionData has correct structure
            for rid, year_data in data["regionData"].items():
                for year_str, records in year_data.items():
                    for record in records:
                        assert "socCode" in record
                        assert "totEmp" in record
                        assert "gdp" in record
                        assert "aMean" in record
                        assert "complexity" in record
        finally:
            out_path.unlink(missing_ok=True)

    def test_export_json_aggregates(self, seeded_db):
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            out_path = Path(f.name)

        try:
            export_json.export_json(seeded_db, ["USA"], out_path)
            data = json.loads(out_path.read_text(encoding="utf-8"))

            assert "2024" in data["aggregates"]
            agg = data["aggregates"]["2024"]
            assert "byOccupation" in agg
            assert "minMaxStats" in agg
            stats = agg["minMaxStats"]
            assert stats["minWage"] > 0
            assert stats["maxWage"] >= stats["minWage"]
        finally:
            out_path.unlink(missing_ok=True)


class TestExportJsonLevels:
    """Test level-split JSON export."""

    def test_soc_level_calculation(self):
        from scripts.pipeline.export_json import _soc_level
        assert _soc_level("11-0000") == 1
        assert _soc_level("11-1000") == 2
        assert _soc_level("11-1100") == 3
        assert _soc_level("11-1110") == 4
        assert _soc_level("11-1011") == 5

    def test_level_filter_reduces_records(self, seeded_db):
        """Level-1 should have fewer occupations than full data."""
        from scripts.pipeline.export_json import _build_static_data, _query_records
        records = _query_records(seeded_db, ["USA"])

        # Full data: 7 occupations
        full_data = _build_static_data(records)
        assert len(full_data["occupations"]) == 7

        # Level 1 only: 1 occupation (11-0000)
        level1_data = _build_static_data(records, max_level=1)
        assert len(level1_data["occupations"]) == 1
        assert level1_data["occupations"][0]["socCode"] == "11-0000"

        # Level 2: 2 occupations (11-0000 + 11-1000)
        level2_data = _build_static_data(records, max_level=2)
        assert len(level2_data["occupations"]) == 2


class TestExportCountryTagged:
    """Test country-tagged JSON export (new format)."""

    def test_export_country_year(self, seeded_db):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "bls-data-us-2024.json"
            count = export_json.export_country_year(
                seeded_db, "USA", 2024, out_path
            )
            assert count > 0

            data = json.loads(out_path.read_text(encoding="utf-8"))
            assert data["metadata"]["country"] == "us"
            assert data["metadata"]["maxLevel"] == 2
            assert data["metadata"]["years"] == [2024]

            # Should only contain level 1 and 2 occupations
            for occ in data["occupations"]:
                assert occ["level"] <= 2

    def test_export_level_file(self, seeded_db):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "bls-data-us-2024-5.json"
            count = export_json.export_level_file(
                seeded_db, "USA", 2024, 5, out_path
            )
            # We have level-5 occupations in test data
            assert count > 0

            data = json.loads(out_path.read_text(encoding="utf-8"))
            assert data["metadata"]["level"] == 5

            # Should only contain exact level 5 occupations
            for occ in data["occupations"]:
                assert occ["level"] == 5

    def test_export_level_file_empty_level(self, seeded_db):
        """Level 3 should have 0 records (no XX-XX00 codes in test data)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "bls-data-us-2024-3.json"
            count = export_json.export_level_file(
                seeded_db, "USA", 2024, 3, out_path
            )
            assert count == 0
            # File should not be created for empty levels
            assert not out_path.exists()

    def test_export_meta(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "bls-data.json"
            export_json.export_meta([{
                "country_code": "USA",
                "country_short": "us",
                "country_name": "United States",
                "year": 2024,
                "levels_available": [3, 4, 5],
            }], out_path)

            data = json.loads(out_path.read_text(encoding="utf-8"))
            assert len(data["datasets"]) == 1
            assert data["datasets"][0]["country"] == "us"
            assert data["datasets"][0]["year"] == 2024
            assert data["datasets"][0]["file"] == "bls-data-us-2024.json"
            assert data["years"] == [2024]
            assert data["countries"] == [{"code": "us", "name": "United States"}]

            # Level files
            lf = data["levelFiles"]["us-2024"]
            assert lf["3"] == "bls-data-us-2024-3.json"
            assert lf["4"] == "bls-data-us-2024-4.json"
            assert lf["5"] == "bls-data-us-2024-5.json"

    def test_export_all(self, seeded_db):
        """Integration test: export_all produces all expected files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Temporarily override config paths to use tmpdir
            import scripts.pipeline.config as cfg
            orig_pub = cfg.PUBLIC_DATA_DIR
            cfg.PUBLIC_DATA_DIR = Path(tmpdir)

            try:
                stats = export_json.export_all(seeded_db, "USA", 2024)
                assert stats["main_count"] > 0

                # Check meta file exists
                meta_path = Path(tmpdir) / "bls-data.json"
                assert meta_path.exists()

                # Check main file exists
                main_path = Path(tmpdir) / "bls-data-us-2024.json"
                assert main_path.exists()

                # Verify main file has only levels 1+2
                main_data = json.loads(main_path.read_text())
                for occ in main_data["occupations"]:
                    assert occ["level"] <= 2

                # Check levels in data
                assert 1 in stats["levels_available"]
                assert 5 in stats["levels_available"]
            finally:
                cfg.PUBLIC_DATA_DIR = orig_pub


class TestExactLevelFilter:
    """Test the exact_level filter in _build_static_data."""

    def test_exact_level_5(self, seeded_db):
        from scripts.pipeline.export_json import _build_static_data, _query_records
        records = _query_records(seeded_db, ["USA"])
        data = _build_static_data(records, exact_level=5)

        # All test occupations at level 5: 11-1011, 15-1252, 29-1141, 35-2014, 53-3032
        assert len(data["occupations"]) == 5
        for occ in data["occupations"]:
            assert occ["level"] == 5

    def test_exact_level_1(self, seeded_db):
        from scripts.pipeline.export_json import _build_static_data, _query_records
        records = _query_records(seeded_db, ["USA"])
        data = _build_static_data(records, exact_level=1)

        # Only 11-0000 is level 1
        assert len(data["occupations"]) == 1
        assert data["occupations"][0]["socCode"] == "11-0000"


class TestExportSplit:
    """Test split data export (meta.js + per-region files)."""

    def test_export_split_creates_files(self, seeded_db):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            stats = export_split.export_split(seeded_db, ["USA"], out)
            assert stats["region_count"] == 3
            assert stats["occ_count"] == 7
            assert (out / "meta.js").exists()
            region_files = list((out / "regions").glob("*.data.js"))
            assert len(region_files) == 3

    def test_meta_structure(self, seeded_db):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            export_split.export_split(seeded_db, ["USA"], out)
            content = (out / "meta.js").read_text(encoding="utf-8")
            assert content.startswith("window.BLS_META = ")
            assert content.rstrip().endswith(";")

            json_str = content.replace("window.BLS_META = ", "").rstrip().rstrip(";")
            meta = json.loads(json_str)
            assert meta["years"] == [2024]
            assert len(meta["occ"]) == 7
            assert "National" in meta["regions"]

    def test_slug_generation(self):
        assert export_split._make_slug("State", "California") == "state-california"
        assert export_split._make_slug("State", "New York") == "state-new_york"
        assert export_split._make_slug("National", "United States") == "national-united_states"
        assert export_split._make_slug("Metro", "Atlanta-Sandy Springs-Alpharetta, GA") == "metro-atlanta"
        assert export_split._make_slug("Metro", "St. Louis, MO-IL") == "metro-st_louis"


class TestValidateJson:
    """Test JSON validation."""

    def test_validate_json_passes(self, seeded_db):
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            out_path = Path(f.name)

        try:
            export_json.export_json(seeded_db, ["USA"], out_path)
            errors = validate.validate_json(out_path)
            assert errors == [], f"Validation errors: {errors}"
        finally:
            out_path.unlink(missing_ok=True)

    def test_validate_json_catches_missing_file(self):
        errors = validate.validate_json(Path("/nonexistent/file.json"))
        assert any("not found" in e for e in errors)

    def test_validate_country_year_json(self, seeded_db):
        """Country-year JSON files should also pass validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "bls-data-us-2024.json"
            export_json.export_country_year(seeded_db, "USA", 2024, out_path)
            errors = validate.validate_json(out_path)
            assert errors == [], f"Validation errors: {errors}"
