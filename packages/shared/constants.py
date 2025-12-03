"""Shared constants for disclosure and draw docs agents.

This module contains field mappings, loan type constants, and MVP critical fields.
"""

from typing import Dict, List


# =============================================================================
# LOAN TYPE CONSTANTS
# =============================================================================

class LoanType:
    """Loan type constants."""
    CONVENTIONAL = "Conventional"
    FHA = "FHA"
    VA = "VA"
    USDA = "USDA"
    
    # MVP: Only Conventional is supported
    MVP_SUPPORTED = [CONVENTIONAL]
    
    @classmethod
    def is_mvp_supported(cls, loan_type: str) -> bool:
        """Check if a loan type is supported in MVP."""
        return loan_type in cls.MVP_SUPPORTED


class LoanPurpose:
    """Loan purpose constants."""
    PURCHASE = "Purchase"
    REFINANCE = "Refinance"
    CASHOUT = "CashOut"
    CONSTRUCTION = "Construction"


class PropertyState:
    """Property state constants."""
    # MVP: Only NV and CA are supported
    MVP_SUPPORTED = ["NV", "CA"]
    
    @classmethod
    def is_mvp_supported(cls, state: str) -> bool:
        """Check if a state is supported in MVP."""
        if state is None:
            return False
        return state.upper() in cls.MVP_SUPPORTED


# =============================================================================
# DISCLOSURE CRITICAL FIELDS (~20 fields for MVP)
# =============================================================================

# These are the critical fields that MUST be populated for disclosure
# Reduced from full CSV list to ~20 MVP critical fields

DISCLOSURE_CRITICAL_FIELDS: Dict[str, List[Dict[str, str]]] = {
    "borrower": [
        {"id": "4000", "name": "Borrower First Name"},
        {"id": "4002", "name": "Borrower Last Name"},
        {"id": "65", "name": "Borrower SSN"},
        {"id": "1402", "name": "Borrower Email"},
    ],
    "property": [
        {"id": "11", "name": "Property Street Address"},
        {"id": "12", "name": "Property City"},
        {"id": "14", "name": "Property State"},
        {"id": "15", "name": "Property Zip"},
    ],
    "loan": [
        {"id": "1109", "name": "Loan Amount"},
        {"id": "3", "name": "Interest Rate"},
        {"id": "4", "name": "Loan Term"},
        {"id": "1172", "name": "Loan Type"},
        {"id": "19", "name": "Loan Purpose"},
        {"id": "353", "name": "LTV"},
    ],
    "property_value": [
        {"id": "356", "name": "Appraised Value"},
        {"id": "136", "name": "Purchase Price"},
    ],
    "contacts": [
        {"id": "VEND.X263", "name": "Settlement Agent Name"},
        {"id": "411", "name": "Title Company Name"},
    ],
    "dates": [
        {"id": "CD1.X1", "name": "CD Date Issued"},
        {"id": "748", "name": "Estimated Closing Date"},
    ],
}


def get_all_critical_field_ids() -> List[str]:
    """Get all critical field IDs as a flat list.
    
    Returns:
        List of all critical field IDs
    """
    field_ids = []
    for category_fields in DISCLOSURE_CRITICAL_FIELDS.values():
        for field in category_fields:
            field_ids.append(field["id"])
    return field_ids


def get_critical_fields_by_category(category: str) -> List[Dict[str, str]]:
    """Get critical fields for a specific category.
    
    Args:
        category: Category name (borrower, property, loan, etc.)
        
    Returns:
        List of field dicts with id and name
    """
    return DISCLOSURE_CRITICAL_FIELDS.get(category, [])


def get_field_name(field_id: str) -> str:
    """Get the name of a critical field by ID.
    
    Args:
        field_id: Encompass field ID
        
    Returns:
        Field name, or field_id if not found
    """
    for category_fields in DISCLOSURE_CRITICAL_FIELDS.values():
        for field in category_fields:
            if field["id"] == field_id:
                return field["name"]
    return field_id


# =============================================================================
# ENCOMPASS FIELD ID MAPPINGS
# =============================================================================

# Key field IDs used across agents
class FieldIds:
    """Common Encompass field IDs."""
    
    # Borrower
    BORROWER_FIRST_NAME = "4000"
    BORROWER_LAST_NAME = "4002"
    BORROWER_SSN = "65"
    BORROWER_EMAIL = "1402"
    BORROWER_DOB = "1402"
    
    # Co-Borrower
    COBORROWER_FIRST_NAME = "4004"
    COBORROWER_LAST_NAME = "4006"
    COBORROWER_SSN = "97"
    
    # Property
    PROPERTY_ADDRESS = "11"
    PROPERTY_CITY = "12"
    PROPERTY_STATE = "14"
    PROPERTY_ZIP = "15"
    PROPERTY_COUNTY = "13"
    
    # Loan Terms
    LOAN_AMOUNT = "1109"
    INTEREST_RATE = "3"
    LOAN_TERM = "4"
    LOAN_TYPE = "1172"
    LOAN_PURPOSE = "19"
    AMORTIZATION_TYPE = "608"
    
    # Values
    APPRAISED_VALUE = "356"
    PURCHASE_PRICE = "136"
    LTV = "353"
    CLTV = "976"
    
    # Property Type
    PROPERTY_TYPE = "1041"
    OCCUPANCY_TYPE = "1811"
    NUMBER_OF_UNITS = "16"
    
    # Mortgage Insurance
    MI_MONTHLY_AMOUNT = "232"
    MI_UPFRONT_AMOUNT = "URLA.X133"
    MI_CANCEL_AT_LTV = "1196"
    
    # Fees - Section A
    ORIGINATION_FEE = "NEWHUD.X7"
    DISCOUNT_POINTS = "NEWHUD.X8"
    
    # CD Fields
    CD_DATE_ISSUED = "CD1.X1"
    CLOSING_DATE = "748"
    DISBURSEMENT_DATE = "2553"
    
    # Contacts
    SETTLEMENT_AGENT = "VEND.X263"
    TITLE_COMPANY = "411"
    
    # Status
    LOAN_STATUS = "1393"


# =============================================================================
# FEE TOLERANCE CONSTANTS
# =============================================================================

class FeeTolerance:
    """Fee tolerance rules for TRID compliance."""
    
    # 0% tolerance - cannot increase at all
    ZERO_TOLERANCE_FEES = [
        "NEWHUD.X7",   # Origination fee
        "NEWHUD.X8",   # Discount points
        # Any fee not on LE is also 0% tolerance
    ]
    
    # 10% tolerance in aggregate - Section B fees when using SPL provider
    TEN_PERCENT_TOLERANCE_FEES = [
        "NEWHUD.X12",  # Appraisal fee
        "NEWHUD.X15",  # Credit report fee
        "NEWHUD.X17",  # Flood certification
        "NEWHUD.X19",  # Tax service
        # Title services when borrower uses provider from SPL
    ]
    
    # No tolerance - Section C fees (borrower-shopped)
    NO_TOLERANCE_FEES = [
        # Title services when borrower chooses own provider
    ]


# =============================================================================
# MI CONSTANTS
# =============================================================================

class MIConstants:
    """Mortgage Insurance constants."""
    
    # LTV threshold for requiring MI
    MI_REQUIRED_LTV = 80.0
    
    # LTV at which MI can be cancelled (for Conventional)
    MI_CANCEL_LTV = 78.0
    
    # FHA MIP rates
    FHA_UPFRONT_MIP_RATE = 0.0175  # 1.75%
    
    # VA Funding Fee rates (as of April 7, 2023)
    VA_FUNDING_FEE_FIRST_USE = {
        "purchase_under_5": 0.0215,   # 2.15%
        "purchase_5_to_10": 0.0150,   # 1.50%
        "purchase_over_10": 0.0125,   # 1.25%
        "cashout": 0.0215,            # 2.15%
        "irrrl": 0.0050,              # 0.50%
    }
    VA_FUNDING_FEE_SUBSEQUENT = {
        "purchase_under_5": 0.0330,   # 3.30%
        "purchase_5_to_10": 0.0150,   # 1.50%
        "purchase_over_10": 0.0125,   # 1.25%
        "cashout": 0.0330,            # 3.30%
        "irrrl": 0.0050,              # 0.50%
    }
    
    # USDA Guarantee Fee
    USDA_UPFRONT_FEE = 0.01  # 1%
    USDA_ANNUAL_FEE = 0.0035  # 0.35%
    USDA_TECHNOLOGY_FEE = 25  # $25
    
    # Conventional MI defaults (when MI Cert not available)
    CONVENTIONAL_MI_ESTIMATE = {
        "85_to_90_ltv": 0.0045,  # 0.45% annual
        "90_to_95_ltv": 0.0070,  # 0.70% annual
        "95_to_97_ltv": 0.0095,  # 0.95% annual
    }


# =============================================================================
# REGZ-LE FIELD MAPPINGS (v2)
# =============================================================================

REGZ_LE_FIELDS = {
    # LE Date
    "le_date_issued": "LE1.X1",
    
    # Interest Accrual
    "interest_days_per_year": "1176",
    "zero_percent_payment_option": "3514",
    "use_simple_interest": "3515",
    "biweekly_interim_days": "3516",
    
    # Late Charge
    "late_charge_days": "672",
    "late_charge_percent": "674",  # Fixed: was 673 which doesn't exist
    
    # Assumption
    "assumption_text": "3517",
    
    # Buydown
    "buydown_marked": "1751",
    "buydown_contributor": "1755",
    "buydown_type": "1753",
    "buydown_rate": "1754",
    "buydown_term": "1756",
    "buydown_funds": "1757",
    
    # Prepayment
    "prepay_indicator": "664",
    "prepay_type": "1762",
    "prepay_period": "1763",
    "prepay_percent": "1764",
}


# =============================================================================
# FORM REQUIRED FIELDS (v2 - per SOP)
# =============================================================================

FORM_REQUIRED_FIELDS = {
    "1003_URLA_Lender": [
        "4000",  # Borrower First Name
        "4002",  # Borrower Last Name
        "65",    # Borrower SSN
        "11",    # Property Address
        "12",    # Property City
        "14",    # Property State
        "15",    # Property Zip
        "1109",  # Loan Amount
        "19",    # Loan Purpose
        "1811",  # Occupancy Type
    ],
    "Borrower_Summary_Origination": [
        "2626",  # Channel
        "1393",  # Current Status
        "745",   # Application Date
    ],
    "RegZ_LE": [
        "LE1.X1",  # LE Date Issued
        "3",       # Interest Rate
        "4",       # Loan Term
    ],
}


# =============================================================================
# CASH TO CLOSE FIELDS (v2)
# =============================================================================

CTC_FIELDS = {
    # Loan Purpose
    "loan_purpose": "19",
    
    # Purchase Settings
    "use_actual_down_payment": "NEWHUD2.X55",
    "closing_costs_financed": "NEWHUD2.X56",
    "include_payoffs_in_adjustments": "NEWHUD2.X57",
    
    # Refinance Settings
    "alternative_form_checkbox": "NEWHUD2.X58",
    
    # CTC Values
    "calculated_ctc": "NEWHUD2.X59",
    "displayed_ctc": "LE1.X77",
    "estimated_ctc": "CD3.X105",
    
    # Section M
    "emd_deposit": "1394",
    "general_lender_credit": "1395",
    "seller_credit": "1396",
}


# =============================================================================
# ATR/QM FIELDS (v2)
# =============================================================================

ATR_QM_FIELDS = {
    # Qualification Flags
    "loan_features_flag": "ATRQM.X1",
    "points_fees_flag": "ATRQM.X2",
    "price_limit_flag": "ATRQM.X3",
    
    # Eligibility
    "atr_qm_eligibility": "ATRQM.X4",
    
    # Points and Fees Test
    "points_fees_limit": "ATRQM.X10",
    "points_fees_actual": "ATRQM.X11",
    "points_fees_test_result": "ATRQM.X12",
    
    # QM Type
    "qm_type": "ATRQM.X20",
}


# =============================================================================
# TRID DATE FIELDS (v2)
# =============================================================================

TRID_FIELDS = {
    # Application/Disclosure dates
    "application_date": "745",
    "le_date_issued": "LE1.X1",
    "disclosure_sent_date": "3152",
    
    # Lock fields
    "lock_date": "761",
    "lock_expiration": "432",
    "rate_locked": "2400",
}


# =============================================================================
# MVP EXCLUSIONS (v2)
# =============================================================================

class MVPExclusions:
    """States and loan types excluded from MVP automation."""
    
    # Texas has special state rules
    EXCLUDED_STATES = ["TX"]
    
    # Non-Conventional loans require manual processing
    EXCLUDED_LOAN_TYPES = ["FHA", "VA", "USDA"]
    
    @classmethod
    def is_excluded_state(cls, state: str) -> bool:
        """Check if state is excluded from MVP."""
        if state is None:
            return False
        return state.upper() in cls.EXCLUDED_STATES
    
    @classmethod
    def is_excluded_loan_type(cls, loan_type: str) -> bool:
        """Check if loan type is excluded from MVP."""
        if loan_type is None:
            return True
        return loan_type in cls.EXCLUDED_LOAN_TYPES