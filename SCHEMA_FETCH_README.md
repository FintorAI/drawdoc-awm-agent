# Encompass Loan Schema Fetcher

This script fetches the Encompass loan schema and analyzes field mappings against your test data.

## Prerequisites

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure your `.env` file:**
   
   Ensure you have the following in your `.env` file:
   ```env
   ENCOMPASS_ACCESS_TOKEN=your_actual_token_here
   ENCOMPASS_API_BASE_URL=https://api.elliemae.com
   ENCOMPASS_INSTANCE_ID=your_instance_id  # Optional
   ```

## Usage

Run the script:

```bash
python fetch_loan_schema.py
```

## What It Does

1. **Fetches the loan schema** from Encompass API v3
2. **Saves the schema** to `encompass_loan_schema.json`
3. **Analyzes field mappings** between your test data and the schema
4. **Generates a report** in `field_mapping_analysis.json`

## Output Files

### 1. `encompass_loan_schema.json`
Full JSON schema from Encompass showing all available fields, their types, and structure.

### 2. `field_mapping_analysis.json`
Analysis of which fields from `test_loan_data_happy_path_simple.json` exist in the schema:

```json
{
  "found": [
    {
      "field_id": "4000",
      "field_name": "Borrower First Name",
      "category": "borrower_fields",
      "expected_value": "ATHENA",
      "schema_location": "applications[].borrower",
      "schema_path": "applications[].borrower.firstName",
      "schema_definition": { ... }
    }
  ],
  "not_found": [
    {
      "field_id": "1172",
      "field_name": "Loan Type",
      "category": "mvp_eligibility",
      "note": "Not found in schema - may be custom field"
    }
  ],
  "summary": {
    "total_fields": 50,
    "found_count": 45,
    "not_found_count": 5
  }
}
```

## Troubleshooting

### Error: "ENCOMPASS_ACCESS_TOKEN not found"
- Check that your `.env` file exists in the project root
- Verify the token is correctly set (no quotes, no spaces)

### Error: "401 Unauthorized"
- Your access token may be expired
- Refresh your token using Encompass authentication flow

### Error: "404 Not Found"
- Check your `ENCOMPASS_API_BASE_URL` is correct
- Verify you have access to the v3 API

## Using the Schema

Once you have the schema, you can:

1. **Identify correct field paths** for updating `loan_details_d47b774f.json`
2. **Validate field IDs** from your test data
3. **Understand data types** required for each field
4. **Map legacy field IDs** to current schema properties

## Next Steps

After running this script:

1. Review `field_mapping_analysis.json` to see which fields were found
2. For "not_found" fields, search the schema manually or check if they're custom fields
3. Use the schema paths to update your loan data file correctly
4. Create a mapping script to automatically populate loan data from test benchmarks

## Example: Finding a Field

If you need to find where "Loan Amount" (field 1109) is located:

```python
# Search in encompass_loan_schema.json
# You might find it at:
# - properties.loanAmount (direct)
# - properties.loan.amount (nested)
# - customFields[].fieldName="1109" (custom)
```

## Support

For Encompass API documentation:
- https://developer.elliemae.com/
- V3 Schema Docs: https://developer.elliemae.com/api/v3/


