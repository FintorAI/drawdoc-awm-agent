"""
Test script for Order Docs Agent

Tests the complete workflow:
1. Mavent compliance check
2. Document ordering
3. Document delivery
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from orderdocs_agent import run_orderdocs_agent

def test_orderdocs_workflow():
    """Test the complete Order Docs workflow."""
    
    print("\n" + "=" * 80)
    print("ORDER DOCS AGENT TEST")
    print("=" * 80)
    
    # Test loan ID (from example_input.json)
    loan_id = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6"
    
    print(f"\nLoan ID: {loan_id}")
    print("Running in DRY RUN mode (no actual API calls)\n")
    
    # Run agent in dry-run mode
    result = run_orderdocs_agent(
        loan_id=loan_id,
        audit_type="closing",
        order_type="closing",
        delivery_method="eFolder",
        dry_run=True  # Set to False to make actual API calls
    )
    
    # Print results
    print("\n" + "=" * 80)
    print("TEST RESULTS")
    print("=" * 80)
    
    print(f"\nStatus: {result.get('status')}")
    print(f"Duration: {result.get('duration_seconds', 0):.1f}s")
    
    if result.get('summary'):
        summary = result['summary']
        print(f"\nSummary:")
        print(f"  Audit ID: {summary.get('audit_id')}")
        print(f"  Doc Set ID: {summary.get('doc_set_id')}")
        print(f"  Compliance Issues: {summary.get('compliance_issues', 0)}")
        print(f"  Documents Ordered: {summary.get('documents_ordered', 0)}")
        print(f"  Delivery Method: {summary.get('delivery_method')}")
    
    if result.get('error'):
        print(f"\nError: {result['error']}")
    
    # Save results
    output_file = Path(__file__).parent / "test_orderdocs_output.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"\n✓ Full results saved to: {output_file}")
    print("\n" + "=" * 80)
    
    # Return success/failure
    return result.get('status') in ['Success', 'PartialSuccess']


def test_individual_steps():
    """Test individual workflow steps."""
    from orderdocs_agent import run_mavent_check, order_documents, deliver_documents
    
    print("\n" + "=" * 80)
    print("TESTING INDIVIDUAL STEPS")
    print("=" * 80)
    
    loan_id = "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6"
    
    # Test Step 1: Mavent Check
    print("\n[TEST] Step 1: Mavent Check")
    mavent_result = run_mavent_check(
        loan_id=loan_id,
        audit_type="closing",
        dry_run=True
    )
    print(f"  Status: {mavent_result.get('status')}")
    print(f"  Audit ID: {mavent_result.get('audit_id')}")
    print(f"  Issues: {len(mavent_result.get('issues', []))}")
    
    # Test Step 2: Order Documents
    print("\n[TEST] Step 2: Order Documents")
    order_result = order_documents(
        loan_id=loan_id,
        audit_id=mavent_result.get('audit_id'),
        order_type="closing",
        dry_run=True
    )
    print(f"  Status: {order_result.get('status')}")
    print(f"  Doc Set ID: {order_result.get('doc_set_id')}")
    print(f"  Documents: {len(order_result.get('documents', []))}")
    
    # Test Step 3: Deliver Documents
    print("\n[TEST] Step 3: Deliver Documents")
    delivery_result = deliver_documents(
        doc_set_id=order_result.get('doc_set_id'),
        order_type="closing",
        delivery_method="eFolder",
        dry_run=True
    )
    print(f"  Status: {delivery_result.get('status')}")
    print(f"  Method: {delivery_result.get('delivery_method')}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Order Docs Agent")
    parser.add_argument("--individual", action="store_true", 
                       help="Test individual steps instead of full workflow")
    args = parser.parse_args()
    
    if args.individual:
        test_individual_steps()
    else:
        success = test_orderdocs_workflow()
        sys.exit(0 if success else 1)

