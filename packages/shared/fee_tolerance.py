"""Fee Tolerance Calculator for disclosure and draw docs agents.

MVP Scope: Flag tolerance violations only (no auto-cure).
Auto-cure is Phase 2.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import FeeTolerance

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ToleranceViolation:
    """A single fee tolerance violation."""
    
    fee_id: str
    fee_name: str
    le_amount: float
    cd_amount: float
    difference: float
    tolerance_type: str  # "zero", "ten_percent", "none"
    violation_amount: float
    section: str  # "A", "B", "C"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "fee_id": self.fee_id,
            "fee_name": self.fee_name,
            "le_amount": self.le_amount,
            "cd_amount": self.cd_amount,
            "difference": self.difference,
            "tolerance_type": self.tolerance_type,
            "violation_amount": self.violation_amount,
            "section": self.section,
        }


@dataclass
class ToleranceResult:
    """Result of fee tolerance check."""
    
    has_violations: bool
    total_cure_needed: float
    zero_tolerance_violations: List[ToleranceViolation] = field(default_factory=list)
    ten_percent_violations: List[ToleranceViolation] = field(default_factory=list)
    section_b_total_le: float = 0.0
    section_b_total_cd: float = 0.0
    section_b_increase: float = 0.0
    section_b_allowed_increase: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "has_violations": self.has_violations,
            "total_cure_needed": self.total_cure_needed,
            "zero_tolerance_violations": [v.to_dict() for v in self.zero_tolerance_violations],
            "ten_percent_violations": [v.to_dict() for v in self.ten_percent_violations],
            "section_b_total_le": self.section_b_total_le,
            "section_b_total_cd": self.section_b_total_cd,
            "section_b_increase": self.section_b_increase,
            "section_b_allowed_increase": self.section_b_allowed_increase,
        }
    
    def get_summary(self) -> str:
        """Get human-readable summary of violations."""
        if not self.has_violations:
            return "No fee tolerance violations found."
        
        lines = ["Fee Tolerance Violations Found:"]
        
        if self.zero_tolerance_violations:
            lines.append(f"\n0% Tolerance Violations ({len(self.zero_tolerance_violations)}):")
            for v in self.zero_tolerance_violations:
                lines.append(f"  - {v.fee_name}: LE ${v.le_amount:.2f} → CD ${v.cd_amount:.2f} (increase ${v.difference:.2f})")
        
        if self.ten_percent_violations:
            lines.append(f"\n10% Tolerance Violations:")
            lines.append(f"  Section B Total: LE ${self.section_b_total_le:.2f} → CD ${self.section_b_total_cd:.2f}")
            lines.append(f"  Increase: ${self.section_b_increase:.2f} (allowed: ${self.section_b_allowed_increase:.2f})")
        
        lines.append(f"\nTotal Cure Needed: ${self.total_cure_needed:.2f}")
        
        return "\n".join(lines)


# =============================================================================
# FEE DEFINITIONS
# =============================================================================

# Section A fees (0% tolerance) - common field IDs
SECTION_A_FEES = {
    "NEWHUD.X7": "Origination Fee",
    "NEWHUD.X8": "Discount Points",
    "NEWHUD.X9": "Application Fee",
    "NEWHUD.X10": "Underwriting Fee",
    "NEWHUD.X11": "Processing Fee",
}

# Section B fees (10% tolerance when using SPL provider)
SECTION_B_FEES = {
    "NEWHUD.X12": "Appraisal Fee",
    "NEWHUD.X13": "Appraisal Management Fee",
    "NEWHUD.X14": "Credit Report - Joint",
    "NEWHUD.X15": "Credit Report Fee",
    "NEWHUD.X17": "Flood Certification",
    "NEWHUD.X18": "Flood Monitoring",
    "NEWHUD.X19": "Tax Service Fee",
    "NEWHUD.X20": "Title - Settlement Fee",
    "NEWHUD.X21": "Title - Lender's Title Insurance",
}

# Section C fees (no tolerance - borrower shopped)
SECTION_C_FEES = {
    # These are borrower-shopped services with no tolerance protection
    # Typically title services if borrower chose own provider
}


# =============================================================================
# TOLERANCE CHECK FUNCTIONS
# =============================================================================

def check_fee_tolerance(
    le_fees: Dict[str, float],
    cd_fees: Dict[str, float],
    section_b_using_spl: bool = True,
) -> ToleranceResult:
    """Check fee tolerance between LE and CD fees.
    
    MVP: Flag violations only (no auto-cure).
    
    TRID Tolerance Rules:
    - Section A (0% tolerance): Fees cannot increase at all
    - Section B (10% tolerance): Aggregate fees can increase up to 10%
    - Section C (no tolerance): Borrower-shopped, no protection
    
    Args:
        le_fees: Dictionary of LE fees {field_id: amount}
        cd_fees: Dictionary of CD fees {field_id: amount}
        section_b_using_spl: If True, Section B fees have 10% tolerance
        
    Returns:
        ToleranceResult with violation details
        
    Example:
        result = check_fee_tolerance(
            le_fees={"NEWHUD.X7": 1000, "NEWHUD.X12": 500},
            cd_fees={"NEWHUD.X7": 1050, "NEWHUD.X12": 550}
        )
        if result.has_violations:
            print(f"Cure needed: ${result.total_cure_needed}")
    """
    logger.info("[TOLERANCE] Checking fee tolerance...")
    
    zero_violations = []
    ten_violations = []
    total_cure = 0.0
    
    # Section B aggregates
    section_b_le_total = 0.0
    section_b_cd_total = 0.0
    
    # Check Section A fees (0% tolerance)
    for fee_id, fee_name in SECTION_A_FEES.items():
        le_amount = le_fees.get(fee_id, 0.0) or 0.0
        cd_amount = cd_fees.get(fee_id, 0.0) or 0.0
        
        if cd_amount > le_amount:
            difference = cd_amount - le_amount
            violation = ToleranceViolation(
                fee_id=fee_id,
                fee_name=fee_name,
                le_amount=le_amount,
                cd_amount=cd_amount,
                difference=difference,
                tolerance_type="zero",
                violation_amount=difference,
                section="A",
            )
            zero_violations.append(violation)
            total_cure += difference
            logger.warning(f"[TOLERANCE] 0% violation: {fee_name} increased ${difference:.2f}")
    
    # Check Section B fees (10% tolerance in aggregate)
    for fee_id, fee_name in SECTION_B_FEES.items():
        le_amount = le_fees.get(fee_id, 0.0) or 0.0
        cd_amount = cd_fees.get(fee_id, 0.0) or 0.0
        
        section_b_le_total += le_amount
        section_b_cd_total += cd_amount
    
    # Calculate 10% tolerance violation
    section_b_increase = section_b_cd_total - section_b_le_total
    section_b_allowed = section_b_le_total * 0.10 if section_b_using_spl else 0.0
    
    if section_b_increase > section_b_allowed:
        violation_amount = section_b_increase - section_b_allowed
        total_cure += violation_amount
        
        # Add violation for the aggregate
        ten_violations.append(ToleranceViolation(
            fee_id="SECTION_B_AGGREGATE",
            fee_name="Section B Aggregate",
            le_amount=section_b_le_total,
            cd_amount=section_b_cd_total,
            difference=section_b_increase,
            tolerance_type="ten_percent",
            violation_amount=violation_amount,
            section="B",
        ))
        logger.warning(f"[TOLERANCE] 10% violation: Section B exceeded by ${violation_amount:.2f}")
    
    has_violations = len(zero_violations) > 0 or len(ten_violations) > 0
    
    result = ToleranceResult(
        has_violations=has_violations,
        total_cure_needed=round(total_cure, 2),
        zero_tolerance_violations=zero_violations,
        ten_percent_violations=ten_violations,
        section_b_total_le=round(section_b_le_total, 2),
        section_b_total_cd=round(section_b_cd_total, 2),
        section_b_increase=round(section_b_increase, 2),
        section_b_allowed_increase=round(section_b_allowed, 2),
    )
    
    logger.info(f"[TOLERANCE] Check complete: {len(zero_violations)} zero-tolerance, "
                f"{len(ten_violations)} ten-percent violations, cure=${total_cure:.2f}")
    
    return result


def check_single_fee_tolerance(
    fee_id: str,
    le_amount: float,
    cd_amount: float,
) -> Dict[str, Any]:
    """Check tolerance for a single fee.
    
    Args:
        fee_id: Encompass fee field ID
        le_amount: LE amount for this fee
        cd_amount: CD amount for this fee
        
    Returns:
        Dictionary with tolerance check result
    """
    # Determine which section this fee belongs to
    if fee_id in SECTION_A_FEES:
        section = "A"
        tolerance_type = "zero"
        allowed_increase = 0.0
    elif fee_id in SECTION_B_FEES:
        section = "B"
        tolerance_type = "ten_percent"
        allowed_increase = le_amount * 0.10
    else:
        section = "C"
        tolerance_type = "none"
        allowed_increase = float("inf")  # No tolerance protection
    
    difference = cd_amount - le_amount
    is_violation = difference > allowed_increase
    violation_amount = max(0, difference - allowed_increase)
    
    return {
        "fee_id": fee_id,
        "section": section,
        "tolerance_type": tolerance_type,
        "le_amount": le_amount,
        "cd_amount": cd_amount,
        "difference": difference,
        "allowed_increase": allowed_increase,
        "is_violation": is_violation,
        "violation_amount": violation_amount,
    }


# =============================================================================
# FEE EXTRACTION HELPERS
# =============================================================================

def extract_fees_from_fields(
    field_values: Dict[str, Any],
    fee_field_ids: List[str],
) -> Dict[str, float]:
    """Extract fee values from field values dictionary.
    
    Args:
        field_values: Dictionary of field values
        fee_field_ids: List of fee field IDs to extract
        
    Returns:
        Dictionary mapping fee_id to float amount
    """
    fees = {}
    
    for fee_id in fee_field_ids:
        value = field_values.get(fee_id)
        if value is not None:
            try:
                # Clean and parse the value
                if isinstance(value, (int, float)):
                    fees[fee_id] = float(value)
                else:
                    cleaned = str(value).replace(",", "").replace("$", "").strip()
                    if cleaned:
                        fees[fee_id] = float(cleaned)
            except (ValueError, TypeError):
                logger.warning(f"[TOLERANCE] Could not parse fee value for {fee_id}: {value}")
    
    return fees


def get_all_fee_field_ids() -> List[str]:
    """Get all fee field IDs that should be checked.
    
    Returns:
        List of all fee field IDs
    """
    return list(SECTION_A_FEES.keys()) + list(SECTION_B_FEES.keys()) + list(SECTION_C_FEES.keys())

