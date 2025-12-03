"""TRID Compliance Checker for Disclosure Agent.

Per Disclosure Desk SOP:
- LE must be sent within 3 business days of Application Date
- "Send Initial Disclosures" alert must exist under Alerts & Messages
- Business days exclude Sundays and federal holidays
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from .encompass_io import read_field, read_fields

logger = logging.getLogger(__name__)


# =============================================================================
# ENCOMPASS FIELD IDS FOR TRID
# =============================================================================

# Application/Disclosure dates
APPLICATION_DATE_FIELD = "745"  # Application Date
LE_DATE_ISSUED_FIELD = "LE1.X1"  # LE Date Issued
DISCLOSURE_SENT_DATE_FIELD = "3152"  # Disclosure Sent Date

# Lock fields
LOCK_DATE_FIELD = "761"  # Lock Date
LOCK_EXPIRATION_FIELD = "432"  # Lock Expiration Date
RATE_LOCKED_FIELD = "2400"  # Rate Locked indicator
LAST_RATE_SET_DATE_FIELD = "3152"  # Last Rate Set Date

# Closing Date field
CLOSING_DATE_FIELD = "748"  # Estimated Closing Date

# G8: Minimum days for closing date
MINIMUM_CLOSING_DAYS = 15  # Per SOP: Closing date must be at least 15 days after app/rate date


# =============================================================================
# FEDERAL HOLIDAYS (US)
# =============================================================================

def get_federal_holidays(year: int) -> List[date]:
    """Get list of federal holidays for a given year.
    
    These are the holidays that Encompass excludes from business day calculations.
    """
    holidays = []
    
    # New Year's Day - January 1
    holidays.append(_observed_date(date(year, 1, 1)))
    
    # MLK Day - Third Monday in January
    holidays.append(_nth_weekday(year, 1, 0, 3))  # 0=Monday, 3rd occurrence
    
    # Presidents Day - Third Monday in February
    holidays.append(_nth_weekday(year, 2, 0, 3))
    
    # Memorial Day - Last Monday in May
    holidays.append(_last_weekday(year, 5, 0))
    
    # Juneteenth - June 19
    holidays.append(_observed_date(date(year, 6, 19)))
    
    # Independence Day - July 4
    holidays.append(_observed_date(date(year, 7, 4)))
    
    # Labor Day - First Monday in September
    holidays.append(_nth_weekday(year, 9, 0, 1))
    
    # Columbus Day - Second Monday in October
    holidays.append(_nth_weekday(year, 10, 0, 2))
    
    # Veterans Day - November 11
    holidays.append(_observed_date(date(year, 11, 11)))
    
    # Thanksgiving - Fourth Thursday in November
    holidays.append(_nth_weekday(year, 11, 3, 4))  # 3=Thursday
    
    # Christmas - December 25
    holidays.append(_observed_date(date(year, 12, 25)))
    
    return holidays


def _observed_date(d: date) -> date:
    """Get observed date for a holiday (shift if on weekend)."""
    if d.weekday() == 5:  # Saturday
        return d - timedelta(days=1)
    elif d.weekday() == 6:  # Sunday
        return d + timedelta(days=1)
    return d


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Get the nth occurrence of a weekday in a month."""
    first_day = date(year, month, 1)
    first_weekday = first_day + timedelta(days=(weekday - first_day.weekday()) % 7)
    return first_weekday + timedelta(weeks=n - 1)


def _last_weekday(year: int, month: int, weekday: int) -> date:
    """Get the last occurrence of a weekday in a month."""
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    last_day = next_month - timedelta(days=1)
    days_back = (last_day.weekday() - weekday) % 7
    return last_day - timedelta(days=days_back)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TRIDResult:
    """Result of TRID compliance check."""
    
    compliant: bool
    application_date: Optional[date]
    le_due_date: Optional[date]
    days_remaining: int
    is_past_due: bool = False
    action: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "compliant": self.compliant,
            "application_date": self.application_date.isoformat() if self.application_date else None,
            "le_due_date": self.le_due_date.isoformat() if self.le_due_date else None,
            "days_remaining": self.days_remaining,
            "is_past_due": self.is_past_due,
            "action": self.action,
            "blocking": not self.compliant,
        }


@dataclass
class LockStatusResult:
    """Result of lock status check."""
    
    is_locked: bool
    lock_date: Optional[date] = None
    lock_expiration: Optional[date] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_locked": self.is_locked,
            "lock_date": self.lock_date.isoformat() if self.lock_date else None,
            "lock_expiration": self.lock_expiration.isoformat() if self.lock_expiration else None,
        }


@dataclass
class ClosingDateResult:
    """Result of closing date validation (G8).
    
    Per SOP: Closing date must be at least 15 days after:
    - Application date (if unlocked)
    - Last rate set date (if locked)
    """
    
    is_valid: bool
    closing_date: Optional[date] = None
    reference_date: Optional[date] = None
    reference_type: str = "application_date"  # or "last_rate_set_date"
    days_until_closing: int = 0
    minimum_days: int = MINIMUM_CLOSING_DAYS
    action: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_valid": self.is_valid,
            "closing_date": self.closing_date.isoformat() if self.closing_date else None,
            "reference_date": self.reference_date.isoformat() if self.reference_date else None,
            "reference_type": self.reference_type,
            "days_until_closing": self.days_until_closing,
            "minimum_days": self.minimum_days,
            "action": self.action,
            "blocking": not self.is_valid,
        }


# =============================================================================
# TRID CHECKER CLASS
# =============================================================================

class TRIDChecker:
    """TRID (TILA-RESPA Integrated Disclosure) compliance checker."""
    
    def __init__(self):
        """Initialize TRID checker."""
        self._holiday_cache: Dict[int, List[date]] = {}
    
    def check_le_timing(self, loan_id: str) -> TRIDResult:
        """Check if we're within the 3 business day window for LE.
        
        Per SOP: LE due date should be set within 3 business days from Application Date.
        
        Args:
            loan_id: Encompass loan GUID
            
        Returns:
            TRIDResult with compliance status and dates
        """
        logger.info(f"[TRID] Checking LE timing for loan {loan_id[:8]}...")
        
        # Get application date
        app_date = self.get_application_date(loan_id)
        
        if app_date is None:
            logger.warning("[TRID] Application Date not set")
            return TRIDResult(
                compliant=False,
                application_date=None,
                le_due_date=None,
                days_remaining=0,
                action="Application Date not set - BLOCKING"
            )
        
        # Calculate LE due date
        le_due = self.calculate_le_due_date(app_date)
        today = date.today()
        
        # Check if past due
        if today > le_due:
            days_past = (today - le_due).days
            logger.warning(f"[TRID] LE Due Date PASSED by {days_past} days")
            return TRIDResult(
                compliant=False,
                application_date=app_date,
                le_due_date=le_due,
                days_remaining=0,
                is_past_due=True,
                action=f"LE Due Date PASSED by {days_past} days - Escalate to Supervisor"
            )
        
        # Calculate days remaining
        days_remaining = (le_due - today).days
        logger.info(f"[TRID] Compliant: {days_remaining} days remaining until LE due date")
        
        return TRIDResult(
            compliant=True,
            application_date=app_date,
            le_due_date=le_due,
            days_remaining=days_remaining
        )
    
    def calculate_le_due_date(self, app_date: date) -> date:
        """Calculate LE due date = 3 business days from application.
        
        Per SOP: Excludes Sundays and federal holidays.
        Note: Saturdays ARE counted as business days for TRID purposes.
        
        Args:
            app_date: Application date
            
        Returns:
            LE due date (3 business days after application)
        """
        business_days = 0
        current = app_date
        
        while business_days < 3:
            current += timedelta(days=1)
            if self.is_business_day(current):
                business_days += 1
        
        return current
    
    def is_business_day(self, d: date) -> bool:
        """Check if a date is a business day for TRID purposes.
        
        Note: Under TRID, business days are all days except Sundays and federal holidays.
        Saturdays ARE included as business days.
        """
        # Sunday = 6
        if d.weekday() == 6:
            return False
        
        # Check federal holidays
        holidays = self._get_holidays_for_year(d.year)
        if d in holidays:
            return False
        
        return True
    
    def _get_holidays_for_year(self, year: int) -> List[date]:
        """Get holidays for a year (cached)."""
        if year not in self._holiday_cache:
            self._holiday_cache[year] = get_federal_holidays(year)
        return self._holiday_cache[year]
    
    def get_application_date(self, loan_id: str) -> Optional[date]:
        """Get Application Date from Encompass.
        
        Args:
            loan_id: Encompass loan GUID
            
        Returns:
            Application date, or None if not set
        """
        value = read_field(loan_id, APPLICATION_DATE_FIELD)
        
        if value is None:
            return None
        
        return self._parse_date(value)
    
    def check_disclosure_alert(self, loan_id: str) -> bool:
        """Check if "Send Initial Disclosures" alert exists.
        
        Per SOP: Under Alerts & Messages tab, there must be an alert titled
        "Send Initial Disclosures" if the initial disclosure has not been issued yet.
        
        Note: This is a placeholder - actual implementation requires
        Encompass Alerts API access.
        
        Args:
            loan_id: Encompass loan GUID
            
        Returns:
            True if alert exists, False otherwise
        """
        # TODO: Implement using Encompass Alerts API
        # For now, return True to not block (alert check is informational)
        logger.info("[TRID] Alert check - returning True (API integration pending)")
        return True
    
    def check_lock_status(self, loan_id: str) -> LockStatusResult:
        """Check rate lock status.
        
        Per SOP:
        - Case 1 (Locked Loans): All TRID info must be updated
        - Case 2 (Non-Locked Loans): Monitor App Date & LE Due Date
        
        Args:
            loan_id: Encompass loan GUID
            
        Returns:
            LockStatusResult with lock information
        """
        logger.info(f"[TRID] Checking lock status for loan {loan_id[:8]}...")
        
        values = read_fields(loan_id, [LOCK_DATE_FIELD, LOCK_EXPIRATION_FIELD, RATE_LOCKED_FIELD])
        
        lock_date = self._parse_date(values.get(LOCK_DATE_FIELD))
        lock_exp = self._parse_date(values.get(LOCK_EXPIRATION_FIELD))
        rate_locked = values.get(RATE_LOCKED_FIELD)
        
        # Check if locked
        is_locked = False
        if rate_locked:
            rate_str = str(rate_locked).lower()
            is_locked = rate_str in ["y", "yes", "true", "1", "locked"]
        
        # Also check if lock date exists and hasn't expired
        if lock_date and lock_exp:
            if date.today() <= lock_exp:
                is_locked = True
        
        logger.info(f"[TRID] Lock status: {'LOCKED' if is_locked else 'NOT LOCKED'}")
        
        return LockStatusResult(
            is_locked=is_locked,
            lock_date=lock_date,
            lock_expiration=lock_exp
        )
    
    def check_closing_date(self, loan_id: str) -> ClosingDateResult:
        """Check closing date is at least 15 days after app/rate date (G8).
        
        Per SOP:
        - If NOT locked: Closing date ≥ 15 days after Application Date
        - If LOCKED: Closing date ≥ 15 days after Last Rate Set Date
        
        Args:
            loan_id: Encompass loan GUID
            
        Returns:
            ClosingDateResult with validation status
        """
        logger.info(f"[TRID] Checking closing date (15-day rule) for loan {loan_id[:8]}...")
        
        # Get all relevant fields
        values = read_fields(loan_id, [
            CLOSING_DATE_FIELD,
            APPLICATION_DATE_FIELD,
            LOCK_DATE_FIELD,
            RATE_LOCKED_FIELD,
        ])
        
        closing_date = self._parse_date(values.get(CLOSING_DATE_FIELD))
        app_date = self._parse_date(values.get(APPLICATION_DATE_FIELD))
        lock_date = self._parse_date(values.get(LOCK_DATE_FIELD))
        rate_locked = values.get(RATE_LOCKED_FIELD)
        
        # Check if we have a closing date
        if closing_date is None:
            logger.warning("[TRID] Closing date not set")
            return ClosingDateResult(
                is_valid=False,
                closing_date=None,
                action="Closing date not set - must be at least 15 days from app date"
            )
        
        # Determine if locked
        is_locked = False
        if rate_locked:
            rate_str = str(rate_locked).lower()
            is_locked = rate_str in ["y", "yes", "true", "1", "locked"]
        
        # Determine reference date based on lock status
        if is_locked and lock_date:
            reference_date = lock_date
            reference_type = "last_rate_set_date"
            logger.info(f"[TRID] Using lock date as reference: {lock_date}")
        elif app_date:
            reference_date = app_date
            reference_type = "application_date"
            logger.info(f"[TRID] Using application date as reference: {app_date}")
        else:
            logger.warning("[TRID] No reference date available")
            return ClosingDateResult(
                is_valid=False,
                closing_date=closing_date,
                action="Application date not set - cannot validate closing date"
            )
        
        # Calculate days between reference and closing
        days_until_closing = (closing_date - reference_date).days
        is_valid = days_until_closing >= MINIMUM_CLOSING_DAYS
        
        if is_valid:
            logger.info(f"[TRID] Closing date valid: {days_until_closing} days after {reference_type}")
        else:
            logger.warning(f"[TRID] Closing date INVALID: Only {days_until_closing} days after {reference_type} "
                          f"(minimum {MINIMUM_CLOSING_DAYS} days required)")
        
        action = None
        if not is_valid:
            action = (f"Closing date must be at least {MINIMUM_CLOSING_DAYS} days after {reference_type}. "
                     f"Current: {days_until_closing} days. Adjust closing date.")
        
        return ClosingDateResult(
            is_valid=is_valid,
            closing_date=closing_date,
            reference_date=reference_date,
            reference_type=reference_type,
            days_until_closing=days_until_closing,
            minimum_days=MINIMUM_CLOSING_DAYS,
            action=action
        )
    
    def _parse_date(self, value: Any) -> Optional[date]:
        """Parse a date value from Encompass.
        
        Handles various date formats.
        """
        if value is None:
            return None
        
        value_str = str(value).strip()
        if not value_str:
            return None
        
        # Try common date formats
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%Y/%m/%d",
            "%m/%d/%y",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(value_str, fmt).date()
            except ValueError:
                continue
        
        # Try ISO format with time
        try:
            return datetime.fromisoformat(value_str.replace("Z", "+00:00")).date()
        except ValueError:
            pass
        
        logger.warning(f"[TRID] Could not parse date: {value_str}")
        return None


# =============================================================================
# MODULE-LEVEL FUNCTIONS
# =============================================================================

# Singleton instance
_checker: Optional[TRIDChecker] = None


def get_trid_checker() -> TRIDChecker:
    """Get the TRID checker singleton."""
    global _checker
    if _checker is None:
        _checker = TRIDChecker()
    return _checker


def check_trid_compliance(loan_id: str) -> Dict[str, Any]:
    """Check TRID compliance for a loan.
    
    Convenience function that returns a dictionary.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with TRID compliance status
    """
    checker = get_trid_checker()
    result = checker.check_le_timing(loan_id)
    return result.to_dict()


def check_closing_date(loan_id: str) -> Dict[str, Any]:
    """Check closing date meets 15-day rule (G8).
    
    Per SOP: Closing date must be at least 15 days after:
    - Application date (if unlocked)
    - Last rate set date (if locked)
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with closing date validation status
    """
    checker = get_trid_checker()
    result = checker.check_closing_date(loan_id)
    return result.to_dict()


def check_lock_status(loan_id: str) -> Dict[str, Any]:
    """Check lock status for a loan.
    
    Convenience function that returns a dictionary.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        Dictionary with lock status
    """
    checker = get_trid_checker()
    result = checker.check_lock_status(loan_id)
    return result.to_dict()


def calculate_le_due_date(app_date: date) -> date:
    """Calculate LE due date from application date.
    
    Convenience function.
    
    Args:
        app_date: Application date
        
    Returns:
        LE due date (3 business days after application)
    """
    checker = get_trid_checker()
    return checker.calculate_le_due_date(app_date)

