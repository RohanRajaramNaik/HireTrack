@echo off
REM HireTrack one-command start for Windows.   Double-click, or run:  start.bat
REM
REM First run (needs internet, about 5-10 minutes):
REM   1. creates a Python 3.11 virtual environment in .venv and installs the packages
REM   2. downloads the all-MiniLM-L6-v2 language model (about 90 MB) into models\
REM   3. installs the frontend packages and builds the frontend into frontend\dist
REM   4. seeds the database (600 candidates, 33 jobs, pipeline, staff, projects)
REM Later runs start the app in a few seconds and work fully offline.
REM The app opens at http://127.0.0.1:8000   (another port:  set PORT=8001 then start.bat)
setlocal
cd /d "%~dp0"
if not defined PORT set "PORT=8000"

if exist ".venv\Scripts\python.exe" goto have_venv
set "PY="
REM A specific Python 3.11 can be given with:  set PYTHON=C:\Python311\python.exe
if defined PYTHON set "PY="%PYTHON%""
if not defined PY where py >nul 2>nul && (py -3.11 --version >nul 2>nul && set "PY=py -3.11")
if not defined PY (
  python --version 2>nul | findstr /b /c:"Python 3.11" >nul && set "PY=python"
)
if not defined PY (
  echo Python 3.11 is required. Install it from https://www.python.org/downloads/ ^(tick "Add to PATH"^) and run start.bat again.
  exit /b 1
)
echo [1/4] Creating the Python virtual environment...
%PY% -m venv .venv || exit /b 1
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
echo       Installing Python packages ^(first run only, a few minutes^)...
".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt || exit /b 1

:have_venv
if exist "models\all-MiniLM-L6-v2\model.safetensors" goto have_model
echo [2/4] Downloading the language model ^(about 90 MB, first run only^)...
pushd backend
"..\.venv\Scripts\python.exe" -m app.download_model
if errorlevel 1 (popd & exit /b 1)
popd

:have_model
if exist "frontend\dist\index.html" goto have_frontend
where npm >nul 2>nul || (echo Node.js 18 or later is required to build the frontend: https://nodejs.org & exit /b 1)
echo [3/4] Building the frontend ^(first run only^)...
pushd frontend
call npm install --no-audit --no-fund || (popd & exit /b 1)
call npm run build || (popd & exit /b 1)
popd

:have_frontend
if not exist ".env" if exist ".env.example" copy ".env.example" ".env" >nul

if exist "data\hiretrack.db" goto have_db
echo [4/4] Creating and seeding the database ^(first run only^)...
".venv\Scripts\python.exe" seed\seed_database.py || exit /b 1

:have_db
netstat -ano -p TCP | findstr /c:"127.0.0.1:%PORT% " | findstr /c:"LISTENING" >nul
if not errorlevel 1 (
  echo Port %PORT% is already in use. Stop the other program, or run:  set PORT=8001 ^&^& start.bat
  exit /b 1
)

set HF_HUB_OFFLINE=1
echo.
echo HireTrack is starting on http://127.0.0.1:%PORT%  ^(press Ctrl+C to stop^)
echo Sign in as admin@hiretrack.local / Admin@123  ^(see INSTALLATION_GUIDE.md for all accounts^)
REM set HT_NO_BROWSER=1 to skip opening the browser (useful for testing)
if not defined HT_NO_BROWSER start "" http://127.0.0.1:%PORT%
cd backend
"..\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port %PORT%
