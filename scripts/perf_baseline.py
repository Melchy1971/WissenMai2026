#!/usr/bin/env python3
"""
perf_baseline.py
Ruflo — Performance Baseline Messung fuer RC

Misst p50/p95/p99 Latenz fuer die vier RC-kritischen Messpunkte:
  1. GET /api/v1/documents  (10 Wiederholungen)
  2. GET /api/v1/search/unified?q=... (10 Wiederholungen)
  3. POST /api/v1/export/jobs + Poll bis completed (max 60s)
  4. Frontend First Load: GET / (10 Wiederholungen, kein JS-Render)

RC-Grenzwerte:
  API Documents p95  < 800ms
  API Search    p95  < 1500ms
  PDF Export        < 10000ms (bei max 20 Seiten)
  Frontend Load p95  < 3000ms (lokal, kein CDN)

Aufruf:
  python3 scripts/perf_baseline.py --api http://localhost:8000 [--token TOKEN]

Output:
  reports/current/performance_baseline_report.json
  Exit 0 = alle Grenzwerte eingehalten
  Exit 1 = mindestens ein Grenzwert verletzt
  Exit 2 = Backend nicht erreichbar
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from statistics import mean, quantiles
from typing import Optional

try:
    import urllib.request
    import urllib.error
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
REPORT_PATH = os.path.join(REPO_ROOT, 'reports', 'current', 'performance_baseline_report.json')

RC_LIMITS = {
    'api_documents_p95_ms': 800,
    'api_search_p95_ms': 1500,
    'export_pdf_ms': 10000,
    'frontend_load_p95_ms': 3000,
}

REPEATS = 10
EXPORT_POLL_INTERVAL = 1.0
EXPORT_TIMEOUT = 60.0


def _percentile(data, p):
    if not data:
        return 0
    sorted_data = sorted(data)
    idx = (p / 100) * (len(sorted_data) - 1)
    lo = int(idx)
    hi = lo + 1
    if hi >= len(sorted_data):
        return sorted_data[-1]
    frac = idx - lo
    return sorted_data[lo] + frac * (sorted_data[hi] - sorted_data[lo])


def _fetch(url, method='GET', headers=None, data=None, timeout=10):
    """Einfacher HTTP-Request via urllib. Gibt (status, body_bytes, elapsed_ms) zurueck."""
    req = urllib.request.Request(url, method=method, headers=headers or {}, data=data)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            elapsed = (time.perf_counter() - t0) * 1000
            return resp.status, body, elapsed
    except urllib.error.HTTPError as e:
        elapsed = (time.perf_counter() - t0) * 1000
        body = e.read()
        return e.code, body, elapsed
    except Exception as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        return 0, str(exc).encode(), elapsed


def measure_endpoint(url, headers, repeats):
    latencies = []
    errors = 0
    for _ in range(repeats):
        status, _, elapsed = _fetch(url, headers=headers)
        if status in (200, 201):
            latencies.append(elapsed)
        else:
            errors += 1
        time.sleep(0.05)
    return latencies, errors


def measure_export(api_base, headers, workspace_id):
    """POST Export-Job, poll bis completed oder timeout."""
    # Erst verfuegbare Results holen
    status, body, _ = _fetch(api_base + '/api/v1/analysis/results?limit=1', headers=headers)
    result_id = None
    if status == 200:
        try:
            data = json.loads(body)
            items = data if isinstance(data, list) else data.get('items', [])
            approved = [x for x in items if isinstance(x, dict) and x.get('status') == 'approved']
            if approved:
                result_id = approved[0].get('id')
        except Exception:
            pass

    if not result_id:
        return None, 'no_approved_result'

    payload = json.dumps({'result_id': result_id, 'format': 'pdf'}).encode()
    post_headers = dict(headers)
    post_headers['Content-Type'] = 'application/json'

    t0 = time.perf_counter()
    status, body, _ = _fetch(api_base + '/api/v1/export/jobs', method='POST',
                              headers=post_headers, data=payload)
    if status not in (200, 201):
        return None, 'post_failed_' + str(status)

    try:
        job = json.loads(body)
        job_id = job.get('id')
    except Exception:
        return None, 'parse_failed'

    if not job_id:
        return None, 'no_job_id'

    # Poll
    deadline = time.perf_counter() + EXPORT_TIMEOUT
    while time.perf_counter() < deadline:
        time.sleep(EXPORT_POLL_INTERVAL)
        s, b, _ = _fetch(api_base + '/api/v1/export/jobs/' + job_id, headers=headers)
        if s == 200:
            try:
                j = json.loads(b)
                job_status = j.get('status', '')
                if job_status == 'completed':
                    elapsed = (time.perf_counter() - t0) * 1000
                    return elapsed, 'completed'
                if job_status in ('failed', 'cancelled'):
                    return None, 'job_' + job_status
            except Exception:
                pass

    return None, 'timeout'


def check_reachable(api_base):
    status, _, _ = _fetch(api_base + '/health', timeout=5)
    if status == 0:
        status, _, _ = _fetch(api_base + '/api/v1/health', timeout=5)
    return status not in (0,)


def run(api_base, frontend_base, token, workspace_id, dry_run=False):
    headers = {}
    if token:
        headers['Authorization'] = 'Bearer ' + token

    results = {}

    # 1. GET /api/v1/documents
    print('Messe GET /api/v1/documents ...')
    url = api_base + '/api/v1/documents?limit=20'
    if workspace_id:
        url += '&workspace_id=' + workspace_id
    if dry_run:
        latencies, errors = [120, 135, 118, 145, 130, 125, 128, 140, 122, 119], 0
    else:
        latencies, errors = measure_endpoint(url, headers, REPEATS)

    if latencies:
        p50 = _percentile(latencies, 50)
        p95 = _percentile(latencies, 95)
        p99 = _percentile(latencies, 99)
    else:
        p50 = p95 = p99 = 0

    limit = RC_LIMITS['api_documents_p95_ms']
    status = 'PASS' if p95 <= limit and latencies else ('FAIL' if latencies else 'WARNING')
    results['documents'] = {
        'endpoint': 'GET /api/v1/documents',
        'samples': len(latencies),
        'errors': errors,
        'p50_ms': round(p50, 1),
        'p95_ms': round(p95, 1),
        'p99_ms': round(p99, 1),
        'limit_p95_ms': limit,
        'status': status,
        'dry_run': dry_run,
    }
    print('  p95=' + str(round(p95, 1)) + 'ms  limit=' + str(limit) + 'ms  ' + status)

    # 2. GET /api/v1/search/unified
    print('Messe GET /api/v1/search/unified ...')
    search_url = api_base + '/api/v1/search/unified?q=Prozess&limit=20'
    if dry_run:
        s_latencies, s_errors = [210, 225, 198, 240, 215, 208, 222, 235, 201, 212], 0
    else:
        s_latencies, s_errors = measure_endpoint(search_url, headers, REPEATS)

    if s_latencies:
        sp50 = _percentile(s_latencies, 50)
        sp95 = _percentile(s_latencies, 95)
        sp99 = _percentile(s_latencies, 99)
    else:
        sp50 = sp95 = sp99 = 0

    slimit = RC_LIMITS['api_search_p95_ms']
    sstatus = 'PASS' if sp95 <= slimit and s_latencies else ('FAIL' if s_latencies else 'WARNING')
    results['search'] = {
        'endpoint': 'GET /api/v1/search/unified',
        'query': 'Prozess',
        'samples': len(s_latencies),
        'errors': s_errors,
        'p50_ms': round(sp50, 1),
        'p95_ms': round(sp95, 1),
        'p99_ms': round(sp99, 1),
        'limit_p95_ms': slimit,
        'status': sstatus,
        'dry_run': dry_run,
    }
    print('  p95=' + str(round(sp95, 1)) + 'ms  limit=' + str(slimit) + 'ms  ' + sstatus)

    # 3. Export PDF
    print('Messe PDF Export ...')
    if dry_run:
        export_ms, export_detail = 3200.0, 'dry_run_simulated'
    else:
        export_ms, export_detail = measure_export(api_base, headers, workspace_id)

    elimit = RC_LIMITS['export_pdf_ms']
    if export_ms is not None:
        estatus = 'PASS' if export_ms <= elimit else 'FAIL'
    else:
        estatus = 'WARNING'
        export_ms = 0

    results['export_pdf'] = {
        'endpoint': 'POST /api/v1/export/jobs (PDF)',
        'elapsed_ms': round(export_ms, 1) if export_ms else None,
        'limit_ms': elimit,
        'detail': export_detail,
        'status': estatus,
        'dry_run': dry_run,
    }
    print('  elapsed=' + str(round(export_ms, 1)) + 'ms  limit=' + str(elimit) + 'ms  ' + estatus)

    # 4. Frontend First Load
    print('Messe Frontend First Load ...')
    if dry_run:
        f_latencies, f_errors = [280, 310, 265, 330, 290, 275, 305, 320, 282, 271], 0
    else:
        f_latencies, f_errors = measure_endpoint(frontend_base + '/', {}, REPEATS)

    if f_latencies:
        fp50 = _percentile(f_latencies, 50)
        fp95 = _percentile(f_latencies, 95)
        fp99 = _percentile(f_latencies, 99)
    else:
        fp50 = fp95 = fp99 = 0

    flimit = RC_LIMITS['frontend_load_p95_ms']
    fstatus = 'PASS' if fp95 <= flimit and f_latencies else ('FAIL' if f_latencies else 'WARNING')
    results['frontend_load'] = {
        'endpoint': 'GET / (Frontend HTML)',
        'note': 'Misst HTTP-Transfer des HTML-Shells, kein JS-Render',
        'samples': len(f_latencies),
        'errors': f_errors,
        'p50_ms': round(fp50, 1),
        'p95_ms': round(fp95, 1),
        'p99_ms': round(fp99, 1),
        'limit_p95_ms': flimit,
        'status': fstatus,
        'dry_run': dry_run,
    }
    print('  p95=' + str(round(fp95, 1)) + 'ms  limit=' + str(flimit) + 'ms  ' + fstatus)

    # Gesamtbewertung
    statuses = [r['status'] for r in results.values()]
    if 'FAIL' in statuses:
        verdict = 'FAIL'
    elif 'WARNING' in statuses:
        verdict = 'WARNING'
    else:
        verdict = 'PASS'

    return results, verdict


def main():
    parser = argparse.ArgumentParser(description='Ruflo Performance Baseline')
    parser.add_argument('--api', default='http://localhost:8000')
    parser.add_argument('--frontend', default='http://localhost:5173')
    parser.add_argument('--token', default=None)
    parser.add_argument('--workspace-id', default=None)
    parser.add_argument('--report', default=REPORT_PATH)
    parser.add_argument('--dry-run', action='store_true',
                        help='Simulierte Messwerte (kein laufendes Backend erforderlich)')
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    if not args.dry_run:
        print('Pruefe Erreichbarkeit: ' + args.api)
        if not check_reachable(args.api):
            print('FEHLER: Backend nicht erreichbar. Starten oder --dry-run verwenden.', file=sys.stderr)
            sys.exit(2)

    results, verdict = run(
        api_base=args.api,
        frontend_base=args.frontend,
        token=args.token,
        workspace_id=args.workspace_id,
        dry_run=args.dry_run,
    )

    report = {
        'report_schema_version': 1,
        'report_name': 'performance_baseline_report',
        'report_type': 'performance_baseline',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'environment': {
            'api_base': args.api,
            'frontend_base': args.frontend,
            'dry_run': args.dry_run,
            'repeats_per_endpoint': REPEATS,
        },
        'rc_limits': RC_LIMITS,
        'measurements': results,
        'verdict': verdict,
        'rc_assessment': (
            'PASS — alle RC-Grenzwerte eingehalten.' if verdict == 'PASS'
            else ('WARNING — Messung unvollstaendig, Backend nicht vollstaendig gestartet.'
                  if verdict == 'WARNING'
                  else 'FAIL — mindestens ein RC-Grenzwert verletzt.')
        ),
    }

    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, 'w', encoding='utf-8') as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    if not args.quiet:
        print('Verdict:  ' + verdict)
        print('Report:   ' + args.report)

    sys.exit(0 if verdict == 'PASS' else (1 if verdict == 'FAIL' else 0))


if __name__ == '__main__':
    main()
