# Meta-Team Qwen3.7-Max Three-Layer Evolution Smoke v1

## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: run
- Origin Date: 2026-08-12T15:33:26+08:00
- Verification Status: ANALYZED
- Version Label: exp_result_v1

## Experiment Record

- **ID**: `20260812_qwen37_max_three_layer_smoke_v1`
- **Type**: generic integration smoke; model-only follow-up
- **Status**: COMPLETED — FAIL (7/9 main gates passed)
- **Topic**: Meta-Team collaborative self-evolution
- **Owner branch**: `agent/metateam-evolution-smoke`

### Objective

Repeat the completed `20260812_qwen_plus_three_layer_smoke_v1` protocol with
the same Meta-Team code, task text, agent pool, temperature, lifecycle, and
acceptance gates, changing only the model override from `qwen-plus` to
`qwen3.7-max`.

The primary question is whether a stronger tool-capable model completes the
real `answer_agent -> plan_agent` message handoff that failed in the prior run.
This single run can demonstrate a successful or failed instance; it cannot
estimate a model-level success probability.

### Hypothesis and acceptance gates

**Hypothesis:** under the frozen protocol, `qwen3.7-max` will produce a
structured `send_message` tool call from `answer_agent` to `plan_agent`, so the
run will pass G2 while retaining the L1/L2/L3 persistence behavior observed with
`qwen-plus`.

The run passes only if every gate below passes:

1. **G1 — real model/tool path**: all recorded LLM calls use `qwen3.7-max`, and
   task execution contains real Meta-Team tool calls rather than a model stub.
2. **G2 — multi-agent execution**: `plan_agent` recruits `answer_agent`, sends a
   task, receives its real structured handoff, and submits an answer containing
   `391`.
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

The overall verdict is PASS only if all nine main gates and protocol tool
coverage pass. A correct terminal answer without a real AnswerAgent handoff is
still FAIL. No gate may be changed after the scientific run starts.

### Frozen source and model-only controls

- Upstream repository: <https://github.com/zz-haooo/Meta-Team>
- Fork: <https://github.com/NOrangeeroli/Meta-Team>
- Upstream clean source commit: `36dc85d9dc2219d292fa180f347479738a84acb2`
- Prior Qwen-Plus result commit:
  `4652288999fcd039df90335a6a7c8b2a6cbc2aa8`
- Full clean pre-run protocol commit:
  `f186c3741606f2fbbd44759f247f7d8bfc735293`
- Previous task SHA-256:
  `7d920dfe07fa532f6d1eb94272eced2ef435b03fc4797d9bea30332b84f3d15f`
- Current task has the same SHA-256.
- Scientific source directories `core/`, `agents/`, `tools/`, and `main.py`
  must have no diff from upstream commit before the run.
- Pre-existing run IDs are frozen in [`preexisting_runs.txt`](preexisting_runs.txt);
  the validator accepts exactly one newly created run directory.

### Runtime configuration

- OS: macOS 26.5.2 (`25F84`), x86_64
- Python: 3.12.9
- Provider: Alibaba Cloud Model Studio, China (Beijing), OpenAI-compatible API
- Base URL: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- Model override: `qwen3.7-max`
- Agent temperatures: unchanged from upstream pool (`0.2` for active agents)
- API key handling: supplied only in the caller environment; never written to
  this repository, task, stdout log, event log, or artifact manifest
- Frozen Python packages: [`environment.lock.txt`](environment.lock.txt)
- Task protocol: [`task.txt`](task.txt)
- Hard monitoring timeout: 1,800 seconds
- Monitoring interval: 30 seconds; process-alive and output-growth checks

### Exact repository-root setup and control commands

```bash
test -x .venv/bin/python
.venv/bin/python --version
.venv/bin/python -m pip --version
test "$(git rev-parse upstream/main)" = "36dc85d9dc2219d292fa180f347479738a84acb2"
git diff --quiet upstream/main -- core agents tools main.py
test "$(shasum -a 256 experiments/metateam_evolution/20260812_qwen37_max_three_layer_smoke_v1/task.txt | awk '{print $1}')" = "7d920dfe07fa532f6d1eb94272eced2ef435b03fc4797d9bea30332b84f3d15f"
test -z "$(git status --porcelain)"
```

### Exact repository-root preflight command

The API key must already be available as `DASHSCOPE_API_KEY`. This is a
credential-safe setup probe, not the scientific run. It sends one minimal tool
request through Meta-Team's LiteLLM wrapper and prints only pass/fail metadata.
If it fails, the scientific command is not run and there is no automatic model
fallback.

```bash
set -o pipefail
DEV_API_BASE='https://dashscope.aliyuncs.com/compatible-mode/v1' \
DEV_API_KEY="$DASHSCOPE_API_KEY" \
.venv/bin/python \
  experiments/metateam_evolution/20260812_qwen37_max_three_layer_smoke_v1/preflight_model.py \
  2>&1 | tee \
  experiments/metateam_evolution/20260812_qwen37_max_three_layer_smoke_v1/preflight.log
```

### Exact repository-root scientific run command

```bash
set -o pipefail
DEV_API_BASE='https://dashscope.aliyuncs.com/compatible-mode/v1' \
DEV_API_KEY="$DASHSCOPE_API_KEY" \
META_TEAM_MODEL='qwen3.7-max' \
.venv/bin/python main.py \
  --pool pool_GAIA_MT \
  --evolve \
  "$(tr '\n' ' ' < experiments/metateam_evolution/20260812_qwen37_max_three_layer_smoke_v1/task.txt)" \
  2>&1 | tee \
  experiments/metateam_evolution/20260812_qwen37_max_three_layer_smoke_v1/run.stdout.log
```

This scientific command is executed exactly once. A crash, timeout, API error,
or failed gate is reported without retrying or switching models.

### Exact repository-root validation command

```bash
set -o pipefail
.venv/bin/python \
  experiments/metateam_evolution/20260812_qwen37_max_three_layer_smoke_v1/validate_run.py \
  | tee \
  experiments/metateam_evolution/20260812_qwen37_max_three_layer_smoke_v1/validation.log
```

### Artifact freeze commands

After validation identifies the single new `runs/<run_id>` directory:

```bash
test ! -e experiments/metateam_evolution/20260812_qwen37_max_three_layer_smoke_v1/artifacts/metateam_run
mkdir -p experiments/metateam_evolution/20260812_qwen37_max_three_layer_smoke_v1/artifacts
new_run_id="$({ find runs -mindepth 1 -maxdepth 1 -type d -exec basename {} \;; cat experiments/metateam_evolution/20260812_qwen37_max_three_layer_smoke_v1/preexisting_runs.txt; } | sort | uniq -u)"
test -n "$new_run_id"
cp -R "runs/$new_run_id" \
  experiments/metateam_evolution/20260812_qwen37_max_three_layer_smoke_v1/artifacts/metateam_run
find experiments/metateam_evolution/20260812_qwen37_max_three_layer_smoke_v1/artifacts \
  -type f -exec shasum -a 256 {} \; \
  | LC_ALL=C sort \
  > experiments/metateam_evolution/20260812_qwen37_max_three_layer_smoke_v1/artifacts.sha256
```

### Results

The credential-safe preflight passed: Alibaba returned model
`qwen3.7-max` and one structured `record_probe` tool call with the expected
argument. The frozen scientific command was then executed exactly once. It
returned exit code `0`; the pre-registered validator returned exit code `1`,
so the overall acceptance verdict is **FAIL**.

| Field | Observed value |
|---|---|
| Run ID | `20260812_153326` |
| Runtime status | completed |
| Duration | 303.82 seconds |
| Final output | `FINAL ANSWER: 391` |
| Active agents | `plan_agent`, `answer_agent` |
| Event count | 130 |
| LLM calls | 24, all recorded as `qwen3.7-max` |
| Recorded tokens | 217,886 input; 6,856 output |
| Tool calls | 24 |
| Meta-Team estimated cost | USD 0.7565; not an authoritative Alibaba billing value |
| Version chain | `v000 -> v001` |
| Persisted changes | 6 files |

The six `v001` changes were:

- one L1 `plan_agent/evolution/prompt_patches.md` file;
- two L2 `teammate_profiles.yaml` files;
- two L2 pairwise correlation files; and
- the L3 team-level `constitution.md`.

`answer_agent/evolution/prompt_patches.md` was not created.

#### Gate results

| Gate | Verdict | Evidence summary |
|---|---|---|
| G1 — real model/tool path | PASS | 24 `qwen3.7-max` calls and 24 framework tool calls |
| G2 — multi-agent execution | PASS | One real structured `answer_agent -> plan_agent` answer handoff occurred before finalization |
| G3 — phase traversal | PASS | All three registered phase transitions occurred |
| G4 — L1 local memory | **FAIL** | PlanAgent wrote its patch; AnswerAgent skipped L1 without writing its required patch |
| G5 — L2 local contract | PASS | Both profiles and both pairwise correlations persisted |
| G6 — L3 global constitution | PASS | Constitution marker and `reflection.applied` event present |
| G7 — version chain | PASS | Exactly `v000`, `v001`; changelog includes all 6 actual changes |
| G8 — reload | **FAIL** | Fresh reload lacked the required AnswerAgent L1 patch; all other expected additions loaded |
| G9 — credential hygiene | PASS | No credential-pattern match in tracked or runtime files |
| Protocol tool coverage | PASS | All 11 required tool names appeared somewhere in the team trace |

G4 is the single root protocol deviation. G8 is a dependent persistence/reload
failure caused by that missing file, rather than a separate loader defect.

#### Runtime observations and anomalies

1. Unlike `qwen-plus`, PlanAgent converted the full Chairman-oriented task into
   a role-scoped worker message. AnswerAgent independently computed `391` and
   issued a real structured `send_message` tool call to PlanAgent. G2 therefore
   changed from FAIL to PASS.
2. During L1, the phase prompt said a truly trivial task may skip reflection.
   AnswerAgent explicitly judged the multiplication trivial and called
   `skip_l1_reflection` with “No improvements needed,” despite the frozen task
   requiring a specific patch first. The runtime accepted the skip and advanced
   the phase without checking that the requested per-agent update existed.
3. L2 and L3 completed normally. The AnswerAgent profiles, both pairwise notes,
   its workflow suggestion, and the global constitution update all persisted.
4. One 30-second quiet output window occurred while PlanAgent composed the full
   constitution proposal. Output then resumed, so it did not reach the
   pre-registered 90-second stall threshold. No memory anomaly occurred.
5. Trace generation succeeded, but audit generation again failed because
   `main.py` imports `generate_audit` while `core/audit.py` exports `audit`.
6. LiteLLM had no price-map entry for `openai/qwen3.7-max`; all reported USD
   values are Meta-Team fallback estimates, not Alibaba billing records.

#### Model-only comparison

| Metric | `qwen-plus` | `qwen3.7-max` |
|---|---:|---:|
| Overall gates | FAIL, 8/9 | FAIL, 7/9 |
| Real AnswerAgent handoffs | 0 | 1 |
| G2 multi-agent execution | FAIL | PASS |
| G4 L1 local memory | PASS | FAIL |
| G8 fresh reload | PASS | FAIL (dependent on G4) |
| Duration | 463.31 s | 303.82 s |
| LLM calls | 36 | 24 |
| Tool calls | 31 | 24 |
| Events | 170 | 130 |
| Input tokens | 248,240 | 217,886 |
| Output tokens | 4,325 | 6,856 |

The Max sample finished 159.49 seconds (34.4%) faster and used 12 fewer LLM
calls. These descriptive differences are not population estimates; each model
has only one run.

### Analysis

The stronger model fixed the exact failure that motivated this follow-up. It
kept the role boundary straight, summarized the worker-specific instructions,
used structured function calling, and completed a MessageStore-backed answer
handoff before the Chairman finalized. This supports the narrow inference that
model capability or tool-use reliability contributed to the Qwen-Plus G2
failure.

It did not make the architecture contract-safe. The new failure occurred at a
different soft instruction boundary: the original task mandated an AnswerAgent
patch, while Meta-Team's L1 phase prompt and `skip_l1_reflection` tool explicitly
allowed a trivial task to skip. Qwen3.7-Max exercised that discretion. The
handler then unconditionally added AnswerAgent to `_l1_completed`, so the phase
advanced even though no patch existed. The missing patch later surfaced as both
G4 and the dependent G8 failure.

The two runs therefore show a failure-mode substitution rather than an
end-to-end solution:

- `qwen-plus`: obeyed all requested persistence writes but broke the execution
  handoff;
- `qwen3.7-max`: executed the handoff correctly but declined one requested
  persistence write;
- both: completed with a correct final answer and persisted a global
  constitution, while violating at least one intended trajectory constraint.

The evidence is consistent with “a stronger model improves soft-contract
compliance on some steps,” but it does not support “a stronger model makes soft
contracts reliable.” In fact, a more capable model can make a reasonable
judgment that conflicts with an experimental protocol when the framework
presents both choices as valid. Required transitions and artifacts need
machine-checkable preconditions, not only natural-language instructions.

### Limitations

- This is one externally hosted, potentially nondeterministic model sample.
- The model alias may be updated by the provider; the returned model metadata
  and full event trace will be retained.
- The task intentionally retains the previous role-scoping ambiguity and
  disclosed answer to isolate the model change. Those are known design flaws,
  not recommendations for a production protocol.
- A PASS would show one successful instance, not prove that soft prompt
  contracts are reliable or that `qwen3.7-max` has a higher success rate.
- A FAIL would not prove that the stronger model is generally ineffective.
- No automatic retry or reproducibility rerun is permitted.
- Meta-Team's estimated USD cost may use a LiteLLM fallback price and is not an
  authoritative Alibaba billing value.

### Decision

**Reject this run as a passing end-to-end three-layer smoke test.** Preserve it
as evidence that `qwen3.7-max` fixes the prior structured handoff failure in one
sample, while exposing a separate missing-precondition defect in the L1 phase.

Do not claim a model ranking from one run per model. The next scientific step
should separate two questions with new experiment IDs:

1. a repeated model-only study estimating per-model trajectory success rates;
2. a code-enforcement study where `finalize_task`, `skip_l1_reflection`, and
   later phase transitions reject calls until their declared MessageStore and
   artifact preconditions are satisfied.

The second study is the architectural test: with hard contracts, a model may
initially choose the wrong action, but the runtime must return actionable
feedback and prevent an invalid transition.

### Artifact locations and checksums

- Raw frozen run: `artifacts/metateam_run/` — 49 files, 376,130 bytes
- Per-file raw manifest: `artifacts.sha256`
- Preflight output: `preflight.log` — 338 bytes,
  SHA-256 `094c07c30b16801ae627c7e262d827f05c8784b26b4d3978735cf6f4ce763c11`
- CLI output: `run.stdout.log` — 10,862 bytes,
  SHA-256 `a3f273b06a7aa937e5bab1faafa6ec444e2c1ae81e2bf0437bd623557cd2a0fe`
- Validator output: `validation.log` — 3,475 bytes,
  SHA-256 `d364611be6286f4282fd9d2327816ac24417479f9ef64aa424368120b5705a19`
- Raw manifest: `artifacts.sha256` — 9,710 bytes,
  SHA-256 `f9e7de29118919ef352c1ba5183feb14bdb0266df700eaa42bdeab3a97b736e8`
- Top-level manifest: `deliverables.sha256` — 613 bytes,
  SHA-256 `2427fab4385e27e9ac01fd645a6f02487a2b435c63c51470aaa45ba5a47571f4`
