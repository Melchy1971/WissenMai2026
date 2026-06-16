/**
 * Regression Guard: Alter Drift-Pfad darf nicht aktiv referenziert werden.
 * Invarianten (Regel 6 Local Final Gate):
 *   - features/drift (alt) ist permission-blocked (ACL).
 *   - Der aktive Pfad ist ausschliesslich features/drift_v2.
 *   - driftApi enthaelt keine mutierenden Operationen (PROHIBIT-02, PROHIBIT-06).
 */
import { readFileSync, readdirSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const SRC_DIR = resolve(__dirname, '../..');

const EXCLUDED_DIRS = new Set(['node_modules', '__snapshots__']);

// Importmuster: from '...features/drift...' -- aber NICHT features/drift_v2
const OLD_DRIFT_IMPORT_RE = /from\s+['"][^'"]*features\/drift(?!_v2)[^'"]*['"]/;

// Mutation in driftApi: POST, PUT, PATCH, DELETE
const MUTATION_HTTP_RE = /\b(POST|PUT|PATCH|DELETE)\b/;

function collectSourceFiles(dir, excludeTests) {
  if (excludeTests === undefined) excludeTests = false;
  var files = [];
  var entries = [];
  try {
    entries = readdirSync(dir, { withFileTypes: true });
  } catch (err) {
    if (err && (err.code === 'EACCES' || err.code === 'EPERM')) return files;
    throw err;
  }
  for (var i = 0; i < entries.length; i++) {
    var entry = entries[i];
    var fullPath = join(dir, entry.name);
    if (entry.isDirectory()) {
      if (!EXCLUDED_DIRS.has(entry.name)) {
        if (excludeTests && entry.name === 'tests') continue;
        var sub = collectSourceFiles(fullPath, excludeTests);
        for (var j = 0; j < sub.length; j++) files.push(sub[j]);
      }
    } else if (entry.isFile() && /\.(js|jsx|ts|tsx)$/.test(entry.name)) {
      files.push(fullPath);
    }
  }
  return files;
}

describe('Drift v2 Regression Guard - alter Pfad darf nicht aktiv sein', function() {

  it('Condition 1: Kein Quellcode importiert aus features/drift (alt)', function() {
    var sourceFiles = collectSourceFiles(SRC_DIR, true);
    var violations = sourceFiles.filter(function(f) {
      var content = readFileSync(f, 'utf-8');
      return OLD_DRIFT_IMPORT_RE.test(content);
    });
    expect(
      violations.map(function(f) { return relative(SRC_DIR, f); }),
      'Folgende Dateien importieren aus dem gesperrten features/drift-Pfad'
    ).toEqual([]);
  });

  it('Condition 2: Route /drift verweist auf DriftPage -> drift_v2/DriftDashboard', function() {
    var routesPath = resolve(SRC_DIR, 'app/routes.jsx');
    var content = readFileSync(routesPath, 'utf-8');
    expect(content).toMatch(/path="\/drift".*DriftPage|DriftPage.*path="\/drift"/);
    expect(content).not.toMatch(/from.*features\/drift(?!_v2)/);
  });

  it('Condition 3: DriftPage importiert ausschliesslich aus drift_v2', function() {
    var driftPagePath = resolve(SRC_DIR, 'pages/DriftPage.jsx');
    var content = readFileSync(driftPagePath, 'utf-8');
    expect(content).toMatch(/features\/drift_v2/);
    expect(content).not.toMatch(/features\/drift(?!_v2)/);
  });

  it('Condition 4: Test-Importe fuer Drift zeigen auf drift_v2', function() {
    // Guard-Test selbst + ClientStaticCheck ausgeschlossen (enthalten Muster zur Detektion)
    var SELF_EXCLUDE = new Set([
      resolve(SRC_DIR, 'tests/features/DriftV2RegressionGuard.test.js'),
      resolve(SRC_DIR, 'tests/api/ClientStaticCheck.test.js'),
    ]);
    var testFiles = collectSourceFiles(join(SRC_DIR, 'tests')).filter(function(f) {
      return !SELF_EXCLUDE.has(f);
    });
    var violations = testFiles.filter(function(f) {
      var content = readFileSync(f, 'utf-8');
      return OLD_DRIFT_IMPORT_RE.test(content);
    });
    expect(
      violations.map(function(f) { return relative(SRC_DIR, f); }),
      'Test-Dateien importieren aus gesperrtem features/drift'
    ).toEqual([]);
  });

  it('Condition 5: driftApi enthaelt keine mutierenden HTTP-Methoden (PROHIBIT-02/06)', function() {
    var driftApiPath = resolve(SRC_DIR, 'features/drift_v2/driftApi.js');
    var content = readFileSync(driftApiPath, 'utf-8');
    var methodLines = content.split('\n').filter(function(line) {
      return MUTATION_HTTP_RE.test(line) && !line.trim().startsWith('//');
    });
    expect(
      methodLines,
      'driftApi enthaelt mutierende HTTP-Methoden - PROHIBIT-02/06 verletzt'
    ).toEqual([]);
  });

  it('Condition 5b: driftApi exportiert nur read-only Funktionen', function() {
    var driftApiPath = resolve(SRC_DIR, 'features/drift_v2/driftApi.js');
    var content = readFileSync(driftApiPath, 'utf-8');
    var mutationExportRe = /export\s+(async\s+)?function\s+(create|update|delete|patch|repair|cleanup|restore|reindex)\w*/i;
    expect(content).not.toMatch(mutationExportRe);
  });

});
