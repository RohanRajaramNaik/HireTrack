# HireTrack test report

**Run date:** 6 November 2026, on the development laptop (Windows 11, 16-thread CPU, Python 3.11.18, Node 20.16, Microsoft Edge).

| Suite | Command | Result |
|---|---|---|
| Backend unit + API (pytest) | `cd backend && python -m pytest` | **123 passed**, 0 failed |
| Performance, real model | `HIRETRACK_REAL_MODEL=1 python -m pytest tests/test_performance.py -s` | **2 passed** |
| Frontend (Vitest) | `cd frontend && npm test` | **24 passed**, 0 failed |
| Recorded guided demo (Playwright + Edge) | `node e2e/demo-flow.mjs` | **12 / 12 checks passed** |
| Full end-to-end through the UI | `node e2e/full-flow.mjs` | **16 / 16 checks passed** |

## Key test cases

### Scoring engine (`backend/tests/test_scoring.py`)

| Test case | Expected | Actual | Result |
|---|---|---|---|
| Skills: 2/3 required, 1/2 preferred | 2/3×80 + 1/2×20 = 63.3 | 63.3 | Pass |
| Skills: no preferred skills, 1/2 required | 50.0 (required counts for 100) | 50.0 | Pass |
| Skills: only preferred matched | 20.0 | 20.0 | Pass |
| Experience below minimum (2 of 4 yrs) | 50.0 | 50.0 | Pass |
| Experience with minimum 0 | 100.0 | 100.0 | Pass |
| Education one level below (3 vs 4) | 75.0 | 75.0 | Pass |
| Education Bachelor's vs Master's (4 vs 6) | 66.7 | 66.7 | Pass |
| Semantic: negative cosine similarity | clipped to 0 | 0.0 | Pass |
| Overall, default weights (90, 100, 75, 60) | 84.25 → 84.3 (half up) | 84.3 | Pass |
| Overall with decimals (63.3, 50, 66.7, 41.2) | 56.065 → 56.1 | 56.1 | Pass |
| Calculation string | `Overall = (100×40 + 100×25 + 100×15 + 62.3×20) / 100 = 92.5` | identical | Pass |
| Weights at 95 | error "Weights must add up to 100% (now 95%)" | identical message | Pass |
| Weights at 105, negative weight, weight above 100 | rejected | rejected | Pass |
| Weights 100/0/0/0 | allowed | allowed | Pass |
| Normaliser: JS, ts, Py, K8s, Postgres, ML, Node JS, "Amazon Web Services" | javascript, typescript, python, kubernetes, postgresql, machine learning, node.js, aws | identical | Pass |
| Normaliser: dedupe after alias (JS, JavaScript, "javascript ") | one entry | ["javascript"] | Pass |
| Preferred repeats required | rejected, names the skill | "...repeat required skills: python" | Pass |
| Job with no required skill | rejected | rejected | Pass |
| Ranking tie on overall | higher skills first | correct | Pass |
| Ranking tie on overall and skills | name A–Z, case-insensitive | andile, Bongani, Zanele | Pass |
| Fairness: same profile, different names | identical scores | identical | Pass |
| Explanation sentence | "Strong on skills (3 of 3 required), meets the experience minimum, one level below the education requirement; ..." | identical | Pass |
| Keyword callout: alias hit | note naming "JS" | present | Pass |
| Keyword callout: meaning ≥ 60 and skills < 60 | "different words" note | present; absent at 59.9 | Pass |

### API (`backend/tests/test_api.py`)

| Test case | Expected | Actual | Result |
|---|---|---|---|
| Candidate CRUD | 201 / 200 / 204 / then 404 | as expected | Pass |
| Search "py" | finds Python candidates via alias | 2 of 5 | Pass |
| Search with SQL injection text `' OR 1=1 --` | 200, no rows | 200, 0 rows | Pass |
| Negative years | 422, field `years_experience`, "cannot be less than 0" | as expected | Pass |
| Years 51 | 422 | 422 | Pass |
| Empty / missing name | 422, field `full_name` | as expected | Pass |
| Summary under 20 characters | 422, field `resume_summary` | as expected | Pass |
| No skills | 422, "Add at least one skill" | as expected | Pass |
| Bad email / blank email | 422 / stored as null | as expected | Pass |
| Job weights at 95 | 422, field `weights`, exact message | `Weights must add up to 100% (now 95%)` | Pass |
| Job weights at 110, negative weight | 422 | 422 | Pass |
| Preferred repeats required (including JS vs JavaScript) | 422, field `preferred_skills` | as expected | Pass |
| No required skill, empty title, short description, negative minimum | 422 with the right field | as expected | Pass |
| Run match | ranked results, weights and run time saved | strong fit ranked 1, skills 100 | Pass |
| Alias recorded in results | `{"javascript": "JS"}` + keyword note | as expected | Pass |
| Results before any run | `run: null`, empty list | as expected | Pass |
| Match with no candidates / unknown job | 400 / 404 | as expected | Pass |
| CSV export | header row, attachment, `=HYPERLINK` neutralised | as expected | Pass |
| Delete candidate cascades results | results removed | removed | Pass |
| Wrong passcode / missing passcode on every admin endpoint | 401, field `passcode` | as expected | Pass |
| Back up, change data, restore | data returns to backup state, safety backup made | as expected | Pass |
| Restore: path traversal / unknown file / corrupt file | rejected (404 / 404 / 400 integrity) | as expected | Pass |
| 12 manual backups | only 10 kept | 10 | Pass |
| Seed demo / seed large | 18 + 3 jobs / 2,018 candidates | as expected | Pass |
| Guided demo start on empty DB / on existing data | seeds / keeps data | as expected | Pass |

### Performance (`backend/tests/test_performance.py`, real all-MiniLM-L6-v2 model)

| Test case | Expected | Actual | Result |
|---|---|---|---|
| Match 50 candidates, nothing cached | < 5 s | 0.55 s | Pass |
| Match 2,018 candidates, embeddings cached | < 5 s | 0.62 s best, 0.90 s worst | Pass |
| Load 2,018 results for the Results page | < 3 s | 0.30 s | Pass |
| One-off encoding of 2,018 new CVs (background, after loading) | reported | 17.0 s | Info |

### Frontend (Vitest)

| Test case | Expected | Actual | Result |
|---|---|---|---|
| MetricBar shows label and number, ARIA meter values | "83.3", aria-valuenow 83.3 | as expected | Pass |
| MetricBar clamps 140 → 100; fill proportional | 100; scaleX(0.25) | as expected | Pass |
| WeightSliders live total, "5% still to assign", "10% over" | correct totals | as expected | Pass |
| WeightSliders balanced mode keeps 100 | total 100 | 100 | Pass |
| Reset to defaults | Total 100% | as expected | Pass |
| Client overall matches Python on the same cases | 84.3, 56.1, 92.5 | identical | Pass |
| Re-rank by weights; tie-breaks; no mutation | order changes; skills then A–Z | as expected | Pass |
| Rebalance always 100, whole numbers | yes for 0…100 | as expected | Pass |
| Candidate / job form validation | same messages as the server | as expected | Pass |
| TagInput: Enter adds, alias duplicate ignored, Backspace removes | as described | as expected | Pass |

### Recorded guided demo (`frontend/e2e/demo-flow.mjs`, 1366×768)

| Test case | Expected | Actual | Result |
|---|---|---|---|
| Results appear after the match response | ≤ 300 ms | 141–145 ms | Pass |
| Rows animate in sequence | later rows still fading in at 450 ms | opacity 1.00 … 0.81 | Pass |
| Tour steps 1–4 find their targets (list, breakdown, keyword callout, weights) | all four shown | all four shown | Pass |
| What-if drag re-orders the list | new order | Andile Mthembu moves to #1 at 96% meaning | Pass |
| What-if makes no API calls | 0 requests | 0 | Pass |
| Whole demo without typing | < 3 minutes | about 11 s with automated clicks | Pass |

### Full end-to-end (`frontend/e2e/full-flow.mjs`)

Wrong passcode rejected → demo data loaded through confirm dialog → new "Data Analyst" job created → Run Match disabled at 95% with the exact message → reset to defaults → saved → matched (Zanele Khumalo ranks first) → breakdown formula shown → what-if re-ranks → CSV downloaded (18 rows) → backup made → data changed → restored (change gone) → candidate form inline errors (negative years, summary, skills) → candidate added, found and deleted → guided demo reaches the tour → no console errors. **16 / 16 passed.**

## Issues found and fixed during testing

| Issue | Fix |
|---|---|
| Model download stalled (hf-xet transfer) | Downloader uses `snapshot_download` with xet disabled and resumes |
| Restore could prune the backup being restored when 10 already existed | Backup is read into memory before the safety backup is taken |
| Results header columns shifted (sr-only cell left the grid) | Wrapped in a grid cell |
| Tour scrolled tall targets to their centre, hiding the weights panel in step 4 | Targets aligned by their top edge; step 4 no longer dims the list it re-ranks |
| Radar chart animated the `points` attribute (console error) | Animation removed; the polygon fades and scales in instead |
| "Keyword search would miss" callout appeared for loosely related CVs | Threshold calibrated against the real model (meaning ≥ 60) |
| Unknown `/api/*` POST returned 405 once the SPA catch-all existed | Explicit `/api/*` fallback returns 404 in the standard error shape |
| First 2,000-candidate match encoded all CVs inside the request | Background warm-up plus a persistent on-disk embedding cache; the UI explains the one-off wait |

## Not automated, to check manually

- **Firefox:** the scripted checks used Microsoft Edge (Chromium). Styles avoid Chromium-only features, and Firefox range-slider styling is included, but Firefox was not driven automatically.
- **A real projector:** checked by screenshot at 1920×1080 only.
- **Screen reader pass** (NVDA or VoiceOver): ARIA roles and labels are in place but have not been heard end to end.
