# Meta-Team Qwen-Plus Three-Layer Evolution Smoke v1

## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: run
- Origin Date: 2026-08-12T14:00:00+08:00
- Verification Status: UNVERIFIED
- Version Label: exp_result_v1

## Experiment Record

- **ID**: `20260812_qwen_plus_three_layer_smoke_v1`
- **Type**: generic integration smoke
- **Status**: PLANNED
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
- Full clean pre-run protocol commit: `PENDING`
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

`PENDING`

### Analysis

`PENDING`

### Limitations

- The reflection changes are protocol-directed, not autonomously discovered.
- This is one task and one model sample, with no baseline or held-out task.
- Passing the smoke gates cannot establish that the changes improve quality.
- Qwen API responses are externally hosted and potentially nondeterministic.
- The `qwen-plus` alias may be updated by the provider; the returned model ID
  and package environment will be retained in the artifacts.
- Editable installation currently fails at the frozen upstream source commit;
  the experiment therefore uses `requirements.txt` and runs from the checkout.

### Decision

`PENDING`

### Artifact locations and checksums

`PENDING`
