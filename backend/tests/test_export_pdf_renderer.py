"""PDF renderer unit tests.

Covers: Snapshot PDF Metadaten, Seitenzahl vorhanden, Quellen vorhanden,
technische IDs nicht vorhanden, ungültiges Markdown robust.
"""
from __future__ import annotations

import io
import struct

import pytest

pytestmark = pytest.mark.unit_fast

# ---------------------------------------------------------------------------
# Minimal PDF parser (no external dependency)
# ---------------------------------------------------------------------------

def _read_pdf_info(data: bytes) -> dict:
    """Extract basic facts from a PDF byte string without a full parser."""
    text = data.decode("latin-1", errors="replace")
    page_count = text.count("/Type /Page\n") + text.count("/Type/Page\n") + text.count("/Type /Page ")
    has_pages = "/Pages" in text
    return {
        "starts_with_pdf": data[:4] == b"%PDF",
        "has_pages": has_pages,
        "raw_page_count": page_count,
        "size_bytes": len(data),
    }


def _make_content(
    *,
    title: str = "Test Export",
    summary: str = "This is the summary.",
    content_markdown: str = "## Section\n\nSome *italic* and **bold** text.",
    key_points: list | None = None,
    sources: list | None = None,
    tags: list | None = None,
    topics: list | None = None,
    approved_at: str | None = "2026-06-16T10:00:00",
    exported_at: str = "2026-06-16T12:00:00",
) -> dict:
    return {
        "title": title,
        "source_type": "ANALYSIS_RESULT",
        "export_format": "PDF",
        "exported_at": exported_at,
        "results": [
            {
                "title": title,
                "summary": summary,
                "content_markdown": content_markdown,
                "key_points": key_points or ["Point A", "Point B"],
                "suggested_tags": tags or ["tag1"],
                "suggested_topics": topics or ["Topic X"],
                "sources": sources or [
                    {"title": "Quelle Eins", "excerpt": "Some excerpt text"},
                    {"title": "Quelle Zwei", "filename": "doc2.pdf"},
                ],
                "approved_at": approved_at,
            }
        ],
    }


# ---------------------------------------------------------------------------
# Fixture: lazy import so tests are skipped if reportlab is absent
# ---------------------------------------------------------------------------

@pytest.fixture
def renderer():
    try:
        from app.services.export.pdf_renderer import PdfRenderer
        return PdfRenderer()
    except ImportError:
        pytest.skip("reportlab not installed")


# ---------------------------------------------------------------------------
# Snapshot: PDF Metadaten
# ---------------------------------------------------------------------------

def test_pdf_starts_with_pdf_header(renderer) -> None:
    content = _make_content()
    pdf = renderer.render(content)
    assert pdf[:4] == b"%PDF", "Output must start with PDF header"


def test_pdf_has_non_trivial_size(renderer) -> None:
    content = _make_content()
    pdf = renderer.render(content)
    # A real PDF with content and styling should be > 5 KB
    assert len(pdf) > 5_000, f"PDF too small: {len(pdf)} bytes"


def test_pdf_title_in_metadata(renderer) -> None:
    content = _make_content(title="Ruflo Test Report")
    pdf = renderer.render(content)
    text = pdf.decode("latin-1", errors="replace")
    assert "Ruflo Test Report" in text


# ---------------------------------------------------------------------------
# Seitenzahl vorhanden
# ---------------------------------------------------------------------------

def test_pdf_contains_page_type(renderer) -> None:
    content = _make_content()
    pdf = renderer.render(content)
    info = _read_pdf_info(pdf)
    assert info["has_pages"], "PDF must contain /Pages structure"


def test_pdf_multi_result_has_more_pages(renderer) -> None:
    """Multi-result export should produce a larger PDF than single-result."""
    single = _make_content()
    multi = {
        **single,
        "results": [single["results"][0], {**single["results"][0], "title": "Second Result"}],
    }
    pdf_single = renderer.render(single)
    pdf_multi = renderer.render(multi)
    # Multi-result PDF includes TOC page — must be larger
    assert len(pdf_multi) > len(pdf_single)


# ---------------------------------------------------------------------------
# Quellen vorhanden
# ---------------------------------------------------------------------------

def test_pdf_contains_source_titles(renderer) -> None:
    content = _make_content(sources=[
        {"title": "Hauptquelle Alpha", "excerpt": "Relevant passage"},
        {"title": "Nebenquelle Beta"},
    ])
    pdf = renderer.render(content)
    text = pdf.decode("latin-1", errors="replace")
    assert "Hauptquelle Alpha" in text
    assert "Nebenquelle Beta" in text


def test_pdf_no_sources_does_not_crash(renderer) -> None:
    content = _make_content(sources=[])
    pdf = renderer.render(content)
    assert pdf[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# Technische IDs nicht vorhanden
# ---------------------------------------------------------------------------

def test_pdf_does_not_contain_uuid_patterns(renderer) -> None:
    """UUIDs must not appear in the rendered PDF — content dict has none,
    and the renderer must not inject any."""
    content = _make_content()
    pdf = renderer.render(content)
    text = pdf.decode("latin-1", errors="replace")
    import re
    uuid_re = re.compile(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        re.IGNORECASE,
    )
    matches = uuid_re.findall(text)
    assert not matches, f"UUID(s) found in PDF: {matches}"


def test_pdf_does_not_contain_secret_keywords(renderer) -> None:
    content = _make_content()
    pdf = renderer.render(content)
    text = pdf.decode("latin-1", errors="replace").lower()
    for kw in ("password", "secret", "token", "api_key", "authorization"):
        assert kw not in text, f"Secret keyword '{kw}' found in PDF"


# ---------------------------------------------------------------------------
# Ungültiges Markdown robust
# ---------------------------------------------------------------------------

def test_pdf_handles_empty_content_markdown(renderer) -> None:
    content = _make_content(content_markdown="")
    pdf = renderer.render(content)
    assert pdf[:4] == b"%PDF"


def test_pdf_handles_none_summary(renderer) -> None:
    content = _make_content(summary="")
    content["results"][0]["summary"] = None
    pdf = renderer.render(content)
    assert pdf[:4] == b"%PDF"


def test_pdf_handles_deeply_nested_markdown(renderer) -> None:
    md = "\n".join([f"## Section {i}\n\nParagraph {i}." for i in range(50)])
    content = _make_content(content_markdown=md)
    pdf = renderer.render(content)
    assert len(pdf) > 5_000


def test_pdf_strips_html_tags_from_markdown(renderer) -> None:
    """HTML injected into content_markdown must not reach the PDF as raw tags."""
    dangerous_md = "<script>alert('xss')</script>\n\nSafe paragraph."
    content = _make_content(content_markdown=dangerous_md)
    pdf = renderer.render(content)
    text = pdf.decode("latin-1", errors="replace")
    assert "<script>" not in text
    assert "alert" not in text


def test_pdf_handles_empty_results_list(renderer) -> None:
    content = {
        "title": "Empty Export",
        "source_type": "ANALYSIS_RESULT",
        "export_format": "PDF",
        "exported_at": "2026-06-16T12:00:00",
        "results": [],
    }
    pdf = renderer.render(content)
    assert pdf[:4] == b"%PDF"


def test_pdf_handles_missing_content_keys(renderer) -> None:
    content: dict = {}
    pdf = renderer.render(content)
    assert pdf[:4] == b"%PDF"
