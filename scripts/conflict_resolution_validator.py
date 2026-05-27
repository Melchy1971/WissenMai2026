# conflict_resolution_validator.py
"""
Gate-Validator mit Konfliktauflösung für widersprüchliche Reports.
Regeln:
1. Aktuellster validierter Pflichtreport gewinnt.
2. Jeder FAIL in Pflichtreport blockiert.
3. RC darf Gate nicht überschreiben.
4. Final Release darf nur aus grünem Gate entstehen.
5. Stale PASS wird ignoriert.
6. Ungültiges JSON blockiert.
"""
import json
from pathlib import Path
from datetime import datetime

REQUIRED_REPORTS = [
    "m3a_final_release.json",
    "m3a_release_candidate.json",
    "frontend_truth_report.json",
    "m4b_upload_queue_truth_report.json",
]

REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"


def load_report(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"status": "BLOCKED", "error": f"invalid JSON: {e}"}

def parse_timestamp(ts):
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        # always return naive UTC for comparison
        if dt.tzinfo:
            return dt.replace(tzinfo=None)
        return dt
    except Exception:
        return datetime.min

def resolve_conflicts():
    results = {}
    for fname in REQUIRED_REPORTS:
        fpath = REPORTS_DIR / fname
        if not fpath.exists():
            results[fname] = {"status": "BLOCKED", "error": "missing report"}
            continue
        report = load_report(fpath)
        if report.get("status") == "BLOCKED" or "error" in report:
            results[fname] = report
            continue
        ts = report.get("timestamp")
        report["_ts"] = parse_timestamp(ts) if ts else datetime.min
        results[fname] = report
    # 1. Aktuellster Pflichtreport gewinnt
    sorted_reports = sorted(results.values(), key=lambda r: r.get("_ts", datetime.min), reverse=True)
    # 2. Jeder FAIL blockiert
    for r in sorted_reports:
        if r.get("status") == "FAIL":
            return {"gate": "BLOCKED", "reason": f"FAIL in {r.get('name', 'unknown')}"}
        if r.get("status") == "BLOCKED":
            return {"gate": "BLOCKED", "reason": r.get("error", "BLOCKED")}
    # 3. RC darf Gate nicht überschreiben
    rc = results.get("m3a_release_candidate.json")
    final = results.get("m3a_final_release.json")
    if rc and final and rc.get("status") == "BLOCKED" and final.get("status") == "PASS":
        return {"gate": "BLOCKED", "reason": "RC BLOCKED, Final Release nicht zulässig"}
    # 4. Final Release nur aus grünem Gate
    if final and final.get("status") == "PASS":
        for fname, r in results.items():
            if fname != "m3a_final_release.json" and r.get("status") != "PASS":
                return {"gate": "BLOCKED", "reason": f"Final Release nur bei grünem Gate ({fname})"}
    # 5. Stale PASS ignorieren (älter als 24h)
    now = datetime.utcnow()
    for r in sorted_reports:
        if r.get("status") == "PASS" and (now - r.get("_ts", now)).total_seconds() > 86400:
            return {"gate": "BLOCKED", "reason": "Stale PASS"}
    # 6. Ungültiges JSON blockiert (bereits oben)
    return {"gate": "PASS", "reason": "Alle Pflichtreports grün und aktuell"}

if __name__ == "__main__":
    result = resolve_conflicts()
    with open(REPORTS_DIR / "validation_report.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(json.dumps(result, indent=2, ensure_ascii=False))
