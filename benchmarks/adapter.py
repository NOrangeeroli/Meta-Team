"""Base adapter class for benchmark integration."""

import os
import sys
import json
import atexit
import asyncio
import threading
import argparse
import subprocess
import concurrent.futures
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

_print_lock = threading.Lock()


_CONTAINER_PREFIXES = (
    "meta-team-swe-",       # SWE-bench
    "mt-pro-",              # SWE-bench Pro
    "mt-nl2rb-",            # NL2RepoBench (agent)
    "nl2rb-eval-",          # NL2RepoBench (eval)
    "mt-bswe-",             # BeyondSWE
    "sa-baseline-",         # Single-Agent Baseline
)

_owned_containers: dict[str, object] = {}   # container_name → container obj
_owned_lock = threading.Lock()


def register_container(name: str, container) -> None:
    with _owned_lock:
        _owned_containers[name] = container


def unregister_container(name: str) -> None:
    with _owned_lock:
        _owned_containers.pop(name, None)


def _cleanup_owned_containers() -> None:
    with _owned_lock:
        to_clean = list(_owned_containers.items())
    if not to_clean:
        return
    for name, ctr in to_clean:
        try:
            ctr.stop(timeout=5)
        except Exception:
            pass
        try:
            ctr.remove(force=True)
        except Exception:
            pass
    for name, _ in to_clean:
        try:
            subprocess.run(
                ["docker", "rm", "-f", name],
                capture_output=True, timeout=10,
            )
        except Exception:
            pass


def cleanup_stale_containers(quiet: bool = False) -> int:
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return 0

        names = [n.strip() for n in result.stdout.strip().split("\n") if n.strip()]
        to_remove = [n for n in names
                     if any(n.startswith(p) for p in _CONTAINER_PREFIXES)]

        if not to_remove:
            return 0

        if not quiet:
            print(f"\n[cleanup] Found {len(to_remove)} stale meta-team container(s), "
                  f"removing...")

        removed = 0
        for name in to_remove:
            try:
                subprocess.run(
                    ["docker", "rm", "-f", name],
                    capture_output=True, timeout=30,
                )
                removed += 1
                if not quiet:
                    print(f"  removed: {name}")
            except Exception:
                if not quiet:
                    print(f"  [warn] failed to remove: {name}")

        if not quiet and removed:
            print(f"[cleanup] Removed {removed} container(s).")
        return removed

    except FileNotFoundError:
        return 0
    except Exception:
        return 0


atexit.register(_cleanup_owned_containers)

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


# ---------------------------------------------------------------------------

@dataclass
class EvalResult:
    success: bool
    score: float
    summary: str = ""
    details: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class EnvContext:
    data: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------

class BenchmarkAdapter(ABC):

    benchmark_name: str = ""            # "swe_bench" / "swe_bench_pro" / "nl2repobench" / "beyondswe"
    default_team: str = ""              # "pool_SWE_Pro"
    default_timeout: float = 300.0
    default_evolve_timeout: float = 600.0
    default_max_cost: float = 0.0
    default_split: str = ""
    results_subdir: str = ""
    split_choices: list[str] | None = None

    # ---------------------------------------------------------------------------

    @abstractmethod
    def load_dataset(self, args: argparse.Namespace) -> list[dict]:
        ...

    @abstractmethod
    def get_item_id(self, item: dict) -> str:
        ...

    @abstractmethod
    def build_task(self, item: dict, session: Any, workspace_files: list[str]) -> str:
        ...

    @abstractmethod
    def evaluate(self, item: dict, predicted: str, session: Any, **ctx) -> EvalResult:
        ...

    @abstractmethod
    def build_record(self, item: dict, idx: int, predicted: str,
                     eval_result: EvalResult, session: Any, error: str) -> dict:
        ...

    @abstractmethod
    def print_summary(self, records: list[dict]) -> None:
        ...

    # ---------------------------------------------------------------------------

    def setup_environment(self, item: dict, session: Any) -> EnvContext:
        return EnvContext()

    def teardown_environment(self, env_ctx: EnvContext) -> None:
        pass

    def post_process(self, item: dict, session: Any, env_ctx: EnvContext) -> None:
        pass

    def get_patch_for_snapshot(self, env_ctx: EnvContext) -> str:
        return ""

    def build_task_validator(self, item: dict, session: Any, **ctx):
        return None

    def add_extra_args(self, parser: argparse.ArgumentParser) -> None:
        pass

    def compute_summary(self, records: list[dict], args: argparse.Namespace) -> dict:
        total = len(records)
        scores = [r.get("score", 0.0) for r in records]
        avg = sum(scores) / total if total else 0.0
        correct = sum(1 for s in scores if s >= 1.0)

        timeout_count = 0
        error_count = 0
        for r in records:
            err = r.get("run_error") or r.get("error") or ""
            if err:
                error_count += 1
                if "TIMEOUT" in err.upper():
                    timeout_count += 1

        return {
            "total": total,
            "avg_score": round(avg, 4),
            "correct": correct,
            "timeout_count": timeout_count,
            "error_count": error_count,
        }

    def dry_run_print(self, items: list[dict], args: argparse.Namespace) -> None:
        print(f"{self.benchmark_name} {getattr(args, 'split', '')}: {len(items)} items\n")
        for i, item in enumerate(items):
            item_id = self.get_item_id(item)
            print(f"  [{i}] {item_id}")
            if i >= 19:
                remaining = len(items) - 20
                if remaining > 0:
                    print(f"  ... and {remaining} more")
                break

    def prepare_items(self, items: list[dict],
                      args: argparse.Namespace) -> list[dict]:
        if args.cases is not None:
            indices = [int(x.strip()) for x in args.cases.split(",")]
            items = [items[i] for i in indices if 0 <= i < len(items)]
        return items

    # ---------------------------------------------------------------------------

    @property
    def results_dir(self) -> Path:
        return BASE_DIR / "benchmarks" / self.results_subdir

    async def run_single_case(
        self,
        item: dict,
        idx: int,
        args: argparse.Namespace,
        run_mgr: Any,
        team_name: str,
        evolve: bool,
        timeout_secs: float,
    ) -> dict:
        from main import (
            _save_trace, copy_team_to_session,
        )
        from core.session import Session

        task_id = self.get_item_id(item)
        with _print_lock:
            print(f"\n{'=' * 60}")
            print(f"[{idx}] {task_id}")
            print(f"{'=' * 60}")

        team_version, actual_source = run_mgr.get_latest_team_version()
        with _print_lock:
            print(f"  [RunManager] using team {team_version}")

        # Pool + Runner info + Session
        from main import load_pool
        pre_pool = load_pool(actual_source)
        team_info = {
            "team_name": team_name,
            "structure": "pool",
            "chairman": pre_pool.chairman_name,
            "total_agents": len(pre_pool.agents),
            "agents": list(pre_pool.agents.keys()),
        }

        case_dir = run_mgr.create_case_dir(idx, task_id)
        session = Session.create(
            task=self.get_item_id(item),
            team_info=team_info,
            session_dir=case_dir,
        )

        # Copy team/pool to session
        runtime_team_dir = copy_team_to_session(Path(session.dir), actual_source)

        predicted = ""
        error_msg = ""
        result = None
        env_ctx = EnvContext()
        eval_result = None

        try:
            env_ctx = self.setup_environment(item, session)

            workspace_files = [
                f.name for f in Path(session.workspace).iterdir()
                if not f.name.startswith(".")
            ]
            task = self.build_task(item, session, workspace_files)

            from main import load_pool
            from core.runner import Runner
            pool = load_pool(runtime_team_dir)
            runner = Runner(
                pool_dir=runtime_team_dir,
                chairman_name=pool.chairman_name,
                constitution=pool.constitution,
                tool_registry=pool.registry,
                max_seconds=float(timeout_secs),
                max_messages=int(pool.settings.get("max_messages", 200)),
                enable_reflection=evolve,
                max_cost_usd=float(getattr(args, "max_cost", 0) or 0),
                reflection_phase_timeout=float(pool.settings.get("reflection_phase_timeout", 0)),
            )

            if evolve:
                validator = self.build_task_validator(
                    item, session, **env_ctx.data)
                if validator:
                    runner.set_task_validator(validator)

                split = getattr(args, "split", "") or ""
                runner._evolution_description_key = f"{self.benchmark_name}_{split}" if split else self.benchmark_name

                def _freeze_eval_snapshot():
                    snapshot_path = Path(session.workspace) / "patch_pre_reflection.diff"
                    if snapshot_path.exists():
                        return
                    try:
                        patch = self.get_patch_for_snapshot(env_ctx)
                        if patch:
                            snapshot_path.write_text(patch, encoding="utf-8")
                    except Exception:
                        pass

                runner.set_pre_reflection_hook(_freeze_eval_snapshot)

            if evolve:
                reflection_phase_timeout = float(pool.settings.get("reflection_phase_timeout", 0)) or 300.0
                outer_timeout = timeout_secs + reflection_phase_timeout * 3 + 120
            else:
                outer_timeout = timeout_secs + 300
            result = await asyncio.wait_for(
                runner.run(task, session=session),
                timeout=outer_timeout,
            )

            predicted = result.output.strip() if result.output else ""

            self.post_process(item, session, env_ctx)

            try:
                eval_result = self.evaluate(
                    item, predicted, session, **env_ctx.data)
            except Exception as e:
                eval_result = EvalResult(
                    success=False, score=0.0,
                    summary=f"Evaluation error: {e}",
                    details=str(e)[:500],
                )

        except asyncio.TimeoutError:
            predicted = ""
            error_msg = f"TIMEOUT after {timeout_secs}s"
        except Exception as e:
            predicted = ""
            error_msg = str(e)
            import traceback
            with _print_lock:
                traceback.print_exc()
        finally:
            if eval_result is None:
                try:
                    eval_result = self.evaluate(
                        item, predicted, session, **env_ctx.data)
                except Exception as e:
                    eval_result = EvalResult(
                        success=False, score=0.0,
                        summary=f"Evaluation error: {e}",
                        details=str(e)[:500],
                    )

            try:
                self.teardown_environment(env_ctx)
            except Exception as e:
                with _print_lock:
                    print(f"[warn] failed to teardown environment: {e}")

        # Close session
        try:
            status = "completed" if not error_msg else "failed"
            session.close(
                status,
                summary={"error": error_msg} if error_msg else None,
            )
            _save_trace(session.id, str(session.dir))
        except Exception as e:
            with _print_lock:
                print(f"[warn] failed to close session: {e}")

        has_reflection = (
            result is not None
            and getattr(result, "reflection_applied", False)
        )
        new_version = team_version
        if evolve:
            try:
                include_l3 = has_reflection
                before_version = team_version
                new_version, modified = run_mgr.persist_team_version(
                    session_team_dir=runtime_team_dir,
                    include_l3=include_l3,
                )
                if modified:
                    run_mgr.write_changelog(
                        case_index=idx,
                        task_id=task_id,
                        from_version=before_version,
                        to_version=new_version,
                        modified_files=modified,
                        reflection_applied=include_l3,
                    )
            except Exception as e:
                with _print_lock:
                    print(f"[warn] failed to persist evolution: {e}")

        icon = "✅" if eval_result.success else (
            "🔶" if eval_result.score > 0 else "❌")
        with _print_lock:
            print(f"\n{icon} [{idx}] {task_id}: score={eval_result.score:.3f}")
            if error_msg:
                print(f"   Run Error: {error_msg[:200]}")
            if eval_result.details:
                print(f"   Eval: {eval_result.summary[:200]}")


        record = self.build_record(
            item, idx, predicted, eval_result, session, error_msg)
        run_mgr.save_case_result(Path(session.dir), record)

        return record

    def _make_error_record(self, idx: int, item: dict, error: Exception) -> dict:
        return {
            "idx": idx,
            "index": idx,
            "instance_id": item.get("instance_id", ""),
            "repo": item.get("repo", ""),
            "task_type": item.get("_task_type", ""),
            "status": "error",
            "error": str(error),
            "run_error": str(error),
            "resolved": False,
            "score": 0.0,
            "eval_summary": f"Error: {str(error)[:150]}",
            "model_output": "",
            "patch": "",
        }

    async def run(self, args: argparse.Namespace) -> None:
        items = self.load_dataset(args)
        items = self.prepare_items(items, args)

        if args.dry_run:
            self.dry_run_print(items, args)
            return

        if args.results_only:
            self._show_results_only()
            return

        team_name = args.team
        evolve = args.evolve
        timeout_secs = args.timeout

        run_id = (args.run_id
                  or datetime.now().strftime("%Y%m%d_%H%M%S")
                  + f"_{self.benchmark_name}")
        if evolve:
            run_id += "_evolve"

        source_team_dir = BASE_DIR / "agents" / team_name
        if not source_team_dir.exists():
            print(f"[error] Team not found: {source_team_dir}")
            sys.exit(1)

        from core.run_manager import RunManager
        resume = getattr(args, "resume", False)
        run_mgr = RunManager.create_run(
            run_id=run_id,
            source_team_dir=source_team_dir,
            team_name=team_name,
            config={
                "benchmark": self.benchmark_name,
                "split": getattr(args, "split", ""),
                "cases": len(items),
                "timeout": timeout_secs,
                "evolve": evolve,
                "layers": getattr(args, "layers", None),
            },
            resume=resume,
        )

        print(f"Run ID: {run_id}")
        print(f"Benchmark: {self.benchmark_name}")
        print(f"Cases: {len(items)}")
        print(f"Team: {team_name}")
        print(f"Timeout: {timeout_secs}s per case")
        print(f"Evolve: {evolve}")
        print(f"Workers: {getattr(args, 'workers', 1)}")
        print(f"Run Dir: {run_mgr.run_dir}")


        records = []
        workers = getattr(args, "workers", 1)

        try:
            if evolve or workers <= 1:
                for i, item in enumerate(items):
                    record = await self.run_single_case(
                        item, i, args, run_mgr,
                        team_name=team_name,
                        evolve=evolve,
                        timeout_secs=timeout_secs,
                    )
                    records.append(record)
            else:
                print(f"Parallel mode: {workers} workers (ThreadPoolExecutor)")

                def _process_case_sync(i: int, item: dict) -> dict:
                    loop = asyncio.new_event_loop()

                    def _quiet_exception_handler(loop, context):
                        msg = context.get("message", "")
                        exc = context.get("exception")
                        if exc and "bound to a different event loop" in str(exc):
                            return
                        loop.default_exception_handler(context)

                    loop.set_exception_handler(_quiet_exception_handler)
                    try:
                        return loop.run_until_complete(self.run_single_case(
                            item, i, args, run_mgr,
                            team_name=team_name,
                            evolve=evolve,
                            timeout_secs=timeout_secs,
                        ))
                    except Exception as e:
                        import traceback
                        with _print_lock:
                            print(f"[Case {i}] EXCEPTION: {e}")
                            traceback.print_exc()
                        return self._make_error_record(i, item, e)
                    finally:
                        loop.close()

                def _run_all_parallel():
                    with concurrent.futures.ThreadPoolExecutor(
                        max_workers=workers
                    ) as executor:
                        futures = {
                            executor.submit(_process_case_sync, i, item): (i, item)
                            for i, item in enumerate(items)
                        }
                        result_map = {}
                        for future in concurrent.futures.as_completed(futures):
                            idx, item = futures[future]
                            try:
                                result_map[idx] = future.result()
                            except Exception as e:
                                import traceback
                                with _print_lock:
                                    print(f"[Case {idx}] FUTURE EXCEPTION: {e}")
                                    traceback.print_exc()
                                result_map[idx] = self._make_error_record(
                                    idx, item, e)
                        return [result_map[i] for i in range(len(items))]

                records = await asyncio.to_thread(_run_all_parallel)
        finally:
            with _owned_lock:
                leaked = len(_owned_containers)
            if leaked:
                print(f"\n[cleanup] Found {leaked} leaked container(s) "
                      f"from this process, cleaning up...")
                _cleanup_owned_containers()
                print(f"[cleanup] Done.")

        # Summary
        summary_data = self.compute_summary(records, args)
        summary = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "benchmark": self.benchmark_name,
            "split": getattr(args, "split", ""),
            "team": team_name,
            "evolve": evolve,
            "records": records,
            "team_versions": run_mgr.list_team_versions(),
            **summary_data,
        }
        run_mgr.save_summary(summary)

        # Legacy results dir
        legacy_dir = self.results_dir / run_id
        legacy_dir.mkdir(parents=True, exist_ok=True)
        with open(legacy_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        self.print_summary(records)

    def _show_results_only(self) -> None:
        if not self.results_dir.exists():
            print("No results yet.")
            return
        for run_dir in sorted(self.results_dir.iterdir()):
            if not run_dir.is_dir():
                continue
            summary_file = run_dir / "summary.json"
            if summary_file.exists():
                with open(summary_file, encoding="utf-8") as sf:
                    s = json.load(sf)
                score = s.get("avg_score", s.get("accuracy", 0))
                total = s.get("total", 0)
                split = s.get("split", "?")
                team = s.get("team", "?")
                evo = " [evolve]" if s.get("evolve") else ""
                print(f"  {run_dir.name}: score={score:.3f} "
                      f"({total} cases) split={split} team={team}{evo}")

    # CLI
    # ---------------------------------------------------------------------------

    def build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description=f"{self.benchmark_name} benchmark")
        if self.split_choices:
            parser.add_argument(
                "--split", type=str,
                default=self.default_split,
                choices=self.split_choices,
                help=f"Data subset (default: {self.default_split})",
            )
        parser.add_argument(
            "--cases", type=str, default=None,
            help="Comma-separated case indices")
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Print items only, do not run")
        parser.add_argument(
            "--results-only", action="store_true",
            help="Show existing results only")
        parser.add_argument(
            "--run-id", type=str, default=None,
            help="Specify run ID")
        parser.add_argument(
            "--team", type=str, default=self.default_team,
            help=f"Team to use (default: {self.default_team})")
        parser.add_argument(
            "--evolve", action="store_true",
            help="Enter evolution phase after each case")
        parser.add_argument(
            "--timeout", type=float, default=None,
            help="Timeout seconds per case")
        parser.add_argument(
            "--max-cost", type=float, default=None,
            help="Max cost USD per case (0=unlimited)")
        parser.add_argument(
            "--layers", type=str, default=None,
            help="Ablation: specify enabled evolution layers")
        parser.add_argument(
            "--workers", type=int, default=1,
            help="Parallel workers (non-evolve only, default 1=serial)")
        parser.add_argument(
            "--resume", action="store_true",
            help="Reuse existing run dir (append cases to same run-id)")
        parser.add_argument(
            "--rollout", type=int, default=1,
            help="Number of independent runs for avg@K (default: 1)")
        self.add_extra_args(parser)
        return parser

    def cli(self) -> None:
        parser = self.build_parser()
        args = parser.parse_args()

        if args.timeout is None:
            args.timeout = (self.default_evolve_timeout if args.evolve
                            else self.default_timeout)

        if args.max_cost is None:
            args.max_cost = self.default_max_cost

        if args.evolve and args.workers > 1:
            print("[error] --evolve and --workers > 1 are mutually exclusive. "
                  "Evolution mode requires sequential execution (--workers 1).")
            sys.exit(1)

        if args.rollout <= 1:
            asyncio.run(self.run(args))
        else:
            base_run_id = args.run_id or f"{self.benchmark_name}"
            for r in range(1, args.rollout + 1):
                args.run_id = f"{base_run_id}_r{r}"
                print(f"\n=== Rollout {r}/{args.rollout} (run_id: {args.run_id}) ===")
                asyncio.run(self.run(args))
