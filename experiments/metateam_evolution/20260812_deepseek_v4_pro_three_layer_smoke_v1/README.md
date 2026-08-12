# Meta-Team DeepSeek-V4-Pro Three-Layer Evolution Smoke v1

## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: run
- Origin Date: 2026-08-12T16:00:34+08:00
- Verification Status: ANALYZED
- Version Label: exp_result_v1

## Experiment Record

- **ID**: `20260812_deepseek_v4_pro_three_layer_smoke_v1`
- **Type**: generic integration smoke; model-only follow-up
- **Status**: COMPLETED — PASS (9/9 main gates passed)
- **Topic**: Meta-Team collaborative self-evolution
- **Owner branch**: `agent/metateam-evolution-smoke`

### Objective

Repeat the completed Qwen-Plus and Qwen3.7-Max protocols with the same
Meta-Team code, task text, agent pool, temperature, lifecycle, and acceptance
gates, changing only the model override to `deepseek-v4-pro`.

The primary question is whether DeepSeek-V4-Pro completes both the real
`answer_agent -> plan_agent` structured handoff and every requested L1/L2/L3
persistence action. This single run can demonstrate one successful or failed
instance; it cannot estimate a model-level success probability.

### Hypothesis and acceptance gates

**Hypothesis:** under the frozen protocol, `deepseek-v4-pro` will produce a
structured AnswerAgent handoff and complete all requested local and global
persistence writes, passing all nine gates.

The run passes only if every gate below passes:

1. **G1 — real model/tool path**: all recorded LLM calls use
   `deepseek-v4-pro`, and task execution contains real Meta-Team tool calls
   rather than a model stub.
2. **G2 — multi-agent execution**: `plan_agent` recruits `answer_agent`, sends
   a task, receives its real structured handoff, and submits an answer
   containing `391`.
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
- Qwen-Plus result commit: `4652288999fcd039df90335a6a7c8b2a6cbc2aa8`
- Qwen3.7-Max result commit: `0d8c7987df2ee93a5c13d8f7ecbac266fb3a8bcd`
- Full clean pre-run protocol commit:
  `fa6a5d123a4c3714fd28634acd17744f572d323f`
- Frozen task SHA-256:
  `7d920dfe07fa532f6d1eb94272eced2ef435b03fc4797d9bea30332b84f3d15f`
- Scientific source directories `core/`, `agents/`, `tools/`, and `main.py`
  must have no diff from the upstream source commit before the run.
- Pre-existing run IDs are frozen in [`preexisting_runs.txt`](preexisting_runs.txt);
  the validator accepts exactly one newly created run directory.
- The scientific command is executed exactly once. It is not retried after a
  crash, timeout, API error, or failed gate, and it never switches models.

### Runtime configuration

- OS: macOS 26.5.2 (`25F84`), x86_64
- Python: 3.12.9
- Provider: Alibaba Cloud Model Studio, China (Beijing), OpenAI-compatible API
- Base URL: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- Model override: `deepseek-v4-pro`
- Agent temperatures: unchanged from upstream pool (`0.2` for active agents)
- API key handling: supplied only in the caller environment; never written to
  this repository, task, stdout log, event log, or artifact manifest
- Frozen Python packages: [`environment.lock.txt`](environment.lock.txt)
- Task protocol: [`task.txt`](task.txt)
- Hard monitoring timeout: 1,800 seconds
- Monitoring interval: 30 seconds; process-alive, RSS, and output-growth checks

### Exact repository-root setup and control commands

```bash
test -x .venv/bin/python
.venv/bin/python --version
.venv/bin/python -m pip --version
test "$(git rev-parse upstream/main)" = "36dc85d9dc2219d292fa180f347479738a84acb2"
git diff --quiet upstream/main -- core agents tools main.py
test "$(shasum -a 256 experiments/metateam_evolution/20260812_deepseek_v4_pro_three_layer_smoke_v1/task.txt | awk '{print $1}')" = "7d920dfe07fa532f6d1eb94272eced2ef435b03fc4797d9bea30332b84f3d15f"
test -z "$(git status --porcelain)"
```

### Exact repository-root preflight command

The API key must already be available as `DASHSCOPE_API_KEY`. This
credential-safe setup probe is not the scientific run. It sends one minimal
tool request through Meta-Team's LiteLLM wrapper and prints only pass/fail
metadata. If it fails, the scientific command is not run and there is no
automatic endpoint or model fallback.

```bash
set -o pipefail
DEV_API_BASE='https://dashscope.aliyuncs.com/compatible-mode/v1' \
DEV_API_KEY="$DASHSCOPE_API_KEY" \
.venv/bin/python \
  experiments/metateam_evolution/20260812_deepseek_v4_pro_three_layer_smoke_v1/preflight_model.py \
  2>&1 | tee \
  experiments/metateam_evolution/20260812_deepseek_v4_pro_three_layer_smoke_v1/preflight.log
```

### Exact repository-root scientific run command

```bash
set -o pipefail
DEV_API_BASE='https://dashscope.aliyuncs.com/compatible-mode/v1' \
DEV_API_KEY="$DASHSCOPE_API_KEY" \
META_TEAM_MODEL='deepseek-v4-pro' \
.venv/bin/python main.py \
  --pool pool_GAIA_MT \
  --evolve \
  "$(tr '\n' ' ' < experiments/metateam_evolution/20260812_deepseek_v4_pro_three_layer_smoke_v1/task.txt)" \
  2>&1 | tee \
  experiments/metateam_evolution/20260812_deepseek_v4_pro_three_layer_smoke_v1/run.stdout.log
```

### Exact repository-root validation command

```bash
set -o pipefail
.venv/bin/python \
  experiments/metateam_evolution/20260812_deepseek_v4_pro_three_layer_smoke_v1/validate_run.py \
  | tee \
  experiments/metateam_evolution/20260812_deepseek_v4_pro_three_layer_smoke_v1/validation.log
```

### Artifact freeze commands

After validation identifies the single new `runs/<run_id>` directory:

```bash
test ! -e experiments/metateam_evolution/20260812_deepseek_v4_pro_three_layer_smoke_v1/artifacts/metateam_run
mkdir -p experiments/metateam_evolution/20260812_deepseek_v4_pro_three_layer_smoke_v1/artifacts
new_run_id="$({ find runs -mindepth 1 -maxdepth 1 -type d -exec basename {} \;; cat experiments/metateam_evolution/20260812_deepseek_v4_pro_three_layer_smoke_v1/preexisting_runs.txt; } | sort | uniq -u)"
test -n "$new_run_id"
cp -R "runs/$new_run_id" \
  experiments/metateam_evolution/20260812_deepseek_v4_pro_three_layer_smoke_v1/artifacts/metateam_run
find experiments/metateam_evolution/20260812_deepseek_v4_pro_three_layer_smoke_v1/artifacts \
  -type f -exec shasum -a 256 {} \; \
  | LC_ALL=C sort \
  > experiments/metateam_evolution/20260812_deepseek_v4_pro_three_layer_smoke_v1/artifacts.sha256
```

### Results

The credential-safe preflight passed: Alibaba returned model
`deepseek-v4-pro` and one structured `record_probe` tool call with the
expected argument. The frozen scientific command was then executed exactly
once. It returned exit code `0`, and the pre-registered validator also
returned exit code `0`, so the overall acceptance verdict is **PASS**.

| Field | Observed value |
|---|---|
| Run ID | `20260812_160034` |
| Runtime status | completed |
| Duration | 476.97 seconds |
| Final output | `FINAL ANSWER: 391` |
| Active agents | `plan_agent`, `answer_agent` |
| Event count | 221 |
| LLM calls | 42, all recorded as `deepseek-v4-pro` |
| Recorded tokens | 432,797 input; 12,265 output |
| Tool calls | 38 |
| Meta-Team estimated cost | USD 0.1303; not an authoritative Alibaba billing value |
| Version chain | `v000 -> v001` |
| Persisted changes | 7 files |

The seven `v001` changes were:

- two L1 `evolution/prompt_patches.md` files, one per active agent;
- two L2 `teammate_profiles.yaml` files;
- two L2 pairwise correlation files; and
- the L3 team-level `constitution.md`.

#### Gate results

| Gate | Verdict | Evidence summary |
|---|---|---|
| G1 — real model/tool path | PASS | 42 `deepseek-v4-pro` calls and 38 framework tool calls |
| G2 — multi-agent execution | PASS | AnswerAgent independently computed with Python and sent `FINAL ANSWER: 391` at event 29, before PlanAgent finalized at event 87 |
| G3 — phase traversal | PASS | All three registered phase transitions occurred in order |
| G4 — L1 local memory | PASS | Both required independent-verification patches persisted |
| G5 — L2 local contract | PASS | Both profiles and both pairwise correlations persisted |
| G6 — L3 global constitution | PASS | Constitution marker and one `reflection.applied` event present |
| G7 — version chain | PASS | Exactly `v000`, `v001`; changelog lists all 7 actual changes |
| G8 — reload | PASS | Fresh loader exposed both L1 patches, all L2 data, and the constitution rule |
| G9 — credential hygiene | PASS | No credential-pattern match in tracked, runtime, or experiment files |
| Protocol tool coverage | PASS | All 11 required lifecycle tool names appeared in the trace |

#### Runtime observations and anomalies

1. PlanAgent recruited only AnswerAgent, sent the full protocol, waited, and
   received a real structured `FINAL ANSWER: 391` handoff before calling
   `finalize_task`. The handoff therefore satisfies the ordering intended by
   G2, not merely the validator's existence check.
2. DeepSeek initially tried to execute future L1/L2/L3 instructions during the
   task-execution phase. Because the lifecycle tools were not yet available,
   it issued six `bash` echo calls and sent a premature message claiming those
   layers were complete. These calls changed no evolution artifacts.
3. After `finalize_task` moved the runner into the registered reflection
   phases, both agents used the actual lifecycle primitives. All required
   writes and skips then occurred in the correct phase and were persisted.
   The artifact-based gates prevented the earlier simulated actions from
   counting as completion.
4. AnswerAgent sent three structured messages to PlanAgent: the real answer,
   the premature reflection summary, and the actual L3 completion summary.
   This redundancy contributed to the longer trajectory but did not violate a
   registered gate.
5. The run had continuous output growth and no memory anomaly. One slower
   response window stayed below the 90-second stall threshold.
6. Trace generation succeeded, but audit generation again failed because
   `main.py` imports `generate_audit` while `core/audit.py` exports `audit`.
7. LiteLLM had no price-map entry for `openai/deepseek-v4-pro`; the reported
   USD value is Meta-Team's fallback estimate, not Alibaba billing data.

#### Three-model comparison

| Metric | `qwen-plus` | `qwen3.7-max` | `deepseek-v4-pro` |
|---|---:|---:|---:|
| Overall gates | FAIL, 8/9 | FAIL, 7/9 | **PASS, 9/9** |
| Real AnswerAgent handoffs | 0 | 1 | 3; first was the answer before finalization |
| G2 multi-agent execution | FAIL | PASS | PASS |
| G4 L1 local memory | PASS | FAIL | PASS |
| G8 fresh reload | PASS | FAIL, dependent on G4 | PASS |
| Duration | 463.31 s | 303.82 s | 476.97 s |
| LLM calls | 36 | 24 | 42 |
| Tool calls | 31 | 24 | 38 |
| Events | 170 | 130 | 221 |
| Input tokens | 248,240 | 217,886 | 432,797 |
| Output tokens | 4,325 | 6,856 | 12,265 |

DeepSeek was the only model to pass this single frozen trajectory, but it was
also the most verbose: 18 more LLM calls than Qwen3.7-Max and nearly twice its
input-token total. It finished 173.15 seconds (57.0%) slower than Max and 13.66
seconds (2.9%) slower than Qwen-Plus. These are descriptive observations from
one run per model, not population estimates.

### Analysis

This run answers the narrow experimental question positively: changing only
the model to `deepseek-v4-pro` produced one trajectory that satisfied the
entire registered execution-and-persistence contract. It retained the
structured handoff that Qwen3.7-Max added and did not take Max's permissive L1
skip path, so both local patches and the dependent fresh reload passed.

The result strengthens the inference that model behavior materially affects
which soft-contract failure appears. Across the three samples:

- `qwen-plus` persisted every requested evolution artifact but broke the
  execution handoff;
- `qwen3.7-max` completed the handoff but treated AnswerAgent's L1 write as
  optional and skipped it;
- `deepseek-v4-pro` eventually completed both sets of actions.

It does **not** show that the code defect disappeared. Meta-Team still accepts
`skip_l1_reflection` without checking whether a required patch exists, and
other lifecycle transitions still rely heavily on prompt compliance. DeepSeek
simply did not exploit that loophole in this sample. Its premature bash-based
simulation of future phases is additional evidence that natural-language
instructions alone do not define a reliable state machine; the actual phase
tool availability and artifact checks are what kept this run scientifically
interpretable.

The strongest conclusion is therefore two-part: a stronger/different model can
turn a failed trajectory into a passing one, but hard runtime preconditions are
still required if the architecture is meant to guarantee contracts rather
than merely make them likely.

### Limitations

- This is one externally hosted, potentially nondeterministic model sample.
- The model alias may be updated by the provider; returned model metadata and
  the full event trace will be retained.
- The task intentionally retains the prior role-scoping ambiguity and disclosed
  answer to isolate the model change.
- This PASS shows one successful instance; it does not prove that soft prompt
  contracts are reliable or establish a model ranking.
- A different single run could fail because the provider is nondeterministic.
- No automatic retry or reproducibility rerun is permitted.
- Meta-Team's estimated USD cost may use a LiteLLM fallback price and is not an
  authoritative Alibaba billing value.

### Decision

**Accept this run as a passing single-instance three-layer integration smoke
test.** Preserve it as evidence that `deepseek-v4-pro` completed the full
model-only protocol once.

Do not treat it as a model ranking or as evidence that Meta-Team's lifecycle is
contract-safe. The next architectural experiment should enforce machine-level
preconditions on `finalize_task`, `skip_l1_reflection`, and later phase
transitions; a separate repeated-run study is needed to estimate per-model
trajectory success rates.

### Artifact locations and checksums

- Raw frozen run: `artifacts/metateam_run/` — 51 files, 537,081 bytes
- Per-file raw manifest: `artifacts.sha256`
- Preflight output: `preflight.log` — 346 bytes,
  SHA-256 `b57badc1856e16800b5afdc8f95858b7878ebcdc8a3c9a9d2e538b5aaa2883bc`
- CLI output: `run.stdout.log` — 16,274 bytes,
  SHA-256 `9c77d18f67ecd8ea38f33f47d059a82e53e549ce4467e5ef76b3dc3331681411`
- Validator output: `validation.log` — 3,563 bytes,
  SHA-256 `35c4fc614222bdda0c36fc0dd4d612b3bd5e26d25a2cad9cd39155e151c75277`
- Raw manifest: `artifacts.sha256` — 10,399 bytes,
  SHA-256 `b8b78cb5a7203a13252f63b49343aeb3c29f6e4b1f89b8bb2ba4ec40c7dbe667`
- Top-level manifest: `deliverables.sha256` — 633 bytes,
  SHA-256 `67c7aceaa4967e1a7ab08c77ffc68824da1ffc20e07fd452f619d27d8f6f5860`
