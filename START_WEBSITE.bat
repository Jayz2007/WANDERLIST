@echo off
setlocal
cd /d "%~dp0"
title Workbench - Local website
if not exist ".venv\Scripts\python.exe" goto missing_setup
".venv\Scripts\python.exe" run.py %*
set "WORKBENCH_RESULT=%ERRORLEVEL%"
if not "%WORKBENCH_RESULT%"=="0" pause
exit /b %WORKBENCH_RESULT%
:missing_setup
echo Run SETUP_WINDOWS.bat first, then reopen START_WEBSITE.bat.
pause
exit /b 1
