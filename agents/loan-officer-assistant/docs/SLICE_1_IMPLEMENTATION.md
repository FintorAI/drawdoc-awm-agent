# LOA Agent - Slice 1 Implementation Guide

> **Last Updated:** December 11, 2025  
> **Status:** Slice 1 ✅ Complete | Slice 2 🔄 Ready to Start

---

## Slice 1: Loan Context + Data Gap Analysis (Fast Mode) ✅

### Goal
Retrieve loan data from Encompass and identify missing/invalid fields against questionnaire requirements.

### Implementation Summary

| Component | File | Status | Description |
|-----------|------|--------|-------------|
| **State Models** | `state.py` | ✅ | `LoanFacts`, `BorrowerFacts`, `PropertyFacts`, `GapItem`, `NeedsListResult` |
| **Loan Context Tool** | `tools/fetch_loan_context.py` | ✅ | Encompass API integration, field normalization |
| **Gap Analyzer** | `tools/gap_analyzer.py` | ✅ | Phase 1 data completeness analysis |
| **Field Mapping** | `config/field_mapping.yaml` | ✅ | 100+ Encompass field ID mappings |
| **Entry Point** | `agent.py` | ✅ | `run_loan_officer_agent()` orchestration |
| **Unit Tests** | `tests/test_*.py` | ✅ | Fetch context + gap analyzer tests |
| **E2E Test** | `test_slice1_e2e.py` | ✅ | All 5 tests passing |

### Architecture Decisions

#### 1. Data Models (`state.py`)
```
LoanFacts
├── loan_id, loan_type, loan_purpose, loan_amount, ...
├── borrowers: List[BorrowerFacts]
│   ├── first_name, last_name, ssn, dob, ...
│   ├── current_address_*, employer_*, income fields
│   └── borrower_type: "PRIMARY" | "CO_BORROWER"
├── subject_property: PropertyFacts
│   └── address, city, state, property_type, occupancy_type, ...
├── milestones: List[MilestoneInfo]
├── efolder_docs: List[EFolderDoc]
└── scenario_tag: str (e.g., "CONV_PURCHASE_PRIMARY")
```

#### 2. Field Path Resolution
Maps questionnaire field names to `LoanFacts` paths:
```python
FIELD_PATH_MAP = {
    "borrower_ssn": "borrowers[0].ssn",
    "subject_property_type": "subject_property.property_type",
    "loan_amount": "loan_amount",
    ...
}
```

#### 3. Severity Classification
- **CRITICAL**: Blocks loan progress (SSN, DOB, citizenship_status)
- **WARN**: Needs attention but not blocking (address, employer)
- **INFO**: Informational only

#### 4. Conditional Evaluation
Parses questionnaire conditionals like:
```
"Only required if marital_status == 'Separated'"
```

### API Integration Points

| API | Endpoint | Purpose |
|-----|----------|---------|
| Encompass Fields | `POST /fieldReader` | Fetch 100+ loan fields |
| Encompass Milestones | `GET /loans/{id}/milestones` | Loan workflow status |
| Encompass Attachments | `GET /loans/{id}/attachments` | eFolder document list |

### Test Results (Mock Data)
```
[TEST 1] Complete loan with all required fields...
  Total gaps: 10, Critical: 0, Can proceed: True ✓

[TEST 2] Loan with missing SSN (should be CRITICAL)...
  Total gaps: 19, Critical: 2, Can proceed: False ✓

[TEST 3] Verify DATA phase is recorded... ✓
[TEST 4] Summary formatting... ✓
[TEST 5] can_proceed flag logic... ✓
```

### Definition of Done ✅

| Requirement | Status |
|-------------|--------|
| `fetch_loan_context` returns valid `LoanFacts` | ✅ |
| `analyze_data_gaps` returns correct gap items | ✅ |
| Fast mode e2e test passes | ✅ |
| Error handling for API failures | ✅ |

---

## Slice 2: Document Coverage + Doc Gap Analysis (Full Mode) 🔄

### Goal
Integrate **Rack & Stack (R&S)** via TaskTile API to retrieve classified document manifest and identify missing documents against questionnaire requirements.

### Implementation Plan

| Component | File | Status | Description |
|-----------|------|--------|-------------|
| **State Models** | `state.py` | 🔄 | Add `DocCoverage`, `DocCoverageItem`, `RSJobStatus` |
| **R&S Client** | `tools/rs_client.py` | ⬜ | TaskTile API auth, upload, job creation |
| **Doc Coverage Tool** | `tools/fetch_doc_coverage.py` | ⬜ | Manifest parsing, doc type normalization |
| **Gap Analyzer Phase 2** | `tools/gap_analyzer.py` | ⬜ | Add `analyze_doc_gaps()` function |
| **Doc Type Mapping** | `config/doc_type_mapping.yaml` | ⬜ | R&S category_name → logical doc type |
| **Unit Tests** | `tests/test_fetch_doc_coverage.py` | ⬜ | Doc coverage retrieval tests |
| **E2E Test** | `test_slice2_e2e.py` | ⬜ | Full mode end-to-end test |

### Mapping Slice 1 → Slice 2

| Slice 1 Component | Slice 2 Equivalent | Notes |
|-------------------|-------------------|-------|
| `fetch_loan_context.py` | `fetch_doc_coverage.py` | Similar pattern: API call → normalize → return typed result |
| `packages.shared.auth` | `tools/rs_client.py` | R&S has its own OAuth (client_id/secret → token) |
| `LoanFacts` | `DocCoverage` | Container for normalized doc data |
| `BorrowerFacts` | `DocCoverageItem` | Individual unit (borrower vs document) |
| `field_mapping.yaml` | `doc_type_mapping.yaml` | Maps R&S `category_name` to internal types |
| `FIELD_PATH_MAP` | `DOC_TYPE_MAP` | Resolution lookup |
| `analyze_data_gaps()` | `analyze_doc_gaps()` | Same pattern: iterate questions → check requirements → emit gaps |
| `required_fields` | `required_documents` | What to check in questionnaire |

---

### R&S API Overview (TaskTile)

**Base URL:** `https://tasktile.staging.cybersoftbpo.ai/api`

**Auth Model:** Client credentials flow
- `POST /auth/token` with `client_id` + `client_secret` → `access_token`
- Token expires in 3600 seconds (1 hour)

**Pipeline:** `rack-and-stack` - classifies and indexes uploaded PDFs

---

### R&S API Integration Flow

| Step | Endpoint | Purpose | Notes |
|------|----------|---------|-------|
| 1 | `POST /auth/token` | Get access token | Cache token, refresh on expiry |
| 2 | (internal) | Check for cached manifest | Skip upload if recent manifest exists |
| 3 | `POST /uploads/initiate` | Get presigned upload URL | For each eFolder PDF |
| 4 | `PUT {put_url}` | Upload PDF to S3 | Direct to storage, no auth header |
| 5 | `POST /uploads/complete` | Confirm upload | Returns `upload_id` |
| 6 | `POST /jobs` | Create R&S job | With `upload_ids[]`, returns `job_id` |
| 7 | Webhook | Receive manifest | TaskTile POSTs to our webhook URL |

**Alternatively for Step 7:** Poll for job status or store/retrieve cached manifests.

---

### State Models to Add

```python
@dataclass
class DocCoverageItem:
    """
    Single document from R&S manifest.
    
    Maps from manifest.documents[] structure.
    """
    doc_id: str                          # R&S document ID
    blob_id: str                         # R&S blob ID (source PDF)
    doc_type: str                        # Normalized type (W2, PAYSTUB, etc.)
    
    # From manifest.documents[].category
    category_id: Optional[int] = None    # R&S category ID (e.g., 2174)
    category_name: Optional[str] = None  # R&S category name (e.g., "SmartFees")
    category_source: Optional[str] = None  # "ai" or "hil"
    
    # From manifest.documents[].metadata
    page_count: Optional[int] = None     # total_pages
    confidence: Optional[float] = None   # classification confidence (0-1)
    
    # Borrower association from metadata.borrowers[]
    borrower_first_name: Optional[str] = None
    borrower_last_name: Optional[str] = None
    
    # Source location for download
    source_bucket: Optional[str] = None
    source_key: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass  
class DocCoverage:
    """
    Document coverage from Rack & Stack manifest.
    
    Aggregates all classified documents for a loan.
    """
    loan_id: str
    
    # Job metadata
    job_id: Optional[str] = None
    job_status: Optional[str] = None  # "success" | "failed" | "pending"
    job_created_at: Optional[str] = None
    job_completed_at: Optional[str] = None
    
    # Manifest info
    manifest_version: Optional[str] = None
    
    # All documents
    documents: List[DocCoverageItem] = field(default_factory=list)
    
    # Aggregated by normalized doc type
    coverage_by_type: Dict[str, List[DocCoverageItem]] = field(default_factory=dict)
    
    # Quick coverage flags (computed)
    has_w2: bool = False
    has_paystubs: bool = False
    has_tax_returns: bool = False
    has_bank_statements: bool = False
    has_purchase_contract: bool = False
    
    # Counts
    total_documents: int = 0
    total_blobs: int = 0
    
    def compute_coverage_flags(self):
        """Compute quick lookup flags from coverage_by_type."""
        self.has_w2 = "W2" in self.coverage_by_type
        self.has_paystubs = "PAYSTUB" in self.coverage_by_type
        self.has_tax_returns = "TAX_RETURN" in self.coverage_by_type
        self.has_bank_statements = "BANK_STATEMENT" in self.coverage_by_type
        self.has_purchase_contract = "PURCHASE_CONTRACT" in self.coverage_by_type
        self.total_documents = len(self.documents)
    
    def to_dict(self) -> dict:
        return {
            "loan_id": self.loan_id,
            "job_id": self.job_id,
            "job_status": self.job_status,
            "total_documents": self.total_documents,
            "coverage_by_type": {k: len(v) for k, v in self.coverage_by_type.items()},
            "documents": [d.to_dict() for d in self.documents],
        }
```

---

### R&S Client (`tools/rs_client.py`)

```python
"""
Rack & Stack API Client

Handles TaskTile authentication and API calls.
"""

import os
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from pathlib import Path

# Environment variables
RS_BASE_URL = os.getenv("TASKTILE_API_URL", "https://tasktile.staging.cybersoftbpo.ai/api")
RS_CLIENT_ID = os.getenv("TASKTILE_CLIENT_ID")
RS_CLIENT_SECRET = os.getenv("TASKTILE_CLIENT_SECRET")

# Token cache
_token_cache: Dict[str, any] = {}

def get_rs_access_token() -> str:
    """Get or refresh R&S access token."""
    global _token_cache
    
    # Check cache
    if _token_cache.get("expires_at") and datetime.utcnow() < _token_cache["expires_at"]:
        return _token_cache["access_token"]
    
    # Request new token
    resp = requests.post(
        f"{RS_BASE_URL}/auth/token",
        json={
            "client_id": RS_CLIENT_ID,
            "client_secret": RS_CLIENT_SECRET,
        }
    )
    resp.raise_for_status()
    data = resp.json()
    
    # Cache with 5-minute buffer
    _token_cache = {
        "access_token": data["access_token"],
        "expires_at": datetime.utcnow() + timedelta(seconds=data["expires_in"] - 300),
    }
    
    return _token_cache["access_token"]


def initiate_upload(filename: str, content_type: str, size: int) -> Dict:
    """Initiate upload and get presigned URL."""
    token = get_rs_access_token()
    resp = requests.post(
        f"{RS_BASE_URL}/uploads/initiate",
        headers={"Authorization": f"Bearer {token}"},
        json={"filename": filename, "content_type": content_type, "size": size}
    )
    resp.raise_for_status()
    return resp.json()  # {upload_id, put_url, expires_in}


def complete_upload(upload_id: str) -> Dict:
    """Confirm upload completion."""
    token = get_rs_access_token()
    resp = requests.post(
        f"{RS_BASE_URL}/uploads/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={"upload_id": upload_id}
    )
    resp.raise_for_status()
    return resp.json()


def create_job(upload_ids: List[str], entity: Dict = None) -> Dict:
    """Create R&S job with uploaded files."""
    token = get_rs_access_token()
    resp = requests.post(
        f"{RS_BASE_URL}/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "pipeline_name": "rack-and-stack",
            "upload_ids": upload_ids,
            "entity": entity or {},
        }
    )
    resp.raise_for_status()
    return resp.json()  # {job_id, pipeline, blobs, groups}


def get_presigned_download_urls(files: List[Dict]) -> List[Dict]:
    """Get presigned URLs for downloading processed documents."""
    token = get_rs_access_token()
    resp = requests.post(
        f"{RS_BASE_URL}/files/presign-get/batch",
        headers={"Authorization": f"Bearer {token}"},
        json={"files": files}
    )
    resp.raise_for_status()
    return resp.json()
```

---

### Doc Type Mapping Config

```yaml
# config/doc_type_mapping.yaml

# Maps R&S category_name → normalized doc type
# Based on actual R&S category schema

version: "1.0"

mappings:
  # Income Documents
  - category_name: "W-2"
    doc_type: "W2"
    applies_to: "borrower"
    critical: true
    
  - category_name: "W2"
    doc_type: "W2"
    applies_to: "borrower"
    critical: true
    
  - category_name: "Pay Stub"
    doc_type: "PAYSTUB"
    applies_to: "borrower"
    critical: true
    
  - category_name: "Paystub"
    doc_type: "PAYSTUB"
    applies_to: "borrower"
    critical: true
    
  - category_name: "1040"
    doc_type: "TAX_RETURN"
    applies_to: "borrower"
    critical: true
    
  - category_name: "Tax Return"
    doc_type: "TAX_RETURN"
    applies_to: "borrower"
    critical: true
    
  - category_name: "1099"
    doc_type: "1099"
    applies_to: "borrower"
    critical: false
    
  # Asset Documents
  - category_name: "Bank Statement"
    doc_type: "BANK_STATEMENT"
    applies_to: "borrower"
    critical: true
    
  - category_name: "Investment Statement"
    doc_type: "INVESTMENT_STATEMENT"
    applies_to: "borrower"
    critical: false
    
  - category_name: "401k Statement"
    doc_type: "RETIREMENT_STATEMENT"
    applies_to: "borrower"
    critical: false
    
  # Property Documents  
  - category_name: "Purchase Agreement"
    doc_type: "PURCHASE_CONTRACT"
    applies_to: "loan"
    critical: true
    conditional: "loan_purpose == 'Purchase'"
    
  - category_name: "Appraisal"
    doc_type: "APPRAISAL"
    applies_to: "loan"
    critical: true
    
  - category_name: "Title"
    doc_type: "TITLE"
    applies_to: "loan"
    critical: false
    
  # Identity Documents
  - category_name: "Driver License"
    doc_type: "DRIVERS_LICENSE"
    applies_to: "borrower"
    critical: true
    
  - category_name: "Passport"
    doc_type: "PASSPORT"
    applies_to: "borrower"
    critical: false
    
  - category_name: "SSN Card"
    doc_type: "SSN_CARD"
    applies_to: "borrower"
    critical: false
    
  # Conditional Documents
  - category_name: "Divorce Decree"
    doc_type: "DIVORCE_DECREE"
    applies_to: "borrower"
    critical: true
    conditional: "marital_status == 'Divorced'"
    
  - category_name: "Separation Agreement"
    doc_type: "SEPARATION_AGREEMENT"
    applies_to: "borrower"
    critical: true
    conditional: "marital_status == 'Separated'"
    
  - category_name: "Gift Letter"
    doc_type: "GIFT_LETTER"
    applies_to: "loan"
    critical: true
    conditional: "has_gift_funds == true"
    
  # Other
  - category_name: "SmartFees"
    doc_type: "FEES_WORKSHEET"
    applies_to: "loan"
    critical: false

# Default for unknown categories
default:
  doc_type: "OTHER"
  applies_to: "loan"
  critical: false
```

---

### Manifest Parsing (`fetch_doc_coverage.py`)

```python
"""
Parse R&S webhook manifest into DocCoverage.

The manifest structure from TaskTile:
{
  "version": "1.0.0",
  "job": { "id", "status", "created_at", "completed_at" },
  "counts": { "blobs", "documents" },
  "documents": [
    {
      "id": "...",
      "blob_id": "...",
      "source": { "bucket", "key" },
      "category": { "category_id", "category_name", "source" },
      "metadata": { "total_pages", "confidence", "borrowers": [...] }
    }
  ]
}
"""

def parse_manifest(manifest: Dict, loan_id: str) -> DocCoverage:
    """Parse R&S manifest into DocCoverage."""
    
    # Load doc type mappings
    mappings = load_doc_type_mapping()
    
    coverage = DocCoverage(loan_id=loan_id)
    
    # Job metadata
    job = manifest.get("job", {})
    coverage.job_id = job.get("id")
    coverage.job_status = job.get("status")
    coverage.job_created_at = job.get("created_at")
    coverage.job_completed_at = job.get("completed_at")
    coverage.manifest_version = manifest.get("version")
    
    # Counts
    counts = manifest.get("counts", {})
    coverage.total_blobs = counts.get("blobs", 0)
    
    # Parse documents
    for doc in manifest.get("documents", []):
        category = doc.get("category", {})
        metadata = doc.get("metadata", {})
        source = doc.get("source", {})
        
        # Get first borrower if present
        borrowers = metadata.get("borrowers", [])
        borrower = borrowers[0] if borrowers else {}
        
        # Map category to normalized doc type
        category_name = category.get("category_name", "")
        doc_type = map_to_doc_type(category_name, mappings)
        
        item = DocCoverageItem(
            doc_id=doc.get("id"),
            blob_id=doc.get("blob_id"),
            doc_type=doc_type,
            category_id=category.get("category_id"),
            category_name=category_name,
            category_source=category.get("source"),
            page_count=metadata.get("total_pages"),
            confidence=metadata.get("confidence"),
            borrower_first_name=borrower.get("firstName"),
            borrower_last_name=borrower.get("lastName"),
            source_bucket=source.get("bucket"),
            source_key=source.get("key"),
        )
        
        coverage.documents.append(item)
        
        # Aggregate by type
        if doc_type not in coverage.coverage_by_type:
            coverage.coverage_by_type[doc_type] = []
        coverage.coverage_by_type[doc_type].append(item)
    
    # Compute flags
    coverage.compute_coverage_flags()
    
    return coverage
```

### Gap Analyzer Phase 2 Additions

```python
# Add to gap_analyzer.py

# Document severity mapping (from doc_type_mapping.yaml)
CRITICAL_DOC_TYPES = {
    "W2", "PAYSTUB", "TAX_RETURN", "BANK_STATEMENT",
    "DRIVERS_LICENSE", "PURCHASE_CONTRACT", "APPRAISAL",
    "DIVORCE_DECREE", "SEPARATION_AGREEMENT", "GIFT_LETTER",
}


def analyze_doc_gaps(
    loan_facts: LoanFacts,
    doc_coverage: DocCoverage,
    questionnaire: Optional[Dict] = None
) -> NeedsListResult:
    """
    Analyze document coverage for gaps (Phase 2).
    
    Checks:
    - required_documents from each questionnaire question
    - conditional document requirements based on loan_facts
    - Per-borrower document requirements (each borrower needs W2, etc.)
    """
    if questionnaire is None:
        questionnaire = load_questionnaire()
    
    gaps: List[GapItem] = []
    checked_docs: set = set()
    
    for section in questionnaire.get("sections", []):
        section_id = section.get("section_id", "unknown")
        
        for question in section.get("questions", []):
            question_id = question.get("question_id", "unknown")
            
            # Skip if question doesn't apply to this loan
            if not _question_applies(question, loan_facts):
                continue
            
            required_docs = question.get("required_documents", [])
            
            for doc_type in required_docs:
                # Skip if already checked
                if doc_type in checked_docs:
                    continue
                checked_docs.add(doc_type)
                
                # Check if document exists in coverage
                if _has_document(doc_coverage, doc_type):
                    continue
                
                # Document missing - create gap
                severity = GapSeverity.CRITICAL.value if doc_type in CRITICAL_DOC_TYPES else GapSeverity.WARN.value
                
                gap = GapItem(
                    id=f"DOC_{section_id}_{question_id}_{doc_type}",
                    category=_get_category(section_id),
                    type=GapType.DOC.value,
                    status=GapStatus.MISSING.value,
                    severity=severity,
                    label=f"Missing document: {_humanize_doc_type(doc_type)}",
                    reason=question.get("prompt", ""),
                    action=f"Upload {_humanize_doc_type(doc_type)}",
                    doc_type=doc_type,
                    section_id=section_id,
                    question_id=question_id,
                )
                gaps.append(gap)
    
    result = NeedsListResult(phases_completed=["DOCS"], items=gaps)
    result.compute_summary()
    return result


def _has_document(doc_coverage: DocCoverage, doc_type: str) -> bool:
    """Check if document type is present in coverage."""
    if doc_coverage is None:
        return False
    return doc_type in doc_coverage.coverage_by_type and \
           len(doc_coverage.coverage_by_type[doc_type]) > 0


def _humanize_doc_type(doc_type: str) -> str:
    """Convert doc_type to human-readable label."""
    labels = {
        "W2": "W-2",
        "PAYSTUB": "Pay Stub",
        "TAX_RETURN": "Tax Return",
        "BANK_STATEMENT": "Bank Statement",
        "DRIVERS_LICENSE": "Driver's License",
        "PURCHASE_CONTRACT": "Purchase Agreement",
        "APPRAISAL": "Appraisal",
        "DIVORCE_DECREE": "Divorce Decree",
        "SEPARATION_AGREEMENT": "Separation Agreement",
        "GIFT_LETTER": "Gift Letter",
    }
    return labels.get(doc_type, doc_type.replace("_", " ").title())


def merge_gap_results(data_gaps: NeedsListResult, doc_gaps: NeedsListResult) -> NeedsListResult:
    """Merge data and doc gap results into single result."""
    merged = NeedsListResult(
        phases_completed=data_gaps.phases_completed + doc_gaps.phases_completed,
        items=data_gaps.items + doc_gaps.items,
    )
    merged.compute_summary()
    return merged
```

---

### Agent.py Updates for Full Mode

```python
async def run_loan_officer_agent(loan_id: str, mode: str = "fast"):
    """
    Execute LOA workflow.
    
    Modes:
    - fast: Data gaps only (~2-5s)
    - full: Data + doc gaps using cached R&S manifest (~5-15s)
    - refresh_docs: Trigger new R&S job, wait for manifest (~30s-5min)
    """
    
    # Phase 1: Gather loan context (always)
    loan_facts = await fetch_loan_context(loan_id)
    
    # Phase 2: Analyze data gaps (always)
    data_gaps = analyze_data_gaps(loan_facts)
    
    # Phase 3: Document coverage (full/refresh_docs modes)
    doc_coverage = None
    all_gaps = data_gaps
    
    if mode in ["full", "refresh_docs"]:
        doc_coverage = await fetch_doc_coverage(
            loan_id=loan_id,
            efolder_docs=loan_facts.efolder_docs,
            refresh=(mode == "refresh_docs")
        )
        
        if doc_coverage and doc_coverage.job_status == "success":
            doc_gaps = analyze_doc_gaps(loan_facts, doc_coverage)
            all_gaps = merge_gap_results(data_gaps, doc_gaps)
        else:
            # R&S not available - log warning, continue with data gaps only
            logger.warning(f"[LOA] R&S manifest not available, using data gaps only")
    
    return LOAResult(
        loan_id=loan_id,
        mode=mode,
        status=AgentStatus.COMPLETE.value,
        loan_facts=loan_facts,
        doc_coverage=doc_coverage.to_dict() if doc_coverage else None,
        needs_list=all_gaps,
    )
```

---

### Environment Variables for R&S

Add to `.env`:
```bash
# TaskTile / Rack & Stack API
TASKTILE_API_URL=https://tasktile.staging.cybersoftbpo.ai/api
TASKTILE_CLIENT_ID=your-client-id
TASKTILE_CLIENT_SECRET=your-client-secret
TASKTILE_WEBHOOK_URL=https://your-system.com/webhooks/tasktile
```

---

### Test Criteria for Slice 2

| Test Case | Expected Result |
|-----------|-----------------|
| Parse valid R&S manifest JSON | Returns `DocCoverage` with documents |
| Manifest with W2, Paystub categories | `coverage_by_type` contains W2, PAYSTUB |
| Loan with R&S manifest, employee missing W-2 | Returns doc gap for W2 (CRITICAL) |
| `marital_status="Separated"` missing Separation Agreement | Returns conditional doc gap |
| R&S job_status="failed" | Graceful handling, doc_coverage with error |
| No cached manifest, `refresh=False` | Returns empty DocCoverage |
| `refresh=True` | Triggers upload flow, creates new job |

---

### Definition of Done (Slice 2)

| Requirement | Status |
|-------------|--------|
| `rs_client.py` authenticates with TaskTile | ⬜ |
| `parse_manifest()` correctly parses R&S webhook JSON | ⬜ |
| `fetch_doc_coverage` returns valid `DocCoverage` | ⬜ |
| `analyze_doc_gaps` returns correct doc gap items | ⬜ |
| Doc type mapping covers common mortgage documents | ⬜ |
| Full mode e2e test passes (data + doc gaps merged) | ⬜ |
| Error handling for R&S API failures | ⬜ |
| Manifest caching strategy documented | ⬜ |

---

## File Structure After Slice 2

```
agents/loan-officer-assistant/
├── __init__.py
├── agent.py                         # Entry point (updated for full mode)
├── state.py                         # + DocCoverage, DocCoverageItem
├── SLICE_1_IMPLEMENTATION.md        # This file
├── config/
│   ├── __init__.py
│   ├── field_mapping.yaml           # Slice 1: Encompass field → LoanFacts
│   └── doc_type_mapping.yaml        # Slice 2: R&S category → doc type (NEW)
├── tools/
│   ├── __init__.py
│   ├── fetch_loan_context.py        # Slice 1: Encompass API
│   ├── rs_client.py                 # Slice 2: TaskTile API client (NEW)
│   ├── fetch_doc_coverage.py        # Slice 2: Manifest parsing (NEW)
│   └── gap_analyzer.py              # + analyze_doc_gaps(), merge_gap_results()
├── tests/
│   ├── __init__.py
│   ├── test_fetch_loan_context.py   # Slice 1
│   ├── test_gap_analyzer_phase1.py  # Slice 1
│   ├── test_rs_client.py            # Slice 2: R&S API tests (NEW)
│   ├── test_fetch_doc_coverage.py   # Slice 2: Manifest parsing tests (NEW)
│   └── test_gap_analyzer_phase2.py  # Slice 2: Doc gap tests (NEW)
├── test_slice1_e2e.py               # Slice 1 e2e (mock data)
└── test_slice2_e2e.py               # Slice 2 e2e (mock manifest) (NEW)
```

---

## Quick Reference: Key Patterns

### Pattern 1: API Fetch → Normalize → Return Typed
```python
async def fetch_X_context(loan_id: str) -> XFacts:
    # 1. Get auth
    token = get_access_token()
    
    # 2. Call API(s)
    raw_data = call_api(loan_id, token)
    
    # 3. Normalize to dataclass
    facts = normalize_to_facts(raw_data)
    
    # 4. Compute derived fields
    facts.computed_field = derive_from(facts)
    
    return facts
```

### Pattern 2: Analyze Gaps (Data or Docs)
```python
def analyze_X_gaps(facts: Facts, questionnaire: Dict) -> NeedsListResult:
    gaps = []
    
    for section in questionnaire["sections"]:
        for question in section["questions"]:
            # Skip if conditionals not met
            if not _question_applies(question, facts):
                continue
            
            # Check required items
            for item_id in question.get("required_X", []):
                if not _is_present(facts, item_id):
                    gaps.append(create_gap_item(...))
    
    result = NeedsListResult(items=gaps)
    result.compute_summary()
    return result
```

### Pattern 3: Conditional Evaluation
```python
def _question_applies(question: Dict, facts: Facts) -> bool:
    for conditional in question.get("conditional_requirements", []):
        if conditional.startswith("Only required if"):
            field, op, value = parse_conditional(conditional)
            if not evaluate(facts, field, op, value):
                return False  # Question doesn't apply
    return True  # All conditions met
```

---

## Slice 2 Implementation Order

1. **Create `tools/rs_client.py`** - TaskTile API authentication and helpers
2. **Add state models** - `DocCoverage`, `DocCoverageItem` to `state.py`
3. **Create `config/doc_type_mapping.yaml`** - R&S category → normalized doc type
4. **Create `tools/fetch_doc_coverage.py`** - Manifest parsing, cache lookup
5. **Extend `tools/gap_analyzer.py`** - Add `analyze_doc_gaps()`, `merge_gap_results()`
6. **Update `agent.py`** - Wire up full mode orchestration
7. **Write tests**:
   - `tests/test_rs_client.py` - API mocking
   - `tests/test_fetch_doc_coverage.py` - Manifest parsing
   - `tests/test_gap_analyzer_phase2.py` - Doc gap detection
8. **Create `test_slice2_e2e.py`** - Full mode with mock manifest

---

## R&S Manifest Sample (for testing)

Save as `tests/fixtures/sample_manifest.json`:

```json
{
  "version": "1.0.0",
  "job": {
    "id": "test-job-123",
    "status": "success",
    "created_at": "1702300000000",
    "completed_at": "1702300300000"
  },
  "counts": {
    "blobs": 1,
    "documents": 3
  },
  "documents": [
    {
      "id": "doc-1",
      "blob_id": "blob-1",
      "source": {"bucket": "test", "key": "docs/w2.pdf"},
      "category": {"category_id": 100, "category_name": "W-2", "source": "hil"},
      "metadata": {
        "total_pages": 1,
        "confidence": 0.95,
        "borrowers": [{"firstName": "John", "lastName": "Smith"}]
      }
    },
    {
      "id": "doc-2",
      "blob_id": "blob-1",
      "source": {"bucket": "test", "key": "docs/paystub.pdf"},
      "category": {"category_id": 101, "category_name": "Pay Stub", "source": "ai"},
      "metadata": {"total_pages": 2, "confidence": 0.88, "borrowers": []}
    },
    {
      "id": "doc-3",
      "blob_id": "blob-1",
      "source": {"bucket": "test", "key": "docs/bank.pdf"},
      "category": {"category_id": 102, "category_name": "Bank Statement", "source": "hil"},
      "metadata": {"total_pages": 5, "confidence": 0.92, "borrowers": []}
    }
  ]
}
```

This provides W2, PAYSTUB, and BANK_STATEMENT coverage for testing.