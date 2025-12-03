# Request Sub-Agent

## Overview

The **Request Sub-Agent** is responsible for sending disclosure review notifications to Loan Officers (LOs) via email. It aggregates results from the Verification and Preparation agents and delivers a comprehensive summary to the LO.

---

## MVP Scope

| Feature | Status | Description |
|---------|--------|-------------|
| Email notifications | ✅ Implemented | Send disclosure review requests to LOs |
| MI calculation results | ✅ Included | Monthly MI amount included in email |
| Fee tolerance warnings | ✅ Included | Warns LO if tolerance violations exist |
| Non-MVP loan flagging | ✅ Implemented | Flags loans requiring manual processing |
| Dry-run mode | ✅ Implemented | Test without sending actual emails |
| Multiple email providers | 🔄 Placeholder | SMTP, SendGrid, AWS SES stubs ready |

---

## Architecture

```
request_agent/
├── __init__.py              # Exports run_disclosure_request
├── request_agent.py         # Main agent logic
├── README.md                # This file
└── tools/
    ├── __init__.py
    └── email_tools.py       # Email sending utilities
```

---

## Tools

### 1. `send_disclosure_email`

Sends an email notification to the Loan Officer with disclosure status.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `loan_id` | `str` | Yes | Encompass loan GUID |
| `lo_email` | `str` | Yes | Loan Officer email address |
| `fields_status` | `dict` | Yes | Verification and preparation results |
| `dry_run` | `bool` | No | If `True`, don't send (default: `True`) |

**Returns:**

```python
{
    "loan_id": "abc-123",
    "lo_email": "lo@example.com",
    "success": True,
    "dry_run": True,  # or False if actually sent
    "email_subject": "Disclosure Ready for Review - Loan abc-123",
    "email_body": "...",
    "timestamp": "2025-12-02T10:30:00"
}
```

**Email Content Includes:**
- Loan ID and type
- Property state
- Field status summary (checked, missing, populated, cleaned)
- MI requirement and monthly amount
- Fee tolerance violations and cure amount
- Warnings for non-MVP loans
- Next steps for LO

---

### 2. `get_lo_contact_info`

Retrieves LO email from Encompass when not provided.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `loan_id` | `str` | Yes | Encompass loan GUID |

**Returns:**

```python
{
    "loan_id": "abc-123",
    "lo_email": "lo@example.com",
    "field_id": "360",  # Field where email was found
    "success": True
}
```

**Searched Fields:**
- `LO.Email`
- `LoanOfficerEmail`
- `360` (common LO email field)

---

## Main Function

### `run_disclosure_request()`

Orchestrates the entire email notification flow.

**Signature:**

```python
def run_disclosure_request(
    loan_id: str,
    lo_email: str,
    verification_results: Dict[str, Any],
    preparation_results: Dict[str, Any],
    demo_mode: bool = True
) -> Dict[str, Any]:
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `loan_id` | `str` | Encompass loan GUID |
| `lo_email` | `str` | Loan Officer email |
| `verification_results` | `dict` | Output from Verification Agent |
| `preparation_results` | `dict` | Output from Preparation Agent |
| `demo_mode` | `bool` | Dry-run mode (default: `True`) |

**Expected `verification_results` structure:**

```python
{
    "fields_checked": 20,
    "fields_missing": ["CD1.X1", "VEND.X263"],
    "fields_with_values": ["1109", "3", "4", "11"],
    "is_mvp_supported": True,
    "mvp_warnings": [],
    "loan_type": "Conventional",
    "property_state": "NV"
}
```

**Expected `preparation_results` structure:**

```python
{
    "fields_populated": ["CD1.X1"],
    "fields_cleaned": ["4000", "4002"],
    "fields_failed": [],
    "mi_result": {
        "requires_mi": True,
        "monthly_amount": 125.50,
        "source": "calculated",
        "ltv": 85.0
    },
    "tolerance_result": {
        "has_violations": False,
        "total_cure_needed": 0
    }
}
```

**Returns:**

```python
{
    "loan_id": "abc-123",
    "status": "success",  # or "failed"
    "email_sent": True,
    "lo_email": "lo@example.com",
    "email_summary": { ... },
    "email_body": "...",
    "timestamp": "2025-12-02T10:30:00",
    "summary": "Request Complete (MVP): ...",
    "demo_mode": True,
    "email_result": { ... },
    "agent_messages": [ ... ]
}
```

---

## Email Template

The agent generates a structured email with the following sections:

```
Disclosure Review Request
========================================

Loan ID: abc-123-def-456
Loan Type: Conventional
State: NV

FIELD STATUS
--------------------
Fields Checked: 20
Fields Missing: 2
Fields Populated: 5
Fields Cleaned: 3

MORTGAGE INSURANCE
--------------------
MI Required: Yes
Monthly MI: $125.50
Source: calculated

FEE TOLERANCE
--------------------
No violations

WARNINGS
--------------------
⚠️ 2 required fields still missing

MISSING FIELDS
--------------------
  - CD1.X1
  - VEND.X263

========================================
⚠️ ATTENTION REQUIRED - See warnings above

Please review and take appropriate action.
```

---

## Email Provider Configuration

The agent supports multiple email backends via environment variables:

### SMTP (Default)

```env
EMAIL_SERVICE=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@yourcompany.com
```

### SendGrid (Placeholder)

```env
EMAIL_SERVICE=sendgrid
SENDGRID_API_KEY=your-api-key
EMAIL_FROM=noreply@yourcompany.com
```

### AWS SES (Placeholder)

```env
EMAIL_SERVICE=aws_ses
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1
EMAIL_FROM=noreply@yourcompany.com
```

> **Note:** SendGrid and AWS SES implementations are stubs. Implement in `email_tools.py` when ready.

---

## Usage

### From Python

```python
from agents.disclosure.subagents.request_agent import run_disclosure_request

result = run_disclosure_request(
    loan_id="abc-123-def-456",
    lo_email="lo@example.com",
    verification_results={
        "fields_checked": 20,
        "fields_missing": [],
        "is_mvp_supported": True,
        "loan_type": "Conventional",
        "property_state": "NV"
    },
    preparation_results={
        "fields_populated": ["CD1.X1"],
        "fields_cleaned": ["4000"],
        "mi_result": {
            "requires_mi": True,
            "monthly_amount": 125.50,
            "source": "calculated"
        },
        "tolerance_result": {
            "has_violations": False,
            "total_cure_needed": 0
        }
    },
    demo_mode=True  # Set to False to actually send
)

print(result["summary"])
```

### From Command Line

```bash
# Dry run (no email sent)
python -m agents.disclosure.subagents.request_agent.request_agent \
    --loan-id "abc-123-def-456" \
    --lo-email "lo@example.com" \
    --demo

# Actually send email (requires email config)
python -m agents.disclosure.subagents.request_agent.request_agent \
    --loan-id "abc-123-def-456" \
    --lo-email "lo@example.com"
```

---

## Agent Instructions

The agent operates with the following system prompt:

```
You are a Disclosure Request Sub-Agent.

Your job is to send disclosure review notifications to loan officers via email.

MVP SCOPE:
- Include MI calculation results in email
- Include fee tolerance warnings in email
- Flag non-MVP loans (non-Conventional or non-NV/CA)

WORKFLOW:
1. Check if all required fields are ready
2. Review MI calculation results
3. Review fee tolerance violations (if any)
4. If LO email not provided, use get_lo_contact_info(loan_id) to find it
5. Use send_disclosure_email() to send notification with full summary
6. Return confirmation of email sent

IMPORTANT:
- Always include field status summary in email
- Include MI calculation result (monthly amount if applicable)
- WARN LO if fee tolerance violations exist
- WARN LO if loan is non-MVP (requires manual processing)
- Include loan ID and next steps in email

Be professional and concise in communications.
```

---

## Helper Functions

### `build_email_summary()`

Builds a comprehensive summary dictionary from verification and preparation results.

**Extracted Data:**
- Field status (checked, missing, populated, cleaned)
- MVP support status and warnings
- Loan type and property state
- MI calculation results
- Fee tolerance violations
- Overall readiness status

### `format_email_body()`

Formats the summary dictionary into a human-readable email body.

---

## Integration with Orchestrator

The Request Agent is called by the Disclosure Orchestrator after verification and preparation:

```python
# In orchestrator_agent.py
from agents.disclosure.subagents.request_agent import run_disclosure_request

# After verification and preparation complete...
request_result = run_disclosure_request(
    loan_id=loan_id,
    lo_email=lo_email,
    verification_results=verification_result,
    preparation_results=preparation_result,
    demo_mode=demo_mode
)
```

---

## Workflow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     REQUEST AGENT FLOW                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUT                                                           │
│  ├── loan_id                                                     │
│  ├── lo_email (optional - can be looked up)                      │
│  ├── verification_results                                        │
│  └── preparation_results                                         │
│                                                                  │
│          ↓                                                       │
│                                                                  │
│  ┌─────────────────────┐                                         │
│  │ build_email_summary │ ← Aggregate all results                 │
│  └─────────────────────┘                                         │
│          ↓                                                       │
│  ┌───────────────────┐                                           │
│  │ format_email_body │ ← Create human-readable email             │
│  └───────────────────┘                                           │
│          ↓                                                       │
│  ┌───────────────────────┐                                       │
│  │ AI Agent Invocation   │                                       │
│  │ ├── Review summary    │                                       │
│  │ ├── Get LO email if   │                                       │
│  │ │   not provided      │                                       │
│  │ └── Call email tool   │                                       │
│  └───────────────────────┘                                       │
│          ↓                                                       │
│  ┌──────────────────────┐                                        │
│  │ send_disclosure_email │ ← Send via configured provider        │
│  └──────────────────────┘                                        │
│          ↓                                                       │
│                                                                  │
│  OUTPUT                                                          │
│  ├── status: "success" | "failed"                                │
│  ├── email_sent: True/False                                      │
│  ├── email_summary: { detailed breakdown }                       │
│  ├── email_body: "formatted email text"                          │
│  └── summary: "human-readable result"                            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Status Flags

| Flag | Meaning |
|------|---------|
| `is_mvp_supported` | Loan type is Conventional AND state is NV/CA |
| `requires_mi` | LTV > 80% for Conventional |
| `has_tolerance_violations` | Fee changes exceed TRID tolerance limits |
| `ready_for_review` | No missing fields AND no tolerance violations |

---

## Dependencies

```python
# External
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

# Internal
from copilotagent import create_deep_agent
from packages.shared import get_encompass_client
```

---

## TODO / Future Improvements

| Priority | Item | Description |
|----------|------|-------------|
| High | Implement SendGrid | Production email service |
| High | Implement AWS SES | Alternative production email |
| Medium | HTML email templates | Better formatting for LOs |
| Medium | Email tracking | Read receipts / delivery status |
| Low | LO preference lookup | Check preferred notification method |
| Low | Slack/Teams integration | Alternative notification channels |

---

## Testing

### Unit Tests (TODO)

```python
# tests/test_request_agent.py

def test_build_email_summary_with_mi():
    """Test summary includes MI when required."""
    pass

def test_build_email_summary_with_tolerance_violations():
    """Test summary includes tolerance warnings."""
    pass

def test_format_email_body_non_mvp():
    """Test email body includes non-MVP warning."""
    pass

def test_send_email_dry_run():
    """Test dry run doesn't send email."""
    pass
```

### Integration Test

```bash
# Test with mock data
python -m agents.disclosure.subagents.request_agent.request_agent \
    --loan-id "test-loan-123" \
    --lo-email "test@example.com" \
    --demo
```

---

*Document generated December 2, 2025*

