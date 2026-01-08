# Historical Racing Manager

**Historical Racing Manager** is a Python-based management game that lets you take control of a racing team throughout
motorsport history.  
Hire drivers, sign contracts with manufacturers, develop your own car parts, and lead your team to glory across decades
of racing evolution.

---

## Installation

### Prerequisites

- Python 3.11 or newer
- pip (Python package manager)

### Clone the repository

```bash
git clone https://github.com/<scirafra>/historical-racing-manager.git
cd historical-racing-manager
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Install as a package

```bash
pip install .
```

Alternatively, you can use pip with the `-e` option for editable installs during development:

```bash
pip install -e .
```

## Usage

Run the game as module:

```bash
python -m historical_racing_manager
```

or, as installed command:

```bash
historical-racing-manager
```

### Game Overview

- **Team Management**: Hire drivers, manage contracts, and invest in your team's growth.
- **Racing Simulation**: Simulate historical races year by year.
- **Manufacturers & Parts**: Sign supplier contracts.
- **Financial System**: Balance income, expenses, and marketing investments.
- **Historical Progression**: Experience how motorsport evolves over time.

## Building a Standalone Executable (PyInstaller)

If you want to distribute the game as a single executable file (without requiring Python), you can use PyInstaller.

### Install PyInstaller

```bash
pip install pyinstaller
```

### Build the executable

```bash
pyinstaller --onefile --windowed main.py
```

After the build completes, the executable will be located in:

```bash
dist/
```

## Testing

Run unit tests using pytest:

```bash
pytest
```

## License

This project is released under the [MIT License](./LICENCE). See the LICENCE file for details.

## Author

František Sciranka
