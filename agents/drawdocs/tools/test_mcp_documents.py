#!/usr/bin/env python3
"""
Test script for document functions using MCP server.
"""

import sys
import os
import json
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv

# Load from MCP server first, then local (local won't override)
mcp_env_path = Path.home() / "Documents/Fintor/encompass-mcp-server/.env"
if mcp_env_path.exists():
    load_dotenv(mcp_env_path)
    print(f"✅ Loaded MCP server environment from {mcp_env_path}")

# Load local .env (won't override existing vars)
local_env_path = project_root / ".env"
if local_env_path.exists():
    load_dotenv(local_env_path, override=False)
    print(f"✅ Loaded local environment from {local_env_path}")

# Now import the primitives
from agents.drawdocs.tools import list_loan_documents, download_document_from_efolder

def test_list_documents():
    """Test listing documents from a loan's eFolder."""
    
    # Test loan ID
    loan_id = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6"
    
    print("\n" + "="*80)
    print("TEST: List Loan Documents")
    print("="*80)
    print(f"\nLoan ID: {loan_id}")
    
    try:
        documents = list_loan_documents(loan_id)
        
        print(f"\n✅ Found {len(documents)} documents")
        
        if documents:
            print("\n--- First 5 Documents ---")
            for i, doc in enumerate(documents[:5], 1):
                print(f"\n{i}. {doc.get('title', 'Untitled')}")
                print(f"   ID: {doc.get('id', 'N/A')}")
                print(f"   Type: {doc.get('type', 'N/A')}")
                print(f"   Size: {doc.get('fileSize', 0) / 1024:.2f} KB")
                print(f"   Date: {doc.get('createdDate', 'N/A')}")
        
        # Save to file
        output_file = project_root / "mcp_documents_list.json"
        with open(output_file, 'w') as f:
            json.dump(documents, f, indent=2, default=str)
        print(f"\n✅ Full document list saved to: {output_file}")
        
        return documents
        
    except Exception as e:
        print(f"\n❌ Error listing documents: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_download_document(loan_id, attachment_id):
    """Test downloading a specific document."""
    
    print("\n" + "="*80)
    print("TEST: Download Document")
    print("="*80)
    print(f"\nLoan ID: {loan_id}")
    print(f"Attachment ID: {attachment_id}")
    
    try:
        file_path = download_document_from_efolder(loan_id, attachment_id)
        
        if file_path:
            file_size = Path(file_path).stat().st_size
            size_kb = file_size / 1024
            print(f"\n✅ Downloaded successfully")
            print(f"   Path: {file_path}")
            print(f"   Size: {size_kb:.2f} KB")
        else:
            print(f"\n❌ Download failed")
        
        return file_path
        
    except Exception as e:
        print(f"\n❌ Error downloading document: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run all tests."""
    
    print("\n" + "="*80)
    print("MCP SERVER DOCUMENT FUNCTIONS TEST")
    print("="*80)
    
    # Test loan ID
    loan_id = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6"
    
    # Test 1: List documents
    documents = test_list_documents()
    
    # Test 2: Download first document (if any)
    if documents and len(documents) > 0:
        first_doc = documents[0]
        attachment_id = first_doc.get("id")  # API returns "id" not "attachmentId"
        
        if attachment_id:
            test_download_document(loan_id, attachment_id)
        else:
            print("\n⚠️ No ID found in first document")
    else:
        print("\n⚠️ No documents to download")
    
    print("\n" + "="*80)
    print("TESTS COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()

