"""
Rack & Stack Integration Tool for Loan Officer Assistant.

This module integrates with TaskTile's Rack & Stack pipeline to process
loan documents from Encompass eFolder. It handles:
1. Fetching document list from Encompass
2. Downloading PDF content
3. Uploading to TaskTile
4. Creating and tracking R&S jobs

Usage:
    from tools.rack_and_stack import submit_efolder_to_rack_and_stack
    
    job = await submit_efolder_to_rack_and_stack(
        loan_id="59d7a711-...",
        max_documents=50  # Optional limit
    )
    print(f"Job ID: {job.job_id}")
"""

import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

# Add paths for imports
LOA_DIR = Path(__file__).parent.parent
PROJECT_ROOT = LOA_DIR.parent.parent
sys.path.insert(0, str(LOA_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment
load_dotenv(PROJECT_ROOT / ".env")

# Import shared utilities
from packages.shared import get_access_token, get_encompass_client

# Import TaskTile client
from tools.tasktile_client import TaskTileClient, JobResult, UploadResult

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class EFolderDocument:
    """Document from Encompass eFolder."""
    attachment_id: str
    title: str
    content_type: str = "application/pdf"
    file_size: int = 0
    created_date: Optional[str] = None
    is_active: bool = True


@dataclass 
class RackAndStackSubmission:
    """Result of submitting documents to Rack & Stack."""
    loan_id: str
    job_id: str
    pipeline: List[str]
    documents_submitted: int
    upload_results: List[Dict[str, Any]] = field(default_factory=list)
    submitted_at: str = ""
    status: str = "submitted"
    error: Optional[str] = None


# =============================================================================
# ENCOMPASS DOCUMENT FUNCTIONS
# =============================================================================

def _get_api_client():
    """Get authenticated API client components."""
    api_base_url = os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com")
    access_token = get_access_token()
    return api_base_url, access_token


def fetch_efolder_documents(loan_id: str) -> List[EFolderDocument]:
    """
    Fetch list of documents from Encompass eFolder.
    
    Args:
        loan_id: Encompass loan GUID
        
    Returns:
        List of EFolderDocument objects
    """
    api_base_url, token = _get_api_client()
    url = f"{api_base_url}/encompass/v3/loans/{loan_id}/attachments"
    
    logger.info(f"[R&S] Fetching eFolder documents for loan {loan_id[:8]}...")
    
    try:
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=60
        )
        
        if resp.status_code != 200:
            logger.error(f"[R&S] Failed to fetch attachments: {resp.status_code}")
            return []
        
        raw_docs = resp.json()
        documents = []
        
        for doc in raw_docs:
            # Skip removed documents
            if doc.get("isRemoved", False):
                continue
            
            # Only include PDF documents
            content_type = doc.get("contentType", "").lower()
            if "pdf" not in content_type and content_type != "":
                continue
            
            documents.append(EFolderDocument(
                attachment_id=doc.get("id", ""),
                title=doc.get("title", "Unknown"),
                content_type="application/pdf",
                file_size=doc.get("size", 0),
                created_date=doc.get("createdDate"),
                is_active=not doc.get("isRemoved", False),
            ))
        
        logger.info(f"[R&S] ✓ Found {len(documents)} PDF documents in eFolder")
        return documents
        
    except Exception as e:
        logger.error(f"[R&S] Error fetching eFolder: {e}")
        return []


def download_document_bytes(loan_id: str, attachment_id: str) -> Optional[bytes]:
    """
    Download document content from Encompass.
    
    Args:
        loan_id: Encompass loan GUID
        attachment_id: Attachment ID to download
        
    Returns:
        PDF bytes or None if failed
    """
    try:
        client = get_encompass_client()
        document_bytes = client.download_attachment(loan_id, attachment_id)
        
        if document_bytes:
            logger.debug(f"[R&S] Downloaded {len(document_bytes)} bytes for {attachment_id[:8]}")
            return document_bytes
        else:
            logger.warning(f"[R&S] Empty document returned for {attachment_id[:8]}")
            return None
            
    except Exception as e:
        logger.error(f"[R&S] Failed to download {attachment_id[:8]}: {e}")
        return None


# =============================================================================
# RACK & STACK SUBMISSION
# =============================================================================

async def submit_efolder_to_rack_and_stack(
    loan_id: str,
    max_documents: Optional[int] = None,
    document_ids: Optional[List[str]] = None,
) -> RackAndStackSubmission:
    """
    Submit eFolder documents to TaskTile Rack & Stack pipeline.
    
    This function:
    1. Fetches document list from Encompass eFolder
    2. Downloads PDF content for each document
    3. Uploads PDFs to TaskTile
    4. Creates a Rack & Stack pipeline job
    
    Results are delivered via webhook when processing completes.
    
    Args:
        loan_id: Encompass loan GUID
        max_documents: Optional limit on number of documents to process
        document_ids: Optional specific attachment IDs to process (if None, process all)
        
    Returns:
        RackAndStackSubmission with job_id and status
        
    Example:
        submission = await submit_efolder_to_rack_and_stack(
            loan_id="59d7a711-70f4-4b12-a3b5-bbefb3ff7dbc",
            max_documents=10
        )
        print(f"Submitted job: {submission.job_id}")
    """
    logger.info(f"[R&S] Starting Rack & Stack submission for loan {loan_id[:8]}...")
    
    submission = RackAndStackSubmission(
        loan_id=loan_id,
        job_id="",
        pipeline=[],
        documents_submitted=0,
        submitted_at=datetime.utcnow().isoformat(),
    )
    
    try:
        # Step 1: Fetch eFolder documents
        documents = fetch_efolder_documents(loan_id)
        
        if not documents:
            submission.status = "error"
            submission.error = "No documents found in eFolder"
            return submission
        
        # Filter to specific documents if requested
        if document_ids:
            documents = [d for d in documents if d.attachment_id in document_ids]
            logger.info(f"[R&S] Filtered to {len(documents)} specific documents")
        
        # Apply limit if specified
        if max_documents and len(documents) > max_documents:
            logger.info(f"[R&S] Limiting to first {max_documents} documents")
            documents = documents[:max_documents]
        
        logger.info(f"[R&S] Processing {len(documents)} documents...")
        
        # Step 2: Initialize TaskTile client
        tasktile = TaskTileClient()
        
        # Step 3: Download and upload each document
        upload_ids = []
        
        for i, doc in enumerate(documents, 1):
            logger.info(f"[R&S] [{i}/{len(documents)}] Processing: {doc.title}")
            
            # Download from Encompass
            pdf_bytes = download_document_bytes(loan_id, doc.attachment_id)
            
            if not pdf_bytes:
                logger.warning(f"[R&S] Skipping {doc.title} - download failed")
                continue
            
            # Upload to TaskTile
            try:
                # Use a descriptive filename
                filename = f"{doc.attachment_id}_{doc.title[:50]}.pdf"
                filename = filename.replace("/", "_").replace("\\", "_")
                
                upload_result = tasktile.upload_pdf_bytes(pdf_bytes, filename)
                upload_ids.append(upload_result.upload_id)
                
                submission.upload_results.append({
                    "attachment_id": doc.attachment_id,
                    "title": doc.title,
                    "upload_id": upload_result.upload_id,
                    "page_count": upload_result.page_count,
                    "status": "uploaded",
                })
                
                logger.info(f"[R&S]   ✓ Uploaded: {upload_result.upload_id[:8]}... ({upload_result.page_count} pages)")
                
            except Exception as e:
                logger.error(f"[R&S]   ✗ Upload failed: {e}")
                submission.upload_results.append({
                    "attachment_id": doc.attachment_id,
                    "title": doc.title,
                    "status": "failed",
                    "error": str(e),
                })
        
        if not upload_ids:
            submission.status = "error"
            submission.error = "All document uploads failed"
            return submission
        
        # Step 4: Create Rack & Stack job
        logger.info(f"[R&S] Creating job with {len(upload_ids)} upload(s)...")
        
        job_result = tasktile.create_job(
            upload_ids=upload_ids,
            entity={
                "loan_id": loan_id,
                "source": "loan_officer_assistant",
                "submitted_at": submission.submitted_at,
            }
        )
        
        submission.job_id = job_result.job_id
        submission.pipeline = job_result.pipeline
        submission.documents_submitted = len(upload_ids)
        submission.status = "submitted"
        
        logger.info(f"[R&S] ✓ Job submitted: {job_result.job_id}")
        logger.info(f"[R&S]   Pipeline: {' → '.join(job_result.pipeline)}")
        logger.info(f"[R&S]   Documents: {len(upload_ids)}")
        
        return submission
        
    except Exception as e:
        logger.error(f"[R&S] ✗ Submission failed: {e}")
        submission.status = "error"
        submission.error = str(e)
        return submission


def submit_efolder_to_rack_and_stack_sync(
    loan_id: str,
    max_documents: Optional[int] = None,
    document_ids: Optional[List[str]] = None,
) -> RackAndStackSubmission:
    """
    Synchronous wrapper for submit_efolder_to_rack_and_stack.
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
    except RuntimeError:
        pass
    
    return asyncio.run(submit_efolder_to_rack_and_stack(
        loan_id, max_documents, document_ids
    ))


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import json
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    
    # Default to test loan
    loan_id = sys.argv[1] if len(sys.argv) > 1 else "59d7a711-70f4-4b12-a3b5-bbefb3ff7dbc"
    max_docs = int(sys.argv[2]) if len(sys.argv) > 2 else 5  # Default to 5 docs for testing
    
    print("=" * 70)
    print("RACK & STACK SUBMISSION")
    print("=" * 70)
    print(f"Loan ID: {loan_id}")
    print(f"Max Documents: {max_docs}")
    print("=" * 70)
    
    result = submit_efolder_to_rack_and_stack_sync(loan_id, max_documents=max_docs)
    
    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)
    print(f"Status: {result.status}")
    print(f"Job ID: {result.job_id}")
    print(f"Documents Submitted: {result.documents_submitted}")
    print(f"Pipeline: {' → '.join(result.pipeline)}")
    
    if result.error:
        print(f"Error: {result.error}")
    
    # Save result
    output_file = f"rack_and_stack_submission_{loan_id[:8]}.json"
    with open(output_file, "w") as f:
        json.dump({
            "loan_id": result.loan_id,
            "job_id": result.job_id,
            "pipeline": result.pipeline,
            "documents_submitted": result.documents_submitted,
            "upload_results": result.upload_results,
            "submitted_at": result.submitted_at,
            "status": result.status,
            "error": result.error,
        }, f, indent=2)
    
    print(f"\nResult saved to: {output_file}")

