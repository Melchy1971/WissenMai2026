import { mapDuplicateImportState, mapErrorToCatalog } from './errorCatalog.js';

export function mapImportStatus(status) {
  const lookup = {
    pending: { kind: 'pending', label: 'Ausstehend', tone: 'warning' },
    parsing: { kind: 'parsing', label: 'Wird verarbeitet', tone: 'info' },
    parsed: { kind: 'parsed', label: 'Geparst', tone: 'info' },
    chunked: { kind: 'chunked', label: 'Lesbar', tone: 'success' },
    failed: { kind: 'failed', label: 'Fehlgeschlagen', tone: 'danger' },
    duplicate: { kind: 'duplicate', label: 'Bereits vorhanden', tone: 'neutral' },
  };

  return lookup[status] || { kind: 'unknown', label: 'Unbekannt', tone: 'neutral' };
}

export function mapLifecycleStatus(status) {
  const lookup = {
    active: { kind: 'active', label: 'active', tone: 'success' },
    archived: { kind: 'archived', label: 'archived', tone: 'warning' },
    deleted: { kind: 'deleted', label: 'deleted', tone: 'danger' },
  };

  return lookup[status] || lookup.active;
}

export function mapJobStatus(job) {
  const status = job?.status || 'unknown';
  const jobType = job?.job_type || 'background_job';

  const lookup = {
    queued: {
      kind: 'queued',
      label: 'In Warteschlange',
      tone: 'warning',
      message: jobType === 'search_index_rebuild' ? 'Rebuild wartet auf Ausfuehrung.' : 'Import wartet auf Ausfuehrung.',
    },
    running: {
      kind: 'running',
      label: 'Wird verarbeitet',
      tone: 'info',
      message: jobType === 'search_index_rebuild' ? 'Search-Index-Rebuild wird verarbeitet.' : 'Dokument wird verarbeitet.',
    },
    completed: {
      kind: 'completed',
      label: 'Abgeschlossen',
      tone: 'success',
      message: jobType === 'search_index_rebuild' ? 'Search-Index-Rebuild abgeschlossen.' : 'Import abgeschlossen.',
    },
    failed: {
      kind: 'failed',
      label: 'Fehlgeschlagen',
      tone: 'danger',
      message: jobType === 'search_index_rebuild' ? 'Search-Index-Rebuild fehlgeschlagen.' : 'Import fehlgeschlagen.',
    },
    cancelled: {
      kind: 'cancelled',
      label: 'Abgebrochen',
      tone: 'neutral',
      message: 'Job wurde abgebrochen.',
    },
  };

  const fallback = { kind: 'unknown', label: 'Unbekannt', tone: 'neutral', message: 'Jobstatus unbekannt.' };
  const mapped = lookup[status] || fallback;
  return {
    ...mapped,
    message: job?.progress_message || mapped.message,
  };
}

export function mapError(error) {
  return mapErrorToCatalog(error);
}

export function mapImportOutcome(result, { fileName = '' } = {}) {
  if (result?.import_status === 'duplicate') {
    return mapDuplicateImportState({
      fileName,
      documentId: result?.duplicate_of_document_id || result?.document_id || null,
    });
  }

  return {
    title: 'Import abgeschlossen',
    message: fileName ? `${fileName} erfolgreich verarbeitet` : 'Dokument erfolgreich verarbeitet.',
    code: 'IMPORT_COMPLETED',
    classification: 'IMPORT_COMPLETED',
    technicalCode: 'IMPORT_COMPLETED',
    allowedAction: 'Dokument pruefen',
    retry: false,
    logging: { level: 'info', event: 'gui_import_completed' },
    details: { documentId: result?.document_id || null },
    status: null,
  };
}

function formatDate(value) {
  if (!value) {
    return 'Unbekannt';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'Unbekannt';
  }

  return new Intl.DateTimeFormat('de-DE', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

export function formatSourceAnchor(anchor) {
  if (!anchor) {
    return 'Keine Quellenposition verfuegbar';
  }

  const parts = [anchor.type || 'unknown'];
  if (anchor.page != null) parts.push(`Seite ${anchor.page}`);
  if (anchor.paragraph != null) parts.push(`Absatz ${anchor.paragraph}`);
  if (anchor.char_start != null || anchor.char_end != null) {
    parts.push(`Zeichen ${anchor.char_start ?? '?'}-${anchor.char_end ?? '?'}`);
  }
  return parts.join(' | ');
}

function formatRank(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '0.00';
  }

  return value.toFixed(2);
}

export function mapDocumentListItem(item) {
  const importStatus = mapImportStatus(item.import_status);
  const lifecycleStatus = mapLifecycleStatus(item.lifecycle_status);
  return {
    id: item.id,
    title: item.title || 'Unbenanntes Dokument',
    mimeType: item.mime_type || 'unbekannt',
    createdAtLabel: formatDate(item.created_at),
    updatedAtLabel: formatDate(item.updated_at),
    latestVersionId: item.latest_version_id || null,
    importStatus,
    lifecycleStatus,
    versionCount: item.version_count ?? 0,
    chunkCount: item.chunk_count ?? 0,
  };
}

export function mapVersionItem(item, latestVersionId = null) {
  return {
    id: item.id,
    versionNumber: item.version_number ?? 0,
    createdAtLabel: formatDate(item.created_at),
    contentHash: item.content_hash || null,
    isLatest: latestVersionId != null && item.id === latestVersionId,
  };
}

export function mapChunkItem(item) {
  return {
    id: item.chunk_id,
    position: item.position ?? 0,
    positionLabel: `Chunk ${((item.position ?? 0) + 1).toString()}`,
    textPreview: item.text_preview || '',
    sourceAnchorLabel: formatSourceAnchor(item.source_anchor),
  };
}

export function mapSearchResult(item) {
  return {
    documentId: item.document_id,
    documentTitle: item.document_title || 'Unbenanntes Dokument',
    documentVersionId: item.document_version_id,
    versionNumber: item.version_number ?? 0,
    chunkId: item.chunk_id,
    position: item.position ?? 0,
    positionLabel: `Chunk ${((item.position ?? 0) + 1).toString()}`,
    textPreview: item.text_preview || 'Keine Vorschau verfuegbar',
    sourceAnchorLabel: formatSourceAnchor(item.source_anchor),
    rank: typeof item.rank === 'number' ? item.rank : 0,
    rankLabel: formatRank(item.rank),
  };
}

export function mapDocumentDetail(detail, versions, chunks) {
  const importStatus = mapImportStatus(detail.import_status);
  const lifecycleStatus = mapLifecycleStatus(detail.lifecycle_status);
  return {
    id: detail.id,
    title: detail.title || 'Unbenanntes Dokument',
    workspaceId: detail.workspace_id || 'unbekannt',
    ownerUserId: detail.owner_user_id || null,
    sourceType: detail.source_type || 'unbekannt',
    mimeType: detail.mime_type || 'unbekannt',
    contentHash: detail.content_hash || null,
    createdAtLabel: formatDate(detail.created_at),
    updatedAtLabel: formatDate(detail.updated_at),
    parserVersion: detail.parser_metadata?.parser_version || 'Unbekannt',
    ocrUsed: detail.parser_metadata?.ocr_used ?? null,
    importStatus,
    lifecycleStatus,
    archivedAtLabel: detail.archived_at ? formatDate(detail.archived_at) : null,
    deletedAtLabel: detail.deleted_at ? formatDate(detail.deleted_at) : null,
    chunkCount: detail.chunk_summary?.chunk_count ?? 0,
    totalChars: detail.chunk_summary?.total_chars ?? 0,
    latestVersionId: detail.latest_version_id || null,
    versions: Array.isArray(versions) ? versions.map((item) => mapVersionItem(item, detail.latest_version_id)) : [],
    chunks: Array.isArray(chunks) ? chunks.map(mapChunkItem) : [],
  };
}

function formatScore(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return 'Unbekannt';
  }

  return value.toFixed(2);
}

export function mapChatSessionSummary(item) {
  return {
    id: item.id,
    workspaceId: item.workspace_id,
    title: item.title || 'Neue Sitzung',
    createdAtLabel: formatDate(item.created_at),
    updatedAtLabel: formatDate(item.updated_at),
    messageCount: item.message_count ?? 0,
    lastUserQuestionPreview: item.last_user_question_preview || 'Noch keine Frage gestellt',
  };
}

export function mapChatCitation(item) {
  return {
    chunkId: item.chunk_id,
    documentId: item.document_id,
    documentTitle: item.document_title || 'Unbenanntes Dokument',
    sourceAnchorLabel: formatSourceAnchor(item.source_anchor),
    quotePreview: item.quote_preview || 'Keine Vorschau verfuegbar',
    sourceStatus: item.source_status || 'missing',
  };
}

export function mapChatConfidence(item) {
  return {
    sufficientContext: item?.sufficient_context ?? true,
    retrievalScoreMaxLabel: formatScore(item?.retrieval_score_max),
    retrievalScoreAvgLabel: formatScore(item?.retrieval_score_avg),
  };
}

export function mapChatMessage(item) {
  const role = item.role || 'assistant';
  return {
    id: item.id,
    role,
    content: role === 'assistant' ? (item.answer || item.content || '') : (item.content || ''),
    createdAtLabel: formatDate(item.created_at),
    citations: Array.isArray(item.citations) ? item.citations.map(mapChatCitation) : [],
    confidence: role === 'assistant' ? mapChatConfidence(item.confidence) : null,
  };
}

export function mapChatSessionDetail(item) {
  return {
    id: item.id,
    workspaceId: item.workspace_id,
    title: item.title || 'Neue Sitzung',
    createdAtLabel: formatDate(item.created_at),
    updatedAtLabel: formatDate(item.updated_at),
    messages: Array.isArray(item.messages) ? item.messages.map(mapChatMessage) : [],
  };
}

export function mapPostedChatResponse(item, { question } = {}) {
  return {
    sessionId: item.session_id,
    userMessage: mapChatMessage({
      id: `local-user-${item.session_id}-${item.id}`,
      session_id: item.session_id,
      role: 'user',
      content: question || '',
      created_at: new Date().toISOString(),
    }),
    assistantMessage: mapChatMessage(item),
  };
}
