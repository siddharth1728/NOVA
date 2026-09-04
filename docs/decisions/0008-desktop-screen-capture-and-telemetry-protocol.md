# ADR 0008: Desktop Screen Capture & Telemetry Protocol

## Status
Accepted (Phase 03)

## Context
A remote controller must provide visual context into what is happening on the user's computer screen and how system resources are performing.
Desktop capture on Windows faces unique runtime challenges:
1. When running interactively, GDI / Pillow capture succeeds directly.
2. When the workstation is running in a service session, headless terminal, or locked secure desktop, direct BitBlt calls fail at the OS level (`win32ui.error: BitBlt failed` or `OSError: screen grab failed`).
A robust solution must gracefully capture desktop pixels when interactive, and supply an informative diagnostic frame when display sessions are detached, without crashing host services.

## Decision
1. **Adaptive Desktop Screen Capture**:
   - Primary: `PIL.ImageGrab.grab(all_screens=True)`.
   - Secondary: Win32 GDI `BitBlt` capture via `win32gui`/`win32ui`.
   - Fallback: High-fidelity diagnostic frame generated in-memory with live host resolution, timestamp, hostname, and active status indicators if display session is detached.
2. **Flexible Compression & Downscaling**:
   Screen captures support optional `max_width`, `max_height`, and JPEG/PNG format specification to optimize bandwidth across local Wi-Fi or cellular connections.
3. **Pydantic Hardware Telemetry**:
   Real-time telemetry (`psutil`) captures CPU %, RAM %, Disk %, uptime, and OS version, streamed over both REST (`GET /api/v1/status`) and WebSockets (`/ws/v1/events`).

## Consequences
- **Positive**: Resilient under all Windows runtime conditions (interactive, headless, locked); bandwidth efficient; zero external video streaming daemon required for snapshot monitoring.
- **Negative**: High-frequency video streaming (e.g. 60 FPS H.264 video) is deferred to future phases (desktop snapshots provide 1-5 FPS monitoring).
