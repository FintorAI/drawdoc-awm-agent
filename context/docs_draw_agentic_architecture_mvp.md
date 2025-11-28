# Docs Draw Agentic Architecture – MVP Design

## 1. Summary

This document outlines a simpler, more modular **minimum viable agentic architecture**. The goal is to:

- Strip the process down to first principles.
- Implement a small number of powerful agents.
- Build on a reusable set of primitive tools.
- Keep it easy to evolve later into more sub-agents if needed.

---

## 2. First-Principles View of Docs Draw

Ignoring Encompass UI specifics, the Docs Draw flow boils down to four core operations:

1. **Ingest & understand the loan**

   - Confirm preconditions (CTC, CD Approved & ACK’d, Docs Ordered queue).
   - Pull the required documents from the eFolder (1003, Approval Final, MI cert, IDs, FHA/VA/USDA docs, etc.).
   - Extract structured data: borrower names, vesting, property, program, terms, fees, case numbers, etc.

2. **Align Encompass with the documents (“source of truth”)**
   For each “dimension” of the loan:

   - Borrower & loan officer
   - Contacts & vendors
   - Property & program (FHA/VA/USDA/Conventional)
   - Financial setup (terms, escrow, itemization)
   - Closing Disclosure pages

   The system should:

   - Read current Encompass fields.
   - Compare against values derived from the documents.
   - Update fields or flag discrepancies.

3. **Verify & audit**

   - Run internal consistency checks across sections.
   - Run Mavent/compliance checks.
   - Decide if the loan is ready for docs or requires human intervention.

4. **Package & distribute**

   - Trigger docs draw / generate closing package.
   - Update milestone (e.g., Docs Ordered – Finished) and add “DOCS Out on [Date]” comments.
   - Send docs to title / LO / processor.

---

## 3. Primitive Tools (Reusable Operations)

Instead of over-optimizing the number of agents upfront, we design a **tool layer** of primitive operations that any agent can call.

Proposed core tools:

1. **Loan context & workflow**

   - `get_loan_context(loan_id)`\
     Returns: pipeline/milestone, loan type, product, state, key IDs, flags (CTC status, CD status, etc.).

   - `update_milestone(loan_id, status, comment)`\
     Used to mark “Docs Ordered – Finished”, log DOCS Out date, etc.

2. **Documents & data extraction**

   - `list_required_documents(loan_id)`\
     Returns a lender- and product-specific list of required docs.

   - `download_documents(loan_id, categories[])`\
     Downloads documents from the eFolder (1003, Approval Final, MI cert, IDs, FHA/VA/USDA docs, etc.).

   - `extract_entities_from_docs(docs)`\
     Uses your document-understanding stack (LandingAI vs Longformer, etc.) to extract structured entities:

     - Borrowers / co-borrowers
     - Vesting and title
     - Property address and type
     - Program details (FHA/VA/USDA/Conv, case numbers)
     - Terms (rate, term, amortization, ARM details)
     - Fees and escrow details

   Output: a normalized **`doc_context`**\*\* JSON\*\* that becomes the canonical reference for other agents.

3. **Encompass field IO**

   - `read_fields(form_id, field_ids[])`
   - `write_fields(form_id, updates[])`

   These give a generic way to interact with Encompass without hardcoding UI flows. Agents work at the level of “forms and fields,” not screens.

4. **Compliance & validation**

   - `run_compliance_check(loan_id, type="Mavent")`
   - `get_compliance_results(loan_id)`

   These run and fetch results from Mavent or other checks.

5. **Docs draw & distribution**

   - `order_docs(loan_id)`\
     Triggers final docs generation.

   - `send_closing_package(loan_id, recipients)`\
     Sends the generated package to title, LO, processor, etc.

6. **Issue logging**

   - `log_issue(loan_id, severity, message)`\
     For anything the agents cannot confidently resolve and need to hand back to humans.

These tools are the “platform primitives”. Once stable, you can plug them into multiple workflows (Docs Draw, Disclosures, Conditions, etc.) without redesigning the integrations.

---

## 4. Minimum Viable Agentic Setup

For an MVP that is **simple, modular, and extendable**, we propose:

- 2–3 true LLM agents:

  - **Docs Prep Agent**
  - **Docs Draw Core Agent**
  - **Audit & Compliance Agent**

- 1 deterministic **Order Docs & Distribution** step (can be wrapped by a very thin agent if desired).

### 4.1 Docs Prep Agent (extension of Preparation Agent)

**Role**\
Takes a `loan_id`, confirms preconditions, pulls required docs, and builds the canonical `doc_context` from documents.

**Responsibilities**

1. Check that:

   - Loan is CTC.
   - CD is Approved & ACK’d.
   - Loan is in the appropriate Docs Ordered queue.

2. Collect documents:

   - Use `list_required_documents` and `download_documents` to fetch 1003, Approval Final, MI cert, IDs, FHA/VA/USDA docs, etc.

3. Build `doc_context`:

   - Run `extract_entities_from_docs(docs)`.
   - Normalize into a structured JSON view of the loan as implied by the documents.

4. Handle missing/invalid docs:

   - If critical docs are missing, call `log_issue` and exit early for human review.

**Tools used**

- `get_loan_context`
- `list_required_documents`
- `download_documents`
- `extract_entities_from_docs`
- `log_issue`

### 4.2 Docs Draw Core Agent

This is the **workhorse** agent that applies the `doc_context` to Encompass. It subsumes several of the proposed sub-agents (Borrower Setup, Contacts & Vendors, Property & Program, Financial Setup, Closing Disclosure) into one coordinated agent with internal phases.

**High-level idea**\
Run a series of phases, each focusing on a “dimension” of the loan, while sharing state:

- Phase 1 – Borrower & LO
- Phase 2 – Contacts & Vendors
- Phase 3 – Property & Program (FHA/VA/USDA/Conv)
- Phase 4 – Financial Setup & Itemization
- Phase 5 – Closing Disclosure Pages (1–4)

**For each phase, the agent:**

1. **Reads** current Encompass fields using `read_fields`.
2. **Looks up** the corresponding entries in `doc_context`.
3. **Compares** Encompass vs. document values.
4. **Decides** for each field:
   - Update Encompass to match the documents.
   - Leave as-is (e.g., internal-only fields, or confirmed with prior notes).
   - Flag as ambiguous or conflicting (using `log_issue`).
5. **Writes** the decided updates with `write_fields`.
6. **Emits a phase summary**: what changed, what’s missing, and any warnings.

**Examples**

- Borrower Setup: ensure names, SSNs, marital status, vesting, title, and relationships align with 1003 and ID docs.
- Property & Program: match property address, type, occupancy, and program-specific details like FHA/VA/USDA case numbers.
- Financial Setup: reconcile terms (rate, term, amortization) and escrow setup with Approval Final, LE/CD, and other docs.
- CD pages: ensure fees, cash to close, and other disclosure line items are consistent with your lender’s tolerances.

**Tools used**

- `get_loan_context`
- `read_fields` / `write_fields`
- Access to `doc_context` from Docs Prep Agent
- `log_issue`

Over time, if you discover that e.g. “Financial Setup” needs a very different prompting strategy from “Borrower Setup,” you can split them out into separate agents without changing the underlying tools.

### 4.3 Audit & Compliance Agent (extension of Verification Agent)

This agent acts as the final check before ordering docs.

**Responsibilities**

1. Run a final cross-section checklist:

   - Confirm all required fields for docs draw are present.
   - Verify no obvious inconsistencies (e.g., borrower names mismatch across forms, program type mismatched with case number pattern, etc.).

2. Run compliance:

   - Call `run_compliance_check(loan_id, "Mavent")`.
   - Interpret `get_compliance_results(loan_id)`.

3. Decide outcome:

   - If clean: mark as ready to order docs.
   - If issues:
     - For trivial fixes (e.g., missing checkbox), optionally auto-correct and rerun.
     - For more complex issues, call `log_issue` and hand off to a closer.

**Tools used**

- `read_fields`
- `run_compliance_check`
- `get_compliance_results`
- `log_issue`

### 4.4 Order Docs & Distribution (Deterministic Flow)

For the MVP, this can be implemented as a straightforward, non-LLM flow (or a very thin “Orderdocs Agent” wrapper around deterministic calls).

**Responsibilities**

1. Call `order_docs(loan_id)`.
2. Update milestones and comments:
   - `update_milestone(loan_id, "Docs Ordered – Finished", "DOCS Out on [Date]")`.
3. Send the closing package:
   - `send_closing_package(loan_id, recipients)` with title company, LO, and processors.
4. Confirm success or `log_issue` in case of failures.

**Tools used**

- `order_docs`
- `update_milestone`
- `send_closing_package`
- `log_issue`

---

## 5. Orchestrator-Level Flow

The high-level orchestrator (which could be your global Loan Orchestrator, or a local Docs Orchestrator) runs these steps in sequence with simple branching:

1. **Docs Prep Agent**

   - If preconditions fail or critical docs missing → halt & notify human.
   - Else → produce `doc_context` and proceed.

2. **Docs Draw Core Agent**

   - Executes phases 1–5.
   - If it encounters ambiguous/conflicting information, it records issues and may:
     - Stop and wait for human review, or
     - Proceed with best-effort updates while clearly flagging discrepancies.

3. **Audit & Compliance Agent**

   - Runs checklists and compliance.
   - If pass: move on to docs ordering.
   - If fail: log issues and hand off to a closer.

4. **Order Docs & Distribution Flow**

   - Trigger docs draw.
   - Update milestones and comments.
   - Send packages.

This gives you a clear, linear pipeline for MVP while still allowing for richer graph patterns later (e.g., loops for auto-fix retries, branching by product type, etc.).

---

## 6. Why This Is a Strong MVP

1. **Simplicity**\
   Only 2–3 real agents and a deterministic final step, instead of 9 sub-agents. Much easier to implement, prompt, and debug.

2. **Modularity**\
   The primitives (tools + `doc_context`) are reusable across flows and across lenders. The agents are just orchestrators of those primitives.

3. **Traceability to SOP**\
   The Docs Draw Core Agent’s phases map directly to the major SOP sections (Borrower, Contacts, Property & Program, Financial, CD). You can easily audit decisions and compare them to the original manual process.

4. **Path to future expansion**\
   As you learn where complexity really lies, you can gradually:

   - Split the Core Agent into specialized sub-agents.
   - Add more product-specific logic.
   - Introduce more advanced planning or LangGraph patterns (retries, branches).

5. **Eval-friendly**\
   You can design evaluations per phase inside the Core Agent (e.g., “% of borrower fields correctly auto-filled,” “# of fee discrepancies caught,” “Mavent pass rate after first attempt”) before committing to a more fragmented multi-agent architecture.

---

## 7. Next Steps

1. **Define the concrete tool interfaces** for Encompass, document download, extraction, compliance, and distribution.
2. **Draft prompts** for:
   - Docs Prep Agent
   - Docs Draw Core Agent (with explicit phase structure)
   - Audit & Compliance Agent
3. **Decide on the document-understanding backend** (LandingAI vs Longformer stack) and finalize the `doc_context` schema.
4. **Mock a few loan scenarios** and run through the pipeline manually to refine assumptions and prompts.

From there, you can iteratively add complexity (new agents, deeper branching, or lender-specific behaviors) without touching the underlying tools and primitives.

