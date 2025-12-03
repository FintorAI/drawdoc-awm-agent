# DrawDoc Agent

A full-stack loan document verification system that automates field extraction, verification, and correction for mortgage loans. Built with a Next.js frontend, FastAPI backend, and multi-agent AI orchestration.

## Overview

DrawDoc Agent processes loan documents through an intelligent pipeline:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Orchestrator Agent                               │
│                                                                          │
│   1. Preparation Agent    2. Verification Agent    3. Orderdocs Agent   │
│   ├─ Downloads docs       ├─ Compares values       ├─ Checks fields     │
│   ├─ OCR extraction       ├─ Identifies gaps       └─ Reports status    │
│   └─ Field mapping        └─ Writes corrections                         │
│                                                                          │
│                      📊 Results + Live Progress                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Features

- **🔒 Safe Demo Mode** — Dry run enabled by default, no writes to production Encompass
- **🤖 Multi-Agent Pipeline** — Sequential execution with retry logic and exponential backoff
- **📊 Live Progress Tracking** — Real-time status updates via web dashboard
- **📄 Document OCR** — Powered by LandingAI for accurate field extraction
- **✅ Smart Verification** — Compares extracted values against Encompass and auto-corrects
- **📋 Comprehensive Reporting** — JSON output + human-readable summaries

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Frontend** | Next.js 16, React 19, TailwindCSS, Radix UI |
| **Backend** | FastAPI, Uvicorn, Pydantic |
| **AI Agents** | LangChain, Anthropic Claude |
| **Document Processing** | LandingAI OCR, python-docx |
| **State Management** | TanStack Query (React Query) |

## Project Structure

```
drawdoc-awm-agent/
├── frontend/               # Next.js web application
│   ├── src/
│   │   ├── app/           # Pages (runs, dashboard, documents)
│   │   ├── components/    # UI components (runs, layout, ui)
│   │   ├── hooks/         # React hooks
│   │   ├── lib/           # API client, utilities
│   │   └── types/         # TypeScript definitions
│   └── package.json
│
├── backend/               # FastAPI server
│   ├── main.py           # API endpoints
│   ├── agent_runner.py   # Agent execution manager
│   ├── services.py       # Run management
│   ├── models.py         # Pydantic models
│   └── output/           # Run result files
│
├── agents/drawdocs/       # AI agent system
│   ├── orchestrator_agent.py   # Main controller
│   ├── status_writer.py        # Progress tracking
│   └── subagents/
│       ├── preparation_agent/  # Document extraction
│       ├── verification_agent/ # Value verification
│       └── orderdocs_agent/    # Completeness check
│
├── docs/                  # Technical documentation
├── requirements.txt       # Python dependencies
└── env.example           # Environment template
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm or pnpm

### 1. Clone and Setup Environment

```bash
# Clone repository
git clone <repository-url>
cd drawdoc-awm-agent

# Copy environment template
cp env.example .env
# Edit .env with your credentials (Encompass, LandingAI)
```

### 2. Install Dependencies

```bash
# Backend dependencies
pip install -r requirements.txt

# Frontend dependencies
cd frontend
npm install
```

### 3. Start Development Servers

```bash
# Terminal 1: Start backend (port 8000)
cd backend
python main.py

# Terminal 2: Start frontend (port 3000)
cd frontend
npm run dev
```

### 4. Access the Application

Open [http://localhost:3000](http://localhost:3000) to view the dashboard.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/runs` | List all runs |
| `GET` | `/api/runs/{run_id}` | Get run details |
| `POST` | `/api/runs` | Start new run |

## Usage

### Running via Web UI

1. Navigate to the **Runs** page
2. Click **New Run**
3. Enter the Loan ID (Encompass GUID)
4. Select demo mode (recommended for testing)
5. Click **Start Run**
6. Monitor real-time progress in the timeline

### Running via CLI

```bash
# Demo mode (safe - no actual writes)
python agents/drawdocs/orchestrator_agent.py \
  --loan-id "387596ee-7090-47ca-8385-206e22c9c9da" \
  --output results.json

# Production mode (⚠️ writes to Encompass)
python agents/drawdocs/orchestrator_agent.py \
  --loan-id "387596ee-7090-47ca-8385-206e22c9c9da" \
  --production \
  --output results.json
```

### Running Programmatically

```python
from agents.drawdocs.orchestrator_agent import run_orchestrator

results = run_orchestrator(
    loan_id="387596ee-7090-47ca-8385-206e22c9c9da",
    demo_mode=True  # Safe testing
)

print(results["summary_text"])
```

## Environment Variables

### Required

```bash
# Encompass API
ENCOMPASS_ACCESS_TOKEN=your_token
ENCOMPASS_API_BASE_URL=https://api.elliemae.com
ENCOMPASS_CLIENT_ID=your_client_id
ENCOMPASS_CLIENT_SECRET=your_client_secret
ENCOMPASS_INSTANCE_ID=your_instance_id
ENCOMPASS_USERNAME=your_username
ENCOMPASS_PASSWORD=your_password

# LandingAI (document OCR)
LANDINGAI_API_KEY=your_api_key
```

### Optional

```bash
# Demo/Production Mode
ENABLE_ENCOMPASS_WRITES=false  # Set true for production

# Backend Configuration
HOST=0.0.0.0
PORT=8000
OUTPUT_DIR=./backend/output

# Development
AI_DEBUG_MODE=false
```

## Agent Pipeline

### 1. Preparation Agent
- Downloads loan documents from Encompass
- Extracts field values using OCR (LandingAI)
- Maps extracted values to Encompass field IDs

### 2. Verification Agent
- Compares prep values against current Encompass data
- Identifies discrepancies
- Writes corrections (or logs them in demo mode)

### 3. Orderdocs Agent
- Checks all required fields are populated
- In demo mode: overlays corrections to simulate post-write state
- Reports completeness status

## Output

### JSON Results

```json
{
  "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
  "execution_timestamp": "2025-11-27T10:30:00",
  "demo_mode": true,
  "agents": {
    "preparation": { "status": "success", "elapsed_seconds": 245.5 },
    "verification": { "status": "success", "elapsed_seconds": 315.2 },
    "orderdocs": { "status": "success", "elapsed_seconds": 12.8 }
  },
  "corrected_fields_summary": [
    { "field_id": "4008", "corrected_value": "John Smith", "source_document": "ID.pdf" }
  ]
}
```

### Human-Readable Summary

```
================================================================================
ORCHESTRATOR EXECUTION SUMMARY
================================================================================
Loan ID: 387596ee-7090-47ca-8385-206e22c9c9da
Mode: DEMO (no actual writes)

[PREPARATION AGENT] ✓ Success
- Documents processed: 9/172
- Fields extracted: 16

[VERIFICATION AGENT] ✓ Success
- Corrections needed: 11

[ORDERDOCS AGENT] ✓ Success
- Fields with values: 150/150

OVERALL STATUS: SUCCESS
================================================================================
```

## Documentation

- **[Orchestrator Agent](agents/drawdocs/README.md)** — Architecture, configuration, usage
- **[Preparation Agent](agents/drawdocs/subagents/preparation_agent/README.md)** — Document extraction
- **[Verification Agent](agents/drawdocs/subagents/verification_agent/README.md)** — Field verification
- **[Orderdocs Agent](agents/drawdocs/subagents/orderdocs_agent/README.md)** — Completeness checking

## Development

### Project Scripts

```bash
# Backend
cd backend && python main.py          # Start API server
cd agents/drawdocs && python test_orchestrator.py  # Run tests

# Frontend
cd frontend && npm run dev           # Development server
cd frontend && npm run build         # Production build
cd frontend && npm run lint          # Lint check
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: copilotagent` | Run `pip install -r requirements.txt` |
| `403 Forbidden` from Encompass | Check API credentials in `.env` |
| Frontend can't connect to backend | Ensure backend is running on port 8000 |
| OCR extraction fails | Verify `LANDINGAI_API_KEY` is set |

## License

Proprietary - All rights reserved.
