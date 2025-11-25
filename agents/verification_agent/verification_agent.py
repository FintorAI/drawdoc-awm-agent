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

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from copilotagent import create_deep_agent
from agents.verification_agent.tools.verification_tools import (
    compare_prep_vs_encompass_value,
    verify_field_against_documents,
    cross_check_field_with_sop,
    attempt_field_inference,
    write_corrected_field
)
from agents.verification_agent.tools.field_lookup_tools import (
    get_field_id_from_name,
    get_missing_field_value
)
from agents.verification_agent.config.field_document_mapping import FIELD_MAPPING
from agents.verification_agent.config.sop_rules import SOP_RULES

# Load environment variables from project root
load_dotenv(Path(__file__).parent.parent.parent / ".env")


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
You receive output from a preparation agent that has extracted CORRECT values from loan documents. 
Your job is to compare these correct values against current Encompass field values and correct 
any mismatches immediately.

## INPUT FORMAT
You will receive:
- loan_id: The Encompass loan GUID
- prep_output: JSON with field_mappings containing CORRECT values extracted from documents
- field_mapping: CSV-based mapping of fields to documents and SOP pages
- sop_rules: Preprocessed SOP rules indexed by page number

## WORKFLOW

For each field_id in prep_output.results.field_mappings:

1. **Get the correct value** from prep_output.results.field_mappings[field_id]
   - This is the CORRECT value extracted from documents

2. **Get the current value** from Encompass:
   - Use get_missing_field_value(loan_id, field_id) to fetch current Encompass value

3. **Compare values**:
   - Normalize both values (strip whitespace, case-insensitive comparison)
   - If values match: Record as VALID
   - If values differ: This is a DISCREPANCY that needs correction

4. **Validate against SOP** (optional):
   - Use cross_check_field_with_sop to validate format/completeness
   - Check field value against SOP rules for that field
   - Generate finding/reason for any violations

5. **Correct mismatched fields**:
   - If Encompass value differs from prep output value:
     * Use write_corrected_field to update Encompass with the correct value
     * Include detailed finding and reason explaining the discrepancy
     * Pass field_mapping parameter to capture source document information
     * Record the correction in validation results

6. **Track results**:
   - Record validation result for each field (valid, invalid, corrected, unable_to_verify)
   - Include detailed finding and reason for corrections
   - Track all corrections made

## OUTPUT FORMAT

After processing all fields, generate a comprehensive validation report:

```json
{
  "loan_id": "...",
  "fields_validated": 10,
  "valid_fields": 7,
  "invalid_fields": 2,
  "corrected_fields": 2,
  "unable_to_verify": 0,
  "validation_results": [
    {
      "field_id": "4000",
      "field_name": "Borrower First Name",
      "status": "valid",
      "prep_value": "Alva",
      "encompass_value": "Alva"
    },
    {
      "field_id": "4002",
      "field_name": "Borrower Last Name",
      "source_document": "ID",
      "status": "corrected",
      "prep_value": "Sorensen",
      "encompass_value": "Sorenson",
      "finding": "Last name spelling mismatch",
      "reason": "Prep output shows 'Sorensen' (extracted from ID document) but Encompass has 'Sorenson'. Corrected to match documents.",
      "correction_written": true
    }
  ],
  "status": "complete"
}
```

## IMPORTANT RULES

1. **Prep output is the source of truth**: Values in prep_output.results.field_mappings are CORRECT (extracted from documents). Encompass values may be wrong.

2. **Always fetch Encompass values**: Use get_missing_field_value for EVERY field to get current Encompass value for comparison.

3. **Always generate findings**: Every correction must include:
   - finding: Human-readable description of what was found
   - reason: Detailed explanation of the discrepancy

4. **Immediate corrections**: When mismatches are found, correct them immediately using write_corrected_field.

5. **Track everything**: Maintain complete validation results with findings/reasons for final report.

6. **Handle missing data gracefully**: If field can't be retrieved from Encompass, mark as "unable_to_verify" with explanation.

## TOOLS AVAILABLE

PRIMARY WORKFLOW TOOLS:
- get_missing_field_value: Fetch current field value from Encompass (USE FOR EVERY FIELD)
- compare_prep_vs_encompass_value: Compare prep value vs Encompass value (returns match/mismatch)
- write_corrected_field: Write corrected value to Encompass when mismatch found

OPTIONAL TOOLS:
- cross_check_field_with_sop: Validate field against SOP rules
- get_field_id_from_name: Look up field ID from field name

LEGACY TOOLS (not needed in main workflow):
- verify_field_against_documents: NOT needed - prep output already verified against documents
- attempt_field_inference: NOT needed - prep output already has extracted values

## RECOMMENDED WORKFLOW FOR EACH FIELD

1. Get prep value from field_mappings[field_id]
2. Call get_missing_field_value(loan_id, field_id) to get Encompass value
3. Call compare_prep_vs_encompass_value(field_id, prep_value, encompass_value, field_mapping)
4. If needs_correction=True: Call write_corrected_field(loan_id, field_id, prep_value, reason, finding, field_mapping) 
   - IMPORTANT: Pass field_mapping parameter to capture source document info

Start verification immediately when you receive prep_output. Process each field in field_mappings systematically.
"""


# =============================================================================
# AGENT CREATION
# =============================================================================

def load_sop_rules() -> Dict[str, Any]:
    """Load SOP rules from preprocessed JSON file."""
    import json
    sop_path = Path(__file__).parent / "config" / "sop_rules.json"
    
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
    default_starting_message="Begin verification of all fields in prep_output.results.field_mappings. For each field, fetch current Encompass value and compare with prep output value.",
    tools=[
        # Primary workflow tools
        get_missing_field_value,
        compare_prep_vs_encompass_value,
        write_corrected_field,
        # Optional SOP validation
        cross_check_field_with_sop,
        # Helper tools
        get_field_id_from_name,
        # Legacy tools (kept for backward compatibility but not needed in main workflow)
        verify_field_against_documents,
        attempt_field_inference,
    ],
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def run_verification(
    loan_id: str,
    prep_output: dict,
    field_mapping: dict = None,
    sop_rules: dict = None,
    dry_run: bool = None
) -> dict:
    """
    Run the verification agent on prep output.
    
    Args:
        loan_id: Encompass loan GUID
        prep_output: Output from prep agent with extracted documents
        field_mapping: Field mapping config (uses default if not provided)
        sop_rules: SOP rules (uses default if not provided)
        dry_run: If True, don't write to Encompass (just print). 
                 If None, reads from DRY_RUN environment variable.
                 Default: False (writes to Encompass)
        
    Returns:
        Dictionary with validation results
        
    Note:
        ⚠️ DRY RUN MODE: Set dry_run=True or environment variable DRY_RUN=true
        to prevent actual writes to Encompass. Use this for testing on production.
    """
    import json
    
    # Set dry run mode via environment variable if specified
    if dry_run is not None:
        os.environ["DRY_RUN"] = "true" if dry_run else "false"
    
    # Check current dry run status
    is_dry_run = os.getenv("DRY_RUN", "false").lower() in ("true", "1", "yes")
    
    if is_dry_run:
        print("\n" + "="*80)
        print("🔍 DRY RUN MODE ENABLED - No changes will be written to Encompass")
        print("="*80 + "\n")
    
    if field_mapping is None:
        field_mapping = FIELD_MAPPING
    
    if sop_rules is None:
        sop_rules = SOP_RULES
    
    # Detect prep output format and extract field data
    field_mappings = prep_output.get("results", {}).get("field_mappings", {})
    
    # Check format: new format has {"value": ..., "attachment_id": ...}
    # Old format has direct values
    is_new_format = False
    attachment_id_map = {}
    
    if field_mappings:
        first_field_id = next(iter(field_mappings))
        first_value = field_mappings[first_field_id]
        if isinstance(first_value, dict) and "value" in first_value:
            is_new_format = True
            print(f"✓ Detected NEW prep output format (with attachment_ids)")
            
            # Build attachment_id mapping for new format
            for fid, fdata in field_mappings.items():
                if isinstance(fdata, dict):
                    attachment_id_map[fid] = fdata.get("attachment_id")
        else:
            print(f"✓ Detected OLD prep output format (direct values)")
    
    # Create a detailed starting message with all the context the agent needs
    # Include the prep_output data directly in the message since state isn't directly accessible
    format_instructions = ""
    if is_new_format:
        format_instructions = """
FORMAT NOTE: Prep output uses NEW format with nested structure:
- prep_output["results"]["field_mappings"][field_id]["value"] = the correct value
- prep_output["results"]["field_mappings"][field_id]["attachment_id"] = source document ID

Attachment ID mapping (field_id -> attachment_id):
""" + json.dumps(attachment_id_map, indent=2)
    
    starting_message = f"""Begin verification of loan {loan_id}.

PREP OUTPUT DATA:
{json.dumps(prep_output, indent=2)}
{format_instructions}

INSTRUCTIONS:
1. Extract all field IDs and values from prep_output["results"]["field_mappings"]
   - These values are CORRECT (extracted from documents)
   - {"For NEW format: extract value using field_mappings[field_id]['value']" if is_new_format else "For OLD format: value is field_mappings[field_id] directly"}
   - {"For NEW format: get attachment_id using field_mappings[field_id]['attachment_id']" if is_new_format else ""}

2. For EACH field_id in field_mappings:
   a) Get prep_value = {"field_mappings[field_id]['value']" if is_new_format else "field_mappings[field_id]"}
   b) {"Get attachment_id = field_mappings[field_id]['attachment_id']" if is_new_format else ""}
   c) Call get_missing_field_value(loan_id="{loan_id}", field_id=field_id) to get encompass_value
   d) Call compare_prep_vs_encompass_value(field_id, prep_value, encompass_value, field_mapping)
   e) If needs_correction=True: Call write_corrected_field with:
      - loan_id="{loan_id}"
      - field_id=field_id
      - corrected_value=prep_value
      - reason=<explain discrepancy>
      - finding=<detailed finding>
      - field_mapping=field_mapping
      - {"source_document=attachment_id (use the attachment ID from prep output)" if is_new_format else ""}
   f) If match=True: Record as valid

Example: If field_id="4002", prep_value="Sorensen", encompass_value="Sorenson"
→ compare_prep_vs_encompass_value returns needs_correction=True
→ write_corrected_field(loan_id, "4002", "Sorensen", reason, finding, field_mapping{', source_document=attachment_id' if is_new_format else ''}) updates Encompass
→ Correction record includes {"actual source document attachment ID" if is_new_format else "source_document from field_mapping"}

3. Generate a comprehensive validation report with all corrections made

IMPORTANT: Do NOT search for field mapping or SOP configuration files.
- All field mappings ({len(field_mapping)} fields) are ALREADY AVAILABLE through the tools
- All SOP rules ({len(sop_rules.get('page_indexed_rules', {}))} pages) are ALREADY AVAILABLE through the tools
- The tools (get_missing_field_value, write_corrected_field, compare_prep_vs_encompass_value) have direct access to this configuration data
- Just call the tools with the required parameters - they will handle the rest

Start verification now. Process each field systematically."""
    
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
    print(f"  - Primary tools: get_missing_field_value, write_corrected_field, cross_check_field_with_sop")
    print("\nTo run verification, use: run_verification(loan_id, prep_output)")
    print("\nWorkflow:")
    print("  1. Reads field_mappings from prep_output (CORRECT values)")
    print("  2. Fetches current Encompass values for comparison")
    print("  3. Corrects any mismatches immediately")
    print("\n⚠️  DRY RUN MODE (for testing on production):")
    print("  - Set environment variable: DRY_RUN=true")
    print("  - Or call: run_verification(loan_id, prep_output, dry_run=True)")
    print("  - This will print corrections but NOT write to Encompass")

