"""Cash to Close Matcher for Disclosure Agent.

Per Disclosure Desk SOP:
- CTC (Cash to Close) must be matched with the Estimated Cash to Close on LE page 2
- For Purchase: Check 'Use Actual Down Payment & Closing Costs Financed' & 'Include Payoffs in Adjustments'
- For Refinance: Check 'Alternative form checkbox' on all refinance transactions
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .encompass_io import read_field, read_fields, write_fields

logger = logging.getLogger(__name__)


# =============================================================================
# ENCOMPASS FIELD IDS FOR CASH TO CLOSE
# =============================================================================

class CTCFields:
    """Encompass field IDs for Cash to Close matching."""
    
    # Loan Purpose
    LOAN_PURPOSE = "19"
    
    # Purchase CTC Settings
    USE_ACTUAL_DOWN_PAYMENT = "NEWHUD2.X55"  # Use Actual Down Payment
    CLOSING_COSTS_FINANCED = "NEWHUD2.X56"  # Closing Costs Financed
    INCLUDE_PAYOFFS_IN_ADJUSTMENTS = "NEWHUD2.X57"  # Include Payoffs in Adjustments
    
    # Refinance CTC Settings
    ALTERNATIVE_FORM_CHECKBOX = "NEWHUD2.X58"  # Alternative Form (for Refinance)
    
    # CTC Values
    CALCULATED_CTC = "NEWHUD2.X59"  # Calculated Cash to Close
    DISPLAYED_CTC = "LE1.X77"  # Displayed CTC on LE Page 2
    ESTIMATED_CTC = "CD3.X105"  # Estimated Cash to Close
    
    # Section M fields
    EMD_DEPOSIT = "1394"  # Earnest Money Deposit (Line M2/M3)
    GENERAL_LENDER_CREDIT = "1395"  # General Lender Credit (Line M4)
    SELLER_CREDIT = "1396"  # Seller Credit (Line M5/M6)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CTCResult:
    """Result of Cash to Close matching."""
    
    success: bool
    matched: bool
    loan_purpose: str
    calculated_ctc: Optional[float] = None
    displayed_ctc: Optional[float] = None
    difference: Optional[float] = None
    updates_made: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "matched": self.matched,
            "loan_purpose": self.loan_purpose,
            "calculated_ctc": self.calculated_ctc,
            "displayed_ctc": self.displayed_ctc,
            "difference": self.difference,
            "updates_made": self.updates_made,
            "errors": self.errors,
            "warnings": self.warnings,
            "blocking": not self.success or not self.matched,
        }


# =============================================================================
# CTC MATCHER CLASS
# =============================================================================

class CTCMatcher:
    """Matches Cash to Close per SOP requirements."""
    
    # Tolerance for CTC match (allow penny rounding)
    MATCH_TOLERANCE = 0.01
    
    def match_cash_to_close(self, loan_id: str, dry_run: bool = True) -> CTCResult:
        """Apply CTC settings and verify match.
        
        Per SOP:
        - Purchase: Check specific boxes
        - Refinance: Check Alternative form checkbox
        - Verify calculated CTC matches displayed CTC
        
        Args:
            loan_id: Encompass loan GUID
            dry_run: If True, only calculate without writing
            
        Returns:
            CTCResult with match status
        """
        logger.info(f"[CTC] Matching Cash to Close for loan {loan_id[:8]}...")
        
        errors = []
        warnings = []
        
        # Get loan purpose
        loan_purpose = self._get_loan_purpose(loan_id)
        logger.info(f"[CTC] Loan purpose: {loan_purpose}")
        
        # Get settings based on purpose
        updates = self._get_ctc_settings(loan_purpose)
        
        # Apply updates
        if dry_run:
            logger.info(f"[CTC] [DRY RUN] Would update {len(updates)} fields")
        else:
            success = write_fields(loan_id, updates, dry_run=False)
            if not success:
                errors.append("Failed to write CTC settings to Encompass")
        
        # Verify match
        calculated = self._get_calculated_ctc(loan_id)
        displayed = self._get_displayed_ctc(loan_id)
        
        if calculated is None:
            warnings.append("Calculated CTC not available")
        if displayed is None:
            warnings.append("Displayed CTC not available")
        
        # Check match
        matched = False
        difference = None
        
        if calculated is not None and displayed is not None:
            difference = abs(calculated - displayed)
            matched = difference <= self.MATCH_TOLERANCE
            
            # Safely format values
            calc_str = f"${calculated:,.2f}" if isinstance(calculated, (int, float)) else str(calculated)
            disp_str = f"${displayed:,.2f}" if isinstance(displayed, (int, float)) else str(displayed)
            diff_str = f"${difference:.2f}" if isinstance(difference, (int, float)) else str(difference)
            
            if matched:
                logger.info(f"[CTC] Match verified: {calc_str}")
            else:
                msg = f"CTC mismatch: Calculated={calc_str}, Displayed={disp_str}, Diff={diff_str}"
                logger.warning(f"[CTC] {msg}")
                warnings.append(msg)
        else:
            # Can't verify match without both values
            warnings.append("Cannot verify CTC match - missing values")
        
        return CTCResult(
            success=len(errors) == 0,
            matched=matched,
            loan_purpose=loan_purpose,
            calculated_ctc=calculated,
            displayed_ctc=displayed,
            difference=difference,
            updates_made=updates,
            errors=errors,
            warnings=warnings
        )
    
    def _get_ctc_settings(self, loan_purpose: str) -> Dict[str, Any]:
        """Get CTC field settings based on loan purpose.
        
        Per SOP:
        - Purchase: Check 'Use Actual Down Payment & Closing Costs Financed'
                   & 'Include Payoffs in Adjustments and Credits'
        - Refinance: Check 'Alternative form checkbox'
        
        Args:
            loan_purpose: Loan purpose (Purchase, Refinance, etc.)
            
        Returns:
            Dictionary of field updates
        """
        purpose_lower = loan_purpose.lower()
        
        if "purchase" in purpose_lower:
            logger.info("[CTC] Applying Purchase CTC settings")
            return {
                CTCFields.USE_ACTUAL_DOWN_PAYMENT: "Y",
                CTCFields.CLOSING_COSTS_FINANCED: "Y",
                CTCFields.INCLUDE_PAYOFFS_IN_ADJUSTMENTS: "Y",
            }
        
        elif any(x in purpose_lower for x in ["refinance", "refi", "cashout"]):
            logger.info("[CTC] Applying Refinance CTC settings")
            return {
                CTCFields.ALTERNATIVE_FORM_CHECKBOX: "Y",
            }
        
        else:
            logger.warning(f"[CTC] Unknown loan purpose: {loan_purpose}")
            return {}
    
    def _get_loan_purpose(self, loan_id: str) -> str:
        """Get loan purpose from Encompass."""
        value = read_field(loan_id, CTCFields.LOAN_PURPOSE)
        
        if value is None:
            return "Unknown"
        
        value_str = str(value).strip().lower()
        
        if "purchase" in value_str:
            return "Purchase"
        elif "refinance" in value_str or "refi" in value_str:
            if "cash" in value_str:
                return "CashOut Refinance"
            return "Refinance"
        elif "construction" in value_str:
            return "Construction"
        
        return value_str.title() if value_str else "Unknown"
    
    def _get_calculated_ctc(self, loan_id: str) -> Optional[float]:
        """Get calculated Cash to Close value."""
        value = read_field(loan_id, CTCFields.CALCULATED_CTC)
        return self._parse_currency(value)
    
    def _get_displayed_ctc(self, loan_id: str) -> Optional[float]:
        """Get displayed Cash to Close value from LE page 2."""
        value = read_field(loan_id, CTCFields.DISPLAYED_CTC)
        return self._parse_currency(value)
    
    def _parse_currency(self, value: Any) -> Optional[float]:
        """Parse a currency value."""
        if value is None:
            return None
        
        try:
            # Remove currency formatting
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
_matcher: Optional[CTCMatcher] = None


def get_ctc_matcher() -> CTCMatcher:
    """Get the CTC matcher singleton."""
    global _matcher
    if _matcher is None:
        _matcher = CTCMatcher()
    return _matcher


def match_cash_to_close(loan_id: str, dry_run: bool = True) -> Dict[str, Any]:
    """Match Cash to Close for a loan.
    
    Convenience function that returns a dictionary.
    
    Args:
        loan_id: Encompass loan GUID
        dry_run: If True, only calculate without writing
        
    Returns:
        Dictionary with CTC match results
    """
    matcher = get_ctc_matcher()
    result = matcher.match_cash_to_close(loan_id, dry_run=dry_run)
    return result.to_dict()


def get_ctc_settings(loan_purpose: str) -> Dict[str, Any]:
    """Get CTC settings for a loan purpose.
    
    Convenience function.
    
    Args:
        loan_purpose: Loan purpose (Purchase, Refinance, etc.)
        
    Returns:
        Dictionary of field settings
    """
    matcher = get_ctc_matcher()
    return matcher._get_ctc_settings(loan_purpose)

