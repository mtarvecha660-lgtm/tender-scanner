@echo off
REM ==========================================================
REM  Tender Scanner - GeM on your PC - one-time setup
REM  Double-click this file. It will:
REM   1) check Python   2) install 3 small packages
REM   3) save your GitHub token + data key   4) schedule a GeM scan every 3 hours
REM ==========================================================
cd /d "%~dp0"
title Tender Scanner setup
set PY=
where py >nul 2>nul && set PY=py -3
if "%PY%"=="" ( where python >nul 2>nul && set PY=python )
if "%PY%"=="" (
  echo.
  echo  Python is not installed.
  echo  1. Open https://www.python.org/downloads/ and click "Download Python"
  echo  2. Run the installer and TICK "Add python.exe to PATH" at the bottom
  echo  3. Then double-click setup.bat again.
  echo.
  start https://www.python.org/downloads/
  pause
  exit /b 1
)
echo Using: %PY%
%PY% --version
echo.
echo Installing packages (requests, lxml, PyYAML, cryptography)...
%PY% -m pip install --user --upgrade requests lxml PyYAML cryptography
if errorlevel 1 ( echo Package install failed. Check your internet and run setup.bat again. & pause & exit /b 1 )
echo.
if exist token.txt (
  echo A token is already saved. Press Enter to keep it, or paste a new one.
)
set /p TOK=Paste your GitHub token (starts with github_pat_) and press Enter: 
if not "%TOK%"=="" ( > token.txt echo %TOK% )
if not exist token.txt ( echo No token saved. Run setup.bat again. & pause & exit /b 1 )
echo.
echo The GeM list is encrypted on this PC before upload. It needs your DATA KEY:
echo the value of the TS_DATA_KEY secret (44 characters, ends with =). See GEM_SETUP.md.
if exist datakey.txt (
  echo A data key is already saved. Press Enter to keep it, or paste a new one.
)
set /p DKEY=Paste your data key and press Enter: 
if not "%DKEY%"=="" ( > datakey.txt echo %DKEY% )
if not exist datakey.txt ( echo No data key saved. Run setup.bat again. & pause & exit /b 1 )
%PY% gem_scan.py --check-key
if errorlevel 1 ( del datakey.txt & echo That data key is not right. Copy it again and run setup.bat again. & pause & exit /b 1 )
echo.
echo Scheduling the GeM scan every 3 hours...
schtasks /create /tn "TenderScanner GeM" /tr "\"%~dp0run_now.bat\" silent" /sc hourly /mo 3 /f
if errorlevel 1 ( echo Could not create the scheduled task. Right-click setup.bat and choose "Run as administrator". & pause & exit /b 1 )
schtasks /create /tn "TenderScanner GeM at logon" /tr "\"%~dp0run_now.bat\" silent" /sc onlogon /delay 0005:00 /f >nul 2>nul
if errorlevel 1 ( echo  (Optional "at logon" task skipped - needs "Run as administrator". The 3-hour task is enough.) )
echo.
echo Running the first GeM scan now (takes about 5-15 minutes)...
call "%~dp0run_now.bat"
echo.
echo Setup finished. Your PC will scan GeM every 3 hours while it is on.
echo To stop it: open Task Scheduler and delete "TenderScanner GeM".
pause
