from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import contextlib
import io
import json
import os
from pathlib import Path
import sys
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"
JSON_REPORT_PATH = REPORTS_DIR / "truth_marker_taxonomy.json"
MARKDOWN_REPORT_PATH = REPORTS_DIR / "truth_marker_taxonomy.md"

GATE_MARKERS = (
    "m4_truth",
    "m4a_auth_truth",
    "m4b_upload_queue_truth",
    "m4c_lifecycle_retrieval_truth",
    "m4e_backup_restore_truth",
    "m5_truth",
    "governance_truth",
)

M4_BLOCKING_MARKERS = {
    "m4_truth",
    "m4a_auth_truth",
    "m4b_upload_queue_truth",
    "m4c_lifecycle_retrieval_truth",
    "m4e_backup_restore_truth",
}


@dataclass(eq=False)
class TaxonomyCollectPlugin:
    collected: int = 0
    tests_by_marker: dict[str, list[str]] = field(
        default_factory=lambda: {marker: [] for marker in GATE_MARKERS}
    )
    unclassified: list[str] = field(default_factory=list)
    ambiguous: list[dict[str, Any]] = field(default_factory=list)

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        self.collected = len(session.items)
        for item in session.items:
            markers = sorted({marker.name for marker in item.iter_markers()} & set(GATE_MARKERS))
            marker_names = {marker.name for marker in item.iter_markers()}
            nodeid = item.nodeid.replace("\\", "/")
            is_truth_test = bool(markers) or "postgres_truth" in marker_names or "postgres_truth/" in nodeid
            if not is_truth_test:
                continue
            if not markers:
                self.unclassified.append(item.nodeid)
            elif len(markers) > 1:
                self.ambiguous.append({"nodeid": item.nodeid, "markers": markers})
            else:
                self.tests_by_marker[markers[0]].append(item.nodeid)


def _collect_taxonomy() -> tuple[int, TaxonomyCollectPlugin]:
    plugin = TaxonomyCollectPlugin()
    old_env = os.environ.get("WISSEN_MARKER_TAXONOMY_ONLY")
    os.environ["WISSEN_MARKER_TAXONOMY_ONLY"] = "1"
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = pytest.main(["backend/tests", "--collect-only", "-qq"], plugins=[plugin])
    finally:
        if old_env is None:
            os.environ.pop("WISSEN_MARKER_TAXONOMY_ONLY", None)
        else:
            os.environ["WISSEN_MARKER_TAXONOMY_ONLY"] = old_env
    return int(exit_code), plugin


def _build_payload(exit_code: int, plugin: TaxonomyCollectPlugin) -> dict[str, Any]:
    counts = {marker: len(tests) for marker, tests in plugin.tests_by_marker.items()}
    errors = []
    if plugin.unclassified:
        errors.append(f"{len(plugin.unclassified)} unklassifizierte Tests")
    if plugin.ambiguous:
        errors.append(f"{len(plugin.ambiguous)} mehrfach klassifizierte Tests")
    if exit_code != int(pytest.ExitCode.OK):
        errors.append(f"pytest collect exit code {exit_code}")

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "taxonomy": {
            "gate_markers": list(GATE_MARKERS),
            "blocking_rules": {
                "m3a": ["frontend_truth"],
                "m4": sorted(M4_BLOCKING_MARKERS),
                "m5": ["m4_truth"],
                "not_m4_blocking": ["m5_truth", "governance_truth"],
            },
        },
        "collected": plugin.collected,
        "marker_counts": counts,
        "tests_by_marker": plugin.tests_by_marker,
        "unclassified_tests": plugin.unclassified,
        "ambiguous_tests": plugin.ambiguous,
        "errors": errors,
        "result": "FAIL" if errors else "PASS",
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Truth-Test Marker Taxonomie",
        "",
        f"- Result: `{payload['result']}`",
        f"- Collected: `{payload['collected']}`",
        f"- Generated: `{payload['generated_at']}`",
        "",
        "## Marker",
        "",
    ]
    lines.extend(f"- `{marker}`" for marker in payload["taxonomy"]["gate_markers"])
    lines.extend(["", "## Blocking-Regeln", ""])
    for gate, markers in payload["taxonomy"]["blocking_rules"].items():
        lines.append(f"- `{gate}`: {', '.join(f'`{marker}`' for marker in markers)}")
    lines.extend(["", "## Testklassifikation", ""])
    for marker, tests in payload["tests_by_marker"].items():
        lines.append(f"### `{marker}` ({len(tests)})")
        lines.extend(f"- `{test}`" for test in tests)
        if not tests:
            lines.append("- keine")
        lines.append("")
    lines.append("## Unklassifizierte Tests")
    if payload["unclassified_tests"]:
        lines.extend(f"- `{test}`" for test in payload["unclassified_tests"])
    else:
        lines.append("- keine")
    lines.append("")
    lines.append("## Mehrfach klassifizierte Tests")
    if payload["ambiguous_tests"]:
        for item in payload["ambiguous_tests"]:
            lines.append(f"- `{item['nodeid']}` -> {', '.join(item['markers'])}")
    else:
        lines.append("- keine")
    return "\n".join(lines) + "\n"


def main() -> int:
    exit_code, plugin = _collect_taxonomy()
    payload = _build_payload(exit_code, plugin)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_REPORT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    MARKDOWN_REPORT_PATH.write_text(_render_markdown(payload), encoding="utf-8")
    print(f"Truth Marker Taxonomy = {payload['result']}")
    print(f"Collected: {payload['collected']}")
    print(f"Unclassified: {len(payload['unclassified_tests'])}")
    print(f"Ambiguous: {len(payload['ambiguous_tests'])}")
    print(f"Wrote: {JSON_REPORT_PATH}")
    print(f"Wrote: {MARKDOWN_REPORT_PATH}")
    return 0 if payload["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
