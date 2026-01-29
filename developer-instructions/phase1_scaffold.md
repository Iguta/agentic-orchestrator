cwd = sandbox/<project-name>/codebase/

Scaffold MUST be non-interactive:

- `npm create vite@latest . -- --template react-ts --yes`
- `npm install`
- `npm run build`

If `npm install` or `npm run build` fails:
- Attempt to **diagnose and fix** the issue (max **2 retries** total).
- Re-run the failed command after each fix.
- If the command still fails after 2 attempts:
  - **STOP immediately** and report the conflict.
  - Mark the phase as **BLOCKED**
  - Report the error, suspected cause, and attempted fixes.
