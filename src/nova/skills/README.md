# NOVA Skills Architecture

Skills in NOVA follow the Google Antigravity skill specification:
- Each skill is encapsulated in a dedicated directory containing a `SKILL.md` file.
- The `SKILL.md` file must begin with YAML frontmatter specifying `name` and `description`.
- Skills provide contextual procedural knowledge, tool constraints, and workflows that the agent discovers dynamically.

## Skill Directory Layout

```
skills/
├── workspace-explorer/
│   ├── SKILL.md
│   └── (optional scripts/ or references/)
```

## Discovery

Skills directories are passed directly to Antigravity's `LocalAgentConfig(skills_paths=[...])`, allowing the harness to index and offer relevant skills to the agent runtime.
