# Testing evidence

This folder holds copies of the test code next to the results they produced. The test code that runs lives in `backend/` and `frontend/` (paths below); these copies are here so the tests can be read without opening the project.

| Folder | Contents | Runs from |
|---|---|---|
| `unit/backend/` | pytest unit tests: scoring engine, pipeline rules, allocation rules, database constraints (133 tests) | `backend/tests/unit/` |
| `unit/frontend/` | Vitest tests for validation, what-if re-ranking and small components | `frontend/src/test/` |
| `integration/backend/` | pytest API tests through FastAPI's TestClient on a temporary database (197 tests) | `backend/tests/integration/` |
| `integration/frontend/` | Vitest + React Testing Library tests of the main screens with the API mocked | `frontend/src/test/screens.test.jsx` |
| `e2e/` | Playwright journeys TC-01 to TC-22, configuration, and the HTML report (`html-report/index.html`) | `frontend/e2e/` |
| `results/` | Raw outputs and JUnit XML of the runs (see below) | |
| `coverage/backend/` | pytest-cov HTML report (`index.html`) and `coverage.xml` | |
| `coverage/frontend/` | Vitest coverage HTML report (`index.html`) | |

## Files in results/

| File | What it is |
|---|---|
| `backend-pytest-raw.txt` | Final backend run: 330 passed, coverage table (95%) |
| `backend-junit.xml` | Same run in JUnit format |
| `backend-performance-real-model.txt` | Speed tests with the real all-MiniLM-L6-v2 model |
| `frontend-vitest-raw.txt` | Final Vitest run with coverage: 49 passed |
| `e2e-run1-raw.txt` ... `e2e-run5-raw.txt` | Every Playwright run while defects were being fixed (run 1: 14/22, run 5: 22/22) |
| `e2e-final-raw.txt`, `e2e-junit.xml` | Final Playwright run in Microsoft Edge |
| `e2e-chrome-raw.txt` | Playwright run in Google Chrome: 22/22 |
| `fresh-install-log.txt` | Output of `start.bat` on a clean copy of the repository |
