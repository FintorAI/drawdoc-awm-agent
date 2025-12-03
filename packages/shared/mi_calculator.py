"""Mortgage Insurance Calculator for disclosure and draw docs agents.

MVP Scope: Conventional MI calculation only.
FHA/VA/USDA calculations are Phase 2.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .constants import MIConstants, LoanType

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MIResult:
    """Result of MI calculation."""
    
    requires_mi: bool
    loan_type: str
    ltv: float
    
    # Upfront MI
    upfront_amount: Optional[float] = None
    upfront_rate: Optional[float] = None
    upfront_financed: bool = True
    
    # Monthly MI
    monthly_amount: Optional[float] = None
    annual_rate: Optional[float] = None
    
    # Renewal/Cancellation
    first_renewal_months: Optional[int] = None
    first_renewal_rate: Optional[float] = None
    second_renewal_rate: Optional[float] = None
    cancel_at_ltv: Optional[float] = None
    
    # Source
    source: str = "calculated"  # "mi_cert" or "calculated"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "requires_mi": self.requires_mi,
            "loan_type": self.loan_type,
            "ltv": self.ltv,
            "upfront_amount": self.upfront_amount,
            "upfront_rate": self.upfront_rate,
            "upfront_financed": self.upfront_financed,
            "monthly_amount": self.monthly_amount,
            "annual_rate": self.annual_rate,
            "first_renewal_months": self.first_renewal_months,
            "first_renewal_rate": self.first_renewal_rate,
            "second_renewal_rate": self.second_renewal_rate,
            "cancel_at_ltv": self.cancel_at_ltv,
            "source": self.source,
        }


@dataclass
class MICertData:
    """Data from MI Certificate (when available)."""
    
    upfront_premium: Optional[float] = None
    monthly_rate: Optional[float] = None
    renewal_months: Optional[int] = None
    renewal_rate: Optional[float] = None
    second_renewal_rate: Optional[float] = None


# =============================================================================
# CONVENTIONAL MI CALCULATION
# =============================================================================

def calculate_conventional_mi(
    loan_amount: float,
    appraised_value: float,
    ltv: Optional[float] = None,
    mi_cert_data: Optional[MICertData] = None,
    number_of_units: int = 1,
) -> MIResult:
    """Calculate Conventional PMI for loans with LTV > 80%.
    
    Args:
        loan_amount: Loan amount in dollars
        appraised_value: Appraised value in dollars
        ltv: LTV percentage (calculated if not provided)
        mi_cert_data: Optional data from MI Certificate
        number_of_units: Number of units (affects cancel at LTV)
        
    Returns:
        MIResult with calculated MI details
        
    Note:
        MVP: Uses MI Certificate rates if available, else uses estimates.
        For 2+ units, MI does not cancel at 78% LTV.
    """
    # Calculate LTV if not provided
    if ltv is None:
        if appraised_value > 0:
            ltv = (loan_amount / appraised_value) * 100
        else:
            ltv = 100.0
    
    # Format loan amount safely
    amount_str = f"${loan_amount:,.0f}" if loan_amount is not None else "$0"
    logger.info(f"[MI] Calculating Conventional MI: LTV={ltv:.2f}%, Amount={amount_str}")
    
    # No MI required for LTV <= 80%
    if ltv <= MIConstants.MI_REQUIRED_LTV:
        logger.info("[MI] No MI required (LTV <= 80%)")
        return MIResult(
            requires_mi=False,
            loan_type=LoanType.CONVENTIONAL,
            ltv=ltv,
        )
    
    # Use MI Certificate data if available
    if mi_cert_data is not None:
        logger.info("[MI] Using MI Certificate data")
        
        upfront = mi_cert_data.upfront_premium or 0
        annual_rate = mi_cert_data.monthly_rate or _estimate_annual_rate(ltv)
        monthly = (loan_amount * annual_rate) / 12
        
        return MIResult(
            requires_mi=True,
            loan_type=LoanType.CONVENTIONAL,
            ltv=ltv,
            upfront_amount=upfront,
            upfront_rate=upfront / loan_amount if loan_amount > 0 else None,
            upfront_financed=True,
            monthly_amount=round(monthly, 2),
            annual_rate=annual_rate,
            first_renewal_months=mi_cert_data.renewal_months or 120,
            first_renewal_rate=mi_cert_data.renewal_rate or annual_rate,
            second_renewal_rate=mi_cert_data.second_renewal_rate or 0.0020,
            cancel_at_ltv=None if number_of_units >= 2 else MIConstants.MI_CANCEL_LTV,
            source="mi_cert",
        )
    
    # Estimate MI if no certificate
    logger.info("[MI] Estimating MI (no MI Certificate)")
    
    annual_rate = _estimate_annual_rate(ltv)
    monthly = (loan_amount * annual_rate) / 12
    
    return MIResult(
        requires_mi=True,
        loan_type=LoanType.CONVENTIONAL,
        ltv=ltv,
        upfront_amount=None,  # Single premium not calculated without cert
        upfront_rate=None,
        upfront_financed=True,
        monthly_amount=round(monthly, 2),
        annual_rate=annual_rate,
        first_renewal_months=120,  # Default 10 years
        first_renewal_rate=annual_rate,
        second_renewal_rate=0.0020,  # Default 0.20%
        cancel_at_ltv=None if number_of_units >= 2 else MIConstants.MI_CANCEL_LTV,
        source="calculated",
    )


def _estimate_annual_rate(ltv: float) -> float:
    """Estimate annual MI rate based on LTV.
    
    These are rough estimates when MI Certificate is not available.
    """
    if ltv <= 85:
        return MIConstants.CONVENTIONAL_MI_ESTIMATE["85_to_90_ltv"]
    elif ltv <= 90:
        return MIConstants.CONVENTIONAL_MI_ESTIMATE["85_to_90_ltv"]
    elif ltv <= 95:
        return MIConstants.CONVENTIONAL_MI_ESTIMATE["90_to_95_ltv"]
    else:
        return MIConstants.CONVENTIONAL_MI_ESTIMATE["95_to_97_ltv"]


# =============================================================================
# PHASE 2: FHA/VA/USDA (STUBS)
# =============================================================================

def calculate_fha_mip(
    loan_amount: float,
    ltv: float,
    loan_term: int,
) -> MIResult:
    """Calculate FHA MIP (Mortgage Insurance Premium).
    
    Phase 2 implementation - currently returns placeholder.
    
    Args:
        loan_amount: Loan amount in dollars
        ltv: LTV percentage
        loan_term: Loan term in months
        
    Returns:
        MIResult with FHA MIP details
    """
    logger.warning("[MI] FHA MIP calculation is Phase 2 - returning estimate")
    
    upfront = loan_amount * MIConstants.FHA_UPFRONT_MIP_RATE
    
    # Simplified annual MIP rate (actual varies by LTV, term, amount)
    annual_rate = 0.0055 if ltv > 95 else 0.0050
    monthly = (loan_amount * annual_rate) / 12
    
    return MIResult(
        requires_mi=True,
        loan_type=LoanType.FHA,
        ltv=ltv,
        upfront_amount=round(upfront, 2),
        upfront_rate=MIConstants.FHA_UPFRONT_MIP_RATE,
        upfront_financed=True,
        monthly_amount=round(monthly, 2),
        annual_rate=annual_rate,
        cancel_at_ltv=None,  # FHA MIP typically for life of loan
        source="calculated",
    )


def calculate_va_funding_fee(
    loan_amount: float,
    down_payment_percent: float,
    is_subsequent_use: bool = False,
    is_exempt: bool = False,
    purpose: str = "purchase",
) -> MIResult:
    """Calculate VA Funding Fee.
    
    Phase 2 implementation - currently returns estimate.
    
    Args:
        loan_amount: Loan amount in dollars
        down_payment_percent: Down payment as percentage
        is_subsequent_use: True if veteran has used VA loan before
        is_exempt: True if veteran is exempt from funding fee
        purpose: "purchase", "cashout", or "irrrl"
        
    Returns:
        MIResult with VA Funding Fee details
    """
    logger.warning("[MI] VA Funding Fee calculation is Phase 2 - returning estimate")
    
    if is_exempt:
        return MIResult(
            requires_mi=False,
            loan_type=LoanType.VA,
            ltv=100 - down_payment_percent,
        )
    
    # Determine rate category
    rates = (MIConstants.VA_FUNDING_FEE_SUBSEQUENT if is_subsequent_use 
             else MIConstants.VA_FUNDING_FEE_FIRST_USE)
    
    if purpose.lower() == "irrrl":
        rate = rates["irrrl"]
    elif purpose.lower() == "cashout":
        rate = rates["cashout"]
    elif down_payment_percent >= 10:
        rate = rates["purchase_over_10"]
    elif down_payment_percent >= 5:
        rate = rates["purchase_5_to_10"]
    else:
        rate = rates["purchase_under_5"]
    
    funding_fee = loan_amount * rate
    
    return MIResult(
        requires_mi=True,
        loan_type=LoanType.VA,
        ltv=100 - down_payment_percent,
        upfront_amount=round(funding_fee, 2),
        upfront_rate=rate,
        upfront_financed=True,
        monthly_amount=None,  # VA has no monthly MI
        source="calculated",
    )


def calculate_usda_guarantee(
    loan_amount: float,
) -> MIResult:
    """Calculate USDA Guarantee Fee.
    
    Phase 2 implementation - currently returns estimate.
    
    Args:
        loan_amount: Loan amount in dollars
        
    Returns:
        MIResult with USDA Guarantee details
    """
    logger.warning("[MI] USDA Guarantee calculation is Phase 2 - returning estimate")
    
    upfront = loan_amount * MIConstants.USDA_UPFRONT_FEE
    monthly = (loan_amount * MIConstants.USDA_ANNUAL_FEE) / 12
    
    return MIResult(
        requires_mi=True,
        loan_type=LoanType.USDA,
        ltv=100.0,  # USDA is typically 100% LTV
        upfront_amount=round(upfront, 2),
        upfront_rate=MIConstants.USDA_UPFRONT_FEE,
        upfront_financed=True,
        monthly_amount=round(monthly, 2),
        annual_rate=MIConstants.USDA_ANNUAL_FEE,
        source="calculated",
    )


# =============================================================================
# MAIN CALCULATION FUNCTION
# =============================================================================

def calculate_mi(
    loan_type: str,
    loan_amount: float,
    appraised_value: float,
    ltv: Optional[float] = None,
    mi_cert_data: Optional[MICertData] = None,
    number_of_units: int = 1,
    **kwargs,
) -> MIResult:
    """Calculate MI based on loan type.
    
    MVP: Only Conventional is fully supported.
    FHA/VA/USDA return estimates (Phase 2).
    
    Args:
        loan_type: "Conventional", "FHA", "VA", or "USDA"
        loan_amount: Loan amount in dollars
        appraised_value: Appraised value in dollars
        ltv: LTV percentage (calculated if not provided)
        mi_cert_data: Optional MI Certificate data (Conventional only)
        number_of_units: Number of units (affects Conventional cancel at LTV)
        **kwargs: Additional args for specific loan types
        
    Returns:
        MIResult with calculated MI details
    """
    # Calculate LTV if not provided
    if ltv is None and appraised_value > 0:
        ltv = (loan_amount / appraised_value) * 100
    elif ltv is None:
        ltv = 100.0
    
    loan_type_upper = loan_type.upper() if loan_type else ""
    
    if "CONVENTIONAL" in loan_type_upper or "CONV" in loan_type_upper:
        return calculate_conventional_mi(
            loan_amount=loan_amount,
            appraised_value=appraised_value,
            ltv=ltv,
            mi_cert_data=mi_cert_data,
            number_of_units=number_of_units,
        )
    elif "FHA" in loan_type_upper:
        return calculate_fha_mip(
            loan_amount=loan_amount,
            ltv=ltv,
            loan_term=kwargs.get("loan_term", 360),
        )
    elif "VA" in loan_type_upper:
        return calculate_va_funding_fee(
            loan_amount=loan_amount,
            down_payment_percent=kwargs.get("down_payment_percent", 0),
            is_subsequent_use=kwargs.get("is_subsequent_use", False),
            is_exempt=kwargs.get("is_exempt", False),
            purpose=kwargs.get("purpose", "purchase"),
        )
    elif "USDA" in loan_type_upper or "RURAL" in loan_type_upper:
        return calculate_usda_guarantee(loan_amount=loan_amount)
    else:
        logger.warning(f"[MI] Unknown loan type: {loan_type}")
        return MIResult(
            requires_mi=False,
            loan_type=loan_type or "Unknown",
            ltv=ltv,
        )

