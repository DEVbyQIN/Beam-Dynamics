@echo off
rem Run the GUI regression suite on Windows (GUI contracts, platform layer,
rem Windows-native checks and the end-to-end GUI test).
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul 2>nul
cd /d "%~dp0"
if errorlevel 1 goto :path_failed
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONDONTWRITEBYTECODE=1"
rem Writable caches inside the project so the sandbox/test account is irrelevant.
set "NUMBA_CACHE_DIR=%~dp0.gui_test_cache\numba"
set "MPLCONFIGDIR=%~dp0.gui_test_cache\mpl"

set "UED_PY="
if exist "%~dp0.venv\Scripts\python.exe" set UED_PY="%~dp0.venv\Scripts\python.exe"
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

%UED_PY% -m unittest gui.test_gui gui.test_platform_compat gui.test_windows_native gui.test_review_regressions gui.test_gui_e2e -v
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (echo GUI TEST COMMAND SUCCEEDED - check skip lines above) else (echo GUI TESTS FAILED with code %RC%)
pause
exit /b %RC%

:no_python
echo [ERROR] No working Python was found. See gui\WINDOWS.md.
pause
exit /b 9009

:path_failed
echo [ERROR] Cannot enter the project folder. Use a local writable path.
pause
exit /b 1
