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
env_file_path = Path(__file__).parent / ".env"
print(f"Loading environment from: {env_file_path}")
load_dotenv(env_file_path)

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

# Handle imports from both standalone and orchestrator contexts
try:
    # Try relative imports first (when run as standalone)
    from tools.extraction_schemas import get_extraction_schema, list_supported_document_types
    from tools.field_mappings import (
        get_field_mapping,
        get_all_mappings_for_document,
        is_mapping_ready,
        list_ready_mappings,
        get_common_field_ids
    )
except ImportError:
    # Fall back to absolute imports (when called from orchestrator)
    from agents.drawdocs.subagents.preparation_agent.tools.extraction_schemas import get_extraction_schema, list_supported_document_types
    from agents.drawdocs.subagents.preparation_agent.tools.field_mappings import (
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
# PROGRESS CALLBACK
# =============================================================================
# Module-level callbacks for live updates during document processing
# Set via set_progress_callback() and set_log_callback() before calling process_loan_documents()
_progress_callback = None
_log_callback = None

def set_progress_callback(callback):
    """Set the progress callback for live metric updates.
    
    The callback signature should be:
        callback(documents_found, documents_processed, fields_extracted, current_document)
    
    Args:
        callback: Callable or None to clear
    """
    global _progress_callback
    _progress_callback = callback

def set_log_callback(callback):
    """Set the log callback for detailed activity logging.
    
    The callback signature should be:
        callback(message, level, event_type, details)
    
    Args:
        callback: Callable or None to clear
    """
    global _log_callback
    _log_callback = callback

def _notify_progress(documents_found=None, documents_processed=None, fields_extracted=None, current_document=None):
    """Notify progress if callback is set."""
    if _progress_callback:
        try:
            _progress_callback(
                documents_found=documents_found,
                documents_processed=documents_processed,
                fields_extracted=fields_extracted,
                current_document=current_document,
            )
        except Exception as e:
            logger.warning(f"Progress callback failed: {e}")

def _log_activity(message: str, level: str = "info", event_type: str = None, details: dict = None):
    """Log activity if callback is set."""
    if _log_callback:
        try:
            _log_callback(
                message=message,
                level=level,
                event_type=event_type,
                details=details,
            )
        except Exception as e:
            logger.warning(f"Log callback failed: {e}")


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
    
    Files are saved with filename based on attachment_id (e.g., "{attachment_id}.pdf").
    If a file already exists, it will not be re-downloaded.
    
    Args:
        loan_id: The Encompass loan GUID
        attachment_id: The attachment entity ID (used as filename)
        document_title: Optional document title (e.g., "W-2", "Title Report") - for reference only
        document_type: Optional document type (e.g., "W-2", "ID") - for reference only
        
    Returns:
        Dictionary with file_path and metadata
    """
    import time
    
    logger.info(f"[DOWNLOAD] Starting - Loan: {loan_id[:8]}..., Attachment: {attachment_id[:8]}...")
    
    output_dir = _get_output_directory(loan_id)
    
    # Use attachment_id as filename
    file_path = output_dir / f'{attachment_id}.pdf'
    
    # Check if file already exists - if so, skip download (same attachment_id = same file)
    if file_path.exists():
        file_size = file_path.stat().st_size
        size_kb = file_size / 1024
        logger.info(f"[DOWNLOAD] File already exists ({attachment_id}.pdf), skipping download - {file_size:,} bytes ({size_kb:.2f} KB)")
        
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
    logger.info(f"[DOWNLOAD] Success - {len(document_bytes):,} bytes ({size_kb:.2f} KB) saved to {attachment_id}.pdf")
    
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
            try:
                from tools.extraction_schemas import list_supported_document_types
            except ImportError:
                from agents.drawdocs.subagents.preparation_agent.tools.extraction_schemas import list_supported_document_types
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
        try:
            from tools.extraction_schemas import get_extraction_schema
        except ImportError:
                from agents.drawdocs.subagents.preparation_agent.tools.extraction_schemas import get_extraction_schema
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
        
        # Safety check: ensure extract_result is not None
        if extract_result is None:
            logger.error(f"[PROCESS] Extraction returned None for '{doc_title}'")
            return {
                "document_title": doc_title,
                "document_type": normalized_doc_type,
                "attachment_id": attachment_id,
                "status": "extraction_failed",
                "error": "Extraction returned None",
            }
        
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
            try:
                from tools.field_mappings import get_all_mappings_for_document
            except ImportError:
                from agents.drawdocs.subagents.preparation_agent.tools.field_mappings import get_all_mappings_for_document
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
    
    # Notify progress: documents found
    _notify_progress(documents_found=len(all_documents), documents_processed=0, fields_extracted=0)
    
    # Step 2: Filter documents to only those matching requested types
    try:
        from tools.extraction_schemas import list_supported_document_types
    except ImportError:
        from agents.drawdocs.subagents.preparation_agent.tools.extraction_schemas import list_supported_document_types
    
    matching_documents = []
    MAX_DOCS_PER_TYPE = 5  # Process up to 5 documents per requested type
    
    if document_types:
        # Filter to only documents that match the requested types
        # Use strict matching to avoid false positives
        # Track which documents match which requested types
        documents_by_requested_type = {req_type: [] for req_type in document_types}
        
        for doc in all_documents:
            doc_title = doc.get("title", "Unknown")
            doc_type = doc.get("documentType") or doc.get("type", "Unknown")
            doc_title_lower = doc_title.lower()
            doc_type_lower = doc_type.lower()
            
            # Check if this document matches any requested type
            matches = False
            matched_requested_type = None
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
                        matched_requested_type = requested_type
                        break
                elif requested_lower == "title report":
                    # Match "Title Report", "Prelim Title Report", "Preliminary Title Report"
                    if ("title report" in doc_title_lower or 
                        "title report" in doc_type_lower or
                        doc_title_lower.startswith("title report") or
                        "prelim" in doc_title_lower and "title" in doc_title_lower):
                        matches = True
                        matched_requested_type = requested_type
                        break
                elif requested_lower == "appraisal report":
                    # Match "Appraisal Report", "Appraisal"
                    if ("appraisal report" in doc_title_lower or 
                        "appraisal report" in doc_type_lower or
                        (doc_title_lower.startswith("appraisal") and "report" in doc_title_lower) or
                        (doc_type_lower == "appraisal" and "report" in doc_title_lower)):
                        matches = True
                        matched_requested_type = requested_type
                        break
                elif requested_lower in ["w-2", "w2"]:
                    # Match "W-2", "W2", "W-2 all years", etc.
                    if (requested_lower in doc_title_lower or 
                        requested_lower in doc_type_lower or
                        doc_title_lower.startswith(requested_lower) or
                        (doc_title_lower.startswith("w") and "2" in doc_title_lower)):
                        matches = True
                        matched_requested_type = requested_type
                        break
                else:
                    # For other types, use exact or startswith matching
                    if (requested_lower == doc_title_lower or
                        requested_lower == doc_type_lower or
                        doc_title_lower.startswith(requested_lower) or
                        doc_type_lower.startswith(requested_lower)):
                        matches = True
                        matched_requested_type = requested_type
                        break
            
            if matches and matched_requested_type:
                # Store which requested type this document matches
                documents_by_requested_type[matched_requested_type].append(doc)
                logger.debug(f"[PROCESS] Found matching document: {doc_title} (type: {doc_type}) for requested type: {matched_requested_type}")
        
        # Now select up to 5 BEST documents for each requested type (balance speed vs coverage)
        # Increased to help find ID documents and other types that might be missed
        matching_documents = []
        
        def score_document(doc: Dict[str, Any], requested_type: str, preferred_doc_types: set) -> tuple:
            """Score a document - higher score = better match. Returns (score, is_exact_title, is_preferred)."""
            doc_title = doc.get("title", "Unknown")
            doc_type = doc.get("documentType") or doc.get("type", "Unknown")
            doc_title_lower = doc_title.lower()
            doc_type_lower = doc_type.lower()
            requested_lower = requested_type.lower().strip()
            
            score = 0
            
            # Exact title match = highest priority (score 1000)
            if doc_title_lower == requested_lower:
                score += 1000
            
            # Exact type match = high priority (score 800)
            if doc_type_lower == requested_lower:
                score += 800
            
            # Preferred document type = priority boost (score 400)
            is_preferred = any(
                pref.lower() in doc_type_lower or pref.lower() in doc_title_lower
                for pref in preferred_doc_types
            )
            if is_preferred:
                score += 400
            
            # Title starts with requested type = medium priority (score 200)
            if doc_title_lower.startswith(requested_lower):
                score += 200
            
            # Type starts with requested type = medium priority (score 100)
            if doc_type_lower.startswith(requested_lower):
                score += 100
            
            return (score, doc_title_lower == requested_lower, is_preferred)
        
        # Get preferred doc types for scoring (load once)
        try:
            from tools.csv_loader import get_csv_loader
        except ImportError:
                from agents.drawdocs.subagents.preparation_agent.tools.csv_loader import get_csv_loader
        loader = get_csv_loader()
        all_csv_fields = loader.get_all_fields()
        preferred_doc_types = set()
        for field in all_csv_fields:
            primary_doc = field.get('primary_document', '').strip()
            if primary_doc:
                preferred_doc_types.add(primary_doc)
        
        # Select up to MAX_DOCS_PER_TYPE best documents for each requested type
        for requested_type in document_types:  # Check all requested types, even if no matches
            docs = documents_by_requested_type.get(requested_type, [])
            if not docs:
                logger.warning(f"[PROCESS] ⚠️  No documents found matching requested type: '{requested_type}'")
                # Show available document titles that might match
                all_titles = [d.get("title", "Unknown") for d in all_documents]
                logger.warning(f"[PROCESS] Available document titles (first 15): {all_titles[:15]}")
                continue
            
            # Score all documents
            scored_docs = [(doc, score_document(doc, requested_type, preferred_doc_types)) for doc in docs]
            # Sort by score (descending), then by exact title match, then by preferred status
            scored_docs.sort(key=lambda x: (x[1][0], x[1][1], x[1][2]), reverse=True)
            
            # For ID, process ALL matching documents (no limit) to ensure we find it
            # For other types, use MAX_DOCS_PER_TYPE limit
            if requested_type.lower() == "id":
                selected_docs = scored_docs  # Process all ID documents
                logger.info(f"[PROCESS] Processing ALL {len(selected_docs)} ID documents (no limit for ID)")
            else:
                # Select up to MAX_DOCS_PER_TYPE best documents
                selected_docs = scored_docs[:MAX_DOCS_PER_TYPE]
            
            for doc, (score, is_exact_title, is_preferred) in selected_docs:
                doc_title = doc.get("title", "Unknown")
                logger.info(f"[PROCESS] Selected match for '{requested_type}': {doc_title} (score: {score}, exact_title: {is_exact_title}, preferred: {is_preferred})")
                matching_documents.append(doc)
            
            if len(docs) > MAX_DOCS_PER_TYPE:
                logger.info(f"[PROCESS] Selected {len(selected_docs)} best document(s) for '{requested_type}' (skipped {len(docs) - MAX_DOCS_PER_TYPE} lower-scoring documents)")
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
    
    # Step 3: Process only the best matching documents (one per requested type)
    processing_results = []
    
    # We've already selected up to MAX_DOCS_PER_TYPE best documents per requested type
    prioritized_matching_documents = matching_documents
    
    logger.info(f"[OPTIMIZE] Processing {len(prioritized_matching_documents)} best-matched documents (up to {MAX_DOCS_PER_TYPE} per requested type)")
    
    # Preload extraction schemas for all document types we'll process (cache optimization)
    step2_start = time.time()
    if prioritized_matching_documents:
        unique_doc_types = set()
        for doc in prioritized_matching_documents:
            doc_type = doc.get("documentType") or doc.get("type", "Unknown")
            if doc_type != "Unknown":
                unique_doc_types.add(doc_type)
        
        # Preload schemas to populate cache
        try:
            from tools.extraction_schemas import get_extraction_schema
        except ImportError:
                from agents.drawdocs.subagents.preparation_agent.tools.extraction_schemas import get_extraction_schema
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
    
    # Track progress for live updates
    docs_processed_count = 0
    fields_extracted_count = 0
    
    if len(documents_to_process) > 1:
        logger.info(f"[PROCESS] Processing {len(documents_to_process)} best-matched documents in parallel (max {max_workers} concurrent)")
        _log_activity(
            f"Processing {len(documents_to_process)} documents in parallel",
            level="info",
            event_type="prep_summary",
            details={"document_count": len(documents_to_process)}
        )
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_doc = {executor.submit(process_document, doc): doc for doc in documents_to_process}
            for future in as_completed(future_to_doc):
                doc = future_to_doc[future]
                doc_title = doc.get("title", "Unknown")
                doc_type = doc.get("documentType") or doc.get("type", "Unknown")
                try:
                    result = future.result()
                    if result:
                        processing_results.append(result)
                        # Count fields extracted from this document
                        mapped_fields = result.get("mapped_fields", {})
                        doc_field_count = 0
                        for doc_data in mapped_fields.values():
                            if isinstance(doc_data, dict):
                                doc_field_count += len([k for k in doc_data.keys() if k != "extracted_entities"])
                        fields_extracted_count += doc_field_count
                        
                        # Log successful extraction
                        if doc_field_count > 0:
                            _log_activity(
                                f"Extracted {doc_field_count} fields from {doc_title[:25]}",
                                level="info",
                                event_type="fields_extracted",
                                details={"document_name": doc_title, "field_count": doc_field_count}
                            )
                except Exception as e:
                    logger.error(f"[PROCESS] Exception processing document '{doc_title}': {e}")
                    processing_results.append({
                        "document_title": doc_title,
                        "document_type": doc_type,
                        "status": "error",
                        "error": str(e),
                    })
                    # Log error
                    _log_activity(
                        f"Failed to process {doc_title[:25]}: {str(e)[:50]}",
                        level="error",
                        event_type="document",
                        details={"document_name": doc_title, "error": str(e)}
                    )
                
                # Update progress after each document
                docs_processed_count += 1
                _notify_progress(
                    documents_processed=docs_processed_count,
                    fields_extracted=fields_extracted_count,
                    current_document=doc_title[:30] if doc_title else None,
                )
    else:
        # Sequential processing for single document
        for doc in documents_to_process:
            doc_title = doc.get("title", "Unknown")
            _notify_progress(current_document=doc_title[:30] if doc_title else None)
            _log_activity(
                f"Processing: {doc_title[:30]}",
                level="info",
                event_type="document",
                details={"document_name": doc_title}
            )
            
            result = _process_single_document(doc, loan_id, document_types, dry_run)
            if result:
                processing_results.append(result)
                # Count fields extracted
                mapped_fields = result.get("mapped_fields", {})
                doc_field_count = 0
                for doc_data in mapped_fields.values():
                    if isinstance(doc_data, dict):
                        doc_field_count += len([k for k in doc_data.keys() if k != "extracted_entities"])
                fields_extracted_count += doc_field_count
                
                if doc_field_count > 0:
                    _log_activity(
                        f"Extracted {doc_field_count} fields from {doc_title[:25]}",
                        level="info",
                        event_type="fields_extracted",
                        details={"document_name": doc_title, "field_count": doc_field_count}
                    )
            
            docs_processed_count += 1
            _notify_progress(
                documents_processed=docs_processed_count,
                fields_extracted=fields_extracted_count,
            )
    
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
    # Format: {field_id: (value, source_document_type, attachment_id, is_preferred, is_valid, is_non_zero)}
    field_extractions = {}
    
    try:
        from tools.field_mappings import get_preferred_documents_for_field, should_extract_from_document
    except ImportError:
            from agents.drawdocs.subagents.preparation_agent.tools.field_mappings import get_preferred_documents_for_field, should_extract_from_document
    
    # First pass: Collect all extractions, prioritizing preferred documents
    for result in processing_results:
        doc_type = result.get("document_type", "Unknown")
        doc_title = result.get("document_title", "")
        attachment_id = result.get("attachment_id")
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
                    # Check if value is valid (not None, not empty string) - 0 is a valid value
                    is_valid = value is not None and value != ""
                    is_non_zero = is_valid and value != 0
                    
                    if field_id not in field_extractions:
                        field_extractions[field_id] = (value, doc_type, attachment_id, is_preferred, is_valid, is_non_zero)
                    else:
                        existing_value, existing_doc, existing_att_id, existing_preferred, existing_valid, existing_non_zero = field_extractions[field_id]
                        
                        # Prefer non-zero values over zero values
                        if is_non_zero and not existing_non_zero:
                            field_extractions[field_id] = (value, doc_type, attachment_id, is_preferred, is_valid, is_non_zero)
                        elif not is_non_zero and existing_non_zero:
                            # Keep existing non-zero value
                            pass
                        elif is_preferred and not existing_preferred:
                            # Replace with preferred document extraction
                            field_extractions[field_id] = (value, doc_type, attachment_id, is_preferred, is_valid, is_non_zero)
                        elif not existing_preferred and not is_preferred:
                            # Both are non-preferred, prefer non-zero value
                            if is_non_zero and not existing_non_zero:
                                field_extractions[field_id] = (value, doc_type, attachment_id, is_preferred, is_valid, is_non_zero)
                            # Otherwise keep first one
    
    # Second pass: Build final field_mappings (prioritized) - include all valid values (including 0)
    # Format: {field_id: {"value": value, "attachment_id": attachment_id}}
    # Only exclude None and empty strings - 0 is a valid value
    for field_id, extraction_data in field_extractions.items():
        # Handle tuple formats: (value, doc_type, attachment_id, is_preferred, is_valid, is_non_zero) or older formats
        if len(extraction_data) == 6:
            value, source_doc_type, attachment_id, is_preferred, is_valid, is_non_zero = extraction_data
        elif len(extraction_data) == 5:
            value, source_doc_type, is_preferred, is_valid, is_non_zero = extraction_data
            attachment_id = None  # Fallback for older format
        elif len(extraction_data) == 4:
            value, source_doc_type, is_preferred, is_meaningful = extraction_data
            attachment_id = None
            is_valid = value is not None and value != ""
            is_non_zero = is_valid and value != 0
        else:
            value, source_doc_type, is_preferred = extraction_data
            attachment_id = None
            is_valid = value is not None and value != ""
            is_non_zero = is_valid and value != 0
        
        # Include all valid values (including 0) - only exclude None and empty strings
        if is_valid:
            aggregated_results["field_mappings"][field_id] = {
                "value": value,
                "attachment_id": attachment_id
            }
            
            # Log preferred document usage
            value_type = "non-zero" if is_non_zero else "zero"
            att_id_str = f" (attachment: {attachment_id[:8]}...)" if attachment_id else ""
            if is_preferred:
                logger.debug(f"[AGGREGATE] Field {field_id} = {value} ({value_type}) from preferred document: {source_doc_type}{att_id_str}")
            else:
                preferred_docs = get_preferred_documents_for_field(field_id)
                if preferred_docs:
                    logger.debug(f"[AGGREGATE] Field {field_id} = {value} ({value_type}) from {source_doc_type} (preferred: {', '.join(preferred_docs)}){att_id_str}")
                else:
                    logger.debug(f"[AGGREGATE] Field {field_id} = {value} ({value_type}) from {source_doc_type}{att_id_str}")
    
    # Log summary
    total_fields = len(aggregated_results["field_mappings"])
    non_zero_fields = sum(1 for v in aggregated_results["field_mappings"].values() 
                         if isinstance(v, dict) and v.get("value", 0) != 0)
    zero_fields = total_fields - non_zero_fields
    logger.info(f"[AGGREGATE] Field mappings summary: {total_fields} total ({non_zero_fields} non-zero, {zero_fields} zero values)")
    
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

