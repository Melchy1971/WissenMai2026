from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import JSON
import enum

from .documents import Base

class DataQualityFindingType(enum.Enum):
    DUPLICATE_DOCUMENT = "DUPLICATE_DOCUMENT"
    DUPLICATE_CONTENT = "DUPLICATE_CONTENT"
    EMPTY_DOCUMENT = "EMPTY_DOCUMENT"
    EMPTY_CHUNK = "EMPTY_CHUNK"
    ORPHAN_CHUNK = "ORPHAN_CHUNK"
    ORPHAN_VERSION = "ORPHAN_VERSION"
    MISSING_METADATA = "MISSING_METADATA"
    INVALID_SOURCE_STATUS = "INVALID_SOURCE_STATUS"
    INVALID_LIFECYCLE = "INVALID_LIFECYCLE"
    RETRIEVAL_RISK = "RETRIEVAL_RISK"

class DataQualityRun(Base):
    __tablename__ = "data_quality_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=True)
    findings = relationship("DataQualityFinding", back_populates="run")

class DataQualityFinding(Base):
    __tablename__ = "data_quality_findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("data_quality_runs.id", ondelete="CASCADE"), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False)
    finding_type: Mapped[DataQualityFindingType] = mapped_column(Enum(DataQualityFindingType), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    document_id: Mapped[str | None] = mapped_column(String, nullable=True)
    version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    chunk_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_status: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Text] = mapped_column(Text, nullable=False)
    remediation: Mapped[Text] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    run = relationship("DataQualityRun", back_populates="findings")

class DataQualityMetric(Base):
    __tablename__ = "data_quality_metrics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("data_quality_runs.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[float] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class DataQualitySnapshot(Base):
    __tablename__ = "data_quality_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False)
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=True)
    findings: Mapped[dict] = mapped_column(JSON, nullable=True)
