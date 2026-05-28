"""Runner — minimal task execution engine that manages Agent lifecycles and reflection."""

import asyncio
import logging
import time
import uuid
from pathlib import Path
from dataclasses import dataclass, field

from core.agent import Agent, AgentResult
from core.message_store import MessageStore
from core.reflection_runner import ReflectionMixin
from core.tool_registry import ToolRegistry
from core.utils import load_prompt_template as _load_prompt_template

logger = logging.getLogger(__name__)


@dataclass
class RunnerResult:
    """Result of a Runner execution."""
    output: str
    agents: dict[str, Agent] = field(default_factory=dict)
    cost_seconds: float = 0.0
    reflection_applied: bool = False
    metadata: dict = field(default_factory=dict)


class Runner(ReflectionMixin):
    """Minimal task execution engine. Starts Chairman, waits for terminate or timeout, collects results."""

    REFLECTION_MAX_STEPS = 50
    REFLECTION_PHASE_TIMEOUT = 300.0
    _CHAIRMAN_EXIT_GRACE_SECONDS = 2.0

    def __init__(
        self,
        pool_dir: str | Path,
        chairman_name: str,
        constitution: str = "",
        tool_registry: ToolRegistry | None = None,
        max_seconds: float = 600.0,
        max_messages: int = 200,
        idle_timeout: float = 120.0,
        enable_reflection: bool = False,
        max_cost_usd: float = 0.0,
        reflection_phase_timeout: float = 0.0,
    ):
        self.pool_dir = Path(pool_dir)
        self.chairman_name = chairman_name
        self.constitution = constitution
        self.tool_registry = tool_registry or ToolRegistry(
            str(Path(__file__).parent.parent / "tools")
        )
        self.max_seconds = max_seconds
        self.max_messages = max_messages
        self.idle_timeout = idle_timeout
        self.enable_reflection = enable_reflection
        self.max_cost_usd = max_cost_usd
        self.reflection_phase_timeout = (
            reflection_phase_timeout if reflection_phase_timeout > 0
            else self.REFLECTION_PHASE_TIMEOUT
        )

        self.runner_id: str = uuid.uuid4().hex

        self._pool_agents_cache: list[dict] | None = None

        self.message_store = MessageStore()
        self.agents: dict[str, Agent] = {}
        self._agent_tasks: dict[str, asyncio.Task] = {}  # name → asyncio.Task
        self._result: str | None = None
        self._done = asyncio.Event()
        self._forced_termination: str | None = None

        self._stopped_agents_cost: float = 0.0

        self._phase: str = "task_execution"
        self._all_reflection_agents: list[str] = []
        self._l1_completed: set[str] = set()
        self._l2_completed: set[str] = set()
        self._l3_completed: set[str] = set()
        self._reflection_phase_start: float = 0.0
        self._reflection_phase_guard: asyncio.Task | None = None
        self._agent_dirs: dict[str, str] = {}
        self._agent_change_suggestions: list[dict] = []
        self._reflection_applied: bool = False
        self._task_validation = None
        self._task_validator = None
        self._pre_reflection_hook = None
        self._evolution_description_key: str = ""
        self._run_start_time: float = 0.0
        self._event_log = None
        self._cwd: str | None = None
        self._task: str = ""

        self._reflection_plan = None
        self._reflection_review_state = None

    # ------------------------------------------------------------------

    def set_task_validator(self, validator) -> None:
        """Set task validation callback (injected by adapter)."""
        self._task_validator = validator

    def set_pre_reflection_hook(self, hook) -> None:
        """Set pre-reflection callback (injected by adapter for eval snapshot)."""
        self._pre_reflection_hook = hook

    # ------------------------------------------------------------------

    def load_agent_from_pool(self, agent_name: str) -> Agent:
        """Load an Agent from the Pool directory (does not start run_loop)."""
        agent_dir = self.pool_dir / agent_name
        if not agent_dir.exists():
            raise FileNotFoundError(f"Agent '{agent_name}' not found in pool: {agent_dir}")
        config_path = agent_dir / "config.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Agent '{agent_name}' has no config.yaml: {config_path}")
        return Agent(str(agent_dir), self.tool_registry)

    def start_agent(
        self,
        agent: Agent,
        event_log=None,
        cwd: str | None = None,
    ) -> None:
        """Start an agent from the pool and begin its run loop."""
        name = agent.config.name
        if name in self.agents:
            return

        agent.bind_message_store(self.message_store)
        agent._runner_ref = self
        agent._reflection_enabled = self.enable_reflection
        self.agents[name] = agent

        if self.enable_reflection:
            from tools.primitives import rebuild_primitive_schemas
            agent._primitive_tools_refresher = lambda: rebuild_primitive_schemas(
                self, include_chairman_tools=False,
            )

        if hasattr(agent, 'agent_dir'):
            self._agent_dirs[name] = str(agent.agent_dir)

        system_context = self._build_agent_context(agent)

        task = asyncio.create_task(
            agent.run_loop(
                event_log=event_log,
                cwd=cwd,
                initial_task=None,
                system_context=system_context,
                idle_timeout=self.idle_timeout,
                max_idle_rounds=5,
            ),
            name=f"agent-{name}",
        )
        self._agent_tasks[name] = task

    def stop_agent(self, agent_name: str) -> bool:
        """Stop a running agent gracefully."""
        task = self._agent_tasks.get(agent_name)
        if task and not task.done():
            task.cancel()
            agent = self.agents.get(agent_name)
            if agent:
                self._stopped_agents_cost += getattr(agent, "_total_cost_usd", 0.0)
            self.message_store.unregister(agent_name)
            self.agents.pop(agent_name, None)
            self._agent_tasks.pop(agent_name, None)
            return True
        return False

    def get_agent_states(self) -> dict[str, dict]:
        """Return current state of all agents in the pool."""
        states = {}
        for name, agent in self.agents.items():
            states[name] = {
                "state": agent._state,
                "state_since": agent._state_since,
            }
        return states

    def list_pool_agents(self) -> list[dict]:
        """List available agents in the pool directory."""
        if self._pool_agents_cache is None:
            self._pool_agents_cache = self._scan_pool_agents()

        for entry in self._pool_agents_cache:
            entry["started"] = entry["name"] in self.agents
        return self._pool_agents_cache

    def _scan_pool_agents(self) -> list[dict]:
        import os
        import yaml
        model_override = os.environ.get("META_TEAM_MODEL")

        result = []
        for agent_dir in sorted(self.pool_dir.iterdir()):
            if not agent_dir.is_dir():
                continue
            config_path = agent_dir / "config.yaml"
            if not config_path.exists():
                continue
            try:
                raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            name = raw.get("name", agent_dir.name)
            if name == self.chairman_name:
                continue
            result.append({
                "name": name,
                "description": raw.get("description", ""),
                "model": model_override or raw.get("model", ""),
                "tools": raw.get("tools", []),
                "skills": raw.get("skills", []),
                "started": False,
            })
        return result

    # ------------------------------------------------------------------

    async def run(self, task: str, session=None) -> RunnerResult:
        """Execute the full task lifecycle: start chairman, wait for completion, run reflection."""
        start = time.time()
        self._run_start_time = start
        event_log = session.event_log if session else None
        cwd = session.workspace if session else None
        self._event_log = event_log
        self._cwd = cwd
        self._task = task

        logger.info(
            "Runner[%s] starting: chairman=%s, pool=%s, max_seconds=%.0f, "
            "max_messages=%d, reflection=%s",
            self.runner_id[:8], self.chairman_name, self.pool_dir.name,
            self.max_seconds, self.max_messages, self.enable_reflection,
        )

        if event_log:
            event_log.log("runner.start", data={
                "task": task[:500],
                "chairman": self.chairman_name,
                "pool_dir": str(self.pool_dir),
                "max_seconds": self.max_seconds,
                "enable_reflection": self.enable_reflection,
            })

        if self.enable_reflection:
            from core.types import ReflectionPlan, ReviewState
            self._reflection_plan = ReflectionPlan()
            self._reflection_review_state = ReviewState()

        chairman = self.load_agent_from_pool(self.chairman_name)
        chairman.bind_message_store(self.message_store)
        chairman._runner_ref = self
        chairman._reflection_enabled = self.enable_reflection
        self.agents[self.chairman_name] = chairman

        if hasattr(chairman, 'agent_dir'):
            self._agent_dirs[self.chairman_name] = str(chairman.agent_dir)

        chairman_context = self._build_chairman_context()

        from tools.primitives import build_primitive_tools, rebuild_primitive_schemas, cleanup_handlers
        primitive_tools = build_primitive_tools(self)

        chairman._primitive_tools_refresher = lambda: rebuild_primitive_schemas(
            self, include_chairman_tools=True,
        )

        chairman_task = asyncio.create_task(
            chairman.run_loop(
                event_log=event_log,
                cwd=cwd,
                initial_task=f"## Task\n\n{task}",
                system_context=chairman_context,
                extra_tools=primitive_tools,
                idle_timeout=self.idle_timeout,
                max_idle_rounds=3,
            ),
            name=f"agent-{self.chairman_name}",
        )
        self._agent_tasks[self.chairman_name] = chairman_task

        guard_tasks = []
        if self.max_messages > 0:
            guard_tasks.append(
                asyncio.create_task(self._guard_max_messages(event_log))
            )
        if self.max_cost_usd > 0:
            guard_tasks.append(
                asyncio.create_task(self._guard_cost_limit(event_log))
            )

        #
        #

        async def _guard_chairman_exit():
            try:
                await chairman_task
            except (asyncio.CancelledError, Exception):
                pass
            await asyncio.sleep(self._CHAIRMAN_EXIT_GRACE_SECONDS)
            if not self._done.is_set():
                if event_log:
                    event_log.log("runner.chairman_exited_without_terminate", data={
                        "elapsed": round(time.time() - start, 2),
                        "phase": self._phase,
                    })
                self.message_store.terminate(reason="chairman_exited")
                self._done.set()

        chairman_guard = asyncio.create_task(_guard_chairman_exit())
        guard_tasks.append(chairman_guard)

        try:
            await asyncio.wait_for(self._done.wait(), timeout=self.max_seconds)
        except asyncio.TimeoutError:
            if self._phase != "task_execution":
                reflection_total_timeout = self.reflection_phase_timeout * 3 + 60
                if event_log:
                    event_log.log("runner.task_timeout_in_reflection", data={
                        "max_seconds": self.max_seconds,
                        "elapsed": round(time.time() - start, 2),
                        "phase": self._phase,
                        "reflection_total_timeout": reflection_total_timeout,
                    })
                try:
                    await asyncio.wait_for(
                        self._done.wait(), timeout=reflection_total_timeout,
                    )
                except asyncio.TimeoutError:
                    if event_log:
                        event_log.log("runner.reflection_total_timeout", data={
                            "timeout": reflection_total_timeout,
                            "elapsed": round(time.time() - start, 2),
                            "phase": self._phase,
                        })
                    self.message_store.terminate(reason="reflection_total_timeout")
            else:
                elapsed = round(time.time() - start, 2)
                total_cost = round(self._get_total_cost_usd(), 4)
                if event_log:
                    event_log.log("runner.timeout", data={
                        "max_seconds": self.max_seconds,
                        "elapsed": elapsed,
                        "total_cost_usd": total_cost,
                    })
                self._forced_termination = (
                    f"timeout (elapsed {elapsed}s, limit {self.max_seconds}s, "
                    f"cost ${total_cost})"
                )

        try:
            if (
                self._forced_termination
                and self.enable_reflection
                and self._phase == "task_execution"
            ):
                for t in guard_tasks:
                    t.cancel()
                if guard_tasks:
                    await asyncio.gather(*guard_tasks, return_exceptions=True)
                guard_tasks.clear()

                await self._enter_forced_reflection(event_log)

                if not self._done.is_set():
                    reflection_total_timeout = self.reflection_phase_timeout * 3 + 60
                    try:
                        await asyncio.wait_for(
                            self._done.wait(), timeout=reflection_total_timeout,
                        )
                    except asyncio.TimeoutError:
                        if event_log:
                            event_log.log("runner.reflection_total_timeout", data={
                                "timeout": reflection_total_timeout,
                                "elapsed": round(time.time() - start, 2),
                                "phase": self._phase,
                            })
                        self.message_store.terminate(reason="forced_reflection_total_timeout")
        finally:
            cleanup_handlers(self)

        if self._agent_tasks:
            done, pending = await asyncio.wait(
                self._agent_tasks.values(),
                timeout=10.0,
                return_when=asyncio.ALL_COMPLETED,
            )
            for t in pending:
                t.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)

        for t in guard_tasks:
            t.cancel()
        if self._reflection_phase_guard and not self._reflection_phase_guard.done():
            self._reflection_phase_guard.cancel()
            guard_tasks.append(self._reflection_phase_guard)
        if guard_tasks:
            await asyncio.gather(*guard_tasks, return_exceptions=True)

        cost = time.time() - start
        total_cost_usd = self._get_total_cost_usd()

        #
        if (
            not self._result
            and self._forced_termination
            and not self.enable_reflection
        ):
            chairman = self.agents.get(self.chairman_name)
            if (chairman is not None
                    and getattr(chairman, "messages", None)
                    and len(chairman.messages) >= 2):
                try:
                    forced_output = await self._force_finalize_chairman(
                        chairman, event_log,
                    )
                    if forced_output and forced_output.strip():
                        self._result = forced_output.strip()
                        if event_log:
                            event_log.log("runner.force_finalize_success", data={
                                "reason": self._forced_termination,
                                "output_len": len(self._result),
                            })
                        logger.info(
                            "Runner[%s]: force-finalize LLM call produced "
                            "%d-char output (trigger=%s)",
                            self.runner_id[:8], len(self._result),
                            self._forced_termination,
                        )
                except Exception as e:
                    if event_log:
                        event_log.log("runner.force_finalize_error", data={
                            "reason": self._forced_termination,
                            "error": str(e)[:500],
                        })
                    logger.warning(
                        "Runner[%s]: force-finalize failed: %s",
                        self.runner_id[:8], e,
                    )

        #
        if not self._result:
            chairman = self.agents.get(self.chairman_name)
            fallback_output = ""
            fallback_reason = ""
            if chairman is not None and hasattr(chairman, "messages"):
                for msg in reversed(chairman.messages or []):
                    if msg.get("role") != "assistant":
                        continue
                    if msg.get("tool_calls"):
                        continue
                    content = msg.get("content") or ""
                    if isinstance(content, str) and len(content.strip()) >= 200:
                        fallback_output = content.strip()
                        fallback_reason = "last_pure_assistant_message"
                        break

                if not fallback_output:
                    for msg in reversed(chairman.messages or []):
                        if msg.get("role") != "assistant":
                            continue
                        content = msg.get("content") or ""
                        if isinstance(content, str) and len(content.strip()) >= 500:
                            fallback_output = content.strip()
                            fallback_reason = "last_assistant_content_with_tool_calls"
                            break

            if fallback_output:
                if event_log:
                    event_log.log("runner.fallback_output_from_assistant", data={
                        "reason": fallback_reason,
                        "output_len": len(fallback_output),
                    })
                logger.warning(
                    "Runner[%s]: Chairman did not call set_final_output/finalize_task; "
                    "falling back to last assistant content (%d chars, reason=%s)",
                    self.runner_id[:8], len(fallback_output), fallback_reason,
                )
                self._result = fallback_output

        output = self._result or "[no output — Chairman did not call set_final_output/finalize_task]"

        logger.info(
            "Runner[%s] finished: %.1fs elapsed, $%.4f cost, agents=%s, "
            "phase=%s, reflection_applied=%s%s",
            self.runner_id[:8], cost, total_cost_usd,
            list(self.agents.keys()), self._phase,
            self._reflection_applied,
            f", forced_termination={self._forced_termination}" if self._forced_termination else "",
        )

        if event_log:
            event_log.log("runner.end", data={
                "output": output[:1000],
                "cost_seconds": round(cost, 2),
                "cost_usd": round(total_cost_usd, 4),
                "agents_used": list(self.agents.keys()),
                "reflection_applied": self._reflection_applied,
            })

        return RunnerResult(
            output=output,
            agents=self.agents,
            cost_seconds=cost,
            reflection_applied=self._reflection_applied,
            metadata={
                "agents_used": list(self.agents.keys()),
                "enable_reflection": self.enable_reflection,
                "phase": self._phase,
                "forced_termination": self._forced_termination,
            },
        )

    # ------------------------------------------------------------------

    def _build_chairman_context(self) -> str:
        parts = []

        if self.constitution:
            parts.append(f"## Constitution\n\n{self.constitution}")

        if self.enable_reflection:
            parts.append(
                "## Your Role\n\n"
                "You are the Chairman of this Meta-Team. Your responsibilities:\n"
                "1. **Analyze the task** and decide which agents to recruit from the Pool\n"
                "2. **Use `list_pool`** to see available agents and their capabilities\n"
                "3. **Use `start_agent`** to recruit agents into the team\n"
                "4. **Use `send_message`** to assign tasks and coordinate work\n"
                "5. **Use `wait_for_replies`** to wait for agents to complete their work\n"
                "6. **Use `finalize_task`** to submit the final result and enter reflection\n"
                "7. After reflection is complete, **use `terminate`** to end the task\n\n"
                "All agents can communicate freely with each other via send_message.\n\n"
                "**IMPORTANT**: When the task is done, call `finalize_task(output)` "
                "(NOT `set_final_output` + `terminate`). This will enter the reflection phase "
                "where you and your team improve for future tasks."
            )
        else:
            parts.append(
                "## Your Role\n\n"
                "You are the Chairman of this Meta-Team. Your responsibilities:\n"
                "1. **Analyze the task** and decide which agents to recruit from the Pool\n"
                "2. **Use `list_pool`** to see available agents and their capabilities\n"
                "3. **Use `start_agent`** to recruit agents into the team\n"
                "4. **Use `send_message`** to assign tasks and coordinate work\n"
                "5. **Use `wait_for_replies`** to wait for agents to complete their work\n"
                "6. **Use `set_final_output`** to submit the final result\n"
                "7. **Use `terminate`** to end the task\n\n"
                "All agents can communicate freely with each other via send_message."
            )

        return "\n\n---\n\n".join(parts)

    def _build_agent_context(self, agent: Agent) -> str:
        parts = []

        if self.constitution:
            parts.append(f"## Constitution\n\n{self.constitution}")

        parts.append(
            "## Your Role\n\n"
            "You are a member of a Meta-Team, recruited by the Chairman for this task.\n"
            "- Wait for the Chairman to assign you work via message\n"
            "- Complete your assigned work using your tools\n"
            "- Report results back to the Chairman via send_message\n"
            "- You can also communicate with other team members directly"
        )
        
        # NEW: Load and inject teammate profiles from previous reflections
        teammate_context = self._build_teammate_context(agent)
        if teammate_context:
            parts.append(teammate_context)

        return "\n\n---\n\n".join(parts)
    
    def _build_teammate_context(self, agent: Agent) -> str:
        """Load teammate profiles from evolution files and inject as context.
        
        This allows agents to make better decisions about who to ask for help,
        who is reliable, etc. based on previous task experience.
        """
        # Try to find this agent's teammate_profiles.yaml
        agent_name = agent.config.name if hasattr(agent.config, 'name') else agent.name
        agent_dir = self._agent_dirs.get(agent_name)
        
        if not agent_dir:
            return ""
        
        profiles_path = Path(agent_dir) / "evolution" / "teammate_profiles.yaml"
        if not profiles_path.exists():
            return ""
        
        try:
            import yaml
            with open(profiles_path, 'r', encoding='utf-8') as f:
                profiles = yaml.safe_load(f)
            
            if not profiles:
                return ""
            
            lines = ["## Team Insights (From Your Experience)"]
            lines.append("")
            
            for teammate_name, profile in profiles.items():
                if not isinstance(profile, dict):
                    continue
                
                reliability = profile.get("reliability", "unknown")
                strengths = profile.get("strengths", [])
                weaknesses = profile.get("weaknesses", [])
                communication = profile.get("communication_style", "")
                
                lines.append(f"### {teammate_name}")
                if communication:
                    lines.append(f"- **Style**: {communication}")
                if reliability:
                    lines.append(f"- **Reliability**: {reliability}")
                if strengths:
                    strengths_str = ", ".join(strengths) if isinstance(strengths, list) else str(strengths)
                    lines.append(f"- **Strengths**: {strengths_str}")
                if weaknesses:
                    weaknesses_str = ", ".join(weaknesses) if isinstance(weaknesses, list) else str(weaknesses)
                    lines.append(f"- **Weaknesses**: {weaknesses_str}")
                lines.append("")
            
            return "\n".join(lines)
        
        except Exception as e:
            logger.debug("Failed to load teammate profiles from %s: %s", profiles_path, e)
            return ""

    # ------------------------------------------------------------------

    async def _force_finalize_chairman(self, chairman, event_log=None) -> str:
        from core import llm

        FORCE_FINISH_MSG = (
            "You have reached the resource budget limit "
            f"({self._forced_termination}). "
            "You can no longer call any tools. "
            "Based on ALL the information you have already gathered above "
            "in this conversation, provide your FINAL ANSWER NOW as a "
            "comprehensive markdown report. Do NOT make any tool calls. "
            "Do NOT say 'let me do X'. Directly output the complete final "
            "report as your response content. End with a 'Confidence: X%' line."
        )

        force_msgs = list(chairman.messages) + [
            {"role": "user", "content": FORCE_FINISH_MSG},
        ]

        if event_log:
            event_log.log("runner.force_finalize_start",
                agent=chairman.config.name, data={
                    "reason": self._forced_termination,
                    "history_len": len(chairman.messages),
                })

        response = await asyncio.wait_for(
            llm.complete(
                model=chairman.config.model,
                messages=force_msgs,
                tools=None,
                temperature=chairman.config.temperature,
                max_tokens=max(4096, chairman.config.max_tokens),
            ),
            timeout=240.0,
        )

        if not response.choices:
            return ""
        msg = response.choices[0].message
        content = (msg.content or "").strip()

        try:
            if hasattr(chairman, "_track_cost_usd"):
                chairman._track_cost_usd(response)
        except Exception as e:
            logger.debug("Cost tracking failed for force-finalize: %s", e)

        return content

    # ------------------------------------------------------------------

    async def _guard_max_messages(self, event_log=None) -> None:
        try:
            while not self._done.is_set():
                await asyncio.sleep(5.0)
                if self._phase != "task_execution":
                    continue
                if self.message_store.total_count >= self.max_messages:
                    if event_log:
                        event_log.log("runner.guard", data={
                            "reason": "max_messages",
                            "count": self.message_store.total_count,
                            "limit": self.max_messages,
                        })
                    self._forced_termination = (
                        f"max_messages ({self.message_store.total_count} >= {self.max_messages})"
                    )
                    self._done.set()
                    break
        except asyncio.CancelledError:
            pass

    def _get_total_cost_usd(self) -> float:
        total = self._stopped_agents_cost
        for agent in self.agents.values():
            total += getattr(agent, "_total_cost_usd", 0.0)
        return total

    REFLECTION_MAX_COST_USD = 30.0

    async def _guard_cost_limit(self, event_log=None) -> None:
        try:
            reflection_cost_baseline: float | None = None

            while not self._done.is_set():
                await asyncio.sleep(10.0)
                total_cost = self._get_total_cost_usd()

                if self._phase == "task_execution":
                    if total_cost >= self.max_cost_usd:
                        if event_log:
                            event_log.log("runner.guard", data={
                                "reason": "cost_limit",
                                "total_cost_usd": round(total_cost, 4),
                                "limit_usd": self.max_cost_usd,
                            })
                        self._forced_termination = (
                            f"cost_limit (${total_cost:.2f} >= ${self.max_cost_usd:.2f})"
                        )
                        self._done.set()
                        break
                else:
                    if self.REFLECTION_MAX_COST_USD <= 0:
                        continue
                    if reflection_cost_baseline is None:
                        reflection_cost_baseline = total_cost
                    reflection_cost = total_cost - reflection_cost_baseline
                    if reflection_cost >= self.REFLECTION_MAX_COST_USD:
                        if event_log:
                            event_log.log("runner.guard", data={
                                "reason": "reflection_cost_limit",
                                "reflection_cost_usd": round(reflection_cost, 4),
                                "limit_usd": self.REFLECTION_MAX_COST_USD,
                                "total_cost_usd": round(total_cost, 4),
                            })
                        self.terminate(
                            reason=f"reflection_cost_limit_${reflection_cost:.2f}"
                                   f">=${self.REFLECTION_MAX_COST_USD:.2f}"
                        )
                        break
        except asyncio.CancelledError:
            pass
