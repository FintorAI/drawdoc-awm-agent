"""Gradio UI for Disclosure Agent.

Provides a web interface to run the disclosure orchestrator with real-time progress updates.
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

from agents.disclosure.orchestrator_agent import run_disclosure_orchestrator


def format_field_status_table(field_details):
    """Format field status as pandas DataFrame."""
    if not field_details:
        return pd.DataFrame({"Message": ["No field data available"]})
    
    data = []
    for field_id, details in field_details.items():
        data.append({
            "Field ID": field_id,
            "Field Name": details.get("name", "Unknown"),
            "Has Value": "✓" if details.get("has_value") else "✗",
            "Value": str(details.get("value", ""))[:50] if details.get("has_value") else "(empty)"
        })
    
    return pd.DataFrame(data)


def format_populated_fields_table(actions):
    """Format populated fields as pandas DataFrame."""
    if not actions:
        return pd.DataFrame({"Message": ["No fields were populated"]})
    
    populated = [a for a in actions if a.get("action") == "populate"]
    
    if not populated:
        return pd.DataFrame({"Message": ["No fields were populated"]})
    
    data = []
    for action in populated:
        data.append({
            "Field ID": action.get("field_id", "Unknown"),
            "Value": str(action.get("value", ""))[:50]
        })
    
    return pd.DataFrame(data)


def run_disclosure_with_progress(loan_id, lo_email, demo_mode):
    """Run disclosure orchestrator with progress updates."""
    
    # Queue for progress updates
    progress_queue = queue.Queue()
    
    def progress_callback(agent_name, result, orchestrator):
        """Callback for progress updates."""
        progress_queue.put({"agent": agent_name, "result": result})
    
    # Build progress display
    progress_lines = [
        "🚀 Disclosure Processing Started",
        f"Loan ID: {loan_id}",
        f"LO Email: {lo_email}",
        f"Demo Mode: {'✅ Enabled (no actual writes)' if demo_mode else '❌ Disabled (will write to Encompass)'}",
        "",
        "📋 Processing Pipeline:",
        "",
        "1️⃣ VERIFICATION AGENT",
        "Purpose: Check if required disclosure fields have values",
        "Steps:",
        "  🔍 Loading field mappings from CSV",
        "  📊 Checking each field in Encompass",
        "  📝 Identifying missing fields",
        "Status: 🔄 Starting...",
        "",
        "2️⃣ PREPARATION AGENT",
        "Purpose: Populate missing fields using AI",
        "Steps:",
        "  🤖 Using AI to search for related fields",
        "  🔎 Reading candidate field values",
        "  💡 Intelligently deriving missing values",
        "  📝 Writing populated values (dry run)" if demo_mode else "  ✍️ Writing populated values",
        "  🧹 Cleaning and normalizing existing values",
        "Status: ⏳ Waiting...",
        "",
        "3️⃣ REQUEST AGENT",
        "Purpose: Send disclosure to LO for review",
        "Steps:",
        "  📧 Composing email with field status summary",
        "  📤 Sending to LO (" + lo_email + ")",
        "Status: ⏳ Waiting...",
    ]
    
    # Run in background thread
    def run_background():
        try:
            results = run_disclosure_orchestrator(
                loan_id=loan_id,
                lo_email=lo_email,
                demo_mode=demo_mode,
                progress_callback=progress_callback
            )
            progress_queue.put({"done": True, "results": results})
        except Exception as e:
            progress_queue.put({"error": str(e)})
    
    thread = threading.Thread(target=run_background, daemon=True)
    thread.start()
    
    # Initial yield
    yield (
        "\n".join(progress_lines),
        pd.DataFrame(),
        pd.DataFrame(),
        "",
        ""
    )
    
    # Poll for updates
    results = None
    while True:
        try:
            update = progress_queue.get(timeout=0.5)
            
            if "error" in update:
                progress_lines.append(f"\n❌ ERROR: {update['error']}")
                yield (
                    "\n".join(progress_lines),
                    pd.DataFrame({"Message": ["Error occurred"]}),
                    pd.DataFrame(),
                    f"Error: {update['error']}",
                    ""
                )
                break
            
            if "done" in update:
                results = update["results"]
                break
            
            # Update progress for agent completion
            agent = update.get("agent")
            if agent == "verification":
                # Update verification status
                for i, line in enumerate(progress_lines):
                    if "1️⃣ VERIFICATION AGENT" in line:
                        for j in range(i, len(progress_lines)):
                            if progress_lines[j].startswith("Status:"):
                                progress_lines[j] = "Status: ✅ Complete"
                                break
                        break
                progress_lines.append("")
                progress_lines.append("⏳ Verification complete, starting preparation...")
                
            elif agent == "preparation":
                # Update preparation status
                for i, line in enumerate(progress_lines):
                    if "2️⃣ PREPARATION AGENT" in line:
                        for j in range(i, len(progress_lines)):
                            if progress_lines[j].startswith("Status:"):
                                progress_lines[j] = "Status: ✅ Complete"
                                break
                        break
                progress_lines.append("")
                progress_lines.append("⏳ Preparation complete, sending request...")
                
            elif agent == "request":
                # Update request status
                for i, line in enumerate(progress_lines):
                    if "3️⃣ REQUEST AGENT" in line:
                        for j in range(i, len(progress_lines)):
                            if progress_lines[j].startswith("Status:"):
                                progress_lines[j] = "Status: ✅ Complete"
                                break
                        break
                progress_lines.append("")
                progress_lines.append("✅ All agents complete!")
            
            yield (
                "\n".join(progress_lines),
                pd.DataFrame(),
                pd.DataFrame(),
                "",
                ""
            )
            
        except queue.Empty:
            continue
    
    # Final results
    if results:
        # Extract data
        verification = results.get("agents", {}).get("verification", {}).get("output", {})
        preparation = results.get("agents", {}).get("preparation", {}).get("output", {})
        
        field_details = verification.get("field_details", {})
        actions = preparation.get("actions", [])
        
        # Format tables
        field_status_df = format_field_status_table(field_details)
        populated_fields_df = format_populated_fields_table(actions)
        
        # Format summary
        summary = results.get("summary", "No summary available")
        
        # Format JSON
        json_output = json.dumps(results.get("json_output", {}), indent=2, default=str)
        
        yield (
            "\n".join(progress_lines) + "\n\n✅ Processing complete!",
            field_status_df,
            populated_fields_df,
            summary,
            json_output
        )


# Create Gradio interface
with gr.Blocks(title="Disclosure Agent") as app:
    gr.Markdown("# Disclosure Agent")
    gr.Markdown("Check and prepare disclosure fields, then send to LO for review")
    
    with gr.Row():
        with gr.Column():
            loan_id_input = gr.Textbox(
                label="Loan ID",
                placeholder="387596ee-7090-47ca-8385-206e22c9c9da",
                value="387596ee-7090-47ca-8385-206e22c9c9da"
            )
            lo_email_input = gr.Textbox(
                label="Loan Officer Email",
                placeholder="loan.officer@example.com",
                value="loan.officer@example.com"
            )
            demo_mode_checkbox = gr.Checkbox(
                label="Demo Mode (Dry Run - No Actual Writes)",
                value=True
            )
            run_button = gr.Button("Run Disclosure Agent", variant="primary")
    
    with gr.Tabs():
        with gr.Tab("Progress & Status"):
            progress_output = gr.Textbox(
                label="Progress",
                lines=30,
                interactive=False
            )
        
        with gr.Tab("Field Status"):
            field_status_output = gr.DataFrame(
                label="Field Status",
                interactive=False
            )
        
        with gr.Tab("Populated Fields"):
            populated_fields_output = gr.DataFrame(
                label="Fields Populated by Preparation Agent",
                interactive=False
            )
        
        with gr.Tab("Human-Readable Summary"):
            summary_output = gr.Textbox(
                label="Summary",
                lines=30,
                interactive=False
            )
        
        with gr.Tab("Full JSON Output"):
            json_output = gr.Code(
                label="Complete Results (JSON)",
                language="json",
                interactive=False
            )
    
    # Connect button to function
    run_button.click(
        fn=run_disclosure_with_progress,
        inputs=[loan_id_input, lo_email_input, demo_mode_checkbox],
        outputs=[
            progress_output,
            field_status_output,
            populated_fields_output,
            summary_output,
            json_output
        ]
    )

if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7861)

