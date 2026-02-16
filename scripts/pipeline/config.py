"""Country registry, metro-to-country mapping, and SOC group names."""

from pathlib import Path

# Project root (two levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "bls.db"
EXPORT_DIR = DATA_DIR / "export"
RAW_DIR = DATA_DIR / "raw"
PUBLIC_DATA_DIR = PROJECT_ROOT / "public" / "data"

# JSONP path (for bls2-compatible export, kept for reference)
JSONP_PATH = DATA_DIR / "job_data.js"

# JSON output paths (for metroverse-jobs frontend)
JSON_FULL_PATH = PUBLIC_DATA_DIR / "bls-data.json"

# BLS OES bulk download URLs (YY = 2-digit year)
BLS_BASE_URL = "https://www.bls.gov/oes/special-requests"
ONET_BASE_URL = "https://www.onetcenter.org/dl_files/database"

# Country configurations
COUNTRIES = {
    "USA": {
        "name": "United States",
        "code_system": "SOC",
        "currency": "USD",
        "national_csv": DATA_DIR / "us_occupational_data.csv",
        "states_dir": DATA_DIR / "states",
        "national_region_name": "United States",
    },
    "GBR": {
        "name": "United Kingdom",
        "code_system": "ISCO",
        "currency": "GBP",
        "national_csv": DATA_DIR / "gbr_occupational_data.csv",
        "national_region_name": "United Kingdom",
    },
    "IND": {
        "name": "India",
        "code_system": "ISCO",
        "currency": "INR",
        "national_csv": DATA_DIR / "ind_occupational_data.csv",
        "national_region_name": "India",
    },
    "EGY": {
        "name": "Egypt",
        "code_system": "ISCO",
        "currency": "EGP",
        "national_csv": DATA_DIR / "egy_occupational_data.csv",
        "national_region_name": "Egypt",
    },
    "CAN": {
        "name": "Canada",
        "code_system": "ISCO",
        "currency": "CAD",
        "national_csv": DATA_DIR / "can_occupational_data.csv",
        "national_region_name": "Canada",
    },
    "MEX": {
        "name": "Mexico",
        "code_system": "ISCO",
        "currency": "MXN",
        "national_csv": DATA_DIR / "mex_occupational_data.csv",
        "national_region_name": "Mexico",
    },
    "EUU": {
        "name": "European Union",
        "code_system": "ISCO",
        "currency": "EUR",
        "national_csv": DATA_DIR / "eu_occupational_data.csv",
        "national_region_name": "European Union",
    },
}

# Map metro CSV file stems to country codes.
# US metros are not listed here — any metro not in this map defaults to USA.
METRO_COUNTRY_MAP = {
    "london": "GBR",
    "paris": "EUU",
    "berlin": "EUU",
    "madrid": "EUU",
    "rome": "EUU",
    "toronto": "CAN",
    "montreal": "CAN",
    "vancouver": "CAN",
    "mexico_city": "MEX",
    "guadalajara": "MEX",
    "monterrey": "MEX",
    "mumbai": "IND",
    "delhi": "IND",
    "bangalore": "IND",
    "cairo": "EGY",
    "alexandria": "EGY",
}

# Map metro CSV file stems to display names.
# Only entries that need explicit mapping; others derived from filename.
METRO_DISPLAY_NAMES = {
    "new_york_newark_jersey_city": "New York-Newark-Jersey City, NY-NJ-PA",
    "los_angeles_long_beach_anaheim": "Los Angeles-Long Beach-Anaheim, CA",
    "chicago_naperville_elgin": "Chicago-Naperville-Elgin, IL-IN-WI",
    "dallas_fort_worth_arlington": "Dallas-Fort Worth-Arlington, TX",
    "houston_the_woodlands_sugar_land": "Houston-The Woodlands-Sugar Land, TX",
    "washington_arlington_alexandria": "Washington-Arlington-Alexandria, DC-VA-MD-WV",
    "miami_fort_lauderdale_pompano_beach": "Miami-Fort Lauderdale-Pompano Beach, FL",
    "philadelphia_camden_wilmington": "Philadelphia-Camden-Wilmington, PA-NJ-DE-MD",
    "atlanta_sandy_springs_alpharetta": "Atlanta-Sandy Springs-Alpharetta, GA",
    "boston_cambridge_newton": "Boston-Cambridge-Newton, MA-NH",
    "phoenix_mesa_chandler": "Phoenix-Mesa-Chandler, AZ",
    "san_francisco_oakland_berkeley": "San Francisco-Oakland-Berkeley, CA",
    "riverside_san_bernardino_ontario": "Riverside-San Bernardino-Ontario, CA",
    "detroit_warren_dearborn": "Detroit-Warren-Dearborn, MI",
    "seattle_tacoma_bellevue": "Seattle-Tacoma-Bellevue, WA",
    "minneapolis_st._paul_bloomington": "Minneapolis-St. Paul-Bloomington, MN-WI",
    "san_diego_chula_vista_carlsbad": "San Diego-Chula Vista-Carlsbad, CA",
    "tampa_st._petersburg_clearwater": "Tampa-St. Petersburg-Clearwater, FL",
    "denver_aurora_lakewood": "Denver-Aurora-Lakewood, CO",
    "st._louis": "St. Louis, MO-IL",
    "baltimore_columbia_towson": "Baltimore-Columbia-Towson, MD",
    "london": "London",
    "paris": "Paris",
    "berlin": "Berlin",
    "madrid": "Madrid",
    "rome": "Rome",
    "toronto": "Toronto",
    "montreal": "Montreal",
    "vancouver": "Vancouver",
    "mexico_city": "Mexico City",
    "guadalajara": "Guadalajara",
    "monterrey": "Monterrey",
    "mumbai": "Mumbai",
    "delhi": "Delhi",
    "bangalore": "Bangalore",
    "cairo": "Cairo",
    "alexandria": "Alexandria",
}

# SOC major group names (US BLS)
SOC_MAJOR_GROUPS = {
    "11": "Management",
    "13": "Business and Financial Operations",
    "15": "Computer and Mathematical",
    "17": "Architecture and Engineering",
    "19": "Life, Physical, and Social Science",
    "21": "Community and Social Service",
    "23": "Legal",
    "25": "Educational Instruction and Library",
    "27": "Arts, Design, Entertainment, Sports, and Media",
    "29": "Healthcare Practitioners and Technical",
    "31": "Healthcare Support",
    "33": "Protective Service",
    "35": "Food Preparation and Serving Related",
    "37": "Building and Grounds Cleaning and Maintenance",
    "39": "Personal Care and Service",
    "41": "Sales and Related",
    "43": "Office and Administrative Support",
    "45": "Farming, Fishing, and Forestry",
    "47": "Construction and Extraction",
    "49": "Installation, Maintenance, and Repair",
    "51": "Production",
    "53": "Transportation and Material Moving",
}

# SOC Major Group colors (for frontend visualization)
SOC_MAJOR_GROUP_COLORS = {
    "11": "#A973BE",  # Management - Purple
    "13": "#F1866C",  # Business and Financial - Coral
    "15": "#488098",  # Computer and Mathematical - Steel Blue
    "17": "#6A6AAD",  # Architecture and Engineering - Indigo
    "19": "#77C898",  # Life, Physical, Social Science - Green
    "21": "#93CFD0",  # Community and Social Service - Teal
    "23": "#D35162",  # Legal - Crimson
    "25": "#FFC135",  # Educational Instruction - Gold
    "27": "#F28188",  # Arts, Design, Entertainment - Pink
    "29": "#5B9BD5",  # Healthcare Practitioners - Blue
    "31": "#70AD47",  # Healthcare Support - Lime Green
    "33": "#BF8F00",  # Protective Service - Dark Gold
    "35": "#ED7D31",  # Food Preparation - Orange
    "37": "#8DB4E2",  # Building and Grounds - Light Blue
    "39": "#C5B0D5",  # Personal Care - Lavender
    "41": "#FF6B6B",  # Sales - Red
    "43": "#4ECDC4",  # Office and Administrative - Cyan
    "45": "#556B2F",  # Farming, Fishing, Forestry - Olive
    "47": "#DAA520",  # Construction - Goldenrod
    "49": "#708090",  # Installation, Maintenance - Slate Gray
    "51": "#CD853F",  # Production - Peru
    "53": "#9370DB",  # Transportation - Medium Purple
}

# State filename stem to display name mapping
STATE_DISPLAY_NAMES = {
    "alabama": "Alabama",
    "alaska": "Alaska",
    "arizona": "Arizona",
    "arkansas": "Arkansas",
    "california": "California",
    "colorado": "Colorado",
    "connecticut": "Connecticut",
    "delaware": "Delaware",
    "florida": "Florida",
    "georgia": "Georgia",
    "hawaii": "Hawaii",
    "idaho": "Idaho",
    "illinois": "Illinois",
    "indiana": "Indiana",
    "iowa": "Iowa",
    "kansas": "Kansas",
    "kentucky": "Kentucky",
    "louisiana": "Louisiana",
    "maine": "Maine",
    "maryland": "Maryland",
    "massachusetts": "Massachusetts",
    "michigan": "Michigan",
    "minnesota": "Minnesota",
    "mississippi": "Mississippi",
    "missouri": "Missouri",
    "montana": "Montana",
    "nebraska": "Nebraska",
    "nevada": "Nevada",
    "new_hampshire": "New Hampshire",
    "new_jersey": "New Jersey",
    "new_mexico": "New Mexico",
    "new_york": "New York",
    "north_carolina": "North Carolina",
    "north_dakota": "North Dakota",
    "ohio": "Ohio",
    "oklahoma": "Oklahoma",
    "oregon": "Oregon",
    "pennsylvania": "Pennsylvania",
    "rhode_island": "Rhode Island",
    "south_carolina": "South Carolina",
    "south_dakota": "South Dakota",
    "tennessee": "Tennessee",
    "texas": "Texas",
    "utah": "Utah",
    "vermont": "Vermont",
    "virginia": "Virginia",
    "washington": "Washington",
    "west_virginia": "West Virginia",
    "wisconsin": "Wisconsin",
    "wyoming": "Wyoming",
}


def metro_stem(filename: str) -> str:
    """Extract the metro stem from a CSV filename.

    'new_york_newark_jersey_city_occupational_data.csv' -> 'new_york_newark_jersey_city'
    """
    return filename.replace("_occupational_data.csv", "")


def country_for_metro(stem: str) -> str:
    """Return country code for a metro stem. Defaults to USA."""
    # Check exact match first
    if stem in METRO_COUNTRY_MAP:
        return METRO_COUNTRY_MAP[stem]
    # Check if stem starts with any known international metro
    for known_metro, country in METRO_COUNTRY_MAP.items():
        if stem.startswith(known_metro):
            return country
    return "USA"


def display_name_for_metro(stem: str) -> str:
    """Return display name for a metro. Falls back to title-casing the stem."""
    if stem in METRO_DISPLAY_NAMES:
        return METRO_DISPLAY_NAMES[stem]
    # Fallback: title-case with hyphens
    return stem.replace("_", " ").title()


def display_name_for_state(stem: str) -> str:
    """Return display name for a state. Falls back to title-casing."""
    if stem in STATE_DISPLAY_NAMES:
        return STATE_DISPLAY_NAMES[stem]
    return stem.replace("_", " ").title()


def country_short(code: str) -> str:
    """Convert 3-letter country code to 2-letter short form.

    USA -> us, GBR -> gb, etc.
    """
    mapping = {
        "USA": "us", "GBR": "gb", "IND": "in", "EGY": "eg",
        "CAN": "ca", "MEX": "mx", "EUU": "eu",
    }
    return mapping.get(code, code.lower()[:2])


def json_level_path(level: int) -> Path:
    """Return path for a level-specific split JSON file."""
    return PUBLIC_DATA_DIR / f"bls-data-level-{level}.json"


def json_country_year_path(country: str, year: int) -> Path:
    """Return path for a country-year main JSON file (levels 1+2)."""
    return PUBLIC_DATA_DIR / f"bls-data-{country}-{year}.json"


def json_country_year_level_path(country: str, year: int, level: int) -> Path:
    """Return path for a country-year-level extension JSON file."""
    return PUBLIC_DATA_DIR / f"bls-data-{country}-{year}-{level}.json"


def json_meta_path() -> Path:
    """Return path for the meta catalog file."""
    return PUBLIC_DATA_DIR / "bls-data.json"
