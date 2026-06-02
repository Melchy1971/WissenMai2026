import json
from datetime import datetime
from typing import List

from app.services.quality_score import calculate_quality_score_from_findings

class DataQualityReportGenerator:
    def __init__(self, findings: List[dict], total_documents: int):
        self.findings = findings
        self.total_documents = total_documents

    def generate(self) -> dict:
        duplicates = [f for f in self.findings if f["type"].startswith("DUPLICATE")]
        metadata_issues = [f for f in self.findings if "METADATA" in f["type"]]
        lifecycle_issues = [f for f in self.findings if f["type"] == "INVALID_LIFECYCLE"]
        source_status_issues = [f for f in self.findings if f["type"] == "INVALID_SOURCE_STATUS"]
        orphan_objects = [f for f in self.findings if "ORPHAN" in f["type"]]
        score_result = calculate_quality_score_from_findings(self.findings)
        return {
            "report_schema_version": "1.0.0",
            "report_name": "data_quality_report",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_documents": self.total_documents,
            "duplicates": len(duplicates),
            "metadata_issues": len(metadata_issues),
            "lifecycle_issues": len(lifecycle_issues),
            "source_status_issues": len(source_status_issues),
            "orphan_objects": len(orphan_objects),
            "quality_score": score_result.score,
            "score_explanation": score_result.score_explanation,
            "findings": self.findings
        }

    def calculate_score(self, duplicates, metadata_issues, lifecycle_issues, source_status_issues, orphan_objects):
        findings = [
            *duplicates,
            *metadata_issues,
            *lifecycle_issues,
            *source_status_issues,
            *orphan_objects,
        ]
        return calculate_quality_score_from_findings(findings).score

    def write_json(self, path: str):
        report = self.generate()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    def write_md(self, path: str):
        report = self.generate()
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Data Quality Report\n\n")
            f.write(f"**Stand:** {report['timestamp']}\n\n")
            f.write(f"- Total Documents: {report['total_documents']}\n")
            f.write(f"- Duplicates: {report['duplicates']}\n")
            f.write(f"- Metadata Issues: {report['metadata_issues']}\n")
            f.write(f"- Lifecycle Issues: {report['lifecycle_issues']}\n")
            f.write(f"- Source Status Issues: {report['source_status_issues']}\n")
            f.write(f"- Orphan Objects: {report['orphan_objects']}\n")
            f.write(f"- Quality Score: {report['quality_score']}\n\n")
            f.write("## Findings\n\n")
            for fnd in report["findings"]:
                f.write(f"- [{fnd['severity']}] {fnd['type']}: {fnd['remediation']}\n")
