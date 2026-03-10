**English** | [Русский](README.ru.md)

# Python Embeddable Manager

A manager for portable Python versions on Windows: downloads the **embeddable package** from python.org into a chosen folder and lets you run them without installing Python system-wide.

## Why use it

- One folder with all needed versions (3.10, 3.11, 3.12, etc.)
- Does not touch the system Python installation
- Handy for CI, portable builds, and testing under different versions
- Can be put on a USB stick or in a repo (without the binaries themselves)

## Requirements

- Windows (embeddable packages are only available for Windows)
- Any installed Python 3.x to run the manager (or download one embed once and run the manager with it — see below)

If the console shows garbled characters instead of your locale, run once: `chcp 65001` or set `PYTHONIOENCODING=utf-8`.

## Computer without Python

On a machine with no Python installed, the manager cannot run by itself (`python run.py` and `pyembed` need an interpreter). You need a **one-time manual bootstrap**:

1. **Download one embeddable archive** from python.org, e.g.:
   - 64-bit: https://www.python.org/ftp/python/3.12.0/python-3.12.0-embed-amd64.zip  
   - 32-bit: replace `amd64` with `win32` in the URL.

2. **Extract** the archive to any folder (e.g. `C:\py\3.12.0`). It should contain `python.exe` and other files.

3. **Copy the PythonManager project** to this computer (folder with `run.py`, `pyembed/`, etc.).

4. **Run the manager with that Python:**
   ```bat
   C:\py\3.12.0\python.exe run.py list
   C:\py\3.12.0\python.exe run.py install 3.14.3 --pip
   ```
   After that you can install other versions via the manager and use them as usual.

5. **(Optional)** Add the bootstrap Python folder or project folder to PATH so you don’t have to type the full path every time.

The “first” version is then only used to run the manager; all other versions you get via `install`.

### Automatic bootstrap

On a clean machine you can **skip manual steps 1–4**: run **`bootstrap.bat`** or **`.\bootstrap.ps1`** from the project folder. The script:

- checks whether the system has Python or an already downloaded version in `pythons\`;
- if not — downloads embed **3.12.0** from python.org (64- or 32-bit per system) to `pythons\3.12.0` and extracts it;
- then runs the manager with the arguments you passed.

Examples:
```bat
bootstrap.bat
bootstrap.bat list
bootstrap.bat install 3.14.3 --pip
```
Double-clicking `bootstrap.bat` opens the manager menu (or downloads 3.12.0 on first run, then the menu).

## Installation

Clone the repo or download an archive, then go to the project folder:

```bash
git clone <repo-url> PythonManager
cd PythonManager
pip install -e .
```

Or without installing the package: `pip install -r requirements.txt` (no real dependencies, for compatibility only) and run `python run.py` from the project folder. After `pip install -e .` the **`pyembed`** command is available from anywhere (if Scripts is in PATH).

## Interactive menu

Running **with no arguments** opens an **interactive menu** (script stays open):

- Shows installed versions (and `[pip]` if pip is installed)
- **1** — Download a version (with optional pip install)
- **2** — Remove a version
- **3** — Pip: install/list packages for selected version
- **4** — Install pip into an already installed version
- **5** — Packages (list / install / remove)
- **6** — Create venv (virtual environment)
- **7** — PATH: add/remove version or fix duplicates (Windows)
- **8** — Version info (path, pip, size, PATH)
- **9** — Cache (list / clear)
- **10** — Upgrade pip in version
- **11** — Copy version to folder (e.g. C:/Python/3.15) and to PATH
- **12** — Exit

In items 2–11 you can enter the version by number from the list (1, 2, …) or by string (3.12.0).

From the project folder: `pyembed.bat` or `.\pyembed.ps1`. With arguments — same commands as `python run.py` (list, install, pip, packages, path, add-pip, uninstall, run, use). To run from any folder, add the project directory to PATH.

## Usage

Default root folder for versions: `PythonManager\pythons`. You can change it with the `PYEMBED_ROOT` environment variable or the `--root` flag.

### All commands (summary)

| Command | Description |
|---------|-------------|
| `list` | Installed versions; `-a` — available on python.org |
| `install <version> [--pip] [-y]` | Download and extract; `-y` — no prompt after install |
| `which [version]` | Path to python.exe |
| `path show/add/remove/list/fix-duplicates` | Path and PATH management (Windows); fix-duplicates — remove duplicates |
| `packages <version> list/add/remove` | Packages (pip) for version |
| `pip <version> <args>` | Run pip for version |
| `venv <version> [name]` | Create virtual environment |
| `run <version> [args]` | Run this Python version |
| `use <version>` | Hint: how to add to PATH |
| `default [version]` | Default version for run/which/path show |
| `verify [version]` | Verify installation integrity |
| `info [version]` | Path, pip, size, in PATH |
| `cache list/clear [version]` | Archive cache |
| `upgrade-pip [version]` | Upgrade pip in version |
| `add-pip <version>` | Install pip into already installed version |
| `uninstall <version> [-y]` | Remove version (shows size before confirmation) |
| `copy <version> [folder] [--force] [--no-path] [--dry-run]` | Copy version to folder and to PATH (Windows); `--dry-run` — show plan only |
| `doctor [--fix]` | Check: python.org, disk, version integrity, PATH (duplicates and missing dirs); --fix — fix |
| `ide [version] [--json]` | Path for Cursor/VS Code (python.defaultInterpreterPath); --json — snippet for settings.json |

```bash
# Show installed versions
pyembed.bat list
# or: python run.py list

# Show versions available on python.org
pyembed.bat list -a

# Download and extract Python 3.12.0
pyembed.bat install 3.12.0

# Download with pip installed for this version
pyembed.bat install 3.12.0 --pip
# No prompt after install (for CI/scripts)
pyembed.bat install 3.12.0 --pip -y

# Path to python.exe and PATH management (Windows)
pyembed.bat which 3.12.0         # path to python.exe (handy for scripts and CI)
pyembed.bat which 3.12.0 -c      # path and copy to clipboard
pyembed.bat path show 3.12.0
pyembed.bat path show -c         # default path and copy to clipboard
pyembed.bat path add 3.12.0      # add to user PATH
pyembed.bat path remove 3.12.0   # remove from PATH
pyembed.bat path list            # which versions from this root are in PATH
pyembed.bat path fix-duplicates  # remove duplicate PATH entries

# Copy version to folder (e.g. C:/Python/3.15) and add to PATH
pyembed.bat copy 3.15.0                    # default C:/Python/3.15.0
pyembed.bat copy 3.15.0 C:/Python/3.15     # specify folder
pyembed.bat copy 3.15.0 --force            # overwrite if folder exists
pyembed.bat copy 3.15.0 C:/Python/3.15 --no-path  # don't add to PATH

# Package (pip) management for version
pyembed.bat packages 3.12.0 list
pyembed.bat packages 3.12.0 add requests
pyembed.bat packages 3.12.0 remove requests

# Virtual environment (venv) from selected version
pyembed.bat venv 3.12.0
pyembed.bat venv 3.12.0 myenv

# Run this version
pyembed.bat run 3.12.0 -c "print(1)"
pyembed.bat run 3.12.0 script.py

# Default version (for run/path show without specifying version)
pyembed.bat default              # show
pyembed.bat default 3.12.0       # set
pyembed.bat run -c "print(1)"    # uses default version

# Hint: how to add version to PATH (without changing registry)
pyembed.bat use 3.12.0

# Remove version (with confirmation; -y — skip)
pyembed.bat uninstall 3.12.0
pyembed.bat uninstall 3.12.0 -y

# Verify installed version integrity
pyembed.bat verify 3.12.0

# Version info (path, pip, size, in PATH)
pyembed.bat info 3.12.0
pyembed.bat info                  # default version

# Downloaded archive cache
pyembed.bat cache list            # list cache files
pyembed.bat cache clear           # clear entire cache
pyembed.bat cache clear 3.12.0    # clear cache for 3.12.0 only

# Upgrade pip in installed version
pyembed.bat upgrade-pip 3.12.0
pyembed.bat upgrade-pip            # default version

# Install pip into already installed version (no reinstall)
pyembed.bat add-pip 3.12.0

# Pip for selected version (requires install --pip or add-pip)
pyembed.bat pip 3.12.0 install requests
pyembed.bat pip 3.12.0 list
pyembed.bat pip 3.12.0 uninstall requests
```

Example `use` output:

```
Add to PATH to use this version:
  set PATH=T:\Projects\PythonManager\pythons\3.12.0;%PATH%
Or run directly: T:\Projects\PythonManager\pythons\3.12.0\python.exe
```

## FAQ

- **No network / timeout when downloading.** Ensure python.org is reachable. If needed, download the embed archive manually and extract to `pythons/<version>/` (e.g. `pythons/3.12.0/`), then install pip if needed: `pyembed add-pip 3.12.0`.
- **Need ARM64.** Specify architecture: `pyembed install 3.12.0 --arch arm64` (if python.org has an arm64 build).
- **Where is the cache?** In `pythons/.cache/` (or `PYEMBED_ROOT/.cache/`). Commands: `pyembed cache list`, `pyembed cache clear [version]`.
- **How to remove the manager completely?** Delete the project folder. If you added versions to PATH via `path add`, remove those entries from the user PATH (Settings → Environment variables → Path) or run `pyembed path remove <path_to_version_folder>` for each.
- **Garbled characters in console.** Run `chcp 65001` or set `PYTHONIOENCODING=utf-8`.

## Cache and exe build

- **Archive cache:** downloaded zips are stored in `pythons/.cache/` and reused when reinstalling the same version (and architecture). Commands: `pyembed cache list`, `pyembed cache clear`. Manually — delete the `.cache` folder.
- **Single exe build:** `pip install pyinstaller`, then from project root:
  ```bat
  python scripts/build_exe.py
  ```
  Or manually: `pyinstaller --onefile --name pyembed --paths . run.py`. The resulting `pyembed.exe` is in `dist/`. Suitable for machines without Python (along with bootstrap.ps1).

## Layout after install

```
PythonManager/
  pythons/
    .cache/           # downloaded zip cache (optional)
    3.12.0/
      python.exe
      python312.dll
      python312._pth
      ...
    3.11.5/
      ...
  pyembed/
  run.py
  requirements.txt
```

## Architecture

By default the package for the current architecture (amd64 / win32 / arm64) is installed. You can set it explicitly:

```bash
python run.py install 3.12.0 --arch amd64
```

## Run as module

```bash
python -m pyembed list
python -m pyembed install 3.12.0 --pip
```

## Python vs Rust

The manager is written in **Python** because:

- Faster to write and change
- Target audience already has or will get Python
- Convenient to use `zipfile`, `urllib`, HTML parsing

**Rust** would make sense if you need a single executable with no dependency on an installed Python (e.g. to ship one .exe for “bare” Windows). Then the manager could be distributed as a single binary and used to bootstrap the first version. The logic could be ported to Rust later if desired.

## Development and CI

- Tests: `pip install -e ".[dev]"`, then `pytest tests/ -v`.
- Linter: `ruff check pyembed`.
- Types: `pyright` in strict mode (`pyrightconfig.json` has `typeCheckingMode: "strict"`).
- You can enable GitHub Actions (see `.github/workflows/ci.yml`) to run tests on Windows on push/PR.

### CI usage examples

**GitHub Actions** — install version via pyembed and run tests:

```yaml
- name: Install Python via pyembed
  run: |
    pip install -e .
    pyembed install 3.12.0 --pip
    pyembed default 3.12.0
- name: Run tests
  run: pyembed run -m pytest tests/ -v
```

**GitLab CI** — same idea:

```yaml
test:
  script:
    - pip install -e .
    - pyembed install 3.12.0 --pip
    - pyembed default 3.12.0
    - pyembed run -m pytest tests/ -v
```

Install root can be set with the `PYEMBED_ROOT` variable (e.g. in CI — a cached directory).

## Cursor / VS Code integration

Cursor and VS Code use the Python interpreter from **`python.defaultInterpreterPath`** or from “Python: Select Interpreter”. To use a version installed via pyembed:

### Option 1: path manually

Get the path to the version and set it in settings:

```bash
pyembed which 3.12.0
# or default version:
pyembed which
```

Copy the output (or `pyembed which 3.12.0 -c` — path goes to clipboard). In Cursor/VS Code: **Ctrl+Shift+P** → “Python: Select Interpreter” → “Enter interpreter path...” → paste the path to `python.exe`.

### Option 2: ide command and settings.json

The **`pyembed ide`** command prints the path and a hint; with **`--json`** — a ready snippet for `settings.json`:

```bash
pyembed ide 3.12.0
# JSON only (to paste into .vscode/settings.json):
pyembed ide 3.12.0 --json
```

In the project root create or edit `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "T:\\Projects\\PythonManager\\pythons\\3.12.0\\python.exe"
}
```

Use the path from `pyembed which 3.12.0` or `pyembed ide 3.12.0 --json`.

### Option 3: via PATH

If you add the version to PATH (`pyembed path add 3.12.0`), Cursor may list it when scanning the environment. Then just select it in “Python: Select Interpreter”.

### Multiple versions in one project

For different folders you can set a different interpreter in workspace settings (`.vscode/settings.json` in the project), using the path to `python.exe` from pyembed for the desired version.

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
ruff check pyembed scripts
```

## License

MIT. See [LICENSE](LICENSE).
