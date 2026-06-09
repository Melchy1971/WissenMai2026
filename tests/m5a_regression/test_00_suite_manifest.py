from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


pytestmark = pytest.mark.m3a_truth


REPO_ROOT = Path(__file__).resolve().parents[2]
SUITE_DIR = REPO_ROOT / "tests" / "m5a_regression"

REGRESSION_AREAS = {
    "duplicate_detection": {
        "suite_file": "test_01_duplicate_detection.py",
        "source_tests": ["backend/tests/test_duplicate_detector.py"],
    },
    "metadata_detection": {
        "suite_file": "test_02_metadata_detection.py",
        "source_tests": ["backend/tests/test_metadata_quality_detector.py"],
    },
    "lifecycle_integrity": {
        "suite_file": "test_03_lifecycle_integrity.py",
        "source_tests": ["backend/tests/test_lifecycle_integrity_detector.py"],
    },
    "source_status_integrity": {
        "suite_file": "test_04_source_status_integrity.py",
        "source_tests": ["backend/tests/test_source_status_integrity_detector.py"],
    },
    "orphan_detection": {
        "suite_file": "test_05_orphan_detection.py",
        "source_tests": ["backend/tests/test_orphan_detector.py"],
    },
    "quality_score": {
        "suite_file": "test_06_quality_score.py",
        "source_tests": ["backend/tests/test_m5a_quality_score.py"],
    },
    "data_quality_report": {
        "suite_file": "test_07_data_quality_report.py",
        "source_tests": [
            "backend/tests/test_data_quality_runner.py",
            "backend/tests/test_run_data_quality_report_v2.py",
        ],
    },
}


def test_all_required_m5a_regression_areas_are_registered() -> None:
    assert set(REGRESSION_AREAS) == {
        "duplicate_detection",
        "metadata_detection",
        "lifecycle_integrity",
        "source_status_integrity",
        "orphan_detection",
        "quality_score",
        "data_quality_report",
    }


@pytest.mark.parametrize("area", sorted(REGRESSION_AREAS))
def test_regression_area_has_collectable_suite_file(area: str) -> None:
    suite_file = SUITE_DIR / REGRESSION_AREAS[area]["suite_file"]

    assert suite_file.exists()
    assert _count_collectable_tests(suite_file) > 0


@pytest.mark.parametrize("area", sorted(REGRESSION_AREAS))
def test_regression_area_source_tests_exist(area: str) -> None:
    for source in REGRESSION_AREAS[area]["source_tests"]:
        assert (REPO_ROOT / source).exists(), source


def _count_collectable_tests(path: Path) -> int:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    count = 0
    for name, value in vars(module).items():
        if name.startswith("test_") and callable(value):
            count += 1
        if name.startswith("Test") and isinstance(value, type):
            count += sum(1 for attr in vars(value) if attr.startswith("test_"))
    return count
