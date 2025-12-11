
# LOA Agent - Slice Implementation Guide

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
Integrate Rack & Stack to retrieve document manifest and identify missing documents against questionnaire requirements.

### Implementation Plan

| Component | File | Status | Description |
|-----------|------|--------|-------------|
| **State Models** | `state.py` | 🔄 | Add `DocCoverage`, `DocCoverageItem` |
| **Doc Coverage Tool** | `tools/fetch_doc_coverage.py` | ⬜ | R&S API integration, manifest parsing |
| **Gap Analyzer Phase 2** | `tools/gap_analyzer.py` | ⬜ | Add `analyze_doc_gaps()` function |
| **Doc Type Mapping** | `config/doc_type_mapping.yaml` | ⬜ | R&S category → logical doc type |
| **Unit Tests** | `tests/test_fetch_doc_coverage.py` | ⬜ | Doc coverage retrieval tests |
| **E2E Test** | `test_slice2_e2e.py` | ⬜ | Full mode end-to-end test |

### Mapping Slice 1 → Slice 2

| Slice 1 Component | Slice 2 Equivalent | Notes |
|-------------------|-------------------|-------|
| `fetch_loan_context.py` | `fetch_doc_coverage.py` | Similar pattern: API call → normalize → return typed result |
| `LoanFacts` | `DocCoverage` | Container for normalized doc data |
| `BorrowerFacts` | `DocCoverageItem` | Individual unit (borrower vs document) |
| `field_mapping.yaml` | `doc_type_mapping.yaml` | Maps external IDs to internal types |
| `FIELD_PATH_MAP` | `DOC_TYPE_MAP` | Resolution lookup |
| `analyze_data_gaps()` | `analyze_doc_gaps()` | Same pattern: iterate questions → check requirements → emit gaps |
| `required_fields` | `required_documents` | What to check in questionnaire |

### State Models to Add

```python
@dataclass
class DocCoverageItem:
    """Single document in the R&S manifest."""
    doc_id: str
    doc_type: str  # Normalized type (W2, PAYSTUB, TAX_RETURN, etc.)
    raw_category: str  # Original R&S category
    borrower_id: Optional[str] = None  # Which borrower this belongs to
    date_received: Optional[str] = None
    page_count: Optional[int] = None
    confidence: Optional[float] = None
    source_file: Optional[str] = None

@dataclass
class DocCoverage:
    """Document coverage from Rack & Stack manifest."""
    loan_id: str
    manifest_id: Optional[str] = None
    manifest_timestamp: Optional[str] = None
    documents: List[DocCoverageItem] = field(default_factory=list)
    
    # Aggregated coverage by doc type
    coverage_by_type: Dict[str, List[DocCoverageItem]] = field(default_factory=dict)
    
    # Quick lookups
    has_w2: bool = False
    has_paystubs: bool = False
    has_tax_returns: bool = False
    has_bank_statements: bool = False
    
    def to_dict(self) -> dict:
        ...
```

### R&S API Integration

| Step | API | Endpoint | Purpose |
|------|-----|----------|---------|
| 1 | Auth | `POST /auth/token` | Get access token |
| 2 | Check Cache | (internal) | Look for existing manifest |
| 3 | Upload Files | `POST /jobs/{id}/files` | Upload eFolder docs if refresh |
| 4 | Trigger Job | `POST /jobs` | Start R&S pipeline |
| 5 | Get Manifest | Webhook or poll | Receive classified documents |

### Doc Type Mapping Config

```yaml
# config/doc_type_mapping.yaml

# R&S category → Normalized doc type
mappings:
  - raw_category: "W-2"
    doc_type: "W2"
    applies_to: "borrower"
    
  - raw_category: "Pay Stub"
    doc_type: "PAYSTUB"
    applies_to: "borrower"
    
  - raw_category: "1040"
    doc_type: "TAX_RETURN"
    applies_to: "borrower"
    
  - raw_category: "Bank Statement"
    doc_type: "BANK_STATEMENT"
    applies_to: "borrower"
    
  - raw_category: "Purchase Agreement"
    doc_type: "PURCHASE_CONTRACT"
    applies_to: "loan"
    
  - raw_category: "Divorce Decree"
    doc_type: "DIVORCE_DECREE"
    applies_to: "borrower"
    conditional: "marital_status == 'Divorced'"
    
  - raw_category: "Separation Agreement"
    doc_type: "SEPARATION_AGREEMENT"
    applies_to: "borrower"
    conditional: "marital_status == 'Separated'"
```

### Gap Analyzer Phase 2 Additions

```python
# Add to gap_analyzer.py

def analyze_doc_gaps(
    loan_facts: LoanFacts,
    doc_coverage: DocCoverage,
    questionnaire: Optional[Dict] = None
) -> NeedsListResult:
    """
    Analyze document coverage for gaps (Phase 2).
    
    Similar to analyze_data_gaps but checks:
    - required_documents from questionnaire
    - conditional document requirements
    """
    gaps: List[GapItem] = []
    
    for section in questionnaire.get("sections", []):
        for question in section.get("questions", []):
            # Skip if question doesn't apply
            if not _question_applies(question, loan_facts):
                continue
            
            required_docs = question.get("required_documents", [])
            
            for doc_type in required_docs:
                if not _has_document(doc_coverage, doc_type):
                    gap = GapItem(
                        id=f"DOC_{section_id}_{question_id}_{doc_type}",
                        category=_get_category(section_id),
                        type=GapType.DOC.value,
                        status=GapStatus.MISSING.value,
                        severity=_get_doc_severity(doc_type),
                        label=f"Missing document: {doc_type}",
                        reason=question.get("prompt", ""),
                        doc_type=doc_type,
                    )
                    gaps.append(gap)
    
    return NeedsListResult(phases_completed=["DOCS"], items=gaps)


def _has_document(doc_coverage: DocCoverage, doc_type: str) -> bool:
    """Check if document type is present in coverage."""
    return doc_type in doc_coverage.coverage_by_type and \
           len(doc_coverage.coverage_by_type[doc_type]) > 0
```

### Agent.py Updates

```python
async def run_loan_officer_agent(loan_id: str, mode: str = "fast"):
    # Phase 1: Gather loan context
    loan_facts = await fetch_loan_context(loan_id)
    
    # Phase 2: Analyze data gaps (always)
    data_gaps = analyze_data_gaps(loan_facts)
    
    # Phase 3: Document coverage (full mode only)
    if mode in ["full", "refresh_docs"]:
        doc_coverage = await fetch_doc_coverage(
            loan_id,
            efolder_docs=loan_facts.efolder_docs,
            refresh=(mode == "refresh_docs")
        )
        doc_gaps = analyze_doc_gaps(loan_facts, doc_coverage)
        
        # Merge gaps
        all_gaps = merge_gap_results(data_gaps, doc_gaps)
    else:
        all_gaps = data_gaps
    
    return LOAResult(
        loan_facts=loan_facts,
        doc_coverage=doc_coverage if mode != "fast" else None,
        needs_list=all_gaps,
    )
```

### Test Criteria for Slice 2

| Test Case | Expected Result |
|-----------|-----------------|
| Loan with R&S manifest | Returns populated `DocCoverage` |
| W2 employee missing W-2 | Returns doc gap for W2 |
| `marital_status="Separated"` missing Separation Agreement | Returns conditional doc gap |
| R&S API error | Graceful failure, error in result |
| No existing manifest, `refresh=False` | Uses empty/stale coverage |

### Definition of Done (Slice 2)

| Requirement | Status |
|-------------|--------|
| `fetch_doc_coverage` returns valid `DocCoverage` | ⬜ |
| `analyze_doc_gaps` returns correct doc gap items | ⬜ |
| Full mode e2e test passes (data + doc gaps) | ⬜ |
| Parallel execution verified | ⬜ |
| R&S manifest caching implemented | ⬜ |

---

## File Structure After Slice 2

```
agents/loan-officer-assistant/
├── __init__.py
├── agent.py                         # Entry point (updated for full mode)
├── state.py                         # + DocCoverage, DocCoverageItem
├── SLICE_IMPLEMENTATION.md          # This file
├── config/
│   ├── __init__.py
│   ├── field_mapping.yaml           # Slice 1
│   └── doc_type_mapping.yaml        # Slice 2 (NEW)
├── tools/
│   ├── __init__.py
│   ├── fetch_loan_context.py        # Slice 1
│   ├── fetch_doc_coverage.py        # Slice 2 (NEW)
│   └── gap_analyzer.py              # + analyze_doc_gaps()
├── tests/
│   ├── __init__.py
│   ├── test_fetch_loan_context.py   # Slice 1
│   ├── test_gap_analyzer_phase1.py  # Slice 1
│   ├── test_fetch_doc_coverage.py   # Slice 2 (NEW)
│   └── test_gap_analyzer_phase2.py  # Slice 2 (NEW)
├── test_slice1_e2e.py               # Slice 1 e2e
└── test_slice2_e2e.py               # Slice 2 e2e (NEW)
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

## Next Steps

1. **Start Slice 2**: Create `tools/fetch_doc_coverage.py`
2. **Add state models**: `DocCoverage`, `DocCoverageItem` to `state.py`
3. **Create mapping**: `config/doc_type_mapping.yaml`
4. **Extend gap analyzer**: Add `analyze_doc_gaps()` function
5. **Update agent.py**: Wire up full mode
6. **Write tests**: Unit tests + e2e for Slice 2