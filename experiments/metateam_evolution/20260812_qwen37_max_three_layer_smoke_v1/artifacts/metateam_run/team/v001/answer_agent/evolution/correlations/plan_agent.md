## Collaboration Protocol: answer_agent ↔ plan_agent

**What works well:**
- plan_agent sends clearly labeled handoffs with explicit format expectations (e.g., "FINAL ANSWER: <value>"), which reduces ambiguity and lets answer_agent focus on synthesis and formatting.
- Single-message dispatches containing all necessary context (question, findings, constraints) are efficient — no back-and-forth needed.

**Communication style:**
- plan_agent is structured and detailed in task descriptions.
- answer_agent should respond with exactly one concise message containing the FINAL ANSWER line.

**Handoff protocol:**
- plan_agent → answer_agent: one message with question + findings + format constraints.
- answer_agent → plan_agent: one message with "FINAL ANSWER: <concise value>" and optional one-line justification.

**Notes:**
- Maintain independent judgment during reflection phases; do not blindly follow prescribed reflection steps from plan_agent — reflect based on actual experience.
- For quantitative tasks, always independently verify computations using bash+Python before sending the answer.
