# Request Sub-Agent (Legacy)

**Version**: 1.0 (Deprecated in v2)  
**Status**: ⚠️ Legacy - Available but not primary in v2  
**Last Updated**: December 3, 2025

[🔙 Back to Main Disclosure README](../../README.md)

---

## ⚠️ Deprecation Notice

**This agent is deprecated in the v2 architecture.**

In v2, the **Send Agent** handles disclosure delivery via the eDisclosures API. This Request Agent remains available for email notifications but is no longer the primary method for disclosure delivery.

**v2 Replacement**: [Send Agent](../send_agent/README.md)

---

## Overview

The **Request Sub-Agent** sends disclosure review notifications to Loan Officers (LOs) via email. It aggregates results from the Verification and Preparation agents and delivers a comprehensive summary to the LO.

**Original Purpose** (v1): Final step to notify LO that disclosure is ready for review.

**v2 Status**: Optional email notifications only. Disclosure ordering now handled by Send Agent.

---

## Features

- Email notifications to LOs
- Summary of field status (checked, missing, populated, cleaned)
- MI calculation results in email
- Fee tolerance warnings in email
- Non-MVP loan flagging
- Dry-run mode for testing
- Multiple email provider support (SMTP, SendGrid, AWS SES stubs)

---

## Tools

### `send_disclosure_email(loan_id, lo_email, fields_status, dry_run)`
Sends email notification to LO with disclosure status.

**Returns**:
```python
{
    "loan_id": "...",
    "lo_email": "lo@example.com",
    "success": True/False,
    "dry_run": True/False,
    "email_subject": "Disclosure Ready for Review - Loan abc-123",
    "email_body": "...",
    "timestamp": "2025-12-03T10:30:00"
}
```

### `get_lo_contact_info(loan_id)`
Retrieves LO email from Encompass when not provided.

**Returns**:
```python
{
    "loan_id": "...",
    "lo_email": "lo@example.com",
    "field_id": "360",
    "success": True/False
}
```

---

## Usage

### Python API

```python
from agents.disclosure.subagents.request_agent import run_disclosure_request

result = run_disclosure_request(
    loan_id="your-loan-guid",
    lo_email="lo@example.com",
    verification_results={...},
    preparation_results={...},
    demo_mode=True  # Don't actually send
)

print(result["email_sent"])
print(result["summary"])
```

---

## Email Template

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

WARNINGS
--------------------
⚠️ 2 required fields still missing

MISSING FIELDS
--------------------
  - LE1.X1
  - LE1.X77

========================================
⚠️ ATTENTION REQUIRED - See warnings above

Please review and take appropriate action.
```

---

## Configuration

Set in `.env`:

```env
# Email notifications (optional in v2)
EMAIL_SERVICE=smtp
EMAIL_FROM=noreply@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email
SMTP_PASSWORD=your_password
```

---

## v2 Migration Notes

### What Changed
- **v1**: Request Agent was the final step, sent emails to LOs
- **v2**: Send Agent is the final step, orders disclosures via eDisclosures API

### When to Use Request Agent in v2
- Optional email notifications to LOs
- Status updates during processing
- Error notifications
- Not for primary disclosure delivery

### Recommended v2 Workflow
```
Verification → Preparation → Send (eDisclosures API)
                                ↓
                         (Optional: Request Agent for email)
```

---

## File Structure

```
request_agent/
├── request_agent.py           # Legacy email agent
├── README.md                  # This file
├── __init__.py
└── tools/
    └── email_tools.py         # Email sending utilities
```

---

## See Also

- **v2 Send Agent**: [send_agent/README.md](../send_agent/README.md) - Primary disclosure delivery
- **Main README**: [../../README.md](../../README.md) - v2 architecture overview

---

*Last updated: December 3, 2025 - Marked as legacy in v2*
