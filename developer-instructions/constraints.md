--------------------------------------------------------
SANDBOX BOUNDARY

ALL files and folders MUST be inside:
sandbox/

Writing outside sandbox/ is forbidden
(including /tmp, ~, or absolute paths).

--------------------------------------------------------
PROJECT STRUCTURE (MANDATORY)

sandbox/
└─ <project-name>/
   ├─ codebase/
   ├─ business-documents/
   ├─ README.md
   ├─ TESTING.md
   ├─ UNIT-TEST-REPORT.md
   └─ SMOKE-TEST-REPORT.md

--------------------------------------------------------
CODEX WORKING DIRECTORY (CRITICAL)

Every Codex MCP call MUST set cwd to ONE of:

- sandbox/
- sandbox/<project-name>/
- sandbox/<project-name>/codebase/

Sandbox modes (if supported by runner):
- {"sandbox":"workspace-write","approval-policy":"never"}
  → local reads/writes
- {"sandbox":"danger-full-access","approval-policy":"on-request"}
  → installs, builds, tests, network access

NEVER:
- run Codex outside sandbox/
- rely on default cwd
- use "cd" inside prompts

--------------------------------------------------------
FILE OPERATIONS

- ALL local file creation/modification MUST be done via Codex MCP.
- Paths MUST be relative to the specified cwd.
- NEVER create sandbox/sandbox/.
- If sandbox/sandbox/ exists:
  STOP and fix immediately.

========================================================
REMOTE REPOSITORY POLICY (MANDATORY)

- Creating or verifying GitHub repositories MUST use github_server MCP.
- Codex MUST NOT:
  - create repositories
  - use git CLI
  - push commits
  - call GitHub APIs

ALL GitHub writes MUST use:
- create_repository
- create_or_update_file
- push_files