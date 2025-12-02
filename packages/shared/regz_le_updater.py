"""RegZ-LE Form Updater for Disclosure Agent.

Per Disclosure Desk SOP, updates the following on RegZ-LE form:
- LE Date Issued = Current/Present Date
- Interest Accrual = 360/360
- Late Charge: Conventional 15d/5%, FHA/VA 15d/4%, NC 4% all
- Assumption: Conventional "may not", FHA/VA "may, subject to conditions"
- Buydown fields (if marked)
- Prepayment penalty fields
"""

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

from .encompass_io import read_field, read_fields, write_fields

logger = logging.getLogger(__name__)


# =============================================================================
# ENCOMPASS FIELD IDS FOR REGZ-LE
# =============================================================================

class RegZLEFields:
    """Encompass field IDs for RegZ-LE form."""
    
    # LE Date
    LE_DATE_ISSUED = "LE1.X1"
    
    # Interest Accrual
    INTEREST_DAYS_PER_YEAR = "1176"  # Days in Year
    ZERO_PERCENT_PAYMENT_OPTION = "3514"  # 0% Payment Option
    USE_SIMPLE_INTEREST = "3515"  # Use Simple Interest Accrual
    BIWEEKLY_INTERIM_DAYS = "3516"  # Biweekly/Interim Days
    
    # Late Charge
    LATE_CHARGE_DAYS = "672"  # Late Charge Grace Period
    LATE_CHARGE_PERCENT = "674"  # Late Charge Percentage (fixed: was 673)
    
    # Assumption
    ASSUMPTION_TEXT = "3517"  # Assumption clause
    
    # Buydown
    BUYDOWN_MARKED = "1751"  # Is Buydown marked
    BUYDOWN_CONTRIBUTOR = "1755"  # Buydown Contributor
    BUYDOWN_TYPE = "1753"  # Buydown Type
    BUYDOWN_RATE = "1754"  # Buydown Rate %
    BUYDOWN_TERM = "1756"  # Buydown Term
    BUYDOWN_FUNDS = "1757"  # Buydown Funds Amount
    
    # Prepayment
    PREPAY_INDICATOR = "664"  # Prepayment Penalty Indicator
    PREPAY_TYPE = "1762"  # Type of Prepay
    PREPAY_PERIOD = "1763"  # Prepayment Period
    PREPAY_PERCENT = "1764"  # Prepayment as %
    
    # Loan metadata
    LOAN_TYPE = "1172"  # Loan Type
    PROPERTY_STATE = "14"  # Property State


# =============================================================================
# LATE CHARGE RULES BY LOAN TYPE AND STATE
# =============================================================================

# Default late charge rules by loan type
LATE_CHARGE_RULES = {
    "Conventional": {"days": 15, "percent": 5.0},
    "FHA": {"days": 15, "percent": 4.0},
    "VA": {"days": 15, "percent": 4.0},
    "USDA": {"days": 15, "percent": 4.0},
}

# State overrides (e.g., North Carolina has 4% for all loan types)
STATE_LATE_CHARGE_OVERRIDES = {
    "NC": {"percent": 4.0},  # North Carolina: 4% for all loan types
}


# =============================================================================
# ASSUMPTION TEXT BY LOAN TYPE
# =============================================================================

ASSUMPTION_TEXT = {
    "Conventional": "may not",
    "FHA": "may, subject to conditions",
    "VA": "may, subject to conditions",
    "USDA": "may, subject to conditions",
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class RegZLEUpdateResult:
    """Result of RegZ-LE form update."""
    
    success: bool
    updates_made: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "updates_made": self.updates_made,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# =============================================================================
# REGZ-LE UPDATER CLASS
# =============================================================================

class RegZLEUpdater:
    """Updates RegZ-LE form fields per SOP requirements."""
    
    def update(self, loan_id: str, dry_run: bool = True) -> RegZLEUpdateResult:
        """Update RegZ-LE form with SOP-required values.
        
        Args:
            loan_id: Encompass loan GUID
            dry_run: If True, only calculate updates without writing
            
        Returns:
            RegZLEUpdateResult with update details
        """
        logger.info(f"[REGZ-LE] Updating form for loan {loan_id[:8]}...")
        
        updates = {}
        errors = []
        warnings = []
        
        # Get loan metadata
        loan_type = self._get_loan_type(loan_id)
        property_state = self._get_property_state(loan_id)
        
        logger.info(f"[REGZ-LE] Loan type: {loan_type}, State: {property_state}")
        
        # 1. LE Date Issued = Current Date
        updates[RegZLEFields.LE_DATE_ISSUED] = date.today().strftime("%m/%d/%Y")
        
        # 2. Interest Accrual Options
        interest_updates = self._get_interest_accrual_updates()
        updates.update(interest_updates)
        
        # 3. Late Charge
        late_days, late_pct = self._get_late_charge(loan_type, property_state)
        updates[RegZLEFields.LATE_CHARGE_DAYS] = late_days
        updates[RegZLEFields.LATE_CHARGE_PERCENT] = late_pct
        
        # 4. Assumption
        assumption_text = self._get_assumption_text(loan_type)
        updates[RegZLEFields.ASSUMPTION_TEXT] = assumption_text
        
        # 5. Handle Buydown if marked
        buydown_result = self._handle_buydown(loan_id)
        if buydown_result.get("has_buydown"):
            updates.update(buydown_result.get("updates", {}))
            warnings.extend(buydown_result.get("warnings", []))
        
        # 6. Handle Prepayment
        prepay_result = self._handle_prepayment(loan_id)
        if prepay_result.get("updates"):
            updates.update(prepay_result.get("updates", {}))
        
        # Write updates
        if dry_run:
            logger.info(f"[REGZ-LE] [DRY RUN] Would update {len(updates)} fields")
            success = True
        else:
            success = write_fields(loan_id, updates, dry_run=False)
            if not success:
                errors.append("Failed to write updates to Encompass")
        
        return RegZLEUpdateResult(
            success=success and len(errors) == 0,
            updates_made=updates,
            errors=errors,
            warnings=warnings
        )
    
    def _get_interest_accrual_updates(self) -> Dict[str, Any]:
        """Get interest accrual field updates.
        
        Per SOP:
        - 0% Payment Option: blank
        - Interest Days/Days in Year: 360/360
        - Use Simple Interest Accrual: blank
        - Number of Days (Biweekly): 365
        """
        return {
            RegZLEFields.INTEREST_DAYS_PER_YEAR: "360",
            RegZLEFields.ZERO_PERCENT_PAYMENT_OPTION: "",
            RegZLEFields.USE_SIMPLE_INTEREST: "",
            RegZLEFields.BIWEEKLY_INTERIM_DAYS: "365",
        }
    
    def _get_late_charge(self, loan_type: str, property_state: str) -> tuple:
        """Get late charge days and percentage.
        
        Per SOP:
        - Conventional: 15 Days, 5%
        - FHA/VA: 15 Days, 4%
        - North Carolina: 4% for ALL loan types
        
        Args:
            loan_type: Loan type (Conventional, FHA, VA, USDA)
            property_state: State abbreviation
            
        Returns:
            Tuple of (days, percentage)
        """
        # Get base rule
        rule = LATE_CHARGE_RULES.get(loan_type, LATE_CHARGE_RULES["Conventional"])
        days = rule["days"]
        percent = rule["percent"]
        
        # Apply state overrides
        if property_state and property_state.upper() in STATE_LATE_CHARGE_OVERRIDES:
            override = STATE_LATE_CHARGE_OVERRIDES[property_state.upper()]
            if "percent" in override:
                percent = override["percent"]
            if "days" in override:
                days = override["days"]
        
        logger.info(f"[REGZ-LE] Late charge: {days} days, {percent}%")
        return (days, percent)
    
    def _get_assumption_text(self, loan_type: str) -> str:
        """Get assumption text for loan type.
        
        Per SOP:
        - Conventional: "may not"
        - FHA/VA: "may, subject to conditions"
        
        Args:
            loan_type: Loan type
            
        Returns:
            Assumption text
        """
        return ASSUMPTION_TEXT.get(loan_type, ASSUMPTION_TEXT["Conventional"])
    
    def _handle_buydown(self, loan_id: str) -> Dict[str, Any]:
        """Handle buydown fields if buydown is marked.
        
        Per SOP: If buydown is marked, ensure these fields are updated:
        - Contributor
        - Buydown Type
        - Rate %
        - Term
        
        Args:
            loan_id: Encompass loan GUID
            
        Returns:
            Dictionary with has_buydown flag, updates, and warnings
        """
        result = {
            "has_buydown": False,
            "updates": {},
            "warnings": []
        }
        
        # Check if buydown is marked
        buydown_marked = read_field(loan_id, RegZLEFields.BUYDOWN_MARKED)
        
        if not buydown_marked or str(buydown_marked).lower() not in ["y", "yes", "true", "1"]:
            return result
        
        result["has_buydown"] = True
        logger.info("[REGZ-LE] Buydown is marked - checking fields")
        
        # Read buydown fields
        buydown_fields = [
            RegZLEFields.BUYDOWN_CONTRIBUTOR,
            RegZLEFields.BUYDOWN_TYPE,
            RegZLEFields.BUYDOWN_RATE,
            RegZLEFields.BUYDOWN_TERM,
            RegZLEFields.BUYDOWN_FUNDS,
        ]
        
        values = read_fields(loan_id, buydown_fields)
        
        # Check for missing required fields
        missing = []
        if not values.get(RegZLEFields.BUYDOWN_CONTRIBUTOR):
            missing.append("Buydown Contributor")
        if not values.get(RegZLEFields.BUYDOWN_TYPE):
            missing.append("Buydown Type")
        if not values.get(RegZLEFields.BUYDOWN_RATE):
            missing.append("Buydown Rate")
        if not values.get(RegZLEFields.BUYDOWN_TERM):
            missing.append("Buydown Term")
        
        if missing:
            result["warnings"].append(f"Buydown marked but missing: {', '.join(missing)}")
        
        return result
    
    def _handle_prepayment(self, loan_id: str) -> Dict[str, Any]:
        """Handle prepayment penalty fields.
        
        Per SOP:
        - If Prepayment is "Will not, May not": proceed as-is
        - If Prepayment is "Will, May, May be": update penalty fields
        
        Args:
            loan_id: Encompass loan GUID
            
        Returns:
            Dictionary with updates (if any)
        """
        result = {"updates": {}}
        
        # Check prepayment indicator
        prepay_indicator = read_field(loan_id, RegZLEFields.PREPAY_INDICATOR)
        
        if not prepay_indicator:
            return result
        
        indicator_str = str(prepay_indicator).lower()
        
        # If "will not" or "may not", no action needed
        if "will not" in indicator_str or "may not" in indicator_str:
            logger.info("[REGZ-LE] Prepayment: Will not/May not - no action needed")
            return result
        
        # If "will", "may", or "may be", check penalty fields are populated
        if any(x in indicator_str for x in ["will", "may"]):
            logger.info("[REGZ-LE] Prepayment penalty indicated - checking fields")
            
            prepay_fields = [
                RegZLEFields.PREPAY_TYPE,
                RegZLEFields.PREPAY_PERIOD,
                RegZLEFields.PREPAY_PERCENT,
            ]
            
            values = read_fields(loan_id, prepay_fields)
            
            # Log any missing fields (we don't auto-populate these)
            missing = []
            if not values.get(RegZLEFields.PREPAY_TYPE):
                missing.append("Prepay Type")
            if not values.get(RegZLEFields.PREPAY_PERIOD):
                missing.append("Prepay Period")
            if not values.get(RegZLEFields.PREPAY_PERCENT):
                missing.append("Prepay Percent")
            
            if missing:
                logger.warning(f"[REGZ-LE] Prepayment penalty fields missing: {missing}")
        
        return result
    
    def _get_loan_type(self, loan_id: str) -> str:
        """Get loan type from Encompass."""
        value = read_field(loan_id, RegZLEFields.LOAN_TYPE)
        
        if value is None:
            return "Conventional"  # Default
        
        value_str = str(value).strip().lower()
        
        if "conventional" in value_str or "conv" in value_str:
            return "Conventional"
        elif "fha" in value_str:
            return "FHA"
        elif "va" in value_str:
            return "VA"
        elif "usda" in value_str:
            return "USDA"
        
        return "Conventional"
    
    def _get_property_state(self, loan_id: str) -> str:
        """Get property state from Encompass."""
        value = read_field(loan_id, RegZLEFields.PROPERTY_STATE)
        
        if value is None:
            return ""
        
        return str(value).strip().upper()


# =============================================================================
# MODULE-LEVEL FUNCTIONS
# =============================================================================

# Singleton instance
_updater: Optional[RegZLEUpdater] = None


def get_regz_le_updater() -> RegZLEUpdater:
    """Get the RegZ-LE updater singleton."""
    global _updater
    if _updater is None:
        _updater = RegZLEUpdater()
    return _updater


def update_regz_le_form(loan_id: str, dry_run: bool = True) -> Dict[str, Any]:
    """Update RegZ-LE form with SOP-required values.
    
    Convenience function that returns a dictionary.
    
    Args:
        loan_id: Encompass loan GUID
        dry_run: If True, only calculate updates without writing
        
    Returns:
        Dictionary with update results
    """
    updater = get_regz_le_updater()
    result = updater.update(loan_id, dry_run=dry_run)
    return result.to_dict()


def get_late_charge(loan_type: str, property_state: str = "") -> Dict[str, Any]:
    """Get late charge values for a loan type and state.
    
    Convenience function.
    
    Args:
        loan_type: Loan type (Conventional, FHA, VA, USDA)
        property_state: State abbreviation
        
    Returns:
        Dictionary with days and percentage
    """
    updater = get_regz_le_updater()
    days, percent = updater._get_late_charge(loan_type, property_state)
    return {"days": days, "percent": percent}


def get_assumption_text(loan_type: str) -> str:
    """Get assumption text for a loan type.
    
    Convenience function.
    
    Args:
        loan_type: Loan type
        
    Returns:
        Assumption text
    """
    return ASSUMPTION_TEXT.get(loan_type, ASSUMPTION_TEXT["Conventional"])

