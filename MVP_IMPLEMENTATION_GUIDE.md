# Docs Draw MVP - Implementation Guide

## Quick Start Summary

The MVP architecture uses **3 LLM-based agents** + **1 deterministic flow**:

1. **Docs Prep Agent** - Downloads docs, extracts data, builds `doc_context`
2. **Docs Draw Core Agent** - Updates Encompass fields across 5 phases
3. **Audit & Compliance Agent** - Final verification before docs ordering
4. **Order Docs & Distribution** - Deterministic flow (non-LLM)

---

## Implementation Roadmap

### Phase 1: Build Primitive Tools (Week 1-2)
### Phase 2: Implement Docs Prep Agent (Week 2-3)
### Phase 3: Implement Docs Draw Core Agent (Week 3-5)
### Phase 4: Implement Audit & Compliance Agent (Week 5-6)
### Phase 5: Implement Order Docs & Distribution (Week 6)
### Phase 6: Integration & Testing (Week 7-8)

---

## Phase 1: Build Primitive Tools

Before building any agents, you need to implement these **6 tool categories**:

### 1.1 Loan Context & Workflow Tools

#### `get_loan_context(loan_id)` → dict

**Returns:**
```json
{
  "loan_id": "364",
  "loan_number": "...",
  "loan_status": "1393",
  "loan_type": "1172",
  "loan_program": "1401",
  "loan_purpose": "19",
  "occupancy": "1811",
  "state": "14",
  "core_milestone": "CoreMilestone",
  "last_milestone": "Pipeline.LastCompletedMilestone",
  "last_milestone_date": "MS.STATUSDATE",
  "flags": {
    "is_ctc": boolean,
    "cd_approved": boolean,
    "cd_acknowledged": boolean,
    "in_docs_ordered_queue": boolean
  }
}
```

**Encompass Fields Needed:**
- Loan Number: `364`
- Loan Status: `1393`
- Loan Type: `1172`
- Loan Program: `1401`
- Loan Purpose: `19`
- Occupancy: `1811`
- Subject Property State: `14`
- Core Milestone: `CoreMilestone`
- Last Finished Milestone: `Pipeline.LastCompletedMilestone`
- Last Finished Milestone Date: `MS.STATUSDATE`
- CTC/CD status flags (custom logic based on milestone/conditions)

#### `update_milestone(loan_id, status, comment)` → bool

**Parameters:**
- `status`: e.g., "Finished"
- `comment`: e.g., "DOCS Out on 11/28/2025"

**Encompass Fields to Update:**
- Milestone Status - Docs Out: `Log.MS.Status.Docs Out`
- Milestone Date - Docs Out: `Log.MS.Date.Docs Out`
- Milestone Comments - Docs Out: `Log.MS.Comments.Docs Out`
- Date Completed: `MS.CLO`

---

### 1.2 Documents & Data Extraction Tools

#### `list_required_documents(loan_id)` → list[str]

**Returns:** List of required document types based on loan program
```python
[
  "1003 - Uniform Residential Loan Application",
  "Approval Final",
  "MI Certificate",
  "Driver's License - Borrower",
  "SSN Card - Borrower",
  "FHA Case Assignment" (if FHA),
  "VA Certificate of Eligibility" (if VA),
  # ... more based on loan type
]
```

**Logic depends on:**
- Loan Type: `1172`
- Loan Program: `1401`
- Loan Purpose: `19`
- State: `14`

#### `download_documents(loan_id, categories)` → list[Document]

**Returns:** Downloaded documents from eFolder
```python
[
  {
    "doc_id": "...",
    "category": "1003",
    "file_path": "/path/to/file.pdf",
    "file_name": "1003_Final.pdf",
    "upload_date": "2025-11-20"
  },
  # ... more documents
]
```

#### `extract_entities_from_docs(docs)` → doc_context

**This is the KEY output that all other agents consume**

**Returns:** Normalized `doc_context` JSON
```json
{
  "borrowers": [
    {
      "first_name": "...",
      "middle_name": "...",
      "last_name": "...",
      "suffix": "...",
      "ssn": "...",
      "dob": "...",
      "marital_status": "...",
      "phone_home": "...",
      "phone_work": "...",
      "email": "...",
      "is_primary": true
    },
    {
      "first_name": "...",
      // ... co-borrower
      "is_primary": false
    }
  ],
  "vesting": {
    "vesting_type": "...",
    "trust_name": "...",
    "trust_state": "...",
    "trust_tax_id": "...",
    "beneficiaries": "...",
    "final_vesting_to_read": "...",
    "aka_names": []
  },
  "loan_officer": {
    "name": "...",
    "nmls_id": "...",
    "email": "...",
    "phone": "...",
    "state_license": "..."
  },
  "property": {
    "address": "...",
    "address_2": "...",
    "city": "...",
    "state": "...",
    "zip": "...",
    "county": "...",
    "type": "...",
    "units": "...",
    "year_built": "...",
    "purchase_price": "...",
    "appraised_value": "...",
    "legal_description": "...",
    "parcel_number": "..."
  },
  "program": {
    "loan_type": "FHA|VA|USDA|Conventional",
    "agency_case_number": "...",
    "fha_case_assigned_date": "...",
    "va_funding_fee": "...",
    "va_funding_fee_exempt": boolean,
    // ... program-specific fields
  },
  "loan_terms": {
    "loan_amount": "...",
    "note_rate": "...",
    "loan_term": "...",
    "amortization_type": "...",
    "first_payment_date": "...",
    "closing_date": "...",
    "lien_position": "..."
  },
  "contacts": {
    "title_company": {
      "name": "...",
      "contact": "...",
      "phone": "..."
    },
    "escrow_company": {
      "name": "...",
      "contact": "...",
      "phone": "..."
    },
    "hazard_insurance": {
      "name": "...",
      "phone": "..."
    },
    "flood_insurance": {
      "name": "...",
      "phone": "..."
    }
  },
  "financial": {
    "ltv": "...",
    "cltv": "...",
    "down_payment": "...",
    "escrow_setup": {
      "taxes": boolean,
      "insurance": boolean,
      "mi": boolean
    },
    "mortgage_insurance": {
      "premium": "...",
      "amount": "..."
    }
  },
  "fees": {
    "origination_fee": "...",
    "discount_points": "...",
    "lender_credits": "...",
    // ... itemized fees
  },
  "metadata": {
    "extraction_date": "...",
    "source_documents": ["1003", "Approval Final", ...],
    "confidence_scores": {...}
  }
}
```

---

### 1.3 Encompass Field IO Tools

#### `read_fields(loan_id, field_ids)` → dict

**Parameters:**
```python
field_ids = ["4000", "4002", "65", "1172", "14"]
```

**Returns:**
```json
{
  "4000": "John",
  "4002": "Smith",
  "65": "123-45-6789",
  "1172": "Conventional",
  "14": "CA"
}
```

#### `write_fields(loan_id, updates)` → bool

**Parameters:**
```python
updates = [
  {"field_id": "4000", "value": "John"},
  {"field_id": "4002", "value": "Smith"},
  {"field_id": "65", "value": "123-45-6789"}
]
```

**Returns:** Success/failure boolean

---

### 1.4 Compliance & Validation Tools

#### `run_compliance_check(loan_id, type="Mavent")` → str

**Returns:** Job ID or run identifier

#### `get_compliance_results(loan_id)` → dict

**Returns:**
```json
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

### 1.5 Docs Draw & Distribution Tools

#### `order_docs(loan_id)` → dict

**Returns:**
```json
{
  "success": boolean,
  "doc_package_id": "...",
  "generated_date": "...",
  "error": "..." (if failed)
}
```

#### `send_closing_package(loan_id, recipients)` → dict

**Parameters:**
```python
recipients = {
  "title_company": "email@title.com",
  "loan_officer": "lo@lender.com",
  "processor": "processor@lender.com"
}
```

**Returns:**
```json
{
  "success": boolean,
  "sent_to": ["email1", "email2"],
  "failed": [],
  "tracking_ids": {...}
}
```

---

### 1.6 Issue Logging Tool

#### `log_issue(loan_id, severity, message, context)` → str

**Parameters:**
```python
severity = "critical|high|medium|low"
message = "Borrower SSN mismatch between 1003 and ID"
context = {
  "doc_ssn": "123-45-6789",
  "encompass_ssn": "987-65-4321",
  "field_id": "65"
}
```

**Returns:** Issue ID for tracking

---

## Phase 2: Agent 1 - Docs Prep Agent

### Purpose
Downloads documents, extracts entities, produces `doc_context`

### Tools Required
- ✅ `get_loan_context`
- ✅ `list_required_documents`
- ✅ `download_documents`
- ✅ `extract_entities_from_docs`
- ✅ `log_issue`

### Fields Needed (Read Only)

| Field Description | Encompass Field ID |
|---|---|
| Loan Number | 364 |
| Loan Type | 1172 |
| Loan Program | 1401 |
| Loan Purpose | 19 |
| Subject Property State | 14 |
| Core Milestone | CoreMilestone |
| Loan Status | 1393 |

### Agent Workflow

```python
def docs_prep_agent(loan_id):
    # Step 1: Get loan context
    context = get_loan_context(loan_id)
    
    # Step 2: Check preconditions
    if not context['flags']['is_ctc']:
        log_issue(loan_id, "critical", "Loan is not CTC", context)
        return {"status": "failed", "reason": "Not CTC"}
    
    if not context['flags']['cd_approved']:
        log_issue(loan_id, "critical", "CD not approved", context)
        return {"status": "failed", "reason": "CD not approved"}
    
    # Step 3: Get required documents
    required_docs = list_required_documents(loan_id)
    
    # Step 4: Download documents
    documents = download_documents(loan_id, required_docs)
    
    # Step 5: Check if critical docs are missing
    critical_docs = ["1003", "Approval Final", "MI Certificate"]
    missing = [doc for doc in critical_docs if doc not in [d['category'] for d in documents]]
    
    if missing:
        log_issue(loan_id, "critical", f"Missing critical docs: {missing}", {"missing": missing})
        return {"status": "failed", "reason": f"Missing docs: {missing}"}
    
    # Step 6: Extract entities and build doc_context
    doc_context = extract_entities_from_docs(documents)
    
    # Step 7: Return doc_context for next agent
    return {
        "status": "success",
        "doc_context": doc_context,
        "documents_processed": len(documents)
    }
```

### Output Schema
```json
{
  "status": "success|failed",
  "reason": "...", (if failed)
  "doc_context": {...},  (the canonical doc_context JSON)
  "documents_processed": 12
}
```

---

## Phase 3: Agent 2 - Docs Draw Core Agent

### Purpose
**The workhorse** - Updates Encompass fields across 5 phases using `doc_context`

### Tools Required
- ✅ `get_loan_context`
- ✅ `read_fields`
- ✅ `write_fields`
- ✅ `log_issue`
- ✅ Access to `doc_context` from Docs Prep Agent

### Internal Phases

#### **Phase 1: Borrower & Loan Officer**
#### **Phase 2: Contacts & Vendors**
#### **Phase 3: Property & Program**
#### **Phase 4: Financial Setup & Itemization**
#### **Phase 5: Closing Disclosure Pages (1-4)**

---

### Phase 1: Borrower & Loan Officer

**Fields to Read/Write:**

| Field Description | Encompass Field ID | Source in doc_context |
|---|---|---|
| Borrower First Name | 4000 | borrowers[0].first_name |
| Borrower Middle Name | 4001 | borrowers[0].middle_name |
| Borrower Last Name | 4002 | borrowers[0].last_name |
| Borrower Suffix | 4003 | borrowers[0].suffix |
| Borrower First/Middle Name | 36 | borrowers[0].first_name + middle_name |
| Borrower Last Name/Suffix | 37 | borrowers[0].last_name + suffix |
| Borrower SSN | 65 | borrowers[0].ssn |
| Borrower Home Phone | 66 | borrowers[0].phone_home |
| Borrower Work Email | 1178 | borrowers[0].email |
| Co-Borrower First Name | 4004 | borrowers[1].first_name |
| Co-Borrower Middle Name | 4005 | borrowers[1].middle_name |
| Co-Borrower Last Name | 4006 | borrowers[1].last_name |
| Co-Borrower Suffix | 4007 | borrowers[1].suffix |
| Co-Borrower SSN | 97 | borrowers[1].ssn |
| Co-Borrower Home Phone | 98 | borrowers[1].phone_home |
| MERS MIN Number | 1051 | (generated/verified) |
| **Vesting Fields:** | | |
| Borrower Vesting Type | 4008 | vesting.vesting_type |
| Borrower Vesting Corp/Trust Name | 1859 | vesting.trust_name |
| Borrower Vesting Org State | 1860 | vesting.trust_state |
| Borrower Vesting Org Tax ID | 1862 | vesting.trust_tax_id |
| Borrower Vesting Beneficiaries | 2970 | vesting.beneficiaries |
| Borrower Vesting Final to Read | 1867 | vesting.final_vesting_to_read |
| Occupancy Type | 3335 | property.occupancy |
| **Loan Officer Fields:** | | |
| Loan Officer | 317 | loan_officer.name |
| NMLS Loan Originator ID | 3238 | loan_officer.nmls_id |

**Agent Logic:**
```python
def phase_1_borrower_lo(loan_id, doc_context):
    # Read current Encompass values
    current_fields = read_fields(loan_id, [
        "4000", "4001", "4002", "4003", "65", "66",
        "4004", "4005", "4006", "4007", "97", "98",
        "1051", "4008", "1859", "1860", "1862", "2970", "1867",
        "317", "3238"
    ])
    
    # Build updates based on doc_context
    updates = []
    issues = []
    
    # Borrower name fields
    if doc_context['borrowers'][0]['first_name'] != current_fields['4000']:
        updates.append({
            "field_id": "4000",
            "value": doc_context['borrowers'][0]['first_name'],
            "reason": "From 1003"
        })
    
    # ... repeat for all fields
    
    # Check for mismatches that need human review
    if doc_context['borrowers'][0]['ssn'] != current_fields['65']:
        issues.append({
            "severity": "high",
            "field": "65",
            "message": "SSN mismatch between document and Encompass",
            "doc_value": doc_context['borrowers'][0]['ssn'],
            "encompass_value": current_fields['65']
        })
    
    # Write updates
    if updates:
        write_fields(loan_id, updates)
    
    # Log issues
    for issue in issues:
        log_issue(loan_id, issue['severity'], issue['message'], issue)
    
    return {
        "phase": "Borrower & LO",
        "updates_made": len(updates),
        "issues_logged": len(issues),
        "status": "success" if not issues else "warning"
    }
```

---

### Phase 2: Contacts & Vendors

**Fields to Read/Write:**

| Field Description | Encompass Field ID | Source in doc_context |
|---|---|---|
| **Closing Location:** | | |
| Subject Property City | 12 | property.city |
| Subject Property State | 14 | property.state |
| Subject Property County | 13 | property.county |
| **Title Company:** | | |
| Title Insurance Company Name | 411 | contacts.title_company.name |
| Title Co Contact | 416 | contacts.title_company.contact |
| Title Co Phone | 417 | contacts.title_company.phone |
| **Escrow Company:** | | |
| Escrow Company Name | 610 | contacts.escrow_company.name |
| Escrow Co Contact | 611 | contacts.escrow_company.contact |
| Escrow Co Phone | 615 | contacts.escrow_company.phone |
| **Hazard Insurance:** | | |
| Hazard Insurance Company Name | L252 | contacts.hazard_insurance.name |
| Hazard Ins Co Phone | VEND.X163 | contacts.hazard_insurance.phone |
| **Flood Insurance:** | | |
| Flood Insurance Company Name | 1500 | contacts.flood_insurance.name |
| Flood Ins Co Phone | VEND.X19 | contacts.flood_insurance.phone |

---

### Phase 3: Property & Program

**Fields to Read/Write:**

| Field Description | Encompass Field ID | Source in doc_context |
|---|---|---|
| **Property Info:** | | |
| Subject Property Type | 1041 | property.type |
| Subject Property Address | 11 | property.address |
| Subject Property City | 12 | property.city |
| Subject Property State | 14 | property.state |
| Subject Property Zip | 15 | property.zip |
| Subject Property County | 13 | property.county |
| Subject Property # Units | 16 | property.units |
| Subject Property Year Built | 18 | property.year_built |
| Subject Property Legal Desc1 | 17 | property.legal_description |
| Subject Property Purchase Price | 136 | property.purchase_price |
| Appraised Value | 356 | property.appraised_value |
| **Program-Specific (FHA):** | | |
| Agency Case # | 1040 | program.agency_case_number |
| **Program-Specific (VA):** | | |
| VA Veteran Loan Code | 958 | program.va_loan_code |
| VA Loan Summ Total Disc Points | VASUMM.X45 | program.va_disc_points |

**Conditional Logic:**
```python
def phase_3_property_program(loan_id, doc_context):
    loan_type = doc_context['program']['loan_type']
    
    # Base property fields (always update)
    base_updates = [...]
    
    # Conditional program fields
    if loan_type == "FHA":
        fha_updates = [
            {"field_id": "1040", "value": doc_context['program']['agency_case_number']}
        ]
        base_updates.extend(fha_updates)
    
    elif loan_type == "VA":
        va_updates = [
            {"field_id": "958", "value": doc_context['program']['va_loan_code']},
            {"field_id": "VASUMM.X45", "value": doc_context['program']['va_disc_points']}
        ]
        base_updates.extend(va_updates)
    
    elif loan_type == "USDA":
        usda_updates = [...]
        base_updates.extend(usda_updates)
    
    write_fields(loan_id, base_updates)
    
    return {"phase": "Property & Program", "updates_made": len(base_updates)}
```

---

### Phase 4: Financial Setup & Itemization

**Fields to Read/Write:**

| Field Description | Encompass Field ID | Source in doc_context |
|---|---|---|
| **Loan Terms:** | | |
| Loan Amount | 1109 | loan_terms.loan_amount |
| Total Loan Amount | 2 | loan_terms.loan_amount |
| Note Rate | 3 | loan_terms.note_rate |
| Loan Term | 4 | loan_terms.loan_term |
| Amortization Type | 608 | loan_terms.amortization_type |
| Closing Date | 748 | loan_terms.closing_date |
| Lien Position | 420 | loan_terms.lien_position |
| **LTV/CLTV:** | | |
| Down Payment Amount | 1335 | financial.down_payment |
| Down Payment % | 1771 | (calculated) |
| **Escrow:** | | |
| Impound Types | 2294 | financial.escrow_setup |
| Impounds Waived | 2293 | financial.escrow_setup |
| **Mortgage Insurance:** | | |
| Insurance Mtg Ins Pymt 1 | 1766 | financial.mortgage_insurance.premium |
| **Fees:** | | |
| Fees Loan Origination Fee Borr | 454 | fees.origination_fee |
| Fees Loan Discount Fee % | 1061 | fees.discount_points |
| Non-Specific Lender Credit | 4794 | fees.lender_credits |

---

### Phase 5: Closing Disclosure Pages (1-4)

**Fields to Read/Write:**

| Field Description | Encompass Field ID | Source in doc_context |
|---|---|---|
| **CD Page 1:** | | |
| CD Changed Circumstance Chkbx | CD1.X61 | (check if needed) |
| **CD Page 2:** | | |
| CD Last Disclosed Loan Costs | CD2.XLDLC | fees.loan_costs |
| CD Last Disclosed Other Costs | CD2.XLDOC | fees.other_costs |
| CD Last Disclosed Lender Credits | CD2.XLDLCR | fees.lender_credits |
| **CD Page 3:** | | |
| Cash To Close | CD3.X23 | financial.cash_to_close |
| Loan Amount (CD3) | CD3.X81 | loan_terms.loan_amount |
| From To Borrower | CD3.X48 | (calculated) |
| **CD Page 4:** | | |
| Negative Amortization | CD4.X2 | loan_terms.neg_am |
| Escrow status | CD4.X fields | financial.escrow_setup |

---

### Core Agent Full Workflow

```python
def docs_draw_core_agent(loan_id, doc_context):
    results = {
        "phases": [],
        "total_updates": 0,
        "total_issues": 0
    }
    
    # Phase 1: Borrower & LO
    phase1 = phase_1_borrower_lo(loan_id, doc_context)
    results['phases'].append(phase1)
    results['total_updates'] += phase1['updates_made']
    results['total_issues'] += phase1['issues_logged']
    
    # Phase 2: Contacts & Vendors
    phase2 = phase_2_contacts_vendors(loan_id, doc_context)
    results['phases'].append(phase2)
    results['total_updates'] += phase2['updates_made']
    
    # Phase 3: Property & Program
    phase3 = phase_3_property_program(loan_id, doc_context)
    results['phases'].append(phase3)
    results['total_updates'] += phase3['updates_made']
    
    # Phase 4: Financial Setup
    phase4 = phase_4_financial_setup(loan_id, doc_context)
    results['phases'].append(phase4)
    results['total_updates'] += phase4['updates_made']
    
    # Phase 5: CD Pages
    phase5 = phase_5_cd_pages(loan_id, doc_context)
    results['phases'].append(phase5)
    results['total_updates'] += phase5['updates_made']
    
    return results
```

---

## Phase 4: Agent 3 - Audit & Compliance Agent

### Purpose
Final verification before ordering docs

### Tools Required
- ✅ `read_fields`
- ✅ `run_compliance_check`
- ✅ `get_compliance_results`
- ✅ `log_issue`

### Fields Needed (Read Only - for verification)

**All critical fields that must be populated:**

| Field Description | Encompass Field ID | Verification Logic |
|---|---|---|
| Borrower First Name | 4000 | Must not be empty |
| Borrower Last Name | 4002 | Must not be empty |
| Borrower SSN | 65 | Must be valid format |
| Subject Property Address | 11 | Must not be empty |
| Subject Property State | 14 | Must be valid state code |
| Loan Amount | 1109 | Must be > 0 |
| Note Rate | 3 | Must be > 0 |
| Closing Date | 748 | Must be future date |
| Vesting Type | 4008 | Must match state requirements |
| Agency Case # (if FHA/VA/USDA) | 1040 | Must be populated for govt loans |
| Title Company Name | 411 | Must not be empty |
| Escrow Company Name | 610 | Must not be empty |

### Agent Workflow

```python
def audit_compliance_agent(loan_id):
    # Step 1: Run field completeness check
    required_fields = [
        "4000", "4002", "65", "11", "14", 
        "1109", "3", "748", "4008", "411", "610"
    ]
    
    field_values = read_fields(loan_id, required_fields)
    
    missing_fields = []
    for field_id, value in field_values.items():
        if not value or value == "":
            missing_fields.append(field_id)
    
    if missing_fields:
        log_issue(loan_id, "critical", f"Missing required fields: {missing_fields}", 
                 {"missing_fields": missing_fields})
        return {
            "status": "failed",
            "reason": "Missing required fields",
            "missing_fields": missing_fields
        }
    
    # Step 2: Run cross-field consistency checks
    # Example: Borrower name consistency
    first_name = field_values["4000"]
    # ... check against other name fields
    
    # Step 3: Run Mavent compliance check
    run_id = run_compliance_check(loan_id, "Mavent")
    
    # Wait for results (or poll)
    time.sleep(5)  # In reality, implement proper polling
    
    compliance_results = get_compliance_results(loan_id)
    
    # Step 4: Evaluate compliance results
    if compliance_results['status'] == "fail":
        critical_issues = [i for i in compliance_results['issues'] if i['severity'] == 'critical']
        
        if critical_issues:
            for issue in critical_issues:
                log_issue(loan_id, "critical", issue['message'], issue)
            
            return {
                "status": "failed",
                "reason": "Mavent compliance failures",
                "issues": critical_issues
            }
    
    # Step 5: All checks passed
    return {
        "status": "success",
        "compliance_status": compliance_results['status'],
        "warnings": [i for i in compliance_results['issues'] if i['severity'] == 'warning']
    }
```

---

## Phase 5: Order Docs & Distribution (Deterministic Flow)

### Purpose
Trigger docs generation and distribution

### Tools Required
- ✅ `order_docs`
- ✅ `update_milestone`
- ✅ `send_closing_package`
- ✅ `log_issue`

### Fields Needed

| Field Description | Encompass Field ID | Purpose |
|---|---|---|
| Loan Officer | 317 | Get LO email for distribution |
| Loan Processor | 362 | Get processor email |
| Loan Closer | 1855 | Get closer email |
| Escrow Company Name | 610 | Get escrow contact |
| Escrow Co Contact | 611 | Get contact email |
| Title Insurance Company Name | 411 | Get title contact |
| Title Co Contact | 416 | Get contact email |

### Workflow

```python
def order_docs_distribution(loan_id):
    # Step 1: Order docs
    result = order_docs(loan_id)
    
    if not result['success']:
        log_issue(loan_id, "critical", f"Docs ordering failed: {result['error']}", result)
        return {"status": "failed", "reason": "Docs ordering failed"}
    
    # Step 2: Update milestone
    today = datetime.now().strftime("%m/%d/%Y")
    update_milestone(loan_id, "Finished", f"DOCS Out on {today}")
    
    # Step 3: Get recipient list
    fields = read_fields(loan_id, ["317", "362", "1855", "611", "416"])
    
    recipients = {
        "loan_officer": get_user_email(fields["317"]),
        "processor": get_user_email(fields["362"]),
        "escrow": get_contact_email(fields["611"]),
        "title": get_contact_email(fields["416"])
    }
    
    # Step 4: Send closing package
    send_result = send_closing_package(loan_id, recipients)
    
    if not send_result['success']:
        log_issue(loan_id, "high", f"Failed to send to some recipients: {send_result['failed']}", 
                 send_result)
    
    return {
        "status": "success",
        "doc_package_id": result['doc_package_id'],
        "sent_to": send_result['sent_to'],
        "failed": send_result['failed']
    }
```

---

## Phase 6: Full Orchestration

### Main Orchestrator

```python
def docs_draw_orchestrator(loan_id):
    print(f"Starting Docs Draw process for loan {loan_id}")
    
    # STEP 1: Docs Prep Agent
    print("Step 1: Running Docs Prep Agent...")
    prep_result = docs_prep_agent(loan_id)
    
    if prep_result['status'] != 'success':
        return {
            "status": "failed",
            "stage": "prep",
            "reason": prep_result['reason']
        }
    
    doc_context = prep_result['doc_context']
    print(f"✓ Docs Prep complete. Processed {prep_result['documents_processed']} documents")
    
    # STEP 2: Docs Draw Core Agent
    print("Step 2: Running Docs Draw Core Agent...")
    core_result = docs_draw_core_agent(loan_id, doc_context)
    print(f"✓ Core Agent complete. Made {core_result['total_updates']} updates")
    
    if core_result['total_issues'] > 0:
        print(f"⚠ Warning: {core_result['total_issues']} issues logged for review")
        # Optionally halt here and wait for human review
        # return {"status": "pending_review", "issues": core_result['total_issues']}
    
    # STEP 3: Audit & Compliance Agent
    print("Step 3: Running Audit & Compliance Agent...")
    audit_result = audit_compliance_agent(loan_id)
    
    if audit_result['status'] != 'success':
        return {
            "status": "failed",
            "stage": "compliance",
            "reason": audit_result['reason'],
            "issues": audit_result.get('issues', [])
        }
    
    print("✓ Audit & Compliance passed")
    
    # STEP 4: Order Docs & Distribution
    print("Step 4: Ordering docs and distributing...")
    distribution_result = order_docs_distribution(loan_id)
    
    if distribution_result['status'] != 'success':
        return {
            "status": "failed",
            "stage": "distribution",
            "reason": distribution_result['reason']
        }
    
    print(f"✓ Docs ordered and sent to {len(distribution_result['sent_to'])} recipients")
    
    # SUCCESS
    return {
        "status": "success",
        "summary": {
            "documents_processed": prep_result['documents_processed'],
            "fields_updated": core_result['total_updates'],
            "issues_logged": core_result['total_issues'],
            "compliance_warnings": len(audit_result.get('warnings', [])),
            "doc_package_id": distribution_result['doc_package_id'],
            "recipients": distribution_result['sent_to']
        }
    }
```

---

## Summary of Fields by Agent

### Agent 1: Docs Prep Agent
**Fields Needed (Read Only):**
- Loan Number (364)
- Loan Type (1172)
- Loan Program (1401)
- Loan Purpose (19)
- Subject Property State (14)
- Core Milestone (CoreMilestone)

**Outputs:** `doc_context` JSON

---

### Agent 2: Docs Draw Core Agent
**Fields Needed (Read/Write):**

**Phase 1 - Borrower & LO (21 fields):**
- 4000, 4001, 4002, 4003, 36, 37, 65, 66, 1178
- 4004, 4005, 4006, 4007, 97, 98
- 1051, 4008, 1859, 1860, 1862, 2970, 1867
- 317, 3238

**Phase 2 - Contacts & Vendors (12 fields):**
- 12, 13, 14
- 411, 416, 417
- 610, 611, 615
- L252, VEND.X163
- 1500, VEND.X19

**Phase 3 - Property & Program (15+ fields):**
- 1041, 11, 12, 14, 15, 13, 16, 18, 17, 136, 356
- 1040 (FHA/USDA)
- 958, VASUMM.X45 (VA)

**Phase 4 - Financial Setup (15+ fields):**
- 1109, 2, 3, 4, 608, 748, 420
- 1335, 1771
- 2294, 2293
- 1766
- 454, 1061, 4794

**Phase 5 - CD Pages (10+ fields):**
- CD1.X61
- CD2.XLDLC, CD2.XLDOC, CD2.XLDLCR
- CD3.X23, CD3.X81, CD3.X48
- CD4.X2, CD4.X fields

**Total: ~70-80 fields across all phases**

---

### Agent 3: Audit & Compliance Agent
**Fields Needed (Read Only):**
- All critical fields for verification (~40 fields)
- Mavent compliance results (external API)

---

### Deterministic Flow: Order Docs & Distribution
**Fields Needed (Read Only):**
- 317, 362, 1855 (user IDs for emails)
- 610, 611, 411, 416 (contact info)

---

## Implementation Priority

### Week 1-2: Foundation
1. ✅ Implement `get_loan_context`
2. ✅ Implement `read_fields` / `write_fields`
3. ✅ Implement `log_issue`
4. ✅ Design `doc_context` schema

### Week 2-3: Document Pipeline
1. ✅ Implement `list_required_documents`
2. ✅ Implement `download_documents`
3. ✅ Implement `extract_entities_from_docs`
4. ✅ Build Docs Prep Agent

### Week 3-5: Core Agent
1. ✅ Implement Phase 1 (Borrower & LO)
2. ✅ Implement Phase 2 (Contacts & Vendors)
3. ✅ Implement Phase 3 (Property & Program)
4. ✅ Implement Phase 4 (Financial Setup)
5. ✅ Implement Phase 5 (CD Pages)
6. ✅ Integrate all phases

### Week 5-6: Compliance & Distribution
1. ✅ Implement `run_compliance_check` / `get_compliance_results`
2. ✅ Build Audit & Compliance Agent
3. ✅ Implement `order_docs` / `send_closing_package`
4. ✅ Build Order Docs & Distribution flow

### Week 7-8: Testing & Integration
1. ✅ End-to-end testing with test loans
2. ✅ Refinement based on results
3. ✅ Deploy to staging environment
4. ✅ Pilot with real loans

---

## Key Success Metrics

1. **Docs Prep Agent:**
   - Document download success rate > 95%
   - Entity extraction accuracy > 90%
   - Missing critical doc detection rate: 100%

2. **Docs Draw Core Agent:**
   - Field update accuracy > 95%
   - False positive issue rate < 5%
   - Processing time < 2 minutes per loan

3. **Audit & Compliance Agent:**
   - Mavent pass rate after agent processing > 85%
   - Critical issue detection rate: 100%

4. **Overall:**
   - End-to-end success rate > 75% (no human intervention)
   - Time savings vs manual process > 70%
   - Zero critical errors in production

---

**Generated**: Based on docs_draw_agentic_architecture.md MVP design
**Date**: November 28, 2025



