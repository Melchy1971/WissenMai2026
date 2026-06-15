/**
 * Static check: no source file outside api/client.js may call fetch() directly.
 *
 * Rule: All HTTP requests must route through requestJson() in api/client.js.
 * Components and API modules must never call fetch() themselves.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const SRC_DIR = resolve(__dirname, '../..');
// client.js is the only file allowed to call fetch()
const ALLOWED_FILES = new Set([resolve(SRC_DIR, 'api/client.js')]);
// Test files and the ACL-defective legacy drift directory are excluded.
const EXCLUDED_DIRS = new Set(['tests']);
const EXCLUDED_PATHS = new Set([resolve(SRC_DIR, 'features/drift')]);

function collectSourceFiles(dir) {
  const files = [];
  if (EXCLUDED_PATHS.has(resolve(dir))) {
    return files;
  }
  let entries = [];
  try {
    entries = readdirSync(dir, { withFileTypes: true });
  } catch (error) {
    if (error?.code === 'EACCES' || error?.code === 'EPERM') {
      return files;
    }
    throw error;
  }
  for (const entry of entries) {
    const fullPath = join(dir, entry.name);
    if (entry.isDirectory()) {
      if (!EXCLUDED_DIRS.has(entry.name)) {
        files.push(...collectSourceFiles(fullPath));
      }
    } else if (entry.isFile() && /\.(js|jsx)$/.test(entry.name)) {
      files.push(fullPath);
    }
  }
  return files;
}

const FETCH_CALL_PATTERN = /(?<![.\w])fetch\s*\(/;
const HEADER_BUILD_PATTERNS = [
  /\bheaders\s*:/,
  /\bnew\s+Headers\s*\(/,
  /\bAuthorization\b/,
  /\bX-Workspace-Id\b/,
];

describe('static check — no direct fetch() outside client.js', () => {
  it('no source file calls fetch() directly', () => {
    const sourceFiles = collectSourceFiles(SRC_DIR);
    const violations = sourceFiles
      .filter((f) => !ALLOWED_FILES.has(f))
      .filter((f) => FETCH_CALL_PATTERN.test(readFileSync(f, 'utf-8')));

    expect(violations.map((f) => relative(SRC_DIR, f))).toEqual([]);
  });

  it('api/client.js is present and exports requestJson', () => {
    const clientPath = resolve(SRC_DIR, 'api/client.js');
    const content = readFileSync(clientPath, 'utf-8');
    expect(content).toMatch(/export\s+async\s+function\s+requestJson/);
  });

  it('api/client.js is the only file that calls fetch()', () => {
    const sourceFiles = collectSourceFiles(SRC_DIR);
    const fetchCallers = sourceFiles.filter((f) =>
      FETCH_CALL_PATTERN.test(readFileSync(f, 'utf-8')),
    );
    const expected = [resolve(SRC_DIR, 'api/client.js')];
    expect(fetchCallers).toEqual(expected);
  });

  it('api/client.js is the only source file that builds HTTP headers', () => {
    const sourceFiles = collectSourceFiles(SRC_DIR);
    const violations = sourceFiles
      .filter((f) => !ALLOWED_FILES.has(f))
      .filter((f) => {
        const content = readFileSync(f, 'utf-8');
        return HEADER_BUILD_PATTERNS.some((pattern) => pattern.test(content));
      });

    expect(violations.map((f) => relative(SRC_DIR, f))).toEqual([]);
  });
});
