"""
Sprint service for business logic operations.

Handles sprint CRUD operations, JIRA synchronization, and analysis.
"""

import hashlib
import json
import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone

from sqlalchemy import select, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.sprint import (
    Sprint, SprintAnalysis, SyncMetadata, ConflictResolution, SyncHistory,
    SyncStatus, ConflictResolutionStrategy
)
from app.schemas.sprint import SprintCreate, SprintUpdate, SprintAnalysisCreate
from app.services.jira_service import JiraService
from app.core.logging import get_logger

logger = get_logger(__name__)


class SprintService:
    """Service class for sprint operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_sprints(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        state: Optional[str] = None
    ) -> List[Sprint]:
        """Get list of sprints with optional filtering."""
        query = select(Sprint)
        
        if state:
            query = query.where(Sprint.state == state)
        
        query = query.offset(skip).limit(limit).order_by(desc(Sprint.updated_at))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_active_sprints(self) -> List[Sprint]:
        """Get only active sprints."""
        query = select(Sprint).where(Sprint.state == "active")
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_sprint(self, sprint_id: int) -> Optional[Sprint]:
        """Get a sprint by ID."""
        query = select(Sprint).where(Sprint.id == sprint_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_sprint_by_name(self, name: str) -> Optional[Sprint]:
        """Get a sprint by name."""
        query = select(Sprint).where(Sprint.name == name)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_sprint_by_jira_id(self, jira_sprint_id: int) -> Optional[Sprint]:
        """Get a sprint by JIRA sprint ID."""
        query = select(Sprint).where(Sprint.jira_sprint_id == jira_sprint_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_sprint(self, sprint_data: SprintCreate) -> Sprint:
        """Create a new sprint."""
        # Check if sprint with same JIRA ID already exists
        existing = await self.get_sprint_by_jira_id(sprint_data.jira_sprint_id)
        if existing:
            raise ValueError(f"Sprint with JIRA ID {sprint_data.jira_sprint_id} already exists")
        
        sprint = Sprint(**sprint_data.model_dump())
        self.db.add(sprint)
        await self.db.commit()
        await self.db.refresh(sprint)
        return sprint
    
    async def update_sprint(
        self, 
        sprint_id: int, 
        sprint_data: SprintUpdate
    ) -> Optional[Sprint]:
        """Update an existing sprint."""
        sprint = await self.get_sprint(sprint_id)
        if not sprint:
            return None
        
        update_data = sprint_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(sprint, field, value)
        
        await self.db.commit()
        await self.db.refresh(sprint)
        return sprint
    
    async def delete_sprint(self, sprint_id: int) -> bool:
        """Delete a sprint."""
        sprint = await self.get_sprint(sprint_id)
        if not sprint:
            return False
        
        await self.db.delete(sprint)
        await self.db.commit()
        return True
    
    async def sync_from_jira(
        self, 
        jira_service: JiraService, 
        board_id: Optional[int] = None
    ) -> List[Sprint]:
        """Sync sprints from JIRA."""
        # Get sprints from JIRA
        jira_sprints = await jira_service.get_sprints(board_id=board_id)
        synced_sprints = []
        
        for jira_sprint in jira_sprints:
            # Check if sprint already exists
            existing = await self.get_sprint_by_jira_id(jira_sprint["id"])
            
            if existing:
                # Update existing sprint
                sprint_update = SprintUpdate(
                    name=jira_sprint["name"],
                    state=jira_sprint["state"].lower(),
                    goal=jira_sprint.get("goal"),
                    start_date=jira_sprint.get("startDate"),
                    end_date=jira_sprint.get("endDate"),
                    complete_date=jira_sprint.get("completeDate")
                )
                sprint = await self.update_sprint(existing.id, sprint_update)
            else:
                # Create new sprint
                sprint_create = SprintCreate(
                    jira_sprint_id=jira_sprint["id"],
                    name=jira_sprint["name"],
                    state=jira_sprint["state"].lower(),
                    goal=jira_sprint.get("goal"),
                    start_date=jira_sprint.get("startDate"),
                    end_date=jira_sprint.get("endDate"),
                    complete_date=jira_sprint.get("completeDate"),
                    board_id=jira_sprint.get("originBoardId"),
                    origin_board_id=jira_sprint.get("originBoardId")
                )
                sprint = await self.create_sprint(sprint_create)
            
            synced_sprints.append(sprint)
        
        return synced_sprints
    
    async def analyze_sprint(
        self, 
        sprint_id: int, 
        analysis_data: SprintAnalysisCreate,
        field_mapping_template_id: Optional[int] = None
    ) -> SprintAnalysis:
        """Analyze a sprint and create discipline team breakdown with dynamic field mapping support."""
        sprint = await self.get_sprint(sprint_id)
        if not sprint:
            raise ValueError(f"Sprint with ID {sprint_id} not found")
        
        # Get JIRA service for data collection with field mapping support
        jira_service = JiraService(db=self.db)
        
        # Try to get mapped issues first, fall back to regular issues
        try:
            if field_mapping_template_id:
                issues = await jira_service.get_sprint_issues_with_mapping(
                    sprint.jira_sprint_id,
                    template_id=field_mapping_template_id,
                    exclude_subtasks=analysis_data.exclude_subtasks,
                    jql_filter=analysis_data.jql_filter
                )
            else:
                issues = await jira_service.get_sprint_issues(
                    sprint.jira_sprint_id,
                    exclude_subtasks=analysis_data.exclude_subtasks,
                    jql_filter=analysis_data.jql_filter
                )
        except Exception as e:
            # Fall back to regular issues if mapping fails
            issues = await jira_service.get_sprint_issues(
                sprint.jira_sprint_id,
                exclude_subtasks=analysis_data.exclude_subtasks,
                jql_filter=analysis_data.jql_filter
            )
        
        # Process issues and create discipline team breakdown
        discipline_breakdown = {}
        total_issues = len(issues)
        total_story_points = 0.0
        
        for issue in issues:
            # Extract team information - try mapped fields first, then fall back to hardcoded
            team_name = self._extract_discipline_team(issue)
            story_points = self._extract_story_points(issue)
            
            total_story_points += story_points
            
            # Update team breakdown
            if team_name not in discipline_breakdown:
                discipline_breakdown[team_name] = {
                    "issues": 0,
                    "story_points": 0.0,
                    "issue_keys": []
                }
            
            discipline_breakdown[team_name]["issues"] += 1
            discipline_breakdown[team_name]["story_points"] += story_points
            discipline_breakdown[team_name]["issue_keys"].append(issue["key"])
        
        # Create analysis record
        analysis = SprintAnalysis(
            sprint_id=sprint_id,
            analysis_type=analysis_data.analysis_type,
            total_issues=total_issues,
            total_story_points=total_story_points,
            discipline_teams_count=len(discipline_breakdown),
            discipline_breakdown=discipline_breakdown,
            issue_details={"issues": issues},
            jql_filter=analysis_data.jql_filter,
            exclude_subtasks=analysis_data.exclude_subtasks
        )
        
        self.db.add(analysis)
        await self.db.commit()
        await self.db.refresh(analysis)
        
        return analysis
    
    def _extract_discipline_team(self, issue: Dict[str, Any]) -> str:
        """Extract discipline team from issue with fallback logic."""
        # Try mapped fields first
        if "mapped_fields" in issue:
            mapped_team = issue["mapped_fields"].get("discipline_team")
            if mapped_team:
                if isinstance(mapped_team, dict):
                    return mapped_team.get("value", "Unassigned")
                return str(mapped_team)
        
        # Fall back to hardcoded custom field
        discipline_team = issue.get("fields", {}).get("customfield_10741", {})
        if isinstance(discipline_team, dict):
            return discipline_team.get("value", "Unassigned")
        elif discipline_team:
            return str(discipline_team)
        
        return "Unassigned"
    
    def _extract_story_points(self, issue: Dict[str, Any]) -> float:
        """Extract story points from issue with fallback logic."""
        # Try mapped fields first
        if "mapped_fields" in issue:
            mapped_points = issue["mapped_fields"].get("story_points")
            if mapped_points is not None:
                try:
                    return float(mapped_points)
                except (ValueError, TypeError):
                    pass
        
        # Fall back to hardcoded custom field
        story_points = issue.get("fields", {}).get("customfield_10002", 0.0)
        if story_points is not None:
            try:
                return float(story_points)
            except (ValueError, TypeError):
                pass
        
        return 0.0
    
    async def get_sprint_analyses(self, sprint_id: int) -> List[SprintAnalysis]:
        """Get all analyses for a sprint."""
        query = select(SprintAnalysis).where(
            SprintAnalysis.sprint_id == sprint_id
        ).order_by(desc(SprintAnalysis.created_at))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_latest_analysis(self, sprint_id: int) -> Optional[SprintAnalysis]:
        """Get the latest analysis for a sprint."""
        query = select(SprintAnalysis).where(
            SprintAnalysis.sprint_id == sprint_id
        ).order_by(desc(SprintAnalysis.created_at)).limit(1)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()