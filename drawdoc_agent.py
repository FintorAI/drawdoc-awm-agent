"""DrawDoc-AWM Agent - Document Drawing and Annotation Agent.

This agent is specialized for drawing and annotating documents for AWM
(Asset and Wealth Management) workflows with Encompass integration.
"""

# ==============================================================================
# DEVELOPMENT MODE CONFIGURATION
# ==============================================================================
# Set USE_LOCAL_COPILOTAGENT=true in .env to use local development version
# Set USE_LOCAL_COPILOTAGENT=false (or omit) to use PyPI version
#
# Local version enables testing unreleased features and bug fixes before
# deploying to PyPI.
#
# Installation (one-time setup):
#   pip install -e /Users/masoud/Desktop/WORK/DeepCopilotAgent2/baseCopilotAgent
# ==============================================================================

import os
import sys
import logging
from pathlib import Path
from typing import Any, Literal, Optional
from dotenv import load_dotenv

# Load environment variables first so we can check USE_LOCAL_COPILOTAGENT
load_dotenv(Path(__file__).parent / ".env")

# Check if we should use local copilotagent
USE_LOCAL = os.getenv("USE_LOCAL_COPILOTAGENT", "false").lower() == "true"

if USE_LOCAL:
    # Add local baseCopilotAgent to path
    local_path = Path(__file__).parent.parent.parent / "baseCopilotAgent" / "src"
    if local_path.exists():
        sys.path.insert(0, str(local_path))
        print(f"🔧 DEV MODE: Using LOCAL copilotagent from {local_path}")
    else:
        print(f"⚠️  LOCAL path not found: {local_path}, falling back to installed version")

# Configure logging to output to terminal/stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True  # Override any existing configuration
)

# Suppress noisy LangGraph infrastructure logs
logging.getLogger('langgraph_runtime_inmem').setLevel(logging.WARNING)
logging.getLogger('langgraph_api').setLevel(logging.WARNING)
logging.getLogger('langgraph').setLevel(logging.WARNING)
logging.getLogger('uvicorn').setLevel(logging.WARNING)
logging.getLogger('watchfiles').setLevel(logging.WARNING)

# Enable AI model response logging for debugging
# Set to INFO to see model responses, WARNING to hide them
AI_DEBUG_MODE = os.getenv("AI_DEBUG_MODE", "false").lower() == "true"
if AI_DEBUG_MODE:
    logging.getLogger('langchain').setLevel(logging.DEBUG)
    logging.getLogger('langchain_anthropic').setLevel(logging.DEBUG)
    logging.getLogger('langchain_core').setLevel(logging.DEBUG)
    print("🐛 AI DEBUG MODE: Model responses will be logged")

logger = logging.getLogger(__name__)

from copilotagent import create_deep_agent, EncompassConnect
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langchain.agents.middleware.types import AgentMiddleware, AgentState
from langgraph.types import Command
from typing import Annotated, TypedDict
from typing_extensions import NotRequired
from datetime import datetime, UTC
from extraction_schemas import get_extraction_schema, list_supported_document_types

# Verify which version is loaded
import copilotagent
if USE_LOCAL and "baseCopilotAgent" in copilotagent.__file__:
    print(f"✅ Using LOCAL copilotagent: {copilotagent.__file__}")
elif not USE_LOCAL and "site-packages" in copilotagent.__file__:
    print(f"✅ Using PyPI copilotagent: {copilotagent.__file__}")
else:
    print(f"⚠️  Unexpected copilotagent location: {copilotagent.__file__}")

# =============================================================================
# TEST DATA - Sample values for tool testing only
# =============================================================================
# NOTE: All real test data (loan IDs, borrower names) are now configured in:
# - DEFAULT_STARTING_MESSAGE (below) - for automatic agent startup
# - planner_prompt.md - for agent instructions
#
# Individual tool tests are disabled - use --demo for full workflow testing
# =============================================================================

# =============================================================================
# DOCREPO S3 STORAGE - Per-client S3 document storage
# =============================================================================

def _create_docrepo_bucket(client_id: str) -> dict[str, Any]:
    """Create an S3 bucket for a client in docRepo.
    
    This is idempotent - if the bucket already exists, it returns success.
    
    Args:
        client_id: The client identifier
        
    Returns:
        Dictionary containing:
        - bucket_created: Boolean indicating if bucket was newly created
        - bucket_exists: Boolean indicating if bucket exists after call
        - client_id: The client ID used
        - bucket_name: The S3 bucket name
        - message: Status message
    """
    import requests
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Get docRepo configuration from environment
    create_api_base = os.getenv("DOCREPO_CREATE_API_BASE", "https://dnobbdlzyb.execute-api.us-west-1.amazonaws.com/prod")
    auth_token = os.getenv("DOCREPO_AUTH_TOKEN", "esfuse-token")
    
    try:
        logger.info(f"[DOCREPO] Creating bucket for client: {client_id}")
        
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{create_api_base}/create-bucket",
            json={"clientId": client_id},
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            bucket_name = result.get("bucketName", "")
            was_created = result.get("created", False)
            
            if was_created:
                logger.info(f"[DOCREPO] Bucket created - {bucket_name}")
            else:
                logger.info(f"[DOCREPO] Bucket already exists - {bucket_name}")
            
            return {
                "bucket_created": was_created,
                "bucket_exists": True,
                "client_id": result.get("clientId", client_id),
                "bucket_name": bucket_name,
                "message": result.get("message", "Bucket ready")
            }
        else:
            logger.error(f"[DOCREPO] Bucket creation failed - Status {response.status_code}: {response.text}")
            return {
                "bucket_created": False,
                "bucket_exists": False,
                "client_id": client_id,
                "error": f"Failed with status {response.status_code}",
                "message": response.text
            }
            
    except Exception as e:
        logger.error(f"[DOCREPO] Exception creating bucket: {e}")
        return {
            "bucket_created": False,
            "bucket_exists": False,
            "client_id": client_id,
            "error": str(e),
            "message": f"Failed to create bucket: {str(e)}"
        }


def _upload_to_docrepo_s3(
    document_bytes: bytes,
    client_id: str,
    doc_id: str,
    data_object: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Upload a document to docRepo S3 storage.
    
    This uploads documents to per-client S3 buckets for persistent storage
    and generates signed URLs for UI access. If the bucket doesn't exist,
    it will be created automatically.
    
    Args:
        document_bytes: The PDF document content as bytes
        client_id: The client identifier (e.g., "docAgent")
        doc_id: The document identifier (e.g., attachment ID)
        data_object: Optional structured data to store with the document
        
    Returns:
        Dictionary containing:
        - s3_uploaded: Boolean indicating success
        - client_id: The client ID used
        - doc_id: The document ID used
        - message: Status message
        - (error if failed)
    """
    import base64
    import requests
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Get docRepo configuration from environment
    put_api_base = os.getenv("DOCREPO_PUT_API_BASE", "https://ekrhupxp1d.execute-api.us-west-1.amazonaws.com/prod")
    auth_token = os.getenv("DOCREPO_AUTH_TOKEN", "esfuse-token")
    
    if not auth_token:
        logger.warning("[DOCREPO] No auth token configured, skipping S3 upload")
        return {
            "s3_uploaded": False,
            "message": "DocRepo auth token not configured in environment"
        }
    
    try:
        # Encode document as base64
        content_base64 = base64.b64encode(document_bytes).decode('utf-8')
        
        # Prepare payload
        payload = {
            "clientId": client_id,
            "docId": doc_id,
            "content_base64": content_base64,
        }
        
        # Add data object if provided
        if data_object:
            payload["dataObject"] = data_object
        
        # Upload to docRepo
        logger.info(f"[DOCREPO] Uploading to S3 - Client: {client_id}, Doc: {doc_id}")
        
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{put_api_base}/put",
            json=payload,
            headers=headers,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"[DOCREPO] Success - Uploaded to S3 for client {client_id}")
            return {
                "s3_uploaded": True,
                "client_id": client_id,
                "doc_id": doc_id,
                "message": result.get("message", "Uploaded"),
                "data_object_stored": result.get("dataObjectStored", False),
            }
        elif response.status_code == 400 and "No S3 bucket" in response.text:
            # Bucket doesn't exist - create it and retry
            logger.info(f"[DOCREPO] Bucket doesn't exist, creating it for client {client_id}")
            bucket_result = _create_docrepo_bucket(client_id)
            
            if not bucket_result.get("bucket_exists"):
                logger.error(f"[DOCREPO] Failed to create bucket: {bucket_result.get('message')}")
                return {
                    "s3_uploaded": False,
                    "client_id": client_id,
                    "doc_id": doc_id,
                    "error": "Failed to create bucket",
                    "message": bucket_result.get("message", "Bucket creation failed")
                }
            
            # Retry upload after creating bucket
            logger.info(f"[DOCREPO] Retrying upload after bucket creation")
            response = requests.post(
                f"{put_api_base}/put",
                json=payload,
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"[DOCREPO] Success - Uploaded to S3 for client {client_id} (after bucket creation)")
                return {
                    "s3_uploaded": True,
                    "client_id": client_id,
                    "doc_id": doc_id,
                    "message": result.get("message", "Uploaded"),
                    "data_object_stored": result.get("dataObjectStored", False),
                    "bucket_created": True,
                }
            else:
                logger.error(f"[DOCREPO] Upload failed after bucket creation - Status {response.status_code}: {response.text}")
                return {
                    "s3_uploaded": False,
                    "client_id": client_id,
                    "doc_id": doc_id,
                    "error": f"Upload failed with status {response.status_code}",
                    "message": response.text
                }
        else:
            logger.error(f"[DOCREPO] Upload failed - Status {response.status_code}: {response.text}")
            return {
                "s3_uploaded": False,
                "client_id": client_id,
                "doc_id": doc_id,
                "error": f"Upload failed with status {response.status_code}",
                "message": response.text
            }
            
    except Exception as e:
        logger.error(f"[DOCREPO] Exception during upload: {e}")
        return {
            "s3_uploaded": False,
            "client_id": client_id,
            "doc_id": doc_id,
            "error": str(e),
            "message": f"Failed to upload to S3: {str(e)}"
        }


def _get_docrepo_signed_url(client_id: str, doc_id: str) -> dict[str, Any]:
    """Get a signed URL for a document from docRepo S3.
    
    Args:
        client_id: The client identifier
        doc_id: The document identifier
        
    Returns:
        Dictionary containing signed URL and document info
    """
    import requests
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Get docRepo configuration from environment
    get_api_base = os.getenv("DOCREPO_GET_API_BASE", "https://m49lxh6q5d.execute-api.us-west-1.amazonaws.com/prod")
    auth_token = os.getenv("DOCREPO_AUTH_TOKEN", "esfuse-token")
    
    try:
        headers = {
            "Authorization": f"Bearer {auth_token}"
        }
        
        response = requests.get(
            f"{get_api_base}/doc",
            params={"clientId": client_id, "docId": doc_id},
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"[DOCREPO] Retrieved signed URL for client {client_id}, doc {doc_id}")
            return {
                "success": True,
                "url": result.get("url"),
                "expires_in_seconds": result.get("expiresInSeconds", 300),
                "has_data_object": result.get("hasDataObject", False),
                "data_object": result.get("dataObject"),
            }
        else:
            logger.error(f"[DOCREPO] Failed to get URL - Status {response.status_code}")
            return {
                "success": False,
                "error": f"Status {response.status_code}",
                "message": response.text
            }
            
    except Exception as e:
        logger.error(f"[DOCREPO] Exception getting URL: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# =============================================================================
# ENCOMPASS TOOLS - Tools for interacting with Encompass API
# =============================================================================


def _find_document_with_llm(documents: list[dict[str, Any]], target_type: str) -> dict[str, Any] | None:
    """Use LLM to semantically match target document type to loan documents.
    
    Args:
        documents: List of document dicts with title, documentId, documentType
        target_type: Target document type (e.g., "W-2", "Bank Statement")
        
    Returns:
        Matching document dict or None if no match found
        
    Example:
        >>> docs = get_loan_documents(loan_id)
        >>> w2_doc = _find_document_with_llm(docs, "W-2")
        >>> print(w2_doc['title'])
    """
    import os
    from langchain_anthropic import ChatAnthropic
    
    if not documents:
        return None
    
    # Initialize LLM
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0  # Deterministic for document matching
    )
    
    # Build document list for LLM with relevant details
    doc_descriptions = []
    for i, doc in enumerate(documents):
        attachments = doc.get('attachments', [])
        doc_descriptions.append(
            f"{i+1}. Title: '{doc.get('title', 'Untitled')}' "
            f"(Type: {doc.get('documentType', 'N/A')}, "
            f"Attachments: {len(attachments)})"
        )
    
    doc_list = "\n".join(doc_descriptions)
    
    # Create prompt for LLM
    prompt = f"""You are helping find a {target_type} document in a loan file.

Here are the available documents:

{doc_list}

Which document number (1-{len(documents)}) most likely contains {target_type} tax forms?

Return ONLY the number (e.g., "5" for document 5). 
If no document clearly matches, return "0"."""
    
    try:
        response = llm.invoke(prompt)
        match_num = int(response.content.strip())
        
        if 1 <= match_num <= len(documents):
            return documents[match_num - 1]
        else:
            return None
            
    except (ValueError, AttributeError) as e:
        # Failed to parse LLM response
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[LLM_MATCH] Failed to parse LLM response: {e}")
        return None


def _get_encompass_client() -> EncompassConnect:
    """Get an initialized Encompass client with credentials from environment variables."""
    return EncompassConnect(
        access_token=os.getenv("ENCOMPASS_ACCESS_TOKEN", ""),
        api_base_url=os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com"),
        credentials={
            "username": os.getenv("ENCOMPASS_USERNAME", ""),
            "password": os.getenv("ENCOMPASS_PASSWORD", ""),
            "client_id": os.getenv("ENCOMPASS_CLIENT_ID", ""),
            "client_secret": os.getenv("ENCOMPASS_CLIENT_SECRET", ""),
            "instance_id": os.getenv("ENCOMPASS_INSTANCE_ID", ""),
            "subject_user_id": os.getenv("ENCOMPASS_SUBJECT_USER_ID", ""),
        },
        landingai_api_key=os.getenv("LANDINGAI_API_KEY", ""),
    )


def _get_output_directory() -> Path:
    """Get the output directory for saving files.
    
    - Local development: Uses tmp/ directory in the agent folder
    - LangGraph Cloud: Uses /tmp directory (ephemeral, per-run storage)
    
    Files are NOT stored in state to avoid bloating the conversation context.
    Only file paths are returned in tool responses.
    """
    # Check if we have a local tmp directory (for local development)
    local_tmp_dir = Path(__file__).parent / "tmp"
    
    if local_tmp_dir.exists() and os.access(local_tmp_dir, os.W_OK):
        # Local development - use local tmp directory
        return local_tmp_dir
    else:
        # LangGraph Cloud or restricted environment - use system /tmp
        return Path("/tmp")


@tool
def read_loan_fields(loan_id: str, field_ids: list[str]) -> dict[str, Any]:
    """Read one or multiple fields from an Encompass loan.

    Use this tool to retrieve loan field values from Encompass. Common field IDs include:
    - 4000: Loan Amount
    - 4002: Borrower First Name
    - 4004: Borrower Last Name
    - 353: Loan Number
    - 1109: Property Street Address
    - 12: Property City
    - 14: Property State
    - 748: Loan Purpose

    Args:
        loan_id: The Encompass loan GUID (e.g., "65ec32a1-99df-4685-92ce-41a08fd3b64e")
        field_ids: List of field IDs to retrieve (e.g., ["4000", "4002", "4004"])

    Returns:
        Dictionary mapping field IDs to their values

    Example:
        >>> read_loan_fields("loan-guid", ["4000", "4002"])
        {"4000": "350000", "4002": "John"}
    """
    import logging
    import time
    
    logger = logging.getLogger(__name__)
    logger.info(f"[READ_FIELDS] Starting - Loan: {loan_id[:8]}..., Fields: {field_ids}")
    
    start_time = time.time()
    client = _get_encompass_client()
    result = client.get_field(loan_id, field_ids)
    read_time = time.time() - start_time
    
    logger.info(f"[READ_FIELDS] Success - Read {len(result)} fields in {read_time:.2f}s")
    
    return result


@tool
def get_loan_documents(loan_id: str, max_documents: int = 10) -> dict[str, Any]:
    """List documents in an Encompass loan with their attachment IDs.

    This tool retrieves documents associated with a loan, including document
    metadata and attachment IDs which can be used with download_loan_document.
    
    Large responses are saved to a JSON file to avoid token limits.
    Returns only a summary with key validation data.

    Args:
        loan_id: The Encompass loan GUID
        max_documents: Maximum number of documents to return in response (default: 10)
                      Full list is always saved to JSON file

    Returns:
        Dictionary containing:
        - total_documents: Total count of documents
        - total_attachments: Total count of attachments across all documents
        - file_path: Path to JSON file with complete document list
        - sample_documents: Summary of first N documents (title, ID, attachment count)
        - showing_first: How many documents are in the sample

    Example:
        >>> get_loan_documents("loan-guid", max_documents=5)
        {
            "total_documents": 159,
            "total_attachments": 207,
            "file_path": "/tmp/loan_documents_387596ee.json",
            "sample_documents": [
                {"title": "W2", "documentId": "0985d4a6-f92...", "attachment_count": 1},
                ...
            ],
            "showing_first": 5
        }
    """
    import logging
    import time
    import tempfile
    import json
    
    logger = logging.getLogger(__name__)
    logger.info(f"[LIST_DOCS] Starting - Loan: {loan_id[:8]}...")
    
    start_time = time.time()
    client = _get_encompass_client()
    
    documents = client.get_loan_documents(loan_id)
    elapsed = time.time() - start_time
    
    # Count attachments
    total_attachments = sum(len(doc.get('attachments', [])) for doc in documents)
    
    logger.info(f"[LIST_DOCS] Success - {len(documents)} documents, {total_attachments} attachments in {elapsed:.2f}s")
    
    # Save full list to JSON file (always, to avoid bloating conversation)
    output_dir = _get_output_directory()
    file_path = output_dir / f'loan_documents_{loan_id[:8]}_{int(time.time())}.json'
    
    with open(file_path, 'w') as f:
        json.dump(documents, f, indent=2)
    
    logger.info(f"[LIST_DOCS] Saved full document list to {file_path}")
    
    # Extract key info for validation - just titles and attachment counts
    sample_docs_summary = []
    for doc in documents[:max_documents]:
        sample_docs_summary.append({
            "title": doc.get('title', 'N/A'),
            "documentId": doc.get('documentId', 'N/A')[:12] + "...",  # Truncate ID
            "attachment_count": len(doc.get('attachments', [])),
            "first_attachment_id": doc.get('attachments', [{}])[0].get('attachmentId', 'N/A') if doc.get('attachments') else None
        })
    
    return {
        "total_documents": len(documents),
        "total_attachments": total_attachments,
        "file_path": str(file_path),
        "sample_documents": sample_docs_summary,  # Just summaries, not full data
        "showing_first": min(max_documents, len(documents)),
        "loan_id": loan_id,
        "message": f"Full document list ({len(documents)} docs) saved to JSON file. Use read_file on '{file_path}' if you need all details."
    }


@tool
def get_loan_entity(loan_id: str) -> dict[str, Any]:
    """Get complete loan data including all fields and custom fields.

    This tool retrieves the full loan entity from Encompass, including standard fields,
    custom fields, and other loan metadata. The full data is saved to a JSON file to
    avoid token limits.

    Args:
        loan_id: The Encompass loan GUID

    Returns:
        Dictionary containing:
        - field_count: Number of populated fields in the response
        - loan_number: The loan number (if available)
        - file_path: Path to JSON file with complete loan data
        - key_fields: Sample of important loan fields
        - loan_id: The loan ID

    Example:
        >>> get_loan_entity("loan-guid")
        {
            "field_count": 247,
            "loan_number": "12345",
            "file_path": "/tmp/loan_entity_65ec32a1.json",
            "key_fields": {
                "loanNumber": "12345",
                "borrowerFirstName": "John",
                "borrowerLastName": "Doe"
            },
            "loan_id": "65ec32a1-99df-4685-92ce-41a08fd3b64e"
        }
    """
    import logging
    import time
    import json
    
    logger = logging.getLogger(__name__)
    logger.info(f"[GET_LOAN] Starting - Loan: {loan_id[:8]}...")
    
    start_time = time.time()
    client = _get_encompass_client()
    
    loan_data = client.get_loan_entity(loan_id)
    elapsed = time.time() - start_time
    
    # Count populated fields
    field_count = len(loan_data)
    loan_number = loan_data.get('loanNumber', 'N/A')
    
    logger.info(f"[GET_LOAN] Success - {field_count} fields retrieved in {elapsed:.2f}s")
    
    # Save full loan data to JSON file to avoid bloating conversation
    output_dir = _get_output_directory()
    file_path = output_dir / f'loan_entity_{loan_id[:8]}_{int(time.time())}.json'
    
    with open(file_path, 'w') as f:
        json.dump(loan_data, f, indent=2)
    
    logger.info(f"[GET_LOAN] Saved full loan data to {file_path}")
    
    # Extract key fields for quick reference
    key_fields = {}
    important_fields = [
        'loanNumber', 'borrowerFirstName', 'borrowerLastName',
        'loanAmount', 'propertyStreetAddress', 'propertyCity', 'propertyState'
    ]
    for field in important_fields:
        if field in loan_data:
            key_fields[field] = loan_data[field]
    
    # Extract borrower and employment information for validation
    borrower_info = {}
    if 'applications' in loan_data and len(loan_data['applications']) > 0:
        borrower = loan_data['applications'][0].get('borrower', {})
        
        # Parse alias names (comma-separated string) into a list
        alias_names_str = borrower.get('aliasName', '')
        alias_names = [name.strip() for name in alias_names_str.split(',')] if alias_names_str else []
        
        borrower_info = {
            'first_name': borrower.get('firstName', ''),
            'middle_name': borrower.get('middleName', ''),
            'last_name': borrower.get('lastNameWithSuffix', ''),
            'full_name': borrower.get('fullName', ''),
            'alias_names': alias_names,
            'employment': []
        }
        
        # Extract employment history
        for employment in borrower.get('employment', []):
            emp_record = {
                'employer_name': employment.get('employerName', ''),
                'current_employment': employment.get('currentEmploymentIndicator', False)
            }
            borrower_info['employment'].append(emp_record)
    
    return {
        "field_count": field_count,
        "loan_number": loan_number,
        "file_path": str(file_path),
        "key_fields": key_fields,
        "borrower_info": borrower_info,
        "loan_id": loan_id,
        "message": f"Full loan entity saved to file. Use read_file tool on '{file_path}' to see all fields."
    }


@tool
def write_loan_field(loan_id: str, field_id: str, value: Any) -> dict[str, Any]:
    """Write a value to a single field in an Encompass loan.

    Use this tool to update loan field values in Encompass. Make sure you have
    the correct field ID and that the value type matches what Encompass expects.

    Args:
        loan_id: The Encompass loan GUID
        field_id: The field ID to update (e.g., "4000" for Loan Amount)
        value: The value to write (string, number, etc. depending on field type)

    Returns:
        Dictionary with success status

    Example:
        >>> write_loan_field("loan-guid", "4000", 350000)
        {"success": True, "field_id": "4000", "value": 350000}
    """
    client = _get_encompass_client()
    success = client.write_field(loan_id, field_id, value)
    return {
        "success": success,
        "field_id": field_id,
        "value": value,
        "loan_id": loan_id,
    }


@tool
def find_loan(
    tool_call_id: Annotated[str, InjectedToolCallId],
    borrower_name: str | None = None,
    loan_number: str | None = None,
) -> Command:
    """Find a loan by borrower name or loan number and save loan ID to state.

    Use this tool to look up a loan when you have a borrower name or loan number
    but need the loan GUID for other operations. The loan GUID is automatically
    saved to state and used by all subsequent tools.

    You must provide at least one search parameter (borrower_name or loan_number).
    If multiple loans match the search, you will need to ask the user which loan
    to use and then call this tool again with the loan_number to disambiguate.

    Args:
        borrower_name: Full borrower name in "LastName, FirstName MiddleName" format 
                       as stored in Encompass (e.g., "Sorensen, Alva Scott")
        loan_number: Loan number (e.g., "2509946673")

    Returns:
        Command that updates state with loan_id if exactly one match is found,
        or returns matching loans for user disambiguation if multiple matches found.

    Example:
        >>> find_loan(borrower_name="Sorensen, Alva Scott")
        # If one match: saves loan_id to state
        # If multiple: returns list of loans for user to choose
    """
    import logging
    import json
    
    logger = logging.getLogger(__name__)
    
    # Validate inputs
    if not borrower_name and not loan_number:
        error_result = {
            "error": "Must provide either borrower_name or loan_number",
            "matching_loans": [],
            "count": 0
        }
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=json.dumps(error_result),
                        tool_call_id=tool_call_id
                    )
                ]
            }
        )
    
    # Search for loans
    search_param = f"Name: {borrower_name}" if borrower_name else f"Number: {loan_number}"
    logger.info(f"[FIND_LOAN] Searching for loan - {search_param}")
    
    client = _get_encompass_client()
    
    try:
        results = client.search_loans_pipeline(
            borrower_name=borrower_name,
            loan_number=loan_number
        )
    except Exception as e:
        logger.error(f"[FIND_LOAN] Search failed: {e}")
        error_result = {
            "error": f"Search failed: {str(e)}",
            "matching_loans": [],
            "count": 0
        }
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=json.dumps(error_result),
                        tool_call_id=tool_call_id
                    )
                ]
            }
        )
    
    # Handle results based on count
    if len(results) == 0:
        logger.warning(f"[FIND_LOAN] No loans found for {search_param}")
        no_match_result = {
            "error": f"No loans found matching {search_param}",
            "matching_loans": [],
            "count": 0
        }
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=json.dumps(no_match_result),
                        tool_call_id=tool_call_id
                    )
                ]
            }
        )
    
    if len(results) == 1:
        # Exactly one match - save loan_id to state
        loan = results[0]
        loan_guid = loan["loanGuid"]
        
        logger.info(f"[FIND_LOAN] Found loan - GUID: {loan_guid[:8]}..., Number: {loan['loanNumber']}")
        
        success_result = {
            "loan_id": loan_guid,
            "loan_number": loan["loanNumber"],
            "borrower_name": loan["borrowerName"],
            "loan_folder": loan["loanFolder"],
            "count": 1,
            "message": f"Found loan and saved to state. Loan ID: {loan_guid}"
        }
        
        return Command(
            update={
                "loan_id": loan_guid,  # Save to state for other tools
                "messages": [
                    ToolMessage(
                        content=json.dumps(success_result),
                        tool_call_id=tool_call_id
                    )
                ]
            }
        )
    
    # Multiple matches - ask user to disambiguate
    logger.warning(f"[FIND_LOAN] Found {len(results)} loans matching {search_param}")
    
    multi_match_result = {
        "count": len(results),
        "matching_loans": [
            {
                "loan_number": loan["loanNumber"],
                "borrower_name": loan["borrowerName"],
                "loan_folder": loan["loanFolder"],
                "loan_guid_preview": loan["loanGuid"][:12] + "..."
            }
            for loan in results
        ],
        "action_needed": "Multiple loans found. Please ask the user which loan to use, then call find_loan again with the specific loan_number to select the correct loan.",
        "message": f"Found {len(results)} loans. User must choose one by loan number."
    }
    
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=json.dumps(multi_match_result),
                    tool_call_id=tool_call_id
                )
            ]
        }
    )


@tool
def find_attachment(
    tool_call_id: Annotated[str, InjectedToolCallId],
    loan_id: str,
    target_document_type: str = "W-2",
) -> Command:
    """Find document attachment ID using LLM semantic matching and save to state.
    
    This tool gets all documents for a loan, uses an LLM to semantically match
    the target document type to the correct document, retrieves its attachments,
    and saves the first attachment ID to state for use in download phase.
    
    Args:
        loan_id: The loan GUID (from state, set by find_loan in Phase 0)
        target_document_type: Type of document to find (e.g., "W-2", "Bank Statement")
        
    Returns:
        Command that updates state with attachment_id if a match is found
        
    Example:
        >>> find_attachment(loan_id, "W-2")
        # Uses LLM to find W-2 document, saves attachment_id to state
    """
    import logging
    import json
    
    logger = logging.getLogger(__name__)
    logger.info(f"[FIND_ATTACHMENT] Searching for {target_document_type} in loan {loan_id[:8]}...")
    
    client = _get_encompass_client()
    
    try:
        # Get all documents for the loan (raw list for LLM processing)
        documents = client.get_loan_documents_raw(loan_id)
        logger.info(f"[FIND_ATTACHMENT] Found {len(documents)} total documents")
        
        # Create simplified document list for state (only title, documentId, attachment count)
        simplified_docs = [
            {
                "title": doc.get("title", "Untitled"),
                "documentId": doc.get("id"),  # API uses "id" not "documentId"
                "attachment_count": len(doc.get("attachments", []))
            }
            for doc in documents
        ]
        
        # Use LLM to find matching document
        matched_doc = _find_document_with_llm(documents, target_document_type)
        
        if not matched_doc:
            logger.warning(f"[FIND_ATTACHMENT] LLM could not find matching {target_document_type} document")
            error_result = {
                "error": f"No {target_document_type} document found",
                "total_documents": len(documents),
                "message": f"LLM could not identify a {target_document_type} document among {len(documents)} documents"
            }
            return Command(
                update={
                    "messages": [
                        ToolMessage(
                            content=json.dumps(error_result),
                            tool_call_id=tool_call_id
                        )
                    ]
                }
            )
        
        doc_id = matched_doc.get('id') or matched_doc.get('documentId')  # API uses "id"
        doc_title = matched_doc.get('title', 'Unknown')
        logger.info(f"[FIND_ATTACHMENT] LLM matched: '{doc_title}' (ID: {doc_id[:12]}...)")
        
        # Get attachments for the matched document
        attachments = matched_doc.get('attachments', [])
        
        if not attachments:
            logger.warning(f"[FIND_ATTACHMENT] Document has no attachments")
            error_result = {
                "error": f"Matched document '{doc_title}' has no attachments",
                "matched_document": doc_title,
                "document_id": doc_id
            }
            return Command(
                update={
                    "messages": [
                        ToolMessage(
                            content=json.dumps(error_result),
                            tool_call_id=tool_call_id
                        )
                    ]
                }
            )
        
        # Use the first attachment - API uses "entityId" not "attachmentId"
        attachment_id = attachments[0].get('entityId') or attachments[0].get('attachmentId')
        attachment_name = attachments[0].get('entityName', 'N/A')
        logger.info(f"[FIND_ATTACHMENT] Found attachment: '{attachment_name}' ID: {attachment_id[:12]}...")
        
        # Create summary for response (don't include full document list in message)
        success_result = {
            "attachment_id": attachment_id,
            "document_title": doc_title,
            "document_id": doc_id,
            "document_type": matched_doc.get('documentType', 'N/A'),
            "total_attachments": len(attachments),
            "total_documents_in_loan": len(documents),
            "message": f"Found {target_document_type} document and saved attachment ID to state"
        }
        
        return Command(
            update={
                "attachment_id": attachment_id,  # Save to state for Phase 3
                "loan_documents": simplified_docs,  # Save simplified list to state (title + ID only)
                "messages": [
                    ToolMessage(
                        content=json.dumps(success_result),
                        tool_call_id=tool_call_id
                    )
                ]
            }
        )
        
    except Exception as e:
        logger.error(f"[FIND_ATTACHMENT] Error: {e}")
        error_result = {
            "error": f"Failed to find attachment: {str(e)}",
            "target_type": target_document_type
        }
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=json.dumps(error_result),
                        tool_call_id=tool_call_id
                    )
                ]
            }
        )


@tool
def download_loan_document(
    loan_id: str,
    attachment_id: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Get a W-2 document from Encompass and upload to S3 for UI access.

    This tool downloads a document from Encompass, saves it locally for extraction,
    and uploads it to docRepo S3 storage so the UI can display it.

    Args:
        loan_id: The Encompass loan GUID
        attachment_id: The attachment entity ID to download

    Returns:
        Dictionary containing:
        - file_path: Path to the local temporary file for extraction
        - file_size_bytes: Size of the downloaded document in bytes
        - file_size_kb: Size in kilobytes for readability
        - attachment_id: The attachment ID that was downloaded
        - loan_id: The loan ID it came from
        - s3_info: Information about S3 upload (client_id, doc_id, s3_uploaded status)

    Example:
        >>> download_loan_document("loan-guid", "attachment-guid")
        {
            "file_path": "/tmp/document_abc123.pdf",
            "file_size_bytes": 583789,
            "file_size_kb": 570.11,
            "attachment_id": "attachment-guid",
            "loan_id": "loan-guid",
            "s3_info": {
                "s3_uploaded": true,
                "client_id": "loan-guid",
                "doc_id": "attachment-guid",
                "message": "Uploaded"
            }
        }
    """
    import logging
    import time
    
    logger = logging.getLogger(__name__)
    logger.info(f"[GET_W2] Starting - Loan: {loan_id[:8]}..., Attachment: {attachment_id[:8]}...")
    
    start_time = time.time()
    client = _get_encompass_client()
    
    # Download the document from Encompass
    document_bytes = client.download_attachment(loan_id, attachment_id)
    
    # Save to local file for extraction tool
    output_dir = _get_output_directory()
    file_path = output_dir / f'document_{attachment_id[:8]}_{int(time.time())}.pdf'
    
    with open(file_path, 'wb') as f:
        f.write(document_bytes)
    
    download_time = time.time() - start_time
    size_kb = len(document_bytes) / 1024
    logger.info(f"[GET_W2] Downloaded - {len(document_bytes):,} bytes ({size_kb:.2f} KB) saved to {file_path} in {download_time:.2f}s")
    
    # Upload to docRepo S3 for UI access
    # Use consistent client_id "docAgent" for all documents
    s3_result = _upload_to_docrepo_s3(
        document_bytes=document_bytes,
        client_id="docAgent",  # Consistent client ID for all documents
        doc_id=f"{loan_id}_{attachment_id}",  # FULL IDs (not truncated) - UI needs these to fetch from DocRepo
        data_object={
            "document_type": "W2",
            "loan_id": loan_id,
            "attachment_id": attachment_id,
            "file_size_bytes": len(document_bytes),
            "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source": "encompass"
        }
    )
    
    # Create display name for the file
    file_display_name = f"W-2 Document ({datetime.now(UTC).year})"
    
    # Create loan file metadata for UI
    import json
    loan_file_metadata = {
        "name": file_display_name,
        "size": len(document_bytes),
        "type": "application/pdf",
        "document_type": "W2",
        "uploaded_at": datetime.now(UTC).isoformat(),
        "s3_client_id": s3_result.get("client_id", "docAgent"),
        "s3_doc_id": s3_result.get("doc_id"),
        "s3_uploaded": s3_result.get("s3_uploaded", False),
    }
    
    # Return Command to update loan_files state
    result_summary = {
        "file_path": str(file_path),
        "file_size_bytes": len(document_bytes),
        "file_size_kb": round(size_kb, 2),
        "s3_uploaded": s3_result.get("s3_uploaded", False),
        "added_to_ui": True
    }
    
    return Command(
        update={
            "loan_files": {file_display_name: loan_file_metadata},
            "messages": [
                ToolMessage(
                    content=json.dumps(result_summary),
                    tool_call_id=tool_call_id
                )
            ],
        }
    )


@tool
def extract_document_data(
    file_path: str,
    extraction_schema: dict[str, Any],
    document_type: str = "Document",
) -> dict[str, Any]:
    """Extract structured data from a document using LandingAI.

    This tool uses AI to extract specific fields from a PDF document based on a schema
    you provide. Pass the file_path from download_loan_document result.
    
    Extraction schemas are defined in extraction_schemas.py. Use get_extraction_schema()
    to load the appropriate schema for your document type.

    Args:
        file_path: Path to the PDF file (from download_loan_document result)
        extraction_schema: JSON schema defining what to extract. 
            Load using: get_extraction_schema("W-2") from extraction_schemas.py
            Format:
            {
                "type": "object",
                "properties": {
                    "field_name": {
                        "type": "string|number|array",
                        "title": "Display Name",
                        "description": "What to extract"
                    }
                }
            }
        document_type: Label for the document type (e.g., "W2", "1003", "Bank Statement")

    Returns:
        Dictionary containing:
        - extracted_schema: The extracted data matching your schema
        - doc_type: The document type you specified
        - extraction_method: The method used (landingai-agentic)

    Example:
        >>> from extraction_schemas import get_extraction_schema
        >>> 
        >>> # Get the W-2 schema
        >>> schema = get_extraction_schema("W-2")
        >>> 
        >>> # Extract from downloaded document
        >>> download_result = download_loan_document(loan_id, attachment_id)
        >>> extract_document_data(download_result["file_path"], schema, "W2")
        {
            "extracted_schema": {
                "employer_name": "Acme Corp",
                "employee_name": "John Doe",
                "wages": 75000
            },
            "doc_type": "W2",
            "extraction_method": "landingai-agentic"
        }
    """
    import logging
    import time
    import os
    
    logger = logging.getLogger(__name__)
    
    # Read the file
    with open(file_path, 'rb') as f:
        document_bytes = f.read()
    
    file_size_kb = len(document_bytes) / 1024
    logger.info(f"[EXTRACT] Starting - Type: {document_type}, File: {os.path.basename(file_path)}, Size: {file_size_kb:.2f} KB")
    
    start_time = time.time()
    client = _get_encompass_client()
    
    filename = f"{document_type.lower().replace(' ', '_')}_document.pdf"

    # Extract data using LandingAI
    result = client.extract_document_data(
        document_bytes=document_bytes,
        schema=extraction_schema,
        doc_type=document_type,
        filename=filename,
    )
    
    extraction_time = time.time() - start_time
    extracted_data = result.get("extracted_schema", {})
    
    logger.info(f"[EXTRACT] Success - {len(extracted_data)} fields in {extraction_time:.2f}s")

    return result


@tool
def compare_extracted_data(comparison_rules: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare extracted data using deterministic string matching.
    
    This tool performs exact string comparison to validate if extracted values match
    expected values. It uses case-insensitive matching with whitespace normalization.
    
    Args:
        comparison_rules: List of comparison rules, each containing:
            - target: The actual value to validate (string)
            - acceptable: List of acceptable variations (list of strings)
            - label: Optional label for this comparison (string)
    
    Returns:
        Dictionary containing:
        - matches: List of successful matches with details
        - mismatches: List of failed matches with details
        - total_rules: Total number of rules checked
        - passed_rules: Number of rules that passed
        - failed_rules: Number of rules that failed
        - overall_status: "PASS" if all rules pass, "FAIL" otherwise
    
    Example:
        >>> rules = [
        ...     {
        ...         "target": "Alva Sorenson",
        ...         "acceptable": ["Alva Scott Sorensen", "Alva Sorensen"],
        ...         "label": "Employee Name"
        ...     },
        ...     {
        ...         "target": "Hynds Bros Inc",
        ...         "acceptable": ["Hynds Bros", "Hynds Brothers"],
        ...         "label": "Employer Name"
        ...     }
        ... ]
        >>> compare_extracted_data(rules)
        {
            "matches": [
                {
                    "label": "Employee Name",
                    "target": "Alva Sorenson",
                    "matched_with": "Alva Sorensen",
                    "status": "MATCH"
                }
            ],
            "mismatches": [
                {
                    "label": "Employer Name",
                    "target": "Hynds Bros Inc",
                    "acceptable": ["Hynds Bros", "Hynds Brothers"],
                    "status": "NO_MATCH"
                }
            ],
            "total_rules": 2,
            "passed_rules": 1,
            "failed_rules": 1,
            "overall_status": "FAIL"
        }
    """
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"[COMPARE] Starting validation of {len(comparison_rules)} rules")
    
    def normalize_string(s: str) -> str:
        """Normalize string for comparison: lowercase and strip whitespace."""
        if not s:
            return ""
        return str(s).lower().strip()
    
    matches = []
    mismatches = []
    
    for i, rule in enumerate(comparison_rules):
        target = rule.get('target', '')
        acceptable = rule.get('acceptable', [])
        label = rule.get('label', f'Rule {i+1}')
        
        # Normalize target
        normalized_target = normalize_string(target)
        
        # Check if target matches any acceptable value
        match_found = False
        matched_value = None
        
        for acceptable_value in acceptable:
            normalized_acceptable = normalize_string(acceptable_value)
            if normalized_target == normalized_acceptable:
                match_found = True
                matched_value = acceptable_value
                break
        
        if match_found:
            # Determine if this was a primary or alias match
            # First item in acceptable list is typically the primary value
            is_alias_match = len(acceptable) > 1 and matched_value != acceptable[0]
            
            matches.append({
                'label': label,
                'target': target,
                'matched_with': matched_value,
                'is_alias': is_alias_match,
                'status': 'MATCH'
            })
            
            if is_alias_match:
                logger.info(f"[COMPARE] ✓ {label}: '{target}' matches alias '{matched_value}'")
            else:
                logger.info(f"[COMPARE] ✓ {label}: '{target}' matches '{matched_value}'")
        else:
            mismatches.append({
                'label': label,
                'target': target,
                'acceptable': acceptable,
                'status': 'NO_MATCH'
            })
            logger.warning(f"[COMPARE] ✗ {label}: '{target}' does not match any of {acceptable}")
    
    passed_rules = len(matches)
    failed_rules = len(mismatches)
    total_rules = len(comparison_rules)
    overall_status = "PASS" if failed_rules == 0 else "FAIL"
    
    logger.info(f"[COMPARE] Complete - {passed_rules}/{total_rules} rules passed")
    
    return {
        'matches': matches,
        'mismatches': mismatches,
        'total_rules': total_rules,
        'passed_rules': passed_rules,
        'failed_rules': failed_rules,
        'overall_status': overall_status
    }


# =============================================================================
# AGENT CONFIGURATION
# =============================================================================

# System prompt for the DrawDoc-AWM agent
drawdoc_instructions = """You are an Encompass W-2 document validation assistant. Your ONLY job is to validate W-2 tax documents against loan entity data.

CRITICAL RULES - FOLLOW THESE EXACTLY:
- If you see ANY borrower names or loan numbers in a message → IMMEDIATELY create todos and run validation
- DO NOT ask for clarification or more information
- DO NOT create documentation, markdown files, or guides  
- We are ONLY testing READ operations and VALIDATION

IMMEDIATE ACTIONS when you see borrower/loan identifiers:
1. write_todos - Create 7-step validation plan (see planner_prompt.md)
2. Execute Step 0 immediately
3. Execute ALL 7 steps in order:
   Step 0: find_loan(borrower_name) → Find loan GUID and save to state
   Step 1: find_attachment(loan_id, "W-2") → Use LLM to find W-2 attachment, save to state
   Step 2: get_loan_entity(loan_id) → Get borrower name and employment (use loan_id from state)
   Step 3: download_loan_document(loan_id, attachment_id) → Retrieve W-2 (use both from state)
   Step 4: extract_document_data(file_path, schema, "W2") → Extract employee/employer with AI
   Step 5: compare_extracted_data(rules) → Validate consistency
   Step 6: write_file(validation_report.md) → Save final validation report

IMPORTANT NOTES:
- Large responses are automatically saved to files to avoid token limits
- Tools return file_path for saved data - you can read files if needed with read_file tool
- Pass the file_path from download_loan_document result to extract_document_data
- Step 0 saves loan_id to state - all subsequent tools use this automatically
- Step 1 uses LLM to find W-2 document and saves attachment_id to state
- Step 3 uploads documents to S3 for UI access - s3_info contains client_id, doc_id, and upload status
- Keep validation reports clear and concise - focus on results, not methodology

If message has borrower name/loan number = START VALIDATION IMMEDIATELY. Do not ask questions."""

# Load local planning prompt if it exists
planner_prompt_file = Path(__file__).parent / "planner_prompt.md"
planning_prompt = planner_prompt_file.read_text() if planner_prompt_file.exists() else None

# Define the default starting message for automatic W-2 validation testing
# This message will be automatically injected when the agent starts with no messages
# The actual test values (borrower name, loan number) are defined in the planning prompt
DEFAULT_STARTING_MESSAGE = """Run the W-2 validation test for borrower: Sorensen, Alva Scott."""

# Minimal middleware to add loan_files, loan_id, attachment_id, and loan_documents state fields
class LoanFilesState(AgentState):
    """State schema with loan_files, loan_id, attachment_id, and loan_documents fields."""
    loan_files: NotRequired[dict[str, dict]]
    loan_id: NotRequired[str]  # Stores the loan GUID from find_loan tool
    attachment_id: NotRequired[str]  # Stores the W-2 attachment ID from find_attachment tool
    loan_documents: NotRequired[list[dict]]  # Simplified list: [{title, documentId, attachment_count}]

class LoanFilesMiddleware(AgentMiddleware):
    """Minimal middleware that adds loan_files to state."""
    state_schema = LoanFilesState
    def __init__(self):
        super().__init__()
        self.tools = []  # No tools needed

# Create the DrawDoc-AWM agent with Encompass tools
# Test IDs are embedded in DEFAULT_STARTING_MESSAGE using Python constants
agent = create_deep_agent(
    agent_type="DrawDoc-AWM",
    middleware=(LoanFilesMiddleware(),),  # Add loan_files to state
    system_prompt=drawdoc_instructions,
    planning_prompt=planning_prompt,
    default_starting_message=DEFAULT_STARTING_MESSAGE,
    tools=[
        find_loan,
        find_attachment,
        read_loan_fields,
        get_loan_documents,
        get_loan_entity,
        write_loan_field,
        download_loan_document,
        extract_document_data,
        compare_extracted_data,
    ],
)

# =============================================================================
# TEST/DEMO FUNCTIONS
# =============================================================================


def test_encompass_tools():
    """Individual tool testing is disabled - use --demo for full workflow."""
    print("=" * 80)
    print("Individual Tool Testing")
    print("=" * 80)
    print()
    print("❌ Individual tool tests are disabled.")
    print()
    print("The DrawDoc-AWM agent now uses a fully integrated workflow where:")
    print("  - Loan IDs are found dynamically by borrower name")
    print("  - Attachment IDs are found using LLM semantic matching")
    print("  - All data flows through state")
    print()
    print("To test the complete 7-step workflow:")
    print("  python drawdoc_agent.py --demo")
    print()
    print("=" * 80)


def demo_agent_workflow():
    """Demonstrate the agent workflow using DEFAULT_STARTING_MESSAGE."""
    from langchain_core.messages import HumanMessage

    print("=" * 80)
    print("Demo: Agent Workflow - Complete 7-Step W-2 Validation")
    print("=" * 80)
    print()
    print("This demo uses the DEFAULT_STARTING_MESSAGE which contains:")
    print("  - Borrower Name: Sorensen, Alva Scott")
    print("  - Loan Number: 2509946673")
    print()
    print("The agent will automatically:")
    print("  - Find the loan GUID from the borrower name")
    print("  - Use LLM to find the W-2 document attachment")
    print("  - Complete the full validation workflow")
    print()
    print("Starting agent with default message...")
    print()

    # Invoke the agent with the DEFAULT_STARTING_MESSAGE
    result = agent.invoke({"messages": [HumanMessage(content=DEFAULT_STARTING_MESSAGE)]})

    # Print the results
    print("=" * 80)
    print("Agent Response:")
    print("=" * 80)
    for message in result["messages"]:
        if hasattr(message, "content") and message.content:
            print(f"\n{message.type}: {message.content}")
    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="DrawDoc-AWM Agent - Document Drawing and Annotation Agent with Encompass Integration"
    )
    parser.add_argument("--test-tools", action="store_true", help="Test individual tools")
    parser.add_argument("--demo", action="store_true", help="Run agent workflow demo")

    args = parser.parse_args()

    if args.test_tools:
        test_encompass_tools()
    elif args.demo:
        demo_agent_workflow()
    else:
        print("DrawDoc-AWM Agent")
        print("=" * 80)
        print()
        print("This agent provides Encompass document processing capabilities.")
        print()
        print("Available commands:")
        print("  --test-tools  (Disabled - use --demo instead)")
        print("  --demo        Run complete 7-step agent workflow with automatic lookup")
        print()
        print("7-Step Validation Flow:")
        print("  Step 0: find_loan           - Find loan GUID by borrower name")
        print("  Step 1: find_attachment     - Find W-2 attachment using LLM")
        print("  Step 2: get_loan_entity     - Get borrower info and employment")
        print("  Step 3: download_document   - Retrieve W-2 document")
        print("  Step 4: extract_data        - AI extraction of W-2 fields")
        print("  Step 5: compare_data        - Validate consistency")
        print("  Step 6: save_report         - Save validation report")
        print()
        print("Configuration:")
        print("  - API credentials loaded from .env file")
        print("  - Test borrower/loan configured in DEFAULT_STARTING_MESSAGE")
        print()
        print("Example usage:")
        print("  python drawdoc_agent.py --demo        # Run full 7-step workflow")
        print()
        print("The agent will automatically find loan and attachment IDs at runtime.")
        print()
