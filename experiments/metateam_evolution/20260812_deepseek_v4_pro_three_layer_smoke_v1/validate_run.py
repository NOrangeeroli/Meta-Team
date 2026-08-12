#!/usr/bin/env python3
"""Validate the frozen Meta-Team DeepSeek-V4-Pro three-layer evolution run."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml


EXPERIMENT_ID = "20260812_deepseek_v4_pro_three_layer_smoke_v1"
EXPECTED_MODEL = "deepseek-v4-pro"
CONSTITUTION_MARKER = "## Independent Verification Handoff"
SECRET_PATTERN = re.compile(rb"sk-[A-Za-z0-9_-]{24,}")

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]
RUNS_DIR = REPO_ROOT / "runs"
PREEXISTING_RUNS = {
    line.strip()
    for line in (EXPERIMENT_DIR / "preexisting_runs.txt").read_text(encoding="utf-8").splitlines()
    if line.strip()
}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def nonempty(path: Path) -> bool:
    return path.is_file() and bool(path.read_text(encoding="utf-8").strip())


def contains_casefold(path: Path, needle: str) -> bool:
    return nonempty(path) and needle.casefold() in path.read_text(encoding="utf-8").casefold()


def scan_for_secrets(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if SECRET_PATTERN.search(data):
            findings.append(str(path.relative_to(REPO_ROOT)))
    return findings


def main() -> int:
    gates: dict[str, dict] = {}

    run_dirs = sorted(path for path in RUNS_DIR.glob("*") if path.is_dir())
    new_run_dirs = [path for path in run_dirs if path.name not in PREEXISTING_RUNS]
    if len(new_run_dirs) != 1:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error": f"expected exactly one new run directory, found {len(new_run_dirs)}",
                    "preexisting_run_ids": sorted(PREEXISTING_RUNS),
                    "observed_run_ids": [path.name for path in run_dirs],
                },
                indent=2,
            )
        )
        return 1
    run_dir = new_run_dirs[0]
    case_dir = run_dir / "cases" / "000_task"
    events_path = case_dir / "events.jsonl"
    events = read_jsonl(events_path)

    llm_models = {
        event.get("data", {}).get("model")
        for event in events
        if event.get("type") == "llm.call"
    }
    llm_models.discard(None)
    tool_calls = [
        event.get("data", {}).get("tool")
        for event in events
        if event.get("type") == "tool.call"
    ]
    tool_calls_set = set(tool_calls)
    gates["G1_real_model_tool_path"] = {
        "pass": llm_models == {EXPECTED_MODEL} and len(tool_calls) > 0,
        "models": sorted(llm_models),
        "tool_call_count": len(tool_calls),
    }

    runner_end = [event for event in events if event.get("type") == "runner.end"]
    final_output = runner_end[-1].get("data", {}).get("output", "") if runner_end else ""
    agents_used = runner_end[-1].get("data", {}).get("agents_used", []) if runner_end else []
    answer_handoffs = [
        event
        for event in events
        if event.get("type") == "tool.call"
        and event.get("agent") == "answer_agent"
        and event.get("data", {}).get("tool") == "send_message"
        and "plan_agent" in event.get("data", {}).get("args", {}).get("to", [])
    ]
    gates["G2_multi_agent_execution"] = {
        "pass": (
            set(agents_used) == {"plan_agent", "answer_agent"}
            and "391" in final_output
            and "start_agent" in tool_calls_set
            and "send_message" in tool_calls_set
            and bool(answer_handoffs)
        ),
        "agents_used": agents_used,
        "final_output": final_output,
        "answer_handoff_count": len(answer_handoffs),
    }

    transitions = [
        (event.get("data", {}).get("from"), event.get("data", {}).get("to"))
        for event in events
        if event.get("type") == "runner.phase_change"
    ]
    expected_transitions = [
        ("task_execution", "l1_reflection"),
        ("l1_reflection", "l2_reflection"),
        ("l2_reflection", "l3_reflection"),
    ]
    gates["G3_phase_traversal"] = {
        "pass": all(transition in transitions for transition in expected_transitions),
        "transitions": transitions,
    }

    v001 = run_dir / "team" / "v001"
    plan_patch = v001 / "plan_agent" / "evolution" / "prompt_patches.md"
    answer_patch = v001 / "answer_agent" / "evolution" / "prompt_patches.md"
    gates["G4_l1_local_memory"] = {
        "pass": contains_casefold(plan_patch, "independent") and contains_casefold(answer_patch, "independent"),
        "files": [str(plan_patch.relative_to(run_dir)), str(answer_patch.relative_to(run_dir))],
    }

    plan_profile = v001 / "plan_agent" / "evolution" / "teammate_profiles.yaml"
    answer_profile = v001 / "answer_agent" / "evolution" / "teammate_profiles.yaml"
    plan_corr = v001 / "plan_agent" / "evolution" / "correlations" / "answer_agent.md"
    answer_corr = v001 / "answer_agent" / "evolution" / "correlations" / "plan_agent.md"
    plan_profile_data = yaml.safe_load(plan_profile.read_text(encoding="utf-8")) if nonempty(plan_profile) else {}
    answer_profile_data = yaml.safe_load(answer_profile.read_text(encoding="utf-8")) if nonempty(answer_profile) else {}
    gates["G5_l2_local_contract"] = {
        "pass": (
            isinstance(plan_profile_data, dict)
            and "answer_agent" in plan_profile_data
            and isinstance(answer_profile_data, dict)
            and "plan_agent" in answer_profile_data
            and nonempty(plan_corr)
            and nonempty(answer_corr)
        ),
        "files": [
            str(plan_profile.relative_to(run_dir)),
            str(answer_profile.relative_to(run_dir)),
            str(plan_corr.relative_to(run_dir)),
            str(answer_corr.relative_to(run_dir)),
        ],
    }

    constitution = v001 / "constitution.md"
    reflection_applied_events = [event for event in events if event.get("type") == "reflection.applied"]
    gates["G6_l3_global_constitution"] = {
        "pass": contains_casefold(constitution, CONSTITUTION_MARKER) and bool(reflection_applied_events),
        "marker": CONSTITUTION_MARKER,
        "reflection_applied_events": len(reflection_applied_events),
    }

    versions = sorted(path.name for path in (run_dir / "team").glob("v[0-9][0-9][0-9]") if path.is_dir())
    changelog_path = run_dir / "changelog.jsonl"
    changelog = read_jsonl(changelog_path) if changelog_path.exists() else []
    version_entry = changelog[-1] if changelog else {}
    gates["G7_version_chain"] = {
        "pass": (
            versions == ["v000", "v001"]
            and version_entry.get("from_version") == "v000"
            and version_entry.get("to_version") == "v001"
            and version_entry.get("reflection_applied") is True
            and "constitution.md" in version_entry.get("modified_files", [])
        ),
        "versions": versions,
        "changelog": changelog,
    }

    os.environ.setdefault("DEV_API_BASE", "http://127.0.0.1:9/v1")
    os.environ.setdefault("DEV_API_KEY", "not-needed")
    sys.path.insert(0, str(REPO_ROOT))
    from main import load_pool  # noqa: PLC0415

    reloaded = load_pool(v001)
    reloaded_plan = reloaded.agents["plan_agent"]
    reloaded_answer = reloaded.agents["answer_agent"]
    gates["G8_reload"] = {
        "pass": (
            CONSTITUTION_MARKER in reloaded.constitution
            and "independent" in reloaded_plan.prompt_patches.casefold()
            and "answer_agent" in reloaded_plan.teammate_profiles
            and "answer_agent" in reloaded_plan.correlations
            and "independent" in reloaded_answer.prompt_patches.casefold()
            and "plan_agent" in reloaded_answer.teammate_profiles
            and "plan_agent" in reloaded_answer.correlations
        ),
        "loaded_agents": sorted(reloaded.agents),
    }

    tracked_raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=REPO_ROOT)
    tracked_paths = [REPO_ROOT / item.decode() for item in tracked_raw.split(b"\0") if item]
    runtime_paths = [path for path in run_dir.rglob("*") if path.is_file()]
    experiment_paths = [path for path in EXPERIMENT_DIR.rglob("*") if path.is_file()]
    secret_findings = scan_for_secrets(tracked_paths + runtime_paths + experiment_paths)
    gates["G9_credential_hygiene"] = {
        "pass": not secret_findings,
        "findings": secret_findings,
    }

    required_tools = {
        "finalize_task",
        "update_prompt_patch",
        "skip_l1_reflection",
        "update_teammate_profile",
        "update_correlation",
        "skip_l2_reflection",
        "suggest_team_improvement",
        "skip_l3_reflection",
        "view_current_config",
        "propose_reflection",
        "apply_reflection",
    }
    gates["protocol_tool_coverage"] = {
        "pass": required_tools.issubset(tool_calls_set),
        "required": sorted(required_tools),
        "observed": sorted(tool_calls_set),
        "missing": sorted(required_tools - tool_calls_set),
    }

    passed = all(gate["pass"] for gate in gates.values())
    result = {
        "experiment_id": EXPERIMENT_ID,
        "status": "PASS" if passed else "FAIL",
        "run_id": run_dir.name,
        "run_dir": str(run_dir.relative_to(REPO_ROOT)),
        "event_count": len(events),
        "gates": gates,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
