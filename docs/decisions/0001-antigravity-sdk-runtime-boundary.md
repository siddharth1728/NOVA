# ADR 0001: Decoupling NOVA Product Runtime from Antigravity SDK

## Status
Accepted

## Context
NOVA is built on the Google Antigravity ecosystem. The installed SDK (`google-antigravity` v0.1.16) provides an asynchronous `Agent` runtime communicating with a Go binary (`localharness.exe`) over local WebSockets. We needed an architectural boundary between NOVA's domain logic (prompts, permissions, verification, memory, CLI) and Antigravity's internal protocols.

## Decision
We created an abstraction layer (`NovaRuntime`, `build_agent_config`, `AuditPostToolCallHook`) encapsulating the Antigravity `Agent` and `LocalAgentConfig`. The product layer interacts strictly through `NovaRuntime.query()`, while configuration builder and hooks map Antigravity primitives to NOVA's security and telemetry models.

## Consequences
- The rest of the codebase has no coupling to the Go binary or WebSocket protocols.
- Upgrading or adapting the underlying Antigravity SDK version requires changes only in the runtime configuration adapter.
- Automated tests can easily mock the Agent boundary without spinning up external processes.
