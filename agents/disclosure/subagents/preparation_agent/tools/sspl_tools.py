"""SSPL management tools for preparation agent.

Implements G6: Settlement Service Provider List management.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List
from langchain_core.tools import tool

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

from packages.shared.sspl_updater import manage_sspl, apply_sspl_template, delete_unwanted_services

logger = logging.getLogger(__name__)


@tool
def manage_settlement_service_provider_list(loan_id: str, dry_run: bool = False) -> dict:
    """Manage Settlement Service Provider List (G6 - CRITICAL).
    
    Per GAPS.md G6 and SOP Video Notes Lines 198-201:
    - Apply SSPL template if blank
    - Delete unwanted services: Pest Inspection, Home Inspection, Engineering, Land Survey
    - Copy title fees from LE Page 2 Section C to SSPL
    
    Note: Template detection and service list field IDs are UNKNOWN - requires manual verification.
    
    Args:
        loan_id: Encompass loan GUID
        dry_run: If True, simulate operations without making changes
        
    Returns:
        Dictionary with SSPL management results
    """
    logger.info(f"[G6] Managing SSPL for loan {loan_id[:8]}...")
    
    result = manage_sspl(loan_id, dry_run)
    
    if result.get("requires_manual_verification"):
        logger.warning("[G6] Manual verification required for SSPL operations")
    
    return result


@tool
def apply_sspl_template_tool(loan_id: str) -> dict:
    """Apply SSPL template to loan (G6).
    
    Per GAPS.md G6:
    - Check if SSPL is blank
    - Apply template if needed
    
    Note: Template detection field ID UNKNOWN.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with template application results
    """
    logger.info(f"[G6] Applying SSPL template for loan {loan_id[:8]}...")
    
    return apply_sspl_template(loan_id)


@tool
def delete_sspl_services(loan_id: str, services: List[str] = None) -> dict:
    """Delete unwanted services from SSPL (G6).
    
    Per GAPS.md G6:
    - Delete specified services from SSPL
    - Default: Pest Inspection, Home Inspection, Engineering, Land Survey
    
    Note: Service list field IDs UNKNOWN.
    
    Args:
        loan_id: Encompass loan GUID
        services: List of services to delete (optional)
        
    Returns:
        Dictionary with deletion results
    """
    logger.info(f"[G6] Deleting SSPL services for loan {loan_id[:8]}...")
    
    return delete_unwanted_services(loan_id, services)


# Export tools
sspl_tools = [
    manage_settlement_service_provider_list,
    apply_sspl_template_tool,
    delete_sspl_services,
]

