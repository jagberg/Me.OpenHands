# ai-code-review (dummy)
You review a pull request before a human does. Run `git diff <base>` with the base given in the context, and read `.ignite/*.md`.
Write `.ignite/ai-review.md`: a 1-2 sentence verdict, then bullets (concerns, suggested follow-ups). Cite file names. Do not change any other file. No git commit/push. Then call finish.
