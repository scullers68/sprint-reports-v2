"""
Sprint service for business logic operations.

Handles sprint CRUD operations, JIRA synchronization, and analysis.
"""

import hashlib
import json
import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.sprint import (
    Sprint, SprintAnalysis, SyncMetadata, ConflictResolution, SyncHistory,
    SyncStatus, ConflictResolutionStrategy
)
from app.models.project import ProjectWorkstream, ProjectSprintAssociation, ProjectSprintMetrics
from app.models.cached_sprint import CachedSprint
from app.schemas.sprint import SprintCreate, SprintUpdate, SprintAnalysisCreate
from app.schemas.meta_boards import (
    ProjectPortfolioResponse, ProjectPortfolioSummary, ProjectMetrics,
    ProjectCompletionForecast, ResourceAllocation, ProjectRanking,
    ProjectRankingCriteria, ProjectPortfolioFilters, ProjectHealthStatus,
    ProjectPriority, SprintHealthIndicator
)
from app.services.jira_service import JiraService
from app.core.logging import get_logger
from app.core.exceptions import NotFoundError, ValidationError

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
    
    # ========== PROJECT PORTFOLIO METHODS ==========
    
    async def get_project_portfolio(
        self,
        board_id: int,
        sprint_id: Optional[int] = None,
        filters: Optional[ProjectPortfolioFilters] = None,
        use_cache: bool = True
    ) -> ProjectPortfolioResponse:
        """
        Get comprehensive project portfolio data for meta-board dashboard.
        
        Args:
            board_id: Meta-board ID
            sprint_id: Optional specific sprint, defaults to active sprint
            filters: Optional filtering criteria
            use_cache: Whether to use cached data when available
            
        Returns:
            Complete project portfolio response with metrics and health indicators
        """
        logger.info(f"Aggregating project portfolio for board {board_id}")
        
        # Get target sprint
        if sprint_id:
            sprint = await self.get_sprint(sprint_id)
        else:
            # Get active sprint for this board
            sprint = await self._get_active_sprint_for_board(board_id)
        
        if not sprint:
            raise NotFoundError(f"No active sprint found for meta-board {board_id}")
        
        # Get project associations for this sprint
        project_associations = await self._get_project_sprint_associations(sprint.id)
        
        if not project_associations:
            logger.warning(f"No project associations found for sprint {sprint.id}")
            return self._create_empty_portfolio_response(board_id, sprint)
        
        # Aggregate project metrics
        project_metrics = []
        summary_metrics = {
            'total_projects': 0,
            'active_projects': 0,
            'completed_projects': 0,
            'blocked_projects': 0,
            'total_story_points': 0.0,
            'completed_story_points': 0.0,
            'projects_on_track': 0,
            'projects_at_risk': 0,
            'projects_behind': 0,
            'risk_scores': []
        }
        
        for association in project_associations:
            try:
                # Get project metrics
                metrics = await self._calculate_project_metrics(
                    association.project_workstream,
                    association,
                    sprint
                )
                
                # Apply filters if provided
                if filters and not self._matches_filters(metrics, filters):
                    continue
                
                project_metrics.append(metrics)
                
                # Update summary metrics
                self._update_summary_metrics(summary_metrics, metrics)
                
            except Exception as e:
                logger.warning(f"Error calculating metrics for project {association.project_workstream.project_key}: {str(e)}")
                continue
        
        # Calculate health indicators
        health_indicators = await self._calculate_health_indicators(project_metrics, sprint)
        
        # Create portfolio summary
        summary = ProjectPortfolioSummary(
            meta_board_id=board_id,
            meta_board_name=f"Meta-board {board_id}",  # Could be enhanced with actual name
            sprint_id=sprint.id,
            sprint_name=sprint.name,
            total_projects=summary_metrics['total_projects'],
            active_projects=summary_metrics['active_projects'],
            completed_projects=summary_metrics['completed_projects'],
            blocked_projects=summary_metrics['blocked_projects'],
            total_story_points=summary_metrics['total_story_points'],
            completed_story_points=summary_metrics['completed_story_points'],
            overall_completion_percentage=self._calculate_overall_completion(summary_metrics),
            projects_on_track=summary_metrics['projects_on_track'],
            projects_at_risk=summary_metrics['projects_at_risk'],
            projects_behind=summary_metrics['projects_behind'],
            average_risk_score=sum(summary_metrics['risk_scores']) / len(summary_metrics['risk_scores']) if summary_metrics['risk_scores'] else 0.0,
            last_updated=datetime.now(timezone.utc)
        )
        
        return ProjectPortfolioResponse(
            summary=summary,
            projects=project_metrics,
            health_indicators=health_indicators,
            last_sync=datetime.now(timezone.utc),
            data_freshness="current" if not use_cache else "cached"
        )
    
    async def get_project_completion_forecasts(
        self,
        board_id: int,
        sprint_id: Optional[int] = None,
        project_keys: Optional[List[str]] = None,
        confidence_threshold: float = 0.7
    ) -> List[ProjectCompletionForecast]:
        """Generate project completion forecasts based on velocity and remaining work."""
        logger.info(f"Generating completion forecasts for board {board_id}")
        
        # Get target sprint
        if sprint_id:
            sprint = await self.get_sprint(sprint_id)
        else:
            sprint = await self._get_active_sprint_for_board(board_id)
        
        if not sprint:
            raise NotFoundError(f"No active sprint found for meta-board {board_id}")
        
        # Get project associations
        project_associations = await self._get_project_sprint_associations(sprint.id)
        
        forecasts = []
        for association in project_associations:
            if project_keys and association.project_workstream.project_key not in project_keys:
                continue
            
            try:
                forecast = await self._calculate_project_forecast(
                    association.project_workstream,
                    association,
                    sprint,
                    confidence_threshold
                )
                
                if forecast.confidence_level >= confidence_threshold:
                    forecasts.append(forecast)
                    
            except Exception as e:
                logger.warning(f"Error generating forecast for project {association.project_workstream.project_key}: {str(e)}")
                continue
        
        return forecasts
    
    async def get_project_resource_allocation(
        self,
        board_id: int,
        sprint_id: Optional[int] = None,
        include_discipline_breakdown: bool = True
    ) -> Dict[str, Any]:
        """Get resource allocation data for projects within meta-board sprint."""
        logger.info(f"Calculating resource allocation for board {board_id}")
        
        # Get target sprint
        if sprint_id:
            sprint = await self.get_sprint(sprint_id)
        else:
            sprint = await self._get_active_sprint_for_board(board_id)
        
        if not sprint:
            raise NotFoundError(f"No active sprint found for meta-board {board_id}")
        
        # Get project associations
        project_associations = await self._get_project_sprint_associations(sprint.id)
        
        allocations = []
        total_capacity = 0.0
        total_utilized = 0.0
        
        for association in project_associations:
            try:
                allocation = await self._calculate_resource_allocation(
                    association.project_workstream,
                    association,
                    sprint,
                    include_discipline_breakdown
                )
                
                allocations.append(allocation)
                total_capacity += allocation.allocated_capacity
                total_utilized += allocation.utilized_capacity
                
            except Exception as e:
                logger.warning(f"Error calculating allocation for project {association.project_workstream.project_key}: {str(e)}")
                continue
        
        return {
            "allocations": allocations,
            "summary": {
                "total_capacity": total_capacity,
                "total_utilized": total_utilized,
                "utilization_percentage": (total_utilized / total_capacity * 100) if total_capacity > 0 else 0.0,
                "projects_count": len(allocations)
            }
        }
    
    async def get_project_rankings(
        self,
        board_id: int,
        ranking_criteria: ProjectRankingCriteria,
        sprint_id: Optional[int] = None,
        limit: int = 20
    ) -> List[ProjectRanking]:
        """Get project rankings based on specified criteria."""
        logger.info(f"Generating project rankings for board {board_id} by {ranking_criteria}")
        
        # Get target sprint
        if sprint_id:
            sprint = await self.get_sprint(sprint_id)
        else:
            sprint = await self._get_active_sprint_for_board(board_id)
        
        if not sprint:
            raise NotFoundError(f"No active sprint found for meta-board {board_id}")
        
        # Get project associations
        project_associations = await self._get_project_sprint_associations(sprint.id)
        
        # Calculate ranking scores
        project_scores = []
        for association in project_associations:
            try:
                score = await self._calculate_ranking_score(
                    association.project_workstream,
                    association,
                    sprint,
                    ranking_criteria
                )
                
                project_scores.append({
                    'project': association.project_workstream,
                    'score': score
                })
                
            except Exception as e:
                logger.warning(f"Error calculating ranking score for project {association.project_workstream.project_key}: {str(e)}")
                continue
        
        # Sort by score (descending for most criteria)
        reverse_sort = ranking_criteria != ProjectRankingCriteria.RISK_SCORE  # Lower risk is better
        project_scores.sort(key=lambda x: x['score'], reverse=reverse_sort)
        
        # Create rankings
        rankings = []
        for i, item in enumerate(project_scores[:limit]):
            ranking = ProjectRanking(
                project_key=item['project'].project_key,
                project_name=item['project'].project_name,
                rank=i + 1,
                score=item['score'],
                ranking_criteria=ranking_criteria,
                justification=self._get_ranking_justification(ranking_criteria, item['score'])
            )
            rankings.append(ranking)
        
        return rankings
    
    async def get_portfolio_health_summary(
        self,
        board_id: int,
        sprint_id: Optional[int] = None,
        include_trends: bool = True
    ) -> Dict[str, Any]:
        """Get portfolio health summary with risk indicators."""
        logger.info(f"Generating health summary for board {board_id}")
        
        # Get portfolio data
        portfolio = await self.get_project_portfolio(board_id, sprint_id)
        
        # Calculate risk metrics
        high_risk_projects = [p for p in portfolio.projects if p.health_status in [ProjectHealthStatus.AT_RISK, ProjectHealthStatus.BEHIND]]
        blocked_projects = [p for p in portfolio.projects if p.health_status == ProjectHealthStatus.BLOCKED]
        
        # Calculate velocity trends if requested
        trends = {}
        if include_trends:
            trends = await self._calculate_portfolio_trends(board_id, sprint_id)
        
        return {
            "overall_health": "healthy" if len(high_risk_projects) == 0 else "at_risk" if len(high_risk_projects) < len(portfolio.projects) * 0.3 else "critical",
            "risk_summary": {
                "high_risk_projects": len(high_risk_projects),
                "blocked_projects": len(blocked_projects),
                "total_projects": len(portfolio.projects),
                "risk_percentage": len(high_risk_projects) / len(portfolio.projects) * 100 if portfolio.projects else 0
            },
            "completion_summary": {
                "overall_completion": portfolio.summary.overall_completion_percentage,
                "projects_on_track": portfolio.summary.projects_on_track,
                "estimated_completion": None  # Could be enhanced with actual forecasting
            },
            "capacity_summary": {
                "utilization": portfolio.summary.capacity_utilization_percentage,
                "total_capacity": portfolio.summary.total_team_capacity,
                "status": "normal" if portfolio.summary.capacity_utilization_percentage <= 100 else "over_capacity"
            },
            "trends": trends if include_trends else {}
        }
    
    # ========== HELPER METHODS FOR PORTFOLIO FUNCTIONALITY ==========
    
    async def _get_active_sprint_for_board(self, board_id: int) -> Optional[Sprint]:
        """Get the active sprint for a given board."""
        query = select(Sprint).where(
            and_(
                Sprint.board_id == board_id,
                Sprint.state == "active"
            )
        ).order_by(desc(Sprint.updated_at)).limit(1)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_project_sprint_associations(self, sprint_id: int) -> List[ProjectSprintAssociation]:
        """Get project associations for a sprint."""
        query = select(ProjectSprintAssociation).where(
            and_(
                ProjectSprintAssociation.sprint_id == sprint_id,
                ProjectSprintAssociation.is_active == True
            )
        ).options(
            selectinload(ProjectSprintAssociation.project_workstream)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def _calculate_project_metrics(
        self,
        project: ProjectWorkstream,
        association: ProjectSprintAssociation,
        sprint: Sprint
    ) -> ProjectMetrics:
        """Calculate comprehensive metrics for a project within sprint context."""
        # Get JIRA data for this project within the sprint
        jira_service = JiraService(self.db)
        
        try:
            # Get sprint issues filtered by project
            issues = await jira_service.get_sprint_issues(
                sprint.jira_sprint_id,
                jql_filter=f"project = {project.project_key}"
            )
        except Exception as e:
            logger.warning(f"Error fetching JIRA issues for project {project.project_key}: {str(e)}")
            issues = []
        
        # Calculate basic metrics
        total_issues = len(issues)
        completed_issues = len([i for i in issues if i.get('fields', {}).get('status', {}).get('name', '').lower() in ['done', 'closed', 'resolved']])
        in_progress_issues = len([i for i in issues if 'progress' in i.get('fields', {}).get('status', {}).get('name', '').lower()])
        blocked_issues = len([i for i in issues if 'blocked' in str(i.get('fields', {})).lower()])
        
        # Calculate story points
        total_story_points = sum(self._extract_story_points(issue) for issue in issues)
        completed_story_points = sum(
            self._extract_story_points(issue) for issue in issues 
            if issue.get('fields', {}).get('status', {}).get('name', '').lower() in ['done', 'closed', 'resolved']
        )
        in_progress_story_points = sum(
            self._extract_story_points(issue) for issue in issues 
            if 'progress' in issue.get('fields', {}).get('status', {}).get('name', '').lower()
        )
        
        # Calculate completion percentage
        completion_percentage = (completed_story_points / total_story_points * 100) if total_story_points > 0 else 0.0
        
        # Determine health status
        health_status = ProjectHealthStatus.ON_TRACK
        risk_score = 0.0
        
        if blocked_issues > 0:
            health_status = ProjectHealthStatus.BLOCKED
            risk_score = 80.0
        elif completion_percentage < 25.0 and total_issues > 0:
            health_status = ProjectHealthStatus.BEHIND
            risk_score = 60.0
        elif completion_percentage < 50.0 and blocked_issues > total_issues * 0.2:
            health_status = ProjectHealthStatus.AT_RISK
            risk_score = 40.0
        else:
            risk_score = max(0.0, 100.0 - completion_percentage)
        
        # Calculate velocity (simplified)
        velocity = completed_story_points / max(1, (datetime.now(timezone.utc) - sprint.start_date).days) if sprint.start_date else None
        
        return ProjectMetrics(
            project_key=project.project_key,
            project_name=project.project_name,
            total_issues=total_issues,
            completed_issues=completed_issues,
            in_progress_issues=in_progress_issues,
            blocked_issues=blocked_issues,
            total_story_points=total_story_points,
            completed_story_points=completed_story_points,
            in_progress_story_points=in_progress_story_points,
            completion_percentage=completion_percentage,
            velocity=velocity,
            health_status=health_status,
            risk_score=risk_score,
            priority=ProjectPriority.MEDIUM,  # Could be enhanced with actual priority mapping
            team_allocation_percentage=association.expected_story_points / total_story_points * 100 if total_story_points > 0 else None,
            capacity_utilization=association.actual_story_points / association.expected_story_points * 100 if association.expected_story_points and association.expected_story_points > 0 else None
        )
    
    def _matches_filters(self, metrics: ProjectMetrics, filters: ProjectPortfolioFilters) -> bool:
        """Check if project metrics match the provided filters."""
        if filters.project_keys and metrics.project_key not in filters.project_keys:
            return False
        
        if filters.priority and metrics.priority not in filters.priority:
            return False
        
        if filters.health_status and metrics.health_status not in filters.health_status:
            return False
        
        if filters.min_completion_percentage is not None and metrics.completion_percentage < filters.min_completion_percentage:
            return False
        
        if filters.max_completion_percentage is not None and metrics.completion_percentage > filters.max_completion_percentage:
            return False
        
        if not filters.include_completed and metrics.completion_percentage >= 100.0:
            return False
        
        if not filters.include_blocked and metrics.health_status == ProjectHealthStatus.BLOCKED:
            return False
        
        return True
    
    def _update_summary_metrics(self, summary: Dict[str, Any], metrics: ProjectMetrics) -> None:
        """Update summary metrics with project data."""
        summary['total_projects'] += 1
        summary['total_story_points'] += metrics.total_story_points
        summary['completed_story_points'] += metrics.completed_story_points
        summary['risk_scores'].append(metrics.risk_score)
        
        if metrics.completion_percentage >= 100.0:
            summary['completed_projects'] += 1
        elif metrics.health_status == ProjectHealthStatus.BLOCKED:
            summary['blocked_projects'] += 1
        else:
            summary['active_projects'] += 1
        
        if metrics.health_status == ProjectHealthStatus.ON_TRACK:
            summary['projects_on_track'] += 1
        elif metrics.health_status == ProjectHealthStatus.AT_RISK:
            summary['projects_at_risk'] += 1
        elif metrics.health_status == ProjectHealthStatus.BEHIND:
            summary['projects_behind'] += 1
    
    async def _calculate_health_indicators(self, project_metrics: List[ProjectMetrics], sprint: Sprint) -> List[SprintHealthIndicator]:
        """Calculate health indicators for the portfolio."""
        if not project_metrics:
            return []
        
        indicators = []
        
        # Overall completion indicator
        avg_completion = sum(p.completion_percentage for p in project_metrics) / len(project_metrics)
        indicators.append(SprintHealthIndicator(
            metric_name="Overall Completion",
            current_value=avg_completion,
            target_value=75.0,
            status="good" if avg_completion >= 75.0 else "warning" if avg_completion >= 50.0 else "critical",
            trend="stable",  # Could be enhanced with historical data
            details=f"Average completion across {len(project_metrics)} projects"
        ))
        
        # Risk indicator
        avg_risk = sum(p.risk_score for p in project_metrics) / len(project_metrics)
        indicators.append(SprintHealthIndicator(
            metric_name="Portfolio Risk",
            current_value=avg_risk,
            target_value=25.0,
            status="good" if avg_risk <= 25.0 else "warning" if avg_risk <= 50.0 else "critical",
            trend="stable",
            details=f"Average risk score across portfolio"
        ))
        
        # Velocity indicator
        velocities = [p.velocity for p in project_metrics if p.velocity is not None]
        if velocities:
            avg_velocity = sum(velocities) / len(velocities)
            indicators.append(SprintHealthIndicator(
                metric_name="Portfolio Velocity",
                current_value=avg_velocity,
                target_value=None,
                status="good",  # Could be enhanced with velocity targets
                trend="stable",
                details=f"Average velocity: {avg_velocity:.1f} points/day"
            ))
        
        return indicators
    
    def _calculate_overall_completion(self, summary: Dict[str, Any]) -> float:
        """Calculate overall completion percentage."""
        if summary['total_story_points'] > 0:
            return summary['completed_story_points'] / summary['total_story_points'] * 100
        return 0.0
    
    def _create_empty_portfolio_response(self, board_id: int, sprint: Sprint) -> ProjectPortfolioResponse:
        """Create empty portfolio response when no projects found."""
        summary = ProjectPortfolioSummary(
            meta_board_id=board_id,
            meta_board_name=f"Meta-board {board_id}",
            sprint_id=sprint.id,
            sprint_name=sprint.name,
            last_updated=datetime.now(timezone.utc)
        )
        
        return ProjectPortfolioResponse(
            summary=summary,
            projects=[],
            health_indicators=[],
            last_sync=datetime.now(timezone.utc),
            data_freshness="current"
        )
    
    async def _calculate_project_forecast(
        self,
        project: ProjectWorkstream,
        association: ProjectSprintAssociation,
        sprint: Sprint,
        confidence_threshold: float
    ) -> ProjectCompletionForecast:
        """Calculate completion forecast for a project."""
        # Get current metrics
        metrics = await self._calculate_project_metrics(project, association, sprint)
        
        # Simple velocity-based forecasting
        remaining_points = metrics.total_story_points - metrics.completed_story_points
        
        confidence = 0.8  # Default confidence
        estimated_completion = None
        risk_factors = []
        
        if metrics.velocity and metrics.velocity > 0:
            days_remaining = remaining_points / metrics.velocity
            estimated_completion = datetime.now(timezone.utc) + timedelta(days=days_remaining)
            
            # Adjust confidence based on various factors
            if metrics.blocked_issues > 0:
                confidence *= 0.7
                risk_factors.append("Blocked issues present")
            
            if metrics.health_status == ProjectHealthStatus.BEHIND:
                confidence *= 0.6
                risk_factors.append("Project behind schedule")
        else:
            risk_factors.append("No velocity data available")
            confidence = 0.3
        
        return ProjectCompletionForecast(
            project_key=project.project_key,
            project_name=project.project_name,
            current_velocity=metrics.velocity,
            remaining_story_points=remaining_points,
            estimated_completion_date=estimated_completion,
            confidence_level=confidence * 100,
            risk_factors=risk_factors,
            scenarios={
                "best_case": estimated_completion - timedelta(days=2) if estimated_completion else None,
                "worst_case": estimated_completion + timedelta(days=5) if estimated_completion else None,
                "likely": estimated_completion
            }
        )
    
    async def _calculate_resource_allocation(
        self,
        project: ProjectWorkstream,
        association: ProjectSprintAssociation,
        sprint: Sprint,
        include_discipline_breakdown: bool
    ) -> ResourceAllocation:
        """Calculate resource allocation for a project."""
        # Get team allocation data (simplified)
        allocated_capacity = association.expected_story_points or 0.0
        utilized_capacity = association.actual_story_points or 0.0
        
        utilization_percentage = (utilized_capacity / allocated_capacity * 100) if allocated_capacity > 0 else 0.0
        
        capacity_status = "normal"
        if utilization_percentage > 110:
            capacity_status = "over"
        elif utilization_percentage < 70:
            capacity_status = "under"
        
        disciplines = []
        if include_discipline_breakdown:
            # Could be enhanced with actual discipline data from JIRA
            disciplines = ["Development", "QA", "Design"]  # Placeholder
        
        return ResourceAllocation(
            project_key=project.project_key,
            project_name=project.project_name,
            allocated_capacity=allocated_capacity,
            utilized_capacity=utilized_capacity,
            utilization_percentage=utilization_percentage,
            team_members_assigned=3,  # Placeholder - could be enhanced
            disciplines_involved=disciplines,
            capacity_status=capacity_status
        )
    
    async def _calculate_ranking_score(
        self,
        project: ProjectWorkstream,
        association: ProjectSprintAssociation,
        sprint: Sprint,
        criteria: ProjectRankingCriteria
    ) -> float:
        """Calculate ranking score based on criteria."""
        metrics = await self._calculate_project_metrics(project, association, sprint)
        
        if criteria == ProjectRankingCriteria.PRIORITY:
            # Convert priority to numeric score
            priority_scores = {
                ProjectPriority.CRITICAL: 100.0,
                ProjectPriority.HIGH: 75.0,
                ProjectPriority.MEDIUM: 50.0,
                ProjectPriority.LOW: 25.0
            }
            return priority_scores.get(metrics.priority, 50.0)
        
        elif criteria == ProjectRankingCriteria.COMPLETION:
            return metrics.completion_percentage
        
        elif criteria == ProjectRankingCriteria.RISK_SCORE:
            return metrics.risk_score
        
        elif criteria == ProjectRankingCriteria.VELOCITY:
            return metrics.velocity or 0.0
        
        elif criteria == ProjectRankingCriteria.CAPACITY_UTILIZATION:
            return metrics.capacity_utilization or 0.0
        
        return 0.0
    
    def _get_ranking_justification(self, criteria: ProjectRankingCriteria, score: float) -> str:
        """Get justification text for ranking."""
        if criteria == ProjectRankingCriteria.PRIORITY:
            return f"Priority score: {score:.1f}/100"
        elif criteria == ProjectRankingCriteria.COMPLETION:
            return f"Completion: {score:.1f}%"
        elif criteria == ProjectRankingCriteria.RISK_SCORE:
            return f"Risk score: {score:.1f}/100 (lower is better)"
        elif criteria == ProjectRankingCriteria.VELOCITY:
            return f"Velocity: {score:.1f} points/day"
        elif criteria == ProjectRankingCriteria.CAPACITY_UTILIZATION:
            return f"Capacity utilization: {score:.1f}%"
        return f"Score: {score:.1f}"
    
    async def _calculate_portfolio_trends(self, board_id: int, sprint_id: Optional[int]) -> Dict[str, Any]:
        """Calculate portfolio trends (placeholder for future enhancement)."""
        # This could be enhanced with historical data analysis
        return {
            "velocity_trend": "stable",
            "completion_trend": "improving",
            "risk_trend": "stable",
            "note": "Trend analysis requires historical data"
        }
    
    # ========== ENHANCED PROJECT PROGRESS REPORTING METHODS ==========
    
    async def calculate_project_velocity_with_history(
        self,
        project_key: str,
        sprint_count: int = 5,
        include_current: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate project velocity using historical sprint data with advanced analytics.
        
        Args:
            project_key: Project key to analyze
            sprint_count: Number of historical sprints to analyze
            include_current: Whether to include current/active sprint data
            
        Returns:
            Comprehensive velocity analysis with trends and predictions
        """
        logger.info(f"Calculating historical velocity for project {project_key}")
        
        # Get project workstream
        query = select(ProjectWorkstream).where(ProjectWorkstream.project_key == project_key)
        result = await self.db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise NotFoundError(f"Project {project_key} not found")
        
        # Get historical sprint associations for this project
        associations_query = select(ProjectSprintAssociation).join(Sprint).where(
            and_(
                ProjectSprintAssociation.project_workstream_id == project.id,
                ProjectSprintAssociation.is_active == True,
                Sprint.state.in_(["closed", "active"] if include_current else ["closed"])
            )
        ).options(
            selectinload(ProjectSprintAssociation.sprint)
        ).order_by(desc(Sprint.end_date)).limit(sprint_count)
        
        result = await self.db.execute(associations_query)
        associations = result.scalars().all()
        
        if not associations:
            return {
                "project_key": project_key,
                "analysis_period": f"Last {sprint_count} sprints",
                "velocity_data": [],
                "trends": {
                    "average_velocity": 0.0,
                    "velocity_trend": "insufficient_data",
                    "trend_direction": "unknown",
                    "consistency_score": 0.0
                },
                "forecasting": {
                    "predicted_next_sprint": 0.0,
                    "confidence_interval": {"low": 0.0, "high": 0.0}
                },
                "note": "No historical sprint data available"
            }
        
        # Calculate velocity for each sprint
        velocity_data = []
        jira_service = JiraService(self.db)
        
        for association in associations:
            sprint = association.sprint
            try:
                # Get sprint issues for this project
                issues = await jira_service.get_sprint_issues(
                    sprint.jira_sprint_id,
                    jql_filter=f"project = {project_key}"
                )
                
                # Calculate completed story points
                completed_points = sum(
                    self._extract_story_points(issue) for issue in issues 
                    if issue.get('fields', {}).get('status', {}).get('name', '').lower() in ['done', 'closed', 'resolved']
                )
                
                # Calculate sprint duration in days
                duration_days = 1
                if sprint.start_date and sprint.end_date:
                    duration_days = max(1, (sprint.end_date - sprint.start_date).days)
                elif sprint.start_date and sprint.state == "active":
                    duration_days = max(1, (datetime.now(timezone.utc) - sprint.start_date).days)
                
                velocity = completed_points / duration_days
                
                velocity_data.append({
                    "sprint_id": sprint.id,
                    "sprint_name": sprint.name,
                    "start_date": sprint.start_date.isoformat() if sprint.start_date else None,
                    "end_date": sprint.end_date.isoformat() if sprint.end_date else None,
                    "duration_days": duration_days,
                    "total_issues": len(issues),
                    "completed_story_points": completed_points,
                    "velocity": velocity,
                    "sprint_state": sprint.state
                })
                
            except Exception as e:
                logger.warning(f"Error calculating velocity for sprint {sprint.id}: {str(e)}")
                continue
        
        # Calculate trends and statistics
        velocities = [data["velocity"] for data in velocity_data if data["velocity"] > 0]
        
        if not velocities:
            return {
                "project_key": project_key,
                "analysis_period": f"Last {sprint_count} sprints",
                "velocity_data": velocity_data,
                "trends": {
                    "average_velocity": 0.0,
                    "velocity_trend": "no_data",
                    "trend_direction": "unknown",
                    "consistency_score": 0.0
                },
                "forecasting": {
                    "predicted_next_sprint": 0.0,
                    "confidence_interval": {"low": 0.0, "high": 0.0}
                }
            }
        
        # Statistical analysis
        avg_velocity = sum(velocities) / len(velocities)
        velocity_std = (sum((v - avg_velocity) ** 2 for v in velocities) / len(velocities)) ** 0.5
        consistency_score = max(0.0, 100.0 - (velocity_std / avg_velocity * 100)) if avg_velocity > 0 else 0.0
        
        # Trend analysis (simple linear regression)
        trend_direction = "stable"
        if len(velocities) >= 3:
            # Calculate trend using last 3 points vs first 3 points
            recent_avg = sum(velocities[:3]) / 3 if len(velocities) >= 3 else avg_velocity
            older_avg = sum(velocities[-3:]) / 3 if len(velocities) >= 3 else avg_velocity
            
            if recent_avg > older_avg * 1.1:
                trend_direction = "improving"
            elif recent_avg < older_avg * 0.9:
                trend_direction = "declining"
        
        # Forecasting with confidence intervals
        predicted_velocity = avg_velocity
        confidence_low = max(0.0, avg_velocity - velocity_std)
        confidence_high = avg_velocity + velocity_std
        
        return {
            "project_key": project_key,
            "project_name": project.project_name,
            "analysis_period": f"Last {len(velocity_data)} sprints",
            "velocity_data": velocity_data,
            "trends": {
                "average_velocity": round(avg_velocity, 2),
                "velocity_standard_deviation": round(velocity_std, 2),
                "velocity_trend": trend_direction,
                "trend_direction": trend_direction,
                "consistency_score": round(consistency_score, 1)
            },
            "forecasting": {
                "predicted_next_sprint": round(predicted_velocity, 2),
                "confidence_interval": {
                    "low": round(confidence_low, 2),
                    "high": round(confidence_high, 2)
                }
            },
            "statistics": {
                "min_velocity": round(min(velocities), 2),
                "max_velocity": round(max(velocities), 2),
                "median_velocity": round(sorted(velocities)[len(velocities)//2], 2),
                "total_sprints_analyzed": len(velocity_data)
            }
        }
    
    async def monte_carlo_completion_forecast(
        self,
        project_key: str,
        remaining_story_points: float,
        simulation_runs: int = 1000,
        confidence_levels: List[float] = [0.5, 0.8, 0.95]
    ) -> Dict[str, Any]:
        """
        Perform Monte Carlo simulation for project completion forecasting.
        
        Args:
            project_key: Project key to forecast
            remaining_story_points: Remaining work in story points
            simulation_runs: Number of simulation iterations
            confidence_levels: Confidence levels for forecasting intervals
            
        Returns:
            Monte Carlo simulation results with completion probabilities
        """
        logger.info(f"Running Monte Carlo simulation for project {project_key}")
        
        # Get historical velocity data
        velocity_data = await self.calculate_project_velocity_with_history(project_key)
        
        if not velocity_data["velocity_data"]:
            return {
                "project_key": project_key,
                "error": "Insufficient historical data for Monte Carlo simulation",
                "remaining_story_points": remaining_story_points
            }
        
        # Extract velocity statistics
        velocities = [data["velocity"] for data in velocity_data["velocity_data"] if data["velocity"] > 0]
        
        if not velocities:
            return {
                "project_key": project_key,
                "error": "No positive velocity data available",
                "remaining_story_points": remaining_story_points
            }
        
        import random
        import statistics
        
        # Prepare simulation parameters
        avg_velocity = statistics.mean(velocities)
        velocity_std = statistics.stdev(velocities) if len(velocities) > 1 else avg_velocity * 0.2
        
        # Run Monte Carlo simulation
        completion_days = []
        
        for _ in range(simulation_runs):
            # Sample velocity from normal distribution (constrained to positive values)
            simulated_velocity = max(0.1, random.gauss(avg_velocity, velocity_std))
            
            # Calculate days to completion
            days_to_complete = remaining_story_points / simulated_velocity
            completion_days.append(days_to_complete)
        
        # Sort results for percentile calculations
        completion_days.sort()
        
        # Calculate confidence intervals
        forecasts = {}
        for confidence in confidence_levels:
            percentile_index = int(confidence * len(completion_days))
            forecasts[f"p{int(confidence * 100)}"] = {
                "days": round(completion_days[percentile_index], 1),
                "completion_date": (datetime.now(timezone.utc) + timedelta(days=completion_days[percentile_index])).isoformat()
            }
        
        # Calculate statistics
        mean_days = statistics.mean(completion_days)
        median_days = statistics.median(completion_days)
        std_days = statistics.stdev(completion_days)
        
        # Risk analysis
        risk_threshold_days = mean_days * 1.5  # 50% over expected
        risk_probability = sum(1 for days in completion_days if days > risk_threshold_days) / len(completion_days)
        
        return {
            "project_key": project_key,
            "simulation_parameters": {
                "remaining_story_points": remaining_story_points,
                "simulation_runs": simulation_runs,
                "historical_velocity_avg": round(avg_velocity, 2),
                "historical_velocity_std": round(velocity_std, 2)
            },
            "forecasts": forecasts,
            "statistics": {
                "mean_completion_days": round(mean_days, 1),
                "median_completion_days": round(median_days, 1),
                "standard_deviation_days": round(std_days, 1),
                "earliest_completion": round(min(completion_days), 1),
                "latest_completion": round(max(completion_days), 1)
            },
            "risk_analysis": {
                "probability_of_delay": round(risk_probability * 100, 1),
                "risk_threshold_days": round(risk_threshold_days, 1),
                "risk_level": "high" if risk_probability > 0.3 else "medium" if risk_probability > 0.1 else "low"
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def generate_project_burndown_data(
        self,
        project_key: str,
        sprint_id: int,
        include_burnup: bool = True
    ) -> Dict[str, Any]:
        """
        Generate project-level burndown and burnup chart data within sprint context.
        
        Args:
            project_key: Project key to analyze
            sprint_id: Sprint ID for context
            include_burnup: Whether to include burnup chart data
            
        Returns:
            Burndown and burnup chart data with daily tracking
        """
        logger.info(f"Generating burndown/burnup data for project {project_key} in sprint {sprint_id}")
        
        # Get sprint and project
        sprint = await self.get_sprint(sprint_id)
        if not sprint:
            raise NotFoundError(f"Sprint {sprint_id} not found")
        
        # Get project workstream
        query = select(ProjectWorkstream).where(ProjectWorkstream.project_key == project_key)
        result = await self.db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise NotFoundError(f"Project {project_key} not found")
        
        # Get project association for this sprint
        association_query = select(ProjectSprintAssociation).where(
            and_(
                ProjectSprintAssociation.sprint_id == sprint_id,
                ProjectSprintAssociation.project_workstream == project,
                ProjectSprintAssociation.is_active == True
            )
        )
        result = await self.db.execute(association_query)
        association = result.scalar_one_or_none()
        
        if not association:
            raise NotFoundError(f"Project {project_key} not associated with sprint {sprint_id}")
        
        # Get historical metrics for this project-sprint combination
        metrics_query = select(ProjectSprintMetrics).where(
            and_(
                ProjectSprintMetrics.sprint_id == sprint_id,
                ProjectSprintMetrics.project_workstream_id == project.id
            )
        ).order_by(ProjectSprintMetrics.metrics_date)
        
        result = await self.db.execute(metrics_query)
        historical_metrics = result.scalars().all()
        
        # If no historical data, get current state
        if not historical_metrics:
            jira_service = JiraService(self.db)
            try:
                issues = await jira_service.get_sprint_issues(
                    sprint.jira_sprint_id,
                    jql_filter=f"project = {project_key}"
                )
                
                total_points = sum(self._extract_story_points(issue) for issue in issues)
                completed_points = sum(
                    self._extract_story_points(issue) for issue in issues 
                    if issue.get('fields', {}).get('status', {}).get('name', '').lower() in ['done', 'closed', 'resolved']
                )
                
                # Create current state data point
                current_data = {
                    "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "total_story_points": total_points,
                    "completed_story_points": completed_points,
                    "remaining_story_points": total_points - completed_points,
                    "total_issues": len(issues),
                    "completed_issues": len([i for i in issues if i.get('fields', {}).get('status', {}).get('name', '').lower() in ['done', 'closed', 'resolved']])
                }
                
                return {
                    "project_key": project_key,
                    "sprint_id": sprint_id,
                    "sprint_name": sprint.name,
                    "burndown_data": [current_data],
                    "burnup_data": [current_data] if include_burnup else None,
                    "summary": {
                        "sprint_start": sprint.start_date.isoformat() if sprint.start_date else None,
                        "sprint_end": sprint.end_date.isoformat() if sprint.end_date else None,
                        "current_completion": round((completed_points / total_points * 100) if total_points > 0 else 0, 1),
                        "data_points": 1
                    },
                    "note": "Limited historical data - showing current state only"
                }
            except Exception as e:
                logger.error(f"Error fetching current sprint data: {str(e)}")
                raise
        
        # Process historical metrics into chart data
        burndown_data = []
        burnup_data = []
        
        for metric in historical_metrics:
            data_point = {
                "date": metric.metrics_date.strftime("%Y-%m-%d"),
                "total_story_points": metric.total_story_points,
                "completed_story_points": metric.completed_story_points,
                "remaining_story_points": metric.total_story_points - metric.completed_story_points,
                "total_issues": metric.total_issues,
                "completed_issues": metric.completed_issues,
                "in_progress_issues": metric.in_progress_issues,
                "blocked_issues": metric.blocked_issues,
                "velocity": metric.velocity,
                "completion_percentage": metric.completion_percentage
            }
            
            burndown_data.append(data_point)
            
            if include_burnup:
                burnup_data.append({
                    **data_point,
                    "cumulative_completed": metric.completed_story_points,
                    "scope_added": metric.scope_added_points,
                    "scope_removed": metric.scope_removed_points,
                    "net_scope_change": metric.scope_added_points - metric.scope_removed_points
                })
        
        # Calculate ideal burndown line
        if sprint.start_date and sprint.end_date and burndown_data:
            sprint_duration = (sprint.end_date - sprint.start_date).days
            initial_points = burndown_data[0]["total_story_points"]
            
            ideal_burndown = []
            for i in range(sprint_duration + 1):
                date = sprint.start_date + timedelta(days=i)
                remaining_ideal = initial_points * (1 - i / sprint_duration)
                ideal_burndown.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "ideal_remaining": max(0, remaining_ideal)
                })
        else:
            ideal_burndown = []
        
        # Calculate trend analysis
        trend_analysis = {}
        if len(burndown_data) >= 3:
            recent_velocity = []
            for i in range(1, min(4, len(burndown_data))):
                current = burndown_data[-i]
                previous = burndown_data[-i-1]
                daily_completed = current["completed_story_points"] - previous["completed_story_points"]
                recent_velocity.append(daily_completed)
            
            avg_recent_velocity = sum(recent_velocity) / len(recent_velocity) if recent_velocity else 0
            remaining_points = burndown_data[-1]["remaining_story_points"]
            
            trend_analysis = {
                "recent_velocity": round(avg_recent_velocity, 2),
                "projected_completion_days": round(remaining_points / avg_recent_velocity, 1) if avg_recent_velocity > 0 else None,
                "trend": "on_track" if avg_recent_velocity > 0 else "at_risk",
                "completion_probability": min(100, max(0, (avg_recent_velocity * (sprint.end_date - datetime.now(timezone.utc)).days / remaining_points * 100))) if avg_recent_velocity > 0 and remaining_points > 0 and sprint.end_date else None
            }
        
        return {
            "project_key": project_key,
            "project_name": project.project_name,
            "sprint_id": sprint_id,
            "sprint_name": sprint.name,
            "burndown_data": burndown_data,
            "burnup_data": burnup_data if include_burnup else None,
            "ideal_burndown": ideal_burndown,
            "trend_analysis": trend_analysis,
            "summary": {
                "sprint_start": sprint.start_date.isoformat() if sprint.start_date else None,
                "sprint_end": sprint.end_date.isoformat() if sprint.end_date else None,
                "current_completion": burndown_data[-1]["completion_percentage"] if burndown_data else 0,
                "data_points": len(burndown_data),
                "total_scope_changes": len([d for d in burnup_data if d.get("net_scope_change", 0) != 0]) if burnup_data else 0
            }
        }
    
    async def assess_project_risks(
        self,
        project_key: str,
        sprint_id: Optional[int] = None,
        include_capacity_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Assess project risks based on velocity trends and capacity constraints.
        
        Args:
            project_key: Project key to analyze
            sprint_id: Optional specific sprint, defaults to active sprint
            include_capacity_analysis: Whether to include team capacity analysis
            
        Returns:
            Comprehensive risk assessment with mitigation recommendations
        """
        logger.info(f"Assessing project risks for {project_key}")
        
        # Get project
        query = select(ProjectWorkstream).where(ProjectWorkstream.project_key == project_key)
        result = await self.db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise NotFoundError(f"Project {project_key} not found")
        
        # Get target sprint
        if sprint_id:
            sprint = await self.get_sprint(sprint_id)
        else:
            # Get active sprint for this project
            sprint = await self._get_active_sprint_for_project(project_key)
        
        if not sprint:
            return {
                "project_key": project_key,
                "error": "No active sprint found for project",
                "risk_level": "unknown"
            }
        
        # Initialize risk assessment
        risk_factors = []
        risk_score = 0.0
        
        # 1. Velocity Risk Analysis
        try:
            velocity_data = await self.calculate_project_velocity_with_history(project_key)
            
            if velocity_data["trends"]["consistency_score"] < 50:
                risk_factors.append({
                    "category": "velocity",
                    "risk": "inconsistent_velocity",
                    "severity": "medium",
                    "description": f"Velocity consistency score is {velocity_data['trends']['consistency_score']:.1f}% (below 50%)",
                    "impact": 20,
                    "mitigation": "Review sprint planning process and work breakdown consistency"
                })
                risk_score += 20
            
            if velocity_data["trends"]["trend_direction"] == "declining":
                risk_factors.append({
                    "category": "velocity",
                    "risk": "declining_velocity",
                    "severity": "high",
                    "description": "Project velocity is declining over recent sprints",
                    "impact": 30,
                    "mitigation": "Investigate blockers, technical debt, or resource allocation issues"
                })
                risk_score += 30
            
        except Exception as e:
            risk_factors.append({
                "category": "data",
                "risk": "insufficient_velocity_data",
                "severity": "medium",
                "description": "Cannot assess velocity trends due to insufficient data",
                "impact": 15,
                "mitigation": "Ensure consistent sprint tracking and data collection"
            })
            risk_score += 15
        
        # 2. Capacity Utilization Risk
        if include_capacity_analysis:
            try:
                # Get project association for capacity data
                association_query = select(ProjectSprintAssociation).where(
                    and_(
                        ProjectSprintAssociation.sprint_id == sprint.id,
                        ProjectSprintAssociation.project_workstream_id == project.id,
                        ProjectSprintAssociation.is_active == True
                    )
                )
                result = await self.db.execute(association_query)
                association = result.scalar_one_or_none()
                
                if association:
                    if association.expected_story_points and association.actual_story_points:
                        utilization = (association.actual_story_points / association.expected_story_points) * 100
                        
                        if utilization > 120:
                            risk_factors.append({
                                "category": "capacity",
                                "risk": "over_capacity",
                                "severity": "high",
                                "description": f"Team over-capacity at {utilization:.1f}% (expected: 100%)",
                                "impact": 35,
                                "mitigation": "Reduce scope or add resources to prevent burnout"
                            })
                            risk_score += 35
                        elif utilization < 60:
                            risk_factors.append({
                                "category": "capacity",
                                "risk": "under_utilization",
                                "severity": "low",
                                "description": f"Team under-utilized at {utilization:.1f}% (expected: 80-100%)",
                                "impact": 10,
                                "mitigation": "Consider adding scope or reallocating resources"
                            })
                            risk_score += 10
                
            except Exception as e:
                logger.warning(f"Error analyzing capacity: {str(e)}")
        
        # 3. Sprint Progress Risk
        try:
            # Get current project metrics for this sprint
            jira_service = JiraService(self.db)
            issues = await jira_service.get_sprint_issues(
                sprint.jira_sprint_id,
                jql_filter=f"project = {project_key}"
            )
            
            total_points = sum(self._extract_story_points(issue) for issue in issues)
            completed_points = sum(
                self._extract_story_points(issue) for issue in issues 
                if issue.get('fields', {}).get('status', {}).get('name', '').lower() in ['done', 'closed', 'resolved']
            )
            blocked_issues = len([i for i in issues if 'blocked' in str(i.get('fields', {})).lower()])
            
            completion_percentage = (completed_points / total_points * 100) if total_points > 0 else 0
            
            # Time-based risk assessment
            if sprint.start_date and sprint.end_date:
                total_days = (sprint.end_date - sprint.start_date).days
                elapsed_days = (datetime.now(timezone.utc) - sprint.start_date).days
                time_percentage = (elapsed_days / total_days * 100) if total_days > 0 else 0
                
                # Check if completion is lagging behind time
                if time_percentage > 50 and completion_percentage < time_percentage * 0.8:
                    risk_factors.append({
                        "category": "progress",
                        "risk": "behind_schedule",
                        "severity": "high",
                        "description": f"Project {completion_percentage:.1f}% complete vs {time_percentage:.1f}% time elapsed",
                        "impact": 25,
                        "mitigation": "Accelerate delivery or reduce scope to meet sprint goals"
                    })
                    risk_score += 25
            
            # Blocked work risk
            if blocked_issues > 0:
                blocked_percentage = (blocked_issues / len(issues) * 100) if issues else 0
                if blocked_percentage > 20:
                    risk_factors.append({
                        "category": "blockers",
                        "risk": "high_blocked_work",
                        "severity": "critical",
                        "description": f"{blocked_issues} issues blocked ({blocked_percentage:.1f}% of total work)",
                        "impact": 40,
                        "mitigation": "Prioritize unblocking work and escalate persistent blockers"
                    })
                    risk_score += 40
                elif blocked_issues > 0:
                    risk_factors.append({
                        "category": "blockers",
                        "risk": "some_blocked_work",
                        "severity": "medium",
                        "description": f"{blocked_issues} issues currently blocked",
                        "impact": 15,
                        "mitigation": "Monitor blocked work and ensure timely resolution"
                    })
                    risk_score += 15
                    
        except Exception as e:
            logger.warning(f"Error analyzing sprint progress: {str(e)}")
        
        # 4. Dependency Risk (placeholder for future enhancement)
        # This could be enhanced with actual dependency tracking
        
        # Determine overall risk level
        if risk_score >= 60:
            risk_level = "critical"
        elif risk_score >= 35:
            risk_level = "high"
        elif risk_score >= 15:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Generate recommendations
        recommendations = []
        if risk_score > 30:
            recommendations.append("Consider daily standups to address blockers quickly")
            recommendations.append("Review sprint scope and consider reducing commitment")
        if any(rf["category"] == "velocity" for rf in risk_factors):
            recommendations.append("Analyze velocity trends and identify improvement opportunities")
        if any(rf["category"] == "capacity" for rf in risk_factors):
            recommendations.append("Review team capacity allocation and adjust expectations")
        
        return {
            "project_key": project_key,
            "project_name": project.project_name,
            "sprint_id": sprint.id,
            "sprint_name": sprint.name,
            "risk_assessment": {
                "overall_risk_level": risk_level,
                "risk_score": round(risk_score, 1),
                "risk_factors_count": len(risk_factors),
                "critical_risks": len([rf for rf in risk_factors if rf["severity"] == "critical"]),
                "high_risks": len([rf for rf in risk_factors if rf["severity"] == "high"]),
                "medium_risks": len([rf for rf in risk_factors if rf["severity"] == "medium"]),
                "low_risks": len([rf for rf in risk_factors if rf["severity"] == "low"])
            },
            "risk_factors": risk_factors,
            "recommendations": recommendations,
            "assessment_date": datetime.now(timezone.utc).isoformat()
        }
    
    async def _get_active_sprint_for_project(self, project_key: str) -> Optional[Sprint]:
        """Get the active sprint for a given project."""
        query = select(Sprint).join(ProjectSprintAssociation).join(ProjectWorkstream).where(
            and_(
                ProjectWorkstream.project_key == project_key,
                ProjectSprintAssociation.is_active == True,
                Sprint.state == "active"
            )
        ).order_by(desc(Sprint.updated_at)).limit(1)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def track_project_milestones(
        self,
        project_key: str,
        sprint_id: Optional[int] = None,
        milestone_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Track project milestones within sprint context.
        
        Args:
            project_key: Project key to analyze
            sprint_id: Optional specific sprint, defaults to active sprint
            milestone_types: Optional filter for milestone types
            
        Returns:
            Project milestone tracking data with progress indicators
        """
        logger.info(f"Tracking milestones for project {project_key}")
        
        # Get project
        query = select(ProjectWorkstream).where(ProjectWorkstream.project_key == project_key)
        result = await self.db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise NotFoundError(f"Project {project_key} not found")
        
        # Get target sprint
        if sprint_id:
            sprint = await self.get_sprint(sprint_id)
        else:
            sprint = await self._get_active_sprint_for_project(project_key)
        
        if not sprint:
            return {
                "project_key": project_key,
                "error": "No active sprint found for project",
                "milestones": []
            }
        
        # Get JIRA issues that could represent milestones
        jira_service = JiraService(self.db)
        try:
            # Look for Epic-type issues or issues with milestone labels
            milestone_jql = f"project = {project_key} AND (type = Epic OR labels in (milestone, Milestone, MILESTONE))"
            milestone_issues = await jira_service.get_sprint_issues(
                sprint.jira_sprint_id,
                jql_filter=milestone_jql
            )
            
            # Also get all issues to calculate completion rates
            all_issues = await jira_service.get_sprint_issues(
                sprint.jira_sprint_id,
                jql_filter=f"project = {project_key}"
            )
            
        except Exception as e:
            logger.warning(f"Error fetching milestone data: {str(e)}")
            return {
                "project_key": project_key,
                "sprint_id": sprint.id,
                "error": f"Failed to fetch milestone data: {str(e)}",
                "milestones": []
            }
        
        milestones = []
        
        # Process milestone issues
        for issue in milestone_issues:
            fields = issue.get('fields', {})
            issue_type = fields.get('issuetype', {}).get('name', '').lower()
            
            # Skip if milestone type filter is specified and doesn't match
            if milestone_types and issue_type not in [mt.lower() for mt in milestone_types]:
                continue
            
            # Get milestone status
            status = fields.get('status', {})
            status_name = status.get('name', '').lower()
            status_category = status.get('statusCategory', {}).get('name', '').lower()
            
            # Calculate completion status
            is_completed = status_name in ['done', 'closed', 'resolved'] or status_category == 'done'
            is_blocked = 'blocked' in status_name or 'blocked' in str(fields).lower()
            
            # Get milestone dates
            due_date = fields.get('duedate')
            resolution_date = fields.get('resolutiondate')
            
            # Calculate related work (issues linked to this milestone)
            related_issues = []
            if issue_type == 'epic':
                # For epics, find issues in the same epic
                epic_link = fields.get('customfield_10014')  # Common epic link field
                if epic_link:
                    related_issues = [i for i in all_issues if i.get('fields', {}).get('customfield_10014') == epic_link]
            
            # Calculate progress metrics
            total_related = len(related_issues)
            completed_related = len([i for i in related_issues if i.get('fields', {}).get('status', {}).get('name', '').lower() in ['done', 'closed', 'resolved']])
            progress_percentage = (completed_related / total_related * 100) if total_related > 0 else (100 if is_completed else 0)
            
            # Determine milestone health
            health_status = "on_track"
            if is_blocked:
                health_status = "blocked"
            elif is_completed:
                health_status = "completed"
            elif due_date:
                from datetime import datetime, timezone
                try:
                    due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    days_until_due = (due_dt - datetime.now(timezone.utc)).days
                    if days_until_due < 0:
                        health_status = "overdue"
                    elif days_until_due < 3 and progress_percentage < 80:
                        health_status = "at_risk"
                except:
                    pass
            
            milestone = {
                "milestone_id": issue['key'],
                "title": fields.get('summary', ''),
                "type": issue_type,
                "status": status_name,
                "health_status": health_status,
                "progress_percentage": round(progress_percentage, 1),
                "is_completed": is_completed,
                "is_blocked": is_blocked,
                "due_date": due_date,
                "resolution_date": resolution_date,
                "related_work": {
                    "total_issues": total_related,
                    "completed_issues": completed_related,
                    "remaining_issues": total_related - completed_related
                },
                "story_points": self._extract_story_points(issue),
                "assignee": fields.get('assignee', {}).get('displayName') if fields.get('assignee') else None,
                "priority": fields.get('priority', {}).get('name', 'Medium'),
                "created_date": fields.get('created'),
                "last_updated": fields.get('updated')
            }
            
            milestones.append(milestone)
        
        # Calculate overall milestone metrics
        total_milestones = len(milestones)
        completed_milestones = len([m for m in milestones if m['is_completed']])
        blocked_milestones = len([m for m in milestones if m['is_blocked']])
        overdue_milestones = len([m for m in milestones if m['health_status'] == 'overdue'])
        at_risk_milestones = len([m for m in milestones if m['health_status'] == 'at_risk'])
        
        # Sort milestones by priority and due date
        priority_order = {'Highest': 0, 'High': 1, 'Medium': 2, 'Low': 3, 'Lowest': 4}
        milestones.sort(key=lambda m: (
            priority_order.get(m['priority'], 2),
            m['due_date'] or '9999-12-31',
            -m['progress_percentage']
        ))
        
        return {
            "project_key": project_key,
            "project_name": project.project_name,
            "sprint_id": sprint.id,
            "sprint_name": sprint.name,
            "milestone_summary": {
                "total_milestones": total_milestones,
                "completed_milestones": completed_milestones,
                "blocked_milestones": blocked_milestones,
                "overdue_milestones": overdue_milestones,
                "at_risk_milestones": at_risk_milestones,
                "on_track_milestones": total_milestones - completed_milestones - blocked_milestones - overdue_milestones - at_risk_milestones,
                "overall_progress": round((completed_milestones / total_milestones * 100) if total_milestones > 0 else 0, 1)
            },
            "milestones": milestones,
            "tracking_date": datetime.now(timezone.utc).isoformat()
        }
    
    async def analyze_project_dependencies(
        self,
        project_key: str,
        sprint_id: Optional[int] = None,
        include_impact_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze project dependencies and their impact on progress.
        
        Args:
            project_key: Project key to analyze
            sprint_id: Optional specific sprint, defaults to active sprint
            include_impact_analysis: Whether to include dependency impact analysis
            
        Returns:
            Project dependency analysis with impact assessment
        """
        logger.info(f"Analyzing dependencies for project {project_key}")
        
        # Get project
        query = select(ProjectWorkstream).where(ProjectWorkstream.project_key == project_key)
        result = await self.db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise NotFoundError(f"Project {project_key} not found")
        
        # Get target sprint
        if sprint_id:
            sprint = await self.get_sprint(sprint_id)
        else:
            sprint = await self._get_active_sprint_for_project(project_key)
        
        if not sprint:
            return {
                "project_key": project_key,
                "error": "No active sprint found for project",
                "dependencies": []
            }
        
        # Get JIRA issues for dependency analysis
        jira_service = JiraService(self.db)
        try:
            issues = await jira_service.get_sprint_issues(
                sprint.jira_sprint_id,
                jql_filter=f"project = {project_key}"
            )
        except Exception as e:
            logger.warning(f"Error fetching issues for dependency analysis: {str(e)}")
            return {
                "project_key": project_key,
                "sprint_id": sprint.id,
                "error": f"Failed to fetch issue data: {str(e)}",
                "dependencies": []
            }
        
        dependencies = []
        dependency_map = {}
        
        # Analyze issue links for dependencies
        for issue in issues:
            issue_key = issue['key']
            fields = issue.get('fields', {})
            issue_links = fields.get('issuelinks', [])
            
            # Process issue links
            for link in issue_links:
                link_type = link.get('type', {})
                link_name = link_type.get('name', '').lower()
                
                # Check for dependency-related link types
                if any(dep_type in link_name for dep_type in ['blocks', 'depends', 'relates', 'clones']):
                    # Determine direction and dependency type
                    if 'outwardIssue' in link:
                        # This issue depends on the outward issue
                        dependent_issue = issue_key
                        dependency_issue = link['outwardIssue']['key']
                        relationship = link_type.get('outward', 'depends on')
                    elif 'inwardIssue' in link:
                        # The inward issue depends on this issue
                        dependent_issue = link['inwardIssue']['key']
                        dependency_issue = issue_key
                        relationship = link_type.get('inward', 'is depended on by')
                    else:
                        continue
                    
                    # Get status of dependency
                    target_issue = link.get('outwardIssue') or link.get('inwardIssue')
                    if target_issue:
                        dep_status = target_issue.get('fields', {}).get('status', {}).get('name', 'Unknown')
                        dep_priority = target_issue.get('fields', {}).get('priority', {}).get('name', 'Medium')
                        dep_project = target_issue.get('fields', {}).get('project', {}).get('key', 'Unknown')
                        dep_assignee = target_issue.get('fields', {}).get('assignee', {}).get('displayName', 'Unassigned')
                        
                        # Determine dependency health
                        health_status = "healthy"
                        if 'blocked' in dep_status.lower():
                            health_status = "blocked"
                        elif dep_status.lower() in ['done', 'closed', 'resolved']:
                            health_status = "resolved"
                        elif dep_priority in ['Highest', 'High'] and dep_status.lower() not in ['in progress', 'done', 'closed', 'resolved']:
                            health_status = "at_risk"
                        
                        dependency = {
                            "dependent_issue": dependent_issue,
                            "dependency_issue": dependency_issue,
                            "relationship": relationship,
                            "dependency_type": link_name,
                            "dependency_status": dep_status,
                            "dependency_priority": dep_priority,
                            "dependency_project": dep_project,
                            "dependency_assignee": dep_assignee,
                            "health_status": health_status,
                            "is_external": dep_project != project_key,
                            "is_blocking": 'blocks' in link_name,
                            "impact_level": "high" if dep_priority in ['Highest', 'High'] else "medium" if dep_priority == 'Medium' else "low"
                        }
                        
                        dependencies.append(dependency)
                        
                        # Build dependency map for impact analysis
                        if dependent_issue not in dependency_map:
                            dependency_map[dependent_issue] = []
                        dependency_map[dependent_issue].append(dependency_issue)
        
        # Perform impact analysis if requested
        impact_analysis = {}
        if include_impact_analysis and dependencies:
            # Calculate dependency risks
            critical_deps = [d for d in dependencies if d['health_status'] in ['blocked', 'at_risk'] and d['impact_level'] == 'high']
            external_deps = [d for d in dependencies if d['is_external']]
            blocking_deps = [d for d in dependencies if d['is_blocking']]
            
            # Calculate dependency chains (simplified)
            max_chain_length = 0
            for issue_key in dependency_map:
                chain_length = len(dependency_map[issue_key])
                max_chain_length = max(max_chain_length, chain_length)
            
            # Risk scoring
            risk_score = 0
            risk_factors = []
            
            if critical_deps:
                risk_score += len(critical_deps) * 15
                risk_factors.append(f"{len(critical_deps)} critical dependencies at risk")
            
            if len(external_deps) > len(dependencies) * 0.3:
                risk_score += 20
                risk_factors.append(f"{len(external_deps)} external dependencies may be harder to control")
            
            if blocking_deps:
                risk_score += len(blocking_deps) * 10
                risk_factors.append(f"{len(blocking_deps)} dependencies are blocking other work")
            
            if max_chain_length > 3:
                risk_score += 15
                risk_factors.append(f"Complex dependency chains detected (max depth: {max_chain_length})")
            
            impact_analysis = {
                "overall_risk_score": min(100, risk_score),
                "risk_level": "critical" if risk_score >= 60 else "high" if risk_score >= 35 else "medium" if risk_score >= 15 else "low",
                "critical_dependencies": len(critical_deps),
                "external_dependencies": len(external_deps),
                "blocking_dependencies": len(blocking_deps),
                "max_dependency_chain_length": max_chain_length,
                "risk_factors": risk_factors,
                "recommendations": self._generate_dependency_recommendations(dependencies)
            }
        
        # Categorize dependencies
        dependency_summary = {
            "total_dependencies": len(dependencies),
            "internal_dependencies": len([d for d in dependencies if not d['is_external']]),
            "external_dependencies": len([d for d in dependencies if d['is_external']]),
            "resolved_dependencies": len([d for d in dependencies if d['health_status'] == 'resolved']),
            "blocked_dependencies": len([d for d in dependencies if d['health_status'] == 'blocked']),
            "at_risk_dependencies": len([d for d in dependencies if d['health_status'] == 'at_risk']),
            "healthy_dependencies": len([d for d in dependencies if d['health_status'] == 'healthy'])
        }
        
        return {
            "project_key": project_key,
            "project_name": project.project_name,
            "sprint_id": sprint.id,
            "sprint_name": sprint.name,
            "dependency_summary": dependency_summary,
            "dependencies": dependencies,
            "impact_analysis": impact_analysis if include_impact_analysis else None,
            "analysis_date": datetime.now(timezone.utc).isoformat()
        }
    
    def _generate_dependency_recommendations(self, dependencies: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on dependency analysis."""
        recommendations = []
        
        critical_deps = [d for d in dependencies if d['health_status'] in ['blocked', 'at_risk']]
        external_deps = [d for d in dependencies if d['is_external']]
        
        if critical_deps:
            recommendations.append("Prioritize resolving blocked or at-risk dependencies")
            recommendations.append("Establish regular check-ins with dependency owners")
        
        if external_deps:
            recommendations.append("Create contingency plans for external dependencies")
            recommendations.append("Increase communication frequency with external teams")
        
        if len(dependencies) > 10:
            recommendations.append("Consider breaking down work to reduce dependency complexity")
        
        blocking_deps = [d for d in dependencies if d['is_blocking']]
        if blocking_deps:
            recommendations.append("Focus on completing work that is blocking other tasks")
        
        return recommendations