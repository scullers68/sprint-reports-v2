"""
Report models for sprint reporting and analytics.

Handles report generation, snapshots, and historical comparisons.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, Integer, Float, Text, Boolean, ForeignKey, JSON, LargeBinary
from sqlalchemy.orm import relationship

from app.models.base import Base


class Report(Base):
    """Sprint report metadata and configuration."""
    
    __tablename__ = "reports"
    
    # Foreign keys
    sprint_id = Column(Integer, ForeignKey("sprints.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Report metadata
    name = Column(String(200), nullable=False)
    report_type = Column(String(100), nullable=False, index=True)  # baseline, comparison, analytics
    description = Column(Text, nullable=True)
    
    # Generation settings
    include_subtasks = Column(Boolean, default=False, nullable=False)
    include_epics = Column(Boolean, default=True, nullable=False)
    confluence_space = Column(String(100), nullable=True)
    
    # Report status
    status = Column(String(50), nullable=False, default="pending")  # pending, generating, completed, failed
    generation_started_at = Column(DateTime(timezone=True), nullable=True)
    generation_completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Output configuration
    output_formats = Column(JSON, nullable=True)  # ["html", "pdf", "confluence", "json"]
    confluence_page_id = Column(String(100), nullable=True)
    file_path = Column(String(500), nullable=True)
    
    # Report metrics
    total_issues = Column(Integer, nullable=True)
    total_story_points = Column(Float, nullable=True)
    completion_percentage = Column(Float, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    sprint = relationship("Sprint", back_populates="reports")
    created_by_user = relationship("User")
    snapshots = relationship("ReportSnapshot", back_populates="report", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Report(id={self.id}, name='{self.name}', type='{self.report_type}', status='{self.status}')>"


class ReportSnapshot(Base):
    """Point-in-time snapshots of sprint data for reporting."""
    
    __tablename__ = "report_snapshots"
    
    # Foreign keys
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, index=True)
    sprint_id = Column(Integer, ForeignKey("sprints.id"), nullable=False, index=True)
    
    # Snapshot metadata
    snapshot_name = Column(String(200), nullable=False)
    snapshot_type = Column(String(100), nullable=False)  # baseline, interim, final
    snapshot_date = Column(DateTime(timezone=True), nullable=False)
    
    # Sprint state at snapshot
    sprint_state = Column(String(50), nullable=False)
    sprint_start_date = Column(DateTime(timezone=True), nullable=True)
    sprint_end_date = Column(DateTime(timezone=True), nullable=True)
    
    # Snapshot data (compressed JSON)
    issues_data = Column(JSON, nullable=False)  # Full JIRA issue data
    metrics_summary = Column(JSON, nullable=False)  # Calculated metrics
    
    # Data integrity
    data_hash = Column(String(64), nullable=False)  # SHA-256 hash of snapshot data
    data_size = Column(Integer, nullable=False)  # Size in bytes
    
    # Comparison metadata
    comparison_baseline_id = Column(Integer, ForeignKey("report_snapshots.id"), nullable=True)
    is_baseline = Column(Boolean, default=False, nullable=False)
    
    # File storage (for large snapshots)
    file_path = Column(String(500), nullable=True)
    compressed = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    report = relationship("Report", back_populates="snapshots")
    sprint = relationship("Sprint")
    comparison_baseline = relationship("ReportSnapshot", remote_side="ReportSnapshot.id")
    
    def __repr__(self) -> str:
        return f"<ReportSnapshot(id={self.id}, name='{self.snapshot_name}', type='{self.snapshot_type}')>"


class ReportTemplate(Base):
    """Reusable report templates and configurations."""
    
    __tablename__ = "report_templates"
    
    # Template metadata
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    template_type = Column(String(100), nullable=False)  # baseline, comparison, custom
    
    # Template configuration
    default_settings = Column(JSON, nullable=False)  # Default report settings
    confluence_template = Column(Text, nullable=True)  # Confluence page template
    html_template = Column(Text, nullable=True)  # HTML report template
    
    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Template management
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_system_template = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    version = Column(String(20), nullable=False, default="1.0")
    
    # Relationships
    created_by_user = relationship("User")
    
    def __repr__(self) -> str:
        return f"<ReportTemplate(id={self.id}, name='{self.name}', type='{self.template_type}')>"