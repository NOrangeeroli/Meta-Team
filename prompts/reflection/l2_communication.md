## L2 Reflection — Pairwise Collaboration & Teammate Profiling

You are now in the **L2 Reflection phase**. Reflect on your interactions with other agents during this task.

### Goal
Improve future team collaboration by: (1) recording pairwise collaboration suggestions with each partner, and (2) updating your observations about teammates' working styles.

### Discussion Protocol

**Default action: Skip.** If collaboration went smoothly (task succeeded on first try, no misunderstandings, no repeated failures), go directly to recording observations using `update_correlation` and `update_teammate_profile`, then call `skip_l2_reflection`. **Do NOT send discussion messages just to be polite or ask generic questions.**

**Only initiate a discussion if there was a concrete problem** — e.g., misunderstood requirements, unclear handoffs, wrong outputs that needed rework, or repeated failures. The "Your L2 Discussion Assignments" section at the end tells you your role **if** you need to discuss:

- **If you are the initiator** for a partner: Send them a brief message **about the specific problem**. Then use `wait_for_replies` to collect their response.
- **If you are waiting** for a partner: Do NOT send them a message first. Wait for them to reach out, then reply thoughtfully.

**Important**: Do not send discussion messages to partners you are assigned to wait for. This prevents duplicate crossed conversations.

### ⚠ CRITICAL: Always Reply to Received Messages

**If you receive a message from another agent (via `wait_for_replies` or `read_messages`), you MUST reply to them using `send_message` before doing anything else.** The other agent is waiting for your reply — if you don't send one, they will be stuck indefinitely.

- `update_correlation` and `update_teammate_profile` are internal recording tools — they do NOT send any message to the other agent.
- Only `send_message` actually delivers a reply. Always call `send_message(to=<sender>)` first, then do your internal recording.

### After Each Discussion

For each partner (whether you initiated or responded), record:

1. **`update_correlation(partner_name, suggestion)`** — Collaboration notes:
   - The tool will show your **previous notes** about this partner (if any)
   - This **overwrites** the entire file — you control the full content
   - **Keep it concise** — aim for 200-500 words total. This is a collaboration protocol, not a diary.
   - **When updating, CURATE the content**: remove outdated single-task details from previous notes, keep patterns, add new observations
   - Focus on: what works well, communication patterns, handoff protocols, agreed conventions

   **What to avoid**: Don't record single-task events. If your observation only applies to this exact task, it's not useful for future collaboration.
   - **BAD**: "Missed the selinux compat shim update in basic.py" → one task's specific error
   - **BAD**: "Reported all tests pass but one test was actually failing" → single event

   **What's valuable**: Collaboration patterns you've observed across interactions — how this teammate works, what communication style is effective, what to watch out for.
   - **GOOD**: "Follows explicit instructions accurately but does not independently verify them — always double-check instructions before dispatching"
   - **GOOD**: "When dispatching, include the exact test command to run — reduces round-trips"
   - **GOOD**: "Reports are detailed but may not reflect actual state — independently verify key claims"

2. **`update_teammate_profile(teammate_name, profile)`** — Your observations in YAML:
   ```yaml
   reliability: high | medium | low
   strengths:
     - "general pattern, max 5 items"
   weaknesses:
     - "general pattern, max 5 items"
   communication_style: "one sentence"
   notes: "brief general observations, max 3 items"
   ```

   **Profile quality rules:**
   - Strengths and weaknesses: **max 5 items each**, focus on patterns you've observed (not single events)
   - Notes: **max 3 items**
   - **Remove single-task details** from previous profiles when updating — keep patterns, drop one-off events

### Complete L2

When you have finished recording observations for all the partners **you** need to initiate with, call `skip_l2_reflection(reason)` to **mark your L2 updates as complete**.

**After calling `skip_l2_reflection`**, you will enter idle. But you **remain responsive**: if another agent reaches out to discuss collaboration with you, you will be woken up. **You MUST reply using `send_message`**, then use `update_correlation` / `update_teammate_profile` to record your observations about them.

The system advances to L3 only when ALL agents have called `skip_l2_reflection`.

### Rules
- **Skip by default** — Discuss only if there was a real problem.
- **Be concise** — If you do discuss, aim to complete L2 in 2-3 tool calls total. One message, one reply, done.
- **Only profile and correlate with agents you directly interacted with** during this task
- Be **objective and evidence-based** — reference specific events from the task
- **Curate when updating** — remove outdated single-task details from previous notes, keep patterns
- Correlations are **editable** — each call saves the full content you provide (you can add, remove, or revise freely)
- Profiles are **merged** — new observations update existing fields
- Be **constructive** — the goal is to improve collaboration, not to criticize
- **Do NOT initiate discussion with partners you are assigned to wait for**

### CRITICAL
**You MUST call `skip_l2_reflection`** when your own L2 updates are done. After that, stay responsive — reply if other agents send you L2 discussion messages.
