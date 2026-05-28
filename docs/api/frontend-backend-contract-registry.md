# Frontend/Backend Contract Registry

Stand: 2026-05-18
API-Version: v1
Scope: Alle GUI-verwendeten HTTP-Contracts zwischen Frontend (React/Vite) und Backend (FastAPI).

## Breaking-Change-Regeln

Ein Contract-Change ist **breaking**, wenn er eines der folgenden tut:

- ein required field entfernt, umbenennt oder nullable macht, obwohl es bisher non-null war
- den Typ eines Feldes ändert
- einen Enum-Wert entfernt oder dessen Bedeutung ändert
- einen Error-Code entfernt, umbenennt oder auf eine andere Fehlerklasse mappt
- ein Array in ein Objekt oder ein Objekt in ein Array ändert
- ein bisher optionales Feld required macht
- Datumsformat, ID-Format oder Pagination-Semantik inkompatibel ändert

Nicht-breaking:

- neues optionales Feld
- neuer Enum-Wert, wenn das Frontend unbekannte Werte kontrolliert als `unknown` anzeigen kann
- neuer Error-Code, wenn er zusätzlich dokumentiert und vom zentralen API-Client klassifiziert wird
- neue `details`-Felder in `ErrorResponse`

Pflichtprozess:

1. Breaking Changes erfordern neue Contract-Version (`v2` oder explizites Feld-Deprecation-Fenster).
2. Deprecated fields bleiben mindestens eine Minor-Version erhalten und müssen hier dokumentiert sein.
3. Contract-Tests (`test_frontend_backend_contracts.py`) müssen vor Merge grün sein. Quelle: `reports/current/masterplan_status.json`.
4. Frontend-Mapping (`mappers.js`, `errorCatalog.js`) und diese Registry müssen im selben PR aktualisiert werden.
5. Pydantic-Schema-Änderungen erfordern Registry-Update im selben Change.

## Gemeinsame Regeln

- IDs sind Strings (UUID-Format).
- Zeitstempel sind ISO-8601 Strings.
- `ErrorResponse` ist die einzige Fehlerform für alle 4xx/5xx Responses.
- `Authorization: Bearer <token>` und `X-Workspace-Id: <id>` werden vom zentralen Frontend API Client gesetzt.
- **Nullable** (`string | null`): Feld ist immer in der Response vorhanden, Wert kann `null` sein.
- **Optional**: Feld kann in der Response fehlen (nur wo explizit markiert).
- Deprecated fields: aktuell keine.

## 1. AuthMeResponse

Version: `v1`
Endpoint: `GET /api/v1/auth/me`

Required fields:
- `user: AuthUser`
- `memberships: WorkspaceMembership[]`
- `active_workspace_id: string | null`

AuthUser required fields:
- `id: string`
- `login: string`
- `display_name: string`

Optional fields: keine
Enum values: keine
Error codes: `AUTH_REQUIRED`
Deprecated fields: keine

## 2. WorkspaceMembership

Version: `v1`
Used by: `AuthMeResponse`, Login-Response

Required fields:
- `workspace_id: string`
- `role: string`

Optional fields: keine
Enum values: `role` — bekannte Werte: `owner`, `admin`, `member`. Frontend behandelt unbekannte Werte konservativ.
Error codes: keine eigenen
Deprecated fields: keine

## 3. DocumentListResponse

Version: `v1`
Endpoint: `GET /documents`
Shape: `DocumentListItem[]`

Required fields per item:
- `id: string`
- `title: string`
- `mime_type: string | null`
- `created_at: string`
- `updated_at: string`
- `latest_version_id: string | null`
- `import_status: ImportStatus`
- `lifecycle_status: LifecycleStatus`
- `archived_at: string | null`
- `deleted_at: string | null`
- `version_count: number`
- `chunk_count: number`

Optional fields: keine
Enum values:
- `ImportStatus`: `pending`, `parsing`, `parsed`, `chunked`, `failed`, `duplicate`
- `LifecycleStatus`: `active`, `archived`, `deleted`

Error codes: `AUTH_REQUIRED`, `WORKSPACE_ACCESS_FORBIDDEN`, `INVALID_PAGINATION`, `INVALID_LIFECYCLE_STATUS`, `INTERNAL_ERROR`
Deprecated fields: keine

## 4. DocumentDetailResponse

Version: `v1`
Endpoint: `GET /documents/{document_id}`

Required fields:
- `id: string`
- `workspace_id: string`
- `owner_user_id: string`
- `title: string`
- `source_type: string`
- `mime_type: string | null`
- `content_hash: string`
- `created_at: string`
- `updated_at: string`
- `latest_version_id: string | null`
- `latest_version: DocumentVersionSummary | null`
- `parser_metadata: DocumentParserMetadata | null`
- `import_status: ImportStatus`
- `lifecycle_status: LifecycleStatus`
- `archived_at: string | null`
- `deleted_at: string | null`
- `chunk_summary: DocumentChunkSummary`

DocumentVersionSummary fields (wenn `latest_version != null`):
- `id: string`
- `version_number: number`
- `created_at: string`
- `content_hash: string`

DocumentParserMetadata fields (wenn `parser_metadata != null`):
- `parser_version: string`
- `ocr_used: boolean`
- `ki_provider: string | null`
- `ki_model: string | null`
- `metadata: object`

DocumentChunkSummary fields (immer vorhanden):
- `chunk_count: number`
- `total_chars: number`
- `first_chunk_id: string | null`
- `last_chunk_id: string | null`

Optional fields: nullable fields oben
Enum values:
- `ImportStatus`: `pending`, `parsing`, `parsed`, `chunked`, `failed`, `duplicate`
- `LifecycleStatus`: `active`, `archived`, `deleted`

Error codes: `AUTH_REQUIRED`, `WORKSPACE_ACCESS_FORBIDDEN`, `DOCUMENT_NOT_FOUND`, `DOCUMENT_STATE_CONFLICT`, `INTERNAL_ERROR`
Deprecated fields: keine

## 5. UploadJobResponse

Version: `v1`
Endpoints: `POST /documents/import`, `GET /api/v1/jobs/{job_id}`

Required fields:
- `id: string`
- `job_type: JobType`
- `status: JobStatus`
- `workspace_id: string`
- `requested_by_user_id: string | null`
- `filename: string | null`
- `created_at: string`
- `started_at: string | null`
- `finished_at: string | null`
- `progress_current: number`
- `progress_total: number`
- `progress_message: string | null`
- `error_code: string | null`
- `error_message: string | null`
- `previous_error: JobPreviousError | null`
- `replay_history: JobReplayAuditEntry[]`
- `result: ImportJobResult | SearchIndexRebuildJobResult | null`

JobPreviousError / JobReplayAuditEntry fields (selbe Shape):
- `previous_error_code: string | null`
- `previous_error_message: string | null`
- `replayed_at: string` (ISO-8601)
- `replayed_by_user_id: string | null`

ImportJobResult fields (wenn `result != null` und `job_type == "document_import"`):
- `document_id: string`
- `version_id: string | null`
- `import_status: string` (ImportStatus-Wert)
- `duplicate_of_document_id: string | null`
- `chunk_count: number`
- `parser_type: string`
- `warnings: object[]`

SearchIndexRebuildJobResult fields (wenn `result != null` und `job_type == "search_index_rebuild"`):
- `workspace_id: string | null`
- `reindexed_chunk_count: number`
- `reindexed_document_count: number`
- `index_name: string`
- `index_action: string`
- `status: string`

Optional fields: nullable fields oben
Enum values:
- `JobType`: `document_import`, `search_index_rebuild`
- `JobStatus`: `pending`, `running`, `completed`, `failed`, `retryable`, `dead_letter`, `cancelled`
- `result.import_status`: dieselben Werte wie `ImportStatus`

Error codes: `AUTH_REQUIRED`, `WORKSPACE_ACCESS_FORBIDDEN`, `JOB_NOT_FOUND`, `FILE_TOO_LARGE`, `UNSUPPORTED_FILE_TYPE`, `OCR_REQUIRED`, `PARSER_FAILED`, `IMPORT_FAILED`, `SERVICE_UNAVAILABLE`
Deprecated fields: keine

## 6. SearchResponse

Version: `v1`
Endpoint: `GET /api/v1/search/chunks`
Shape: `SearchChunkResult[]`

Required fields per result:
- `document_id: string`
- `document_title: string`
- `document_created_at: string`
- `document_version_id: string`
- `version_number: number`
- `chunk_id: string`
- `position: number`
- `text_preview: string`
- `source_anchor: SourceAnchor`
- `rank: number` (float)
- `filters: object`

SourceAnchor required fields:
- `type: SourceAnchorType`
- `page: number | null`
- `paragraph: number | null`
- `char_start: number | null`
- `char_end: number | null`

Optional fields: nullable SourceAnchor-Positionen
Enum values:
- `SourceAnchorType`: `text`, `pdf_page`, `docx_paragraph`, `legacy_unknown`

Error codes: `AUTH_REQUIRED`, `WORKSPACE_ACCESS_FORBIDDEN`, `INVALID_QUERY`, `INVALID_PAGINATION`, `SERVICE_UNAVAILABLE`
Deprecated fields: keine

## 7. ChatSessionResponse

Version: `v1`
Endpoints: `GET /api/v1/chat/sessions`, `POST /api/v1/chat/sessions`, `GET /api/v1/chat/sessions/{session_id}`

Required fields:
- `id: string`
- `workspace_id: string`
- `title: string`
- `created_at: string`
- `updated_at: string`
- `message_count: number`
- `last_user_question_preview: string | null`

Detail-only required field (nur bei `GET /{session_id}`):
- `messages: ChatMessageResponse[]`

Optional fields: `messages` fehlt in List-/Create-Responses
Enum values: keine eigenen
Error codes: `AUTH_REQUIRED`, `WORKSPACE_ACCESS_FORBIDDEN`, `CHAT_SESSION_NOT_FOUND`, `CHAT_PERSISTENCE_FAILED`, `CHAT_MESSAGE_INVALID`
Deprecated fields: keine

## 8. ChatMessageResponse

Version: `v1`
Endpoint: `POST /api/v1/chat/sessions/{session_id}/messages`; nested in `ChatSessionResponse.messages`

Required fields:
- `id: string`
- `session_id: string`
- `role: ChatRole`
- `content: string`
- `basis_type: ChatBasisType`
- `created_at: string`
- `citations: ChatCitationResponse[]`
- `confidence: ChatConfidenceResponse | null`

ChatCitationResponse required fields:
- `chunk_id: string | null`
- `document_id: string`
- `document_title: string`
- `source_anchor: SourceAnchor`
- `quote_preview: string`
- `source_status: SourceStatus`

ChatConfidenceResponse fields (wenn `confidence != null`):
- `sufficient_context: boolean`
- `retrieval_score_max: number | null`
- `retrieval_score_avg: number | null`

Optional fields: nullable fields oben
Enum values:
- `ChatRole`: `system`, `user`, `assistant`
- `ChatBasisType`: `knowledge_base`, `general`, `mixed`, `unknown`
- `SourceStatus`: `active`, `archived`, `deleted`, `missing`

Error codes: `AUTH_REQUIRED`, `WORKSPACE_ACCESS_FORBIDDEN`, `CHAT_SESSION_NOT_FOUND`, `CHAT_MESSAGE_INVALID`, `INSUFFICIENT_CONTEXT`, `RETRIEVAL_FAILED`, `LLM_UNAVAILABLE`, `CHAT_PERSISTENCE_FAILED`
Deprecated fields: keine

## 9. DiagnosticsResponse

Version: `v1`
Endpoint: `GET /api/v1/admin/diagnostics`
Hinweis: Dieser Endpoint verwendet `UNAUTHORIZED` (401), nicht `AUTH_REQUIRED` — Bearer-Token Pflicht.

Required fields:
- `system: DiagnosticsSystem`
- `database: DiagnosticsDatabase`
- `counts: DiagnosticsCounts`
- `imports: DiagnosticsImports`
- `search: DiagnosticsSearch`
- `auth: DiagnosticsAuth`
- `drift_awareness: DiagnosticsDriftAwareness`

DiagnosticsSystem required fields:
- `status: "ok" | "degraded" | "error"`
- `version: string`
- `environment: "local" | "test" | "production"`

DiagnosticsDatabase required fields:
- `reachable: boolean`
- `migration_head: string | null`
- `current_revision: string | null`
- `is_current: boolean`

DiagnosticsCounts required fields:
- `documents: number`
- `versions: number`
- `chunks: number`
- `chat_sessions: number`
- `chat_messages: number`

DiagnosticsImports required fields:
- `running_jobs: number`
- `failed_jobs_last_24h: number`
- `last_error_code: string | null`

DiagnosticsSearch required fields:
- `index_available: boolean`
- `indexed_chunks: number`
- `stale_index_entries: number`

DiagnosticsAuth required fields:
- `auth_enabled: boolean`
- `workspace_isolation_enabled: boolean`

DiagnosticsDriftAwareness required fields:
- `concept: string[]`
- `warning_model: DiagnosticsWarningModel`
- `indicators: DiagnosticsIndicator[]`

DiagnosticsWarningModel required fields:
- `no_silent_degradation: boolean`
- `no_fake_green: boolean`
- `no_hidden_warnings: boolean`
- `unknown_is_not_ok: boolean`
- `highest_severity_wins: boolean`

DiagnosticsIndicator required fields:
- `key: string`
- `label: string`
- `state: "active" | "inactive" | "unknown"`
- `severity: "info" | "warning" | "critical"`
- `summary: string`
- `source: string`

Optional fields: nullable database fields
Enum values:
- `system.status`: `ok`, `degraded`, `error`
- `system.environment`: `local`, `test`, `production`
- `drift_awareness.indicators[].state`: `active`, `inactive`, `unknown`
- `drift_awareness.indicators[].severity`: `info`, `warning`, `critical`

Error codes: `UNAUTHORIZED`, `FORBIDDEN`, `DIAGNOSTICS_FAILED`, `INTERNAL_ERROR`
Deprecated fields: keine

## 10. ErrorResponse

Version: `v1`
Shape:
- `error: ApiErrorBody`

Required fields:
- `error.code: string`
- `error.message: string`
- `error.details: object`

Optional fields: keine; `details` kann leer sein
Enum values: code ist open set — muss pro Endpoint dokumentiert sein.
Deprecated fields: keine

Known GUI-relevant error codes:
- Auth/workspace: `AUTH_REQUIRED`, `UNAUTHORIZED`, `AUTH_INVALID_CREDENTIALS`, `WORKSPACE_ACCESS_FORBIDDEN`, `FORBIDDEN`, `ADMIN_REQUIRED`
- Documents/import: `DOCUMENT_NOT_FOUND`, `DOCUMENT_STATE_CONFLICT`, `INVALID_LIFECYCLE_STATUS`, `INVALID_LIFECYCLE_TRANSITION`, `DOCUMENT_ALREADY_ARCHIVED`, `DOCUMENT_ALREADY_DELETED`, `DUPLICATE_DOCUMENT`, `UNSUPPORTED_FILE_TYPE`, `FILE_TOO_LARGE`, `OCR_REQUIRED`, `PARSER_FAILED`, `IMPORT_FAILED`
- Search/chat: `INVALID_QUERY`, `INVALID_PAGINATION`, `CHAT_SESSION_NOT_FOUND`, `CHAT_MESSAGE_INVALID`, `CHAT_PERSISTENCE_FAILED`, `RETRIEVAL_FAILED`, `INSUFFICIENT_CONTEXT`, `LLM_UNAVAILABLE`
- Jobs/admin: `JOB_NOT_FOUND`, `RESOURCE_LOCKED`, `JOB_NOT_REPLAYABLE`, `REPLAY_FAILED`, `SERVICE_UNAVAILABLE`, `ADMIN_ACTION_NOT_IMPLEMENTED`, `DIAGNOSTICS_FAILED`, `BACKUP_VALIDATION_FAILED`, `REINDEX_CONSTRAINT_VIOLATION`
- Generic: `INTERNAL_ERROR`
