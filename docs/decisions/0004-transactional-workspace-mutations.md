# ADR 0004: Transactional Workspace Mutations and LIFO Rollback

## Context
Phase 01 operated primarily in read-only mode to prevent accidental damage. Phase 02 requires turning NOVA into a controlled workspace operator capable of file and directory creation, editing, renaming, moving, and copying. Without transactional rollback guarantees, partial execution failures (e.g. failing on step 4 of 6) would leave the user's workspace in a corrupt, half-configured state.

## Decision
1. **LIFO Rollback Engine**: Mutations are performed within discrete transactions identified by unique IDs. Reversal follows strict Last-In-First-Out (LIFO) order.
2. **Precondition Hashing**: Before modifying an existing file, its SHA-256 digest is recorded. Edits verify that the current hash matches the expected pre-hash. Stale files modified since planning raise `FILE_CHANGED_SINCE_PLAN` and abort.
3. **Atomic Writes**: All file mutations write to temporary sibling files before calling `os.replace`, guaranteeing atomicity on Windows NTFS and POSIX file systems.
4. **Snapshot Storage**: Original contents are snapshotted in `.nova/backups/<tx_id>/` before modification.
5. **Critical Failure Reporting**: If execution fails and rollback itself encounters an unrecoverable filesystem error, NOVA reports `ROLLBACK_FAILED` and raises `RollbackFailedError` rather than falsely claiming clean restoration.

## Status
Accepted and Implemented.
