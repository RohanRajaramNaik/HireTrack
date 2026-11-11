"""Build Test_Cases.xlsx from test_cases.py.   python system_testing/build_test_cases_xlsx.py"""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from test_cases import CASES, COLUMNS, REQUIREMENTS

OUT = Path(__file__).resolve().parent / "Test_Cases.xlsx"
HEAD = PatternFill("solid", fgColor="1D3FBF")
PASS = PatternFill("solid", fgColor="E8F5EC")
FAIL = PatternFill("solid", fgColor="FDECEC")
THIN = Side(style="thin", color="CBD1DA")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")


def style_header(ws, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEAD
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        cell.border = BORDER
    ws.freeze_panes = "B2"
    ws.row_dimensions[1].height = 30


wb = Workbook()

# Sheet 1: test cases
ws = wb.active
ws.title = "Test Cases"
ws.append(COLUMNS)
for case in CASES:
    ws.append(list(case))
widths = [9, 14, 34, 24, 44, 26, 40, 40, 10, 34]
for i, w in enumerate(widths, start=1):
    ws.column_dimensions[get_column_letter(i)].width = w
for row in ws.iter_rows(min_row=2):
    for cell in row:
        cell.alignment = WRAP
        cell.border = BORDER
    res = row[8]
    res.fill = PASS if res.value == "Pass" else FAIL
    res.font = Font(bold=True, color="157A3B" if res.value == "Pass" else "B91C1C")
    res.alignment = Alignment(horizontal="center", vertical="top")
style_header(ws, len(COLUMNS))
ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}{len(CASES) + 1}"

# Sheet 2: traceability
tr = wb.create_sheet("Traceability")
tr.append(["Requirement", "Description", "Test cases", "Count", "All passed"])
for rid, desc in REQUIREMENTS:
    hits = [c[0] for c in CASES if rid in [t.strip() for t in c[1].split(",")]]
    passed = all(c[8] == "Pass" for c in CASES if c[0] in hits) and bool(hits)
    tr.append([rid, desc, ", ".join(hits), len(hits), "Yes" if passed else "NO TEST"])
for i, w in enumerate([12, 70, 40, 8, 11], start=1):
    tr.column_dimensions[get_column_letter(i)].width = w
for row in tr.iter_rows(min_row=2):
    for cell in row:
        cell.alignment = WRAP
        cell.border = BORDER
    row[4].fill = PASS if row[4].value == "Yes" else FAIL
style_header(tr, 5)

# Sheet 3: summary
sm = wb.create_sheet("Summary")
rows = [
    ("Suite", "Tool", "Tests", "Passed", "Pass rate"),
    ("Backend unit", "pytest", 133, 133, 1.0),
    ("Backend integration (API)", "pytest + FastAPI TestClient", 197, 197, 1.0),
    ("Frontend components", "Vitest + React Testing Library", 49, 49, 1.0),
    ("End-to-end (Edge)", "Playwright", 22, 22, 1.0),
    ("End-to-end (Chrome)", "Playwright", 22, 22, 1.0),
    ("System test cases (this workbook)", "Manual + automated", len(CASES), sum(c[8] == "Pass" for c in CASES), None),
    ("", "", "", "", ""),
    ("Backend line coverage", "pytest-cov", "", "", 0.95),
    ("Frontend line coverage", "Vitest v8", "", "", 0.506),
]
for r in rows:
    sm.append(list(r))
sm["E7"] = "=D7/C7"
for r in range(2, 11):
    sm.cell(row=r, column=5).number_format = "0.0%"
for i, w in enumerate([36, 32, 10, 10, 12], start=1):
    sm.column_dimensions[get_column_letter(i)].width = w
for row in sm.iter_rows(min_row=1, max_row=7):
    for cell in row:
        cell.border = BORDER
style_header(sm, 5)
sm.freeze_panes = None

wb.save(OUT)
print("wrote", OUT, len(CASES), "cases")
