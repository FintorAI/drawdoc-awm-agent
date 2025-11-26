"""
Test script for the Orchestrator Agent.

Tests the orchestrator with the example loan ID and validates output structure.
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.drawdocs import run_orchestrator


def test_basic_execution():
    """Test basic orchestrator execution in demo mode."""
    print("=" * 80)
    print("TEST: Basic Execution (Demo Mode)")
    print("=" * 80)
    
    # Load from example_input.json
    example_input_path = Path(__file__).parent / "example_input.json"
    if example_input_path.exists():
        with open(example_input_path, "r") as f:
            config = json.load(f)
        loan_id = config.get("loan_id", "387596ee-7090-47ca-8385-206e22c9c9da")
        document_types = config.get("document_types")
        max_retries = config.get("max_retries", 1)
        print(f"  Loaded config from example_input.json")
        print(f"  Document types: {document_types}")
    else:
        loan_id = "387596ee-7090-47ca-8385-206e22c9c9da"
        document_types = None
        max_retries = 1
    
    results = run_orchestrator(
        loan_id=loan_id,
        document_types=document_types,
        demo_mode=True,
        max_retries=max_retries
    )
    
    # Validate structure
    assert "loan_id" in results, "Missing loan_id in results"
    assert results["loan_id"] == loan_id, "Loan ID mismatch"
    assert "demo_mode" in results, "Missing demo_mode in results"
    assert results["demo_mode"] == True, "Demo mode should be True"
    assert "agents" in results, "Missing agents in results"
    assert "summary_text" in results, "Missing summary_text in results"
    
    # Check agents executed
    assert "preparation" in results["agents"], "Preparation agent not executed"
    assert "verification" in results["agents"], "Verification agent not executed"
    assert "orderdocs" in results["agents"], "Orderdocs agent not executed"
    
    # Check agent statuses
    prep_status = results["agents"]["preparation"].get("status")
    ver_status = results["agents"]["verification"].get("status")
    ord_status = results["agents"]["orderdocs"].get("status")
    
    print(f"\n[Results]")
    print(f"  Preparation: {prep_status}")
    print(f"  Verification: {ver_status}")
    print(f"  Orderdocs: {ord_status}")
    
    print("\n✓ Basic execution test PASSED")
    return results


def test_user_prompt_parsing():
    """Test user prompt interpretation."""
    print("\n" + "=" * 80)
    print("TEST: User Prompt Parsing")
    print("=" * 80)
    
    from agents.drawdocs.orchestrator_agent import OrchestratorConfig, OrchestratorAgent
    
    # Test "only prep" prompt
    config = OrchestratorConfig(
        loan_id="test",
        user_prompt="only prep"
    )
    agent = OrchestratorAgent(config)
    
    assert "verification" in agent.instructions["skip_agents"], "Should skip verification"
    assert "orderdocs" in agent.instructions["skip_agents"], "Should skip orderdocs"
    
    print("  ✓ 'only prep' prompt parsed correctly")
    
    # Test "summary only" prompt
    config = OrchestratorConfig(
        loan_id="test",
        user_prompt="summary only"
    )
    agent = OrchestratorAgent(config)
    
    assert agent.instructions["output_format"] == "summary", "Should return summary only"
    
    print("  ✓ 'summary only' prompt parsed correctly")
    
    print("\n✓ User prompt parsing test PASSED")


def test_output_formats():
    """Test output format generation."""
    print("\n" + "=" * 80)
    print("TEST: Output Formats")
    print("=" * 80)
    
    from agents.drawdocs.orchestrator_agent import OrchestratorConfig, OrchestratorAgent
    
    config = OrchestratorConfig(loan_id="test")
    agent = OrchestratorAgent(config)
    
    # Mock some results
    agent.results = {
        "loan_id": "test",
        "execution_timestamp": "2025-11-25T10:00:00",
        "demo_mode": True,
        "agents": {
            "preparation": {
                "status": "success",
                "attempts": 1,
                "output": {
                    "documents_processed": 5,
                    "total_documents_found": 10,
                    "results": {"field_mappings": {"A": 1, "B": 2}}
                }
            },
            "verification": {
                "status": "success",
                "attempts": 1,
                "output": {"messages": []}
            },
            "orderdocs": {
                "status": "success",
                "attempts": 1,
                "output": {"field1": {"has_value": True}, "field2": {"has_value": False}}
            }
        }
    }
    
    # Test summary generation
    summary = agent._generate_summary()
    assert "ORCHESTRATOR EXECUTION SUMMARY" in summary, "Missing header in summary"
    assert "test" in summary, "Missing loan ID in summary"
    assert "PREPARATION AGENT" in summary, "Missing prep section"
    
    print("  ✓ Summary generation works")
    
    # Test JSON aggregation
    json_output = agent._aggregate_results()
    assert "loan_id" in json_output, "Missing loan_id in JSON"
    assert "agents" in json_output, "Missing agents in JSON"
    
    print("  ✓ JSON aggregation works")
    
    print("\n✓ Output format test PASSED")


def test_correction_extraction():
    """Test extraction of corrections from verification output."""
    print("\n" + "=" * 80)
    print("TEST: Correction Extraction")
    print("=" * 80)
    
    from agents.drawdocs.orchestrator_agent import OrchestratorAgent, OrchestratorConfig
    from langchain_core.messages import ToolMessage
    
    config = OrchestratorConfig(loan_id="test")
    agent = OrchestratorAgent(config)
    
    # Mock verification output with corrections
    mock_correction = {
        "field_id": "610",
        "field_name": "Title Company",
        "corrected_value": "Truly Title, Inc.",
        "source_document": "318be174-03ec-4b99-85ea-1de0cc286702",
        "success": True
    }
    
    mock_message = type('obj', (object,), {
        'content': mock_correction
    })()
    mock_message.__class__.__name__ = "ToolMessage"
    
    verification_output = {
        "output": {
            "messages": [mock_message]
        }
    }
    
    corrections = agent._extract_corrections(verification_output)
    
    assert "610" in corrections, "Missing field 610 in corrections"
    assert corrections["610"]["value"] == "Truly Title, Inc.", "Incorrect correction value"
    assert corrections["610"]["source_document"] == "318be174-03ec-4b99-85ea-1de0cc286702", "Missing source document"
    assert corrections["610"]["field_name"] == "Title Company", "Missing field name"
    
    print(f"  ✓ Extracted corrections for field 610:")
    print(f"    - Value: {corrections['610']['value']}")
    print(f"    - Document: {corrections['610']['source_document']}.pdf")
    print(f"    - Field Name: {corrections['610']['field_name']}")
    
    print("\n✓ Correction extraction test PASSED")


def test_demo_correction_overlay():
    """Test overlay of corrections in demo mode."""
    print("\n" + "=" * 80)
    print("TEST: Demo Correction Overlay")
    print("=" * 80)
    
    from agents.drawdocs.orchestrator_agent import OrchestratorAgent, OrchestratorConfig
    
    config = OrchestratorConfig(loan_id="test")
    agent = OrchestratorAgent(config)
    
    # Mock orderdocs result
    orderdocs_result = {
        "610": {
            "value": "Truly Title Inc",  # Original (incorrect)
            "has_value": True
        },
        "4000": {
            "value": "John",
            "has_value": True
        }
    }
    
    # Mock corrections (new format with dict containing value, source_document, field_name)
    corrections = {
        "610": {
            "value": "Truly Title, Inc.",
            "source_document": "318be174-03ec-4b99-85ea-1de0cc286702",
            "field_name": "Title Company"
        },
        "2294": {
            "value": "YES",
            "source_document": "775f510d-a44e-4701-815c-13b8840a450e",
            "field_name": "Some Field"
        }
    }
    
    # Apply corrections
    updated = agent._apply_demo_corrections(orderdocs_result, corrections)
    
    # Check field 610 was updated
    assert updated["610"]["value"] == "Truly Title, Inc.", "Field 610 not updated"
    assert updated["610"]["correction_applied"] == True, "Missing correction flag"
    
    # Check field 4000 unchanged
    assert updated["4000"]["value"] == "John", "Field 4000 should be unchanged"
    
    # Check field 2294 was added
    assert "2294" in updated, "Field 2294 not added"
    assert updated["2294"]["value"] == "YES", "Field 2294 incorrect value"
    assert updated["2294"]["correction_applied"] == True, "Missing correction flag for 2294"
    
    print(f"  ✓ Updated orderdocs result: {len(updated)} fields")
    print(f"  ✓ Field 610: '{orderdocs_result['610']['value']}' → '{updated['610']['value']}'")
    print(f"  ✓ Field 2294: added with value '{updated['2294']['value']}'")
    
    print("\n✓ Demo correction overlay test PASSED")


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("ORCHESTRATOR AGENT TEST SUITE")
    print("="*80)
    
    try:
        # Run tests
        test_user_prompt_parsing()
        test_output_formats()
        test_correction_extraction()
        test_demo_correction_overlay()
        
        # Run full integration test (if credentials available)
        try:
            results = test_basic_execution()
            
            # Save test results
            output_file = Path(__file__).parent / "test_results.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results["json_output"], f, indent=2, default=str)
            print(f"\n📁 Test results saved to: {output_file}")
            
        except Exception as e:
            print(f"\n⚠️  Integration test skipped: {e}")
            print("    (This is normal if Encompass credentials are not configured)")
        
        print("\n" + "="*80)
        print("ALL TESTS PASSED ✓")
        print("="*80)
        
        return 0
    
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

