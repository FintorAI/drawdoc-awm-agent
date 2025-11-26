"""
Verification tools for the Verification Sub-Agent.

These tools perform value comparison between prep output and Encompass,
SOP validation, and field correction writing.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.types import Command
from typing import Annotated
from langchain_core.messages import ToolMessage

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from copilotagent import EncompassConnect
from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv(Path(__file__).parent.parent.parent.parent.parent / ".env")


def _get_encompass_client() -> EncompassConnect:
    """Get an initialized Encompass client with credentials from environment variables."""
    return EncompassConnect(
        access_token=os.getenv("ENCOMPASS_ACCESS_TOKEN", ""),
        api_base_url=os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com"),
        credentials={
            "username": os.getenv("ENCOMPASS_USERNAME", ""),
            "password": os.getenv("ENCOMPASS_PASSWORD", ""),
            "client_id": os.getenv("ENCOMPASS_CLIENT_ID", ""),
            "client_secret": os.getenv("ENCOMPASS_CLIENT_SECRET", ""),
            "instance_id": os.getenv("ENCOMPASS_INSTANCE_ID", ""),
            "subject_user_id": os.getenv("ENCOMPASS_SUBJECT_USER_ID", ""),
        },
        landingai_api_key=os.getenv("LANDINGAI_API_KEY", ""),
    )


@tool
def compare_prep_vs_encompass_value(
    field_id: str,
    prep_value: Any,
    encompass_value: Any,
    field_mapping: dict
) -> dict[str, Any]:
    """
    Compare prep output value (correct) against Encompass value (potentially wrong).
    
    This is the primary verification tool. Prep output values are considered CORRECT
    (extracted from documents), and Encompass values may need correction.
    
    Args:
        field_id: The Encompass field ID
        prep_value: The correct value from prep output (extracted from documents)
        encompass_value: The current value in Encompass
        field_mapping: Field mapping configuration from CSV
        
    Returns:
        Dictionary containing:
        - field_id: The field ID
        - field_name: The field name
        - match: True if values match, False if they differ
        - prep_value: The correct value from prep output
        - encompass_value: The current Encompass value
        - finding: Human-readable description of comparison result
        - needs_correction: True if Encompass needs to be corrected
        - reason: Detailed explanation if mismatch found
    """
    field_name = field_mapping.get(field_id, {}).get("field_name", field_id) if field_id in field_mapping else field_id
    
    # Handle None/empty values
    prep_str = str(prep_value).strip() if prep_value is not None else ""
    encompass_str = str(encompass_value).strip() if encompass_value is not None else ""
    
    # Normalize for comparison (case-insensitive, strip whitespace)
    prep_normalized = prep_str.lower()
    encompass_normalized = encompass_str.lower()
    
    match = prep_normalized == encompass_normalized
    
    if match:
        return {
            "field_id": field_id,
            "field_name": field_name,
            "match": True,
            "prep_value": prep_value,
            "encompass_value": encompass_value,
            "finding": f"Field {field_name} matches: '{prep_value}'",
            "needs_correction": False,
            "reason": None
        }
    else:
        return {
            "field_id": field_id,
            "field_name": field_name,
            "match": False,
            "prep_value": prep_value,
            "encompass_value": encompass_value,
            "finding": f"Field {field_name} mismatch: Prep='{prep_value}' vs Encompass='{encompass_value}'",
            "needs_correction": True,
            "reason": f"Prep output shows '{prep_value}' (extracted from documents) but Encompass has '{encompass_value}'. Encompass value needs correction."
        }


@tool
def verify_field_against_documents(
    field_id: str,
    field_value: Any,
    loan_id: str,
    extracted_documents: dict[str, dict],
    field_mapping: dict
) -> dict[str, Any]:
    """
    Verify field value against required documents (fail-fast).
    
    Checks the field value against primary document first, then secondary documents
    sequentially. Stops at the first discrepancy found (fail-fast approach).
    
    Args:
        field_id: The Encompass field ID (e.g., "4000")
        field_value: The current field value to verify
        loan_id: The Encompass loan GUID
        extracted_documents: Dictionary of extracted document data keyed by document type
        field_mapping: Field mapping configuration from CSV
        
    Returns:
        Dictionary containing:
        - field_id: The field ID verified
        - status: "valid" | "invalid" | "unable_to_verify"
        - checked_documents: List of documents checked
        - first_discrepancy: Details of first mismatch found (if any)
        - finding: Human-readable description of what was found
        - reason: Detailed explanation of why validation failed
    """
    if field_id not in field_mapping:
        return {
            "field_id": field_id,
            "status": "unable_to_verify",
            "checked_documents": [],
            "first_discrepancy": None,
            "finding": f"Field ID {field_id} not found in field mapping",
            "reason": "Field mapping does not contain configuration for this field"
        }
    
    mapping = field_mapping[field_id]
    field_name = mapping.get("field_name", field_id)
    primary_doc = mapping.get("primary_document", "")
    secondary_docs = mapping.get("secondary_documents", [])
    
    # If no documents specified, can't verify
    if not primary_doc and not secondary_docs:
        return {
            "field_id": field_id,
            "field_name": field_name,
            "status": "unable_to_verify",
            "checked_documents": [],
            "first_discrepancy": None,
            "finding": f"No documents specified for {field_name} verification",
            "reason": "Field mapping does not specify which documents to check"
        }
    
    checked_documents = []
    
    # Check primary document first (fail-fast)
    if primary_doc:
        doc_data = extracted_documents.get(primary_doc, {})
        
        if not doc_data:
            return {
                "field_id": field_id,
                "field_name": field_name,
                "status": "unable_to_verify",
                "checked_documents": checked_documents,
                "first_discrepancy": None,
                "finding": f"Primary document '{primary_doc}' not found in extracted documents",
                "reason": f"Document '{primary_doc}' required for verification but not available in prep output"
            }
        
        checked_documents.append(primary_doc)
        
        # Look for field value in extracted document data
        # Documents may have nested data, need to search for matching values
        doc_extracted = doc_data.get("extracted_data", {})
        
        # Try to find matching field in extracted data
        # Use field name to match (convert to snake_case for comparison)
        field_name_snake = field_name.lower().replace(' ', '_').replace('-', '_')
        
        # Check for exact match or similar keys
        found_value = None
        for key, value in doc_extracted.items():
            key_normalized = key.lower().replace(' ', '_').replace('-', '_')
            if field_name_snake in key_normalized or key_normalized in field_name_snake:
                found_value = value
                break
        
        # Also check if field_id is in the document mapping
        if not found_value and field_id in doc_data:
            found_value = doc_data[field_id]
        
        # Compare values if found
        if found_value is not None:
            # Normalize for comparison (case-insensitive, strip whitespace)
            field_value_norm = str(field_value).strip().lower()
            found_value_norm = str(found_value).strip().lower()
            
            if field_value_norm != found_value_norm:
                return {
                    "field_id": field_id,
                    "field_name": field_name,
                    "status": "invalid",
                    "checked_documents": checked_documents,
                    "first_discrepancy": {
                        "document": primary_doc,
                        "expected": found_value,
                        "actual": field_value
                    },
                    "finding": f"Field value '{field_value}' does not match '{found_value}' in {primary_doc}",
                    "reason": f"Document cross-check failed - {primary_doc} (primary source) shows '{found_value}' but field value is '{field_value}'. Values must match exactly per SOP."
                }
    
    # Check secondary documents sequentially (fail-fast)
    for doc_type in secondary_docs:
        doc_data = extracted_documents.get(doc_type, {})
        
        if not doc_data:
            # Secondary document missing is not a hard failure, continue
            continue
        
        checked_documents.append(doc_type)
        
        # Similar verification logic as primary
        doc_extracted = doc_data.get("extracted_data", {})
        field_name_snake = field_name.lower().replace(' ', '_').replace('-', '_')
        
        found_value = None
        for key, value in doc_extracted.items():
            key_normalized = key.lower().replace(' ', '_').replace('-', '_')
            if field_name_snake in key_normalized or key_normalized in field_name_snake:
                found_value = value
                break
        
        if not found_value and field_id in doc_data:
            found_value = doc_data[field_id]
        
        if found_value is not None:
            field_value_norm = str(field_value).strip().lower()
            found_value_norm = str(found_value).strip().lower()
            
            if field_value_norm != found_value_norm:
                return {
                    "field_id": field_id,
                    "field_name": field_name,
                    "status": "invalid",
                    "checked_documents": checked_documents,
                    "first_discrepancy": {
                        "document": doc_type,
                        "expected": found_value,
                        "actual": field_value
                    },
                    "finding": f"Field value '{field_value}' does not match '{found_value}' in {doc_type}",
                    "reason": f"Document cross-check failed - {doc_type} (secondary source) shows '{found_value}' but field value is '{field_value}'. Values must be consistent across documents."
                }
    
    # All checks passed
    return {
        "field_id": field_id,
        "field_name": field_name,
        "status": "valid",
        "checked_documents": checked_documents,
        "first_discrepancy": None,
        "finding": f"Field value '{field_value}' verified across {len(checked_documents)} document(s)",
        "reason": None
    }


@tool
def cross_check_field_with_sop(
    field_id: str,
    field_value: Any,
    sop_rules: dict,
    field_mapping: dict
) -> dict[str, Any]:
    """
    Validate field against SOP rules for that field.
    
    Checks if the field value complies with SOP requirements based on the
    field's referenced SOP pages and validation rules.
    
    Args:
        field_id: The Encompass field ID
        field_value: The current field value to validate
        sop_rules: SOP rules indexed by page number
        field_mapping: Field mapping configuration from CSV
        
    Returns:
        Dictionary containing:
        - field_id: The field ID validated
        - field_name: The field name
        - sop_valid: True if passes SOP validation, False otherwise
        - sop_pages_checked: List of SOP pages referenced
        - violations: List of validation rule violations
        - finding: Human-readable description of validation result
        - reason: Detailed explanation of why validation failed
        - recommendation: Suggested correction (if applicable)
        - correction_value: Recommended corrected value (if determinable)
    """
    if field_id not in field_mapping:
        return {
            "field_id": field_id,
            "sop_valid": True,  # Can't validate without mapping
            "sop_pages_checked": [],
            "violations": [],
            "finding": f"Field ID {field_id} not found in field mapping",
            "reason": "Cannot validate against SOP without field configuration",
            "recommendation": None,
            "correction_value": None
        }
    
    mapping = field_mapping[field_id]
    field_name = mapping.get("field_name", field_id)
    sop_pages = mapping.get("sop_pages", [])
    validation_rules = mapping.get("validation_rules", [])
    notes = mapping.get("notes", "")
    
    if not sop_pages and not validation_rules:
        return {
            "field_id": field_id,
            "field_name": field_name,
            "sop_valid": True,  # No rules to validate against
            "sop_pages_checked": [],
            "violations": [],
            "finding": f"No SOP rules defined for {field_name}",
            "reason": None,
            "recommendation": None,
            "correction_value": None
        }
    
    violations = []
    
    # Check validation rules from field mapping (extracted from notes)
    field_value_str = str(field_value).strip()
    
    for rule in validation_rules:
        rule_lower = rule.lower()
        
        # Check for common validation patterns
        if "must be exact match" in rule_lower:
            # This is typically checked in document verification
            # SOP validation focuses on format/completeness
            pass
        
        elif "required" in rule_lower and not field_value_str:
            violations.append(f"Field is required but empty: {rule}")
        
        elif "must match" in rule_lower and "1003" in rule_lower:
            # Cross-document match - typically verified in document check
            pass
        
        elif "middle initial" in rule_lower:
            # Check if middle initial should be present
            if "no middle initial" in rule_lower and len(field_value_str.split()) > 2:
                violations.append(f"Field should not have middle initial: {rule}")
            elif "must have middle initial" in rule_lower and len(field_value_str.split()) <= 1:
                violations.append(f"Field must have middle initial: {rule}")
        
        elif "verify" in rule_lower or "check" in rule_lower:
            # General verification requirement - requires manual review
            pass
    
    # Collect applicable SOP rules from referenced pages
    applicable_sop_rules = []
    for page in sop_pages:
        if page in sop_rules.get("page_indexed_rules", {}):
            page_data = sop_rules["page_indexed_rules"][page]
            page_rules = page_data.get("rules", [])
            applicable_sop_rules.extend(page_rules)
    
    if violations:
        return {
            "field_id": field_id,
            "field_name": field_name,
            "sop_valid": False,
            "sop_pages_checked": sop_pages,
            "violations": violations,
            "finding": f"SOP validation failed for {field_name}: {len(violations)} violation(s)",
            "reason": f"SOP Pages {', '.join(sop_pages)} require: {'; '.join(violations)}",
            "recommendation": f"Review field value against SOP requirements: {notes[:200]}",
            "correction_value": None  # Manual determination required
        }
    
    return {
        "field_id": field_id,
        "field_name": field_name,
        "sop_valid": True,
        "sop_pages_checked": sop_pages,
        "violations": [],
        "finding": f"Field {field_name} passes SOP validation",
        "reason": None,
        "recommendation": None,
        "correction_value": None
    }


@tool
def attempt_field_inference(
    field_id: str,
    available_documents: dict[str, dict],
    field_mapping: dict
) -> dict[str, Any]:
    """
    Try to infer missing field value from other documents.
    
    When a field value is missing, attempts to extract it from documents that
    typically contain that field based on the field mapping.
    
    Args:
        field_id: The Encompass field ID
        available_documents: Dictionary of extracted document data
        field_mapping: Field mapping configuration from CSV
        
    Returns:
        Dictionary containing:
        - field_id: The field ID
        - field_name: The field name
        - inferred: True if value was inferred, False otherwise
        - inferred_value: The inferred value (if successful)
        - source_document: Document from which value was inferred
        - confidence: "high" | "medium" | "low" confidence in inference
        - finding: Description of inference result
        - reason: Explanation of inference logic
    """
    if field_id not in field_mapping:
        return {
            "field_id": field_id,
            "inferred": False,
            "inferred_value": None,
            "source_document": None,
            "confidence": "low",
            "finding": f"Field ID {field_id} not found in field mapping",
            "reason": "Cannot infer without field configuration"
        }
    
    mapping = field_mapping[field_id]
    field_name = mapping.get("field_name", field_id)
    primary_doc = mapping.get("primary_document", "")
    secondary_docs = mapping.get("secondary_documents", [])
    
    # Try primary document first
    documents_to_check = []
    if primary_doc:
        documents_to_check.append((primary_doc, "high"))
    for doc in secondary_docs:
        documents_to_check.append((doc, "medium"))
    
    # Try to extract value from each document
    for doc_type, confidence in documents_to_check:
        doc_data = available_documents.get(doc_type, {})
        
        if not doc_data:
            continue
        
        # Look for field value in extracted document data
        doc_extracted = doc_data.get("extracted_data", {})
        field_name_snake = field_name.lower().replace(' ', '_').replace('-', '_')
        
        # Try to find matching field
        found_value = None
        matched_key = None
        
        for key, value in doc_extracted.items():
            key_normalized = key.lower().replace(' ', '_').replace('-', '_')
            if field_name_snake in key_normalized or key_normalized in field_name_snake:
                found_value = value
                matched_key = key
                break
        
        # Also check if field_id is directly in the document
        if not found_value and field_id in doc_data:
            found_value = doc_data[field_id]
            matched_key = field_id
        
        if found_value is not None and str(found_value).strip():
            return {
                "field_id": field_id,
                "field_name": field_name,
                "inferred": True,
                "inferred_value": found_value,
                "source_document": doc_type,
                "confidence": confidence,
                "finding": f"Field value '{found_value}' inferred from {doc_type}",
                "reason": f"Field missing in Encompass but found in {doc_type} document (key: {matched_key})"
            }
    
    # Could not infer
    return {
        "field_id": field_id,
        "field_name": field_name,
        "inferred": False,
        "inferred_value": None,
        "source_document": None,
        "confidence": "low",
        "finding": f"Unable to infer {field_name} from available documents",
        "reason": f"Checked {len(documents_to_check)} document(s) but no matching value found"
    }


@tool
def write_corrected_field(
    tool_call_id: Annotated[str, InjectedToolCallId],
    loan_id: str,
    field_id: str,
    corrected_value: Any,
    reason: str,
    finding: str,
    field_mapping: dict = None,
    source_document: str = None
) -> Command:
    """
    Write corrected value back to Encompass field.
    
    Updates an Encompass field with a corrected value and records the correction
    in the agent state for tracking and reporting.
    
    ⚠️ DRY RUN MODE: Set environment variable DRY_RUN=true to prevent actual writes.
    In dry run mode, corrections are logged but NOT written to Encompass.
    
    Args:
        loan_id: The Encompass loan GUID
        field_id: The field ID to update
        corrected_value: The corrected value to write
        reason: Why the correction was needed (e.g., "SOP violation", "Document mismatch")
        finding: Detailed explanation of what was wrong
        field_mapping: Field mapping configuration (optional, used to get source document if source_document not provided)
        source_document: Source document reference (attachment ID or document type). 
                        If provided, this takes precedence over field_mapping.
        
    Returns:
        Command that updates state with correction record
    """
    # Get source document info
    # Priority: 1) source_document parameter, 2) field_mapping primary_document
    field_name = field_id
    
    if source_document is None and field_mapping and field_id in field_mapping:
        # Fall back to field_mapping if source_document not provided
        mapping = field_mapping[field_id]
        field_name = mapping.get("field_name", field_id)
        source_document = mapping.get("primary_document", "Unknown")
    elif field_mapping and field_id in field_mapping:
        # Use provided source_document but still get field_name from mapping
        field_name = field_mapping[field_id].get("field_name", field_id)
    
    # Check if DRY RUN mode is enabled
    dry_run = os.getenv("DRY_RUN", "false").lower() in ("true", "1", "yes")
    
    if dry_run:
        # DRY RUN MODE - Don't actually write to Encompass
        print(f"\n{'='*80}")
        print(f"🔍 DRY RUN - Field Correction (NOT written to Encompass)")
        print(f"{'='*80}")
        print(f"Loan ID:         {loan_id}")
        print(f"Field ID:        {field_id}")
        print(f"Field Name:      {field_name}")
        print(f"Source Document: {source_document}")
        print(f"Corrected Value: {corrected_value}")
        print(f"Finding:         {finding}")
        print(f"Reason:          {reason}")
        print(f"{'='*80}\n")
        
        success = True  # Simulated success
        message = f"🔍 [DRY RUN] Would correct field {field_id} to '{corrected_value}'. Reason: {reason}"
    else:
        # PRODUCTION MODE - Actually write to Encompass
        print(f"\n⚠️  WRITING TO ENCOMPASS: Field {field_id} → '{corrected_value}'")
        client = _get_encompass_client()
        success = client.write_field(loan_id, field_id, corrected_value)
        message = f"✓ Corrected field {field_id} to '{corrected_value}'. Reason: {reason}"
    
    # Create correction record
    correction_record = {
        "field_id": field_id,
        "field_name": field_name,
        "source_document": source_document,
        "corrected_value": corrected_value,
        "reason": reason,
        "finding": finding,
        "success": success,
        "dry_run": dry_run,
        "timestamp": str(datetime.now())
    }
    
    # Return the correction record directly
    # Note: Command doesn't support messages parameter in this version
    return correction_record


if __name__ == "__main__":
    """Test the verification tools."""
    print("Verification tools loaded successfully")
    print(f"Primary tools: compare_prep_vs_encompass_value, write_corrected_field")
    print(f"Optional tools: cross_check_field_with_sop")
    print(f"Legacy tools: verify_field_against_documents, attempt_field_inference")

