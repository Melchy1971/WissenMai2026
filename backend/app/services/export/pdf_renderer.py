"""PDF renderer for export center.

Structure:
  1. Cover page  — title, exported_at, source count
  2. Table of Contents
  3. Summary  — for each result
  4. Main content  — content_markdown rendered as paragraphs
  5. Sources  — numbered source list (no technical IDs)
  6. Export metadata  — format, date, result count (no IDs, no secrets)

Security:
  - No external resources loaded
  - No scripts
  - No technical IDs (UUIDs) in output
  - No secrets
  - Markdown sanitized: only plain text, lists, headings, bold, italic
"""
from __future__ import annotations

import re
from datetime import datetime
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

# ---------------------------------------------------------------------------
# Brand colours (Telekom-compatible neutral palette)
# ---------------------------------------------------------------------------

_MAGENTA = colors.HexColor("#E20074")
_DARK = colors.HexColor("#1A1A1A")
_GREY = colors.HexColor("#6B6B6B")
_LIGHT_GREY = colors.HexColor("#F5F5F5")
_WHITE = colors.white

# ---------------------------------------------------------------------------
# Page dimensions
# ---------------------------------------------------------------------------

_PAGE_W, _PAGE_H = A4
_MARGIN = 20 * mm
_HEADER_H = 12 * mm
_FOOTER_H = 10 * mm

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

_BASE = getSampleStyleSheet()


def _styles() -> dict[str, ParagraphStyle]:
    return {
        "cover_title": ParagraphStyle(
            "cover_title",
            fontName="Helvetica-Bold",
            fontSize=28,
            textColor=_DARK,
            alignment=TA_LEFT,
            spaceAfter=6 * mm,
            leading=34,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub",
            fontName="Helvetica",
            fontSize=11,
            textColor=_GREY,
            alignment=TA_LEFT,
            spaceAfter=4 * mm,
        ),
        "h1": ParagraphStyle(
            "h1",
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=_DARK,
            spaceBefore=8 * mm,
            spaceAfter=3 * mm,
            leading=20,
        ),
        "h2": ParagraphStyle(
            "h2",
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=_DARK,
            spaceBefore=5 * mm,
            spaceAfter=2 * mm,
            leading=17,
        ),
        "h3": ParagraphStyle(
            "h3",
            fontName="Helvetica-BoldOblique",
            fontSize=11,
            textColor=_GREY,
            spaceBefore=3 * mm,
            spaceAfter=1.5 * mm,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=10,
            textColor=_DARK,
            spaceAfter=2 * mm,
            leading=14,
        ),
        "caption": ParagraphStyle(
            "caption",
            fontName="Helvetica-Oblique",
            fontSize=9,
            textColor=_GREY,
            spaceAfter=1 * mm,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName="Helvetica",
            fontSize=8,
            textColor=_GREY,
            alignment=TA_RIGHT,
        ),
        "toc_entry": ParagraphStyle(
            "toc_entry",
            fontName="Helvetica",
            fontSize=10,
            textColor=_DARK,
            leading=14,
        ),
        "source_label": ParagraphStyle(
            "source_label",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=_DARK,
            spaceAfter=1 * mm,
        ),
        "source_text": ParagraphStyle(
            "source_text",
            fontName="Helvetica",
            fontSize=9,
            textColor=_GREY,
            spaceAfter=2 * mm,
            leftIndent=4 * mm,
        ),
        "meta_key": ParagraphStyle(
            "meta_key",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=_GREY,
        ),
        "meta_val": ParagraphStyle(
            "meta_val",
            fontName="Helvetica",
            fontSize=9,
            textColor=_DARK,
        ),
    }


# ---------------------------------------------------------------------------
# Page template — header + footer
# ---------------------------------------------------------------------------

class _HeaderFooterCanvas:
    """Mixin applied via onFirstPage / onLaterPages callbacks."""

    def __init__(self, title: str, exported_at: str) -> None:
        self.title = title
        self.exported_at = exported_at

    def draw(self, canvas: Any, doc: Any) -> None:
        canvas.saveState()
        w = _PAGE_W
        # Header line
        canvas.setStrokeColor(_MAGENTA)
        canvas.setLineWidth(1.5)
        canvas.line(_MARGIN, _PAGE_H - _MARGIN + 2 * mm, w - _MARGIN, _PAGE_H - _MARGIN + 2 * mm)

        # Header text (title left, date right)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(_MAGENTA)
        canvas.drawString(_MARGIN, _PAGE_H - _MARGIN + 4 * mm, self.title[:60])
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(_GREY)
        canvas.drawRightString(w - _MARGIN, _PAGE_H - _MARGIN + 4 * mm, self.exported_at)

        # Footer line
        canvas.setStrokeColor(_LIGHT_GREY)
        canvas.setLineWidth(0.5)
        canvas.line(_MARGIN, _FOOTER_H, w - _MARGIN, _FOOTER_H)

        # Page number right-aligned
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(_GREY)
        canvas.drawRightString(
            w - _MARGIN, _FOOTER_H - 4 * mm,
            f"Seite {doc.page}",
        )
        canvas.restoreState()


# ---------------------------------------------------------------------------
# Markdown → ReportLab elements (safe subset only)
# ---------------------------------------------------------------------------

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"\*(.+?)\*")
_STRIP_HTML_RE = re.compile(r"<[^>]+>")  # strip any remaining HTML tags


def _md_to_para(text: str, style: ParagraphStyle) -> Paragraph:
    """Convert a single markdown paragraph to a ReportLab Paragraph.

    Supports: **bold**, *italic*. All other HTML is stripped.
    No external resources, no scripts.
    """
    safe = _STRIP_HTML_RE.sub("", text)
    safe = _BOLD_RE.sub(r"<b>\1</b>", safe)
    safe = _ITALIC_RE.sub(r"<i>\1</i>", safe)
    return Paragraph(safe, style)


def _render_markdown_block(md: str, style: ParagraphStyle) -> list:
    """Split markdown into paragraphs and list items; return ReportLab elements."""
    if not md:
        return []
    elements: list = []
    current_list: list[ListItem] = []

    for line in md.splitlines():
        stripped = line.strip()
        if not stripped:
            if current_list:
                elements.append(ListFlowable(current_list, bulletType="bullet", leftIndent=10))
                current_list = []
            elements.append(Spacer(1, 2 * mm))
            continue

        if stripped.startswith("### "):
            _flush_list(elements, current_list)
            current_list = []
            elements.append(_md_to_para(stripped[4:], _styles()["h3"]))
        elif stripped.startswith("## "):
            _flush_list(elements, current_list)
            current_list = []
            elements.append(_md_to_para(stripped[3:], _styles()["h2"]))
        elif stripped.startswith("# "):
            _flush_list(elements, current_list)
            current_list = []
            elements.append(_md_to_para(stripped[2:], _styles()["h1"]))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            current_list.append(
                ListItem(Paragraph(_STRIP_HTML_RE.sub("", stripped[2:]), style), leftIndent=10)
            )
        else:
            _flush_list(elements, current_list)
            current_list = []
            elements.append(_md_to_para(stripped, style))

    _flush_list(elements, current_list)
    return elements


def _flush_list(elements: list, items: list[ListItem]) -> None:
    if items:
        elements.append(ListFlowable(items, bulletType="bullet", leftIndent=10))
        items.clear()


# ---------------------------------------------------------------------------
# Main PdfRenderer
# ---------------------------------------------------------------------------

class PdfRenderer:
    """Renders a content dict to PDF bytes using ReportLab.

    Content dict schema (from ExportService._load_analysis_result_content):
      title: str
      source_type: str
      export_format: str
      exported_at: str  (ISO-8601)
      results: list of:
        title: str
        summary: str
        content_markdown: str
        key_points: list[str]
        suggested_tags: list[str]
        suggested_topics: list[str]
        sources: list[str|dict]
        approved_at: str|None
    """

    def render(self, content: dict) -> bytes:
        buf = BytesIO()
        st = _styles()

        title = content.get("title") or "Export"
        exported_at = content.get("exported_at") or datetime.utcnow().isoformat()
        exported_at_display = exported_at[:19].replace("T", " ")
        results: list[dict] = content.get("results") or []

        hf = _HeaderFooterCanvas(title, exported_at_display)

        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=_MARGIN,
            rightMargin=_MARGIN,
            topMargin=_MARGIN + _HEADER_H,
            bottomMargin=_MARGIN + _FOOTER_H,
            title=title,
            author="Ruflo Export",
            subject="Analyse-Export",
            creator="Ruflo",
            # No external resources
        )

        story: list = []

        # ── 1. Cover page ──────────────────────────────────────────────────
        story.append(Spacer(1, 20 * mm))
        story.append(HRFlowable(width="100%", thickness=3, color=_MAGENTA, spaceAfter=6 * mm))
        story.append(Paragraph(title, st["cover_title"]))
        story.append(Paragraph(f"Exportiert am: {exported_at_display}", st["cover_sub"]))
        story.append(Paragraph(
            f"Anzahl Ergebnisse: {len(results)}", st["cover_sub"]
        ))
        story.append(HRFlowable(width="100%", thickness=1, color=_LIGHT_GREY, spaceBefore=6 * mm))
        story.append(PageBreak())

        # ── 2. Table of Contents ───────────────────────────────────────────
        if len(results) > 1:
            story.append(Paragraph("Inhaltsverzeichnis", st["h1"]))
            for i, r in enumerate(results, 1):
                entry_title = r.get("title") or f"Ergebnis {i}"
                story.append(Paragraph(f"{i}. {entry_title}", st["toc_entry"]))
            story.append(PageBreak())

        # ── 3. Summary ────────────────────────────────────────────────────
        story.append(Paragraph("Zusammenfassung", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=_MAGENTA, spaceAfter=3 * mm))

        for i, r in enumerate(results, 1):
            entry_title = r.get("title") or f"Ergebnis {i}"
            if len(results) > 1:
                story.append(Paragraph(f"{i}. {entry_title}", st["h2"]))
            summary = r.get("summary") or ""
            if summary:
                story.append(_md_to_para(summary, st["body"]))
            key_points: list = r.get("key_points") or []
            if key_points:
                story.append(Paragraph("Kernpunkte", st["h3"]))
                items = [
                    ListItem(Paragraph(str(kp), st["body"]), leftIndent=10)
                    for kp in key_points
                ]
                story.append(ListFlowable(items, bulletType="bullet", leftIndent=10))
            story.append(Spacer(1, 3 * mm))

        story.append(PageBreak())

        # ── 4. Main content ───────────────────────────────────────────────
        story.append(Paragraph("Inhalt", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=_MAGENTA, spaceAfter=3 * mm))

        for i, r in enumerate(results, 1):
            entry_title = r.get("title") or f"Ergebnis {i}"
            if len(results) > 1:
                story.append(Paragraph(f"{i}. {entry_title}", st["h2"]))
            md = r.get("content_markdown") or ""
            if md:
                story.extend(_render_markdown_block(md, st["body"]))
            else:
                story.append(_md_to_para(r.get("summary") or "", st["body"]))

            tags: list = r.get("suggested_tags") or []
            topics: list = r.get("suggested_topics") or []
            if tags:
                story.append(Paragraph(
                    f"<b>Tags:</b> {', '.join(str(t) for t in tags)}", st["caption"]
                ))
            if topics:
                story.append(Paragraph(
                    f"<b>Themen:</b> {', '.join(str(t) for t in topics)}", st["caption"]
                ))
            story.append(Spacer(1, 4 * mm))

        story.append(PageBreak())

        # ── 5. Sources ────────────────────────────────────────────────────
        all_sources: list = []
        for r in results:
            for src in (r.get("sources") or []):
                all_sources.append(src)

        if all_sources:
            story.append(Paragraph("Quellen", st["h1"]))
            story.append(HRFlowable(
                width="100%", thickness=0.5, color=_MAGENTA, spaceAfter=3 * mm
            ))
            for j, src in enumerate(all_sources, 1):
                if isinstance(src, dict):
                    label = src.get("title") or src.get("filename") or f"Quelle {j}"
                    # Omit technical IDs — only show human-readable fields
                    detail = src.get("excerpt") or src.get("description") or ""
                else:
                    label = str(src)
                    detail = ""
                story.append(Paragraph(f"{j}. {label}", st["source_label"]))
                if detail:
                    story.append(Paragraph(detail[:500], st["source_text"]))
            story.append(PageBreak())

        # ── 6. Export metadata (no technical IDs, no secrets) ─────────────
        story.append(Paragraph("Export-Informationen", st["h1"]))
        story.append(HRFlowable(
            width="100%", thickness=0.5, color=_MAGENTA, spaceAfter=3 * mm
        ))
        meta_rows = [
            ("Format", content.get("export_format") or "PDF"),
            ("Exportiert am", exported_at_display),
            ("Anzahl Ergebnisse", str(len(results))),
            ("Quelltyp", content.get("source_type") or ""),
        ]
        meta_table_data = [
            [
                Paragraph(k, st["meta_key"]),
                Paragraph(v, st["meta_val"]),
            ]
            for k, v in meta_rows
        ]
        meta_table = Table(
            meta_table_data,
            colWidths=[50 * mm, 110 * mm],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), _LIGHT_GREY),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [_WHITE, _LIGHT_GREY]),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E0E0E0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]),
        )
        story.append(meta_table)

        doc.build(
            story,
            onFirstPage=hf.draw,
            onLaterPages=hf.draw,
        )
        return buf.getvalue()
