"""DrawDoc-AWM Agent - Document Drawing and Annotation Agent.

This agent is specialized for drawing and annotating documents for AWM
(Asset and Wealth Management) workflows.
"""

import os
import sys
from pathlib import Path

# Add local baseCopilotAgent source to path for development
# Insert at position 0 to ensure local version is used before installed package
baseCopilotAgent_path = Path(__file__).parent.parent.parent / "baseCopilotAgent" / "src"
if str(baseCopilotAgent_path) not in sys.path:
    sys.path.insert(0, str(baseCopilotAgent_path))

# Remove any cached imports of copilotagent to force reload from local path
if 'copilotagent' in sys.modules:
    del sys.modules['copilotagent']
if 'copilotagent.encompass_connect' in sys.modules:
    del sys.modules['copilotagent.encompass_connect']

from copilotagent import create_deep_agent, EncompassConnect

# =============================================================================
# TEST CONFIGURATION - Fill in these values with your actual credentials
# =============================================================================

# Encompass API Configuration
ENCOMPASS_CONFIG = {
    "access_token": "0004SB1QUuN9Iq5879IWiSyx8BvQ",  # Fresh token from get_fresh_token_and_test.sh
    "api_base_url": "https://api.elliemae.com",
    "credentials": {
        "username": "testadmin",
        "password": "Fintor#Inc5",
        "client_id": "ddtjp20",
        "client_secret": "eJCLnEw#2ue502eD#vKZZh2JrG$YFv8@lK^1uNT2sGE2pomnm0FwLKd#xcdFt7z1",
        "instance_id": "BE11207984",
        "subject_user_id": "testdocdrawer",
    },
}

# LandingAI Configuration
LANDINGAI_API_KEY = "N2M5NWh0MzJoNDd2NTczZ3dkOHVmOmUxdDdpdFFkd1RzZ21ZUExUa01BTEU5MXBGZHZza3FQ"

# Test Data - Fill these with actual IDs from your Encompass system
# NOTE: For get_field tests
TEST_LOAN_ID = "65ec32a1-99df-4685-92ce-41a08fd3b64e"  # From get_fresh_token_and_test.sh

# NOTE: For get_document and extract_document tests - these belong to different loan
TEST_LOAN_ID_WITH_DOCS = "387596ee-7090-47ca-8385-206e22c9c9da"  # Loan with documents
TEST_DOCUMENT_ID = "0985d4a6-f928-4254-87db-8ccaeae2f5e9"  # From test_get_document.py
TEST_ATTACHMENT_ID = "d78186cc-a8a2-454f-beaf-19f0e6c3aa8c"  # From download_attachment.py

# Field IDs to test
TEST_FIELD_IDS = ["4000", "4002", "4004", "353"]  # Loan Amount, First Name, Last Name, Loan Number

# Test Flags
SAVE_DOWNLOADED_DOCS = True  # Save downloaded documents to disk for review
DOWNLOAD_DIR = Path(__file__).parent.parent.parent / "downloaded_documents"

# Simple system prompt - detailed workflow guidance is handled by the planner
drawdoc_instructions = """You are a document drawing and annotation specialist for AWM (Asset and Wealth Management).

Your job is to create, annotate, and prepare professional documents for AWM clients. Use the planner to organize your work."""

# Load local planning prompt
planner_prompt_file = Path(__file__).parent / "planner_prompt.md"
planning_prompt = planner_prompt_file.read_text() if planner_prompt_file.exists() else None

# Create the DrawDoc-AWM agent
agent = create_deep_agent(
    agent_type="DrawDoc-AWM",
    system_prompt=drawdoc_instructions,
    planning_prompt=planning_prompt,  # Use local planning prompt
)

# When this agent is invoked without messages, it will present the default message:
# "Let's draw the docs for AWM"
# The user can approve or modify this message before proceeding.

# =============================================================================
# TEST FUNCTIONS - EncompassConnect API Methods
# =============================================================================


def test_get_field():
    """Test reading loan fields from Encompass API."""
    print("=" * 80)
    print("TEST: Get Loan Fields")
    print("=" * 80)
    print()

    try:
        # Initialize client
        client = EncompassConnect(
            access_token=ENCOMPASS_CONFIG["access_token"],
            credentials=ENCOMPASS_CONFIG["credentials"],
            api_base_url=ENCOMPASS_CONFIG["api_base_url"],
        )

        print(f"Loan ID: {TEST_LOAN_ID}")
        print(f"Field IDs: {TEST_FIELD_IDS}")
        print()

        # Test reading multiple fields
        print("Reading fields...")
        result = client.get_field(TEST_LOAN_ID, TEST_FIELD_IDS)

        print("✅ Success!")
        print()
        print("Field Values:")
        print("-" * 80)
        for field_id, value in result.items():
            field_names = {
                "4000": "Loan Amount",
                "4002": "Borrower First Name",
                "4004": "Borrower Last Name",
                "353": "Loan Number",
            }
            field_name = field_names.get(field_id, field_id)
            print(f"  {field_id} ({field_name}): {value}")
        print()

        return result

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_get_document():
    """Test retrieving document metadata from Encompass API."""
    print("=" * 80)
    print("TEST: Get Document Metadata")
    print("=" * 80)
    print()

    try:
        # Initialize client
        client = EncompassConnect(
            access_token=ENCOMPASS_CONFIG["access_token"],
            credentials=ENCOMPASS_CONFIG["credentials"],
            api_base_url=ENCOMPASS_CONFIG["api_base_url"],
        )

        print(f"Loan ID: {TEST_LOAN_ID_WITH_DOCS}")
        print(f"Document ID: {TEST_DOCUMENT_ID}")
        print()

        # Get document metadata
        print("Retrieving document metadata...")
        doc = client.get_document(TEST_LOAN_ID_WITH_DOCS, TEST_DOCUMENT_ID)

        print("✅ Success!")
        print()
        print("Document Information:")
        print("-" * 80)
        print(f"  Title: {doc.get('title', 'N/A')}")
        print(f"  Document Type: {doc.get('documentType', 'N/A')}")
        print(f"  Document Type ID: {doc.get('documentTypeId', 'N/A')}")
        print(f"  Status: {doc.get('status', 'N/A')}")
        print(f"  Date Created: {doc.get('dateCreated', 'N/A')}")
        print(f"  Date Modified: {doc.get('dateModified', 'N/A')}")
        print(f"  Created By: {doc.get('createdBy', 'N/A')}")
        print(f"  Modified By: {doc.get('modifiedBy', 'N/A')}")
        print()

        # Show attachments
        attachments = doc.get("attachments", [])
        if attachments:
            print(f"Attachments ({len(attachments)}):")
            print("-" * 80)
            for idx, attach in enumerate(attachments, 1):
                print(f"\n  Attachment {idx}:")
                print(f"    Attachment ID: {attach.get('attachmentId', 'N/A')}")
                print(f"    Title: {attach.get('title', 'N/A')}")
                print(f"    Media Type: {attach.get('mediaType', 'N/A')}")
                print(f"    Page Count: {attach.get('pageCount', 'N/A')}")
                print(f"    Size (bytes): {attach.get('attachmentSize', 'N/A')}")
        else:
            print("Attachments: None")
        print()

        return doc

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_extract_document():
    """Test document extraction with LandingAI."""
    print("=" * 80)
    print("TEST: Extract Document Data with LandingAI")
    print("=" * 80)
    print()

    try:
        # Initialize client
        client = EncompassConnect(
            access_token=ENCOMPASS_CONFIG["access_token"],
            credentials=ENCOMPASS_CONFIG["credentials"],
            api_base_url=ENCOMPASS_CONFIG["api_base_url"],
            landingai_api_key=LANDINGAI_API_KEY,
        )

        print(f"Loan ID: {TEST_LOAN_ID_WITH_DOCS}")
        print(f"Attachment ID: {TEST_ATTACHMENT_ID}")
        print()

        # Step 1: Download the document
        print("Step 1: Downloading document...")
        document_bytes = client.download_attachment(TEST_LOAN_ID_WITH_DOCS, TEST_ATTACHMENT_ID)
        print(f"✅ Downloaded {len(document_bytes):,} bytes ({len(document_bytes) / 1024:.2f} KB)")
        
        # Save to disk if flag is set
        if SAVE_DOWNLOADED_DOCS:
            DOWNLOAD_DIR.mkdir(exist_ok=True, parents=True)
            saved_path = DOWNLOAD_DIR / f"attachment_{TEST_ATTACHMENT_ID}.pdf"
            with open(saved_path, "wb") as f:
                f.write(document_bytes)
            print(f"💾 Saved to: {saved_path}")
        print()

        # Step 2: Define extraction schema - simplified to extract names
        # Based on LandingAI documentation format
        extraction_schema = {
            "type": "object",
            "properties": {
                "employer_name": {
                    "type": "string",
                    "title": "Employer Name",
                    "description": "The name of the employer/company from the W-2 form",
                },
                "employee_name": {
                    "type": "string",
                    "title": "Employee Name",
                    "description": "The full name of the employee from the W-2 form",
                },
                "tax_year": {
                    "type": "string",
                    "title": "Tax Year",
                    "description": "The tax year for this W-2 form",
                },
            },
        }

        # Step 3: Extract data using LandingAI
        print("Step 2: Extracting data with LandingAI...")
        print("Schema fields:")
        print("  - employer_name: Employer/company name")
        print("  - employee_name: Employee full name")
        print("  - tax_year: Tax year")
        print()

        result = client.extract_document_data(document_bytes, extraction_schema, doc_type="W2", filename="w2_document.pdf")

        print("✅ Extraction successful!")
        print()
        print("Extraction Results:")
        print("-" * 80)
        print(f"  Document Type: {result.get('doc_type', 'N/A')}")
        print(f"  Extraction Method: {result['extraction_method']}")
        print()
        print("Extracted Data:")
        print("-" * 80)

        # Pretty print the extracted data
        import json

        extracted_data = result.get("extracted_schema", {})
        print(json.dumps(extracted_data, indent=2))
        print()
        
        # Also show key fields clearly
        if extracted_data:
            print("Key Fields:")
            print("-" * 80)
            print(f"  Employer Name: {extracted_data.get('employer_name', 'N/A')}")
            print(f"  Employee Name: {extracted_data.get('employee_name', 'N/A')}")
            print(f"  Tax Year: {extracted_data.get('tax_year', 'N/A')}")
        print()

        return result

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_extract_local_document():
    """Test document extraction with a local PDF file."""
    print("=" * 80)
    print("TEST: Extract Local Document (Letter of Explanation)")
    print("=" * 80)
    print()

    try:
        # Initialize client
        client = EncompassConnect(
            access_token=ENCOMPASS_CONFIG["access_token"],
            credentials=ENCOMPASS_CONFIG["credentials"],
            api_base_url=ENCOMPASS_CONFIG["api_base_url"],
            landingai_api_key=LANDINGAI_API_KEY,
        )

        # Path to local document
        local_doc_path = Path(__file__).parent.parent.parent / "downloaded_documents" / "Letter_of_Explanation_d9b13391-733f-4abc-ae0d-3b4470e9c29c.pdf"
        
        if not local_doc_path.exists():
            print(f"❌ Document not found: {local_doc_path}")
            return None

        print(f"Document: {local_doc_path.name}")
        print()

        # Read the document
        print("Step 1: Reading local document...")
        with open(local_doc_path, "rb") as f:
            document_bytes = f.read()
        print(f"✅ Read {len(document_bytes):,} bytes ({len(document_bytes) / 1024:.2f} KB)")
        print()

        # Define extraction schema for Letter of Explanation
        extraction_schema = {
            "type": "object",
            "properties": {
                "borrower_name": {
                    "type": "string",
                    "title": "Borrower Name",
                    "description": "The full name of the borrower who wrote the letter",
                },
                "property_address": {
                    "type": "string",
                    "title": "Property Address",
                    "description": "The address of the property mentioned in the letter",
                },
                "letter_date": {
                    "type": "string",
                    "title": "Letter Date",
                    "description": "The date the letter was written",
                },
                "explanation_subject": {
                    "type": "string",
                    "title": "Subject of Explanation",
                    "description": "What the letter is explaining (e.g., gap in employment, credit issue, etc.)",
                },
                "key_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "title": "Key Points",
                    "description": "Main points or reasons mentioned in the explanation",
                },
            },
        }

        # Extract data using LandingAI
        print("Step 2: Extracting data with LandingAI...")
        print("Schema fields:")
        print("  - borrower_name: Name of the person writing the letter")
        print("  - property_address: Property address mentioned")
        print("  - letter_date: Date of the letter")
        print("  - explanation_subject: What is being explained")
        print("  - key_points: Main points in the explanation")
        print()

        result = client.extract_document_data(
            document_bytes, 
            extraction_schema, 
            doc_type="Letter of Explanation",
            filename=local_doc_path.name
        )

        print("✅ Extraction successful!")
        print()
        print("Extraction Results:")
        print("-" * 80)
        print(f"  Document Type: {result.get('doc_type', 'N/A')}")
        print(f"  Extraction Method: {result['extraction_method']}")
        print()
        print("Extracted Data:")
        print("-" * 80)

        # Pretty print the extracted data
        import json

        extracted_data = result.get("extracted_schema", {})
        print(json.dumps(extracted_data, indent=2))
        print()
        
        # Also show key fields clearly
        if extracted_data:
            print("Key Fields:")
            print("-" * 80)
            print(f"  Borrower Name: {extracted_data.get('borrower_name', 'N/A')}")
            print(f"  Property Address: {extracted_data.get('property_address', 'N/A')}")
            print(f"  Letter Date: {extracted_data.get('letter_date', 'N/A')}")
            print(f"  Subject: {extracted_data.get('explanation_subject', 'N/A')}")
            
            key_points = extracted_data.get('key_points', [])
            if key_points:
                print(f"  Key Points ({len(key_points)}):")
                for i, point in enumerate(key_points, 1):
                    print(f"    {i}. {point}")
        print()

        return result

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return None


def run_all_tests():
    """Run all EncompassConnect tests."""
    print("\n")
    print("=" * 80)
    print("ENCOMPASS CONNECT - INTEGRATION TESTS")
    print("=" * 80)
    print()

    # Check if configuration is set
    if ENCOMPASS_CONFIG["access_token"] == "YOUR_ACCESS_TOKEN_HERE":
        print("⚠️  WARNING: Test configuration not set!")
        print()
        print("Please update the configuration variables at the top of this file:")
        print("  - ENCOMPASS_CONFIG (access_token, credentials)")
        print("  - LANDINGAI_API_KEY")
        print("  - TEST_LOAN_ID")
        print("  - TEST_DOCUMENT_ID")
        print("  - TEST_ATTACHMENT_ID")
        print()
        return

    tests = [
        ("Get Field", test_get_field),
        ("Get Document", test_get_document),
        ("Extract Document (Encompass)", test_extract_document),
        ("Extract Local Document", test_extract_local_document),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = "✅ PASSED" if result is not None else "❌ FAILED"
        except Exception as e:
            results[test_name] = f"❌ FAILED: {e}"
        print()

    # Print summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    for test_name, status in results.items():
        print(f"  {test_name}: {status}")
    print()


if __name__ == "__main__":
    import argparse
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="DrawDoc-AWM Agent - Document Drawing and Annotation Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--test-all",
        action="store_true",
        help="Run all tests",
    )
    parser.add_argument(
        "--test-field",
        action="store_true",
        help="Run only the get_field test",
    )
    parser.add_argument(
        "--test-document",
        action="store_true",
        help="Run only the get_document test",
    )
    parser.add_argument(
        "--test-extract",
        action="store_true",
        help="Run only the extract_document test (from Encompass)",
    )
    parser.add_argument(
        "--test-local",
        action="store_true",
        help="Run only the local document extraction test",
    )
    parser.add_argument(
        "--save-docs",
        action="store_true",
        default=SAVE_DOWNLOADED_DOCS,
        help=f"Save downloaded documents to disk (default: {SAVE_DOWNLOADED_DOCS})",
    )
    parser.add_argument(
        "--no-save-docs",
        action="store_true",
        help="Don't save downloaded documents to disk",
    )
    
    args = parser.parse_args()
    
    # Handle save/no-save flags
    if args.no_save_docs:
        globals()["SAVE_DOWNLOADED_DOCS"] = False
    elif args.save_docs:
        globals()["SAVE_DOWNLOADED_DOCS"] = True
    
    # Check if any test flag is provided
    any_test = args.test_all or args.test_field or args.test_document or args.test_extract or args.test_local
    
    if any_test:
        # Run requested tests
        print("\n")
        print("=" * 80)
        print("ENCOMPASS CONNECT - INTEGRATION TESTS")
        print("=" * 80)
        print()
        
        # Check if configuration is set
        if ENCOMPASS_CONFIG["access_token"] == "YOUR_ACCESS_TOKEN_HERE":
            print("⚠️  WARNING: Test configuration not set!")
            print()
            print("Please update the configuration variables at the top of this file:")
            print("  - ENCOMPASS_CONFIG (access_token, credentials)")
            print("  - LANDINGAI_API_KEY")
            print("  - TEST_LOAN_ID")
            print("  - TEST_DOCUMENT_ID")
            print("  - TEST_ATTACHMENT_ID")
            print()
            sys.exit(1)
        
        # Show configuration
        print(f"Configuration:")
        print(f"  Save downloaded docs: {SAVE_DOWNLOADED_DOCS}")
        if SAVE_DOWNLOADED_DOCS:
            print(f"  Download directory: {DOWNLOAD_DIR}")
        print()
        
        results = {}
        
        # Run selected tests
        if args.test_all or args.test_field:
            try:
                result = test_get_field()
                results["Get Field"] = "✅ PASSED" if result is not None else "❌ FAILED"
            except Exception as e:
                results["Get Field"] = f"❌ FAILED: {e}"
            print()
        
        if args.test_all or args.test_document:
            try:
                result = test_get_document()
                results["Get Document"] = "✅ PASSED" if result is not None else "❌ FAILED"
            except Exception as e:
                results["Get Document"] = f"❌ FAILED: {e}"
            print()
        
        if args.test_all or args.test_extract:
            try:
                result = test_extract_document()
                results["Extract Document (Encompass)"] = "✅ PASSED" if result is not None else "❌ FAILED"
            except Exception as e:
                results["Extract Document (Encompass)"] = f"❌ FAILED: {e}"
            print()
        
        if args.test_all or args.test_local:
            try:
                result = test_extract_local_document()
                results["Extract Local Document"] = "✅ PASSED" if result is not None else "❌ FAILED"
            except Exception as e:
                results["Extract Local Document"] = f"❌ FAILED: {e}"
            print()
        
        # Print summary
        if results:
            print("=" * 80)
            print("TEST SUMMARY")
            print("=" * 80)
            for test_name, status in results.items():
                print(f"  {test_name}: {status}")
            print()
    else:
        # No test flags - show usage info
        print("DrawDoc-AWM Agent created successfully!")
        print("This agent is configured for document drawing and annotation workflows.")
        print()
        print("Default starting message:")
        print("'Let's draw the docs for AWM'")
        print()
        print("To use this agent:")
        print("1. Invoke with no messages to use the default starting message")
        print("2. Or provide specific document drawing instructions")
        print()
        print("Example usage:")
        print('agent.invoke({"messages": []})')
        print('# or')
        print('agent.invoke({"messages": [{"role": "user", "content": "Draw the quarterly report for client XYZ"}]})')
        print()
        print("-" * 80)
        print()
        print("To run EncompassConnect tests:")
        print("1. Update the configuration variables at the top of this file")
        print()
        print("2. Run tests:")
        print("   python drawdoc_agent.py --test-all          # Run all tests")
        print("   python drawdoc_agent.py --test-field        # Test get_field only")
        print("   python drawdoc_agent.py --test-document     # Test get_document only")
        print("   python drawdoc_agent.py --test-extract      # Test extract_document only")
        print("   python drawdoc_agent.py --test-local        # Test local extraction only")
        print()
        print("3. Options:")
        print("   --save-docs      # Save downloaded documents (default)")
        print("   --no-save-docs   # Don't save downloaded documents")
        print()

