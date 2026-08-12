# Meta-Team Qwen3.7-Max Three-Layer Evolution Smoke v1

## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: run
- Origin Date: 2026-08-12 Asia/Shanghai
- Verification Status: UNVERIFIED
- Version Label: exp_protocol_v1

## Experiment Record

- **ID**: `20260812_qwen37_max_three_layer_smoke_v1`
- **Type**: generic integration smoke; model-only follow-up
- **Status**: PLANNED — PENDING
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
- Full clean pre-run protocol commit: `PENDING`
- Previous task SHA-256:
  `7d920dfe07fa532f6d1eb94272eced2ef435b03fc4797d9bea30332b84f3d15f`
- Current task must have the same SHA-256.
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

`PENDING`

### Analysis

`PENDING`

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

`PENDING`

### Artifact locations and checksums

`PENDING`
