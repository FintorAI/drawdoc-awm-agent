# Docs Draw Core Agent

The **Docs Draw Core Agent** is the heart of the docs draw system. It takes extracted data from the Prep Agent and updates Encompass fields in a structured, 5-phase process.

## Overview

This agent performs the main field update operations across 5 logical phases:

1. **Phase 1: Borrower & LO** - Borrower names, vesting, contact info, loan officer
2. **Phase 2: Contacts & Vendors** - Title company, escrow, lenders, insurance providers
3. **Phase 3: Property & Program** - Property details, FHA/VA/USDA case numbers, amortization
4. **Phase 4: Financial Setup** - Loan terms, rates, fees, escrow, APR
5. **Phase 5: Closing Disclosure** - CD page fields with final numbers

## Architecture

```
drawcore_agent/
├── drawcore_agent.py           # Main agent coordinator
├── phases/
│   ├── __init__.py
│   ├── phase1_borrower_lo.py   # Borrower & LO updates
│   ├── phase2_contacts.py      # Contacts & Vendors
│   ├── phase3_property.py      # Property & Program
│   ├── phase4_financial.py     # Financial Setup
│   └── phase5_cd.py            # Closing Disclosure
├── test_drawcore_with_primitives.py
└── README.md (this file)
```

## Features

- **Modular Phase Design**: Each phase is independent and can be run separately
- **Primitive-Based**: Uses primitives for all Encompass I/O (no direct API calls)
- **Dry Run Mode**: Test updates without writing to Encompass
- **Comprehensive Logging**: Detailed logs for audit trail
- **Error Handling**: Gracefully handles missing/ambiguous data
- **Issue Tracking**: Logs issues for human review

## Usage

### Basic Usage

```python
from agents.drawdocs.subagents.drawcore_agent.drawcore_agent import run_drawcore_agent

# Run all phases
result = run_drawcore_agent(
    loan_id="b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6",
    doc_context=prep_agent_output,  # From Prep Agent
    dry_run=True  # No actual writes
)

print(f"Status: {result['status']}")
print(f"Fields updated: {result['summary']['total_fields_updated']}")
```

### Run Specific Phases

```python
# Only run Phase 1 and Phase 5
result = run_drawcore_agent(
    loan_id="b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6",
    doc_context=prep_agent_output,
    dry_run=True,
    phases_to_run=[1, 5]  # Only Borrower & CD
)
```

### CLI Usage

```bash
# Dry run (default)
python drawcore_agent.py \
  --loan-id b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6 \
  --doc-context prep_output.json \
  --output result.json

# Production mode (actually writes)
python drawcore_agent.py \
  --loan-id b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6 \
  --doc-context prep_output.json \
  --production

# Run specific phases
python drawcore_agent.py \
  --loan-id b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6 \
  --doc-context prep_output.json \
  --phases "1,2,3"  # Only phases 1-3
```

## Input: `doc_context`

The agent expects a `doc_context` object from the Prep Agent with this structure:

```json
{
  "loan_id": "...",
  "results": {
    "field_mappings": {
      "4000": "John",        // Borrower First Name
      "4002": "Doe",          // Borrower Last Name
      "356": 290000,          // Appraised Value
      "CD1.X69": "$168,259.37" // CD Total Cash to Close
      // ... more fields
    },
    "extracted_entities": {
      "ID": { ... },
      "Title Report": { ... },
      // ... document extractions
    }
  }
}
```

## Output

Returns a comprehensive result dictionary:

```json
{
  "loan_id": "...",
  "execution_timestamp": "2025-12-01T...",
  "dry_run": true,
  "status": "success",  // "success" | "partial_success" | "failed"
  "phases": {
    "phase_1": {
      "status": "success",
      "fields_processed": 10,
      "fields_updated": 5,
      "issues_logged": 0,
      "updates": [...],
      "issues": []
    },
    // ... other phases
  },
  "summary": {
    "total_fields_processed": 25,
    "total_fields_updated": 15,
    "total_issues_logged": 2,
    "phases_completed": 5,
    "phases_failed": 0
  },
  "loan_context": { ... },
  "error": null
}
```

## Phase Details

### Phase 1: Borrower & LO
Updates 13+ borrower-related fields including names, vesting, contact info, and personal details.

**Key Fields:**
- Borrower First/Middle/Last Name (4000, 36, 4001, 4002)
- Borrower Vesting Type (4008)
- Contact info (66, FE0117, 1240)
- Personal info (1402, 65, 52, 471)

### Phase 2: Contacts & Vendors
Updates title company, escrow, and other vendor information.

**Key Fields:**
- Escrow Company Name (610)
- Title Insurance Company Name (411)

### Phase 3: Property & Program
Updates property details and loan program information (FHA/VA/USDA).

**Key Fields:**
- Appraised Value (356)
- Loan Amount (1109)
- Agency Case # (1040)
- Amortization Type (608, 995)

### Phase 4: Financial Setup
Updates loan terms, rates, fees, and escrow information.

**Key Fields:**
- APR (799)
- Impound Types (2294)

### Phase 5: Closing Disclosure
Updates all CD page fields with final closing numbers.

**Key Fields:**
- CD Total Cash to Close (CD1.X69)
- CD Lender Credits (CD2.X1)
- CD Total Closing Costs (CD2.XSTJ, CD3.X82)
- CD Loan/Other Costs (CD2.XSTD, CD2.XSTI)
- CD Special Provisions (CD4.X2, CD4.X3, 674)

## Integration with Orchestrator

The Drawcore Agent is called by the main Orchestrator between the Prep Agent and Verification Agent:

```
1. Prep Agent    → Extracts data from documents
2. Drawcore Agent → Updates Encompass fields (THIS)
3. Verification Agent → Verifies and audits
4. Order Docs Flow → Triggers docs draw
```

## Error Handling

The agent handles errors gracefully:
- **Missing fields**: Skips and continues
- **Write failures**: Logs issue and continues to next field
- **Phase failures**: Continues to next phase, reports partial success
- **Fatal errors**: Logs critical issue and returns failed status

## Testing

Run the test script:

```bash
python test_drawcore_with_primitives.py
```

This will:
1. Load sample prep output
2. Run all 5 phases in dry run mode
3. Show detailed field-by-field updates
4. Save results to JSON

## Future Enhancements

- [ ] Add more field mappings per phase (currently MVP set)
- [ ] Implement field validation rules from CSV Notes column
- [ ] Add cross-field consistency checks
- [ ] Implement conditional logic for state-specific fields
- [ ] Add support for co-borrowers
- [ ] Implement trust vesting fields
- [ ] Add retry logic for failed field updates
- [ ] Implement smart field grouping (batch updates)

## Dependencies

- `agents.drawdocs.tools.primitives` - All Encompass I/O
- Prep Agent output (`doc_context`)
- MCP Server (for Encompass API access)

## Notes

- **Always run in dry run mode first** to verify updates
- Field IDs are sourced from `DrawingDoc Verifications - Sheet1.csv`
- Each phase is independent and can be extended with more fields
- The agent uses primitives exclusively (no direct API calls)

