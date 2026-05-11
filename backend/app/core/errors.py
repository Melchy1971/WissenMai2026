from typing import Any


class ApiError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"
    message = "Internal server error"

    def __init__(self, message: str | None = None, details: dict[str, Any] | None = None) -> None:
        self.message = message or self.message
        self.details = details or {}
        super().__init__(self.message)


class DocumentNotFoundApiError(ApiError):
    status_code = 404
    code = "DOCUMENT_NOT_FOUND"
    message = "Document not found"


class WorkspaceRequiredApiError(ApiError):
    status_code = 403
    code = "WORKSPACE_ACCESS_FORBIDDEN"
    message = "Workspace access forbidden"


class AuthRequiredApiError(ApiError):
    status_code = 401
    code = "AUTH_REQUIRED"
    message = "Authentication required"


class UnauthorizedApiError(ApiError):
    status_code = 401
    code = "UNAUTHORIZED"
    message = "Unauthorized"


class AuthInvalidCredentialsApiError(ApiError):
    status_code = 401
    code = "AUTH_INVALID_CREDENTIALS"
    message = "Invalid credentials"


class WorkspaceAccessForbiddenApiError(ApiError):
    status_code = 403
    code = "WORKSPACE_ACCESS_FORBIDDEN"
    message = "Workspace access forbidden"


class AdminRequiredApiError(ApiError):
    status_code = 403
    code = "ADMIN_REQUIRED"
    message = "Admin access required"


class ForbiddenApiError(ApiError):
    status_code = 403
    code = "FORBIDDEN"
    message = "Forbidden"


class InvalidPaginationApiError(ApiError):
    status_code = 422
    code = "INVALID_PAGINATION"
    message = "Invalid pagination parameters"


class InvalidQueryApiError(ApiError):
    status_code = 422
    code = "INVALID_QUERY"
    message = "Invalid search query"


class ChatSessionNotFoundApiError(ApiError):
    status_code = 404
    code = "CHAT_SESSION_NOT_FOUND"
    message = "Chat session not found"


class ChatMessageInvalidApiError(ApiError):
    status_code = 422
    code = "CHAT_MESSAGE_INVALID"
    message = "Chat message is invalid"


class ChatPersistenceFailedApiError(ApiError):
    status_code = 500
    code = "CHAT_PERSISTENCE_FAILED"
    message = "Chat persistence failed"


class RetrievalFailedApiError(ApiError):
    status_code = 502
    code = "RETRIEVAL_FAILED"
    message = "Retrieval failed"


class InsufficientContextApiError(ApiError):
    status_code = 422
    code = "INSUFFICIENT_CONTEXT"
    message = "Insufficient context"


class LlmUnavailableApiError(ApiError):
    status_code = 503
    code = "LLM_UNAVAILABLE"
    message = "LLM service unavailable"


class DocumentStateConflictApiError(ApiError):
    status_code = 409
    code = "DOCUMENT_STATE_CONFLICT"
    message = "Document state is inconsistent"


class InvalidLifecycleTransitionApiError(ApiError):
    status_code = 409
    code = "INVALID_LIFECYCLE_TRANSITION"
    message = "Invalid lifecycle transition"


class DocumentAlreadyArchivedApiError(ApiError):
    status_code = 409
    code = "DOCUMENT_ALREADY_ARCHIVED"
    message = "Document is already archived"


class DocumentAlreadyDeletedApiError(ApiError):
    status_code = 409
    code = "DOCUMENT_ALREADY_DELETED"
    message = "Document is already deleted"


class InvalidLifecycleStatusApiError(ApiError):
    status_code = 422
    code = "INVALID_LIFECYCLE_STATUS"
    message = "Invalid lifecycle status"


class DuplicateDocumentApiError(ApiError):
    status_code = 409
    code = "DUPLICATE_DOCUMENT"
    message = "Document already exists"


class UnsupportedFileTypeApiError(ApiError):
    status_code = 415
    code = "UNSUPPORTED_FILE_TYPE"
    message = "Unsupported file type"


class FileTooLargeApiError(ApiError):
    status_code = 413
    code = "FILE_TOO_LARGE"
    message = "Uploaded file exceeds the configured maximum size"


class OcrRequiredApiError(ApiError):
    status_code = 422
    code = "OCR_REQUIRED"
    message = "OCR is required but no OCR engine is configured"


class ParserFailedApiError(ApiError):
    status_code = 422
    code = "PARSER_FAILED"
    message = "Document parser failed"


class ImportFailedApiError(ApiError):
    status_code = 500
    code = "IMPORT_FAILED"
    message = "Document import failed"


class ServiceUnavailableApiError(ApiError):
    status_code = 503
    code = "SERVICE_UNAVAILABLE"
    message = "Service unavailable"


class AdminActionNotImplementedApiError(ApiError):
    status_code = 501
    code = "ADMIN_ACTION_NOT_IMPLEMENTED"
    message = "Admin action is not implemented"


class DiagnosticsFailedApiError(ApiError):
    status_code = 500
    code = "DIAGNOSTICS_FAILED"
    message = "Diagnostics failed"


class BackgroundJobNotFoundApiError(ApiError):
    status_code = 404
    code = "JOB_NOT_FOUND"
    message = "Background job not found"


class ResourceLockedApiError(ApiError):
    status_code = 409
    code = "RESOURCE_LOCKED"
    message = "Resource is currently locked by another operation"


class JobNotReplayableApiError(ApiError):
    status_code = 409
    code = "JOB_NOT_REPLAYABLE"
    message = "Job is not in a replayable state"


class ReplayFailedApiError(ApiError):
    status_code = 500
    code = "REPLAY_FAILED"
    message = "Job replay failed"
