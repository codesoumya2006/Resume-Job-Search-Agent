import io
import os
import pytest
from fastapi.testclient import TestClient

os.environ["API_KEY"] = "test-secret-key"

from api.main import app
from services.db import Base, engine

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db() -> None:
    Base.metadata.create_all(engine)


def make_valid_pdf_bytes(text: str = "Senior Python Engineer with 6 years experience in FastAPI and PyTorch") -> bytes:
    """Creates a deterministic valid single-page PDF containing extractable text."""
    stream_content = f"BT /F1 12 Tf 72 712 Td ({text}) Tj ET"
    stream_len = len(stream_content)
    pdf = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length {stream_len} >>
stream
{stream_content}
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000340 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
425
%%EOF"""
    return pdf.encode("latin1")


def make_blank_pdf_bytes() -> bytes:
    """Creates a valid PDF structure with zero text."""
    import pypdf
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def make_valid_docx_bytes(text: str = "Full Stack Developer proficient in React, Python, and SQL") -> bytes:
    """Creates a deterministic valid DOCX containing extractable text."""
    import docx
    doc = docx.Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def make_blank_docx_bytes() -> bytes:
    """Creates a valid DOCX structure with zero text paragraphs."""
    import docx
    doc = docx.Document()
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# -------------------------------------------------------------
# Valid Upload Tests
# -------------------------------------------------------------

def test_valid_pdf_upload_succeeds() -> None:
    pdf_bytes = make_valid_pdf_bytes("Senior Python Engineer with 6 years experience")
    response = client.post(
        "/upload",
        headers={"X-API-Key": "test-secret-key"},
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "Senior Python Engineer" in data["text"]


def test_valid_docx_upload_succeeds() -> None:
    docx_bytes = make_valid_docx_bytes("Full Stack Developer proficient in React")
    response = client.post(
        "/upload",
        headers={"X-API-Key": "test-secret-key"},
        files={"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "Full Stack Developer proficient in React" in data["text"]


def test_valid_txt_upload_succeeds() -> None:
    txt_bytes = b"Backend Engineer with Golang and AWS experience."
    response = client.post(
        "/upload",
        headers={"X-API-Key": "test-secret-key"},
        files={"file": ("resume.txt", txt_bytes, "text/plain")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "Backend Engineer with Golang" in data["text"]


# -------------------------------------------------------------
# Corrupt / Malformed / Empty PDF Tests
# -------------------------------------------------------------

def test_corrupt_pdf_returns_controlled_400() -> None:
    corrupt_bytes = b"%PDF-1.4\ncorrupt header and junk content\x00\xff\xfe random garbage"
    response = client.post(
        "/upload",
        headers={"X-API-Key": "test-secret-key"},
        files={"file": ("bad_resume.pdf", corrupt_bytes, "application/pdf")}
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Corrupt or invalid PDF file" in data["detail"]
    assert "Traceback" not in response.text
    assert "Python" not in data.get("text", "")


def test_truncated_pdf_returns_controlled_400() -> None:
    full_pdf = make_valid_pdf_bytes()
    truncated_bytes = full_pdf[:30]  # truncated halfway through header
    response = client.post(
        "/upload",
        headers={"X-API-Key": "test-secret-key"},
        files={"file": ("truncated.pdf", truncated_bytes, "application/pdf")}
    )
    assert response.status_code == 400
    data = response.json()
    assert "Corrupt or invalid PDF file" in data["detail"]


def test_empty_pdf_returns_controlled_400() -> None:
    response = client.post(
        "/upload",
        headers={"X-API-Key": "test-secret-key"},
        files={"file": ("empty.pdf", b"", "application/pdf")}
    )
    assert response.status_code == 400
    data = response.json()
    assert "Empty file uploaded" in data["detail"]


def test_blank_pdf_without_text_returns_controlled_400() -> None:
    blank_bytes = make_blank_pdf_bytes()
    response = client.post(
        "/upload",
        headers={"X-API-Key": "test-secret-key"},
        files={"file": ("blank.pdf", blank_bytes, "application/pdf")}
    )
    assert response.status_code == 400
    data = response.json()
    assert "contains no extractable text" in data["detail"]


# -------------------------------------------------------------
# Corrupt / Malformed / Empty DOCX Tests
# -------------------------------------------------------------

def test_corrupt_docx_returns_controlled_400() -> None:
    corrupt_bytes = b"PK\x03\x04\x00\x00not a valid docx zip archive\x00\x12\x34"
    response = client.post(
        "/upload",
        headers={"X-API-Key": "test-secret-key"},
        files={"file": ("corrupt.docx", corrupt_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Corrupt or invalid DOCX file" in data["detail"]
    assert "Traceback" not in response.text


def test_truncated_docx_returns_controlled_400() -> None:
    full_docx = make_valid_docx_bytes()
    truncated_bytes = full_docx[:50]
    response = client.post(
        "/upload",
        headers={"X-API-Key": "test-secret-key"},
        files={"file": ("truncated.docx", truncated_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert response.status_code == 400
    data = response.json()
    assert "Corrupt or invalid DOCX file" in data["detail"]


def test_empty_docx_returns_controlled_400() -> None:
    response = client.post(
        "/upload",
        headers={"X-API-Key": "test-secret-key"},
        files={"file": ("empty.docx", b"", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert response.status_code == 400
    data = response.json()
    assert "Empty file uploaded" in data["detail"]


def test_blank_docx_without_text_returns_controlled_400() -> None:
    blank_docx = make_blank_docx_bytes()
    response = client.post(
        "/upload",
        headers={"X-API-Key": "test-secret-key"},
        files={"file": ("blank.docx", blank_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert response.status_code == 400
    data = response.json()
    assert "contains no extractable text" in data["detail"]


# -------------------------------------------------------------
# Miscellaneous & Security Checks
# -------------------------------------------------------------

def test_empty_txt_returns_controlled_400() -> None:
    response = client.post(
        "/upload",
        headers={"X-API-Key": "test-secret-key"},
        files={"file": ("empty.txt", b"   \n  ", "text/plain")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_unsupported_file_extension_returns_controlled_400() -> None:
    response = client.post(
        "/upload",
        headers={"X-API-Key": "test-secret-key"},
        files={"file": ("malware.exe", b"MZ\x90\x00binary content", "application/octet-stream")}
    )
    assert response.status_code == 400
    data = response.json()
    assert "Unsupported file type" in data["detail"]


def test_upload_requires_api_key() -> None:
    response = client.post(
        "/upload",
        files={"file": ("resume.txt", b"text content", "text/plain")}
    )
    assert response.status_code == 401
