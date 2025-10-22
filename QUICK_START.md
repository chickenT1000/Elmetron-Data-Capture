# Quick Start Guide

## For New PC Setup

### 1. Install Prerequisites
```cmd
# Install these first (in order):
1. Python 3.9+ from https://www.python.org/downloads/
   ✓ Check "Add Python to PATH" during installation
   
2. Node.js LTS from https://nodejs.org/
   ✓ npm is included automatically
   
3. FTDI D2XX Drivers (optional, for hardware)
   https://ftdichip.com/drivers/d2xx-drivers/
```

### 2. Run the Launcher
```cmd
# Just double-click or run:
start.bat

# The script automatically:
# - Checks all dependencies
# - Creates virtual environment
# - Installs Python packages
# - Installs UI packages
# - Launches the application
```

### 3. Verify Installation (Optional)
```cmd
# Check if everything is installed correctly:
python check_dependencies.py
```

## For Daily Use

### Start Application
```cmd
start.bat
```

### Manual Start (Alternative)
```cmd
# Activate virtual environment
.venv\Scripts\activate

# Run launcher
python launcher.py
```

### Stop Services
- Use the GUI **Stop** buttons in the launcher
- Or press `Ctrl+C` in terminal
- ⚠️ **Never use** `Stop-Process -Force` (can corrupt database)

## Troubleshooting

### "Python not found"
```cmd
# Verify installation:
python --version
# or
py --version

# If still not found, reinstall Python with "Add to PATH" checked
```

### "Node.js not found"
```cmd
# Verify installation:
node --version
npm --version

# If still not found, reinstall Node.js and restart Command Prompt
```

### "ftd2xx.dll not found"
```cmd
# Application runs in Archive Mode (read-only)
# For DEVELOPMENT/TESTING: Install FTDI drivers even without hardware
# This enables full code path testing and hardware simulation

# Install from:
https://ftdichip.com/drivers/d2xx-drivers/
```

### Python packages fail to install
```cmd
# Delete virtual environment and try again:
rmdir /s /q .venv
start.bat
```

### UI packages fail to install
```cmd
# Delete node_modules and try again:
cd ui
rmdir /s /q node_modules
del package-lock.json
cd ..
start.bat
```

## Common Commands

### Check Dependencies
```cmd
python check_dependencies.py
```

### View Logs
```cmd
# Setup logs:
type captures\setup_python.log
type captures\setup_ui.log

# Service logs:
type captures\data_api_service.log
type captures\live_ui_dev.log
```

### Update Dependencies
```cmd
# Python packages:
.venv\Scripts\pip.exe install -r requirements.txt --upgrade

# UI packages:
cd ui
npm update
cd ..
```

### Clean Install
```cmd
# Remove all installed dependencies:
rmdir /s /q .venv
rmdir /s /q ui\node_modules
del ui\package-lock.json

# Reinstall:
start.bat
```

## File Locations

- **Virtual Environment:** `.venv\`
- **UI Packages:** `ui\node_modules\`
- **Configuration:** `config\`
- **Data:** `data\elmetron.sqlite`
- **Captures:** `captures\`
- **Logs:** `captures\*.log`
- **Exports:** `exports\`

## Need More Help?

- **Setup Guide:** `SETUP_NEW_PC.md`
- **Full Documentation:** `README.md`
- **Troubleshooting:** `TROUBLESHOOTING.md`
- **Operator Guide:** `docs/OPERATOR_PLAYBOOK.md`

## Quick Checklist

Before reporting issues, verify:
- [ ] Python 3.9+ installed and in PATH
- [ ] Node.js LTS installed and in PATH
- [ ] `start.bat` runs without errors
- [ ] Launcher GUI opens
- [ ] Check logs in `captures\` directory

---

**TIP:** Bookmark this file for quick reference!
