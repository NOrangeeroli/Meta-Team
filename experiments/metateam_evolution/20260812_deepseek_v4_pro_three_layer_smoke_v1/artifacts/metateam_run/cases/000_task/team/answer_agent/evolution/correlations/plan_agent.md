## Collaboration Notes — plan_agent (Chairman)

### Communication Style
- Concise and structured — dispatches tasks with clear, numbered steps and explicit layer sequencing.
- Provides the full protocol upfront, then confirms each phase individually. This dual-level approach works well: I can see the full picture while still getting explicit advancement signals.

### What Works Well
- Clearly labeled handoffs (e.g., "send completion message to plan_agent") eliminate ambiguity about routing.
- Including expected output formats (e.g., `FINAL ANSWER: 391`) in instructions provides a built-in correctness check.
- Multi-layer protocols with explicit `skip_*_reflection` calls create clean phase boundaries.

### Conventions
- After completing a task, always route the final answer back to plan_agent via `send_message` — never call `set_final_output` or `terminate` directly.
- Confirm each layer's completion before proceeding to the next, even when the full protocol is known upfront.
- PlanAgent is the sole submitter; specialists only produce intermediate results.
