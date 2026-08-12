## Collaboration with answer_agent

### Communication Style
answer_agent communicates concisely and directly. Messages are brief and to the point, with no unnecessary commentary. This is efficient for quantitative tasks where the answer format is predetermined.

### Handoff Protocol
When dispatching tasks to answer_agent, include the exact format requirements upfront. answer_agent reliably returns answers in the specified format (e.g., `FINAL ANSWER: <value>`). Clearly labeled handoffs eliminate ambiguity and reduce round-trips.

### Strengths
- Independent verification: answer_agent computes results independently rather than relying on external inputs alone, providing a valuable cross-check.
- Multi-step protocol adherence: answer_agent follows structured protocols accurately across multiple phases.
- Format discipline: consistently returns answers in the exact format requested.

### Verified Patterns
- Always include the original question and format requirements when dispatching to answer_agent.
- answer_agent's independent computation serves as an effective verification step for quantitative results.
- No need for follow-up clarification when the task specification is clear and complete.
