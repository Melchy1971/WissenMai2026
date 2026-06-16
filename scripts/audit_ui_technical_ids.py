#!/usr/bin/env python3
"""
audit_ui_technical_ids.py
Ruflo — UI Technical ID Leak Audit

Prüft Frontend-Komponenten auf sichtbare Ausgabe technischer IDs.
Blockierende Muster: {document.id}, {workspaceId}, {ownerUserId}, {job.id},
{run.id}, {run_id}, {latest_run_id}, UUID-Werte als primärer UI-Text.

Erlaubt (kein Leak):
  - key={...id} — React-intern
  - value={...id} — Form-Attribut, nicht sichtbar
  - to={...id}, href={...id} — URL-Routing
  - data-testid=... — Testattribut
  - Variable-Deklarationen (const/let/var ...)
  - Kommentare
  - API-Layer (src/api/)
  - Tests (src/tests/, .test.)
  - Logs, Reports, Entwickler-Doku

Aufruf:
  python3 scripts/audit_ui_technical_ids.py [--root FRONTEND_SRC]

Output:
  reports/current/ui_technical_id_leak_audit.json
  Exit 0 = PASS (0 Leaks), Exit 1 = BLOCKED (Leaks gefunden)
"""

import re
import os
import sys
import json
import argparse
from datetime import datetime, timezone

# --- Konfiguration ---

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)

DEFAULT_SRC = os.path.join(REPO_ROOT, 'frontend', 'src')
REPORT_PATH = os.path.join(REPO_ROOT, 'reports', 'current', 'ui_technical_id_leak_audit.json')

# Dateien/Ordner die IMMER ausgeschlossen werden
EXCLUDE_PATH_FRAGMENTS = [
    '/api/',
    '/tests/',
    '/__tests__/',
    '/lib/',
    '.test.',
    '.spec.',
    'setup.js',
    'setup.ts',
]

# Admin/Debug-Seiten die explizit vom 1.0-Endanwender-Scope ausgeschlossen sind
ADMIN_SCOPE_EXCEPTIONS = {
    'AdminDiagnosticsPage.jsx': 'Explizit ausgeschlossen aus 1.0-Scope (docs/version_1_0_scope_freeze.md)',
}

# Blocking-Muster: sichtbare ID-Ausgabe als JSX-Text-Kind
# Jedes Muster: (regex, beschreibung, severity)
LEAK_PATTERNS = [
    # Direkte Feld-Ausgaben
    (r'\{[^}]*\bdocument\.id\b[^}]*\}',              'document.id als JSX-Ausdruck',          'P1'),
    (r'\{[^}]*\bdocument\.workspaceId\b[^}]*\}',     'document.workspaceId als JSX-Ausdruck', 'P1'),
    (r'\{[^}]*\bdocument\.ownerUserId\b[^}]*\}',     'document.ownerUserId als JSX-Ausdruck', 'P1'),
    (r'\{[^}]*\buser\.id\b[^}]*\}',                  'user.id als JSX-Ausdruck',              'P1'),
    (r'\{[^}]*\bworkspace\.id\b[^}]*\}',             'workspace.id als JSX-Ausdruck',         'P1'),
    (r'\{[^}]*\bjob\??\.id\b[^}]*\}',                'job.id als JSX-Ausdruck',               'P1'),
    (r'\{[^}]*\brun\.id\b[^}]*\}',                   'run.id als JSX-Ausdruck',               'P1'),
    (r'\{[^}]*\blatest_run_id\b[^}]*\}',             'latest_run_id als JSX-Ausdruck',        'P1'),
    (r'\{[^}]*\brun_id\b(?!\s*\}?\s*/\*)[^}]*\}',   'run_id als JSX-Ausdruck',               'P1'),
    # workspaceId als sichtbarer Text (nicht als value=/key=)
    (r'>\s*\{[^}]*workspaceId[^}]*\}\s*<',           'workspaceId als sichtbarer Tag-Inhalt', 'P1'),
    (r'<strong>\{[^}]*workspaceId[^}]*\}</strong>',  'workspaceId in <strong>',               'P1'),
    # ownerUserId
    (r'\{[^}]*ownerUserId[^}]*\}(?!\s*[=,])',        'ownerUserId als JSX-Ausdruck',          'P1'),
    # dt-Labels die technische IDs ankündigen
    (r'<dt>\s*(ID|Workspace|Owner|WorkspaceId|OwnerId)\s*</dt>', 'technisches dt-Label',      'P1'),
    # item.id als direkter Render-Text (nicht key=, value=, URL)
    (r'>\s*\{[^}]*\bitem\.id\b[^}]*\}\s*<',         'item.id als sichtbarer Tag-Inhalt',     'P2'),
    # uuid literal
    (r'\{[^}]*\buuid\b[^}]*\}(?!\s*[=,])',           'uuid-Feld als JSX-Ausdruck',            'P1'),
]

# Erlaubt-Muster: wenn Zeile auf eines dieser Muster passt, ist der Match kein Leak
ALLOWED_PATTERNS = [
    r'^\s*(const|let|var|function|import|export)\b',  # Deklarationen
    r'^\s*//',                                          # Kommentare
    r'^\s*\*',                                          # JSDoc
    r'key=\{',                                          # React-Key
    r'value=\{',                                        # Form-Attribut
    r'to=\{',                                           # Link-Attribut
    r'href=\{',                                         # href
    r'data-testid=',                                    # Test-Attribut
    r'data-\w+=\{',                                     # data-Attribute
    r'correlationId',                                   # Interne Logging-ID
    r'selectedId\b',                                    # State-Variable
    r'onSelect\(',                                      # Callback
    r'fetch\w*\(',                                      # API-Calls
    r'useRef\(',                                        # Refs
    r'requestContextRef',                               # Interne Refs
    r'\.current\s*=',                                   # Ref-Zuweisung
    r'aria-label=',                                     # Barrierefreiheit-Label (kein Sichttext)
]


def should_exclude(filepath: str) -> tuple[bool, str | None]:
    """Gibt (True, Grund) zurück wenn Datei ausgeschlossen werden soll."""
    basename = os.path.basename(filepath)
    if basename in ADMIN_SCOPE_EXCEPTIONS:
        return True, f'Admin-Ausnahme: {ADMIN_SCOPE_EXCEPTIONS[basename]}'
    for fragment in EXCLUDE_PATH_FRAGMENTS:
        if fragment in filepath.replace('\\', '/'):
            return True, f'Ausschluss-Pfad: {fragment}'
    return False, None


def is_allowed(line: str) -> bool:
    """Gibt True zurück wenn die Zeile durch ein Erlaubt-Muster gedeckt ist."""
    return any(re.search(p, line) for p in ALLOWED_PATTERNS)


def scan_file(filepath: str, src_root: str) -> list[dict]:
    """Scannt eine Datei und gibt Liste von Leak-Funden zurück."""
    leaks = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except OSError:
        return []

    for i, raw_line in enumerate(lines, 1):
        line = raw_line.rstrip()
        if is_allowed(line):
            continue
        for pattern, description, severity in LEAK_PATTERNS:
            if re.search(pattern, line):
                rel_path = os.path.relpath(filepath, src_root)
                leaks.append({
                    'file': rel_path.replace('\\', '/'),
                    'line': i,
                    'pattern': description,
                    'severity': severity,
                    'content': line.strip()[:120],
                })
                break  # Eine Meldung pro Zeile

    return leaks


def collect_files(src_root: str) -> list[str]:
    """Gibt alle zu prüfenden .jsx/.js Dateien zurück."""
    result = []
    for dirpath, _, filenames in os.walk(src_root):
        for fname in filenames:
            if not (fname.endswith('.jsx') or fname.endswith('.js')):
                continue
            full = os.path.join(dirpath, fname)
            excluded, _ = should_exclude(full)
            if not excluded:
                result.append(full)
    return sorted(result)


def run_audit(src_root: str) -> dict:
    files = collect_files(src_root)
    all_leaks = []
    scanned = []
    exceptions = []

    for fp in collect_files.__wrapped__ if hasattr(collect_files, '__wrapped__') else []:
        pass

    # Auch Ausnahmen dokumentieren
    for dirpath, _, filenames in os.walk(src_root):
        for fname in filenames:
            if not (fname.endswith('.jsx') or fname.endswith('.js')):
                continue
            full = os.path.join(dirpath, fname)
            excluded, reason = should_exclude(full)
            if excluded and reason and 'Admin' in reason:
                rel = os.path.relpath(full, src_root).replace('\\', '/')
                exceptions.append({'file': rel, 'reason': reason})

    for fp in files:
        leaks = scan_file(fp, src_root)
        all_leaks.extend(leaks)
        scanned.append(os.path.relpath(fp, src_root).replace('\\', '/'))

    return {
        'scanned_files': len(scanned),
        'leaks': all_leaks,
        'visible_leaks': len(all_leaks),
        'exceptions': exceptions,
        'verdict': 'PASS' if len(all_leaks) == 0 else 'BLOCKED',
    }


def main():
    parser = argparse.ArgumentParser(description='Ruflo UI Technical ID Leak Audit')
    parser.add_argument('--root', default=DEFAULT_SRC, help='Pfad zu frontend/src')
    parser.add_argument('--report', default=REPORT_PATH, help='Ausgabepfad für JSON-Report')
    parser.add_argument('--quiet', action='store_true', help='Kein Console-Output außer Fehler')
    args = parser.parse_args()

    if not os.path.isdir(args.root):
        print(f'FEHLER: Quellverzeichnis nicht gefunden: {args.root}', file=sys.stderr)
        sys.exit(2)

    result = run_audit(args.root)

    report = {
        'report_schema_version': 2,
        'report_name': 'ui_technical_id_leak_audit',
        'report_type': 'automated_security_ux_audit',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'audit_root': args.root,
        'rule': (
            'Technische IDs (UUIDs, interne Schlüssel) dürfen nicht als sichtbarer Text '
            'in der Endanwender-GUI erscheinen. Erlaubt: React-Keys, URL-Parameter, '
            'value=-Attribute, API-Layer, Tests, Admin-Ausnahmen.'
        ),
        'scanned_files': result['scanned_files'],
        'visible_leaks': result['visible_leaks'],
        'leaks': result['leaks'],
        'exceptions_accepted': result['exceptions'],
        'verdict': result['verdict'],
        'leaks': result['leaks'],
    }

    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    if not args.quiet:
        print(f'Dateien geprüft:  {result["scanned_files"]}')
        print(f'Sichtbare Leaks:  {result["visible_leaks"]}')
        if result['leaks']:
            for leak in result['leaks']:
                print(f'  LEAK  {leak["severity"]}  {leak["file"]}:{leak["line"]}  [{leak["pattern"]}]')
                print(f'         {leak["content"]}')
        print(f'Verdict:          {result["verdict"]}')
        print(f'Report:           {args.report}')

    sys.exit(0 if result['verdict'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
