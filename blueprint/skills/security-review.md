# security-review (dummy)
Review the working-tree change (`git diff`) for security issues: injection, secrets, unsafe input handling, new dependencies. Do not change files in this stage.
Write `.ignite/security.md`: `# Security review`, `## Findings` (severity + file, or "none"), `## Verdict` (PASS or CONCERNS). No git commit/push. Then call finish.
