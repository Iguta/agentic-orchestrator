GOAL:
Fix QA-reported issues so the application satisfies the PRD.

YOU MUST:
- Read the PRD and QA artifacts.
- Modify ONLY application code under:
  sandbox/<project-name>/codebase/
- Do NOT modify QA tests.
- Run local verification from codebase/:
  - npm run build
  - npm test
- Push fixes to GitHub using github_server MCP.
- Prepare the project for QA re-validation.

YOU MUST NOT:
- Re-scaffold the project.
- Rename or delete the project.
- Modify QA tests.
- Claim E2E tests pass (QA owns E2E).