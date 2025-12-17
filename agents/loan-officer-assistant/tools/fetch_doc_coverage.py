"""
Loan Officer Assistant - Document Coverage Fetcher

Fetches and parses Rack & Stack manifest to determine document coverage.
Integrates with TaskTile API for document classification.

Usage:
    coverage = await fetch_doc_coverage(loan_id, efolder_docs)
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Add paths for imports
LOA_DIR = Path(__file__).parent.parent
PROJECT_ROOT = LOA_DIR.parent.parent
sys.path.insert(0, str(LOA_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

from state import DocCoverage, DocCoverageItem, EFolderDoc

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

CONFIG_DIR = LOA_DIR / "config"
DOC_TYPE_MAPPING_PATH = CONFIG_DIR / "doc_type_mapping.yaml"
MANIFEST_DIR = PROJECT_ROOT / "backend" / "output" / "tasktile_manifests"


def load_doc_type_mapping() -> Dict[str, Any]:
    """Load document type mapping configuration."""
    if not DOC_TYPE_MAPPING_PATH.exists():
        logger.warning(f"Doc type mapping not found at {DOC_TYPE_MAPPING_PATH}")
        return {"mappings": [], "default": {"doc_type": "OTHER"}}
    
    with open(DOC_TYPE_MAPPING_PATH, "r") as f:
        return yaml.safe_load(f)


# =============================================================================
# CATEGORY → DOC TYPE MAPPING
# =============================================================================

_mapping_cache: Optional[Dict[str, Any]] = None


def get_mapping_config() -> Dict[str, Any]:
    """Get cached mapping config."""
    global _mapping_cache
    if _mapping_cache is None:
        _mapping_cache = load_doc_type_mapping()
    return _mapping_cache


def map_category_to_doc_type(category_name: str) -> str:
    """
    Map R&S category name to normalized doc type.
    
    Args:
        category_name: Category name from R&S manifest
        
    Returns:
        Normalized doc type (e.g., "W2", "PAYSTUB", "BANK_STATEMENT")
    """
    config = get_mapping_config()
    mappings = config.get("mappings", [])
    default = config.get("default", {"doc_type": "OTHER"})
    
    category_lower = category_name.lower() if category_name else ""
    
    for mapping in mappings:
        patterns = mapping.get("category_patterns", [])
        for pattern in patterns:
            if pattern.lower() == category_lower or pattern.lower() in category_lower:
                return mapping.get("doc_type", "OTHER")
    
    return default.get("doc_type", "OTHER")


def is_critical_doc_type(doc_type: str) -> bool:
    """Check if a doc type is considered critical."""
    config = get_mapping_config()
    critical_types = config.get("critical_doc_types", [])
    return doc_type in critical_types


def map_questionnaire_doc_name(doc_name: str) -> str:
    """
    Map questionnaire document name to normalized doc type.
    
    Args:
        doc_name: Document name from questionnaire required_documents
        
    Returns:
        Normalized doc type
    """
    config = get_mapping_config()
    questionnaire_map = config.get("questionnaire_doc_map", {})
    return questionnaire_map.get(doc_name, "OTHER")


# =============================================================================
# MANIFEST PARSING
# =============================================================================

def parse_manifest(manifest: Dict[str, Any], loan_id: str) -> DocCoverage:
    """
    Parse TaskTile webhook manifest into DocCoverage.
    
    Args:
        manifest: Raw manifest JSON from webhook
        loan_id: Loan ID for context
        
    Returns:
        DocCoverage with parsed document data
    """
    logger.info(f"[DOC_COVERAGE] Parsing manifest for loan {loan_id[:8]}...")
    
    coverage = DocCoverage(loan_id=loan_id)
    
    # Job metadata
    job = manifest.get("job", {})
    coverage.job_id = job.get("id")
    coverage.job_status = job.get("status")
    coverage.job_created_at = job.get("created_at")
    coverage.job_completed_at = job.get("completed_at")
    coverage.manifest_version = manifest.get("version")
    
    # Counts
    counts = manifest.get("counts", {})
    coverage.total_blobs = counts.get("blobs", 0)
    
    # Parse documents
    for doc in manifest.get("documents", []):
        category = doc.get("category", {})
        metadata = doc.get("metadata", {})
        source = doc.get("source", {})
        exceptions = metadata.get("exceptions", {})
        
        # Get first borrower if present
        borrowers = metadata.get("borrowers", [])
        borrower = borrowers[0] if borrowers else {}
        
        # Map category to normalized doc type
        category_name = category.get("category_name", "")
        doc_type = map_category_to_doc_type(category_name)
        
        # Check for exceptions
        has_exceptions = any(exceptions.values()) if exceptions else False
        
        item = DocCoverageItem(
            doc_id=doc.get("id", ""),
            blob_id=doc.get("blob_id", ""),
            doc_type=doc_type,
            category_id=category.get("category_id"),
            category_name=category_name,
            category_source=category.get("source"),
            page_count=metadata.get("total_pages"),
            confidence=metadata.get("confidence"),
            borrower_first_name=borrower.get("firstName"),
            borrower_last_name=borrower.get("lastName"),
            source_bucket=source.get("bucket"),
            source_key=source.get("key"),
            has_exceptions=has_exceptions,
            exceptions=exceptions,
        )
        
        coverage.documents.append(item)
        
        # Track by type
        if doc_type not in coverage.coverage_by_type:
            coverage.coverage_by_type[doc_type] = []
        coverage.coverage_by_type[doc_type].append(item.doc_id)
        
        # Track issues
        if has_exceptions:
            coverage.documents_with_exceptions += 1
        if item.confidence and item.confidence < 0.8:
            coverage.low_confidence_count += 1
    
    # Compute flags
    coverage.compute_coverage_flags()
    
    logger.info(f"[DOC_COVERAGE] ✓ Parsed {coverage.total_documents} documents")
    logger.info(f"[DOC_COVERAGE]   Types found: {list(coverage.coverage_by_type.keys())}")
    
    return coverage


# =============================================================================
# MANIFEST LOOKUP
# =============================================================================

def find_cached_manifest(loan_id: str) -> Optional[Dict[str, Any]]:
    """
    Find a cached manifest for the given loan.
    
    Looks in the manifest directory for files matching the loan_id
    in the entity metadata or job entity.
    
    Args:
        loan_id: Loan ID to search for
        
    Returns:
        Manifest dict if found, None otherwise
    """
    if not MANIFEST_DIR.exists():
        logger.debug(f"[DOC_COVERAGE] Manifest directory not found: {MANIFEST_DIR}")
        return None
    
    # Get all manifest files, sorted by modification time (newest first)
    manifest_files = sorted(
        MANIFEST_DIR.glob("manifest_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    logger.debug(f"[DOC_COVERAGE] Searching {len(manifest_files)} cached manifests...")
    
    for manifest_file in manifest_files:
        try:
            with open(manifest_file) as f:
                manifest = json.load(f)
            
            # Check if this manifest is for our loan
            entity = manifest.get("entity", {})
            if entity.get("loan_id") == loan_id:
                logger.info(f"[DOC_COVERAGE] ✓ Found cached manifest: {manifest_file.name}")
                return manifest
            
            # Also check input[] for loan_id in metadata
            inputs = manifest.get("input", [])
            for inp in inputs:
                if inp.get("metadata", {}).get("loan_id") == loan_id:
                    logger.info(f"[DOC_COVERAGE] ✓ Found cached manifest: {manifest_file.name}")
                    return manifest
                    
        except Exception as e:
            logger.warning(f"[DOC_COVERAGE] Error reading manifest {manifest_file.name}: {e}")
    
    return None


def find_latest_manifest() -> Optional[Dict[str, Any]]:
    """Find the most recent manifest regardless of loan_id."""
    if not MANIFEST_DIR.exists():
        return None
    
    manifest_files = sorted(
        MANIFEST_DIR.glob("manifest_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    if manifest_files:
        with open(manifest_files[0]) as f:
            return json.load(f)
    
    return None


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def fetch_doc_coverage(
    loan_id: str,
    efolder_docs: Optional[List[EFolderDoc]] = None,
    refresh: bool = False,
) -> Optional[DocCoverage]:
    """
    Fetch document coverage for a loan.
    
    This function:
    1. Looks for a cached R&S manifest for the loan
    2. If refresh=True or no manifest, triggers a new R&S job
    3. Parses the manifest into DocCoverage
    
    Args:
        loan_id: Encompass loan GUID
        efolder_docs: List of eFolder documents (for R&S submission if needed)
        refresh: Force new R&S job even if cached manifest exists
        
    Returns:
        DocCoverage if manifest found/created, None otherwise
    """
    logger.info(f"[DOC_COVERAGE] Fetching doc coverage for loan {loan_id[:8]}...")
    logger.info(f"[DOC_COVERAGE]   refresh={refresh}")
    
    # Check for cached manifest
    manifest = None
    if not refresh:
        manifest = find_cached_manifest(loan_id)
    
    # If no manifest and refresh requested, trigger R&S job
    if manifest is None and refresh:
        logger.info("[DOC_COVERAGE] No cached manifest, triggering R&S job...")
        
        if efolder_docs:
            try:
                from tools.rack_and_stack import submit_efolder_to_rack_and_stack
                
                submission = await submit_efolder_to_rack_and_stack(
                    loan_id=loan_id,
                    max_documents=50,  # Limit for reasonable processing time
                )
                
                logger.info(f"[DOC_COVERAGE] R&S job submitted: {submission.job_id}")
                logger.warning("[DOC_COVERAGE] Job submitted - manifest will arrive via webhook")
                
                # Return pending status
                coverage = DocCoverage(
                    loan_id=loan_id,
                    job_id=submission.job_id,
                    job_status="pending",
                )
                return coverage
                
            except Exception as e:
                logger.error(f"[DOC_COVERAGE] R&S submission failed: {e}")
                return None
        else:
            logger.warning("[DOC_COVERAGE] No eFolder docs provided for R&S submission")
            return None
    
    # If still no manifest, return None
    if manifest is None:
        logger.warning("[DOC_COVERAGE] No manifest available")
        return None
    
    # Parse manifest
    coverage = parse_manifest(manifest, loan_id)
    
    return coverage


# =============================================================================
# SYNCHRONOUS WRAPPER
# =============================================================================

def fetch_doc_coverage_sync(
    loan_id: str,
    efolder_docs: Optional[List[EFolderDoc]] = None,
    refresh: bool = False,
) -> Optional[DocCoverage]:
    """Synchronous wrapper for fetch_doc_coverage."""
    import asyncio
    return asyncio.run(fetch_doc_coverage(loan_id, efolder_docs, refresh))


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python fetch_doc_coverage.py <loan_id> [--refresh]")
        print("\nChecking for any cached manifests...")
        
        manifest = find_latest_manifest()
        if manifest:
            job = manifest.get("job", {})
            print(f"\nLatest manifest found:")
            print(f"  Job ID: {job.get('id', 'N/A')[:8]}...")
            print(f"  Status: {job.get('status', 'N/A')}")
            print(f"  Documents: {manifest.get('counts', {}).get('documents', 0)}")
        else:
            print("No manifests found.")
        sys.exit(0)
    
    loan_id = sys.argv[1]
    refresh = "--refresh" in sys.argv
    
    coverage = fetch_doc_coverage_sync(loan_id, refresh=refresh)
    
    if coverage:
        print("\n" + "=" * 60)
        print("DOCUMENT COVERAGE")
        print("=" * 60)
        print(f"Loan ID: {coverage.loan_id}")
        print(f"Job ID: {coverage.job_id}")
        print(f"Status: {coverage.job_status}")
        print(f"Total Documents: {coverage.total_documents}")
        print(f"\nCoverage by Type:")
        for doc_type, doc_ids in coverage.coverage_by_type.items():
            print(f"  {doc_type}: {len(doc_ids)}")
        print(f"\nFlags:")
        print(f"  has_w2: {coverage.has_w2}")
        print(f"  has_paystubs: {coverage.has_paystubs}")
        print(f"  has_tax_returns: {coverage.has_tax_returns}")
        print(f"  has_bank_statements: {coverage.has_bank_statements}")
        print(f"  has_purchase_contract: {coverage.has_purchase_contract}")
        print(f"  has_government_id: {coverage.has_government_id}")
    else:
        print("No document coverage available.")

