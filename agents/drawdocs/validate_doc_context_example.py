#!/usr/bin/env python3
"""
Example script to validate doc_context against the schema.
This is NOT yet integrated into agents - just for testing the schema.
"""

import json
from pathlib import Path

def validate_doc_context_example():
    """Example of how to validate doc_context against the schema."""
    
    print("\n" + "="*80)
    print("DOC CONTEXT SCHEMA VALIDATION - EXAMPLE")
    print("="*80)
    print("\nThis script shows how to validate doc_context.")
    print("NOTE: This is NOT yet integrated into agents - just a demo!")
    print("="*80 + "\n")
    
    # Check if jsonschema is installed
    try:
        from jsonschema import validate, ValidationError
    except ImportError:
        print("❌ jsonschema not installed")
        print("\nTo use validation, install it:")
        print("  pip install jsonschema")
        return
    
    # Load the schema
    schema_path = Path(__file__).parent / "doc_context_schema.json"
    if not schema_path.exists():
        print(f"❌ Schema file not found: {schema_path}")
        return
    
    with open(schema_path) as f:
        schema = json.load(f)
    
    print(f"✅ Loaded schema from: {schema_path}\n")
    
    # Example 1: Valid doc_context (minimal)
    print("=" * 80)
    print("EXAMPLE 1: Minimal Valid doc_context")
    print("=" * 80)
    
    valid_minimal = {
        "loan_id": "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6",
        "results": {
            "field_mappings": {
                "4000": "John",
                "4002": "Doe"
            },
            "extracted_entities": {
                "ID": {
                    "borrower_first_name": "John",
                    "borrower_last_name": "Doe"
                }
            }
        }
    }
    
    try:
        validate(instance=valid_minimal, schema=schema)
        print("✅ VALID - Minimal doc_context is valid!\n")
        print(json.dumps(valid_minimal, indent=2))
    except ValidationError as e:
        print(f"❌ INVALID: {e.message}")
    
    # Example 2: Valid doc_context (complete)
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Complete Valid doc_context")
    print("=" * 80)
    
    valid_complete = {
        "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
        "total_documents_found": 172,
        "documents_processed": 17,
        "status": "success",
        "results": {
            "field_mappings": {
                "4008": "Christopher Berger and Alva Scott Sorensen",
                "610": "Truly Title, Inc.",
                "356": 290000
            },
            "extracted_entities": {
                "Title Report": {
                    "borrower_vesting_type": "Christopher Berger and Alva Scott Sorensen",
                    "escrow_company_name": "Truly Title, Inc."
                },
                "Appraisal": {
                    "appraised_value": 290000
                }
            }
        },
        "timing": {
            "total_time_seconds": 379.87
        }
    }
    
    try:
        validate(instance=valid_complete, schema=schema)
        print("✅ VALID - Complete doc_context is valid!\n")
        print("(Showing first 500 chars...)")
        print(json.dumps(valid_complete, indent=2)[:500] + "...")
    except ValidationError as e:
        print(f"❌ INVALID: {e.message}")
    
    # Example 3: Invalid doc_context (missing required field)
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Invalid doc_context (missing 'results')")
    print("=" * 80)
    
    invalid_missing_results = {
        "loan_id": "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6",
        "field_mappings": {  # WRONG: Should be under "results"
            "4000": "John"
        }
    }
    
    try:
        validate(instance=invalid_missing_results, schema=schema)
        print("✅ VALID")
    except ValidationError as e:
        print(f"❌ INVALID (Expected): {e.message}")
        print(f"   Path: {' -> '.join(str(p) for p in e.path)}")
    
    # Example 4: Invalid doc_context (wrong loan_id format)
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Invalid doc_context (bad loan_id format)")
    print("=" * 80)
    
    invalid_loan_id = {
        "loan_id": "not-a-valid-uuid",  # Should be UUID format
        "results": {
            "field_mappings": {},
            "extracted_entities": {}
        }
    }
    
    try:
        validate(instance=invalid_loan_id, schema=schema)
        print("✅ VALID")
    except ValidationError as e:
        print(f"❌ INVALID (Expected): {e.message}")
    
    # Example 5: Test with actual prep output
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Validate Actual Prep Output")
    print("=" * 80)
    
    prep_output_path = Path(__file__).parent / "subagents/verification_agent/data/prep_output.json"
    if prep_output_path.exists():
        with open(prep_output_path) as f:
            actual_prep_output = json.load(f)
        
        try:
            validate(instance=actual_prep_output, schema=schema)
            print("✅ VALID - Actual prep output matches schema!")
            print(f"\nValidated output from: {prep_output_path}")
            print(f"  - Loan ID: {actual_prep_output.get('loan_id')}")
            print(f"  - Documents processed: {actual_prep_output.get('documents_processed')}")
            print(f"  - Fields extracted: {len(actual_prep_output.get('results', {}).get('field_mappings', {}))}")
        except ValidationError as e:
            print(f"❌ INVALID: {e.message}")
            print(f"   Path: {' -> '.join(str(p) for p in e.path)}")
            print(f"\n   This means the schema needs adjustment to match actual output!")
    else:
        print(f"⚠️  Prep output not found at: {prep_output_path}")
    
    print("\n" + "=" * 80)
    print("VALIDATION EXAMPLES COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Review the schema (doc_context_schema.json)")
    print("  2. Review the documentation (DOC_CONTEXT_SCHEMA.md)")
    print("  3. Provide feedback on the structure")
    print("  4. Once approved, we'll integrate validation into agents")
    print("="*80 + "\n")


if __name__ == "__main__":
    validate_doc_context_example()

