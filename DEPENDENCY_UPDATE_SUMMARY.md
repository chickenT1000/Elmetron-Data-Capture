# Dependency Check & Installation Update Summary

**Date:** 2025-10-06  
**Issue:** The `start.bat` launcher script and launcher application did not check or install all required dependencies, causing problems on new development PCs.

## Changes Made

### 1. Created `requirements.txt` ✅
**File:** `requirements.txt` (NEW)

Previously only `requirements_data_api.txt` existed with minimal packages. Now there's a comprehensive `requirements.txt` that includes:

- `flask>=3.0.0` - Web framework for Data API service
- `flask-cors>=4.0.0` - CORS support for API endpoints
- Documentation for standard library dependencies (tkinter, sqlite3, ctypes)
- Notes about FTDI D2XX driver requirements

### 2. Enhanced `start.bat` Script ✅
**File:** `start.bat` (UPDATED)

Added comprehensive dependency checks:

#### New Checks Added:
1. **Node.js and npm verification** (lines 11-43)
   - Checks if Node.js is installed
   - Checks if npm is installed  
   - Displays versions of both
   - Exits with error message if missing

2. **FTDI D2XX driver detection** (lines 107-132)
   - Checks for `ftd2xx.dll` in `System32`
   - Checks for `ftd2xx.dll` in application directory
   - Warns if missing but continues (since app can run in Archive Mode)
   - Provides download link for drivers

3. **Improved status messages**
   - Changed from `[INFO] Wykryto` to `[OK]` for successful checks
   - Consistent Polish/English messaging
   - Clear error vs warning distinction

### 3. Created Setup Documentation ✅
**File:** `SETUP_NEW_PC.md` (NEW)

Comprehensive guide for setting up on a new development PC:

- Prerequisites with download links (Python, Node.js, FTDI drivers, Git)
- Step-by-step installation instructions
- What gets installed and where
- Troubleshooting section for common issues
- Manual setup alternative
- Verification checklist
- Links to additional resources

### 4. Created Dependency Verification Script ✅
**File:** `check_dependencies.py` (NEW)

Python script that verifies all dependencies:

- Checks Python version (3.9+ required)
- Verifies standard library modules (tkinter, sqlite3, ctypes)
- Checks third-party packages (Flask, Flask-CORS)
- Tests FTDI driver availability
- Validates local elmetron package structure
- Checks directory structure
- Verifies configuration files exist
- Provides detailed summary with clear ✓/✗/⚠ indicators

**Usage:**
```cmd
python check_dependencies.py
```

## Complete Dependency List

### System Requirements:
1. **Python 3.9+** - Core language
2. **Node.js LTS** - For UI frontend (React/Vite)
3. **FTDI D2XX Drivers** - For CX-505 hardware access (optional)

### Python Packages (installed via pip):
- `flask>=3.0.0` - Data API web service
- `flask-cors>=4.0.0` - Cross-origin resource sharing

### Python Standard Library (included with Python):
- `tkinter` - GUI for launcher
- `sqlite3` - Database backend
- `ctypes` - Windows API and FTDI driver access
- `pathlib`, `subprocess`, `threading`, etc. - Various utilities

### Node.js Packages (installed via npm):
See `ui/package.json` for complete list (~60 packages), including:
- React 19.1.1 - UI framework
- Material-UI 7.3.2 - Component library
- Vite 7.1.7 - Build tool
- TypeScript 5.8.3 - Type checking
- Recharts 3.2.1 - Data visualization
- And many more...

### Local Packages (no installation needed):
- `elmetron` package with submodules:
  - `elmetron.config` - Configuration management
  - `elmetron.acquisition` - Data acquisition
  - `elmetron.hardware` - Hardware interface
  - `elmetron.storage` - Database operations
  - `elmetron.ingestion` - Data ingestion pipeline
  - `elmetron.protocols` - Protocol registry
  - `elmetron.service` - Service management
  - `elmetron.analytics` - Analytics engine
  - `elmetron.reporting` - Report generation

## How to Use on New PC

### Option 1: Automatic (Recommended)
Just run `start.bat`:
```cmd
start.bat
```

The script will:
1. Check all prerequisites (Python, Node.js, FTDI)
2. Create Python virtual environment
3. Install Python packages
4. Install UI dependencies
5. Launch the application

### Option 2: Manual Verification First
1. Run dependency check:
   ```cmd
   python check_dependencies.py
   ```

2. Install any missing components based on output

3. Run `start.bat` or directly:
   ```cmd
   python launcher.py
   ```

## What Happens If Dependencies Are Missing?

### Missing Python:
- `start.bat` exits with error
- Shows download link: https://www.python.org/downloads/

### Missing Node.js/npm:
- `start.bat` exits with error
- Shows download link: https://nodejs.org/

### Missing FTDI drivers:
- `start.bat` shows warning but continues
- Application runs in Archive Mode (can browse historical data only)
- **Testing limitations:** Cannot test hardware capture, live monitoring, or device communication
- **For dev/test PCs:** Install drivers even if hardware not connected (enables full code paths)
- Shows download link: https://ftdichip.com/drivers/d2xx-drivers/

### Missing Python packages:
- Automatically installed by `start.bat`
- Can also install manually: `pip install -r requirements.txt`

### Missing UI packages:
- Automatically installed by `start.bat`
- Can also install manually: `cd ui && npm install`

## Testing

To test on a clean PC:
1. Install Python 3.9+ and Node.js LTS
2. Clone the repository
3. Run `start.bat`
4. Verify launcher opens successfully

To test dependency checker:
```cmd
python check_dependencies.py
```

Expected output shows ✓ for all required dependencies and ⚠ for optional FTDI (if not installed).

## Files Modified/Created

### Modified:
- `start.bat` - Enhanced with Node.js and FTDI checks

### Created:
- `requirements.txt` - Python package dependencies
- `SETUP_NEW_PC.md` - Setup guide for new PCs
- `check_dependencies.py` - Dependency verification script
- `DEPENDENCY_UPDATE_SUMMARY.md` - This file

## Notes

1. **Virtual Environment:** All Python packages are installed in `.venv` directory, isolated from system Python

2. **UI Dependencies:** Node.js packages are installed in `ui/node_modules` directory

3. **Archive Mode:** The application gracefully handles missing hardware and operates in read-only mode for historical data

4. **Logs:** Setup logs are written to `captures/` directory:
   - `setup_pip.log` - pip upgrade log
   - `setup_python.log` - Python package installation log
   - `setup_ui.log` - npm installation log

5. **No `setup.py`:** The elmetron package is used as a local package (no installation required), so no `setup.py` or `pyproject.toml` is needed

## Future Improvements

Potential enhancements (not implemented):
- Add automatic download/installation of FTDI drivers
- Create Windows installer package (.msi or .exe)
- Add dependency version locking for reproducible builds
- Automated testing of fresh installations in CI/CD
