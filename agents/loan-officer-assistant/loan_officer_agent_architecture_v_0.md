# Loan Officer Agent (LOA) – Architecture Specification v0.3

## 1. Summary

### 1.1 Overview

The **Loan Officer Assistant Agent** is an LLM-powered agent that automates Needs List and Gap Analysis generation for mortgage loans. Given a loan ID, the agent:

1. **Retrieves loan context** from Encompass (borrower data, loan terms, property info, milestones, eFolder document list)
2. **Retrieves document intelligence** from Rack & Stack (classified documents, metadata, coverage status)
3. **Reasons over the combined context** to identify gaps against the questionnaire requirements
4. **Generates a prioritized Needs List** with missing data, missing documents, and data-document mismatches
5. **Presents actionable findings** to the Loan Officer Assistant for review

### 1.2 What the Agent Is

The Loan Officer Assistant Agent is a **reasoning agent** that operates as a decision-support system for Loan Officer Assistants. It combines:

- **Structured data retrieval** (Encompass loan fields, Rack & Stack document manifest)
- **Rules-based gap detection** (questionnaire requirements engine)
- **LLM reasoning** (prioritization, natural language output, action recommendations)

The agent does not autonomously take actions on loans. It analyzes, reasons, and recommends—the human LOA makes final decisions.

### 1.3 How It Works

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        LOAN OFFICER ASSISTANT AGENT                          │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   INPUT: loan_id                                                             │
│      │                                                                       │
│      ▼                                                                       │
│   ┌────────────────────────────────────────────────────────────────────┐    │
│   │  1. GATHER LOAN CONTEXT                                            │    │
│   │     • Encompass API → LoanFacts (fields, borrowers, property)      │    │
│   │     • Rack & Stack API → DocCoverage (documents, classifications)  │    │
│   └────────────────────────────────────────────────────────────────────┘    │
│      │                                                                       │
│      ▼                                                                       │
│   ┌────────────────────────────────────────────────────────────────────┐    │
│   │  2. REASON OVER CONTEXT                                            │    │
│   │     • Compare LoanFacts against questionnaire required_fields      │    │
│   │     • Compare DocCoverage against questionnaire required_documents │    │
│   │     • Evaluate conditional_requirements based on loan scenario     │    │
│   │     • Detect mismatches between stated data and document content   │    │
│   └────────────────────────────────────────────────────────────────────┘    │
│      │                                                                       │
│      ▼                                                                       │
│   ┌────────────────────────────────────────────────────────────────────┐    │
│   │  3. GENERATE GAP ANALYSIS                                          │    │
│   │     • Structured NeedsListResult with gap items                    │    │
│   │     • Severity classification (CRITICAL, WARN, INFO)               │    │
│   │     • LLM synthesizes human-readable summary and action items      │    │
│   └────────────────────────────────────────────────────────────────────┘    │
│      │                                                                       │
│      ▼                                                                       │
│   OUTPUT: Prioritized Needs List for LOA review                              │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 1.4 MVP Scope

| In Scope | Out of Scope |
|----------|--------------|
| Conventional purchase/refi loans | FHA/VA/USDA-specific logic |
| Data completeness gaps (missing fields) | Full underwriting decisioning |
| Document coverage gaps (missing docs) | Direct borrower communication |
| Data-document mismatches | Automatic Encompass writes |
| Human-readable gap summary | FNMA/FHLMC guideline citations |
| Proposed actions for LOA | Multi-lender overlay rules |

---

## 2. Agentic Pattern

### 2.1 Agent Definition

The **Loan Officer Assistant Agent** is a tool-augmented LLM agent that:

1. **Invokes tools** to gather loan context (Encompass) and document coverage (Rack & Stack)
2. **Reasons over the combined context** using a rules engine driven by `questionnaire_mapping.json`
3. **Synthesizes findings** into a prioritized, human-readable Needs List via LLM

The agent operates in a **single-pass workflow**: gather → analyze → present. It does not loop or retry autonomously.

### 2.2 Agent Reasoning Process

The agent reasons over loan context to generate the gap analysis as follows:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AGENT REASONING FLOW                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CONTEXT ASSEMBLY                                                           │
│  ─────────────────                                                          │
│  The agent assembles a complete picture of the loan by combining:           │
│                                                                             │
│  ┌─────────────────────────┐    ┌─────────────────────────┐                │
│  │     LOAN FACTS          │    │     DOC COVERAGE        │                │
│  │     (from Encompass)    │    │     (from Rack & Stack) │                │
│  ├─────────────────────────┤    ├─────────────────────────┤                │
│  │ • Borrower names, SSN   │    │ • Paystubs: PRESENT     │                │
│  │ • Employment info       │    │ • W-2s: MISSING         │                │
│  │ • Property address      │    │ • Bank statements: STALE│                │
│  │ • Loan amount, LTV      │    │ • Purchase contract: OK │                │
│  │ • Marital status        │    │ • Gift letter: MISSING  │                │
│  │ • Income sources        │    │ • Gov ID: PRESENT       │                │
│  └─────────────────────────┘    └─────────────────────────┘                │
│              │                              │                               │
│              └──────────────┬───────────────┘                               │
│                             ▼                                               │
│  GAP DETECTION                                                              │
│  ─────────────                                                              │
│  The agent evaluates the combined context against requirements:             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  QUESTIONNAIRE REQUIREMENTS (questionnaire_mapping.json)            │   │
│  │                                                                     │   │
│  │  For each section/question:                                         │   │
│  │  1. Check if required_fields are populated in LoanFacts             │   │
│  │  2. Check if required_documents are present in DocCoverage          │   │
│  │  3. Evaluate conditional_requirements based on field values         │   │
│  │                                                                     │   │
│  │  Example:                                                           │   │
│  │  • marital_status = "Separated" → require "Separation Agreement"   │   │
│  │  • is_self_employed = true → require "1040s", "P&L Statement"      │   │
│  │  • downpayment_source includes "Gift" → require "Gift Letter"      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                             │                                               │
│                             ▼                                               │
│  OUTPUT SYNTHESIS                                                           │
│  ────────────────                                                           │
│  The LLM reasons over the structured gap items to produce:                  │
│                                                                             │
│  • Priority ranking based on severity and loan stage                        │
│  • Natural language summary of loan status                                  │
│  • Specific action items for the LOA                                        │
│  • Proposed Encompass field corrections (if requested)                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 LangGraph Implementation

The agent is implemented as a LangGraph StateGraph with three nodes:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LangGraph StateGraph                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   START     │───▶│  GATHER     │───▶│  ANALYZE    │───▶│  PRESENT    │  │
│  │             │    │  DATA       │    │  GAPS       │    │  RESULTS    │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                            │                  │                  │          │
│                     ┌──────┴──────┐           │                  │          │
│                     ▼             ▼           ▼                  ▼          │
│              ┌───────────┐ ┌───────────┐ ┌───────────┐    ┌───────────┐    │
│              │ TOOL:     │ │ TOOL:     │ │ TOOL:     │    │ LLM:      │    │
│              │ fetch     │ │ fetch     │ │ gap       │    │ synthesize│    │
│              │ loan      │ │ doc       │ │ analyzer  │    │ findings  │    │
│              │ context   │ │ coverage  │ │           │    │           │    │
│              └───────────┘ └───────────┘ └───────────┘    └───────────┘    │
│                    │             │              │                │          │
│                    ▼             ▼              ▼                ▼          │
│              ┌───────────┐ ┌───────────┐ ┌───────────┐    ┌───────────┐    │
│              │ LoanFacts │ │DocCoverage│ │NeedsList  │    │ Summary + │    │
│              │           │ │           │ │ Result    │    │ Actions   │    │
│              └───────────┘ └───────────┘ └───────────┘    └───────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Node Descriptions:
─────────────────
GATHER DATA (deterministic):
  • Calls Encompass API to retrieve loan fields, milestones, eFolder list
  • Calls Rack & Stack API to retrieve document manifest and classifications
  • Normalizes data into LoanFacts and DocCoverage structures

ANALYZE GAPS (deterministic):
  • Loads questionnaire_mapping.json as the requirements specification
  • Iterates each question's required_fields against LoanFacts
  • Iterates each question's required_documents against DocCoverage
  • Evaluates conditional_requirements to trigger additional checks
  • Outputs structured NeedsListResult with all gap items

PRESENT RESULTS (LLM-powered):
  • Receives structured LoanFacts, DocCoverage, and NeedsListResult
  • Reasons over severity, loan stage, and gap patterns
  • Generates prioritized human-readable summary
  • Proposes specific actions for the LOA
```

### 2.4 Component Classification

| Component | Type | Role |
|-----------|------|------|
| `fetch_loan_context` | **Tool** (deterministic) | Retrieve and normalize Encompass loan data |
| `fetch_doc_coverage` | **Tool** (deterministic) | Retrieve and normalize Rack & Stack document data |
| `run_gap_analysis` | **Tool** (deterministic) | Execute rules engine over questionnaire requirements |
| `present_results` | **LLM Node** | Reason over findings, generate summary and actions |

### 2.6 LangGraph State Schema

```python
from typing import TypedDict, Optional, List
from langgraph.graph import StateGraph

class LOAState(TypedDict):
    # Inputs
    loan_id: str
    mode: str  # "fast" | "full" | "refresh_docs"
    
    # Gathered data
    loan_facts: Optional[dict]
    doc_coverage: Optional[dict]
    
    # Analysis results
    needs_list: Optional[dict]
    
    # Outputs
    summary: Optional[str]
    write_proposals: Optional[List[dict]]
    
    # Control
    status: str  # "running" | "complete" | "error"
    errors: List[str]
```

### 2.7 LangGraph Workflow Definition

```python
from langgraph.graph import StateGraph, END

def build_loa_graph():
    graph = StateGraph(LOAState)
    
    # Nodes
    graph.add_node("gather_data", gather_data_node)
    graph.add_node("analyze_gaps", analyze_gaps_node)
    graph.add_node("present_results", present_results_node)
    
    # Edges
    graph.set_entry_point("gather_data")
    graph.add_edge("gather_data", "analyze_gaps")
    graph.add_edge("analyze_gaps", "present_results")
    graph.add_edge("present_results", END)
    
    return graph.compile()
```

---

## 3. Tools

### 3.1 `fetch_loan_context`

**Type:** Deterministic tool

**Input:**
```python
loan_id: str
```

**Output:**
```python
LoanFacts: dict  # Normalized loan data
```

**Implementation:**
1. Call `encompass/v3/loans/{loan_id}/fieldReader` with field list
2. Call `encompass/v1/loans/{loan_id}/milestones`
3. Call `encompass/v3/loans/{loan_id}/attachments`
4. Normalize to `LoanFacts` schema
5. Compute `scenario_tag` for rule routing

**Field Mapping (subset):**

| Encompass Field | LoanFacts Field |
|-----------------|-----------------|
| `4000` | `borrowers[0].first_name` |
| `4002` | `borrowers[0].last_name` |
| `65` | `borrowers[0].ssn` |
| `52` | `borrowers[0].dob` |
| `1268` | `borrowers[0].email` |
| `66` | `borrowers[0].phone` |
| `BE0015` | `borrowers[0].employer_name` |
| `BE0012` | `borrowers[0].employer_phone` |
| `11` | `property.address` |
| `12` | `property.city` |
| `14` | `property.state` |
| `15` | `property.zip` |
| `1109` | `loan_amount` |
| `136` | `purchase_price` |
| `19` | `loan_purpose` |
| `1172` | `loan_type` |
| `1811` | `occupancy_type` |
| `1041` | `property_type` |

---

### 3.2 `fetch_doc_coverage`

**Type:** Deterministic tool

**Input:**
```python
loan_id: str
efolder_docs: List[dict]  # From fetch_loan_context
refresh: bool
```

**Output:**
```python
DocCoverage: dict  # Document coverage status per doc type
```

**Implementation:**
1. Check for cached R&S manifest for `loan_id`
2. If missing and `refresh=True`: trigger R&S job, wait for completion
3. Parse manifest `documents[]` array
4. Apply category → doc_type mapping
5. Aggregate coverage status per doc_type

**Category Mapping (subset):**

| R&S Category Pattern | Logical Doc Type |
|---------------------|------------------|
| `Paystub`, `Pay Stub` | `PAYSTUB` |
| `W-2`, `W2` | `W2` |
| `1040`, `Tax Return` | `TAX_RETURN` |
| `Driver License`, `Passport`, `State ID` | `GOVERNMENT_ID` |
| `Purchase Contract`, `Sales Contract` | `PURCHASE_CONTRACT` |
| `Bank Statement` | `BANK_STATEMENT` |
| `Gift Letter` | `GIFT_LETTER` |
| `DD-214` | `DD214` |
| `VA Disability Award` | `VA_DISABILITY_LETTER` |

---

### 3.3 `run_gap_analysis`

**Type:** Deterministic tool (rules engine)

**Input:**
```python
loan_facts: dict
doc_coverage: Optional[dict]
questionnaire_config: dict  # Loaded from questionnaire_mapping.json
```

**Output:**
```python
NeedsListResult: dict  # Structured gap items
```

**Implementation:** See Section 4.

---

## 4. Gap Analysis Engine

### 4.1 Rules Source: `questionnaire_mapping.json`

The gap analysis engine evaluates rules defined in `questionnaire_mapping.json`. Each question in the questionnaire maps to:
- **Required fields** to check for presence/validity
- **Required documents** to check for presence
- **Conditional requirements** to evaluate based on field values

### 4.2 Three-Phase Analysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 1: Data Completeness                                                 │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Input: LoanFacts + questionnaire_mapping.json                              │
│  Logic: For each question, check if required_fields are populated           │
│  Output: DATA gap items (MISSING, INVALID)                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 2: Document Coverage                                                 │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Input: LoanFacts + DocCoverage + questionnaire_mapping.json                │
│  Logic: For each question, check if required_documents are present          │
│         Evaluate conditional_requirements for doc triggers                  │
│  Output: DOC gap items (MISSING, STALE, PARTIAL)                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 3: Data-Document Reconciliation                                      │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Input: LoanFacts + DocCoverage (with extractions)                          │
│  Logic: Compare extracted doc values to stated LoanFacts values             │
│  Output: MISMATCH gap items                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Phase 1: Data Completeness

**Algorithm:**

```python
def analyze_data_gaps(loan_facts: dict, questionnaire: dict) -> List[GapItem]:
    gaps = []
    
    for section in questionnaire["sections"]:
        for question in section["questions"]:
            # Check if question applies based on conditionals
            if not evaluate_conditions(question, loan_facts):
                continue
            
            for field in question["required_fields"]:
                value = get_field_value(loan_facts, field)
                
                if value is None or value == "":
                    gaps.append(GapItem(
                        id=f"DATA_{section['section_id']}_{question['question_id']}_{field}",
                        category=map_section_to_category(section["section_id"]),
                        type="DATA",
                        status="MISSING",
                        severity=determine_severity(question, field),
                        field_id=field,
                        label=f"Missing: {field}",
                        reason=question["prompt"],
                        action=f"Collect {field} from borrower"
                    ))
    
    return gaps
```

**Example Evaluation:**

Given `questionnaire_mapping.json` section:
```json
{
  "section_id": "borrower_profile",
  "questions": [{
    "question_id": "ssn_and_dob",
    "prompt": "Please provide your Social Security Number and Date of Birth.",
    "required_fields": ["borrower_ssn", "borrower_dob"]
  }]
}
```

And `loan_facts`:
```json
{
  "borrowers": [{
    "ssn": null,
    "dob": "1985-03-15"
  }]
}
```

Output:
```json
{
  "id": "DATA_borrower_profile_ssn_and_dob_borrower_ssn",
  "category": "BORROWER",
  "type": "DATA",
  "status": "MISSING",
  "severity": "CRITICAL",
  "field_id": "borrower_ssn",
  "label": "Missing: borrower_ssn",
  "reason": "Please provide your Social Security Number and Date of Birth.",
  "action": "Collect borrower_ssn from borrower"
}
```

### 4.4 Phase 2: Document Coverage

**Algorithm:**

```python
def analyze_doc_gaps(
    loan_facts: dict, 
    doc_coverage: dict, 
    questionnaire: dict
) -> List[GapItem]:
    gaps = []
    
    for section in questionnaire["sections"]:
        for question in section["questions"]:
            # Check if question applies
            if not evaluate_conditions(question, loan_facts):
                continue
            
            # Check required_documents
            for doc_name in question["required_documents"]:
                doc_type = map_doc_name_to_type(doc_name)
                coverage = doc_coverage["items"].get(doc_type)
                
                if coverage is None or coverage["status"] == "MISSING":
                    gaps.append(GapItem(
                        id=f"DOC_{section['section_id']}_{question['question_id']}_{doc_type}",
                        category="DOCS",
                        type="DOC",
                        status="MISSING",
                        severity="WARN",
                        doc_type=doc_type,
                        label=f"Missing document: {doc_name}",
                        reason=get_conditional_reason(question),
                        action=f"Request {doc_name} from borrower"
                    ))
            
            # Evaluate conditional document requirements
            for conditional in question["conditional_requirements"]:
                if requires_document(conditional) and condition_met(conditional, loan_facts):
                    doc_name = extract_doc_from_conditional(conditional)
                    doc_type = map_doc_name_to_type(doc_name)
                    coverage = doc_coverage["items"].get(doc_type)
                    
                    if coverage is None or coverage["status"] == "MISSING":
                        gaps.append(GapItem(
                            id=f"DOC_COND_{question['question_id']}_{doc_type}",
                            category="DOCS",
                            type="DOC",
                            status="MISSING",
                            severity="WARN",
                            doc_type=doc_type,
                            label=f"Missing document: {doc_name}",
                            reason=conditional,
                            action=f"Request {doc_name} from borrower"
                        ))
    
    return gaps
```

**Example Evaluation:**

Given conditional requirement:
```json
{
  "question_id": "marital_status",
  "conditional_requirements": [
    "If borrower_marital_status == 'Separated', collect Separation Agreement document."
  ]
}
```

And `loan_facts`:
```json
{
  "borrowers": [{
    "marital_status": "Separated"
  }]
}
```

And `doc_coverage`:
```json
{
  "items": {
    "SEPARATION_AGREEMENT": null
  }
}
```

Output:
```json
{
  "id": "DOC_COND_marital_status_SEPARATION_AGREEMENT",
  "category": "DOCS",
  "type": "DOC",
  "status": "MISSING",
  "severity": "WARN",
  "doc_type": "SEPARATION_AGREEMENT",
  "label": "Missing document: Separation Agreement",
  "reason": "If borrower_marital_status == 'Separated', collect Separation Agreement document.",
  "action": "Request Separation Agreement from borrower"
}
```

### 4.5 Phase 3: Data-Document Reconciliation

**Requires:** Field-level extractions from R&S (future capability)

**Algorithm:**

```python
def analyze_reconciliation_gaps(
    loan_facts: dict,
    doc_extractions: dict
) -> List[GapItem]:
    gaps = []
    
    # Define reconciliation rules
    reconciliation_rules = [
        ("borrowers[0].first_name", "GOVERNMENT_ID", "first_name"),
        ("borrowers[0].last_name", "GOVERNMENT_ID", "last_name"),
        ("borrowers[0].employer_name", "PAYSTUB", "employer_name"),
        ("property.address", "PURCHASE_CONTRACT", "property_address"),
    ]
    
    for loan_field, doc_type, doc_field in reconciliation_rules:
        loan_value = get_field_value(loan_facts, loan_field)
        doc_value = get_extraction(doc_extractions, doc_type, doc_field)
        
        if loan_value and doc_value and not values_match(loan_value, doc_value):
            gaps.append(GapItem(
                id=f"RECON_{loan_field}_{doc_type}",
                category="RECONCILIATION",
                type="MISMATCH",
                status="MISMATCH",
                severity="CRITICAL",
                field_id=loan_field,
                doc_type=doc_type,
                label=f"Mismatch: {loan_field}",
                reason=f"Encompass: '{loan_value}' vs Document: '{doc_value}'",
                action="Verify correct value and update Encompass or request corrected document"
            ))
    
    return gaps
```

---

## 5. LLM Agent Node

### 5.1 Purpose

The LLM node (`present_results`) transforms structured `NeedsListResult` into human-readable output and proposes remediation actions.

### 5.2 System Prompt

```
You are an assistant for Loan Officer Assistants (LOAs) at a mortgage company. 

Your task is to summarize a gap analysis for a loan file and present clear action items.

Input: You will receive structured data containing:
- loan_facts: Current loan data from Encompass
- needs_list: List of gap items with category, type, status, severity, and recommended actions

Output Requirements:
1. SUMMARY: 2-3 sentence overview of loan status and gap severity
2. CRITICAL ISSUES: List items with severity=CRITICAL that block loan progress
3. HIGH PRIORITY: List items with severity=WARN requiring attention
4. ACTION ITEMS: Numbered list of specific actions the LOA should take
5. WRITE PROPOSALS (if requested): Specific Encompass field updates to consider

Formatting:
- Use clear headers and bullet points
- Group related items together
- Prioritize by severity
- Be concise and actionable
- Do not include explanations of your process
```

### 5.3 User Prompt Template

```
Analyze this loan and generate a needs list summary.

## Loan Facts
{loan_facts_json}

## Gap Analysis Results
{needs_list_json}

## Instructions
- Summarize the loan status
- List critical blockers
- List high priority items  
- Provide numbered action items
- {if include_write_proposals} Propose specific Encompass field updates
```

### 5.4 Example LLM Output

```
## Loan Summary
Purchase loan for John Smith, $450,000 conventional, 80% LTV. 
3 critical issues blocking progress, 5 items requiring attention.

## Critical Issues
❌ **Missing SSN** - Required for credit pull (borrower_ssn)
❌ **Missing Government ID** - Required for identity verification
❌ **Employer name mismatch** - Encompass: "Acme Corp" vs Paystub: "Acme Corporation Inc"

## High Priority
⚠️ Paystubs older than 30 days - request current paystubs
⚠️ Bank statements needed - downpayment source is "Bank Accounts"
⚠️ Employer phone missing - needed for VOE
⚠️ 2-year address history incomplete
⚠️ Gift letter needed - gift funds indicated

## Action Items
1. Request SSN from borrower via secure portal
2. Request government-issued photo ID (driver's license or passport)
3. Clarify employer name discrepancy with borrower
4. Request paystubs dated within last 30 days
5. Request 2 months bank statements (all pages)
6. Collect employer HR phone number for VOE
7. Request previous address to complete 2-year history
8. Request signed gift letter from donor

## Proposed Encompass Updates
| Field | Current | Proposed | Source |
|-------|---------|----------|--------|
| BE0015 | Acme Corp | Acme Corporation Inc | Paystub |
```

---

## 6. Execution Flow

### 6.1 Entry Point

```python
async def run_loan_officer_agent(
    loan_id: str,
    mode: str = "full",  # "fast" | "full" | "refresh_docs"
    include_write_proposals: bool = False
) -> LOAResult:
    """
    Execute LOA workflow.
    
    Modes:
    - fast: Data gaps only, skip document processing
    - full: Data + document gaps, use cached R&S
    - refresh_docs: Trigger new R&S job
    """
    graph = build_loa_graph()
    
    initial_state = {
        "loan_id": loan_id,
        "mode": mode,
        "include_write_proposals": include_write_proposals,
        "status": "running",
        "errors": []
    }
    
    result = await graph.ainvoke(initial_state)
    return LOAResult(**result)
```

### 6.2 Node Implementations

**gather_data_node:**
```python
async def gather_data_node(state: LOAState) -> LOAState:
    # Always fetch loan context
    loan_facts = await fetch_loan_context(state["loan_id"])
    state["loan_facts"] = loan_facts
    
    # Fetch doc coverage unless fast mode
    if state["mode"] != "fast":
        doc_coverage = await fetch_doc_coverage(
            loan_id=state["loan_id"],
            efolder_docs=loan_facts.get("efolder_docs", []),
            refresh=(state["mode"] == "refresh_docs")
        )
        state["doc_coverage"] = doc_coverage
    
    return state
```

**analyze_gaps_node:**
```python
async def analyze_gaps_node(state: LOAState) -> LOAState:
    questionnaire = load_questionnaire_config()
    
    # Phase 1: Data completeness (always runs)
    data_gaps = analyze_data_gaps(state["loan_facts"], questionnaire)
    
    # Phase 2: Document coverage (if doc_coverage available)
    doc_gaps = []
    if state.get("doc_coverage"):
        doc_gaps = analyze_doc_gaps(
            state["loan_facts"], 
            state["doc_coverage"], 
            questionnaire
        )
    
    # Phase 3: Reconciliation (if extractions available)
    recon_gaps = []
    if state.get("doc_coverage", {}).get("extractions"):
        recon_gaps = analyze_reconciliation_gaps(
            state["loan_facts"],
            state["doc_coverage"]["extractions"]
        )
    
    # Combine results
    all_gaps = data_gaps + doc_gaps + recon_gaps
    state["needs_list"] = {
        "items": all_gaps,
        "phases_completed": get_completed_phases(state),
        "summary": compute_summary(all_gaps)
    }
    
    return state
```

**present_results_node:**
```python
async def present_results_node(state: LOAState) -> LOAState:
    # Invoke LLM for human-readable output
    prompt = format_presentation_prompt(
        loan_facts=state["loan_facts"],
        needs_list=state["needs_list"],
        include_write_proposals=state.get("include_write_proposals", False)
    )
    
    response = await llm.ainvoke([
        SystemMessage(content=PRESENTATION_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ])
    
    state["summary"] = response.content
    state["status"] = "complete"
    
    # Extract write proposals if present
    if state.get("include_write_proposals"):
        state["write_proposals"] = extract_write_proposals(response.content)
    
    return state
```

---

## 7. Data Models

### 7.1 LoanFacts

```python
@dataclass
class BorrowerFacts:
    borrower_type: str  # "PRIMARY" | "CO_BORROWER"
    first_name: Optional[str]
    last_name: Optional[str]
    middle_name: Optional[str]
    ssn: Optional[str]
    dob: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    marital_status: Optional[str]
    citizenship_status: Optional[str]
    
    # Employment
    is_self_employed: Optional[bool]
    employer_name: Optional[str]
    employer_phone: Optional[str]
    employer_address: Optional[str]
    years_on_job: Optional[float]
    
    # Income
    annual_income: Optional[float]
    has_variable_income: Optional[bool]

@dataclass
class PropertyFacts:
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip: Optional[str]
    county: Optional[str]
    property_type: Optional[str]
    occupancy_type: Optional[str]

@dataclass
class LoanFacts:
    loan_id: str
    loan_number: Optional[str]
    loan_purpose: Optional[str]
    loan_type: Optional[str]
    loan_amount: Optional[float]
    purchase_price: Optional[float]
    ltv: Optional[float]
    dti: Optional[float]
    
    borrowers: List[BorrowerFacts]
    property: PropertyFacts
    
    current_milestone: Optional[str]
    application_date: Optional[str]
    
    # eFolder document list (for R&S input)
    efolder_docs: List[dict]
    
    # Computed
    scenario_tag: str
    is_mvp_supported: bool
```

### 7.2 DocCoverage

```python
@dataclass
class DocCoverageItem:
    doc_type: str
    status: str  # "PRESENT" | "MISSING" | "PARTIAL" | "STALE"
    document_ids: List[str]
    confidence: Optional[float]
    document_date: Optional[str]

@dataclass
class DocCoverage:
    manifest_id: Optional[str]
    manifest_status: str  # "AVAILABLE" | "PENDING" | "NOT_FOUND"
    items: Dict[str, DocCoverageItem]
    extractions: Optional[Dict[str, dict]]  # Field extractions per doc_type
```

### 7.3 GapItem

```python
@dataclass
class GapItem:
    id: str
    category: str  # "BORROWER" | "INCOME" | "ASSETS" | "PROPERTY" | "DOCS" | "RECONCILIATION"
    type: str  # "DATA" | "DOC" | "MISMATCH"
    status: str  # "MISSING" | "INVALID" | "STALE" | "MISMATCH"
    severity: str  # "INFO" | "WARN" | "CRITICAL"
    
    label: str
    reason: str
    action: Optional[str]
    
    # For DATA gaps
    field_id: Optional[str]
    current_value: Optional[Any]
    
    # For DOC gaps
    doc_type: Optional[str]
    
    # For MISMATCH gaps
    expected_value: Optional[Any]
```

### 7.4 NeedsListResult

```python
@dataclass
class NeedsListSummary:
    total: int
    by_status: Dict[str, int]
    by_severity: Dict[str, int]
    by_category: Dict[str, int]
    critical_count: int
    can_proceed: bool

@dataclass
class NeedsListResult:
    timestamp: str
    phases_completed: List[str]  # ["DATA", "DOCS", "RECONCILIATION"]
    items: List[GapItem]
    summary: NeedsListSummary
```

### 7.5 LOAResult

```python
@dataclass
class WriteProposal:
    field_id: str
    current_value: Any
    proposed_value: Any
    source: str
    encompass_field: str

@dataclass
class LOAResult:
    loan_id: str
    execution_timestamp: str
    mode: str
    status: str  # "complete" | "error"
    
    loan_facts: LoanFacts
    doc_coverage: Optional[DocCoverage]
    needs_list: NeedsListResult
    
    summary: str  # Human-readable output from LLM
    write_proposals: Optional[List[WriteProposal]]
    
    errors: List[str]
```

---

## 8. Questionnaire-to-Rule Mapping

### 8.1 Section → Category Mapping

| Section ID | Category |
|------------|----------|
| `account_setup` | BORROWER |
| `current_status` | LOAN |
| `application_type` | LOAN |
| `borrower_profile` | BORROWER |
| `borrower_housing` | PROPERTY |
| `real_estate_owned` | ASSETS |
| `veteran_status` | BORROWER |
| `credit_information` | BORROWER |
| `income_and_employment` | INCOME |
| `subject_property` | PROPERTY |
| `monthly_payment` | LOAN |
| `assets` | ASSETS |
| `declarations` | BORROWER |

### 8.2 Document Name → Doc Type Mapping

| Questionnaire Document Name | Doc Type |
|----------------------------|----------|
| `Signed Purchase Agreement` | PURCHASE_CONTRACT |
| `Separation Agreement` | SEPARATION_AGREEMENT |
| `Divorce Decree` | DIVORCE_DECREE |
| `Child Support Agreement` | CHILD_SUPPORT_AGREEMENT |
| `Mortgage Statement` | MORTGAGE_STATEMENT |
| `Homeowners Insurance Declaration Page` | INSURANCE_DEC |
| `Property Tax Bill` | PROPERTY_TAX |
| `HOA Statement` | HOA_STATEMENT |
| `Rental Agreement` | RENTAL_AGREEMENT |
| `DD-214` | DD214 |
| `VA Active Duty Orders` | VA_ORDERS |
| `VA Disability Award Letter` | VA_DISABILITY_LETTER |
| `BK Paperwork` | BANKRUPTCY_DOCS |
| `Loan Modification Paperwork` | LOAN_MOD_DOCS |
| `1040s` | TAX_RETURN |
| `1099s` | TAX_1099 |
| `Gift Letter` | GIFT_LETTER |
| `Bank Statement` | BANK_STATEMENT |
| `401K/Retirement Account Statement` | RETIREMENT_STATEMENT |

### 8.3 Conditional Requirement Parsing

Pattern matching for conditional requirements in `questionnaire_mapping.json`:

| Pattern | Action |
|---------|--------|
| `If {field} == '{value}', collect {document}` | Add DOC gap if condition met and doc missing |
| `If {field} == '{value}', ask question '{question_id}'` | Evaluate that question's required_fields |
| `Only required if {field} == '{value}'` | Skip gap check if condition not met |
| `If {condition}, collect {field}` | Add DATA gap if condition met and field missing |

---

## 9. File Structure

```
agents/loan-officer-assistant/
├── __init__.py
├── orchestrator.py              # LangGraph workflow definition
├── state.py                     # LOAState and data models
├── tools/
│   ├── __init__.py
│   ├── fetch_loan_context.py    # Encompass API integration
│   ├── fetch_doc_coverage.py    # R&S API integration
│   └── gap_analyzer.py          # Rules engine
├── config/
│   ├── questionnaire_mapping.json  # Rules source
│   ├── field_mapping.yaml          # Encompass → LoanFacts mapping
│   └── doc_type_mapping.yaml       # R&S category → doc type mapping
├── prompts/
│   ├── presentation.py          # LLM prompt templates
│   └── __init__.py
└── tests/
    ├── test_gap_analyzer.py
    ├── test_fetch_loan_context.py
    └── test_orchestrator.py
```

---

## 10. Implementation Plan

### Slice 1: Loan Context + Data Gap Analysis (Fast Mode)

**Goal:** Retrieve loan data from Encompass and identify missing/invalid fields against questionnaire requirements.

**Dependencies:** 
- Encompass API credentials and access
- `questionnaire_mapping.json` field requirements

**Deliverables:**

| File | Description |
|------|-------------|
| `tools/fetch_loan_context.py` | Encompass API integration, field mapping to `LoanFacts` |
| `tools/gap_analyzer.py` | Phase 1 data gap analysis against `required_fields` |
| `config/field_mapping.yaml` | Encompass field ID → LoanFacts field mapping |
| `state.py` | `LoanFacts`, `GapItem`, `NeedsListResult` dataclasses |
| `tests/test_fetch_loan_context.py` | Unit tests for loan context retrieval |
| `tests/test_gap_analyzer_phase1.py` | Unit tests for data gap detection |

**Implementation:**
1. Implement `fetch_loan_context(loan_id)` tool
   - Call Encompass `fieldReader` API with field list from `field_mapping.yaml`
   - Call Encompass `milestones` API
   - Call Encompass `attachments` API (eFolder list)
   - Normalize response to `LoanFacts` dataclass
   - Compute `scenario_tag` based on loan type, purpose, occupancy
2. Implement `analyze_data_gaps(loan_facts, questionnaire)` 
   - Load `questionnaire_mapping.json`
   - For each question, check if `required_fields` are populated in `LoanFacts`
   - Evaluate `conditional_requirements` to determine applicability
   - Generate `GapItem` for each missing/invalid field
3. Wire up as standalone callable: `run_loan_officer_agent(loan_id, mode="fast")`

**Test Criteria:**
- Given loan ID, returns populated `LoanFacts` with borrower, property, loan data
- Given `LoanFacts` with missing SSN, returns `GapItem` for `borrower_ssn`
- Given `LoanFacts` with `marital_status="Separated"`, flags conditional requirements
- Handles Encompass API errors gracefully

**Definition of Done:**
- [ ] `fetch_loan_context` returns valid `LoanFacts` for test loan
- [ ] `analyze_data_gaps` returns correct gap items for known test scenarios
- [ ] Fast mode end-to-end test passes: `loan_id` → `NeedsListResult` with data gaps
- [ ] Unit test coverage ≥80% for new code
- [ ] Error handling for API failures documented and tested

---

### Slice 2: Document Coverage + Doc Gap Analysis (Full Mode)

**Goal:** Integrate Rack & Stack to retrieve document manifest and identify missing documents against questionnaire requirements.

**Dependencies:**
- Slice 1 complete
- TaskTile R&S API credentials and access
- `questionnaire_mapping.json` document requirements

**Deliverables:**

| File | Description |
|------|-------------|
| `tools/fetch_doc_coverage.py` | R&S API integration, manifest parsing, doc type mapping |
| `tools/gap_analyzer.py` | Phase 2 doc gap analysis against `required_documents` |
| `config/doc_type_mapping.yaml` | R&S category → logical doc type mapping |
| `state.py` | `DocCoverage`, `DocCoverageItem` dataclasses |
| `tests/test_fetch_doc_coverage.py` | Unit tests for doc coverage retrieval |
| `tests/test_gap_analyzer_phase2.py` | Unit tests for doc gap detection |

**Implementation:**
1. Implement `fetch_doc_coverage(loan_id, efolder_docs, refresh)` tool
   - Check for existing R&S manifest (cache lookup by loan_id)
   - If `refresh=True` or no manifest: trigger R&S job via TaskTile API
   - Parse manifest `documents[]` array
   - Apply `doc_type_mapping.yaml` to classify documents
   - Aggregate into `DocCoverage` with status per doc type
2. Implement `analyze_doc_gaps(loan_facts, doc_coverage, questionnaire)`
   - For each question, check if `required_documents` are present in `DocCoverage`
   - Evaluate `conditional_requirements` that trigger document needs
   - Generate `GapItem` for each missing document
3. Wire up parallel execution in orchestrator: fetch loan context ∥ fetch doc coverage
4. Implement `mode="full"` behavior

**Test Criteria:**
- Given loan with R&S manifest, returns populated `DocCoverage`
- Given `DocCoverage` missing W-2s for W2 employee, returns doc gap item
- Given `marital_status="Separated"` and missing Separation Agreement, returns gap
- Handles R&S API errors and missing manifests gracefully

**Definition of Done:**
- [ ] `fetch_doc_coverage` returns valid `DocCoverage` for test loan with manifest
- [ ] `analyze_doc_gaps` returns correct doc gap items for known scenarios
- [ ] Full mode end-to-end test passes: `loan_id` → `NeedsListResult` with data + doc gaps
- [ ] Parallel execution of loan context and doc coverage verified
- [ ] R&S manifest caching strategy implemented

---

### Slice 3: LLM Presentation Layer

**Goal:** Generate human-readable summary and action items from structured gap analysis using LLM.

**Dependencies:**
- Slice 1 and 2 complete
- LLM API access (Claude/GPT)

**Deliverables:**

| File | Description |
|------|-------------|
| `prompts/presentation.py` | System prompt and user prompt templates |
| `orchestrator.py` | `present_results_node` LLM invocation |
| `tests/test_presentation.py` | Tests for LLM output formatting |

**Implementation:**
1. Implement `present_results_node(state)` in orchestrator
   - Format `LoanFacts` and `NeedsListResult` into prompt
   - Invoke LLM with system prompt (see Section 5.2)
   - Parse response into `summary` field
2. Implement prompt templates
   - System prompt: role, output format requirements, severity handling
   - User prompt: loan facts JSON, gap items JSON, instructions
3. Add `summary` field to `LOAResult`

**Test Criteria:**
- Given structured gap items, LLM generates summary with correct sections
- Critical items appear in "Critical Issues" section
- Action items are numbered and specific
- Output follows expected markdown format

**Definition of Done:**
- [ ] `present_results_node` generates valid summary for test inputs
- [ ] Summary includes: loan overview, critical issues, high priority, action items
- [ ] Output format matches spec in Section 5.4
- [ ] LLM errors handled gracefully (fallback to structured output)

---

### Slice 4: Write Proposals

**Goal:** Generate proposed Encompass field updates from gap analysis for LOA review.

**Dependencies:**
- Slice 3 complete

**Deliverables:**

| File | Description |
|------|-------------|
| `state.py` | `WriteProposal` dataclass |
| `prompts/presentation.py` | Extended prompt for write proposal generation |
| `orchestrator.py` | Write proposal extraction from LLM output |
| `tests/test_write_proposals.py` | Tests for write proposal generation |

**Implementation:**
1. Extend `present_results_node` to generate write proposals when `include_write_proposals=True`
2. Implement `WriteProposal` dataclass with:
   - `field_id`: Encompass field to update
   - `current_value`: Current value in Encompass
   - `proposed_value`: Suggested new value
   - `source`: Where proposed value came from
3. Parse LLM output table into `WriteProposal` objects
4. Add `write_proposals` field to `LOAResult`

**Test Criteria:**
- Given mismatch gap item, generates corresponding `WriteProposal`
- Write proposals include valid Encompass field IDs
- Proposals correctly identify source of suggested value

**Definition of Done:**
- [ ] `include_write_proposals=True` returns list of `WriteProposal` objects
- [ ] Each proposal has valid `field_id`, `current_value`, `proposed_value`
- [ ] Proposals are presented in structured format for LOA review
- [ ] No automatic writes occur (presentation only)

---

### Slice 5: Data-Document Reconciliation (Phase 3)

**Goal:** Detect mismatches between stated loan data in Encompass and values extracted from documents.

**Dependencies:**
- Slice 2 complete
- R&S field-level extractions available (may require R&S enhancement)

**Deliverables:**

| File | Description |
|------|-------------|
| `tools/gap_analyzer.py` | Phase 3 reconciliation logic |
| `config/reconciliation_rules.yaml` | Field-to-document mapping rules |
| `tests/test_gap_analyzer_phase3.py` | Tests for mismatch detection |

**Implementation:**
1. Define reconciliation rules mapping `LoanFacts` fields to doc extractions:
   - `borrower.first_name` ↔ `GOVERNMENT_ID.first_name`
   - `borrower.employer_name` ↔ `PAYSTUB.employer_name`
   - `property.address` ↔ `PURCHASE_CONTRACT.property_address`
2. Implement `analyze_reconciliation_gaps(loan_facts, doc_extractions)`
   - For each rule, compare `LoanFacts` value to extracted doc value
   - Use fuzzy matching for name/address comparisons
   - Generate `GapItem` with `type="MISMATCH"` for discrepancies
3. Integrate into gap analyzer as Phase 3

**Test Criteria:**
- Given `employer_name="Acme Corp"` in Encompass and `"Acme Corporation"` on paystub, detects mismatch
- Given matching values, no mismatch gap generated
- Fuzzy matching handles minor variations (case, spacing, abbreviations)

**Definition of Done:**
- [ ] Reconciliation rules defined for core fields (name, employer, property)
- [ ] Mismatch detection works for test cases with known discrepancies
- [ ] Fuzzy matching reduces false positives for minor variations
- [ ] Phase 3 integrates into full gap analysis flow

---

### Slice 6: Encompass Write-Back

**Goal:** Execute approved write proposals to update Encompass fields.

**Dependencies:**
- Slice 4 complete
- Encompass write API access

**Deliverables:**

| File | Description |
|------|-------------|
| `tools/encompass_writer.py` | Encompass field write API integration |
| `orchestrator.py` | Write execution flow with approval check |
| `tests/test_encompass_writer.py` | Tests for write operations |

**Implementation:**
1. Implement `write_to_encompass(loan_id, proposals)` tool
   - Filter to only `approved=True` proposals
   - Call Encompass `fieldWriter` API for each field update
   - Return success/failure status per field
2. Add approval workflow
   - LOA marks proposals as approved via API/UI
   - Write execution only processes approved items
3. Implement dry-run mode for testing
4. Add audit logging for all writes

**Test Criteria:**
- Given approved proposal, field is updated in Encompass
- Given unapproved proposal, no write occurs
- Dry-run mode logs intended writes without executing
- API errors handled and reported per field

**Definition of Done:**
- [ ] `write_to_encompass` successfully updates fields for approved proposals
- [ ] Unapproved proposals are not written
- [ ] Dry-run mode works for testing without side effects
- [ ] Audit log captures all write attempts with timestamps
- [ ] Error handling for partial failures (some fields succeed, some fail)

---

## 11. API

### 11.1 Entry Point

```python
async def run_loan_officer_agent(
    loan_id: str,
    mode: str = "full",
    include_write_proposals: bool = False
) -> LOAResult
```

### 11.2 Modes

| Mode | Phases | R&S Behavior | Latency |
|------|--------|--------------|---------|
| `fast` | Phase 1 only | Skip | ~2-5s |
| `full` | Phase 1 + 2 | Use cached | ~5-15s |
| `refresh_docs` | Phase 1 + 2 | Trigger new job | ~30s-5min |

### 11.3 Response Codes

| Status | Meaning |
|--------|---------|
| `complete` | Analysis finished successfully |
| `error` | Fatal error, check `errors` array |
