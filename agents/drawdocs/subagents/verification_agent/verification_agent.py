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
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from copilotagent import create_deep_agent
from agents.drawdocs.subagents.verification_agent.tools.verification_tools import (
    compare_prep_vs_encompass_value,
    verify_field_against_documents,
    cross_check_field_with_sop,
    attempt_field_inference,
    write_corrected_field
)
from agents.drawdocs.subagents.verification_agent.tools.field_lookup_tools import (
    get_field_id_from_name,
    get_missing_field_value
)
from agents.drawdocs.subagents.verification_agent.tools.usps_validation_tools import (
    validate_usps_addresses
)
from agents.drawdocs.subagents.verification_agent.tools.insurance_validation_tools import (
    validate_insurance
)
from agents.drawdocs.subagents.verification_agent.tools.escrow_validation_tools import (
    validate_escrow_setup
)
from agents.drawdocs.subagents.verification_agent.tools.fee_tolerance_tools import (
    validate_fee_tolerance
)
from agents.drawdocs.subagents.verification_agent.tools.fee_mapping_tools import (
    validate_apr_flags
)
from agents.drawdocs.subagents.verification_agent.tools.cd_page_tools import (
    validate_changed_circumstance,
    validate_cd_page_3,
    validate_cd_page_4
)
from agents.drawdocs.subagents.verification_agent.tools.entry_conditions_tools import (
    validate_entry_conditions
)
from agents.drawdocs.subagents.verification_agent.tools.mers_verification_tools import (
    validate_mers_min
)
from agents.drawdocs.subagents.verification_agent.tools.fha_validation_tools import (
    validate_fha_loan
)
from agents.drawdocs.subagents.verification_agent.tools.va_validation_tools import (
    validate_va_loan
)
from agents.drawdocs.subagents.verification_agent.tools.state_validation_tools import (
    validate_state_specific_rules
)
from agents.drawdocs.subagents.verification_agent.tools.closing_conditions_tools import (
    validate_closing_conditions
)
from agents.drawdocs.subagents.verification_agent.tools.hard_stop_escalations_tools import (
    validate_hard_stops
)
from agents.drawdocs.subagents.verification_agent.tools.file_contacts_validation_tools import (
    validate_file_contacts
)
from agents.drawdocs.subagents.verification_agent.config.field_document_mapping import FIELD_MAPPING
from agents.drawdocs.subagents.verification_agent.config.sop_rules import SOP_RULES

# Load environment variables from project root
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")


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
        # Validation tools (USPS, Insurance, Escrow)
        validate_usps_addresses,
        validate_insurance,
        validate_escrow_setup,
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
        Dictionary with validation results including:
        - status: "success" | "failed" | "needs_review"
        - loan_context: Loan metadata from Encompass
        - validation_results: Detailed results for each field
        - corrections_made: List of corrections written
        
    Note:
        ⚠️ DRY RUN MODE: Set dry_run=True or environment variable DRY_RUN=true
        to prevent actual writes to Encompass. Use this for testing on production.
    """
    import json
    
    # ==========================================================================
    # ENTRY CONDITIONS (PREREQUISITES) - MUST RUN FIRST
    # ==========================================================================
    print(f"\n{'='*80}")
    print("VERIFICATION AGENT - Starting")
    print(f"{'='*80}")
    print(f"Loan ID: {loan_id}")
    
    # Validate entry conditions FIRST - these are HARD STOPS
    # NOTE: Entry conditions ALWAYS run (even in dry-run/demo mode) - they are read-only checks
    print("\n" + "="*80)
    print("PHASE 0: ENTRY CONDITIONS (PREREQUISITES)")
    print("="*80)
    print("ℹ️  Entry conditions are READ-ONLY checks - always run regardless of dry-run mode")
    
    entry_conditions_validation = None
    try:
        print("\n🔍 Validating entry conditions (CTC, CD Approved, CD Acknowledged, 3-Day Wait, Docs Ordered Queue)...")
        entry_conditions_validation = validate_entry_conditions(loan_id)
        
        if entry_conditions_validation:
            all_conditions_met = entry_conditions_validation.get('all_conditions_met', False)
            blocking_conditions = entry_conditions_validation.get('blocking_conditions', [])
            
            if all_conditions_met:
                print(f"[VERIFICATION] ✅ ALL ENTRY CONDITIONS MET - Proceeding with verification")
            else:
                print(f"[VERIFICATION] ❌ BLOCKING CONDITIONS FOUND: {len(blocking_conditions)} conditions not met")
                print(f"[VERIFICATION] ⚠️  Loan is NOT ready for DrawDocs processing")
                for block in blocking_conditions:
                    print(f"  - {block['condition']}: {block['message']}")
                
                # Log blocking conditions but continue (agent can still validate other things)
                print(f"[VERIFICATION] ⚠️  Continuing with validation, but loan should not proceed to DrawDocs")
    except Exception as entry_error:
        print(f"[VERIFICATION] WARNING: Could not run entry conditions validation: {entry_error}")
        entry_conditions_validation = {"error": str(entry_error)}
    
    print("\n" + "="*80)
    print("PHASE 0 COMPLETE")
    print("="*80)
    
    # ========================================
    # PHASE 1: HARD STOP ESCALATIONS
    # ========================================
    print("\n" + "="*80)
    print("PHASE 1: HARD STOP ESCALATIONS")
    print("="*80)
    
    hard_stops = None
    try:
        print("\n🛑 Checking for hard stops (Approval Expiration, ARM Lock Desk, Pre-Funding QC, Random Fees)...")
        hard_stops = validate_hard_stops(loan_id)
        
        if hard_stops:
            hard_stops_found = hard_stops.get('hard_stops_found', False)
            hard_stops_list = hard_stops.get('hard_stops', [])
            warnings = hard_stops.get('warnings', [])
            
            if hard_stops_found:
                print(f"[VERIFICATION] 🛑 CRITICAL: {len(hard_stops_list)} HARD STOP(S) FOUND - PROCESSING MUST HALT")
                for stop in hard_stops_list:
                    print(f"[VERIFICATION]   - {stop['title']}: {stop['message']}")
                    print(f"[VERIFICATION]     Escalate to: {stop['escalation_required']}")
            else:
                print(f"[VERIFICATION] ✅ No hard stops found")
            
            if warnings:
                print(f"[VERIFICATION] ⚠️  {len(warnings)} warning(s) - some field IDs may be missing")
    except Exception as hs_error:
        print(f"[VERIFICATION] WARNING: Could not run hard stop validation: {hs_error}")
        hard_stops = {"error": str(hs_error)}
    
    print("\n" + "="*80)
    print("PHASE 1 COMPLETE")
    print("="*80)
    
    # ========================================
    # PHASE 4: MERS MIN VALIDATION
    # ========================================
    print("\n" + "="*80)
    print("PHASE 4: MERS MIN VALIDATION")
    print("="*80)
    
    # MERS validation temporarily disabled - API not hosted yet
    # TODO: Re-enable when MERS API is available
    mers_validation = {
        "status": "skipped",
        "message": "MERS validation temporarily disabled - API not hosted yet",
        "violations": [],
        "warnings": []
    }
    print("\n⏭️  Skipping MERS MIN validation (API not hosted yet)")
    
    # Original MERS validation code (commented out for now)
    # try:
    #     print("\n🔍 Validating MERS MIN number (generation, uniqueness, SSN search)...")
    #     mers_validation = validate_mers_min(loan_id)
    #     
    #     if mers_validation:
    #         mers_status = mers_validation.get('status', 'unknown')
    #         violations = mers_validation.get('violations', [])
    #         warnings = mers_validation.get('warnings', [])
    #         min_number = mers_validation.get('min_generation', {}).get('min_number') or "Not Generated"
    #         
    #         print(f"[VERIFICATION] MERS MIN Check: Status={mers_status}")
    #         print(f"[VERIFICATION] MIN Number: {min_number}")
    #         print(f"[VERIFICATION] PTF conditions added: {len(violations)}")
    #         print(f"[VERIFICATION] Warnings: {len(warnings)}")
    #         
    #         if violations:
    #             print(f"[VERIFICATION] ⚠️  Found {len(violations)} MERS violations")
    #             for violation in violations:
    #                 print(f"  - {violation['message']}")
    #         else:
    #             print(f"[VERIFICATION] ✅ No MERS violations")
    #         
    #         if warnings:
    #             print(f"[VERIFICATION] ℹ️  {len(warnings)} manual verification steps required")
    #             for warning in warnings:
    #                 print(f"  - {warning['message']}")
    # except Exception as mers_error:
    #     print(f"[VERIFICATION] WARNING: Could not run MERS validation: {mers_error}")
    #     mers_validation = {"error": str(mers_error)}
    
    print("\n" + "="*80)
    print("PHASE 4 COMPLETE")
    print("="*80)
    
    # ========================================
    # PHASE 5: LOAN TYPE SPECIFIC VALIDATIONS
    # ========================================
    print("\n" + "="*80)
    print("PHASE 5: LOAN TYPE SPECIFIC VALIDATIONS")
    print("="*80)
    
    # Get loan context to check loan type
    try:
        from agents.drawdocs.tools import get_loan_context
        loan_context = get_loan_context(loan_id, include_milestones=False)
        loan_type = loan_context.get("loan_type", "").upper()
        
        # FHA Loan Validation
        fha_validation = None
        if "FHA" in loan_type:
            print("\n🔍 Validating FHA-specific requirements (Case Assignment, Refi Authorization, MIP Refund)...")
            try:
                fha_validation = validate_fha_loan(loan_id)
                
                if fha_validation:
                    fha_status = fha_validation.get('status', 'unknown')
                    violations = fha_validation.get('violations', [])
                    is_refi = fha_validation.get('is_refinance', False)
                    
                    print(f"[VERIFICATION] FHA Validation: Status={fha_status}")
                    print(f"[VERIFICATION] Is Refinance: {is_refi}")
                    print(f"[VERIFICATION] PTF conditions added: {len(violations)}")
                    
                    if violations:
                        print(f"[VERIFICATION] ⚠️  Found {len(violations)} FHA violations")
                        for violation in violations:
                            print(f"  - {violation['message']}")
                    else:
                        print(f"[VERIFICATION] ✅ No FHA violations")
            except Exception as fha_error:
                print(f"[VERIFICATION] WARNING: Could not run FHA validation: {fha_error}")
                fha_validation = {"error": str(fha_error)}
        else:
            print(f"\nℹ️  Loan type is '{loan_type}' - skipping FHA validation")
        
        # VA Loan Validation
        va_validation = None
        if "VA" in loan_type:
            print("\n🔍 Validating VA-specific requirements (Case#, Funding Fee, 26-1820 form)...")
            try:
                va_validation = validate_va_loan(loan_id)
                
                if va_validation:
                    va_status = va_validation.get('status', 'unknown')
                    violations = va_validation.get('violations', [])
                    
                    print(f"[VERIFICATION] VA Validation: Status={va_status}")
                    print(f"[VERIFICATION] PTF conditions added: {len(violations)}")
                    
                    if violations:
                        print(f"[VERIFICATION] ⚠️  Found {len(violations)} VA violations")
                        for violation in violations:
                            print(f"  - {violation['message']}")
                    else:
                        print(f"[VERIFICATION] ✅ No VA violations")
            except Exception as va_error:
                print(f"[VERIFICATION] WARNING: Could not run VA validation: {va_error}")
                va_validation = {"error": str(va_error)}
        else:
            print(f"\nℹ️  Loan type is '{loan_type}' - skipping VA validation")
        
        # TODO: Add USDA validation here
        
    except Exception as loan_type_error:
        print(f"[VERIFICATION] WARNING: Could not check loan type: {loan_type_error}")
        fha_validation = None
    
    print("\n" + "="*80)
    print("PHASE 5 COMPLETE")
    print("="*80)
    
    # ========================================
    # PHASE 6: STATE-SPECIFIC RULES
    # ========================================
    print("\n" + "="*80)
    print("PHASE 6: STATE-SPECIFIC RULES")
    print("="*80)
    
    state_validation = None
    try:
        print("\n🔍 Validating state-specific rules (TX, CA, NV, CO)...")
        state_validation = validate_state_specific_rules(loan_id)
        
        if state_validation:
            state = state_validation.get('state', 'Unknown')
            state_status = state_validation.get('status', 'unknown')
            violations = state_validation.get('violations', [])
            warnings = state_validation.get('warnings', [])
            
            print(f"[VERIFICATION] State Validation: State={state}, Status={state_status}")
            print(f"[VERIFICATION] PTF conditions added: {len(violations)}")
            print(f"[VERIFICATION] Warnings: {len(warnings)}")
            
            if violations:
                print(f"[VERIFICATION] ⚠️  Found {len(violations)} state violations")
                for violation in violations:
                    print(f"  - {violation['message']}")
            else:
                print(f"[VERIFICATION] ✅ No state violations")
            
            if warnings:
                print(f"[VERIFICATION] ℹ️  {len(warnings)} state-specific warnings")
                for warning in warnings:
                    print(f"  - {warning['message']}")
    except Exception as state_error:
        print(f"[VERIFICATION] WARNING: Could not run state validation: {state_error}")
        state_validation = {"error": str(state_error)}
    
    print("\n" + "="*80)
    print("PHASE 6 COMPLETE")
    print("="*80)
    
    # ========================================
    # PHASE 7: CLOSING CONDITIONS MANAGEMENT
    # ========================================
    print("\n" + "="*80)
    print("PHASE 7: CLOSING CONDITIONS MANAGEMENT")
    print("="*80)
    
    closing_conditions = None
    try:
        print("\n🔍 Validating and generating closing conditions...")
        closing_conditions = validate_closing_conditions(loan_id)
        
        if closing_conditions:
            conditions_to_add = closing_conditions.get('conditions_to_add', [])
            ptf_from_uw = closing_conditions.get('ptf_conditions_from_uw', [])
            warnings = closing_conditions.get('warnings', [])
            
            print(f"[VERIFICATION] Closing Conditions: {len(conditions_to_add)} conditions to add")
            print(f"[VERIFICATION] PTF from UW: {len(ptf_from_uw)} conditions to copy")
            print(f"[VERIFICATION] Warnings: {len(warnings)}")
            
            if conditions_to_add:
                print(f"[VERIFICATION] ✅ Generated {len(conditions_to_add)} closing conditions")
                for condition in conditions_to_add:
                    print(f"  - {condition.get('type', 'unknown')}: {condition.get('description', '')[:60]}...")
            
            if ptf_from_uw:
                print(f"[VERIFICATION] ℹ️  {len(ptf_from_uw)} PTF condition(s) from UW to copy")
            
            if warnings:
                print(f"[VERIFICATION] ⚠️  {len(warnings)} warning(s) - some field IDs may be missing")
    except Exception as cc_error:
        print(f"[VERIFICATION] WARNING: Could not run closing conditions validation: {cc_error}")
        closing_conditions = {"error": str(cc_error)}
    
    print("\n" + "="*80)
    print("PHASE 7 COMPLETE")
    print("="*80)
    
    # ========================================
    # PHASE 8: FILE CONTACTS VALIDATION
    # ========================================
    print("\n" + "="*80)
    print("PHASE 8: FILE CONTACTS VALIDATION")
    print("="*80)
    
    file_contacts = None
    try:
        print("\n🔍 Validating File Contacts (Lender, Investor, Title, Escrow, Settlement Agent)...")
        file_contacts = validate_file_contacts(loan_id)
        
        if file_contacts:
            validations = file_contacts.get('validations', {})
            violations = file_contacts.get('violations', [])
            warnings = file_contacts.get('warnings', [])
            
            print(f"[VERIFICATION] File Contacts: {len(validations)} sections validated")
            print(f"[VERIFICATION] Violations: {len(violations)}")
            print(f"[VERIFICATION] Warnings: {len(warnings)}")
            
            if violations:
                print(f"[VERIFICATION] ⚠️  Found {len(violations)} file contacts violations")
                for violation in violations:
                    print(f"  - {violation.get('category', 'unknown')}: {violation.get('message', '')}")
            else:
                print(f"[VERIFICATION] ✅ No file contacts violations")
            
            if warnings:
                print(f"[VERIFICATION] ℹ️  {len(warnings)} warning(s) - some field IDs may be missing")
    except Exception as fc_error:
        print(f"[VERIFICATION] WARNING: Could not run file contacts validation: {fc_error}")
        file_contacts = {"error": str(fc_error)}
    
    print("\n" + "="*80)
    print("PHASE 8 COMPLETE")
    print("="*80)
    
    # ==========================================================================
    # PRECONDITION CHECKS (using primitives)
    # ==========================================================================
    try:
        # Import primitives for precondition checks
        from agents.drawdocs.tools import get_loan_context, log_issue
        
        print(f"\nChecking loan preconditions...")
        if 'loan_context' not in locals():
            loan_context = get_loan_context(loan_id, include_milestones=False)
        
        # ALWAYS run SOP field verification first (independent of prep status)
        print(f"\n[VERIFICATION] Running full SOP field verification for loan {loan_id}...")
        sop_verification = None
        try:
            from agents.drawdocs.tools.primitives import verify_all_sop_fields
            sop_verification = verify_all_sop_fields(loan_id)
            
            if sop_verification:
                summary = sop_verification.get("summary", {})
                print(f"[VERIFICATION] SOP Check: {summary.get('populated', 0)}/{summary.get('total', 0)} fields populated ({summary.get('completion_pct', 0)}%)")
                print(f"[VERIFICATION] Missing fields: {summary.get('missing', 0)} ({summary.get('required_missing', 0)} required)")
                print(f"[VERIFICATION] Documents needed: {summary.get('documents_needed_count', 0)}")
        except Exception as sop_error:
            print(f"[VERIFICATION] WARNING: Could not run SOP verification: {sop_error}")
            sop_verification = {"error": str(sop_error)}
        
        # Run USPS address validation (independent of prep status)
        print(f"\n[VERIFICATION] Running USPS address validation for loan {loan_id}...")
        usps_validation = None
        try:
            usps_validation = validate_usps_addresses(loan_id)
        
            if usps_validation:
                print(f"[VERIFICATION] USPS Check: {usps_validation.get('addresses_validated', 0)} addresses validated")
                print(f"[VERIFICATION] Addresses passed: {usps_validation.get('addresses_passed', 0)}")
                print(f"[VERIFICATION] Addresses flagged: {usps_validation.get('addresses_flagged', 0)}")
                print(f"[VERIFICATION] PTF conditions added: {usps_validation.get('ptf_conditions_added', 0)}")
        except Exception as usps_error:
            print(f"[VERIFICATION] WARNING: Could not run USPS validation: {usps_error}")
            usps_validation = {"error": str(usps_error)}
    
        # Run Insurance validation (HOI + Flood) - independent of prep status
        print(f"\n[VERIFICATION] Running insurance validation (HOI + Flood) for loan {loan_id}...")
        insurance_validation = None
        try:
            insurance_validation = validate_insurance(loan_id)
        
            if insurance_validation:
                hoi_status = insurance_validation.get('hoi_validation', {}).get('status', 'unknown')
                flood_status = insurance_validation.get('flood_validation', {}).get('status', 'unknown')
                total_ptf = insurance_validation.get('total_ptf_conditions', 0)
                hardstops = insurance_validation.get('hardstops', [])
            
                print(f"[VERIFICATION] Insurance Check: HOI={hoi_status}, Flood={flood_status}")
                print(f"[VERIFICATION] PTF conditions added: {total_ptf}")
                if hardstops:
                    print(f"[VERIFICATION] ⚠️  HARDSTOPS: {', '.join(hardstops)}")
        except Exception as insurance_error:
            print(f"[VERIFICATION] WARNING: Could not run insurance validation: {insurance_error}")
            insurance_validation = {"error": str(insurance_error)}
    
        # Run Escrow validation - independent of prep status
        print(f"\n[VERIFICATION] Running escrow validation (taxes, insurance, cushions, impounds) for loan {loan_id}...")
        escrow_validation = None
        try:
            escrow_validation = validate_escrow_setup(loan_id)
        
            if escrow_validation:
                escrow_status = escrow_validation.get('status', 'unknown')
                total_monthly = escrow_validation.get('total_monthly_escrow', 0)
                total_ptf = escrow_validation.get('total_ptf_conditions', 0)
            
                print(f"[VERIFICATION] Escrow Check: Status={escrow_status}, Total Monthly=${total_monthly:.2f}")
                print(f"[VERIFICATION] PTF conditions added: {total_ptf}")
            
                # Show cushion validation
                cushion = escrow_validation.get('cushion_validation', {})
                if cushion.get('correct_cushions') is False:
                    print(f"[VERIFICATION] ⚠️  Cushion errors: {len(cushion.get('discrepancies', []))} issues found")
            
                # Show impound validation
                impound = escrow_validation.get('impound_validation', {})
                if impound.get('correct_setup') is False:
                    print(f"[VERIFICATION] ⚠️  Impound setup error: {impound.get('rule_applied')}")
        except Exception as escrow_error:
            print(f"[VERIFICATION] WARNING: Could not run escrow validation: {escrow_error}")
            escrow_validation = {"error": str(escrow_error)}
    
        # ========================================
        # PHASE 3: CD VALIDATION
        # ========================================
        print("\n" + "="*80)
        print("PHASE 3: CD VALIDATION")
        print("="*80)
    
        # Part 1: Fee Tolerance Validation
        fee_tolerance_validation = None
        try:
            print("\n🔍 Validating fee tolerance (Section A: 0%, Section B: 10%)...")
            fee_tolerance_validation = validate_fee_tolerance(
                loan_id=loan_id,
                loan_type=loan_context.get("loan_type", "Conventional")
            )
        
            if fee_tolerance_validation:
                tolerance_status = fee_tolerance_validation.get('status', 'unknown')
                violations = fee_tolerance_validation.get('violations', [])
                total_cure = fee_tolerance_validation.get('total_required_cure', 0)
            
                print(f"[VERIFICATION] Fee Tolerance Check: Status={tolerance_status}")
                print(f"[VERIFICATION] PTF conditions added: {len(violations)}")
                if total_cure > 0:
                    print(f"[VERIFICATION] ⚠️  Total required cure: ${total_cure:,.2f}")
            
                if violations:
                    print(f"[VERIFICATION] ⚠️  Found {len(violations)} tolerance violations")
                else:
                    print(f"[VERIFICATION] ✅ All fees within tolerance")
        except Exception as tolerance_error:
            print(f"[VERIFICATION] WARNING: Could not run fee tolerance validation: {tolerance_error}")
            fee_tolerance_validation = {"error": str(tolerance_error)}
    
        # Part 2: APR Flag Validation
        apr_flag_validation = None
        try:
            print("\n🔍 Validating APR impact flags...")
            apr_flag_validation = validate_apr_flags(loan_id=loan_id)
        
            if apr_flag_validation:
                apr_status = apr_flag_validation.get('status', 'unknown')
                violations = apr_flag_validation.get('violations', [])
            
                print(f"[VERIFICATION] APR Flags Check: Status={apr_status}")
                print(f"[VERIFICATION] PTF conditions added: {len(violations)}")
            
                if violations:
                    print(f"[VERIFICATION] ⚠️  Found {len(violations)} APR flag violations")
                else:
                    print(f"[VERIFICATION] ✅ All APR flags correct")
        except Exception as apr_error:
            print(f"[VERIFICATION] WARNING: Could not run APR flag validation: {apr_error}")
            apr_flag_validation = {"error": str(apr_error)}
    
        # Part 3: CD Page 4 Validation
        cd_page_4_validation = None
        try:
            print("\n🔍 Validating CD Page 4 disclosures...")
            cd_page_4_validation = validate_cd_page_4(
                loan_id=loan_id,
                loan_type=loan_context.get("loan_type", "Conventional"),
                amort_type=loan_context.get("amortization_type", "Fixed")
            )
        
            if cd_page_4_validation:
                cd4_status = cd_page_4_validation.get('status', 'unknown')
                violations = cd_page_4_validation.get('violations', [])
            
                print(f"[VERIFICATION] CD Page 4 Check: Status={cd4_status}")
                print(f"[VERIFICATION] PTF conditions added: {len(violations)}")
            
                if violations:
                    print(f"[VERIFICATION] ⚠️  Found {len(violations)} CD Page 4 violations")
                else:
                    print(f"[VERIFICATION] ✅ All CD Page 4 fields correct")
        except Exception as cd4_error:
            print(f"[VERIFICATION] WARNING: Could not run CD Page 4 validation: {cd4_error}")
            cd_page_4_validation = {"error": str(cd4_error)}
    
        # Part 4: Changed Circumstance (COC) Validation
        coc_validation = None
        try:
            print("\n🔍 Validating Changed Circumstance (COC) tracking...")
            coc_validation = validate_changed_circumstance(loan_id=loan_id)
        
            if coc_validation:
                coc_status = coc_validation.get('status', 'unknown')
                warnings = coc_validation.get('warnings', [])
            
                print(f"[VERIFICATION] COC Check: Status={coc_status}")
                print(f"[VERIFICATION] Warnings: {len(warnings)}")
            
                if warnings:
                    print(f"[VERIFICATION] ⚠️  Found {len(warnings)} COC tracking warnings")
                else:
                    print(f"[VERIFICATION] ✅ COC tracking compliant")
        except Exception as coc_error:
            print(f"[VERIFICATION] WARNING: Could not run COC validation: {coc_error}")
            coc_validation = {"error": str(coc_error)}
    
        # Part 5: CD Page 3 Validation
        cd_page_3_validation = None
        try:
            print("\n🔍 Validating CD Page 3 transaction summaries...")
            cd_page_3_validation = validate_cd_page_3(loan_id=loan_id)
        
            if cd_page_3_validation:
                cd3_status = cd_page_3_validation.get('status', 'unknown')
                violations = cd_page_3_validation.get('violations', [])
            
                print(f"[VERIFICATION] CD Page 3 Check: Status={cd3_status}")
                print(f"[VERIFICATION] Warnings: {len(violations)}")
            
                if violations:
                    print(f"[VERIFICATION] ⚠️  Found {len(violations)} CD Page 3 warnings")
                else:
                    print(f"[VERIFICATION] ✅ CD Page 3 appears correct")
        except Exception as cd3_error:
            print(f"[VERIFICATION] WARNING: Could not run CD Page 3 validation: {cd3_error}")
            cd_page_3_validation = {"error": str(cd3_error)}
    
        print("\n" + "="*80)
        print("PHASE 3 COMPLETE")
        print("="*80)
    
        # Check if prep agent completed (for field validation workflow)
        if prep_output.get("status") == "failed":
            error_msg = "Prep agent failed - cannot verify extracted fields"
            print(f"⚠️  Prep status failed: {error_msg}")
            print(f"ℹ️  SOP field verification, USPS validation, and insurance validation still completed - see output")
            log_issue(loan_id, "ERROR", error_msg)
            return {
                "status": "failed",
                "loan_id": loan_id,
                "error": error_msg,
                "loan_context": loan_context,
                "sop_verification": sop_verification,  # Include SOP results even if prep failed
                "usps_validation": usps_validation,     # Include USPS results even if prep failed
                "insurance_validation": insurance_validation,  # Include insurance results even if prep failed
                "escrow_validation": escrow_validation,  # Include escrow results even if prep failed
                "phase_0_entry_conditions": entry_conditions_validation if 'entry_conditions_validation' in locals() else None,
                "phase_4_mers_validation": mers_validation if 'mers_validation' in locals() else None,
                "phase_5_fha_validation": fha_validation if 'fha_validation' in locals() else None,
                "phase_5_va_validation": va_validation if 'va_validation' in locals() else None,
                "phase_6_state_validation": state_validation if 'state_validation' in locals() else None,
                "phase_7_closing_conditions": closing_conditions if 'closing_conditions' in locals() else None,
                "phase_8_file_contacts": file_contacts if 'file_contacts' in locals() else None,
                "phase_1_hard_stops": hard_stops if 'hard_stops' in locals() else None,
                "phase_3_fee_tolerance": fee_tolerance_validation if 'fee_tolerance_validation' in locals() else None,
                "phase_3_apr_flags": apr_flag_validation if 'apr_flag_validation' in locals() else None,
                "phase_3_cd_page_4": cd_page_4_validation if 'cd_page_4_validation' in locals() else None
            }
    
        print(f"✓ Loan context retrieved - Loan #{loan_context.get('loan_number')}, Type: {loan_context.get('loan_type')}, State: {loan_context.get('state')}")
    
    except Exception as e:
        # Don't fail if precondition check fails
        print(f"⚠️  Could not check loan preconditions: {e}")
        loan_context = {"loan_id": loan_id}
    
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
    
    # Enhance result with loan_context and SOP verification
    if isinstance(result, dict):
        result["loan_context"] = loan_context
    # Add SOP verification results (already ran at the start)
    if sop_verification:
        result["sop_verification"] = sop_verification
    # Add USPS validation results
    if usps_validation:
        result["usps_validation"] = usps_validation
    # Add insurance validation results
    if insurance_validation:
        result["insurance_validation"] = insurance_validation
    # Add escrow validation results
    if escrow_validation:
        result["escrow_validation"] = escrow_validation
    # Add USPS validation results (already ran at the start)
    if usps_validation:
        result["usps_validation"] = usps_validation
    # Add insurance validation results (already ran at the start)
    if insurance_validation:
        result["insurance_validation"] = insurance_validation
    # Add Phase 3 CD validation results
    if fee_tolerance_validation:
        result["phase_3_fee_tolerance"] = fee_tolerance_validation
    if apr_flag_validation:
        result["phase_3_apr_flags"] = apr_flag_validation
    if cd_page_4_validation:
        result["phase_3_cd_page_4"] = cd_page_4_validation
    if coc_validation:
        result["phase_3_coc_tracking"] = coc_validation
    if cd_page_3_validation:
        result["phase_3_cd_page_3"] = cd_page_3_validation
    # Add Entry Conditions (Phase 0) results
    if entry_conditions_validation:
        result["phase_0_entry_conditions"] = entry_conditions_validation
        # If entry conditions not met, set status to blocked
        if not entry_conditions_validation.get('all_conditions_met', False):
            result["status"] = "blocked_by_entry_conditions"
            result["blocking_reason"] = "Entry conditions not met - loan not ready for DrawDocs processing"
    # Add MERS Validation (Phase 4) results
    if mers_validation:
        result["phase_4_mers_validation"] = mers_validation
    # Add Loan Type Validations (Phase 5) results
    if fha_validation:
        result["phase_5_fha_validation"] = fha_validation
    if va_validation:
        result["phase_5_va_validation"] = va_validation
    # Add State-Specific Rules (Phase 6) results
    if state_validation:
        result["phase_6_state_validation"] = state_validation
    # Add Closing Conditions (Phase 7) results
    if closing_conditions:
        result["phase_7_closing_conditions"] = closing_conditions
    # Add File Contacts (Phase 8) results
    if file_contacts:
        result["phase_8_file_contacts"] = file_contacts
    # Add Hard Stop Escalations (Phase 1) results
    if hard_stops:
        result["phase_1_hard_stops"] = hard_stops
    # Determine status if not already set
    if "status" not in result:
        result["status"] = "success"  # Default to success if agent completed
    
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

