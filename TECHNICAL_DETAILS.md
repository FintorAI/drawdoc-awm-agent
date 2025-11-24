# Verification Agent - Technical Details

## Architecture Overview

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Verification Agent                       │
│  (agents/verification_agent.py)                             │
│  - Orchestrates workflow                                     │
│  - Uses create_deep_agent from copilotagent                 │
└─────────────────────────────────────────────────────────────┘
                           │
                           ├─► Tools (tools/verification_tools.py)
                           │   • compare_prep_vs_encompass_value
                           │   • write_corrected_field
                           │   • cross_check_field_with_sop
                           │
                           ├─► Field Lookup (tools/field_lookup_tools.py)
                           │   • get_missing_field_value
                           │   • get_field_id_from_name
                           │
                           ├─► Configuration (config/)
                           │   • field_document_mapping.py (CSV parser)
                           │   • sop_rules.py (SOP JSON loader)
                           │
                           └─► Encompass API (copilotagent.EncompassConnect)
                               • Read field values
                               • Write field corrections
```

## Workflow Implementation

### Step 1: Load Prep Output
```python
prep_output = {
  "loan_id": "...",
  "results": {
    "field_mappings": {
      "4002": "Sorensen",  # Correct value
      "4000": "Alva"
    }
  }
}
```

### Step 2: Agent Processing
```python
for field_id, prep_value in field_mappings.items():
    # Get current Encompass value
    encompass_value = get_missing_field_value(loan_id, field_id)
    
    # Compare
    comparison = compare_prep_vs_encompass_value(
        field_id, prep_value, encompass_value, field_mapping
    )
    
    # Correct if needed
    if comparison['needs_correction']:
        write_corrected_field(
            loan_id, field_id, prep_value, reason, finding
        )
```

### Step 3: Results Extraction

**Challenge:** `create_deep_agent` returns:
```python
{
  "messages": [...],  # All conversation
  "todos": [],
  "files": []
}
```

**NOT:**
```python
{
  "loan_id": "...",
  "corrections_made": [...]  # ← Not directly accessible
}
```

**Solution:** Parse corrections from ToolMessages:
```python
for msg in result['messages']:
    if type(msg).__name__ == "ToolMessage":
        content = msg.content
        if isinstance(content, dict) and "field_id" in content:
            corrections_list.append(content)
```

## Tool Details

### compare_prep_vs_encompass_value

**Purpose:** Compare two values and determine if correction needed

**Input:**
```python
{
  "field_id": "4002",
  "prep_value": "Sorensen",      # Correct
  "encompass_value": "Sorenson",  # Wrong
  "field_mapping": {...}
}
```

**Output:**
```python
{
  "match": False,
  "needs_correction": True,
  "prep_value": "Sorensen",
  "encompass_value": "Sorenson",
  "finding": "Field mismatch",
  "reason": "Prep shows 'Sorensen' but Encompass has 'Sorenson'"
}
```

**Logic:**
- Normalizes both values (lowercase, strip whitespace)
- Case-insensitive comparison
- Returns detailed mismatch information

### write_corrected_field

**Purpose:** Write correction to Encompass (or simulate in dry run)

**Input:**
```python
{
  "loan_id": "387596ee-...",
  "field_id": "4002",
  "corrected_value": "Sorensen",
  "reason": "Document mismatch",
  "finding": "Prep vs Encompass mismatch"
}
```

**Output (Dry Run):**
```python
{
  "field_id": "4002",
  "field_name": "Borrower Last Name",
  "source_document": "ID",
  "corrected_value": "Sorensen",
  "reason": "...",
  "finding": "...",
  "success": True,
  "dry_run": True,
  "timestamp": "2024-01-15 10:30:45"
}
```

**Dry Run Logic:**
```python
dry_run = os.getenv("DRY_RUN", "false").lower() in ("true", "1", "yes")

if dry_run:
    print("🔍 DRY RUN - NOT written to Encompass")
    success = True  # Simulated
else:
    client = _get_encompass_client()
    success = client.write_field(loan_id, field_id, corrected_value)
```

### get_missing_field_value

**Purpose:** Fetch current field value from Encompass

**Input:**
```python
{
  "loan_id": "387596ee-...",
  "field_id": "4002"
}
```

**Output:**
```python
{
  "field_id": "4002",
  "value": "Sorenson",  # Current Encompass value
  "found": True,
  "error": None
}
```

## Configuration Files

### field_document_mapping.py

Parses `DrawingDoc Verifications - Sheet1.csv`:

```python
FIELD_MAPPING = {
  "4002": {
    "field_id": "4002",
    "field_name": "Borrower First Name",
    "primary_document": "ID",
    "secondary_documents": ["1003", "Credit Report"],
    "sop_pages": ["20", "21"],
    "validation_rules": ["Must be exact match", "Required"]
  }
}
```

### sop_rules.py

Loads `sop_rules.json`:

```python
SOP_RULES = {
  "page_indexed_rules": {
    "20": {
      "fields": [...],
      "rules": ["Exact match required", "..."]
    }
  }
}
```

## State Management Issue

### Problem
The `VerificationState` TypedDict we defined is just a type hint:

```python
class VerificationState(TypedDict):
    loan_id: str
    corrections_made: NotRequired[list[dict]]
    # ...
```

This doesn't automatically populate `result["loan_id"]` or `result["corrections_made"]`.

### Why
`create_deep_agent` doesn't use this TypedDict. It returns its own structure with `messages`, `todos`, `files`.

### Solution
Parse data from messages and use input values:

```python
clean_result = {
    "loan_id": loan_id,  # From prep_output, not result
    "corrections_made": corrections_list,  # Parsed from messages
    "total_corrections": len(corrections_list)
}
```

## Logging System

### Setup
```python
logger, log_file = setup_logging()
# Creates: logs/verification_test_YYYYMMDD_HHMMSS.log
```

### Levels

**DEBUG (log file only):**
- ToolMessage contents
- Full prep output
- Parsing attempts
- Agent conversation

**INFO (log file + console):**
- Progress updates
- Corrections found
- Summary statistics

**WARNING (log file + console):**
- Parsing failures
- Missing data

**ERROR (log file + console):**
- Exceptions
- Stack traces

### File Handler
```python
# Detailed formatting
'%(asctime)s - %(levelname)s - %(message)s'
```

### Console Handler
```python
# Clean formatting
'%(message)s'
```

## Parsing Logic

### Challenge
Tool returns dict but may appear as:
1. Dict object in ToolMessage.content
2. String representation: `"{'field_id': '4002', ...}"`
3. JSON string: `'{"field_id": "4002", ...}'`
4. Formatted string: `"🔍 [DRY RUN] Would correct..."`

### Solution - Multi-Format Parser

```python
# Handle dict directly
if isinstance(content, dict):
    corrections_list.append(content)

# Handle formatted string
elif "[DRY RUN]" in content_str:
    # Parse: "field 4002 to 'Sorensen'"
    field_id = content_str.split("field ")[1].split(" to ")[0]
    value = content_str.split(" to '")[1].split("'")[0]

# Handle JSON string
elif "field_id" in content_str:
    try:
        data = json.loads(content_str)
        corrections_list.append(data)
    except:
        data = ast.literal_eval(content_str)
        corrections_list.append(data)
```

## Error Handling

### Command Error (Fixed)
**Problem:**
```python
return Command(
    update={"corrections_made": [record]},
    messages=[ToolMessage(...)]  # ← Not supported
)
```

**Solution:**
```python
return correction_record  # Return data directly
```

### Missing Field Values
```python
if not result.get("found"):
    logger.warning(f"Field {field_id} not found in Encompass")
    status = "unable_to_verify"
```

### Parsing Failures
```python
try:
    correction = parse_correction(content)
except Exception as e:
    logger.warning(f"Failed to parse: {e}")
    logger.debug(f"Content: {content}")
```

## Testing

### Unit Testing Tools
```python
# Test individual tools
python test_verification_agent.py --test-tools
```

### Integration Testing
```python
# Test full workflow
python test_verification_agent.py
```

### New Workflow Testing
```python
# Test comparison workflow
python test_verification_agent.py --test-new-workflow
```

## Performance Considerations

### Field Processing
- Sequential processing: ~1-2 seconds per field
- Includes Encompass API calls
- 18 fields ≈ 20-40 seconds total

### Optimization Opportunities
1. **Batch API calls** - Fetch multiple fields at once
2. **Parallel processing** - Process fields concurrently
3. **Caching** - Cache field mappings and SOP rules

### Current Approach
- Simple sequential processing
- Easy to debug
- Good enough for current scale

## Security

### Credentials
```python
# From .env file
ENCOMPASS_ACCESS_TOKEN=...
ENCOMPASS_CLIENT_ID=...
ENCOMPASS_CLIENT_SECRET=...
```

### Dry Run Protection
```python
# Default: safe mode
if os.getenv("DRY_RUN") is None:
    os.environ["DRY_RUN"] = "true"
```

### Logging
- Sensitive data may appear in logs
- `logs/` in `.gitignore`
- Don't commit log files

## Troubleshooting

### corrections_made is empty

**Check:**
1. Log file shows ToolMessages?
2. `write_corrected_field` called? (tool usage analysis)
3. Content type of ToolMessages (dict vs string)

**Debug:**
```python
logger.debug(f"ToolMessage content type: {type(content).__name__}")
logger.debug(f"Content: {content}")
```

### Agent times out

**Causes:**
- Encompass API slow/unreachable
- Too many fields
- Network issues

**Solutions:**
- Check Encompass connectivity
- Process fewer fields
- Increase timeout in agent config

### Values don't match but should

**Check:**
- Normalization logic (case, whitespace)
- Data types (string "123" vs int 123)
- Special characters

**Debug:**
```python
logger.debug(f"Prep value: '{prep_value}' ({type(prep_value)})")
logger.debug(f"Encompass value: '{encompass_value}' ({type(encompass_value)})")
```

## Maintenance

### Adding New Tools
1. Create tool function with `@tool` decorator
2. Add to `tools/__init__.py`
3. Add to agent's tools list
4. Update system prompt

### Updating Field Mappings
1. Edit CSV: `DrawingDoc Verifications - Sheet1.csv`
2. Reload: `FIELD_MAPPING` auto-loads on import
3. No code changes needed

### Updating SOP Rules
1. Run: `python scripts/preprocess_sop.py`
2. Regenerates `config/sop_rules.json`
3. Agent auto-loads on next run

## Future Enhancements

### Potential Improvements
1. **Batch API calls** - Faster field fetching
2. **Better state management** - Direct state access
3. **Parallel processing** - Multiple fields at once
4. **Retry logic** - Handle transient failures
5. **Progress bar** - Visual feedback
6. **Email reports** - Automated notifications
7. **Dashboard** - Web UI for results

### Current Limitations
1. Sequential processing only
2. No retry on failure
3. Manual result review
4. No automated deployment

---

For quick start and usage, see `VERIFICATION_AGENT_README.md`

