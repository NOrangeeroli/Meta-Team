---
name: research-report-workflow
description: Structured 5-step workflow for producing long-form research reports that satisfy rubric-based evaluation across 6 axes (Explicit, Implicit, Synthesis, Communication, Instruction Following, References).
trigger: Load this when you receive a research report task in Solo Mode, or before dispatching a research task to a specialist in Chairman Mode.
---

# Research Report Workflow

A 5-step pipeline for producing evidence-backed research reports. Each step
maps to specific rubric axes. Follow it strictly in Solo Mode; use it to
structure your dispatches in Chairman Mode.

## Step 1: Decompose the Prompt

Parse the user prompt into an **explicit requirement checklist**. You'll
return to this checklist in Step 5 to make sure nothing is missed.

Three kinds of requirements:

1. **Explicit requirements** — things the prompt literally asks for
   (e.g., "include a section on X", "cover at least 5 years", "provide a
   competitor analysis"). Copy each as a checklist item.

2. **Implicit requirements** — things a domain expert knows should be
   included but the prompt didn't spell out (e.g., defining acronyms,
   citing authoritative sources, covering dominant alternative views).
   These come from domain knowledge, not the prompt.

3. **Anti-requirements (Instruction Following)** — things the prompt
   explicitly rules out (e.g., "don't include monetization discussion",
   "keep under 1 page"). List these too — forgetting them tanks the
   Instruction Following axis.

Output of this step: an internal checklist you'll use throughout.

## Step 2: Plan Your Searches

Before searching, map checklist items to search queries. Aim for:

- **2-5 distinct search queries** covering the main themes. Don't issue
  10 minor variations of the same query.
- **Broad first, then narrow.** Start with a general query to orient
  yourself; then drill down based on what you learn.
- **English queries** — Serper/Google returns better results in English.

Avoid: generic fishing ("latest research on X") without a target. Every
query should be tied to a specific checklist item.

## Step 3: Search and Read

Execute searches and selectively read pages:

1. For each planned query, call `web_search(query="...")`. Note the top 3-5
   results (title + snippet + URL).

2. **Don't `web_fetch` everything.** Fetch only when:
   - The snippet is promising but incomplete, OR
   - You need to cite specific numbers/quotes, OR
   - You need to verify the source is authoritative (matches rubric's
     citation quality requirements).

3. After fetching, **record what you learned**:
   - What facts did this source give you?
   - What URL did they come from?
   - Is this source authoritative? (peer-reviewed > reputable org docs >
     mainstream news > blog posts > forum threads)

Budget discipline: you have a search/visit quota. If you're at 10 searches
with only 3 good sources, stop searching and start writing. More searches
yield diminishing returns.

## Step 4: Verify Before Citing

**Fabricated citations are the #1 killer of the References axis.** Before
including any `<cite url="X">claim</cite>` in the report:

1. Confirm URL X actually came from a `web_search` or `web_fetch` call in
   this session. Never invent URLs.
2. Confirm the page at URL X actually supports the claim. If you haven't
   `web_fetch`-ed the URL, fetch it now — don't cite based on a snippet
   alone if the snippet is ambiguous.
3. When sources disagree, cite both and describe the disagreement.
4. When evidence is thin, say so — this is the "state uncertainty" rule.

## Step 5: Write the Report

Structure the report as a cohesive narrative, not a list of facts.

1. **Front matter** — a 2-3 sentence overview of what the report covers.
2. **Sections** — one per major theme from your checklist. Each section:
   - Opens with a topic sentence
   - Develops with 2-5 sentences of substance + citations
   - Transitions to the next section
3. **Synthesis, not enumeration** — When multiple sources cover the same
   theme, integrate them: "Sources A and B both report X, though A emphasizes
   Y while B focuses on Z." Not: "Source A says X. Source B says X."
4. **Walk the checklist** — Before finalizing, re-read the requirement
   checklist from Step 1. For each item, point to the section that addresses
   it. Items not addressed? Add them or explicitly explain why they're out
   of scope.
5. **Closing** — A brief synthesis pulling the themes together. End with
   `Confidence: X%`.

## Common Failure Modes (and how to avoid them)

| Failure                                      | Typical axis hit            | Prevention                                                             |
| :------------------------------------------- | :-------------------------- | :--------------------------------------------------------------------- |
| Inventing a URL that looks plausible         | References & Citation       | Step 4 — only cite URLs from actual tool results                       |
| Listing sources without integrating them     | Synthesis                   | Step 5.3 — "A and B both report X, though A emphasizes Y"              |
| Missing one of several prompt requirements   | Explicit Criteria           | Step 1's checklist; Step 5.4 walk-through                              |
| Not defining a domain acronym                | Implicit / Communication    | Step 1's "implicit" category; proofread first use of each acronym      |
| Including content the prompt excluded        | Instruction Following       | Step 1's "anti-requirements"; re-check before finalize                 |
| Format issues (broken tables, raw LaTeX)     | Communication Quality       | Plain markdown only; no LaTeX unless you know it renders               |
| No confidence line at the end                | Instruction Following       | Always end with `Confidence: X%`                                       |

## Output

Once Step 5 is complete, the report is ready. Submit it using the required
keyword argument — the `output=` parameter is mandatory:

In **Solo Mode** (non-evolve runs):
```python
set_final_output(output="<the complete markdown report>")
```

In **Chairman Mode** or when **evolve is enabled**:
```python
finalize_task(output="<the complete markdown report>")
```

⚠️ Never call these tools with empty arguments. The `output` string must
contain the full report including the trailing `Confidence: X%` line.
Calling `set_final_output()` or `finalize_task()` without passing `output=`
will return an error and your work won't be saved.
