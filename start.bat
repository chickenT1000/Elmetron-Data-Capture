@echo off
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION

cd /d "%~dp0" || exit /b 1

echo --------------------------------------------------
echo [INFO] Elmetron startup helper
echo --------------------------------------------------

:: ----------------------------------------------------------------------------
:: Check Node.js and npm (required for UI)
:: ----------------------------------------------------------------------------
echo [INFO] Sprawdzanie Node.js i npm...
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js nie znaleziony w PATH.
    echo        Pobierz i zainstaluj Node.js z https://nodejs.org/
    echo        Zalecana wersja: LTS ^(Long Term Support^)
    goto :fail
)

where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] npm nie znaleziony w PATH.
    echo        npm powinien byc zainstalowany razem z Node.js.
    goto :fail
)

for /f "tokens=*" %%v in ('node --version 2^>^&1') do (
    set "NODE_VERSION=%%v"
    goto :after_node_version
)
:after_node_version
if defined NODE_VERSION echo [OK] Node.js %NODE_VERSION% gotowy.

for /f "tokens=*" %%v in ('npm --version 2^>^&1') do (
    set "NPM_VERSION=%%v"
    goto :after_npm_version
)
:after_npm_version
if defined NPM_VERSION echo [OK] npm %NPM_VERSION% gotowy.

:: ----------------------------------------------------------------------------
:: Resolve Python interpreter (prefer py launcher, fallback to python.exe)
:: ----------------------------------------------------------------------------
set "PYTHON_CMD="
where py >nul 2>nul && set "PYTHON_CMD=py -3"

if not defined PYTHON_CMD (
    where python >nul 2>nul && set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo [ERROR] Nie znaleziono Python 3 w PATH. Zainstaluj Python 3.9+ i sproboj ponownie.
    goto :fail
)

for /f "tokens=2 delims= " %%v in ('%PYTHON_CMD% --version 2^>^&1') do (
    set "PYTHON_VERSION=%%v"
    goto :after_py_version
)
:after_py_version
if defined PYTHON_VERSION echo [OK] Python %PYTHON_VERSION% gotowy.

:: ----------------------------------------------------------------------------
:: Utwórz/odśwież wirtualne środowisko
:: ----------------------------------------------------------------------------
set "VENV_DIR=.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"

if not exist "%VENV_PY%" (
    echo [INFO] Tworzenie wirtualnego środowiska w %VENV_DIR% ...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Nie udalo sie utworzyc wirtualnego srodowiska.
        goto :fail
    )
) else (
    echo [INFO] Wirtualne srodowisko juz istnieje.
)

echo [INFO] Aktualizacja pip...
"%VENV_PY%" -m pip install --upgrade pip >"captures\setup_pip.log" 2>&1
if errorlevel 1 (
    echo [ERROR] Aktualizacja pip nie powiodla sie. Szczegoly w captures\setup_pip.log
    goto :fail
)
echo [OK] pip gotowy.

:: ----------------------------------------------------------------------------
:: Instalacja zaleznosci Pythona (jesli istnieje requirements.txt)
:: ----------------------------------------------------------------------------
if exist "requirements.txt" (
    echo [INFO] Instalacja zaleznosci Pythona z requirements.txt ...
    "%VENV_PIP%" install -r requirements.txt >"captures\setup_python.log" 2>&1
    if errorlevel 1 (
        echo [ERROR] Instalacja pakietow Pythona nie powiodla sie. Zobacz captures\setup_python.log
        goto :fail
    )
    echo [OK] Pakiety Pythona gotowe.
) else (
    echo [WARN] Brak pliku requirements.txt - pomijam instalacje pakietow Pythona.
)

:: ----------------------------------------------------------------------------
:: Sprawdz obecnosc sterownikow FTDI D2XX (opcjonalne - dla hardware)
:: ----------------------------------------------------------------------------
echo [INFO] Sprawdzanie sterownikow FTDI D2XX...
set "FTDI_FOUND=0"

:: Sprawdz w System32
if exist "%SystemRoot%\System32\ftd2xx.dll" (
    echo [OK] ftd2xx.dll znaleziony w System32.
    set "FTDI_FOUND=1"
)

:: Sprawdz w katalogu aplikacji
if exist "ftd2xx.dll" (
    echo [OK] ftd2xx.dll znaleziony w katalogu aplikacji.
    set "FTDI_FOUND=1"
)

if "%FTDI_FOUND%"=="0" (
    echo [WARN] ftd2xx.dll nie znaleziony - ograniczone mozliwosci testowania!
    echo        Pobierz sterowniki FTDI D2XX z https://ftdichip.com/drivers/d2xx-drivers/
    echo        WAZNE dla deweloperow: Zainstaluj sterowniki nawet bez podlaczonego hardware.
    echo        Bez strownikow: tylko tryb archiwalny ^(odczyt danych historycznych^).
    echo        Ze sterownikami: pelne testowanie + symulacja hardware.
)

:: ----------------------------------------------------------------------------
:: Instalacja zaleznosci UI (npm) jezeli potrzeba
:: ----------------------------------------------------------------------------
if exist "ui\package.json" (
    where npm >nul 2>nul
    if errorlevel 1 (
        echo [WARN] npm nie znaleziony w PATH - pomijam instalacje UI.
    ) else (
        if not exist "ui\node_modules" (
            echo [INFO] Instalacja zaleznosci UI (npm install)...
            pushd "ui"
            if exist "package-lock.json" (
                npm ci >"..\captures\setup_ui.log" 2>&1
            ) else (
                npm install >"..\captures\setup_ui.log" 2>&1
            )
            set "NPM_EXIT=!ERRORLEVEL!"
            popd
            if not "!NPM_EXIT!"=="0" (
                echo [ERROR] Instalacja zaleznosci UI nie powiodla sie. Szczegoly w captures\setup_ui.log
                goto :fail
            )
            echo [OK] Pakiety UI zainstalowane.
        ) else (
            echo [INFO] UI node_modules juz istnieje - pomijam instalacje.
        )
    )
) else (
    echo [INFO] Katalog UI nie znaleziony - pomijam instalacje npm.
)

:: ----------------------------------------------------------------------------
:: Uruchom launcher
:: ----------------------------------------------------------------------------
echo [INFO] Uruchamianie Elmetron Launch Monitor...
"%VENV_PY%" launcher.py
set "EXITCODE=%ERRORLEVEL%"

if "%EXITCODE%"=="0" (
    echo [OK] Launcher zakonczyl dzialanie pomyslnie.
) else (
    echo [ERROR] Launcher zakonczyl sie kodem %EXITCODE%.
)

goto :end

:fail
echo.
echo [FAIL] Przygotowanie srodowiska nie powiodlo sie.
echo        Sprawdz komunikaty powyzej oraz logi w folderze captures.
set "EXITCODE=1"

:end
echo --------------------------------------------------
endlocal & exit /b %EXITCODE%
