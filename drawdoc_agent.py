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

# Add local baseCopilotAgent source to path for development
baseCopilotAgent_path = Path(__file__).parent.parent.parent / "baseCopilotAgent" / "src"
if str(baseCopilotAgent_path) not in sys.path:
    sys.path.insert(0, str(baseCopilotAgent_path))

# Remove any cached imports
if 'copilotagent' in sys.modules:
    del sys.modules['copilotagent']
if 'copilotagent.encompass_connect' in sys.modules:
    del sys.modules['copilotagent.encompass_connect']

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
    import tempfile
    
    logger = logging.getLogger(__name__)
    logger.info(f"[DOWNLOAD] Starting - Loan: {loan_id[:8]}..., Attachment: {attachment_id[:8]}...")
    
    start_time = time.time()
    client = _get_encompass_client()
    
    # Download the document
    document_bytes = client.download_attachment(loan_id, attachment_id)
    
    # Save to temporary file (avoids putting binary data in message history)
    temp_file = tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False)
    temp_file.write(document_bytes)
    temp_file.close()
    
    download_time = time.time() - start_time
    size_kb = len(document_bytes) / 1024
    logger.info(f"[DOWNLOAD] Success - {len(document_bytes):,} bytes ({size_kb:.2f} KB) saved to {temp_file.name} in {download_time:.2f}s")
    
    return {
        "file_path": temp_file.name,
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
1. Use write_todos to create 3-phase test plan (read fields, download document, extract data)
2. Execute Phase 1 immediately
3. Execute using ONLY these 3 tools:
   - read_loan_fields(loan_id, field_ids)
   - download_loan_document(loan_id, attachment_id) → returns file_path
   - extract_document_data(file_path, extraction_schema, doc_type)

IMPORTANT: Pass the file_path from download_loan_document result to extract_document_data.

If message has loan IDs = START TESTING IMMEDIATELY. Do not ask questions."""

# Load local planning prompt if it exists
planner_prompt_file = Path(__file__).parent / "planner_prompt.md"
planning_prompt = planner_prompt_file.read_text() if planner_prompt_file.exists() else None

# Define the default initial message for LangGraph Studio
# This message will automatically trigger the agent to test the Encompass tools
DEFAULT_INITIAL_MESSAGE = f"""Test the Encompass integration tools. Please:

1. Read loan fields from loan {TEST_LOAN_ID}
   - Get fields: {', '.join(TEST_FIELD_IDS)} (Loan Amount, Borrower First Name, Borrower Last Name, Loan Number)

2. Download the W-2 document
   - Loan: {TEST_LOAN_WITH_DOCS}
   - Attachment: {TEST_ATTACHMENT_ID}

3. Extract data from the W-2 document
   - Extract: employer name, employee name, and tax year

Create a plan and execute each step, showing me the results."""

# Create the DrawDoc-AWM agent with Encompass tools
agent = create_deep_agent(
    agent_type="DrawDoc-AWM",
    system_prompt=drawdoc_instructions,
    planning_prompt=planning_prompt,
    tools=[
        read_loan_fields,
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

    # Test 2: Download document
    print("Test 2: Downloading document...")
    try:
        result = download_loan_document.invoke(
            {
                "loan_id": TEST_LOAN_WITH_DOCS,
                "attachment_id": TEST_ATTACHMENT_ID,
                "save_to_memory": False,  # Save to temp file
            }
        )
        print(f"✅ Success: Downloaded {result['document_bytes_length']} bytes")
        if "file_path" in result:
            print(f"   Saved to: {result['file_path']}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Test 3: Extract data
    print("Test 3: Extracting data with LandingAI...")
    try:
        # First download the document
        doc_result = download_loan_document.invoke(
            {
                "loan_id": TEST_LOAN_WITH_DOCS,
                "attachment_id": TEST_ATTACHMENT_ID,
                "save_to_memory": True,
            }
        )

        # Use the pre-configured W-2 schema
        extract_result = extract_document_data.invoke(
            {
                "document_source": {"base64_data": doc_result["base64_data"]},
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
    """Demonstrate the agent workflow with a complete document processing example using test data."""
    from langchain_core.messages import HumanMessage

    print("=" * 80)
    print("Demo: Agent Workflow - Process W-2 Document")
    print("=" * 80)
    print()
    print("Using test data:")
    print(f"  Loan: {TEST_LOAN_WITH_DOCS}")
    print(f"  Attachment: {TEST_ATTACHMENT_ID}")
    print()

    # Define the task using test constants
    task = f"""Process the W-2 document from loan {TEST_LOAN_WITH_DOCS}.
    
    Steps:
    1. Download the document with attachment ID: {TEST_ATTACHMENT_ID}
    2. Extract the employer name, employee name, and tax year
    3. Show me the extracted data
    
    Use the tools available to complete this task."""

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
        print("  --test-tools  Test individual Encompass tools")
        print("  --demo        Run a complete agent workflow demo")
        print()
        print("Available tools:")
        print("  1. read_loan_fields      - Read field values from Encompass loans")
        print("  2. write_loan_field      - Write/update field values in Encompass")
        print("  3. download_loan_document - Download documents from Encompass")
        print("  4. extract_document_data  - Extract data from documents with AI")
        print()
        print("Configuration:")
        print("  - API credentials are loaded from .env file")
        print("  - Loan IDs and test data are provided as inputs to tools/graph")
        print()
        print("Example usage:")
        print("  python drawdoc_agent.py --test-tools")
        print("  python drawdoc_agent.py --demo")
        print()
