@echo off
REM HireTrack one-command start for Windows.
REM First run: creates the virtual environment, installs everything, downloads
REM the model, builds the frontend and asks for an admin passcode.
REM Later runs: just starts the app on http://127.0.0.1:8000
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" goto have_venv
set "PY="
where py >nul 2>nul && (py -3.11 --version >nul 2>nul && set "PY=py -3.11")
if not defined PY (
  python --version 2>nul | findstr /b "Python 3.11" >nul && set "PY=python"
)
if not defined PY (
  echo Python 3.11 is required. Install it from https://www.python.org/downloads/ and try again.
  exit /b 1
)
echo Creating virtual environment...
%PY% -m venv .venv || exit /b 1
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
echo Installing Python packages ^(first run only, a few minutes^)...
".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt || exit /b 1

:have_venv
if not exist "models\all-MiniLM-L6-v2\model.safetensors" (
  echo Downloading the language model ^(about 90 MB, first run only^)...
  pushd backend
  "..\.venv\Scripts\python.exe" -m app.download_model || (popd & exit /b 1)
  popd
)

if not exist "frontend\dist\index.html" (
  where npm >nul 2>nul || (echo Node.js 18+ is required to build the frontend: https://nodejs.org & exit /b 1)
  echo Building the frontend ^(first run only^)...
  pushd frontend
  call npm install || (popd & exit /b 1)
  call npm run build || (popd & exit /b 1)
  popd
)

REM (kept outside a ( ) block so %PASSCODE% expands after it is typed)
if exist ".env" goto run
echo.
set /p "PASSCODE=Choose an admin passcode (6+ characters): "
pushd backend
"..\.venv\Scripts\python.exe" -m app.hash_passcode "%PASSCODE%" --write
if errorlevel 1 (popd & exit /b 1)
popd

:run
set HF_HUB_OFFLINE=1
echo.
echo HireTrack is starting on http://127.0.0.1:8000  (press Ctrl+C to stop)
start "" http://127.0.0.1:8000
cd backend
"..\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
