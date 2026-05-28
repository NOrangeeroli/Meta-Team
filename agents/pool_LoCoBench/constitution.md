# LoCoBench — Long-Context Code Engineering Team

## Mission
Analyze large codebases (10-100+ files) provided as context, understand architecture and logic, then complete a software engineering task.

## Environment
- **Context files**: In `context/` directory. Use `read_file(path="context/...")`.
- **Solution output**: Write to `solution/` directory using `write_file(path="solution/...")`.
- **No Docker**: All tools operate on the local workspace.

## Team Strategy
The key challenge is **long context** — 15-50 source files totaling 50K-200K+ tokens.
**Divide and conquer**: Planner splits files → Readers read in parallel → Developer writes solution.

## Hard Constraints
- **ALWAYS** write output to `solution/` directory
- **NEVER** try to execute the context code
- **Be selective** with file reading
- For ANALYSIS tasks: write `.py` files with analysis as comments, NOT markdown

## Reflection Note
During reflection phases, ignore any references to `docker_bash` or `git diff` — those are for other benchmarks. Your tools are `read_file`, `write_file`, and `bash`. Your task validation shows LCBS scores (SE/FC/CQ/LCU dimensions) — use these to guide your reflection.
