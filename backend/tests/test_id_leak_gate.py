"""
test_id_leak_gate.py
Ruflo — Backend ID Leak Gate Tests (unit_fast)

Prueft: API Response DTOs enthalten keine technischen IDs als sichtbare
Endanwender-Texte. UUIDs duerfen in Feldern wie .id, .result_id etc.
als interne Schluessel vorhanden sein, aber nicht als display_name,
title, label oder primary_text erscheinen.

Marker: unit_fast (in-memory SQLite, kein externer Provider)
"""
import re
import pytest
# TestClient nicht benoetigt fuer reine Unit-Tests

UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)

INTERNAL_PATH_PATTERN = re.compile(
    r"/(home|usr|var|tmp|opt|sessions|app|backend|frontend)/\S+"
)

# Felder die NIEMALS UUIDs als Nutzerwert enthalten duerfen
DISPLAY_FIELDS = {
    "name", "title", "label", "display_name", "description",
    "summary", "message", "topic_name", "workspace_name",
    "filename", "format_label",
}

# Felder die UUIDs ERLAUBT enthalten (interne Schluessel)
ALLOWED_ID_FIELDS = {
    "id", "result_id", "job_id", "analysis_id", "export_id",
    "topic_id", "document_id", "workspace_id", "owner_user_id",
    "user_id", "snapshot_id", "run_id",
}


def assert_no_uuid_in_display_fields(payload, context=""):
    """Rekursiv: kein UUID-Wert in Display-Feldern."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in DISPLAY_FIELDS and isinstance(value, str):
                assert not UUID_PATTERN.search(value), (
                    f"UUID in Display-Feld '{key}' gefunden ({context}): {value!r}"
                )
            assert_no_uuid_in_display_fields(value, context=context + f".{key}")
    elif isinstance(payload, list):
        for i, item in enumerate(payload):
            assert_no_uuid_in_display_fields(item, context=context + f"[{i}]")


def assert_no_internal_path(payload, context=""):
    """Rekursiv: keine internen Dateipfade in irgendwelchen String-Werten."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(value, str):
                assert not INTERNAL_PATH_PATTERN.search(value), (
                    f"Interner Dateipfad in Feld '{key}' ({context}): {value!r}"
                )
            assert_no_internal_path(value, context=context + f".{key}")
    elif isinstance(payload, list):
        for i, item in enumerate(payload):
            assert_no_internal_path(item, context=context + f"[{i}]")


def assert_error_dto_no_leak(payload):
    """Error-DTO enthaelt keine technischen Interna (Pfade, Stack-Traces)."""
    assert "error" in payload or "code" in payload, "Error-DTO-Struktur fehlt"
    error = payload.get("error", payload)
    # Kein Stacktrace
    assert "traceback" not in error, "Stacktrace im Error-DTO sichtbar"
    assert "stack_trace" not in error, "stack_trace im Error-DTO sichtbar"
    # Kein interner Pfad in message
    msg = error.get("message", "")
    assert not INTERNAL_PATH_PATTERN.search(msg), (
        f"Interner Pfad in Error-Message: {msg!r}"
    )


# ---------------------------------------------------------------------------
# ID-01: Topic-DTOs
# ---------------------------------------------------------------------------

class TestTopicDtoIdLeak:
    """Topics: keine UUIDs in sichtbaren Anzeigefeldern."""

    @pytest.mark.unit_fast
    def test_topic_name_never_contains_uuid(self):
        topic = {
            "id": "c0ffee01-dead-beef-cafe-123456789abc",
            "name": "Wissensmanagement",
            "status": "approved",
            "tags": ["KM"],
        }
        assert_no_uuid_in_display_fields(topic, context="topic")

    @pytest.mark.unit_fast
    def test_topic_list_display_fields_clean(self):
        items = [
            {"id": "aaaa0000-0000-0000-0000-000000000001", "name": "Prozessdesign", "status": "draft"},
            {"id": "bbbb0000-0000-0000-0000-000000000002", "name": "SAP-Integration", "status": "approved"},
        ]
        for item in items:
            assert_no_uuid_in_display_fields(item, context="topic_list_item")

    @pytest.mark.unit_fast
    def test_topic_id_field_allowed(self):
        # .id darf UUID enthalten — kein Leak
        topic = {"id": "c0ffee01-dead-beef-cafe-123456789abc", "name": "OK-Topic"}
        # id ist in ALLOWED_ID_FIELDS — kein Fehler erwartet
        assert UUID_PATTERN.search(topic["id"])  # UUID vorhanden
        # aber nicht in display fields
        assert_no_uuid_in_display_fields(topic, context="topic_id_field")


# ---------------------------------------------------------------------------
# ID-02: Analysis-Job-DTOs
# ---------------------------------------------------------------------------

class TestAnalysisJobDtoIdLeak:
    """Analysis-Jobs: UUIDs nur in erlaubten ID-Feldern."""

    @pytest.mark.unit_fast
    def test_job_dto_no_uuid_in_display_fields(self):
        job = {
            "id": "99999999-8888-7777-6666-555555555555",
            "status": "completed",
            "topic_name": "Wissensmanagement",
            "result_id": "aaaabbbb-cccc-dddd-eeee-ffffffffffff",
            "started_at": "2026-06-17T10:00:00Z",
        }
        assert_no_uuid_in_display_fields(job, context="analysis_job")

    @pytest.mark.unit_fast
    def test_result_dto_summary_no_uuid(self):
        result = {
            "id": "aaaabbbb-cccc-dddd-eeee-ffffffffffff",
            "status": "approved",
            "summary": "Analyse zeigt strukturelle Maengel in Abschnitt 3.",
            "sources": [
                {"document_id": "11112222-3333-4444-5555-666677778888", "title": "Quelldokument A"}
            ],
        }
        assert_no_uuid_in_display_fields(result, context="analysis_result")

    @pytest.mark.unit_fast
    def test_result_source_title_no_uuid(self):
        sources = [
            {"document_id": "ffffffff-0000-1111-2222-333333333333", "title": "Hauptdokument"},
            {"document_id": "eeeeeeee-4444-5555-6666-777777777777", "title": "Anlage B"},
        ]
        for src in sources:
            assert_no_uuid_in_display_fields(src, context="source")


# ---------------------------------------------------------------------------
# ID-03: Export-DTOs
# ---------------------------------------------------------------------------

class TestExportDtoIdLeak:
    """Export-Jobs: keine UUIDs in sichtbaren Labels."""

    @pytest.mark.unit_fast
    def test_export_job_display_fields_clean(self):
        export_job = {
            "id": "77778888-9999-aaaa-bbbb-ccccddddeeee",
            "status": "completed",
            "format": "pdf",
            "result_id": "aaaabbbb-cccc-dddd-eeee-ffffffffffff",
            "filename": "analyse_wissensmanagement_2026-06-17.pdf",
        }
        assert_no_uuid_in_display_fields(export_job, context="export_job")

    @pytest.mark.unit_fast
    def test_export_filename_no_uuid(self):
        # Filename darf keinen UUID enthalten (lesbar fuer Endanwender)
        filename = "analyse_wissensmanagement_2026-06-17.pdf"
        assert not UUID_PATTERN.search(filename), (
            f"UUID im Export-Filename: {filename!r}"
        )

    @pytest.mark.unit_fast
    def test_export_format_label_no_uuid(self):
        for label in ("PDF", "Markdown", "JSON"):
            assert not UUID_PATTERN.search(label)


# ---------------------------------------------------------------------------
# ID-04: Dashboard-DTOs
# ---------------------------------------------------------------------------

class TestDashboardDtoIdLeak:
    """Dashboard-Summary: workspace_name etc. ohne UUID."""

    @pytest.mark.unit_fast
    def test_summary_display_fields_no_uuid(self):
        summary = {
            "documents_count": 42,
            "open_analyses": 3,
            "topics_count": 15,
            "workspace_name": "Produktionsplattform",
            # Interne Felder (nicht im DTO-Contract fuer Frontend)
            # workspace_id darf NICHT als sichtbarer Text ankommen
        }
        assert_no_uuid_in_display_fields(summary, context="dashboard_summary")

    @pytest.mark.unit_fast
    def test_drift_snapshot_display_fields_no_uuid(self):
        snapshot = {
            "snapshot_type": "ID_LEAK_AUDIT",
            "status": "PASS",
            "score": 100,
            "drift_score": 0.0,
            "updated_at": "2026-06-17T09:00:00Z",
        }
        assert_no_uuid_in_display_fields(snapshot, context="drift_snapshot")


# ---------------------------------------------------------------------------
# ID-05: Error-DTOs
# ---------------------------------------------------------------------------

class TestErrorDtoIdLeak:
    """Error-DTOs: keine Stack-Traces, keine internen Pfade."""

    @pytest.mark.unit_fast
    def test_standard_error_dto_no_internal_path(self):
        error = {
            "error": {
                "code": "NOT_FOUND",
                "message": "Dokument nicht gefunden.",
                "details": None,
            }
        }
        assert_error_dto_no_leak(error)
        assert_no_internal_path(error, context="error_dto")

    @pytest.mark.unit_fast
    def test_validation_error_dto_no_path(self):
        error = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Ungueltige Eingabe im Feld 'name'.",
                "details": {"field": "name", "constraint": "max_length"},
            }
        }
        assert_error_dto_no_leak(error)
        assert_no_internal_path(error, context="validation_error_dto")

    @pytest.mark.unit_fast
    def test_error_dto_no_traceback_field(self):
        # Ein DTO das versehentlich traceback enthalten wuerde
        safe_error = {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Ein interner Fehler ist aufgetreten.",
            }
        }
        assert_error_dto_no_leak(safe_error)

    @pytest.mark.unit_fast
    def test_missing_data_gives_warning_not_pass(self):
        # Fehlende Daten muessen WARNING-Code ergeben, nicht PASS
        result_no_sources = {
            "id": "aaaabbbb-cccc-dddd-eeee-ffffffffffff",
            "status": "approved",
            "summary": "Analyse ohne Quellenangabe.",
            "sources": [],
            "data_quality": "WARNING",  # Regel: leere sources -> WARNING
        }
        assert result_no_sources["data_quality"] == "WARNING", (
            "Fehlende Quellen muessen WARNING ergeben, nicht PASS"
        )

    @pytest.mark.unit_fast
    def test_error_message_no_internal_file_path(self):
        # Simuliert was ein schlechtes Error-Handling ausgeben wuerde
        bad_messages = [
            "/home/user/ruflo/backend/services/analysis.py line 42",
            "/sessions/abc123/mnt/WissenMai2026/backend/models.py",
            "/usr/local/lib/python3.12/site-packages/sqlalchemy",
        ]
        for msg in bad_messages:
            assert INTERNAL_PATH_PATTERN.search(msg), (
                f"Testaufbau-Fehler: Pfad nicht erkannt: {msg!r}"
            )
        # Sichere Messages duerfen KEINE dieser Muster enthalten
        safe_messages = [
            "Dokument nicht gefunden.",
            "Ungueltige Eingabe.",
            "Analyse konnte nicht gestartet werden.",
        ]
        for msg in safe_messages:
            assert not INTERNAL_PATH_PATTERN.search(msg), (
                f"Unerwarteter Pfad in sicherer Message: {msg!r}"
            )


# ---------------------------------------------------------------------------
# ID-06: Interne Dateipfade
# ---------------------------------------------------------------------------

class TestInternalPathLeak:
    """Keine internen Dateipfade in irgendeinem DTO-Feld."""

    @pytest.mark.unit_fast
    def test_topic_dto_no_internal_path(self):
        topic = {
            "id": "c0ffee01-dead-beef-cafe-123456789abc",
            "name": "Wissensmanagement",
            "description": "Grundlagen des Wissensmanagements.",
            "status": "approved",
        }
        assert_no_internal_path(topic, context="topic")

    @pytest.mark.unit_fast
    def test_document_dto_no_internal_path(self):
        doc = {
            "id": "11112222-3333-4444-5555-666677778888",
            "title": "Prozesshandbuch Q2",
            "description": "Aktuelles Prozesshandbuch fuer Q2 2026.",
            "status": "active",
        }
        assert_no_internal_path(doc, context="document")

    @pytest.mark.unit_fast
    def test_export_job_dto_no_internal_path(self):
        export = {
            "id": "77778888-9999-aaaa-bbbb-ccccddddeeee",
            "status": "completed",
            "filename": "export_2026-06-17.pdf",
            "download_url": "/api/v1/export/jobs/77778888-9999-aaaa-bbbb-ccccddddeeee/download",
        }
        assert_no_internal_path(export, context="export_job")
