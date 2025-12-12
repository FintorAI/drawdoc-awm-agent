"""
TaskTile Webhook Handler

Receives job manifests from TaskTile when Rack & Stack pipeline completes.
Stores manifests for processing and can trigger downstream workflows.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Directory to store received manifests
MANIFEST_DIR = Path(__file__).parent.parent / "output" / "tasktile_manifests"
MANIFEST_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# MODELS
# =============================================================================

class TaskTileDocument(BaseModel):
    """Document from TaskTile manifest."""
    id: str
    blob_id: str
    source: Dict[str, str]
    category: Dict[str, Any]
    metadata: Dict[str, Any]


class TaskTileManifest(BaseModel):
    """TaskTile job completion manifest."""
    version: str
    job: Dict[str, Any]
    tenant: Dict[str, str]
    counts: Dict[str, int]
    input: list
    documents: list


# =============================================================================
# WEBHOOK ENDPOINTS
# =============================================================================

@router.post("/tasktile")
async def receive_tasktile_webhook(request: Request):
    """
    Receive TaskTile Rack & Stack job completion webhook.
    
    This endpoint receives the job manifest when a Rack & Stack pipeline
    completes (success or failure). The manifest contains:
    - Job status and metadata
    - List of processed documents with categories
    - Document storage locations (bucket/key)
    
    The manifest is saved to disk and can trigger downstream processing.
    
    Returns:
        Acknowledgment with job_id
    """
    try:
        # Parse the raw JSON body
        body = await request.json()
        
        # Extract key info for logging
        job_info = body.get("job", {})
        job_id = job_info.get("id", "unknown")
        job_status = job_info.get("status", "unknown")
        counts = body.get("counts", {})
        documents = body.get("documents", [])
        
        logger.info(f"[WEBHOOK] Received TaskTile manifest for job {job_id[:8]}...")
        logger.info(f"[WEBHOOK]   Status: {job_status}")
        logger.info(f"[WEBHOOK]   Blobs: {counts.get('blobs', 0)}, Documents: {counts.get('documents', 0)}")
        
        # Save manifest to file
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        manifest_file = MANIFEST_DIR / f"manifest_{job_id[:8]}_{timestamp}.json"
        
        with open(manifest_file, "w") as f:
            json.dump(body, f, indent=2)
        
        logger.info(f"[WEBHOOK] ✓ Manifest saved to: {manifest_file.name}")
        
        # Log document categories for debugging
        if documents:
            logger.info(f"[WEBHOOK] Documents received:")
            for doc in documents:
                category = doc.get("category", {})
                cat_name = category.get("category_name", "Unknown")
                doc_id = doc.get("id", "")[:8]
                logger.info(f"[WEBHOOK]   - {doc_id}: {cat_name}")
        
        # Run document coverage analysis
        coverage_summary = None
        try:
            import sys
            from pathlib import Path
            # Add LOA tools to path
            loa_path = Path(__file__).parent.parent.parent / "agents/loan-officer-assistant"
            sys.path.insert(0, str(loa_path))
            
            from tools.doc_coverage import analyze_document_coverage
            coverage = analyze_document_coverage(body)
            coverage_summary = {
                "documents_count": coverage.documents_count,
                "categories_found": list(coverage.categories_found),
                "coverage_score": coverage.coverage_score,
                "exceptions_count": len(coverage.documents_with_exceptions),
            }
            logger.info(f"[WEBHOOK] ✓ Coverage analysis: {coverage.coverage_score:.1%}")
        except Exception as e:
            logger.warning(f"[WEBHOOK] Coverage analysis failed: {e}")
        
        return {
            "status": "received",
            "job_id": job_id,
            "documents_count": len(documents),
            "manifest_file": manifest_file.name,
            "coverage": coverage_summary,
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"[WEBHOOK] Invalid JSON in request body: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    except Exception as e:
        logger.error(f"[WEBHOOK] Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasktile/manifests")
async def list_manifests():
    """
    List all received TaskTile manifests.
    
    Returns:
        List of manifest files with metadata
    """
    manifests = []
    
    for manifest_file in sorted(MANIFEST_DIR.glob("manifest_*.json"), reverse=True):
        try:
            with open(manifest_file) as f:
                data = json.load(f)
            
            job = data.get("job", {})
            counts = data.get("counts", {})
            
            manifests.append({
                "filename": manifest_file.name,
                "job_id": job.get("id", ""),
                "status": job.get("status", ""),
                "documents": counts.get("documents", 0),
                "created_at": job.get("created_at", ""),
            })
        except Exception as e:
            logger.warning(f"Error reading manifest {manifest_file.name}: {e}")
    
    return {"manifests": manifests}


@router.get("/tasktile/manifests/{job_id}")
async def get_manifest(job_id: str):
    """
    Get a specific TaskTile manifest by job ID.
    
    Args:
        job_id: Full or partial (8 char) job ID
        
    Returns:
        Full manifest data
    """
    # Search for manifest file by job_id prefix
    for manifest_file in MANIFEST_DIR.glob(f"manifest_{job_id[:8]}*.json"):
        try:
            with open(manifest_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading manifest: {e}")
            raise HTTPException(status_code=500, detail="Error reading manifest")
    
    raise HTTPException(status_code=404, detail=f"Manifest not found for job {job_id}")


@router.get("/tasktile/manifests/{job_id}/coverage")
async def analyze_manifest_coverage(job_id: str):
    """
    Analyze document coverage for a specific manifest.
    
    Args:
        job_id: Full or partial (8 char) job ID
        
    Returns:
        Document coverage analysis
    """
    import sys
    from pathlib import Path
    
    # Find manifest
    manifest_data = None
    for manifest_file in MANIFEST_DIR.glob(f"manifest_{job_id[:8]}*.json"):
        try:
            with open(manifest_file) as f:
                manifest_data = json.load(f)
            break
        except Exception as e:
            logger.error(f"Error reading manifest: {e}")
            raise HTTPException(status_code=500, detail="Error reading manifest")
    
    if not manifest_data:
        raise HTTPException(status_code=404, detail=f"Manifest not found for job {job_id}")
    
    # Run coverage analysis
    try:
        loa_path = Path(__file__).parent.parent.parent / "agents/loan-officer-assistant"
        sys.path.insert(0, str(loa_path))
        
        from tools.doc_coverage import analyze_document_coverage, format_coverage_summary
        coverage = analyze_document_coverage(manifest_data)
        
        return {
            "job_id": coverage.job_id,
            "job_status": coverage.job_status,
            "loan_id": coverage.loan_id,
            "documents_count": coverage.documents_count,
            "categories_found": list(coverage.categories_found),
            "coverage_score": coverage.coverage_score,
            "missing_by_type": coverage.missing_by_type,
            "exceptions_count": len(coverage.documents_with_exceptions),
            "low_confidence_count": len(coverage.low_confidence_documents),
            "summary": format_coverage_summary(coverage),
        }
    except Exception as e:
        logger.error(f"Coverage analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

