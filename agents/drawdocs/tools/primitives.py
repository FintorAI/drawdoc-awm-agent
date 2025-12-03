"""
Primitive Tools for Docs Draw MVP

Consolidated tools for all agents. These are the foundational operations for:
1. Loan context & workflow
2. Document extraction
3. Encompass field IO
4. Compliance checks
5. Document distribution
6. Issue logging

These tools are reusable across all agents and workflows.
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from BOTH sources
# Strategy: Load MCP server FIRST (for Encompass OAuth), then local for other vars

# 1. Load MCP server .env FIRST (for working Encompass OAuth credentials)
mcp_env_path = Path(__file__).parent.parent.parent.parent.parent / "encompass-mcp-server" / ".env"
if mcp_env_path.exists():
    load_dotenv(mcp_env_path)  # Load MCP credentials first
    
# 2. Then load local .env WITHOUT override (for LandingAI, DOCREPO, etc.)
load_dotenv(override=False)  # Adds local vars without overriding MCP's Encompass creds

# Configure logging
logger = logging.getLogger(__name__)

# Import Encompass client
from copilotagent import EncompassConnect

# Try to import HTTP client for raw API requests (milestones, etc.)
try:
    import sys
    from pathlib import Path
    # Add encompass-mcp-server to path if available
    # primitives.py -> tools -> drawdocs -> agents -> drawdoc-awm-agent -> Fintor
    mcp_server_path = Path(__file__).parent.parent.parent.parent.parent / "encompass-mcp-server"
    if mcp_server_path.exists():
        sys.path.insert(0, str(mcp_server_path))
        from util.auth import EncompassAuthManager
        from util.http import EncompassHttpClient
        MCP_HTTP_CLIENT_AVAILABLE = True
    else:
        MCP_HTTP_CLIENT_AVAILABLE = False
except ImportError:
    MCP_HTTP_CLIENT_AVAILABLE = False
    logger.warning("MCP HTTP client not available. Milestone API features will be limited.")

# Import extraction schema tools (from preparation agent)
try:
    from ..subagents.preparation_agent.tools.extraction_schemas import (
        get_extraction_schema,
        list_supported_document_types,
        get_fields_for_document_type
    )
    from ..subagents.preparation_agent.tools.csv_loader import get_csv_loader
    from ..subagents.preparation_agent.tools.field_mappings import (
        get_field_mapping,
        get_all_mappings_for_document
    )
    CSV_EXTRACTION_AVAILABLE = True
except ImportError:
    logger.warning("Could not import CSV-based extraction tools. Falling back to basic extraction.")
    CSV_EXTRACTION_AVAILABLE = False


# =============================================================================
# HELPER: Get Encompass Clients
# =============================================================================

def _get_encompass_client() -> EncompassConnect:
    """Get an initialized Encompass client with credentials from environment variables.
    
    Supports both MCP server variable names and direct variables.
    """
    # Try MCP server variable names first, then fall back to direct variables
    api_server = (
        os.getenv("ENCOMPASS_API_SERVER") or  # MCP server uses this
        os.getenv("ENCOMPASS_API_BASE_URL") or  # Direct variable
        "https://api.elliemae.com"  # Default
    )
    
    # Support both MCP server and direct credential variable names
    username = os.getenv("ENCOMPASS_SMART_USER") or os.getenv("ENCOMPASS_USERNAME", "")
    password = os.getenv("ENCOMPASS_SMART_PASS") or os.getenv("ENCOMPASS_PASSWORD", "")
    
    return EncompassConnect(
        access_token=os.getenv("ENCOMPASS_ACCESS_TOKEN", ""),
        api_base_url=api_server,
        credentials={
            "username": username,
            "password": password,
            "client_id": os.getenv("ENCOMPASS_CLIENT_ID", ""),
            "client_secret": os.getenv("ENCOMPASS_CLIENT_SECRET", ""),
            "instance_id": os.getenv("ENCOMPASS_INSTANCE_ID", ""),
            "subject_user_id": os.getenv("ENCOMPASS_SUBJECT_USER_ID", ""),
        },
        landingai_api_key=os.getenv("LANDINGAI_API_KEY", ""),
    )


def _get_http_client():
    """Get HTTP client for raw API requests (milestones, etc.)."""
    if not MCP_HTTP_CLIENT_AVAILABLE:
        raise RuntimeError("MCP HTTP client not available. Cannot make raw API requests.")
    
    # Get API server URL (handle both ENCOMPASS_API_SERVER and old var names)
    api_server = os.getenv("ENCOMPASS_API_SERVER") or os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com")
    timeout = int(os.getenv("ENCOMPASS_TIMEOUT", "60"))
    verify_ssl = os.getenv("ENCOMPASS_VERIFY_SSL", "true").lower() != "false"
    
    logger.debug(f"Using API server: {api_server}, CLIENT_ID: {os.getenv('ENCOMPASS_CLIENT_ID')}, INSTANCE: {os.getenv('ENCOMPASS_INSTANCE_ID')}")
    
    # Create auth manager (reads credentials from env vars internally)
    auth_manager = EncompassAuthManager(
        api_server=api_server,
        timeout=timeout,
        verify_ssl=verify_ssl
    )
    
    # Create HTTP client
    http_client = EncompassHttpClient(
        api_server=api_server,
        auth_manager=auth_manager,
        timeout=timeout,
        verify_ssl=verify_ssl
    )
    
    return http_client


# =============================================================================
# 1. LOAN CONTEXT & WORKFLOW TOOLS
# =============================================================================

def get_loan_context(loan_id: str, include_milestones: bool = True) -> Dict[str, Any]:
    """
    Get comprehensive loan context including pipeline status and flags.
    
    All field IDs are sourced from DrawingDoc Verifications CSV.
    
    Args:
        loan_id: The Encompass loan GUID or loan number
        include_milestones: Whether to fetch full milestone data via API (default: True)
        
    Returns:
        Dictionary containing:
        - loan_id: The loan GUID
        - loan_number: Loan number (Field ID: 364)
        - loan_type: Loan type (Field ID: 1172)
        - loan_program: Loan program (Field ID: 1401)
        - loan_purpose: Loan purpose (Field ID: 384)
        - occupancy: Occupancy type (Field ID: 3335)
        - state: Property state (Field ID: 14)
        - closing_date: Closing date (Field ID: 748)
        - application_date: Application date (Field ID: 745)
        - loan_amount: Loan amount (Field ID: 1109)
        - ltv: Loan-to-value ratio (Field ID: 353)
        - amortization_type: Amortization type (Field ID: 608)
        - flags: Dict with CTC, CD approved, CD acknowledged, in_docs_ordered_queue
        - milestones: Full milestone data from API (if include_milestones=True)
    """
    # Read all required fields (from DrawingDoc Verifications CSV)
    field_ids = [
        "364",   # Loan Number (row 166)
        "1172",  # Loan Type (row 172)
        "1401",  # Loan Program (row 168)
        "384",   # Loan Purpose (row 169) - corrected from "19"
        "3335",  # Occupancy Type (row 184) - corrected from "1811"
        "14",    # Subject Property State (row 221)
        "748",   # Closing Date (row 41)
        "745",   # Application Date (row 6)
        "1109",  # Loan Amount (row 154)
        "353",   # LTV (row 175)
        "608",   # Amortization Type (row 5)
    ]
    
    try:
        # Use read_fields which handles both MCP and legacy clients
        fields = read_fields(loan_id, field_ids)
        
        # Build base context (using field IDs from DrawingDoc Verifications CSV)
        context = {
            "loan_id": loan_id,
            "loan_number": fields.get("364", ""),
            "loan_type": fields.get("1172", ""),
            "loan_program": fields.get("1401", ""),
            "loan_purpose": fields.get("384", ""),
            "occupancy": fields.get("3335", ""),
            "state": fields.get("14", ""),
            "closing_date": fields.get("748", ""),
            "application_date": fields.get("745", ""),
            "loan_amount": fields.get("1109", ""),
            "ltv": fields.get("353", ""),
            "amortization_type": fields.get("608", ""),
        }
        
        # Get full milestone data from API (if available)
        if include_milestones and MCP_HTTP_CLIENT_AVAILABLE:
            try:
                milestones = get_loan_milestones(loan_id)
                context["milestones"] = {
                    "all": milestones,
                    "docs_ordered": get_milestone_by_name(loan_id, "Docs Ordered"),
                    "clear_to_close": get_milestone_by_name(loan_id, "Clear to Close"),
                    "docs_out": get_milestone_by_name(loan_id, "Docs Out"),
                }
                
                # Enhanced flags based on milestone API
                docs_ordered = context["milestones"]["docs_ordered"]
                clear_to_close = context["milestones"]["clear_to_close"]
                
                context["flags"] = {
                    "is_ctc": clear_to_close and clear_to_close.get("status") == "Finished",
                    "cd_approved": _check_cd_approved(fields),
                    "cd_acknowledged": _check_cd_acknowledged(fields),
                    "in_docs_ordered_queue": docs_ordered and docs_ordered.get("status") in ["Started", "InProgress"],
                    "docs_ordered_finished": docs_ordered and docs_ordered.get("status") == "Finished",
                }
            except Exception as e:
                logger.warning(f"Could not fetch milestone API data: {e}")
                # Fall back to field-based flags
                context["flags"] = {
                    "is_ctc": _check_is_ctc(fields),
                    "cd_approved": _check_cd_approved(fields),
                    "cd_acknowledged": _check_cd_acknowledged(fields),
                    "in_docs_ordered_queue": _check_in_docs_ordered_queue(fields),
                }
        else:
            # Use field-based flags
            context["flags"] = {
                "is_ctc": _check_is_ctc(fields),
                "cd_approved": _check_cd_approved(fields),
                "cd_acknowledged": _check_cd_acknowledged(fields),
                "in_docs_ordered_queue": _check_in_docs_ordered_queue(fields),
            }
        
        logger.info(f"Retrieved loan context for {loan_id}: {context['loan_number']}")
        return context
        
    except Exception as e:
        logger.error(f"Error getting loan context for {loan_id}: {e}")
        raise


def _check_is_ctc(fields: Dict[str, Any]) -> bool:
    """Check if loan is Clear to Close based on fields."""
    # TODO: Implement actual CTC check logic based on your business rules
    # This should check specific fields in your Encompass instance
    # For now, return placeholder value
    return False  # Placeholder - implement with actual field checks


def _check_cd_approved(fields: Dict[str, Any]) -> bool:
    """Check if CD is approved."""
    # TODO: Implement actual CD approval check
    # Check specific CD status fields in your Encompass instance
    return False  # Placeholder


def _check_cd_acknowledged(fields: Dict[str, Any]) -> bool:
    """Check if CD is acknowledged."""
    # TODO: Implement actual CD acknowledgment check
    return False  # Placeholder


def _check_in_docs_ordered_queue(fields: Dict[str, Any]) -> bool:
    """Check if loan is in Docs Ordered queue."""
    # TODO: Implement actual queue check
    # Check specific milestone/queue fields in your Encompass instance
    return False  # Placeholder


def update_milestone(loan_id: str, status: str, comment: str) -> bool:
    """
    Update milestone status and add comment (legacy field-based approach).
    
    DEPRECATED: Use update_milestone_api() for full milestone API support.
    
    Args:
        loan_id: The loan GUID
        status: Milestone status (e.g., "Finished")
        comment: Comment to add (e.g., "DOCS Out on 11/28/2025")
        
    Returns:
        True if successful, False otherwise
    """
    client = _get_encompass_client()
    
    try:
        updates = {
            "Log.MS.Status.Docs Out": status,
            "Log.MS.Date.Docs Out": datetime.now().strftime("%Y-%m-%d"),
            "Log.MS.Comments.Docs Out": comment,
            "MS.CLO": datetime.now().strftime("%Y-%m-%d"),  # Date Completed
        }
        
        # Write each field individually
        for field_id, value in updates.items():
            client.write_field(loan_id, field_id, value)
        logger.info(f"Updated milestone for {loan_id}: {status} - {comment}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating milestone for {loan_id}: {e}")
        return False


def get_loan_milestones(loan_id: str) -> List[Dict[str, Any]]:
    """
    Get all milestones for a loan using the Encompass Milestones API.
    
    Requires MCP HTTP client to be available.
    
    Args:
        loan_id: The loan GUID
        
    Returns:
        List of milestone dictionaries with:
        - id: Milestone ID
        - milestoneName: Name of milestone
        - status: Current status (Started, InProgress, Finished, etc.)
        - statusDate: Date of current status
        - comment: Comments for this milestone
        - logs: Array of log entries
    """
    if not MCP_HTTP_CLIENT_AVAILABLE:
        logger.warning("MCP HTTP client not available. Falling back to field-based milestone data.")
        return []
    
    try:
        http_client = _get_http_client()
        token = http_client.auth_manager.get_client_credentials_token()
        
        resp = http_client.request(
            method="GET",
            path=f"/encompass/v1/loans/{loan_id}/milestones",
            token=token
        )
        
        if resp.status_code == 200:
            milestones = resp.json()
            logger.info(f"Retrieved {len(milestones)} milestones for loan {loan_id}")
            return milestones
        else:
            logger.error(f"Failed to get milestones: {resp.status_code} - {resp.text}")
            return []
        
    except Exception as e:
        logger.error(f"Error getting milestones for {loan_id}: {e}")
        return []


def get_milestone_by_name(
    loan_id: str, 
    milestone_name: str
) -> Optional[Dict[str, Any]]:
    """
    Get a specific milestone by name.
    
    Args:
        loan_id: The loan GUID
        milestone_name: Name of milestone (e.g., "Docs Ordered", "Clear to Close")
        
    Returns:
        Milestone dictionary or None if not found
    """
    milestones = get_loan_milestones(loan_id)
    
    for milestone in milestones:
        if milestone.get("milestoneName") == milestone_name:
            return milestone
            
    logger.warning(f"Milestone '{milestone_name}' not found for loan {loan_id}")
    return None


def update_milestone_api(
    loan_id: str,
    milestone_name: str,
    status: str,
    comment: Optional[str] = None
) -> bool:
    """
    Update a milestone's status using the Milestones API (preferred method).
    
    This is the modern API-based approach vs the legacy field-based update_milestone().
    
    Args:
        loan_id: The loan GUID
        milestone_name: Name of milestone to update (e.g., "Docs Ordered")
        status: New status (Started, InProgress, Finished, etc.)
        comment: Optional comment to add
        
    Returns:
        True if successful, False otherwise
    """
    if not MCP_HTTP_CLIENT_AVAILABLE:
        logger.warning("MCP HTTP client not available. Falling back to legacy field-based update.")
        return update_milestone(loan_id, status, comment or "")
    
    try:
        # First, get the milestone to find its ID
        milestone = get_milestone_by_name(loan_id, milestone_name)
        if not milestone:
            logger.error(f"Cannot update: milestone '{milestone_name}' not found for loan {loan_id}")
            return False
        
        milestone_id = milestone.get("id")
        
        # Prepare update data
        update_data = {
            "status": status,
            "statusDate": datetime.now().isoformat()
        }
        
        if comment:
            update_data["comment"] = comment
        
        # PATCH /encompass/v1/loans/{loanId}/milestones/{milestoneId}
        http_client = _get_http_client()
        token = http_client.auth_manager.get_client_credentials_token()
        
        resp = http_client.request(
            method="PATCH",
            path=f"/encompass/v1/loans/{loan_id}/milestones/{milestone_id}",
            token=token,
            json_body=update_data
        )
        
        if resp.status_code in [200, 204]:
            logger.info(f"Updated milestone '{milestone_name}' to '{status}' for loan {loan_id}")
            return True
        else:
            logger.error(f"Failed to update milestone: {resp.status_code} - {resp.text}")
            return False
        
    except Exception as e:
        logger.error(f"Error updating milestone for {loan_id}: {e}")
        return False


def add_milestone_log(
    loan_id: str,
    milestone_name: str,
    comment: str,
    done_by: Optional[str] = None
) -> bool:
    """
    Add a log entry to a milestone.
    
    Args:
        loan_id: The loan GUID
        milestone_name: Name of milestone
        comment: Comment to add
        done_by: Optional user who performed the action
        
    Returns:
        True if successful, False otherwise
    """
    if not MCP_HTTP_CLIENT_AVAILABLE:
        logger.warning("MCP HTTP client not available. Cannot add milestone log.")
        return False
    
    try:
        milestone = get_milestone_by_name(loan_id, milestone_name)
        if not milestone:
            return False
        
        milestone_id = milestone.get("id")
        
        # Prepare log data
        log_data = {
            "comment": comment,
            "date": datetime.now().isoformat()
        }
        
        if done_by:
            log_data["doneBy"] = done_by
        
        # POST /encompass/v1/loans/{loanId}/milestones/{milestoneId}/logs
        http_client = _get_http_client()
        token = http_client.auth_manager.get_client_credentials_token()
        
        resp = http_client.request(
            method="POST",
            path=f"/encompass/v1/loans/{loan_id}/milestones/{milestone_id}/logs",
            token=token,
            json_body=log_data
        )
        
        if resp.status_code in [200, 201]:
            logger.info(f"Added log to milestone '{milestone_name}' for loan {loan_id}")
            return True
        else:
            logger.error(f"Failed to add milestone log: {resp.status_code} - {resp.text}")
            return False
        
    except Exception as e:
        logger.error(f"Error adding milestone log for {loan_id}: {e}")
        return False


# =============================================================================
# 2. DOCUMENTS & DATA EXTRACTION TOOLS
# =============================================================================

def list_required_documents(loan_id: str) -> List[str]:
    """
    Get list of required documents based on loan type and program.
    
    Args:
        loan_id: The loan GUID
        
    Returns:
        List of required document categories
    """
    client = _get_encompass_client()
    
    try:
        # Get loan context to determine requirements
        context = get_loan_context(loan_id)
        loan_type = context.get("loan_type", "")
        loan_program = context.get("loan_program", "")
        state = context.get("state", "")
        
        # Base required documents (always needed)
        required_docs = [
            "1003 - Uniform Residential Loan Application",
            "Approval Final",
            "MI Certificate",
            "Driver's License - Borrower",
            "SSN Card - Borrower",
        ]
        
        # Add program-specific documents
        if "FHA" in loan_type.upper():
            required_docs.extend([
                "FHA Case Assignment",
                "FHA Approval Letter",
            ])
        
        if "VA" in loan_type.upper():
            required_docs.extend([
                "VA Certificate of Eligibility",
                "VA Funding Fee Documentation",
            ])
        
        if "USDA" in loan_type.upper():
            required_docs.extend([
                "USDA Eligibility Documentation",
                "USDA Case Assignment",
            ])
        
        # Add state-specific documents
        if state in ["TX", "CA", "NV", "CO"]:
            required_docs.append(f"{state} State-Specific Disclosures")
        
        logger.info(f"Required documents for {loan_id}: {len(required_docs)} documents")
        return required_docs
        
    except Exception as e:
        logger.error(f"Error listing required documents for {loan_id}: {e}")
        return []


def list_loan_documents(loan_id: str) -> List[Dict[str, Any]]:
    """
    List all documents/attachments in a loan's eFolder using MCP server.
    
    Args:
        loan_id: The loan GUID
        
    Returns:
        List of document dictionaries with metadata
    """
    if not MCP_HTTP_CLIENT_AVAILABLE:
        error_msg = "MCP HTTP client not available. Cannot list documents."
        logger.error(error_msg)
        raise ImportError(error_msg)
    
    try:
        http_client = _get_http_client()
        token = http_client.auth_manager.get_client_credentials_token()
        
        # GET /encompass/v3/loans/{loanId}/attachments
        resp = http_client.request(
            method="GET",
            path=f"/encompass/v3/loans/{loan_id}/attachments",
            token=token
        )
        
        if resp.status_code == 200:
            documents = resp.json()
            logger.info(f"Found {len(documents)} documents for loan {loan_id}")
            return documents
        else:
            error_msg = f"Failed to list documents: {resp.status_code} - {resp.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
            
    except Exception as e:
        logger.error(f"Error listing documents for {loan_id}: {e}")
        raise  # Re-raise exception so fallback can be triggered


def download_document_from_efolder(loan_id: str, attachment_id: str, save_path: Optional[Path] = None) -> Optional[str]:
    """
    Download a single document from Encompass eFolder using MCP server.
    
    Uses the Encompass v3 API:
    1. POST /attachmentDownloadUrl → get signed URL + auth header
    2. GET signed URL → download actual file bytes
    
    Args:
        loan_id: The loan GUID
        attachment_id: The attachment ID to download
        save_path: Optional path to save the document. If None, saves to /tmp/loan_docs/{loan_id}/
        
    Returns:
        Path to downloaded file, or None if failed
    """
    if not MCP_HTTP_CLIENT_AVAILABLE:
        logger.error("MCP HTTP client not available. Cannot download document.")
        return None
    
    try:
        http_client = _get_http_client()
        token = http_client.auth_manager.get_client_credentials_token()
        
        # Step 1: Get signed download URL and auth header
        resp = http_client.request(
            method="POST",
            path=f"/encompass/v3/loans/{loan_id}/attachmentDownloadUrl",
            token=token,
            json_body={"attachments": [attachment_id]}
        )
        
        if resp.status_code != 200:
            logger.error(f"Failed to get download URL: {resp.status_code} - {resp.text}")
            return None
        
        data = resp.json()
        attachments = data.get("attachments", [])
        if not attachments:
            logger.error(f"No download information returned for attachment {attachment_id}")
            return None
        
        attachment_info = attachments[0]
        
        # Extract download URL (check multiple possible field names)
        # Based on encompass-mcp-server/test_download_documents.py
        download_url = (
            attachment_info.get("downloadUrl") or  # Primary field name
            attachment_info.get("url") or          # Alternative field name
            (attachment_info.get("originalUrls", [None])[0] if attachment_info.get("originalUrls") else None) or  # Legacy
            (attachment_info.get("pages", [{}])[0].get("url") if attachment_info.get("pages") else None)  # Page-based
        )
        
        if not download_url:
            logger.error(f"No download URL found in response for {attachment_id}. Available fields: {list(attachment_info.keys())}")
            return None
        
        # Step 2: Download the actual file from signed URL
        import requests
        download_headers = {}
        
        # Cloud Storage requires authorization header
        authorization_header = attachment_info.get("authorizationHeader")
        if authorization_header:
            download_headers["Authorization"] = authorization_header
        
        doc_response = requests.get(download_url, headers=download_headers, timeout=60)
        
        if doc_response.status_code != 200:
            logger.error(f"Failed to download file: {doc_response.status_code}")
            return None
        
        # Step 3: Save to file
        if save_path is None:
            temp_dir = Path(f"/tmp/loan_docs/{loan_id}")
            temp_dir.mkdir(parents=True, exist_ok=True)
            save_path = temp_dir / f"{attachment_id}.pdf"
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(doc_response.content)
        
        logger.info(f"Downloaded document {attachment_id} to {save_path} ({len(doc_response.content)} bytes)")
        return str(save_path)
        
    except Exception as e:
        logger.error(f"Error downloading document {attachment_id} from {loan_id}: {e}")
        return None


def download_documents(loan_id: str, categories: List[str] = None) -> List[Dict[str, Any]]:
    """
    Download documents from Encompass eFolder using MCP server.
    
    Args:
        loan_id: The loan GUID
        categories: Optional list of document categories to filter by.
                   If None, downloads all documents.
        
    Returns:
        List of document dictionaries with metadata and local file paths
    """
    try:
        # Get all documents for the loan
        documents = list_loan_documents(loan_id)
        
        if not documents:
            logger.warning(f"No documents found for loan {loan_id}")
            return []
        
        logger.info(f"Found {len(documents)} documents for loan {loan_id}")
        
        # Filter by categories if specified
        if categories:
            # Normalize categories for comparison
            categories_lower = [cat.lower() for cat in categories]
            documents = [
                doc for doc in documents 
                if any(cat in doc.get("title", "").lower() for cat in categories_lower)
            ]
            logger.info(f"Filtered to {len(documents)} documents matching categories")
        
        # Download each document
        downloaded_docs = []
        
        for doc in documents:
            try:
                # API returns "id" not "attachmentId"
                doc_id = doc.get("id", doc.get("attachmentId", ""))
                doc_title = doc.get("title", "")
                
                if not doc_id:
                    logger.warning(f"Skipping document with no ID: {doc_title}")
                    continue
                
                # Download using MCP server
                file_path_str = download_document_from_efolder(loan_id, doc_id)
                
                if not file_path_str:
                    logger.warning(f"Failed to download document: {doc_title} ({doc_id})")
                    continue
                
                file_path = Path(file_path_str)
                file_size = file_path.stat().st_size
                
                downloaded_docs.append({
                    "doc_id": doc_id,
                    "category": doc_title,
                    "file_path": str(file_path),
                    "file_name": f"{doc_id}.pdf",
                    "file_size_bytes": file_size,
                    "upload_date": doc.get("dateCreated", ""),
                })
                
            except Exception as e:
                logger.error(f"Error downloading document {doc.get('title', 'unknown')}: {e}")
                continue
        
        logger.info(f"Successfully downloaded {len(downloaded_docs)} documents for {loan_id}")
        return downloaded_docs
        
    except Exception as e:
        logger.error(f"Error downloading documents for {loan_id}: {e}")
        return []


def extract_entities_from_docs(loan_id: str, docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract entities from documents using LandingAI OCR.
    
    This creates the canonical doc_context JSON that all other agents consume.
    
    Args:
        loan_id: The loan GUID
        docs: List of document dictionaries from download_documents
        
    Returns:
        Comprehensive doc_context dictionary with all extracted entities
    """
    client = _get_encompass_client()
    
    try:
        # Initialize doc_context structure
        # FULLY DYNAMIC doc_context - no hardcoded field names
        doc_context = {
            "extracted_by_document": {},  # Keyed by document category
            "all_mapped_fields": {},      # All mapped fields (field_id -> {value, source, field_name})
            "all_pending_fields": {},     # All pending fields (field_name -> {value, status, source})
            "all_unmapped_fields": {},    # All unmapped fields (field_name -> {value, status, source})
            "metadata": {
                "loan_id": loan_id,
                "extraction_date": datetime.now().isoformat(),
                "source_documents": [],
                "extraction_results": {}
            }
        }
        
        # Process each document
        for doc in docs:
            category = doc.get("category", "")
            file_path = doc.get("file_path", "")
            doc_id = doc.get("doc_id", "")
            
            if not file_path or not Path(file_path).exists():
                logger.warning(f"Skipping document with invalid path: {category}")
                continue
            
            doc_context["metadata"]["source_documents"].append(category)
            
            logger.info(f"Extracting entities from: {category}")
            
            try:
                # Extract based on document type (DYNAMIC - no hardcoding)
                extracted = None
                
                if "1003" in category.upper():
                    extracted = _extract_from_1003(file_path, client)
                    
                elif "APPROVAL" in category.upper() or "FINAL" in category.upper():
                    extracted = _extract_from_approval(file_path, client)
                    
                elif "MI" in category.upper() and "CERTIFICATE" in category.upper():
                    extracted = _extract_from_mi_cert(file_path, client)
                    
                elif "LICENSE" in category.upper() or "SSN" in category.upper() or "ID" in category.upper():
                    extracted = _extract_from_id_docs(file_path, client)
                    
                elif "FHA" in category.upper():
                    extracted = _extract_from_fha_docs(file_path, client)
                    
                elif "VA" in category.upper():
                    extracted = _extract_from_va_docs(file_path, client)
                    
                elif "USDA" in category.upper():
                    extracted = _extract_from_usda_docs(file_path, client)
                    
                else:
                    # Try generic extraction for other document types
                    logger.info(f"Attempting generic extraction for: {category}")
                    extracted = _extract_using_csv_schema(file_path, category, client)
                
                # Process extraction results (DYNAMIC - aggregates all fields)
                if extracted and extracted.get("mapped_fields"):
                    # Store per-document results
                    doc_context["extracted_by_document"][category] = extracted
                    
                    # Aggregate mapped fields
                    for field_name, field_info in extracted.get("mapped_fields", {}).items():
                        field_id = field_info.get("encompass_field_id")
                        value = field_info.get("value")
                        if field_id and value:
                            # Store with source info
                            doc_context["all_mapped_fields"][field_id] = {
                                "value": value,
                                "source_document": category,
                                "field_name": field_name
                            }
                    
                    # Aggregate pending fields
                    for field_name, field_info in extracted.get("pending_fields", {}).items():
                        doc_context["all_pending_fields"][field_name] = {
                            **field_info,
                            "source_document": category
                        }
                    
                    # Aggregate unmapped fields
                    for field_name, field_info in extracted.get("unmapped_fields", {}).items():
                        doc_context["all_unmapped_fields"][field_name] = {
                            **field_info,
                            "source_document": category
                        }
                    
                    doc_context["metadata"]["extraction_results"][category] = {
                        "status": "success",
                        "mapped_fields": len(extracted.get("mapped_fields", {})),
                        "pending_fields": len(extracted.get("pending_fields", {})),
                        "unmapped_fields": len(extracted.get("unmapped_fields", {}))
                    }
                else:
                    # No extraction or no mappings found
                    doc_context["metadata"]["extraction_results"][category] = {
                        "status": "skipped",
                        "reason": "No extraction schema or no mappings"
                    }
                    
            except Exception as e:
                logger.error(f"Error extracting from {category}: {e}")
                doc_context["metadata"]["extraction_results"][category] = {
                    "status": "error",
                    "error": str(e)
                }
                continue
        
        total_mapped = len(doc_context["all_mapped_fields"])
        total_pending = len(doc_context["all_pending_fields"])
        total_unmapped = len(doc_context["all_unmapped_fields"])
        
        logger.info(f"Extracted entities from {len(docs)} documents")
        logger.info(f"Field summary - Mapped: {total_mapped}, Pending: {total_pending}, Unmapped: {total_unmapped}")
        
        return doc_context
        
    except Exception as e:
        logger.error(f"Error extracting entities from documents: {e}")
        raise


def _extract_using_csv_schema(
    file_path: str, 
    document_type: str, 
    client: EncompassConnect
) -> Dict[str, Any]:
    """Extract data from document using CSV-driven schema (fully dynamic).
    
    Uses the ACTUAL working implementation from preparation_agent with:
    - Retry logic for timeouts and rate limits
    - Exponential backoff
    - Proper error handling
    - Timing metrics
    
    This function uses the DrawingDoc Verifications.csv to dynamically
    generate extraction schemas and map fields - NO HARDCODED FIELD NAMES.
    
    Args:
        file_path: Path to the PDF file
        document_type: Type of document (e.g., "Final 1003", "W-2")
        client: Encompass client for extraction
        
    Returns:
        Dictionary with extracted data, field mappings categorized as:
        - mapped_fields: Fields with confirmed Encompass field IDs
        - pending_fields: Fields with "TBD" mapping
        - unmapped_fields: Fields with no mapping
    """
    import time
    import os
    
    if not CSV_EXTRACTION_AVAILABLE:
        logger.warning("CSV extraction not available, returning empty dict")
        return {}
    
    logger.info(f"[EXTRACT] Starting - Type: {document_type}, File: {os.path.basename(file_path)}")
    
    try:
        # Get extraction schema from CSV
        schema = get_extraction_schema(document_type)
        
        if not schema:
            logger.warning(f"[EXTRACT] No schema found for {document_type}")
            return {
                "error": f"No extraction schema for document type: {document_type}",
                "document_type": document_type,
            }
        
        # Read the file
        with open(file_path, 'rb') as f:
            document_bytes = f.read()
        
        file_size_kb = len(document_bytes) / 1024
        file_size_mb = file_size_kb / 1024
        
        # Adjust timeout based on file size (larger files need more time)
        # Base timeout: 120s, add 30s per MB over 1MB
        base_timeout = 120
        size_adjusted_timeout = base_timeout + (max(0, file_size_mb - 1) * 30)
        max_timeout = 300  # Cap at 5 minutes
        effective_timeout = min(size_adjusted_timeout, max_timeout)
        
        logger.info(f"[EXTRACT] File size: {file_size_kb:.2f} KB ({file_size_mb:.2f} MB), Timeout: {effective_timeout}s")
        
        # Retry logic for timeouts and rate limits
        max_retries = 3
        retry_delay = 5  # Initial delay in seconds
        
        start_time = time.time()
        last_exception = None
        
        for attempt in range(1, max_retries + 1):
            try:
                result = client.extract_document_data(
                    document_bytes=document_bytes,
                    schema=schema,
                    doc_type=document_type,
                    filename=f"{document_type.lower().replace(' ', '_')}.pdf",
                )
                extraction_time = time.time() - start_time
                break  # Success, exit retry loop
                
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()
                
                # Check if it's a timeout or rate limit error
                is_timeout = 'timeout' in error_str or 'timed out' in error_str
                is_rate_limit = 'rate limit' in error_str or '429' in error_str or 'too many requests' in error_str
                
                if attempt < max_retries and (is_timeout or is_rate_limit):
                    # Exponential backoff: 5s, 10s, 20s
                    delay = retry_delay * (2 ** (attempt - 1))
                    logger.warning(f"[EXTRACT] Attempt {attempt}/{max_retries} failed ({type(e).__name__}). Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    # Last attempt or non-retryable error
                    extraction_time = time.time() - start_time
                    logger.error(f"[EXTRACT] Extraction failed after {attempt} attempts: {e}")
                    raise
        else:
            # All retries exhausted
            extraction_time = time.time() - start_time
            error_msg = f"Extraction failed after {max_retries} attempts"
            if last_exception:
                error_msg += f": {last_exception}"
            raise Exception(error_msg) from last_exception
        
        extracted_data = result.get("extracted_schema", {})
        
        # Get field mappings for this document type
        all_mappings = get_all_mappings_for_document(document_type)
        
        logger.info(f"[EXTRACT] Looking up mappings for document_type: '{document_type}'")
        logger.info(f"[EXTRACT] Available mappings: {list(all_mappings.keys())}")
        logger.info(f"[EXTRACT] Extracted fields: {list(extracted_data.keys())}")
        
        # Categorize fields by mapping status (DYNAMIC - no hardcoding)
        mapped_fields = {}
        unmapped_fields = {}
        pending_fields = {}
        
        for field_name, field_value in extracted_data.items():
            # Look up field ID dynamically from CSV
            field_id = get_field_mapping(document_type, field_name)
            
            if field_id and field_id != "TBD":
                # Field has confirmed mapping
                mapped_fields[field_name] = {
                    "value": field_value,
                    "encompass_field_id": field_id,
                }
                logger.debug(f"[EXTRACT] Mapped {field_name} -> {field_id} = {field_value}")
            elif field_id == "TBD":
                # Field mapping pending
                pending_fields[field_name] = {
                    "value": field_value,
                    "status": "mapping_pending",
                }
            else:
                # No mapping found
                unmapped_fields[field_name] = {
                    "value": field_value,
                    "status": "no_mapping",
                }
                logger.debug(f"[EXTRACT] No mapping for {field_name} (field_id: {field_id})")
        
        logger.info(f"[EXTRACT] Success - {len(extracted_data)} fields in {extraction_time:.2f}s")
        logger.info(f"[EXTRACT] Mappings - Ready: {len(mapped_fields)}, Pending: {len(pending_fields)}, Unmapped: {len(unmapped_fields)}")
        
        return {
            "extracted_data": extracted_data,
            "mapped_fields": mapped_fields,
            "pending_fields": pending_fields,
            "unmapped_fields": unmapped_fields,
            "document_type": document_type,
            "all_mappings": all_mappings,
            "extraction_time_seconds": round(extraction_time, 2),
        }
        
    except Exception as e:
        logger.error(f"[EXTRACT] Error extracting from {document_type}: {e}")
        return {
            "error": str(e),
            "document_type": document_type,
        }


def _extract_from_1003(file_path: str, client: EncompassConnect) -> Dict[str, Any]:
    """Extract data from 1003 form using CSV-driven schema (fully dynamic)."""
    # Try different 1003 document type names
    for doc_type in ["Final 1003", "1003", "Initial 1003"]:
        result = _extract_using_csv_schema(file_path, doc_type, client)
        if result and result.get("mapped_fields"):
            # Return fully dynamic result - NO hardcoded field names
            return result
    
    # Fallback to empty if no extraction worked
    logger.warning("Could not extract from 1003 using any document type variant")
    return {}


def _extract_from_approval(file_path: str, client: EncompassConnect) -> Dict[str, Any]:
    """Extract data from Approval Final document using CSV-driven schema (fully dynamic)."""
    # Try different approval document type names
    for doc_type in ["Approval Final", "Final Approval", "Approval Letter", "Underwriting Approval"]:
        result = _extract_using_csv_schema(file_path, doc_type, client)
        if result and result.get("mapped_fields"):
            # Return fully dynamic result - NO hardcoded field names
            return result
    
    logger.warning("Could not extract from Approval document using any document type variant")
    return {}


def _extract_from_1003(file_path: str, client: EncompassConnect) -> Dict[str, Any]:
    """Extract data from 1003 form using CSV-driven schema (fully dynamic - NO hardcoded fields)."""
    # Try different 1003 document type names
    for doc_type in ["Final 1003", "1003", "Initial 1003"]:
        result = _extract_using_csv_schema(file_path, doc_type, client)
        if result and result.get("mapped_fields"):
            # Return fully dynamic result
            return result
    
    logger.warning("Could not extract from 1003 using any document type variant")
    return {}


def _extract_from_approval(file_path: str, client: EncompassConnect) -> Dict[str, Any]:
    """Extract data from Approval Final document using CSV-driven schema (fully dynamic - NO hardcoded fields)."""
    # Try different approval document type names
    for doc_type in ["Approval Final", "Final Approval", "Approval Letter", "Underwriting Approval"]:
        result = _extract_using_csv_schema(file_path, doc_type, client)
        if result and result.get("mapped_fields"):
            return result
    
    logger.warning("Could not extract from Approval document using any document type variant")
    return {}


def _extract_from_mi_cert(file_path: str, client: EncompassConnect) -> Dict[str, Any]:
    """Extract data from MI Certificate using CSV-driven schema (fully dynamic - NO hardcoded fields)."""
    for doc_type in ["Mortgage Insurance Certificate", "MI Certificate", "Mortgage Insurance details"]:
        result = _extract_using_csv_schema(file_path, doc_type, client)
        if result and result.get("mapped_fields"):
            return result
    
    return {}


def _extract_from_id_docs(file_path: str, client: EncompassConnect) -> Dict[str, Any]:
    """Extract data from ID documents using CSV-driven schema (fully dynamic - NO hardcoded fields)."""
    # Determine document type from filename
    if "license" in file_path.lower():
        doc_types = ["Driver's License", "ID"]
    else:
        doc_types = ["ID", "SSN Card", "ID Customer Identification"]
    
    for doc_type in doc_types:
        result = _extract_using_csv_schema(file_path, doc_type, client)
        if result and result.get("mapped_fields"):
            return result
    
    return {}


def _extract_from_fha_docs(file_path: str, client: EncompassConnect) -> Dict[str, Any]:
    """Extract data from FHA documents using CSV-driven schema (fully dynamic - NO hardcoded fields)."""
    for doc_type in ["FHA Case assignment document", "FHA Document", "FHA Case Assignment"]:
        result = _extract_using_csv_schema(file_path, doc_type, client)
        if result and result.get("mapped_fields"):
            return result
    
    return {}


def _extract_from_va_docs(file_path: str, client: EncompassConnect) -> Dict[str, Any]:
    """Extract data from VA documents using CSV-driven schema (fully dynamic - NO hardcoded fields)."""
    for doc_type in ["VA Certificate of Eligibility", "VA Document", "VA COE"]:
        result = _extract_using_csv_schema(file_path, doc_type, client)
        if result and result.get("mapped_fields"):
            return result
    
    return {}


def _extract_from_usda_docs(file_path: str, client: EncompassConnect) -> Dict[str, Any]:
    """Extract data from USDA documents using CSV-driven schema (fully dynamic - NO hardcoded fields)."""
    for doc_type in ["USDA Eligibility Documentation", "USDA Document", "USDA Case Assignment"]:
        result = _extract_using_csv_schema(file_path, doc_type, client)
        if result and result.get("mapped_fields"):
            return result
    
    return {}


# =============================================================================
# 3. ENCOMPASS FIELD IO TOOLS
# =============================================================================

def read_fields(loan_id: str, field_ids: List[str]) -> Dict[str, Any]:
    """
    Read multiple fields from Encompass using Field Reader API.
    
    Two-tier approach:
    1. Try MCP server's HTTP client first (uses server's OAuth)
    2. Fall back to EncompassConnect if MCP fails
    
    Args:
        loan_id: The loan GUID
        field_ids: List of Encompass field IDs to read
        
    Returns:
        Dictionary mapping field_id -> value
    """
    mcp_error = None
    
    # Tier 1: Try MCP server's HTTP client
    if MCP_HTTP_CLIENT_AVAILABLE:
        try:
            logger.info(f"[read_fields] Tier 1: Trying MCP HTTP client for {len(field_ids)} fields...")
            http_client = _get_http_client()
            token = http_client.auth_manager.get_client_credentials_token()
            
            response = http_client.request(
                method="POST",
                path=f"/encompass/v3/loans/{loan_id}/fieldReader",
                token=token,
                params={"invalidFieldBehavior": "Exclude"},
                headers={"Content-Type": "application/json"},
                json_body=field_ids
            )
            
            if response.status_code == 200:
                fields = response.json()
                logger.info(f"[read_fields] ✓ MCP: Read {len(fields)} fields from loan {loan_id}")
                return fields
            else:
                mcp_error = f"MCP field read failed (status {response.status_code}): {response.text}"
                logger.warning(f"[read_fields] {mcp_error}")
                
        except Exception as e:
            mcp_error = str(e)
            logger.warning(f"[read_fields] MCP failed: {mcp_error}")
    else:
        mcp_error = "MCP HTTP client not available"
        logger.info(f"[read_fields] {mcp_error}")
    
    # Tier 2: Fall back to EncompassConnect
    logger.info(f"[read_fields] Tier 2: Falling back to EncompassConnect...")
    try:
        client = _get_encompass_client()
        fields = client.get_field(loan_id, field_ids)
        logger.info(f"[read_fields] ✓ EncompassConnect: Read {len(fields)} fields from loan {loan_id}")
        return fields
        
    except Exception as e:
        fallback_error = str(e)
        logger.error(f"[read_fields] ✗ EncompassConnect fallback also failed: {fallback_error}")
        # Raise with both errors for debugging
        raise RuntimeError(f"Field read failed. MCP: {mcp_error}. EncompassConnect: {fallback_error}")


def write_fields(loan_id: str, updates: List[Dict[str, Any]]) -> bool:
    """
    Write multiple fields to Encompass.
    
    Two-tier approach:
    1. Try MCP server's HTTP client first (PATCH loan)
    2. Fall back to EncompassConnect if MCP fails
    
    Args:
        loan_id: The loan GUID
        updates: List of dicts with 'field_id' and 'value' keys
                Example: [{"field_id": "4000", "value": "John"}]
        
    Returns:
        True if successful, False otherwise
    """
    # Check if writes are enabled
    if not os.getenv("ENABLE_ENCOMPASS_WRITES", "false").lower() == "true":
        logger.warning(f"[write_fields] Encompass writes disabled. Would have written {len(updates)} fields to {loan_id}")
        return False
    
    mcp_error = None
    
    # Tier 1: Try MCP server's HTTP client (batch PATCH)
    if MCP_HTTP_CLIENT_AVAILABLE:
        try:
            logger.info(f"[write_fields] Tier 1: Trying MCP HTTP client for {len(updates)} fields...")
            http_client = _get_http_client()
            token = http_client.auth_manager.get_client_credentials_token()
            
            # Convert updates to loan PATCH format
            # Format: { "fieldId": value, ... }
            patch_body = {}
            for update in updates:
                field_id = update.get("field_id") or update.get("fieldId")
                value = update.get("value")
                if field_id:
                    patch_body[field_id] = value
            
            response = http_client.request(
                method="PATCH",
                path=f"/encompass/v3/loans/{loan_id}",
                token=token,
                headers={"Content-Type": "application/json"},
                json_body=patch_body
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"[write_fields] ✓ MCP: Wrote {len(updates)} fields to loan {loan_id}")
                return True
            else:
                mcp_error = f"MCP field write failed (status {response.status_code}): {response.text}"
                logger.warning(f"[write_fields] {mcp_error}")
                
        except Exception as e:
            mcp_error = str(e)
            logger.warning(f"[write_fields] MCP failed: {mcp_error}")
    else:
        mcp_error = "MCP HTTP client not available"
        logger.info(f"[write_fields] {mcp_error}")
    
    # Tier 2: Fall back to EncompassConnect
    logger.info(f"[write_fields] Tier 2: Falling back to EncompassConnect...")
    try:
        client = _get_encompass_client()
        
        # Write each field individually (EncompassConnect's approach)
        success_count = 0
        for update in updates:
            field_id = update.get("field_id") or update.get("fieldId")
            value = update.get("value")
            if field_id:
                try:
                    if client.write_field(loan_id, field_id, value):
                        success_count += 1
                except Exception as field_error:
                    logger.warning(f"[write_fields] Failed to write field {field_id}: {field_error}")
        
        logger.info(f"[write_fields] ✓ EncompassConnect: Wrote {success_count}/{len(updates)} fields to loan {loan_id}")
        return success_count == len(updates)
        
    except Exception as e:
        fallback_error = str(e)
        logger.error(f"[write_fields] ✗ EncompassConnect fallback also failed: {fallback_error}")
        return False


# =============================================================================
# 4. COMPLIANCE & VALIDATION TOOLS
# =============================================================================

def run_compliance_check(loan_id: str, check_type: str = "Mavent") -> str:
    """
    Run compliance check (Mavent or other).
    
    Args:
        loan_id: The loan GUID
        check_type: Type of compliance check ("Mavent", etc.)
        
    Returns:
        Job ID or run identifier
    """
    # TODO: Implement actual Mavent integration
    logger.info(f"Running {check_type} compliance check for {loan_id}")
    
    # Placeholder: return a mock job ID
    job_id = f"{check_type}_{loan_id}_{datetime.now().timestamp()}"
    return job_id


def get_compliance_results(loan_id: str, job_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get compliance check results.
    
    Args:
        loan_id: The loan GUID
        job_id: Optional job ID from run_compliance_check
        
    Returns:
        Dictionary containing:
        - status: "pass", "fail", or "warning"
        - issues: List of issue dicts
        - run_date: Timestamp
        - report_url: URL to full report
    """
    # TODO: Implement actual Mavent results retrieval
    logger.info(f"Getting compliance results for {loan_id}")
    
    # Placeholder: return mock results
    return {
        "status": "pass",
        "issues": [],
        "run_date": datetime.now().isoformat(),
        "report_url": f"https://mavent.example.com/reports/{job_id}"
    }


# =============================================================================
# 5. DOCS DRAW & DISTRIBUTION TOOLS
# =============================================================================

def order_docs(loan_id: str) -> Dict[str, Any]:
    """
    Trigger docs draw / generate closing package.
    
    Args:
        loan_id: The loan GUID
        
    Returns:
        Dictionary containing:
        - success: bool
        - doc_package_id: Package identifier
        - generated_date: Timestamp
        - error: Error message if failed
    """
    # TODO: Implement actual docs ordering through Encompass API
    logger.info(f"Ordering docs for {loan_id}")
    
    try:
        # Placeholder implementation
        package_id = f"PKG_{loan_id}_{datetime.now().timestamp()}"
        
        return {
            "success": True,
            "doc_package_id": package_id,
            "generated_date": datetime.now().isoformat(),
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Error ordering docs for {loan_id}: {e}")
        return {
            "success": False,
            "doc_package_id": None,
            "generated_date": None,
            "error": str(e)
        }


def send_closing_package(loan_id: str, recipients: Dict[str, str]) -> Dict[str, Any]:
    """
    Send closing package to recipients.
    
    Args:
        loan_id: The loan GUID
        recipients: Dict mapping role -> email
                   Example: {"title_company": "email@title.com", ...}
        
    Returns:
        Dictionary containing:
        - success: bool
        - sent_to: List of successfully sent emails
        - failed: List of failed emails
        - tracking_ids: Dict mapping email -> tracking ID
    """
    # TODO: Implement actual email/distribution system
    logger.info(f"Sending closing package for {loan_id} to {len(recipients)} recipients")
    
    try:
        sent_to = []
        failed = []
        tracking_ids = {}
        
        for role, email in recipients.items():
            # Placeholder: simulate sending
            if email and "@" in email:
                sent_to.append(email)
                tracking_ids[email] = f"TRK_{datetime.now().timestamp()}"
            else:
                failed.append(email)
        
        return {
            "success": len(failed) == 0,
            "sent_to": sent_to,
            "failed": failed,
            "tracking_ids": tracking_ids
        }
        
    except Exception as e:
        logger.error(f"Error sending closing package for {loan_id}: {e}")
        return {
            "success": False,
            "sent_to": [],
            "failed": list(recipients.values()),
            "tracking_ids": {}
        }


# =============================================================================
# 6. ISSUE LOGGING TOOL
# =============================================================================

def log_issue(
    loan_id: str,
    severity: str,
    message: str,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Log an issue for human review.
    
    Args:
        loan_id: The loan GUID
        severity: "critical", "high", "medium", "low"
        message: Issue description
        context: Additional context (field IDs, values, etc.)
        
    Returns:
        Issue ID for tracking
    """
    issue_id = f"ISSUE_{loan_id}_{datetime.now().timestamp()}"
    
    issue_data = {
        "issue_id": issue_id,
        "loan_id": loan_id,
        "severity": severity,
        "message": message,
        "context": context or {},
        "logged_at": datetime.now().isoformat(),
        "resolved": False
    }
    
    # Log to file and logger
    logger.warning(f"[{severity.upper()}] Issue logged for {loan_id}: {message}")
    
    # Save to issues file
    issues_dir = Path("/tmp/loan_issues")
    issues_dir.mkdir(parents=True, exist_ok=True)
    
    issue_file = issues_dir / f"{loan_id}_issues.json"
    
    # Load existing issues
    existing_issues = []
    if issue_file.exists():
        with open(issue_file, "r") as f:
            existing_issues = json.load(f)
    
    # Add new issue
    existing_issues.append(issue_data)
    
    # Save back
    with open(issue_file, "w") as f:
        json.dump(existing_issues, f, indent=2)
    
    logger.info(f"Issue {issue_id} logged to {issue_file}")
    
    return issue_id


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_all_tools():
    """Get dictionary of all primitive tools for easy access."""
    return {
        # Loan context & workflow
        "get_loan_context": get_loan_context,
        "update_milestone": update_milestone,
        # Documents & extraction
        "list_required_documents": list_required_documents,
        "download_documents": download_documents,
        "extract_entities_from_docs": extract_entities_from_docs,
        # Encompass IO
        "read_fields": read_fields,
        "write_fields": write_fields,
        # Compliance
        "run_compliance_check": run_compliance_check,
        "get_compliance_results": get_compliance_results,
        # Distribution
        "order_docs": order_docs,
        "send_closing_package": send_closing_package,
        # Issue logging
        "log_issue": log_issue,
    }



