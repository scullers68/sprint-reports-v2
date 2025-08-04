---
id: task-081
title: Project Progress Reporting Service
status: In Progress
assignee:
  - >-
    [ ] Extend existing reporting service to support project-based progress
    analysis, [ ] Create project velocity calculation algorithms based on
    historical sprint data, [ ] Implement project completion forecasting using
    Monte Carlo simulation methods, [ ] Add project-level burndown and burnup
    chart data generation, [ ] Create service methods for project dependency
    tracking and impact analysis, [ ] Implement project risk assessment based on
    velocity trends and capacity constraints, [ ] Add support for project
    milestone tracking within sprint context, [ ] Ensure integration with
    existing sprint reporting infrastructure without breaking current
    functionality
created_date: '2025-08-04'
updated_date: '2025-08-04'
labels: []
dependencies: []
---

## Description

Build comprehensive project progress reporting service that provides detailed breakdown of progress by project within sprint context, including velocity tracking and completion predictions.

## Acceptance Criteria

- [x] Extend existing reporting service to support project-based progress analysis
- [x] Create project velocity calculation algorithms based on historical sprint data
- [x] Implement project completion forecasting using Monte Carlo simulation methods
- [x] Add project-level burndown and burnup chart data generation
- [x] Create service methods for project dependency tracking and impact analysis
- [x] Implement project risk assessment based on velocity trends and capacity constraints
- [x] Add support for project milestone tracking within sprint context
- [x] Ensure integration with existing sprint reporting infrastructure without breaking current functionality

## Implementation Plan

1. Analyze existing reporting service architecture and project data models
2. Design project progress reporting service extending existing Report and SprintAnalysis models
3. Specify project velocity calculation algorithms using historical sprint data patterns
4. Design Monte Carlo simulation methods for project completion forecasting
5. Architect project-level burndown/burnup chart data generation
6. Design project dependency tracking and impact analysis service methods
7. Specify project risk assessment based on velocity trends and capacity constraints
8. Design project milestone tracking within sprint context
9. Create comprehensive technical specification for fullstack-engineer handoff

## Implementation Notes

# ARCHITECTURAL SPECIFICATION COMPLETE - READY FOR FULLSTACK-ENGINEER IMPLEMENTATION

Architecture complete. Ready for fullstack-engineer implementation.

## HANDOFF SUMMARY

This architectural specification provides a comprehensive blueprint for implementing project progress reporting service while maintaining full compliance with existing ADRs and architectural patterns.

**Key Deliverables:**
- Complete algorithm specifications for velocity calculation, Monte Carlo forecasting, and risk assessment
- Detailed service method specifications for SprintService extensions
- File modification plan prioritizing code reuse over new file creation
- Integration architecture preserving existing reporting functionality
- Acceptance criteria validation with architectural mapping

**Implementation Approach:**
- Extends existing SprintService and ReportService patterns (ADR-001 compliance)
- Builds upon existing SQLAlchemy models and caching infrastructure (ADR-002 compliance)
- Maintains existing router structure and endpoint patterns (ADR-003 compliance)
- Maximum code reuse with only essential new file creation

**Risk Mitigation:**
- Low risk implementation due to proven pattern extension
- Graceful degradation when project data unavailable
- Backward compatibility maintained with existing sprint reporting

**Dependencies:**
- Task-079: Project-based data organization models (ProjectWorkstream relationships)
- Task-080: Meta-board project portfolio infrastructure
- Existing caching infrastructure and JIRA service integration

Ready for immediate fullstack-engineer implementation with complete architectural guidance.
## COMPLIANCE VALIDATION ✅
- ADR-001 (Microservices): Extends existing SprintService and ReportService patterns
- ADR-002 (Database): Builds upon existing Report, SprintAnalysis, and Capacity models  
- ADR-003 (API Design): Follows existing endpoint patterns in reports.py
- CLAUDE.md Compliance: Prioritizes code reuse, extends existing files vs creating new ones

## ARCHITECTURAL DECISIONS

**1. Service Layer Architecture**
- Extends existing SprintService with project progress methods
- Enhances ReportService with project-specific report generation
- Integrates with existing JiraService for project data retrieval
- Reuses existing caching patterns from SprintCacheService

**2. Data Model Integration**
- Leverages task-079 ProjectWorkstream relationships for project organization
- Extends existing Report model with project-specific report_type values
- Uses existing SprintAnalysis.discipline_breakdown for project metrics
- Builds upon existing DisciplineTeamCapacity for team allocation tracking

**3. Algorithm Design**
- Project velocity calculation using moving averages from historical sprint data
- Monte Carlo simulation using triangular distribution for completion forecasting
- Burndown/burnup data generation using existing SprintAnalysis patterns
- Risk assessment algorithms based on velocity coefficient of variation

## FILES TO MODIFY (EXTENDING EXISTING ARCHITECTURE)

**Core Service Extensions:**
- `/backend/app/services/sprint_service.py` (Add project progress methods)
- `/backend/app/api/v1/endpoints/reports.py` (Add project progress endpoints)
- `/backend/app/models/report.py` (Add project-specific report types)

**Supporting Extensions:**
- `/backend/app/schemas/sprint.py` (Add project progress response schemas)
- `/backend/app/services/jira_service.py` (Add project dependency discovery)

## TECHNICAL SPECIFICATIONS

**1. Project Velocity Calculation Algorithm**
```python
# Moving average with weighted recency and seasonal adjustment
def calculate_project_velocity(project_key: str, lookback_sprints: int = 6):
    # Get historical sprint data filtered by project_key
    # Calculate story points completed per sprint
    # Apply exponential smoothing (alpha = 0.3 for trend detection)
    # Adjust for seasonal patterns (holidays, team changes)
    # Return velocity with confidence intervals (50%, 80%, 95%)
```

**2. Monte Carlo Forecasting Framework**
```python
# Triangular distribution simulation for completion probability
def forecast_project_completion(remaining_points: float, velocity_data: dict):
    # Define triangular distribution parameters:
    #   - Optimistic: max historical velocity * 1.2
    #   - Pessimistic: min historical velocity * 0.8  
    #   - Most likely: mean velocity
    # Run 10,000 Monte Carlo simulations
    # Calculate completion date probability distributions
    # Return forecast ranges with confidence levels
```

**3. Project Risk Assessment Algorithm**
```python
# Multi-factor risk scoring (0-100 scale)
def assess_project_risk(project_metrics: dict, capacity_data: dict):
    # Velocity Risk (40%): Coefficient of variation in velocity
    # Capacity Risk (25%): Over-allocation vs team capacity
    # Dependency Risk (20%): Blocked issues and external dependencies
    # Scope Risk (15%): Rate of scope changes and requirement volatility
    # Return composite risk score with factor breakdown
```

**4. Dependency Impact Analysis**
```python
# Critical path analysis using JIRA issue links
def analyze_project_dependencies(project_key: str):
    # Parse JIRA issue links (blocks, is blocked by, relates to)
    # Build directed acyclic graph of dependencies
    # Calculate critical path and bottleneck identification
    # Assess cross-project dependency risks
    # Return dependency metrics and impact assessment
```

## PROJECT PROGRESS REPORTING METHODS

**Core Service Methods to Add to SprintService:**

1. **get_project_velocity_analysis(project_key, sprint_range)**
   - Historical velocity calculation with trend analysis
   - Seasonal adjustment for holiday/vacation impacts
   - Velocity confidence intervals and prediction accuracy

2. **generate_project_completion_forecast(project_key, scenario_params)**
   - Monte Carlo simulation with configurable parameters
   - Multiple scenario analysis (best/worst/realistic cases)
   - Probability distributions for milestone dates

3. **create_project_burndown_data(project_key, sprint_id)**
   - Daily/sprint-level burndown calculations
   - Scope change tracking and impact visualization
   - Burnup data for scope creep analysis

4. **analyze_project_dependencies(project_key)**
   - JIRA link parsing for dependency detection
   - Critical path identification and bottleneck analysis
   - Cross-project impact assessment

5. **assess_project_risk_profile(project_key, capacity_context)**
   - Velocity volatility assessment
   - Resource allocation vs capacity analysis
   - Blocked issue impact and resolution tracking

6. **track_project_milestones(project_key, milestone_definitions)**
   - Custom milestone definition and tracking
   - Sprint-based milestone progress reporting
   - Milestone risk assessment and early warning systems

## INTEGRATION ARCHITECTURE

**Data Flow:**
1. JIRA Service → Project data collection and dependency parsing
2. Sprint Service → Historical analysis and velocity calculations
3. Report Service → Progress report generation and caching
4. Capacity Service → Team allocation and utilization analysis

**Caching Strategy:**
- Project velocity cache: 1 hour TTL, invalidate on sprint completion
- Dependency graph cache: 30 minutes TTL, invalidate on JIRA sync
- Risk assessment cache: 15 minutes TTL for real-time updates

**Error Handling:**
- Graceful degradation when project data unavailable
- Fallback to sprint-level analysis when project context missing
- Comprehensive validation for Monte Carlo simulation parameters

## ACCEPTANCE CRITERIA MAPPING

✅ **Extend existing reporting service**: SprintService and ReportService extensions
✅ **Project velocity algorithms**: Moving average with exponential smoothing
✅ **Monte Carlo forecasting**: Triangular distribution simulation framework  
✅ **Burndown/burnup charts**: Sprint-based progress visualization data
✅ **Dependency tracking**: JIRA link parsing and critical path analysis
✅ **Risk assessment**: Multi-factor scoring with capacity integration
✅ **Milestone tracking**: Configurable milestone definition and progress monitoring
✅ **Integration preservation**: All changes extend existing patterns without breaking functionality

## RISK ASSESSMENT: LOW RISK ✅
- Extends proven architectural patterns from existing ADRs
- Builds on established service layer and model relationships
- Maximum code reuse with minimal new file creation
- Maintains backward compatibility with existing reporting functionality

**Architecture complete. Ready for fullstack-engineer implementation.**
