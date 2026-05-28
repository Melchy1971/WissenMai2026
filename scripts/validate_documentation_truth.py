"""Documentation Truth Linter.

Rules enforced:
1. claim-without-reference  — lines with truth keywords (abgeschlossen, grün, freigegeben,
   PASS, GO) lack a report reference in ±3 lines  → error
2. broken-reference         — reports/X referenced in docs does not exist on disk → error
3. stale-reference          — referenced report timestamp > STALE_DAYS old → warning
4. manual-percentage        — bare N% value in paragraph without a report ref → warning
5. masterplan-contradiction — phase claim contradicts masterplan_status.json  → error
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_DIR = REPO_ROOT / "reports" / "current"
MASTERPLAN_STATUS_PATH = CURRENT_DIR / "masterplan_status.json"
DEFAULT_OUTPUT = CURRENT_DIR / "documentation_truth_lint.json"
STALE_DAYS = 30

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

REPORT_REF_RE = re.compile(r'reports/[\w./:-]+\.(?:json|md)')
PERCENTAGE_RE = re.compile(r'(?<![\d.])\d{1,3}(?:\.\d+)?%(?![\d.])')
CODE_FENCE_RE = re.compile(r'^\s*```')

CLAIM_KW_RE = re.compile(
    r'\b(abgeschlossen|freigegeben|bestanden|grün[ae]?|green|PASS)\b',
    re.IGNORECASE,
)
# Only match GO when it is explicitly a release decision marker
GO_DECISION_RE = re.compile(
    r'GO-Entscheidung|Entscheidung[:\s]+GO\b|\bGO\b\s*\(',
    re.IGNORECASE,
)

# Negation: word in the 50 chars before a keyword negates the claim
NEGATION_RE = re.compile(
    r'\b(nicht|kein[e]?(?:[rnms](?:t)?)?|noch\s+nicht|nur\s+teilweise|not|no\s+longer|never|nein)\b',
    re.IGNORECASE,
)

# Phase-level claim detection is split into phase and status matches so
# negation is evaluated at the status keyword, not at the phase keyword.
STATUS_CLAIM_RE = re.compile(
    r'\b(abgeschlossen|freigegeben|PASS|grün[ae]?|green|bestanden)\b'
    r'|GO-Entscheidung'
    r'|Entscheidung[:\s]+GO\b'
    r'|(?<!NO_)\bGO\b',
    re.IGNORECASE,
)
PHASE_RE: dict[str, re.Pattern[str]] = {
    'm3a': re.compile(r'\bM3a\b', re.IGNORECASE),
    'm4': re.compile(r'\bM4\b(?![a-z])', re.IGNORECASE),
    'm5': re.compile(r'\bM5\b(?![a-z])', re.IGNORECASE),
}

# Only these files are checked for masterplan contradictions (current-state docs)
CONTRADICTION_FILES = frozenset({
    'masterplan.md',
    'README.md',
    'docs/status.md',
    'docs/m4-m5-freigabefassung.md',
    'docs/pre-m5-decision.md',
})

# Phases are contradicted when masterplan says decision is not GO or status is not released
_NOGO_DECISIONS = {'NO_GO', 'UNKNOWN'}
_NOGO_STATUSES = {'blocked', 'draft', 'tested'}


# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------

def collect_scan_files(repo_root: Path = REPO_ROOT) -> list[Path]:
    files: list[Path] = []
    for name in ('masterplan.md', 'README.md'):
        p = repo_root / name
        if p.exists():
            files.append(p)
    for candidate in (repo_root / 'backend' / 'README.md', repo_root / 'backend' / 'scripts' / 'README.md'):
        if candidate.exists():
            files.append(candidate)
    docs_dir = repo_root / 'docs'
    if docs_dir.exists():
        for md in sorted(docs_dir.rglob('*.md')):
            if 'prompts' not in md.parts:
                files.append(md)
    return files


# ---------------------------------------------------------------------------
# Report resolution and freshness
# ---------------------------------------------------------------------------

def resolve_report(ref: str, repo_root: Path = REPO_ROOT) -> Path | None:
    """Return existing Path for a report reference, else None."""
    exact = repo_root / ref
    if exact.exists():
        return exact
    in_current = repo_root / 'reports' / 'current' / Path(ref).name
    if in_current.exists():
        return in_current
    return None


def _report_ts(path: Path) -> datetime | None:
    if path.suffix != '.json':
        return None
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return None
    raw: str | None = data.get('timestamp') or data.get('generated_at')
    if not raw:
        return None
    try:
        # Normalise to a naive datetime (truncate sub-second and timezone)
        clean = re.sub(r'(\.\d+)?([+Z].*)?$', '', raw[:26])
        return datetime.fromisoformat(clean)
    except (ValueError, TypeError):
        return None


def is_stale(path: Path, days: int = STALE_DAYS) -> bool:
    ts = _report_ts(path)
    if ts is None:
        return False
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)
    return ts < cutoff


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _in_code_block(lines: list[str], idx: int) -> bool:
    depth = sum(1 for i in range(idx + 1) if CODE_FENCE_RE.match(lines[i]))
    return depth % 2 == 1


_POST_NEGATION_RE = re.compile(
    r':\s*`?(?:nein|no|false|falsch)`?',
    re.IGNORECASE,
)

_DEFINITIONAL_RE = re.compile(
    r'\b(zaehlt\s+(?:nicht\s+)?als|gilt\s+(?:ab\s+sofort|als)|bedeutet\s*:|'
    r'ist\s+definiert\s+als|erst\s+dieser\s+Status\s+zaehlt)\b',
    re.IGNORECASE,
)


def _claim_is_negated(line: str, match_start: int, match_end: int) -> bool:
    """True if a negation word appears in the 70 chars before or directly after the keyword."""
    prefix = line[max(0, match_start - 70): match_start]
    if NEGATION_RE.search(prefix):
        return True
    suffix = line[match_end: match_end + 40]
    return bool(_POST_NEGATION_RE.match(suffix))


def _claim_is_definitional(line: str, match_start: int) -> bool:
    """True if the keyword appears in a definitional sentence (defining the term, not claiming it)."""
    context = line[max(0, match_start - 60): match_start + 60]
    return bool(_DEFINITIONAL_RE.search(context))


_CONDITIONAL_RE = re.compile(
    r'\b(wenn|if|solange|sobald|darf\s+nur|kann\s+nur|nur\s+dann|'
    r'only\s+if|only\s+when|must\s+be|soll\s+nur|muss\s+nur|sobald|'
    r'setzt\s+voraus|vorausgesetzt)\b',
    re.IGNORECASE,
)

_NON_STATUS_PERCENTAGE_RE = re.compile(
    r'\b(jitter|wahrscheinlichkeit|risk|risiko|technical[-\s]?debt|schuld|'
    r'failure\s+rate|parser_failure_rate|ocr_required|duplicate-spike|'
    r'schwelle|threshold|zielwert|laufzeit|performance|'
    r'm4a_gate|m4b_gate|m4c_gate|m4d_gate)\b|[<>]=?\s*\d',
    re.IGNORECASE,
)


def _claim_is_conditional(line: str, match_start: int) -> bool:
    """True if the keyword is inside a conditional clause."""
    prefix = line[max(0, match_start - 70): match_start]
    return bool(_CONDITIONAL_RE.search(prefix))


def _percentage_is_non_status_context(rel: str, line: str, para_text: str) -> bool:
    """True for technical thresholds and risk estimates that are not status progress."""
    if rel in {'masterplan.md', 'docs/generated/status_section.md'} and 'Fortschritt:' in line:
        return True
    if _NON_STATUS_PERCENTAGE_RE.search(line) or _NON_STATUS_PERCENTAGE_RE.search(para_text):
        return True
    if any(part in rel for part in (
        'm4-gap-risk-analysis.md',
        'paket-5-observability.md',
        'paket-5-performance-baseline.md',
        'paket-5-technical-debt-register.md',
        'm4-stabilization-exit-criteria.md',
        'frontend-api-unreachable-recovery.md',
    )):
        return True
    return False


def _claim_in_backticks(line: str, match_start: int) -> bool:
    """True if the keyword appears inside backtick-quoted inline code."""
    before = line[:match_start]
    return before.count('`') % 2 == 1


def _claim_is_compound_prefix(line: str, match_end: int) -> bool:
    """True if the keyword is used as a hyphenated compound-word prefix (e.g., PASS-Entscheidung)."""
    return match_end < len(line) and line[match_end] == '-'


def _paragraph_lines(lines: list[str], idx: int) -> list[str]:
    start = idx
    while start > 0 and lines[start - 1].strip():
        start -= 1
    end = idx
    while end < len(lines) - 1 and lines[end + 1].strip():
        end += 1
    return lines[start:end + 1]


def _window(lines: list[str], idx: int, radius: int = 3) -> str:
    return '\n'.join(lines[max(0, idx - radius): min(len(lines), idx + radius + 1)])


# ---------------------------------------------------------------------------
# Per-file scanning
# ---------------------------------------------------------------------------

def scan_file(
    file_path: Path,
    masterplan: dict[str, Any],
    repo_root: Path = REPO_ROOT,
) -> list[dict[str, Any]]:
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return []

    lines = content.splitlines()
    rel = file_path.relative_to(repo_root).as_posix()
    raw: list[dict[str, Any]] = []
    seen_refs: set[str] = set()

    for i, line in enumerate(lines):
        if _in_code_block(lines, i):
            continue

        # ----------------------------------------------------------------
        # Rule 2 + 3: Every report reference must resolve; warn if stale
        # ----------------------------------------------------------------
        for ref in REPORT_REF_RE.findall(line):
            if ref in seen_refs:
                continue
            seen_refs.add(ref)
            resolved = resolve_report(ref, repo_root)
            if resolved is None:
                raw.append({
                    'rule': 'broken-reference',
                    'severity': 'error',
                    'file': rel,
                    'line': i + 1,
                    'evidence': ref,
                    'message': f'Report reference not found on disk: {ref}',
                    'fix': (
                        f'Update to reports/current/{Path(ref).name} '
                        'or regenerate the report'
                    ),
                })
            elif is_stale(resolved):
                raw.append({
                    'rule': 'stale-reference',
                    'severity': 'warning',
                    'file': rel,
                    'line': i + 1,
                    'evidence': ref,
                    'message': f'Report older than {STALE_DAYS} days: {ref}',
                    'fix': f'Regenerate {ref} to reflect current state',
                })

        # ----------------------------------------------------------------
        # Rule 1: Truth claim must have a report reference nearby
        # (negated claims are skipped)
        # ----------------------------------------------------------------
        kw_match = CLAIM_KW_RE.search(line) or GO_DECISION_RE.search(line)
        if kw_match and not (
            _claim_is_negated(line, kw_match.start(), kw_match.end())
            or _claim_is_conditional(line, kw_match.start())
            or _claim_in_backticks(line, kw_match.start())
            or _claim_is_definitional(line, kw_match.start())
            or _claim_is_compound_prefix(line, kw_match.end())
        ):
            if not REPORT_REF_RE.search(_window(lines, i)):
                raw.append({
                    'rule': 'claim-without-reference',
                    'severity': 'error',
                    'file': rel,
                    'line': i + 1,
                    'evidence': line.strip()[:140],
                    'message': 'Truth claim without report reference in ±3-line context',
                    'fix': (
                        'Add "laut reports/current/xxx.json" or qualify as historical; '
                        'or add the backing report reference nearby'
                    ),
                })

        # ----------------------------------------------------------------
        # Rule 4: Manual percentage without report reference in paragraph
        # ----------------------------------------------------------------
        for m in PERCENTAGE_RE.finditer(line):
            para_text = '\n'.join(_paragraph_lines(lines, i))
            if _percentage_is_non_status_context(rel, line, para_text):
                continue
            if not REPORT_REF_RE.search(para_text):
                raw.append({
                    'rule': 'manual-percentage',
                    'severity': 'warning',
                    'file': rel,
                    'line': i + 1,
                    'evidence': line.strip()[:140],
                    'percentage': m.group(),
                    'message': f"Percentage '{m.group()}' has no report reference in its paragraph",
                    'fix': 'Cite the report from which this value is derived',
                })

    # --------------------------------------------------------------------
    # Rule 5: Masterplan contradiction — only checked in current-state files
    # --------------------------------------------------------------------
    if rel not in CONTRADICTION_FILES:
        return raw
    phases = masterplan.get('phases', {})
    for phase_id, pattern in PHASE_RE.items():
        phase = phases.get(phase_id, {})
        decision = phase.get('decision', 'UNKNOWN')
        status = phase.get('status', 'unknown')
        if decision not in _NOGO_DECISIONS and status not in _NOGO_STATUSES:
            continue
        for i, line in enumerate(lines):
            if _in_code_block(lines, i):
                continue
            phase_match = pattern.search(line)
            if not phase_match:
                continue
            status_match = next(STATUS_CLAIM_RE.finditer(line, phase_match.end()), None)
            if status_match and not (
                _claim_is_negated(line, status_match.start(), status_match.end())
                or _claim_is_conditional(line, status_match.start())
                or _claim_in_backticks(line, status_match.start())
                or _claim_is_definitional(line, status_match.start())
                or _claim_is_compound_prefix(line, status_match.end())
            ):
                raw.append({
                    'rule': 'masterplan-contradiction',
                    'severity': 'error',
                    'file': rel,
                    'line': i + 1,
                    'evidence': line.strip()[:140],
                    'phase': phase_id,
                    'masterplan_decision': decision,
                    'masterplan_status': status,
                    'message': (
                        f'{phase_id.upper()} claim contradicts masterplan_status.json '
                        f'(decision={decision}, status={status})'
                    ),
                    'fix': (
                        f'Revise claim: {phase_id}.decision={decision}, '
                        f'{phase_id}.status={status}'
                    ),
                })

    return raw


# ---------------------------------------------------------------------------
# Evaluation and output
# ---------------------------------------------------------------------------

def evaluate(
    repo_root: Path = REPO_ROOT,
    masterplan_path: Path = MASTERPLAN_STATUS_PATH,
    *,
    timestamp: str | None = None,
) -> dict[str, Any]:
    timestamp = timestamp or datetime.now(UTC).isoformat()
    masterplan = {}
    if masterplan_path.exists():
        try:
            masterplan = json.loads(masterplan_path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            pass

    all_findings: list[dict[str, Any]] = []
    for file_path in collect_scan_files(repo_root):
        all_findings.extend(scan_file(file_path, masterplan, repo_root))

    # Assign sequential IDs
    for idx, f in enumerate(all_findings, 1):
        f['id'] = f'DTL-{idx:03d}'

    errors = [f for f in all_findings if f['severity'] == 'error']
    warnings = [f for f in all_findings if f['severity'] == 'warning']

    # Build fix list: one entry per unique (file, rule, evidence)
    seen_fixes: set[tuple[str, str, str]] = set()
    fixes: list[dict[str, Any]] = []
    for f in all_findings:
        key = (f['file'], f['rule'], f.get('evidence', ''))
        if key in seen_fixes:
            continue
        seen_fixes.add(key)
        fixes.append({
            'id': f['id'],
            'severity': f['severity'],
            'file': f['file'],
            'line': f['line'],
            'rule': f['rule'],
            'action': f['fix'],
        })

    overall = 'FAIL' if errors else ('WARN' if warnings else 'PASS')
    return {
        'report_schema_version': 1,
        'report_name': 'documentation_truth_lint',
        'generated_by': 'documentation_truth_linter',
        'timestamp': timestamp,
        'result': overall,
        'status': overall,
        'summary': {
            'files_scanned': len(collect_scan_files(repo_root)),
            'total_findings': len(all_findings),
            'errors': len(errors),
            'warnings': len(warnings),
            'by_rule': _count_by_rule(all_findings),
        },
        'masterplan_source': str(masterplan_path),
        'findings': all_findings,
        'fixes': fixes,
        'exit_code': 0 if overall == 'PASS' else 1,
    }


def _count_by_rule(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f['rule']] = counts.get(f['rule'], 0) + 1
    return counts


def write_output(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Documentation Truth Linter')
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--masterplan', type=Path, default=MASTERPLAN_STATUS_PATH)
    args = parser.parse_args(argv)

    payload = evaluate(REPO_ROOT, args.masterplan)
    write_output(payload, args.output)

    result = payload['result']
    s = payload['summary']
    print(f'Documentation Truth Lint = {result}')
    print(f'  Files scanned : {s["files_scanned"]}')
    print(f'  Errors        : {s["errors"]}')
    print(f'  Warnings      : {s["warnings"]}')
    for rule, count in sorted(s['by_rule'].items()):
        print(f'    [{rule}] {count}')
    print(f'Wrote: {args.output}')
    return 0 if result != 'FAIL' else 1


if __name__ == '__main__':
    raise SystemExit(main())
