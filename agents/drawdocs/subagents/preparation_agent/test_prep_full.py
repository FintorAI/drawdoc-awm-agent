"""
Test the full Prep Agent workflow with example input.
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment from PROJECT ROOT first
from dotenv import load_dotenv
env_file = project_root / ".env"
print(f"\nLoading environment from: {env_file}\n")
load_dotenv(env_file)

# Now import the prep agent
from agents.drawdocs.subagents.preparation_agent.preparation_agent import process_from_json

# Load sample input
input_file = Path(__file__).parent / "example_input.json"
with open(input_file, 'r') as f:
    input_data = json.load(f)

print("=" * 80)
print("PREPARATION AGENT - FULL WORKFLOW TEST")
print("=" * 80)
print(f"\nInput:")
print(json.dumps(input_data, indent=2))
print("\nStarting...\n")

# Run the agent
result = process_from_json(input_data)

print("\n" + "=" * 80)
print("RESULT SUMMARY")
print("=" * 80)
print(f"\nLoan ID: {result.get('loan_id')}")
print(f"Total documents found: {result.get('total_documents', 0)}")
print(f"Total documents processed: {len(result.get('results', {}).get('documents', []))}")

if 'error' in result:
    print(f"\n❌ Error: {result['error']}")
else:
    print(f"\n✅ Success!")
    
    # Show field mappings summary
    field_mappings = result.get('results', {}).get('field_mappings', {})
    if field_mappings:
        print(f"\nField mappings extracted: {len(field_mappings)}")
        print("\nSample field mappings:")
        for i, (field_id, value) in enumerate(list(field_mappings.items())[:10]):
            print(f"  {field_id}: {str(value)[:60]}{'...' if len(str(value)) > 60 else ''}")
    
    # Show documents processed
    documents = result.get('results', {}).get('documents', [])
    if documents:
        print(f"\nDocuments processed:")
        for doc in documents:
            doc_type = doc.get('document_type', 'Unknown')
            status = doc.get('status', 'unknown')
            field_count = len(doc.get('field_mappings', {}))
            print(f"  - {doc_type}: {status} ({field_count} fields)")

# Save output
output_file = Path(__file__).parent / "prep_full_test_output.json"
with open(output_file, 'w') as f:
    json.dump(result, f, indent=2, default=str)
print(f"\n✓ Full output saved to: {output_file}")
print("=" * 80)

