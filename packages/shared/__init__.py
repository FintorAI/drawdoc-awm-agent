"""Shared utilities for disclosure and draw docs agents."""

from .auth import get_access_token
from .encompass_client import get_encompass_client
from .encompass_io import (
    read_field,
    read_fields,
    write_field,
    write_fields,
    get_loan_summary,
    get_loan_type,
)
from .constants import (
    LoanType,
    PropertyState,
    MVPExclusions,
    DISCLOSURE_CRITICAL_FIELDS,
    get_all_critical_field_ids,
    get_field_name,
    FieldIds,
)
from .form_validator import (
    validate_disclosure_forms,
    check_hard_stop_fields,
)
from .trid_checker import (
    check_trid_compliance,
    check_lock_status,
    check_closing_date,
)
from .regz_le_updater import (
    update_regz_le_form,
    get_late_charge,
    get_assumption_text,
    get_regz_le_updater,
)
from .ctc_matcher import (
    match_cash_to_close,
    get_ctc_settings,
    get_ctc_matcher,
)
from .mi_calculator import (
    calculate_conventional_mi,
    calculate_mi,
    MICertData,
)
from .fee_tolerance import (
    check_fee_tolerance,
    extract_fees_from_fields,
    get_all_fee_field_ids,
    SECTION_A_FEES,
    SECTION_B_FEES,
)
from .milestone_checker import (
    run_pre_check,
    PreCheckResult,
    check_milestone,
)
from .mavent_checker import check_mavent_compliance, get_mavent_checker
from .atr_qm_checker import (
    check_atr_qm_flags,
    get_points_fees_status,
    get_atr_qm_checker,
    FlagStatus,
)
from .disclosure_orderer import (
    order_initial_disclosure,
    audit_loan_for_disclosure,
    get_disclosure_orderer,
)
from .csv_utils import load_field_mappings

# Logging utilities
from .logging_config import (
    setup_logging,
    add_agent_context,
    get_recent_logs,
    get_agent_timeline,
)

__all__ = [
    # Auth & Client
    "get_access_token",
    "get_encompass_client",
    # Field I/O
    "read_field",
    "read_fields",
    "write_field",
    "write_fields",
    "get_loan_summary",
    "get_loan_type",
    # Constants
    "LoanType",
    "PropertyState",
    "MVPExclusions",
    "DISCLOSURE_CRITICAL_FIELDS",
    "get_all_critical_field_ids",
    "get_field_name",
    "FieldIds",
    # Validators
    "validate_disclosure_forms",
    "check_hard_stop_fields",
    # TRID
    "check_trid_compliance",
    "check_lock_status",
    "check_closing_date",
    # Updaters
    "update_regz_le_form",
    "get_late_charge",
    "get_assumption_text",
    "get_regz_le_updater",
    "match_cash_to_close",
    "get_ctc_settings",
    "get_ctc_matcher",
    # Calculators
    "calculate_conventional_mi",
    "calculate_mi",
    "MICertData",
    "FieldIds",
    "check_fee_tolerance",
    "extract_fees_from_fields",
    "get_all_fee_field_ids",
    "SECTION_A_FEES",
    "SECTION_B_FEES",
    # Pre-checks
    "run_pre_check",
    "PreCheckResult",
    "check_milestone",
    # Mavent
    "check_mavent_compliance",
    "get_mavent_checker",
    # ATR/QM
    "check_atr_qm_flags",
    "get_points_fees_status",
    "get_atr_qm_checker",
    "FlagStatus",
    # Disclosure Ordering
    "order_initial_disclosure",
    "audit_loan_for_disclosure",
    "get_disclosure_orderer",
    # CSV
    "load_field_mappings",
    # Logging
    "setup_logging",
    "add_agent_context",
    "get_recent_logs",
    "get_agent_timeline",
]
