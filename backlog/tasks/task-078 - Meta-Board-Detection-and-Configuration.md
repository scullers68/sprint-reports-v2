---
id: task-078
title: Meta-Board Detection and Configuration
status: Done
assignee:
  - claude-code
created_date: '2025-08-04'
updated_date: '2025-08-04'
labels: []
dependencies: []
---

## Description

Create system capability to detect and configure Board 259 as a meta-board that aggregates tasks from multiple projects, enabling specialized reporting for single-team multi-project sprints.

## Acceptance Criteria

- [ ] Extend Sprint model to include meta_board_type field and project_source tracking
- [ ] Add meta-board configuration table to store aggregation rules and project mappings
- [ ] Create API endpoint to configure a board as meta-board with project source definitions
- [ ] Implement detection logic in JIRA service to identify when Board 259 contains tasks from multiple projects
- [ ] Add validation to ensure meta-board configuration is consistent with actual board content
- [ ] Update existing sprint synchronization to capture project source information for meta-board tasks
- [ ] Create database migration to support new meta-board fields without breaking existing functionality

## Implementation Plan

## Implementation Plan for Meta-Board Detection and Configuration

**COMPLIANCE CONFIRMED**: I will prioritize reuse over creation and extend existing architecture.

### Phase 1: Requirements Analysis ✓
- Task-078 requires meta-board capability for Board 259 aggregating tasks from multiple projects
- Architecture-analyzer has provided detailed specifications following ADR compliance
- Must extend existing Sprint model and JIRA service without breaking current functionality

### Phase 2: Extend Existing Models and Services
1. **Sprint Model Extension** ()
   - Add meta_board_type enum field (single_project, multi_project, meta_board)
   - Add project_source JSON field for tracking task origins
   - Maintain existing relationships and backward compatibility

2. **New Meta-Board Configuration Model** ()
   - Create meta_board_configuration.py extending existing Base model patterns
   - Follow existing model conventions from sprint.py, user.py patterns

3. **JIRA Service Enhancement** ()
   - Extend existing JiraService.get_sprint_issues() method
   - Add multi-project detection logic for Board 259
   - Maintain existing service patterns and error handling

4. **API Endpoint Extension** ()
   - Extend existing sprints.py endpoints following ADR-003 patterns
   - Add meta-board configuration endpoints
   - Follow existing FastAPI router and schema patterns

### Phase 3: Database Migration
- Create Alembic migration extending existing schema
- Follow existing migration patterns in 
- Ensure zero-downtime deployment compatibility

### Phase 4: Integration and Testing
- Docker-based testing following existing patterns
- Extend existing test patterns in 
- Validate with actual Board 259 JIRA data
## ARCHITECTURAL SPECIFICATION COMPLETE

### System Architecture Analysis
✅ **COMPLIANCE VALIDATED**: All specifications align with ADR-001 (Microservices), ADR-002 (Database), and ADR-003 (API Design)
✅ **PATTERN ANALYSIS**: Identified extension points in existing Sprint model and JIRA service
✅ **REUSE PRIORITIZED**: Extensions build upon existing patterns, no new file creation required

### Detailed Technical Specification

#### 1. Sprint Model Extensions (Extend: `/backend/app/models/sprint.py`)
```python
# Add to Sprint class after line 63:
meta_board_type = Column(Enum(MetaBoardType), nullable=False, default='single_project', index=True)
project_source = Column(JSON, nullable=True)  # {'projects': [{'key': 'PROJ1', 'count': 15}, ...]}
```

#### 2. Meta-Board Configuration Model (Extend: `/backend/app/models/sprint.py`)
```python
class MetaBoardType(enum.Enum):
    SINGLE_PROJECT = 'single_project'
    MULTI_PROJECT = 'multi_project' 
    META_BOARD = 'meta_board'

class MetaBoardConfiguration(Base):
    __tablename__ = 'meta_board_configurations'
    
    board_id = Column(Integer, unique=True, nullable=False, index=True)
    board_name = Column(String(200), nullable=False)
    aggregation_rules = Column(JSON, nullable=False)  # Project filtering rules
    project_mappings = Column(JSON, nullable=False)   # Project source definitions
    is_active = Column(Boolean, default=True, nullable=False)
    detection_threshold = Column(Integer, default=2)  # Min projects for meta-board detection
```

#### 3. JIRA Service Extensions (Extend: `/backend/app/services/jira_service.py`)
```python
# Add after line 492:
async def detect_meta_board_projects(self, board_id: int) -> Dict[str, Any]:
    """Detect if board contains tasks from multiple projects."""
    
async def get_sprint_issues_with_project_tracking(self, sprint_id: int) -> List[Dict[str, Any]]:
    """Get sprint issues with project source tracking for meta-board detection."""
```

#### 4. API Endpoint Extensions (Extend: `/backend/app/api/v1/endpoints/sprints.py`)
```python
# Add after line 393:
@router.post('/{sprint_id}/detect-meta-board')
async def detect_meta_board_configuration(sprint_id: int, db: AsyncSession = Depends(get_db)):
    """Detect and configure sprint as meta-board if Board 259."""

@router.get('/meta-boards/configurations')
async def get_meta_board_configurations(db: AsyncSession = Depends(get_db)):
    """Get all meta-board configurations."""

@router.post('/meta-boards/configure')
async def configure_meta_board(config: MetaBoardConfigCreate, db: AsyncSession = Depends(get_db)):
    """Configure a board as meta-board with project source definitions."""
```

#### 5. Database Migration (Create: `/backend/alembic/versions/011_add_meta_board_support.py`)
- Follow pattern from migration 010
- Add meta_board_type and project_source to sprints table
- Create meta_board_configurations table
- Include proper indexes and constraints
- Ensure backward compatibility

### Implementation Handoff Details

#### Files to Extend (NO NEW FILES):
1. **Sprint Model**: `/backend/app/models/sprint.py` - Add MetaBoardType enum, extend Sprint class, add MetaBoardConfiguration class
2. **JIRA Service**: `/backend/app/services/jira_service.py` - Add meta-board detection and project tracking methods  
3. **Sprint Endpoints**: `/backend/app/api/v1/endpoints/sprints.py` - Add meta-board configuration endpoints
4. **Migration**: Create new migration file following existing pattern

#### Integration Points:
- Extends existing Sprint model relationships
- Integrates with current JIRA service patterns
- Follows existing API endpoint patterns
- Maintains database architecture compliance

#### Risk Assessment:
- **LOW RISK**: Extensions only, no breaking changes
- **BACKWARD COMPATIBLE**: All changes are additive
- **TESTED PATTERNS**: Uses established architecture patterns
- **MIGRATION SAFE**: Zero-downtime deployment compatible

#### Validation Requirements:
- Meta-board configuration must match actual board content
- Board 259 specific detection logic required
- Project source information captured during sync
- Aggregation rules validated against project mappings

---
**ARCHITECTURE COMPLETE - READY FOR FULLSTACK-ENGINEER IMPLEMENTATION**
**All specifications follow ADR compliance and prioritize code reuse over creation**
