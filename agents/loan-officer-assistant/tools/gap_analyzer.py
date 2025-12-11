"""
Loan Officer Assistant - Gap Analyzer Tool

Phase 1: Data Completeness Analysis

Evaluates loan facts against questionnaire requirements to identify
missing or invalid fields. This is the core rules engine for the LOA agent.

Usage:
    gaps = analyze_data_gaps(loan_facts, questionnaire)
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add LOA directory to path for imports
LOA_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(LOA_DIR))

from state import (
    BorrowerFacts,
    GapCategory,
    GapItem,
    GapSeverity,
    GapStatus,
    GapType,
    LoanFacts,
    NeedsListResult,
    PropertyFacts,
)

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

CONFIG_DIR = Path(__file__).parent.parent / "config"
QUESTIONNAIRE_PATH = Path(__file__).parent.parent / "questionnaire_mapping.json"


def load_questionnaire() -> Dict[str, Any]:
    """Load questionnaire mapping configuration."""
    if not QUESTIONNAIRE_PATH.exists():
        logger.error(f"Questionnaire mapping not found at {QUESTIONNAIRE_PATH}")
        raise FileNotFoundError(f"Questionnaire mapping not found: {QUESTIONNAIRE_PATH}")
    
    with open(QUESTIONNAIRE_PATH, "r") as f:
        return json.load(f)


# =============================================================================
# SECTION → CATEGORY MAPPING
# =============================================================================

SECTION_CATEGORY_MAP = {
    "account_setup": GapCategory.BORROWER,
    "current_status": GapCategory.LOAN,
    "application_type": GapCategory.LOAN,
    "borrower_profile": GapCategory.BORROWER,
    "borrower_housing": GapCategory.PROPERTY,
    "real_estate_owned": GapCategory.ASSETS,
    "veteran_status": GapCategory.BORROWER,
    "credit_information": GapCategory.BORROWER,
    "income_and_employment": GapCategory.INCOME,
    "subject_property": GapCategory.PROPERTY,
    "monthly_payment": GapCategory.LOAN,
    "assets": GapCategory.ASSETS,
    "declarations": GapCategory.BORROWER,
}


# =============================================================================
# FIELD SEVERITY MAPPING
# =============================================================================
# Fields marked as CRITICAL block loan progress
# Fields marked as WARN need attention but don't block

CRITICAL_FIELDS = {
    "borrower_ssn",
    "borrower_dob",
    "first_name",
    "last_name",
    "borrower_first_name",
    "borrower_last_name",
    "loan_amount",
    "subject_property_type",
    "borrower_citizenship_status",
}

WARN_FIELDS = {
    "email",
    "primary_phone",
    "borrower_current_address_street",
    "borrower_current_address_city",
    "borrower_current_address_state",
    "borrower_current_address_zip",
    "employer_name",
    "hr_contact_phone",
    "borrower_marital_status",
    "subject_property_occupancy",
    "annual_income_amount",
}


# =============================================================================
# FIELD PATH RESOLUTION
# =============================================================================

# Maps questionnaire field names to LoanFacts paths
FIELD_PATH_MAP = {
    # Account Setup
    "first_name": "borrowers[0].first_name",
    "last_name": "borrowers[0].last_name",
    "primary_phone": "borrowers[0].phone",
    "email": "borrowers[0].email",
    
    # Borrower Profile
    "borrower_first_name": "borrowers[0].first_name",
    "borrower_last_name": "borrowers[0].last_name",
    "borrower_middle_name": "borrowers[0].middle_name",
    "borrower_marital_status": "borrowers[0].marital_status",
    "borrower_citizenship_status": "borrowers[0].citizenship_status",
    "borrower_ssn": "borrowers[0].ssn",
    "borrower_dob": "borrowers[0].dob",
    
    # Borrower Address
    "borrower_current_address_street": "borrowers[0].current_address_street",
    "borrower_current_address_city": "borrowers[0].current_address_city",
    "borrower_current_address_state": "borrowers[0].current_address_state",
    "borrower_current_address_zip": "borrowers[0].current_address_zip",
    "borrower_years_at_current_address": "borrowers[0].years_at_current_address",
    
    # Employment
    "is_self_employed_boolean": "borrowers[0].is_self_employed",
    "employer_name": "borrowers[0].employer_name",
    "employer_address_street": "borrowers[0].employer_address_street",
    "employer_address_city": "borrowers[0].employer_address_city",
    "employer_address_state": "borrowers[0].employer_address_state",
    "employer_address_zip": "borrowers[0].employer_address_zip",
    "hr_contact_phone": "borrowers[0].employer_phone",
    "employer_tenure_years": "borrowers[0].years_on_job",
    "annual_income_amount": "borrowers[0].total_monthly_income",
    
    # Property
    "subject_property_type": "subject_property.property_type",
    "subject_property_occupancy": "subject_property.occupancy_type",
    
    # Loan
    "loan_amount": "loan_amount",
    "purchase_price": "purchase_price",
    "loan_type": "loan_type",
    "loan_purpose": "loan_purpose",
    
    # Co-borrower
    "co_borrower_first_name": "borrowers[1].first_name",
    "co_borrower_last_name": "borrowers[1].last_name",
    "co_borrower_ssn": "borrowers[1].ssn",
    "co_borrower_dob": "borrowers[1].dob",
    
    # Housing
    "borrower_current_housing_status": None,  # Derived field, not in LoanFacts
    "monthly_rent_amount": None,
    "first_time_homebuyer_boolean": None,
    
    # Credit
    "borrower_credit_score_range": "credit_score",
    
    # Contact preferences (typically not in Encompass)
    "preferred_contact_methods[]": None,
    "preferred_contact_times[]": None,
    "has_upcoming_travel_boolean": None,
    "travel_dates_from": None,
    "travel_dates_to": None,
    
    # Real estate agent
    "has_real_estate_agent_boolean": None,
    "real_estate_agent_name": None,
    "real_estate_agent_email": None,
    "real_estate_agent_phone": None,
    
    # Various conditionals / derived
    "homebuying_stage": None,
    "intended_purchase_state": "subject_property.state",
    "intended_purchase_county[]": "subject_property.county",
    "application_type": None,  # Joint/Individual - derived
}


def _get_field_value(loan_facts: LoanFacts, field_path: str) -> Any:
    """
    Get a value from LoanFacts using dot notation path.
    
    Supports array notation like "borrowers[0].first_name"
    """
    if not field_path:
        return None
    
    # Convert LoanFacts to dict for easier traversal
    data = loan_facts.to_dict()
    
    # Parse path components
    parts = re.split(r'\.|\[|\]', field_path)
    parts = [p for p in parts if p]  # Remove empty strings
    
    current = data
    for part in parts:
        if current is None:
            return None
        
        # Array index
        if part.isdigit():
            idx = int(part)
            if isinstance(current, list) and idx < len(current):
                current = current[idx]
            else:
                return None
        # Dict key
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    
    return current


def _is_field_populated(value: Any) -> bool:
    """Check if a field value is considered populated."""
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def _get_severity(field_id: str, question: Dict) -> str:
    """Determine severity for a missing field."""
    # Check explicit severity mappings
    if field_id in CRITICAL_FIELDS:
        return GapSeverity.CRITICAL.value
    if field_id in WARN_FIELDS:
        return GapSeverity.WARN.value
    
    # Check if field ends with common critical patterns
    if field_id.endswith("_ssn") or field_id.endswith("_dob"):
        return GapSeverity.CRITICAL.value
    
    # Default to WARN
    return GapSeverity.WARN.value


def _get_category(section_id: str) -> str:
    """Get category for a section."""
    return SECTION_CATEGORY_MAP.get(section_id, GapCategory.BORROWER).value


# =============================================================================
# CONDITIONAL EVALUATION
# =============================================================================

def _parse_conditional(conditional: str) -> Optional[Tuple[str, str, str, str]]:
    """
    Parse a conditional requirement string.
    
    Patterns:
    - "If {field} == '{value}', collect {document} document."
    - "If {field} == '{value}', ask question '{question_id}'."
    - "Only required if {field} == '{value}'."
    
    Returns:
        Tuple of (field, operator, value, action) or None if not parseable
    """
    # Pattern: If field == 'value', ...
    pattern1 = r"If (\w+) == ['\"]([^'\"]+)['\"],?\s*(.+)"
    match = re.match(pattern1, conditional, re.IGNORECASE)
    if match:
        field, value, action = match.groups()
        return (field, "==", value, action.strip())
    
    # Pattern: Only required if field == 'value'
    pattern2 = r"Only required if (\w+) == ['\"]([^'\"]+)['\"]"
    match = re.match(pattern2, conditional, re.IGNORECASE)
    if match:
        field, value = match.groups()
        return (field, "==", value, "required")
    
    return None


def _evaluate_condition(loan_facts: LoanFacts, field: str, operator: str, expected: str) -> bool:
    """
    Evaluate a condition against loan facts.
    
    Returns True if condition is met.
    """
    # Map field to path
    field_path = FIELD_PATH_MAP.get(field)
    if not field_path:
        # Try direct path
        field_path = field
    
    actual = _get_field_value(loan_facts, field_path)
    
    if actual is None:
        return False
    
    actual_str = str(actual).lower()
    expected_str = expected.lower()
    
    if operator == "==":
        return actual_str == expected_str
    elif operator == "!=":
        return actual_str != expected_str
    elif operator == "contains":
        return expected_str in actual_str
    
    return False


def _question_applies(question: Dict, loan_facts: LoanFacts) -> bool:
    """
    Check if a question applies to this loan based on conditionals.
    
    A question does NOT apply if it has an "Only required if..." conditional
    that evaluates to False.
    """
    conditionals = question.get("conditional_requirements", [])
    
    for cond_str in conditionals:
        if not cond_str.startswith("Only required if"):
            continue
        
        parsed = _parse_conditional(cond_str)
        if not parsed:
            continue
        
        field, operator, expected, _ = parsed
        
        # If the "only required" condition is NOT met, question doesn't apply
        if not _evaluate_condition(loan_facts, field, operator, expected):
            return False
    
    return True


# =============================================================================
# PHASE 1: DATA COMPLETENESS ANALYSIS
# =============================================================================

def analyze_data_gaps(
    loan_facts: LoanFacts,
    questionnaire: Optional[Dict] = None
) -> NeedsListResult:
    """
    Analyze loan facts for data completeness gaps (Phase 1).
    
    This function evaluates each question in the questionnaire and checks
    if the required_fields are populated in loan_facts.
    
    Args:
        loan_facts: Normalized loan data from Encompass
        questionnaire: Questionnaire mapping config (loads default if None)
        
    Returns:
        NeedsListResult with all identified data gaps
    """
    if questionnaire is None:
        questionnaire = load_questionnaire()
    
    logger.info(f"[GAP] Starting data gap analysis for loan {loan_facts.loan_id[:8]}...")
    
    gaps: List[GapItem] = []
    checked_fields: set = set()  # Track fields we've already checked
    
    sections = questionnaire.get("sections", [])
    
    for section in sections:
        section_id = section.get("section_id", "unknown")
        questions = section.get("questions", [])
        
        for question in questions:
            question_id = question.get("question_id", "unknown")
            
            # Check if question applies to this loan
            if not _question_applies(question, loan_facts):
                logger.debug(f"[GAP] Skipping question {question_id} - conditionals not met")
                continue
            
            required_fields = question.get("required_fields", [])
            prompt = question.get("prompt", "")
            
            for field_id in required_fields:
                # Skip array fields for now (like "previous_address[]")
                if field_id.endswith("[]"):
                    continue
                
                # Skip if we've already checked this field
                if field_id in checked_fields:
                    continue
                checked_fields.add(field_id)
                
                # Get the field path in LoanFacts
                field_path = FIELD_PATH_MAP.get(field_id)
                
                # Skip fields that aren't mapped to Encompass
                if field_path is None:
                    logger.debug(f"[GAP] Field {field_id} not mapped to Encompass - skipping")
                    continue
                
                # Get the current value
                value = _get_field_value(loan_facts, field_path)
                
                # Check if populated
                if _is_field_populated(value):
                    logger.debug(f"[GAP] ✓ Field {field_id} is populated: {value}")
                    continue
                
                # Field is missing - create gap item
                severity = _get_severity(field_id, question)
                category = _get_category(section_id)
                
                gap = GapItem(
                    id=f"DATA_{section_id}_{question_id}_{field_id}",
                    category=category,
                    type=GapType.DATA.value,
                    status=GapStatus.MISSING.value,
                    severity=severity,
                    label=f"Missing: {field_id}",
                    reason=prompt,
                    action=f"Collect {_humanize_field(field_id)} from borrower",
                    field_id=field_id,
                    current_value=None,
                    section_id=section_id,
                    question_id=question_id,
                )
                
                gaps.append(gap)
                logger.info(f"[GAP] ✗ Missing field: {field_id} ({severity})")
    
    # Build result
    result = NeedsListResult(
        phases_completed=["DATA"],
        items=gaps,
    )
    
    # Compute summary
    result.compute_summary()
    
    logger.info(f"[GAP] Analysis complete:")
    logger.info(f"[GAP]   - Total gaps: {result.summary.total}")
    logger.info(f"[GAP]   - Critical: {result.summary.critical_count}")
    logger.info(f"[GAP]   - Warnings: {result.summary.warn_count}")
    logger.info(f"[GAP]   - Can proceed: {result.summary.can_proceed}")
    
    return result


def _humanize_field(field_id: str) -> str:
    """Convert field_id to human-readable label."""
    # Remove prefixes
    label = field_id
    for prefix in ("borrower_", "co_borrower_", "subject_", "has_", "is_"):
        if label.startswith(prefix):
            label = label[len(prefix):]
            break
    
    # Remove suffixes
    for suffix in ("_boolean", "_amount", "[]"):
        if label.endswith(suffix):
            label = label[:-len(suffix)]
    
    # Replace underscores with spaces and title case
    label = label.replace("_", " ").title()
    
    # Common replacements
    label = label.replace("Ssn", "SSN")
    label = label.replace("Dob", "Date of Birth")
    label = label.replace("Hr ", "HR ")
    
    return label


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_critical_gaps(result: NeedsListResult) -> List[GapItem]:
    """Get only critical severity gaps."""
    return [g for g in result.items if g.severity == GapSeverity.CRITICAL.value]


def get_gaps_by_category(result: NeedsListResult, category: str) -> List[GapItem]:
    """Get gaps for a specific category."""
    return [g for g in result.items if g.category == category]


def format_gaps_summary(result: NeedsListResult) -> str:
    """Format gaps as a human-readable summary."""
    lines = []
    
    if result.summary.total == 0:
        return "No data gaps identified."
    
    lines.append(f"Found {result.summary.total} data gaps:")
    lines.append("")
    
    # Critical items
    critical = get_critical_gaps(result)
    if critical:
        lines.append("CRITICAL ISSUES:")
        for gap in critical:
            lines.append(f"  ❌ {gap.label}")
        lines.append("")
    
    # Warnings
    warnings = [g for g in result.items if g.severity == GapSeverity.WARN.value]
    if warnings:
        lines.append("NEEDS ATTENTION:")
        for gap in warnings:
            lines.append(f"  ⚠️ {gap.label}")
        lines.append("")
    
    # Summary
    if result.summary.can_proceed:
        lines.append("✅ Loan can proceed (no critical blockers)")
    else:
        lines.append("⛔ Loan BLOCKED - resolve critical issues first")
    
    return "\n".join(lines)


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test with sample data (state already imported at top)
    
    # Create test loan facts with some missing data
    test_loan = LoanFacts(
        loan_id="test-loan-123",
        loan_type="Conventional",
        loan_purpose="Purchase",
        loan_amount=450000.0,
        borrowers=[
            BorrowerFacts(
                borrower_type="PRIMARY",
                first_name="John",
                last_name="Smith",
                ssn=None,  # Missing!
                dob="1985-03-15",
                email="john@example.com",
                phone=None,  # Missing!
                marital_status="Separated",  # Triggers conditional
            )
        ],
        subject_property=PropertyFacts(
            address="123 Main St",
            city="Denver",
            state="CO",
            zip="80202",
            property_type=None,  # Missing!
            occupancy_type="PrimaryResidence",
        ),
    )
    
    # Run analysis
    result = analyze_data_gaps(test_loan)
    
    # Print results
    print("\n" + "=" * 60)
    print("GAP ANALYSIS RESULTS")
    print("=" * 60)
    print(format_gaps_summary(result))
    print("\n" + "=" * 60)
    print("DETAILED GAPS:")
    print("=" * 60)
    for gap in result.items:
        print(f"\n{gap.id}:")
        print(f"  Severity: {gap.severity}")
        print(f"  Label: {gap.label}")
        print(f"  Reason: {gap.reason}")
        print(f"  Action: {gap.action}")

