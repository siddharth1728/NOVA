# ADR 0003: Local-First Modular Memory Store

## Status
Accepted

## Context
NOVA requires long-term recall of user preferences, environment facts, execution history, and project domain context. Transmitting this state to third-party cloud databases compromises privacy and violates our local-first principle. Furthermore, premature adoption of heavyweight vector or graph databases adds unwarranted complexity to Phase 01.

## Decision
We established a clean `MemoryStore` ABC defining distinct domain records (`UserPreference`, `EnvironmentFact`, `TaskState`, `ExecutionRecord`, `LearnedWorkflow`, `ProjectContext`). The initial implementation (`LocalFileMemoryStore`) persists these entities as local, atomic JSON files inside the workstation's `.nova/memory/` directory.

## Consequences
- 100% of user memory remains on the local workstation.
- Clean interface permits drop-in replacement with SQLite, Chroma, or vector databases in future phases without altering agent code.
