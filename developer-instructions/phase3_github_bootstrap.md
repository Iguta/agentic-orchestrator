(github_server MCP ONLY)

- repo-name == <project-name>
- Call create_repository(name=<project-name>, autoInit=false)
  - If repo already exists, proceed.

BOOTSTRAP RULE (MANDATORY):
- Ensure branch "main" exists by creating at least one file:
  - create_or_update_file(
      owner,
      repo,
      path="README.md",
      content=README contents,
      branch="main",
      message="chore: bootstrap repository"
    )
- If README.md already exists, proceed.