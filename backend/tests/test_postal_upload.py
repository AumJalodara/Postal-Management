"""
Tests for Admin Document Upload, Indexing, and Retrieval (Module 3 / Task 3).
"""

import io
from pathlib import Path
import pytest
from pypdf import PdfReader, PdfWriter

from tests.conftest import auth_header_for_user


def create_sample_pdf_bytes() -> bytes:
    """Creates a valid, real test PDF using raw source slice or minimal PdfWriter."""
    raw_pdf_path = Path("data/postal_documents/raw/postal 2024 rule.pdf")
    if raw_pdf_path.exists():
        reader = PdfReader(str(raw_pdf_path))
        writer = PdfWriter()
        # Take page 6 (index 5) which is pure English statutory rules
        page_idx = min(5, len(reader.pages) - 1)
        writer.add_page(reader.pages[page_idx])
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()
    else:
        # Fallback if raw file is missing: generate standard PDF stream
        writer = PdfWriter()
        writer.add_blank_page(width=300, height=300)
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()


def test_admin_upload_postal_document(client, seed_users):
    """Admin can upload an official PDF, extract text, and index statutory chunks."""
    admin_headers = auth_header_for_user(seed_users["admin"])
    pdf_bytes = create_sample_pdf_bytes()

    files = {
        "file": ("test_official_gazette.pdf", pdf_bytes, "application/pdf")
    }
    data = {
        "title": "Post Office Test Directive 2026",
        "document_type": "Statutory Directive",
        "issuing_authority": "Department of Posts"
    }

    res = client.post("/api/v1/postal/upload", headers=admin_headers, files=files, data=data)
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["success"] is True
    doc_data = payload["data"]
    assert doc_data["document_title"] == "Post Office Test Directive 2026"
    assert doc_data["status"] == "indexed"
    assert doc_data["chunks_created"] > 0
    assert doc_data["total_pages"] >= 1


def test_upload_non_admin_forbidden(client, seed_users):
    """Citizen or non-admin user cannot upload official documents."""
    citizen_headers = auth_header_for_user(seed_users["citizen1"])
    pdf_bytes = create_sample_pdf_bytes()

    files = {
        "file": ("unauthorized.pdf", pdf_bytes, "application/pdf")
    }
    res = client.post("/api/v1/postal/upload", headers=citizen_headers, files=files)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN_ROLE"


def test_upload_unauthenticated_unauthorized(client):
    """Anonymous user is rejected with 401."""
    pdf_bytes = create_sample_pdf_bytes()
    files = {
        "file": ("anonymous.pdf", pdf_bytes, "application/pdf")
    }
    res = client.post("/api/v1/postal/upload", files=files)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "MISSING_TOKEN"


def test_upload_invalid_file_extension(client, seed_users):
    """Reject non-PDF file formats."""
    admin_headers = auth_header_for_user(seed_users["admin"])
    files = {
        "file": ("fake_document.txt", b"Plain text content", "text/plain")
    }
    res = client.post("/api/v1/postal/upload", headers=admin_headers, files=files)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_FILE_TYPE"


def test_get_indexed_documents(client, seed_users):
    """Public or administrative inspection of indexed postal legal documents."""
    res = client.get("/api/v1/postal/documents")
    assert res.status_code == 200
    payload = res.json()
    assert payload["success"] is True
    assert isinstance(payload["data"], list)

