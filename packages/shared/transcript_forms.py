"""Transcript Forms API Integration (G4 - CRITICAL).

Implements Encompass Developer Connect API for Request for Transcript of Tax forms:
- 4506-C: Request for Transcript of Tax Return
- 4506-T: Request for Transcript of Tax Return (Legacy)
- 8821: Tax Information Authorization (Halcyon consent)

Uses V3 API endpoints for template-based population (recommended approach).

API Documentation:
- GET /v3/settings/templates/transcriptRequests - List templates
- GET /v3/settings/templates/transcriptRequests/{templateId} - Get template details
- PATCH /v3/loans/{loanId} (with templateType=transcriptRequest) - Apply template
- PATCH /v3/loans/{loanId}/applications/{applicationId}/transcriptRequests - Manage records
"""

import os
import logging
from typing import Dict, List, Optional
from packages.shared.encompass_client import get_encompass_client

logger = logging.getLogger(__name__)


# =============================================================================
# API ENDPOINTS
# =============================================================================

TRANSCRIPT_API_ENDPOINTS = {
    "list_templates": "/v3/settings/templates/transcriptRequests",
    "get_template": "/v3/settings/templates/transcriptRequests/{templateId}",
    "manage_transcripts": "/v3/loans/{loanId}/applications/{applicationId}/transcriptRequests",
    "apply_template": "/v3/loans/{loanId}",  # with query params
}


# =============================================================================
# TEMPLATE CONFIGURATION
# =============================================================================

# Template Query Params for V3 Update Loan
TEMPLATE_PARAMS = {
    "templateType": "transcriptRequest",
    "templatePath": "{templatePath}",  # Path to transcript template in Encompass Settings
}

# Pre-configured IVES Participant Info (Section 5a)
TRANSCRIPT_5A_INFO = {
    "ives_participant_name": "Xactus, LLC",
    "ives_participant_id": "0000304771",
    "ives_participant_phone": "888-212-4200",
    "ives_participant_address": "370 Reed Road Suite 100",
    "ives_participant_city_state_zip": "Broomall, PA 19008",
}

# Pre-configured Third Party Designee Info (Section 5d / AWM Info)
TRANSCRIPT_5D_INFO = {
    "third_party_name": "All Western Mortgage, Inc.",
    "third_party_phone": "702-369-0905",
    "third_party_address": "8345 W. Sunset Road #380",
    "third_party_city_state_zip": "Las Vegas, NV 89113",
}

# Tax Years to Request
TAX_YEARS = ["12/31/2024", "12/31/2023", "12/31/2022"]

# Tax Form Types
TAX_FORMS = {
    "4506-C": "Request for Transcript of Tax Return",
    "4506-T": "Request for Transcript of Tax Return (Legacy)",
    "8821": "Tax Information Authorization (Halcyon consent)",
}

# Direct field IDs (fallback if needed)
IRS_FIELD_IDS = {
    "print_version": "IRS4506.X92",
    "use_4506c": "IRS4506.X67",
    "send_return_first_name": "IRS4506.X8",
}


# =============================================================================
# TEMPLATE OPERATIONS
# =============================================================================

def get_transcript_templates(client) -> List[Dict]:
    """Fetch available Transcript of Tax templates from Encompass Settings.
    
    Args:
        client: EncompassClient instance
        
    Returns:
        List of template dictionaries with id, name, path, etc.
    """
    logger.info("[Transcript] Fetching available templates...")
    
    try:
        endpoint = TRANSCRIPT_API_ENDPOINTS["list_templates"]
        response = client._make_request("GET", endpoint)
        
        templates = response if isinstance(response, list) else []
        logger.info(f"[Transcript] Found {len(templates)} templates")
        
        return templates
        
    except Exception as e:
        logger.error(f"[Transcript] Error fetching templates: {e}")
        return []


def get_template_settings(client, template_id: str) -> Dict:
    """Get configured settings for a specific template (IVES info, tax years, etc.).
    
    Args:
        client: EncompassClient instance
        template_id: Template ID from Encompass Settings
        
    Returns:
        Dictionary with template settings
    """
    logger.info(f"[Transcript] Fetching template settings for ID: {template_id}")
    
    try:
        endpoint = TRANSCRIPT_API_ENDPOINTS["get_template"].format(templateId=template_id)
        response = client._make_request("GET", endpoint)
        
        logger.info(f"[Transcript] Retrieved template settings")
        return response
        
    except Exception as e:
        logger.error(f"[Transcript] Error fetching template settings: {e}")
        return {}


def apply_transcript_template(
    client, 
    loan_id: str, 
    template_path: str,
    dry_run: bool = False
) -> Dict:
    """Apply transcript template to loan using V3 Update Loan API.
    
    This is the RECOMMENDED approach - applies entire template in one call.
    Auto-populates Section 5a (IVES), Section 5d (Third Party), and tax years.
    
    Args:
        client: EncompassClient instance
        loan_id: Encompass loan GUID
        template_path: Path to template in Encompass (e.g., "Public\\Templates\\4506-C")
        dry_run: If True, log but don't actually apply
        
    Returns:
        Dictionary with operation results
    """
    logger.info(f"[Transcript] Applying template '{template_path}' to loan {loan_id[:8]}...")
    
    if dry_run:
        logger.info(f"[Transcript] DRY RUN - Would apply template: {template_path}")
        return {
            "success": True,
            "dry_run": True,
            "template_path": template_path,
            "message": "Template would be applied (dry run)",
        }
    
    try:
        endpoint = TRANSCRIPT_API_ENDPOINTS["apply_template"].format(loanId=loan_id)
        params = {
            "templateType": "transcriptRequest",
            "templatePath": template_path
        }
        
        response = client._make_request("PATCH", endpoint, params=params)
        
        logger.info(f"[Transcript] Template applied successfully")
        
        return {
            "success": True,
            "template_path": template_path,
            "response": response,
        }
        
    except Exception as e:
        logger.error(f"[Transcript] Error applying template: {e}")
        return {
            "success": False,
            "error": str(e),
            "template_path": template_path,
        }


# =============================================================================
# RECORD MANAGEMENT (Fine-grained control)
# =============================================================================

def manage_transcript_records(
    client,
    loan_id: str,
    application_id: str,
    action: str,  # add, update, delete, reorder, replace
    records: List[Dict],
    dry_run: bool = False
) -> Dict:
    """Add/Update/Delete/Reorder transcript request records.
    
    Use this for fine-grained control over individual transcript records.
    For most cases, use apply_transcript_template() instead.
    
    Args:
        client: EncompassClient instance
        loan_id: Encompass loan GUID
        application_id: Application ID (usually "1" for primary borrower)
        action: One of "add", "update", "delete", "reorder", "replace"
        records: List of transcript record dictionaries
        dry_run: If True, log but don't actually modify
        
    Returns:
        Dictionary with operation results
    """
    logger.info(f"[Transcript] Managing records - action: {action}, count: {len(records)}")
    
    if dry_run:
        logger.info(f"[Transcript] DRY RUN - Would {action} {len(records)} records")
        return {
            "success": True,
            "dry_run": True,
            "action": action,
            "records_count": len(records),
        }
    
    try:
        endpoint = TRANSCRIPT_API_ENDPOINTS["manage_transcripts"].format(
            loanId=loan_id,
            applicationId=application_id
        )
        params = {"action": action}
        
        response = client._make_request("PATCH", endpoint, params=params, json_data=records)
        
        logger.info(f"[Transcript] Records {action} successfully")
        
        return {
            "success": True,
            "action": action,
            "records_count": len(records),
            "response": response,
        }
        
    except Exception as e:
        logger.error(f"[Transcript] Error managing records: {e}")
        return {
            "success": False,
            "error": str(e),
            "action": action,
        }


# =============================================================================
# HIGH-LEVEL FUNCTIONS (SOP-Specific)
# =============================================================================

def populate_transcript_forms(
    client,
    loan_id: str,
    application_id: str = "1",
    borrower_type: str = "Borrower",
    dry_run: bool = False
) -> Dict:
    """Populate 4506-C and 8821 forms for disclosure.
    
    Per SOP Video Notes Lines 158-179:
    - 4506-C: Tax transcript request with IVES participant (Xactus)
    - 8821: Halcyon consent form
    - Tax years: 12/31/2024, 12/31/2023, 12/31/2022
    
    Uses template-based approach (recommended).
    
    Args:
        client: EncompassClient instance
        loan_id: Encompass loan GUID
        application_id: Application ID (usually "1")
        borrower_type: "Borrower" or "CoBorrower"
        dry_run: If True, log but don't actually apply
        
    Returns:
        Dictionary with operation results for both forms
    """
    logger.info(f"[Transcript] Populating transcript forms for loan {loan_id[:8]}...")
    logger.info(f"[Transcript] Borrower type: {borrower_type}, Application: {application_id}")
    
    results = {
        "4506c": None,
        "8821": None,
        "success": False,
        "forms_populated": [],
        "dry_run": dry_run,
    }
    
    # Step 1: Apply 4506-C template
    # This auto-populates 5a (Xactus) and 5d (AWM) info
    logger.info("[Transcript] Applying 4506-C template...")
    
    template_4506c = "Public\\Templates\\4506-C Request for Transcript"
    results["4506c"] = apply_transcript_template(
        client,
        loan_id,
        template_4506c,
        dry_run=dry_run
    )
    
    if results["4506c"]["success"]:
        results["forms_populated"].append("4506-C")
        logger.info("[Transcript] ✓ 4506-C template applied")
    else:
        logger.error(f"[Transcript] ✗ 4506-C failed: {results['4506c'].get('error')}")
    
    # Step 2: Apply 8821 Halcyon consent template
    logger.info("[Transcript] Applying 8821 template...")
    
    template_8821 = "Public\\Templates\\8821 – Halcyon consent form"
    results["8821"] = apply_transcript_template(
        client,
        loan_id,
        template_8821,
        dry_run=dry_run
    )
    
    if results["8821"]["success"]:
        results["forms_populated"].append("8821")
        logger.info("[Transcript] ✓ 8821 template applied")
    else:
        logger.error(f"[Transcript] ✗ 8821 failed: {results['8821'].get('error')}")
    
    # Overall success if at least one form populated
    results["success"] = len(results["forms_populated"]) > 0
    
    # Add metadata
    results["tax_years"] = TAX_YEARS
    results["ives_participant"] = f"{TRANSCRIPT_5A_INFO['ives_participant_name']} ({TRANSCRIPT_5A_INFO['ives_participant_id']})"
    results["third_party_designee"] = TRANSCRIPT_5D_INFO["third_party_name"]
    
    if results["success"]:
        logger.info(f"[Transcript] ✓ Transcript forms populated: {results['forms_populated']}")
    else:
        logger.error("[Transcript] ✗ Failed to populate transcript forms")
    
    return results


def create_manual_transcript_record(
    loan_id: str,
    tax_form: str = "1040",
    transcript_type: str = "ReturnTranscript",
    tax_years: Optional[List[str]] = None
) -> Dict:
    """Create a manual transcript record dictionary.
    
    Use this to build a record for manage_transcript_records().
    
    Args:
        loan_id: Encompass loan GUID
        tax_form: Tax form number (1040, W2, etc.)
        transcript_type: Type of transcript (ReturnTranscript, etc.)
        tax_years: List of tax years (defaults to TAX_YEARS)
        
    Returns:
        Dictionary formatted for transcript record API
    """
    if tax_years is None:
        tax_years = TAX_YEARS
    
    return {
        "taxFormNumber": tax_form,
        "transcriptType": transcript_type,
        "taxYears": tax_years,
        "ivesParticipant": {
            "name": TRANSCRIPT_5A_INFO["ives_participant_name"],
            "participantId": TRANSCRIPT_5A_INFO["ives_participant_id"],
            "phone": TRANSCRIPT_5A_INFO["ives_participant_phone"],
            "address": TRANSCRIPT_5A_INFO["ives_participant_address"],
            "cityStateZip": TRANSCRIPT_5A_INFO["ives_participant_city_state_zip"],
        },
        "thirdPartyDesignee": {
            "name": TRANSCRIPT_5D_INFO["third_party_name"],
            "phone": TRANSCRIPT_5D_INFO["third_party_phone"],
            "address": TRANSCRIPT_5D_INFO["third_party_address"],
            "cityStateZip": TRANSCRIPT_5D_INFO["third_party_city_state_zip"],
        }
    }
