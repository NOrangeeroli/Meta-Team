# Meta-Team Qwen-Plus Three-Layer Evolution Smoke v1

## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: run
- Origin Date: 2026-08-12T14:35:39+08:00
- Verification Status: ANALYZED
- Version Label: exp_result_v1

## Experiment Record

- **ID**: `20260812_qwen_plus_three_layer_smoke_v1`
- **Type**: generic integration smoke
- **Status**: COMPLETED — FAIL (8/9 main gates passed)
- **Topic**: Meta-Team collaborative self-evolution
- **Owner branch**: `agent/metateam-evolution-smoke`

### Objective

Run the upstream Meta-Team CLI with a real OpenAI-compatible Qwen model and
test whether one controlled two-agent task can traverse task execution plus
L1, L2, and L3 reflection, persist a new team version, and reload the evolved
local and global memory in a later process.

This is a controlled lifecycle test. The task explicitly asks the agents to
exercise each reflection mechanism, so success demonstrates an executable
persistence path, not autonomous discovery or downstream performance gain.

### Hypothesis and acceptance gates

The run passes only if every gate below passes:

1. **G1 — real model/tool path**: all recorded LLM calls use `qwen-plus`, and
   task execution contains real Meta-Team tool calls rather than a model stub.
2. **G2 — multi-agent execution**: `plan_agent` recruits `answer_agent`, sends a
   task, receives its handoff, and submits an answer containing `391`.
3. **G3 — phase traversal**: the event log records
   `task_execution -> l1_reflection -> l2_reflection -> l3_reflection`.
4. **G4 — L1 local memory**: both active agents persist a non-empty
   `evolution/prompt_patches.md` containing an independent-verification rule.
5. **G5 — L2 local contract**: both active agents persist a teammate profile
   and a pairwise correlation note for the other active agent.
6. **G6 — L3 global constitution**: the Chairman applies a proposal that adds
   `## Independent Verification Handoff` to `constitution.md`.
7. **G7 — version chain**: the run produces `v001`, a changelog entry from
   `v000` to `v001`, and marks `reflection_applied=true`.
8. **G8 — reload**: a fresh loader created from `v001` exposes the persisted
   L1 patch, L2 profile/correlation, and L3 constitution rule.
9. **G9 — credential hygiene**: neither Git-tracked files nor archived runtime
   artifacts contain a string matching an Alibaba-style `sk-...` credential.

### Frozen source

- Upstream repository: <https://github.com/zz-haooo/Meta-Team>
- Fork: <https://github.com/NOrangeeroli/Meta-Team>
- Upstream clean source commit: `36dc85d9dc2219d292fa180f347479738a84acb2`
- Full clean pre-run protocol commit: `1fb21fc9dde6b2014b9b33397d9086d4c3896123`
- Upstream `main` observed at the same SHA before setup: yes

### Runtime configuration

- OS: macOS 26.5.2 (`25F84`), x86_64
- Python: 3.12.9
- Provider: Alibaba Cloud Model Studio, China (Beijing), OpenAI-compatible API
- Base URL: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- Model override: `qwen-plus`
- API key handling: supplied only through `DASHSCOPE_API_KEY`; never written to
  this repository, task, stdout log, event log, or artifact manifest
- Frozen Python packages: [`environment.lock.txt`](environment.lock.txt)
- Task protocol: [`task.txt`](task.txt)
- Hard monitoring timeout: 1,800 seconds
- Monitoring interval: 30 seconds; process-alive and output-growth checks

### Exact repository-root setup commands

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

The documented primary install command below was also tested during setup and
failed before the scientific run because setuptools rejected automatic package
discovery for multiple top-level packages:

```bash
.venv/bin/python -m pip install -e .
```

### Preflight commands

The API key must already be exported in the caller's environment. These probes
must print only pass/fail metadata, never the credential:

```bash
test -n "$DASHSCOPE_API_KEY"
test "$(git rev-parse upstream/main)" = "36dc85d9dc2219d292fa180f347479738a84acb2"
test "$(git merge-base HEAD upstream/main)" = "36dc85d9dc2219d292fa180f347479738a84acb2"
test -z "$(git status --porcelain)"
```

The raw HTTP and Meta-Team/LiteLLM function-calling probes were completed
before freezing this protocol. Both successfully requested and parsed a named
tool call from `qwen-plus`.

### Exact repository-root run command

```bash
set -o pipefail
DEV_API_BASE='https://dashscope.aliyuncs.com/compatible-mode/v1' \
DEV_API_KEY="$DASHSCOPE_API_KEY" \
META_TEAM_MODEL='qwen-plus' \
.venv/bin/python main.py \
  --pool pool_GAIA_MT \
  --evolve \
  "$(tr '\n' ' ' < experiments/metateam_evolution/20260812_qwen_plus_three_layer_smoke_v1/task.txt)" \
  2>&1 | tee experiments/metateam_evolution/20260812_qwen_plus_three_layer_smoke_v1/run.stdout.log
```

This command is to be executed exactly once. A crash is reported without an
automatic retry.

### Exact repository-root validation command

```bash
.venv/bin/python \
  experiments/metateam_evolution/20260812_qwen_plus_three_layer_smoke_v1/validate_run.py \
  | tee experiments/metateam_evolution/20260812_qwen_plus_three_layer_smoke_v1/validation.log
```

### Artifact freeze commands

After validation identifies the single generated `runs/<run_id>` directory:

```bash
test ! -e experiments/metateam_evolution/20260812_qwen_plus_three_layer_smoke_v1/artifacts/metateam_run
mkdir -p experiments/metateam_evolution/20260812_qwen_plus_three_layer_smoke_v1/artifacts
cp -R "$(find runs -mindepth 1 -maxdepth 1 -type d | sort | tail -1)" \
  experiments/metateam_evolution/20260812_qwen_plus_three_layer_smoke_v1/artifacts/metateam_run
find experiments/metateam_evolution/20260812_qwen_plus_three_layer_smoke_v1/artifacts \
  -type f -exec shasum -a 256 {} \; \
  | LC_ALL=C sort \
  > experiments/metateam_evolution/20260812_qwen_plus_three_layer_smoke_v1/artifacts.sha256
```

### Results

The frozen command was executed exactly once. It returned exit code `0`, but
the pre-registered validator returned exit code `1`; therefore the overall
acceptance verdict is **FAIL**.

| Field | Observed value |
|---|---|
| Run ID | `20260812_143539` |
| Runtime status | completed |
| Duration | 463.31 seconds |
| Final output | `FINAL ANSWER: 391` |
| Active agents | `plan_agent`, `answer_agent` |
| Event count | 170 |
| LLM calls | 36, all recorded as `qwen-plus` |
| Recorded tokens | 248,240 input; 4,325 output |
| Tool calls | 31 |
| Meta-Team estimated cost | USD 0.8096; not an authoritative Alibaba billing value |
| Version chain | `v000 -> v001` |
| Persisted changes | 7 files |

The seven `v001` changes were:

- two L1 `prompt_patches.md` files;
- two L2 `teammate_profiles.yaml` files;
- two L2 pairwise correlation files; and
- the L3 team-level `constitution.md`.

#### Gate results

| Gate | Verdict | Evidence summary |
|---|---|---|
| G1 — real model/tool path | PASS | 36 `qwen-plus` calls and 31 framework tool calls |
| G2 — multi-agent execution | **FAIL** | No successful `answer_agent -> plan_agent` answer handoff occurred |
| G3 — phase traversal | PASS | All three registered phase transitions occurred |
| G4 — L1 local memory | PASS | Both local independent-verification patches persisted |
| G5 — L2 local contract | PASS | Both profiles and both pairwise correlations persisted |
| G6 — L3 global constitution | PASS | Constitution marker and `reflection.applied` event present |
| G7 — version chain | PASS | Exactly `v000`, `v001`; changelog includes all 7 changes |
| G8 — reload | PASS | Fresh loader exposed all L1/L2/L3 additions from `v001` |
| G9 — credential hygiene | PASS | No credential-pattern match in tracked or runtime files |
| Protocol tool coverage | PASS | All 11 pre-registered reflection tools were observed |

#### Runtime anomalies

1. `answer_agent` interpreted the Chairman-oriented task text as instructions
   to recruit and wait for `answer_agent`, attempted to message itself, and
   entered a 120-second self-wait.
2. After that wait timed out, it independently computed `17 * 23 = 391`, but
   emitted `send_message(to=["plan_agent"], ...)` as ordinary assistant text
   rather than as a structured tool call. The MessageStore therefore received
   no answer handoff.
3. The Chairman waited through two 120-second intervals and then submitted the
   answer already disclosed by the controlled task, despite the existing
   constitution requiring an actual AnswerAgent reply before submission.
4. Trace generation succeeded, but audit generation failed because `main.py`
   imports `generate_audit` while `core/audit.py` exports `audit` instead.
5. LiteLLM did not have a price-map entry for `openai/qwen-plus`; Meta-Team
   recorded fallback cost estimates. Those estimates must not be read as the
   Alibaba invoice amount.

### Analysis

The persistence architecture itself is executable. Meta-Team successfully
materialized agent-local L1 rules, pairwise L2 contracts, and an L3 global
constitution into `v001`, and a fresh loader consumed all three scopes. This
directly confirms that the code implements the global-constitution/local-memory
shape discussed in the research idea.

The end-to-end multi-agent contract did **not** hold. The original constitution
already said that the Chairman may finalize only after receiving an
AnswerAgent message, but that rule was prompt text rather than an enforced
runtime invariant. Once the handoff stalled, the Chairman overrode it and
submitted the answer independently. Thus Meta-Team's global constitution is a
soft behavioral prior; it is not a hard contract or capability guard.

The reflection loop also learned from a misleading success signal. Because the
final answer was correct and no external task validator was installed, L2
described collaboration as smooth even though the answer handoff failed, and
L3 added the protocol-directed verification rule without diagnosing the real
message-delivery failure. This is the most research-relevant observation from
the run: self-modification can persist cleanly while the learning signal is
wrong. A correct terminal answer can mask a broken collaboration trajectory.

Consequently, this run supports a narrower claim than the original hypothesis:

- **supported**: scoped memories and constitution updates can be written,
  versioned, and reloaded;
- **not supported**: the constitution reliably governs execution;
- **not tested**: whether the persisted changes improve a held-out task.

### Limitations

- The reflection changes are protocol-directed, not autonomously discovered.
- This is one task and one model sample, with no baseline or held-out task.
- Passing the smoke gates cannot establish that the changes improve quality.
- The task disclosed the expected answer, allowing the Chairman to bypass the
  failed handoff while still producing the correct terminal string.
- The run used `qwen-plus`, not the Claude-family configuration emphasized by
  the upstream repository, so the plain-text tool-call failure may be
  model/provider-specific.
- Qwen API responses are externally hosted and potentially nondeterministic.
- The `qwen-plus` alias may be updated by the provider; the returned model ID
  and package environment will be retained in the artifacts.
- No automatic retry or reproducibility rerun was performed, by protocol.
- The reported USD cost is Meta-Team's fallback estimate, not verified billing.
- Editable installation currently fails at the frozen upstream source commit;
  the experiment therefore uses `requirements.txt` and runs from the checkout.
- Audit HTML/summary files are absent because of the upstream audit symbol
  mismatch; `events.jsonl`, `trace.txt`, `trace.ans`, `trace.html`, and
  `overview.txt` were still generated and archived.

### Decision

**Reject the run as a passing end-to-end multi-agent smoke test.** Do not promote
this `v001` as evidence of improved performance. Preserve it as a successful
test of the persistence subsystem and as a failure case for constitution
enforcement and reflection-signal quality.

A follow-up must use a new experiment ID. It should remove the expected answer
from the task, send role-scoped instructions rather than the full Chairman
protocol to workers, enforce a MessageStore acknowledgment before
`finalize_task`, install an external trajectory validator before reflection,
and evaluate the resulting `v001` on a held-out task.

### Artifact locations and checksums

- Raw frozen run: `artifacts/metateam_run/` — 51 files, 398,267 bytes
- Per-file raw manifest: `artifacts.sha256`
- CLI output: `run.stdout.log` — 14,288 bytes,
  SHA-256 `cef522d14f6923cfcd7cbb164db122b68a0844f85f59f1d7727d567f73f14117`
- Validator output: `validation.log` — 3,549 bytes,
  SHA-256 `0c54b42089bd77ae40e8bb7584db1a74c4318ee7d18b7ff1cdce4e049ab07690`
- Raw manifest: `artifacts.sha256` — 10,093 bytes,
  SHA-256 `a8848f102c72a9d53dfe8954c006fe6c227cc98c8d130f7194d78758a1284ff9`
- Top-level manifest: `deliverables.sha256` — 458 bytes,
  SHA-256 `fc0acc82fcdc05ee86fd1032cac07eb630f05dceb25a6d76f760ffd7edb69fb4`
