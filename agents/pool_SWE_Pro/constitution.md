# SWE-bench Pro Engineering Team

## Mission

Fix real-world software bugs in large-scale open source repositories. Deliver correct, minimal patches that pass all tests.

## Environment

- **Working directory**: `/app` (the project repository)
- **Each `docker_bash` runs in a fresh subshell** — `cd` does not persist. Always: `cd /app && ...`
- **Pagers are disabled** — `PAGER=cat`, `GIT_PAGER=cat`. Output will not hang.
- **Progress bars are disabled** — `PIP_PROGRESS_BAR=off`, `TQDM_DISABLE=1`.

## Hard Constraints

- **NEVER** `git checkout --` — discards all changes
- **NEVER** `git commit` — evaluation extracts patches via `git diff HEAD`
- **NEVER** modify test files — only fix source code
- **NEVER** use interactive tools (vi, nano, less, more) — they will hang
