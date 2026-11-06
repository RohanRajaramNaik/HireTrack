"""Performance: time a full match (score + save) on 50 and on ~2,000 candidates.

By default the fast fallback embedder is used. To time the real
all-MiniLM-L6-v2 model run (from backend/):
    HIRETRACK_REAL_MODEL=1 python -m pytest tests/test_performance.py -s

In the app the model is loaded once at start-up and every CV summary is
encoded once, in the background, then cached in memory and on disk. These
tests mirror that: the model is loaded before timing starts.
"""
import time

import pytest


def _load_generated(n):
    import sys

    from app.config import settings

    sys.path.insert(0, str(settings.seed_dir.parent))
    from seed.generate_large_dataset import generate

    return generate(n)


@pytest.mark.perf
def test_match_50_candidates_under_5s(client):
    from app.database import SessionLocal
    from app.engine.embeddings import embedder
    from app.services import seed_service

    with SessionLocal() as db:
        seed_service._load(db, extra=_load_generated(32))  # 18 demo + 32 = 50
    seed_service.warm_embeddings(wait=True)  # let the background warm-up finish
    embedder.warm_up()  # model loaded, as it is at app start-up
    embedder.clear_cache()  # ...but no CV has been encoded yet (worst case)
    jobs = client.get("/api/jobs").json()
    assert client.get("/api/candidates", params={"page_size": 1}).json()["total"] == 50
    started = time.perf_counter()
    r = client.post(f"/api/jobs/{jobs[0]['job_id']}/match")
    elapsed = time.perf_counter() - started
    assert r.status_code == 200 and len(r.json()["results"]) == 50
    print(f"\n50 candidates, nothing cached: {elapsed:.2f}s  embedder={embedder.backend_name}")
    assert elapsed < 5


@pytest.mark.perf
def test_match_2000_candidates(client, admin_headers):
    from app.engine.embeddings import embedder
    from app.services import seed_service

    assert client.post("/api/admin/seed-large", headers=admin_headers).status_code == 200
    embedder.warm_up()
    embedder.clear_cache()
    started = time.perf_counter()
    seed_service.warm_embeddings(wait=True)  # what the app does in the background after loading
    cold = time.perf_counter() - started
    print(f"\n2,018 CVs encoded once (background, after loading): {cold:.1f}s")

    job_id = client.get("/api/jobs").json()[0]["job_id"]
    timings = []
    for _ in range(3):
        started = time.perf_counter()
        r = client.post(f"/api/jobs/{job_id}/match")
        timings.append(time.perf_counter() - started)
        assert r.status_code == 200 and len(r.json()["results"]) == 2018
    print(f"2,018 candidates, match with warm cache: {min(timings):.2f}s best, {max(timings):.2f}s worst, embedder={embedder.backend_name}")
    assert max(timings) < 5

    started = time.perf_counter()
    assert len(client.get(f"/api/jobs/{job_id}/results").json()["results"]) == 2018
    load = time.perf_counter() - started
    print(f"2,018 results loaded for the Results page: {load:.2f}s")
    assert load < 3
