# Orchestrator Agent

The Orchestrator Agent manages the sequential execution of three sub-agents for loan document processing and verification:

1. **Preparation Agent**: Extracts field values from loan documents
2. **Verification Agent**: Verifies extracted values against Encompass and corrects mismatches
3. **Orderdocs Agent**: Checks that all required fields are present

## Features

- **Automatic Demo Mode**: Runs in safe demo mode by default (no actual writes to Encompass)
- **Retry Logic**: Automatic retry with exponential backoff for failed agents
- **Comprehensive Reporting**: Generates both JSON and human-readable summaries
- **User Prompt Interpretation**: Flexible control via natural language prompts
- **Correction Overlay**: In demo mode, simulates post-correction state for orderdocs

## Quick Start

### Basic Usage

```python
from orchestrator import run_orchestrator

# Run with all defaults (demo mode)
results = run_orchestrator(
    loan_id="387596ee-7090-47ca-8385-206e22c9c9da"
)

# Access summary
print(results["summary_text"])
```

### Command Line

```bash
# Demo mode (default - no actual writes)
python orchestrator/orchestrator_agent.py \
  --loan-id "387596ee-7090-47ca-8385-206e22c9c9da" \
  --output results.json

# With custom prompt
python orchestrator/orchestrator_agent.py \
  --loan-id "387596ee-7090-47ca-8385-206e22c9c9da" \
  --prompt "Focus on borrower name fields" \
  --output results.json

# Production mode (⚠️ CAUTION - actually writes to Encompass)
python orchestrator/orchestrator_agent.py \
  --loan-id "387596ee-7090-47ca-8385-206e22c9c9da" \
  --production \
  --output results.json
```

## Architecture

### Execution Flow

```
┌─────────────────────┐
│  Orchestrator       │
│  Agent              │
└──────┬──────────────┘
       │
       ├─► 1. Preparation Agent
       │    ├─ Downloads documents
       │    ├─ Extracts entities with OCR
       │    └─ Maps to field IDs
       │    
       ├─► 2. Verification Agent (uses prep output)
       │    ├─ Compares prep values vs Encompass
       │    ├─ Identifies discrepancies
       │    └─ Writes corrections (or logs in demo mode)
       │    
       └─► 3. Orderdocs Agent (uses prep + verification)
            ├─ Reads current field values
            ├─ Overlays corrections (in demo mode)
            └─ Reports completeness
```

### Demo Mode vs Production Mode

#### Demo Mode (Default)
- `DRY_RUN=true` environment variable set automatically
- Verification agent **logs** corrections but doesn't write to Encompass
- Orderdocs agent **simulates** post-correction state by overlaying corrections
- Safe for testing on production data

#### Production Mode
- `DRY_RUN=false`
- Verification agent **actually writes** corrections to Encompass
- Orderdocs agent reads actual Encompass values
- ⚠️ Use with caution!

### Correction Overlay Logic

In demo mode, the orchestrator simulates what Encompass would look like after corrections:

```
┌──────────────────────┐
│ Encompass (actual)   │
│ Field 610: "Truly    │
│ Title Inc"           │
└──────────────────────┘
           │
           ├─► Verification Agent (demo mode)
           │   Identifies: should be "Truly Title, Inc."
           │   Logs correction (doesn't write)
           │
           ├─► Orderdocs Agent (with overlay)
           │   Reads: "Truly Title Inc" (actual)
           │   Overlays: "Truly Title, Inc." (correction)
           │   Reports: "Truly Title, Inc." (simulated)
           │
           └─► Result: Demo shows post-correction state
```

## Configuration

### OrchestratorConfig

```python
from orchestrator import OrchestratorConfig, OrchestratorAgent

config = OrchestratorConfig(
    loan_id="387596ee-7090-47ca-8385-206e22c9c9da",
    user_prompt=None,                    # Optional custom instructions
    demo_mode=True,                      # True = no actual writes
    max_retries=2,                       # Retry attempts per agent
    document_types=None,                 # Optional document filter
    output_file="results.json"           # Optional output file
)

orchestrator = OrchestratorAgent(config)
results = orchestrator.run()
```

## User Prompt Interpretation

The orchestrator interprets natural language prompts to control execution:

### Agent Selection
- `"only prep"` → Run only preparation agent
- `"skip verification"` → Skip verification agent
- `"skip orderdocs"` → Skip orderdocs agent

### Output Format
- `"summary only"` → Return only human-readable summary
- `"json only"` → Return only JSON output

### Examples

```python
# Run only preparation
run_orchestrator(
    loan_id="...",
    user_prompt="only prep"
)

# Focus on specific aspect
run_orchestrator(
    loan_id="...",
    user_prompt="Focus on borrower name fields, summary only"
)
```

## Output Format

### JSON Output Structure

```json
{
  "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
  "execution_timestamp": "2025-11-25T16:30:00",
  "demo_mode": true,
  "summary": {
    "total_fields_extracted": 16,
    "fields_verified": 16,
    "corrections_needed": 11,
    "corrections_applied": 11,
    "orderdocs_complete": true
  },
  "agents": {
    "preparation": {
      "status": "success",
      "attempts": 1,
      "elapsed_seconds": 245.5,
      "output": { ... }
    },
    "verification": {
      "status": "success",
      "attempts": 1,
      "elapsed_seconds": 315.2,
      "output": { ... }
    },
    "orderdocs": {
      "status": "success",
      "attempts": 1,
      "elapsed_seconds": 12.8,
      "output": { ... }
    }
  }
}
```

### Human-Readable Summary

```
================================================================================
ORCHESTRATOR EXECUTION SUMMARY
================================================================================
Loan ID: 387596ee-7090-47ca-8385-206e22c9c9da
Timestamp: 2025-11-25T16:30:00
Mode: DEMO (no actual writes)

[PREPARATION AGENT]
✓ Success (1 attempt)
- Documents processed: 9/172
- Fields extracted: 16

[VERIFICATION AGENT]
✓ Success (1 attempt)
- Corrections needed: 11
  • Field 4008: corrected to 'Christopher Berger and Alva Scott Sorensen'
  • Field 610: corrected to 'Truly Title, Inc.'
  • Field 1109: corrected to '152625'
  • Field 2294: corrected to 'YES'
  • Field CD3.X82: corrected to '11517.98'
  ... and 6 more

[ORDERDOCS AGENT]
✓ Success (1 attempt)
- Total fields checked: 150
- Fields with values: 150
- Corrections applied (demo): 11

OVERALL STATUS: SUCCESS
================================================================================
```

## Error Handling

### Retry Logic

Each agent is automatically retried on failure with exponential backoff:

- Attempt 1: Immediate
- Attempt 2: Wait 2 seconds
- Attempt 3: Wait 4 seconds
- ...

### Failure Modes

1. **Preparation Fails**: Orchestration stops (verification needs prep output)
2. **Verification Fails**: Continues to orderdocs (orderdocs can still check fields)
3. **Orderdocs Fails**: Execution completes (other agents succeeded)

### Example Error Output

```json
{
  "agents": {
    "preparation": {
      "status": "failed",
      "attempts": 3,
      "error": "Connection timeout to Encompass API"
    }
  }
}
```

## Environment Variables

### Required (inherited from sub-agents)

```bash
# Encompass API credentials
ENCOMPASS_ACCESS_TOKEN=your_token
ENCOMPASS_API_BASE_URL=https://api.elliemae.com
ENCOMPASS_CLIENT_ID=your_client_id
ENCOMPASS_CLIENT_SECRET=your_client_secret
ENCOMPASS_INSTANCE_ID=your_instance_id
ENCOMPASS_USERNAME=your_username
ENCOMPASS_PASSWORD=your_password

# LandingAI for document OCR
LANDINGAI_API_KEY=your_landingai_key
```

### Optional

```bash
# Demo mode (set automatically by orchestrator)
DRY_RUN=true
```

## Sub-Agent Integration

### Preparation Agent
- **Location**: `agents/preparation_agent/`
- **Function**: `process_loan_documents(loan_id, document_types, dry_run)`
- **Output**: Field mappings with values and attachment IDs

### Verification Agent
- **Location**: `agents/verification_agent/`
- **Function**: `run_verification(loan_id, prep_output, dry_run)`
- **Output**: Validation results and corrections

### Orderdocs Agent
- **Location**: `agents/orderdocs_agent/`
- **Function**: `process_orderdocs_request({"loan_id": ..., "document_types": ...})`
- **Output**: Field values from Encompass

## Testing

### Test with Example Loan

```bash
# Run on example loan in demo mode
python orchestrator/orchestrator_agent.py \
  --loan-id "387596ee-7090-47ca-8385-206e22c9c9da" \
  --output test_results.json

# Check results
cat test_results.json | jq '.summary'
cat test_results_summary.txt
```

### Test Script

```python
# orchestrator/test_orchestrator.py
from orchestrator import run_orchestrator

def test_basic_execution():
    """Test basic orchestrator execution."""
    results = run_orchestrator(
        loan_id="387596ee-7090-47ca-8385-206e22c9c9da",
        demo_mode=True
    )
    
    assert results["demo_mode"] == True
    assert "preparation" in results["agents"]
    assert "verification" in results["agents"]
    assert "orderdocs" in results["agents"]
    
    print("✓ Basic execution test passed")

if __name__ == "__main__":
    test_basic_execution()
```

## Troubleshooting

### Common Issues

1. **"Module not found: copilotagent"**
   - Solution: Install dependencies: `pip install -r requirements.txt`

2. **"Missing environment variable: ENCOMPASS_ACCESS_TOKEN"**
   - Solution: Set up `.env` file with Encompass credentials

3. **"Preparation agent failed: 403 Forbidden"**
   - Solution: Check Encompass API credentials and permissions

4. **"All agents skipped"**
   - Solution: Check user prompt - may have skipped all agents

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

results = run_orchestrator(loan_id="...")
```

## Best Practices

1. **Always start with demo mode** for testing
2. **Review corrections** before running in production mode
3. **Save outputs** to files for auditing
4. **Use specific loan IDs** that you know are valid
5. **Check environment variables** before production runs

## Limits and Constraints

- **Timeout**: No built-in timeout (inherits from sub-agents)
- **Rate Limiting**: Subject to Encompass API rate limits
- **Retry Limit**: Default 2 retries per agent (configurable)
- **Document Types**: Processes all available documents by default

## Future Enhancements

- [ ] Parallel agent execution (where possible)
- [ ] Real-time progress updates
- [ ] Webhook notifications on completion
- [ ] Advanced AI prompt interpretation
- [ ] Audit trail export
- [ ] Custom validation rules

## Support

For issues or questions:
1. Check sub-agent READMEs: `agents/{agent_name}/README.md`
2. Review logs in `agents/verification_agent/logs/`
3. Examine detailed output files

## License

Same as parent project.

