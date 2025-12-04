"""
Phase 1: Borrower & LO

Updates borrower-related fields:
- Borrower names (first, middle, last)
- Borrower vesting type
- Contact information (phone, email)
- Personal information (DOB, SSN, marital status)
- Loan officer information
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.drawdocs.tools.primitives import read_fields, write_fields, log_issue

logger = logging.getLogger(__name__)


# Field mappings for Phase 1
BORROWER_LO_FIELDS = {
    # Borrower Names
    "4000": {"name": "Borrower First Name", "source_docs": ["ID", "1003"]},
    "36": {"name": "Borrower First/Middle Name", "source_docs": ["ID", "1003"]},
    "4001": {"name": "Borrower Middle Name", "source_docs": ["ID", "1003"]},
    "4002": {"name": "Borrower Last Name", "source_docs": ["ID", "1003"]},
    
    # Vesting
    "4008": {"name": "Borrower Vesting Type", "source_docs": ["1003", "Title Report"]},
    
    # Contact Info
    "66": {"name": "Borrower Home Phone", "source_docs": ["ID", "1003"]},
    "FE0117": {"name": "Borrower Business Phone", "source_docs": ["1003"]},
    "1240": {"name": "Borrower Email", "source_docs": ["1003"]},
    
    # Personal Info
    "1402": {"name": "Borrower DOB", "source_docs": ["ID"]},
    "65": {"name": "Borrower SSN", "source_docs": ["Application", "1003"]},
    "52": {"name": "Borrower Marital Status", "source_docs": ["1003"]},
    "471": {"name": "Borrower Sex Male/Female", "source_docs": ["1003"]},
    "FR0104": {"name": "Borrower Present Addr", "source_docs": ["1003"]},
}


def process_borrower_lo_phase(
    loan_id: str,
    doc_context: Dict[str, Any],
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Process Phase 1: Borrower & LO fields.
    
    Args:
        loan_id: Encompass loan GUID
        doc_context: Prep Agent output with extracted field values
        dry_run: If True, don't actually write to Encompass
        
    Returns:
        Dictionary with phase results:
            - status: "success" | "partial_success" | "failed"
            - fields_processed: Count of fields checked
            - fields_updated: Count of fields updated (or would be in dry run)
            - issues_logged: Count of issues/discrepancies
            - updates: List of update details
            - issues: List of issue details
    """
    logger.info("[PHASE 1] Borrower & LO - Starting")
    
    result = {
        "status": "in_progress",
        "fields_processed": 0,
        "fields_updated": 0,
        "issues_logged": 0,
        "updates": [],
        "issues": []
    }
    
    try:
        # Extract field mappings from doc_context
        field_mappings = doc_context.get("results", {}).get("field_mappings", {})
        
        if not field_mappings:
            logger.warning("[PHASE 1] No field mappings found in doc_context")
            result["status"] = "failed"
            result["issues"].append({
                "type": "warning",
                "message": "No field mappings found in doc_context"
            })
            return result
        
        logger.info(f"[PHASE 1] Found {len(field_mappings)} total extracted fields")
        
        # Get list of Phase 1 field IDs that we have values for
        phase1_field_ids = [
            field_id for field_id in BORROWER_LO_FIELDS.keys()
            if field_id in field_mappings
        ]
        
        if not phase1_field_ids:
            logger.warning("[PHASE 1] No Phase 1 fields found in extracted data")
            result["status"] = "success"  # Not an error, just nothing to do
            return result
        
        logger.info(f"[PHASE 1] Processing {len(phase1_field_ids)} borrower/LO fields")
        
        # Read current Encompass values
        logger.info("[PHASE 1] Reading current Encompass field values...")
        current_values = read_fields(loan_id, phase1_field_ids)
        
        # Compare and update fields
        for field_id in phase1_field_ids:
            result["fields_processed"] += 1
            
            field_info = BORROWER_LO_FIELDS.get(field_id, {})
            field_name = field_info.get("name", field_id)
            # Extract actual value from mapping (may be dict with "value" key or simple value)
            raw_mapping = field_mappings[field_id]
            extracted_value = raw_mapping.get("value") if isinstance(raw_mapping, dict) and "value" in raw_mapping else raw_mapping
            current_value = current_values.get(field_id)
            
            logger.info(f"[PHASE 1] Processing {field_name} ({field_id})")
            logger.info(f"  Extracted: {extracted_value}")
            logger.info(f"  Current:   {current_value}")
            
            # Normalize values for comparison
            extracted_str = str(extracted_value).strip() if extracted_value is not None else ""
            current_str = str(current_value).strip() if current_value is not None else ""
            
            # Check if update is needed
            if extracted_str != current_str:
                logger.info(f"  → Update needed")
                
                # Perform update (or log intention in dry run)
                if not dry_run:
                    try:
                        success = write_fields(loan_id, {field_id: extracted_value})
                        if success:
                            result["fields_updated"] += 1
                            result["updates"].append({
                                "field_id": field_id,
                                "field_name": field_name,
                                "old_value": current_value,
                                "new_value": extracted_value,
                                "written": True
                            })
                            logger.info(f"  ✓ Updated successfully")
                        else:
                            result["issues_logged"] += 1
                            result["issues"].append({
                                "field_id": field_id,
                                "field_name": field_name,
                                "type": "error",
                                "message": "Write operation failed"
                            })
                            logger.error(f"  ✗ Update failed")
                            
                            # Log issue
                            log_issue(
                                loan_id=loan_id,
                                issue_type="error",
                                message=f"Failed to update {field_name}",
                                field_id=field_id
                            )
                    except Exception as e:
                        logger.error(f"  ✗ Error updating field: {e}")
                        result["issues_logged"] += 1
                        result["issues"].append({
                            "field_id": field_id,
                            "field_name": field_name,
                            "type": "error",
                            "message": str(e)
                        })
                        log_issue(
                            loan_id=loan_id,
                            issue_type="error",
                            message=f"Error updating {field_name}: {str(e)}",
                            field_id=field_id
                        )
                else:
                    # Dry run: just record the intended update
                    result["fields_updated"] += 1
                    result["updates"].append({
                        "field_id": field_id,
                        "field_name": field_name,
                        "old_value": current_value,
                        "new_value": extracted_value,
                        "written": False,
                        "dry_run": True
                    })
                    logger.info(f"  🔍 DRY RUN - Would update")
            else:
                logger.info(f"  ✓ Already correct")
        
        # Determine status
        if result["issues_logged"] == 0:
            result["status"] = "success"
        elif result["fields_updated"] > 0:
            result["status"] = "partial_success"
        else:
            result["status"] = "failed"
        
        logger.info(f"[PHASE 1] Complete - {result['fields_processed']} processed, "
                   f"{result['fields_updated']} updated, {result['issues_logged']} issues")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 1] Failed: {e}")
        result["status"] = "failed"
        result["issues_logged"] += 1
        result["issues"].append({
            "type": "error",
            "message": f"Phase 1 failed: {str(e)}"
        })
        return result

