"""Empirical verification engine performing direct filesystem postcondition assertions."""

from pathlib import Path
from typing import Any

from nova.planning.models import Plan, PlanStep
from nova.transactions.manager import compute_file_hash
from nova.transactions.models import OperationType, TransactionRecord


class VerificationEngine:
    """Performs empirical verification by inspecting real filesystem state."""

    def verify_step(self, step: PlanStep) -> tuple[bool, str]:
        """Validates that the postconditions of an individual step are satisfied on disk.

        Args:
            step: The completed plan step.

        Returns:
            Tuple of (is_verified, explanation_string).
        """
        target = Path(step.target)
        post = step.expected_postcondition

        if post.get("exists") is True:
            if not target.exists():
                return False, f"Expected target '{target}' to exist, but it was not found."

            expected_type = post.get("type")
            if expected_type == "file" and not target.is_file():
                return False, f"Expected target '{target}' to be a regular file, but found a directory."
            elif expected_type == "dir" and not target.is_dir():
                return False, f"Expected target '{target}' to be a directory, but found a file."

            expected_hash = post.get("hash")
            if expected_hash:
                actual_hash = compute_file_hash(target)
                if actual_hash != expected_hash:
                    return False, f"File '{target}' hash mismatch: expected {expected_hash}, observed {actual_hash}."

        elif post.get("exists") is False:
            if target.exists():
                return False, f"Expected target '{target}' to be absent, but it still exists."

        # Verify source absence for move / rename operations
        if post.get("source_absent"):
            source_path = Path(post["source_absent"])
            if source_path.exists():
                return False, f"Source path '{source_path}' still exists after move/rename."

        return True, f"Step {step.step_id} ({step.description}) postconditions empirically verified."

    def verify_final_plan(self, plan: Plan) -> tuple[bool, str]:
        """Evaluates the holistic final state of the workspace after all steps have completed."""
        for step in plan.steps:
            valid, reason = self.verify_step(step)
            if not valid:
                return False, f"Final verification failed on step {step.step_id}: {reason}"

        return True, f"All {len(plan.steps)} planned operations verified successfully."

    def verify_rollback(self, tx: TransactionRecord) -> tuple[bool, str]:
        """Verifies that all reversed operations accurately returned the workspace to its prior state."""
        for op in tx.operations:
            if not op.rolled_back:
                continue

            target = op.target_path
            if op.op_type == OperationType.CREATE_FILE:
                if op.created_new and target.exists():
                    return False, f"Rollback failed: newly created file '{target}' still exists."

            elif op.op_type == OperationType.CREATE_DIRECTORY:
                if op.created_new and target.exists():
                    return False, f"Rollback failed: newly created directory '{target}' still exists."

            elif op.op_type == OperationType.EDIT_FILE:
                current_hash = compute_file_hash(target)
                if op.pre_hash and current_hash != op.pre_hash:
                    return False, f"Rollback failed: restored file '{target}' hash {current_hash} != pre-hash {op.pre_hash}."

            elif op.op_type in (OperationType.RENAME_FILE, OperationType.MOVE_FILE):
                if target.exists():
                    return False, f"Rollback failed: destination '{target}' still exists after reverse move."
                if op.secondary_path and not op.secondary_path.exists():
                    return False, f"Rollback failed: original file '{op.secondary_path}' was not restored."

            elif op.op_type == OperationType.COPY_FILE:
                if op.created_new and target.exists():
                    return False, f"Rollback failed: copied file '{target}' still exists."

        return True, "Rollback verified: workspace cleanly restored to pre-transaction state."
