"""DrawDoc-AWM Agent - Document Drawing and Annotation Agent.

This agent is specialized for drawing and annotating documents for AWM
(Asset and Wealth Management) workflows with Encompass integration.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Any, Literal, Optional
from dotenv import load_dotenv

# Configure logging to output to terminal/stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True  # Override any existing configuration
)

# Suppress noisy LangGraph infrastructure logs
logging.getLogger('langgraph_runtime_inmem').setLevel(logging.WARNING)
logging.getLogger('langgraph_api').setLevel(logging.WARNING)
logging.getLogger('langgraph').setLevel(logging.WARNING)
logging.getLogger('uvicorn').setLevel(logging.WARNING)
logging.getLogger('watchfiles').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

from copilotagent import create_deep_agent, EncompassConnect
from langchain_core.tools import tool
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent / ".env")

# =============================================================================
# TEST DATA - Hardcoded test values that are known to work
# =============================================================================

# Loan ID for field reading tests
TEST_LOAN_ID = "65ec32a1-99df-4685-92ce-41a08fd3b64e"

# Loan ID that has documents attached
TEST_LOAN_WITH_DOCS = "387596ee-7090-47ca-8385-206e22c9c9da"

# Document ID for metadata tests
TEST_DOCUMENT_ID = "0985d4a6-f928-4254-87db-8ccaeae2f5e9"

# Attachment ID for download and extraction tests (W-2 document)
TEST_ATTACHMENT_ID = "d78186cc-a8a2-454f-beaf-19f0e6c3aa8c"

# Common field IDs to test
TEST_FIELD_IDS = ["4000", "4002", "4004", "353"]  # Loan Amount, First Name, Last Name, Loan Number

# Sample extraction schema for W-2 documents
TEST_W2_SCHEMA = {
    "type": "object",
    "properties": {
        "employer_name": {
            "type": "string",
            "title": "Employer Name",
            "description": "Name of the employer/company from W-2",
        },
        "employee_name": {
            "type": "string",
            "title": "Employee Name",
            "description": "Full name of the employee from W-2",
        },
        "tax_year": {
            "type": "string",
            "title": "Tax Year",
            "description": "The tax year for this W-2 form",
        },
    },
}

# =============================================================================
# ENCOMPASS TOOLS - Tools for interacting with Encompass API
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


def _get_output_directory() -> Path:
    """Get the output directory for saving files.
    
    - Local development: Uses tmp/ directory in the agent folder
    - LangGraph Cloud: Uses /tmp directory (ephemeral, per-run storage)
    
    Files are NOT stored in state to avoid bloating the conversation context.
    Only file paths are returned in tool responses.
    """
    # Check if we have a local tmp directory (for local development)
    local_tmp_dir = Path(__file__).parent / "tmp"
    
    if local_tmp_dir.exists() and os.access(local_tmp_dir, os.W_OK):
        # Local development - use local tmp directory
        return local_tmp_dir
    else:
        # LangGraph Cloud or restricted environment - use system /tmp
        return Path("/tmp")


@tool
def read_loan_fields(loan_id: str, field_ids: list[str]) -> dict[str, Any]:
    """Read one or multiple fields from an Encompass loan.

    Use this tool to retrieve loan field values from Encompass. Common field IDs include:
    - 4000: Loan Amount
    - 4002: Borrower First Name
    - 4004: Borrower Last Name
    - 353: Loan Number
    - 1109: Property Street Address
    - 12: Property City
    - 14: Property State
    - 748: Loan Purpose

    Args:
        loan_id: The Encompass loan GUID (e.g., "65ec32a1-99df-4685-92ce-41a08fd3b64e")
        field_ids: List of field IDs to retrieve (e.g., ["4000", "4002", "4004"])

    Returns:
        Dictionary mapping field IDs to their values

    Example:
        >>> read_loan_fields("loan-guid", ["4000", "4002"])
        {"4000": "350000", "4002": "John"}
    """
    import logging
    import time
    
    logger = logging.getLogger(__name__)
    logger.info(f"[READ_FIELDS] Starting - Loan: {loan_id[:8]}..., Fields: {field_ids}")
    
    start_time = time.time()
    client = _get_encompass_client()
    result = client.get_field(loan_id, field_ids)
    read_time = time.time() - start_time
    
    logger.info(f"[READ_FIELDS] Success - Read {len(result)} fields in {read_time:.2f}s")
    
    return result


@tool
def get_loan_documents(loan_id: str, max_documents: int = 10) -> dict[str, Any]:
    """List documents in an Encompass loan with their attachment IDs.

    This tool retrieves documents associated with a loan, including document
    metadata and attachment IDs which can be used with download_loan_document.
    
    Large responses are saved to a JSON file to avoid token limits.
    Returns only a summary with key validation data.

    Args:
        loan_id: The Encompass loan GUID
        max_documents: Maximum number of documents to return in response (default: 10)
                      Full list is always saved to JSON file

    Returns:
        Dictionary containing:
        - total_documents: Total count of documents
        - total_attachments: Total count of attachments across all documents
        - file_path: Path to JSON file with complete document list
        - sample_documents: Summary of first N documents (title, ID, attachment count)
        - showing_first: How many documents are in the sample

    Example:
        >>> get_loan_documents("loan-guid", max_documents=5)
        {
            "total_documents": 159,
            "total_attachments": 207,
            "file_path": "/tmp/loan_documents_387596ee.json",
            "sample_documents": [
                {"title": "W2", "documentId": "0985d4a6-f92...", "attachment_count": 1},
                ...
            ],
            "showing_first": 5
        }
    """
    import logging
    import time
    import tempfile
    import json
    
    logger = logging.getLogger(__name__)
    logger.info(f"[LIST_DOCS] Starting - Loan: {loan_id[:8]}...")
    
    start_time = time.time()
    client = _get_encompass_client()
    
    documents = client.get_loan_documents(loan_id)
    elapsed = time.time() - start_time
    
    # Count attachments
    total_attachments = sum(len(doc.get('attachments', [])) for doc in documents)
    
    logger.info(f"[LIST_DOCS] Success - {len(documents)} documents, {total_attachments} attachments in {elapsed:.2f}s")
    
    # Save full list to JSON file (always, to avoid bloating conversation)
    output_dir = _get_output_directory()
    file_path = output_dir / f'loan_documents_{loan_id[:8]}_{int(time.time())}.json'
    
    with open(file_path, 'w') as f:
        json.dump(documents, f, indent=2)
    
    logger.info(f"[LIST_DOCS] Saved full document list to {file_path}")
    
    # Extract key info for validation - just titles and attachment counts
    sample_docs_summary = []
    for doc in documents[:max_documents]:
        sample_docs_summary.append({
            "title": doc.get('title', 'N/A'),
            "documentId": doc.get('documentId', 'N/A')[:12] + "...",  # Truncate ID
            "attachment_count": len(doc.get('attachments', [])),
            "first_attachment_id": doc.get('attachments', [{}])[0].get('attachmentId', 'N/A') if doc.get('attachments') else None
        })
    
    return {
        "total_documents": len(documents),
        "total_attachments": total_attachments,
        "file_path": str(file_path),
        "sample_documents": sample_docs_summary,  # Just summaries, not full data
        "showing_first": min(max_documents, len(documents)),
        "loan_id": loan_id,
        "message": f"Full document list ({len(documents)} docs) saved to JSON file. Use read_file on '{file_path}' if you need all details."
    }


@tool
def get_loan_entity(loan_id: str) -> dict[str, Any]:
    """Get complete loan data including all fields and custom fields.

    This tool retrieves the full loan entity from Encompass, including standard fields,
    custom fields, and other loan metadata. The full data is saved to a JSON file to
    avoid token limits.

    Args:
        loan_id: The Encompass loan GUID

    Returns:
        Dictionary containing:
        - field_count: Number of populated fields in the response
        - loan_number: The loan number (if available)
        - file_path: Path to JSON file with complete loan data
        - key_fields: Sample of important loan fields
        - loan_id: The loan ID

    Example:
        >>> get_loan_entity("loan-guid")
        {
            "field_count": 247,
            "loan_number": "12345",
            "file_path": "/tmp/loan_entity_65ec32a1.json",
            "key_fields": {
                "loanNumber": "12345",
                "borrowerFirstName": "John",
                "borrowerLastName": "Doe"
            },
            "loan_id": "65ec32a1-99df-4685-92ce-41a08fd3b64e"
        }
    """
    import logging
    import time
    import json
    
    logger = logging.getLogger(__name__)
    logger.info(f"[GET_LOAN] Starting - Loan: {loan_id[:8]}...")
    
    start_time = time.time()
    client = _get_encompass_client()
    
    loan_data = client.get_loan_entity(loan_id)
    elapsed = time.time() - start_time
    
    # Count populated fields
    field_count = len(loan_data)
    loan_number = loan_data.get('loanNumber', 'N/A')
    
    logger.info(f"[GET_LOAN] Success - {field_count} fields retrieved in {elapsed:.2f}s")
    
    # Save full loan data to JSON file to avoid bloating conversation
    output_dir = _get_output_directory()
    file_path = output_dir / f'loan_entity_{loan_id[:8]}_{int(time.time())}.json'
    
    with open(file_path, 'w') as f:
        json.dump(loan_data, f, indent=2)
    
    logger.info(f"[GET_LOAN] Saved full loan data to {file_path}")
    
    # Extract key fields for quick reference
    key_fields = {}
    important_fields = [
        'loanNumber', 'borrowerFirstName', 'borrowerLastName',
        'loanAmount', 'propertyStreetAddress', 'propertyCity', 'propertyState'
    ]
    for field in important_fields:
        if field in loan_data:
            key_fields[field] = loan_data[field]
    
    return {
        "field_count": field_count,
        "loan_number": loan_number,
        "file_path": str(file_path),
        "key_fields": key_fields,
        "loan_id": loan_id,
        "message": f"Full loan entity saved to file. Use read_file tool on '{file_path}' to see all fields."
    }


@tool
def write_loan_field(loan_id: str, field_id: str, value: Any) -> dict[str, Any]:
    """Write a value to a single field in an Encompass loan.

    Use this tool to update loan field values in Encompass. Make sure you have
    the correct field ID and that the value type matches what Encompass expects.

    Args:
        loan_id: The Encompass loan GUID
        field_id: The field ID to update (e.g., "4000" for Loan Amount)
        value: The value to write (string, number, etc. depending on field type)

    Returns:
        Dictionary with success status

    Example:
        >>> write_loan_field("loan-guid", "4000", 350000)
        {"success": True, "field_id": "4000", "value": 350000}
    """
    client = _get_encompass_client()
    success = client.write_field(loan_id, field_id, value)
    return {
        "success": success,
        "field_id": field_id,
        "value": value,
        "loan_id": loan_id,
    }


@tool
def download_loan_document(
    loan_id: str,
    attachment_id: str,
) -> dict[str, Any]:
    """Download a document attachment from an Encompass loan to a temporary file.

    This tool downloads a document from Encompass and saves it to a temporary file.
    The file path can then be passed to extract_document_data for AI extraction.

    Args:
        loan_id: The Encompass loan GUID
        attachment_id: The attachment entity ID to download

    Returns:
        Dictionary containing:
        - file_path: Path to the temporary file containing the document
        - file_size_bytes: Size of the downloaded document in bytes
        - file_size_kb: Size in kilobytes for readability
        - attachment_id: The attachment ID that was downloaded
        - loan_id: The loan ID it came from

    Example:
        >>> download_loan_document("loan-guid", "attachment-guid")
        {
            "file_path": "/tmp/encompass_doc_abc123.pdf",
            "file_size_bytes": 583789,
            "file_size_kb": 570.11,
            "attachment_id": "attachment-guid",
            "loan_id": "loan-guid"
        }
    """
    import logging
    import time
    
    logger = logging.getLogger(__name__)
    logger.info(f"[DOWNLOAD] Starting - Loan: {loan_id[:8]}..., Attachment: {attachment_id[:8]}...")
    
    start_time = time.time()
    client = _get_encompass_client()
    
    # Download the document
    document_bytes = client.download_attachment(loan_id, attachment_id)
    
    # Save to file (avoids putting binary data in message history)
    output_dir = _get_output_directory()
    file_path = output_dir / f'document_{attachment_id[:8]}_{int(time.time())}.pdf'
    
    with open(file_path, 'wb') as f:
        f.write(document_bytes)
    
    download_time = time.time() - start_time
    size_kb = len(document_bytes) / 1024
    logger.info(f"[DOWNLOAD] Success - {len(document_bytes):,} bytes ({size_kb:.2f} KB) saved to {file_path} in {download_time:.2f}s")
    
    return {
        "file_path": str(file_path),
        "file_size_bytes": len(document_bytes),
        "file_size_kb": round(size_kb, 2),
        "attachment_id": attachment_id,
        "loan_id": loan_id,
    }


@tool
def extract_document_data(
    file_path: str,
    extraction_schema: dict[str, Any],
    document_type: str = "Document",
) -> dict[str, Any]:
    """Extract structured data from a document using LandingAI.

    This tool uses AI to extract specific fields from a PDF document based on a schema
    you provide. Pass the file_path from download_loan_document result.

    Args:
        file_path: Path to the PDF file (from download_loan_document result)
        extraction_schema: JSON schema defining what to extract. Format:
            {
                "type": "object",
                "properties": {
                    "field_name": {
                        "type": "string|number|array",
                        "title": "Display Name",
                        "description": "What to extract"
                    }
                }
            }
        document_type: Label for the document type (e.g., "W2", "1003", "Bank Statement")

    Returns:
        Dictionary containing:
        - extracted_schema: The extracted data matching your schema
        - doc_type: The document type you specified
        - extraction_method: The method used (landingai-agentic)

    Example schema for W-2:
        {
            "type": "object",
            "properties": {
                "employer_name": {
                    "type": "string",
                    "title": "Employer Name",
                    "description": "Name of the employer from W-2"
                },
                "employee_name": {
                    "type": "string",
                    "title": "Employee Name",
                    "description": "Full name of the employee"
                },
                "wages": {
                    "type": "number",
                    "title": "Total Wages",
                    "description": "Total wages from box 1"
                }
            }
        }

    Example:
        >>> schema = {"type": "object", "properties": {...}}
        >>> download_result = download_loan_document(loan_id, attachment_id)
        >>> extract_document_data(download_result["file_path"], schema, "W2")
        {
            "extracted_schema": {
                "employer_name": "Acme Corp",
                "employee_name": "John Doe",
                "wages": 75000
            },
            "doc_type": "W2",
            "extraction_method": "landingai-agentic"
        }
    """
    import logging
    import time
    import os
    
    logger = logging.getLogger(__name__)
    
    # Read the file
    with open(file_path, 'rb') as f:
        document_bytes = f.read()
    
    file_size_kb = len(document_bytes) / 1024
    logger.info(f"[EXTRACT] Starting - Type: {document_type}, File: {os.path.basename(file_path)}, Size: {file_size_kb:.2f} KB")
    
    start_time = time.time()
    client = _get_encompass_client()
    
    filename = f"{document_type.lower().replace(' ', '_')}_document.pdf"

    # Extract data using LandingAI
    result = client.extract_document_data(
        document_bytes=document_bytes,
        schema=extraction_schema,
        doc_type=document_type,
        filename=filename,
    )
    
    extraction_time = time.time() - start_time
    extracted_data = result.get("extracted_schema", {})
    
    logger.info(f"[EXTRACT] Success - {len(extracted_data)} fields in {extraction_time:.2f}s")

    return result


# =============================================================================
# AGENT CONFIGURATION
# =============================================================================

# System prompt for the DrawDoc-AWM agent
drawdoc_instructions = """You are an Encompass API testing assistant. Your ONLY job is to TEST Encompass READ operations.

CRITICAL RULES - FOLLOW THESE EXACTLY:
- If you see ANY loan IDs, field IDs, or attachment IDs in a message → IMMEDIATELY create todos and run tests
- DO NOT ask for clarification or more information
- DO NOT create documentation, markdown files, or guides  
- DO NOT use write_file, edit_file, or write_loan_field tools
- We are ONLY testing READ operations (read fields, download documents, extract data)

IMMEDIATE ACTIONS when you see loan/attachment IDs:
1. Use write_todos to create 5-phase test plan (see planner_prompt.md)
2. Execute Phase 1 immediately
3. Execute ALL 5 READ tools in order:
   Phase 1: read_loan_fields(loan_id, field_ids) → read specific loan fields
   Phase 2: get_loan_documents(loan_id, max_documents=5) → lists documents, saves full list to CSV
   Phase 3: get_loan_entity(loan_id) → gets loan data, saves full data to JSON file
   Phase 4: download_loan_document(loan_id, attachment_id) → download doc, returns file_path
   Phase 5: extract_document_data(file_path, extraction_schema, doc_type) → extract with AI

IMPORTANT NOTES:
- Large responses are automatically saved to files to avoid token limits
- Tools return file_path for saved data - you can read files if needed with read_file tool
- Pass the file_path from download_loan_document result to extract_document_data

If message has loan IDs = START TESTING IMMEDIATELY. Do not ask questions."""

# Load local planning prompt if it exists
planner_prompt_file = Path(__file__).parent / "planner_prompt.md"
planning_prompt = planner_prompt_file.read_text() if planner_prompt_file.exists() else None

# Define the default initial message for LangGraph Studio
# This message will automatically trigger the agent to test the Encompass tools
DEFAULT_INITIAL_MESSAGE = f"""Test the Encompass integration tools. Please:

1. Read loan fields from loan {TEST_LOAN_ID}
   - Get fields: {', '.join(TEST_FIELD_IDS)} (Loan Amount, Borrower First Name, Borrower Last Name, Loan Number)

2. Get loan documents list from loan {TEST_LOAN_WITH_DOCS}
   - Show all documents and attachments available

3. Get complete loan entity from loan {TEST_LOAN_ID}
   - Show field count and loan number

4. Download the W-2 document
   - Loan: {TEST_LOAN_WITH_DOCS}
   - Attachment: {TEST_ATTACHMENT_ID}

5. Extract data from the W-2 document
   - Extract: employer name, employee name, and tax year

Create a plan and execute each step, showing me the results."""

# Create the DrawDoc-AWM agent with Encompass tools
agent = create_deep_agent(
    agent_type="DrawDoc-AWM",
    system_prompt=drawdoc_instructions,
    planning_prompt=planning_prompt,
    tools=[
        read_loan_fields,
        get_loan_documents,
        get_loan_entity,
        write_loan_field,
        download_loan_document,
        extract_document_data,
    ],
)

# =============================================================================
# TEST/DEMO FUNCTIONS
# =============================================================================


def test_encompass_tools():
    """Test the Encompass tools with sample data using hardcoded test values."""
    print("=" * 80)
    print("Testing DrawDoc-AWM Agent with Encompass Tools")
    print("=" * 80)
    print()
    print("Using test data:")
    print(f"  TEST_LOAN_ID: {TEST_LOAN_ID}")
    print(f"  TEST_LOAN_WITH_DOCS: {TEST_LOAN_WITH_DOCS}")
    print(f"  TEST_ATTACHMENT_ID: {TEST_ATTACHMENT_ID}")
    print(f"  TEST_FIELD_IDS: {TEST_FIELD_IDS}")
    print()

    # Test 1: Read fields
    print("Test 1: Reading loan fields...")
    try:
        result = read_loan_fields.invoke(
            {"loan_id": TEST_LOAN_ID, "field_ids": TEST_FIELD_IDS}
        )
        print(f"✅ Success: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Test 2: Get loan documents
    print("Test 2: Getting loan documents list...")
    try:
        result = get_loan_documents.invoke({"loan_id": TEST_LOAN_WITH_DOCS, "max_documents": 5})
        print(f"✅ Success: Found {result['total_documents']} documents with {result['total_attachments']} attachments")
        print(f"   Full list saved to: {result.get('file_path', 'N/A')}")
        if result.get('sample_documents'):
            print(f"   First document: {result['sample_documents'][0].get('title', 'N/A')}")
            print(f"   Sample shows {result['showing_first']} of {result['total_documents']} documents")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Test 3: Get loan entity
    print("Test 3: Getting complete loan entity...")
    try:
        result = get_loan_entity.invoke({"loan_id": TEST_LOAN_ID})
        print(f"✅ Success: Retrieved {result['field_count']} fields")
        print(f"   Loan Number: {result.get('loan_number', 'N/A')}")
        print(f"   Full data saved to: {result.get('file_path', 'N/A')}")
        if result.get('key_fields'):
            print(f"   Key fields: {list(result['key_fields'].keys())}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Test 4: Download document
    print("Test 4: Downloading document...")
    try:
        result = download_loan_document.invoke(
            {
                "loan_id": TEST_LOAN_WITH_DOCS,
                "attachment_id": TEST_ATTACHMENT_ID,
            }
        )
        print(f"✅ Success: Downloaded {result['file_size_bytes']} bytes ({result['file_size_kb']} KB)")
        if "file_path" in result:
            print(f"   Saved to: {result['file_path']}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Test 5: Extract data
    print("Test 5: Extracting data with LandingAI...")
    try:
        # First download the document
        doc_result = download_loan_document.invoke(
            {
                "loan_id": TEST_LOAN_WITH_DOCS,
                "attachment_id": TEST_ATTACHMENT_ID,
            }
        )

        # Use the pre-configured W-2 schema
        extract_result = extract_document_data.invoke(
            {
                "file_path": doc_result["file_path"],
                "extraction_schema": TEST_W2_SCHEMA,
                "document_type": "W2",
            }
        )

        print(f"✅ Success: Extracted data:")
        import json

        print(json.dumps(extract_result.get("extracted_schema", {}), indent=2))
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
    print()

    print("=" * 80)
    print("Tests complete!")
    print("=" * 80)


def demo_agent_workflow():
    """Demonstrate the agent workflow with a complete 5-phase test using test data."""
    from langchain_core.messages import HumanMessage

    print("=" * 80)
    print("Demo: Agent Workflow - Complete 5-Phase Encompass Test")
    print("=" * 80)
    print()
    print("Using test data:")
    print(f"  TEST_LOAN_ID: {TEST_LOAN_ID}")
    print(f"  TEST_LOAN_WITH_DOCS: {TEST_LOAN_WITH_DOCS}")
    print(f"  TEST_ATTACHMENT_ID: {TEST_ATTACHMENT_ID}")
    print(f"  TEST_FIELD_IDS: {TEST_FIELD_IDS}")
    print()

    # Define the comprehensive task using test constants
    task = f"""Test all Encompass READ operations. Execute the complete 5-phase test:

Phase 1: Read loan fields from loan {TEST_LOAN_ID}
- Get fields: {', '.join(TEST_FIELD_IDS)} (Loan Amount, First Name, Last Name, Loan Number)

Phase 2: Get loan documents list from loan {TEST_LOAN_WITH_DOCS}
- Show all documents and attachments available

Phase 3: Get complete loan entity from loan {TEST_LOAN_ID}
- Show field count and loan number

Phase 4: Download the W-2 document
- Loan: {TEST_LOAN_WITH_DOCS}
- Attachment: {TEST_ATTACHMENT_ID}

Phase 5: Extract data from the W-2 document
- Extract: employer name, employee name, and tax year

Create a plan with write_todos and execute all 5 phases, showing results for each."""

    print(f"Task: {task}")
    print()
    print("Invoking agent...")
    print()

    # Invoke the agent
    result = agent.invoke({"messages": [HumanMessage(content=task)]})

    # Print the results
    print("=" * 80)
    print("Agent Response:")
    print("=" * 80)
    for message in result["messages"]:
        if hasattr(message, "content") and message.content:
            print(f"\n{message.type}: {message.content}")
    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="DrawDoc-AWM Agent - Document Drawing and Annotation Agent with Encompass Integration"
    )
    parser.add_argument("--test-tools", action="store_true", help="Test individual tools")
    parser.add_argument("--demo", action="store_true", help="Run agent workflow demo")

    args = parser.parse_args()

    if args.test_tools:
        test_encompass_tools()
    elif args.demo:
        demo_agent_workflow()
    else:
        print("DrawDoc-AWM Agent")
        print("=" * 80)
        print()
        print("This agent provides Encompass document processing capabilities.")
        print()
        print("Available commands:")
        print("  --test-tools  Test individual Encompass tools (5 comprehensive READ tests)")
        print("  --demo        Run complete 5-phase agent workflow with planning")
        print()
        print("5-Phase Test Flow:")
        print("  Phase 1: read_loan_fields       - Read specific field values")
        print("  Phase 2: get_loan_documents     - List all documents and attachments")
        print("  Phase 3: get_loan_entity        - Get complete loan data")
        print("  Phase 4: download_loan_document - Download document attachments")
        print("  Phase 5: extract_document_data  - AI extraction of structured data")
        print()
        print("Additional tools:")
        print("  - write_loan_field - Write/update field values (not used in READ tests)")
        print()
        print("Configuration:")
        print("  - API credentials are loaded from .env file")
        print("  - Test data (loan IDs, attachment IDs) defined in TEST_* constants")
        print()
        print("Example usage:")
        print("  python drawdoc_agent.py --test-tools  # Run 5 individual tool tests")
        print("  python drawdoc_agent.py --demo        # Run full workflow with agent")
        print()
