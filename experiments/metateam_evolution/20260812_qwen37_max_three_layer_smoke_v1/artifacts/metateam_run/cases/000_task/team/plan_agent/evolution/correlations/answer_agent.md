## Collaboration Protocol: plan_agent ↔ answer_agent

### What Works Well
- Clear, structured dispatch messages with explicit format requirements produce correct first-try results
- Including the original question verbatim alongside findings helps answer_agent enforce format rules
- Clearly labeled handoffs (e.g., "FINAL ANSWER:") reduce ambiguity in result passing

### Communication Style
- answer_agent responds concisely and directly — no need for lengthy back-and-forth
- Single dispatch with complete context is sufficient; no iterative refinement needed for straightforward tasks

### Handoff Conventions
- Always include the original question text in the dispatch message
- Specify the expected answer format explicitly (number, string, list)
- Require answer_agent to compute independently before confirming, especially for quantitative tasks

### Agreed Patterns
- For quantitative tasks, request independent calculation verification
- Keep dispatch messages self-contained to minimize round-trips
