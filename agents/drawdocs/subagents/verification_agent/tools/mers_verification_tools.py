"""
MERS MIN Number Generation and Verification Tools.

Implements SOP Step 4:
- Generate MERS MIN number (click MERS MIN box in Encompass)
- Verify MIN is unique (check MERS website for duplicates)
- Search by SSN for borrower & co-borrower
- Upload MIN search & SSN search results to Encompass

Per SOP Step 4 - Borrower Summary - Origination.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.drawdocs.tools.primitives import read_fields, get_loan_context

logger = logging.getLogger(__name__)


# =============================================================================
# FIELD MAPPINGS
# =============================================================================

class MERSFields:
    """Encompass field IDs for MERS MIN validation."""
    
    # MERS MIN field
    MERS_MIN = "1051"  # Mers Min # (from master_field_data.csv)
    
    # SSN fields for verification
    BORROWER_SSN = "65"  # Borrower SSN
    COBORROWER_SSN = "97"  # Co-Borrower SSN


# =============================================================================
# MERS WEBSITE CONSTANTS
# =============================================================================

MERS_WEBSITE_URL = "https://www.mersonline.org/"
MERS_SEARCH_URL = "https://www.mersonline.org/minsearch"  # May need to verify actual URL


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_ssn(ssn: str) -> str:
    """Format SSN for display (mask sensitive parts)."""
    if not ssn or len(str(ssn)) < 4:
        return "***-**-****"
    ssn_str = str(ssn).replace("-", "").replace(" ", "")
    if len(ssn_str) >= 4:
        return f"***-**-{ssn_str[-4:]}"
    return "***-**-****"


# =============================================================================
# MERS MIN GENERATION
# =============================================================================

def generate_mers_min(loan_id: str) -> Dict[str, Any]:
    """
    Generate MERS MIN number by clicking MERS MIN box in Encompass.
    
    Per SOP Step 4:
    - Click on "MERS MIN" box to generate identical MIN Number for the loan
    
    Note: This requires Encompass API to trigger the MIN generation.
    The actual implementation depends on Encompass API capabilities.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with generation result
    """
    logger.info(f"[MERS MIN] Starting MIN generation for loan {loan_id}")
    
    result = {
        "status": "in_progress",
        "loan_id": loan_id,
        "min_generated": False,
        "min_number": None,
        "error": None,
        "details": []
    }
    
    try:
        # Read current MIN value
        logger.info("[MERS MIN] Reading current MERS MIN field...")
        fields = read_fields(loan_id, [MERSFields.MERS_MIN])
        
        current_min = fields.get(MERSFields.MERS_MIN, "")
        result["details"].append(f"Current MIN value: {current_min or 'Empty'}")
        
        if current_min and str(current_min).strip():
            # MIN already exists
            result["status"] = "min_exists"
            result["min_generated"] = True
            result["min_number"] = str(current_min).strip()
            result["details"].append(f"MIN already exists: {result['min_number']}")
            logger.info(f"[MERS MIN] ✅ MIN already exists: {result['min_number']}")
        else:
            # MIN needs to be generated
            # TODO: Implement Encompass API call to click MERS MIN box
            # This may require:
            # 1. Field writer API to trigger MIN generation
            # 2. Or a specific Encompass API endpoint for MIN generation
            # 3. Or manual instruction to user
            
            result["status"] = "needs_generation"
            result["min_generated"] = False
            result["details"].append("MIN field is empty - needs to be generated")
            result["action_required"] = "Click 'MERS MIN' box in Encompass >> Forms >> Borrower Summary - Origination to generate MIN number"
            
            logger.warning("[MERS MIN] ⚠️  MIN field is empty - manual generation required")
            logger.warning("[MERS MIN] Action: Click 'MERS MIN' box in Encompass to generate")
        
        return result
        
    except Exception as e:
        logger.error(f"[MERS MIN] Error during generation: {e}", exc_info=True)
        result["status"] = "error"
        result["error"] = str(e)
        result["details"].append(f"Error: {str(e)}")
        return result


# =============================================================================
# MERS MIN UNIQUENESS VERIFICATION
# =============================================================================

def verify_min_uniqueness(min_number: str, borrower_ssn: str, coborrower_ssn: Optional[str] = None) -> Dict[str, Any]:
    """
    Verify MERS MIN number is unique on MERS website.
    
    Per SOP Step 4:
    - Verify if the generated "MIN #" is unique and not a duplicate on MERS site
    
    Args:
        min_number: MERS MIN number to verify
        borrower_ssn: Borrower SSN (for additional verification)
        coborrower_ssn: Co-Borrower SSN (optional, for additional verification)
        
    Returns:
        Dictionary with verification result
    """
    logger.info(f"[MERS MIN] Verifying MIN uniqueness: {min_number}")
    
    result = {
        "status": "in_progress",
        "min_number": min_number,
        "is_unique": False,
        "is_duplicate": False,
        "verification_method": "website_search",
        "search_results": {},
        "warnings": [],
        "details": []
    }
    
    try:
        if not min_number or not min_number.strip():
            result["status"] = "error"
            result["error"] = "MIN number is empty"
            result["details"].append("MIN number is required for verification")
            return result
        
        # TODO: Implement MERS website search
        # Options:
        # 1. Web scraping MERS website (https://www.mersonline.org/)
        # 2. MERS API (if available)
        # 3. Selenium/Playwright automation
        
        # For now, return placeholder that indicates manual verification needed
        result["status"] = "manual_verification_required"
        result["verification_method"] = "manual"
        result["details"].append(f"MIN number: {min_number}")
        result["details"].append("Manual verification required on MERS website")
        result["action_required"] = f"Visit {MERS_WEBSITE_URL} and search for MIN: {min_number}"
        result["search_url"] = MERS_WEBSITE_URL
        
        logger.warning("[MERS MIN] ⚠️  Manual verification required - MERS website search not yet automated")
        logger.warning(f"[MERS MIN] Action: Visit {MERS_WEBSITE_URL} and search for MIN: {min_number}")
        
        return result
        
    except Exception as e:
        logger.error(f"[MERS MIN] Error during uniqueness verification: {e}", exc_info=True)
        result["status"] = "error"
        result["error"] = str(e)
        result["details"].append(f"Error: {str(e)}")
        return result


# =============================================================================
# SSN SEARCH ON MERS WEBSITE
# =============================================================================

def search_ssn_on_mers(ssn: str, borrower_type: str = "Borrower") -> Dict[str, Any]:
    """
    Search by SSN on MERS website to verify uniqueness.
    
    Per SOP Step 4:
    - Search by SSN Number of borrower & co-borrower both
    - Verify no duplicate MINs exist for the SSN
    
    Args:
        ssn: SSN to search (borrower or co-borrower)
        borrower_type: "Borrower" or "Co-Borrower"
        
    Returns:
        Dictionary with search result
    """
    logger.info(f"[MERS SSN] Searching MERS website for {borrower_type} SSN: {format_ssn(ssn)}")
    
    result = {
        "status": "in_progress",
        "ssn": format_ssn(ssn),  # Masked for logging
        "borrower_type": borrower_type,
        "matches_found": False,
        "match_count": 0,
        "matches": [],
        "verification_method": "website_search",
        "details": []
    }
    
    try:
        if not ssn or not str(ssn).strip():
            result["status"] = "error"
            result["error"] = f"{borrower_type} SSN is empty"
            result["details"].append(f"{borrower_type} SSN is required for verification")
            return result
        
        # TODO: Implement MERS website SSN search
        # Options:
        # 1. Web scraping MERS website
        # 2. MERS API (if available)
        # 3. Selenium/Playwright automation
        
        # For now, return placeholder that indicates manual verification needed
        result["status"] = "manual_verification_required"
        result["verification_method"] = "manual"
        result["details"].append(f"{borrower_type} SSN: {format_ssn(ssn)}")
        result["details"].append("Manual verification required on MERS website")
        result["action_required"] = f"Visit {MERS_WEBSITE_URL} and search by SSN for {borrower_type}"
        result["search_url"] = MERS_WEBSITE_URL
        
        logger.warning(f"[MERS SSN] ⚠️  Manual verification required - MERS website SSN search not yet automated")
        logger.warning(f"[MERS SSN] Action: Visit {MERS_WEBSITE_URL} and search by SSN for {borrower_type}")
        
        return result
        
    except Exception as e:
        logger.error(f"[MERS SSN] Error during SSN search: {e}", exc_info=True)
        result["status"] = "error"
        result["error"] = str(e)
        result["details"].append(f"Error: {str(e)}")
        return result


# =============================================================================
# COMPREHENSIVE MERS VERIFICATION
# =============================================================================

def validate_mers_min(loan_id: str) -> Dict[str, Any]:
    """
    Comprehensive MERS MIN validation.
    
    Per SOP Step 4:
    1. Generate MERS MIN number (if not exists)
    2. Verify MIN is unique on MERS website
    3. Search by SSN for borrower & co-borrower
    4. Generate verification report
    5. Upload to Encompass (manual step for now)
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with complete validation results
    """
    logger.info(f"[MERS VALIDATION] Starting comprehensive MERS validation for loan {loan_id}")
    
    result = {
        "status": "in_progress",
        "loan_id": loan_id,
        "min_generation": None,
        "min_uniqueness": None,
        "borrower_ssn_search": None,
        "coborrower_ssn_search": None,
        "all_checks_passed": False,
        "violations": [],
        "warnings": [],
        "details": []
    }
    
    try:
        # Get loan context for SSNs
        logger.info("[MERS VALIDATION] Reading loan context and SSN fields...")
        loan_context = get_loan_context(loan_id, include_milestones=False)
        
        # Read MERS MIN and SSN fields
        fields = read_fields(loan_id, [
            MERSFields.MERS_MIN,
            MERSFields.BORROWER_SSN,
            MERSFields.COBORROWER_SSN,
        ])
        
        borrower_ssn = fields.get(MERSFields.BORROWER_SSN, "")
        coborrower_ssn = fields.get(MERSFields.COBORROWER_SSN, "")
        min_number = fields.get(MERSFields.MERS_MIN, "")
        
        logger.info(f"[MERS VALIDATION] MIN: {min_number or 'Empty'}")
        logger.info(f"[MERS VALIDATION] Borrower SSN: {format_ssn(borrower_ssn)}")
        logger.info(f"[MERS VALIDATION] Co-Borrower SSN: {format_ssn(coborrower_ssn) if coborrower_ssn else 'N/A'}")
        
        # =====================================================================
        # STEP 1: Generate MERS MIN (if needed)
        # =====================================================================
        logger.info("\n[MERS VALIDATION] Step 1: Checking MIN generation...")
        min_generation = generate_mers_min(loan_id)
        result["min_generation"] = min_generation
        
        if min_generation["status"] == "needs_generation":
            result["violations"].append({
                "type": "PTF",
                "severity": "HIGH",
                "category": "MERS MIN Missing",
                "message": "MERS MIN number has not been generated",
                "action_required": "Click 'MERS MIN' box in Encompass >> Forms >> Borrower Summary - Origination",
                "fields_affected": [MERSFields.MERS_MIN],
                "sop_reference": "Step 4 - Borrower Summary - Origination"
            })
            logger.warning("[MERS VALIDATION] ⚠️  MIN not generated")
        else:
            min_number = min_generation.get("min_number") or min_number
            logger.info(f"[MERS VALIDATION] ✅ MIN exists: {min_number}")
        
        # =====================================================================
        # STEP 2: Verify MIN Uniqueness (if MIN exists)
        # =====================================================================
        if min_number and str(min_number).strip():
            logger.info("\n[MERS VALIDATION] Step 2: Verifying MIN uniqueness...")
            min_uniqueness = verify_min_uniqueness(
                min_number=min_number,
                borrower_ssn=borrower_ssn,
                coborrower_ssn=coborrower_ssn
            )
            result["min_uniqueness"] = min_uniqueness
            
            if min_uniqueness["status"] == "manual_verification_required":
                result["warnings"].append({
                    "type": "WARNING",
                    "severity": "MEDIUM",
                    "category": "MERS Verification",
                    "message": f"Manual verification required for MIN: {min_number}",
                    "action_required": f"Visit {MERS_WEBSITE_URL} and verify MIN is unique",
                    "search_url": MERS_WEBSITE_URL,
                    "min_number": min_number
                })
                logger.warning("[MERS VALIDATION] ⚠️  Manual MIN verification required")
        
        # =====================================================================
        # STEP 3: Search Borrower SSN on MERS
        # =====================================================================
        if borrower_ssn and str(borrower_ssn).strip():
            logger.info("\n[MERS VALIDATION] Step 3: Searching Borrower SSN on MERS...")
            borrower_ssn_search = search_ssn_on_mers(borrower_ssn, "Borrower")
            result["borrower_ssn_search"] = borrower_ssn_search
            
            if borrower_ssn_search["status"] == "manual_verification_required":
                result["warnings"].append({
                    "type": "WARNING",
                    "severity": "MEDIUM",
                    "category": "MERS SSN Verification",
                    "message": f"Manual SSN verification required for Borrower",
                    "action_required": f"Visit {MERS_WEBSITE_URL} and search by Borrower SSN",
                    "search_url": MERS_WEBSITE_URL,
                    "borrower_type": "Borrower"
                })
                logger.warning("[MERS VALIDATION] ⚠️  Manual Borrower SSN verification required")
        else:
            logger.warning("[MERS VALIDATION] ⚠️  Borrower SSN not found - skipping SSN search")
        
        # =====================================================================
        # STEP 4: Search Co-Borrower SSN on MERS (if exists)
        # =====================================================================
        if coborrower_ssn and str(coborrower_ssn).strip():
            logger.info("\n[MERS VALIDATION] Step 4: Searching Co-Borrower SSN on MERS...")
            coborrower_ssn_search = search_ssn_on_mers(coborrower_ssn, "Co-Borrower")
            result["coborrower_ssn_search"] = coborrower_ssn_search
            
            if coborrower_ssn_search["status"] == "manual_verification_required":
                result["warnings"].append({
                    "type": "WARNING",
                    "severity": "MEDIUM",
                    "category": "MERS SSN Verification",
                    "message": f"Manual SSN verification required for Co-Borrower",
                    "action_required": f"Visit {MERS_WEBSITE_URL} and search by Co-Borrower SSN",
                    "search_url": MERS_WEBSITE_URL,
                    "borrower_type": "Co-Borrower"
                })
                logger.warning("[MERS VALIDATION] ⚠️  Manual Co-Borrower SSN verification required")
        else:
            logger.info("[MERS VALIDATION] No Co-Borrower SSN - skipping")
        
        # =====================================================================
        # DETERMINE OVERALL STATUS
        # =====================================================================
        # All checks passed if:
        # 1. MIN exists (or was generated)
        # 2. No critical violations
        
        has_min = bool(min_number and str(min_number).strip())
        has_critical_violations = any(v.get("severity") == "HARD_STOP" for v in result["violations"])
        
        if has_min and not has_critical_violations:
            result["all_checks_passed"] = True
            result["status"] = "verification_required"  # Manual verification still needed
            logger.info("[MERS VALIDATION] ✅ MIN exists - manual verification required on MERS website")
        elif not has_min:
            result["status"] = "min_missing"
            logger.warning("[MERS VALIDATION] ❌ MIN missing - generation required")
        else:
            result["status"] = "violations_found"
            logger.warning(f"[MERS VALIDATION] ⚠️  Found {len(result['violations'])} violations")
        
        # Add summary details
        result["details"].append(f"MIN Number: {min_number or 'Not Generated'}")
        result["details"].append(f"Borrower SSN: {format_ssn(borrower_ssn) if borrower_ssn else 'Not Found'}")
        result["details"].append(f"Co-Borrower SSN: {format_ssn(coborrower_ssn) if coborrower_ssn else 'N/A'}")
        result["details"].append(f"Violations: {len(result['violations'])}")
        result["details"].append(f"Warnings: {len(result['warnings'])}")
        
        return result
        
    except Exception as e:
        logger.error(f"[MERS VALIDATION] Error during validation: {e}", exc_info=True)
        result["status"] = "error"
        result["details"].append(f"Validation error: {str(e)}")
        return result


# =============================================================================
# EXPORT TOOLS
# =============================================================================

__all__ = [
    "generate_mers_min",
    "verify_min_uniqueness",
    "search_ssn_on_mers",
    "validate_mers_min",
]



