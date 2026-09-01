# SIH26122 | KaryaSetu

## Current Phase
**Phase 01 — Project Foundation**

## Purpose
This project provides an intelligent data capture and schedule-linking layer for infrastructure project management (Oil India Limited). It converts unstructured field execution reports into structured, schedule-linked actual progress using semantic matching and validation.

## Architecture
```text
React
 ↓
FastAPI
 ↓
PostgreSQL (pgvector)
```

## Prerequisites
* Git
* Node.js (v24+)
* npm
* Python (3.14+)
* Docker & Docker Compose (Note: Currently missing in the primary environment)

## Setup
1. Clone the repository.
2. Setup environment variables by copying `.env.example` in `backend/` to `.env`.

## Running locally

### 1. Database
```bash
docker-compose up -d
```
*(Requires Docker)*

### 2. Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

## Testing
To run backend tests:
```bash
cd backend
pytest
```

## Phase Limitations
**Currently in Phase 01.**
* AI, OCR, and Activity matching are **NOT** implemented yet.
* Only the project foundation, health endpoints, and database connection checks are active.
