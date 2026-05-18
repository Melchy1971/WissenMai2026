import { describe, expect, it } from 'vitest';

import { ERROR_STATE_CATALOG, getErrorState, mapDuplicateImportState, mapErrorToCatalog } from '../../view-models/errorCatalog.js';

const REQUIRED_CODES = [
  'API_UNREACHABLE',
  'AUTH_REQUIRED',
  'FORBIDDEN',
  'WORKSPACE_NOT_CONFIGURED',
  'TIMEOUT',
  'VALIDATION_ERROR',
  'SERVER_ERROR',
  'IMPORT_FAILED',
  'OCR_REQUIRED',
  'DUPLICATE_DOCUMENT',
];

describe('Error-State-Catalog', () => {
  it('defines all required GUI error states with action, retry flag and logging', () => {
    for (const code of REQUIRED_CODES) {
      const state = ERROR_STATE_CATALOG[code];
      expect(state, code).toBeTruthy();
      expect(state.title).toEqual(expect.any(String));
      expect(state.message).toEqual(expect.any(String));
      expect(state.technicalCode).toEqual(expect.any(String));
      expect(state.allowedAction).toEqual(expect.any(String));
      expect(typeof state.retry).toBe('boolean');
      expect(state.logging).toEqual({
        level: expect.stringMatching(/^(info|warn|error)$/),
        event: expect.stringMatching(/^gui_/),
      });
    }
  });

  it('allows retry only for unreachable, timeout and server error states', () => {
    expect(getErrorState('API_UNREACHABLE').retry).toBe(true);
    expect(getErrorState('TIMEOUT').retry).toBe(true);
    expect(getErrorState('SERVER_ERROR').retry).toBe(true);
    expect(getErrorState('FORBIDDEN').retry).toBe(false);
    expect(getErrorState('WORKSPACE_NOT_CONFIGURED').retry).toBe(false);
    expect(getErrorState('VALIDATION_ERROR').retry).toBe(false);
  });

  it('maps backend domain codes to standard GUI states', () => {
    expect(mapErrorToCatalog({ code: 'INVALID_QUERY', message: 'bad query' })).toMatchObject({
      title: 'Validierungsfehler',
      message: 'Die Suchanfrage ist ungueltig.',
      technicalCode: 'VALIDATION_ERROR',
      retry: false,
      code: 'INVALID_QUERY',
      details: { backendMessage: 'bad query' },
    });

    expect(mapErrorToCatalog({ code: 'SERVICE_UNAVAILABLE', message: 'down' })).toMatchObject({
      title: 'Serverfehler',
      technicalCode: 'SERVER_ERROR',
      retry: true,
      code: 'SERVICE_UNAVAILABLE',
    });

    expect(mapErrorToCatalog({ code: 'PARSER_FAILED', message: 'parse failed' })).toMatchObject({
      title: 'Import fehlgeschlagen',
      technicalCode: 'IMPORT_FAILED',
      retry: false,
      code: 'PARSER_FAILED',
    });
  });

  it('keeps backend code visible while using client classification as fallback', () => {
    expect(
      mapErrorToCatalog({
        code: 'VALIDATION_ERROR',
        message: 'Invalid search query',
        details: { backendCode: 'INVALID_QUERY', classification: 'VALIDATION_ERROR' },
        status: 422,
      }),
    ).toMatchObject({
      code: 'INVALID_QUERY',
      classification: 'VALIDATION_ERROR',
      title: 'Validierungsfehler',
      message: 'Die Suchanfrage ist ungueltig.',
      technicalCode: 'VALIDATION_ERROR',
      status: 422,
    });
  });

  it('maps local GUI aliases into the standard technical classes', () => {
    expect(mapErrorToCatalog({ code: 'FILE_REQUIRED', message: 'missing file' })).toMatchObject({
      title: 'Validierungsfehler',
      technicalCode: 'VALIDATION_ERROR',
      retry: false,
      details: { backendMessage: 'missing file' },
    });

    expect(mapErrorToCatalog({ code: 'JOB_TIMEOUT', message: 'job too slow' })).toMatchObject({
      title: 'Zeitueberschreitung',
      technicalCode: 'TIMEOUT',
      retry: true,
      details: { backendMessage: 'job too slow' },
    });
  });

  it('maps duplicate import result to controlled duplicate state', () => {
    expect(mapDuplicateImportState({ fileName: 'notes.txt', documentId: 'doc-1' })).toMatchObject({
      title: 'Duplicate erkannt',
      code: 'DUPLICATE_DOCUMENT',
      technicalCode: 'DUPLICATE_DOCUMENT',
      retry: false,
      details: { documentId: 'doc-1' },
    });
  });
});
