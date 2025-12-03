"""
Primitive Tools for Docs Draw MVP

These tools are reusable across all agents and workflows.
They provide the foundational operations for interacting with:
- Loan context and workflow
- Document extraction
- Encompass field IO
- Compliance checks
- Document distribution
- Issue logging

All tools are consolidated in primitives.py for easy access.
"""

from .primitives import (
    # Loan context & workflow
    get_loan_context,
    update_milestone,  # Legacy field-based
    # Milestone API (new)
    get_loan_milestones,
    get_milestone_by_name,
    update_milestone_api,
    add_milestone_log,
    # Document extraction
    list_required_documents,
    list_loan_documents,
    download_document_from_efolder,
    download_documents,
    extract_entities_from_docs,
    # Encompass IO
    read_fields,
    write_fields,
    # Compliance
    run_compliance_check,
    get_compliance_results,
    # Distribution
    order_docs,
    send_closing_package,
    # Issue logging
    log_issue,
    # Convenience
    get_all_tools,
)

__all__ = [
    # Loan context & workflow
    "get_loan_context",
    "update_milestone",
    # Milestone API (new)
    "get_loan_milestones",
    "get_milestone_by_name",
    "update_milestone_api",
    "add_milestone_log",
    # Document extraction
    "list_required_documents",
    "list_loan_documents",
    "download_document_from_efolder",
    "download_documents",
    "extract_entities_from_docs",
    # Encompass IO
    "read_fields",
    "write_fields",
    # Compliance
    "run_compliance_check",
    "get_compliance_results",
    # Distribution
    "order_docs",
    "send_closing_package",
    # Issue logging
    "log_issue",
    # Convenience
    "get_all_tools",
]

