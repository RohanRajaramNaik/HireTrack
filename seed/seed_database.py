"""Create (or re-create) the HireTrack database with realistic, fictitious data.

Run from the project root, with the virtual environment active:

    python seed/seed_database.py            # full dataset: 600 candidates, 33 jobs
    python seed/seed_database.py --small    # 18 candidates and 3 jobs (guided demo)
    python seed/seed_database.py --large    # full dataset + 2,000 extra candidates
    python seed/seed_database.py --no-match # skip the first matching run

What the full dataset contains
- 600 candidates (18 hand-written + 582 generated) with skills, education,
  experience, location and a CV summary
- 33 job specifications (3 demo + 30 from seed/catalogue.py), 30 open
- about 800 applications spread across the pipeline, each with a stage history
- staff (everyone hired through the pipeline plus existing staff), 12 client
  projects and allocations, with some staff deliberately left on the bench
- the three default user accounts (only created if no users exist)

The existing database is backed up to backups/ first, unless it is empty.
After seeding, the demo job (Cloud Data Engineer) is matched once so the
Results and Dashboard screens have data and the CV embeddings are cached.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))
os.chdir(ROOT / "backend")


def main() -> int:
    ap = argparse.ArgumentParser(description="Seed the HireTrack database")
    size = ap.add_mutually_exclusive_group()
    size.add_argument("--small", action="store_true", help="18 candidates and 3 jobs only")
    size.add_argument("--large", action="store_true", help="add 2,000 extra generated candidates")
    ap.add_argument("--no-match", action="store_true", help="do not run the first match")
    args = ap.parse_args()

    from sqlalchemy import func, select

    from app.database import SessionLocal, init_db
    from app.logging_setup import setup_logging
    from app.models import Candidate, JobSpecification
    from app.services import backup_service, match_service, seed_service

    setup_logging()
    init_db()
    started = time.perf_counter()
    with SessionLocal() as db:
        if (db.scalar(select(func.count(Candidate.candidate_id))) or 0) > 0:
            b = backup_service.create_backup("pre-seed")
            print(f"Backed up the existing database to backups/{b['file']}")
        if args.small:
            out = seed_service._load(db)
        elif args.large:
            out = seed_service.build_full(db, extra_candidates=seed_service.FULL_CANDIDATES - 18 + 2000)
        else:
            out = seed_service.build_full(db)
        print("Seeded:", ", ".join(f"{v} {k}" for k, v in out.items()))

        if not args.no_match:
            print("Running the first match (encodes every CV once; about 5-20 s with the real model)...")
            job_id = db.scalar(
                select(JobSpecification.job_id).where(JobSpecification.job_title == seed_service.DEMO_JOB_TITLE)
            )
            res = match_service.run_match(db, job_id)
            top = res.results[0]
            print(
                f"Matched {res.run.candidate_count} candidates for '{res.job.job_title}' in "
                f"{res.run.duration_ms} ms. Top: {top.full_name} ({top.overall_score})"
            )
    print(f"Done in {time.perf_counter() - started:.1f} s")
    print("Sign in at http://127.0.0.1:8000 with admin@hiretrack.local / Admin@123")
    return 0


if __name__ == "__main__":
    sys.exit(main())
