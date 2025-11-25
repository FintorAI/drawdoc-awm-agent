"""
Gradio UI for Draw Docs
Provides a web interface to run the orchestrator with real-time progress updates.
"""

import gradio as gr
import json
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import threading
import time
import queue

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from orchestrator.orchestrator_agent import run_orchestrator


# Available document types
DOCUMENT_TYPES = [
    "ID",
    "Title Report", 
    "Appraisal",
    "LE",
    "1003",
    "CD",
    "VOE",
    "Paystub",
    "Bank Statement",
    "Tax Return"
]


def format_corrected_fields_table(corrected_fields_summary):
    """Format corrected fields as a pandas DataFrame for display."""
    if not corrected_fields_summary:
        return pd.DataFrame({"Message": ["No corrections were needed"]})
    
    # Convert to DataFrame
    data = []
    for field in corrected_fields_summary:
        # Truncate long values
        value_str = str(field["corrected_value"])
        if len(value_str) > 50:
            value_str = value_str[:47] + "..."
        
        data.append({
            "Field ID": field["field_id"],
            "Field Name": field.get("field_name", field["field_id"]),
            "Corrected Value": value_str,
            "Source Document": field["document_filename"]
        })
    
    return pd.DataFrame(data)


def format_agent_status(agent_name, agent_result):
    """Format agent status for display."""
    status = agent_result.get("status", "unknown")
    attempts = agent_result.get("attempts", 0)
    elapsed = agent_result.get("elapsed_seconds", 0)
    
    symbol = "✅" if status == "success" else "❌"
    
    return f"{symbol} **{agent_name.upper()} AGENT**: {status.title()} ({attempts} attempt(s), {elapsed:.1f}s)"


def run_orchestrator_with_progress(loan_id, document_types, progress=gr.Progress()):
    """
    Run orchestrator and yield progress updates using threading and queue.
    
    Args:
        loan_id: Encompass loan GUID
        document_types: List of document types to process
        progress: Gradio progress tracker
        
    Yields:
        Tuple of (progress_text, corrected_fields_df, summary_text, json_text)
    """
    # Validate inputs
    if not loan_id or not loan_id.strip():
        yield (
            "❌ Error: Loan ID is required",
            pd.DataFrame({"Message": ["Please provide a loan ID"]}),
            "",
            ""
        )
        return
    
    loan_id = loan_id.strip()
    doc_types = None if not document_types else document_types
    
    # Create queue for progress updates
    update_queue = queue.Queue()
    results_container = {"results": None, "error": None}
    
    # Initial progress text
    initial_text = f"""
## 🚀 Draw Docs Processing Started
**Loan ID:** `{loan_id}`
**Document Types:** {', '.join(doc_types) if doc_types else 'ALL (with schemas)'}
**Demo Mode:** ✅ Enabled (no actual writes)

---

### 📋 Processing Pipeline:

### 1️⃣ PREPARATION AGENT
**Purpose:** Extract field values from loan documents

**Steps:**
- 🔍 Fetching all attachments from Encompass for loan
- 📄 Identifying document types (ID, Title Report, Appraisal, LE, 1003, etc.)
- 🤖 Using AI to extract structured data from each document
- 🗺️ Mapping extracted values to Encompass field IDs
- 📊 Aggregating all extracted fields

**Status:** 🔄 Starting...
  ⏳ Fetching documents from Encompass...
  ⏳ Analyzing documents with AI (this may take 2-4 minutes)...
"""
    
    # Initial yield
    yield (
        initial_text,
        pd.DataFrame({"Message": ["Starting preparation agent..."]}),
        "",
        ""
    )
    
    # Define callback for progress updates
    def progress_callback(agent_name, agent_result, orchestrator):
        """Called after each agent completes - puts update in queue."""
        update_queue.put((agent_name, agent_result, orchestrator))
    
    # Run orchestrator in separate thread
    def run_in_thread():
        try:
            results = run_orchestrator(
                loan_id=loan_id,
                user_prompt=None,
                demo_mode=True,
                max_retries=1,
                document_types=doc_types,
                progress_callback=progress_callback
            )
            results_container["results"] = results
            update_queue.put(("DONE", None, None))
        except Exception as e:
            results_container["error"] = e
            update_queue.put(("ERROR", str(e), None))
    
    # Start orchestrator thread
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
    
    # Track progress
    progress_text = initial_text
    corrected_fields_df = pd.DataFrame({"Message": ["Processing..."]})
    summary_text = ""
    json_text = ""
    
    # Poll queue for updates
    while True:
        try:
            # Check queue with timeout
            update = update_queue.get(timeout=1.0)
            agent_name, data, orchestrator = update
            
            if agent_name == "ERROR":
                error_text = f"""
## ❌ Error Occurred

**Error Message:** {data}

Please check the logs for more details.
"""
                yield (error_text, pd.DataFrame({"Message": ["Error occurred"]}), "", "")
                return
            
            elif agent_name == "DONE":
                # Final update
                results = results_container["results"]
                
                # Get corrected fields
                corrected_fields_summary = results.get("json_output", {}).get("corrected_fields_summary", [])
                corrected_fields_df = format_corrected_fields_table(corrected_fields_summary)
                
                # Get summary
                summary_text = results.get("summary_text", "")
                
                # Get full JSON output (same format as test_results.json)
                # Use default=str to handle non-serializable objects like LangChain messages
                json_text = json.dumps(results.get("json_output", {}), indent=2, default=str)
                
                # Final progress text
                progress_text += "\n\n---\n\n## ✅ Draw Docs Processing Complete!"
                progress_text += f"\n**Timestamp:** {results.get('execution_timestamp', 'N/A')}"
                progress_text += f"\n\n🎉 All agents executed successfully! Review the **Corrected Fields** and **Summary** tabs for detailed results."
                
                progress(1.0, desc="Complete!")
                yield (progress_text, corrected_fields_df, summary_text, json_text)
                return
            
            elif agent_name == "preparation":
                progress(0.35, desc="Preparation complete!")
                progress_text += f"\n\n**Result:** {format_agent_status('preparation', data)}"
                
                if data.get("status") == "success":
                    prep_output = data.get("output", {})
                    docs_processed = prep_output.get("documents_processed", 0)
                    total_docs = prep_output.get("total_documents_found", 0)
                    fields_extracted = len(prep_output.get("results", {}).get("field_mappings", {}))
                    progress_text += f"\n  ✅ Documents analyzed: {docs_processed}/{total_docs}"
                    progress_text += f"\n  ✅ Fields successfully extracted: {fields_extracted}"
                
                # Add verification agent details
                progress_text += """

---

### 2️⃣ VERIFICATION AGENT
**Purpose:** Compare extracted values with Encompass and correct mismatches

**Steps:**
- 🔍 Loading field mapping configuration (193 fields)
- 📚 Loading SOP rules (67 pages of validation rules)
- 🔄 For each extracted field:
  - Fetching current value from Encompass
  - Comparing prep value (from docs) vs Encompass value
  - Identifying discrepancies and mismatches
  - Determining if correction is needed
  - Writing corrections (dry run mode)
- 📝 Generating comprehensive validation report
- 🎯 Tracking source documents for each correction

**Status:** 🔄 Starting...
  ⏳ Loading field mappings and SOP rules...
  ⏳ Fetching current Encompass field values...
  ⏳ Comparing values and identifying discrepancies (this may take 2-4 minutes)...
"""
                yield (progress_text, corrected_fields_df, summary_text, json_text)
            
            elif agent_name == "verification":
                progress(0.70, desc="Verification complete!")
                progress_text += f"\n\n**Result:** {format_agent_status('verification', data)}"
                
                # Get corrected fields from orchestrator
                if orchestrator:
                    corrected_fields_summary = orchestrator._aggregate_results().get("corrected_fields_summary", [])
                    corrected_fields_df = format_corrected_fields_table(corrected_fields_summary)
                    
                    if corrected_fields_summary:
                        progress_text += f"\n  ✅ Corrections identified: {len(corrected_fields_summary)} fields"
                        progress_text += f"\n  📄 All corrections logged with source documents"
                    else:
                        progress_text += f"\n  ✅ All fields matched - no corrections needed!"
                
                # Add orderdocs agent details
                progress_text += """

---

### 3️⃣ ORDER DOCS AGENT
**Purpose:** Verify all required fields have values in Encompass

**Steps:**
- 📋 Loading document type requirements
- 🔍 Checking field values in Encompass
- ✅ Verifying required fields are populated
- 🔄 Applying demo corrections overlay (simulating verification writes)
- 📊 Generating field completion report

**Status:** 🔄 Starting...
  ⏳ Checking Encompass field values...
  ⏳ Applying demo corrections overlay...
"""
                yield (progress_text, corrected_fields_df, summary_text, json_text)
            
            elif agent_name == "orderdocs":
                progress(0.95, desc="Order docs complete!")
                progress_text += f"\n\n**Result:** {format_agent_status('orderdocs', data)}"
                
                if data.get("status") == "success":
                    ord_output = data.get("output", {})
                    total_fields = len(ord_output)
                    fields_with_value = sum(1 for f in ord_output.values() if isinstance(f, dict) and f.get("has_value"))
                    corrections_applied = sum(1 for f in ord_output.values() if isinstance(f, dict) and f.get("correction_applied"))
                    progress_text += f"\n  ✅ Total fields checked: {total_fields}"
                    progress_text += f"\n  ✅ Fields with values: {fields_with_value}"
                    if corrections_applied > 0:
                        progress_text += f"\n  ✅ Demo corrections overlaid: {corrections_applied}"
                
                yield (progress_text, corrected_fields_df, summary_text, json_text)
        
        except queue.Empty:
            # No update yet, keep waiting
            time.sleep(0.5)
            continue


def create_gradio_interface():
    """Create and return the Gradio interface."""
    
    with gr.Blocks(title="Draw Docs") as demo:
        gr.Markdown("""
# 📄 Draw Docs
        
Automated loan document processing with AI-powered field extraction, verification, and validation.
        
**Demo Mode:** All operations run in demo mode - no actual writes to Encompass.
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                loan_id_input = gr.Textbox(
                    label="Loan ID",
                    placeholder="Enter Encompass loan GUID",
                    value="387596ee-7090-47ca-8385-206e22c9c9da"
                )
                
                document_types_input = gr.CheckboxGroup(
                    choices=DOCUMENT_TYPES,
                    label="Document Types",
                    info="Select document types to process (leave empty for ALL)",
                    value=["ID", "Title Report", "Appraisal", "LE", "1003"]
                )
                
                run_button = gr.Button("🚀 Run Draw Docs", variant="primary", size="lg")
                
                gr.Markdown("""
---
                
### ℹ️ How It Works
                
1. **Preparation Agent**: 
   - Fetches documents from Encompass
   - Uses AI to extract structured field data
   - Maps values to Encompass field IDs
   
2. **Verification Agent**:
   - Compares extracted values with current Encompass values
   - Identifies mismatches and discrepancies
   - Generates corrections with source documents
   
3. **Order Docs Agent**:
   - Verifies all required fields have values
   - Checks field completion status
                
**Demo Mode:** No changes written to Encompass - all corrections are logged only.
                """)
        
            with gr.Column(scale=2):
                with gr.Tabs():
                    with gr.Tab("Progress & Status"):
                        progress_output = gr.Markdown("Click 'Run Draw Docs' to start...")
                    
                    with gr.Tab("Corrected Fields"):
                        corrected_fields_output = gr.DataFrame(
                            headers=["Field ID", "Field Name", "Corrected Value", "Source Document"]
                        )
                    
                    with gr.Tab("Human-Readable Summary"):
                        summary_output = gr.Textbox(
                            label="Execution Summary",
                            lines=30,
                            interactive=False
                        )
                    
                    with gr.Tab("Full JSON Output"):
                        json_output = gr.Code(
                            label="Complete Results (JSON)",
                            language="json",
                            lines=30,
                            interactive=False
                        )
        
        # Example inputs
        gr.Markdown("### 📌 Example")
        
        gr.Examples(
            examples=[
                ["387596ee-7090-47ca-8385-206e22c9c9da", ["ID", "Title Report", "Appraisal", "LE", "1003"]],
                ["387596ee-7090-47ca-8385-206e22c9c9da", []],
            ],
            inputs=[loan_id_input, document_types_input],
            label="Try these examples:"
        )
        
        # Wire up the run button
        run_button.click(
            fn=run_orchestrator_with_progress,
            inputs=[loan_id_input, document_types_input],
            outputs=[progress_output, corrected_fields_output, summary_output, json_output]
        )
    
    return demo


if __name__ == "__main__":
    """Launch the Gradio app."""
    print("=" * 80)
    print("🚀 Starting Draw Docs Interface")
    print("=" * 80)
    print("Demo mode is ENABLED - no actual writes will be made to Encompass")
    print("Local URL: http://localhost:7860")
    print("=" * 80)
    
    demo = create_gradio_interface()
    
    # Launch with share=False for local only, share=True to get public URL
    demo.launch(
        server_name="0.0.0.0",  # Allow external access
        server_port=7860,
        share=False,  # Set to True to get a public URL
        show_error=True
    )

