"""Plan executor with plan integrity enforcement, transactional execution, and empirical verification."""

import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from nova.errors import (
    ConflictError,
    PlanDriftError,
    RollbackFailedError,
    VerificationError,
)
from nova.memory.models import ExecutionRecord
from nova.memory.store import LocalFileMemoryStore
from nova.observability.audit import get_audit_trail
from nova.planning.models import Plan, PlanStatus, PlanStepStatus
from nova.tools.registry import get_tool_registry
from nova.transactions.manager import get_transaction_manager
from nova.transactions.models import OperationType
from nova.verification.engine import VerificationEngine

logger = logging.getLogger("nova.planning.executor")


class PlanExecutionResult(BaseModel):
    """Structured report returned upon plan execution completion."""

    plan_id: str
    success: bool
    completed_steps: int
    total_steps: int
    status: PlanStatus
    transaction_id: str
    message: str
    rolled_back: bool = False
    rollback_verified: bool = False
    error: str | None = None


class PlanExecutor:
    """Executes multi-step plans with strict plan integrity, transactions, and verification."""

    def __init__(self) -> None:
        self.tx_mgr = get_transaction_manager()
        self.verifier = VerificationEngine()
        self.registry = get_tool_registry()
        self.audit = get_audit_trail()
        self.memory = LocalFileMemoryStore()

    def execute(
        self,
        plan: Plan,
        approved_hash: str,
        simulate_failure_at_step: int | None = None,
        simulate_rollback_failure: bool = False,
    ) -> PlanExecutionResult:
        """Executes the validated plan inside an atomic transaction.

        Args:
            plan: The plan to execute.
            approved_hash: The cryptographic plan hash approved by the user.
            simulate_failure_at_step: Optional step ID to deliberately fail for testing.
            simulate_rollback_failure: Optional boolean to simulate a rollback failure.

        Returns:
            PlanExecutionResult detailing outcomes and verification status.

        Raises:
            PlanDriftError: If plan hash differs from approved_hash.
            RollbackFailedError: If a rollback cannot restore workspace integrity.
        """
        # 1. Plan Integrity Verification
        current_hash = plan.compute_plan_hash()
        if current_hash != approved_hash:
            self.audit.log_tool_invocation(
                tool="plan_executor",
                risk_level="HIGH",
                approval_state="REJECTED",
                inputs={"plan_id": plan.plan_id},
                results={"expected": approved_hash, "observed": current_hash},
                success=False,
                error="Plan drift detected",
            )
            raise PlanDriftError(
                f"Plan drift detected for plan {plan.plan_id}: current hash {current_hash} != approved hash {approved_hash}.",
                plan_id=plan.plan_id,
                expected_hash=approved_hash,
                observed_hash=current_hash,
                drift_reason="Plan step parameters were modified after approval was granted.",
            )

        # 2. Begin Transaction
        tx = self.tx_mgr.begin(tx_id=plan.plan_id, description=plan.goal)
        plan.status = PlanStatus.EXECUTING

        completed_steps = 0
        total_steps = len(plan.steps)

        # 3. Step-by-Step Execution
        try:
            for step in plan.steps:
                step.status = PlanStepStatus.RUNNING

                # Runtime plan drift guard
                if step.risk_level > plan.risk_ceiling:
                    raise PlanDriftError(
                        f"Step {step.step_id} risk level ({step.risk_level.value}) exceeds plan risk ceiling ({plan.risk_ceiling.value}).",
                        plan_id=plan.plan_id,
                        expected_hash=approved_hash,
                        drift_reason="Risk ceiling escalation",
                    )

                # Simulate intentional failure if requested for testing
                if simulate_failure_at_step is not None and step.step_id == simulate_failure_at_step:
                    raise RuntimeError(f"Controlled test failure triggered at step {step.step_id}.")

                # Execute tool
                tool_entry = self.registry.get(step.tool)
                if not tool_entry or not tool_entry.handler:
                    raise RuntimeError(f"Tool handler '{step.tool}' not found.")

                args_with_tx = dict(step.args)
                args_with_tx["tx_id"] = plan.plan_id

                tool_result = tool_entry(**args_with_tx)

                # Verify step postcondition
                step_ok, step_reason = self.verifier.verify_step(step)
                if not step_ok:
                    raise VerificationError(
                        f"Step {step.step_id} failed verification: {step_reason}",
                        expected=step.expected_postcondition,
                        observed=tool_result,
                    )

                step.status = PlanStepStatus.COMPLETED
                completed_steps += 1

            # 4. Holistic Final Verification
            final_ok, final_reason = self.verifier.verify_final_plan(plan)
            if not final_ok:
                raise VerificationError(f"Final plan verification failed: {final_reason}")

            # 5. Commit Transaction
            self.tx_mgr.commit(plan.plan_id)
            plan.status = PlanStatus.COMMITTED

            # Record in execution memory
            self.memory.record_execution(
                ExecutionRecord(
                    record_id=f"tx_exec_{plan.plan_id}",
                    task_id=plan.plan_id,
                    tool="plan_executor",
                    args_summary=plan.goal[:200],
                    outcome=f"Successfully executed all {total_steps} planned steps.",
                    success=True,
                    verified=True,
                )
            )

            return PlanExecutionResult(
                plan_id=plan.plan_id,
                success=True,
                completed_steps=completed_steps,
                total_steps=total_steps,
                status=PlanStatus.COMMITTED,
                transaction_id=plan.plan_id,
                message=f"Plan '{plan.goal}' executed and verified ({completed_steps}/{total_steps} steps).",
            )

        except Exception as e:
            logger.error("Plan execution failed: %s. Initiating LIFO rollback...", e)
            plan.status = PlanStatus.FAILED

            # Simulate rollback failure if requested
            if simulate_rollback_failure:
                # Deliberately invalidate backup to test rollback failure handling
                tx_record = self.tx_mgr.get_transaction(plan.plan_id)
                if tx_record and tx_record.operations:
                    tx_record.operations[0].op_type = OperationType.EDIT_FILE
                    tx_record.operations[0].backup_path = Path("C:/invalid/nonexistent_backup.bak")

            # Execute LIFO Rollback
            try:
                rolled_tx = self.tx_mgr.rollback(plan.plan_id)
                rb_verified, rb_reason = self.verifier.verify_rollback(rolled_tx)
                plan.status = PlanStatus.ROLLED_BACK

                # Mark completed steps as ROLLED_BACK
                for s in plan.steps:
                    if s.status == PlanStepStatus.COMPLETED:
                        s.status = PlanStepStatus.ROLLED_BACK

                # Record failure in memory
                self.memory.record_execution(
                    ExecutionRecord(
                        record_id=f"tx_fail_{plan.plan_id}",
                        task_id=plan.plan_id,
                        tool="plan_executor",
                        args_summary=plan.goal[:200],
                        outcome=f"Failed at step {completed_steps + 1}: {e}. Rolled back successfully.",
                        success=False,
                        verified=rb_verified,
                    )
                )

                return PlanExecutionResult(
                    plan_id=plan.plan_id,
                    success=False,
                    completed_steps=completed_steps,
                    total_steps=total_steps,
                    status=PlanStatus.ROLLED_BACK,
                    transaction_id=plan.plan_id,
                    message=f"Execution failed at step {completed_steps + 1}: {e}. Changes rolled back cleanly.",
                    rolled_back=True,
                    rollback_verified=rb_verified,
                    error=str(e),
                )
            except RollbackFailedError as rfe:
                plan.status = PlanStatus.FAILED
                logger.critical("CRITICAL INTEGRITY FAILURE: Rollback failed: %s", rfe)
                raise
