"""Preparation Sub-Agent - Document Processing and Field Population.

This agent:
1. Retrieves all documents for a given loan
2. Downloads each document
3. Extracts entities using LandingAI OCR
4. Maps extracted fields to Encompass field IDs
5. Returns extracted data as a dictionary (does NOT write to Encompass)

Supports both direct function calls and JSON input.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True
)

# Suppress noisy logs
logging.getLogger('langgraph_runtime_inmem').setLevel(logging.WARNING)
logging.getLogger('langgraph_api').setLevel(logging.WARNING)
logging.getLogger('langgraph').setLevel(logging.WARNING)
logging.getLogger('uvicorn').setLevel(logging.WARNING)
logging.getLogger('watchfiles').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

from copilotagent import create_deep_agent, EncompassConnect
from langchain_core.tools import tool
from tools.extraction_schemas import get_extraction_schema, list_supported_document_types
from tools.field_mappings import (
    get_field_mapping,
    get_all_mappings_for_document,
    is_mapping_ready,
    list_ready_mappings,
    get_common_field_ids
)

# =============================================================================
# SAFETY CONFIGURATION
# =============================================================================
# Set ENABLE_ENCOMPASS_WRITES=false in .env to prevent writes to production
# This is CRITICAL when testing against production environments
# Note: This agent does NOT write to Encompass - it only returns extracted data as a dictionary
ENABLE_WRITES = False  # Always disabled - agent returns data, doesn't write


# =============================================================================
# ENCOMPASS CLIENT
# =============================================================================

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


def _sanitize_loan_id_for_folder(loan_id: str) -> str:
    """Sanitize loan ID for use in folder name.
    
    Args:
        loan_id: Loan GUID (e.g., "387596ee-7090-47ca-8385-206e22c9c9da")
        
    Returns:
        Sanitized loan ID for folder name (e.g., "387596ee-7090-47ca-8385-206e22c9c9da")
    """
    # Remove any invalid filesystem characters
    import re
    sanitized = re.sub(r'[<>:"|?*]', '', loan_id)
    return sanitized


def _get_output_directory(loan_id: Optional[str] = None) -> Path:
    """Get the output directory for saving files.
    
    Creates loan-specific folder: assets-{loan_id}
    
    Args:
        loan_id: Loan ID to create loan-specific folder (e.g., assets-387596ee-7090-47ca-8385-206e22c9c9da)
        
    Returns:
        Path to the assets directory
    """
    base_dir = Path(__file__).parent
    
    if loan_id:
        # Create loan-specific folder: assets-{loan_id}
        loan_sanitized = _sanitize_loan_id_for_folder(loan_id)
        assets_dir = base_dir / f"assets-{loan_sanitized}"
    else:
        # Fallback to generic assets folder if no loan_id
        assets_dir = base_dir / "assets"
    
    # Create assets directory if it doesn't exist
    if not assets_dir.exists():
        assets_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"[DOWNLOAD] Created assets directory: {assets_dir}")
    
    # Check if we can write to assets directory
    if assets_dir.exists() and os.access(assets_dir, os.W_OK):
        return assets_dir
    else:
        # Fallback to tmp if assets directory can't be created/used
        logger.warning(f"[DOWNLOAD] Cannot write to assets directory, falling back to /tmp")
        return Path("/tmp")


# =============================================================================
# TOOLS
# =============================================================================

@tool
def get_loan_documents(loan_id: str) -> Dict[str, Any]:
    """Get all documents for a loan.
    
    Args:
        loan_id: The Encompass loan GUID
        
    Returns:
        Dictionary with document list and metadata
    """
    import time
    
    logger.info(f"[GET_DOCS] Starting - Loan: {loan_id[:8]}...")
    
    client = _get_encompass_client()
    documents = client.get_loan_documents(loan_id)
    
    logger.info(f"[GET_DOCS] Found {len(documents)} documents")
    
    return {
        "documents": documents,
        "total_documents": len(documents),
        "loan_id": loan_id,
    }


def _sanitize_filename(name: str) -> str:
    """Convert a document name to a filesystem-safe filename.
    
    Args:
        name: Document title or type (e.g., "W-2", "Title Report", "ID Customer Identification")
        
    Returns:
        Sanitized filename (e.g., "w2", "title_report", "id_customer_identification")
    """
    import re
    
    # Convert to lowercase
    filename = name.lower()
    
    # Replace common patterns
    filename = filename.replace('w-2', 'w2')
    filename = filename.replace('w 2', 'w2')
    filename = filename.replace('1003', 'form_1003')
    filename = filename.replace('-', '_')
    filename = filename.replace(' ', '_')
    filename = filename.replace('/', '_')
    filename = filename.replace('\\', '_')
    filename = filename.replace('(', '')
    filename = filename.replace(')', '')
    filename = filename.replace('[', '')
    filename = filename.replace(']', '')
    filename = filename.replace('{', '')
    filename = filename.replace('}', '')
    
    # Remove special characters, keep only alphanumeric and underscores
    filename = re.sub(r'[^a-z0-9_]', '', filename)
    
    # Remove multiple consecutive underscores
    filename = re.sub(r'_+', '_', filename)
    
    # Remove leading/trailing underscores
    filename = filename.strip('_')
    
    # Limit length
    if len(filename) > 100:
        filename = filename[:100]
    
    # Ensure it's not empty
    if not filename:
        filename = 'document'
    
    return filename


@tool
def download_document(
    loan_id: str, 
    attachment_id: str,
    document_title: Optional[str] = None,
    document_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Download a document from Encompass and save to assets folder.
    
    Files are saved with a filename based on document title/type (e.g., "w2.pdf", "title_report.pdf").
    If a file already exists, it will not be re-downloaded.
    If multiple documents have the same name, attachment_id is appended for uniqueness.
    
    Args:
        loan_id: The Encompass loan GUID
        attachment_id: The attachment entity ID
        document_title: Optional document title (e.g., "W-2", "Title Report")
        document_type: Optional document type (e.g., "W-2", "ID")
        
    Returns:
        Dictionary with file_path and metadata
    """
    import time
    
    logger.info(f"[DOWNLOAD] Starting - Loan: {loan_id[:8]}..., Attachment: {attachment_id[:8]}...")
    
    output_dir = _get_output_directory(loan_id)
    
    # Generate filename from document title/type
    if document_title:
        base_name = _sanitize_filename(document_title)
    elif document_type and document_type != "Unknown":
        base_name = _sanitize_filename(document_type)
    else:
        # Fallback to attachment_id if no title/type provided
        base_name = f"document_{attachment_id[:8]}"
    
    # Start with base filename
    file_path = output_dir / f'{base_name}.pdf'
    
    # Check if file already exists - if so, skip download (same loan, same document name = same file)
    if file_path.exists():
        file_size = file_path.stat().st_size
        size_kb = file_size / 1024
        logger.info(f"[DOWNLOAD] File already exists ({base_name}.pdf), skipping download - {file_size:,} bytes ({size_kb:.2f} KB)")
        return {
            "file_path": str(file_path),
            "file_size_bytes": file_size,
            "file_size_kb": round(size_kb, 2),
            "attachment_id": attachment_id,
            "loan_id": loan_id,
            "cached": True,  # Indicate this was a cached file
        }
    
    # If file doesn't exist, we'll download it below
    # Note: Since files are organized by loan_id folder, duplicates are handled by folder structure
    
    # Download the document
    client = _get_encompass_client()
    document_bytes = client.download_attachment(loan_id, attachment_id)
    
    # Save to file
    with open(file_path, 'wb') as f:
        f.write(document_bytes)
    
    size_kb = len(document_bytes) / 1024
    logger.info(f"[DOWNLOAD] Success - {len(document_bytes):,} bytes ({size_kb:.2f} KB) saved to {file_path.name}")
    
    return {
        "file_path": str(file_path),
        "file_size_bytes": len(document_bytes),
        "file_size_kb": round(size_kb, 2),
        "attachment_id": attachment_id,
        "loan_id": loan_id,
        "cached": False,  # Indicate this was newly downloaded
    }


@tool
def extract_document_entities(
    file_path: str,
    document_type: str,
    attachment_id: str,
) -> Dict[str, Any]:
    """Extract entities from a document using LandingAI OCR.
    
    Args:
        file_path: Path to the PDF file
        document_type: Type of document (e.g., "W-2", "Bank Statement")
        attachment_id: Attachment ID for reference
        
    Returns:
        Dictionary with extracted entities and mapping status
    """
    import time
    import os
    
    logger.info(f"[EXTRACT] Starting - Type: {document_type}, File: {os.path.basename(file_path)}")
    
    # Get extraction schema for this document type
    try:
        schema = get_extraction_schema(document_type)
    except ValueError as e:
        logger.warning(f"[EXTRACT] No schema found for {document_type}: {e}")
        return {
            "error": f"No extraction schema for document type: {document_type}",
            "document_type": document_type,
            "attachment_id": attachment_id,
        }
    
    # Read the file
    with open(file_path, 'rb') as f:
        document_bytes = f.read()
    
    # Extract using LandingAI with retry logic for timeouts
    client = _get_encompass_client()
    filename = f"{document_type.lower().replace(' ', '_')}_document.pdf"
    
    file_size_kb = len(document_bytes) / 1024
    file_size_mb = file_size_kb / 1024
    
    # Adjust timeout based on file size (larger files need more time)
    # Base timeout: 60s, add 30s per MB over 1MB
    base_timeout = 120  # Increased base timeout from 60 to 120 seconds
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
                filename=filename,
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
    
    # Identify which extracted fields have mappings
    mapped_fields = {}
    unmapped_fields = {}
    pending_fields = {}
    
    for field_name, field_value in extracted_data.items():
        field_id = get_field_mapping(document_type, field_name)
        
        if field_id and field_id != "TBD":
            mapped_fields[field_name] = {
                "value": field_value,
                "encompass_field_id": field_id,
            }
            logger.debug(f"[EXTRACT] Mapped {field_name} -> {field_id} = {field_value}")
        elif field_id == "TBD":
            pending_fields[field_name] = {
                "value": field_value,
                "status": "mapping_pending",
            }
        else:
            unmapped_fields[field_name] = {
                "value": field_value,
                "status": "no_mapping",
            }
            logger.debug(f"[EXTRACT] No mapping for {field_name} (field_id: {field_id})")
    
    logger.info(f"[EXTRACT] Success - {len(extracted_data)} fields in {extraction_time:.2f}s")
    logger.info(f"[EXTRACT] Mappings - Ready: {len(mapped_fields)}, Pending: {len(pending_fields)}, Unmapped: {len(unmapped_fields)}")
    
    return {
        "extracted_data": extracted_data,
        "document_type": document_type,
        "attachment_id": attachment_id,
        "mapped_fields": mapped_fields,
        "pending_fields": pending_fields,
        "unmapped_fields": unmapped_fields,
        "extraction_time_seconds": round(extraction_time, 2),
    }


@tool
def get_mapped_fields_dict(
    mapped_fields: Dict[str, Dict[str, Any]],
    document_type: str,
) -> Dict[str, Any]:
    """Convert mapped fields to dictionary format with Encompass field IDs as keys.
    
    This returns what WOULD be written to Encompass without actually writing.
    
    Args:
        mapped_fields: Dictionary of {field_name: {value, encompass_field_id}}
        document_type: Type of document
        
    Returns:
        Dictionary in format: {document_type: {encompass_field_id: value}}
        
    Example:
        {
            "W-2": {
                "4002": "John",
                "4004": "Doe"
            }
        }
    """
    # Build dictionary with Encompass field IDs as keys
    encompass_fields = {}
    
    for field_name, field_info in mapped_fields.items():
        field_id = field_info.get("encompass_field_id")
        value = field_info.get("value")
        
        if field_id and is_mapping_ready(field_id):
            encompass_fields[field_id] = value
    
    return {
        document_type: {
            "extracted_entities": mapped_fields,  # Original extracted data
            **encompass_fields  # Mapped fields with Encompass IDs as keys
        }
    }


@tool
def write_extracted_fields(
    loan_id: str,
    mapped_fields: Dict[str, Dict[str, Any]],
    document_type: str,
    attachment_id: str,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Write extracted fields to Encompass.
    
    NOTE: Writes are DISABLED by default. This function returns what would be written.
    
    Args:
        loan_id: The Encompass loan GUID
        mapped_fields: Dictionary of {field_name: {value, encompass_field_id}}
        document_type: Type of document for logging
        attachment_id: Attachment ID for reference
        dry_run: If True, simulate writes without actually writing (default: True)
        
    Returns:
        Dictionary with mapped fields in format: {document_type: {field_id: value}}
    """
    import time
    
    # Safety check - ALWAYS use dry_run unless explicitly enabled
    if not ENABLE_WRITES:
        dry_run = True
    
    logger.info(f"[WRITE] Processing - Loan: {loan_id[:8]}..., Document: {document_type}")
    logger.info(f"[WRITE] Mode: {'DRY RUN (no writes)' if dry_run else 'LIVE WRITE'}")
    logger.info(f"[WRITE] Fields to process: {len(mapped_fields)}")
    
    # Build output dictionary with Encompass field IDs as keys
    encompass_fields = {}
    skipped_fields = []
    
    for field_name, field_info in mapped_fields.items():
        field_id = field_info.get("encompass_field_id")
        value = field_info.get("value")
        
        if not field_id or not is_mapping_ready(field_id):
            skipped_fields.append({
                "field_name": field_name,
                "reason": "invalid_or_pending_field_id",
                "field_id": field_id,
            })
            continue
        
        # Add to output dictionary
        encompass_fields[field_id] = value
        
        if dry_run:
            logger.info(f"[WRITE] [DRY RUN] Would write {field_name} ({field_id}) = {value}")
        else:
            # Actual write (only if explicitly enabled)
            try:
                start_time = time.time()
                client = _get_encompass_client()
                success = client.write_field(loan_id, field_id, value)
                write_time = time.time() - start_time
                
                if success:
                    logger.info(f"[WRITE] ✅ {field_name} ({field_id}) = {value} in {write_time:.2f}s")
                else:
                    logger.error(f"[WRITE] ❌ Failed to write {field_name} ({field_id})")
                    # Remove from output if write failed
                    encompass_fields.pop(field_id, None)
            except Exception as e:
                logger.error(f"[WRITE] ❌ Exception writing {field_name} ({field_id}): {e}")
                # Remove from output if write failed
                encompass_fields.pop(field_id, None)
    
    logger.info(f"[WRITE] Complete - Mapped fields: {len(encompass_fields)}, Skipped: {len(skipped_fields)}")
    
    # Return in the format requested: {document_type: {field_id: value}}
    return {
        document_type: {
            "extracted_entities": {k: v.get("value") for k, v in mapped_fields.items()},
            **encompass_fields  # Encompass field IDs as keys
        },
        "skipped_fields": skipped_fields,
        "dry_run": dry_run,
    }


def _process_single_document(
    doc: Dict[str, Any],
    loan_id: str,
    document_types: Optional[List[str]],
    dry_run: bool,
) -> Optional[Dict[str, Any]]:
    """Process a single document: download, extract, and map fields.
    
    Returns:
        Processing result dictionary or None if document should be skipped
    """
    doc_title = doc.get("title", "Unknown")
    doc_type = doc.get("documentType") or doc.get("type", "Unknown")
    attachments = doc.get("attachments", [])
    
    # Filter by document type if specified
    if document_types:
        matches = False
        doc_title_lower = doc_title.lower()
        doc_type_lower = doc_type.lower()
        
        for requested_type in document_types:
            requested_lower = requested_type.lower().strip()
            if (requested_lower in doc_title_lower or 
                requested_lower in doc_type_lower or
                doc_title_lower.startswith(requested_lower) or
                doc_type_lower.startswith(requested_lower) or
                (requested_lower in ["title report", "appraisal report"] and 
                 (requested_lower in doc_title_lower or requested_lower in doc_type_lower)) or
                (requested_lower == "id" and ("id" in doc_title_lower or "license" in doc_title_lower or "driver" in doc_title_lower))):
                matches = True
                break
        
        if not matches:
            logger.info(f"[PROCESS] Skipping {doc_title} (type: {doc_type}) - not in filter")
            return None
    
    if not attachments:
        logger.warning(f"[PROCESS] Document '{doc_title}' has no attachments")
        return None
    
    attachment = attachments[0]
    attachment_id = attachment.get("attachmentId") or attachment.get("entityId")
    
    if not attachment_id:
        logger.warning(f"[PROCESS] Attachment has no ID for document '{doc_title}'")
        return None
    
    logger.info(f"[PROCESS] Processing document: {doc_title} (type: {doc_type})")
    
    try:
        # Download document
        download_result = download_document.invoke({
            "loan_id": loan_id,
            "attachment_id": attachment_id,
            "document_title": doc_title,
            "document_type": doc_type,
        })
        file_path = download_result.get("file_path")
        
        if not file_path:
            logger.error(f"[PROCESS] Failed to download document '{doc_title}'")
            return {
                "document_title": doc_title,
                "document_type": doc_type,
                "attachment_id": attachment_id,
                "status": "download_failed",
            }
        
        # Normalize document type
        normalized_doc_type = doc_type
        if doc_type == "Unknown" or doc_type == "":
            from tools.extraction_schemas import list_supported_document_types
            supported_types = list_supported_document_types()
            doc_title_lower = doc_title.lower()
            
            def calculate_match_score(requested: str, supported: str, title: str) -> int:
                requested_lower = requested.lower()
                supported_lower = supported.lower()
                title_lower = title.lower()
                score = 0
                if requested_lower == supported_lower:
                    score += 1000
                if requested_lower in title_lower and supported_lower in title_lower:
                    score += 500
                requested_words = set(requested_lower.split())
                supported_words = set(supported_lower.split())
                overlap = len(requested_words.intersection(supported_words))
                score += overlap * 10
                if requested_words.issubset(supported_words):
                    score += 50
                if supported_words.issubset(requested_words):
                    score += 50
                return score
            
            if document_types:
                best_match = None
                best_score = 0
                for requested_type in document_types:
                    requested_lower = requested_type.lower().strip()
                    requested_words = set(requested_lower.split())
                    title_words = set(doc_title_lower.split())
                    if requested_words.intersection(title_words) or requested_lower in doc_title_lower:
                        for supported_type in supported_types:
                            score = calculate_match_score(requested_type, supported_type, doc_title)
                            if score > best_score:
                                best_score = score
                                best_match = supported_type
                if best_match and best_score >= 10:
                    normalized_doc_type = best_match
                    logger.info(f"[PROCESS] Normalized document type from '{doc_type}' to '{normalized_doc_type}' based on requested types (match score: {best_score})")
            
            if normalized_doc_type == "Unknown" or normalized_doc_type == "":
                best_match = None
                best_score = 0
                for supported_type in supported_types:
                    supported_lower = supported_type.lower()
                    supported_words = set(supported_lower.split())
                    title_words = set(doc_title_lower.split())
                    overlap = len(supported_words.intersection(title_words))
                    if supported_words.issubset(title_words):
                        overlap += len(supported_words)
                    if overlap > best_score:
                        best_score = overlap
                        best_match = supported_type
                if best_match and best_score >= 2:
                    normalized_doc_type = best_match
                    logger.info(f"[PROCESS] Normalized document type from '{doc_type}' to '{normalized_doc_type}' based on title (word overlap: {best_score})")
        
        # Check if we have an extraction schema
        from tools.extraction_schemas import get_extraction_schema
        try:
            schema = get_extraction_schema(normalized_doc_type)
        except ValueError:
            logger.warning(f"[PROCESS] No extraction schema found for '{normalized_doc_type}' - skipping extraction")
            return {
                "document_title": doc_title,
                "document_type": normalized_doc_type,
                "attachment_id": attachment_id,
                "status": "no_schema",
                "error": f"No extraction schema for document type: {normalized_doc_type}",
            }
        
        logger.info(f"[PROCESS] Found extraction schema for '{normalized_doc_type}' with {len(schema.get('properties', {}))} fields")
        
        # Extract entities
        extract_result = extract_document_entities.invoke({
            "file_path": file_path,
            "document_type": normalized_doc_type,
            "attachment_id": attachment_id,
        })
        
        if "error" in extract_result:
            logger.error(f"[PROCESS] Extraction failed for '{doc_title}': {extract_result['error']}")
            return {
                "document_title": doc_title,
                "document_type": normalized_doc_type,
                "attachment_id": attachment_id,
                "status": "extraction_failed",
                "error": extract_result["error"],
            }
        
        mapped_fields = extract_result.get("mapped_fields", {})
        
        if not mapped_fields:
            logger.warning(f"[PROCESS] No mapped fields for document '{doc_title}' (type: {normalized_doc_type})")
            from tools.field_mappings import get_all_mappings_for_document
            available_mappings = get_all_mappings_for_document(normalized_doc_type)
            if available_mappings:
                logger.warning(f"[PROCESS] Field mappings exist for '{normalized_doc_type}' but no fields were mapped. Extracted data: {list(extract_result.get('extracted_data', {}).keys())}")
            return {
                "document_title": doc_title,
                "document_type": normalized_doc_type,
                "attachment_id": attachment_id,
                "status": "no_mapped_fields",
                "extracted_fields": extract_result.get("extracted_data", {}),
            }
        
        # Get mapped fields dictionary
        mapped_result = write_extracted_fields.invoke({
            "loan_id": loan_id,
            "mapped_fields": mapped_fields,
            "document_type": normalized_doc_type,
            "attachment_id": attachment_id,
            "dry_run": dry_run,
        })
        
        return {
            "document_title": doc_title,
            "document_type": normalized_doc_type,
            "attachment_id": attachment_id,
            "status": "completed",
            "extraction": extract_result,
            "mapped_fields": mapped_result,
        }
        
    except Exception as e:
        logger.error(f"[PROCESS] Error processing document '{doc_title}': {e}")
        return {
            "document_title": doc_title,
            "document_type": doc_type,
            "attachment_id": attachment_id if 'attachment_id' in locals() else None,
            "status": "error",
            "error": str(e),
        }


@tool
def process_loan_documents(
    loan_id: str,
    document_types: Optional[List[str]] = None,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Process all documents for a loan: download, extract, and write fields.
    
    This is the main workflow tool that orchestrates the entire process.
    
    MULTIPLE DOCUMENT SUPPORT:
    - Processes ALL matching documents in the loan (not just one)
    - Each document is processed independently
    - Results are aggregated by document type
    - Fields are extracted from preferred documents when available
    
    Field Extraction Priority (from DrawingDoc Verifications.csv):
    - Field 4000 (Borrower First Name) → prefers "ID" document, but extracts from anywhere if ID not available
    - Field 610 (Escrow Company Name) → prefers "Title Report", but extracts from anywhere if Title Report not available
    - Field 356 (Appraised Value) → prefers "Appraisal Report", but extracts from anywhere if Appraisal not available
    - See field_mappings.py FIELD_PREFERRED_DOCUMENTS for complete mappings
    
    Args:
        loan_id: The Encompass loan GUID
        document_types: Optional list of document types to process (e.g., ["W-2", "ID", "Title Report"])
                       If None, processes all documents with extraction schemas
        dry_run: If True, simulate writes without actually writing (default: True)
        
    Returns:
        Dictionary with processing results for all documents:
        {
            "loan_id": "...",
            "total_documents_found": 167,
            "documents_processed": 3,
            "results": {
                "W-2": {"extracted_entities": {...}, "4002": "value", ...},
                "ID": {"extracted_entities": {...}, "4000": "value", ...},
                "Title Report": {"extracted_entities": {...}, "610": "value", ...}
            }
        }
    """
    import time
    process_start_time = time.time()
    
    logger.info(f"[PROCESS] Starting - Loan: {loan_id[:8]}...")
    logger.info(f"[PROCESS] Document types filter: {document_types or 'ALL (with schemas)'}")
    logger.info(f"[PROCESS] Dry run: {dry_run}")
    
    # Step 1: Get all documents
    step1_start = time.time()
    docs_result = get_loan_documents.invoke({"loan_id": loan_id})
    all_documents = docs_result.get("documents", [])
    step1_time = time.time() - step1_start
    logger.info(f"[PROCESS] Step 1 (Get documents) took {step1_time:.2f}s")
    
    if not all_documents:
        return {
            "loan_id": loan_id,
            "error": "No documents found for this loan",
            "total_documents": 0,
        }
    
    logger.info(f"[PROCESS] Found {len(all_documents)} total documents in loan")
    
    # Step 2: Filter documents to only those matching requested types
    from tools.extraction_schemas import list_supported_document_types
    
    matching_documents = []
    
    if document_types:
        # Filter to only documents that match the requested types
        # Use strict matching to avoid false positives
        for doc in all_documents:
            doc_title = doc.get("title", "Unknown")
            doc_type = doc.get("documentType") or doc.get("type", "Unknown")
            doc_title_lower = doc_title.lower()
            doc_type_lower = doc_type.lower()
            
            # Check if this document matches any requested type
            matches = False
            for requested_type in document_types:
                requested_lower = requested_type.lower().strip()
                
                # Strict matching - check for whole words or specific patterns
                if requested_lower == "id":
                    # For ID, match: "ID", "Driver License", "Driver's License", "State ID", "Identification"
                    # But NOT words containing "id" like "Evidence", "Provider", "Addendum"
                    import re
                    id_patterns = [
                        r'\bid\b',  # Whole word "id"
                        r'\bdriver.*license',  # "Driver License" or "Driver's License"
                        r'\bstate.*id\b',  # "State ID"
                        r'\bidentification',  # "Identification"
                        r'customer.*identification',  # "Customer Identification"
                    ]
                    matches_id = any(re.search(pattern, doc_title_lower) or re.search(pattern, doc_type_lower) 
                                   for pattern in id_patterns)
                    if matches_id:
                        matches = True
                        break
                elif requested_lower == "title report":
                    # Match "Title Report", "Prelim Title Report", "Preliminary Title Report"
                    if ("title report" in doc_title_lower or 
                        "title report" in doc_type_lower or
                        doc_title_lower.startswith("title report") or
                        "prelim" in doc_title_lower and "title" in doc_title_lower):
                        matches = True
                        break
                elif requested_lower == "appraisal report":
                    # Match "Appraisal Report", "Appraisal"
                    if ("appraisal report" in doc_title_lower or 
                        "appraisal report" in doc_type_lower or
                        (doc_title_lower.startswith("appraisal") and "report" in doc_title_lower) or
                        (doc_type_lower == "appraisal" and "report" in doc_title_lower)):
                        matches = True
                        break
                elif requested_lower in ["w-2", "w2"]:
                    # Match "W-2", "W2", "W-2 all years", etc.
                    if (requested_lower in doc_title_lower or 
                        requested_lower in doc_type_lower or
                        doc_title_lower.startswith(requested_lower) or
                        (doc_title_lower.startswith("w") and "2" in doc_title_lower)):
                        matches = True
                        break
                else:
                    # For other types, use exact or startswith matching
                    if (requested_lower == doc_title_lower or
                        requested_lower == doc_type_lower or
                        doc_title_lower.startswith(requested_lower) or
                        doc_type_lower.startswith(requested_lower)):
                        matches = True
                        break
            
            if matches:
                matching_documents.append(doc)
                logger.info(f"[PROCESS] Found matching document: {doc_title} (type: {doc_type})")
    else:
        # No filter - use all documents that have schemas
        supported_types = list_supported_document_types()
        for doc in all_documents:
            doc_title = doc.get("title", "Unknown")
            doc_type = doc.get("documentType") or doc.get("type", "Unknown")
            doc_title_lower = doc_title.lower()
            
            # Check if document has a schema
            has_schema = False
            for supported_type in supported_types:
                if supported_type.lower() in doc_title_lower or supported_type.lower() in doc_type.lower():
                    has_schema = True
                    break
            
            if has_schema:
                matching_documents.append(doc)
    
    logger.info(f"[PROCESS] Filtered to {len(matching_documents)} matching documents to process")
    
    if not matching_documents:
        return {
            "loan_id": loan_id,
            "total_documents_found": len(all_documents),
            "documents_processed": 0,
            "results": {
                "extracted_entities": {},
                "field_mappings": {}
            },
            "error": f"No documents found matching requested types: {document_types or 'with extraction schemas'}"
        }
    
    # Step 3: Process only the matching documents (in parallel for speed)
    processing_results = []
    
    # OPTIMIZATION: Prioritize documents - process preferred documents first
    # NOTE: We process ALL documents because duplicates might have different data or the first might fail
    from tools.csv_loader import get_csv_loader
    
    # Get preferred document types from CSV (documents marked as "Primary document")
    loader = get_csv_loader()
    all_csv_fields = loader.get_all_fields()
    preferred_doc_types = set()
    
    for field in all_csv_fields:
        primary_doc = field.get('primary_document', '').strip()
        if primary_doc:
            preferred_doc_types.add(primary_doc)
    
    # Separate documents into preferred and non-preferred for prioritization
    prioritized_docs = []
    other_docs = []
    
    for doc in matching_documents:
        doc_type = doc.get("documentType") or doc.get("type", "Unknown")
        doc_title = doc.get("title", "Unknown")
        doc_type_lower = doc_type.lower()
        doc_title_lower = doc_title.lower()
        
        # Check if this is a preferred document type
        is_preferred = any(
            pref.lower() in doc_type_lower or pref.lower() in doc_title_lower
            for pref in preferred_doc_types
        )
        
        if is_preferred:
            prioritized_docs.append(doc)
        else:
            other_docs.append(doc)
    
    # Combine: preferred first, then others - process ALL documents
    prioritized_matching_documents = prioritized_docs + other_docs
    
    logger.info(f"[OPTIMIZE] Priority order: {len(prioritized_docs)} preferred documents will be processed first, then {len(other_docs)} others")
    logger.info(f"[OPTIMIZE] Processing all {len(prioritized_matching_documents)} documents to ensure complete field extraction")
    
    # Preload extraction schemas for all document types we'll process (cache optimization)
    step2_start = time.time()
    if prioritized_matching_documents:
        unique_doc_types = set()
        for doc in prioritized_matching_documents:
            doc_type = doc.get("documentType") or doc.get("type", "Unknown")
            if doc_type != "Unknown":
                unique_doc_types.add(doc_type)
        
        # Preload schemas to populate cache
        from tools.extraction_schemas import get_extraction_schema
        for doc_type in unique_doc_types:
            try:
                schema = get_extraction_schema(doc_type)
                if schema:
                    logger.debug(f"[OPTIMIZE] Preloaded schema for {doc_type}")
            except Exception:
                pass  # Schema doesn't exist for this type, skip
    step2_time = time.time() - step2_start
    if step2_time > 0.1:
        logger.info(f"[PROCESS] Step 2 (Preload schemas) took {step2_time:.2f}s")
    
    def process_document(doc: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single document - extracted to function for parallel processing."""
        return _process_single_document(doc, loan_id, document_types, dry_run)
    
    # Process documents in parallel - increased workers for faster processing
    # OPTIMIZATION: Increased to 5 workers for better throughput
    # Monitor for rate limit errors - can reduce if needed
    max_workers = min(5, len(matching_documents), 5)
    
    step3_start = time.time()
    
    # Use prioritized list instead of original
    documents_to_process = prioritized_matching_documents
    
    if len(documents_to_process) > 1:
        logger.info(f"[PROCESS] Processing {len(documents_to_process)} documents in parallel (max {max_workers} concurrent)")
        logger.info(f"[PROCESS] Priority order: {len(prioritized_docs)} preferred documents processed first")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_doc = {executor.submit(process_document, doc): doc for doc in documents_to_process}
            for future in as_completed(future_to_doc):
                doc = future_to_doc[future]
                try:
                    result = future.result()
                    if result:
                        processing_results.append(result)
                except Exception as e:
                    logger.error(f"[PROCESS] Exception processing document '{doc.get('title', 'Unknown')}': {e}")
                    processing_results.append({
                        "document_title": doc.get("title", "Unknown"),
                        "document_type": doc.get("documentType", "Unknown"),
                        "status": "error",
                        "error": str(e),
                    })
    else:
        # Sequential processing for single document
        for doc in documents_to_process:
            result = _process_single_document(doc, loan_id, document_types, dry_run)
            if result:
                processing_results.append(result)
    
    step3_time = time.time() - step3_start
    logger.info(f"[PROCESS] Step 3 (Process documents) took {step3_time:.2f}s")
    logger.info(f"[PROCESS] Complete - Processed {len(processing_results)} documents")
    
    # Aggregate results with separated structure:
    # - extracted_entities: organized by document type
    # - field_mappings: final field_id -> value mapping (prioritized by preferred documents)
    aggregated_results = {
        "extracted_entities": {},
        "field_mappings": {}
    }
    
    # Track which fields have been extracted from preferred documents
    # Format: {field_id: (value, source_document_type, is_preferred)}
    field_extractions = {}
    
    from tools.field_mappings import get_preferred_documents_for_field, should_extract_from_document
    
    # First pass: Collect all extractions, prioritizing preferred documents
    for result in processing_results:
        doc_type = result.get("document_type", "Unknown")
        doc_title = result.get("document_title", "")
        mapped_result = result.get("mapped_fields", {})
        
        if doc_type in mapped_result:
            doc_data = mapped_result[doc_type]
            
            # Process each field
            for key, value in doc_data.items():
                if key == "extracted_entities":
                    # Store extracted entities per document type
                    if doc_type not in aggregated_results["extracted_entities"]:
                        aggregated_results["extracted_entities"][doc_type] = {}
                    aggregated_results["extracted_entities"][doc_type].update(value)
                else:
                    # This is an Encompass field ID (e.g., "4002")
                    field_id = key
                    preferred_docs = get_preferred_documents_for_field(field_id)
                    
                    # Check if this document is preferred for this field
                    is_preferred = any(
                        pref.lower() in doc_type.lower() or 
                        pref.lower() in doc_title.lower()
                        for pref in preferred_docs
                    ) if preferred_docs else False
                    
                    # Store extraction (prefer preferred documents, but prefer non-zero values)
                    # Check if value is meaningful (not None, not empty string, not 0 for numeric)
                    is_meaningful = value is not None and value != "" and value != 0
                    
                    if field_id not in field_extractions:
                        field_extractions[field_id] = (value, doc_type, is_preferred, is_meaningful)
                    else:
                        existing_value, existing_doc, existing_preferred, existing_meaningful = field_extractions[field_id]
                        
                        # Prefer meaningful values over non-meaningful ones
                        if is_meaningful and not existing_meaningful:
                            field_extractions[field_id] = (value, doc_type, is_preferred, is_meaningful)
                        elif not is_meaningful and existing_meaningful:
                            # Keep existing meaningful value
                            pass
                        elif is_preferred and not existing_preferred:
                            # Replace with preferred document extraction
                            field_extractions[field_id] = (value, doc_type, is_preferred, is_meaningful)
                        elif not existing_preferred and not is_preferred:
                            # Both are non-preferred, prefer meaningful value
                            if is_meaningful and not existing_meaningful:
                                field_extractions[field_id] = (value, doc_type, is_preferred, is_meaningful)
                            # Otherwise keep first one
    
    # Second pass: Build final field_mappings (prioritized) - only include fields with actual values
    for field_id, extraction_data in field_extractions.items():
        # Handle both old format (3-tuple) and new format (4-tuple)
        if len(extraction_data) == 4:
            value, source_doc_type, is_preferred, is_meaningful = extraction_data
        else:
            value, source_doc_type, is_preferred = extraction_data
            is_meaningful = value is not None and value != "" and value != 0
        
        # Only include mapped fields with meaningful values (non-empty, non-zero)
        if is_meaningful:
            aggregated_results["field_mappings"][field_id] = value
            
            # Log preferred document usage
            if is_preferred:
                logger.info(f"[AGGREGATE] Field {field_id} extracted from preferred document: {source_doc_type}")
            else:
                preferred_docs = get_preferred_documents_for_field(field_id)
                if preferred_docs:
                    logger.info(f"[AGGREGATE] Field {field_id} extracted from {source_doc_type} (preferred: {', '.join(preferred_docs)})")
                else:
                    logger.info(f"[AGGREGATE] Field {field_id} extracted from {source_doc_type} (no preference)")
    
    # Clean up extracted_entities - only include fields that were actually extracted (non-empty)
    cleaned_extracted_entities = {}
    for doc_type, entities in aggregated_results["extracted_entities"].items():
        cleaned_entities = {k: v for k, v in entities.items() if v is not None and v != ""}
        if cleaned_entities:  # Only include document types with non-empty extracted fields
            cleaned_extracted_entities[doc_type] = cleaned_entities
    
    # Build final clean results - only mapped fields
    aggregation_start = time.time()
    final_results = {
        "extracted_entities": cleaned_extracted_entities,
        "field_mappings": aggregated_results["field_mappings"],  # Only non-empty mapped fields
    }
    aggregation_time = time.time() - aggregation_start
    
    total_time = time.time() - process_start_time
    
    logger.info(f"[PROCESS] ========================================")
    logger.info(f"[PROCESS] TIMING SUMMARY:")
    logger.info(f"[PROCESS]   Total time: {total_time:.2f}s ({total_time/60:.2f} minutes)")
    logger.info(f"[PROCESS]   - Get documents: {step1_time:.2f}s")
    logger.info(f"[PROCESS]   - Preload schemas: {step2_time:.2f}s")
    logger.info(f"[PROCESS]   - Process documents: {step3_time:.2f}s")
    logger.info(f"[PROCESS]   - Aggregate results: {aggregation_time:.2f}s")
    if processing_results:
        logger.info(f"[PROCESS]   Average per document: {step3_time/len(processing_results):.2f}s")
    logger.info(f"[PROCESS] ========================================")
    
    return {
        "loan_id": loan_id,
        "total_documents_found": len(all_documents),
        "documents_processed": len(processing_results),
        "results": final_results,
        "timing": {
            "total_time_seconds": round(total_time, 2),
            "total_time_minutes": round(total_time / 60, 2),
            "average_time_per_document_seconds": round(step3_time / len(processing_results), 2) if processing_results else 0,
            "get_documents_time_seconds": round(step1_time, 2),
            "preload_schemas_time_seconds": round(step2_time, 2),
            "processing_time_seconds": round(step3_time, 2),
            "aggregation_time_seconds": round(aggregation_time, 2),
        }
    }


# =============================================================================
# AGENT CONFIGURATION
# =============================================================================

preparation_instructions = """You are a Preparation Sub-Agent for Encompass loan processing.

Your job is to:
1. Retrieve all documents for a given loan
2. Process each document through OCR extraction
3. Map extracted fields to Encompass field IDs
4. Write fields back to Encompass (if enabled)

IMPORTANT SAFETY RULES:
- Check ENABLE_ENCOMPASS_WRITES environment variable before writing
- By default, writes are DISABLED (dry_run=True) to protect production
- Always verify field mappings before writing
- Log all write operations for audit purposes

WORKFLOW:
1. Use process_loan_documents(loan_id) to process all documents
2. Or use individual tools: get_loan_documents → download_document → extract_document_entities → write_extracted_fields

When processing:
- Extract entities from each document using LandingAI
- Map extracted fields to Encompass field IDs using field_mappings
- Only write fields that have valid mappings (not "TBD")
- Report any unmapped or pending fields for manual review
"""

# Create the preparation agent
preparation_agent = create_deep_agent(
    agent_type="Preparation-SubAgent",
    system_prompt=preparation_instructions,
    tools=[
        get_loan_documents,
        download_document,
        extract_document_entities,
        get_mapped_fields_dict,
        write_extracted_fields,
        process_loan_documents,
    ],
)


# =============================================================================
# JSON INPUT SUPPORT
# =============================================================================

def process_from_json(input_json: Dict[str, Any]) -> Dict[str, Any]:
    """Process documents from JSON input.
    
    Args:
        input_json: JSON dictionary with loan_id and optional parameters
        
    Returns:
        Dictionary with processing results (always returns a dict)
        
    Example input:
        {
            "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
            "document_types": ["W-2"],
            "dry_run": true
        }
    """
    # Validate required fields
    if "loan_id" not in input_json:
        return {
            "error": "Missing required field: loan_id",
            "expected_format": {
                "loan_id": "string (required)",
                "document_types": "array of strings (optional)",
                "dry_run": "boolean (optional, default: true)"
            }
        }
    
    loan_id = input_json["loan_id"]
    document_types = input_json.get("document_types")
    dry_run = input_json.get("dry_run", True)
    
    # Safety check - always use dry_run since writes are disabled
    dry_run = True
    
    logger.info(f"Processing loan: {loan_id[:8]}...")
    logger.info(f"Document types filter: {document_types or 'ALL (with schemas)'}")
    logger.info(f"Dry run: {dry_run} (SAFE MODE - No writes)")
    
    try:
        # Process documents
        result = process_loan_documents.invoke({
            "loan_id": loan_id,
            "document_types": document_types,
            "dry_run": dry_run,
        })
        
        # Ensure result is always a dictionary
        if not isinstance(result, dict):
            return {
                "error": "Unexpected result type",
                "result_type": str(type(result)),
                "loan_id": loan_id
            }
        
        # Ensure results key exists and is a dict
        if "results" not in result:
            result["results"] = {}
        
        # Ensure results is always a dictionary (even if empty)
        if not isinstance(result.get("results"), dict):
            result["results"] = {}
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing loan: {e}")
        return {
            "error": str(e),
            "loan_id": loan_id,
            "results": {}
        }


# =============================================================================
# TEST/DEMO FUNCTIONS
# =============================================================================

if __name__ == "__main__":
    import argparse
    from langchain_core.messages import HumanMessage
    
    parser = argparse.ArgumentParser(
        description="Preparation Sub-Agent - Document Processing and Field Population"
    )
    parser.add_argument("--loan-id", type=str, help="Loan ID to process")
    parser.add_argument("--demo", action="store_true", help="Run demo with test loan ID")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Dry run mode (default: True)")
    parser.add_argument("--enable-writes", action="store_true", help="Enable writes (overrides env var)")
    parser.add_argument("--json", type=str, help="JSON input as string")
    parser.add_argument("--json-file", type=str, help="Path to JSON input file")
    
    args = parser.parse_args()
    
    # Handle JSON input
    if args.json or args.json_file:
        if args.json:
            input_data = json.loads(args.json)
        else:
            with open(args.json_file, 'r') as f:
                input_data = json.load(f)
        
        result = process_from_json(input_data)
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0)
    
    if args.enable_writes:
        # Modify the module-level variable
        import preparation_agent as prep_module
        prep_module.ENABLE_WRITES = True
        ENABLE_WRITES = True  # Update local reference
        logger.warning("⚠️  WRITES ENABLED via command line argument!")
    
    if args.demo:
        # Demo with a test loan ID
        test_loan_id = "387596ee-7090-47ca-8385-206e22c9c9da"
        print("=" * 80)
        print("Demo: Preparation Sub-Agent")
        print("=" * 80)
        print(f"Loan ID: {test_loan_id}")
        print(f"Dry Run: {args.dry_run}")
        print(f"Writes Enabled: {ENABLE_WRITES}")
        print()
        
        task = f"Process all documents for loan {test_loan_id}. Extract entities and map them to Encompass fields."
        if args.dry_run:
            task += " Use dry run mode - do not actually write to Encompass."
        
        result = preparation_agent.invoke({"messages": [HumanMessage(content=task)]})
        
        print("=" * 80)
        print("Agent Response:")
        print("=" * 80)
        for message in result["messages"]:
            if hasattr(message, "content") and message.content:
                print(f"\n{message.type}: {message.content}")
    
    elif args.loan_id:
        task = f"Process all documents for loan {args.loan_id}."
        if args.dry_run:
            task += " Use dry run mode."
        
        result = preparation_agent.invoke({"messages": [HumanMessage(content=task)]})
        
        for message in result["messages"]:
            if hasattr(message, "content") and message.content:
                print(message.content)
    
    else:
        print("Preparation Sub-Agent")
        print("=" * 80)
        print()
        print("Usage:")
        print("  python preparation_agent.py --json-file input.json    # Process from JSON file")
        print("  python preparation_agent.py --json '{\"loan_id\":\"...\"}'  # Process from JSON string")
        print("  python preparation_agent.py --demo                    # Run demo")
        print("  python preparation_agent.py --loan-id <GUID>          # Process specific loan")
        print()
        print("JSON Input Format:")
        print("  {")
        print('    "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",')
        print('    "document_types": ["W-2", "W2"]  // optional')
        print("  }")
        print()
        print("Note: This agent does NOT write to Encompass - it only returns extracted data.")
        print()

