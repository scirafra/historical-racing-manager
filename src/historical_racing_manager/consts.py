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
    "Next Week": 7
}
SIMULATION_NEXT_RACE = "Next Race"

# UI Labels for DataFrames
COLUMN_LABELS = {
    "forename": "First Name",
    "surname": "Last Name",
    "nationality": "Nationality",
    "age": "Age",
    "salary": "Salary",
    "start_year": "Start Year",
    "end_year": "End Year",
    "part_type": "Part Type",
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
FILE_CAR_PARTS = "car_parts.csv"
FILE_CARS = "cars.csv"
FILE_MANUFACTURERS = "manufacturers.csv"
FILE_CAR_PART_MODELS = "car_part_models.csv"
FILE_RULES = "rules.csv"
MANUFACTURER_REQUIRED_FILES = [
    FILE_CAR_PARTS,
    FILE_CARS,
    FILE_MANUFACTURERS,
    FILE_CAR_PART_MODELS,
    FILE_RULES,
]
# --- Required files for ContractsModel ---
FILE_DT_CONTRACT = "dt_contract.csv"  # Driver–Team contracts
FILE_ST_CONTRACT = "st_contract.csv"  # Staff–Team contracts
FILE_CS_CONTRACT = "cs_contract.csv"  # Car–Series contracts
FILE_MS_CONTRACT = "ms_contract.csv"  # Manufacturer–Series contracts
FILE_MT_CONTRACT = "mt_contract.csv"  # Manufacturer–Team contracts

CONTRACTS_REQUIRED_FILES = [
    FILE_DT_CONTRACT,
    FILE_ST_CONTRACT,
    FILE_CS_CONTRACT,
    FILE_MS_CONTRACT,
    FILE_MT_CONTRACT,
]

# --- Merge keys used when generating new parts ---
MERGE_KEYS = ["rules_id", "manufacture_id", "part_type", "series_id"]

# --- Default cost of generated parts ---
DEFAULT_PART_COST = 250_000

# --- Random improvement ranges ---
UPGRADE_POWER_MIN = 0
UPGRADE_POWER_MAX = 8

UPGRADE_RELIABILITY_MIN = 0
UPGRADE_RELIABILITY_MAX = 9

UPGRADE_SAFETY_MIN = 0
UPGRADE_SAFETY_MAX = 9

# --- Required files for RaceModel ---
FILE_STANDS = "stands.csv"
FILE_RACES = "races.csv"
FILE_POINT_SYSTEM = "point_system.csv"
FILE_RESULTS = "results.csv"
FILE_CIRCUITS = "circuits.csv"
FILE_CIRCUIT_LAYOUTS = "circuit_layouts.csv"

RACE_REQUIRED_FILES = [
    FILE_STANDS,
    FILE_RACES,
    FILE_POINT_SYSTEM,
    FILE_RESULTS,
    FILE_CIRCUITS,
    FILE_CIRCUIT_LAYOUTS,
]
# --- Required files for Controller save/load ---
FILE_CONTROLLER_DATA = "data.csv"
FILE_CONTROLLER_GENERATED_RACES = "generated_races.csv"

CONTROLLER_REQUIRED_FILES = [
    FILE_CONTROLLER_DATA,
    FILE_CONTROLLER_GENERATED_RACES,
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
SPEED_MULTIPLIER = 1000

# --- Result codes ---
CRASH_CODE = 999
DEATH_CODE = 998

# --- Series model files ----
SERIES_FILE = "series.csv"
POINT_RULES_FILE = "point_rules.csv"

# --- Column names for series ---
COL_SERIES_ID = "series_id"
COL_SERIES_NAME = "name"
COL_SERIES_START = "start_year"
COL_SERIES_END = "end_year"

# --- Column names for point rules ---
COL_RULE_SERIES_ID = "series_id"
COL_RULE_START = "start_season"
COL_RULE_END = "end_season"

# ===== Teams Model =====
TEAMS_FILE = "teams.csv"

COL_TEAM_ID = "team_id"
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

# ===== CONTRACTS MODEL CONSTANTS =====

# Contract lengths
CONTRACT_MIN_LENGTH = 1
CONTRACT_MAX_LENGTH = 4

# AI contract preferences
AI_CONTRACT_LENGTHS = [1, 2, 3, 4]
AI_CONTRACT_WEIGHTS = [40, 30, 20, 10]  # probability distribution

# Salary rules
DEFAULT_SALARY = 10000
DEFAULT_SALARY_BASE = 25_000
SALARY_REPUTATION_MULTIPLIER = 100
MIN_SALARY_BASE = 4_000_000  # base for calculating driver price

# Human contract decision delay
CONTRACT_DECISION_DAYS = 1

# Car part contract types
CONTRACT_YEARS = ["Current Year", "Next Year"]
PART_TYPES = ["engine", "chassi", "pneu"]
