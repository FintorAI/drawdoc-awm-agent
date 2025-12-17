"""Transcript Forms tools for Preparation Agent (G4 - CRITICAL).

Implements tools for populating 4506-C and 8821 transcript forms
using Encompass Developer Connect API.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict
from langchain_core.tools import tool

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

from packages.shared.encompass_client import get_encompass_client
from packages.shared.transcript_forms import (
    populate_transcript_forms,
    get_transcript_templates,
    apply_transcript_template,
)

logger = logging.getLogger(__name__)


@tool
def populate_transcript_forms_tool(
    loan_id: str,
    application_id: str = "1",
    dry_run: bool = False
) -> dict:
    """Populate 4506-C and 8821 transcript forms via API (G4 - CRITICAL).
    
    Per GAPS.md and SOP Video Notes Lines 158-179:
    - 4506-C: Tax transcript request with IVES participant (Xactus)
    - 8821: Halcyon consent form
    - Tax years: 12/31/2024, 12/31/2023, 12/31/2022
    - Section 5a: Xactus IVES info (auto-populated)
    - Section 5d: All Western Mortgage info (auto-populated)
    
    Uses Encompass API template approach (recommended).
    
    Args:
        loan_id: Encompass loan GUID
        application_id: Application ID (default "1" for primary borrower)
        dry_run: If True, log but don't actually apply templates
        
    Returns:
        Dictionary with operation results for both forms
    """
    logger.info(f"[G4] Populating transcript forms for loan {loan_id[:8]}...")
    
    if dry_run:
        logger.info("[G4] DRY RUN mode - templates will not be applied")
    
    try:
        logger.warning("[G4] Transcript forms tool requires legacy EncompassConnect client")
        logger.warning("[G4] This tool is not yet compatible with disclosure agent v2")
        
        return {
            "gap_id": "G4",
            "gap_name": "Transcript Forms (4506-C, 8821)",
            "status": "not_implemented",
            "success": False,
            "error": "Transcript forms not yet supported in disclosure v2 - requires manual processing",
            "requires_manual_processing": True,
            "message": "LO must manually populate 4506-C and 8821 forms via Encompass UI"
        }
        
    except Exception as e:
        logger.error(f"[G4] Error in transcript forms tool: {e}")
        return {
            "gap_id": "G4",
            "gap_name": "Transcript Forms (4506-C, 8821)",
            "status": "error",
            "success": False,
            "error": str(e),
        }


@tool
def list_transcript_templates_tool() -> dict:
    """List available transcript templates from Encompass Settings.
    
    Useful for discovering template paths before applying them.
    
    Returns:
        Dictionary with list of available templates
    """
    logger.info("[G4] Listing available transcript templates...")
    
    try:
        logger.warning("[G4] Transcript templates listing not yet supported in disclosure v2")
        
        return {
            "gap_id": "G4",
            "status": "not_implemented",
            "success": False,
            "error": "Transcript templates not yet supported - requires legacy client"
        }
        
    except Exception as e:
        logger.error(f"[G4] Error listing templates: {e}")
        return {
            "gap_id": "G4",
            "status": "error",
            "error": str(e),
        }


@tool
def apply_custom_transcript_template_tool(
    loan_id: str,
    template_path: str,
    dry_run: bool = False
) -> dict:
    """Apply a custom transcript template to a loan.
    
    Use this to apply a specific template path not covered by the main tool.
    
    Args:
        loan_id: Encompass loan GUID
        template_path: Full path to template (e.g., "Public\\Templates\\...")
        dry_run: If True, log but don't actually apply
        
    Returns:
        Dictionary with operation results
    """
    logger.info(f"[G4] Applying custom template '{template_path}' to loan {loan_id[:8]}...")
    
    try:
        logger.warning("[G4] Apply transcript template not yet supported in disclosure v2")
        
        return {
            "gap_id": "G4",
            "status": "not_implemented",
            "success": False,
            "error": "Template application not yet supported - requires legacy client",
            "requires_manual_processing": True
        }
        
    except Exception as e:
        logger.error(f"[G4] Error applying custom template: {e}")
        return {
            "gap_id": "G4",
            "status": "error",
            "success": False,
            "error": str(e),
        }


# Export all transcript tools
transcript_tools = [
    populate_transcript_forms_tool,
    list_transcript_templates_tool,
    apply_custom_transcript_template_tool,
]
