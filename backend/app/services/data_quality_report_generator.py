import json
from datetime import datetime
from typing import List

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
        quality_score = self.calculate_score(duplicates, metadata_issues, lifecycle_issues, source_status_issues, orphan_objects)
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
            "quality_score": quality_score,
            "findings": self.findings
        }

    def calculate_score(self, duplicates, metadata_issues, lifecycle_issues, source_status_issues, orphan_objects):
        # Gewichtung laut Vorgabe
        weights = {
            "duplicates": 0.25,
            "metadata": 0.15,
            "lifecycle": 0.25,
            "source": 0.20,
            "orphan": 0.15
        }
        penalty = (
            weights["duplicates"] * min(len(duplicates), 10) / 10 +
            weights["metadata"] * min(len(metadata_issues), 10) / 10 +
            weights["lifecycle"] * min(len(lifecycle_issues), 10) / 10 +
            weights["source"] * min(len(source_status_issues), 10) / 10 +
            weights["orphan"] * min(len(orphan_objects), 10) / 10
        )
        score = max(0, 100 - int(penalty * 100))
        return score

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
