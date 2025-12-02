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
    # v2 additions
    REGZ_LE_FIELDS,
    FORM_REQUIRED_FIELDS,
    CTC_FIELDS,
    ATR_QM_FIELDS,
    TRID_FIELDS,
    MVPExclusions,
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
    DisclosureType,
    HandoffStatus,
    create_handoff_from_results,
)
# v2 additions - TRID Checker
from .trid_checker import (
    TRIDChecker,
    TRIDResult,
    LockStatusResult,
    ClosingDateResult,  # G8: Closing date validation
    check_trid_compliance,
    check_lock_status,
    check_closing_date,  # G8: Closing date 15-day rule
    calculate_le_due_date,
    get_trid_checker,
)
# v2 additions - RegZ-LE Updater
from .regz_le_updater import (
    RegZLEUpdater,
    RegZLEUpdateResult,
    update_regz_le_form,
    get_late_charge,
    get_assumption_text,
    get_regz_le_updater,
)
# v2 additions - CTC Matcher
from .ctc_matcher import (
    CTCMatcher,
    CTCResult,
    match_cash_to_close,
    get_ctc_settings,
    get_ctc_matcher,
)
# v2 additions - Mavent Checker
from .mavent_checker import (
    MaventChecker,
    MaventResult,
    ComplianceIssue,
    check_mavent_compliance,
    get_mavent_checker,
)
# v2 additions - ATR/QM Checker
from .atr_qm_checker import (
    ATRQMChecker,
    ATRQMResult,
    FlagStatus,
    check_atr_qm_flags,
    get_points_fees_status,
    get_atr_qm_checker,
)
# v2 additions - Disclosure Orderer
from .disclosure_orderer import (
    DisclosureOrderer,
    OrderResult,
    AuditResult,
    order_initial_disclosure,
    audit_loan_for_disclosure,
    get_disclosure_orderer,
)
# v2 additions - Form Validator
from .form_validator import (
    FormValidator,
    FormCheckResult,
    ValidationResult,
    validate_disclosure_forms,
    validate_single_form,
    get_form_validator,
    check_hard_stop_fields,  # G1: Phone/Email hard stop check
    HARD_STOP_FIELDS,  # G1: Field IDs for hard stops
)
# v2 additions - Milestone Checker (pre-check for queue/status)
from .milestone_checker import (
    MilestoneChecker,
    MilestoneCheckResult,
    DisclosureTrackingResult,
    MilestoneAPIResult,
    PreCheckResult,
    check_milestone,
    is_ready_for_disclosure,
    get_disclosure_tracking_logs,
    get_loan_milestones,
    run_pre_check,
    check_initial_le_eligibility,
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
    # v2 Constants
    "REGZ_LE_FIELDS",
    "FORM_REQUIRED_FIELDS",
    "CTC_FIELDS",
    "ATR_QM_FIELDS",
    "TRID_FIELDS",
    "MVPExclusions",
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
    "DisclosureType",
    "HandoffStatus",
    "create_handoff_from_results",
    # v2 - TRID Checker
    "TRIDChecker",
    "TRIDResult",
    "LockStatusResult",
    "ClosingDateResult",  # G8
    "check_trid_compliance",
    "check_lock_status",
    "check_closing_date",  # G8: 15-day rule
    "calculate_le_due_date",
    "get_trid_checker",
    # v2 - RegZ-LE Updater
    "RegZLEUpdater",
    "RegZLEUpdateResult",
    "update_regz_le_form",
    "get_late_charge",
    "get_assumption_text",
    "get_regz_le_updater",
    # v2 - CTC Matcher
    "CTCMatcher",
    "CTCResult",
    "match_cash_to_close",
    "get_ctc_settings",
    "get_ctc_matcher",
    # v2 - Mavent Checker
    "MaventChecker",
    "MaventResult",
    "ComplianceIssue",
    "check_mavent_compliance",
    "get_mavent_checker",
    # v2 - ATR/QM Checker
    "ATRQMChecker",
    "ATRQMResult",
    "FlagStatus",
    "check_atr_qm_flags",
    "get_points_fees_status",
    "get_atr_qm_checker",
    # v2 - Disclosure Orderer
    "DisclosureOrderer",
    "OrderResult",
    "AuditResult",
    "order_initial_disclosure",
    "audit_loan_for_disclosure",
    "get_disclosure_orderer",
    # v2 - Form Validator
    "FormValidator",
    "FormCheckResult",
    "ValidationResult",
    "validate_disclosure_forms",
    "validate_single_form",
    "get_form_validator",
    "check_hard_stop_fields",  # G1: Phone/Email hard stop
    "HARD_STOP_FIELDS",  # G1
    # v2 - Milestone Checker & Pre-Check
    "MilestoneChecker",
    "MilestoneCheckResult",
    "DisclosureTrackingResult",
    "MilestoneAPIResult",
    "PreCheckResult",
    "check_milestone",
    "is_ready_for_disclosure",
    "get_disclosure_tracking_logs",
    "get_loan_milestones",
    "run_pre_check",
    "check_initial_le_eligibility",
]

