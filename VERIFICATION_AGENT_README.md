# Verification Agent - Quick Start Guide

## What It Does

The Verification Agent compares field values extracted from loan documents (prep output) against current Encompass values and corrects any mismatches.

**Key Feature:** 🔒 **DRY RUN MODE** - Test safely on production without making changes!

## Quick Start

### 1. Pull Latest Changes
```powershell
git pull origin main
```

### 2. Run Test (Safe - Dry Run Mode)
```bash
python test_verification_agent.py
```

This will:
- ✅ Compare prep output values vs Encompass values
- ✅ Identify corrections needed
- ✅ **NOT write** anything to Encompass (dry run mode)
- ✅ Save results to `verification_results.json`
- ✅ Save detailed logs to `logs/verification_test_*.log`

### 3. Review Results

**Console Output:**
```
SUMMARY REPORT
  Loan ID: 387596ee-7090-47ca-8385-206e22c9c9da
  Corrections identified: 5
  Status: ✓ Success

📁 Results saved to: verification_results.json
📝 Detailed logs saved to: logs/verification_test_20250115_143045.log
```

**JSON Results:**
```json
{
  "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
  "corrections_made": [
    {
      "field_id": "4002",
      "field_name": "Borrower Last Name",
      "source_document": "ID",
      "corrected_value": "Sorensen",
      "reason": "Prep shows 'Sorensen' but Encompass has 'Sorenson'",
      "dry_run": true
    }
  ],
  "total_corrections": 5
}
```

## Workflow

```
Prep Output (CORRECT values) → Verification Agent
                                      ↓
                         Fetch Encompass Values
                                      ↓
                              Compare Values
                                      ↓
                    Mismatch? → Track Correction
                                      ↓
                        Generate Report
```

### Input: Prep Output
```json
{
  "loan_id": "387596ee-...",
  "results": {
    "field_mappings": {
      "4002": "Sorensen",  ← CORRECT value from documents
      "4000": "Alva",
      "36": "Alva Scott"
    }
  }
}
```

### Process
1. For each field in `field_mappings`
2. Fetch current Encompass value via API
3. Compare prep value (correct) vs Encompass value (potentially wrong)
4. If mismatch → Track correction
5. Generate report with all corrections

### Output: Corrections Report
- All mismatches identified
- Corrections tracked with reasons
- Ready to apply (when dry run disabled)

## Dry Run Mode (Default)

**Always enabled by default** for safety on production!

### How to Use

**Option 1: Default (Recommended)**
```bash
python test_verification_agent.py
# Automatically runs in dry run mode
```

**Option 2: Explicitly Enable**
```powershell
$env:DRY_RUN="true"
python test_verification_agent.py
```

**Option 3: In Code**
```python
result = run_verification(
    loan_id=loan_id,
    prep_output=prep_output,
    dry_run=True
)
```

### What You See in Dry Run

Console shows corrections but doesn't write:
```
🔍 DRY RUN MODE ENABLED - No changes will be written to Encompass

🔍 DRY RUN - Field Correction (NOT written to Encompass)
Loan ID:         387596ee-7090-47ca-8385-206e22c9c9da
Field ID:        4002
Corrected Value: Sorensen
Finding:         Last name spelling mismatch
Reason:          Prep shows 'Sorensen' but Encompass has 'Sorenson'
```

## Apply Corrections (Production Mode)

**Only after reviewing dry run results!**

```bash
# Disable dry run
python test_verification_agent.py --no-dry-run
```

Or:
```powershell
$env:DRY_RUN="false"
python test_verification_agent.py
```

Now corrections will be **actually written** to Encompass.

## File Locations

### Input
- `data/prep_output.json` - Field values extracted from documents

### Output
- `verification_results.json` - Structured validation results
- `logs/verification_test_*.log` - Detailed debug logs (timestamped)

### Configuration
- `config/field_document_mapping.py` - Field to document mappings
- `config/sop_rules.json` - SOP rules by page

## Example Run

```bash
python test_verification_agent.py
```

```
================================================================================
VERIFICATION SUB-AGENT TEST
================================================================================

📝 Detailed logs will be saved to: logs/verification_test_20250115_143045.log

⚠️  DRY RUN MODE ENABLED (set DRY_RUN=false to disable)

[1] Loading test prep output...
[OK] Loaded prep output for loan: 387596ee-7090-47ca-8385-206e22c9c9da
  - Documents processed: 17
  - Total documents: 172

[2] Field mapping loaded:
  - Total fields: 193
  - SOP pages referenced: 67

[3] Running verification on loan 387596ee-7090-47ca-8385-206e22c9c9da...

[4] Parsing corrections from messages...
  ✓ Found 5 corrections

[5] Tool usage:
  • get_missing_field_value: 18 times
  • compare_prep_vs_encompass_value: 18 times
  • write_corrected_field: 5 times

================================================================================
SUMMARY REPORT
================================================================================
  Loan ID: 387596ee-7090-47ca-8385-206e22c9c9da
  Documents processed: 17/172
  Fields in prep output: 18
  Corrections identified: 5
  Agent messages: 49
  Status: ✓ Success

📁 Results saved to: verification_results.json
📝 Detailed logs saved to: logs/verification_test_20250115_143045.log
```

## Troubleshooting

### Issue: corrections_made is empty
- Check log file for ToolMessage details
- Verify `write_corrected_field` was called (see tool usage)
- Review agent messages in log file

### Issue: Can't connect to Encompass
- Check `.env` file has credentials
- Verify `ENCOMPASS_ACCESS_TOKEN` is set
- Check API base URL is correct

### Issue: Field not in prep output
- Verify field exists in `data/prep_output.json`
- Check field_mappings section has the field ID
- Ensure prep agent successfully extracted the field

### Issue: Want more detail
- Check log file: `logs/verification_test_*.log`
- All debug output is saved there
- Includes full agent conversation and parsing details

## Safety Checklist

Before running in production mode:

- [ ] Tested with dry run on production data
- [ ] Reviewed all corrections in `verification_results.json`
- [ ] Verified corrections are accurate
- [ ] Checked log file for any warnings
- [ ] Ready to apply changes

## Key Commands

```bash
# Safe testing (default)
python test_verification_agent.py

# Actually write to Encompass (use with caution!)
python test_verification_agent.py --no-dry-run

# View latest log
notepad logs\verification_test_*.log
```

## Architecture

**Agent:** `agents/verification_agent.py`
- Uses `create_deep_agent` from copilotagent
- Orchestrates verification workflow

**Tools:**
- `get_missing_field_value` - Fetch current Encompass values
- `compare_prep_vs_encompass_value` - Compare prep vs Encompass
- `write_corrected_field` - Update Encompass (respects dry run)

**Configuration:**
- Field mappings from CSV
- SOP rules from JSON
- Credentials from `.env`

## Support

For more technical details, see `TECHNICAL_DETAILS.md`

For issues:
1. Check log file for errors
2. Review `verification_results.json`
3. Verify credentials in `.env`
4. Check prep output format

---

**Remember:** Always test with dry run first! 🔒

