"""Form Field Validator for Disclosure Agent.

Per Disclosure Desk SOP, validates key fields in:
- 1003 URLA Lender Form (all 4 parts)
- Borrower Summary Origination
- FACT Act Disclosure
- RegZ-LE fields
- Affiliated Business Arrangements
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .encompass_io import read_fields

logger = logging.getLogger(__name__)


# =============================================================================
# FORM FIELD DEFINITIONS (from SOP)
# =============================================================================

# 1003 URLA - Lender Form
URLA_LENDER_FIELDS = {
    "borrower_first_name": "4000",
    "borrower_last_name": "4002",
    "borrower_ssn": "65",
    "property_address": "11",
    "property_city": "12",
    "property_state": "14",
    "property_zip": "15",
    "loan_amount": "1109",
    "loan_purpose": "19",
    "occupancy_type": "1811",
    "property_type": "1041",
}

# 1003 URLA Part 1
URLA_PART1_FIELDS = {
    "borrower_current_address": "FR0104",
    "borrower_mailing_same_as_current": "FR0108",  # Should be marked "Same as Current"
}

# 1003 URLA Part 2
URLA_PART2_FIELDS = {
    "current_employment": "FE0102",
    "gross_monthly_income": "1389",
    "total_income": "1389",  # Same field
}

# 1003 URLA Part 4
URLA_PART4_FIELDS = {
    "lo_name": "317",
    "lo_nmls_id": "3238",
    "lo_company_nmls": "3330",
    "declarations_completed": "1087",  # Check if declarations are filled
}

# Borrower Summary Origination
BORROWER_SUMMARY_FIELDS = {
    "channel": "2626",
    "current_status": "1393",
    "application_date": "745",
    "lock_date": "761",  # If locked
}

# FACT Act Disclosure
FACT_ACT_FIELDS = {
    "credit_score_experian": "CUST02FV",  # May vary by instance
    "credit_score_transunion": "CUST03FV",
    "credit_score_equifax": "CUST04FV",
    "credit_report_date": "CUST05FV",
}

# RegZ-LE Required Fields
REGZ_LE_FIELDS = {
    "le_date_issued": "LE1.X1",
    "interest_rate": "3",
    "loan_term": "4",
    "monthly_pi": "5",
}

# Affiliated Business Arrangements
ABA_FIELDS = {
    "settlement_box_marked": "NEWHUD.X1",  # Settlement box
    "transaction_type_marked": "NEWHUD.X2",  # Purchase/Sale/Refinance
}

# Loan Originator Info (NMLS verification)
LO_INFO_FIELDS = {
    "lo_name": "317",
    "lo_nmls_id": "3238",
    "lo_company_name": "3331",
    "lo_company_nmls": "3330",
    "branch_nmls": "3322",
}


# =============================================================================
# FORM DEFINITIONS
# =============================================================================

REQUIRED_FORMS = {
    "1003_URLA_Lender": URLA_LENDER_FIELDS,
    "1003_URLA_Part1": URLA_PART1_FIELDS,
    "1003_URLA_Part2": URLA_PART2_FIELDS,
    "1003_URLA_Part4": URLA_PART4_FIELDS,
    "Borrower_Summary_Origination": BORROWER_SUMMARY_FIELDS,
    "FACT_Act_Disclosure": FACT_ACT_FIELDS,
    "RegZ_LE": REGZ_LE_FIELDS,
    "Affiliated_Business_Arrangements": ABA_FIELDS,
    "LO_Info": LO_INFO_FIELDS,
}

# Critical fields that MUST be present (subset of above)
CRITICAL_FIELDS = {
    "borrower_first_name": "4000",
    "borrower_last_name": "4002",
    "property_address": "11",
    "property_city": "12",
    "property_state": "14",
    "property_zip": "15",
    "loan_amount": "1109",
    "loan_purpose": "19",
    "application_date": "745",
    "lo_nmls_id": "3238",
}

# =============================================================================
# HARD STOP FIELDS - Per SOP: Missing these is a HARD STOP for disclosure
# =============================================================================

HARD_STOP_FIELDS = {
    "borrower_phone": "FE0117",   # Home Phone Number - HARD STOP if missing
    "borrower_email": "1240",     # Email Address - HARD STOP if missing
}

# Combined blocking fields (critical + hard stop)
BLOCKING_FIELDS = {**CRITICAL_FIELDS, **HARD_STOP_FIELDS}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class FormCheckResult:
    """Result of validating a single form."""
    
    form_name: str
    all_valid: bool
    field_count: int = 0
    valid_count: int = 0
    missing_fields: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "form_name": self.form_name,
            "all_valid": self.all_valid,
            "field_count": self.field_count,
            "valid_count": self.valid_count,
            "missing_fields": self.missing_fields,
            "warnings": self.warnings,
        }


@dataclass
class ValidationResult:
    """Result of validating all required forms."""
    
    all_valid: bool
    forms_checked: int = 0
    forms_passed: int = 0
    total_fields: int = 0
    valid_fields: int = 0
    missing_critical: List[str] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    form_results: Dict[str, FormCheckResult] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    # G1: Hard stop fields (phone/email)
    hard_stop_fields: List[str] = field(default_factory=list)
    has_hard_stops: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "all_valid": self.all_valid,
            "forms_checked": self.forms_checked,
            "forms_passed": self.forms_passed,
            "total_fields": self.total_fields,
            "valid_fields": self.valid_fields,
            "missing_critical": self.missing_critical,
            "missing_fields": self.missing_fields,
            "form_results": {k: v.to_dict() for k, v in self.form_results.items()},
            "warnings": self.warnings,
            # Blocking if critical fields OR hard stops missing
            "blocking": len(self.missing_critical) > 0 or self.has_hard_stops,
            # G1: Hard stop info
            "hard_stop_fields": self.hard_stop_fields,
            "has_hard_stops": self.has_hard_stops,
        }


# =============================================================================
# FORM VALIDATOR CLASS
# =============================================================================

class FormValidator:
    """Validates form fields per SOP requirements."""
    
    def validate_form(self, loan_id: str, form_name: str) -> FormCheckResult:
        """Validate all required fields for a specific form.
        
        Args:
            loan_id: Encompass loan GUID
            form_name: Name of form to validate
            
        Returns:
            FormCheckResult with validation details
        """
        if form_name not in REQUIRED_FORMS:
            logger.warning(f"[FORM] Unknown form: {form_name}")
            return FormCheckResult(
                form_name=form_name,
                all_valid=True,
                warnings=[f"Unknown form: {form_name}"]
            )
        
        form_fields = REQUIRED_FORMS[form_name]
        field_ids = list(form_fields.values())
        
        logger.info(f"[FORM] Validating {form_name} ({len(field_ids)} fields)...")
        
        # Read all fields
        values = read_fields(loan_id, field_ids)
        
        # Check which are missing
        missing = []
        valid_count = 0
        
        for field_name, field_id in form_fields.items():
            value = values.get(field_id)
            if value is None or str(value).strip() == "":
                missing.append(field_name)
            else:
                valid_count += 1
        
        all_valid = len(missing) == 0
        
        if all_valid:
            logger.info(f"[FORM] {form_name}: All {len(field_ids)} fields valid")
        else:
            logger.warning(f"[FORM] {form_name}: Missing {len(missing)} fields: {missing}")
        
        return FormCheckResult(
            form_name=form_name,
            all_valid=all_valid,
            field_count=len(field_ids),
            valid_count=valid_count,
            missing_fields=missing
        )
    
    def validate_all_required_forms(self, loan_id: str) -> ValidationResult:
        """Validate all required forms for disclosure.
        
        Args:
            loan_id: Encompass loan GUID
            
        Returns:
            ValidationResult with all form validations
        """
        logger.info(f"[FORM] Validating all required forms for loan {loan_id[:8]}...")
        
        form_results = {}
        total_fields = 0
        valid_fields = 0
        forms_passed = 0
        all_missing = []
        
        for form_name in REQUIRED_FORMS.keys():
            result = self.validate_form(loan_id, form_name)
            form_results[form_name] = result
            
            total_fields += result.field_count
            valid_fields += result.valid_count
            
            if result.all_valid:
                forms_passed += 1
            
            # Add to overall missing list with form prefix
            for field in result.missing_fields:
                all_missing.append(f"{form_name}.{field}")
        
        # Check critical fields specifically
        missing_critical = self._check_critical_fields(loan_id)
        
        # G1: Check HARD STOP fields (phone/email)
        hard_stop_result = self.check_hard_stops(loan_id)
        hard_stop_fields = hard_stop_result.get("missing_fields", [])
        has_hard_stops = hard_stop_result.get("has_hard_stops", False)
        
        # All valid only if no critical AND no hard stops
        all_valid = len(missing_critical) == 0 and not has_hard_stops
        
        logger.info(f"[FORM] Validation complete: {forms_passed}/{len(REQUIRED_FORMS)} forms passed, "
                   f"{valid_fields}/{total_fields} fields valid")
        
        if has_hard_stops:
            logger.warning(f"[FORM] HARD STOPS DETECTED: {hard_stop_fields}")
        
        return ValidationResult(
            all_valid=all_valid,
            forms_checked=len(REQUIRED_FORMS),
            forms_passed=forms_passed,
            total_fields=total_fields,
            valid_fields=valid_fields,
            missing_critical=missing_critical,
            missing_fields=all_missing,
            form_results=form_results,
            # G1: Hard stop info
            hard_stop_fields=hard_stop_fields,
            has_hard_stops=has_hard_stops,
        )
    
    def _check_critical_fields(self, loan_id: str) -> List[str]:
        """Check critical fields that must be present.
        
        These fields are blocking if missing.
        """
        field_ids = list(CRITICAL_FIELDS.values())
        values = read_fields(loan_id, field_ids)
        
        missing = []
        for field_name, field_id in CRITICAL_FIELDS.items():
            value = values.get(field_id)
            if value is None or str(value).strip() == "":
                missing.append(field_name)
        
        return missing
    
    def check_hard_stops(self, loan_id: str) -> Dict[str, Any]:
        """Check HARD STOP fields per SOP.
        
        Per SOP: Missing phone number or email is a HARD STOP.
        These will block disclosure from being sent.
        
        Args:
            loan_id: Encompass loan GUID
            
        Returns:
            Dictionary with:
            - has_hard_stops: Whether any hard stop fields are missing
            - missing_fields: List of missing hard stop fields
            - field_details: Details of each field checked
            - blocking_message: Message if blocking
        """
        logger.info(f"[FORM] Checking HARD STOP fields for loan {loan_id[:8]}...")
        
        field_ids = list(HARD_STOP_FIELDS.values())
        values = read_fields(loan_id, field_ids)
        
        missing = []
        field_details = {}
        
        for field_name, field_id in HARD_STOP_FIELDS.items():
            value = values.get(field_id)
            has_value = value is not None and str(value).strip() != ""
            
            field_details[field_name] = {
                "field_id": field_id,
                "has_value": has_value,
                "value": value if has_value else None,
            }
            
            if not has_value:
                missing.append(field_name)
                logger.warning(f"[FORM] HARD STOP: {field_name} ({field_id}) is missing!")
        
        has_hard_stops = len(missing) > 0
        
        blocking_message = None
        if has_hard_stops:
            blocking_message = f"HARD STOP: Missing {', '.join(missing)}. Cannot proceed with disclosure."
            logger.error(f"[FORM] {blocking_message}")
        else:
            logger.info(f"[FORM] All HARD STOP fields present")
        
        return {
            "has_hard_stops": has_hard_stops,
            "missing_fields": missing,
            "field_details": field_details,
            "blocking": has_hard_stops,
            "blocking_message": blocking_message,
        }
    
    def validate_lo_info(self, loan_id: str) -> Dict[str, Any]:
        """Validate Loan Originator information.
        
        Per SOP:
        - Verify LO is authorized to conduct business in property state
        - Verify LO license is approved and renewed for current year
        
        Args:
            loan_id: Encompass loan GUID
            
        Returns:
            Dictionary with LO validation info
        """
        logger.info(f"[FORM] Validating LO info for loan {loan_id[:8]}...")
        
        field_ids = list(LO_INFO_FIELDS.values())
        field_ids.append("14")  # Property State
        
        values = read_fields(loan_id, field_ids)
        
        lo_nmls = values.get(LO_INFO_FIELDS["lo_nmls_id"])
        property_state = values.get("14")
        
        warnings = []
        
        if not lo_nmls:
            warnings.append("LO NMLS ID is missing")
        
        # Note: Actual NMLS verification requires external API
        # This is a placeholder for the structure
        
        return {
            "lo_name": values.get(LO_INFO_FIELDS["lo_name"]),
            "lo_nmls_id": lo_nmls,
            "lo_company_name": values.get(LO_INFO_FIELDS["lo_company_name"]),
            "lo_company_nmls": values.get(LO_INFO_FIELDS["lo_company_nmls"]),
            "branch_nmls": values.get(LO_INFO_FIELDS["branch_nmls"]),
            "property_state": property_state,
            "warnings": warnings,
            "needs_verification": "Verify LO is licensed in " + (property_state or "property state"),
        }


# =============================================================================
# MODULE-LEVEL FUNCTIONS
# =============================================================================

# Singleton instance
_validator: Optional[FormValidator] = None


def get_form_validator() -> FormValidator:
    """Get the form validator singleton."""
    global _validator
    if _validator is None:
        _validator = FormValidator()
    return _validator


def validate_disclosure_forms(loan_id: str) -> Dict[str, Any]:
    """Validate all required forms for disclosure.
    
    Convenience function that returns a dictionary.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with validation results
    """
    validator = get_form_validator()
    result = validator.validate_all_required_forms(loan_id)
    return result.to_dict()


def check_hard_stop_fields(loan_id: str) -> Dict[str, Any]:
    """Check HARD STOP fields per SOP.
    
    Per SOP: Missing phone number or email is a HARD STOP.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with hard stop check results
    """
    validator = get_form_validator()
    return validator.check_hard_stops(loan_id)


def validate_single_form(loan_id: str, form_name: str) -> Dict[str, Any]:
    """Validate a specific form.
    
    Convenience function.
    
    Args:
        loan_id: Encompass loan GUID
        form_name: Name of form to validate
        
    Returns:
        Dictionary with form validation result
    """
    validator = get_form_validator()
    result = validator.validate_form(loan_id, form_name)
    return result.to_dict()

