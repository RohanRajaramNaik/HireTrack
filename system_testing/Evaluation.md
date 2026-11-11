# Evaluation of the Testing Results

HireTrack Phase 5. Student 402311822. Final runs: 11 November 2026.

## 1. Summary

| Level | Tool | Tests | Passed | Pass rate |
|---|---|---|---|---|
| Unit (backend) | pytest | 133 | 133 | 100% |
| Integration (backend API) | pytest + FastAPI TestClient | 197 | 197 | 100% |
| Component (frontend) | Vitest + React Testing Library | 49 | 49 | 100% |
| System / end-to-end | Playwright, Microsoft Edge | 22 | 22 | 100% |
| System / end-to-end | Playwright, Google Chrome | 22 | 22 | 100% |
| System test cases (Test_Cases.xlsx) | traced to every requirement | 37 | 37 | 100% |

Backend line coverage is **95%** (target 70%). Frontend line coverage is **50.6%**: the component tests target the new screens (sign-in, navigation by role, dashboard, pipeline, resources, import, administration). The older matching screens are covered by the end-to-end journeys instead.

Every functional requirement (FR1 to FR26) and non-functional requirement (NFR1 to NFR10) has at least one passing test case.

## 2. How the pass rate developed

The final figures are not first-time results. Each suite was run, failures were investigated, and the cause was fixed in the product or in the test. All raw outputs are kept in `testing/results/`.

| Run | Suite | Result | What happened |
|---|---|---|---|
| 1 | Backend | 322 / 326 | Four failures, see D3 and T1 to T3 below |
| 2 | Backend | 326 / 326 | After fixes; 330 after the password-reset tests were added |
| 1 | Frontend | 45 / 46 | Old validation test lacked the new required job location (T4) |
| 1 | End-to-end | 14 / 22 (64%) | D1, D2, T5 to T9 |
| 2 | End-to-end | 21 / 22 | TC-13 failed with "target closed" |
| 3 to 4 | End-to-end | 21 / 22 | E1 found and fixed; TC-13 still failing (E2) |
| 5 | End-to-end | 22 / 22 | E2 worked around; final runs in Edge and Chrome 22 / 22 |

## 3. Defects found and how they were fixed

Product defects (changes to the system):

| ID | Found by | Defect | Fix |
|---|---|---|---|
| D1 | e2e TC-07 | Skills read from a CV appeared as lower-case chips ("airflow") because the server returns canonical names | The form converts them to display labels (`skillLabel`) before adding the chips |
| D2 | e2e TC-20 | Clickable dashboard chart bars were hidden from keyboard and screen-reader users (`aria-hidden`, `tabIndex=-1`) | Interactive bars are real buttons with names such as "Bench (0%): 12"; a component test now checks this |
| D3 | pytest test_import | On a new database, CV parsing found no skills, because it only knew skills already saved | Added a built-in list of common IT skills plus the alias table; ambiguous words ("go", "r") are left out |
| D4 | Screenshot review | Seed data was unrealistic: many stage changes had the same timestamp, people hired for one job still had open offers for others, 59% of staff were on the bench | Stage dates are spread between application and today; a hire withdraws the person's other open applications; bench reduced to about 1 in 8 |
| D5 | Screenshot review | Project panel showed "170% booked today", which reads as over-booking | Shown as full-time equivalents ("1.7 FTE") |
| D6 | Manual test of start.bat | The busy-port check never fired, so the server failed later with a socket error | Replaced the regular expression with two plain `findstr` filters; verified with port 8000 in use |
| D7 | Fresh-install check | `start.bat` could not find Python 3.11 when it is installed outside PATH (for example by uv) | Added the `PYTHON` override to both start scripts and documented it |

Test defects (the product was right, the test was wrong):

| ID | Test | Problem | Fix |
|---|---|---|---|
| T1 | test_seed_dashboard | Expected 29 open jobs; the catalogue has 3 closed, so 30 is correct | Expectation corrected |
| T2 | test_import (two cases) | Assumed skills are listed in typing order | Compared as sets |
| T3 | test_performance | Expected the old 2,018-candidate size after the large dataset grew to 2,600 | Updated; a 600-candidate test added |
| T4 | Vitest logic test | Sample job had no location | Location added; new tests for location and phone rules |
| T5 to T8 | e2e TC-06, 09, 14, 17 | Ambiguous locators (a "Skills added" list also matched "Skills"); Playwright 1.49 does not accept a regular expression in `selectOption` | Exact labels, rows scoped by name, option chosen by value |
| T9 | e2e TC-10 | Hard-coded 600 candidates, but TC-08 imports two more | Accepts any 6xx count |

Test environment issues:

| ID | Problem | Resolution |
|---|---|---|
| E1 | The e2e server switched off the start-up model warm-up, so the first match on a new server took 8.3 s and TC-13 failed | The e2e server now starts exactly like the real app (warm-up on). The product was never affected. |
| E2 | In Microsoft Edge under automation, a finished blob download is held open and the next test's browser context hangs ("target closed"). Chrome does not do this. | TC-12 captures the CSV at the final browser step and checks its name, header and row count. The app's own code (authenticated fetch, server file name, blob) still runs. Recorded as a tool limitation. |

## 4. Non-functional results

| Requirement | Evidence | Result |
|---|---|---|
| NFR1 Performance | 600 candidates re-ranked end to end through the screen in 0.69 s (TC-13). Real model: 50 uncached in 0.52 s; 600 warm in 0.16 s; 2,600 warm in 0.93 to 1.06 s. A first match must read every new CV once: 8 to 11 s for 600 CVs and 20 s for 2,600. This happens in the background after loading data. | Met (warm). Cold first run is longer, and the screen says why. |
| NFR2 Offline | Fresh install started with `HF_HUB_OFFLINE=1` and all HTTP(S) traffic sent to an unreachable proxy; sign-in, matching and every screen worked | Met |
| NFR3 Usability | Inline messages under every field; role-based menus; keyboard-reachable charts; consistent layout at 1366 x 768 | Met (no formal user study) |
| NFR4 Maintainability | 133 unit tests run the rules with no database or server | Met |
| NFR5 / NFR7 Privacy and fairness | All seed data fictitious; tests prove name and email do not change scores; every score has a visible calculation | Met |
| NFR6 Reliability | Invalid data rejected in the screen, by Pydantic and by 21 database constraint tests | Met |
| NFR8 Compatibility | All 22 journeys pass in Edge and Chrome | Met for Edge and Chrome; Firefox not tested |
| NFR9 Security | 36 role and endpoint combinations, lock-out, expired and forged tokens, bcrypt-only storage, SQL injection, password re-confirmation | Met |
| NFR10 Coverage | 95% backend | Met |

## 5. Limitations

1. **Firefox and Safari were not tested.** The design named Firefox; Playwright here drives the installed Edge and Chrome only.
2. **No real users.** Usability was judged from screenshot reviews and accessibility checks, not observed sessions with recruiters.
3. **Cold-start speed.** The first match after loading new CVs is slower than 5 s because each CV is read once by the model. It is cached afterwards.
4. **Single computer.** SQLite and a 127.0.0.1-only server suit one user at a time. Concurrent multi-user load was not tested.
5. **Frontend coverage is 50.6%.** Older matching screens rely on end-to-end tests rather than component tests.
6. **CV parsing is text-based.** Scanned (image-only) PDFs are rejected with a message; no OCR.
7. **The Edge download workaround (E2)** means the very last browser step of saving the CSV is not exercised in Edge (it is in Chrome).
8. **Seed data is generated.** It is realistic in shape but not taken from real recruitment records, so match quality on real CVs is not measured.

## 6. Recommendations

1. Add Firefox to the Playwright run and test at 1920 x 1080 and tablet widths.
2. Run a short usability session with two or three recruiters using the test journeys as tasks.
3. Move to PostgreSQL and run the server on a lab network before more than one recruiter uses it at once; add a load test (for example 20 users matching at the same time).
4. Raise frontend coverage with component tests for the Candidates, Jobs and Results screens.
5. Encode new CVs in the background immediately after each import or edit, so a first match is never cold.
6. Add OCR for scanned CVs and a measured comparison of match quality against recruiter shortlists.
7. Add an automated check that fails the build if backend coverage drops below 90%.
