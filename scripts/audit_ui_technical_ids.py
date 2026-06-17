#!/usr/bin/env python3
"""
audit_ui_technical_ids.py
Ruflo - UI Technical ID Leak Audit

Prueft Frontend-Komponenten auf sichtbare Ausgabe technischer IDs.
Exit 0 = PASS (0 Leaks), Exit 1 = BLOCKED (Leaks gefunden)
"""

import re
import os
import sys
import json
import argparse
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_SRC = os.path.join(REPO_ROOT, 'frontend', 'src')
REPORT_PATH = os.path.join(REPO_ROOT, 'reports', 'current', 'ui_technical_id_leak_audit.json')

EXCLUDE_PATH_FRAGMENTS = [
    '/api/', '/tests/', '/__tests__/', '/lib/',
    '.test.', '.spec.', 'setup.js', 'setup.ts',
]

ADMIN_SCOPE_EXCEPTIONS = {
    'AdminDiagnosticsPage.jsx': 'Explizit ausgeschlossen aus 1.0-Scope',
}

LEAK_PATTERNS = [
    (r'\{[^}]*\bdocument\.id\b[^}]*\}',               'document.id als JSX-Ausdruck',          'P1'),
    (r'\{[^}]*\bdocument\.workspaceId\b[^}]*\}',      'document.workspaceId als JSX-Ausdruck', 'P1'),
    (r'\{[^}]*\bdocument\.ownerUserId\b[^}]*\}',      'document.ownerUserId als JSX-Ausdruck', 'P1'),
    (r'\{[^}]*\buser\.id\b[^}]*\}',                   'user.id als JSX-Ausdruck',              'P1'),
    (r'\{[^}]*\bworkspace\.id\b[^}]*\}',              'workspace.id als JSX-Ausdruck',         'P1'),
    (r'\{[^}]*\bjob\??\.id\b[^}]*\}',                 'job.id als JSX-Ausdruck',               'P1'),
    (r'\{[^}]*\brun\.id\b[^}]*\}',                    'run.id als JSX-Ausdruck',               'P1'),
    (r'\{[^}]*\blatest_run_id\b[^}]*\}',              'latest_run_id als JSX-Ausdruck',        'P1'),
    (r'\{[^}]*\brun_id\b(?!\s*\}?\s*/\*)[^}]*\}',    'run_id als JSX-Ausdruck',               'P1'),
    (r'>\s*\{[^}]*workspaceId[^}]*\}\s*<',            'workspaceId als sichtbarer Tag-Inhalt', 'P1'),
    (r'<strong>\{[^}]*workspaceId[^}]*\}</strong>',   'workspaceId in <strong>',               'P1'),
    (r'\{[^}]*ownerUserId[^}]*\}(?!\s*[=,])',         'ownerUserId als JSX-Ausdruck',          'P1'),
    (r'<dt>\s*(ID|Workspace|Owner|WorkspaceId|OwnerId)\s*</dt>', 'technisches dt-Label',       'P1'),
    (r'>\s*\{[^}]*\bitem\.id\b[^}]*\}\s*<',          'item.id als sichtbarer Tag-Inhalt',     'P2'),
    (r'\{[^}]*\buuid\b[^}]*\}(?!\s*[=,])',            'uuid-Feld als JSX-Ausdruck',            'P1'),
]

ALLOWED_PATTERNS = [
    r'^\s*(const|let|var|function|import|export)\b',
    r'^\s*//',
    r'^\s*\*',
    r'key=\{',
    r'value=\{',
    r'to=\{',
    r'href=\{',
    r'data-testid=',
    r'data-\w+=\{',
    r'correlationId',
    r'selectedId\b',
    r'on[A-Z]\w*=\{',
    r'on[A-Z]\w*\(',
    r'\bif\s*\(',
    r'fetch\w*\(',
    r'useRef\(',
    r'requestContextRef',
    r'\.current\s*=',
    r'aria-label=',
    r'dispatch\(',
    r'navigate\(',
    r'console\.',
]


def should_exclude(filepath):
    basename = os.path.basename(filepath)
    if basename in ADMIN_SCOPE_EXCEPTIONS:
        return True, 'Admin-Ausnahme: ' + ADMIN_SCOPE_EXCEPTIONS[basename]
    for fragment in EXCLUDE_PATH_FRAGMENTS:
        if fragment in filepath.replace('\\', '/'):
            return True, 'Ausschluss-Pfad: ' + fragment
    return False, None


def is_allowed(line):
    return any(re.search(p, line) for p in ALLOWED_PATTERNS)


def scan_file(filepath, src_root):
    leaks = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as fh:
            lines = fh.readlines()
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
                break
    return leaks


def collect_files(src_root):
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


def run_audit(src_root):
    files = collect_files(src_root)
    all_leaks = []
    scanned = []
    exceptions = []

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
    parser.add_argument('--root', default=DEFAULT_SRC)
    parser.add_argument('--report', default=REPORT_PATH)
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    if not os.path.isdir(args.root):
        print('FEHLER: Verzeichnis nicht gefunden: ' + args.root, file=sys.stderr)
        sys.exit(2)

    result = run_audit(args.root)

    report = {
        'report_schema_version': 2,
        'report_name': 'ui_technical_id_leak_audit',
        'report_type': 'automated_security_ux_audit',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'audit_root': args.root,
        'rule': (
            'Technische IDs duerfen nicht als sichtbarer Text in der Endanwender-GUI erscheinen. '
            'Erlaubt: React-Keys, URL-Parameter, value=-Attribute, API-Layer, Tests, '
            'Admin-Ausnahmen, Event-Handler, bedingte Logik.'
        ),
        'scanned_files': result['scanned_files'],
        'visible_leaks': result['visible_leaks'],
        'leaks': result['leaks'],
        'exceptions_accepted': result['exceptions'],
        'verdict': result['verdict'],
    }

    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, 'w', encoding='utf-8') as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    if not args.quiet:
        print('Dateien geprueft:  ' + str(result['scanned_files']))
        print('Sichtbare Leaks:   ' + str(result['visible_leaks']))
        for leak in result['leaks']:
            print('  LEAK  ' + leak['severity'] + '  ' + leak['file'] + ':' + str(leak['line']) + '  [' + leak['pattern'] + ']')
            print('         ' + leak['content'])
        print('Verdict:           ' + result['verdict'])
        print('Report:            ' + args.report)

    sys.exit(0 if result['verdict'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
