# LOA Agent - Slice 2 Implementation Guide

> **Last Updated:** December 12, 2025  
> **Status:** Slice 2 ✅ Complete

---

## Slice 2: Document Coverage + Doc Gap Analysis (Full Mode)

### Goal
Integrate **Rack & Stack (R&S)** via TaskTile API to retrieve classified document manifest and identify missing documents against questionnaire requirements.

---

## Implementation Summary

| Component | File | Status | Description |
|-----------|------|--------|-------------|
| **State Models** | `state.py` | ✅ | Added `DocCoverage`, `DocCoverageItem` dataclasses |
| **TaskTile Client** | `tools/tasktile_client.py` | ✅ | Full TaskTile API: auth, upload, job creation |
| **R&S Submission** | `tools/rack_and_stack.py` | ✅ | eFolder → TaskTile upload workflow |
| **Doc Coverage Tool** | `tools/fetch_doc_coverage.py` | ✅ | Manifest parsing, doc type normalization |
| **Gap Analyzer Phase 2** | `tools/gap_analyzer.py` | ✅ | Added `analyze_doc_gaps()`, `merge_gap_results()` |
| **Doc Type Mapping** | `config/doc_type_mapping.yaml` | ✅ | R&S category_name → logical doc type |
| **Webhook Handler** | `backend/routes/webhooks.py` | ✅ | Receives R&S job manifests |
| **Coverage Analyzer** | `tools/doc_coverage.py` | ✅ | Standalone coverage analysis helper |
| **Agent Full Mode** | `agent.py` | ✅ | Full mode with data + doc gap analysis |

---

## Architecture

### End-to-End Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      RACK & STACK INTEGRATION FLOW                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. SUBMIT                                                                  │
│     ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│     │  Encompass   │───▶│   Download   │───▶│   Upload to  │               │
│     │   eFolder    │    │   PDF bytes  │    │   TaskTile   │               │
│     └──────────────┘    └──────────────┘    └──────────────┘               │
│                                                     │                       │
│                                                     ▼                       │
│     ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│     │   Create     │◀───│   Complete   │◀───│   Presigned  │               │
│     │   R&S Job    │    │   Upload     │    │   PUT to S3  │               │
│     └──────────────┘    └──────────────┘    └──────────────┘               │
│            │                                                                │
│            ▼                                                                │
│  2. PROCESS (TaskTile Pipeline)                                             │
│     ┌─────────────────────────────────────────────────────────────────┐    │
│     │ ai:pagegen → hil:splicer → hil:splitter → ai:ocr_partial →     │    │
│     │ ai:classify → hil:classify → ai:indexing → hil:indexing        │    │
│     └─────────────────────────────────────────────────────────────────┘    │
│            │                                                                │
│            ▼                                                                │
│  3. RECEIVE                                                                 │
│     ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│     │   Webhook    │───▶│    Parse     │───▶│   Analyze    │               │
│     │   Manifest   │    │   Manifest   │    │   Coverage   │               │
│     └──────────────┘    └──────────────┘    └──────────────┘               │
│                                                     │                       │
│                                                     ▼                       │
│  4. ANALYZE                                                                 │
│     ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│     │   Doc Gap    │───▶│    Merge     │───▶│   Needs List │               │
│     │   Analysis   │    │   Results    │    │   Output     │               │
│     └──────────────┘    └──────────────┘    └──────────────┘               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. State Models (`state.py`)

```python
@dataclass
class DocCoverageItem:
    """Single document from R&S manifest."""
    doc_id: str                          # R&S document ID
    blob_id: str                         # R&S blob ID (source PDF)
    doc_type: str                        # Normalized type (W2, PAYSTUB, etc.)
    category_id: Optional[int] = None    # R&S category ID
    category_name: Optional[str] = None  # R&S category name
    category_source: Optional[str] = None  # "ai" or "hil"
    page_count: Optional[int] = None
    confidence: Optional[float] = None
    borrower_first_name: Optional[str] = None
    borrower_last_name: Optional[str] = None
    source_bucket: Optional[str] = None
    source_key: Optional[str] = None
    has_exceptions: bool = False
    exceptions: Dict[str, bool] = field(default_factory=dict)

@dataclass  
class DocCoverage:
    """Document coverage from Rack & Stack manifest."""
    loan_id: str
    job_id: Optional[str] = None
    job_status: Optional[str] = None  # "success" | "failed" | "pending"
    documents: List[DocCoverageItem] = field(default_factory=list)
    coverage_by_type: Dict[str, List[str]] = field(default_factory=dict)
    
    # Quick coverage flags
    has_w2: bool = False
    has_paystubs: bool = False
    has_tax_returns: bool = False
    has_bank_statements: bool = False
    has_purchase_contract: bool = False
    has_government_id: bool = False
    
    def has_doc_type(self, doc_type: str) -> bool:
        """Check if a doc type is present in coverage."""
```

---

### 2. TaskTile Client (`tools/tasktile_client.py`)

**Key Methods:**

| Method | Purpose |
|--------|---------|
| `_get_access_token()` | OAuth2 client credentials flow |
| `upload_pdf_bytes()` | Full upload flow: initiate → PUT → complete |
| `create_job()` | Create R&S pipeline job with retry logic |

**Configuration (env vars):**
```bash
TASKTILE_API_BASE_URL=https://tasktile.staging.cybersoftbpo.ai/api
TASKTILE_CLIENT_ID=your-client-id
TASKTILE_CLIENT_SECRET=your-client-secret
TASKTILE_CATEGORIES_URL=https://sbiqai.staging.cybersoftbpo.ai/api/workspaces/1/categories
```

**Key Implementation Notes:**
- Uses `rack_and_stack_v1` pipeline (not `rack-and-stack` as in original docs)
- Implements retry logic for pending virus scans (up to 6 retries, 10s each)
- Token caching with 5-minute buffer before expiry

---

### 3. R&S Submission (`tools/rack_and_stack.py`)

**Main Function:**
```python
async def submit_efolder_to_rack_and_stack(
    loan_id: str,
    max_documents: Optional[int] = None,
    document_ids: Optional[List[str]] = None,
) -> RackAndStackSubmission
```

**Workflow:**
1. Fetch eFolder documents from Encompass
2. Download PDF bytes for each document
3. Upload to TaskTile via presigned URLs
4. Wait for virus scan completion
5. Create R&S job with all upload IDs

**CLI Usage:**
```bash
cd agents/loan-officer-assistant
python tools/rack_and_stack.py 59d7a711-70f4-4b12-a3b5-bbefb3ff7dbc 5
```

---

### 4. Doc Type Mapping (`config/doc_type_mapping.yaml`)

Maps R&S category names to normalized doc types:

```yaml
mappings:
  - category_patterns: ["W-2", "W2", "w-2", "w2"]
    doc_type: "W2"
    applies_to: "borrower"
    critical: true
    
  - category_patterns: ["Pay Stub", "Paystub", "Pay stub"]
    doc_type: "PAYSTUB"
    applies_to: "borrower"
    critical: true
    
  # ... 40+ patterns for income, assets, identity, property docs
```

**Critical Document Types:**
- W2, PAYSTUB, TAX_RETURN, BANK_STATEMENT
- GOVERNMENT_ID, PURCHASE_CONTRACT, APPRAISAL
- DIVORCE_DECREE, SEPARATION_AGREEMENT, GIFT_LETTER

---

### 5. Doc Coverage Fetcher (`tools/fetch_doc_coverage.py`)

**Main Function:**
```python
async def fetch_doc_coverage(
    loan_id: str,
    efolder_docs: Optional[List[EFolderDoc]] = None,
    refresh: bool = False,
) -> Optional[DocCoverage]
```

**Workflow:**
1. Check for cached manifest in `backend/output/tasktile_manifests/`
2. If `refresh=True`, trigger new R&S job
3. Parse manifest into `DocCoverage` structure
4. Map categories to normalized doc types

---

### 6. Gap Analyzer Phase 2 (`tools/gap_analyzer.py`)

**New Functions:**

```python
def analyze_doc_gaps(
    loan_facts: LoanFacts,
    doc_coverage: Optional[DocCoverage],
    questionnaire: Optional[Dict] = None
) -> NeedsListResult:
    """Analyze document coverage for gaps (Phase 2)."""

def merge_gap_results(
    data_gaps: NeedsListResult, 
    doc_gaps: NeedsListResult
) -> NeedsListResult:
    """Merge data and doc gap results into single result."""
```

**Document Gap Detection:**
- Checks `required_documents` from questionnaire
- Evaluates conditional requirements (e.g., "If separated, need Separation Agreement")
- Adds core document checks (paystubs, bank statements, government ID)

---

### 7. Webhook Handler (`backend/routes/webhooks.py`)

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhooks/tasktile` | POST | Receive manifest from TaskTile |
| `/webhooks/tasktile/manifests` | GET | List all received manifests |
| `/webhooks/tasktile/manifests/{job_id}` | GET | Get specific manifest |
| `/webhooks/tasktile/manifests/{job_id}/coverage` | GET | Analyze coverage for manifest |

**Webhook Handler Flow:**
1. Receive POST with manifest JSON
2. Log job info and document count
3. Save manifest to `backend/output/tasktile_manifests/`
4. Run coverage analysis
5. Return acknowledgment

**Manifest Storage:**
```
backend/output/tasktile_manifests/
├── manifest_0fb43008_20251212_102729.json
├── manifest_abc12345_20251212_110530.json
└── ...
```

---

### 8. Agent Full Mode (`agent.py`)

**Updated Entry Point:**
```python
async def run_loan_officer_agent(
    loan_id: str,
    mode: str = "fast",  # "fast" | "full" | "refresh_docs"
    include_write_proposals: bool = False,
) -> LOAResult
```

**Mode Behaviors:**

| Mode | Phase 1 (Data) | Phase 2 (Docs) | R&S Behavior |
|------|----------------|----------------|--------------|
| `fast` | ✅ | ❌ | Skip |
| `full` | ✅ | ✅ | Use cached manifest |
| `refresh_docs` | ✅ | ✅ | Trigger new R&S job |

---

## Testing

### Unit Test Results

```
Testing imports...
✓ State models imported
✓ fetch_doc_coverage imported
✓ gap_analyzer imported

Testing category mapping...
✓ Category mapping works

Testing DocCoverage model...
✓ DocCoverage model works

Testing manifest parsing...
✓ Manifest parsing works

Testing doc gap analysis...
  Doc gaps found: 10
✓ Doc gap analysis works

ALL SLICE 2 TESTS PASSED!
```

### Manual Testing

**1. Submit R&S Job:**
```bash
cd agents/loan-officer-assistant
python tools/rack_and_stack.py 59d7a711-70f4-4b12-a3b5-bbefb3ff7dbc 5
```

**2. Check Webhook (requires backend running):**
```bash
# List manifests
curl http://localhost:8000/webhooks/tasktile/manifests

# Get coverage analysis
curl http://localhost:8000/webhooks/tasktile/manifests/0fb43008/coverage
```

**3. Run Full Agent:**
```bash
python agent.py 59d7a711-70f4-4b12-a3b5-bbefb3ff7dbc full
```

---

## Known Issues & Notes

### Pipeline Name
- The API docs show `rack-and-stack` but the actual working pipeline is `rack_and_stack_v1`
- This was discovered through testing and confirmed working

### HIL Steps
- The R&S pipeline includes human-in-the-loop (HIL) steps:
  - `hil:splicer`, `hil:splitter`, `hil:classify`, `hil:indexing`
- These require manual completion in TaskTile's UI before the manifest is sent
- Job submission is immediate, but manifest delivery depends on HIL completion

### Webhook URL
- Must be publicly accessible for TaskTile to POST to
- For local development, use ngrok or deploy to staging environment
- Current webhook URL is configured in TaskTile client registration

---

## Environment Variables

```bash
# TaskTile / Rack & Stack API
TASKTILE_API_BASE_URL=https://tasktile.staging.cybersoftbpo.ai/api
TASKTILE_CLIENT_ID=your-client-id
TASKTILE_CLIENT_SECRET=your-client-secret
TASKTILE_CATEGORIES_URL=https://sbiqai.staging.cybersoftbpo.ai/api/workspaces/1/categories
TASKTILE_WEBHOOK_URL=https://your-system.com/webhooks/tasktile
```

---

## File Structure After Slice 2

```
agents/loan-officer-assistant/
├── agent.py                         # Entry point (updated for full mode)
├── state.py                         # + DocCoverage, DocCoverageItem
├── config/
│   ├── field_mapping.yaml           # Slice 1: Encompass field → LoanFacts
│   └── doc_type_mapping.yaml        # Slice 2: R&S category → doc type
├── tools/
│   ├── fetch_loan_context.py        # Slice 1: Encompass API
│   ├── tasktile_client.py           # Slice 2: TaskTile API client
│   ├── rack_and_stack.py            # Slice 2: eFolder → R&S submission
│   ├── fetch_doc_coverage.py        # Slice 2: Manifest parsing
│   ├── doc_coverage.py              # Slice 2: Coverage analysis helper
│   └── gap_analyzer.py              # + analyze_doc_gaps(), merge_gap_results()
└── docs/
    ├── SLICE_1_IMPLEMENTATION.md
    ├── SLICE_2_IMPLEMENTATION.md    # This file
    └── tasktile-api-rack-and-stack.md

backend/
├── routes/
│   └── webhooks.py                  # TaskTile webhook handler
└── output/
    └── tasktile_manifests/          # Stored manifests
```

---

## Definition of Done ✅

| Requirement | Status |
|-------------|--------|
| `tasktile_client.py` authenticates with TaskTile | ✅ |
| `parse_manifest()` correctly parses R&S webhook JSON | ✅ |
| `fetch_doc_coverage` returns valid `DocCoverage` | ✅ |
| `analyze_doc_gaps` returns correct doc gap items | ✅ |
| Doc type mapping covers common mortgage documents | ✅ |
| Full mode with data + doc gaps merged | ✅ |
| Error handling for R&S API failures | ✅ |
| Webhook receives and stores manifests | ✅ |

---

## Next Steps (Slice 3)

1. **LLM Presentation Layer** - Generate human-readable summaries
2. Prompt templates for gap analysis output
3. Prioritization and action item generation
4. Write proposal generation (Slice 4)

