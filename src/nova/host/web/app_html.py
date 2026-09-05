"""Mobile Web Control Center single-page application for NOVA Windows Host."""

WEB_APP_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="NOVA Pro">
  <meta name="theme-color" content="#070A0F">
  <title>NOVA — Million Dollar Mobile Command Center</title>
  <link rel="manifest" href="/manifest.json">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-primary: #06080D;
      --bg-surface: #0C1017;
      --bg-card: rgba(16, 22, 34, 0.65);
      --bg-card-hover: rgba(24, 32, 48, 0.8);
      --border-glass: rgba(255, 255, 255, 0.08);
      --border-accent: rgba(0, 240, 255, 0.35);
      --border-glow: rgba(0, 240, 255, 0.6);
      
      --cyan-glow: #00F0FF;
      --cyan-dim: rgba(0, 240, 255, 0.12);
      --purple-glow: #9D4EDD;
      --purple-dim: rgba(157, 78, 221, 0.15);
      --emerald: #10B981;
      --emerald-dim: rgba(16, 185, 129, 0.15);
      --amber: #F59E0B;
      --amber-dim: rgba(245, 158, 11, 0.15);
      --crimson: #FF3B30;
      --crimson-dim: rgba(255, 59, 48, 0.18);
      
      --text-main: #F8FAFC;
      --text-muted: #8E9BAE;
      --text-dim: #5A6578;
      
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
      touch-action: manipulation;
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
        radial-gradient(circle at 10% 5%, rgba(0, 240, 255, 0.08) 0%, transparent 45%),
        radial-gradient(circle at 90% 90%, rgba(157, 78, 221, 0.08) 0%, transparent 45%);
      background-attachment: fixed;
    }

    /* Top Navigation Header */
    header {
      padding-top: calc(var(--safe-top) + 12px);
      padding-bottom: 14px;
      padding-left: 20px;
      padding-right: 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(6, 8, 13, 0.82);
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      border-bottom: 1px solid var(--border-glass);
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .logo-badge {
      width: 36px;
      height: 36px;
      border-radius: 11px;
      background: linear-gradient(135deg, #00F0FF 0%, #7B2CBF 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 18px;
      color: #000;
      box-shadow: 0 0 20px rgba(0, 240, 255, 0.45);
      position: relative;
    }

    .logo-badge::after {
      content: '';
      position: absolute;
      inset: -1px;
      border-radius: 12px;
      padding: 1px;
      background: linear-gradient(135deg, rgba(255,255,255,0.6), transparent);
      -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
      -webkit-mask-composite: xor;
      mask-composite: exclude;
    }

    .brand-text h1 {
      font-size: 17px;
      font-weight: 800;
      letter-spacing: 0.6px;
      background: linear-gradient(135deg, #FFF 60%, #94A3B8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .brand-text p {
      font-size: 9px;
      color: var(--cyan-glow);
      text-transform: uppercase;
      letter-spacing: 1.2px;
      font-weight: 700;
    }

    .status-badge {
      display: flex;
      align-items: center;
      gap: 7px;
      padding: 6px 12px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 600;
      background: rgba(16, 22, 34, 0.8);
      border: 1px solid var(--border-glass);
      backdrop-filter: blur(12px);
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--crimson);
      box-shadow: 0 0 10px var(--crimson);
      transition: all 0.3s ease;
    }

    .status-dot.connected {
      background: var(--emerald);
      box-shadow: 0 0 12px var(--emerald);
    }

    .status-dot.reconnecting {
      background: var(--amber);
      box-shadow: 0 0 12px var(--amber);
      animation: pulse 1s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(1.25); }
    }

    /* Main Content Area */
    main {
      flex: 1;
      overflow-y: auto;
      padding: 18px 18px calc(var(--safe-bottom) + 85px) 18px;
    }

    .tab-content {
      display: none;
      animation: fadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    .tab-content.active {
      display: block;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(10px) scale(0.99); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }

    /* Glassmorphic Cards */
    .card {
      background: var(--bg-card);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid var(--border-glass);
      border-radius: 22px;
      padding: 20px;
      margin-bottom: 16px;
      box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35);
      position: relative;
      overflow: hidden;
    }

    .card-title {
      font-size: 12px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 1px;
      margin-bottom: 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    /* Telemetry Grid */
    .telemetry-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
      margin-bottom: 16px;
    }

    .metric-card {
      background: rgba(12, 16, 23, 0.8);
      border: 1px solid var(--border-glass);
      border-radius: 18px;
      padding: 16px;
      position: relative;
      overflow: hidden;
      transition: border-color 0.2s;
    }

    .metric-card:active {
      border-color: var(--border-accent);
    }

    .metric-label {
      font-size: 10px;
      color: var(--text-muted);
      font-weight: 700;
      letter-spacing: 0.8px;
      margin-bottom: 6px;
    }

    .metric-value {
      font-size: 24px;
      font-weight: 800;
      color: #FFF;
      font-family: var(--font-mono);
      letter-spacing: -0.5px;
    }

    .metric-sub {
      font-size: 10px;
      color: var(--text-dim);
      margin-top: 4px;
    }

    .metric-progress {
      height: 4px;
      background: rgba(255, 255, 255, 0.06);
      border-radius: 3px;
      margin-top: 10px;
      overflow: hidden;
    }

    .metric-bar {
      height: 100%;
      background: linear-gradient(90deg, #00F0FF, #7B2CBF);
      border-radius: 3px;
      transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* Active Task Banner */
    .task-banner {
      background: linear-gradient(135deg, rgba(255, 59, 48, 0.2), rgba(123, 44, 191, 0.2));
      border: 1px solid rgba(255, 59, 48, 0.4);
      border-radius: 20px;
      padding: 16px;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 0 25px rgba(255, 59, 48, 0.2);
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
      margin-top: 3px;
      max-width: 190px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .btn-stop-task {
      background: linear-gradient(135deg, #FF3B30, #D70015);
      color: #FFF;
      border: none;
      padding: 9px 16px;
      border-radius: 12px;
      font-weight: 800;
      font-size: 11px;
      letter-spacing: 0.6px;
      box-shadow: 0 4px 15px rgba(255, 59, 48, 0.4);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: transform 0.1s;
    }

    .btn-stop-task:active {
      transform: scale(0.94);
    }

    /* Quick Action Grid */
    .action-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
    }

    .action-btn {
      background: rgba(16, 22, 34, 0.7);
      border: 1px solid var(--border-glass);
      border-radius: 18px;
      padding: 16px 10px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 10px;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .action-btn:active {
      background: rgba(0, 240, 255, 0.1);
      border-color: var(--cyan-glow);
      transform: scale(0.95);
    }

    .action-icon {
      font-size: 22px;
    }

    .action-label {
      font-size: 11px;
      font-weight: 700;
      color: var(--text-main);
    }

    /* Agent Feed & Voice Interface */
    .agent-feed {
      display: flex;
      flex-direction: column;
      gap: 14px;
      margin-bottom: 90px;
      min-height: 280px;
    }

    .msg {
      max-width: 88%;
      padding: 14px 18px;
      border-radius: 20px;
      font-size: 14px;
      line-height: 1.5;
      user-select: text;
      position: relative;
    }

    .msg.user {
      align-self: flex-end;
      background: linear-gradient(135deg, #00F0FF, #0072FF);
      color: #000;
      font-weight: 600;
      border-bottom-right-radius: 4px;
      box-shadow: 0 6px 20px rgba(0, 240, 255, 0.3);
    }

    .msg.agent {
      align-self: flex-start;
      background: rgba(18, 26, 40, 0.9);
      border: 1px solid var(--border-glass);
      color: var(--text-main);
      border-bottom-left-radius: 4px;
      box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
    }

    .msg.system {
      align-self: center;
      font-size: 11px;
      color: var(--text-muted);
      background: rgba(255, 255, 255, 0.04);
      padding: 8px 16px;
      border-radius: 14px;
      text-align: center;
      max-width: 90%;
      border: 1px solid var(--border-glass);
    }

    .msg-meta {
      font-size: 9px;
      opacity: 0.6;
      margin-top: 6px;
      font-family: var(--font-mono);
    }

    /* Agent Floating Voice & Text Input Container */
    .agent-input-container {
      position: fixed;
      bottom: calc(var(--safe-bottom) + 70px);
      left: 16px;
      right: 16px;
      display: flex;
      gap: 10px;
      z-index: 90;
      align-items: center;
    }

    .agent-input-wrapper {
      flex: 1;
      position: relative;
      background: rgba(12, 16, 23, 0.92);
      border: 1px solid var(--border-glass);
      border-radius: 28px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      padding: 0 16px;
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
    }

    .agent-input-wrapper:focus-within {
      border-color: var(--cyan-glow);
      box-shadow: 0 0 20px rgba(0, 240, 255, 0.3);
    }

    .agent-input {
      width: 100%;
      background: transparent;
      border: none;
      outline: none;
      color: #FFF;
      font-size: 14px;
      font-family: var(--font-sans);
      padding: 14px 0;
      user-select: text;
    }

    .agent-input::placeholder {
      color: var(--text-muted);
    }

    .btn-send {
      width: 48px;
      height: 48px;
      border-radius: 50%;
      background: linear-gradient(135deg, #00F0FF, #0072FF);
      border: none;
      color: #000;
      font-size: 18px;
      font-weight: 800;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 6px 20px rgba(0, 240, 255, 0.4);
      flex-shrink: 0;
      transition: transform 0.1s;
    }

    .btn-send:active {
      transform: scale(0.92);
    }

    /* Screen Viewer Tab */
    .screen-wrapper {
      width: 100%;
      border-radius: 18px;
      overflow: hidden;
      border: 1px solid var(--border-glass);
      background: #000;
      min-height: 220px;
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
      margin-top: 14px;
    }

    .btn-screen-refresh {
      background: rgba(16, 22, 34, 0.8);
      border: 1px solid var(--border-glass);
      color: var(--cyan-glow);
      padding: 10px 16px;
      border-radius: 14px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: background 0.2s;
    }

    .btn-screen-refresh:active {
      background: rgba(0, 240, 255, 0.15);
    }

    /* Ultra-Responsive Touchpad trackpad */
    .ctrl-pill-bar {
      display: flex;
      gap: 8px;
      overflow-x: auto;
      margin-top: 16px;
      margin-bottom: 16px;
      padding-bottom: 4px;
    }

    .ctrl-pill {
      background: rgba(16, 22, 34, 0.8);
      border: 1px solid var(--border-glass);
      color: var(--text-muted);
      padding: 8px 16px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s ease;
    }

    .ctrl-pill.active {
      background: linear-gradient(135deg, #00F0FF, #0072FF);
      color: #000;
      border-color: var(--cyan-glow);
      box-shadow: 0 4px 15px rgba(0, 240, 255, 0.3);
    }

    .touchpad-box {
      width: 100%;
      height: 200px;
      background: radial-gradient(circle at center, rgba(16, 22, 34, 0.9), rgba(8, 11, 16, 0.95));
      border: 1.5px solid var(--border-accent);
      border-radius: 22px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--text-muted);
      font-size: 12px;
      touch-action: none;
      user-select: none;
      position: relative;
      text-align: center;
      padding: 16px;
      box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.6);
    }

    .touchpad-box.active-touch {
      border-color: var(--cyan-glow);
      box-shadow: inset 0 0 30px rgba(0, 240, 255, 0.15), 0 0 20px rgba(0, 240, 255, 0.2);
    }

    .ctrl-btn-row {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
      margin-top: 10px;
    }

    .ctrl-key-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      margin-top: 10px;
    }

    .ctrl-key-btn {
      background: rgba(16, 22, 34, 0.8);
      border: 1px solid var(--border-glass);
      color: var(--text-main);
      padding: 12px 8px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 700;
      text-align: center;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .ctrl-key-btn:active {
      background: rgba(0, 240, 255, 0.2);
      border-color: var(--cyan-glow);
      color: var(--cyan-glow);
      transform: scale(0.95);
    }

    .comp-item-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 0;
      border-bottom: 1px solid var(--border-glass);
      font-size: 12px;
    }

    /* Activity Log */
    .activity-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .activity-item {
      background: rgba(12, 16, 23, 0.8);
      border: 1px solid var(--border-glass);
      border-radius: 14px;
      padding: 12px 16px;
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

    /* Pairing Form */
    .pair-form {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .pin-input {
      background: rgba(12, 16, 23, 0.9);
      border: 2px solid var(--border-accent);
      border-radius: 18px;
      color: #FFF;
      font-size: 32px;
      font-family: var(--font-mono);
      letter-spacing: 10px;
      text-align: center;
      padding: 16px;
      outline: none;
      user-select: text;
    }

    .pin-input:focus {
      border-color: var(--cyan-glow);
      box-shadow: 0 0 20px rgba(0, 240, 255, 0.35);
    }

    .pin-keypad {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      margin: 10px 0;
    }

    .keypad-btn {
      background: rgba(16, 22, 34, 0.9);
      border: 1px solid var(--border-glass);
      border-radius: 16px;
      color: #FFF;
      font-size: 22px;
      font-weight: 700;
      font-family: var(--font-mono);
      padding: 14px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.15s ease;
    }

    .keypad-btn:active {
      background: rgba(0, 240, 255, 0.2);
      border-color: var(--cyan-glow);
      transform: scale(0.93);
    }

    .btn-primary {
      background: linear-gradient(135deg, #00F0FF, #0072FF);
      color: #000;
      border: none;
      border-radius: 16px;
      padding: 16px;
      font-weight: 800;
      font-size: 15px;
      cursor: pointer;
      box-shadow: 0 6px 25px rgba(0, 240, 255, 0.4);
      transition: transform 0.1s;
    }

    .btn-primary:active {
      transform: scale(0.97);
    }

    .btn-danger {
      background: rgba(255, 59, 48, 0.15);
      border: 1px solid rgba(255, 59, 48, 0.4);
      color: #FF3B30;
      border-radius: 16px;
      padding: 14px;
      font-weight: 700;
      font-size: 14px;
      cursor: pointer;
    }

    .btn-danger:active {
      background: rgba(255, 59, 48, 0.3);
    }

    /* Fixed Bottom Glass Tab Bar */
    nav.tab-bar {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      height: calc(var(--safe-bottom) + 60px);
      padding-bottom: var(--safe-bottom);
      background: rgba(6, 8, 13, 0.92);
      backdrop-filter: blur(30px);
      -webkit-backdrop-filter: blur(30px);
      border-top: 1px solid var(--border-glass);
      display: grid;
      grid-template-columns: repeat(6, 1fr);
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
      gap: 5px;
      cursor: pointer;
      transition: color 0.2s ease;
    }

    .tab-btn.active {
      color: var(--cyan-glow);
    }

    .tab-icon {
      font-size: 20px;
    }

    .tab-label {
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.3px;
    }

    /* Toast Notifications */
    .toast {
      position: fixed;
      top: calc(var(--safe-top) + 65px);
      left: 50%;
      transform: translateX(-50%) translateY(-20px);
      background: rgba(12, 16, 23, 0.95);
      border: 1px solid var(--cyan-glow);
      color: #FFF;
      padding: 12px 22px;
      border-radius: 24px;
      font-size: 13px;
      font-weight: 700;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
      opacity: 0;
      pointer-events: none;
      transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
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
        <h1>NOVA PRO</h1>
        <p>Command Center</p>
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
      
      <!-- Active Task Banner -->
      <div id="taskBanner" class="task-banner" style="display: none;">
        <div class="task-info">
          <h3><span style="display:inline-block;animation:pulse 1s infinite;">●</span> Active Agent Task</h3>
          <p id="bannerTaskPrompt">Processing remote query...</p>
        </div>
        <button id="btnBannerStop" class="btn-stop-task">
          <span>■</span> STOP TASK
        </button>
      </div>

      <!-- Telemetry Grid -->
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
          <div class="metric-progress"><div class="metric-bar" id="ramBar" style="width: 0%; background: #9D4EDD;"></div></div>
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
        <div class="card-title">Quick Controls</div>
        <div class="action-grid">
          <button class="action-btn" onclick="switchTab('computer')">
            <span class="action-icon">🖥️</span>
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

      <!-- System Connection Card -->
      <div class="card">
        <div class="card-title">Connection Info</div>
        <div style="font-size: 13px; color: var(--text-muted); line-height: 1.8;">
          <div>Host Address: <strong style="color: #FFF;" id="connIp">Loading...</strong></div>
          <div>Server Version: <strong style="color: #FFF;">v0.8.0 (Phase 08)</strong></div>
          <div>Device Status: <strong style="color: #00F0FF;" id="connDeviceStatus">Pairing required</strong></div>
        </div>
      </div>

    </div>

    <!-- Tab 2: Agent (Voice & Chat Command Center) -->
    <div id="tab-agent" class="tab-content">
      <div class="card-title" style="margin-bottom: 10px;">
        <span>NOVA AI Agent Feed</span>
        <span id="agentStatusBadge" style="font-size: 10px; color: #10B981; font-weight:800;">IDLE</span>
      </div>

      <!-- Active Stop Task Button inside Agent tab if task is active -->
      <div id="agentActiveTaskBar" style="display:none; margin-bottom: 14px;">
        <button id="btnAgentStop" class="btn-stop-task" style="width: 100%; justify-content: center; padding: 14px;">
          <span>■</span> EMERGENCY STOP TASK
        </button>
      </div>

      <!-- Messages Feed -->
      <div id="agentFeed" class="agent-feed">
        <div class="msg system">
          NOVA Intelligence Online. Send a command or prompt to control your Windows PC remotely.
        </div>
      </div>

      <!-- Bottom Floating Text Input Bar -->
      <div class="agent-input-container">
        <div class="agent-input-wrapper">
          <input id="agentQueryInput" class="agent-input" type="text" placeholder="Tell NOVA to do something..." autocomplete="off">
        </div>
        <button id="btnSendQuery" class="btn-send" onclick="sendAgentQuery()">
          ➤
        </button>
      </div>
    </div>

    <!-- Tab 3: Computer (Touchpad & Keyboard Control) -->
    <div id="tab-computer" class="tab-content">
      <div class="card">
        <div class="card-title">
          <span>Live Desktop Display</span>
          <span id="screenMeta" style="font-size: 10px; color: var(--cyan-glow);">Ready</span>
        </div>
        <div class="screen-wrapper" id="screenWrapper">
          <div class="screen-loading" id="screenStatus">Tap Refresh to load desktop preview</div>
          <img id="screenImg" class="screen-img" style="display: none;" alt="Windows Desktop">
        </div>
        <div class="screen-controls">
          <button class="btn-screen-refresh" onclick="fetchScreenshot()">
            <span>🔄</span> Capture Desktop
          </button>
          <label style="font-size: 11px; color: var(--text-muted); display: flex; align-items: center; gap: 6px;">
            <input type="checkbox" id="chkAutoRefresh" onchange="toggleAutoRefresh(this.checked)"> Auto (3s)
          </label>
        </div>

        <!-- Control Mode Pills -->
        <div class="ctrl-pill-bar">
          <button class="ctrl-pill active" id="pill-touchpad" onclick="switchCompSubTab('touchpad')">Touchpad</button>
          <button class="ctrl-pill" id="pill-keyboard" onclick="switchCompSubTab('keyboard')">Keyboard</button>
          <button class="ctrl-pill" id="pill-windows" onclick="switchCompSubTab('windows')">Windows</button>
          <button class="ctrl-pill" id="pill-apps" onclick="switchCompSubTab('apps')">Apps</button>
        </div>

        <!-- Subtab 1: Touchpad -->
        <div id="comp-touchpad" class="comp-subpanel">
          <div class="touchpad-box" id="touchpadSurface">
            <span>🖱️ Drag across surface to move mouse<br>Tap to Left Click • 2-Finger Tap for Right Click</span>
          </div>
          <div class="ctrl-btn-row">
            <button class="btn-screen-refresh" style="justify-content:center;" onclick="remoteClick('left')">Left Click</button>
            <button class="btn-screen-refresh" style="justify-content:center; color:#9D4EDD;" onclick="remoteClick('right')">Right Click</button>
          </div>
          <div class="ctrl-btn-row" style="margin-top:8px;">
            <button class="btn-screen-refresh" style="justify-content:center; font-size:12px;" onclick="remoteScroll(120)">▲ Scroll Up</button>
            <button class="btn-screen-refresh" style="justify-content:center; font-size:12px;" onclick="remoteScroll(-120)">▼ Scroll Down</button>
          </div>
        </div>

        <!-- Subtab 2: Keyboard -->
        <div id="comp-keyboard" class="comp-subpanel" style="display:none;">
          <div style="display:flex; gap:8px;">
            <input type="text" id="compKeyInput" class="agent-input" style="flex:1; background:rgba(12,16,23,0.8); border:1px solid var(--border-glass); border-radius:14px; padding:10px 14px;" placeholder="Type text to send to PC...">
            <button class="btn-screen-refresh" onclick="sendCompType()">Send</button>
          </div>
          <div class="ctrl-key-grid">
            <button class="ctrl-key-btn" onclick="remoteKeyPress('Enter')">Enter</button>
            <button class="ctrl-key-btn" onclick="remoteKeyPress('Escape')">Esc</button>
            <button class="ctrl-key-btn" onclick="remoteKeyPress('Tab')">Tab</button>
            <button class="ctrl-key-btn" onclick="remoteKeyPress('Backspace')">⌫ Back</button>
            <button class="ctrl-key-btn" onclick="remoteKeyCombo(['ctrl', 'c'])">Ctrl+C</button>
            <button class="ctrl-key-btn" onclick="remoteKeyCombo(['ctrl', 'v'])">Ctrl+V</button>
            <button class="ctrl-key-btn" onclick="remoteKeyCombo(['ctrl', 'z'])">Ctrl+Z</button>
            <button class="ctrl-key-btn" onclick="remoteKeyCombo(['alt', 'tab'])">Alt+Tab</button>
          </div>
          <div class="ctrl-key-grid" style="margin-top:6px;">
            <button class="ctrl-key-btn" onclick="remoteKeyPress('Left')">←</button>
            <button class="ctrl-key-btn" onclick="remoteKeyPress('Up')">↑</button>
            <button class="ctrl-key-btn" onclick="remoteKeyPress('Down')">↓</button>
            <button class="ctrl-key-btn" onclick="remoteKeyPress('Right')">→</button>
          </div>
        </div>

        <!-- Subtab 3: Windows -->
        <div id="comp-windows" class="comp-subpanel" style="display:none;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span style="font-size:12px; color:var(--text-muted);" id="winListHeader">Active Windows</span>
            <button class="btn-screen-refresh" style="padding:6px 12px; font-size:11px;" onclick="loadWindowsList()">Refresh</button>
          </div>
          <div id="winListContainer" style="max-height:220px; overflow-y:auto;">
            <div style="color:var(--text-muted); font-size:12px;">Loading windows...</div>
          </div>
        </div>

        <!-- Subtab 4: Apps -->
        <div id="comp-apps" class="comp-subpanel" style="display:none;">
          <div style="display:flex; gap:8px; margin-bottom:8px;">
            <input type="text" id="appSearchInput" class="agent-input" style="flex:1; background:rgba(12,16,23,0.8); border:1px solid var(--border-glass); border-radius:14px; padding:8px 12px;" placeholder="Filter apps..." oninput="filterAppsList()">
            <button class="btn-screen-refresh" style="padding:6px 12px; font-size:11px;" onclick="loadAppsList()">Refresh</button>
          </div>
          <div id="appsListContainer" style="max-height:220px; overflow-y:auto;">
            <div style="color:var(--text-muted); font-size:12px;">Loading apps...</div>
          </div>
        </div>

      </div>
    </div>

    <!-- Tab: Browser (Phase 08) -->
    <div id="tab-browser" class="tab-content">
      <div class="card">
        <div class="card-title">Browser Subsystem</div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
          <span style="font-size:12px; color:var(--text-muted);">Status</span>
          <span id="browserStatusText" style="font-size:12px; font-weight:700; color:var(--amber);">Checking...</span>
        </div>
        <button class="btn-screen-refresh" style="width:100%; justify-content:center; margin-bottom:16px;" onclick="checkBrowserStatus()">Refresh Status</button>
      </div>
      
      <div class="card">
        <div class="card-title">
          <span>Active Tabs</span>
          <button class="btn-screen-refresh" style="padding:6px 12px; font-size:11px;" onclick="loadBrowserTabs()">Refresh</button>
        </div>
        <div id="browserTabsContainer" style="max-height:250px; overflow-y:auto; margin-bottom: 12px;">
          <div style="color:var(--text-muted); font-size:12px;">No tabs loaded.</div>
        </div>
        
        <div style="display:flex; gap:8px;">
          <input type="text" id="browserNewUrl" class="agent-input" style="flex:1; background:rgba(12,16,23,0.8); border:1px solid var(--border-glass); border-radius:14px; padding:10px 14px;" placeholder="https://...">
          <button class="btn-screen-refresh" onclick="openBrowserTab()">Open Tab</button>
        </div>
      </div>
    </div>

    <!-- Tab 4: Activity (Live Event Stream) -->
    <div id="tab-activity" class="tab-content">
      <div class="card">
        <div class="card-title">
          <span>Real-Time Host Audit Log</span>
          <button onclick="clearActivity()" style="background:none; border:none; color:var(--text-muted); font-size:11px; font-weight:700; cursor:pointer;">Clear</button>
        </div>
        <div id="activityList" class="activity-list">
          <div class="activity-item">
            <div class="activity-header">
              <span class="activity-type">SYSTEM</span>
              <span>LIVE</span>
            </div>
            <div class="activity-payload">Listening for system events...</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Tab 5: Settings / Pairing -->
    <div id="tab-settings" class="tab-content">
      <div class="card" id="pairingCard">
        <div class="card-title">Device Pairing</div>
        <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 16px; line-height: 1.5;">
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

          <button class="btn-primary" onclick="submitPairing()">Pair This Device</button>
          <button class="btn-screen-refresh" onclick="quickLocalPair()" style="justify-content: center; font-weight:800; color:#00F0FF; padding: 14px;">
            ⚡ Quick Auto-Pair (1-Tap Connect)
          </button>
        </div>
      </div>

      <div class="card" id="pairedInfoCard" style="display: none;">
        <div class="card-title">Paired Controller</div>
        <div style="font-size: 13px; line-height: 1.8; color: var(--text-muted); margin-bottom: 16px;">
          <div>Device Name: <strong style="color:#FFF;" id="infoDeviceName">iPhone Controller</strong></div>
          <div>Device ID: <strong style="color:#FFF; font-family:var(--font-mono); font-size:11px;" id="infoDeviceId">--</strong></div>
          <div>Role: <strong style="color:#00F0FF;">CONTROLLER (Authorized)</strong></div>
        </div>
        <button class="btn-danger" style="width: 100%;" onclick="unpairDevice()">Unpair This Device</button>
      </div>

      <div class="card">
        <div class="card-title">Add to iPhone Home Screen</div>
        <p style="font-size: 13px; color: var(--text-muted); line-height: 1.6;">
          To use NOVA as a native full-screen app on your iPhone:
          <br>1. Tap the <strong>Share</strong> icon (square with arrow) in Safari.
          <br>2. Scroll down and tap <strong>"Add to Home Screen"</strong>.
          <br>3. Open NOVA from your home screen for the full borderless app experience!
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
    <button class="tab-btn" onclick="switchTab('browser')">
      <span class="tab-icon">🌐</span>
      <span class="tab-label">Browser</span>
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
    let speechRecognition = null;
    let isRecording = false;

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

      const idx = ["home", "agent", "computer", "browser", "activity", "settings"].indexOf(tabName);
      if (idx !== -1) {
        document.querySelectorAll(".tab-btn")[idx].classList.add("active");
      }

      if (tabName === "computer" && authToken) {
        fetchScreenshot();
        initTouchpad();
      }
    }

    // Formatting Helpers
    function formatBytes(bytes) {
      if (!bytes) return "0 GB";
      const gb = bytes / (1024 * 1024 * 1024);
      return gb.toFixed(1) + " GB";
    }

    function formatUptime(seconds) {
      if (!seconds) return "--";
      const hrs = Math.floor(seconds / 3600);
      const mins = Math.floor((seconds % 3600) / 60);
      if (hrs > 0) return `${hrs}h ${mins}m`;
      return `${mins}m`;
    }

    // WebSocket Connectivity
    function connectWebSocket() {
      if (!authToken) return;
      const wsProtocol = location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${wsProtocol}//${location.host}/ws/v1/events?token=${authToken}`;

      const statusDot = document.getElementById("statusDot");
      const statusText = document.getElementById("statusText");

      statusDot.className = "status-dot reconnecting";
      statusText.innerText = "Connecting...";

      try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          statusDot.className = "status-dot connected";
          statusText.innerText = "Online";
          showToast("Connected to NOVA Host");
          fetchSystemMetrics();
        };

        ws.onmessage = (evt) => {
          try {
            const msg = JSON.parse(evt.data);
            handleServerEvent(msg);
          } catch (e) {}
        };

        ws.onclose = () => {
          statusDot.className = "status-dot";
          statusText.innerText = "Offline";
          setTimeout(connectWebSocket, 3000);
        };

        ws.onerror = () => {
          statusDot.className = "status-dot";
          statusText.innerText = "Error";
        };
      } catch (e) {}
    }

    // Handle WebSocket events
    function handleServerEvent(evt) {
      logActivity(evt.event_type || "EVENT", JSON.stringify(evt.data || {}));

      if (evt.event_type === "telemetry" && evt.data) {
        updateTelemetryUI(evt.data);
      } else if (evt.event_type === "task_update" && evt.data) {
        updateTaskUI(evt.data);
      } else if (evt.event_type === "alert" && evt.data) {
        showToast(`ALERT: ${evt.data.message || evt.data.action}`);
      }
    }

    function updateTelemetryUI(data) {
      if (data.cpu_usage_percent !== undefined) {
        document.getElementById("cpuVal").innerText = Math.round(data.cpu_usage_percent) + "%";
        document.getElementById("cpuBar").style.width = Math.min(100, data.cpu_usage_percent) + "%";
      }
      if (data.memory) {
        const memPct = Math.round(data.memory.used_percent || 0);
        document.getElementById("ramVal").innerText = memPct + "%";
        document.getElementById("ramBar").style.width = memPct + "%";
        document.getElementById("ramSub").innerText = `${formatBytes(data.memory.used_bytes)} / ${formatBytes(data.memory.total_bytes)}`;
      }
      if (data.disk) {
        const freeGb = (data.disk.free_bytes / (1024 * 1024 * 1024)).toFixed(0);
        document.getElementById("diskVal").innerText = freeGb + " GB";
        document.getElementById("diskBar").style.width = (100 - (data.disk.used_percent || 0)) + "%";
      }
      if (data.uptime_seconds !== undefined) {
        document.getElementById("uptimeVal").innerText = formatUptime(data.uptime_seconds);
      }
    }

    async function fetchSystemMetrics() {
      if (!authToken) return;
      try {
        const resp = await fetch("/api/v1/health");
        if (resp.ok) {
          const data = await resp.json();
          if (data.host_name) document.getElementById("hostNameSub").innerText = data.host_name;
          if (data.uptime_seconds) document.getElementById("uptimeVal").innerText = formatUptime(data.uptime_seconds);
        }
      } catch (e) {}
    }

    // Task Management UI
    function updateTaskUI(taskData) {
      const banner = document.getElementById("taskBanner");
      const agentBar = document.getElementById("agentActiveTaskBar");
      const promptEl = document.getElementById("bannerTaskPrompt");
      const badge = document.getElementById("agentStatusBadge");

      if (taskData.status === "RUNNING") {
        activeTaskId = taskData.task_id;
        banner.style.display = "flex";
        agentBar.style.display = "block";
        promptEl.innerText = taskData.prompt || "Running task...";
        badge.innerText = "RUNNING";
        badge.style.color = "#FF3B30";
      } else {
        activeTaskId = null;
        banner.style.display = "none";
        agentBar.style.display = "none";
        badge.innerText = "IDLE";
        badge.style.color = "#10B981";
      }
    }

    async function cancelActiveTask() {
      if (!activeTaskId || !authToken) return;
      showToast("Cancelling task...");
      try {
        await fetch(`/api/v1/agent/tasks/${activeTaskId}/cancel`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": "Bearer " + authToken },
          body: JSON.stringify({ reason: "User cancelled from web client" })
        });
      } catch (e) {
        showToast("Cancel failed: " + e.message);
      }
    }

    document.getElementById("btnBannerStop").onclick = cancelActiveTask;
    document.getElementById("btnAgentStop").onclick = cancelActiveTask;

    // Agent Query & Voice Mode
    async function sendAgentQuery(overrideText = null) {
      const input = document.getElementById("agentQueryInput");
      const text = overrideText || input.value.trim();
      if (!text) return;
      if (!authToken) { showToast("Please pair device first"); return; }

      if (!overrideText) input.value = "";
      appendAgentMsg("user", text);

      try {
        const resp = await fetch("/api/v1/agent/query", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": "Bearer " + authToken },
          body: JSON.stringify({ prompt: text })
        });

        const data = await resp.json();
        if (resp.ok) {
          appendAgentMsg("agent", data.response || "Task initiated.");
          if (data.task_id) {
            updateTaskUI({ status: "RUNNING", task_id: data.task_id, prompt: text });
          }
        } else {
          appendAgentMsg("agent", "Error: " + (data.error?.message || "Failed to process query"));
        }
      } catch (e) {
        appendAgentMsg("agent", "Network error sending prompt.");
      }
    }

    function appendAgentMsg(role, text) {
      const feed = document.getElementById("agentFeed");
      const msgDiv = document.createElement("div");
      msgDiv.className = `msg ${role}`;
      msgDiv.innerText = text;

      const meta = document.createElement("div");
      meta.className = "msg-meta";
      meta.innerText = new Date().toLocaleTimeString();
      msgDiv.appendChild(meta);

      feed.appendChild(msgDiv);
      feed.scrollTop = feed.scrollHeight;
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
      statusEl.innerText = "Capturing desktop...";

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

    // Sub-tab switching for Computer Tab
    function switchCompSubTab(sub) {
      const pills = ['touchpad', 'keyboard', 'windows', 'apps'];
      pills.forEach(p => {
        const pillEl = document.getElementById('pill-' + p);
        const panelEl = document.getElementById('comp-' + p);
        if (pillEl) pillEl.className = (p === sub) ? 'ctrl-pill active' : 'ctrl-pill';
        if (panelEl) panelEl.style.display = (p === sub) ? 'block' : 'none';
      });
      if (sub === 'windows') loadWindowsList();
      if (sub === 'apps') loadAppsList();
    }

    // Touchpad and Ultra-Responsive Mouse Control
    let lastTouchX = null, lastTouchY = null;
    let isTouchActive = false;

    function initTouchpad() {
      const touchpadEl = document.getElementById('touchpadSurface');
      if (touchpadEl && !touchpadEl._init) {
        touchpadEl._init = true;
        
        touchpadEl.addEventListener('touchstart', (e) => {
          touchpadEl.classList.add('active-touch');
          if (e.touches.length === 1) {
            lastTouchX = e.touches[0].clientX;
            lastTouchY = e.touches[0].clientY;
          }
        }, { passive: true });

        touchpadEl.addEventListener('touchmove', (e) => {
          if (e.touches.length === 1 && lastTouchX !== null) {
            const dx = Math.round((e.touches[0].clientX - lastTouchX) * 2.2);
            const dy = Math.round((e.touches[0].clientY - lastTouchY) * 2.2);
            lastTouchX = e.touches[0].clientX;
            lastTouchY = e.touches[0].clientY;
            if (Math.abs(dx) > 0 || Math.abs(dy) > 0) {
              sendMouseMove(dx, dy);
            }
          }
        }, { passive: true });

        touchpadEl.addEventListener('touchend', (e) => {
          touchpadEl.classList.remove('active-touch');
          if (e.changedTouches.length === 2) {
            remoteClick('right');
          }
          lastTouchX = null;
          lastTouchY = null;
        }, { passive: true });
      }
    }

    async function sendMouseMove(dx, dy) {
      if (!authToken) return;
      try {
        await fetch("/api/v1/computer/mouse/move", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": "Bearer " + authToken },
          body: JSON.stringify({ x: dx, y: dy, delta: true })
        });
      } catch (e) {}
    }

    async function remoteClick(btn) {
      if (!authToken) { showToast("Pairing required"); return; }
      try {
        await fetch("/api/v1/computer/mouse/click", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": "Bearer " + authToken },
          body: JSON.stringify({ button: btn, count: 1 })
        });
        showToast(btn === 'left' ? "Left Click" : "Right Click");
      } catch (e) {
        showToast("Click failed");
      }
    }

    async function remoteScroll(clicks) {
      if (!authToken) return;
      try {
        await fetch("/api/v1/computer/mouse/scroll", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": "Bearer " + authToken },
          body: JSON.stringify({ clicks: clicks })
        });
        showToast(clicks > 0 ? "Scrolled Up" : "Scrolled Down");
      } catch (e) {}
    }

    // Keyboard Control
    async function sendCompType() {
      const inp = document.getElementById('compKeyInput');
      const text = inp.value;
      if (!text || !authToken) return;
      inp.value = "";
      try {
        await fetch("/api/v1/computer/keyboard/type", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": "Bearer " + authToken },
          body: JSON.stringify({ text: text })
        });
        showToast("Sent text");
      } catch (e) {
        showToast("Type failed");
      }
    }

    async function remoteKeyPress(key) {
      if (!authToken) return;
      try {
        await fetch("/api/v1/computer/keyboard/press", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": "Bearer " + authToken },
          body: JSON.stringify({ key: key })
        });
        showToast("Key: " + key);
      } catch (e) {}
    }

    async function remoteKeyCombo(keys) {
      if (!authToken) return;
      try {
        await fetch("/api/v1/computer/keyboard/combo", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": "Bearer " + authToken },
          body: JSON.stringify({ keys: keys })
        });
        showToast("Combo: " + keys.join("+"));
      } catch (e) {}
    }

    // Windows List
    async function loadWindowsList() {
      const cont = document.getElementById("winListContainer");
      if (!authToken) { cont.innerHTML = "<div>Pairing required</div>"; return; }
      cont.innerHTML = "<div>Loading active windows...</div>";
      try {
        const resp = await fetch("/api/v1/computer/windows", {
          headers: { "Authorization": "Bearer " + authToken }
        });
        const wins = await resp.json();
        if (!wins || wins.length === 0) {
          cont.innerHTML = "<div style='color:var(--text-muted);'>No visible windows found</div>";
          return;
        }
        cont.innerHTML = wins.map(w => `
          <div class="comp-item-row">
            <div style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; padding-right:8px;">
              <strong>${w.title || w.process_name}</strong>
              <div style="color:var(--text-muted); font-size:10px;">${w.process_name} • HWND ${w.hwnd}</div>
            </div>
            <div style="display:flex; gap:6px;">
              <button class="btn-screen-refresh" style="padding:6px 10px; font-size:11px;" onclick="remoteFocusWin(${w.hwnd})">Focus</button>
              <button class="btn-screen-refresh" style="padding:6px 10px; font-size:11px; color:#FF3B30;" onclick="remoteCloseWin(${w.hwnd})">✕</button>
            </div>
          </div>
        `).join("");
      } catch (e) {
        cont.innerHTML = "<div>Error loading windows</div>";
      }
    }

    async function remoteFocusWin(hwnd) {
      try {
        await fetch("/api/v1/computer/windows/focus", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": "Bearer " + authToken },
          body: JSON.stringify({ hwnd: hwnd })
        });
        showToast("Focused window");
        fetchScreenshot();
      } catch(e) {}
    }

    async function remoteCloseWin(hwnd) {
      if (!confirm("Close this window (HWND " + hwnd + ")?")) return;
      try {
        await fetch("/api/v1/computer/windows/close", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": "Bearer " + authToken },
          body: JSON.stringify({ hwnd: hwnd })
        });
        showToast("Closed window");
        loadWindowsList();
        fetchScreenshot();
      } catch(e) {}
    }

    // Apps List
    let cachedApps = [];
    async function loadAppsList() {
      const cont = document.getElementById("appsListContainer");
      if (!authToken) { cont.innerHTML = "<div>Pairing required</div>"; return; }
      cont.innerHTML = "<div>Discovering installed apps...</div>";
      try {
        const resp = await fetch("/api/v1/computer/apps", {
          headers: { "Authorization": "Bearer " + authToken }
        });
        cachedApps = await resp.json();
        renderApps(cachedApps);
      } catch (e) {
        cont.innerHTML = "<div>Error loading apps</div>";
      }
    }

    function filterAppsList() {
      const q = (document.getElementById("appSearchInput").value || "").toLowerCase();
      const filtered = cachedApps.filter(a => a.name.toLowerCase().includes(q));
      renderApps(filtered);
    }

    function renderApps(apps) {
      const cont = document.getElementById("appsListContainer");
      if (!apps || apps.length === 0) {
        cont.innerHTML = "<div style='color:var(--text-muted);'>No matching applications</div>";
        return;
      }
      cont.innerHTML = apps.slice(0, 20).map(a => `
        <div class="comp-item-row">
          <div style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; padding-right:8px;">
            <strong>${a.name}</strong>
            <div style="color:var(--text-muted); font-size:10px;">${a.publisher || a.path || a.executable || 'System App'}</div>
          </div>
          <button class="btn-screen-refresh" style="padding:6px 12px; font-size:11px; color:#10B981;" onclick="remoteLaunchApp('${encodeURIComponent(a.path || a.executable || '')}')">Launch</button>
        </div>
      `).join("");
    }

    async function remoteLaunchApp(encodedPath) {
      const path = decodeURIComponent(encodedPath);
      try {
        showToast("Launching app...");
        const resp = await fetch("/api/v1/computer/apps/launch", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": "Bearer " + authToken },
          body: JSON.stringify({ app_name_or_path: path })
        });
        const res = await resp.json();
        showToast(res.success ? "App Launched (PID " + res.pid + ")" : "Launch failed");
        setTimeout(fetchScreenshot, 1500);
      } catch(e) {}
    }

    // Browser Subsystem
    async function checkBrowserStatus() {
      const el = document.getElementById("browserStatusText");
      if (!authToken) { el.innerText = "Pairing Required"; return; }
      el.innerText = "Checking...";
      try {
        const resp = await fetch("/api/v1/browser/status", {
          headers: { "Authorization": "Bearer " + authToken }
        });
        const data = await resp.json();
        if (resp.ok) {
          el.innerText = data.running ? "ONLINE" : (data.enabled ? "ENABLED, NOT RUNNING" : "DISABLED");
          el.style.color = data.running ? "var(--emerald)" : "var(--amber)";
        } else {
          el.innerText = "Error";
        }
      } catch (e) {
        el.innerText = "Network Error";
      }
    }

    async function loadBrowserTabs() {
      const cont = document.getElementById("browserTabsContainer");
      if (!authToken) { cont.innerHTML = "<div>Pairing Required</div>"; return; }
      cont.innerHTML = "<div>Loading tabs...</div>";
      try {
        const resp = await fetch("/api/v1/browser/tabs", {
          headers: { "Authorization": "Bearer " + authToken }
        });
        const tabs = await resp.json();
        if (resp.ok && tabs.length > 0) {
          cont.innerHTML = tabs.map(t => `
            <div class="comp-item-row">
              <div style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; padding-right:8px;">
                <strong>${t.title}</strong>
                <div style="color:var(--text-muted); font-size:10px;">${t.url || "about:blank"}</div>
              </div>
              <div style="color:var(--cyan-glow); font-size:11px;">${t.tab_id}</div>
            </div>
          `).join("");
        } else {
          cont.innerHTML = "<div style='color:var(--text-muted);'>No active tabs</div>";
        }
      } catch (e) {
        cont.innerHTML = "<div>Failed to load tabs</div>";
      }
    }

    async function openBrowserTab() {
      const url = document.getElementById("browserNewUrl").value;
      if (!authToken) { showToast("Pairing Required"); return; }
      showToast("Opening Tab...");
      try {
        await fetch("/api/v1/browser/tabs", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": "Bearer " + authToken },
          body: JSON.stringify({ url: url })
        });
        document.getElementById("browserNewUrl").value = "";
        loadBrowserTabs();
      } catch (e) {
        showToast("Error opening tab");
      }
    }

    // Emergency PC Lock
    async function triggerEmergencyLock() {
      if (!confirm("Are you sure you want to LOCK your PC workstation right now?")) return;
      if (!authToken) { showToast("Pairing required"); return; }
      try {
        await fetch("/api/v1/emergency/lock", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": "Bearer " + authToken },
          body: JSON.stringify({ reason: "User triggered emergency lock from mobile web UI" })
        });
        showToast("PC Workstation Locked!");
      } catch (e) {
        showToast("Emergency lock failed: " + e.message);
      }
    }

    // Activity Audit Stream
    function logActivity(type, payload) {
      const list = document.getElementById("activityList");
      const item = document.createElement("div");
      item.className = "activity-item";
      item.innerHTML = `
        <div class="activity-header">
          <span class="activity-type">${type}</span>
          <span>${new Date().toLocaleTimeString()}</span>
        </div>
        <div class="activity-payload">${payload}</div>
      `;
      list.insertBefore(item, list.firstChild);
      if (list.children.length > 50) list.removeChild(list.lastChild);
    }

    function clearActivity() {
      document.getElementById("activityList").innerHTML = "";
    }

    // PIN Keypad logic
    function extractDigits(val) {
      return (val || "").replace(/\D/g, "");
    }

    function formatAndSetPin(digits) {
      const pinInput = document.getElementById("pinInput");
      if (digits.length <= 3) {
        pinInput.value = digits;
      } else {
        pinInput.value = digits.slice(0, 3) + " " + digits.slice(3, 6);
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
  "background_color": "#06080D",
  "theme_color": "#06080D",
  "icons": [
    {
      "src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%2306080D'/><text x='50' y='65' font-size='50' font-family='sans-serif' font-weight='bold' text-anchor='middle' fill='%2300F0FF'>N</text></svg>",
      "sizes": "192x192 512x512",
      "type": "image/svg+xml"
    }
  ]
}
"""
