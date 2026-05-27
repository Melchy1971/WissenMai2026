from dataclasses import dataclass
from time import perf_counter
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb

from app.core.database import get_connection
from app.models.import_models import NormalizedDocument
from app.observability.logging import log_event, log_import_event
from app.services.advisory_lock import advisory_lock_on_connection
from app.services.chunking_service import MarkdownChunkingService
from app.services.original_file_store import OriginalFileStore



@dataclass(frozen=True)
class PersistedImportDocument:
    document_id: str
    version_id: str | None
    title: str
    chunk_count: int
    duplicate_existing: bool
    import_status: str


class DocumentImportPersistenceService:
    def __init__(
        self,
        chunking_service: MarkdownChunkingService | None = None,
        original_file_store: OriginalFileStore | None = None,
    ) -> None:
        self._chunking_service = chunking_service or MarkdownChunkingService()
        self._original_file_store = original_file_store or OriginalFileStore()

    def persist_import(
        self,
        *,
        workspace_id: str,
        owner_user_id: str,
        title: str,
        mime_type: str,
        content_hash: str,
        document: NormalizedDocument,
        source_filename: str,
        source_bytes: bytes,
        connection: psycopg.Connection | None = None,
    ) -> PersistedImportDocument:
        if connection is not None:
            return self._persist_import_on_connection(
                connection,
                workspace_id=workspace_id,
                owner_user_id=owner_user_id,
                title=title,
                mime_type=mime_type,
                content_hash=content_hash,
                document=document,
                source_filename=source_filename,
                source_bytes=source_bytes,
            )

        with get_connection() as managed_connection:
            return self._persist_import_on_connection(
                managed_connection,
                workspace_id=workspace_id,
                owner_user_id=owner_user_id,
                title=title,
                mime_type=mime_type,
                content_hash=content_hash,
                document=document,
                source_filename=source_filename,
                source_bytes=source_bytes,
            )

    def _persist_import_on_connection(
        self,
        connection: psycopg.Connection,
        *,
        workspace_id: str,
        owner_user_id: str,
        title: str,
        mime_type: str,
        content_hash: str,
        document: NormalizedDocument,
        source_filename: str,
        source_bytes: bytes,
    ) -> PersistedImportDocument:
        existing = self._fetch_existing(connection, workspace_id=workspace_id, content_hash=content_hash)
        if existing is not None:
            log_event(
                "import_duplicate_detected",
                event_type="duplicate_import_detected",
                workspace_id=workspace_id,
                status="completed",
            )
            return existing

        with advisory_lock_on_connection(
            connection,
            scope_name="document_import",
            resource_key=f"{workspace_id}:{content_hash}",
            wait=True,
        ):
            existing = self._fetch_existing(connection, workspace_id=workspace_id, content_hash=content_hash)
            if existing is not None:
                log_event(
                    "import_duplicate_detected",
                    event_type="duplicate_import_detected",
                    workspace_id=workspace_id,
                    status="completed",
                )
                return existing
            try:
                with connection.transaction():
                    return self._insert_document(
                        connection,
                        workspace_id=workspace_id,
                        owner_user_id=owner_user_id,
                        title=title,
                        mime_type=mime_type,
                        content_hash=content_hash,
                        document=document,
                        source_filename=source_filename,
                        source_bytes=source_bytes,
                    )
            except (psycopg.errors.UniqueViolation, psycopg.IntegrityError):
                log_event(
                    "import_duplicate_integrityerror",
                    event_type="duplicate_import_detected",
                    workspace_id=workspace_id,
                    status="completed",
                )
                existing = self._fetch_existing(connection, workspace_id=workspace_id, content_hash=content_hash)
                if existing is not None:
                    return existing
                raise

    def _insert_document(
        self,
        connection: psycopg.Connection,
        *,
        workspace_id: str,
        owner_user_id: str,
        title: str,
        mime_type: str,
        content_hash: str,
        document: NormalizedDocument,
        source_filename: str,
        source_bytes: bytes,
    ) -> PersistedImportDocument:
        document_id = str(uuid4())
        version_id = str(uuid4())
        original_file = self._original_file_store.store_source_file(
            workspace_id=workspace_id,
            document_id=document_id,
            content_hash=content_hash,
            filename=source_filename,
            source_bytes=source_bytes,
        )
        version_metadata = dict(document.metadata)
        version_metadata["backup_original"] = original_file
        parser_type = parser_type_from_document(document)
        chunking_start = perf_counter()
        log_import_event(
            "chunking_started",
            document_id=document_id,
            workspace_id=workspace_id,
            duration_ms=0,
            parser_type=parser_type,
            chunk_count=0,
            status="started",
        )
        try:
            version_chunks = self._chunking_service.chunk(
                document.normalized_markdown,
                document_version_id=version_id,
                source_anchor_type=source_anchor_type_for_document(document),
            )
        except Exception as exc:
            log_import_event(
                "import_failed",
                document_id=document_id,
                workspace_id=workspace_id,
                duration_ms=int((perf_counter() - chunking_start) * 1000),
                parser_type=parser_type,
                chunk_count=0,
                status="failed",
                error_code="CHUNKING_FAILED",
            )
            raise
        chunk_count = len(version_chunks)
        log_import_event(
            "chunking_completed",
            document_id=document_id,
            workspace_id=workspace_id,
            duration_ms=int((perf_counter() - chunking_start) * 1000),
            parser_type=parser_type,
            chunk_count=chunk_count,
            status="completed",
        )

        indexing_start = perf_counter()
        log_import_event(
            "indexing_started",
            document_id=document_id,
            workspace_id=workspace_id,
            duration_ms=0,
            parser_type=parser_type,
            chunk_count=chunk_count,
            status="started",
        )

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    insert into documents (
                        id,
                        workspace_id,
                        owner_user_id,
                        title,
                        source_type,
                        mime_type,
                        content_hash,
                        import_status
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        document_id,
                        workspace_id,
                        owner_user_id,
                        title,
                        "upload",
                        mime_type,
                        content_hash,
                        "pending",
                    ),
                )
                cursor.execute(
                    """
                    insert into document_versions (
                        id,
                        document_id,
                        version_number,
                        normalized_markdown,
                        markdown_hash,
                        parser_version,
                        ocr_used,
                        ki_provider,
                        ki_model,
                        metadata
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        version_id,
                        document_id,
                        1,
                        document.normalized_markdown,
                        document.markdown_hash,
                        document.parser_version or "unknown",
                        document.ocr_used,
                        document.ki_provider,
                        document.ki_model,
                        Jsonb(version_metadata),
                    ),
                )
                cursor.execute(
                    "update documents set current_version_id = %s, import_status = %s, updated_at = now() where id = %s",
                    (version_id, "parsed", document_id),
                )

                chunk_rows = [
                    (
                        str(uuid4()),
                        document_id,
                        version_id,
                        chunk.chunk_index,
                        Jsonb(chunk.heading_path),
                        chunk.anchor,
                        chunk.content,
                        chunk.content_hash,
                        chunk.token_estimate,
                        Jsonb(chunk.metadata),
                    )
                    for chunk in version_chunks
                ]
                if chunk_rows:
                    cursor.executemany(
                        """
                        insert into document_chunks (
                            id,
                            document_id,
                            document_version_id,
                            chunk_index,
                            heading_path,
                            anchor,
                            content,
                            content_hash,
                            token_estimate,
                            metadata
                        )
                        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        chunk_rows,
                    )

                cursor.execute(
                    "update documents set import_status = %s, updated_at = now() where id = %s",
                    ("chunked", document_id),
                )
        except Exception:
            log_import_event(
                "import_failed",
                document_id=document_id,
                workspace_id=workspace_id,
                duration_ms=int((perf_counter() - indexing_start) * 1000),
                parser_type=parser_type,
                chunk_count=chunk_count,
                status="failed",
                error_code="INDEXING_FAILED",
            )
            raise

        log_import_event(
            "indexing_completed",
            document_id=document_id,
            workspace_id=workspace_id,
            duration_ms=int((perf_counter() - indexing_start) * 1000),
            parser_type=parser_type,
            chunk_count=chunk_count,
            status="completed",
        )

        return PersistedImportDocument(
            document_id=document_id,
            version_id=version_id,
            title=title,
            chunk_count=chunk_count,
            duplicate_existing=False,
            import_status="chunked",
        )

    def _fetch_existing(
        self,
        connection: psycopg.Connection,
        *,
        workspace_id: str,
        content_hash: str,
    ) -> PersistedImportDocument | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select d.id, d.current_version_id, d.title, count(c.id)
                from documents d
                left join document_chunks c on c.document_id = d.id
                where d.workspace_id = %s and d.content_hash = %s
                group by d.id, d.current_version_id, d.title
                order by d.created_at asc
                limit 1
                """,
                (workspace_id, content_hash),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        return PersistedImportDocument(
            document_id=str(row[0]),
            version_id=str(row[1]) if row[1] is not None else None,
            title=row[2],
            chunk_count=row[3],
            duplicate_existing=True,
            import_status="duplicate",
        )

def source_anchor_type_for_document(document: NormalizedDocument) -> str:
    mime_type = str(document.metadata.get("mime_type") or "")
    parser_name = document.parser_version or ""
    if mime_type == "application/pdf":
        return "pdf_page"
    if mime_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    }:
        return "docx_paragraph"
    if mime_type.startswith("text/") or parser_name:
        return "text"
    return "legacy_unknown"


def parser_type_from_document(document: NormalizedDocument) -> str:
    parser_name = document.metadata.get("parser_name") if isinstance(document.metadata, dict) else None
    if isinstance(parser_name, str) and parser_name.strip():
        return parser_name.strip()
    if isinstance(document.parser_version, str) and document.parser_version.strip():
        return document.parser_version.strip()
    return "unknown"
