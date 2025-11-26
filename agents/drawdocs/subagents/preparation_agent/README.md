# Preparation Agent

This folder contains the complete Preparation Sub-Agent for Encompass loan document processing.

## Overview

The Preparation Agent:
1. Retrieves all documents for a given loan
2. Downloads each document
3. Extracts entities using LandingAI OCR
4. Maps extracted fields to Encompass field IDs
5. Returns extracted data as a dictionary (does NOT write to Encompass)

## Files

### Core Scripts
- **`preparation_agent.py`** - Main agent script with all tools and workflow
- **`extraction_schemas.py`** - JSON schemas for extracting structured data from different document types
- **`field_mappings.py`** - Maps extracted document fields to Encompass field IDs

### Data Files
- **`DrawingDoc Verifications.csv`** - Source of truth for document types and field mappings

### Example Files
- **`example_input.json`** - Example JSON input for single document type
- **`example_input_multiple.json`** - Example JSON input for multiple document types
- **`preparation_input_schema.json`** - JSON schema defining the expected input format
- **`example_programmatic_usage.py`** - Example of how to call the agent programmatically
- **`process_5_documents_demo.py`** - Demo script for processing documents

### Configuration
- **`requirements.txt`** - Python dependencies
- **`env.example`** - Template for environment variables (copy to `.env` and fill in your credentials)

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```bash
   cp env.example .env
   # Edit .env with your API credentials
   ```

3. **Required environment variables:**
   - `ENCOMPASS_ACCESS_TOKEN` - Encompass API access token
   - `ENCOMPASS_API_BASE_URL` - Encompass API base URL (default: https://api.elliemae.com)
   - `ENCOMPASS_USERNAME` - Encompass username
   - `ENCOMPASS_PASSWORD` - Encompass password
   - `ENCOMPASS_CLIENT_ID` - Encompass client ID
   - `ENCOMPASS_CLIENT_SECRET` - Encompass client secret
   - `ENCOMPASS_INSTANCE_ID` - Encompass instance ID
   - `ENCOMPASS_SUBJECT_USER_ID` - Encompass subject user ID
   - `LANDINGAI_API_KEY` - LandingAI API key for OCR extraction

## Usage

### Command Line

**From JSON file:**
```bash
python preparation_agent.py --json-file example_input_multiple.json
```

**From JSON string:**
```bash
python preparation_agent.py --json '{"loan_id":"387596ee-7090-47ca-8385-206e22c9c9da","document_types":["W-2","ID"]}'
```

**Demo mode:**
```bash
python preparation_agent.py --demo
```

### Programmatic Usage

```python
from preparation_agent import process_from_json

input_data = {
    "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
    "document_types": ["W-2", "ID", "Title Report"]
}

result = process_from_json(input_data)
print(result)
```

## Input Format

```json
{
  "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
  "document_types": ["W-2", "ID", "Title Report", "Appraisal Report"]
}
```

- **`loan_id`** (required): The Encompass loan GUID
- **`document_types`** (optional): Array of document type names to extract from. If omitted, processes all documents with extraction schemas.

## Output Format

```json
{
  "loan_id": "...",
  "total_documents_found": 167,
  "documents_processed": 3,
  "results": {
    "extracted_entities": {
      "W-2": {
        "employee_first_name": "John",
        "employee_last_name": "Doe"
      },
      "ID": {
        "first_name": "John",
        "last_name": "Doe"
      }
    },
    "field_mappings": {
      "4000": "John",
      "4002": "Doe",
      "4004": "Doe"
    }
  }
}
```

- **`extracted_entities`**: Organized by document type, contains all extracted fields
- **`field_mappings`**: Final prioritized mapping of Encompass field IDs to values (only includes fields with actual values)

## Supported Document Types

The agent supports extraction from these document types (based on `DrawingDoc Verifications.csv`):

- **W-2** / W2 / W-2 Form
- **ID** / Driver License / State ID
- **Title Report** / Prelim Title Report
- **Appraisal Report** / Appraisal
- **Final 1003** / Initial 1003 / 1003 form
- **Last LE** / LE / Loan Estimate
- **Closing Disclosure** / COC CD / Initial CD / Final CD
- **Trust Document** / Trust Agreement
- **Purchase Agreement** / Purchase Contract
- **Aggregate Escrow Account Form**
- **2015 Itemization form**
- **HOI Policy** / Evidence of Insurance
- **Mortgage Insurance details** / Mortgage Insurance Certificate
- **Loan file**
- **FHA Case assignment document**
- **Escrow wire instruction**
- **Credit report**

## Field Extraction Priority

The agent prioritizes fields from preferred documents when available:
- Field 4000 (Borrower First Name) → prefers "ID" document
- Field 610 (Escrow Company Name) → prefers "Title Report"
- Field 356 (Appraised Value) → prefers "Appraisal Report"

If a preferred document is not available, the field is extracted from any available document.

## Safety

- **Writes are DISABLED by default** - The agent only returns extracted data, it does NOT write to Encompass
- All operations are read-only
- Set `ENABLE_ENCOMPASS_WRITES=true` in `.env` only if you need write functionality (not recommended for production testing)

## Notes

- The agent filters out empty values from the output
- Only fields with actual extracted values are included in `field_mappings`
- Document type matching is case-insensitive and handles variations (e.g., "W-2 all years" matches "W-2")
- The agent processes all matching documents in the loan, not just one




