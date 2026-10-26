@echo off
rem UED GUI environment installer for Windows (creates .venv, installs pins).
rem ASCII-only on purpose; see gui\WINDOWS.md for the full instructions.
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul 2>nul
cd /d "%~dp0"
if errorlevel 1 goto :path_failed
echo === UED GUI environment installer (Windows) ===
echo Project: "%~dp0"
echo.

set "UED_BOOT="
py -3.12 -c "import sys" >nul 2>nul
if not errorlevel 1 set "UED_BOOT=py -3.12"
if not defined UED_BOOT (
  python -c "import sys; sys.exit(0 if sys.version_info[:2]==(3,12) else 1)" >nul 2>nul
  if not errorlevel 1 set "UED_BOOT=python"
)
if not defined UED_BOOT goto :no_python312

%UED_BOOT% -c "import sys,sysconfig; sys.exit(0 if sys.implementation.name=='cpython' and sys.version_info[:2]==(3,12) and sysconfig.get_platform()=='win-amd64' else 1)" >nul 2>nul
if errorlevel 1 goto :no_python312

echo Using Python launcher: %UED_BOOT%
%UED_BOOT% -c "import sys; print('Python', sys.version.split()[0], 'at', sys.executable)"
echo.

if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Creating virtual environment .venv ...
  %UED_BOOT% -m venv "%~dp0.venv"
  if errorlevel 1 goto :venv_failed
) else (
  echo Reusing existing virtual environment .venv
)
set UED_PY="%~dp0.venv\Scripts\python.exe"

%UED_PY% -c "import sys,sysconfig; sys.exit(0 if sys.implementation.name=='cpython' and sys.version_info[:2]==(3,12) and sysconfig.get_platform()=='win-amd64' else 1)" >nul 2>nul
if errorlevel 1 goto :wrong_venv

echo.
echo Upgrading pip ...
%UED_PY% -m pip install --disable-pip-version-check --upgrade pip
if errorlevel 1 goto :pip_failed

echo.
echo Installing pinned GUI/driver requirements ...
%UED_PY% -m pip install --disable-pip-version-check -r "%~dp0requirements-gui.txt"
if errorlevel 1 goto :pip_failed

echo.
echo Verifying imports ...
%UED_PY% -c "import numpy, scipy, yaml, matplotlib; print('core imports OK')"
if errorlevel 1 goto :verify_failed
%UED_PY% -c "import ocelot; print('ocelot imports OK')"
if errorlevel 1 echo [WARN] ocelot import failed: the OCELOT route will fail, the AG route still works. See gui\WINDOWS.md.

echo.
echo Done. Start the GUI by double-clicking the launcher .bat in this folder.
echo Details and troubleshooting: gui\WINDOWS.md
pause
exit /b 0

:no_python312
echo [ERROR] 64-bit CPython 3.12 was not found.
echo The pinned requirements need CPython 3.12 (win_amd64 wheels).
echo Install it from https://www.python.org/downloads/windows/
echo and enable "Add python.exe to PATH"; then run this file again.
echo See gui\WINDOWS.md.
pause
exit /b 9009

:venv_failed
echo [ERROR] Could not create .venv (see the message above).
pause
exit /b 1

:pip_failed
echo [ERROR] pip install failed (see the message above).
echo If the machine is offline or behind a proxy, configure pip first: gui\WINDOWS.md
pause
exit /b 1

:verify_failed
echo [ERROR] The core packages do not import. See gui\WINDOWS.md.
pause
exit /b 1

:path_failed
echo [ERROR] Cannot enter the project folder. Use a local writable path.
pause
exit /b 1

:wrong_venv
echo [ERROR] Existing .venv is not CPython 3.12 x64. No packages were changed.
echo Rename that environment yourself before reinstalling; it was not deleted.
pause
exit /b 1
