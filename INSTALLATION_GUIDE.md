# HireTrack Installation Guide

HireTrack: Applicant Tracking and Resource Allocation System
IT Project (Year 3), Phase 5 Implementation. Group: Rohan Naik (402311822), Nadhir Mahomed (402110343), Joshua S Pillay (402200878), Sheik Kader (402413277), Tiara Govender (402306095), Rudo Fourie (402410352).

This guide installs HireTrack on one Windows or macOS computer. It takes 5 to 10 minutes the first time. After installation the system runs fully offline.

---

## 1. Prerequisites

| Item | Version | Notes |
|---|---|---|
| Operating system | Windows 10/11 or macOS 12+ (Linux also works) | 64-bit |
| Python | **3.11** | Windows: python.org installer, tick "Add python.exe to PATH". macOS: `brew install python@3.11` |
| Node.js | 18 or later (tested with 20.16) | Only needed to build the screens once. Includes `npm`. |
| Browser | Microsoft Edge or Google Chrome (current) | |
| Disk space | about 3 GB free | Python packages (PyTorch is the largest), Node packages, model |
| Memory | 4 GB minimum, 8 GB recommended | |
| Internet | During installation only | Downloads packages and the 90 MB language model once |

Check the versions in a terminal (Command Prompt, PowerShell or Terminal):

```
python --version        (Windows; macOS: python3.11 --version)
node --version
npm --version
```

## 2. Get the files

1. Clone the repository (needs Git), or use **Code > Download ZIP** on the repository page and unzip it:

```
git clone https://github.com/RohanRajaramNaik/hiretrack.git
cd hiretrack
```

2. The folder you are now in is the project folder; every command below runs from here.

The repository does not contain `node_modules`, the Python virtual environment, the language model or a database. The start script creates all of them.

## 3. Quick start (one command)

### Windows

Double-click `start.bat`, or in Command Prompt:

```
cd path\to\source_code
start.bat
```

### macOS / Linux

```
cd path/to/source_code
chmod +x start.sh
./start.sh
```

The first run shows four steps:

1. `[1/4]` creates `.venv` and installs the Python packages from `backend/requirements.txt`
2. `[2/4]` downloads the all-MiniLM-L6-v2 model into `models/`
3. `[3/4]` installs the Node packages and builds the screens into `frontend/dist`
4. `[4/4]` creates `data/hiretrack.db` and seeds it with 600 candidates, 33 jobs, applications, staff and projects, then runs the first match

The browser then opens at **http://127.0.0.1:8000**. Later runs skip the finished steps and start in a few seconds. Press `Ctrl+C` in the terminal to stop the server.

Options (set before running the script):

| Variable | Use |
|---|---|
| `PORT` | Another port, e.g. Windows `set PORT=8001` then `start.bat`; macOS `PORT=8001 ./start.sh` |
| `PYTHON` | Full path to a Python 3.11 interpreter if it is not on PATH, e.g. `set PYTHON=C:\Python311\python.exe` |
| `HT_NO_BROWSER` | Set to `1` to stop the script opening the browser |

## 4. Default sign-in accounts

| Role | Email | Password | Can do |
|---|---|---|---|
| Administrator | admin@hiretrack.local | Admin@123 | Everything, plus users, data loading, backups and restore |
| Recruiter (HR) | recruiter@hiretrack.local | Recruiter@123 | Candidates, jobs, matching, pipeline. Read-only staff and projects |
| Resource Manager | manager@hiretrack.local | Manager@123 | Staff, projects, allocations. Read-only candidates, jobs and pipeline |

These accounts are created the first time the database is set up. **Change the passwords** (account menu, top right, then Change password) before using real data. The sign-in page also lists them under "Demo accounts".

## 5. Manual installation (step by step)

Use this if the start script cannot be used, or to see each step.

```
# 1. Python environment
#    Windows:  py -3.11 -m venv .venv      (or: python -m venv .venv)
#    macOS:    python3.11 -m venv .venv
.venv\Scripts\activate                 # macOS: source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt

# 2. Language model (once, needs internet)
cd backend
python -m app.download_model
cd ..

# 3. Frontend (once)
cd frontend
npm install
npm run build
cd ..

# 4. Database with seed data
python seed/seed_database.py           # full dataset (600 candidates, 33 jobs)
#   --small   18 candidates and 3 jobs (for the guided matching demo)
#   --large   full dataset plus 2,000 extra candidates

# 5. Run (one port serves the API and the screens)
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Interactive API documentation is at http://127.0.0.1:8000/docs.

### Development mode (hot reload)

```
# terminal 1
cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
# terminal 2
cd frontend && npm run dev            # http://127.0.0.1:5173, passes /api calls to :8000
```

## 6. Seeding and resetting data

| Method | Result |
|---|---|
| `python seed/seed_database.py` | Recreates all business data (600 candidates, 33 jobs, ~850 applications with history, ~75 staff, 12 projects). Backs up the old database first. User accounts are kept. |
| Admin screen, Data section | The same three datasets (full, small demo, large), each confirmed with the administrator's password. A safety backup is taken first. |
| Delete `data/hiretrack.db` | The next start creates an empty database with the three default accounts; `start.bat`/`start.sh` then seeds it again. |

All seed data is fictitious (names, clients and CVs are invented).

## 7. Running the tests

```
# Backend: unit + integration tests with coverage (from backend/)
cd backend
python -m pytest --cov=app --cov-report=term --cov-report=html:../testing/coverage/backend

# Speed with the real language model
#   Windows PowerShell:  $env:HIRETRACK_REAL_MODEL=1; python -m pytest tests/integration/test_performance.py -s
#   macOS:               HIRETRACK_REAL_MODEL=1 python -m pytest tests/integration/test_performance.py -s

# Frontend component tests (from frontend/)
cd ../frontend
npm test
npm run test:coverage

# End-to-end journeys in Microsoft Edge (starts its own server on port 8010
# with a separate database in e2e-data/; your data is not touched)
npm run test:e2e
#   Chrome instead:  set HT_BROWSER=chrome   (macOS: HT_BROWSER=chrome npm run test:e2e)
```

## 8. Where things are kept

| Path | Contents |
|---|---|
| `data/hiretrack.db` | SQLite database |
| `data/.jwt_secret` | Random key that signs sign-in tokens (created on first run) |
| `data/embedding_cache.npz` | Cached CV vectors (no CV text) |
| `backups/` | Automatic and manual database backups (10 most recent kept) |
| `logs/app.log` | Rotating log (ids and counts only, no CV text) |
| `models/all-MiniLM-L6-v2/` | The local language model |

To back up by hand, copy `data/hiretrack.db` while the server is stopped, or use Admin > Back up now.

## 9. Troubleshooting

| Problem | Fix |
|---|---|
| "Python 3.11 is required" | Install Python 3.11, or point the script at it: `set PYTHON=C:\path\to\python.exe` (macOS: `PYTHON=/path/to/python3.11 ./start.sh`). |
| "Port 8000 is already in use" | Another program (or an older HireTrack window) is using the port. Close it, or start on another port: `set PORT=8001` then `start.bat`. |
| `pip install` fails on torch | Check the internet connection and that Python is 64-bit 3.11. Re-run the script; finished steps are skipped. |
| "Node.js 18 or later is required" | Install Node.js LTS from nodejs.org, open a new terminal and run the script again. |
| Model download fails | Needs internet once. Run `cd backend` then `python -m app.download_model`. If it still fails, the app runs with a simpler word-based fallback and the Dashboard shows "Fallback (model not downloaded)". |
| Screens look old after changing code | Run `npm run build` in `frontend/` and restart the server. |
| Forgot the admin password | Stop the server, then in `backend/`: `python -m app.reset_password admin@hiretrack.local NewPassw0rd` |
| "Too many failed sign-in attempts" | Wait 60 seconds; five wrong passwords lock that email for one minute. |
| Session expired | Sign-in tokens last 8 hours; sign in again. Closing the browser tab also signs you out. |
| First match after loading data is slow | The first match reads every new CV once (about 10 to 20 s per 1,000 CVs). Later matches take under a second. |
| Start-up error about the database after an upgrade | Older databases are upgraded automatically. If a database is damaged, restore a backup from Admin, or delete `data/hiretrack.db` and seed again. |
| macOS: "permission denied" for start.sh | Run `chmod +x start.sh` once. |

## 10. Uninstall

Stop the server and delete the `source_code` folder. Nothing is installed outside it except the global Python and Node.js you installed yourself.
