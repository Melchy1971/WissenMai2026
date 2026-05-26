"""
Truth Marker Split Reporter
===========================
Pytest plugin.  Registriert via conftest.py → pytest_configure.

Regeln (aus dem Truth-Marker-Split-Briefing):
  Rule 1  M4-Gate wertet nur M4-Marker aus.
  Rule 2  M5-/Governance-Tests blockieren M4 nicht.
  Rule 3  Tests in postgres_truth/ ohne Gate-Marker brechen die Collection ab.
  Rule 4  Split-Reports werden automatisch nach jedem Run geschrieben.

Ausgabe (TRUTH_REPORT_DIR oder Standardpfad):
  truth_split_<timestamp>.json   – maschinenlesbare Zusammenfassung
  truth_split_<timestamp>.txt    – menschenlesbare Zusammenfassung
  m4_gate_<timestamp>.json       – M4-Gate-Ergebnis isoliert
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

# ─── Gate-Marker-Mengen ──────────────────────────────────────────────────────

TRUTH_GATE_MARKERS: frozenset[str] = frozenset(
    {
        "m4_truth",
        "m4a_auth_truth",
        "m4b_upload_queue_truth",
        "m4c_lifecycle_retrieval_truth",
        "m4e_backup_restore_truth",
        "m5_truth",
        "governance_truth",
    }
)

M4_GATE_MARKERS: frozenset[str] = frozenset(
    {
        "m4_truth",
        "m4a_auth_truth",
        "m4b_upload_queue_truth",
        "m4c_lifecycle_retrieval_truth",
        "m4e_backup_restore_truth",
    }
)

NON_BLOCKING_MARKERS: frozenset[str] = TRUTH_GATE_MARKERS - M4_GATE_MARKERS

# Default-Ausgabepfad: <repo-root>/reports/truth_split/
_DEFAULT_REPORT_DIR: Path = (
    Path(__file__).resolve().parents[4] / "reports" / "truth_split"
)


# ─── Modul-Level-State (einmal pro Pytest-Session) ───────────────────────────

_item_gate_markers: dict[str, frozenset[str]] = {}
_results: dict[str, list[dict]] = {}


# ─── Plugin-Klasse ───────────────────────────────────────────────────────────


class TruthSplitReporter:
    """
    Pytest-Plugin.  Wird von conftest.py via pytest_configure registriert.

    Hooks:
      pytest_collection_modifyitems  – baut Marker-Cache auf
      pytest_collection_finish       – Rule 3: bricht bei unmarkierten Tests ab
      pytest_runtest_logreport       – akkumuliert Ergebnisse pro Gate-Marker
      pytest_sessionfinish           – schreibt Split-Reports
    """

    def __init__(self, report_dir: Path) -> None:
        self._report_dir = report_dir
        # State zurücksetzen, damit parallele xdist-Runs nicht interferieren
        _item_gate_markers.clear()
        _results.clear()

    # ── Collection ──────────────────────────────────────────────────────────

    def pytest_collection_modifyitems(self, items: list[pytest.Item]) -> None:
        for item in items:
            if _is_truth_item(item):
                _item_gate_markers[item.nodeid] = _gate_markers_for(item)

    @pytest.hookimpl(tryfirst=True)
    def pytest_collection_finish(self, session: pytest.Session) -> None:
        if os.getenv("WISSEN_MARKER_TAXONOMY_ONLY") == "1":
            return
        unmarked = [
            item.nodeid
            for item in session.items
            if _is_truth_item(item) and not _gate_markers_for(item)
        ]
        if unmarked:
            detail = "\n".join(f"  {n}" for n in sorted(unmarked))
            pytest.exit(
                f"[Rule 3] {len(unmarked)} postgres_truth-Test(s) ohne Gate-Marker.\n"
                f"Jeder Test braucht mindestens einen aus: {sorted(TRUTH_GATE_MARKERS)}\n"
                f"{detail}",
                returncode=3,
            )

    # ── Laufzeit ────────────────────────────────────────────────────────────

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.when != "call":
            return
        gate_marks = _item_gate_markers.get(report.nodeid, frozenset())
        if not gate_marks:
            return
        entry: dict = {
            "nodeid": report.nodeid,
            "outcome": report.outcome,  # "passed" | "failed" | "error"
            "duration": round(report.duration, 4),
        }
        for marker in gate_marks:
            _results.setdefault(marker, []).append(entry)

    # ── Abschluss ───────────────────────────────────────────────────────────

    def pytest_sessionfinish(self, session: pytest.Session, exitstatus: int) -> None:
        if not _results:
            return
        self._report_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S")
        self._write_json_report(ts)
        self._write_text_report(ts)
        self._write_m4_gate_report(ts)
        _write_latest_symlinks(self._report_dir, ts)

    # ── Report-Schreiber ────────────────────────────────────────────────────

    def _write_json_report(self, ts: str) -> None:
        out = self._report_dir / f"truth_split_{ts}.json"
        out.write_text(
            json.dumps(_build_full_summary(ts), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _write_text_report(self, ts: str) -> None:
        summary = _build_full_summary(ts)
        lines: list[str] = [
            f"Truth Marker Split Report  {ts}",
            "=" * 70,
            "",
            "M4-GATE (blocking)",
            "-" * 70,
        ]
        for marker in sorted(M4_GATE_MARKERS):
            d = summary["markers"].get(marker, _empty_marker_data("m4"))
            _append_marker_line(lines, marker, d)

        lines += ["", "NON-BLOCKING", "-" * 70]
        for marker in sorted(NON_BLOCKING_MARKERS):
            d = summary["markers"].get(marker, _empty_marker_data("non_blocking"))
            _append_marker_line(lines, marker, d)

        lines += [
            "",
            "=" * 70,
            f"M4-GATE STATUS : {summary['m4_gate']['status']}",
            f"Blocking failures: {summary['m4_gate']['blocking_failures']}",
            "",
        ]
        out = self._report_dir / f"truth_split_{ts}.txt"
        out.write_text("\n".join(lines), encoding="utf-8")

    def _write_m4_gate_report(self, ts: str) -> None:
        out = self._report_dir / f"m4_gate_{ts}.json"
        out.write_text(
            json.dumps(_build_m4_gate_data(ts), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# ─── Hilfsfunktionen ─────────────────────────────────────────────────────────


def _is_truth_item(item: pytest.Item) -> bool:
    return "postgres_truth" in str(item.fspath)


def _gate_markers_for(item: pytest.Item) -> frozenset[str]:
    return frozenset(
        m.name for m in item.iter_markers() if m.name in TRUTH_GATE_MARKERS
    )


def _empty_marker_data(gate: str) -> dict:
    return {
        "gate": gate,
        "total": 0,
        "passed": 0,
        "failed": 0,
        "error": 0,
        "failed_tests": [],
    }


def _append_marker_line(lines: list[str], marker: str, d: dict) -> None:
    status = "PASS" if d["failed"] + d["error"] == 0 and d["total"] > 0 else (
        "FAIL" if d["failed"] + d["error"] > 0 else "NO TESTS"
    )
    lines.append(
        f"  {marker:<40} {status:8}  "
        f"passed={d['passed']} failed={d['failed']} error={d['error']} total={d['total']}"
    )
    for n in d["failed_tests"]:
        lines.append(f"    FAIL  {n}")


def _build_full_summary(ts: str) -> dict:
    markers_data: dict[str, dict] = {}
    for marker in sorted(TRUTH_GATE_MARKERS):
        entries = _results.get(marker, [])
        passed = sum(1 for e in entries if e["outcome"] == "passed")
        failed = sum(1 for e in entries if e["outcome"] == "failed")
        error = sum(1 for e in entries if e["outcome"] == "error")
        markers_data[marker] = {
            "gate": "m4" if marker in M4_GATE_MARKERS else "non_blocking",
            "total": len(entries),
            "passed": passed,
            "failed": failed,
            "error": error,
            "failed_tests": [
                e["nodeid"]
                for e in entries
                if e["outcome"] in ("failed", "error")
            ],
            "tests": entries,
        }
    m4_failures = sum(
        d["failed"] + d["error"]
        for m, d in markers_data.items()
        if m in M4_GATE_MARKERS
    )
    return {
        "generated_at": ts,
        "m4_gate": {
            "status": "PASS" if m4_failures == 0 else "FAIL",
            "blocking_failures": m4_failures,
            "evaluated_markers": sorted(M4_GATE_MARKERS),
            "excluded_markers": sorted(NON_BLOCKING_MARKERS),
        },
        "markers": markers_data,
    }


def _build_m4_gate_data(ts: str) -> dict:
    summary = _build_full_summary(ts)
    return {
        "generated_at": ts,
        "gate": "M4",
        "status": summary["m4_gate"]["status"],
        "blocking_failures": summary["m4_gate"]["blocking_failures"],
        "evaluated_markers": sorted(M4_GATE_MARKERS),
        "excluded_markers": sorted(NON_BLOCKING_MARKERS),
        "per_marker": {
            m: summary["markers"][m]
            for m in sorted(M4_GATE_MARKERS)
            if m in summary["markers"]
        },
    }


def _write_latest_symlinks(report_dir: Path, ts: str) -> None:
    """Überschreibt *_latest.{json,txt} mit dem aktuellen Run (kein Symlink auf Windows)."""
    for suffix in ("json", "txt"):
        src = report_dir / f"truth_split_{ts}.{suffix}"
        if src.exists():
            dst = report_dir / f"truth_split_latest.{suffix}"
            try:
                dst.write_bytes(src.read_bytes())
            except OSError:
                pass
    src_gate = report_dir / f"m4_gate_{ts}.json"
    if src_gate.exists():
        dst_gate = report_dir / "m4_gate_latest.json"
        try:
            dst_gate.write_bytes(src_gate.read_bytes())
        except OSError:
            pass
