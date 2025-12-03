# DrawDocs Agent System

A comprehensive multi-agent system for automated loan document processing, field extraction, verification, and closing document generation in Encompass.

## Overview

The DrawDocs Agent System orchestrates 4 specialized sub-agents in a sequential pipeline to:

1. **Extract** field values from loan documents (PDFs)
2. **Update** Encompass fields with extracted data
3. **Verify** field values against SOP rules
4. **Order** closing documents through Encompass

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DRAWDOCS AGENT PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐ │
│   │ Preparation  │───►│   Drawcore   │───►│ Verification │───►│ OrderDocs│ │
│   │    Agent     │    │    Agent     │    │    Agent     │    │   Agent  │ │
│   └──────────────┘    └──────────────┘    └──────────────┘    └──────────┘ │
│         │                   │                   │                   │       │
│         ▼                   ▼                   ▼                   ▼       │
│   Extract fields      Write fields to     Verify against     Run Mavent    │
│   from documents      Encompass (bulk)    SOP rules &        & Order Docs  │
│                                           correct errors                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Sub-Agents

### 1. Preparation Agent (`subagents/preparation_agent/`)

**Purpose**: Extract field values from loan documents using OCR and AI.

**Workflow**:
1. List all documents in the loan's eFolder
2. Filter documents by type (ID, Title Report, Appraisal, LE, 1003, etc.)
3. Download documents via MCP server (with EncompassConnect fallback)
4. Extract entities using LandingAI OCR
5. Map extracted values to Encompass field IDs using CSV-driven schemas

**Key Features**:
- Two-tier document download (MCP → EncompassConnect fallback)
- Parallel document processing with ThreadPoolExecutor
- CSV-driven extraction schemas from `DrawingDoc Verifications.csv`
- Timeout and retry handling for OCR requests

**Output** (`doc_context`):
```json
{
  "loan_id": "...",
  "field_mappings": {
    "4000": "John",           // Borrower First Name
    "4002": "Smith",          // Borrower Last Name
    "1109": "250000",         // Loan Amount
    "356": "300000"           // Appraised Value
  },
  "extracted_entities": { ... },
  "documents_processed": 15,
  "total_documents_found": 244
}
```

---

### 2. Drawcore Agent (`subagents/drawcore_agent/`)

**Purpose**: Write extracted field values to Encompass in bulk across 5 phases.

**Phases**:
| Phase | Name | Fields |
|-------|------|--------|
| 1 | Borrower & LO | Borrower names, vesting, loan officer info |
| 2 | Contacts & Vendors | Title company, escrow, lenders, settlement agents |
| 3 | Property & Program | FHA/VA/USDA case numbers, property details |
| 4 | Financial Setup | Terms, rates, fees, escrow, itemization |
| 5 | Closing Disclosure | CD pages with final numbers |

**Workflow**:
1. Read current Encompass field values
2. Compare against extracted values from Prep Agent
3. Update fields that differ (or flag discrepancies)
4. Log all actions for audit trail

**Key Features**:
- Two-tier field I/O (MCP → EncompassConnect fallback)
- Dry run mode (no actual writes)
- Phase-by-phase execution with individual status tracking

**Output**:
```json
{
  "phases": {
    "phase_1": { "status": "success", "fields_updated": 12 },
    "phase_2": { "status": "success", "fields_updated": 8 },
    ...
  },
  "summary": {
    "total_fields_processed": 150,
    "total_fields_updated": 45,
    "phases_completed": 5
  }
}
```

---

### 3. Verification Agent (`subagents/verification_agent/`)

**Purpose**: Verify field values against SOP rules and correct discrepancies.

**Workflow**:
1. Load SOP rules from `sop_rules.json` (67 pages of rules)
2. Load field mappings from `DrawingDoc Verifications.csv` (193 fields)
3. For each field extracted by Prep Agent:
   - Read current Encompass value
   - Compare against extracted value
   - Apply SOP validation rules
   - Write corrections if needed

**Key Features**:
- LLM-powered (Claude) for intelligent verification
- SOP rule enforcement
- Detailed correction logging with reasons
- Demo mode support (log-only, no writes)

**Output**:
```json
{
  "status": "success",
  "fields_validated": 16,
  "corrections_needed": 3,
  "corrections": [
    {
      "field_id": "4002",
      "field_name": "borrower_last_name",
      "old_value": "Sorenson",
      "corrected_value": "Sorensen",
      "reason": "Document shows 'Sorensen' on ID"
    }
  ]
}
```

---

### 4. OrderDocs Agent (`subagents/orderdocs_agent/`)

**Purpose**: Run compliance checks and order closing documents.

**3-Step Pipeline**:
| Step | Name | API Endpoint |
|------|------|--------------|
| 1 | Mavent Compliance Check | `POST /encompassdocs/v1/documentAudits/closing` |
| 2 | Order Documents | `POST /encompassdocs/v1/documentOrders/closing` |
| 3 | Deliver Documents | `POST /encompassdocs/v1/documentOrders/closing/{id}/delivery` |

**Workflow**:
1. **Mavent Check**: Run loan audit for compliance issues
2. **Order Docs**: Generate closing document package using audit ID
3. **Deliver**: Send documents to eFolder, email, or print

**Key Features**:
- Polling for async operations (audit & order completion)
- Multiple delivery methods (eFolder, Email, Print)
- Dry run mode for testing

**Output**:
```json
{
  "steps": {
    "mavent_check": {
      "audit_id": "abc-123",
      "status": "Completed",
      "compliance_issues": 0
    },
    "order_documents": {
      "doc_set_id": "xyz-789",
      "status": "Completed",
      "documents": [...]
    },
    "deliver_documents": {
      "status": "Success",
      "delivery_method": "eFolder"
    }
  }
}
```

---

## Primitive Tools (`tools/primitives.py`)

Shared foundational operations used by all agents:

### Loan Context & Workflow
| Function | Description |
|----------|-------------|
| `get_loan_context(loan_id)` | Get comprehensive loan info (fields, milestones, flags) |
| `get_loan_milestones(loan_id)` | Get all milestones for a loan |
| `update_milestone(loan_id, name, status)` | Update milestone status |

### Document Operations
| Function | Description |
|----------|-------------|
| `list_loan_documents(loan_id)` | List all documents in eFolder (two-tier fallback) |
| `download_document_from_efolder(loan_id, doc_id, save_path)` | Download document (two-tier fallback) |
| `extract_entities_from_docs(loan_id, doc_types, extraction_mode)` | Extract entities using OCR |

### Field I/O
| Function | Description |
|----------|-------------|
| `read_fields(loan_id, field_ids)` | Read multiple fields (two-tier fallback) |
| `write_fields(loan_id, updates)` | Write multiple fields (two-tier fallback) |

### Compliance & Validation
| Function | Description |
|----------|-------------|
| `run_compliance_check(loan_id, check_type)` | Run Mavent or other compliance checks |

### Issue Logging
| Function | Description |
|----------|-------------|
| `log_issue(loan_id, issue_type, message, field_id)` | Log issues for audit trail |

### Two-Tier Fallback Pattern

All document and field operations use a two-tier approach:

```
┌─────────────────────────────────────────┐
│           Tier 1: MCP Server            │
│  (Uses server's OAuth credentials)      │
└────────────────┬────────────────────────┘
                 │ If 401/error
                 ▼
┌─────────────────────────────────────────┐
│       Tier 2: EncompassConnect          │
│  (Uses local .env credentials)          │
└─────────────────────────────────────────┘
```

---

## Orchestrator (`orchestrator_agent.py`)

The orchestrator manages the sequential execution of all 4 agents:

```python
from orchestrator_agent import run_orchestrator

results = run_orchestrator(
    loan_id="387596ee-7090-47ca-8385-206e22c9c9da",
    document_types=["ID", "Title Report", "Appraisal", "LE", "1003"],
    demo_mode=True  # Default: no actual writes
)
```

### Execution Flow

```
1. PREPARATION AGENT
   ├── List documents → Filter by type → Download → Extract → Map to fields
   └── Output: doc_context with field_mappings

2. DRAWCORE AGENT
   ├── Input: doc_context from Prep Agent
   ├── Phase 1-5: Read current values → Compare → Update fields
   └── Output: fields_updated count, issues_logged

3. VERIFICATION AGENT
   ├── Input: doc_context from Prep Agent
   ├── For each field: Read Encompass → Compare → Apply SOP rules → Correct
   └── Output: corrections list with reasons

4. ORDERDOCS AGENT
   ├── Step 1: Mavent compliance check
   ├── Step 2: Order closing documents
   ├── Step 3: Deliver to eFolder
   └── Output: audit_id, doc_set_id, delivery status
```

---

## Configuration

### Environment Variables

```bash
# Encompass API (required)
ENCOMPASS_API_BASE_URL=https://api.elliemae.com  # or concept.api.elliemae.com for sandbox
ENCOMPASS_USERNAME=your_username
ENCOMPASS_PASSWORD=your_password
ENCOMPASS_CLIENT_ID=your_client_id
ENCOMPASS_CLIENT_SECRET=your_client_secret
ENCOMPASS_INSTANCE_ID=your_instance_id

# Optional
ENCOMPASS_ACCESS_TOKEN=your_token
ENCOMPASS_SUBJECT_USER_ID=your_subject_user_id

# LandingAI for OCR (required for Prep Agent)
LANDINGAI_API_KEY=your_landingai_key

# Feature flags
ENABLE_ENCOMPASS_WRITES=false  # Set to 'true' for production writes
DRY_RUN=true                    # Set by orchestrator for demo mode
```

### Document Types

Supported document types for filtering:
- `ID` - Driver's license, passport, etc.
- `Title Report` - Title commitment, preliminary title
- `Appraisal` - Property appraisal documents
- `LE` - Loan Estimate
- `1003` - Uniform Residential Loan Application
- `CD` - Closing Disclosure
- `W2` - W-2 wage statements
- `Paystub` - Pay stubs

---

## Frontend Integration

The DrawDocs system includes a Next.js frontend for monitoring runs:

### Features
- **Dashboard**: System overview with agent performance metrics
- **Runs List**: View all pipeline runs with status
- **Run Detail**: Deep-dive into specific runs with:
  - Overview tab: Configuration, timing, key metrics
  - Timeline tab: Real-time log stream
  - **Report tab**: Final report with flagged items and field changes
  - Documents tab: PDF viewer (coming soon)
  - Fields tab: Extracted data viewer (coming soon)

### Running the Frontend

```bash
# Terminal 1: Backend
cd /Users/antonboquer/Documents/Fintor/drawdoc-awm-agent
source venv/bin/activate
python backend/main.py

# Terminal 2: Frontend
cd /Users/antonboquer/Documents/Fintor/drawdoc-awm-agent/frontend
npm install
npm run dev
```

Then open http://localhost:3000

---

## Testing

### CLI Test

```bash
cd /Users/antonboquer/Documents/Fintor/drawdoc-awm-agent
source venv/bin/activate

# Run full pipeline test
python agents/drawdocs/test_orchestrator_full_pipeline.py
```

### Output Location

Run results are saved to:
```
backend/output/{loan_id}_{timestamp}_results.json
```

---

## File Structure

```
agents/drawdocs/
├── orchestrator_agent.py          # Main orchestrator
├── status_writer.py               # Live status updates for frontend
├── README.md                      # This file
│
├── tools/
│   ├── primitives.py              # Shared primitive operations
│   └── __init__.py
│
├── subagents/
│   ├── preparation_agent/
│   │   ├── preparation_agent.py   # Document extraction agent
│   │   ├── tools/
│   │   │   ├── extraction_schemas.py
│   │   │   ├── field_mappings.py
│   │   │   └── csv_loader.py
│   │   └── example_input.json
│   │
│   ├── drawcore_agent/
│   │   ├── drawcore_agent.py      # Field update agent
│   │   └── phases/
│   │       ├── phase1_borrower_lo.py
│   │       ├── phase2_contacts.py
│   │       ├── phase3_property.py
│   │       ├── phase4_financial.py
│   │       └── phase5_cd.py
│   │
│   ├── verification_agent/
│   │   ├── verification_agent.py  # SOP verification agent
│   │   ├── config/
│   │   │   ├── sop_rules.json
│   │   │   └── field_document_mapping.py
│   │   └── tools/
│   │       ├── verification_tools.py
│   │       └── field_lookup_tools.py
│   │
│   └── orderdocs_agent/
│       └── orderdocs_agent.py     # Mavent & closing docs agent
│
└── test_orchestrator_full_pipeline.py
```

---

## Demo Mode vs Production Mode

### Demo Mode (Default)
- `demo_mode=True` in orchestrator
- No actual writes to Encompass
- Drawcore logs field updates but doesn't write
- Verification logs corrections but doesn't write
- OrderDocs returns dry-run IDs
- Safe for testing on production data

### Production Mode
- `demo_mode=False` in orchestrator
- `ENABLE_ENCOMPASS_WRITES=true` in environment
- **Actually writes** to Encompass
- ⚠️ Use with caution!

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `401 Unauthorized` | Check Encompass credentials in `.env`. Ensure correct environment (api vs concept). |
| `Failed to open PDF` | Document may be corrupted or metadata-only in test environment. |
| `No module named 'copilotagent'` | Run `pip install -r requirements.txt` in venv. |
| `MCP HTTP client not available` | Ensure `encompass-mcp-server` is at the same level as this project. |
| `No field mappings found` | Select specific document types instead of "All Documents". |

### Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## API Reference

### Orchestrator

```python
run_orchestrator(
    loan_id: str,                    # Required: Encompass loan GUID
    document_types: List[str] = None, # Optional: Filter document types
    demo_mode: bool = True,          # Default: no actual writes
    max_retries: int = 2,            # Retry attempts per agent
    output_file: str = None          # Optional: Save results to file
) -> Dict[str, Any]
```

### Preparation Agent

```python
process_loan_documents(
    loan_id: str,
    document_types: List[str] = None,
    dry_run: bool = True
) -> Dict[str, Any]
```

### Drawcore Agent

```python
run_drawcore_agent(
    loan_id: str,
    doc_context: Dict[str, Any],     # Output from Prep Agent
    dry_run: bool = True,
    phases_to_run: List[int] = None  # Optional: [1,2,3,4,5]
) -> Dict[str, Any]
```

### Verification Agent

```python
run_verification_agent(
    loan_id: str,
    prep_output: Dict[str, Any],     # Output from Prep Agent
    dry_run: bool = True
) -> Dict[str, Any]
```

### OrderDocs Agent

```python
run_orderdocs_agent(
    loan_id: str,
    audit_type: str = "closing",
    delivery_method: str = "eFolder",
    dry_run: bool = True
) -> Dict[str, Any]
```

---

## License

Same as parent project.
