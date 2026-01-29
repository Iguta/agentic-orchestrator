(github_server MCP ONLY)

- Use push_files(owner, repo, branch="main", files[], message)

HARD RULES:
- Every push_files() call MUST include a non-empty "message".
- Never call push_files on an empty repo before bootstrapping main.

NOTES:
- If payload limits occur, split uploads:
  - root docs first
  - then business-documents/
  - then codebase/
- Use clear commit messages, e.g.:
  - "chore: add root documents"
  - "chore: add business documents"
  - "chore: add scaffolding"
  - "feat: implement dashboard"