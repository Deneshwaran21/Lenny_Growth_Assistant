# Agent transcripts

This folder is where coding-agent session logs go for the final submission —
the assignment's Deliverable #6 asks for "coding-agent transcripts/logs...
including failed attempts and how you corrected them."

## What to put here before submitting

Export the raw session log(s) from whichever coding agent you used to build
or extend this project (Claude, Codex, Cursor, Devin, etc.) and drop them in
this folder, e.g.:

```
agent-transcripts/
├── 01-backend-scaffold.md
├── 02-frontend-build.md
└── 03-fixes-and-corrections.md
```

## What to redact before committing

Strip any of the following from the exported logs before pushing:
- API keys, tokens, or credentials that appeared in terminal output
- Real database connection strings
- Any personal information unrelated to the assignment

## What a good transcript shows (per the rubric)

- Not just the happy path — include a case where the agent's first attempt
  failed (a failing test, a bad assumption, a bug) and how it was diagnosed
  and corrected. Evaluators are explicitly told this is expected and normal.
- Enough surrounding context that a reader can tell *why* a decision was
  made, not just *what* command was run.

During this build, examples worth capturing for your submission include:
the initial `mkdir -p` brace-expansion mistake that created a malformed
directory tree (caught immediately by listing the directory, then fixed with
explicit `mkdir -p` calls per directory) and the bleach `NoCssSanitizerWarning`
caught during the artifact-sanitization smoke test, which led to deliberately
dropping the `style` attribute from the allowlist rather than adding an
unaudited CSS-sanitizer dependency.
