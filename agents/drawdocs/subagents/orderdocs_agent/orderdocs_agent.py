"""
OrderDocs Agent - Runs Mavent compliance checks and orders closing documents

This agent implements the complete workflow for:
1. Running Mavent compliance checks (Loan Audit)
2. Ordering closing documents through Encompass
3. Delivering documents to eFolder

Based on: MAVENT_AND_ORDER_DOCS_GUIDE.md and test_mavent.py/test_order_docs.py
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Load environment variables
try:
    from dotenv import load_dotenv
    env_paths = [
        Path(__file__).parent.parent.parent.parent / ".env",
        Path(__file__).parent.parent.parent.parent.parent / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            break
except ImportError:
    pass

# Add MCP server to path for imports
mcp_server_path = Path(__file__).parent.parent.parent.parent.parent / "encompass-mcp-server"
if mcp_server_path.exists():
    sys.path.insert(0, str(mcp_server_path))
    # Load MCP server .env
    mcp_env = mcp_server_path / ".env"
    if mcp_env.exists():
        load_dotenv(mcp_env, override=False)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Try to import primitives HTTP client (which works for API calls)
PRIMITIVES_AVAILABLE = False
try:
    from agents.drawdocs.tools.primitives import _get_http_client
    PRIMITIVES_AVAILABLE = True
    logger.info("[OrderDocs] ✓ Primitives HTTP client available")
except ImportError as e:
    logger.warning(f"[OrderDocs] Primitives not available: {e}")
    # Try alternative import path
    try:
        import sys
        from pathlib import Path
        tools_path = Path(__file__).parent.parent.parent / "tools"
        sys.path.insert(0, str(tools_path.parent))
        from drawdocs.tools.primitives import _get_http_client
        PRIMITIVES_AVAILABLE = True
        logger.info("[OrderDocs] ✓ Primitives HTTP client available (alt path)")
    except ImportError as e2:
        logger.warning(f"[OrderDocs] Primitives alt import also failed: {e2}")


def _make_api_request(method: str, path: str, json_body: Any = None) -> Dict[str, Any]:
    """Make an API request using the primitives HTTP client.
    
    This uses the same working HTTP client that primitives.py uses.
    
    Returns:
        Dict with keys: status_code, headers, body
    """
    if not PRIMITIVES_AVAILABLE:
        raise RuntimeError("Primitives HTTP client not available")
    
    try:
        http_client = _get_http_client()
        token = http_client.auth_manager.get_client_credentials_token()
        
        headers = {"Content-Type": "application/json"} if json_body else {}
        
        response = http_client.request(
            method=method,
            path=path,
            token=token,
            headers=headers,
            json_body=json_body
        )
        
        # Parse response
        status_code = response.status_code
        resp_headers = dict(response.headers) if hasattr(response, 'headers') else {}
        
        # Try to parse body as JSON
        body = {}
        if hasattr(response, 'text') and response.text:
            try:
                body = json.loads(response.text)
            except json.JSONDecodeError:
                body = {"raw": response.text}
        elif hasattr(response, 'json'):
            try:
                body = response.json()
            except:
                pass
        
        return {
            "status_code": status_code,
            "headers": resp_headers,
            "body": body
        }
        
    except Exception as e:
        logger.error(f"[_make_api_request] Error: {e}")
        raise


def _poll_until_complete(
    location_path: str,
    max_attempts: int = 30,
    poll_interval: int = 2,
    resource_type: str = "resource"
) -> Dict[str, Any]:
    """Poll a resource until it completes.
    
    Args:
        location_path: Path to poll (from Location header)
        max_attempts: Maximum number of polling attempts
        poll_interval: Seconds between polls
        resource_type: Type of resource (for logging)
        
    Returns:
        Final resource data
    """
    logger.info(f"[POLL] Polling {resource_type} at: {location_path}")
    
    for attempt in range(1, max_attempts + 1):
        try:
            # Make GET request using primitives HTTP client
            response = _make_api_request("GET", location_path)
            status_code = response.get("status_code")
            data = response.get("body", {})
            
            if status_code != 200:
                logger.warning(f"[POLL] Attempt {attempt}/{max_attempts}: HTTP {status_code}")
                time.sleep(poll_interval)
                continue
            
            status = (data.get('status', '') or 'Unknown').lower()
            logger.info(f"[POLL] Attempt {attempt}/{max_attempts}: {resource_type} status = {status}")
            
            # Check if complete
            if status == 'completed':
                logger.info(f"[POLL] {resource_type} completed successfully!")
                return data
            
            # Check if failed
            if status in ['failed', 'error']:
                logger.error(f"[POLL] {resource_type} failed!")
                return {"status": "Failed", "error": data.get('error', 'Unknown error'), "body": data}
            
            # Wait before next poll
            if attempt < max_attempts:
                time.sleep(poll_interval)
            
        except Exception as e:
            logger.error(f"[POLL] Error polling {resource_type}: {e}")
            if attempt < max_attempts:
                time.sleep(poll_interval)
            else:
                raise
    
    logger.warning(f"[POLL] {resource_type} did not complete after {max_attempts} attempts")
    return {"status": "Timeout", "error": "Polling timeout"}


def run_mavent_check(
    loan_id: str,
    application_id: Optional[str] = None,
    audit_type: str = "closing",
    dry_run: bool = False
) -> Dict[str, Any]:
    """Run Mavent compliance check (Loan Audit).
    
    Based on test_mavent.py implementation.
    
    Args:
        loan_id: Encompass loan GUID
        application_id: Borrower application ID (optional, defaults to loan_id)
        audit_type: "closing" or "opening"
        dry_run: If True, don't actually make API calls
        
    Returns:
        Dictionary with audit results:
        {
            "audit_id": "...",
            "status": "Completed",
            "issues": [...],
            "location": "...",
            "error": null
        }
    """
    logger.info(f"[MAVENT] Starting Mavent check for loan {loan_id[:8]}... (type: {audit_type})")
    
    if not PRIMITIVES_AVAILABLE:
        return {"error": "Primitives HTTP client not available", "status": "Error"}
    
    if dry_run:
        logger.warning("[MAVENT] DRY RUN - Not making actual API calls")
        return {
            "audit_id": "dry-run-audit-id",
            "status": "Completed",
            "issues": [],
            "location": "/encompassdocs/v1/documentAudits/closing/dry-run-audit-id",
            "error": None,
            "dry_run": True
        }
    
    try:
        # Default application_id to loan_id if not provided
        if not application_id:
            application_id = loan_id
        
        # Step 1: Create Loan Audit (same as test_mavent.py)
        audit_endpoint = f"/encompassdocs/v1/documentAudits/{audit_type}"
        audit_body = {
            "entity": {
                "entityId": loan_id,
                "entityType": "urn:elli:encompass:loan"
            },
            "scope": {
                "entityId": application_id,
                "entityType": "urn:elli:encompass:loan:borrower"
            }
        }
        
        logger.info(f"[MAVENT] Creating audit: POST {audit_endpoint}")
        response = _make_api_request("POST", audit_endpoint, json_body=audit_body)
        
        status_code = response.get("status_code")
        headers = response.get("headers", {})
        body = response.get("body", {})
        
        # Accept 200, 201, and 202 (Accepted - async processing)
        if status_code not in [200, 201, 202]:
            logger.error(f"[MAVENT] Error creating audit: HTTP {status_code}")
            logger.error(f"[MAVENT] Response: {body}")
            return {"error": f"Failed to create audit: HTTP {status_code}", "status": "Error", "details": body}
        
        # Extract Location header and audit ID
        location = headers.get('Location') or headers.get('location', '')
        audit_id = body.get('id', '')
        
        if not audit_id:
            logger.error("[MAVENT] Failed to get audit ID from response")
            return {"error": "Failed to create audit - no ID returned", "status": "Error"}
        
        logger.info(f"[MAVENT] ✓ Audit created: {audit_id}")
        logger.info(f"[MAVENT] Location: {location}")
        
        # Step 2: Poll until audit completes
        if location:
            audit_data = _poll_until_complete(
                location_path=location,
                max_attempts=30,
                poll_interval=2,
                resource_type="Mavent Audit"
            )
        else:
            # If no location header, the audit might be synchronous
            audit_data = body
        
        # Step 3: Check for issues
        issues = audit_data.get('issues', [])
        status = audit_data.get('status', 'Unknown')
        
        if issues:
            logger.warning(f"[MAVENT] Found {len(issues)} compliance issues")
            for i, issue in enumerate(issues[:5]):  # Show first 5
                issue_type = issue.get('type', 'N/A')
                issue_desc = issue.get('description', 'N/A')
                logger.warning(f"[MAVENT] Issue {i+1}: {issue_type}: {issue_desc}")
        else:
            logger.info("[MAVENT] ✓ No compliance issues found")
        
        return {
            "audit_id": audit_id,
            "status": status,
            "issues": issues,
            "location": location,
            "audit_data": audit_data,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"[MAVENT] Error running Mavent check: {e}")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "status": "Error"
        }


def order_documents(
    loan_id: str,
    audit_id: str,
    order_type: str = "closing",
    print_mode: str = "LoanData",
    dry_run: bool = False
) -> Dict[str, Any]:
    """Order closing or opening documents.
    
    Based on test_order_docs.py implementation.
    
    Args:
        loan_id: Encompass loan GUID
        audit_id: Audit snapshot ID from Mavent check
        order_type: "closing" or "opening"
        print_mode: "LoanData" or other print mode
        dry_run: If True, don't actually make API calls
        
    Returns:
        Dictionary with order results:
        {
            "doc_set_id": "...",
            "status": "Completed",
            "documents": [...],
            "location": "...",
            "error": null
        }
    """
    logger.info(f"[ORDER_DOCS] Ordering {order_type} documents for loan {loan_id[:8]}...")
    logger.info(f"[ORDER_DOCS] Using audit ID: {audit_id}")
    
    if not PRIMITIVES_AVAILABLE:
        return {"error": "Primitives HTTP client not available", "status": "Error"}
    
    if dry_run:
        logger.warning("[ORDER_DOCS] DRY RUN - Not making actual API calls")
        return {
            "doc_set_id": "dry-run-docset-id",
            "status": "Completed",
            "documents": [],
            "location": f"/encompassdocs/v1/documentOrders/{order_type}/dry-run-docset-id",
            "error": None,
            "dry_run": True
        }
    
    try:
        # Step 1: Create Document Order
        order_endpoint = f"/encompassdocs/v1/documentOrders/{order_type}"
        order_body = {
            "auditId": audit_id,
            "printMode": print_mode
        }
        
        logger.info(f"[ORDER_DOCS] Creating order: POST {order_endpoint}")
        response = _make_api_request("POST", order_endpoint, json_body=order_body)
        
        status_code = response.get("status_code")
        headers = response.get("headers", {})
        body = response.get("body", {})
        
        # Accept 200, 201, and 202 (Accepted - async processing)
        if status_code not in [200, 201, 202]:
            logger.error(f"[ORDER_DOCS] Error creating order: HTTP {status_code}")
            logger.error(f"[ORDER_DOCS] Response: {body}")
            return {"error": f"Failed to create order: HTTP {status_code}", "status": "Error", "details": body}
        
        # Extract Location header and doc set ID
        location = headers.get('Location') or headers.get('location', '')
        doc_set_id = body.get('id', '')
        
        if not doc_set_id:
            logger.error("[ORDER_DOCS] Failed to get doc set ID from response")
            return {"error": "Failed to create order - no ID returned", "status": "Error"}
        
        logger.info(f"[ORDER_DOCS] ✓ Order created: {doc_set_id}")
        logger.info(f"[ORDER_DOCS] Location: {location}")
        
        # Step 2: Poll until order completes
        if location:
            order_data = _poll_until_complete(
                location_path=location,
                max_attempts=30,
                poll_interval=2,
                resource_type="Document Order"
            )
        else:
            order_data = body
        
        # Step 3: Get document list
        documents = order_data.get('documents', [])
        status = order_data.get('status', 'Unknown')
        
        if documents:
            logger.info(f"[ORDER_DOCS] ✓ Order contains {len(documents)} documents")
            for i, doc in enumerate(documents[:5]):  # Show first 5
                doc_id = doc.get('id', 'N/A')
                doc_type = doc.get('type', 'N/A')
                doc_title = doc.get('title', 'N/A')
                logger.info(f"[ORDER_DOCS] Document {i+1}: {doc_type}: {doc_title}")
            if len(documents) > 5:
                logger.info(f"[ORDER_DOCS] ... and {len(documents) - 5} more")
        else:
            logger.warning("[ORDER_DOCS] No documents in order")
        
        return {
            "doc_set_id": doc_set_id,
            "status": status,
            "documents": documents,
            "location": location,
            "order_data": order_data,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"[ORDER_DOCS] Error ordering documents: {e}")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "status": "Error"
        }


def deliver_documents(
    doc_set_id: str,
    order_type: str = "closing",
    delivery_method: str = "eFolder",
    recipients: Optional[List[str]] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Request delivery of ordered documents.
    
    Based on test_order_docs.py implementation.
    
    Args:
        doc_set_id: Document set ID from order_documents
        order_type: "closing" or "opening"
        delivery_method: "eFolder", "Email", "Print", etc.
        recipients: Optional list of recipient emails
        dry_run: If True, don't actually make API calls
        
    Returns:
        Dictionary with delivery results
    """
    logger.info(f"[DELIVER] Requesting delivery for docSetId {doc_set_id}")
    logger.info(f"[DELIVER] Method: {delivery_method}")
    
    if not PRIMITIVES_AVAILABLE:
        return {"error": "Primitives HTTP client not available", "status": "Error"}
    
    if dry_run:
        logger.warning("[DELIVER] DRY RUN - Not making actual API calls")
        return {
            "status": "Success",
            "delivery_method": delivery_method,
            "error": None,
            "dry_run": True
        }
    
    try:
        # Create delivery request
        delivery_endpoint = f"/encompassdocs/v1/documentOrders/{order_type}/{doc_set_id}/delivery"
        delivery_body = {
            "deliveryMethod": delivery_method
        }
        
        if recipients:
            delivery_body["recipients"] = recipients
        
        logger.info(f"[DELIVER] Requesting delivery: POST {delivery_endpoint}")
        response = _make_api_request("POST", delivery_endpoint, json_body=delivery_body)
        
        status_code = response.get("status_code")
        body = response.get("body", {})
        
        if status_code in [200, 201]:
            logger.info("[DELIVER] ✓ Delivery requested successfully")
            logger.info(f"[DELIVER] Documents will be delivered via {delivery_method}")
            return {
                "status": "Success",
                "delivery_method": delivery_method,
                "response": body,
                "error": None
            }
        else:
            logger.error(f"[DELIVER] Error requesting delivery: HTTP {status_code}")
            logger.error(f"[DELIVER] Response: {body}")
            return {
                "status": "Error",
                "error": f"Delivery failed: HTTP {status_code}",
                "details": body
            }
        
    except Exception as e:
        logger.error(f"[DELIVER] Error requesting delivery: {e}")
        return {
            "error": str(e),
            "status": "Error"
        }


def run_orderdocs_agent(
    loan_id: str,
    application_id: Optional[str] = None,
    audit_type: str = "closing",
    order_type: str = "closing",
    delivery_method: str = "eFolder",
    recipients: Optional[List[str]] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Run the complete Order Docs Agent workflow.
    
    This executes:
    1. Mavent compliance check (Loan Audit)
    2. Document ordering
    3. Document delivery
    
    Args:
        loan_id: Encompass loan GUID
        application_id: Borrower application ID (optional)
        audit_type: "closing" or "opening"
        order_type: "closing" or "opening"
        delivery_method: "eFolder", "Email", "Print", etc.
        recipients: Optional list of recipient emails
        dry_run: If True, don't actually make API calls
        
    Returns:
        Dictionary with complete workflow results
    """
    logger.info("=" * 80)
    logger.info("[ORDERDOCS AGENT] Starting Order Docs Agent workflow")
    logger.info(f"[ORDERDOCS AGENT] Loan ID: {loan_id}")
    logger.info(f"[ORDERDOCS AGENT] Type: {order_type}")
    logger.info(f"[ORDERDOCS AGENT] Dry Run: {dry_run}")
    logger.info("=" * 80)
    
    start_time = datetime.now()
    results = {
        "loan_id": loan_id,
        "start_time": start_time.isoformat(),
        "dry_run": dry_run,
        "steps": {},
        "preflight_warnings": []  # Warnings about loan readiness
    }
    
    try:
        # Pre-flight check: Verify loan readiness flags
        logger.info("\n[PRE-FLIGHT] Checking loan readiness for closing docs...")
        try:
            from agents.drawdocs.tools.primitives import get_loan_context
            loan_context = get_loan_context(loan_id)
            flags = loan_context.get("flags", {})
            
            # Check critical flags for closing document ordering
            preflight_checks = [
                ("is_ctc", "Clear to Close", flags.get("is_ctc", False)),
                ("cd_approved", "Closing Disclosure Approved", flags.get("cd_approved", False)),
                ("cd_acknowledged", "Closing Disclosure Acknowledged", flags.get("cd_acknowledged", False)),
            ]
            
            for flag_id, flag_name, flag_value in preflight_checks:
                if not flag_value:
                    warning = {
                        "flag": flag_id,
                        "name": flag_name,
                        "status": False,
                        "message": f"{flag_name} is not complete - closing documents may fail to generate"
                    }
                    results["preflight_warnings"].append(warning)
                    logger.warning(f"[PRE-FLIGHT] ⚠️ {warning['message']}")
                else:
                    logger.info(f"[PRE-FLIGHT] ✓ {flag_name}: Complete")
            
            if results["preflight_warnings"]:
                logger.warning(f"[PRE-FLIGHT] Found {len(results['preflight_warnings'])} warning(s) - proceeding anyway")
            else:
                logger.info("[PRE-FLIGHT] ✓ All readiness checks passed")
                
        except Exception as preflight_error:
            logger.warning(f"[PRE-FLIGHT] Could not verify loan flags: {preflight_error}")
        
        # Step 1: Run Mavent Check
        logger.info("\n[STEP 1/3] Running Mavent compliance check...")
        mavent_result = run_mavent_check(
            loan_id=loan_id,
            application_id=application_id,
            audit_type=audit_type,
            dry_run=dry_run
        )
        results["steps"]["mavent_check"] = mavent_result
        
        # Check for errors (can be in "error" field or "status" field)
        mavent_status = str(mavent_result.get("status", "")).lower()
        mavent_error = mavent_result.get("error") or mavent_result.get("audit_data", {}).get("error")
        
        if mavent_result.get("error") or mavent_status in ["failed", "error"]:
            error_msg = mavent_result.get("error") or f"Mavent check status: {mavent_status}"
            if mavent_error and isinstance(mavent_error, dict):
                error_msg = f"{mavent_error.get('summary', 'Unknown error')}: {mavent_error.get('details', '')}"
            logger.error(f"[ORDERDOCS AGENT] Mavent check failed: {error_msg}")
            # Don't return early - continue to try ordering (some loans may work)
            logger.warning("[ORDERDOCS AGENT] Continuing despite Mavent failure...")
        
        # Check for critical issues
        issues = mavent_result.get("issues", [])
        if issues:
            logger.warning(f"[ORDERDOCS AGENT] Found {len(issues)} compliance issues")
        
        audit_id = mavent_result.get("audit_id")
        if not audit_id:
            logger.error("[ORDERDOCS AGENT] No audit ID returned from Mavent check")
            results["status"] = "Failed"
            results["error"] = "No audit ID returned from Mavent check"
            return results
        
        # Step 2: Order Documents
        logger.info("\n[STEP 2/3] Ordering documents...")
        order_result = order_documents(
            loan_id=loan_id,
            audit_id=audit_id,
            order_type=order_type,
            dry_run=dry_run
        )
        results["steps"]["order_documents"] = order_result
        
        # Check for order errors (can be in "error" field or "status" field)
        order_status = str(order_result.get("status", "")).lower()
        order_error = order_result.get("error") or order_result.get("order_data", {}).get("error")
        
        if order_result.get("error") or order_status in ["failed", "error"]:
            error_msg = order_result.get("error") or f"Document order status: {order_status}"
            if order_error and isinstance(order_error, dict):
                error_msg = f"{order_error.get('summary', 'Unknown error')}: {order_error.get('details', '')}"
            logger.error(f"[ORDERDOCS AGENT] Document ordering failed: {error_msg}")
            # Don't attempt delivery if ordering failed
        
        doc_set_id = order_result.get("doc_set_id")
        documents = order_result.get("documents", [])
        
        if not doc_set_id:
            logger.error("[ORDERDOCS AGENT] No docSetId returned from order")
            results["status"] = "Failed"
            results["error"] = "No docSetId returned from document order"
            return results
        
        # Step 3: Request Delivery (only if documents were generated)
        if not documents or len(documents) == 0:
            logger.warning("[ORDERDOCS AGENT] No documents generated - skipping delivery")
            results["steps"]["deliver_documents"] = {
                "status": "Skipped",
                "error": "No documents to deliver - document generation failed or produced 0 documents"
            }
            results["status"] = "PartialSuccess"
            results["error"] = "Document generation produced 0 documents"
        else:
            logger.info(f"\n[STEP 3/3] Requesting document delivery for {len(documents)} documents...")
            delivery_result = deliver_documents(
                doc_set_id=doc_set_id,
                order_type=order_type,
                delivery_method=delivery_method,
                recipients=recipients,
                dry_run=dry_run
            )
            results["steps"]["deliver_documents"] = delivery_result
            
            if delivery_result.get("error"):
                logger.error(f"[ORDERDOCS AGENT] Document delivery failed: {delivery_result['error']}")
                results["status"] = "PartialSuccess"  # Documents ordered but not delivered
                results["error"] = f"Document delivery failed: {delivery_result['error']}"
            else:
                logger.info("[ORDERDOCS AGENT] ✓ Document delivery requested successfully")
                results["status"] = "Success"
        
        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        results["end_time"] = end_time.isoformat()
        results["duration_seconds"] = duration
        results["summary"] = {
            "audit_id": audit_id,
            "doc_set_id": doc_set_id,
            "compliance_issues": len(issues),
            "documents_ordered": len(order_result.get("documents", [])),
            "delivery_method": delivery_method
        }
        
        logger.info("\n" + "=" * 80)
        logger.info("[ORDERDOCS AGENT] Workflow completed!")
        logger.info(f"[ORDERDOCS AGENT] Status: {results['status']}")
        logger.info(f"[ORDERDOCS AGENT] Duration: {duration:.1f}s")
        logger.info(f"[ORDERDOCS AGENT] Audit ID: {audit_id}")
        logger.info(f"[ORDERDOCS AGENT] Doc Set ID: {doc_set_id}")
        logger.info(f"[ORDERDOCS AGENT] Documents: {len(order_result.get('documents', []))}")
        logger.info("=" * 80 + "\n")
        
        return results
        
    except Exception as e:
        logger.error(f"[ORDERDOCS AGENT] Unexpected error: {e}")
        results["status"] = "Error"
        results["error"] = str(e)
        return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="OrderDocs Agent - Run Mavent checks and order documents"
    )
    parser.add_argument("--loan-id", type=str, required=True, help="Encompass loan GUID")
    parser.add_argument("--application-id", type=str, help="Borrower application ID")
    parser.add_argument("--type", type=str, default="closing", choices=["closing", "opening"],
                       help="Document type (closing or opening)")
    parser.add_argument("--delivery", type=str, default="eFolder", help="Delivery method")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (no API calls)")
    parser.add_argument("--output", type=str, help="Output file for results (JSON)")
    
    args = parser.parse_args()
    
    # Run agent
    result = run_orderdocs_agent(
        loan_id=args.loan_id,
        application_id=args.application_id,
        audit_type=args.type,
        order_type=args.type,
        delivery_method=args.delivery,
        dry_run=args.dry_run
    )
    
    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, indent=2, default=str, fp=f)
        print(f"\n✓ Results saved to: {args.output}")
    else:
        print("\n" + "=" * 80)
        print("RESULTS:")
        print("=" * 80)
        print(json.dumps(result, indent=2, default=str))
