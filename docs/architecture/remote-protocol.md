# NOVA Remote Protocol v1 Specification

## 1. Transport

The protocol supports two transport channels over TCP:
- **HTTP/1.1 REST**: Request/response operations.
- **WebSocket (`/ws/v1/events`)**: Bi-directional asynchronous event streaming.

All request and response payloads use UTF-8 JSON.
Authentication is enforced via `Authorization: Bearer <token>`.

---

## 2. API Endpoints

### 2.1 Device Pairing
* **`POST /api/v1/pair`**
  * **Auth**: None (ephemeral PIN protected)
  * **Request**:
    ```json
    {
      "pairing_code": "961003",
      "device_id": "ios-uuid-12345",
      "device_name": "Siddharth's iPhone",
      "platform": "iOS"
    }
    ```
  * **Response (200 OK)**:
    ```json
    {
      "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "device_id": "ios-uuid-12345",
      "host_name": "WORKSTATION-PC",
      "server_version": "0.1.0",
      "expires_at": "2026-10-04T11:40:26.123456Z"
    }
    ```

### 2.2 System & Agent Telemetry
* **`GET /api/v1/status`**
  * **Auth**: Bearer token
  * **Response (200 OK)**: Returns real-time CPU %, RAM %, Disk %, boot time, OS version, and Agent state (`IDLE`, `PLANNING`, `EXECUTING`, `ERROR`).

### 2.3 Desktop Screen Capture
* **`POST /api/v1/screen/capture`**
  * **Auth**: Bearer token
  * **Request**:
    ```json
    {
      "format": "png",
      "max_width": 1280,
      "quality": 80
    }
    ```
  * **Response (200 OK)**: Returns base64 encoded image string, dimensions (`width`, `height`), and payload size.

### 2.4 Capabilities Discovery
* **`GET /api/v1/capabilities`**
  * **Auth**: Bearer token
  * **Response (200 OK)**: Matrix of available features, risk levels, and operational flags (e.g. `arbitrary_shell_execution: false`).

### 2.5 Agent Goal Dispatch
* **`POST /api/v1/agent/query`**
  * **Auth**: Bearer token
  * **Request**:
    ```json
    {
      "query": "List files in workspace and verify layout",
      "require_approval": false,
      "max_steps": 10
    }
    ```
  * **Response (200 OK)**: Returns session ID, execution status, response text with verified observations, and step count.

### 2.6 Emergency Workstation Lock
* **`POST /api/v1/emergency/lock`**
  * **Auth**: Bearer token
  * **Parameters**: `?dry_run=true|false`
  * **Response (200 OK)**: Immediate Win32 `LockWorkStation` invocation status.

### 2.7 Device Management
* **`GET /api/v1/devices`**: List registered devices.
* **`POST /api/v1/devices/{device_id}/revoke`**: Mark device revoked.

---

## 3. WebSocket Streaming Channel

* **Endpoint**: `/ws/v1/events?token=<token>`
* **Event Types**:
  * `welcome`: Initial connection confirmation.
  * `telemetry`: Periodic hardware metric broadcast.
  * `agent_plan`: Plan generation updates.
  * `agent_step`: Step completion updates.
  * `audit`: Real-time audit log event.
  * `alert`: Emergency lock or policy alert.
