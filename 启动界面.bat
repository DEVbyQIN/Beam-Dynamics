@echo off
rem UED local GUI launcher for Windows.
rem ASCII-only on purpose: cmd.exe parses batch text with the console code page,
rem so non-ASCII bytes here can corrupt labels and quoted paths.
setlocal EnableExtensions
chcp 65001 >nul 2>nul
cd /d "%~dp0"

rem 1) Prefer the project virtual environment created by the installer.
set "UED_PY="
if exist "%~dp0.venv\Scripts\python.exe" set UED_PY="%~dp0.venv\Scripts\python.exe"
if not defined UED_PY if exist "%~dp0venv\Scripts\python.exe" set UED_PY="%~dp0venv\Scripts\python.exe"

rem 2) Fall back to the Python launcher, then to python.exe on PATH.
if not defined UED_PY (
  py -3.12 -c "import sys" >nul 2>nul
  if not errorlevel 1 set "UED_PY=py -3.12"
)
if not defined UED_PY (
  py -3 -c "import sys" >nul 2>nul
  if not errorlevel 1 set "UED_PY=py -3"
)
if not defined UED_PY (
  python -c "import sys" >nul 2>nul
  if not errorlevel 1 set "UED_PY=python"
)
if not defined UED_PY goto :no_python

rem UTF-8 mode for the GUI and for every worker child it starts.
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONDONTWRITEBYTECODE=1"

%UED_PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 goto :old_python

%UED_PY% -c "import numpy, scipy, yaml, matplotlib" >nul 2>nul
if errorlevel 1 goto :no_deps

%UED_PY% -c "import ocelot" >nul 2>nul
if errorlevel 1 echo [WARN] Module "ocelot" is missing: the OCELOT route will fail, the AG route still works.

%UED_PY% run_gui.py --open %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [ERROR] run_gui.py exited with code %RC%.
  pause
)
exit /b %RC%

:no_python
echo [ERROR] No working Python 3.10+ was found.
echo Install 64-bit Python 3.12 from https://www.python.org/downloads/windows/
echo Enable "Add python.exe to PATH", then run the environment installer in this folder.
echo See gui\WINDOWS.md for details.
pause
exit /b 9009

:old_python
echo [ERROR] Python 3.10 or newer is required. See gui\WINDOWS.md.
pause
exit /b 1

:no_deps
echo [ERROR] Missing packages: numpy, scipy, PyYAML or matplotlib.
echo Run the environment installer in this folder first (gui\WINDOWS.md).
pause
exit /b 1
