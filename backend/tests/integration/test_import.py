"""Bulk candidate import (CSV / Excel) and CV text extraction."""
import csv
import io
import zipfile

from tests.helpers import assert_error

HEADER = ["full_name", "email", "phone", "location", "years_experience", "education", "previous_titles", "skills", "resume_summary"]
SUMMARY = "Backend developer who builds REST APIs in Python and Django for an online retailer."


def _csv(rows, header=HEADER) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _upload(client, name, content, path="/api/candidates/import"):
    return client.post(path, files={"file": (name, content, "application/octet-stream")})


GOOD = ["Ayanda Zulu", "ayanda@example.com", "+27 82 555 0101", "Durban", "4", "Bachelor's Degree", "Developer", "Python; Django; SQL", SUMMARY]


class TestCsvImport:
    def test_valid_rows_saved(self, client):
        rows = [GOOD, ["Lerato Moloi", "", "", "Cape Town", "2", "3", "", "SQL, Power BI", SUMMARY]]
        r = _upload(client, "candidates.csv", _csv(rows))
        assert r.status_code == 200, r.text
        assert r.json() == {"created": 2, "skipped": 0, "errors": []}
        items = {c["full_name"]: c for c in client.get("/api/candidates").json()["items"]}
        assert items["Ayanda Zulu"]["location"] == "Durban" and items["Ayanda Zulu"]["level_name"] == "Bachelor's Degree"
        assert sorted(items["Lerato Moloi"]["skills"]) == ["Power BI", "SQL"] and items["Lerato Moloi"]["level_id"] == 3

    def test_invalid_rows_reported_valid_rows_kept(self, client):
        rows = [
            GOOD,
            ["X", "", "", "", "3", "Diploma", "", "Python", SUMMARY],  # name too short
            ["Thabo Nkosi", "", "", "", "-1", "Diploma", "", "Python", SUMMARY],  # negative years
            ["Mpho Dube", "", "", "", "3", "Grade 9", "", "Python", SUMMARY],  # unknown education
            ["Zanele Cele", "", "", "", "3", "Diploma", "", "", SUMMARY],  # no skills
            ["Karabo Phiri", "", "", "", "3", "Diploma", "", "Python", "too short"],
        ]
        body = _upload(client, "c.csv", _csv(rows)).json()
        assert body["created"] == 1
        errs = {e["row"]: e for e in body["errors"]}
        assert sorted(errs) == [3, 4, 5, 6, 7]
        assert errs[3]["field"] == "full_name"
        assert errs[4]["field"] == "years_experience" and "less than 0" in errs[4]["message"]
        assert errs[5]["field"] == "education"
        assert errs[6]["field"] == "skills"
        assert errs[7]["field"] == "resume_summary" and "20" in errs[7]["message"]

    def test_duplicate_email_skipped(self, client):
        _upload(client, "c.csv", _csv([GOOD]))
        body = _upload(client, "c.csv", _csv([GOOD, GOOD])).json()
        assert body == {"created": 0, "skipped": 2, "errors": []}
        assert client.get("/api/candidates").json()["total"] == 1

    def test_header_aliases(self, client):
        header = ["Name", "Years", "Qualification", "Skills", "CV Summary"]
        body = _upload(client, "c.csv", _csv([["Sipho Dlamini", "5", "Honours", "Python", SUMMARY]], header)).json()
        assert body["created"] == 1

    def test_missing_columns(self, client):
        r = _upload(client, "c.csv", _csv([["A B"]], header=["full_name"]))
        assert_error(r, 422, "file", "missing column")

    def test_wrong_file_type(self, client):
        assert_error(_upload(client, "c.json", b"{}"), 415, "file")

    def test_empty_file(self, client):
        assert_error(_upload(client, "c.csv", b"\n\n"), 422, "file", "empty")

    def test_too_large(self, client):
        assert_error(_upload(client, "c.csv", b"a" * (5 * 1024 * 1024 + 1)), 413, "file")

    def test_template(self, client):
        r = client.get("/api/candidates/import/template")
        assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
        header = next(csv.reader(io.StringIO(r.text.lstrip("﻿"))))
        assert header == HEADER

    def test_template_round_trips(self, client):
        r = client.get("/api/candidates/import/template")
        body = _upload(client, "template.csv", r.content).json()
        assert body["created"] == 1


class TestExcelImport:
    def test_xlsx(self, client):
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.append(HEADER)
        ws.append(["Naledi Mokoena", "naledi@example.com", None, "Pretoria", 3, "Honours", None, "Python, SQL", SUMMARY])
        buf = io.BytesIO()
        wb.save(buf)
        body = _upload(client, "people.xlsx", buf.getvalue()).json()
        assert body["created"] == 1
        c = client.get("/api/candidates").json()["items"][0]
        assert c["years_experience"] == 3 and c["level_name"] == "Honours"

    def test_corrupt_xlsx(self, client):
        assert_error(_upload(client, "bad.xlsx", b"not really excel"), 400, "file", "could not be read")


def _docx(paragraphs) -> bytes:
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", xml)
    return buf.getvalue()


def _pdf(text: str) -> bytes:
    """Smallest valid one-page PDF with a line of text (Helvetica)."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode() + o + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(f"trailer << /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return out.getvalue()


class TestCvParsing:
    path = "/api/candidates/parse-cv"

    def test_txt(self, client):
        text = "Thabo Mokoena\nthabo.m@example.com  082 555 1234\nData engineer using Python, SQL and K8s on AWS."
        r = _upload(client, "cv.txt", text.encode(), self.path)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["full_name"] == "Thabo Mokoena"
        assert body["email"] == "thabo.m@example.com" and body["phone"] == "082 555 1234"
        assert {"python", "sql", "kubernetes", "aws"} <= set(body["skills"])
        assert "Data engineer" in body["resume_summary"] and body["truncated"] is False

    def test_docx(self, client):
        content = _docx(["Lerato Mahlangu", "Business analyst who models processes and writes SQL &amp; reports."])
        body = _upload(client, "cv.docx", content, self.path).json()
        assert body["full_name"] == "Lerato Mahlangu"
        assert "SQL & reports" in body["resume_summary"]

    def test_pdf(self, client):
        body = _upload(client, "cv.pdf", _pdf("Cloud engineer with Terraform and Linux experience"), self.path).json()
        assert "terraform" in body["skills"] and "linux" in body["skills"]

    def test_long_cv_truncated_to_3000(self, client):
        text = "Experienced developer. " + "Built many Python services. " * 200
        body = _upload(client, "cv.txt", text.encode(), self.path).json()
        assert body["truncated"] is True and len(body["resume_summary"]) <= 3000

    def test_unsupported_type(self, client):
        assert_error(_upload(client, "cv.png", b"\x89PNG", self.path), 415, "file")

    def test_no_text(self, client):
        assert_error(_upload(client, "cv.txt", b"   ", self.path), 422, "file", "no readable text")

    def test_broken_docx(self, client):
        assert_error(_upload(client, "cv.docx", b"not a zip", self.path), 400, "file", "could not be read")

    def test_resource_manager_cannot_import(self, client, login):
        r = client.post(self.path, files={"file": ("cv.txt", b"hello world " * 5)}, headers=login("resource_manager"))
        assert_error(r, 403)
