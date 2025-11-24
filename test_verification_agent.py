"""
Test script for the Verification Sub-Agent.

Loads the test_output.json from prep agent and runs verification.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import logging

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.verification_agent import run_verification
from config.field_document_mapping import FIELD_MAPPING
from config.sop_rules import SOP_RULES

# Setup logging
def setup_logging():
    """Setup logging to file and console."""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"verification_test_{timestamp}.log"
    
    # Create logger
    logger = logging.getLogger("verification_test")
    logger.setLevel(logging.DEBUG)
    
    # File handler (detailed)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Console handler (summary only)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger, log_file


def load_test_prep_output() -> dict:
    """Load test output from prep agent."""
    # Use the correct prep_output.json which has the right format
    test_file = Path(__file__).parent / "data" / "prep_output.json"
    
    if not test_file.exists():
        # Fall back to old test_output.json if prep_output doesn't exist
        test_file = Path(__file__).parent / "test_output.json"
    
    if not test_file.exists():
        raise FileNotFoundError(f"Test file not found: {test_file}")
    
    with open(test_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    """Main test function."""
    # Setup logging
    logger, log_file = setup_logging()
    
    print("=" * 80)
    print("VERIFICATION SUB-AGENT TEST")
    print("=" * 80)
    print(f"\n📝 Detailed logs will be saved to: {log_file}")
    
    logger.info("="*80)
    logger.info("VERIFICATION SUB-AGENT TEST STARTED")
    logger.info("="*80)
    
    # ENABLE DRY RUN BY DEFAULT for safety on production
    import os
    if os.getenv("DRY_RUN") is None:
        os.environ["DRY_RUN"] = "true"
        print("\n⚠️  DRY RUN MODE ENABLED (set DRY_RUN=false to disable)")
        logger.info("DRY RUN MODE ENABLED")
    
    # Load test prep output
    print("\n[1] Loading test prep output...")
    logger.info("Loading test prep output...")
    try:
        prep_output = load_test_prep_output()
        print(f"[OK] Loaded prep output for loan: {prep_output['loan_id']}")
        print(f"  - Documents processed: {prep_output['documents_processed']}")
        print(f"  - Total documents: {prep_output['total_documents_found']}")
        
        logger.info(f"Loaded prep output for loan: {prep_output['loan_id']}")
        logger.debug(f"Prep output details: {json.dumps(prep_output, indent=2)}")
    except Exception as e:
        print(f"[ERROR] Error loading test output: {e}")
        logger.error(f"Error loading test output: {e}", exc_info=True)
        return
    
    # Show field mapping stats
    print(f"\n[2] Field mapping loaded:")
    print(f"  - Total fields: {len(FIELD_MAPPING)}")
    print(f"  - SOP pages referenced: {len(SOP_RULES.get('page_indexed_rules', {}))}")
    
    logger.info(f"Field mapping loaded: {len(FIELD_MAPPING)} fields")
    logger.info(f"SOP rules loaded: {len(SOP_RULES.get('page_indexed_rules', {}))} pages")
    
    # Extract loan_id
    loan_id = prep_output['loan_id']
    
    # Run verification
    print(f"\n[3] Running verification on loan {loan_id}...")
    logger.info(f"Starting verification for loan: {loan_id}")
    print("-" * 80)
    
    try:
        result = run_verification(
            loan_id=loan_id,
            prep_output=prep_output,
            field_mapping=FIELD_MAPPING,
            sop_rules=SOP_RULES
        )
        
        print("\n" + "=" * 80)
        print("VERIFICATION RESULTS")
        print("=" * 80)
        
        # Debug: Log what keys are in the result
        logger.debug(f"Result keys: {list(result.keys())}")
        logger.debug(f"Messages: {len(result.get('messages', []))}")
        logger.debug(f"Todos: {len(result.get('todos', []))}")
        logger.debug(f"Files: {len(result.get('files', []))}")
        
        # Parse corrections from messages
        print("\n[4] Parsing corrections from messages...")
        logger.info("-"*80)
        logger.info("PARSING CORRECTIONS FROM MESSAGES")
        logger.info("-"*80)
        
        messages = result.get("messages", [])
        corrections_list = []
        
        # Debug: Log all ToolMessages to see the actual format
        tool_messages_found = 0
        for msg in messages:
            msg_type = type(msg).__name__
            if msg_type == "ToolMessage":
                tool_messages_found += 1
                
                # Get content - might be string or dict
                content = getattr(msg, 'content', '')
                content_type = type(content).__name__
                
                # Debug output for first few messages (to log file only)
                if tool_messages_found <= 5:
                    logger.debug(f"ToolMessage #{tool_messages_found} (content type: {content_type}):")
                    if isinstance(content, dict):
                        logger.debug(f"  Content (dict): {json.dumps(content, indent=2)}")
                    else:
                        logger.debug(f"  Content (str): {str(content)[:500]}")
                
                # Handle dict content (tool returned dict directly)
                if isinstance(content, dict):
                    if "field_id" in content and "corrected_value" in content:
                        corrections_list.append(content)
                        logger.info(f"  ✓ Field {content.get('field_id')}: '{content.get('corrected_value')}'")
                    continue
                
                # Handle string content
                content_str = str(content)
                
                # Format 1: "🔍 [DRY RUN] Would correct field X to 'Y'. Reason: Z"
                if "[DRY RUN]" in content_str and "Would correct field" in content_str:
                    try:
                        field_part = content_str.split("field ")[1].split(" to ")[0]
                        value_part = content_str.split(" to '")[1].split("'")[0] if " to '" in content_str else content_str.split(" to ")[1].split(".")[0]
                        reason_part = content_str.split("Reason: ")[1] if "Reason: " in content_str else ""
                        
                        correction = {
                            "field_id": field_part.strip(),
                            "corrected_value": value_part,
                            "reason": reason_part[:150],
                            "dry_run": True
                        }
                        corrections_list.append(correction)
                        logger.info(f"  ✓ Field {correction['field_id']}: '{correction['corrected_value']}'")
                    except Exception as e:
                        logger.warning(f"  ⚠️  Failed to parse correction: {str(e)}")
                        logger.debug(f"      Content: {content_str[:150]}")
                
                # Format 2: String representation of dict
                elif "field_id" in content_str and "corrected_value" in content_str:
                    try:
                        # Try to parse as JSON
                        import ast
                        correction_data = ast.literal_eval(content_str)
                        if isinstance(correction_data, dict):
                            corrections_list.append(correction_data)
                            logger.info(f"  ✓ Field {correction_data.get('field_id')}: '{correction_data.get('corrected_value')}'")
                    except:
                        # Try JSON parsing
                        try:
                            correction_data = json.loads(content_str)
                            if isinstance(correction_data, dict):
                                corrections_list.append(correction_data)
                                logger.info(f"  ✓ Field {correction_data.get('field_id')}: '{correction_data.get('corrected_value')}'")
                        except:
                            logger.warning(f"  ⚠️  Found correction data but couldn't parse: {content_str[:100]}")
        
        logger.debug(f"Total ToolMessages found: {tool_messages_found}")
        logger.info(f"✓ Total corrections parsed: {len(corrections_list)}")
        print(f"  ✓ Found {len(corrections_list)} corrections")
        
        if len(corrections_list) == 0 and tool_messages_found > 0:
            logger.warning("WARNING: Found ToolMessages but no corrections parsed!")
            logger.warning("This suggests the message format doesn't match expected patterns.")
            logger.warning("Check the log file for ToolMessage details.")
            print("  ⚠️  No corrections parsed - check log file for details")
        
        # Check for write_corrected_field tool calls
        logger.info("-"*80)
        logger.info("TOOL CALLS ANALYSIS")
        logger.info("-"*80)
        
        tool_calls_count = {}
        for msg in messages:
            msg_type = type(msg).__name__
            
            # Check AIMessage for tool calls
            if msg_type == "AIMessage" and hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get('name', 'unknown')
                    tool_calls_count[tool_name] = tool_calls_count.get(tool_name, 0) + 1
        
        print("\n[5] Tool usage:")
        if tool_calls_count:
            for tool_name, count in tool_calls_count.items():
                logger.info(f"  • {tool_name}: {count} times")
                print(f"  • {tool_name}: {count} times")
        else:
            logger.warning("  No tool calls found in messages")
            print("  No tool calls found")
        
        # Log last few agent messages for debugging (detailed log only)
        logger.info("-"*80)
        logger.info("AGENT CONVERSATION (last 5 messages)")
        logger.info("-"*80)
        for i, msg in enumerate(messages[-5:], max(1, len(messages)-4)):
            msg_type = type(msg).__name__
            content = str(msg.content) if hasattr(msg, 'content') else str(msg)
            logger.debug(f"[{i}] {msg_type}:")
            logger.debug(f"  {content[:500]}{'...' if len(content) > 500 else ''}")
        
        # Create clean result from parsed data
        clean_result = {
            "loan_id": loan_id,  # We know this from prep_output
            "prep_output_summary": {
                "documents_processed": prep_output.get('documents_processed'),
                "total_documents": prep_output.get('total_documents_found'),
                "fields_in_prep": len(prep_output.get('results', {}).get('field_mappings', {}))
            },
            "corrections_made": corrections_list,
            "total_corrections": len(corrections_list),
            "messages_count": len(messages),
            "agent_ran_successfully": len(messages) > 0,
            "log_file": str(log_file)
        }
        
        print("\n" + "=" * 80)
        print("SUMMARY REPORT")
        print("=" * 80)
        print(f"  Loan ID: {loan_id}")
        print(f"  Documents processed: {prep_output.get('documents_processed')}/{prep_output.get('total_documents_found')}")
        print(f"  Fields in prep output: {len(prep_output.get('results', {}).get('field_mappings', {}))}")
        print(f"  Corrections identified: {len(corrections_list)}")
        print(f"  Agent messages: {len(messages)}")
        print(f"  Status: {'✓ Success' if len(messages) > 0 else '✗ Failed'}")
        
        logger.info("="*80)
        logger.info("SUMMARY REPORT")
        logger.info("="*80)
        logger.info(json.dumps(clean_result, indent=2))
        
        # Save results to file
        output_file = Path(__file__).parent / "verification_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(clean_result, f, indent=2)
        
        print(f"\n📁 Results saved to: {output_file}")
        print(f"📝 Detailed logs saved to: {log_file}")
        
        logger.info(f"Results saved to: {output_file}")
        logger.info("Test completed successfully")
        
    except Exception as e:
        print(f"\n[ERROR] Error during verification: {e}")
        print(f"📝 Check log file for details: {log_file}")
        
        logger.error(f"Error during verification: {e}", exc_info=True)
        import traceback
        traceback.print_exc()


def test_new_workflow():
    """Test the new simplified workflow with compare_prep_vs_encompass_value."""
    print("\n" + "=" * 80)
    print("TESTING NEW WORKFLOW (Prep vs Encompass Comparison)")
    print("=" * 80)
    
    from tools.verification_tools import compare_prep_vs_encompass_value
    from tools.field_lookup_tools import get_missing_field_value
    
    # Load test prep output
    prep_output = load_test_prep_output()
    loan_id = prep_output['loan_id']
    field_mappings = prep_output.get('results', {}).get('field_mappings', {})
    
    print(f"\nLoan ID: {loan_id}")
    print(f"Fields in prep output: {len(field_mappings)}")
    
    # Test a few fields
    test_fields = ["4000", "36", "4002"]  # First name, middle name, last name
    
    for field_id in test_fields:
        if field_id not in field_mappings:
            continue
            
        prep_value = field_mappings[field_id]
        print(f"\n[Test Field {field_id}]")
        print(f"  Prep value: '{prep_value}'")
        
        # Get Encompass value (would normally fetch from API)
        # For testing, simulate by using the prep value
        print(f"  Getting Encompass value...")
        # encompass_result = get_missing_field_value.invoke({
        #     "loan_id": loan_id,
        #     "field_id": field_id
        # })
        # encompass_value = encompass_result.get("value")
        
        # Simulated values for testing
        encompass_value = prep_value  # In reality, might be different
        print(f"  Encompass value: '{encompass_value}'")
        
        # Compare
        comparison = compare_prep_vs_encompass_value.invoke({
            "field_id": field_id,
            "prep_value": prep_value,
            "encompass_value": encompass_value,
            "field_mapping": FIELD_MAPPING
        })
        
        print(f"  Match: {comparison['match']}")
        print(f"  Needs correction: {comparison['needs_correction']}")
        print(f"  Finding: {comparison['finding']}")
        
        if comparison['needs_correction']:
            print(f"  → Would call write_corrected_field to update Encompass")
    
    print("\n[OK] New workflow test complete")


def test_individual_tools():
    """Test individual verification tools."""
    print("\n" + "=" * 80)
    print("TESTING INDIVIDUAL TOOLS")
    print("=" * 80)
    
    from tools.verification_tools import (
        compare_prep_vs_encompass_value,
        verify_field_against_documents,
        cross_check_field_with_sop,
        attempt_field_inference
    )
    from tools.field_lookup_tools import get_field_id_from_name
    
    # Load test data
    prep_output = load_test_prep_output()
    loan_id = prep_output['loan_id']
    
    # Test 1: Get field ID from name
    print("\n[Test 1] Get field ID from name")
    field_name = "Borrower First Name"
    result = get_field_id_from_name.invoke({
        "field_name": field_name,
        "field_mapping": FIELD_MAPPING
    })
    print(f"  Field name '{field_name}' -> ID: {result}")
    
    # Test 2: Verify field against documents
    print("\n[Test 2] Verify field against documents")
    field_id = "4002"  # Borrower First Name
    field_value = "Alva"
    
    # Get extracted documents from prep output
    extracted_docs = {}
    for doc_result in prep_output.get('detailed_results', []):
        doc_type = doc_result.get('document_type', '')
        if doc_type:
            extracted_docs[doc_type] = doc_result.get('extraction', {})
    
    result = verify_field_against_documents.invoke({
        "field_id": field_id,
        "field_value": field_value,
        "loan_id": loan_id,
        "extracted_documents": extracted_docs,
        "field_mapping": FIELD_MAPPING
    })
    print(f"  Verification result:")
    print(f"    Status: {result['status']}")
    print(f"    Finding: {result['finding']}")
    
    # Test 3: Cross-check with SOP
    print("\n[Test 3] Cross-check field with SOP")
    result = cross_check_field_with_sop.invoke({
        "field_id": field_id,
        "field_value": field_value,
        "sop_rules": SOP_RULES,
        "field_mapping": FIELD_MAPPING
    })
    print(f"  SOP validation result:")
    print(f"    SOP Valid: {result['sop_valid']}")
    print(f"    Finding: {result['finding']}")
    
    # Test 4: Attempt field inference
    print("\n[Test 4] Attempt field inference (for missing field)")
    missing_field_id = "1402"  # Borrower DOB (not in test output)
    result = attempt_field_inference.invoke({
        "field_id": missing_field_id,
        "available_documents": extracted_docs,
        "field_mapping": FIELD_MAPPING
    })
    print(f"  Inference result:")
    print(f"    Inferred: {result['inferred']}")
    print(f"    Finding: {result['finding']}")
    
    print("\n[OK] Individual tool tests complete")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Verification Sub-Agent")
    parser.add_argument(
        "--test-tools",
        action="store_true",
        help="Test individual tools instead of full agent"
    )
    parser.add_argument(
        "--test-new-workflow",
        action="store_true",
        help="Test the new simplified workflow (prep vs Encompass comparison)"
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Disable dry run mode and ACTUALLY WRITE to Encompass (use with caution!)"
    )
    
    args = parser.parse_args()
    
    # Handle dry run mode setting
    if args.no_dry_run:
        import os
        os.environ["DRY_RUN"] = "false"
        print("\n⚠️⚠️⚠️  DRY RUN DISABLED - Will write to Encompass! ⚠️⚠️⚠️\n")
    
    if args.test_new_workflow:
        test_new_workflow()
    elif args.test_tools:
        test_individual_tools()
    else:
        main()

