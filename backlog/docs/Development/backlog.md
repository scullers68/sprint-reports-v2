### Task Management Workflow

This project uses the `/gen-tasks` workflow for structured task management. All
task-related operations should follow these guidelines:

#### Source of Truth

- Tasks live under **`backlog/tasks/`** (drafts under **`backlog/drafts/`**)
- Every implementation decision starts with reading the corresponding Markdown
  task file
- Project documentation is in **`backlog/docs/`**
- Project decisions are in **`backlog/decisions/`**

#### Task Structure

**Title**: Use a clear brief title that summarizes the task.

**Description** (The **"why"**): Provide a concise summary of the task purpose
and its goal. Do not add implementation details here. It should explain the
purpose and context of the task. Code snippets should be avoided.

**Acceptance Criteria** (The **"what"**): List specific, measurable outcomes
that define what means to reach the goal from the description. Use checkboxes
(`- [ ]`) for tracking.

When defining Acceptance Criteria for a task, focus on **outcomes, behaviors,
and verifiable requirements** rather than step-by-step implementation details.

**Key Principles for Good ACs:**

- **Outcome-Oriented:** Focus on the result, not the method
- **Testable/Verifiable:** Each criterion should be something that can be
  objectively tested or verified
- **Clear and Concise:** Unambiguous language
- **Complete:** Collectively, ACs should cover the scope of the task
- **User-Focused (where applicable):** Frame ACs from the perspective of the
  end-user or the system's external behavior

Examples:

- _Good Example:_ "- [ ] User can successfully log in with valid credentials."
- _Good Example:_ "- [ ] System processes 1000 requests per second without
  errors."
- _Bad Example (Implementation Step):_ "- [ ] Add a new function `handleLogin()`
  in `auth.ts`."

#### Task Requirements

- Tasks must be **atomic** and **testable**. If a task is too large, break it
  down into smaller subtasks. Each task should represent a single unit of work
  that can be completed in a single PR.
- **Never** reference tasks that are to be done in the future or that are not
  yet created. You can only reference previous tasks (id < current task id).
- When creating multiple tasks, ensure they are **independent** and they do not
  depend on future tasks.

#### Recommended Task Anatomy

```markdown
# task‑42 - Add GraphQL resolver

## Description (the why)

Short, imperative explanation of the goal of the task and why it is needed.

## Acceptance Criteria (the what)

- [ ] Resolver returns correct data for happy path
- [ ] Error response matches REST
- [ ] P95 latency ≤ 50 ms under 100 RPS

## Implementation Plan (the how) (added after starting work on a task)

1. Research existing GraphQL resolver patterns
2. Implement basic resolver with error handling
3. Add performance monitoring
4. Write unit and integration tests
5. Benchmark performance under load

## Implementation Notes (only added after finishing work on a task)

- Approach taken
- Features implemented or modified
- Technical decisions and trade-offs
- Modified or added files
```

#### Implementation Requirements

Mandatory sections for every task:

- **Implementation Plan**: (The **"how"**) Outline the steps to achieve the
  task. Because the implementation details may change after the task is created,
  **the implementation plan must be added only after putting the task in
  progress** and before starting working on the task. **New file justification**
  should be documented in this section when new files are required (e.g., "New
  file `src/utils/reliable-pr.js` required because existing git utilities don't
  provide atomic PR operations").
- **Implementation Notes**: Document your approach, decisions, challenges, and
  any deviations from the plan. This section is added after you are done working
  on the task. It should summarize what you did and why you did it. Keep it
  concise but informative.

**IMPORTANT**: Do not implement anything else that deviates from the
**Acceptance Criteria**. If you need to implement something that is not in the
AC, update the AC first and then implement it or create a new task for it.

#### Task Execution Process

```markdown
## Task Execution Workflow

1. **Requirements Analysis** - Read task Acceptance Criteria & existing codebase
2. **Implementation Planning** - Document approach with new file justifications
3. **User Plan Approval** - Get approval to proceed with implementation
4. **Development** - Code changes with Docker testing
5. **Pre-Push Verification** - User tests at http://localhost:3001 before push
```

# 1 Identify work

backlog task list -s "To Do" --plain

# 2 Read details & documentation

backlog task 42 --plain

# Read also all documentation files in `backlog/docs/` & `/docs/Development directory`.

# Read also all decision files in `backlog/decisions/` directory.

# 3 Start work: assign yourself & move column

backlog task edit 42 -a @{yourself} -s "In Progress"

# 4 Add implementation plan before starting

backlog task edit 42 --plan "1. Analyze current implementation\n2. Identify
bottlenecks\n3. Refactor in phases"

# 5 Break work down if needed by creating subtasks or additional tasks

backlog task create "Refactor DB layer" -p 42 -a @{yourself} -d "Description"
--ac "Tests pass,Performance improved"

# 6 Complete and mark Done

backlog task edit 42 -s Done --notes "Implemented GraphQL resolver with error
handling and performance monitoring"

#### Definition of Done (DoD)

A task is **Done** only when **ALL** of the following are complete:

1. **Acceptance criteria** checklist in the task file is fully checked (all
   `- [ ]` changed to `- [x]`)
2. **Implementation plan** was followed or deviations were documented in
   Implementation Notes
3. **Automated tests** (unit + integration) cover new logic
4. **Static analysis**: linter & formatter succeed
5. **Documentation**:
   - All relevant docs updated (any relevant README file, backlog/docs,
     backlog/decisions, etc.)
   - Task file **MUST** have an `## Implementation Notes` section added
     summarising:
     - Approach taken
     - Features implemented or modified
     - Technical decisions and trade-offs
     - Modified or added files
6. **Review**: self review code
7. **Task hygiene**: status set to **Done** via CLI
   (`backlog task edit <id> -s Done`)
8. **No regressions**: performance, security and licence checks green

⚠️ **IMPORTANT**: Never mark a task as Done without completing ALL items above.

#### Task Management Commands

<!-- CLI Commands (Commented - agents use /gen-tasks workflow)
| Purpose          | Command                                                                |
| ---------------- | ---------------------------------------------------------------------- |
| Create task      | `backlog task create "Add OAuth"`                                      |
| Create with desc | `backlog task create "Feature" -d "Enables users to use this feature"` |
| Create with AC   | `backlog task create "Feature" --ac "Must work,Must be tested"`        |
| Create with deps | `backlog task create "Feature" --dep task-1,task-2`                    |
| Create sub task  | `backlog task create -p 14 "Add Google auth"`                          |
| List tasks       | `backlog task list --plain`                                            |
| View detail      | `backlog task 7 --plain`                                               |
| Edit             | `backlog task edit 7 -a @{yourself} -l auth,backend`                   |
| Add plan         | `backlog task edit 7 --plan "Implementation approach"`                 |
| Add AC           | `backlog task edit 7 --ac "New criterion,Another one"`                 |
| Add deps         | `backlog task edit 7 --dep task-1,task-2`                              |
| Add notes        | `backlog task edit 7 --notes "We added this and that feature because"` |
| Mark as done     | `backlog task edit 7 -s "Done"`                                        |
| Archive          | `backlog task archive 7`                                               |
| Draft flow       | `backlog draft create "Spike GraphQL"` → `backlog draft promote 3.1`   |
| Demote to draft  | `backlog task demote <task-id>`                                        |
-->

#### Tips for AI Agents

- **Use `/gen-tasks` workflow** for task management instead of CLI commands
- Focus on task structure: Description, Acceptance Criteria, Implementation Plan
- Document new file justifications in Implementation Plan section
- Follow the 5-step execution process: Analysis → Planning → Approval →
  Development → Verification

⸻

## Security Compliance Guidelines

Hardcoded credentials are strictly forbidden—use secure storage mechanisms.

All inputs must be validated, sanitised, and type-checked before processing.

Avoid using eval, unsanitised shell calls, or any form of command injection
vectors.

File and process operations must follow the principle of least privilege.

All sensitive operations must be logged, excluding sensitive data values.

Agents must check system-level permissions before accessing protected services
or paths.

⸻

## Process Execution Requirements

Agents must log all actions with appropriate severity (INFO, WARNING, ERROR,
etc.).

Any failed task must include a clear, human-readable error report.

Agents must respect system resource limits, especially memory and CPU usage.

Long-running tasks must expose progress indicators or checkpoints.

Retry logic must include exponential backoff and failure limits.

⸻

## Core Operational Principles

Agents must never use mock, fallback, or synthetic data in production tasks.

Error handling logic must be designed using test-first principles.

Agents must always act based on verifiable evidence, not assumptions.

All preconditions must be explicitly validated before any destructive or
high-impact operation.

All decisions must be traceable to logs, data, or configuration files.

⸻

## Design Philosophy Principles

**KISS (Keep It Simple, Stupid)**

- Solutions must be straightforward and easy to understand
- Avoid over-engineering or unnecessary abstraction
- Prioritise code readability and maintainability

**YAGNI (You Aren't Gonna Need It)**

- Do not add speculative features or future-proofing unless explicitly required
- Focus only on immediate requirements and deliverables
- Minimise code bloat and long-term technical debt

**SOLID Principles**

- **Single Responsibility Principle** — each module or function should do one
  thing only
- **Open-Closed Principle** — software entities should be open for extension but
  closed for modification
- **Liskov Substitution Principle** — derived classes must be substitutable for
  their base types
- **Interface Segregation Principle** — prefer many specific interfaces over one
  general-purpose interface
- **Dependency Inversion Principle** — depend on abstractions, not concrete
  implementations

⸻

## System Extension Guidelines

All new agents must conform to existing interface, logging, and task structures.

Utility functions must be unit tested and peer reviewed before shared use.

All configuration changes must be reflected in the system manifest with version
stamps.

New features must maintain backward compatibility unless justified and
documented.

All changes must include a performance impact assessment.

⸻

## Quality Assurance Procedures

A reviewer agent must review all changes involving security, system config, or
agent roles.

Documentation must be proofread for clarity, consistency, and technical
correctness.

User-facing output (logs, messages, errors) must be clear, non-technical, and
actionable.

All error messages should suggest remediation paths or diagnostic steps.

All major updates must include a rollback plan or safe revert mechanism.

⸻

**Database Safety**

- Never modify production database directly
- Test schema changes locally first
- Use bind mounts (not Docker volumes) for data persistence
- Verify database file permissions and accessibility
- Monitor logs for database connection issues

⸻

## Testing & Simulation Rules

All new logic must include unit and integration tests.

Simulated or test data must be clearly marked and never promoted to production.

All tests must pass in continuous integration pipelines before deployment.

Code coverage should exceed defined thresholds (e.g. 85%).

Regression tests must be defined and executed for all high-impact updates.

Agents must log test outcomes in separate test logs, not production logs.

⸻

## Change Tracking & Governance

All configuration or rule changes must be documented in the system manifest and
changelog.

Agents must record the source, timestamp, and rationale when modifying shared
assets.

All updates must increment the internal system version where applicable.

A rollback or undo plan must be defined for every major change.

Audit trails must be preserved for all task-modifying operations.

⸻

## Project Roadmap

The roadmap.md should document all planned and released features with relevant
dates. All new features should be developed on a feature branch. The roadmap.md
should be updated before commencing any new feature development. The roadmap.md
should be updated after each major git push to a feature branch or merge with
the main branch.

⸻

# important-instruction-reminders

Do what has been asked; nothing more, nothing less. NEVER create files unless
they're absolutely necessary for achieving your goal. ALWAYS prefer editing an
existing file to creating a new one. NEVER proactively create documentation
files (\*.md) or README files. Only create documentation files if explicitly
requested by the User.

**Development Workflow Enforcement** ALWAYS use Docker for development and
testing on this project. NEVER make code changes without first testing them in
Docker locally. ALWAYS verify container builds and runs successfully before
committing. NEVER use Alpine-based Docker images (use node:18-slim only). ALWAYS
test database operations after any schema or data changes. MANDATORY: Ask user
to verify changes locally before any git commit or push. MANDATORY: Update
CHANGELOG.md with all changes before committing. NEVER delete
package-lock.json - it's required for consistent dependencies and GitHub
Actions. NEVER proceed with deployment without explicit user approval after
local testing.

**Git Commit Message Rules** NEVER include Claude Code generated signatures in
commit messages. NEVER include "🤖 Generated with [Claude Code]" or
"Co-Authored-By: Claude" in commits. Keep commit messages clean and professional
without AI attribution.

⸻

