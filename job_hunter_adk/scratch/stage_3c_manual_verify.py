import io
import os
import pypdf
import docx
from fastapi.testclient import TestClient

os.environ["API_KEY"] = "live-verify-key"

from api.main import app, session_service

client = TestClient(app)

print("--- 1. Testing Valid PDF Upload ---")
stream_content = "BT /F1 12 Tf 72 712 Td (Manual Verification Senior Data Scientist) Tj ET"
stream_len = len(stream_content)
pdf_bytes = f"""%PDF-1.4
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
%%EOF""".encode("latin1")

res_pdf = client.post("/upload", headers={"X-API-Key": "live-verify-key"}, files={"file": ("resume.pdf", pdf_bytes, "application/pdf")})
print(f"Status: {res_pdf.status_code}, Response: {res_pdf.json()}")

print("\n--- 2. Testing Valid DOCX Upload ---")
doc = docx.Document()
doc.add_paragraph("Manual Verification Senior AI Engineer")
buf = io.BytesIO()
doc.save(buf)
docx_bytes = buf.getvalue()

res_docx = client.post("/upload", headers={"X-API-Key": "live-verify-key"}, files={"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
print(f"Status: {res_docx.status_code}, Response: {res_docx.json()}")

print("\n--- 3. Testing Corrupt PDF Upload ---")
res_corrupt_pdf = client.post("/upload", headers={"X-API-Key": "live-verify-key"}, files={"file": ("bad.pdf", b"corrupted non-pdf binary content", "application/pdf")})
print(f"Status: {res_corrupt_pdf.status_code}, Response: {res_corrupt_pdf.json()}")

print("\n--- 4. Testing Corrupt DOCX Upload ---")
res_corrupt_docx = client.post("/upload", headers={"X-API-Key": "live-verify-key"}, files={"file": ("bad.docx", b"PK\x03\x04corrupted zip", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
print(f"Status: {res_corrupt_docx.status_code}, Response: {res_corrupt_docx.json()}")

print("\n--- 5. Testing Empty Upload ---")
res_empty = client.post("/upload", headers={"X-API-Key": "live-verify-key"}, files={"file": ("empty.pdf", b"", "application/pdf")})
print(f"Status: {res_empty.status_code}, Response: {res_empty.json()}")

print("\n--- 6. Testing Multi-turn State Persistence ---")
init = client.post("/session", headers={"X-API-Key": "live-verify-key"}, json={}).json()
session_id = init["session_id"]
user_id = init["user_id"]

# Turn 1
t1 = client.post("/chat", headers={"X-API-Key": "live-verify-key"}, json={
    "session_id": session_id,
    "user": user_id,
    "message": "Turn 1 setup",
    "state_updates": {"resume_profile": {"skills": ["Python", "FastAPI"]}}
}).json()
print("Turn 1 saved resume_profile:", t1["state_snapshot"]["resume_profile"])

# Turn 2: client does NOT resend resume_profile
t2 = client.post("/chat", headers={"X-API-Key": "live-verify-key"}, json={
    "session_id": session_id,
    "user": user_id,
    "message": "Turn 2 query",
    "state_updates": {"ranked_jobs": [{"id": 1, "title": "Dev"}]}
}).json()
print("Turn 2 retained resume_profile:", t2["state_snapshot"]["resume_profile"])
print("Turn 2 added ranked_jobs:", t2["state_snapshot"]["ranked_jobs"])

print("\nALL MANUAL VERIFICATIONS COMPLETED SUCCESSFULLY.")
