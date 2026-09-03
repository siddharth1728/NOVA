# Contributing to NOVA

We welcome contributions that adhere to NOVA's core principles: **reliability, security-first, observable, testable, and local-first**.

---

## 1. Development Guidelines

1. **Safety Invariant**: Never add a capability that bypasses the `PermissionEngine` or `ToolRegistry`.
2. **Epistemic Discipline**: NOVA code and agents must distinguish observed facts from inferences. Never fake functionality or simulate success when a tool execution fails.
3. **Type Hints**: All Python functions and methods must include explicit type annotations.
4. **Secret Protection**: Never commit credentials, tokens, or API keys. Ensure new logs pass through `redact_sensitive_data()`.
5. **Platform Support**: NOVA runs on Windows, macOS, and Linux. Always use `pathlib.Path` and handle case-insensitivity appropriately for Windows.

---

## 2. Environment Setup

```powershell
# Clone and enter workspace
cd c:\KaryaSetu

# Create virtual environment with uv
uv venv .venv

# Install package in editable mode with development dependencies
uv pip install -e ".[dev]"
```

---

## 3. Testing Standards

Every feature or bugfix must be accompanied by automated unit or integration tests in `tests/`:

```powershell
# Run the complete test suite
.venv\Scripts\pytest -v tests/
```

Test requirements:
- Unit tests must be fast and deterministic.
- External API boundaries (such as Gemini model calls) must be mocked in unit tests.
- Negative security tests must prove that out-of-boundary paths or unauthorized tools fail closed.

---

## 4. Conventional Commits

Commit messages must follow the Conventional Commits specification:
- `feat:` New features or capabilities.
- `fix:` Bug fixes or security repairs.
- `test:` Adding or updating test suites.
- `docs:` Documentation improvements.
- `chore:` Build scripts, packaging, or workspace hygiene.
