# ADR 0005: Plan Integrity and Runtime Drift Prevention

## Context
When an autonomous agent generates a multi-step plan that receives user authorization, the runtime must guarantee that the steps actually executed correspond strictly to what was approved. If an LLM or subagent hallucinates or dynamically injects unapproved parameters or out-of-scope tools, user trust is violated.

## Decision
1. **Cryptographic Plan Hashing**: Every plan envelope is serialized canonically (canonical step ordering, tool, arguments, targets, dependencies, risk levels, and expected postconditions) and hashed using SHA-256.
2. **Approval Binding**: When authorization is granted (interactively or via policy), the approval record binds directly to the specific `plan_hash`.
3. **Runtime Drift Detection**: The `PlanExecutor` recomputes the plan hash before opening a transaction. Any mutation of arguments or step targets raises `PlanDriftError` and aborts immediately.
4. **Pre-Step Validation**: Before each individual step is invoked, the executor checks that tool name, target path, argument mapping, and risk level are within the declared plan bounds.

## Status
Accepted and Implemented.
