"""
Document Coverage Analyzer for Loan Officer Assistant.

This module analyzes Rack & Stack manifest results to determine
document coverage for a loan. It parses webhook manifests and
identifies which document categories are present/missing.

Usage:
    from tools.doc_coverage import analyze_document_coverage
    
    coverage = analyze_document_coverage(manifest_data)
    print(f"Found {coverage.documents_count} documents")
    print(f"Categories: {coverage.categories_found}")
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# =============================================================================
# REQUIRED DOCUMENT CATEGORIES
# =============================================================================
# These are the standard document categories required for loan processing.
# Organized by category type. Expand as needed based on your loan requirements.

REQUIRED_CATEGORIES = {
    # Income & Employment
    "income": [
        "W-2",
        "Pay Stub",
        "Tax Return",
        "1099",
        "VOE",  # Verification of Employment
        "Employment Letter",
    ],
    # Assets
    "assets": [
        "Bank Statement",
        "Investment Statement",
        "Retirement Account",
        "Gift Letter",
        "VOD",  # Verification of Deposit
    ],
    # Identity
    "identity": [
        "Driver License",
        "Passport",
        "Social Security Card",
        "Government ID",
    ],
    # Property
    "property": [
        "Purchase Contract",
        "Appraisal",
        "Title Report",
        "HOA Documents",
        "Property Insurance",
    ],
    # Credit
    "credit": [
        "Credit Report",
        "Letter of Explanation",
        "Bankruptcy Documents",
    ],
    # Disclosures
    "disclosures": [
        "Loan Estimate",
        "Closing Disclosure",
        "Intent to Proceed",
    ],
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ProcessedDocument:
    """A document from the R&S manifest."""
    document_id: str
    blob_id: str
    category_id: int
    category_name: str
    category_source: str  # "ai" or "hil"
    confidence: float
    total_pages: int
    borrowers: List[Dict[str, Any]] = field(default_factory=list)
    exceptions: Dict[str, bool] = field(default_factory=dict)
    has_exceptions: bool = False
    source_bucket: str = ""
    source_key: str = ""


@dataclass
class DocumentCoverage:
    """Document coverage analysis result."""
    job_id: str
    job_status: str
    loan_id: Optional[str]
    
    # Counts
    blobs_count: int
    documents_count: int
    
    # Documents by category
    documents: List[ProcessedDocument] = field(default_factory=list)
    categories_found: Set[str] = field(default_factory=set)
    categories_by_type: Dict[str, List[str]] = field(default_factory=dict)
    
    # Coverage analysis
    missing_by_type: Dict[str, List[str]] = field(default_factory=dict)
    coverage_score: float = 0.0
    
    # Issues
    documents_with_exceptions: List[ProcessedDocument] = field(default_factory=list)
    low_confidence_documents: List[ProcessedDocument] = field(default_factory=list)
    
    # Timestamps
    analyzed_at: str = ""
    job_created_at: str = ""
    job_completed_at: str = ""


# =============================================================================
# MANIFEST PARSING
# =============================================================================

def parse_manifest(manifest: Dict[str, Any]) -> DocumentCoverage:
    """
    Parse a TaskTile webhook manifest into DocumentCoverage.
    
    Args:
        manifest: Raw manifest JSON from webhook
        
    Returns:
        DocumentCoverage with parsed data
    """
    job = manifest.get("job", {})
    counts = manifest.get("counts", {})
    raw_docs = manifest.get("documents", [])
    
    # Extract entity info (may contain loan_id)
    entity = manifest.get("entity", {})
    loan_id = entity.get("loan_id")
    
    coverage = DocumentCoverage(
        job_id=job.get("id", ""),
        job_status=job.get("status", "unknown"),
        loan_id=loan_id,
        blobs_count=counts.get("blobs", 0),
        documents_count=counts.get("documents", 0),
        analyzed_at=datetime.now(timezone.utc).isoformat(),
        job_created_at=job.get("created_at", ""),
        job_completed_at=job.get("completed_at", ""),
    )
    
    # Parse each document
    for doc in raw_docs:
        category = doc.get("category", {})
        metadata = doc.get("metadata", {})
        source = doc.get("source", {})
        exceptions = metadata.get("exceptions", {})
        
        # Check for any exceptions
        has_exceptions = any(exceptions.values())
        
        processed = ProcessedDocument(
            document_id=doc.get("id", ""),
            blob_id=doc.get("blob_id", ""),
            category_id=category.get("category_id", 0),
            category_name=category.get("category_name", "Unknown"),
            category_source=category.get("source", "unknown"),
            confidence=metadata.get("confidence", 0.0),
            total_pages=metadata.get("total_pages", 0),
            borrowers=metadata.get("borrowers", []),
            exceptions=exceptions,
            has_exceptions=has_exceptions,
            source_bucket=source.get("bucket", ""),
            source_key=source.get("key", ""),
        )
        
        coverage.documents.append(processed)
        coverage.categories_found.add(processed.category_name)
        
        # Track documents with issues
        if has_exceptions:
            coverage.documents_with_exceptions.append(processed)
        if processed.confidence < 0.8:
            coverage.low_confidence_documents.append(processed)
    
    return coverage


# =============================================================================
# COVERAGE ANALYSIS
# =============================================================================

def analyze_document_coverage(
    manifest: Dict[str, Any],
    required_categories: Optional[Dict[str, List[str]]] = None,
) -> DocumentCoverage:
    """
    Analyze document coverage from a TaskTile manifest.
    
    Args:
        manifest: Raw manifest JSON from webhook
        required_categories: Optional custom required categories dict
        
    Returns:
        DocumentCoverage with full analysis
    """
    logger.info("[DOC_COVERAGE] Analyzing manifest...")
    
    # Parse manifest
    coverage = parse_manifest(manifest)
    
    # Use custom or default required categories
    requirements = required_categories or REQUIRED_CATEGORIES
    
    # Normalize found categories for matching
    found_lower = {cat.lower() for cat in coverage.categories_found}
    
    # Analyze coverage by type
    total_required = 0
    total_found = 0
    
    for doc_type, required_list in requirements.items():
        found_in_type = []
        missing_in_type = []
        
        for req_cat in required_list:
            total_required += 1
            # Fuzzy match - check if required category is contained in any found category
            matched = any(
                req_cat.lower() in found.lower() or found.lower() in req_cat.lower()
                for found in coverage.categories_found
            )
            if matched:
                found_in_type.append(req_cat)
                total_found += 1
            else:
                missing_in_type.append(req_cat)
        
        coverage.categories_by_type[doc_type] = found_in_type
        if missing_in_type:
            coverage.missing_by_type[doc_type] = missing_in_type
    
    # Calculate coverage score
    if total_required > 0:
        coverage.coverage_score = total_found / total_required
    
    logger.info(f"[DOC_COVERAGE] ✓ Analysis complete")
    logger.info(f"[DOC_COVERAGE]   Documents: {coverage.documents_count}")
    logger.info(f"[DOC_COVERAGE]   Categories found: {len(coverage.categories_found)}")
    logger.info(f"[DOC_COVERAGE]   Coverage score: {coverage.coverage_score:.1%}")
    logger.info(f"[DOC_COVERAGE]   Exceptions: {len(coverage.documents_with_exceptions)}")
    
    return coverage


def format_coverage_summary(coverage: DocumentCoverage) -> str:
    """
    Format document coverage as a human-readable summary.
    
    Args:
        coverage: DocumentCoverage analysis result
        
    Returns:
        Formatted string summary
    """
    lines = [
        "=" * 60,
        "DOCUMENT COVERAGE ANALYSIS",
        "=" * 60,
        f"Job ID: {coverage.job_id}",
        f"Status: {coverage.job_status}",
        f"Documents: {coverage.documents_count}",
        f"Coverage Score: {coverage.coverage_score:.1%}",
        "",
    ]
    
    # Categories found
    if coverage.categories_found:
        lines.append("Categories Found:")
        for cat in sorted(coverage.categories_found):
            lines.append(f"  ✓ {cat}")
        lines.append("")
    
    # Missing categories
    if coverage.missing_by_type:
        lines.append("Missing Documents:")
        for doc_type, missing in coverage.missing_by_type.items():
            lines.append(f"  [{doc_type.upper()}]")
            for cat in missing:
                lines.append(f"    ✗ {cat}")
        lines.append("")
    
    # Issues
    if coverage.documents_with_exceptions:
        lines.append(f"Documents with Exceptions: {len(coverage.documents_with_exceptions)}")
        for doc in coverage.documents_with_exceptions[:5]:
            active_exceptions = [k for k, v in doc.exceptions.items() if v]
            lines.append(f"  - {doc.category_name}: {', '.join(active_exceptions)}")
        lines.append("")
    
    if coverage.low_confidence_documents:
        lines.append(f"Low Confidence ({len(coverage.low_confidence_documents)}):")
        for doc in coverage.low_confidence_documents[:5]:
            lines.append(f"  - {doc.category_name}: {doc.confidence:.1%}")
    
    lines.append("=" * 60)
    return "\n".join(lines)


# =============================================================================
# FILE OPERATIONS
# =============================================================================

def load_manifest_from_file(file_path: str) -> Dict[str, Any]:
    """Load a manifest JSON file."""
    with open(file_path) as f:
        return json.load(f)


def analyze_manifest_file(file_path: str) -> DocumentCoverage:
    """Analyze a manifest from a file path."""
    manifest = load_manifest_from_file(file_path)
    return analyze_document_coverage(manifest)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    
    if len(sys.argv) < 2:
        print("Usage: python doc_coverage.py <manifest.json>")
        print("\nLooking for manifests in backend/output/tasktile_manifests/...")
        
        manifest_dir = Path(__file__).parent.parent.parent.parent / "backend/output/tasktile_manifests"
        manifests = list(manifest_dir.glob("*.json"))
        
        if manifests:
            print(f"Found {len(manifests)} manifest(s):")
            for m in manifests:
                print(f"  - {m.name}")
        else:
            print("No manifests found yet. Wait for TaskTile job to complete.")
        sys.exit(1)
    
    manifest_path = sys.argv[1]
    
    try:
        coverage = analyze_manifest_file(manifest_path)
        print(format_coverage_summary(coverage))
    except FileNotFoundError:
        print(f"File not found: {manifest_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        sys.exit(1)

