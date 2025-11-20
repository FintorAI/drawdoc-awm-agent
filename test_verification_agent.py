"""
Test script for the Verification Sub-Agent.

Loads the test_output.json from prep agent and runs verification.
"""

import json
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.verification_agent import run_verification
from config.field_document_mapping import FIELD_MAPPING
from config.sop_rules import SOP_RULES


def load_test_prep_output() -> dict:
    """Load test output from prep agent."""
    test_file = Path(__file__).parent / "test_output.json"
    
    if not test_file.exists():
        raise FileNotFoundError(f"Test file not found: {test_file}")
    
    with open(test_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    """Main test function."""
    print("=" * 80)
    print("VERIFICATION SUB-AGENT TEST")
    print("=" * 80)
    
    # Load test prep output
    print("\n[1] Loading test prep output...")
    try:
        prep_output = load_test_prep_output()
        print(f"[OK] Loaded prep output for loan: {prep_output['loan_id']}")
        print(f"  - Documents processed: {prep_output['documents_processed']}")
        print(f"  - Total documents: {prep_output['total_documents_found']}")
    except Exception as e:
        print(f"[ERROR] Error loading test output: {e}")
        return
    
    # Show field mapping stats
    print(f"\n[2] Field mapping loaded:")
    print(f"  - Total fields: {len(FIELD_MAPPING)}")
    print(f"  - SOP pages referenced: {len(SOP_RULES.get('page_indexed_rules', {}))}")
    
    # Extract loan_id
    loan_id = prep_output['loan_id']
    
    # Run verification
    print(f"\n[3] Running verification on loan {loan_id}...")
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
        
        # Extract clean results from the agent state
        # The result contains the full agent state including messages
        clean_result = {
            "loan_id": result.get("loan_id"),
            "prep_output_summary": {
                "documents_processed": result.get("prep_output", {}).get("documents_processed"),
                "total_documents": result.get("prep_output", {}).get("total_documents_found")
            },
            "validation_results": result.get("validation_results", []),
            "corrections_made": result.get("corrections_made", []),
            "missing_documents": result.get("missing_documents", []),
            "status": result.get("status", "unknown"),
            "messages_count": len(result.get("messages", []))
        }
        
        # Print results
        print(json.dumps(clean_result, indent=2))
        
        # Also print the agent's messages for debugging
        print("\n" + "-" * 80)
        print("AGENT CONVERSATION:")
        print("-" * 80)
        messages = result.get("messages", [])
        for i, msg in enumerate(messages, 1):
            msg_type = type(msg).__name__
            content = str(msg.content)[:200] if hasattr(msg, 'content') else str(msg)[:200]
            print(f"\n[{i}] {msg_type}:")
            print(f"  {content}{'...' if len(str(msg.content if hasattr(msg, 'content') else msg)) > 200 else ''}")
        
        # Save results to file
        output_file = Path(__file__).parent / "verification_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(clean_result, f, indent=2)
        
        print(f"\n[OK] Results saved to: {output_file}")
        
    except Exception as e:
        print(f"\n[ERROR] Error during verification: {e}")
        import traceback
        traceback.print_exc()


def test_individual_tools():
    """Test individual verification tools."""
    print("\n" + "=" * 80)
    print("TESTING INDIVIDUAL TOOLS")
    print("=" * 80)
    
    from tools.verification_tools import (
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
    
    args = parser.parse_args()
    
    if args.test_tools:
        test_individual_tools()
    else:
        main()

