# Loan Officer Agent (LOA) – Architecture v0.1

## 1. Purpose & Scope

The **Loan Officer Agent (LOA)** is a workflow and decision-support agent for Relationship Managers / Loan Officers.

MVP goals:
- Generate a **Needs List / Gap Analysis** for a given loan.
- Leverage **Rack & Stack** document processing to understand which documents exist and what they contain.
- Present a clear, structured set of **required data, missing docs, and risk flags** that the RM can act on.

Non-goals for MVP:
- Full underwriting decisioning.
- Direct borrower communication.
- Full FNMA/FHLMC guideline coverage.

The design must be:
- **Data-source agnostic**: works today with Encompass loan data + eFolder docs; can later ingest Blend payloads.
- **Guideline-extensible**: rules engine can later be enriched with FNMA/FHLMC guideline mappings and overlays.

---

## 2. High-Level Architecture

At a high level, the LOA is a **single orchestrator agent** that coordinates several **specialized subagents** and tools.

```text
RM UI / API
   │
   ▼
LOA Orchestrator Agent
   │
   ├── Loan Context Subagent      (loan facts from Encompass / POS)
   ├── Rack & Stack Subagent      (TaskTile integration; doc classification)
   ├── Doc Intelligence Subagent  (map R&S docs → doc types / coverage)
   └── Needs List Subagent        (deterministic rules engine → gaps)
```

The orchestrator exposes a single entrypoint:

```pseudo
run_loan_officer_agent(loan_id, options) -> LoanOfficerAgentResult
```

Where `options` can include:
- `mode`: `"snapshot" | "refresh_docs" | "full"`
- `stage`: loan stage / pipeline context (e.g., "Tru Offer", "Processing")
- `trigger`: what event invoked the agent (loan opened, doc uploaded, RM manual run).

---

## 3. Subagents & Responsibilities

### 3.1 Loan Context Subagent

**Purpose:** Build a canonical view of the loan and borrower(s) needed by downstream logic.

**Inputs:**
- `loan_id`
- Encompass field APIs (existing loan info extraction tools).

**Outputs:**
- `LoanFacts` object (normalized, schema-owned by LOA):
  - Borrower & co-borrower identity
  - Employment & income summary
  - Property details
  - Loan terms (purpose, product, rate, term, LTV, DTI, etc.)
  - Milestones & status flags

**Key responsibilities:**
- Call primitive tools to fetch loan fields and milestones.
- Map raw fields to canonical `LoanFacts` schema.
- Detect **scenario** (e.g., conventional purchase, refi, investment property) for routing rules.
- Flag obviously unsupported cases (non-conventional, missing core identifiers) for MVP.

---

### 3.2 Rack & Stack Subagent

**Purpose:** Ensure the loan has an up-to-date **document manifest** produced by the Rack & Stack pipeline, and expose it in a LOA-friendly shape.

**Inputs:**
- `loan_id`
- LOA options (e.g., `mode` = `refresh_docs`)
- List of raw eFolder documents (via primitive tools).

**External API:**
- TaskTile Rack & Stack pipeline (uploads, jobs, webhook manifest).

**Outputs:**
- `RackStackManifestRef` (job id, timestamps, status)
- `DocumentIndex` – normalized list of documents with:
  - source location (bucket/key or Encompass doc id)
  - category (mapped to client category schema)
  - basic metadata (pages, confidence, borrower name, doc date, etc.)

**Workflow:**
1. Check if there is a **recent, successful Rack & Stack manifest** for this loan.
2. If missing/stale and `mode` allows, create a new job:
   - Select candidate PDFs from eFolder (or other sources).
   - Upload to TaskTile and create a `rack-and-stack` job.
3. Wait for / retrieve manifest (webhook or later poll).
4. Normalize the manifest into the `DocumentIndex` for downstream consumers.

**Notes:**
- LOA itself should treat Rack & Stack as an **idempotent service**: if a good manifest already exists, reuse it.
- In MVP, assume the manifest is already available when LOA runs (or handle async with a "docs pending" status).

---

### 3.3 Doc Intelligence Subagent

**Purpose:** Bridge Rack & Stack output to the **doc coverage model** required for the needs list.

**Inputs:**
- `LoanFacts`
- `DocumentIndex`
- Doc mapping configuration (category → logical doc type).

**Outputs:**
- `DocCoverage` structure listing, for each logical doc type:
  - `status`: `PRESENT | MISSING | STALE | PARTIAL`
  - `doc_ids`: references into `DocumentIndex`
  - `metadata`: dates, borrower names, coverage notes.

**Workflow:**
1. Load mapping config (e.g., JSON/YAML):
   - e.g., categories containing "Paystub" → `DOC_INCOME_PAYSTUB`.
2. For each document in `DocumentIndex`, map to one or more logical doc types.
3. Aggregate by doc type to compute coverage.
4. Surface basic **quality checks**:
   - e.g., paystubs for each employed borrower, at least 30 days of coverage, etc. (even if simple).

**Notes:**
- This subagent is purely deterministic and stateless over inputs.
- In later phases, this agent can consume **field-level extractions** from Rack & Stack to power smarter checks.

---

### 3.4 Needs List / Gap Analysis Subagent

**Purpose:** Generate a structured list of **data and document requirements** and risk/guideline flags for the RM.

**Inputs:**
- `LoanFacts`
- `DocCoverage`
- Rules configuration:
  - Question templates (data completeness)
  - Doc templates (doc requirements)
  - Lightweight guideline/risk checks (FICO/DTI/LTV thresholds, occupancy constraints).

**Outputs:**
- `NeedsListResult` containing:
  - `items[]`: per item →
    - `id`
    - `category` (Borrower, Income, Property, Docs, Risk)
    - `type` (`DATA`, `DOC`, `GUIDELINE`)
    - `status` (`OK`, `MISSING`, `GAP`, `BLOCKER`)
    - `severity` (`INFO`, `WARN`, `CRITICAL`)
    - `reason` and `recommended_action`
    - optional `guideline_refs` (FNMA/FHLMC citations – future)
  - `summary`: counts by status/severity and a `can_proceed` flag.

**Rule engine (MVP):**
- Deterministic, table-driven rules (e.g., JSON/YAML or DB-backed).
- Each rule references **canonical fields**, not Encompass IDs directly.
- Examples:
  - If `LoanFacts.employment_type = W2` → require `DOC_INCOME_PAYSTUB` and `DOC_INCOME_W2`.
  - If `LoanFacts.has_rental_income` → require `DOC_RENTAL_LEASE`.
  - If `LoanFacts.decision_fico < threshold` → `BLOCKER` guideline item.

**Extensibility:**
- When FNMA/FHLMC guidelines are encoded, rules gain:
  - explicit guideline citations and rationale.
  - more granular triggers (e.g., property type / unit count / product overlays).

---

### 3.5 Presentation & Action Planner Layer

**Purpose:** Transform raw needs list into **human-readable summaries** and potential next actions.

**Inputs:**
- `LoanFacts`
- `DocCoverage`
- `NeedsListResult`

**Outputs (to UI/API):**
- Narrative summary of loan state.
- Grouped lists of:
  - Critical blockers (must fix before Tru Offer / next milestone).
  - High-priority doc requests.
  - Nice-to-have cleanups.
- Optional suggested actions (e.g., "request 2 months bank statements from borrower").

**Notes:**
- This layer is mostly LLM-based text generation on top of structured outputs.
- It should never be the single source of truth; the underlying structured `NeedsListResult` is.

---

## 4. Orchestrator Flow

### 4.1 Entrypoint

```pseudo
run_loan_officer_agent(loan_id, options) -> LoanOfficerAgentResult
```

**High-level steps:**

1. **Load Loan Context**
   - Invoke Loan Context Subagent → `LoanFacts`.
   - If core identifiers missing (loan not found, no borrower, etc.), return early with a blocking issue.

2. **Ensure Document Index**
   - Invoke Rack & Stack Subagent as needed → `DocumentIndex` + manifest refs.
   - If manifest pending and async model is used, return a status like `"docs_processing"` and stop here.

3. **Compute Doc Coverage**
   - Invoke Doc Intelligence Subagent → `DocCoverage` for the loan.

4. **Run Needs List / Gap Analysis**
   - Invoke Needs List Subagent with `LoanFacts` + `DocCoverage` → `NeedsListResult`.

5. **Assemble Final Result**
   - Compose `LoanOfficerAgentResult`:
     - `loan_id`
     - `loan_facts_summary`
     - `doc_coverage_summary`
     - `needs_list` (structured)
     - `status` (`ok`, `blockers`, `docs_pending`, etc.)
   - Optionally generate a human-readable summary via the Presentation layer.

6. **Return to caller** (UI / API / another agent).

---

## 5. Data Models (Conceptual)

### 5.1 LoanFacts (simplified)

```ts
LoanFacts = {
  loanId: string,
  purpose: 'PURCHASE' | 'REFI' | 'OTHER',
  productType: 'CONVENTIONAL' | 'FHA' | 'VA' | 'USDA' | 'OTHER',
  occupancyType: 'PRIMARY' | 'SECOND_HOME' | 'INVESTMENT',
  propertyType: 'SFR' | 'CONDO' | '2_4_UNIT' | 'OTHER',
  loanAmount: number,
  purchasePrice?: number,
  appraisedValue?: number,
  ltv?: number,
  cltv?: number,
  dtiFront?: number,
  dtiBack?: number,
  decisionFico?: number,
  borrowers: BorrowerFacts[],
  milestones: MilestoneSummary,
  scenarioTag: string // e.g. 'CONV_PURCHASE_PRIMARY_SFR'
}
```

### 5.2 DocCoverage (simplified)

```ts
DocCoverageItem = {
  docType: string,          // e.g. 'DOC_INCOME_PAYSTUB'
  status: 'PRESENT' | 'MISSING' | 'PARTIAL' | 'STALE',
  docIds: string[],         // from DocumentIndex
  notes?: string
}

DocCoverage = {
  items: DocCoverageItem[],
  lastUpdatedAt: string,
}
```

### 5.3 NeedsListResult (simplified)

```ts
NeedsItem = {
  id: string,
  category: 'BORROWER' | 'INCOME' | 'PROPERTY' | 'DOCS' | 'RISK',
  type: 'DATA' | 'DOC' | 'GUIDELINE',
  status: 'OK' | 'MISSING' | 'GAP' | 'BLOCKER',
  severity: 'INFO' | 'WARN' | 'CRITICAL',
  label: string,
  reason: string,
  recommendedAction?: string,
  guidelineRefs?: string[] // future
}

NeedsListResult = {
  items: NeedsItem[],
  summary: {
    total: number,
    missing: number,
    blockers: number,
    canProceed: boolean
  }
}
```

### 5.4 LoanOfficerAgentResult (top-level)

```ts
LoanOfficerAgentResult = {
  loanId: string,
  status: 'ok' | 'blockers' | 'docs_pending' | 'error',
  loanFacts: LoanFacts,
  docCoverage: DocCoverage,
  needsList: NeedsListResult,
  rackStack: {
    manifestAvailable: boolean,
    lastJobId?: string,
    lastJobStatus?: string
  },
  messages?: string[], // human-readable hints
}
```

---

## 6. Extensibility

### 6.1 Blend Integration

When Blend POS integration becomes available:

- Add a **Blend Ingestion Tool** that fetches the Blend application payload for a loan.
- Extend the Loan Context Subagent to:
  - normalize Blend payload → additional `LoanFacts` fields (POS answers, consents, marketing source, etc.).
  - define precedence rules between Blend data and Encompass fields.
- Needs List rules can reference these new fields (e.g., consent status, POS-only questionnaire answers).

### 6.2 FNMA/FHLMC Guidelines

To incorporate official guidelines:

- Maintain a **guideline rule store** with:
  - machine-readable rule definitions (trigger conditions + expected docs/data).
  - human-readable references (section IDs, text snippets).
- Extend the Needs List Subagent so each rule:
  - optionally attaches guideline references to `NeedsItem.guidelineRefs`.
  - can be traced back for audit/explanations.
- Add a separate **Guideline QA Agent** (future) that can:
  - handle freeform RM questions about “why is this required?”
  - use RAG over guideline texts, anchored to the rule that fired.

### 6.3 Multi-Agent Ecosystem

The LOA can be composed with other agents (Disclosure, DrawDocs, Conditions) by:

- Exposing a clean API contract (`LoanOfficerAgentResult`).
- Providing shared primitive tools (loan context, Rack & Stack client, rules engine) as reusable building blocks.
- Allowing other agents to:
  - read the current Needs List and mark items as resolved.
  - add their own specialized needs items (e.g., disclosure-specific requirements) into the same structure.

---

## 7. Minimal Slices Plan

This section outlines **vertical slices** (end-to-end building blocks) to implement the LOA iteratively. Each slice should be shippable and testable on its own.

### Slice 1 – LoanFacts Snapshot

**Goal:** Have a reliable, testable canonical `LoanFacts` object for a single loan.

**Scope:**
- Implement the **Loan Context Subagent**.
- Map Encompass loan fields → `LoanFacts` (for 1–2 core scenarios, e.g., conventional purchase).
- Expose a thin endpoint / function:
  - `get_loan_facts(loan_id) -> LoanFacts`.
- Add basic validation & logging (e.g., missing core fields, unsupported product types).

**End-to-end test:** Call `run_loan_officer_agent` in a "LoanFacts-only" mode and verify it returns a populated `LoanFacts` and a simple status (no doc/needs list yet).

---

### Slice 2 – Rack & Stack Integration + DocumentIndex

**Goal:** Wire in Rack & Stack and produce a normalized `DocumentIndex` for a loan.

**Scope:**
- Implement **Rack & Stack Subagent** with TaskTile API integration (using the existing guide).
- For now, assume the manifest is already available or triggered manually.
- Normalize manifest → `DocumentIndex` (doc ids, categories, basic metadata).
- Extend `run_loan_officer_agent` to optionally return:
  - `LoanFacts` + `DocumentIndex`.

**End-to-end test:** Given a loan with a Rack & Stack manifest, LOA returns `DocumentIndex` with expected docs for that loan.

---

### Slice 3 – Doc Intelligence & Basic Doc Needs

**Goal:** Turn `DocumentIndex` into doc coverage and a minimal doc-only needs list.

**Scope:**
- Implement **Doc Intelligence Subagent**:
  - Map Rack & Stack categories/titles → ~6–10 logical doc types (ID, paystub, W-2, bank statement, purchase contract, appraisal, insurance, etc.).
  - Produce `DocCoverage` per doc type.
- Implement a **minimal doc ruleset** in the Needs List Subagent:
  - e.g., for conventional purchase W2 borrower, determine required doc types.
- Update `run_loan_officer_agent` to return:
  - `LoanFacts`, `DocumentIndex`, `DocCoverage`, and a doc-only `NeedsListResult`.

**End-to-end test:** For a known test loan, LOA surfaces which required docs are present vs missing, matching an RM’s manual checklist.

---

### Slice 4 – Data Completeness Needs

**Goal:** Extend needs list to include **data completeness** (questionnaire-style) checks.

**Scope:**
- Define a small config of 10–20 high-value data items:
  - Borrower identifiers, contact info, employment basics, property basics, loan terms.
- Implement deterministic checks in the Needs List Subagent over `LoanFacts`:
  - Flag `MISSING` / `GAP` items with clear `recommendedAction`.
- Merge data needs with doc needs in a single `NeedsListResult`.

**End-to-end test:** LOA returns a combined needs list; RMs can see both missing docs and missing/dirty data for a test loan.

---

### Slice 5 – Lightweight Guideline / Risk Checks + Summary

**Goal:** Add a first layer of **risk / eligibility checks** and a human-readable summary.

**Scope:**
- Implement a handful of simple guideline-style rules in the Needs List Subagent, e.g.:
  - minimum FICO, max DTI, max LTV, occupancy/product compatibility.
- Tag such items as `type = GUIDELINE`, `severity = WARN/CRITICAL`.
- Add a **Presentation layer** pass that:
  - groups needs by category and severity,
  - computes `canProceed` and a short textual summary for the RM.

**End-to-end test:** For a test loan, LOA indicates whether it can proceed to Tru Offer / next step, and provides a readable summary plus structured needs list.

---

### Slice 6 – Extensibility Hooks (Blend & FNMA-ready)

**Goal:** Make the MVP architecture ready for future Blend / guideline expansion without rewrites.

**Scope:**
- Add optional fields / placeholders in `LoanFacts` for POS data (e.g., Blend application fields).
- Ensure rules reference **canonical fields**, not raw Encompass IDs, so additional sources can be added later.
- Add optional `guidelineRefs` fields in `NeedsItem` for future FNMA/FHLMC citations.

**End-to-end test:**
- Confirm that adding new fields to `LoanFacts` or new rules does not break existing slices.
- Optionally stub a fake "Blend payload" into `LoanFacts` to validate the extension path.

