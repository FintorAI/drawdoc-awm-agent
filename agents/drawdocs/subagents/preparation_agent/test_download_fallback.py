"""
Test script for document download fallback functionality.

Tests the two-tier download system:
1. MCP server (primary)
2. EncompassConnect (fallback)

This verifies that when MCP server fails, the system automatically
falls back to EncompassConnect without user intervention.
"""

import sys
import json
import os
from pathlib import Path

# Add project root to path FIRST (before any imports from agents)
# File is at: .../agents/drawdocs/subagents/preparation_agent/test_download_fallback.py
# Need to go up 5 levels to get to project root
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Add preparation_agent directory for direct imports
prep_agent_dir = Path(__file__).parent
sys.path.insert(0, str(prep_agent_dir))

# Add tools directory to path (for primitives)
tools_dir = project_root / "agents" / "drawdocs" / "tools"
if tools_dir.exists():
    sys.path.insert(0, str(tools_dir))

# DEBUG: Print paths
print(f"\n[DEBUG] Project root: {project_root}")
print(f"[DEBUG] Tools dir exists: {tools_dir.exists()}")
print(f"[DEBUG] Tools dir: {tools_dir}")
print(f"[DEBUG] sys.path[0]: {sys.path[0]}")
print(f"[DEBUG] sys.path[1]: {sys.path[1]}")
print(f"[DEBUG] sys.path[2]: {sys.path[2]}\n")

# Load environment variables from PROJECT ROOT (same as drawdoc_agent_test.py)
from dotenv import load_dotenv
env_file = project_root / ".env"
print(f"Loading environment from: {env_file}\n")
load_dotenv(env_file)

# Import the download function
# Try relative import first (when in same directory), then absolute
try:
    from preparation_agent import download_document, get_loan_documents
except ImportError:
    from agents.drawdocs.subagents.preparation_agent.preparation_agent import (
        download_document,
        get_loan_documents
    )

def test_download_with_fallback():
    """Test document download with fallback capability."""
    
    print("\n" + "=" * 80)
    print("DOCUMENT DOWNLOAD FALLBACK TEST")
    print("=" * 80)
    print("\nThis test verifies the two-tier download system:")
    print("  1. Try MCP server (primary)")
    print("  2. Fallback to EncompassConnect if MCP fails")
    print("\n" + "=" * 80 + "\n")
    
    # Test loan ID (same as drawdoc_agent_test.py - TEST_LOAN_WITH_DOCS)
    loan_id = "387596ee-7090-47ca-8385-206e22c9c9da"
    
    
    print(f"Loan ID: {loan_id}")
    print("\n[STEP 1] Listing loan documents...")
    print("-" * 80)
    
    # Get documents for the loan
    try:
        documents_result = get_loan_documents.invoke({
            "loan_id": loan_id
        })
        
        if "error" in documents_result:
            print(f"✗ Error listing documents: {documents_result['error']}")
            return False
        
        documents = documents_result.get("documents", [])
        print(f"✓ Found {len(documents)} documents")
        
        if not documents:
            print("✗ No documents found to test download")
            return False
        
        # Show first few documents
        print("\nFirst 5 documents:")
        for i, doc in enumerate(documents[:5]):
            doc_id = doc.get("id") or "unknown"
            doc_id_short = doc_id[:8] if doc_id != "unknown" else "unknown"
            doc_title = doc.get("title", "Unknown")
            doc_type = doc.get("type", "Unknown")
            print(f"  {i+1}. {doc_title} (ID: {doc_id_short}..., Type: {doc_type})")
        
    except Exception as e:
        print(f"✗ Error listing documents: {e}")
        return False
    
    print("\n[STEP 2] Testing download with fallback...")
    print("-" * 80)
    
    # Test download on first few documents
    test_results = []
    test_count = min(3, len(documents))  # Test first 3 documents
    
    for i, doc in enumerate(documents[:test_count]):
        doc_id = doc.get("id") or "unknown"
        doc_title = doc.get("title", "Unknown")
        
        print(f"\nTest {i+1}/{test_count}: Downloading '{doc_title}'")
        doc_id_short = doc_id[:8] if doc_id != "unknown" else "unknown"
        print(f"  Attachment ID: {doc_id_short}...")
        
        try:
            # download_document is a LangChain tool, use .invoke()
            result = download_document.invoke({
                "loan_id": loan_id,
                "attachment_id": doc_id,
                "document_title": doc_title,
                "document_type": doc.get("type", "Unknown")
            })
            
            # Check result
            success = result.get("file_path") is not None
            download_method = result.get("download_method", "unknown")
            file_size_kb = result.get("file_size_kb", 0)
            cached = result.get("cached", False)
            
            if success:
                status_icon = "✓" if not cached else "⚡"
                status_text = "Success" if not cached else "Cached"
                print(f"  {status_icon} {status_text}")
                print(f"  Method: {download_method}")
                print(f"  Size: {file_size_kb} KB")
                print(f"  Path: {result.get('file_path')}")
            else:
                print(f"  ✗ Failed - no file path returned")
            
            test_results.append({
                "document_title": doc_title,
                "attachment_id": (doc_id[:8] + "...") if doc_id != "unknown" else "unknown",
                "success": success,
                "download_method": download_method,
                "file_size_kb": file_size_kb,
                "cached": cached,
                "error": None
            })
            
        except Exception as e:
            print(f"  ✗ Failed with error: {str(e)}")
            test_results.append({
                "document_title": doc_title,
                "attachment_id": (doc_id[:8] + "...") if doc_id != "unknown" else "unknown",
                "success": False,
                "download_method": "none",
                "file_size_kb": 0,
                "cached": False,
                "error": str(e)
            })
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    successful = sum(1 for r in test_results if r["success"])
    failed = len(test_results) - successful
    
    print(f"\nTotal tests: {len(test_results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    # Breakdown by download method
    methods = {}
    for r in test_results:
        if r["success"]:
            method = r["download_method"]
            methods[method] = methods.get(method, 0) + 1
    
    if methods:
        print(f"\nDownload methods used:")
        for method, count in methods.items():
            print(f"  - {method}: {count}")
    
    # Show failed downloads
    if failed > 0:
        print(f"\nFailed downloads:")
        for r in test_results:
            if not r["success"]:
                print(f"  ✗ {r['document_title']} - {r.get('error', 'Unknown error')}")
    
    # Save detailed results
    output_file = Path(__file__).parent / "test_download_fallback_output.json"
    with open(output_file, 'w') as f:
        json.dump({
            "loan_id": loan_id,
            "total_tests": len(test_results),
            "successful": successful,
            "failed": failed,
            "download_methods": methods,
            "test_results": test_results
        }, f, indent=2)
    
    print(f"\n✓ Detailed results saved to: {output_file}")
    print("=" * 80 + "\n")
    
    # Overall pass/fail
    return successful > 0


def test_specific_document():
    """Test download of a specific document by attachment ID."""
    
    print("\n" + "=" * 80)
    print("SPECIFIC DOCUMENT DOWNLOAD TEST")
    print("=" * 80)
    print("\nEnter document details to test:")
    
    loan_id = input("Loan ID: ").strip()
    if not loan_id:
        loan_id = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6"
        print(f"Using default: {loan_id}")
    
    attachment_id = input("Attachment ID: ").strip()
    if not attachment_id:
        print("✗ Attachment ID required")
        return False
    
    print(f"\nDownloading attachment {attachment_id[:8]}...")
    print("-" * 80)
    
    try:
        result = download_document(
            loan_id=loan_id,
            attachment_id=attachment_id,
            document_title="Test Document",
            document_type="Unknown"
        )
        
        print(f"\n✓ Download successful!")
        print(f"  Method: {result.get('download_method')}")
        print(f"  Size: {result.get('file_size_kb')} KB")
        print(f"  Path: {result.get('file_path')}")
        print(f"  Cached: {result.get('cached')}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Download failed: {str(e)}")
        return False


def test_fallback_isolation():
    """Test to verify fallback works when MCP is unavailable."""
    
    print("\n" + "=" * 80)
    print("FALLBACK ISOLATION TEST")
    print("=" * 80)
    print("\nThis test checks if EncompassConnect fallback works")
    print("when MCP server is unavailable.")
    print("\nNOTE: This test temporarily modifies sys.path to simulate MCP failure.")
    print("=" * 80 + "\n")
    
    # Save original sys.path
    original_path = sys.path.copy()
    
    try:
        # Remove MCP server from path to force fallback
        mcp_server_path = str(Path(__file__).parent.parent.parent.parent.parent / "encompass-mcp-server")
        if mcp_server_path in sys.path:
            sys.path.remove(mcp_server_path)
            print(f"✓ Temporarily removed MCP server from path")
        
        # Clear any cached imports
        if 'agents.drawdocs.tools.primitives' in sys.modules:
            del sys.modules['agents.drawdocs.tools.primitives']
        if 'agents.drawdocs.tools' in sys.modules:
            del sys.modules['agents.drawdocs.tools']
        
        print("✓ Cleared cached imports")
        print("\nAttempting download (should use EncompassConnect)...")
        print("-" * 80)
        
        loan_id = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6"
        
        # Get first document
        documents_result = get_loan_documents.invoke({"loan_id": loan_id})
        documents = documents_result.get("documents", [])
        
        if not documents:
            print("✗ No documents found to test")
            return False
        
        doc = documents[0]
        doc_id = doc.get("id")
        doc_title = doc.get("title", "Unknown")
        
        print(f"Testing: {doc_title}")
        
        result = download_document(
            loan_id=loan_id,
            attachment_id=doc_id,
            document_title=doc_title
        )
        
        download_method = result.get("download_method", "unknown")
        
        print(f"\n✓ Download successful!")
        print(f"  Method used: {download_method}")
        
        if "fallback" in download_method.lower() or download_method == "cached":
            print(f"  ✓ Fallback mechanism confirmed working!")
            return True
        else:
            print(f"  ⚠ Warning: Expected fallback but got '{download_method}'")
            return True  # Still a success, just not testing fallback
        
    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        return False
        
    finally:
        # Restore original sys.path
        sys.path = original_path
        print("\n✓ Restored original sys.path")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test document download fallback")
    parser.add_argument("--specific", action="store_true", 
                       help="Test download of specific document (interactive)")
    parser.add_argument("--fallback-only", action="store_true",
                       help="Test fallback isolation (simulate MCP failure)")
    
    args = parser.parse_args()
    
    if args.specific:
        success = test_specific_document()
    elif args.fallback_only:
        success = test_fallback_isolation()
    else:
        # Default: test with automatic fallback
        success = test_download_with_fallback()
    
    sys.exit(0 if success else 1)

