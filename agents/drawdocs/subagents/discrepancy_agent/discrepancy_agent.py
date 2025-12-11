"""
Discrepancy Detection Agent

Automatically detects discrepancies between extracted field values (from Prep Agent)
and existing Encompass values, categorizes them as HARD STOPS vs PTF conditions,
and generates appropriate PTF text.

Key Features:
- Compares doc_context field mappings against Encompass field values
- Applies intelligent matching rules (fuzzy address, name variations, etc.)
- Auto-generates PTF condition text for soft discrepancies
- Flags hard stops that require immediate escalation
- Integrates with orchestrator between Drawcore and Verification

Based on:
- Docs Draw SOP (1).docx
- discovery/sop_workflow_analysis.md (lines 768-780: Hard Stops)
- context/docs_draw_sop.md (lines 1382-1391: Acceptable Variances)
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import primitives
from agents.drawdocs.tools.primitives import (
    get_loan_context,
    read_fields,
    add_ptf_condition,
    list_ptf_conditions,
    log_issue
)

# Import unified rule engine
from agents.drawdocs.config.unified_rules_engine import (
    get_rule_engine,
    RuleSeverity,
    RuleCategory
)
from agents.drawdocs.config.rule_definitions import register_all_rules

# Register rules on first import
try:
    register_all_rules()
except Exception as e:
    # Rules may already be registered
    pass


def run_discrepancy_detection(
    loan_id: str,
    doc_context: Dict[str, Any],
    loan_type: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Main discrepancy detection function.
    
    Compares extracted field values against Encompass values and:
    1. Identifies hard stops (loan amount, interest rate, etc.)
    2. Identifies soft discrepancies (name variations, address format)
    3. Auto-generates PTF conditions for soft issues
    4. Returns comprehensive report
    
    Args:
        loan_id: The loan GUID
        doc_context: Output from Prep Agent containing field_mappings
        loan_type: Optional loan type (FHA, VA, USDA, Conventional)
        dry_run: If True, don't actually create PTF conditions
        
    Returns:
        Dictionary containing:
        - status: "blocked" (hard stops found) or "proceed_with_conditions" or "success"
        - hard_stops: List of blocking issues
        - soft_discrepancies: List of PTF conditions added
        - ptf_conditions_added: Count of PTF conditions created
        - summary: Human-readable summary
    """
    print(f"\n{'='*80}")
    print(f"🔍 DISCREPANCY DETECTION AGENT - Loan {loan_id}")
    print(f"{'='*80}\n")
    
    result = {
        "loan_id": loan_id,
        "status": "success",
        "hard_stops": [],
        "soft_discrepancies": [],
        "ptf_conditions_added": 0,
        "fields_checked": 0,
        "discrepancies_found": 0,
        "acceptable_variances": 0,
        "summary": "",
        "execution_time": None
    }
    
    start_time = datetime.now()
    
    try:
        # Extract field mappings from doc_context
        field_mappings = doc_context.get("field_mappings", {})
        
        if not field_mappings:
            print("⚠️  No field mappings found in doc_context")
            result["status"] = "skipped"
            result["summary"] = "No field mappings to verify"
            return result
        
        print(f"📊 Checking {len(field_mappings)} extracted fields against Encompass...\n")
        
        # Get loan context for prerequisites
        loan_context_data = get_loan_context(loan_id)
        loan_context = {
            "loan_type": loan_type or loan_context_data.get("loan_type", "ALL"),
            "state": loan_context_data.get("state", "ALL"),
            "loan_purpose": loan_context_data.get("loan_purpose", "ALL"),
            "loan_amount": loan_context_data.get("loan_amount")
        }
        
        # Read all extracted field values from Encompass for comparison
        field_ids_to_check = list(field_mappings.keys())
        encompass_values = read_fields(loan_id, field_ids_to_check)
        
        # Build field_values dict for rule engine
        # Format: field_id -> encompass value, field_id_extracted -> extracted value
        field_values = {}
        for field_id, field_data in field_mappings.items():
            extracted_value = field_data.get("value", "")
            encompass_value = encompass_values.get(field_id, "")
            
            field_values[field_id] = encompass_value
            field_values[f"{field_id}_extracted"] = extracted_value
        
        # Get rule engine and execute all rules
        engine = get_rule_engine()
        print(f"🔧 Executing {len(engine.list_rules())} business rules...\n")
        
        rule_results = engine.execute_all_rules(field_values, loan_context)
        
        # Process rule results
        for rule_result in rule_results:
            result["fields_checked"] += 1
            
            if not rule_result.passed:
                result["discrepancies_found"] += 1
                
                # Get source document
                field_id = rule_result.field_id or "unknown"
                source_doc = field_mappings.get(field_id, {}).get("source", "Unknown")
                
                # Handle based on severity
                if rule_result.severity == RuleSeverity.CRITICAL.value:
                    # HARD STOP - Block the pipeline
                    hard_stop_data = {
                        "type": rule_result.category,
                        "field_id": rule_result.field_id,
                        "field_name": rule_result.field_name or "Unknown Field",
                        "extracted": rule_result.extracted_value,
                        "encompass": rule_result.encompass_value,
                        "source_doc": source_doc,
                        "action": "Contact Team Lead immediately",
                        "message": rule_result.message,
                        "rule_id": rule_result.rule_id
                    }
                    result["hard_stops"].append(hard_stop_data)
                    
                    print(f"  🛑 HARD STOP: {rule_result.field_name}")
                    print(f"     Rule: {rule_result.rule_name}")
                    print(f"     Extracted: {rule_result.extracted_value}")
                    print(f"     Encompass: {rule_result.encompass_value}")
                    print(f"     Message: {rule_result.message}\n")
                    
                    # Log critical issue
                    log_issue(
                        loan_id=loan_id,
                        severity="critical",
                        message=f"HARD STOP: {rule_result.message}",
                        context={
                            "field_id": rule_result.field_id,
                            "field_name": rule_result.field_name,
                            "extracted_value": rule_result.extracted_value,
                            "encompass_value": rule_result.encompass_value,
                            "source_doc": source_doc,
                            "rule_id": rule_result.rule_id
                        },
                        field_id=rule_result.field_id
                    )
                
                elif rule_result.severity == RuleSeverity.HIGH.value and rule_result.ptf_condition:
                    # SOFT DISCREPANCY - Add PTF, continue
                    ptf_text = rule_result.ptf_condition.description_template.format(
                        field_name=rule_result.field_name,
                        extracted=rule_result.extracted_value,
                        encompass=rule_result.encompass_value,
                        expected=rule_result.expected_value or "N/A",
                        message=rule_result.message
                    )
                    
                    soft_discrepancy_data = {
                        "type": rule_result.category,
                        "field_id": rule_result.field_id,
                        "field_name": rule_result.field_name,
                        "extracted": rule_result.extracted_value,
                        "encompass": rule_result.encompass_value,
                        "source_doc": source_doc,
                        "severity": "PTF",
                        "ptf_text": ptf_text,
                        "ptf_added": False,
                        "assigned_to": rule_result.ptf_condition.assigned_to,
                        "rule_id": rule_result.rule_id
                    }
                    
                    # Create PTF condition
                    if not dry_run:
                        ptf_result = add_ptf_condition(
                            loan_id=loan_id,
                            category=rule_result.category,
                            description=ptf_text,
                            severity="PTF",
                            assigned_to=rule_result.ptf_condition.assigned_to,
                            allow_to_clear=True,
                            source_document=source_doc,
                            field_id=rule_result.field_id
                        )
                        
                        if ptf_result["success"]:
                            soft_discrepancy_data["ptf_added"] = True
                            soft_discrepancy_data["condition_id"] = ptf_result["condition_id"]
                            result["ptf_conditions_added"] += 1
                    
                    result["soft_discrepancies"].append(soft_discrepancy_data)
                    
                    print(f"  ⚠️  PTF: {rule_result.field_name}")
                    print(f"     Rule: {rule_result.rule_name}")
                    print(f"     Extracted: {rule_result.extracted_value}")
                    print(f"     Encompass: {rule_result.encompass_value}")
                    print(f"     PTF: {ptf_text[:80]}...\n")
        
        # Determine final status
        if result["hard_stops"]:
            result["status"] = "blocked"
            result["summary"] = f"❌ BLOCKED: {len(result['hard_stops'])} hard stop(s) found. Pipeline halted."
        elif result["soft_discrepancies"]:
            result["status"] = "proceed_with_conditions"
            result["summary"] = f"⚠️  Proceeding with {result['ptf_conditions_added']} PTF condition(s) added."
        else:
            result["status"] = "success"
            result["summary"] = f"✅ No discrepancies found. All {result['fields_checked']} fields match."
        
        # Calculate execution time
        result["execution_time"] = (datetime.now() - start_time).total_seconds()
        
        # Print summary
        print(f"\n{'='*80}")
        print(f"📊 DISCREPANCY DETECTION SUMMARY")
        print(f"{'='*80}")
        print(f"Status: {result['status'].upper()}")
        print(f"Fields Checked: {result['fields_checked']}")
        print(f"Discrepancies Found: {result['discrepancies_found']}")
        print(f"Acceptable Variances: {result['acceptable_variances']}")
        print(f"Hard Stops: {len(result['hard_stops'])}")
        print(f"PTF Conditions Added: {result['ptf_conditions_added']}")
        print(f"Execution Time: {result['execution_time']:.2f}s")
        print(f"\n{result['summary']}")
        print(f"{'='*80}\n")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error in discrepancy detection: {e}")
        log_issue(
            loan_id=loan_id,
            severity="error",
            message=f"Discrepancy detection failed: {e}"
        )
        
        result["status"] = "failed"
        result["error"] = str(e)
        result["summary"] = f"❌ Discrepancy detection failed: {e}"
        return result


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Discrepancy Detection Agent")
    parser.add_argument("--loan-id", required=True, help="Loan GUID")
    parser.add_argument("--doc-context-file", required=True, help="Path to doc_context JSON file (from Prep Agent)")
    parser.add_argument("--loan-type", help="Loan type (FHA, VA, USDA, Conventional)")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually create PTF conditions")
    parser.add_argument("--output", help="Output file for results JSON")
    
    args = parser.parse_args()
    
    # Load doc_context
    with open(args.doc_context_file, "r") as f:
        doc_context = json.load(f)
    
    # Run discrepancy detection
    result = run_discrepancy_detection(
        loan_id=args.loan_id,
        doc_context=doc_context,
        loan_type=args.loan_type,
        dry_run=args.dry_run
    )
    
    # Save output
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"✅ Results saved to {args.output}")

