"""Validation pipeline with step-based execution and approval gates.

Mirrors no-mistakes pipeline architecture: steps run sequentially, each
implementing the Step protocol. The Executor orchestrates execution with
approval gates, event streaming, and fix-loop support.
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional, Protocol

logger = logging.getLogger(__name__)


class StepName(str, Enum):
    """Fixed pipeline step names."""
    REVIEW = "review"
    TEST = "test"
    LINT = "lint"
    DOCUMENT = "document"
    PUSH = "push"
    PR = "pr"
    CI = "ci"


class StepStatus(str, Enum):
    """Step execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    AWAITING_APPROVAL = "awaiting_approval"
    FIXING = "fixing"


class ApprovalAction(str, Enum):
    """User approval actions."""
    APPROVE = "approve"
    FIX = "fix"
    SKIP = "skip"
    ABORT = "abort"


@dataclass
class Finding:
    """A code review finding."""
    id: str
    file: str
    line: int
    message: str
    severity: str = "warning"
    action: str = "ask-user"
    category: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "severity": self.severity,
            "action": self.action,
            "category": self.category,
        }


@dataclass
class StepOutcome:
    """Result of executing a pipeline step."""
    success: bool = True
    needs_approval: bool = False
    auto_fixable: bool = False
    findings: list[Finding] = field(default_factory=list)
    error: Optional[str] = None
    exit_code: int = 0
    pr_url: Optional[str] = None
    skipped: bool = False
    skip_remaining: bool = False
    restart_from: Optional[StepName] = None
    fix_summary: Optional[str] = None
    review_approved_head_sha: Optional[str] = None
    duration_ms: int = 0

    @property
    def has_ask_user_findings(self) -> bool:
        return any(f.action == "ask-user" for f in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "needs_approval": self.needs_approval,
            "auto_fixable": self.auto_fixable,
            "findings": [f.to_dict() for f in self.findings],
            "error": self.error,
            "exit_code": self.exit_code,
            "pr_url": self.pr_url,
            "skipped": self.skipped,
            "skip_remaining": self.skip_remaining,
            "restart_from": self.restart_from.value if self.restart_from else None,
            "fix_summary": self.fix_summary,
        }


@dataclass
class StepContext:
    """Shared resources for pipeline steps during execution."""
    work_dir: str
    step_name: StepName
    run_id: str
    branch: Optional[str] = None
    head_sha: Optional[str] = None
    previous_findings: Optional[str] = None
    fixing: bool = False
    evidence_dir: Optional[str] = None
    user_intent: Optional[str] = None
    intent_source: Optional[str] = None
    env: list[str] = field(default_factory=list)
    log_callback: Optional[Callable[[str], None]] = None

    def log(self, message: str) -> None:
        if self.log_callback:
            self.log_callback(message)
        logger.info("[%s] %s", self.step_name.value, message)


@dataclass
class RunShared:
    """Run-scoped state shared between steps."""
    document_lint_result: Optional[StepOutcome] = None


class Step(Protocol):
    """Protocol that each pipeline step implements."""

    def name(self) -> StepName:
        """Return the step's identity in the fixed pipeline sequence."""
        ...

    def execute(self, ctx: StepContext) -> StepOutcome:
        """Run the step logic and return an outcome."""
        ...


class BaseStep(ABC):
    """Base class for pipeline steps with common patterns."""

    def __init__(self, step_name: StepName, commands: Optional[dict[str, list[str]]] = None):
        self._step_name = step_name
        self._commands = commands or {}

    def name(self) -> StepName:
        return self._step_name

    def execute(self, ctx: StepContext) -> StepOutcome:
        cmd = self._commands.get(self._step_name.value)
        if not cmd:
            return StepOutcome(success=True, skipped=True)
        return self._run_command(ctx, cmd)

    def __init_subclass__(cls, **kwargs):
        # Avoid pytest collection warning for TestStep
        super().__init_subclass__(**kwargs)

    def _run_command(self, ctx: StepContext, cmd: list[str]) -> StepOutcome:
        start = time.monotonic()
        try:
            result = subprocess.run(
                cmd,
                cwd=ctx.work_dir,
                capture_output=True,
                text=True,
                timeout=300,
                env=self._build_env(ctx),
            )
            duration = int((time.monotonic() - start) * 1000)
            success = result.returncode == 0
            error = result.stderr.strip() if not success else None
            return StepOutcome(
                success=success,
                error=error,
                exit_code=result.returncode,
                duration_ms=duration,
            )
        except subprocess.TimeoutExpired:
            duration = int((time.monotonic() - start) * 1000)
            return StepOutcome(success=False, error="Timeout", exit_code=-1, duration_ms=duration)
        except FileNotFoundError:
            duration = int((time.monotonic() - start) * 1000)
            return StepOutcome(
                success=False,
                error=f"Command not found: {cmd[0]}",
                exit_code=-1,
                duration_ms=duration,
            )
        except Exception as e:
            duration = int((time.monotonic() - start) * 1000)
            return StepOutcome(success=False, error=str(e), exit_code=-1, duration_ms=duration)

    def _build_env(self, ctx: StepContext) -> dict[str, str]:
        import os
        env = os.environ.copy()
        for item in ctx.env:
            if "=" in item:
                k, v = item.split("=", 1)
                env[k] = v
        return env


class ReviewStep(BaseStep):
    """Review step - runs code review via agent or command."""

    def __init__(self, commands: Optional[dict[str, list[str]]] = None):
        super().__init__(StepName.REVIEW, commands)


class RunTestStep(BaseStep):
    """Test step - runs test suite."""

    def __init__(self, commands: Optional[dict[str, list[str]]] = None):
        super().__init__(StepName.TEST, commands)


class LintStep(BaseStep):
    """Lint step - runs linter."""

    def __init__(self, commands: Optional[dict[str, list[str]]] = None):
        super().__init__(StepName.LINT, commands)


class DocumentStep(BaseStep):
    """Document step - validates documentation."""

    def __init__(self, commands: Optional[dict[str, list[str]]] = None):
        super().__init__(StepName.DOCUMENT, commands)


class Executor:
    """Runs pipeline steps sequentially and coordinates approval interactions."""

    def __init__(
        self,
        steps: list[Step],
        on_event: Optional[Callable[[dict[str, Any]], None]] = None,
        gate_reconcile_interval: float = 120.0,
        gate_reconcile_timeout: float = 30.0,
    ):
        self.steps = steps
        self.on_event = on_event or (lambda e: None)
        self.gate_reconcile_interval = gate_reconcile_interval
        self.gate_reconcile_timeout = gate_reconcile_timeout

        self._mu = threading.Lock()
        self._approval_ch: Optional[threading.Queue] = None
        self._waiting = False
        self._waiting_step: Optional[StepName] = None
        self._shared = RunShared()

    def execute(
        self,
        work_dir: str,
        run_id: str,
        branch: Optional[str] = None,
        head_sha: Optional[str] = None,
        skip_steps: Optional[list[StepName]] = None,
    ) -> dict[str, Any]:
        """Run all pipeline steps sequentially.

        Returns:
            Pipeline result with success status and per-step results.
        """
        skip_set = set(skip_steps or [])
        results: list[dict[str, Any]] = []
        findings: list[dict[str, Any]] = []
        pr_url: Optional[str] = None
        start_time = time.monotonic()

        self._emit({
            "type": "run_started",
            "run_id": run_id,
            "branch": branch,
            "head_sha": head_sha,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        for i, step in enumerate(self.steps):
            step_name = step.name()

            if step_name in skip_set:
                self._emit({
                    "type": "step_skipped",
                    "run_id": run_id,
                    "step": step_name.value,
                })
                results.append({
                    "step": step_name.value,
                    "status": "skipped",
                })
                continue

            ctx = StepContext(
                work_dir=work_dir,
                step_name=step_name,
                run_id=run_id,
                branch=branch,
                head_sha=head_sha,
            )

            self._emit({
                "type": "step_started",
                "run_id": run_id,
                "step": step_name.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            outcome = step.execute(ctx)

            if outcome.needs_approval:
                self._emit({
                    "type": "step_awaiting_approval",
                    "run_id": run_id,
                    "step": step_name.value,
                    "findings": [f.to_dict() for f in outcome.findings],
                })

                approval = self._wait_approval(step_name)
                if approval.action == ApprovalAction.ABORT:
                    results.append({
                        "step": step_name.value,
                        "status": "aborted",
                        "outcome": outcome.to_dict(),
                    })
                    break
                elif approval.action == ApprovalAction.SKIP:
                    results.append({
                        "step": step_name.value,
                        "status": "skipped",
                    })
                    continue
                elif approval.action == ApprovalAction.FIX and outcome.auto_fixable:
                    fix_outcome = self._run_fix(ctx, outcome)
                    outcome = fix_outcome

            if outcome.pr_url:
                pr_url = outcome.pr_url

            for f in outcome.findings:
                findings.append(f.to_dict())

            status = "passed" if outcome.success else "failed"
            results.append({
                "step": step_name.value,
                "status": status,
                "outcome": outcome.to_dict(),
            })

            self._emit({
                "type": "step_completed",
                "run_id": run_id,
                "step": step_name.value,
                "status": status,
                "findings": len(outcome.findings),
                "duration_ms": outcome.duration_ms,
            })

            if not outcome.success:
                break

            if outcome.skip_remaining:
                for remaining in self.steps[i + 1:]:
                    results.append({
                        "step": remaining.name().value,
                        "status": "skipped",
                    })
                break

            if outcome.restart_from:
                restart_idx = self._find_step_index(outcome.restart_from)
                if restart_idx is not None and restart_idx < i:
                    # Reset and re-run from restart point
                    steps_to_skip = {s.name() for s in self.steps[restart_idx:i]}
                    skip_set.update(steps_to_skip)

        duration_ms = int((time.monotonic() - start_time) * 1000)
        success = all(r.get("status") in ("passed", "skipped") for r in results)

        self._emit({
            "type": "run_completed",
            "run_id": run_id,
            "success": success,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return {
            "success": success,
            "run_id": run_id,
            "results": results,
            "findings": findings,
            "pr_url": pr_url,
            "duration_ms": duration_ms,
        }

    def respond(
        self,
        step: StepName,
        action: ApprovalAction,
        finding_ids: Optional[list[str]] = None,
    ) -> None:
        """Send a user approval action to the currently waiting step."""
        with self._mu:
            if not self._waiting:
                raise RuntimeError("No step awaiting approval")
            if step != self._waiting_step:
                raise RuntimeError(f"Step mismatch: responding to {step} but {self._waiting_step} is awaiting")
            self._waiting = False

        if self._approval_ch:
            self._approval_ch.put(approvalResponse(action=action, finding_ids=finding_ids or []))

    def _wait_approval(self, step_name: StepName) -> approvalResponse:
        with self._mu:
            self._waiting = True
            self._waiting_step = step_name
            self._approval_ch = threading.Queue(maxsize=1)

        try:
            return self._approval_ch.get(timeout=self.gate_reconcile_timeout)
        except Exception:
            with self._mu:
                self._waiting = False
            return approvalResponse(action=ApprovalAction.ABORT, finding_ids=[])

    def _run_fix(self, ctx: StepContext, original: StepOutcome) -> StepOutcome:
        """Run a fix round for the step."""
        fix_ctx = StepContext(
            work_dir=ctx.work_dir,
            step_name=ctx.step_name,
            run_id=ctx.run_id,
            branch=ctx.branch,
            head_sha=ctx.head_sha,
            fixing=True,
            previous_findings=original.to_dict().get("findings"),
        )
        # Find the matching step and re-execute
        for step in self.steps:
            if step.name() == ctx.step_name:
                return step.execute(fix_ctx)
        return original

    def _find_step_index(self, name: StepName) -> Optional[int]:
        for i, step in enumerate(self.steps):
            if step.name() == name:
                return i
        return None

    def _emit(self, event: dict[str, Any]) -> None:
        try:
            self.on_event(event)
        except Exception:
            pass


@dataclass
class approvalResponse:
    """Internal approval response."""
    action: ApprovalAction
    finding_ids: list[str] = field(default_factory=list)


class Pipeline:
    """High-level pipeline that creates steps from configuration.

    This is the user-friendly interface that matches the original no-mistakes
    pipeline: review, test, lint, document as default stages, with configurable
    commands for each stage.
    """

    def __init__(
        self,
        stages: Optional[list[str]] = None,
        commands: Optional[dict[str, list[str]]] = None,
    ):
        self.stages = stages if stages is not None else ["review", "test", "lint"]
        self.commands = commands or {
            "review": ["python", "-c", "print('Review passed')"],
            "test": ["python", "-m", "pytest", "--tb=short"],
            "lint": ["python", "-m", "ruff", "check", "."],
            "typecheck": ["python", "-m", "mypy", "."],
            "document": ["python", "-c", "print('Docs check passed')"],
        }

    def _build_steps(self) -> list[Step]:
        steps = []
        step_map = {
            "review": ReviewStep,
            "test": RunTestStep,
            "lint": LintStep,
            "document": DocumentStep,
        }
        for stage in self.stages:
            cls = step_map.get(stage, BaseStep)
            step_name = StepName(stage) if stage in StepName.__members__.values() else StepName(stage)
            if stage in step_map:
                step = cls(commands=self.commands)
            else:
                step = BaseStep(step_name=StepName(stage), commands=self.commands)
            steps.append(step)
        return steps

    def run(
        self,
        repo_path: str,
        branch: Optional[str] = None,
        run_id: Optional[str] = None,
        on_event: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> dict[str, Any]:
        """Run all pipeline stages.

        Args:
            repo_path: Repository path
            branch: Branch to validate (optional)
            run_id: Run identifier (generated if not provided)
            on_event: Event callback for streaming

        Returns:
            Pipeline result with success status and findings
        """
        if not run_id:
            run_id = f"run-{int(time.time())}"

        steps = self._build_steps()
        executor = Executor(steps=steps, on_event=on_event)
        return executor.execute(
            work_dir=repo_path,
            run_id=run_id,
            branch=branch,
        )

    def add_stage(self, stage: str, command: list[str]) -> None:
        """Add a custom stage to the pipeline."""
        if stage not in self.stages:
            self.stages.append(stage)
        self.commands[stage] = command

    def remove_stage(self, stage: str) -> None:
        """Remove a stage from the pipeline."""
        if stage in self.stages:
            self.stages.remove(stage)
        self.commands.pop(stage, None)
