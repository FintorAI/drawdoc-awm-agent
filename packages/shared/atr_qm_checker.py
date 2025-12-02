"""ATR/QM Checker for Disclosure Agent.

Per Disclosure Desk SOP:
- Go to Forms → ATR/QM Management → Qualification → Points and Fees
- ATR/QM Eligibility: Flags must NOT be RED to proceed
- Flags for Loan Features, Points and Fees Limit, and Price Limit should be GREEN
- This is MANDATORY before ordering disclosures
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .encompass_io import read_fields

logger = logging.getLogger(__name__)


# =============================================================================
# ENCOMPASS FIELD IDS FOR ATR/QM
# =============================================================================

class ATRQMFields:
    """Encompass field IDs for ATR/QM Management."""
    
    # ATR/QM Qualification flags
    LOAN_FEATURES_FLAG = "ATRQM.X1"  # Loan Features Flag
    POINTS_FEES_FLAG = "ATRQM.X2"  # Points and Fees Limit Flag
    PRICE_LIMIT_FLAG = "ATRQM.X3"  # Price Limit Flag
    
    # ATR/QM eligibility
    ATR_QM_ELIGIBILITY = "ATRQM.X4"  # Overall ATR/QM Eligibility
    
    # Points and Fees Test
    POINTS_FEES_LIMIT = "ATRQM.X10"  # Points & Fees Limit Amount
    POINTS_FEES_ACTUAL = "ATRQM.X11"  # Actual Points & Fees
    POINTS_FEES_TEST_RESULT = "ATRQM.X12"  # Points & Fees Test Result
    
    # QM Type
    QM_TYPE = "ATRQM.X20"  # QM Type (General, Safe Harbor, etc.)


# =============================================================================
# FLAG STATUS VALUES
# =============================================================================

class FlagStatus:
    """Possible flag status values."""
    
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"
    UNKNOWN = "UNKNOWN"
    
    @classmethod
    def parse(cls, value: Any) -> str:
        """Parse a flag value to status."""
        if value is None:
            return cls.UNKNOWN
        
        value_str = str(value).upper().strip()
        
        if value_str in ["GREEN", "PASS", "OK", "Y", "YES"]:
            return cls.GREEN
        elif value_str in ["YELLOW", "CAUTION", "WARN"]:
            return cls.YELLOW
        elif value_str in ["RED", "FAIL", "NO", "N"]:
            return cls.RED
        
        return cls.UNKNOWN


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ATRQMResult:
    """Result of ATR/QM check."""
    
    passed: bool
    loan_features_flag: str
    points_fees_flag: str
    price_limit_flag: str
    red_flags: List[str] = field(default_factory=list)
    yellow_flags: List[str] = field(default_factory=list)
    qm_type: Optional[str] = None
    points_fees_limit: Optional[float] = None
    points_fees_actual: Optional[float] = None
    action: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "passed": self.passed,
            "loan_features_flag": self.loan_features_flag,
            "points_fees_flag": self.points_fees_flag,
            "price_limit_flag": self.price_limit_flag,
            "red_flags": self.red_flags,
            "yellow_flags": self.yellow_flags,
            "qm_type": self.qm_type,
            "points_fees_limit": self.points_fees_limit,
            "points_fees_actual": self.points_fees_actual,
            "action": self.action,
            "blocking": not self.passed,
        }


# =============================================================================
# ATR/QM CHECKER CLASS
# =============================================================================

class ATRQMChecker:
    """Checks ATR/QM flags for loans."""
    
    def check(self, loan_id: str) -> ATRQMResult:
        """Check ATR/QM flags for a loan.
        
        Per SOP:
        - All flags must NOT be RED to proceed
        - Loan Features, Points and Fees Limit, Price Limit should be GREEN
        
        Args:
            loan_id: Encompass loan GUID
            
        Returns:
            ATRQMResult with flag status
        """
        logger.info(f"[ATR/QM] Checking flags for loan {loan_id[:8]}...")
        
        # Read ATR/QM fields
        field_ids = [
            ATRQMFields.LOAN_FEATURES_FLAG,
            ATRQMFields.POINTS_FEES_FLAG,
            ATRQMFields.PRICE_LIMIT_FLAG,
            ATRQMFields.QM_TYPE,
            ATRQMFields.POINTS_FEES_LIMIT,
            ATRQMFields.POINTS_FEES_ACTUAL,
        ]
        
        values = read_fields(loan_id, field_ids)
        
        # Parse flag statuses
        loan_features = FlagStatus.parse(values.get(ATRQMFields.LOAN_FEATURES_FLAG))
        points_fees = FlagStatus.parse(values.get(ATRQMFields.POINTS_FEES_FLAG))
        price_limit = FlagStatus.parse(values.get(ATRQMFields.PRICE_LIMIT_FLAG))
        
        logger.info(f"[ATR/QM] Flags - Loan Features: {loan_features}, "
                   f"Points/Fees: {points_fees}, Price Limit: {price_limit}")
        
        # Collect red and yellow flags
        red_flags = []
        yellow_flags = []
        
        flags = {
            "Loan Features": loan_features,
            "Points and Fees": points_fees,
            "Price Limit": price_limit,
        }
        
        for flag_name, status in flags.items():
            if status == FlagStatus.RED:
                red_flags.append(flag_name)
            elif status == FlagStatus.YELLOW:
                yellow_flags.append(flag_name)
        
        # Determine pass/fail
        if red_flags:
            passed = False
            action = f"ATR/QM RED flags: {', '.join(red_flags)} - BLOCKING"
            logger.warning(f"[ATR/QM] {action}")
        elif yellow_flags:
            # Yellow flags are a warning but may not block
            passed = True
            action = f"ATR/QM YELLOW flags: {', '.join(yellow_flags)} - Review recommended"
            logger.info(f"[ATR/QM] {action}")
        else:
            passed = True
            action = None
            logger.info("[ATR/QM] All flags GREEN - PASSED")
        
        # Parse points/fees values
        points_fees_limit = self._parse_currency(values.get(ATRQMFields.POINTS_FEES_LIMIT))
        points_fees_actual = self._parse_currency(values.get(ATRQMFields.POINTS_FEES_ACTUAL))
        
        return ATRQMResult(
            passed=passed,
            loan_features_flag=loan_features,
            points_fees_flag=points_fees,
            price_limit_flag=price_limit,
            red_flags=red_flags,
            yellow_flags=yellow_flags,
            qm_type=values.get(ATRQMFields.QM_TYPE),
            points_fees_limit=points_fees_limit,
            points_fees_actual=points_fees_actual,
            action=action
        )
    
    def _parse_currency(self, value: Any) -> Optional[float]:
        """Parse a currency value."""
        if value is None:
            return None
        
        try:
            value_str = str(value).replace("$", "").replace(",", "").strip()
            if not value_str:
                return None
            return float(value_str)
        except (ValueError, TypeError):
            return None


# =============================================================================
# MODULE-LEVEL FUNCTIONS
# =============================================================================

# Singleton instance
_checker: Optional[ATRQMChecker] = None


def get_atr_qm_checker() -> ATRQMChecker:
    """Get the ATR/QM checker singleton."""
    global _checker
    if _checker is None:
        _checker = ATRQMChecker()
    return _checker


def check_atr_qm_flags(loan_id: str) -> Dict[str, Any]:
    """Check ATR/QM flags for a loan.
    
    Convenience function that returns a dictionary.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with flag status
    """
    checker = get_atr_qm_checker()
    result = checker.check(loan_id)
    return result.to_dict()


def get_points_fees_status(loan_id: str) -> Dict[str, Any]:
    """Get Points & Fees test status.
    
    Convenience function.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with points/fees info
    """
    checker = get_atr_qm_checker()
    result = checker.check(loan_id)
    
    return {
        "flag": result.points_fees_flag,
        "limit": result.points_fees_limit,
        "actual": result.points_fees_actual,
        "passed": result.points_fees_flag != FlagStatus.RED,
    }

