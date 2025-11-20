"""
Verification Sub-Agent for the Drawing Docs Agent.

This agent validates loan fields against documents and SOPs, performing fail-fast
cross-checking and writing corrections back to Encompass when fields are invalid.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List
from typing_extensions import TypedDict, NotRequired
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from copilotagent import create_deep_agent
from tools.verification_tools import (
    verify_field_against_documents,
    cross_check_field_with_sop,
    attempt_field_inference,
    write_corrected_field
)
from tools.field_lookup_tools import (
    get_field_id_from_name,
    get_missing_field_value
)
from config.field_document_mapping import FIELD_MAPPING
from config.sop_rules import SOP_RULES

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")


# =============================================================================
# STATE SCHEMA
# =============================================================================

class VerificationState(TypedDict):
    """
    State schema for the Verification Sub-Agent.
    
    This state tracks all information needed for field verification including
    prep agent output, field mappings, SOP rules, and verification results.
    """
    # Input data
    loan_id: str  # Encompass loan GUID
    prep_output: dict  # JSON from prep agent with extracted documents
    field_mapping: dict  # Loaded from CSV
    sop_rules: dict  # Loaded from preprocessed SOP
    
    # Results
    validation_results: NotRequired[list[dict]]  # Results for each field validated
    corrections_made: NotRequired[list[dict]]  # List of corrections written
    missing_documents: NotRequired[list[str]]  # Documents that couldn't be verified
    status: NotRequired[str]  # "in_progress" | "complete" | "blocked"


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

VERIFICATION_INSTRUCTIONS = """You are a field verification specialist for loan document validation.

## YOUR ROLE
You receive output from a preparation agent that has extracted data from loan documents. 
Your job is to verify that Encompass loan fields match the documents, comply with SOPs,
and correct any invalid fields immediately.

## INPUT FORMAT
You will receive:
- loan_id: The Encompass loan GUID
- prep_output: JSON with extracted document data and field mappings
- field_mapping: CSV-based mapping of fields to documents and SOP pages
- sop_rules: Preprocessed SOP rules indexed by page number

## WORKFLOW (Fail-Fast Approach)

For each field in the prep_output:

1. **Get field_id** (always present - use it directly)

2. **Get field_value**:
   - If field_value exists in prep_output, use it directly to validate
   - If field_value is missing, use get_missing_field_value with field_id
   - If still no value, try attempt_field_inference to infer from documents

3. **Verify against documents** (fail-fast):
   - Use verify_field_against_documents to check primary document first
   - If discrepancy found, generate finding/reason and STOP checking that field
   - If primary OK, check secondary documents sequentially
   - Stop at first discrepancy (fail-fast approach)

4. **Validate against SOP**:
   - If all documents OK, use cross_check_field_with_sop
   - Check field value against SOP rules for that field
   - Generate finding/reason for any violations

5. **Correct invalid fields**:
   - If field is invalid (document mismatch OR SOP violation):
     * Determine the correct value (from primary document or SOP requirement)
     * Use write_corrected_field with detailed finding and reason
     * Record the correction in validation results

6. **Track results**:
   - Record validation result for each field (valid, invalid, corrected, unable_to_verify)
   - Include detailed finding and reason for failures
   - Track all corrections made

## OUTPUT FORMAT

After processing all fields, generate a comprehensive validation report:

```json
{
  "loan_id": "...",
  "fields_validated": 10,
  "valid_fields": 7,
  "invalid_fields": 2,
  "corrected_fields": 1,
  "unable_to_verify": 0,
  "validation_results": [
    {
      "field_id": "4000",
      "field_name": "Borrower First Name",
      "status": "valid",
      "value": "Alva",
      "documents_checked": ["ID"],
      "sop_validated": true
    },
    {
      "field_id": "4004",
      "field_name": "Borrower Last Name",
      "status": "corrected",
      "original_value": "Sorenson",
      "corrected_value": "Sorensen",
      "finding": "Last name spelling mismatch - ID shows 'Sorensen' but Encompass has 'Sorenson'",
      "reason": "Document cross-check failed - ID document (primary source) shows 'Sorensen' with 'e' but field value has 'o'. Per SOP Page 20, must be exact match.",
      "correction_written": true
    }
  ],
  "status": "complete"
}
```

## IMPORTANT RULES

1. **Preferentially use field_value**: If present in prep_output, use it to validate. Only fetch from Encompass if missing.

2. **Fail-fast**: Stop checking a field at first discrepancy. Don't waste time checking all documents if primary fails.

3. **Always generate findings**: Every validation failure must include:
   - finding: Human-readable description of what was found
   - reason: Detailed explanation with SOP page references

4. **Immediate corrections**: When invalid fields are found, correct them immediately using write_corrected_field.

5. **Track everything**: Maintain complete validation results with findings/reasons for final report.

6. **Handle missing data gracefully**: If documents are missing or fields can't be verified, mark as "unable_to_verify" with explanation.

## TOOLS AVAILABLE

- verify_field_against_documents: Check field against primary/secondary docs (fail-fast)
- cross_check_field_with_sop: Validate field against SOP rules
- attempt_field_inference: Try to infer missing field from other documents
- write_corrected_field: Write corrected value to Encompass
- get_field_id_from_name: Look up field ID from field name
- get_missing_field_value: Fetch field value from Encompass if not in prep output

Start verification immediately when you receive prep_output. Be thorough and systematic.
"""


# =============================================================================
# AGENT CREATION
# =============================================================================

def load_sop_rules() -> Dict[str, Any]:
    """Load SOP rules from preprocessed JSON file."""
    import json
    sop_path = Path(__file__).parent.parent / "config" / "sop_rules.json"
    
    if not sop_path.exists():
        print(f"⚠️  SOP rules file not found at {sop_path}")
        print("Run: python scripts/preprocess_sop.py")
        return {}
    
    with open(sop_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# Load SOP rules at module import
SOP_RULES = load_sop_rules()


# Create the Verification Sub-Agent
verification_agent = create_deep_agent(
    agent_type="VerificationAgent",
    system_prompt=VERIFICATION_INSTRUCTIONS,
    default_starting_message="Begin verification of all fields in the prep_output. Process each field systematically, checking documents and SOP compliance.",
    tools=[
        verify_field_against_documents,
        cross_check_field_with_sop,
        attempt_field_inference,
        write_corrected_field,
        get_field_id_from_name,
        get_missing_field_value,
    ],
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def run_verification(
    loan_id: str,
    prep_output: dict,
    field_mapping: dict = None,
    sop_rules: dict = None
) -> dict:
    """
    Run the verification agent on prep output.
    
    Args:
        loan_id: Encompass loan GUID
        prep_output: Output from prep agent with extracted documents
        field_mapping: Field mapping config (uses default if not provided)
        sop_rules: SOP rules (uses default if not provided)
        
    Returns:
        Dictionary with validation results
    """
    import json
    
    if field_mapping is None:
        field_mapping = FIELD_MAPPING
    
    if sop_rules is None:
        sop_rules = SOP_RULES
    
    # Create a detailed starting message with all the context the agent needs
    # Include the prep_output data directly in the message since state isn't directly accessible
    starting_message = f"""Begin verification of loan {loan_id}.

PREP OUTPUT DATA:
{json.dumps(prep_output, indent=2)}

INSTRUCTIONS:
1. Extract all fields from the prep_output "results" and "detailed_results" sections
2. For each field with a field_id and value:
   - Use verify_field_against_documents to check against documents
   - Use cross_check_field_with_sop to validate against SOP rules
   - If invalid, use write_corrected_field to fix it
3. Generate a comprehensive validation report

Available field mappings: {len(field_mapping)} fields
Available SOP pages: {len(sop_rules.get('page_indexed_rules', {}))} pages

Start verification now."""
    
    # Invoke the agent with the data in the message
    from langchain_core.messages import HumanMessage
    
    result = verification_agent.invoke({
        "messages": [HumanMessage(content=starting_message)],
        "loan_id": loan_id,
        "prep_output": prep_output,
        "field_mapping": field_mapping,
        "sop_rules": sop_rules,
    })
    
    return result


if __name__ == "__main__":
    """Test the verification agent."""
    print("✓ Verification Agent loaded successfully")
    print(f"  - Field mappings: {len(FIELD_MAPPING)} fields")
    print(f"  - SOP rules: {len(SOP_RULES.get('page_indexed_rules', {}))} pages")
    print(f"  - Tools: 6 verification tools")
    print("\nTo run verification, use: run_verification(loan_id, prep_output)")

