@echo off
REM Runs one GeM scan now and uploads it to GitHub. Log: gem_pc\gem.log
cd /d "%~dp0"
set PY=
where py >nul 2>nul && set PY=py -3
if "%PY%"=="" ( where python >nul 2>nul && set PY=python )
if "%PY%"=="" ( echo Python not found. Run setup.bat. & if not "%1"=="silent" pause & exit /b 1 )
%PY% gem_scan.py
if not "%1"=="silent" pause
