# ADR 0002: 5-Tier Tool Risk Taxonomy and Deny-by-Default

## Status
Accepted

## Context
AI agents equipped with computer control capabilities present substantial risks of accidental data destruction, secret exposure, or host compromise. A binary permit/deny model is insufficient for granular human-in-the-loop workflows.

## Decision
We implemented a formal 5-tier risk taxonomy:
- `READ_ONLY`: Zero state mutation.
- `LOW`: Minimal, non-destructive external interactions.
- `MEDIUM`: Reversible file modifications within workspace root.
- `HIGH`: Irreversible operations, external data transfer.
- `CRITICAL`: Shell execution, process launching, host admin operations.

Phase 01 strictly restricts available tools to `READ_ONLY`, denying `CRITICAL` shell tools and confining all filesystem operations to `workspace_root`.

## Consequences
- Guarantees zero destructive actions during bootstrap and testing.
- Allows progressive escalation in later phases under explicit human approval.
