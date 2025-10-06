#!/usr/bin/env python3
"""
Dependency checker for Elmetron Data Capture application.
Run this script to verify all required dependencies are installed.
"""

from __future__ import annotations

import sys
import importlib.util
from pathlib import Path


def check_python_version():
    """Check if Python version is 3.9 or later."""
    print("Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print(f"  ✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"  ✗ Python {version.major}.{version.minor}.{version.micro} (requires 3.9+)")
        return False


def check_module(module_name: str, package_name: str = None) -> bool:
    """Check if a Python module can be imported."""
    display_name = package_name or module_name
    try:
        importlib.import_module(module_name)
        print(f"  ✓ {display_name}")
        return True
    except ImportError:
        print(f"  ✗ {display_name} - not installed")
        return False


def check_optional_module(module_name: str, description: str) -> bool:
    """Check optional module and provide context."""
    try:
        importlib.import_module(module_name)
        print(f"  ✓ {description}")
        return True
    except ImportError:
        print(f"  ⚠ {description} - not available (optional)")
        return False


def check_ftdi_drivers():
    """Check if FTDI D2XX drivers are available."""
    print("Checking FTDI D2XX drivers...")
    try:
        import ctypes
        ftd2xx = ctypes.WinDLL('ftd2xx.dll')
        print("  ✓ ftd2xx.dll found")
        return True
    except (OSError, AttributeError):
        print("  ⚠ ftd2xx.dll not found (required for hardware access)")
        print("    Download from: https://ftdichip.com/drivers/d2xx-drivers/")
        return False


def check_local_packages():
    """Check if local elmetron package is accessible."""
    print("Checking local packages...")
    try:
        import elmetron
        print("  ✓ elmetron package")
        
        # Check submodules
        submodules = [
            'elmetron.config',
            'elmetron.acquisition',
            'elmetron.hardware',
            'elmetron.storage',
            'elmetron.ingestion',
            'elmetron.protocols',
            'elmetron.service',
        ]
        
        for module in submodules:
            try:
                importlib.import_module(module)
            except ImportError as e:
                print(f"  ✗ {module} - import error: {e}")
                return False
        
        print("  ✓ All elmetron submodules accessible")
        return True
    except ImportError as e:
        print(f"  ✗ elmetron package - {e}")
        return False


def check_directories():
    """Check if required directories exist."""
    print("Checking directory structure...")
    root = Path(__file__).resolve().parent
    
    required_dirs = [
        'captures',
        'config',
        'elmetron',
        'ui',
    ]
    
    all_exist = True
    for dir_name in required_dirs:
        dir_path = root / dir_name
        if dir_path.exists():
            print(f"  ✓ {dir_name}/")
        else:
            print(f"  ✗ {dir_name}/ - missing")
            all_exist = False
    
    return all_exist


def check_config_files():
    """Check if configuration files exist."""
    print("Checking configuration files...")
    root = Path(__file__).resolve().parent
    
    required_files = [
        'launcher.py',
        'cx505_capture_service.py',
        'data_api_service.py',
        'requirements.txt',
        'ui/package.json',
    ]
    
    all_exist = True
    for file_name in required_files:
        file_path = root / file_name
        if file_path.exists():
            print(f"  ✓ {file_name}")
        else:
            print(f"  ✗ {file_name} - missing")
            all_exist = False
    
    return all_exist


def main():
    """Run all dependency checks."""
    print("=" * 70)
    print("Elmetron Data Capture - Dependency Checker")
    print("=" * 70)
    print()
    
    results = []
    
    # Check Python version
    results.append(("Python version", check_python_version()))
    print()
    
    # Check standard library modules (should always be available)
    print("Checking standard library modules...")
    std_modules = [
        ('tkinter', 'tkinter (GUI)'),
        ('sqlite3', 'sqlite3 (database)'),
        ('ctypes', 'ctypes (FFI)'),
    ]
    
    for module, display in std_modules:
        results.append((display, check_module(module, display)))
    print()
    
    # Check third-party packages
    print("Checking third-party packages...")
    packages = [
        ('flask', 'Flask'),
        ('flask_cors', 'Flask-CORS'),
    ]
    
    for module, display in packages:
        results.append((display, check_module(module, display)))
    print()
    
    # Check FTDI drivers (optional for hardware)
    results.append(("FTDI drivers", check_ftdi_drivers()))
    print()
    
    # Check local packages
    results.append(("Local packages", check_local_packages()))
    print()
    
    # Check directory structure
    results.append(("Directory structure", check_directories()))
    print()
    
    # Check configuration files
    results.append(("Configuration files", check_config_files()))
    print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    required_checks = [
        "Python version",
        "tkinter (GUI)",
        "sqlite3 (database)",
        "ctypes (FFI)",
        "Flask",
        "Flask-CORS",
        "Local packages",
        "Directory structure",
        "Configuration files",
    ]
    
    testing_checks = [
        "FTDI drivers",
    ]
    
    required_passed = all(passed for name, passed in results if name in required_checks)
    testing_passed = all(passed for name, passed in results if name in testing_checks)
    
    if required_passed:
        print("✓ All required dependencies are satisfied!")
        if not testing_passed:
            print("⚠ FTDI drivers missing - required for full testing capability")
            print("  App will run in Archive Mode only (read historical data)")
            print("  For development/testing: Install drivers even without hardware")
        print("\nYou can run the application with: python launcher.py")
    else:
        print("✗ Some required dependencies are missing!")
        print("\nMissing required dependencies:")
        for name, passed in results:
            if name in required_checks and not passed:
                print(f"  - {name}")
        
        print("\nTo install missing Python packages, run:")
        print("  pip install -r requirements.txt")
        print("\nOr use the start.bat script which will set up everything automatically.")
    
    print()
    
    return 0 if required_passed else 1


if __name__ == "__main__":
    sys.exit(main())
