"""
Rule Definitions for Unified Rule Engine

This file contains all business rule definitions for DrawDocs.
Rules are organized by category and can be easily enabled/disabled.

Categories:
- Hard Stop Rules (CRITICAL - must fix before proceeding)
- Discrepancy Rules (HIGH - PTF conditions)
- Pre-flight Checks (CRITICAL/HIGH - validate before processing)
- Insurance Rules (varies)
- State-Specific Rules (varies)

Created: December 9, 2025
"""

from typing import Dict, Any
from datetime import datetime, timedelta
import logging

from .unified_rules_engine import (
    Rule,
    RuleResult,
    RuleSeverity,
    RuleCategory,
    RulePrerequisites,
    PTFCondition,
    compare_names,
    compare_addresses,
    compare_amounts,
    parse_date,
    get_rule_engine
)

logger = logging.getLogger(__name__)


# ============================================================================
# HARD STOP RULES (CRITICAL)
# ============================================================================

def validate_loan_amount_match(field_values: Dict[str, Any], loan_context: Dict[str, Any]) -> RuleResult:
    """Loan Amount must match exactly between documents and Encompass"""
    extracted = field_values.get("1109_extracted")
    encompass = field_values.get("1109")
    
    if not extracted or not encompass:
        return RuleResult(
            rule_id="HARD_LOAN_AMOUNT",
            rule_name="Loan Amount Match",
            passed=False,
            severity=RuleSeverity.CRITICAL.value,
            category=RuleCategory.FINANCIAL.value,
            field_id="1109",
            field_name="Loan Amount",
            extracted_value=extracted,
            encompass_value=encompass,
            message="Missing loan amount - cannot validate",
            metadata={"tolerance": 0}
        )
    
    is_match, diff = compare_amounts(extracted, encompass, tolerance=0)
    
    if not is_match:
        return RuleResult(
            rule_id="HARD_LOAN_AMOUNT",
            rule_name="Loan Amount Match",
            passed=False,
            severity=RuleSeverity.CRITICAL.value,
            category=RuleCategory.FINANCIAL.value,
            field_id="1109",
            field_name="Loan Amount",
            extracted_value=extracted,
            encompass_value=encompass,
            message=f"HARD STOP - {diff}. Contact Team Lead immediately.",
            metadata={"tolerance": 0, "difference": diff}
        )
    
    return RuleResult(
        rule_id="HARD_LOAN_AMOUNT",
        rule_name="Loan Amount Match",
        passed=True,
        severity=RuleSeverity.CRITICAL.value,
        category=RuleCategory.FINANCIAL.value,
        field_id="1109",
        field_name="Loan Amount",
        extracted_value=extracted,
        encompass_value=encompass,
        message="Loan amount matches"
    )


def validate_interest_rate_match(field_values: Dict[str, Any], loan_context: Dict[str, Any]) -> RuleResult:
    """Interest Rate must match exactly"""
    extracted = field_values.get("3_extracted")
    encompass = field_values.get("3")
    
    if not extracted or not encompass:
        return RuleResult(
            rule_id="HARD_INTEREST_RATE",
            rule_name="Interest Rate Match",
            passed=False,
            severity=RuleSeverity.CRITICAL.value,
            category=RuleCategory.FINANCIAL.value,
            field_id="3",
            field_name="Interest Rate",
            extracted_value=extracted,
            encompass_value=encompass,
            message="Missing interest rate - cannot validate"
        )
    
    is_match, diff = compare_amounts(extracted, encompass, tolerance=0)
    
    if not is_match:
        return RuleResult(
            rule_id="HARD_INTEREST_RATE",
            rule_name="Interest Rate Match",
            passed=False,
            severity=RuleSeverity.CRITICAL.value,
            category=RuleCategory.FINANCIAL.value,
            field_id="3",
            field_name="Interest Rate",
            extracted_value=extracted,
            encompass_value=encompass,
            message=f"HARD STOP - {diff}. Contact Team Lead immediately."
        )
    
    return RuleResult(
        rule_id="HARD_INTEREST_RATE",
        rule_name="Interest Rate Match",
        passed=True,
        severity=RuleSeverity.CRITICAL.value,
        category=RuleCategory.FINANCIAL.value,
        field_id="3",
        field_name="Interest Rate",
        extracted_value=extracted,
        encompass_value=encompass,
        message="Interest rate matches"
    )


def validate_hazard_insurance_match(field_values: Dict[str, Any], loan_context: Dict[str, Any]) -> RuleResult:
    """Monthly Hazard Insurance must match UW Final Approval exactly"""
    extracted = field_values.get("578_extracted")
    encompass = field_values.get("578")
    
    if not extracted or not encompass:
        return RuleResult(
            rule_id="HARD_HAZARD_INSURANCE",
            rule_name="Monthly Hazard Insurance Match",
            passed=False,
            severity=RuleSeverity.CRITICAL.value,
            category=RuleCategory.INSURANCE.value,
            field_id="578",
            field_name="Monthly Hazard Insurance",
            extracted_value=extracted,
            encompass_value=encompass,
            message="Missing hazard insurance amount"
        )
    
    is_match, diff = compare_amounts(extracted, encompass, tolerance=0)
    
    if not is_match:
        return RuleResult(
            rule_id="HARD_HAZARD_INSURANCE",
            rule_name="Monthly Hazard Insurance Match",
            passed=False,
            severity=RuleSeverity.CRITICAL.value,
            category=RuleCategory.INSURANCE.value,
            field_id="578",
            field_name="Monthly Hazard Insurance",
            extracted_value=extracted,
            encompass_value=encompass,
            message=f"HARD STOP - {diff}. Get revised Final Approval from UW (NO PTF allowed)."
        )
    
    return RuleResult(
        rule_id="HARD_HAZARD_INSURANCE",
        rule_name="Monthly Hazard Insurance Match",
        passed=True,
        severity=RuleSeverity.CRITICAL.value,
        category=RuleCategory.INSURANCE.value,
        field_id="578",
        field_name="Monthly Hazard Insurance",
        extracted_value=extracted,
        encompass_value=encompass,
        message="Hazard insurance matches"
    )


def validate_property_tax_match(field_values: Dict[str, Any], loan_context: Dict[str, Any]) -> RuleResult:
    """Monthly Property Tax must match UW Final Approval exactly"""
    extracted = field_values.get("231_extracted")
    encompass = field_values.get("231")
    
    if not extracted or not encompass:
        return RuleResult(
            rule_id="HARD_PROPERTY_TAX",
            rule_name="Monthly Property Tax Match",
            passed=False,
            severity=RuleSeverity.CRITICAL.value,
            category=RuleCategory.FINANCIAL.value,
            field_id="231",
            field_name="Monthly Property Tax",
            extracted_value=extracted,
            encompass_value=encompass,
            message="Missing property tax amount"
        )
    
    is_match, diff = compare_amounts(extracted, encompass, tolerance=0)
    
    if not is_match:
        return RuleResult(
            rule_id="HARD_PROPERTY_TAX",
            rule_name="Monthly Property Tax Match",
            passed=False,
            severity=RuleSeverity.CRITICAL.value,
            category=RuleCategory.FINANCIAL.value,
            field_id="231",
            field_name="Monthly Property Tax",
            extracted_value=extracted,
            encompass_value=encompass,
            message=f"HARD STOP - {diff}. Get revised Final Approval from UW (NO PTF allowed)."
        )
    
    return RuleResult(
        rule_id="HARD_PROPERTY_TAX",
        rule_name="Monthly Property Tax Match",
        passed=True,
        severity=RuleSeverity.CRITICAL.value,
        category=RuleCategory.FINANCIAL.value,
        field_id="231",
        field_name="Monthly Property Tax",
        extracted_value=extracted,
        encompass_value=encompass,
        message="Property tax matches"
    )


# ============================================================================
# SOFT DISCREPANCY RULES (HIGH - PTF)
# ============================================================================

def validate_borrower_first_name(field_values: Dict[str, Any], loan_context: Dict[str, Any]) -> RuleResult:
    """Borrower First Name comparison with middle initial tolerance"""
    extracted = field_values.get("11_extracted")
    encompass = field_values.get("11")
    
    if not extracted or not encompass:
        return RuleResult(
            rule_id="SOFT_BORROWER_FIRST_NAME",
            rule_name="Borrower First Name",
            passed=True,  # Missing values don't generate PTF
            severity=RuleSeverity.HIGH.value,
            category=RuleCategory.BORROWER.value,
            field_id="11",
            field_name="Borrower First Name",
            message="Missing name data"
        )
    
    is_match, diff = compare_names(extracted, encompass, ignore_middle_initial=True)
    
    if not is_match:
        return RuleResult(
            rule_id="SOFT_BORROWER_FIRST_NAME",
            rule_name="Borrower First Name",
            passed=False,
            severity=RuleSeverity.HIGH.value,
            category=RuleCategory.BORROWER.value,
            field_id="11",
            field_name="Borrower First Name",
            extracted_value=extracted,
            encompass_value=encompass,
            message=diff,
            ptf_condition=PTFCondition(
                category=RuleCategory.BORROWER.value,
                description_template="PTF - Verify Borrower First Name: Document shows '{extracted}', Encompass shows '{encompass}'",
                assigned_to="Loan Processor"
            )
        )
    
    return RuleResult(
        rule_id="SOFT_BORROWER_FIRST_NAME",
        rule_name="Borrower First Name",
        passed=True,
        severity=RuleSeverity.HIGH.value,
        category=RuleCategory.BORROWER.value,
        field_id="11",
        field_name="Borrower First Name",
        extracted_value=extracted,
        encompass_value=encompass,
        message="Name matches"
    )


def validate_borrower_last_name(field_values: Dict[str, Any], loan_context: Dict[str, Any]) -> RuleResult:
    """Borrower Last Name comparison"""
    extracted = field_values.get("12_extracted")
    encompass = field_values.get("12")
    
    if not extracted or not encompass:
        return RuleResult(
            rule_id="SOFT_BORROWER_LAST_NAME",
            rule_name="Borrower Last Name",
            passed=True,
            severity=RuleSeverity.HIGH.value,
            category=RuleCategory.BORROWER.value,
            field_id="12",
            field_name="Borrower Last Name",
            message="Missing name data"
        )
    
    is_match, diff = compare_names(extracted, encompass, ignore_middle_initial=False)
    
    if not is_match:
        return RuleResult(
            rule_id="SOFT_BORROWER_LAST_NAME",
            rule_name="Borrower Last Name",
            passed=False,
            severity=RuleSeverity.HIGH.value,
            category=RuleCategory.BORROWER.value,
            field_id="12",
            field_name="Borrower Last Name",
            extracted_value=extracted,
            encompass_value=encompass,
            message=diff,
            ptf_condition=PTFCondition(
                category=RuleCategory.BORROWER.value,
                description_template="PTF - Verify Borrower Last Name: Document shows '{extracted}', Encompass shows '{encompass}'",
                assigned_to="Loan Processor"
            )
        )
    
    return RuleResult(
        rule_id="SOFT_BORROWER_LAST_NAME",
        rule_name="Borrower Last Name",
        passed=True,
        severity=RuleSeverity.HIGH.value,
        category=RuleCategory.BORROWER.value,
        field_id="12",
        field_name="Borrower Last Name",
        extracted_value=extracted,
        encompass_value=encompass,
        message="Name matches"
    )


def validate_property_address(field_values: Dict[str, Any], loan_context: Dict[str, Any]) -> RuleResult:
    """Property Address comparison with suffix tolerance"""
    extracted = field_values.get("15_extracted")
    encompass = field_values.get("15")
    
    if not extracted or not encompass:
        return RuleResult(
            rule_id="SOFT_PROPERTY_ADDRESS",
            rule_name="Subject Property Address",
            passed=True,
            severity=RuleSeverity.HIGH.value,
            category=RuleCategory.PROPERTY.value,
            field_id="15",
            field_name="Subject Property Address",
            message="Missing address data"
        )
    
    is_match, diff = compare_addresses(extracted, encompass)
    
    if not is_match:
        return RuleResult(
            rule_id="SOFT_PROPERTY_ADDRESS",
            rule_name="Subject Property Address",
            passed=False,
            severity=RuleSeverity.HIGH.value,
            category=RuleCategory.PROPERTY.value,
            field_id="15",
            field_name="Subject Property Address",
            extracted_value=extracted,
            encompass_value=encompass,
            message=diff,
            ptf_condition=PTFCondition(
                category=RuleCategory.PROPERTY.value,
                description_template="PTF - Property address format mismatch - verify with title report. Document: '{extracted}', Encompass: '{encompass}'",
                assigned_to="Loan Processor"
            )
        )
    
    return RuleResult(
        rule_id="SOFT_PROPERTY_ADDRESS",
        rule_name="Subject Property Address",
        passed=True,
        severity=RuleSeverity.HIGH.value,
        category=RuleCategory.PROPERTY.value,
        field_id="15",
        field_name="Subject Property Address",
        extracted_value=extracted,
        encompass_value=encompass,
        message="Address matches"
    )


def validate_coborrower_first_name(field_values: Dict[str, Any], loan_context: Dict[str, Any]) -> RuleResult:
    """Co-Borrower First Name comparison"""
    extracted = field_values.get("4004_extracted")
    encompass = field_values.get("4004")
    
    if not extracted or not encompass:
        return RuleResult(
            rule_id="SOFT_COBORROWER_FIRST_NAME",
            rule_name="Co-Borrower First Name",
            passed=True,
            severity=RuleSeverity.HIGH.value,
            category=RuleCategory.BORROWER.value,
            field_id="4004",
            field_name="Co-Borrower First Name",
            message="Missing name data or no co-borrower"
        )
    
    is_match, diff = compare_names(extracted, encompass, ignore_middle_initial=True)
    
    if not is_match:
        return RuleResult(
            rule_id="SOFT_COBORROWER_FIRST_NAME",
            rule_name="Co-Borrower First Name",
            passed=False,
            severity=RuleSeverity.HIGH.value,
            category=RuleCategory.BORROWER.value,
            field_id="4004",
            field_name="Co-Borrower First Name",
            extracted_value=extracted,
            encompass_value=encompass,
            message=diff,
            ptf_condition=PTFCondition(
                category=RuleCategory.BORROWER.value,
                description_template="PTF - Verify Co-Borrower First Name: Document shows '{extracted}', Encompass shows '{encompass}'",
                assigned_to="Loan Processor"
            )
        )
    
    return RuleResult(
        rule_id="SOFT_COBORROWER_FIRST_NAME",
        rule_name="Co-Borrower First Name",
        passed=True,
        severity=RuleSeverity.HIGH.value,
        category=RuleCategory.BORROWER.value,
        field_id="4004",
        field_name="Co-Borrower First Name",
        extracted_value=extracted,
        encompass_value=encompass,
        message="Name matches"
    )


# ============================================================================
# PRE-FLIGHT CHECKS
# ============================================================================

def validate_lock_expiration(field_values: Dict[str, Any], loan_context: Dict[str, Any]) -> RuleResult:
    """Lock must not expire before rescission period ends"""
    lock_expiry = field_values.get("762")
    closing_date = field_values.get("748")
    
    if not lock_expiry or not closing_date:
        return RuleResult(
            rule_id="PREFLIGHT_LOCK_EXPIRATION",
            rule_name="Lock Expiration Date Check",
            passed=False,
            severity=RuleSeverity.CRITICAL.value,
            category=RuleCategory.PREFLIGHT.value,
            field_id="762",
            field_name="Lock Expiration Date",
            encompass_value=lock_expiry,
            expected_value="Lock expiry after rescission period",
            message="Missing lock expiration date or closing date",
            metadata={"closing_date": closing_date}
        )
    
    # Parse dates
    lock_date = parse_date(lock_expiry)
    close_date = parse_date(closing_date)
    
    if not lock_date or not close_date:
        return RuleResult(
            rule_id="PREFLIGHT_LOCK_EXPIRATION",
            rule_name="Lock Expiration Date Check",
            passed=False,
            severity=RuleSeverity.CRITICAL.value,
            category=RuleCategory.PREFLIGHT.value,
            field_id="762",
            field_name="Lock Expiration Date",
            encompass_value=lock_expiry,
            message="Invalid date format"
        )
    
    # Calculate rescission end (3 days after closing)
    rescission_end = close_date + timedelta(days=3)
    
    if lock_date < rescission_end:
        return RuleResult(
            rule_id="PREFLIGHT_LOCK_EXPIRATION",
            rule_name="Lock Expiration Date Check",
            passed=False,
            severity=RuleSeverity.CRITICAL.value,
            category=RuleCategory.PREFLIGHT.value,
            field_id="762",
            field_name="Lock Expiration Date",
            encompass_value=lock_expiry,
            expected_value=f"After {rescission_end.strftime('%Y-%m-%d')}",
            message=f"Lock expires {lock_date.strftime('%Y-%m-%d')} before rescission ends {rescission_end.strftime('%Y-%m-%d')}. Must relock before funding.",
            ptf_condition=PTFCondition(
                category=RuleCategory.COMPLIANCE.value,
                description_template="PTF - Lock expires before rescission period. Lock date: {encompass}, Rescission end: {expected}. Must relock before funding.",
                assigned_to="Loan Officer",
                severity="HOLD"
            ),
            metadata={
                "closing_date": closing_date,
                "rescission_end": rescission_end.strftime('%Y-%m-%d')
            }
        )
    
    return RuleResult(
        rule_id="PREFLIGHT_LOCK_EXPIRATION",
        rule_name="Lock Expiration Date Check",
        passed=True,
        severity=RuleSeverity.CRITICAL.value,
        category=RuleCategory.PREFLIGHT.value,
        field_id="762",
        field_name="Lock Expiration Date",
        encompass_value=lock_expiry,
        message=f"Lock valid through {lock_date.strftime('%Y-%m-%d')}",
        metadata={
            "closing_date": closing_date,
            "rescission_end": rescission_end.strftime('%Y-%m-%d')
        }
    )


# ============================================================================
# REGISTER ALL RULES
# ============================================================================

def register_all_rules():
    """Register all rules with the engine"""
    engine = get_rule_engine()
    
    # Hard Stop Rules
    engine.register_rule(Rule(
        rule_id="HARD_LOAN_AMOUNT",
        name="Loan Amount Match",
        description="Loan Amount must match exactly between documents and Encompass (NO tolerance)",
        category=RuleCategory.FINANCIAL,
        severity=RuleSeverity.CRITICAL,
        fields_required=["1109", "1109_extracted"],
        validation_function=validate_loan_amount_match,
        sop_reference="SOP Page 35 - Hard Stop Rules"
    ))
    
    engine.register_rule(Rule(
        rule_id="HARD_INTEREST_RATE",
        name="Interest Rate Match",
        description="Interest Rate must match exactly between Final Approval and Encompass",
        category=RuleCategory.FINANCIAL,
        severity=RuleSeverity.CRITICAL,
        fields_required=["3", "3_extracted"],
        validation_function=validate_interest_rate_match,
        sop_reference="SOP Page 35 - Hard Stop Rules"
    ))
    
    engine.register_rule(Rule(
        rule_id="HARD_HAZARD_INSURANCE",
        name="Monthly Hazard Insurance Match",
        description="Monthly Hazard Insurance must match UW Final Approval exactly",
        category=RuleCategory.INSURANCE,
        severity=RuleSeverity.CRITICAL,
        fields_required=["578", "578_extracted"],
        validation_function=validate_hazard_insurance_match,
        sop_reference="SOP Page 35 - Hard Stop Rules"
    ))
    
    engine.register_rule(Rule(
        rule_id="HARD_PROPERTY_TAX",
        name="Monthly Property Tax Match",
        description="Monthly Property Tax must match UW Final Approval exactly",
        category=RuleCategory.FINANCIAL,
        severity=RuleSeverity.CRITICAL,
        fields_required=["231", "231_extracted"],
        validation_function=validate_property_tax_match,
        sop_reference="SOP Page 35 - Hard Stop Rules"
    ))
    
    # Soft Discrepancy Rules (PTF)
    engine.register_rule(Rule(
        rule_id="SOFT_BORROWER_FIRST_NAME",
        name="Borrower First Name",
        description="Borrower First Name comparison with middle initial tolerance",
        category=RuleCategory.BORROWER,
        severity=RuleSeverity.HIGH,
        fields_required=["11", "11_extracted"],
        validation_function=validate_borrower_first_name,
        sop_reference="SOP Page 37 - Acceptable Variances"
    ))
    
    engine.register_rule(Rule(
        rule_id="SOFT_BORROWER_LAST_NAME",
        name="Borrower Last Name",
        description="Borrower Last Name comparison",
        category=RuleCategory.BORROWER,
        severity=RuleSeverity.HIGH,
        fields_required=["12", "12_extracted"],
        validation_function=validate_borrower_last_name,
        sop_reference="SOP Page 37 - Acceptable Variances"
    ))
    
    engine.register_rule(Rule(
        rule_id="SOFT_PROPERTY_ADDRESS",
        name="Subject Property Address",
        description="Property Address comparison with suffix tolerance",
        category=RuleCategory.PROPERTY,
        severity=RuleSeverity.HIGH,
        fields_required=["15", "15_extracted"],
        validation_function=validate_property_address,
        sop_reference="SOP Page 37 - Acceptable Variances"
    ))
    
    engine.register_rule(Rule(
        rule_id="SOFT_COBORROWER_FIRST_NAME",
        name="Co-Borrower First Name",
        description="Co-Borrower First Name comparison with middle initial tolerance",
        category=RuleCategory.BORROWER,
        severity=RuleSeverity.HIGH,
        fields_required=["4004", "4004_extracted"],
        validation_function=validate_coborrower_first_name,
        sop_reference="SOP Page 37 - Acceptable Variances"
    ))
    
    # Pre-flight Checks
    engine.register_rule(Rule(
        rule_id="PREFLIGHT_LOCK_EXPIRATION",
        name="Lock Expiration Date Check",
        description="Lock must not expire before rescission period ends (Closing + 3 days)",
        category=RuleCategory.PREFLIGHT,
        severity=RuleSeverity.CRITICAL,
        fields_required=["762", "748"],
        validation_function=validate_lock_expiration,
        sop_reference="SOP Step 5 - Lock Expiration Check"
    ))
    
    logger.info(f"Registered {len(engine.list_rules())} rules")


# Don't auto-register on import to avoid circular dependencies
# Call register_all_rules() explicitly when needed

