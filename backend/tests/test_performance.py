"""Performance: time a full match (score + save) on 50 and on ~2,000 candidates.

By default the fast fallback embedder is used. To time the real
all-MiniLM-L6-v2 model run:
    HIRETRACK_REAL_MODEL=1 python -m pytest tests/test_performance.py -s
"""
import time

import pytest


@pytest.mark.perf
def test_match_50_candidates_under_5s(client, admin_headers):
    import sys

    from app.config import settings

    sys.path.insert(0, str(settings.seed_dir.parent))
    from seed.generate_large_dataset import generate

    from app.database import SessionLocal
    from app.services import seed_service

    with SessionLocal() as db:
        seed_service._load(db, extra=generate(32))  # 18 demo + 32 = 50
    jobs = client.get("/api/jobs").json()
    assert client.get("/api/candidates", params={"page_size": 1}).json()["total"] == 50
    started = time.perf_counter()
    r = client.post(f"/api/jobs/{jobs[0]['job_id']}/match")
    elapsed = time.perf_counter() - started
    assert r.status_code == 200 and len(r.json()["results"]) == 50
    print(f"\n50 candidates: {elapsed:.2f}s (cold cache)")
    assert elapsed < 5


@pytest.mark.perf
def test_match_2000_candidates(client, admin_headers):
    from app.engine.embeddings import embedder
    from app.services import seed_service

    assert client.post("/api/admin/seed-large", headers=admin_headers).status_code == 200
    seed_service.warm_embeddings()  # what the app does in the background after loading
    job_id = client.get("/api/jobs").json()[0]["job_id"]
    started = time.perf_counter()
    r = client.post(f"/api/jobs/{job_id}/match")
    warm = time.perf_counter() - started
    assert r.status_code == 200 and len(r.json()["results"]) == 2018
    print(f"\n2,018 candidates, warm cache: {warm:.2f}s, embedder={embedder.backend_name}")
    assert warm < 5
    # results endpoint (what the Results page loads) is also quick
    started = time.perf_counter()
    assert len(client.get(f"/api/jobs/{job_id}/results").json()["results"]) == 2018
    assert time.perf_counter() - started < 3
