#!/usr/bin/env python3
"""
Data migration script to populate project workstreams from existing sprint data.

This script extracts project information from existing Sprint records and creates:
1. ProjectWorkstream records for each unique project
2. ProjectSprintAssociation records linking sprints to their projects
3. Updates SprintAnalysis records with project information
4. Generates baseline ProjectSprintMetrics for recent sprints

Usage:
    python scripts/migrate_project_data.py [--dry-run] [--batch-size=1000]
"""

import asyncio
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from collections import defaultdict

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

# Import our models and database setup
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_db_session
from app.models.sprint import Sprint, SprintAnalysis
from app.models.project import ProjectWorkstream, ProjectSprintAssociation, ProjectSprintMetrics, WorkstreamType, AssociationType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProjectDataMigrator:
    """Handles migration of project data from existing sprint records."""
    
    def __init__(self, db_session: AsyncSession, dry_run: bool = False, batch_size: int = 1000):
        self.db = db_session
        self.dry_run = dry_run
        self.batch_size = batch_size
        
        # Tracking statistics
        self.stats = {
            'sprints_processed': 0,
            'projects_created': 0,
            'associations_created': 0,
            'analyses_updated': 0,
            'metrics_created': 0,
            'errors': 0
        }
    
    async def migrate_all_data(self) -> Dict:
        """Execute complete migration process."""
        logger.info(f"Starting project data migration (dry_run={self.dry_run})")
        
        try:
            # Step 1: Extract and create project workstreams
            await self._create_project_workstreams()
            
            # Step 2: Create sprint-project associations
            await self._create_sprint_associations()
            
            # Step 3: Update sprint analyses with project info
            await self._update_sprint_analyses()
            
            # Step 4: Generate baseline metrics for recent sprints
            await self._generate_baseline_metrics()
            
            # Commit changes if not dry run
            if not self.dry_run:
                await self.db.commit()
                logger.info("Migration completed successfully - changes committed")
            else:
                await self.db.rollback()
                logger.info("Dry run completed - no changes committed")
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            await self.db.rollback()
            self.stats['errors'] += 1
            raise
    
    async def _create_project_workstreams(self):
        """Extract unique projects and create ProjectWorkstream records."""
        logger.info("Step 1: Creating project workstreams...")
        
        # Get unique project data from existing sprints
        stmt = select(
            Sprint.jira_project_key,
            func.max(Sprint.jira_board_name).label('board_name'),
            func.max(Sprint.board_id).label('board_id'),
            func.count().label('sprint_count')
        ).where(
            and_(
                Sprint.jira_project_key.isnot(None),
                Sprint.jira_project_key != ''
            )
        ).group_by(Sprint.jira_project_key)
        
        result = await self.db.execute(stmt)
        project_data = result.fetchall()
        
        logger.info(f"Found {len(project_data)} unique projects to migrate")
        
        for row in project_data:
            project_key = row.jira_project_key
            board_name = row.board_name
            board_id = row.board_id
            sprint_count = row.sprint_count
            
            # Check if project workstream already exists
            existing_stmt = select(ProjectWorkstream).where(
                ProjectWorkstream.project_key == project_key
            )
            existing_result = await self.db.execute(existing_stmt)
            existing_project = existing_result.scalar_one_or_none()
            
            if existing_project:
                logger.info(f"Project workstream already exists: {project_key}")
                continue
            
            # Determine workstream type based on sprint count
            if sprint_count >= 10:
                workstream_type = WorkstreamType.INITIATIVE
            elif sprint_count >= 3:
                workstream_type = WorkstreamType.EPIC
            else:
                workstream_type = WorkstreamType.STANDARD
            
            # Create project workstream
            project_workstream = ProjectWorkstream(
                project_key=project_key,
                project_name=project_key,  # Use key as name initially
                jira_board_id=board_id,
                jira_board_name=board_name,
                workstream_type=workstream_type,
                is_active=True,
                project_category="Development",  # Default category
                metadata={
                    'migrated_from_sprint_data': True,
                    'original_sprint_count': sprint_count,
                    'migration_date': datetime.utcnow().isoformat()
                }
            )
            
            if not self.dry_run:
                self.db.add(project_workstream)
                await self.db.flush()  # Get the ID
            
            self.stats['projects_created'] += 1
            logger.info(f"Created project workstream: {project_key} (type: {workstream_type.value})")
        
        logger.info(f"Step 1 complete: {self.stats['projects_created']} project workstreams created")
    
    async def _create_sprint_associations(self):
        """Create ProjectSprintAssociation records linking sprints to projects."""
        logger.info("Step 2: Creating sprint-project associations...")
        
        # Get all sprints with project keys
        stmt = select(Sprint).where(
            and_(
                Sprint.jira_project_key.isnot(None),
                Sprint.jira_project_key != ''
            )
        )
        result = await self.db.execute(stmt)
        sprints = result.scalars().all()
        
        logger.info(f"Processing {len(sprints)} sprints for associations")
        
        # Get all project workstreams for lookup
        projects_stmt = select(ProjectWorkstream)
        projects_result = await self.db.execute(projects_stmt)
        projects = {p.project_key: p for p in projects_result.scalars().all()}
        
        for sprint in sprints:
            project_key = sprint.jira_project_key
            project_workstream = projects.get(project_key)
            
            if not project_workstream:
                logger.warning(f"No project workstream found for sprint {sprint.id} with project key {project_key}")
                continue
            
            # Check if association already exists
            existing_stmt = select(ProjectSprintAssociation).where(
                and_(
                    ProjectSprintAssociation.sprint_id == sprint.id,
                    ProjectSprintAssociation.project_workstream_id == project_workstream.id
                )
            )
            existing_result = await self.db.execute(existing_stmt)
            existing_assoc = existing_result.scalar_one_or_none()
            
            if existing_assoc:
                continue
            
            # Determine association type based on meta-board type
            if sprint.meta_board_type and sprint.meta_board_type.value in ['multi_project', 'meta_board']:
                association_type = AssociationType.SECONDARY
            else:
                association_type = AssociationType.PRIMARY
            
            # Create association
            association = ProjectSprintAssociation(
                sprint_id=sprint.id,
                project_workstream_id=project_workstream.id,
                association_type=association_type,
                project_priority=1,  # Default priority
                is_active=True,
                notes=f"Migrated from sprint data (meta_board_type: {sprint.meta_board_type.value if sprint.meta_board_type else 'single_project'})"
            )
            
            if not self.dry_run:
                self.db.add(association)
            
            self.stats['associations_created'] += 1
            self.stats['sprints_processed'] += 1
        
        logger.info(f"Step 2 complete: {self.stats['associations_created']} associations created")
    
    async def _update_sprint_analyses(self):
        """Update SprintAnalysis records with project information."""
        logger.info("Step 3: Updating sprint analyses with project information...")
        
        # Get sprint analyses that need project information
        stmt = select(SprintAnalysis).join(Sprint).where(
            and_(
                SprintAnalysis.project_key.is_(None),
                Sprint.jira_project_key.isnot(None),
                Sprint.jira_project_key != ''
            )
        )
        result = await self.db.execute(stmt)
        analyses = result.scalars().all()
        
        logger.info(f"Updating {len(analyses)} sprint analyses")
        
        for analysis in analyses:
            # Get the sprint to extract project info
            sprint_stmt = select(Sprint).where(Sprint.id == analysis.sprint_id)
            sprint_result = await self.db.execute(sprint_stmt)
            sprint = sprint_result.scalar_one_or_none()
            
            if sprint and sprint.jira_project_key:
                if not self.dry_run:
                    analysis.project_key = sprint.jira_project_key
                    analysis.project_name = sprint.jira_project_key  # Use key as name initially
                
                self.stats['analyses_updated'] += 1
        
        logger.info(f"Step 3 complete: {self.stats['analyses_updated']} analyses updated")
    
    async def _generate_baseline_metrics(self):
        """Generate baseline ProjectSprintMetrics for recent sprints."""
        logger.info("Step 4: Generating baseline metrics for recent sprints...")
        
        # Get recent sprint associations (last 3 months)
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        stmt = select(ProjectSprintAssociation).join(Sprint).where(
            and_(
                ProjectSprintAssociation.is_active == True,
                Sprint.start_date >= cutoff_date
            )
        )
        result = await self.db.execute(stmt)
        associations = result.scalars().all()
        
        logger.info(f"Generating baseline metrics for {len(associations)} recent sprint-project combinations")
        
        for association in associations:
            # Check if metrics already exist
            existing_stmt = select(ProjectSprintMetrics).where(
                and_(
                    ProjectSprintMetrics.sprint_id == association.sprint_id,
                    ProjectSprintMetrics.project_workstream_id == association.project_workstream_id
                )
            )
            existing_result = await self.db.execute(existing_stmt)
            existing_metrics = existing_result.scalar_one_or_none()
            
            if existing_metrics:
                continue
            
            # Create baseline metrics
            metrics = ProjectSprintMetrics(
                sprint_id=association.sprint_id,
                project_workstream_id=association.project_workstream_id,
                total_issues=0,  # Would be populated by actual analysis
                completed_issues=0,
                in_progress_issues=0,
                blocked_issues=0,
                total_story_points=association.expected_story_points or 0.0,
                completed_story_points=association.actual_story_points or 0.0,
                in_progress_story_points=0.0,
                completion_percentage=0.0,
                bug_count=0,
                critical_issues_count=0,
                scope_change_count=0,
                scope_added_points=0.0,
                scope_removed_points=0.0,
                metrics_date=datetime.utcnow(),
                issue_breakdown={'migrated': True, 'needs_analysis': True},
                team_breakdown={'migrated': True, 'needs_analysis': True},
                timeline_breakdown={'migrated': True, 'needs_analysis': True}
            )
            
            if not self.dry_run:
                self.db.add(metrics)
            
            self.stats['metrics_created'] += 1
        
        logger.info(f"Step 4 complete: {self.stats['metrics_created']} baseline metrics created")


async def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description='Migrate project data from existing sprint records')
    parser.add_argument('--dry-run', action='store_true', help='Run migration without committing changes')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for processing')
    
    args = parser.parse_args()
    
    logger.info("Starting project data migration")
    logger.info(f"Configuration: dry_run={args.dry_run}, batch_size={args.batch_size}")
    
    # Get database session
    db_session = await get_db_session()
    
    try:
        # Create migrator and run migration
        migrator = ProjectDataMigrator(db_session, args.dry_run, args.batch_size)
        stats = await migrator.migrate_all_data()
        
        # Print final statistics
        logger.info("Migration completed successfully!")
        logger.info("Final Statistics:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return 1
    
    finally:
        await db_session.close()


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))