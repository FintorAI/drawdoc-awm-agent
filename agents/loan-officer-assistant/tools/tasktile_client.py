"""TaskTile API Client for Rack & Stack Pipeline.

This module provides a client for interacting with the TaskTile API
to run the Rack & Stack document processing pipeline.

Usage:
    from tools.tasktile_client import TaskTileClient
    
    client = TaskTileClient()
    
    # Upload PDFs and create a job
    result = client.submit_rack_and_stack_job(
        pdf_files=[("/path/to/file.pdf", "doc.pdf")],
        entity={"loan_id": "123"}
    )
"""

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

# Load .env from project root
LOA_DIR = Path(__file__).parent.parent
PROJECT_ROOT = LOA_DIR.parent.parent
env_path = PROJECT_ROOT / ".env"
load_dotenv(env_path)

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TokenInfo:
    """TaskTile OAuth2 token information."""
    access_token: str
    expires_at: float
    token_type: str = "Bearer"


@dataclass
class UploadResult:
    """Result of a file upload to TaskTile."""
    upload_id: str
    bucket: str
    key: str
    filename: str
    page_count: Optional[int] = None


@dataclass
class JobResult:
    """Result of creating a Rack & Stack job."""
    job_id: str
    pipeline: List[str] = field(default_factory=list)
    blobs: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "pending"


# =============================================================================
# TASKTILE CLIENT
# =============================================================================

class TaskTileClient:
    """Client for TaskTile Rack & Stack API.
    
    This client handles:
    - OAuth2 token management (client credentials flow)
    - File uploads via presigned URLs
    - Job creation and tracking
    
    Attributes:
        api_base_url: Base URL for TaskTile API
        timeout: Request timeout in seconds
    """
    
    def __init__(
        self,
        api_base_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        timeout: int = 60,
    ):
        """Initialize TaskTile client.
        
        Args:
            api_base_url: TaskTile API base URL (defaults to env var)
            client_id: TaskTile client ID (defaults to env var)
            client_secret: TaskTile client secret (defaults to env var)
            timeout: Request timeout in seconds
        """
        self.api_base_url = (
            api_base_url or 
            os.getenv("TASKTILE_API_BASE_URL", "https://tasktile.staging.cybersoftbpo.ai/api")
        ).rstrip("/")
        
        self._client_id = client_id or os.getenv("TASKTILE_CLIENT_ID")
        self._client_secret = client_secret or os.getenv("TASKTILE_CLIENT_SECRET")
        self._categories_url = os.getenv(
            "TASKTILE_CATEGORIES_URL",
            "https://sbiqai.staging.cybersoftbpo.ai/api/workspaces/1/categories"
        )
        
        self.timeout = timeout
        self._token: Optional[TokenInfo] = None
    
    # =========================================================================
    # AUTHENTICATION
    # =========================================================================
    
    def _is_token_valid(self) -> bool:
        """Check if current token is valid (not expired)."""
        if self._token is None:
            return False
        # Add 30 second buffer before expiration
        return time.time() < (self._token.expires_at - 30)
    
    def _get_access_token(self, force_refresh: bool = False) -> str:
        """Get a valid access token, refreshing if necessary.
        
        Args:
            force_refresh: Force token refresh even if current token is valid
            
        Returns:
            Valid access token string
            
        Raises:
            RuntimeError: If credentials are missing
            requests.HTTPError: If token request fails
        """
        if not force_refresh and self._is_token_valid():
            return self._token.access_token
        
        if not self._client_id or not self._client_secret:
            raise RuntimeError(
                "Missing TASKTILE_CLIENT_ID or TASKTILE_CLIENT_SECRET. "
                "Please register as a client at POST /clients and set these in your .env file."
            )
        
        logger.info("[TASKTILE] Requesting access token...")
        
        url = f"{self.api_base_url}/auth/token"
        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        
        resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        
        data = resp.json()
        expires_in = data.get("expires_in", 3600)
        
        self._token = TokenInfo(
            access_token=data["access_token"],
            expires_at=time.time() + expires_in,
            token_type=data.get("token_type", "Bearer"),
        )
        
        logger.info(f"[TASKTILE] ✓ Token obtained, expires in {expires_in}s")
        return self._token.access_token
    
    def _auth_headers(self) -> Dict[str, str]:
        """Get authorization headers for API requests."""
        token = self._get_access_token()
        return {"Authorization": f"Bearer {token}"}
    
    # =========================================================================
    # FILE UPLOAD
    # =========================================================================
    
    def initiate_upload(
        self,
        filename: str,
        file_size: int,
        content_type: str = "application/pdf",
    ) -> Dict[str, Any]:
        """Initiate a file upload and get presigned URL.
        
        Args:
            filename: Original filename
            file_size: File size in bytes
            content_type: MIME type (must be application/pdf)
            
        Returns:
            Dict with upload_id, put_url, bucket, key, expires_in
            
        Raises:
            requests.HTTPError: If initiation fails
        """
        logger.info(f"[TASKTILE] Initiating upload for {filename} ({file_size} bytes)")
        
        url = f"{self.api_base_url}/uploads/initiate"
        payload = {
            "filename": filename,
            "content_type": content_type,
            "size": file_size,
        }
        
        resp = requests.post(
            url,
            json=payload,
            headers=self._auth_headers(),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        
        result = resp.json()
        logger.info(f"[TASKTILE] ✓ Upload initiated: {result.get('upload_id', '')[:8]}...")
        
        return result
    
    def upload_file_to_presigned_url(
        self,
        put_url: str,
        file_path: str,
        content_type: str = "application/pdf",
    ) -> bool:
        """Upload file directly to presigned S3 URL.
        
        Args:
            put_url: Presigned PUT URL from initiate_upload
            file_path: Local path to file
            content_type: MIME type
            
        Returns:
            True if upload successful
            
        Raises:
            requests.HTTPError: If upload fails
        """
        logger.info(f"[TASKTILE] Uploading file to presigned URL...")
        
        file_path = Path(file_path)
        file_size = file_path.stat().st_size
        
        with open(file_path, "rb") as f:
            resp = requests.put(
                put_url,
                data=f,
                headers={
                    "Content-Type": content_type,
                    "Content-Length": str(file_size),
                },
                timeout=300,  # Allow 5 minutes for large files
            )
        
        resp.raise_for_status()
        logger.info("[TASKTILE] ✓ File uploaded to storage")
        return True
    
    def upload_file_bytes_to_presigned_url(
        self,
        put_url: str,
        file_bytes: bytes,
        content_type: str = "application/pdf",
    ) -> bool:
        """Upload file bytes directly to presigned S3 URL.
        
        Args:
            put_url: Presigned PUT URL from initiate_upload
            file_bytes: File content as bytes
            content_type: MIME type
            
        Returns:
            True if upload successful
            
        Raises:
            requests.HTTPError: If upload fails
        """
        logger.info(f"[TASKTILE] Uploading {len(file_bytes)} bytes to presigned URL...")
        
        resp = requests.put(
            put_url,
            data=file_bytes,
            headers={
                "Content-Type": content_type,
                "Content-Length": str(len(file_bytes)),
            },
            timeout=300,
        )
        
        resp.raise_for_status()
        logger.info("[TASKTILE] ✓ File uploaded to storage")
        return True
    
    def complete_upload(self, upload_id: str) -> Dict[str, Any]:
        """Confirm upload completion with TaskTile.
        
        Args:
            upload_id: The upload ID from initiate_upload
            
        Returns:
            Dict with upload confirmation including page_count
            
        Raises:
            requests.HTTPError: If completion fails
        """
        logger.info(f"[TASKTILE] Completing upload {upload_id[:8]}...")
        
        url = f"{self.api_base_url}/uploads/complete"
        payload = {"upload_id": upload_id}
        
        resp = requests.post(
            url,
            json=payload,
            headers=self._auth_headers(),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        
        result = resp.json()
        page_count = result.get("page_count", "unknown")
        logger.info(f"[TASKTILE] ✓ Upload completed: {page_count} pages")
        
        return result
    
    def upload_pdf(
        self,
        file_path: str,
        filename: Optional[str] = None,
    ) -> UploadResult:
        """Upload a PDF file to TaskTile (full workflow).
        
        This method handles the complete upload flow:
        1. Initiate upload → get presigned URL
        2. Upload file to presigned URL
        3. Complete upload notification
        
        Args:
            file_path: Local path to PDF file
            filename: Override filename (defaults to basename of file_path)
            
        Returns:
            UploadResult with upload_id and metadata
            
        Raises:
            requests.HTTPError: If any step fails
            FileNotFoundError: If file doesn't exist
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        filename = filename or file_path.name
        file_size = file_path.stat().st_size
        
        # Step 1: Initiate
        init_result = self.initiate_upload(filename, file_size)
        upload_id = init_result["upload_id"]
        put_url = init_result["put_url"]
        
        # Step 2: Upload to presigned URL
        self.upload_file_to_presigned_url(put_url, str(file_path))
        
        # Step 3: Complete
        complete_result = self.complete_upload(upload_id)
        
        return UploadResult(
            upload_id=upload_id,
            bucket=init_result.get("bucket", ""),
            key=init_result.get("key", ""),
            filename=filename,
            page_count=complete_result.get("page_count"),
        )
    
    def upload_pdf_bytes(
        self,
        file_bytes: bytes,
        filename: str,
    ) -> UploadResult:
        """Upload PDF bytes to TaskTile (full workflow).
        
        Same as upload_pdf but accepts bytes instead of file path.
        Useful when working with in-memory PDFs from Encompass eFolder.
        
        Args:
            file_bytes: PDF content as bytes
            filename: Filename for the upload
            
        Returns:
            UploadResult with upload_id and metadata
        """
        file_size = len(file_bytes)
        
        # Step 1: Initiate
        init_result = self.initiate_upload(filename, file_size)
        upload_id = init_result["upload_id"]
        put_url = init_result["put_url"]
        
        # Step 2: Upload to presigned URL
        self.upload_file_bytes_to_presigned_url(put_url, file_bytes)
        
        # Step 3: Complete
        complete_result = self.complete_upload(upload_id)
        
        return UploadResult(
            upload_id=upload_id,
            bucket=init_result.get("bucket", ""),
            key=init_result.get("key", ""),
            filename=filename,
            page_count=complete_result.get("page_count"),
        )
    
    # =========================================================================
    # JOB MANAGEMENT
    # =========================================================================
    
    def create_job(
        self,
        upload_ids: List[str],
        entity: Optional[Dict[str, Any]] = None,
        categories_url: Optional[str] = None,
        pipeline_name: str = "rack_and_stack_v1",
        max_retries: int = 6,
    ) -> JobResult:
        """Create a Rack & Stack pipeline job.
        
        Args:
            upload_ids: List of completed upload IDs
            entity: Optional metadata about the entity/loan
            categories_url: URL for category schema (defaults to env var)
            pipeline_name: Pipeline to run (default: rack_and_stack_v1)
            max_retries: Max retries if uploads are still pending (default: 6 = ~60s wait)
            
        Returns:
            JobResult with job_id and pipeline info
            
        Raises:
            ValueError: If upload_ids is empty
            requests.HTTPError: If job creation fails after retries
        """
        if not upload_ids:
            raise ValueError("upload_ids cannot be empty")
        
        logger.info(f"[TASKTILE] Creating {pipeline_name} job with {len(upload_ids)} upload(s)...")
        
        url = f"{self.api_base_url}/jobs"
        payload = {
            "pipeline_name": pipeline_name,
            "upload_ids": upload_ids,
            "categories_url": categories_url or self._categories_url,
        }
        
        if entity:
            payload["entity"] = entity
        
        # Retry loop for pending uploads (virus scan in progress)
        last_error = None
        for attempt in range(max_retries + 1):
            resp = requests.post(
                url,
                json=payload,
                headers=self._auth_headers(),
                timeout=self.timeout,
            )
            
            # Success - job created
            if resp.status_code == 201:
                break
            
            # Check if we should retry (uploads still pending)
            if resp.status_code == 400:
                try:
                    error_data = resp.json()
                    retry_after = error_data.get("retry_after_seconds")
                    
                    # Only retry if it's a "pending scan" error
                    if retry_after and attempt < max_retries:
                        pending_count = len(error_data.get("uploads", []))
                        logger.warning(
                            f"[TASKTILE] {pending_count} upload(s) still pending scan, "
                            f"retrying in {retry_after}s (attempt {attempt + 1}/{max_retries})..."
                        )
                        time.sleep(retry_after)
                        continue
                    else:
                        # Different error (not pending) or max retries - don't retry
                        logger.error(f"[TASKTILE] Job creation failed: {resp.status_code}")
                        logger.error(f"[TASKTILE] Error response: {error_data}")
                        last_error = error_data.get("error", "Unknown error")
                        break  # Exit retry loop
                except Exception as e:
                    logger.error(f"[TASKTILE] Error response (raw): {resp.text}")
                    break
            else:
                # Non-400 error, log and fail immediately
                try:
                    error_data = resp.json()
                    logger.error(f"[TASKTILE] Job creation failed: {resp.status_code}")
                    logger.error(f"[TASKTILE] Error response: {error_data}")
                except:
                    logger.error(f"[TASKTILE] Error response (raw): {resp.text}")
                break  # Exit retry loop
        
        resp.raise_for_status()
        
        result = resp.json()
        job_id = result.get("job_id", "")
        pipeline = result.get("pipeline", [])
        
        logger.info(f"[TASKTILE] ✓ Job created: {job_id[:8]}...")
        logger.info(f"[TASKTILE]   Pipeline: {' → '.join(pipeline)}")
        
        return JobResult(
            job_id=job_id,
            pipeline=pipeline,
            blobs=result.get("blobs", []),
            status="pending",
        )
    
    # =========================================================================
    # DOCUMENT DOWNLOAD
    # =========================================================================
    
    def get_presigned_download_urls(
        self,
        files: List[Dict[str, str]],
        expires_seconds: int = 1800,
    ) -> List[Dict[str, Any]]:
        """Get presigned URLs to download processed documents.
        
        Args:
            files: List of dicts with 'bucket' and 'key'
            expires_seconds: URL validity in seconds
            
        Returns:
            List of dicts with 'url' and 'expires_at'
            
        Raises:
            requests.HTTPError: If request fails
        """
        logger.info(f"[TASKTILE] Getting download URLs for {len(files)} file(s)...")
        
        url = f"{self.api_base_url}/files/presign-get/batch"
        payload = {
            "files": [
                {
                    "bucket": f["bucket"],
                    "key": f["key"],
                    "expires_seconds": expires_seconds,
                }
                for f in files
            ]
        }
        
        resp = requests.post(
            url,
            json=payload,
            headers=self._auth_headers(),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        
        result = resp.json()
        logger.info(f"[TASKTILE] ✓ Got {len(result)} download URL(s)")
        
        return result
    
    # =========================================================================
    # HIGH-LEVEL WORKFLOW
    # =========================================================================
    
    def submit_rack_and_stack_job(
        self,
        pdf_files: List[Tuple[str, Optional[str]]],
        entity: Optional[Dict[str, Any]] = None,
    ) -> JobResult:
        """Submit a complete Rack & Stack job.
        
        This is the high-level method that handles the full workflow:
        1. Upload all PDF files
        2. Create the pipeline job
        
        Args:
            pdf_files: List of (file_path, optional_filename) tuples
            entity: Optional metadata about the entity/loan
            
        Returns:
            JobResult with job_id
            
        Example:
            result = client.submit_rack_and_stack_job(
                pdf_files=[
                    ("/path/to/doc1.pdf", "LoanApplication.pdf"),
                    ("/path/to/doc2.pdf", None),  # Uses original filename
                ],
                entity={"loan_id": "abc-123"}
            )
            print(f"Job ID: {result.job_id}")
        """
        logger.info(f"[TASKTILE] Starting Rack & Stack submission with {len(pdf_files)} file(s)...")
        
        # Upload all files
        upload_ids = []
        for file_path, filename in pdf_files:
            result = self.upload_pdf(file_path, filename)
            upload_ids.append(result.upload_id)
        
        # Create job
        job_result = self.create_job(upload_ids, entity)
        
        logger.info(f"[TASKTILE] ✓ Rack & Stack job submitted: {job_result.job_id}")
        return job_result


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_client: Optional[TaskTileClient] = None


def get_tasktile_client(force_new: bool = False) -> TaskTileClient:
    """Get singleton TaskTile client instance.
    
    Args:
        force_new: Create new client instance
        
    Returns:
        TaskTileClient instance
    """
    global _client
    if _client is None or force_new:
        _client = TaskTileClient()
    return _client


def submit_rack_and_stack(
    pdf_files: List[Tuple[str, Optional[str]]],
    entity: Optional[Dict[str, Any]] = None,
) -> JobResult:
    """Submit a Rack & Stack job (convenience function).
    
    Args:
        pdf_files: List of (file_path, optional_filename) tuples
        entity: Optional metadata
        
    Returns:
        JobResult with job_id
    """
    return get_tasktile_client().submit_rack_and_stack_job(pdf_files, entity)

