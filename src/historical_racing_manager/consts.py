# --- Contract defaults ---
DEFAULT_SALARY_BASE = 25_000
SALARY_REPUTATION_MULTIPLIER = 100
HUMAN_CONTRACT_DECISION_DAYS = 1

# --- Car part contract settings ---
DEFAULT_CONTRACT_MIN_LENGTH = 1
DEFAULT_CONTRACT_MAX_LENGTH = 4
AI_CONTRACT_LENGTHS = [1, 2, 3, 4]
AI_CONTRACT_WEIGHTS = [40, 30, 20, 10]  # % chance

# --- Driver salary rules ---
MIN_SALARY_BASE = 4_000_000  # base for calculate drivers price
# --- Simulation timeline ---
DEFAULT_BEGIN_YEAR = 1843
DEFAULT_END_YEAR = 3000
DEFAULT_SIM_YEARS_STEP = 36
DEFAULT_DRIVERS_PER_YEAR = 4

# --- Dates ---
SEASON_START_MONTH = 1
SEASON_START_DAY = 1
FIRST_REAL_SEASON_YEAR = 1894
FIRST_RACE_PLANNING_YEAR = 1896

# ====== DRIVER CONSTANTS ======

# Driver ability limits
DRIVER_ABILITY_MIN = 36
DRIVER_ABILITY_MAX = 69

# Driver age limits
DRIVER_MIN_AGE = 15
DRIVER_RETIRE_MIN_AGE = 30
DRIVER_RETIRE_MAX_AGE = 59

# Driver ability progression
ABILITY_CHANGE_SEQUENCE = [
    4, 4, 3, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1, 1, 0, 0,
    -1, -1, -1, -1, -1, -2, -2, -2, -2, -3, -3, -3,
    -4, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13,
    -14, -15, -16, -17, -18, -19, -20
]

# Driver generation
DRIVER_ABILITY_DISTRIBUTION_START = 69
DRIVER_ABILITY_DISTRIBUTION_END = 36

# Driver file
DRIVERS_FILE = "drivers.csv"
# ====== UI CONFIGURATION ======

# Window settings
WINDOW_TITLE = "Historical Racing Manager"
WINDOW_SIZE = "1600x900"

# Appearance
DEFAULT_THEME = "System"
DEFAULT_COLOR_THEME = "blue"

# Tabs
TAB_NAMES = ["Game", "Drivers", "Teams", "Manufacturers", "Series", "Seasons", "My Team"]

# Fonts
FONT_HEADER = ("Arial", 18, "bold")
FONT_SUBHEADER = ("Arial", 14, "bold")
FONT_TEXT = ("Arial", 13)
FONT_SMALL = ("Arial", 12)

# Team Selector
TEAM_SELECTOR_WIDTH = 250

# Simulation Steps
SIMULATION_STEPS = {
    "Next Day": 1,
    "Next Week": 7,
    "Next Race": 365
}

# Contract
CONTRACT_MIN_LENGTH = 1
CONTRACT_MAX_LENGTH = 4
DEFAULT_SALARY = 10000

# Car Part Contracts
CONTRACT_YEARS = ["Current Year", "Next Year"]
PART_TYPES = ["engine", "chassi", "pneu"]

# UI Labels for DataFrames
COLUMN_LABELS = {
    "forename": "First Name",
    "surname": "Last Name",
    "nationality": "Nationality",
    "age": "Age",
    "salary": "Salary",
    "startYear": "Start Year",
    "endYear": "End Year",
    "partType": "Part Type",
    "cost": "Cost",
    "name": "Component Name",
    "staff": "Staff",
    "car": "Car",
    "date": "Race Date",
    "race": "Race Name",
    "department": "Department",
    "employees": "Employees",
    "team": "Team"
}

# --- Required files for ManufacturerModel ---
MANUFACTURER_REQUIRED_FILES = [
    "car_parts.csv",
    "cars.csv",
    "manufacturers.csv",
    "car_part_models.csv",
    "rules.csv",
]

# --- Merge keys used when generating new parts ---
MERGE_KEYS = ["rulesID", "manufacturerID", "partType", "seriesID"]

# --- Default cost of generated parts ---
DEFAULT_PART_COST = 250_000

# --- Random improvement ranges ---
RANDOM_POWER_MIN = 0
RANDOM_POWER_MAX = 8

RANDOM_RELIABILITY_MIN = 0
RANDOM_RELIABILITY_MAX = 9

RANDOM_SAFETY_MIN = 0
RANDOM_SAFETY_MAX = 9

# --- Required files for RaceModel ---
RACE_REQUIRED_FILES = [
    "stands.csv",
    "races.csv",
    "pointSystem.csv",
    "results.csv",
    "circuits.csv",
    "circuit_layouts.csv",
]

# --- Simulation scheduling constants ---
DAYS_PER_SEASON = 364
RACE_WEEKDAY = "Sun"
RACE_INTERVAL_WEEKS = 5
CHAMPIONSHIP_INTERVAL_WEEKS = 6

# --- Rain generation ---
RAIN_TRIGGER_MIN = 1
RAIN_TRIGGER_MAX = 8
RAIN_STRENGTH_MIN = 1
RAIN_STRENGTH_MAX = 50

# --- Ranking randomness ---
RNG_PICK_MAX = 9
RNG_PICK_THRESHOLD = 3

# --- Outcome randomness ---
SPEED_RANDOM_MULTIPLIER = 1000

# --- Result codes ---
CRASH_CODE = 999
DEATH_CODE = 998

# --- Series model files ----
SERIES_FILE = "series.csv"
POINT_RULES_FILE = "point_rules.csv"

# --- Column names for series ---
COL_SERIES_ID = "seriesID"
COL_SERIES_NAME = "name"
COL_SERIES_START = "startYear"
COL_SERIES_END = "endYear"

# --- Column names for point rules ---
COL_RULE_SERIES_ID = "seriesID"
COL_RULE_START = "startSeason"
COL_RULE_END = "endSeason"

# ===== Teams Model =====
TEAMS_FILE = "teams.csv"

COL_TEAM_ID = "teamID"
COL_TEAM_NAME = "team_name"
COL_OWNER_ID = "owner_id"
COL_MONEY = "money"
COL_FINANCE_EMP = "finance_employees"
COL_DESIGN_EMP = "design_employees"
COL_REPUTATION = "reputation"
COL_FOUND = "found"
COL_FOLDED = "folded"

FINANCE_EMPLOYEE_SALARY = 2500
KICK_EMPLOYEE_PRICE = 1000

DEFAULT_FOUND_YEAR = 1800
DEFAULT_FOLDED_YEAR = 3000

FINANCE_EARN_COEF = [
    12000, 11000, 10000, 9000, 8000,
    7000, 6000, 5000, 4000, 3000,
    2000, 1000, 0
]
