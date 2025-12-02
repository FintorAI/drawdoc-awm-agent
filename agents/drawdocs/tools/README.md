# Primitive Tools for Docs Draw MVP

All primitive tools are consolidated in `primitives.py` for easy access and reuse across all agents.

## Quick Start

```python
from agents.drawdocs.tools import (
    get_loan_context,
    read_fields,
    write_fields,
    download_documents,
    extract_entities_from_docs,
    log_issue,
)

# Or import all at once
from agents.drawdocs.tools import get_all_tools

tools = get_all_tools()
context = tools['get_loan_context'](loan_id)
```

## Available Tools

### 1. Loan Context & Workflow

#### `get_loan_context(loan_id: str) -> dict`
Get comprehensive loan context including pipeline status, milestone, and flags.

**Returns:**
```python
{
    "loan_id": "...",
    "loan_number": "...",
    "loan_status": "...",
    "loan_type": "...",
    "loan_program": "...",
    "loan_purpose": "...",
    "occupancy": "...",
    "state": "...",
    "core_milestone": "...",
    "last_milestone": "...",
    "last_milestone_date": "...",
    "flags": {
        "is_ctc": bool,
        "cd_approved": bool,
        "cd_acknowledged": bool,
        "in_docs_ordered_queue": bool
    }
}
```

#### `update_milestone(loan_id: str, status: str, comment: str) -> bool` *(Legacy)*
Update milestone status using field writes (hardcoded for "Docs Out").

**DEPRECATED:** Use `update_milestone_api()` for full API support.

**Example:**
```python
success = update_milestone(
    loan_id="abc123",
    status="Finished",
    comment="DOCS Out on 11/28/2025"
)
```

#### `get_loan_milestones(loan_id: str) -> list[dict]` *(New)*
Get all milestones for a loan using the Milestones API.

**Returns:** List of milestone dictionaries with status, dates, logs, etc.

**Example:**
```python
milestones = get_loan_milestones("abc123")
for milestone in milestones:
    print(f"{milestone['milestoneName']}: {milestone['status']}")
```

#### `get_milestone_by_name(loan_id: str, milestone_name: str) -> dict` *(New)*
Get a specific milestone by name.

**Example:**
```python
docs_ordered = get_milestone_by_name("abc123", "Docs Ordered")
print(f"Status: {docs_ordered['status']}")
```

#### `update_milestone_api(loan_id: str, milestone_name: str, status: str, comment: str = None) -> bool` *(New)*
Update any milestone using the Milestones API (preferred method).

**Example:**
```python
success = update_milestone_api(
    loan_id="abc123",
    milestone_name="Docs Ordered",
    status="Finished",
    comment="DOCS Out on 12/01/2025"
)
```

#### `add_milestone_log(loan_id: str, milestone_name: str, comment: str, done_by: str = None) -> bool` *(New)*
Add a log entry to a milestone.

**Example:**
```python
success = add_milestone_log(
    loan_id="abc123",
    milestone_name="Docs Ordered",
    comment="Documents sent to title",
    done_by="AutomationAgent"
)
```

---

### 2. Documents & Data Extraction

#### `list_required_documents(loan_id: str) -> list[str]`
Get list of required documents based on loan type and program.

**Returns:**
```python
[
    "1003 - Uniform Residential Loan Application",
    "Approval Final",
    "MI Certificate",
    "Driver's License - Borrower",
    "SSN Card - Borrower",
    "FHA Case Assignment",  # If FHA
    # ... more based on loan type
]
```

#### `download_documents(loan_id: str, categories: list[str]) -> list[dict]`
Download documents from Encompass eFolder.

**Returns:**
```python
[
    {
        "doc_id": "...",
        "category": "1003",
        "file_path": "/tmp/loan_docs/abc123/doc1.pdf",
        "file_name": "1003_Final.pdf",
        "upload_date": "2025-11-20"
    },
    # ... more documents
]
```

#### `extract_entities_from_docs(loan_id: str, docs: list[dict]) -> dict`
Extract entities from documents using LandingAI OCR.

This is the **KEY** function that creates the `doc_context` - the canonical source of truth.

**FULLY DYNAMIC** - Uses CSV-driven schemas and field mappings. NO hardcoded field names!

**Returns:**
```python
{
    "extracted_by_document": {
        "Final 1003": {
            "mapped_fields": {"borrower_first_name": {"value": "John", "encompass_field_id": "4000"}},
            "pending_fields": {...},
            "unmapped_fields": {...}
        },
        "Approval Final": {...}
    },
    "all_mapped_fields": {
        "4000": {"value": "John", "source_document": "Final 1003", "field_name": "borrower_first_name"},
        "4002": {"value": "Doe", "source_document": "Final 1003", "field_name": "borrower_last_name"}
    },
    "all_pending_fields": {...},
    "all_unmapped_fields": {...},
    "metadata": {
        "loan_id": "...",
        "extraction_date": "...",
        "source_documents": [...],
        "extraction_results": {...}
    }
}
```

---

### 3. Encompass Field IO

#### `read_fields(loan_id: str, field_ids: list[str]) -> dict`
Read multiple fields from Encompass.

**Example:**
```python
fields = read_fields(
    loan_id="abc123",
    field_ids=["4000", "4002", "65", "1172"]
)
# Returns: {"4000": "John", "4002": "Smith", "65": "123-45-6789", ...}
```

#### `write_fields(loan_id: str, updates: list[dict]) -> bool`
Write multiple fields to Encompass.

**Example:**
```python
success = write_fields(
    loan_id="abc123",
    updates=[
        {"field_id": "4000", "value": "John"},
        {"field_id": "4002", "value": "Smith"},
        {"field_id": "65", "value": "123-45-6789"}
    ]
)
```

**Note:** Writes are only enabled if `ENABLE_ENCOMPASS_WRITES=true` in `.env`

---

### 4. Compliance & Validation

#### `run_compliance_check(loan_id: str, check_type: str = "Mavent") -> str`
Run compliance check (Mavent or other).

**Returns:** Job ID for tracking

**Example:**
```python
job_id = run_compliance_check(loan_id="abc123", check_type="Mavent")
```

#### `get_compliance_results(loan_id: str, job_id: str = None) -> dict`
Get compliance check results.

**Returns:**
```python
{
    "status": "pass|fail|warning",
    "issues": [
        {
            "severity": "critical|warning|info",
            "code": "...",
            "message": "...",
            "field": "...",
            "suggested_fix": "..."
        }
    ],
    "run_date": "...",
    "report_url": "..."
}
```

---

### 5. Docs Draw & Distribution

#### `order_docs(loan_id: str) -> dict`
Trigger docs draw / generate closing package.

**Returns:**
```python
{
    "success": bool,
    "doc_package_id": "...",
    "generated_date": "...",
    "error": "..." (if failed)
}
```

#### `send_closing_package(loan_id: str, recipients: dict[str, str]) -> dict`
Send closing package to recipients.

**Example:**
```python
result = send_closing_package(
    loan_id="abc123",
    recipients={
        "title_company": "email@title.com",
        "loan_officer": "lo@lender.com",
        "processor": "processor@lender.com"
    }
)
```

**Returns:**
```python
{
    "success": bool,
    "sent_to": ["email1", "email2"],
    "failed": [],
    "tracking_ids": {"email1": "TRK_123", ...}
}
```

---

### 6. Issue Logging

#### `log_issue(loan_id: str, severity: str, message: str, context: dict = None) -> str`
Log an issue for human review.

**Example:**
```python
issue_id = log_issue(
    loan_id="abc123",
    severity="critical",
    message="Borrower SSN mismatch between 1003 and ID",
    context={
        "doc_ssn": "123-45-6789",
        "encompass_ssn": "987-65-4321",
        "field_id": "65"
    }
)
```

**Returns:** Issue ID for tracking

Issues are saved to `/tmp/loan_issues/{loan_id}_issues.json`

---

## Usage in Agents

### Example: Docs Prep Agent

```python
from agents.drawdocs.tools import (
    get_loan_context,
    list_required_documents,
    download_documents,
    extract_entities_from_docs,
    log_issue,
)

def docs_prep_agent(loan_id):
    # Step 1: Get loan context
    context = get_loan_context(loan_id)
    
    # Step 2: Check preconditions
    if not context['flags']['is_ctc']:
        log_issue(loan_id, "critical", "Loan is not CTC", context)
        return {"status": "failed", "reason": "Not CTC"}
    
    # Step 3: Get required documents
    required_docs = list_required_documents(loan_id)
    
    # Step 4: Download documents
    documents = download_documents(loan_id, required_docs)
    
    # Step 5: Extract entities
    doc_context = extract_entities_from_docs(loan_id, documents)
    
    return {
        "status": "success",
        "doc_context": doc_context
    }
```

### Example: Docs Draw Core Agent

```python
from agents.drawdocs.tools import read_fields, write_fields, log_issue

def phase_1_borrower_lo(loan_id, doc_context):
    # DYNAMIC approach - work with all_mapped_fields
    all_mapped = doc_context['all_mapped_fields']
    
    # Read current Encompass values for all mapped fields
    field_ids_to_check = list(all_mapped.keys())
    current_fields = read_fields(loan_id, field_ids_to_check)
    
    # Build updates based on doc_context (DYNAMIC)
    updates = []
    
    for field_id, field_info in all_mapped.items():
        doc_value = field_info['value']
        current_value = current_fields.get(field_id)
        
        # Check for critical mismatches (e.g., SSN field 65)
        if field_id == "65" and doc_value != current_value:
            log_issue(
                loan_id,
                "high",
                f"SSN mismatch between document and Encompass",
                {
                    "field_id": field_id,
                    "field_name": field_info['field_name'],
                    "doc_value": doc_value,
                    "encompass_value": current_value,
                    "source_document": field_info['source_document']
                }
            )
        
        # Add to updates if different
        if doc_value != current_value:
            updates.append({
                "field_id": field_id,
                "value": doc_value
            })
    
    # Write updates
    if updates:
        write_fields(loan_id, updates)
    
    return {"updates_made": len(updates)}
```

---

## Implementation Status

### ✅ Fully Implemented
- `read_fields` - Uses existing EncompassConnect client
- `write_fields` - Uses existing EncompassConnect client
- `log_issue` - Saves to JSON files
- `get_loan_context` - Reads from Encompass (enhanced with milestone API support)
- `get_loan_milestones` - Uses Encompass Milestones API via MCP HTTP client
- `get_milestone_by_name` - Query specific milestones
- `update_milestone_api` - Full milestone update via API
- `add_milestone_log` - Add logs to milestones
- `update_milestone` - Legacy field-based approach (still works)

### 🚧 Partially Implemented (Stubs/TODO)
- `list_required_documents` - Basic logic, needs refinement
- `extract_entities_from_docs` - **NOW USES ACTUAL WORKING IMPLEMENTATION from preparation_agent**
  - ✅ CSV-driven dynamic extraction
  - ✅ Retry logic with exponential backoff
  - ✅ Timeout and rate limit handling
  - 🧪 Ready to test with LandingAI API key
- `run_compliance_check` - Placeholder for Mavent integration
- `get_compliance_results` - Placeholder for Mavent integration
- `order_docs` - Placeholder for docs ordering
- `send_closing_package` - Placeholder for email/distribution

### 🔧 Next Steps for Full Implementation

1. **LandingAI Integration** - Complete the `_extract_from_*` helper functions
2. **Mavent Integration** - Implement actual compliance API calls
3. **Docs Ordering** - Implement Encompass docs generation API
4. **Email Distribution** - Integrate with email service (SendGrid, etc.)
5. **Testing** - Add unit tests for each tool
6. **Error Handling** - Improve error handling and retry logic

---

## Environment Variables Required

```bash
# Encompass API
ENCOMPASS_ACCESS_TOKEN=
ENCOMPASS_API_BASE_URL=https://api.elliemae.com
ENCOMPASS_USERNAME=
ENCOMPASS_PASSWORD=
ENCOMPASS_CLIENT_ID=
ENCOMPASS_CLIENT_SECRET=
ENCOMPASS_INSTANCE_ID=
ENCOMPASS_SUBJECT_USER_ID=

# LandingAI
LANDINGAI_API_KEY=

# Safety
ENABLE_ENCOMPASS_WRITES=false  # Set to 'true' to enable writes
```

---

## File Structure

```
agents/drawdocs/tools/
├── __init__.py          # Exports all tools
├── primitives.py        # All tools consolidated here
└── README.md           # This file
```

All tools are in **one file** (`primitives.py`) for easy maintenance and updates.

---

**Last Updated:** November 28, 2025



