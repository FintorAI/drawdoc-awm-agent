# Gradio UI for Orchestrator Agent

A user-friendly web interface for running the orchestrator agent with real-time progress updates.

## Features

- 🎯 **Interactive Input**: Enter loan ID, select document types, and provide optional prompts
- 📊 **Real-time Progress**: See live updates as each sub-agent runs
- 📋 **Corrected Fields Table**: View all corrections with source document filenames
- 📄 **Human-Readable Summary**: Complete execution summary
- 💾 **Results Export**: Full JSON output available for download

## Installation

Install the additional dependencies for the Gradio UI:

```bash
pip install gradio>=4.0.0 pandas>=1.5.0
```

Or install all orchestrator dependencies:

```bash
pip install -r orchestrator/requirements.txt
```

## Usage

### Launch the UI

```bash
python orchestrator/gradio_app.py
```

The interface will be available at:
- **Local URL**: http://localhost:7860
- **Network URL**: http://0.0.0.0:7860

### Using the Interface

1. **Enter Loan ID**: Required - the Encompass loan GUID
   - Example: `387596ee-7090-47ca-8385-206e22c9c9da`

2. **Select Document Types** (Optional):
   - Choose specific document types to process
   - Leave empty to process ALL documents with schemas
   - Available types: ID, Title Report, Appraisal, LE, 1003, etc.

3. **User Prompt** (Optional):
   - Provide custom instructions for the orchestrator
   - Example: "Focus on borrower name fields"

4. **Click "Run Orchestrator"**:
   - Watch real-time progress updates
   - View results in different tabs

## Interface Tabs

### 1. Progress & Status
Shows real-time updates as the orchestrator runs:
- Preparation agent status and timing
- Verification agent corrections count
- Orderdocs agent field checks
- Overall execution status

### 2. Corrected Fields
Table view of all corrections made:
- **Field ID**: The Encompass field identifier
- **Field Name**: Human-readable field name
- **Corrected Value**: The new value (truncated if long)
- **Source Document**: Filename of the source document (attachment_id.pdf)

Example:
| Field ID | Field Name | Corrected Value | Source Document |
|----------|------------|----------------|-----------------|
| 4008 | Borrower Vesting Type | Christopher Berger and Alva Scott... | 318be174-03ec-4b99-85ea-1de0cc286702.pdf |
| 610 | Escrow Company Name | Truly Title, Inc. | 318be174-03ec-4b99-85ea-1de0cc286702.pdf |

### 3. Human-Readable Summary
Complete text summary including:
- Loan ID and timestamp
- Each agent's status (success/failure)
- Documents processed count
- Fields extracted count
- Corrections needed/made
- Overall execution status

### 4. Download Results
- JSON preview of full results
- Results automatically saved to `orchestrator/test_results.json`

## Demo Mode

**⚠️ IMPORTANT**: The UI always runs in **DEMO MODE**.

- No actual writes are made to Encompass
- All corrections are logged but not applied
- Safe to test with production data
- To apply corrections, use the production mode (requires environment configuration)

## Example Workflows

### Workflow 1: Full Loan Verification
```
1. Enter loan ID: 387596ee-7090-47ca-8385-206e22c9c9da
2. Select document types: ID, Title Report, Appraisal, LE, 1003
3. Leave user prompt empty
4. Click Run
5. Review corrections in "Corrected Fields" tab
6. Read full summary in "Human-Readable Summary" tab
```

### Workflow 2: Focused Field Check
```
1. Enter loan ID
2. Select specific document types (e.g., just "Title Report")
3. Add prompt: "Focus on loan amount and vesting fields"
4. Click Run
5. Review targeted corrections
```

### Workflow 3: Quick All-Document Scan
```
1. Enter loan ID
2. Leave document types empty (processes ALL with schemas)
3. Leave prompt empty
4. Click Run
5. Get comprehensive analysis of all available documents
```

## Troubleshooting

### UI Won't Start
```bash
# Check if port 7860 is already in use
netstat -ano | findstr :7860  # Windows
lsof -i :7860  # Mac/Linux

# Use a different port
# Edit gradio_app.py, line ~345:
# demo.launch(server_port=7861)  # Change port number
```

### Connection Timeout
- Check that the Encompass API is accessible
- Verify environment variables are set correctly
- Check logs for specific error messages

### No Results Showing
- Ensure the loan ID exists in Encompass
- Check document types are available for the loan
- Review progress tab for error messages

## Configuration

### Environment Variables
The Gradio UI respects all orchestrator environment variables:

```bash
# Set in .env file
DRY_RUN=true  # Always true for Gradio UI
```

### Customization

Edit `orchestrator/gradio_app.py` to customize:

- **Port**: Change `server_port` parameter
- **Theme**: Change `theme=gr.themes.Soft()` to other themes
- **Document Types**: Modify `DOCUMENT_TYPES` list
- **Sharing**: Set `share=True` to get public URL

## Performance Notes

- **First Run**: May take 4-8 minutes depending on document count
- **Preparation**: Slowest step (~2-4 minutes)
- **Verification**: ~2-4 minutes (depends on field count)
- **Orderdocs**: Fast (~15-30 seconds)

## Security Considerations

1. **Demo Mode Only**: UI enforces demo mode - no production writes
2. **Local Access**: By default, only accessible on local network
3. **Public Sharing**: Only enable `share=True` if needed temporarily
4. **Credentials**: Ensure .env file is not in public directories

## Support

For issues or questions:
1. Check the terminal output for detailed error messages
2. Review `orchestrator/test_results.json` for full execution details
3. Check agent-specific logs in their directories
4. Refer to `orchestrator/README.md` for orchestrator documentation

