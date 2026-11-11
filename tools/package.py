"""Build the Phase 5 submission folder and zip.

    python tools/package.py <output_dir> [--zip]

Layout (as required):
402311822_HireTrack_Phase5_Implementation/
  402311822_HireTrack_Phase5_Implementation_Report.docx / .pdf
  README.md, INSTALLATION_GUIDE.md (+ .pdf)
  source_code/   backend/, frontend/, seed/, start.bat, start.sh (+ config files)
  testing/       unit/, integration/, e2e/, results/, coverage/
  system_testing/ Test_Cases.xlsx, Evaluation.md
  docs/          screenshots/, diagrams/
node_modules, .venv, __pycache__, .git, model files and runtime data are excluded.
"""
from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "402311822_HireTrack_Phase5_Implementation"
REPORT = "402311822_HireTrack_Phase5_Implementation_Report"

EXCLUDE_DIRS = {
    "node_modules", ".venv", "venv", "__pycache__", ".git", ".pytest_cache", "dist", "test-results",
    "models", "model_cache", "data", "backups", "logs", "e2e-data", ".vscode", ".idea", "coverage",
}
EXCLUDE_FILES = {".env", ".coverage", "large_candidates.json", "Thumbs.db", ".DS_Store"}
EXCLUDE_SUFFIX = {".pyc", ".pyo", ".db", ".db-journal", ".npz", ".log"}


def keep(path: Path) -> bool:
    if path.name in EXCLUDE_FILES or path.suffix in EXCLUDE_SUFFIX:
        return False
    return not any(part in EXCLUDE_DIRS for part in path.parts)


def copy_tree(src: Path, dst: Path, rel_root: Path | None = None) -> None:
    rel_root = rel_root or src
    for p in src.rglob("*"):
        rel = p.relative_to(rel_root)
        if p.is_file() and keep(rel):
            target = dst / p.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)


def build(out: Path) -> Path:
    stage = out / NAME
    if stage.exists():
        shutil.rmtree(stage)
    src = stage / "source_code"
    src.mkdir(parents=True)
    for d in ("backend", "frontend", "seed"):
        copy_tree(ROOT / d, src / d)
    for f in ("start.bat", "start.sh", ".env.example", ".gitignore", ".gitattributes", "README.md", "INSTALLATION_GUIDE.md"):
        if (ROOT / f).exists():
            shutil.copy2(ROOT / f, src / f)

    # Top-level documents
    for f in (f"{REPORT}.docx", f"{REPORT}.pdf", "INSTALLATION_GUIDE.md", "INSTALLATION_GUIDE.pdf", "README.md"):
        p = ROOT / "docs" / "report" / f if f.startswith(REPORT) or f.endswith(".pdf") else ROOT / f
        if p.exists():
            shutil.copy2(p, stage / f)

    # testing/: copies of the test code next to their results (the source of
    # truth stays in source_code/; testing/README.md says so)
    t = stage / "testing"
    copy_tree(ROOT / "backend" / "tests" / "unit", t / "unit" / "backend")
    shutil.copy2(ROOT / "frontend" / "src" / "test" / "logic.test.js", (t / "unit" / "frontend").mkdir(parents=True, exist_ok=True) or t / "unit" / "frontend" / "logic.test.js")
    shutil.copy2(ROOT / "frontend" / "src" / "test" / "components.test.jsx", t / "unit" / "frontend" / "components.test.jsx")
    copy_tree(ROOT / "backend" / "tests" / "integration", t / "integration" / "backend")
    for f in ("conftest.py", "helpers.py"):
        shutil.copy2(ROOT / "backend" / "tests" / f, t / "integration" / "backend" / f)
    (t / "integration" / "frontend").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "frontend" / "src" / "test" / "screens.test.jsx", t / "integration" / "frontend" / "screens.test.jsx")
    copy_tree(ROOT / "frontend" / "e2e" / "tests", t / "e2e" / "tests")
    shutil.copy2(ROOT / "frontend" / "playwright.config.js", t / "e2e" / "playwright.config.js")
    shutil.copy2(ROOT / "frontend" / "e2e" / "start-e2e-server.mjs", t / "e2e" / "start-e2e-server.mjs")
    if (ROOT / "testing" / "e2e-report").exists():
        shutil.copytree(ROOT / "testing" / "e2e-report", t / "e2e" / "html-report")
    shutil.copytree(ROOT / "testing" / "results", t / "results")
    shutil.copytree(ROOT / "testing" / "coverage", t / "coverage")
    if (ROOT / "testing" / "README.md").exists():
        shutil.copy2(ROOT / "testing" / "README.md", t / "README.md")

    st = stage / "system_testing"
    st.mkdir()
    for f in ("Test_Cases.xlsx", "Evaluation.md"):
        if (ROOT / "system_testing" / f).exists():
            shutil.copy2(ROOT / "system_testing" / f, st / f)

    d = stage / "docs"
    shutil.copytree(ROOT / "docs" / "screenshots", d / "screenshots", ignore=shutil.ignore_patterns("large", "r3", "nav-*"))
    shutil.copytree(ROOT / "docs" / "diagrams", d / "diagrams", ignore=shutil.ignore_patterns("__pycache__"))
    return stage


def make_zip(stage: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(stage.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(stage.parent).as_posix())


if __name__ == "__main__":
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    stage = build(out)
    print("Staged", stage)
    if "--zip" in sys.argv:
        zp = out / f"{NAME}.zip"
        make_zip(stage, zp)
        print("Zip", zp, f"{zp.stat().st_size / 1024 / 1024:.1f} MB")
