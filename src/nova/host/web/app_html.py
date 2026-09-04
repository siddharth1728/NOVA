"""Mobile Web Control Center single-page application for NOVA Windows Host."""

WEB_APP_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="NOVA">
  <meta name="theme-color" content="#0B0E14">
  <title>NOVA — Mobile Control Center</title>
  <link rel="manifest" href="/manifest.json">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-primary: #080B10;
      --bg-secondary: #0F141C;
      --bg-card: rgba(18, 24, 35, 0.72);
      --bg-card-hover: rgba(26, 35, 51, 0.85);
      --border-subtle: rgba(255, 255, 255, 0.08);
      --border-accent: rgba(0, 240, 255, 0.3);
      --text-main: #F0F4F8;
      --text-muted: #8E9BAE;
      --cyan-glow: #00F0FF;
      --cyan-dim: rgba(0, 240, 255, 0.12);
      --emerald: #10B981;
      --emerald-dim: rgba(16, 185, 129, 0.15);
      --amber: #F59E0B;
      --amber-dim: rgba(245, 158, 11, 0.15);
      --crimson: #EF4444;
      --crimson-dim: rgba(239, 68, 68, 0.18);
      --purple: #8B5CF6;
      --safe-top: env(safe-area-inset-top, 16px);
      --safe-bottom: env(safe-area-inset-bottom, 20px);
      --font-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-tap-highlight-color: transparent;
      user-select: none;
    }

    body {
      background-color: var(--bg-primary);
      color: var(--text-main);
      font-family: var(--font-sans);
      min-height: 100vh;
      min-height: -webkit-fill-available;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
      background-image: 
        radial-gradient(circle at 15% 10%, rgba(0, 240, 255, 0.05) 0%, transparent 40%),
        radial-gradient(circle at 85% 90%, rgba(139, 92, 246, 0.05) 0%, transparent 40%);
    }

    /* Top Navigation Header */
    header {
      padding-top: calc(var(--safe-top) + 10px);
      padding-bottom: 12px;
      padding-left: 18px;
      padding-right: 18px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(8, 11, 16, 0.85);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-bottom: 1px solid var(--border-subtle);
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .logo-badge {
      width: 32px;
      height: 32px;
      border-radius: 9px;
      background: linear-gradient(135deg, #00F0FF, #8B5CF6);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 16px;
      color: #000;
      box-shadow: 0 0 15px rgba(0, 240, 255, 0.35);
    }

    .brand-text h1 {
      font-size: 16px;
      font-weight: 700;
      letter-spacing: 0.5px;
      color: #FFF;
    }

    .brand-text p {
      font-size: 10px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 1px;
    }

    .status-badge {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 5px 10px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 600;
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
    }

    .status-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--crimson);
      box-shadow: 0 0 8px var(--crimson);
      transition: background 0.3s, box-shadow 0.3s;
    }

    .status-dot.connected {
      background: var(--emerald);
      box-shadow: 0 0 8px var(--emerald);
    }

    .status-dot.reconnecting {
      background: var(--amber);
      box-shadow: 0 0 8px var(--amber);
      animation: pulse 1s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(1.2); }
    }

    /* Main Content Area */
    main {
      flex: 1;
      overflow-y: auto;
      padding: 16px 16px calc(var(--safe-bottom) + 80px) 16px;
    }

    .tab-content {
      display: none;
      animation: fadeIn 0.25s ease-out forwards;
    }

    .tab-content.active {
      display: block;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* Common Card Styles */
    .card {
      background: var(--bg-card);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid var(--border-subtle);
      border-radius: 18px;
      padding: 18px;
      margin-bottom: 14px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
    }

    .card-title {
      font-size: 13px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.8px;
      margin-bottom: 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    /* Telemetry Gauges Grid */
    .telemetry-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
      margin-bottom: 14px;
    }

    .metric-card {
      background: rgba(15, 20, 28, 0.7);
      border: 1px solid var(--border-subtle);
      border-radius: 14px;
      padding: 14px;
      position: relative;
      overflow: hidden;
    }

    .metric-label {
      font-size: 11px;
      color: var(--text-muted);
      font-weight: 600;
      margin-bottom: 6px;
    }

    .metric-value {
      font-size: 22px;
      font-weight: 800;
      color: #FFF;
      font-family: var(--font-mono);
    }

    .metric-sub {
      font-size: 10px;
      color: var(--text-muted);
      margin-top: 4px;
    }

    .metric-progress {
      height: 4px;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 2px;
      margin-top: 8px;
      overflow: hidden;
    }

    .metric-bar {
      height: 100%;
      background: var(--cyan-glow);
      border-radius: 2px;
      transition: width 0.4s ease;
    }

    /* Active Task Banner */
    .task-banner {
      background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(139, 92, 246, 0.15));
      border: 1px solid rgba(239, 68, 68, 0.35);
      border-radius: 16px;
      padding: 14px 16px;
      margin-bottom: 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 0 20px rgba(239, 68, 68, 0.15);
    }

    .task-info h3 {
      font-size: 13px;
      font-weight: 700;
      color: #FFF;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .task-info p {
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 2px;
      max-width: 200px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .btn-stop-task {
      background: #EF4444;
      color: #FFF;
      border: none;
      padding: 8px 14px;
      border-radius: 10px;
      font-weight: 700;
      font-size: 12px;
      letter-spacing: 0.5px;
      box-shadow: 0 0 12px rgba(239, 68, 68, 0.5);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 5px;
      transition: transform 0.1s, background 0.2s;
    }

    .btn-stop-task:active {
      transform: scale(0.95);
      background: #DC2626;
    }

    /* Quick Action Buttons */
    .action-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      margin-bottom: 14px;
    }

    .action-btn {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 14px;
      padding: 12px 8px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 8px;
      cursor: pointer;
      transition: background 0.2s, border-color 0.2s;
    }

    .action-btn:active {
      background: var(--bg-card-hover);
      border-color: var(--border-accent);
      transform: scale(0.96);
    }

    .action-icon {
      font-size: 20px;
    }

    .action-label {
      font-size: 11px;
      font-weight: 600;
      color: var(--text-main);
      text-align: center;
    }

    /* Chat / Agent Feed */
    .agent-feed {
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-bottom: 70px;
      min-height: 250px;
    }

    .msg {
      max-width: 88%;
      padding: 12px 16px;
      border-radius: 16px;
      font-size: 13px;
      line-height: 1.5;
      user-select: text;
    }

    .msg.user {
      align-self: flex-end;
      background: linear-gradient(135deg, #00C6FF, #0072FF);
      color: #FFF;
      border-bottom-right-radius: 4px;
      box-shadow: 0 4px 14px rgba(0, 114, 255, 0.25);
    }

    .msg.agent {
      align-self: flex-start;
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      color: var(--text-main);
      border-bottom-left-radius: 4px;
    }

    .msg.system {
      align-self: center;
      font-size: 11px;
      color: var(--text-muted);
      background: rgba(255, 255, 255, 0.04);
      padding: 6px 12px;
      border-radius: 12px;
      text-align: center;
      max-width: 95%;
    }

    .msg-meta {
      font-size: 9px;
      opacity: 0.6;
      margin-top: 4px;
      font-family: var(--font-mono);
    }

    /* Agent Floating Input Bar */
    .agent-input-container {
      position: fixed;
      bottom: calc(var(--safe-bottom) + 65px);
      left: 16px;
      right: 16px;
      display: flex;
      gap: 8px;
      z-index: 90;
    }

    .agent-input-wrapper {
      flex: 1;
      position: relative;
      background: rgba(18, 24, 35, 0.95);
      border: 1px solid var(--border-subtle);
      border-radius: 24px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
      display: flex;
      align-items: center;
      padding: 0 14px;
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
    }

    .agent-input-wrapper:focus-within {
      border-color: var(--cyan-glow);
      box-shadow: 0 0 15px rgba(0, 240, 255, 0.25);
    }

    .agent-input {
      width: 100%;
      background: transparent;
      border: none;
      outline: none;
      color: #FFF;
      font-size: 14px;
      font-family: var(--font-sans);
      padding: 12px 0;
      user-select: text;
    }

    .agent-input::placeholder {
      color: var(--text-muted);
    }

    .btn-send {
      width: 44px;
      height: 44px;
      border-radius: 50%;
      background: linear-gradient(135deg, #00F0FF, #0072FF);
      border: none;
      color: #000;
      font-weight: 800;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 4px 15px rgba(0, 240, 255, 0.35);
      flex-shrink: 0;
      transition: transform 0.1s;
    }

    .btn-send:active {
      transform: scale(0.92);
    }

    /* Screen Viewer Tab */
    .screen-wrapper {
      width: 100%;
      border-radius: 14px;
      overflow: hidden;
      border: 1px solid var(--border-subtle);
      background: #000;
      min-height: 200px;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
    }

    .screen-img {
      width: 100%;
      height: auto;
      display: block;
      object-fit: contain;
    }

    .screen-loading {
      color: var(--text-muted);
      font-size: 12px;
    }

    .screen-controls {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 10px;
    }

    .btn-screen-refresh {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      color: var(--cyan-glow);
      padding: 8px 14px;
      border-radius: 10px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .btn-screen-refresh:active {
      background: var(--bg-card-hover);
    }

    /* Activity Log Tab */
    .activity-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .activity-item {
      background: rgba(15, 20, 28, 0.6);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 10px 14px;
      font-family: var(--font-mono);
      font-size: 11px;
    }

    .activity-header {
      display: flex;
      justify-content: space-between;
      color: var(--text-muted);
      font-size: 10px;
      margin-bottom: 4px;
    }

    .activity-type {
      font-weight: 700;
      color: var(--cyan-glow);
    }

    .activity-payload {
      color: var(--text-main);
      word-break: break-all;
    }

    /* Pairing / Settings Form */
    .pair-form {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .input-label {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-muted);
      margin-bottom: 4px;
    }

    .pin-input {
      background: rgba(15, 20, 28, 0.8);
      border: 2px solid var(--border-accent);
      border-radius: 14px;
      color: #FFF;
      font-size: 28px;
      font-family: var(--font-mono);
      letter-spacing: 8px;
      text-align: center;
      padding: 14px;
      outline: none;
      user-select: text;
    }

    .pin-input:focus {
      border-color: var(--cyan-glow);
      box-shadow: 0 0 16px rgba(0, 240, 255, 0.3);
    }

    .pin-keypad {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin: 10px 0;
    }

    .keypad-btn {
      background: rgba(22, 27, 34, 0.9);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      color: #FFF;
      font-size: 20px;
      font-weight: 700;
      font-family: var(--font-mono);
      padding: 12px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.15s, transform 0.1s;
    }

    .keypad-btn:active {
      background: var(--cyan-dim);
      border-color: var(--cyan-glow);
      transform: scale(0.94);
    }

    .btn-primary {
      background: linear-gradient(135deg, #00F0FF, #0072FF);
      color: #000;
      border: none;
      border-radius: 14px;
      padding: 14px;
      font-weight: 700;
      font-size: 14px;
      cursor: pointer;
      box-shadow: 0 4px 18px rgba(0, 240, 255, 0.3);
      transition: transform 0.1s;
    }

    .btn-primary:active {
      transform: scale(0.97);
    }

    .btn-danger {
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.4);
      color: #EF4444;
      border-radius: 14px;
      padding: 12px;
      font-weight: 600;
      font-size: 13px;
      cursor: pointer;
    }

    .btn-danger:active {
      background: rgba(239, 68, 68, 0.3);
    }

    /* Fixed Bottom Tab Bar */
    nav.tab-bar {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      height: calc(var(--safe-bottom) + 56px);
      padding-bottom: var(--safe-bottom);
      background: rgba(8, 11, 16, 0.92);
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      border-top: 1px solid var(--border-subtle);
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      z-index: 100;
    }

    .tab-btn {
      background: none;
      border: none;
      color: var(--text-muted);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 4px;
      cursor: pointer;
      transition: color 0.2s;
    }

    .tab-btn.active {
      color: var(--cyan-glow);
    }

    .tab-icon {
      font-size: 18px;
    }

    .tab-label {
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.2px;
    }

    /* Toast Notifications */
    .toast {
      position: fixed;
      top: calc(var(--safe-top) + 60px);
      left: 50%;
      transform: translateX(-50%) translateY(-20px);
      background: rgba(18, 24, 35, 0.95);
      border: 1px solid var(--cyan-glow);
      color: #FFF;
      padding: 10px 18px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.3s, transform 0.3s;
      z-index: 1000;
    }

    .toast.show {
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }
  </style>
</head>
<body>

  <!-- Toast Notification -->
  <div id="toast" class="toast">Connected to Host</div>

  <!-- Header -->
  <header>
    <div class="brand">
      <div class="logo-badge">N</div>
      <div class="brand-text">
        <h1>NOVA</h1>
        <p>Windows Host Control</p>
      </div>
    </div>
    <div class="status-badge">
      <div id="statusDot" class="status-dot"></div>
      <span id="statusText">Offline</span>
    </div>
  </header>

  <!-- Main View Area -->
  <main>

    <!-- Tab 1: Dashboard (Home) -->
    <div id="tab-home" class="tab-content active">
      
      <!-- Active Task Banner (Dynamic) -->
      <div id="taskBanner" class="task-banner" style="display: none;">
        <div class="task-info">
          <h3><span style="display:inline-block;animation:pulse 1s infinite;">●</span> Active Agent Task</h3>
          <p id="bannerTaskPrompt">Processing remote query...</p>
        </div>
        <button id="btnBannerStop" class="btn-stop-task">
          <span>■</span> STOP TASK
        </button>
      </div>

      <!-- Quick Telemetry Grid -->
      <div class="telemetry-grid">
        <div class="metric-card">
          <div class="metric-label">CPU USAGE</div>
          <div class="metric-value" id="cpuVal">--%</div>
          <div class="metric-sub" id="cpuSub">Intel/AMD</div>
          <div class="metric-progress"><div class="metric-bar" id="cpuBar" style="width: 0%"></div></div>
        </div>
        <div class="metric-card">
          <div class="metric-label">MEMORY USAGE</div>
          <div class="metric-value" id="ramVal">--%</div>
          <div class="metric-sub" id="ramSub">-- / -- GB</div>
          <div class="metric-progress"><div class="metric-bar" id="ramBar" style="width: 0%; background: #8B5CF6;"></div></div>
        </div>
        <div class="metric-card">
          <div class="metric-label">DISK FREE</div>
          <div class="metric-value" id="diskVal">--%</div>
          <div class="metric-sub" id="diskSub">System Drive</div>
          <div class="metric-progress"><div class="metric-bar" id="diskBar" style="width: 0%; background: #10B981;"></div></div>
        </div>
        <div class="metric-card">
          <div class="metric-label">HOST UPTIME</div>
          <div class="metric-value" id="uptimeVal">--</div>
          <div class="metric-sub" id="hostNameSub">WIN-HOST</div>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="card">
        <div class="card-title">Quick Actions</div>
        <div class="action-grid">
          <button class="action-btn" onclick="switchTab('computer')">
            <span class="action-icon">📸</span>
            <span class="action-label">Desktop</span>
          </button>
          <button class="action-btn" onclick="switchTab('agent')">
            <span class="action-icon">🤖</span>
            <span class="action-label">Agent Prompt</span>
          </button>
          <button class="action-btn" onclick="triggerEmergencyLock()">
            <span class="action-icon">🔒</span>
            <span class="action-label">Lock PC</span>
          </button>
        </div>
      </div>

      <!-- System Details Card -->
      <div class="card">
        <div class="card-title">Connection Info</div>
        <div style="font-size: 12px; color: var(--text-muted); line-height: 1.8;">
          <div>Host IP: <strong style="color: #FFF;" id="connIp">Loading...</strong></div>
          <div>Server Version: <strong style="color: #FFF;">v0.4.0 (Phase 04)</strong></div>
          <div>Device Status: <strong style="color: #00F0FF;" id="connDeviceStatus">Pairing required</strong></div>
        </div>
      </div>

    </div>

    <!-- Tab 2: Agent (Chat & Task Control) -->
    <div id="tab-agent" class="tab-content">
      <div class="card-title" style="margin-bottom: 8px;">
        <span>Agent Conversation</span>
        <span id="agentStatusBadge" style="font-size: 10px; color: #10B981;">IDLE</span>
      </div>

      <!-- Active Stop Task Button inside Agent tab if task is active -->
      <div id="agentActiveTaskBar" style="display:none; margin-bottom: 12px;">
        <button id="btnAgentStop" class="btn-stop-task" style="width: 100%; justify-content: center; padding: 12px;">
          <span>■</span> EMERGENCY STOP TASK (DIRECT OUT-OF-BAND)
        </button>
      </div>

      <!-- Messages Feed -->
      <div id="agentFeed" class="agent-feed">
        <div class="msg system">
          NOVA Agent Ready. Send a command or prompt to control your Windows PC remotely.
        </div>
      </div>

      <!-- Bottom Floating Input -->
      <div class="agent-input-container">
        <div class="agent-input-wrapper">
          <input id="agentQueryInput" class="agent-input" type="text" placeholder="Tell NOVA to do something..." autocomplete="off">
        </div>
        <button id="btnSendQuery" class="btn-send" onclick="sendAgentQuery()">
          ➤
        </button>
      </div>
    </div>

    <!-- Tab 3: Computer (Screen Viewer) -->
    <div id="tab-computer" class="tab-content">
      <div class="card">
        <div class="card-title">
          <span>Live Desktop Screen</span>
          <span id="screenMeta" style="font-size: 10px; color: var(--cyan-glow);">Ready</span>
        </div>
        <div class="screen-wrapper" id="screenWrapper">
          <div class="screen-loading" id="screenStatus">Tap Refresh to capture desktop</div>
          <img id="screenImg" class="screen-img" style="display: none;" alt="Windows Desktop">
        </div>
        <div class="screen-controls">
          <button class="btn-screen-refresh" onclick="fetchScreenshot()">
            <span>🔄</span> Capture Desktop Now
          </button>
          <label style="font-size: 11px; color: var(--text-muted); display: flex; align-items: center; gap: 6px;">
            <input type="checkbox" id="chkAutoRefresh" onchange="toggleAutoRefresh(this.checked)"> Auto-refresh (3s)
          </label>
        </div>
      </div>
    </div>

    <!-- Tab 4: Activity (Live Event Logs) -->
    <div id="tab-activity" class="tab-content">
      <div class="card">
        <div class="card-title">
          <span>Real-Time WebSocket Stream</span>
          <button onclick="clearActivity()" style="background:none; border:none; color:var(--text-muted); font-size:11px; cursor:pointer;">Clear</button>
        </div>
        <div id="activityList" class="activity-list">
          <div class="activity-item">
            <div class="activity-header">
              <span class="activity-type">SYSTEM</span>
              <span>LIVE</span>
            </div>
            <div class="activity-payload">Listening for events on /ws/v1/events...</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Tab 5: Settings / Pairing -->
    <div id="tab-settings" class="tab-content">
      <div class="card" id="pairingCard">
        <div class="card-title">Device Pairing</div>
        <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 14px; line-height: 1.5;">
          Enter the 6-digit PIN code displayed on your Windows host terminal (e.g. from <code>nova host pair-code</code>) to authorize this iPhone.
        </p>
        <div class="pair-form">
          <input type="text" id="pinInput" class="pin-input" maxlength="12" placeholder="000 000" inputmode="numeric" pattern="[0-9]*" autocomplete="one-time-code">
          
          <div class="pin-keypad">
            <button type="button" class="keypad-btn" onclick="tapKey('1')">1</button>
            <button type="button" class="keypad-btn" onclick="tapKey('2')">2</button>
            <button type="button" class="keypad-btn" onclick="tapKey('3')">3</button>
            <button type="button" class="keypad-btn" onclick="tapKey('4')">4</button>
            <button type="button" class="keypad-btn" onclick="tapKey('5')">5</button>
            <button type="button" class="keypad-btn" onclick="tapKey('6')">6</button>
            <button type="button" class="keypad-btn" onclick="tapKey('7')">7</button>
            <button type="button" class="keypad-btn" onclick="tapKey('8')">8</button>
            <button type="button" class="keypad-btn" onclick="tapKey('9')">9</button>
            <button type="button" class="keypad-btn" onclick="tapKey('clear')" style="color:var(--crimson); font-size:16px;">CLR</button>
            <button type="button" class="keypad-btn" onclick="tapKey('0')">0</button>
            <button type="button" class="keypad-btn" onclick="tapKey('back')" style="color:var(--amber); font-size:18px;">⌫</button>
          </div>

          <button class="btn-primary" onclick="submitPairing()">Pair This iPhone</button>
          <button class="btn-screen-refresh" onclick="quickLocalPair()" style="justify-content: center; font-weight:700; color:#00F0FF; padding: 12px;">
            ⚡ Quick Auto-Pair (1-Tap Connect)
          </button>
        </div>
      </div>

      <div class="card" id="pairedInfoCard" style="display: none;">
        <div class="card-title">Paired Controller</div>
        <div style="font-size: 12px; line-height: 1.8; color: var(--text-muted); margin-bottom: 14px;">
          <div>Device Name: <strong style="color:#FFF;" id="infoDeviceName">iPhone Controller</strong></div>
          <div>Device ID: <strong style="color:#FFF; font-family:var(--font-mono); font-size:10px;" id="infoDeviceId">--</strong></div>
          <div>Role: <strong style="color:#00F0FF;">CONTROLLER (Authorized)</strong></div>
        </div>
        <button class="btn-danger" style="width: 100%;" onclick="unpairDevice()">Unpair This Device</button>
      </div>

      <div class="card">
        <div class="card-title">Add to iPhone Home Screen</div>
        <p style="font-size: 12px; color: var(--text-muted); line-height: 1.6;">
          To use NOVA as a native full-screen app on your iPhone:
          <br>1. Tap the <strong>Share</strong> icon (square with arrow) in Safari.
          <br>2. Scroll down and tap <strong>"Add to Home Screen"</strong>.
          <br>3. Open NOVA from your home screen for the full borderless experience!
        </p>
      </div>
    </div>

  </main>

  <!-- Bottom Navigation Bar -->
  <nav class="tab-bar">
    <button class="tab-btn active" onclick="switchTab('home')">
      <span class="tab-icon">⚡</span>
      <span class="tab-label">Home</span>
    </button>
    <button class="tab-btn" onclick="switchTab('agent')">
      <span class="tab-icon">🤖</span>
      <span class="tab-label">Agent</span>
    </button>
    <button class="tab-btn" onclick="switchTab('computer')">
      <span class="tab-icon">🖥️</span>
      <span class="tab-label">Computer</span>
    </button>
    <button class="tab-btn" onclick="switchTab('activity')">
      <span class="tab-icon">📜</span>
      <span class="tab-label">Activity</span>
    </button>
    <button class="tab-btn" onclick="switchTab('settings')">
      <span class="tab-icon">⚙️</span>
      <span class="tab-label">Settings</span>
    </button>
  </nav>

  <script>
    // App State
    let authToken = localStorage.getItem("nova_token") || null;
    let deviceId = localStorage.getItem("nova_device_id") || ("web-" + Math.random().toString(36).substring(2, 10));
    localStorage.setItem("nova_device_id", deviceId);

    let activeTaskId = null;
    let ws = null;
    let autoRefreshTimer = null;

    // Toast helper
    function showToast(msg) {
      const toast = document.getElementById("toast");
      toast.innerText = msg;
      toast.classList.add("show");
      setTimeout(() => toast.classList.remove("show"), 2500);
    }

    // Tab Switching
    function switchTab(tabName) {
      document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));
      document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));

      const target = document.getElementById("tab-" + tabName);
      if (target) target.classList.add("active");

      const idx = ["home", "agent", "computer", "activity", "settings"].indexOf(tabName);
      if (idx !== -1) {
        document.querySelectorAll(".tab-btn")[idx].classList.add("active");
      }

      if (tabName === "computer" && authToken) {
        fetchScreenshot();
      }
    }

    // Formatting Helpers
    function formatBytes(bytes) {
      if (!bytes) return "0 GB";
      return (bytes / (1024 * 1024 * 1024)).toFixed(1) + " GB";
    }

    function formatUptime(seconds) {
      if (!seconds) return "0s";
      const h = Math.floor(seconds / 3600);
      const m = Math.floor((seconds % 3600) / 60);
      if (h > 0) return `${h}h ${m}m`;
      return `${m}m ${Math.floor(seconds % 60)}s`;
    }

    // Connect WebSocket
    function connectWebSocket() {
      const statusDot = document.getElementById("statusDot");
      const statusText = document.getElementById("statusText");

      if (!authToken) {
        if (statusDot) statusDot.className = "status-dot";
        if (statusText) statusText.innerText = "Pairing Required";
        return;
      }

      if (ws) {
        try { ws.close(); } catch(e) {}
      }

      const protocol = location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${location.host}/ws/v1/events?token=${encodeURIComponent(authToken)}`;

      statusDot.className = "status-dot reconnecting";
      statusText.innerText = "Connecting...";

      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        statusDot.className = "status-dot connected";
        statusText.innerText = "Connected";
        showToast("Connected to Windows Host");
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          handleWebSocketMessage(payload);
        } catch (e) {
          console.error("WS Parse error", e);
        }
      };

      ws.onclose = () => {
        statusDot.className = "status-dot";
        statusText.innerText = "Disconnected";
        if (authToken) {
          setTimeout(connectWebSocket, 3000);
        }
      };

      ws.onerror = () => {
        statusDot.className = "status-dot";
        statusText.innerText = "Error";
      };
    }

    function handleWebSocketMessage(msg) {
      // Add to activity list
      addActivityItem(msg.event_type || "EVENT", JSON.stringify(msg.data || {}));

      if (msg.event_type === "telemetry" && msg.data) {
        updateTelemetry(msg.data);
      } else if (msg.event_type === "task_started") {
        setActiveTask(msg.data?.task_id, msg.data?.prompt || "Running task...");
      } else if (msg.event_type === "task_completed" || msg.event_type === "task_cancelled") {
        clearActiveTask();
      }
    }

    function updateTelemetry(data) {
      const cpu = Math.round(data.cpu_percent || 0);
      document.getElementById("cpuVal").innerText = cpu + "%";
      document.getElementById("cpuBar").style.width = cpu + "%";

      const ram = Math.round(data.memory_percent || 0);
      document.getElementById("ramVal").innerText = ram + "%";
      document.getElementById("ramBar").style.width = ram + "%";
      if (data.memory_used_bytes && data.memory_total_bytes) {
        document.getElementById("ramSub").innerText = `${formatBytes(data.memory_used_bytes)} / ${formatBytes(data.memory_total_bytes)}`;
      }

      if (data.disk_percent) {
        const disk = Math.round(data.disk_percent);
        document.getElementById("diskVal").innerText = (100 - disk) + "%";
        document.getElementById("diskBar").style.width = disk + "%";
      }

      if (data.uptime_seconds) {
        document.getElementById("uptimeVal").innerText = formatUptime(data.uptime_seconds);
      }
    }

    function addActivityItem(type, detail) {
      const list = document.getElementById("activityList");
      const item = document.createElement("div");
      item.className = "activity-item";
      const timeStr = new Date().toLocaleTimeString();
      item.innerHTML = `
        <div class="activity-header">
          <span class="activity-type">${type}</span>
          <span>${timeStr}</span>
        </div>
        <div class="activity-payload">${detail.substring(0, 160)}</div>
      `;
      list.insertBefore(item, list.firstChild);
      if (list.children.length > 50) {
        list.removeChild(list.lastChild);
      }
    }

    function clearActivity() {
      document.getElementById("activityList").innerHTML = "";
    }

    // Task Management
    function setActiveTask(taskId, prompt) {
      activeTaskId = taskId;
      document.getElementById("taskBanner").style.display = "flex";
      document.getElementById("bannerTaskPrompt").innerText = prompt;
      document.getElementById("agentActiveTaskBar").style.display = "block";
      document.getElementById("agentStatusBadge").innerText = "EXECUTING";
      document.getElementById("agentStatusBadge").style.color = "#EF4444";
    }

    function clearActiveTask() {
      activeTaskId = null;
      document.getElementById("taskBanner").style.display = "none";
      document.getElementById("agentActiveTaskBar").style.display = "none";
      document.getElementById("agentStatusBadge").innerText = "IDLE";
      document.getElementById("agentStatusBadge").style.color = "#10B981";
    }

    async function stopActiveTask() {
      if (!activeTaskId) return;
      try {
        const resp = await fetch(`/api/v1/agent/tasks/${activeTaskId}/cancel`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + authToken
          },
          body: JSON.stringify({ reason: "User tapped emergency stop from mobile web interface" })
        });
        const res = await resp.json();
        showToast("Task Cancelled: " + (res.status || "OK"));
        clearActiveTask();
        addMsg("agent", "Task execution stopped directly via out-of-band task controller.");
      } catch (e) {
        showToast("Error cancelling task");
      }
    }

    document.getElementById("btnBannerStop").onclick = stopActiveTask;
    document.getElementById("btnAgentStop").onclick = stopActiveTask;

    // Agent Chat Feed
    function addMsg(role, text) {
      const feed = document.getElementById("agentFeed");
      const div = document.createElement("div");
      div.className = "msg " + role;
      div.innerText = text;
      const meta = document.createElement("div");
      meta.className = "msg-meta";
      meta.innerText = new Date().toLocaleTimeString();
      div.appendChild(meta);
      feed.appendChild(div);
      feed.scrollTop = feed.scrollHeight;
    }

    async function sendAgentQuery() {
      const input = document.getElementById("agentQueryInput");
      const query = input.value.trim();
      if (!query) return;

      if (!authToken) {
        showToast("Please pair device first in Settings!");
        switchTab("settings");
        return;
      }

      input.value = "";
      addMsg("user", query);

      const tempId = "task-" + Date.now();
      setActiveTask(tempId, query);

      try {
        const resp = await fetch("/api/v1/agent/query", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + authToken
          },
          body: JSON.stringify({
            query: query,
            timeout_seconds: 60,
            request_id: "req-" + Date.now()
          })
        });

        const data = await resp.json();
        if (resp.ok) {
          addMsg("agent", data.response || "(No output from agent)");
        } else {
          addMsg("agent", "Error: " + (data.error?.message || "Failed to execute query"));
        }
      } catch (e) {
        addMsg("agent", "Network error communicating with host: " + e.message);
      } finally {
        clearActiveTask();
      }
    }

    document.getElementById("agentQueryInput").addEventListener("keydown", (e) => {
      if (e.key === "Enter") sendAgentQuery();
    });

    // Computer Screen Viewer
    async function fetchScreenshot() {
      if (!authToken) {
        document.getElementById("screenStatus").innerText = "Please pair device first.";
        return;
      }
      const statusEl = document.getElementById("screenStatus");
      const imgEl = document.getElementById("screenImg");
      const metaEl = document.getElementById("screenMeta");

      statusEl.style.display = "block";
      statusEl.innerText = "Capturing screen...";

      try {
        const startTime = Date.now();
        const resp = await fetch("/api/v1/screen/capture", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + authToken
          },
          body: JSON.stringify({ max_width: 1280, quality: 75 })
        });

        if (resp.ok) {
          const data = await resp.json();
          imgEl.src = "data:image/jpeg;base64," + data.image_base64;
          imgEl.style.display = "block";
          statusEl.style.display = "none";
          const elapsed = Date.now() - startTime;
          metaEl.innerText = `${data.width}x${data.height} (${elapsed}ms)`;
        } else {
          statusEl.innerText = "Failed to capture desktop";
        }
      } catch (e) {
        statusEl.innerText = "Capture error: " + e.message;
      }
    }

    function toggleAutoRefresh(enabled) {
      if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
        autoRefreshTimer = null;
      }
      if (enabled) {
        fetchScreenshot();
        autoRefreshTimer = setInterval(fetchScreenshot, 3000);
      }
    }

    // Emergency PC Lock
    async function triggerEmergencyLock() {
      if (!authToken) {
        showToast("Please pair device first!");
        switchTab("settings");
        return;
      }
      if (!confirm("Are you sure you want to immediately lock the Windows workstation?")) {
        return;
      }
      try {
        const resp = await fetch("/api/v1/emergency/lock", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + authToken
          },
          body: JSON.stringify({ reason: "Emergency lock triggered from iPhone Web App" })
        });
        const res = await resp.json();
        showToast(res.message || "PC Locked");
      } catch (e) {
        showToast("Lock request failed: " + e.message);
      }
    }

    // Device Pairing Logic
    function extractDigits(str) {
      if (!str) return "";
      let res = "";
      for (let i = 0; i < str.length; i++) {
        if (str[i] >= "0" && str[i] <= "9") res += str[i];
      }
      return res;
    }

    function formatAndSetPin(digits) {
      const pinInput = document.getElementById("pinInput");
      if (!pinInput) return;
      if (digits.length > 3) {
        pinInput.value = digits.substring(0, 3) + " " + digits.substring(3, 6);
      } else {
        pinInput.value = digits;
      }
      if (digits.length === 6) {
        setTimeout(submitPairing, 120);
      }
    }

    function tapKey(k) {
      const pinInput = document.getElementById("pinInput");
      let digits = extractDigits(pinInput.value);
      if (k === 'clear') {
        digits = "";
      } else if (k === 'back') {
        digits = digits.slice(0, -1);
      } else if (digits.length < 6) {
        digits += k;
      }
      formatAndSetPin(digits);
    }

    async function submitPairing() {
      const pinInput = document.getElementById("pinInput");
      const digits = extractDigits(pinInput.value);
      if (digits.length !== 6) {
        showToast("Please enter a 6-digit PIN (" + digits.length + "/6 entered)");
        return;
      }

      showToast("Pairing with host...");

      try {
        const resp = await fetch("/api/v1/pair", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            pairing_code: digits,
            device_id: deviceId,
            device_name: "iPhone Controller (Web)",
            platform: "iOS"
          })
        });

        const data = await resp.json();
        if (resp.ok && data.token) {
          authToken = data.token;
          localStorage.setItem("nova_token", authToken);
          showToast("Device Paired Successfully!");
          updatePairingUI();
          connectWebSocket();
          switchTab("home");
        } else {
          showToast("Pairing failed: " + (data.error?.message || "Invalid or expired PIN"));
        }
      } catch (e) {
        showToast("Pairing network error: " + e.message);
      }
    }

    async function quickLocalPair() {
      showToast("Fetching active pairing code...");
      try {
        const resp = await fetch("/api/v1/pair/code");
        if (resp.ok) {
          const data = await resp.json();
          if (data.code) {
            formatAndSetPin(data.code);
            return;
          }
        }
      } catch(e) {}
      showToast("No active pairing code found. Run 'nova host pair-code' on PC");
    }

    function unpairDevice() {
      localStorage.removeItem("nova_token");
      authToken = null;
      updatePairingUI();
      showToast("Device Unpaired");
    }

    function updatePairingUI() {
      const pairingCard = document.getElementById("pairingCard");
      const infoCard = document.getElementById("pairedInfoCard");
      const connStatus = document.getElementById("connDeviceStatus");

      if (authToken) {
        pairingCard.style.display = "none";
        infoCard.style.display = "block";
        connStatus.innerText = "Authorized Controller";
        connStatus.style.color = "#10B981";
        document.getElementById("infoDeviceId").innerText = deviceId;
      } else {
        pairingCard.style.display = "block";
        infoCard.style.display = "none";
        connStatus.innerText = "Pairing Required";
        connStatus.style.color = "#F59E0B";
      }
    }

    // Initialize
    window.addEventListener("DOMContentLoaded", () => {
      document.getElementById("connIp").innerText = location.host;
      updatePairingUI();
      connectWebSocket();

      // PIN input auto-formatting
      const pinInput = document.getElementById("pinInput");
      pinInput.addEventListener("input", (e) => {
        const digits = extractDigits(e.target.value);
        formatAndSetPin(digits);
      });
    });
  </script>
</body>
</html>
"""

WEB_APP_MANIFEST = """{
  "name": "NOVA Mobile Control",
  "short_name": "NOVA",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#080B10",
  "theme_color": "#0B0E14",
  "icons": [
    {
      "src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%23080B10'/><text x='50' y='65' font-size='50' font-family='sans-serif' font-weight='bold' text-anchor='middle' fill='%2300F0FF'>N</text></svg>",
      "sizes": "192x192 512x512",
      "type": "image/svg+xml"
    }
  ]
}
"""
