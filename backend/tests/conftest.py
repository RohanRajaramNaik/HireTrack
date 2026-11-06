"""Test configuration: isolate every test run in a temporary data folder.

Environment variables are set before `app` is imported so the engine/session
point at the temporary database, not the real data/hiretrack.db.
"""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="hiretrack-test-")
os.environ["HIRETRACK_DATA_DIR"] = os.path.join(_tmp, "data")
os.environ["HIRETRACK_BACKUP_DIR"] = os.path.join(_tmp, "backups")
os.environ["HIRETRACK_LOG_DIR"] = os.path.join(_tmp, "logs")
os.environ["HIRETRACK_DISABLE_STARTUP_BACKUP"] = "1"
# Fast unit tests use the deterministic fallback embedder unless the perf
# tests explicitly opt into the real model (HIRETRACK_REAL_MODEL=1).
if os.environ.get("HIRETRACK_REAL_MODEL") != "1":
    os.environ["HIRETRACK_DISABLE_MODEL"] = "1"
