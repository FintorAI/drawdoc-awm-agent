# Discrepancy Detection Agent

**Purpose**: Automatically detect discrepancies between extracted document values and Encompass field values, categorize them as HARD STOPS vs PTF conditions, and auto-generate PTF condition text.

---

## 🎯 Key Features

### 1. **Intelligent Field Comparison**
- **Names**: Allows middle initial variations, spelling tolerance
- **Addresses**: Fuzzy matching for suffix differences (Dr vs Drive)
- **Amounts**: Zero-tolerance for critical fields (loan amount, interest rate)

### 2. **Automatic PTF Generation**
- Auto-generates PTF condition text based on discrepancy type
- Assigns to correct department (Loan Processor, Underwriter)
- Logs conditions locally (API integration pending)

### 3. **Hard Stop Detection**
Based on SOP (discovery/sop_workflow_analysis.md lines 768-780):
- Loan Amount mismatch → HALT pipeline
- Interest Rate mismatch → HALT pipeline
- Monthly Hazard/Tax discrepancy with UW → HALT pipeline
- Insufficient Dwelling Coverage → HALT pipeline
- Approval Expiration → HALT pipeline

### 4. **Acceptable Variances**
Based on SOP (context/docs_draw_sop.md lines 1382-1391):
- Missing middle initials on Contract/Appraisal/HOI → IGNORE
- Address suffix differences (DR vs DRIVE) → IGNORE
- Co-Borrower name missing on VA appraisal → IGNORE

---

## 📊 Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                   DISCREPANCY DETECTION AGENT                     │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  Load doc_context from  │
                    │     Prep Agent          │
                    │  (field_mappings)       │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │  Read Encompass values  │
                    │   for all extracted     │
                    │       fields            │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │  For each field:        │
                    │  - Compare values       │
                    │  - Apply matching rules │
                    │  - Categorize severity  │
                    └───────────┬─────────────┘
                                │
                   ┌────────────┴────────────┐
                   │                         │
            HARD STOP?                    SOFT?
                   │                         │
                   ▼                         ▼
        ┌──────────────────┐    ┌──────────────────────┐
        │  - HALT pipeline │    │  - Generate PTF text │
        │  - Log critical  │    │  - Add PTF condition │
        │  - Escalate      │    │  - Continue pipeline │
        └──────────────────┘    └──────────────────────┘
                   │                         │
                   └────────────┬────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │  Return comprehensive   │
                    │       report            │
                    └─────────────────────────┘
```

---

## 🔧 Usage

### Command Line

```bash
# Run discrepancy detection on Prep Agent output
python agents/drawdocs/subagents/discrepancy_agent/discrepancy_agent.py \
  --loan-id "8587ad65-e186-4655-b813-f713ff98709f" \
  --doc-context-file "path/to/prep_output.json" \
  --loan-type "Conventional" \
  --output "discrepancy_results.json"

# Dry run (don't create PTF conditions)
python agents/drawdocs/subagents/discrepancy_agent/discrepancy_agent.py \
  --loan-id "8587ad65-e186-4655-b813-f713ff98709f" \
  --doc-context-file "prep_output.json" \
  --dry-run
```

### Python API

```python
from agents.drawdocs.subagents.discrepancy_agent import run_discrepancy_detection

# Load doc_context from Prep Agent
doc_context = {
    "field_mappings": {
        "11": {"value": "JOHN", "source": "Driver's License"},
        "1109": {"value": "208000", "source": "Final 1003"},
        # ... more fields
    }
}

# Run discrepancy detection
result = run_discrepancy_detection(
    loan_id="8587ad65-e186-4655-b813-f713ff98709f",
    doc_context=doc_context,
    loan_type="Conventional",
    dry_run=False
)

# Check status
if result["status"] == "blocked":
    print(f"🛑 HARD STOPS FOUND: {len(result['hard_stops'])}")
    for stop in result["hard_stops"]:
        print(f"  - {stop['field_name']}: {stop['message']}")
        print(f"    Action: {stop['action']}")
elif result["status"] == "proceed_with_conditions":
    print(f"⚠️  Proceeding with {result['ptf_conditions_added']} PTF conditions")
else:
    print("✅ No discrepancies found")
```

---

## 📤 Output Format

```json
{
  "loan_id": "8587ad65-e186-4655-b813-f713ff98709f",
  "status": "proceed_with_conditions",
  "hard_stops": [
    {
      "type": "Financial Discrepancy",
      "field_id": "1109",
      "field_name": "Loan Amount",
      "extracted": "208000",
      "encompass": "189000",
      "source_doc": "Final 1003",
      "action": "HARD STOP - Contact Team Lead immediately",
      "message": "Loan Amount mismatch between Final 1003 ($208,000) and Encompass ($189,000)"
    }
  ],
  "soft_discrepancies": [
    {
      "type": "Borrower Information",
      "field_id": "11",
      "field_name": "Borrower First Name",
      "extracted": "JOHN M",
      "encompass": "JOHN",
      "source_doc": "Driver's License",
      "severity": "PTF",
      "ptf_text": "PTF - Verify Borrower First Name: Document shows 'JOHN M', Encompass shows 'JOHN'. Source: Driver's License",
      "ptf_added": true,
      "condition_id": "PTF_8587ad65-e186-4655-b813-f713ff98709f_1_1733784960",
      "assigned_to": "Loan Processor"
    }
  ],
  "ptf_conditions_added": 1,
  "fields_checked": 16,
  "discrepancies_found": 2,
  "acceptable_variances": 0,
  "summary": "⚠️  Proceeding with 1 PTF condition(s) added.",
  "execution_time": 2.45
}
```

---

## 🔍 Discrepancy Rules

### Hard Stop Fields
| Field ID | Field Name | Tolerance | Action |
|----------|-----------|-----------|--------|
| 1109 | Loan Amount | 0 | Contact Team Lead |
| 3 | Interest Rate | 0 | Contact Team Lead |
| 578 | Monthly Hazard Insurance | 0 | Get revised Final Approval (NO PTF) |
| 231 | Monthly Property Tax | 0 | Get revised Final Approval (NO PTF) |

### Soft Discrepancy Fields
| Field ID | Field Name | Matching Rule | Assigned To |
|----------|-----------|---------------|-------------|
| 11 | Borrower First Name | Spelling match, ignore middle initial | Loan Processor |
| 12 | Borrower Last Name | Spelling match | Loan Processor |
| FR0104 | Borrower Present Address | Address fuzzy (allow suffix) | Loan Processor |
| 15 | Subject Property Address | Address fuzzy | Loan Processor |
| 4004 | Co-Borrower First Name | Spelling match, ignore middle initial | Loan Processor |

---

## 🚀 Integration with Orchestrator

The Discrepancy Agent runs **after Drawcore** and **before Verification**:

```
Prep → Drawcore → DISCREPANCY → Verification → OrderDocs
```

### In Orchestrator

```python
# Step 3: Drawcore
drawcore_output = run_drawcore_agent(loan_id, doc_context)

# Step 3.5: Discrepancy Detection (NEW)
discrepancy_output = run_discrepancy_detection(
    loan_id=loan_id,
    doc_context=doc_context,
    loan_type=loan_context.get("loan_type")
)

# Check for hard stops
if discrepancy_output["status"] == "blocked":
    print(f"🛑 PIPELINE HALTED - {len(discrepancy_output['hard_stops'])} hard stop(s)")
    return {
        "status": "blocked",
        "agents": {
            "prep": prep_output,
            "drawcore": drawcore_output,
            "discrepancy": discrepancy_output
        }
    }

# If soft discrepancies only, continue with PTF conditions
if discrepancy_output["status"] == "proceed_with_conditions":
    print(f"⚠️  Continuing with {discrepancy_output['ptf_conditions_added']} PTF conditions")

# Step 4: Verification (continue)
verification_output = run_verification_agent(loan_id, prep_output, drawcore_output)
```

---

## 📝 TODO

- [ ] Integrate actual Encompass Conditions API when available
  - Currently logs PTF conditions to `/tmp/ptf_conditions/`
  - Expected endpoint: `POST /encompass/v3/loans/{loanId}/underwritingConditions`
- [ ] Add ARM Lock Desk approval check field
- [ ] Add Non-QM Eric Gut review check field
- [ ] Add Pre-Funding QC flag check field
- [ ] Expand discrepancy rules for all 196 SOP fields
- [ ] Add insurance validation (dwelling coverage, mortgagee clause)
- [ ] Add fee variance checks

---

## 📚 References

- **SOP**: `Docs Draw SOP (1).docx`
- **Hard Stops**: `discovery/sop_workflow_analysis.md` (lines 768-780)
- **Acceptable Variances**: `context/docs_draw_sop.md` (lines 1382-1391)
- **Discrepancy Rules**: `agents/drawdocs/config/discrepancy_rules.py`
- **Primitives**: `agents/drawdocs/tools/primitives.py`

