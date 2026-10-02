# Setup Guide for New Development PC

This guide helps you set up the Elmetron Data Capture application on a new development PC.

## Prerequisites

The `start.bat` script will check for these requirements, but you need to install them manually first:

### 1. Python 3.9 or later
- **Download:** https://www.python.org/downloads/
- **Important:** During installation, check "Add Python to PATH"
- **Verify:** Open Command Prompt and run `python --version`

### 2. Node.js (LTS version recommended)
- **Download:** https://nodejs.org/
- **Note:** npm is included with Node.js
- **Verify:** Open Command Prompt and run:
  ```cmd
  node --version
  npm --version
  ```

### 3. FTDI D2XX Drivers (Required for CX-505 Hardware)
- **Download:** https://ftdichip.com/drivers/d2xx-drivers/
- **Download the Windows version** (typically `CDM212364_Setup.exe` or similar)
- **After installation:**
  - The `ftd2xx.dll` should be automatically installed in `C:\Windows\System32`
  - If not, download the DLL directly and copy it to either:
    - `C:\Windows\System32` (system-wide)
    - The application directory (local to this project)
- **Note:** Without these drivers, the application will still run in Archive Mode (browsing historical data only)

### 4. Git (for repository cloning)
- **Download:** https://git-scm.com/download/win
- **Verify:** `git --version`

## Installation Steps

### 1. Clone the Repository
```cmd
cd C:\Users\YourUsername\Desktop\GitHub
git clone [repository-url] Elmetron-Data-Capture
cd Elmetron-Data-Capture
```

### 2. Run the Start Script
Simply double-click `start.bat` or run it from Command Prompt:
```cmd
start.bat
```

The script will automatically:
- ✅ Check if Python is installed
- ✅ Check if Node.js and npm are installed
- ✅ Create a Python virtual environment (`.venv`)
- ✅ Install Python dependencies from `requirements.txt`
- ✅ Check for FTDI D2XX drivers (optional, warns if missing)
- ✅ Install UI dependencies (npm packages)
- ✅ Launch the application launcher

### 3. First Run
After the setup completes:
- The Elmetron Launch Monitor GUI will appear
- If hardware is connected and drivers are installed, you can start the capture service
- If hardware is not connected, the UI will operate in Archive Mode

## What Gets Installed

### Python Packages (in `.venv`)
- `flask>=3.0.0` - Web framework for Data API
- `flask-cors>=4.0.0` - CORS support for API

### Node.js Packages (in `ui/node_modules`)
See `ui/package.json` for the complete list, including:
- React 19.1.1
- Material-UI 7.3.2
- Recharts (for data visualization)
- Vite (build tool)
- TypeScript
- And many more...

## Troubleshooting

### Python not found
- Make sure Python is in your PATH
- Try using `py` launcher: `py --version`
- Reinstall Python and check "Add Python to PATH" during installation

### Node.js not found
- Install Node.js from https://nodejs.org/
- Restart Command Prompt after installation

### FTDI drivers not working
- Download and install from https://ftdichip.com/drivers/d2xx-drivers/
- Check Device Manager for "USB Serial Converter" under "Universal Serial Bus controllers"
- Manually copy `ftd2xx.dll` to project directory if needed

### npm install fails
- Delete `ui/node_modules` and `ui/package-lock.json`
- Run `start.bat` again
- Check internet connection

### Python packages fail to install
- Check internet connection
- Try running manually: `.venv\Scripts\pip.exe install -r requirements.txt`
- Check logs in `captures\setup_python.log`

## Manual Setup (Alternative)

If you prefer to set up manually:

```cmd
:: Create virtual environment
python -m venv .venv

:: Activate virtual environment
.venv\Scripts\activate

:: Install Python dependencies
pip install -r requirements.txt

:: Install UI dependencies
cd ui
npm install
cd ..

:: Run launcher
python launcher.py
```

## Verification Checklist

Before starting development, verify:
- [ ] Python 3.9+ is installed and in PATH
- [ ] Node.js LTS is installed and in PATH
- [ ] FTDI D2XX drivers installed (required for testing, even without hardware)
- [ ] `.venv` directory exists with packages installed
- [ ] `ui/node_modules` directory exists
- [ ] `start.bat` runs without errors
- [ ] Launcher GUI opens successfully
- [ ] `check_dependencies.py` shows drivers found (for full testing capability)

## Additional Resources

- **Project README:** See `README.md` for architecture overview
- **Operator Guide:** See `docs/OPERATOR_PLAYBOOK.md`
- **Troubleshooting:** See `TROUBLESHOOTING.md`
- **UI Development:** See `docs/UI_DESIGN_SYSTEM.md`

## Support

If you encounter issues:
1. Check the log files in the `captures/` directory
2. Review `TROUBLESHOOTING.md`
3. Contact the development team

---

**Last Updated:** 2025-10-06
