"""
Example usage of primitive tools for Docs Draw MVP

This file demonstrates how to use the primitive tools in your agents.
"""

from primitives import (
    get_loan_context,
    list_required_documents,
    download_documents,
    extract_entities_from_docs,
    read_fields,
    write_fields,
    run_compliance_check,
    get_compliance_results,
    order_docs,
    send_closing_package,
    update_milestone,
    log_issue,
)


# =============================================================================
# Example 1: Docs Prep Agent Flow
# =============================================================================

def example_docs_prep_agent(loan_id: str):
    """
    Example implementation of Docs Prep Agent using primitive tools.
    """
    print(f"\n{'='*60}")
    print(f"DOCS PREP AGENT - Loan {loan_id}")
    print(f"{'='*60}\n")
    
    # Step 1: Get loan context
    print("Step 1: Getting loan context...")
    context = get_loan_context(loan_id)
    print(f"  ✓ Loan Number: {context['loan_number']}")
    print(f"  ✓ Loan Type: {context['loan_type']}")
    print(f"  ✓ State: {context['state']}")
    
    # Step 2: Check preconditions
    print("\nStep 2: Checking preconditions...")
    if not context['flags']['is_ctc']:
        print("  ✗ Loan is not CTC - halting")
        log_issue(loan_id, "critical", "Loan is not CTC", context)
        return {"status": "failed", "reason": "Not CTC"}
    print("  ✓ Loan is CTC")
    
    if not context['flags']['cd_approved']:
        print("  ✗ CD not approved - halting")
        log_issue(loan_id, "critical", "CD not approved", context)
        return {"status": "failed", "reason": "CD not approved"}
    print("  ✓ CD is approved")
    
    # Step 3: Get required documents
    print("\nStep 3: Listing required documents...")
    required_docs = list_required_documents(loan_id)
    print(f"  ✓ Found {len(required_docs)} required documents:")
    for doc in required_docs[:5]:
        print(f"    - {doc}")
    if len(required_docs) > 5:
        print(f"    ... and {len(required_docs) - 5} more")
    
    # Step 4: Download documents
    print("\nStep 4: Downloading documents...")
    documents = download_documents(loan_id, required_docs)
    print(f"  ✓ Downloaded {len(documents)} documents")
    
    # Check for missing critical docs
    critical_docs = ["1003", "Approval Final", "MI Certificate"]
    downloaded_categories = [d['category'] for d in documents]
    missing = [doc for doc in critical_docs if doc not in downloaded_categories]
    
    if missing:
        print(f"  ✗ Missing critical documents: {missing}")
        log_issue(loan_id, "critical", f"Missing docs: {missing}", {"missing": missing})
        return {"status": "failed", "reason": f"Missing docs: {missing}"}
    print("  ✓ All critical documents present")
    
    # Step 5: Extract entities
    print("\nStep 5: Extracting entities from documents...")
    doc_context = extract_entities_from_docs(loan_id, documents)
    print(f"  ✓ Extracted entities from {len(documents)} documents")
    print(f"  ✓ Mapped {len(doc_context['all_mapped_fields'])} fields")
    print(f"  ✓ Pending {len(doc_context['all_pending_fields'])} fields")
    print(f"  ✓ Unmapped {len(doc_context['all_unmapped_fields'])} fields")
    
    # Step 6: Return result
    print("\n" + "="*60)
    print("DOCS PREP COMPLETE")
    print("="*60)
    
    return {
        "status": "success",
        "doc_context": doc_context,
        "documents_processed": len(documents)
    }


# =============================================================================
# Example 2: Docs Draw Core Agent - Phase 1 (Borrower)
# =============================================================================

def example_core_agent_phase1(loan_id: str, doc_context: dict):
    """
    Example implementation of Core Agent Phase 1 (Borrower & LO) - DYNAMIC approach.
    """
    print(f"\n{'='*60}")
    print(f"CORE AGENT PHASE 1: Borrower & LO - Loan {loan_id}")
    print(f"{'='*60}\n")
    
    # Step 1: Read current Encompass fields (DYNAMIC - from all_mapped_fields)
    print("Step 1: Reading current Encompass fields...")
    all_mapped = doc_context['all_mapped_fields']
    field_ids = list(all_mapped.keys())
    current_fields = read_fields(loan_id, field_ids)
    print(f"  ✓ Read {len(current_fields)} fields from Encompass")
    
    # Step 2: Compare with doc_context and build updates (DYNAMIC)
    print("\nStep 2: Comparing with document values...")
    updates = []
    issues = []
    
    for field_id, field_info in all_mapped.items():
        doc_value = field_info['value']
        enc_value = current_fields.get(field_id, '')
        field_name = field_info['field_name']
        source_doc = field_info['source_document']
        
        # Check for mismatch
        if doc_value != enc_value:
            # Critical fields (SSN, etc.) - log as issue
            if field_id == "65":  # Borrower SSN
                print(f"  ✗ {field_name} MISMATCH (CRITICAL): '{enc_value}' vs '{doc_value}'")
                issues.append({
                    "severity": "high",
                    "field_id": field_id,
                    "field_name": field_name,
                    "message": f"{field_name} mismatch between document and Encompass",
                    "doc_value": doc_value,
                    "encompass_value": enc_value,
                    "source_document": source_doc
                })
            else:
                # Non-critical fields - update
                print(f"  ⚠ {field_name} mismatch: '{enc_value}' -> '{doc_value}'")
                updates.append({"field_id": field_id, "value": doc_value})
        else:
            print(f"  ✓ {field_name} matches: '{enc_value}'")
    
    # Step 3: Write updates
    if updates:
        print(f"\nStep 3: Writing {len(updates)} field updates to Encompass...")
        success = write_fields(loan_id, updates)
        if success:
            print("  ✓ Updates written successfully")
        else:
            print("  ⚠ Writes disabled (ENABLE_ENCOMPASS_WRITES=false)")
    else:
        print("\nStep 3: No updates needed - all fields match")
    
    # Step 4: Log issues
    if issues:
        print(f"\nStep 4: Logging {len(issues)} issues for review...")
        for issue in issues:
            issue_id = log_issue(
                loan_id,
                issue['severity'],
                issue['message'],
                issue
            )
            print(f"  ✓ Logged issue {issue_id}")
    
    # Step 5: Return phase summary
    print("\n" + "="*60)
    print("PHASE 1 COMPLETE")
    print("="*60)
    
    return {
        "phase": "Borrower & LO",
        "updates_made": len(updates),
        "issues_logged": len(issues),
        "status": "success" if not issues else "warning"
    }


# =============================================================================
# Example 3: Audit & Compliance Agent
# =============================================================================

def example_audit_compliance_agent(loan_id: str):
    """
    Example implementation of Audit & Compliance Agent.
    """
    print(f"\n{'='*60}")
    print(f"AUDIT & COMPLIANCE AGENT - Loan {loan_id}")
    print(f"{'='*60}\n")
    
    # Step 1: Check required fields
    print("Step 1: Checking required field completeness...")
    required_fields = [
        "4000",  # Borrower First Name
        "4002",  # Borrower Last Name
        "65",    # Borrower SSN
        "11",    # Property Address
        "14",    # Property State
        "1109",  # Loan Amount
        "3",     # Note Rate
        "748",   # Closing Date
    ]
    
    field_values = read_fields(loan_id, required_fields)
    
    missing_fields = []
    for field_id, value in field_values.items():
        if not value or value == "":
            missing_fields.append(field_id)
            print(f"  ✗ Missing: {field_id}")
        else:
            print(f"  ✓ Present: {field_id} = '{value}'")
    
    if missing_fields:
        print(f"\n  ✗ FAILED: {len(missing_fields)} required fields missing")
        log_issue(
            loan_id,
            "critical",
            f"Missing required fields: {missing_fields}",
            {"missing_fields": missing_fields}
        )
        return {
            "status": "failed",
            "reason": "Missing required fields",
            "missing_fields": missing_fields
        }
    
    print("\n  ✓ All required fields present")
    
    # Step 2: Run compliance check
    print("\nStep 2: Running Mavent compliance check...")
    job_id = run_compliance_check(loan_id, "Mavent")
    print(f"  ✓ Compliance check started: {job_id}")
    
    # Step 3: Get compliance results
    print("\nStep 3: Getting compliance results...")
    results = get_compliance_results(loan_id, job_id)
    
    if results['status'] == "pass":
        print("  ✓ Compliance check PASSED")
    elif results['status'] == "warning":
        print(f"  ⚠ Compliance check passed with {len(results['issues'])} warnings")
    else:
        print(f"  ✗ Compliance check FAILED with {len(results['issues'])} issues")
    
    # Step 4: Handle issues
    critical_issues = [i for i in results['issues'] if i['severity'] == 'critical']
    
    if critical_issues:
        print(f"\n  ✗ {len(critical_issues)} CRITICAL compliance issues found:")
        for issue in critical_issues:
            print(f"    - {issue['message']}")
            log_issue(loan_id, "critical", issue['message'], issue)
        
        return {
            "status": "failed",
            "reason": "Mavent compliance failures",
            "issues": critical_issues
        }
    
    # Step 5: Success
    print("\n" + "="*60)
    print("AUDIT & COMPLIANCE PASSED")
    print("="*60)
    
    return {
        "status": "success",
        "compliance_status": results['status'],
        "warnings": [i for i in results['issues'] if i['severity'] == 'warning']
    }


# =============================================================================
# Example 4: Order Docs & Distribution
# =============================================================================

def example_order_distribution(loan_id: str):
    """
    Example implementation of Order Docs & Distribution.
    """
    print(f"\n{'='*60}")
    print(f"ORDER DOCS & DISTRIBUTION - Loan {loan_id}")
    print(f"{'='*60}\n")
    
    # Step 1: Order docs
    print("Step 1: Ordering closing documents...")
    result = order_docs(loan_id)
    
    if not result['success']:
        print(f"  ✗ Failed to order docs: {result['error']}")
        log_issue(loan_id, "critical", f"Docs ordering failed: {result['error']}", result)
        return {"status": "failed", "reason": "Docs ordering failed"}
    
    print(f"  ✓ Docs ordered successfully: {result['doc_package_id']}")
    
    # Step 2: Update milestone
    print("\nStep 2: Updating milestone...")
    from datetime import datetime
    today = datetime.now().strftime("%m/%d/%Y")
    success = update_milestone(loan_id, "Finished", f"DOCS Out on {today}")
    
    if success:
        print(f"  ✓ Milestone updated: DOCS Out on {today}")
    else:
        print("  ⚠ Failed to update milestone")
    
    # Step 3: Get recipient emails
    print("\nStep 3: Getting recipient emails...")
    fields = read_fields(loan_id, ["317", "362", "1855", "611", "416"])
    
    # Mock email lookup (in real implementation, would look up user/contact emails)
    recipients = {
        "loan_officer": "lo@lender.com",
        "processor": "processor@lender.com",
        "escrow": "escrow@title.com",
        "title": "title@title.com"
    }
    print(f"  ✓ Found {len(recipients)} recipients")
    
    # Step 4: Send closing package
    print("\nStep 4: Sending closing package...")
    send_result = send_closing_package(loan_id, recipients)
    
    if send_result['success']:
        print(f"  ✓ Package sent to {len(send_result['sent_to'])} recipients")
        for email in send_result['sent_to']:
            print(f"    - {email}")
    else:
        print(f"  ⚠ Failed to send to some recipients:")
        for email in send_result['failed']:
            print(f"    - {email}")
        log_issue(
            loan_id,
            "high",
            f"Failed to send to: {send_result['failed']}",
            send_result
        )
    
    # Step 5: Success
    print("\n" + "="*60)
    print("DOCS ORDERED AND DISTRIBUTED")
    print("="*60)
    
    return {
        "status": "success",
        "doc_package_id": result['doc_package_id'],
        "sent_to": send_result['sent_to'],
        "failed": send_result['failed']
    }


# =============================================================================
# Example 5: Full Orchestrator
# =============================================================================

def example_full_orchestrator(loan_id: str):
    """
    Example of full orchestrator using all agents.
    """
    print(f"\n{'#'*60}")
    print(f"# FULL DOCS DRAW ORCHESTRATOR")
    print(f"# Loan ID: {loan_id}")
    print(f"{'#'*60}\n")
    
    # Agent 1: Docs Prep
    prep_result = example_docs_prep_agent(loan_id)
    
    if prep_result['status'] != 'success':
        print("\n❌ FAILED at Docs Prep stage")
        return {"status": "failed", "stage": "prep", "reason": prep_result['reason']}
    
    doc_context = prep_result['doc_context']
    
    # Agent 2: Docs Draw Core (Phase 1 example)
    core_result = example_core_agent_phase1(loan_id, doc_context)
    
    if core_result['status'] == 'warning':
        print("\n⚠️ Core Agent completed with warnings")
    
    # Agent 3: Audit & Compliance
    audit_result = example_audit_compliance_agent(loan_id)
    
    if audit_result['status'] != 'success':
        print("\n❌ FAILED at Audit & Compliance stage")
        return {
            "status": "failed",
            "stage": "compliance",
            "reason": audit_result['reason']
        }
    
    # Agent 4: Order & Distribution
    distribution_result = example_order_distribution(loan_id)
    
    if distribution_result['status'] != 'success':
        print("\n❌ FAILED at Distribution stage")
        return {
            "status": "failed",
            "stage": "distribution",
            "reason": distribution_result['reason']
        }
    
    # Success!
    print("\n" + "#"*60)
    print("# ✅ DOCS DRAW COMPLETE - SUCCESS!")
    print("#"*60)
    
    return {
        "status": "success",
        "summary": {
            "documents_processed": prep_result['documents_processed'],
            "fields_updated": core_result['updates_made'],
            "issues_logged": core_result['issues_logged'],
            "doc_package_id": distribution_result['doc_package_id'],
            "recipients": distribution_result['sent_to']
        }
    }


# =============================================================================
# Main (for testing)
# =============================================================================

if __name__ == "__main__":
    # Example loan ID (replace with real GUID)
    TEST_LOAN_ID = "abc123-test-guid"
    
    print("="*60)
    print("PRIMITIVE TOOLS - EXAMPLE USAGE")
    print("="*60)
    print("\nRunning examples with test loan ID:", TEST_LOAN_ID)
    print("\nNote: These examples use placeholder data.")
    print("In production, they would interact with real Encompass data.")
    print("="*60)
    
    # Uncomment to run individual examples:
    
    # Example 1: Docs Prep Agent
    # example_docs_prep_agent(TEST_LOAN_ID)
    
    # Example 2: Core Agent Phase 1
    # mock_doc_context = {
    #     "borrowers": [
    #         {"first_name": "John", "last_name": "Smith", "ssn": "123-45-6789"}
    #     ]
    # }
    # example_core_agent_phase1(TEST_LOAN_ID, mock_doc_context)
    
    # Example 3: Audit & Compliance
    # example_audit_compliance_agent(TEST_LOAN_ID)
    
    # Example 4: Order & Distribution
    # example_order_distribution(TEST_LOAN_ID)
    
    # Example 5: Full Orchestrator
    # example_full_orchestrator(TEST_LOAN_ID)
    
    print("\nTo run examples, uncomment the function calls in __main__ section.")



