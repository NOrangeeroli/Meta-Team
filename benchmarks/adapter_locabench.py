
import sys
import os
import json
import logging
import argparse
import threading
from pathlib import Path
from collections import defaultdict
from typing import Any

_BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BASE_DIR))

LOCABENCH_DIR = _BASE_DIR / "benchmarks" / "LOCA-bench"
sys.path.insert(0, str(LOCABENCH_DIR))
sys.path.insert(0, str(LOCABENCH_DIR / "mcp_convert"))

from benchmarks.adapter import BenchmarkAdapter, EvalResult, EnvContext

os.environ["LOCA_QUIET"] = "1"
logging.getLogger("mcp").setLevel(logging.WARNING)
logging.getLogger("fastmcp").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
_eval_lock = threading.Lock()


TASK_CONFIGS_DIR = LOCABENCH_DIR / "task-configs"

CONTEXT_LEVELS = [
    "8k", "16k", "32k", "64k", "96k", "128k", "256k",
    "evolve_96k",
]

STD_EVAL_SEEDS = [42, 123, 456, 789, 2024]     # Evaluation set
EVOLVE_SEEDS = [101, 102]                       # Evolution set

S2L_TASK_NAMES = [
    "ABTestingS2LEnv",
    "AcademicWarningS2LEnv",
    "ApplyPhDEmailS2LEnv",
    "CanvasArrangeExamS2LEnv",
    "CanvasListTestS2LEnv",
    "CourseAssistantS2LEnv",
    "ExcelMarketResearchS2LEnv",
    "FilterLowSellingProductsS2LEnv",
    "MachineOperatingS2LEnv",
    "NhlB2bAnalysisS2LEnv",
    "PayableInvoiceCheckerS2LEnv",
    "SetConfCrDdlS2LEnv",
    "UpdateMaterialInventoryS2LEnv",
    "WoocommerceNewWelcomeS2LEnv",
    "WoocommerceStockAlertS2LEnv",
]

TASK_SHORT_NAMES = {
    "ABTesting": "ABTestingS2LEnv",
    "AcademicWarning": "AcademicWarningS2LEnv",
    "ApplyPhDEmail": "ApplyPhDEmailS2LEnv",
    "CanvasArrangeExam": "CanvasArrangeExamS2LEnv",
    "CanvasListTest": "CanvasListTestS2LEnv",
    "CourseAssistant": "CourseAssistantS2LEnv",
    "ExcelMarketResearch": "ExcelMarketResearchS2LEnv",
    "FilterLowSelling": "FilterLowSellingProductsS2LEnv",
    "MachineOperating": "MachineOperatingS2LEnv",
    "NhlB2bAnalysis": "NhlB2bAnalysisS2LEnv",
    "PayableInvoiceChecker": "PayableInvoiceCheckerS2LEnv",
    "SetConfCrDdl": "SetConfCrDdlS2LEnv",
    "UpdateMaterialInventory": "UpdateMaterialInventoryS2LEnv",
    "WoocommerceNewWelcome": "WoocommerceNewWelcomeS2LEnv",
    "WoocommerceStockAlert": "WoocommerceStockAlertS2LEnv",
}



def load_locabench_configs(
    context_level: str = "128k",
    task_filter: str | None = None,
    seed_filter: int | None = None,
) -> list[dict]:
    if context_level == "evolve_96k":
        config_file = TASK_CONFIGS_DIR / "evolve_96k_set_config.json"
        display_level = "96k"
    else:
        config_file = TASK_CONFIGS_DIR / f"final_{context_level}_set_config.json"
        display_level = context_level

    if not config_file.exists():
        raise FileNotFoundError(
            f"LOCA-bench config not found: {config_file}\n"
            f"Available: {[f.name for f in TASK_CONFIGS_DIR.glob('*.json')]}"
        )

    with open(config_file, encoding="utf-8") as f:
        data = json.load(f)

    configs = data.get("configurations", [])

    for i, c in enumerate(configs):
        c["_index"] = i
        c["_context_level"] = display_level
        c["_split"] = context_level
        c["_seed"] = c.get("env_params", {}).get("seed", 0)
        c["_task_name"] = c.get("name", "")

    if task_filter:
        full_name = TASK_SHORT_NAMES.get(task_filter, task_filter)
        configs = [c for c in configs if c["_task_name"] == full_name]

    if seed_filter is not None:
        configs = [c for c in configs if c["_seed"] == seed_filter]

    return configs



def _create_loca_env(config: dict, task_dir: str):
    from inference.run_react import dynamic_import_class

    _ensure_pythonpath()

    EnvClass = dynamic_import_class(config["env_class"])
    env_params = dict(config["env_params"])
    env_params["task_dir"] = task_dir

    with _eval_lock:
        return EnvClass(**env_params)


def _ensure_pythonpath():
    import os
    loca_root = str(LOCABENCH_DIR.resolve())
    mcp_root = str((LOCABENCH_DIR / "mcp_convert").resolve())

    current = os.environ.get("PYTHONPATH", "")
    paths = current.split(os.pathsep) if current else []

    changed = False
    if loca_root not in paths:
        paths.insert(0, loca_root)
        changed = True
    if mcp_root not in paths:
        paths.insert(1, mcp_root)
        changed = True

    if changed:
        os.environ["PYTHONPATH"] = os.pathsep.join(paths)


def _setup_mcp_tool(config: dict, task_dir: str):
    import threading

    result_holder = {}

    def _init_in_thread():
        try:
            from inference.run_react import setup_mcp_servers
            from gem.tools.mcp_tool import MCPTool

            task_ws = Path(task_dir)
            agent_ws = task_ws / "agent_workspace"
            agent_ws.mkdir(parents=True, exist_ok=True)

            mcp_config = setup_mcp_servers(config["mcp_servers"], task_ws, agent_ws)
            tool = MCPTool(mcp_config, validate_on_init=False, execution_timeout=120.0)

            _register_mcp_tool(tool)

            available = tool.get_available_tools()
            catalog = [{"name": t["name"], "description": t.get("description", "")} for t in available]

            result_holder["tool"] = tool
            result_holder["catalog"] = catalog
        except Exception as exc:
            result_holder["error"] = exc

    t = threading.Thread(target=_init_in_thread, daemon=True)
    t.start()
    t.join(timeout=120)

    if "error" in result_holder:
        raise result_holder["error"]
    if "tool" not in result_holder:
        raise TimeoutError("MCP tool initialization timed out (120s)")

    return result_holder["tool"], result_holder["catalog"]


def _check_preprocess_integrity(task_dir: str, task_name: str, strict: bool = False) -> None:
    td = Path(task_dir)
    local_db = td / "local_db"
    agent_ws = td / "agent_workspace"

    local_db_files = sum(1 for _ in local_db.rglob("*") if _.is_file()) if local_db.exists() else 0
    agent_ws_files = sum(1 for _ in agent_ws.rglob("*") if _.is_file()) if agent_ws.exists() else 0

    if local_db_files == 0 and agent_ws_files == 0:
        msg = (
            f"  [LOCAbench] ⚠️  WARNING: preprocess for {task_name} produced no data!\n"
            f"  [LOCAbench]   local_db/ has {local_db_files} files, agent_workspace/ has {agent_ws_files} files.\n"
            f"  [LOCAbench]   This usually means the preprocess subprocess failed silently.\n"
            f"  [LOCAbench]   Check PYTHONPATH or run: cd benchmarks/LOCA-bench && python gem/envs/*/preprocess/main.py --help\n"
            f"  [LOCAbench]   The task will run but evaluation will return reward=0.0."
        )
        print(msg)
        if strict:
            raise RuntimeError(
                f"preprocess for {task_name} produced no data in {task_dir} "
                f"(local_db={local_db_files}, agent_workspace={agent_ws_files}); "
                f"refusing to proceed under LOCA_STRICT_PREPROCESS=1"
            )
    else:
        print(f"  [LOCAbench] Preprocess OK: local_db={local_db_files} files, agent_workspace={agent_ws_files} files")


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

def _extract_eval_log(task_dir: str, task_name: str) -> str:
    if not task_dir:
        return ""

    candidates = [
        Path(task_dir) / "logs" / "env.log",
        Path(task_dir) / "workspace" / "logs" / "env.log",
    ]
    content = ""
    for log_path in candidates:
        if log_path.exists():
            try:
                content = log_path.read_text(encoding="utf-8", errors="replace")
                break
            except Exception:
                continue
    if not content:
        return ""

    try:
        marker = "Starting task evaluation"
        idx = content.rfind(marker)
        if idx < 0:
            for alt in ["Evaluation result", "reward", "PASS", "FAIL",
                         "expected", "actual", "mismatch", "incorrect"]:
                idx = content.rfind(alt)
                if idx >= 0:
                    idx = content.rfind("\n", 0, idx)
                    if idx < 0:
                        idx = 0
                    break

        if idx < 0:
            return content[-2000:].strip() if len(content) > 2000 else content.strip()

        eval_section = content[idx:]
        if len(eval_section) > 3000:
            eval_section = eval_section[:3000] + "\n... (truncated)"
        return eval_section.strip()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

import atexit
import threading

_owned_mcp_tools: list = []
_mcp_lock = threading.Lock()


def _register_mcp_tool(tool) -> None:
    """"""
    with _mcp_lock:
        _owned_mcp_tools.append(tool)


def _unregister_mcp_tool(tool) -> None:
    """"""
    with _mcp_lock:
        try:
            _owned_mcp_tools.remove(tool)
        except ValueError:
            pass


def _cleanup_mcp_tools() -> None:
    """"""
    with _mcp_lock:
        to_clean = list(_owned_mcp_tools)
    if not to_clean:
        return
    for tool in to_clean:
        try:
            tool.close()
        except Exception:
            pass


atexit.register(_cleanup_mcp_tools)



class LOCABenchAdapter(BenchmarkAdapter):
    benchmark_name = "locabench"
    default_team = "pool_LOCAbench"
    default_timeout = 7200.0
    default_evolve_timeout = 7200.0
    default_max_cost = 150.0
    default_split = "128k"
    results_subdir = "locabench-results"
    split_choices = CONTEXT_LEVELS

    PER_SPLIT_MAX_COST = {
        "8k": 15.0,
        "16k": 20.0,
        "32k": 30.0,
        "64k": 60.0,
        "96k": 80.0,
        "128k": 100.0,
        "256k": 180.0,
        "evolve_96k": 180.0,
    }

    PER_SPLIT_TIMEOUT = {
        "8k": 1800.0,
        "16k": 1800.0,
        "32k": 3600.0,
        "64k": 3600.0,
        "96k": 5400.0,
        "128k": 7200.0,
        "256k": 7200.0,
        "evolve_96k": 7200.0,
    }

    def cli(self) -> None:
        parser = self.build_parser()
        args = parser.parse_args()

        split = getattr(args, "split", "") or self.default_split

        if args.timeout is None:
            if args.evolve:
                args.timeout = float(self.default_evolve_timeout)
            else:
                args.timeout = float(self.PER_SPLIT_TIMEOUT.get(
                    split, self.default_timeout,
                ))

        if args.max_cost is None:
            args.max_cost = float(self.PER_SPLIT_MAX_COST.get(
                split, self.default_max_cost,
            ))

        if args.evolve and args.workers > 1:
            print(
                "[error] --evolve and --workers > 1 are mutually exclusive. "
                "Evolution mode requires sequential execution (--workers 1)."
            )
            sys.exit(1)

        print(
            f"[LOCABench] split={split} timeout={args.timeout:.0f}s "
            f"max_cost=${args.max_cost:.1f}"
        )

        import asyncio
        asyncio.run(self.run(args))

    def add_extra_args(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--task", type=str, default=None,
            help="Run specific task (short or full name)")
        parser.add_argument(
            "--seed", type=int, default=None,
            help="Run specific seed (42, 123, 456, 789, 2024, or 101/102 for evolve_96k)")

    def load_dataset(self, args: argparse.Namespace) -> list[dict]:
        context_level = getattr(args, "split", "128k") or "128k"
        task_filter = getattr(args, "task", None)
        seed_filter = getattr(args, "seed", None)

        items = load_locabench_configs(
            context_level=context_level,
            task_filter=task_filter,
            seed_filter=seed_filter,
        )

        if not items:
            print(f"[LOCABench] No configurations found for split={context_level}")
            if task_filter:
                print(f"  task={task_filter}")
                print(f"  Available tasks: {list(TASK_SHORT_NAMES.keys())}")
            if seed_filter:
                print(f"  seed={seed_filter}")

        return items

    def get_item_id(self, item: dict) -> str:
        """"""
        task_name = item.get("_task_name", "unknown")
        seed = item.get("_seed", 0)
        return f"{task_name}_seed{seed}"

    def build_task(self, item: dict, session: Any, workspace_files: list[str]) -> str:
        """"""
        task_instruction = item.get("_task_instruction", "")
        task_name = item.get("_task_name", "")
        context_level = item.get("_context_level", "")
        tool_catalog = item.get("_tool_catalog", [])

        tool_list = "\n".join(
            f"  - `{t['name']}`: {t['description'][:100]}"
            for t in tool_catalog
        )

        task = f"""## LOCA-bench Task: {task_name} ({context_level})


{task_instruction}


You can interact with the environment using the `loca_mcp` tool. The following MCP tools are available:

{tool_list}


**List all tools:**
```
loca_mcp(action="list_tools")
```

**Call a specific tool:**
```
loca_mcp(action="call", tool_name="<tool_name>", arguments='{{...}}')
```


1. Read the task instructions carefully before starting.
2. Use `loca_mcp(action="list_tools")` to see all available MCP tools.
3. Execute tools step by step — examine results before proceeding.
4. When the task is complete, call `set_final_output` with a summary of what you did, then call `terminate`.
5. The system will evaluate your work automatically after termination. Make sure ALL work is complete before terminating.


Your workspace is: `{session.workspace}`
"""
        return task

    def setup_environment(self, item: dict, session: Any) -> EnvContext:
        """"""
        from tools.loca_mcp import set_mcp_tool

        task_dir = session.workspace
        config = item

        item.pop("_cached_eval", None)

        print(f"  [LOCAbench] Creating env: {config['_task_name']}...")
        env = _create_loca_env(config, task_dir)
        obs = env._get_instructions() if hasattr(env, '_get_instructions') else ""
        print(f"  [LOCAbench] Env created. Instruction: {len(obs)} chars")

        _strict = os.environ.get("LOCA_STRICT_PREPROCESS", "").strip() in ("1", "true", "True")
        _check_preprocess_integrity(task_dir, config["_task_name"], strict=_strict)

        item["_task_instruction"] = obs

        print(f"  [LOCAbench] Starting MCP servers: {list(config['mcp_servers'].keys())}...")
        mcp_tool, catalog = _setup_mcp_tool(config, task_dir)
        print(f"  [LOCAbench] MCP ready: {len(catalog)} tools discovered")

        item["_tool_catalog"] = catalog

        set_mcp_tool(mcp_tool, catalog)

        return EnvContext(data={
            "env": env,
            "mcp_tool": mcp_tool,
            "catalog": catalog,
            "task_dir": task_dir,
            "task_name": config["_task_name"],
            "seed": config["_seed"],
            "context_level": config["_context_level"],
        })

    def teardown_environment(self, env_ctx: EnvContext) -> None:
        """"""
        from tools.loca_mcp import clear_mcp_tool

        clear_mcp_tool()

        mcp_tool = env_ctx.data.get("mcp_tool")
        if mcp_tool:
            try:
                mcp_tool.close()
            except Exception as e:
                print(f"  [LOCAbench] Warning: MCP cleanup error: {e}")
            finally:
                _unregister_mcp_tool(mcp_tool)

    def evaluate(self, item: dict, predicted: str, session: Any, **ctx) -> EvalResult:
        cached = item.get("_cached_eval")
        if cached is not None:
            return cached

        env = ctx.get("env")
        if env is None:
            return EvalResult(
                success=False, score=0.0,
                summary="No LOCA-bench environment available for evaluation",
            )

        try:
            with _eval_lock:
                obs, reward, terminated, truncated, info = env.step("claim_done")

            score = float(reward)
            success = score >= 1.0

            eval_details = info.get("evaluation", "")
            if isinstance(eval_details, dict):
                eval_details = json.dumps(eval_details)[:500]
            elif not isinstance(eval_details, str):
                eval_details = str(eval_details)[:500]

            return EvalResult(
                success=success,
                score=score,
                summary=f"reward={score:.1f} ({'PASS' if success else 'FAIL'})",
                details=eval_details if eval_details else None,
                extra={
                    "reward": score,
                    "task_name": item.get("_task_name", ""),
                    "seed": item.get("_seed", 0),
                    "context_level": item.get("_context_level", ""),
                },
            )
        except Exception as e:
            return EvalResult(
                success=False, score=0.0,
                summary=f"Evaluation error: {e}",
                details=str(e)[:500],
            )

    def build_task_validator(self, item: dict, session: Any, **ctx):
        """"""
        from core.types import TaskValidation

        env = ctx.get("env")
        if env is None:
            return None

        async def _validator(output: str) -> TaskValidation:
            try:
                with _eval_lock:
                    obs, reward, terminated, truncated, info = env.step("claim_done")
                score = float(reward)
                success = score >= 1.0

                eval_details = info.get("error", "") or info.get("evaluation", "")
                if isinstance(eval_details, dict):
                    eval_details = json.dumps(eval_details)[:500]
                item["_cached_eval"] = EvalResult(
                    success=success,
                    score=score,
                    summary=f"reward={score:.1f} ({'PASS' if success else 'FAIL'})",
                    details=str(eval_details)[:500] if eval_details else None,
                    extra={
                        "reward": score,
                        "task_name": item.get("_task_name", ""),
                        "seed": item.get("_seed", 0),
                        "context_level": item.get("_context_level", ""),
                    },
                )

                task_name = item.get("_task_name", "")
                summary = f"LOCA-bench {task_name}: reward={score:.1f} ({'PASS' if success else 'FAIL'})"

                details_parts = [summary]
                if not success:
                    error_info = info.get("error", "")
                    if error_info:
                        details_parts.append(f"Failure reason: {str(error_info)[:800]}")

                    eval_log = _extract_eval_log(ctx.get("task_dir", ""), task_name)
                    if eval_log:
                        details_parts.append(f"Evaluation log excerpt:\n{eval_log}")

                    if obs and isinstance(obs, str) and len(obs.strip()) > 0:
                        details_parts.append(f"Environment observation: {obs[:800]}")

                    if output and len(output.strip()) > 0:
                        details_parts.append(f"Agent claimed output:\n{output[:1000]}")

                    details_parts.append(
                        "\nKey areas to improve:\n"
                        "  - Ensure ALL items are processed — count them before terminating\n"
                        "  - Verify output format matches exactly (directory names, column headers, email subjects)\n"
                        "  - Check pagination completeness (iterate ALL pages until empty)\n"
                        "  - Confirm no items were skipped or duplicated\n"
                        "  - For customer/order filtering: check the COMPLETE dataset criteria, not just surface-level counts\n"
                        "  - Do NOT call claim_done_claim_done — it doesn't exist. Just call set_final_output + terminate"
                    )

                return TaskValidation(
                    success=success,
                    summary=summary,
                    details="\n".join(details_parts),
                )
            except Exception as e:
                return TaskValidation(
                    success=False,
                    summary=f"Evaluation error: {e}",
                    details=str(e)[:500],
                )

        return _validator

    def build_record(self, item, idx, predicted, eval_result, session, error):
        extra = eval_result.extra or {}

        err_str = error or ""
        forced_termination = None
        if err_str:
            low = err_str.lower()
            if "timeout" in low:
                forced_termination = "timeout"
            elif "cost_limit" in low or "cost limit" in low:
                forced_termination = "cost_limit"
            elif "max_messages" in low:
                forced_termination = "max_messages"

        return {
            "idx": idx,
            "task_name": extra.get("task_name", item.get("_task_name", "")),
            "seed": extra.get("seed", item.get("_seed", 0)),
            "context_level": extra.get("context_level", item.get("_context_level", "")),
            "split": item.get("_split", item.get("_context_level", "")),
            "reward": extra.get("reward", 0.0),
            "score": eval_result.score,
            "success": eval_result.success,
            "eval_summary": eval_result.summary[:200] if eval_result.summary else "",
            "eval_details": eval_result.details[:500] if eval_result.details else "",
            "model_output": predicted[:2000] if predicted else "",
            "run_error": error,
            "forced_termination": forced_termination,
            "session_id": session.id,
        }

    def _make_error_record(self, idx: int, item: dict, error: Exception) -> dict:
        err_str = str(error)
        low = err_str.lower()
        forced_termination = None
        if "timeout" in low:
            forced_termination = "timeout"
        elif "cost_limit" in low or "cost limit" in low:
            forced_termination = "cost_limit"
        elif "max_messages" in low:
            forced_termination = "max_messages"
        return {
            "idx": idx,
            "index": idx,
            "task_name": item.get("_task_name", ""),
            "seed": item.get("_seed", 0),
            "context_level": item.get("_context_level", ""),
            "split": item.get("_split", item.get("_context_level", "")),
            "status": "error",
            "error": err_str,
            "run_error": err_str,
            "forced_termination": forced_termination,
            "score": 0.0,
            "success": False,
            "reward": 0.0,
            "eval_summary": f"Error: {err_str[:150]}",
            "eval_details": "",
            "model_output": "",
            "session_id": "",
        }

    def compute_summary(self, records, args):
        total = len(records)
        if total == 0:
            return {"total": 0, "avg_score": 0, "pass_rate": 0}

        scores = [r.get("score", 0.0) for r in records]
        passed = sum(1 for s in scores if s >= 1.0)
        avg = sum(scores) / total

        by_task = defaultdict(list)
        for r in records:
            by_task[r.get("task_name", "?")].append(r.get("score", 0.0))

        task_summary = {}
        for task, task_scores in sorted(by_task.items()):
            task_summary[task] = {
                "count": len(task_scores),
                "pass": sum(1 for s in task_scores if s >= 1.0),
                "avg": round(sum(task_scores) / len(task_scores), 3),
            }

        return {
            "total": total,
            "passed": passed,
            "pass_rate": round(passed / total, 4) if total else 0,
            "avg_score": round(avg, 4),
            "by_task": task_summary,
        }

    def print_summary(self, records: list[dict]) -> None:
        total = len(records)
        if total == 0:
            print("No results.")
            return

        scores = [r.get("score", 0.0) for r in records]
        passed = sum(1 for s in scores if s >= 1.0)
        avg = sum(scores) / total

        print(f"\n{'=' * 60}")
        print(f"LOCA-bench Results: {passed}/{total} passed ({passed/total*100:.1f}%)")
        print(f"Average score: {avg:.3f}")
        print(f"{'=' * 60}")

        by_task = defaultdict(list)
        for r in records:
            by_task[r.get("task_name", "?")].append(r.get("score", 0.0))

        print("\nBy Task:")
        for task in sorted(by_task):
            vals = by_task[task]
            p = sum(1 for s in vals if s >= 1.0)
            print(f"  {task:45s}: {p}/{len(vals)} passed, avg={sum(vals)/len(vals):.3f}")

        by_seed = defaultdict(list)
        for r in records:
            by_seed[r.get("seed", 0)].append(r.get("score", 0.0))

        if len(by_seed) > 1:
            print("\nBy Seed:")
            for seed in sorted(by_seed):
                vals = by_seed[seed]
                p = sum(1 for s in vals if s >= 1.0)
                print(f"  seed={seed}: {p}/{len(vals)} passed, avg={sum(vals)/len(vals):.3f}")

        errors = [r for r in records if r.get("run_error")]
        if errors:
            print(f"\nErrors: {len(errors)}")
            for r in errors[:5]:
                print(f"  [{r.get('idx')}] {r.get('task_name')}: {r.get('run_error', '')[:100]}")

    def dry_run_print(self, items, args):
        context_level = getattr(args, "split", "128k")
        print(f"LOCA-bench ({context_level}): {len(items)} configurations\n")

        by_task = defaultdict(list)
        for item in items:
            by_task[item["_task_name"]].append(item["_seed"])

        print("By Task:")
        for task in sorted(by_task):
            seeds = sorted(by_task[task])
            print(f"  {task:45s}: seeds={seeds}")

        print(f"\nTotal: {len(by_task)} task types × {len(items)//len(by_task) if by_task else 0} seeds = {len(items)} configurations")

        print("\nFirst 10 items:")
        for i, item in enumerate(items[:10]):
            name = item["_task_name"]
            seed = item["_seed"]
            servers = list(item.get("mcp_servers", {}).keys())
            print(f"  [{i}] {name} seed={seed}")
            print(f"      MCP servers: {servers}")
        if len(items) > 10:
            print(f"  ... and {len(items) - 10} more")



if __name__ == "__main__":
    LOCABenchAdapter().cli()
