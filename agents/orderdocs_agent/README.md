# OrderDocs Agent

This agent reads field values from Encompass based on document types specified in the input.

## How It Works

1. **Reads document types from input** (e.g., `["ID", "Title Report"]`)
2. **Looks up field IDs from CSV** - Uses `data/DrawingDoc Verifications - Sheet1.csv` to find which field IDs correspond to each document type
3. **Reads field values from Encompass** - Fetches the current values for those field IDs
4. **Returns JSON output** - Returns all field values (including empty ones) in format: `{"field_id": "value"}`

## Example

**Input:**
```json
{
  "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
  "document_types": ["ID"]
}
```

**Output:**
```json
{
  "4000": "Jane",
  "4001": "Doe",
  "4002": "Smith",
  "36": "",
  "66": ""
}
```

## Usage

### Method 1: Using JSON file
```bash
cd agents/orderdocs_agent
source ../../venv/bin/activate
python orderdocs_agent.py --json-file example_input.json
```

### Method 2: Using JSON string
```bash
python orderdocs_agent.py --json '{"loan_id":"...","document_types":["ID"]}'
```

## CSV File Structure

The agent uses `data/DrawingDoc Verifications - Sheet1.csv` which has columns:
- **Name**: Field name (e.g., "Borrower First Name")
- **ID**: Field ID (e.g., "4000")
- **Primary document**: Primary document type where this field should be found
- **Secondary documents**: Other document types where this field can be found

## Notes

- Returns **all** field values, even if empty/None
- Field IDs are matched from both Primary and Secondary document columns
- Document type matching is case-insensitive and partial (e.g., "ID" matches "ID Customer Identification Documentation")

