"""
Phase 2: Contacts & Vendors

Updates contact and vendor-related fields:
- Title company information
- Escrow company information
- Lenders and servicers
- Insurance providers
- Other business contacts
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.drawdocs.tools.primitives import read_fields, write_fields, log_issue

logger = logging.getLogger(__name__)


# Field mappings for Phase 2 - File Contacts (SOP Step 9)
CONTACTS_VENDOR_FIELDS = {
    # Lender Information (Fixed values from SOP)
    "L1": {"name": "Lender Name", "source_docs": ["Fixed"]},
    "L2": {"name": "Lender Address", "source_docs": ["Fixed"]},
    "L3": {"name": "Lender City", "source_docs": ["Fixed"]},
    "L4": {"name": "Lender State", "source_docs": ["Fixed"]},
    "L5": {"name": "Lender Zip", "source_docs": ["Fixed"]},
    "L6": {"name": "Lender NMLS", "source_docs": ["Fixed"]},
    "L7": {"name": "Lender License ID", "source_docs": ["Fixed"]},
    "L8": {"name": "Lender Phone", "source_docs": ["Fixed"]},
    "L9": {"name": "Lender Fax", "source_docs": ["Fixed"]},
    
    # Title Company (From Title Report)
    "VEND.X100": {"name": "Title Company Name", "source_docs": ["Title Report"]},
    "VEND.X101": {"name": "Title Company Address", "source_docs": ["Title Report"]},
    "VEND.X102": {"name": "Title Company City", "source_docs": ["Title Report"]},
    "VEND.X103": {"name": "Title Company State", "source_docs": ["Title Report"]},
    "VEND.X104": {"name": "Title Company Zip", "source_docs": ["Title Report"]},
    "VEND.X105": {"name": "Title Officer Name", "source_docs": ["Title Report"]},
    "VEND.X106": {"name": "Title Officer Email", "source_docs": ["Title Report"]},
    "VEND.X107": {"name": "Title Officer Phone", "source_docs": ["Title Report"]},
    
    # Escrow Company (From Title Report / Wire Instructions)
    "186": {"name": "Escrow Case Number", "source_docs": ["Title Report"]},  # From CSV
    "VEND.X110": {"name": "Escrow Company Address", "source_docs": ["Title Report"]},
    "VEND.X111": {"name": "Escrow Company City", "source_docs": ["Title Report"]},
    "VEND.X112": {"name": "Escrow Company State", "source_docs": ["Title Report"]},
    "VEND.X113": {"name": "Escrow Company Zip", "source_docs": ["Title Report"]},
    "VEND.X114": {"name": "Escrow Officer Name", "source_docs": ["Title Report"]},
    "VEND.X115": {"name": "Escrow Officer Email", "source_docs": ["Title Report"]},
    "VEND.X116": {"name": "Escrow Officer Phone", "source_docs": ["Title Report"]},
    "VEND.X117": {"name": "Escrow Bank ABA", "source_docs": ["Wire Instructions"]},
    "VEND.X118": {"name": "Escrow Bank Account", "source_docs": ["Wire Instructions"]},
    
    # Hazard Insurance Company (From Evidence of Insurance)
    "L252": {"name": "Hazard Insurance Company Name", "source_docs": ["Evidence of Insurance"]},  # From CSV
    "VEND.X120": {"name": "Hazard Insurance Company Address", "source_docs": ["Evidence of Insurance"]},
    "VEND.X163": {"name": "Hazard Insurance Agent Name", "source_docs": ["Evidence of Insurance"]},  # From CSV
    "VEND.X164": {"name": "Hazard Insurance Agent Email", "source_docs": ["Evidence of Insurance"]},  # From CSV
    "VEND.X121": {"name": "Hazard Insurance Agent Phone", "source_docs": ["Evidence of Insurance"]},
    "VEND.X122": {"name": "Hazard Insurance Policy Number", "source_docs": ["Evidence of Insurance"]},
    
    # Settlement Agent (From CSV)
    "CD5.X55": {"name": "Settlement Agent Name", "source_docs": ["File Contacts"]},  # From CSV
}


def process_contacts_phase(
    loan_id: str,
    doc_context: Dict[str, Any],
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Process Phase 2: Contacts & Vendors fields.
    
    Args:
        loan_id: Encompass loan GUID
        doc_context: Prep Agent output with extracted field values
        dry_run: If True, don't actually write to Encompass
        
    Returns:
        Dictionary with phase results
    """
    logger.info("[PHASE 2] Contacts & Vendors - Starting")
    
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
            logger.warning("[PHASE 2] No field mappings found in doc_context")
            result["status"] = "failed"
            result["issues"].append({
                "type": "warning",
                "message": "No field mappings found in doc_context"
            })
            return result
        
        # Get list of Phase 2 field IDs that we have values for
        phase2_field_ids = [
            field_id for field_id in CONTACTS_VENDOR_FIELDS.keys()
            if field_id in field_mappings
        ]
        
        if not phase2_field_ids:
            logger.warning("[PHASE 2] No Phase 2 fields found in extracted data")
            result["status"] = "success"  # Not an error, just nothing to do
            return result
        
        logger.info(f"[PHASE 2] Processing {len(phase2_field_ids)} contact/vendor fields")
        
        # Read current Encompass values
        logger.info("[PHASE 2] Reading current Encompass field values...")
        current_values = read_fields(loan_id, phase2_field_ids)
        
        # Compare and update fields
        for field_id in phase2_field_ids:
            result["fields_processed"] += 1
            
            field_info = CONTACTS_VENDOR_FIELDS.get(field_id, {})
            field_name = field_info.get("name", field_id)
            # Extract actual value from mapping (may be dict with "value" key or simple value)
            raw_mapping = field_mappings[field_id]
            extracted_value = raw_mapping.get("value") if isinstance(raw_mapping, dict) and "value" in raw_mapping else raw_mapping
            current_value = current_values.get(field_id)
            
            logger.info(f"[PHASE 2] Processing {field_name} ({field_id})")
            logger.info(f"  Extracted: {extracted_value}")
            logger.info(f"  Current:   {current_value}")
            
            # Normalize values for comparison
            extracted_str = str(extracted_value).strip() if extracted_value is not None else ""
            current_str = str(current_value).strip() if current_value is not None else ""
            
            # Check if update is needed
            if extracted_str != current_str:
                logger.info(f"  → Update needed")
                
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
        
        logger.info(f"[PHASE 2] Complete - {result['fields_processed']} processed, "
                   f"{result['fields_updated']} updated, {result['issues_logged']} issues")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 2] Failed: {e}")
        result["status"] = "failed"
        result["issues_logged"] += 1
        result["issues"].append({
            "type": "error",
            "message": f"Phase 2 failed: {str(e)}"
        })
        return result

