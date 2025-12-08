"""SSPL (Settlement Service Provider List) Updater (G6 - CRITICAL).

Manages Settlement Service Provider List for disclosure.

Per SOP Video Notes Lines 198-201:
- Apply SSPL template if blank
- Delete unwanted services (Pest, Home Inspection, Engineering, Land Survey)
- Copy title fees from LE Page 2 Section C to SSPL

Note: Template detection and service list field IDs are UNKNOWN - requires manual verification.
"""

import logging
from typing import Dict, List, Optional
from packages.shared.encompass_client import get_encompass_client

logger = logging.getLogger(__name__)


# Services to delete from SSPL
UNWANTED_SERVICES = [
    "Pest Inspection",
    "Home Inspection",
    "Engineering",
    "Land Survey"
]


def apply_sspl_template(loan_id: str) -> Dict:
    """Apply Settlement Service Provider template (G6).
    
    Template detection field UNKNOWN - logs warning for manual verification.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with operation results
    """
    logger.info(f"[G6] Applying SSPL template for loan {loan_id[:8]}...")
    logger.warning("[G6] SSPL template detection field ID UNKNOWN - requires manual verification in Encompass")
    
    # TODO: Implement template application when field IDs are mapped
    # Potential approach:
    # 1. Check if SSPL is blank (field ID unknown)
    # 2. Apply template via Encompass API or template endpoint
    # 3. Verify template applied successfully
    
    return {
        "gap_id": "G6",
        "gap_name": "SSPL Template Application",
        "status": "manual_verification_required",
        "message": "Please manually check if SSPL is blank and apply template in Encompass",
        "warnings": [
            "SSPL template detection field ID requires manual verification",
            "Template application method not implemented - manual action required"
        ],
        "requires_manual_verification": True,
    }


def delete_unwanted_services(loan_id: str, services: Optional[List[str]] = None) -> Dict:
    """Delete Pest Inspection, Home Inspection, Engineering, Land Survey from SSPL.
    
    Service list field UNKNOWN - logs warning for manual verification.
    
    Args:
        loan_id: Encompass loan GUID
        services: List of service names to delete (defaults to UNWANTED_SERVICES)
        
    Returns:
        Dictionary with operation results
    """
    if services is None:
        services = UNWANTED_SERVICES
    
    logger.info(f"[G6] Deleting unwanted services from SSPL for loan {loan_id[:8]}...")
    logger.info(f"[G6] Services to delete: {services}")
    logger.warning("[G6] SSPL service list field IDs require manual verification in Encompass")
    
    # TODO: Implement service deletion when field IDs are mapped
    # Potential approach:
    # 1. Get SSPL service list (field ID unknown)
    # 2. Filter out unwanted services by name
    # 3. Update SSPL with filtered list
    # OR use Encompass API to delete specific service records
    
    return {
        "gap_id": "G6",
        "gap_name": "SSPL Service Deletion",
        "status": "manual_verification_required",
        "services_to_delete": services,
        "message": f"Please manually delete these services from SSPL: {', '.join(services)}",
        "warnings": [
            "SSPL service list field IDs require manual verification",
            "Service deletion method not implemented - manual action required"
        ],
        "requires_manual_verification": True,
    }


def copy_title_fees_to_sspl(loan_id: str) -> Dict:
    """Copy title fees from LE Page 2 Section C to SSPL.
    
    Per SOP: Copy title-related fees to Settlement Service Provider List.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with operation results
    """
    logger.info(f"[G6] Copying title fees to SSPL for loan {loan_id[:8]}...")
    logger.warning("[G6] Title fee field IDs and SSPL field IDs require manual verification")
    
    # TODO: Implement when field IDs are mapped
    # Fields needed:
    # - LE Page 2 Section C title fees
    # - SSPL corresponding fields
    
    return {
        "gap_id": "G6",
        "gap_name": "Copy Title Fees to SSPL",
        "status": "manual_verification_required",
        "message": "Please manually copy title fees from LE Page 2 Section C to SSPL",
        "warnings": [
            "Title fee field IDs require manual verification",
            "Fee copying method not implemented - manual action required"
        ],
        "requires_manual_verification": True,
    }


def manage_sspl(loan_id: str, dry_run: bool = False) -> Dict:
    """Complete SSPL management workflow (G6).
    
    Performs all SSPL operations:
    1. Apply template if blank
    2. Delete unwanted services
    3. Copy title fees
    
    Args:
        loan_id: Encompass loan GUID
        dry_run: If True, simulate operations without making changes
        
    Returns:
        Dictionary with complete operation results
    """
    logger.info(f"[G6] Managing SSPL for loan {loan_id[:8]} (dry_run={dry_run})...")
    
    results = {
        "gap_id": "G6",
        "gap_name": "SSPL Management",
        "dry_run": dry_run,
        "operations": [],
    }
    
    # Step 1: Apply template if needed
    template_result = apply_sspl_template(loan_id)
    results["operations"].append({
        "step": "apply_template",
        "result": template_result
    })
    
    # Step 2: Delete unwanted services
    delete_result = delete_unwanted_services(loan_id)
    results["operations"].append({
        "step": "delete_services",
        "result": delete_result
    })
    
    # Step 3: Copy title fees
    copy_result = copy_title_fees_to_sspl(loan_id)
    results["operations"].append({
        "step": "copy_title_fees",
        "result": copy_result
    })
    
    # Collect all warnings
    all_warnings = []
    for op in results["operations"]:
        all_warnings.extend(op["result"].get("warnings", []))
    
    results["warnings"] = list(set(all_warnings))  # Deduplicate
    results["requires_manual_verification"] = True
    results["status"] = "partial_check"
    results["message"] = "SSPL management requires manual verification - see operations for details"
    
    logger.warning("[G6] SSPL management complete - manual verification required for all operations")
    
    return results
