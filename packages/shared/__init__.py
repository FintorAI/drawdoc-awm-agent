"""Shared utilities for all agent pipelines (draw docs, disclosure, LOA)."""

from .auth import (
    EncompassAuthManager,
    TokenInfo,
    get_auth_manager,
    get_access_token,
)
from .encompass_client import get_encompass_client
from .csv_utils import load_field_mappings, get_field_by_id, get_field_by_name, get_fields_for_document_type
from .encompass_io import (
    read_fields,
    read_field,
    write_fields,
    write_field,
    get_loan_type,
    get_loan_purpose,
    get_loan_summary,
    is_conventional_loan,
    is_government_loan,
)
from .constants import (
    LoanType,
    LoanPurpose,
    PropertyState,
    FieldIds,
    FeeTolerance,
    MIConstants,
    DISCLOSURE_CRITICAL_FIELDS,
    get_all_critical_field_ids,
    get_critical_fields_by_category,
    get_field_name,
)
from .mi_calculator import (
    MIResult,
    MICertData,
    calculate_mi,
    calculate_conventional_mi,
    calculate_fha_mip,
    calculate_va_funding_fee,
    calculate_usda_guarantee,
)
from .fee_tolerance import (
    ToleranceResult,
    ToleranceViolation,
    check_fee_tolerance,
    check_single_fee_tolerance,
    extract_fees_from_fields,
    get_all_fee_field_ids,
    SECTION_A_FEES,
    SECTION_B_FEES,
)
from .handoff import (
    DisclosureHandoff,
    create_handoff_from_results,
)

__all__ = [
    # Authentication
    "EncompassAuthManager",
    "TokenInfo",
    "get_auth_manager",
    "get_access_token",
    # Encompass client
    "get_encompass_client",
    # CSV utilities
    "load_field_mappings",
    "get_field_by_id",
    "get_field_by_name",
    "get_fields_for_document_type",
    # Field I/O
    "read_fields",
    "read_field",
    "write_fields",
    "write_field",
    # Loan metadata
    "get_loan_type",
    "get_loan_purpose",
    "get_loan_summary",
    "is_conventional_loan",
    "is_government_loan",
    # Constants
    "LoanType",
    "LoanPurpose",
    "PropertyState",
    "FieldIds",
    "FeeTolerance",
    "MIConstants",
    "DISCLOSURE_CRITICAL_FIELDS",
    "get_all_critical_field_ids",
    "get_critical_fields_by_category",
    "get_field_name",
    # MI Calculator
    "MIResult",
    "MICertData",
    "calculate_mi",
    "calculate_conventional_mi",
    "calculate_fha_mip",
    "calculate_va_funding_fee",
    "calculate_usda_guarantee",
    # Fee Tolerance
    "ToleranceResult",
    "ToleranceViolation",
    "check_fee_tolerance",
    "check_single_fee_tolerance",
    "extract_fees_from_fields",
    "get_all_fee_field_ids",
    "SECTION_A_FEES",
    "SECTION_B_FEES",
    # Handoff
    "DisclosureHandoff",
    "create_handoff_from_results",
]

