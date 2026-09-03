---
name: workspace-explorer
description: Systematic procedure for inspecting, mapping, and analyzing workspace directories and project files safely.
---

# Workspace Explorer Skill

This skill guides NOVA when the user asks to inspect, understand, or audit a project workspace.

## Execution Discipline

1. **Root Discovery First**:
   - Begin by listing the root directory via `list_directory`.
   - Identify project manifest files (e.g. `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`).
   - Identify top-level documentation (`README.md`, `ARCHITECTURE.md`).

2. **Hierarchical Inspection**:
   - Examine primary source directories (`src/`, `lib/`, `app/`).
   - Read manifests or configuration to determine technologies, dependencies, and entrypoints.
   - Use `find_file` to locate specific configurations or modules when targeting a sub-problem.

3. **Epistemic Labeling**:
   - [OBSERVED]: File exists, directory listed, content read.
   - [INFERRED]: Project uses Python based on `pyproject.toml`.
   - [ASSUMED]: Framework version prior to inspecting package lock.
   - [VERIFIED]: Module confirmed importable via runtime verification.

4. **Safety Constraints**:
   - Never attempt to modify or delete files while exploring.
   - Do not inspect files outside the configured workspace root.
