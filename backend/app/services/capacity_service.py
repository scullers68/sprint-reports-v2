"""
Capacity service for multi-project capacity analysis and management.

Handles capacity distribution analysis, forecasting, conflict detection,
and optimization recommendations for teams working across multiple projects.
"""

import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.capacity import (
    DisciplineTeamCapacity, TeamCapacityPlan, ProjectCapacityAllocation
)
from app.models.sprint import Sprint, SprintAnalysis
from app.models.project import (
    ProjectWorkstream, ProjectSprintAssociation, ProjectSprintMetrics
)
from app.core.logging import get_logger
from app.core.exceptions import NotFoundError, ValidationError

logger = get_logger(__name__)


class CapacityConflictType(Enum):
    """Types of capacity conflicts."""
    OVER_ALLOCATION = "over_allocation"
    UNDER_UTILIZATION = "under_utilization"
    TEAM_OVERCOMMIT = "team_overcommit"
    PROJECT_UNDERSTAFF = "project_understaff"
    PRIORITY_MISMATCH = "priority_mismatch"


class OptimizationStrategy(Enum):
    """Capacity optimization strategies."""
    BALANCE_UTILIZATION = "balance_utilization"
    MAXIMIZE_THROUGHPUT = "maximize_throughput"
    MINIMIZE_CONFLICTS = "minimize_conflicts"
    PRIORITY_FOCUSED = "priority_focused"


@dataclass
class CapacityDistribution:
    """Capacity distribution analysis result."""
    team_name: str
    total_capacity: float
    total_allocated: float
    utilization_percentage: float
    project_allocations: List[Dict[str, Any]]
    is_over_capacity: bool
    available_capacity: float


@dataclass
class CapacityConflict:
    """Capacity conflict detection result."""
    conflict_id: str
    conflict_type: CapacityConflictType
    team_name: str
    project_key: Optional[str]
    severity: str  # high, medium, low
    description: str
    impact_assessment: str
    recommended_actions: List[str]
    metadata: Dict[str, Any]


@dataclass
class CapacityForecast:
    """Capacity forecasting result."""
    project_key: str
    team_name: str
    current_capacity: float
    forecasted_need: float
    confidence_level: float
    trend: str  # increasing, decreasing, stable
    risk_factors: List[str]
    recommendations: List[str]


@dataclass
class OptimizationRecommendation:
    """Capacity optimization recommendation."""
    recommendation_id: str
    strategy: OptimizationStrategy
    description: str
    expected_impact: str
    implementation_effort: str  # low, medium, high
    affected_teams: List[str]
    affected_projects: List[str]
    specific_actions: List[Dict[str, Any]]
    priority: int


class CapacityAnalysisService:
    """Service class for multi-project capacity analysis operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def analyze_capacity_distribution(
        self, 
        sprint_id: int,
        include_projects: Optional[List[str]] = None
    ) -> List[CapacityDistribution]:
        """
        Analyze how team capacity is distributed across projects within a sprint.
        
        Args:
            sprint_id: Sprint to analyze
            include_projects: Optional list of project keys to filter by
            
        Returns:
            List of capacity distribution analysis results per team
        """
        try:
            # Get sprint with project associations
            sprint_query = select(Sprint).where(Sprint.id == sprint_id)
            sprint_result = await self.db.execute(sprint_query)
            sprint = sprint_result.scalar_one_or_none()
            
            if not sprint:
                raise NotFoundError(f"Sprint with ID {sprint_id} not found")
            
            # Get discipline team capacities for this sprint
            capacity_query = (
                select(DisciplineTeamCapacity)
                .where(and_(
                    DisciplineTeamCapacity.sprint_id == sprint_id,
                    DisciplineTeamCapacity.is_active == True
                ))
            )
            capacity_result = await self.db.execute(capacity_query)
            team_capacities = capacity_result.scalars().all()
            
            distributions = []
            
            for team_capacity in team_capacities:
                # Get project allocations for this team
                allocation_query = (
                    select(ProjectCapacityAllocation)
                    .options(selectinload(ProjectCapacityAllocation.project_workstream))
                    .where(and_(
                        ProjectCapacityAllocation.discipline_team_capacity_id == team_capacity.id,
                        ProjectCapacityAllocation.is_active == True
                    ))
                )
                
                if include_projects:
                    allocation_query = allocation_query.where(
                        ProjectCapacityAllocation.project_key.in_(include_projects)
                    )
                
                allocation_result = await self.db.execute(allocation_query)
                allocations = allocation_result.scalars().all()
                
                # Calculate distribution metrics
                total_allocated = sum(alloc.allocated_capacity for alloc in allocations)
                utilization_percentage = (total_allocated / team_capacity.capacity_points * 100) if team_capacity.capacity_points > 0 else 0
                
                project_allocations = []
                for alloc in allocations:
                    project_allocations.append({
                        "project_key": alloc.project_key,
                        "project_name": alloc.project_workstream.project_name if alloc.project_workstream else alloc.project_key,
                        "allocated_capacity": alloc.allocated_capacity,
                        "capacity_percentage": alloc.capacity_percentage,
                        "utilized_capacity": alloc.utilized_capacity,
                        "utilization_percentage": alloc.utilization_percentage,
                        "priority": alloc.allocation_priority,
                        "trend": alloc.capacity_trend
                    })
                
                distribution = CapacityDistribution(
                    team_name=team_capacity.discipline_team,
                    total_capacity=team_capacity.capacity_points,
                    total_allocated=total_allocated,
                    utilization_percentage=utilization_percentage,
                    project_allocations=project_allocations,
                    is_over_capacity=total_allocated > team_capacity.capacity_points,
                    available_capacity=max(0.0, team_capacity.capacity_points - total_allocated)
                )
                
                distributions.append(distribution)
            
            logger.info(f"Analyzed capacity distribution for sprint {sprint_id}, found {len(distributions)} teams")
            return distributions
            
        except Exception as e:
            logger.error(f"Error analyzing capacity distribution for sprint {sprint_id}: {str(e)}")
            raise
    
    async def detect_capacity_conflicts(
        self, 
        sprint_id: int,
        threshold_over_allocation: float = 1.1,  # 110% = conflict
        threshold_under_utilization: float = 0.5  # 50% = underutilized
    ) -> List[CapacityConflict]:
        """
        Detect capacity conflicts and issues within a sprint.
        
        Args:
            sprint_id: Sprint to analyze
            threshold_over_allocation: Threshold for over-allocation conflicts (1.1 = 110%)
            threshold_under_utilization: Threshold for under-utilization (0.5 = 50%)
            
        Returns:
            List of detected capacity conflicts
        """
        try:
            distributions = await self.analyze_capacity_distribution(sprint_id)
            conflicts = []
            
            for dist in distributions:
                conflict_id = str(uuid.uuid4())
                
                # Check for over-allocation
                if dist.utilization_percentage > (threshold_over_allocation * 100):
                    severity = "high" if dist.utilization_percentage > 150 else "medium"
                    
                    conflicts.append(CapacityConflict(
                        conflict_id=conflict_id,
                        conflict_type=CapacityConflictType.OVER_ALLOCATION,
                        team_name=dist.team_name,
                        project_key=None,
                        severity=severity,
                        description=f"Team {dist.team_name} is over-allocated at {dist.utilization_percentage:.1f}%",
                        impact_assessment=f"Risk of missed deadlines and team burnout. Overcommitment by {dist.total_allocated - dist.total_capacity:.1f} capacity units.",
                        recommended_actions=[
                            "Redistribute work to other teams",
                            "Extend sprint timeline",
                            "Remove lower priority tasks",
                            "Add temporary capacity"
                        ],
                        metadata={
                            "utilization_percentage": dist.utilization_percentage,
                            "over_allocation_amount": dist.total_allocated - dist.total_capacity,
                            "affected_projects": [p["project_key"] for p in dist.project_allocations]
                        }
                    ))
                
                # Check for under-utilization
                elif dist.utilization_percentage < (threshold_under_utilization * 100):
                    conflicts.append(CapacityConflict(
                        conflict_id=str(uuid.uuid4()),
                        conflict_type=CapacityConflictType.UNDER_UTILIZATION,
                        team_name=dist.team_name,
                        project_key=None,
                        severity="low",
                        description=f"Team {dist.team_name} is under-utilized at {dist.utilization_percentage:.1f}%",
                        impact_assessment=f"Potential for taking on additional work. Available capacity: {dist.available_capacity:.1f} units.",
                        recommended_actions=[
                            "Assign additional tasks from backlog",
                            "Support over-allocated teams",
                            "Focus on improvement activities",
                            "Plan ahead for next sprint"
                        ],
                        metadata={
                            "utilization_percentage": dist.utilization_percentage,
                            "available_capacity": dist.available_capacity,
                            "current_projects": [p["project_key"] for p in dist.project_allocations]
                        }
                    ))
                
                # Check for priority mismatches within team allocations
                high_priority_low_allocation = []
                low_priority_high_allocation = []
                
                for proj in dist.project_allocations:
                    priority = proj.get("priority", 999)
                    capacity_pct = proj.get("capacity_percentage", 0)
                    
                    if priority <= 2 and capacity_pct < 20:  # High priority, low allocation
                        high_priority_low_allocation.append(proj)
                    elif priority >= 5 and capacity_pct > 40:  # Low priority, high allocation
                        low_priority_high_allocation.append(proj)
                
                if high_priority_low_allocation or low_priority_high_allocation:
                    conflicts.append(CapacityConflict(
                        conflict_id=str(uuid.uuid4()),
                        conflict_type=CapacityConflictType.PRIORITY_MISMATCH,
                        team_name=dist.team_name,
                        project_key=None,
                        severity="medium",
                        description=f"Priority-allocation mismatch detected for team {dist.team_name}",
                        impact_assessment="Resource allocation does not align with project priorities, potentially impacting strategic objectives.",
                        recommended_actions=[
                            "Realign capacity allocation with project priorities",
                            "Review and update project priorities",
                            "Consider resource reallocation",
                            "Escalate priority conflicts to management"
                        ],
                        metadata={
                            "high_priority_low_allocation": high_priority_low_allocation,
                            "low_priority_high_allocation": low_priority_high_allocation
                        }
                    ))
            
            logger.info(f"Detected {len(conflicts)} capacity conflicts for sprint {sprint_id}")
            return conflicts
            
        except Exception as e:
            logger.error(f"Error detecting capacity conflicts for sprint {sprint_id}: {str(e)}")
            raise
    
    async def forecast_project_capacity_needs(
        self, 
        project_key: str,
        team_name: Optional[str] = None,
        forecast_periods: int = 3
    ) -> List[CapacityForecast]:
        """
        Forecast capacity needs for a project based on historical patterns.
        
        Args:
            project_key: Project to forecast for
            team_name: Optional specific team to forecast for
            forecast_periods: Number of future periods to forecast
            
        Returns:
            List of capacity forecasts per team
        """
        try:
            # Get historical capacity allocations for this project
            base_query = (
                select(ProjectCapacityAllocation)
                .options(selectinload(ProjectCapacityAllocation.sprint))
                .where(and_(
                    ProjectCapacityAllocation.project_key == project_key,
                    ProjectCapacityAllocation.is_active == True
                ))
                .order_by(desc(ProjectCapacityAllocation.created_at))
                .limit(20)  # Get last 20 records for analysis
            )
            
            if team_name:
                base_query = base_query.where(ProjectCapacityAllocation.discipline_team == team_name)
            
            result = await self.db.execute(base_query)
            historical_allocations = result.scalars().all()
            
            if not historical_allocations:
                logger.warning(f"No historical data found for project {project_key}")
                return []
            
            # Group by team and analyze trends
            team_data = {}
            for alloc in historical_allocations:
                team = alloc.discipline_team
                if team not in team_data:
                    team_data[team] = []
                
                team_data[team].append({
                    "date": alloc.created_at,
                    "allocated_capacity": alloc.allocated_capacity,
                    "utilized_capacity": alloc.utilized_capacity,
                    "trend": alloc.capacity_trend
                })
            
            forecasts = []
            
            for team, data in team_data.items():
                if len(data) < 2:
                    continue  # Need at least 2 data points for trend analysis
                
                # Sort by date
                data.sort(key=lambda x: x["date"])
                
                # Calculate trends
                recent_allocations = [d["allocated_capacity"] for d in data[-3:]]
                recent_utilizations = [d["utilized_capacity"] for d in data[-3:]]
                
                avg_allocation = sum(recent_allocations) / len(recent_allocations)
                avg_utilization = sum(recent_utilizations) / len(recent_utilizations)
                
                # Determine trend
                if len(recent_allocations) >= 2:
                    trend_direction = "increasing" if recent_allocations[-1] > recent_allocations[0] else "decreasing"
                    if abs(recent_allocations[-1] - recent_allocations[0]) < (avg_allocation * 0.1):
                        trend_direction = "stable"
                else:
                    trend_direction = "stable"
                
                # Calculate forecast
                trend_multiplier = 1.1 if trend_direction == "increasing" else 0.9 if trend_direction == "decreasing" else 1.0
                forecasted_need = avg_allocation * trend_multiplier
                
                # Calculate confidence based on data consistency
                allocations_variance = sum((x - avg_allocation) ** 2 for x in recent_allocations) / len(recent_allocations)
                confidence_level = max(0.3, min(0.95, 1.0 - (allocations_variance / avg_allocation)))
                
                # Identify risk factors
                risk_factors = []
                if avg_utilization > avg_allocation * 1.1:
                    risk_factors.append("Historical over-utilization pattern")
                if trend_direction == "increasing":
                    risk_factors.append("Increasing capacity demand trend")
                if confidence_level < 0.6:
                    risk_factors.append("High variability in historical data")
                
                # Generate recommendations
                recommendations = []
                if forecasted_need > avg_allocation * 1.2:
                    recommendations.append("Consider increasing team allocation for this project")
                if avg_utilization < avg_allocation * 0.8:
                    recommendations.append("Review project scope - may be over-allocated")
                if trend_direction == "increasing":
                    recommendations.append("Plan for capacity scaling in upcoming sprints")
                
                forecast = CapacityForecast(
                    project_key=project_key,
                    team_name=team,
                    current_capacity=avg_allocation,
                    forecasted_need=forecasted_need,
                    confidence_level=confidence_level,
                    trend=trend_direction,
                    risk_factors=risk_factors,
                    recommendations=recommendations
                )
                
                forecasts.append(forecast)
            
            logger.info(f"Generated {len(forecasts)} capacity forecasts for project {project_key}")
            return forecasts
            
        except Exception as e:
            logger.error(f"Error forecasting capacity for project {project_key}: {str(e)}")
            raise
    
    async def generate_optimization_recommendations(
        self, 
        sprint_id: int,
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCE_UTILIZATION
    ) -> List[OptimizationRecommendation]:
        """
        Generate capacity optimization recommendations for a sprint.
        
        Args:
            sprint_id: Sprint to optimize
            strategy: Optimization strategy to apply
            
        Returns:
            List of optimization recommendations
        """
        try:
            # Get current capacity distribution and conflicts
            distributions = await self.analyze_capacity_distribution(sprint_id)
            conflicts = await self.detect_capacity_conflicts(sprint_id)
            
            recommendations = []
            recommendation_priority = 1
            
            # Strategy: Balance Utilization
            if strategy == OptimizationStrategy.BALANCE_UTILIZATION:
                over_allocated = [d for d in distributions if d.is_over_capacity]
                under_utilized = [d for d in distributions if d.utilization_percentage < 70]
                
                if over_allocated and under_utilized:
                    for over_team in over_allocated:
                        for under_team in under_utilized:
                            if under_team.available_capacity > 0:
                                # Find transferable projects
                                transferable_projects = [
                                    p for p in over_team.project_allocations 
                                    if p.get("priority", 999) > 3  # Lower priority projects
                                ]
                                
                                if transferable_projects:
                                    recommendations.append(OptimizationRecommendation(
                                        recommendation_id=str(uuid.uuid4()),
                                        strategy=strategy,
                                        description=f"Rebalance capacity between {over_team.team_name} and {under_team.team_name}",
                                        expected_impact=f"Reduce over-allocation by {min(over_team.total_allocated - over_team.total_capacity, under_team.available_capacity):.1f} capacity units",
                                        implementation_effort="medium",
                                        affected_teams=[over_team.team_name, under_team.team_name],
                                        affected_projects=[p["project_key"] for p in transferable_projects[:2]],
                                        specific_actions=[
                                            {
                                                "action": "transfer_capacity",
                                                "from_team": over_team.team_name,
                                                "to_team": under_team.team_name,
                                                "projects": transferable_projects[:2],
                                                "estimated_capacity": min(10.0, under_team.available_capacity)
                                            }
                                        ],
                                        priority=recommendation_priority
                                    ))
                                    recommendation_priority += 1
            
            # Strategy: Minimize Conflicts
            elif strategy == OptimizationStrategy.MINIMIZE_CONFLICTS:
                high_severity_conflicts = [c for c in conflicts if c.severity == "high"]
                
                for conflict in high_severity_conflicts:
                    if conflict.conflict_type == CapacityConflictType.OVER_ALLOCATION:
                        recommendations.append(OptimizationRecommendation(
                            recommendation_id=str(uuid.uuid4()),
                            strategy=strategy,
                            description=f"Resolve over-allocation for {conflict.team_name}",
                            expected_impact="Eliminate high-severity capacity conflict",
                            implementation_effort="high",
                            affected_teams=[conflict.team_name],
                            affected_projects=conflict.metadata.get("affected_projects", []),
                            specific_actions=[
                                {
                                    "action": "reduce_allocation",
                                    "team": conflict.team_name,
                                    "reduction_amount": conflict.metadata.get("over_allocation_amount", 0),
                                    "method": "scope_reduction_or_timeline_extension"
                                }
                            ],
                            priority=recommendation_priority
                        ))
                        recommendation_priority += 1
            
            # Strategy: Priority Focused
            elif strategy == OptimizationStrategy.PRIORITY_FOCUSED:
                for dist in distributions:
                    high_priority_projects = [
                        p for p in dist.project_allocations 
                        if p.get("priority", 999) <= 2 and p.get("capacity_percentage", 0) < 30
                    ]
                    
                    if high_priority_projects:
                        recommendations.append(OptimizationRecommendation(
                            recommendation_id=str(uuid.uuid4()),
                            strategy=strategy,
                            description=f"Increase allocation for high-priority projects in {dist.team_name}",
                            expected_impact="Better alignment with strategic priorities",
                            implementation_effort="medium",
                            affected_teams=[dist.team_name],
                            affected_projects=[p["project_key"] for p in high_priority_projects],
                            specific_actions=[
                                {
                                    "action": "increase_priority_allocation",
                                    "team": dist.team_name,
                                    "projects": high_priority_projects,
                                    "target_increase": "20-30% of team capacity"
                                }
                            ],
                            priority=recommendation_priority
                        ))
                        recommendation_priority += 1
            
            logger.info(f"Generated {len(recommendations)} optimization recommendations for sprint {sprint_id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating optimization recommendations for sprint {sprint_id}: {str(e)}")
            raise
    
    async def get_historical_capacity_analysis(
        self, 
        team_name: Optional[str] = None,
        project_key: Optional[str] = None,
        periods: int = 6
    ) -> Dict[str, Any]:
        """
        Analyze historical capacity patterns for trends and insights.
        
        Args:
            team_name: Optional specific team to analyze
            project_key: Optional specific project to analyze
            periods: Number of historical periods to analyze
            
        Returns:
            Historical capacity analysis results
        """
        try:
            # Build base query for historical data
            base_query = (
                select(ProjectCapacityAllocation)
                .options(
                    selectinload(ProjectCapacityAllocation.sprint),
                    selectinload(ProjectCapacityAllocation.project_workstream)
                )
                .where(ProjectCapacityAllocation.is_active == True)
                .order_by(desc(ProjectCapacityAllocation.created_at))
                .limit(periods * 10)  # Get more data to account for filtering
            )
            
            if team_name:
                base_query = base_query.where(ProjectCapacityAllocation.discipline_team == team_name)
            if project_key:
                base_query = base_query.where(ProjectCapacityAllocation.project_key == project_key)
            
            result = await self.db.execute(base_query)
            historical_data = result.scalars().all()
            
            if not historical_data:
                return {
                    "message": "No historical data found",
                    "filters": {"team_name": team_name, "project_key": project_key}
                }
            
            # Analyze patterns
            team_patterns = {}
            project_patterns = {}
            
            for allocation in historical_data:
                team = allocation.discipline_team
                project = allocation.project_key
                
                # Team pattern analysis
                if team not in team_patterns:
                    team_patterns[team] = {
                        "allocations": [],
                        "utilizations": [],
                        "efficiency_ratios": []
                    }
                
                team_patterns[team]["allocations"].append(allocation.allocated_capacity)
                team_patterns[team]["utilizations"].append(allocation.utilized_capacity)
                team_patterns[team]["efficiency_ratios"].append(allocation.efficiency_ratio)
                
                # Project pattern analysis
                if project not in project_patterns:
                    project_patterns[project] = {
                        "teams_involved": set(),
                        "total_allocations": [],
                        "average_utilization": []
                    }
                
                project_patterns[project]["teams_involved"].add(team)
                project_patterns[project]["total_allocations"].append(allocation.allocated_capacity)
                project_patterns[project]["average_utilization"].append(allocation.utilization_percentage)
            
            # Calculate insights
            team_insights = {}
            for team, data in team_patterns.items():
                if len(data["allocations"]) >= 2:
                    avg_allocation = sum(data["allocations"]) / len(data["allocations"])
                    avg_utilization = sum(data["utilizations"]) / len(data["utilizations"])
                    avg_efficiency = sum(data["efficiency_ratios"]) / len(data["efficiency_ratios"])
                    
                    team_insights[team] = {
                        "average_allocation": avg_allocation,
                        "average_utilization": avg_utilization,
                        "average_efficiency": avg_efficiency,
                        "allocation_trend": "stable",  # Simplified - could be enhanced
                        "consistency_score": 1.0 - (
                            sum((x - avg_allocation) ** 2 for x in data["allocations"]) / 
                            (len(data["allocations"]) * avg_allocation) if avg_allocation > 0 else 0
                        )
                    }
            
            project_insights = {}
            for project, data in project_patterns.items():
                if len(data["total_allocations"]) >= 2:
                    project_insights[project] = {
                        "teams_count": len(data["teams_involved"]),
                        "teams_involved": list(data["teams_involved"]),
                        "average_allocation": sum(data["total_allocations"]) / len(data["total_allocations"]),
                        "average_utilization": sum(data["average_utilization"]) / len(data["average_utilization"]),
                        "resource_distribution": "multi_team" if len(data["teams_involved"]) > 1 else "single_team"
                    }
            
            analysis_result = {
                "analysis_period": {
                    "records_analyzed": len(historical_data),
                    "unique_teams": len(team_patterns),
                    "unique_projects": len(project_patterns)
                },
                "team_insights": team_insights,
                "project_insights": project_insights,
                "key_findings": self._generate_key_findings(team_insights, project_insights),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Completed historical capacity analysis with {len(historical_data)} records")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in historical capacity analysis: {str(e)}")
            raise
    
    def _generate_key_findings(
        self, 
        team_insights: Dict[str, Any], 
        project_insights: Dict[str, Any]
    ) -> List[str]:
        """Generate key findings from historical analysis."""
        findings = []
        
        if team_insights:
            # Find most efficient teams
            efficient_teams = [
                team for team, data in team_insights.items()
                if data["average_efficiency"] > 0.9
            ]
            if efficient_teams:
                findings.append(f"High-efficiency teams identified: {', '.join(efficient_teams[:3])}")
            
            # Find teams with capacity issues
            over_utilized_teams = [
                team for team, data in team_insights.items()
                if data["average_utilization"] > data["average_allocation"] * 1.1
            ]
            if over_utilized_teams:
                findings.append(f"Teams showing over-utilization patterns: {', '.join(over_utilized_teams[:3])}")
        
        if project_insights:
            # Find multi-team projects
            multi_team_projects = [
                project for project, data in project_insights.items()
                if len(data["teams_involved"]) > 2
            ]
            if multi_team_projects:
                findings.append(f"Complex multi-team projects requiring coordination: {', '.join(multi_team_projects[:3])}")
        
        if not findings:
            findings.append("No significant patterns detected in historical data")
        
        return findings


class CapacityPlanningService:
    """Service for long-term capacity planning operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_capacity_plan(
        self, 
        team_name: str,
        plan_data: Dict[str, Any]
    ) -> TeamCapacityPlan:
        """Create a new capacity plan for a team."""
        try:
            plan = TeamCapacityPlan(
                discipline_team=team_name,
                plan_name=plan_data["plan_name"],
                start_date=plan_data["start_date"],
                end_date=plan_data["end_date"],
                default_capacity=plan_data.get("default_capacity", 30.0),
                capacity_unit=plan_data.get("capacity_unit", "story_points"),
                team_size=plan_data.get("team_size"),
                team_members=plan_data.get("team_members"),
                holiday_adjustments=plan_data.get("holiday_adjustments"),
                sprint_exceptions=plan_data.get("sprint_exceptions"),
                created_by=plan_data.get("created_by"),
                notes=plan_data.get("notes")
            )
            
            self.db.add(plan)
            await self.db.commit()
            await self.db.refresh(plan)
            
            logger.info(f"Created capacity plan for team {team_name}: {plan.plan_name}")
            return plan
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating capacity plan for team {team_name}: {str(e)}")
            raise
    
    async def get_active_capacity_plans(
        self, 
        team_name: Optional[str] = None
    ) -> List[TeamCapacityPlan]:
        """Get active capacity plans."""
        try:
            query = select(TeamCapacityPlan).where(TeamCapacityPlan.is_active == True)
            
            if team_name:
                query = query.where(TeamCapacityPlan.discipline_team == team_name)
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error retrieving capacity plans: {str(e)}")
            raise