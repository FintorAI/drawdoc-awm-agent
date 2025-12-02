"""
OrderDocs Agent - Runs Mavent compliance checks and orders closing documents

This agent implements the complete workflow for:
1. Running Mavent compliance checks (Loan Audit)
2. Ordering closing documents through Encompass
3. Delivering documents to eFolder

Based on: MAVENT_AND_ORDER_DOCS_GUIDE.md
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


def _get_mcp_client():
    """Get MCP server client for Encompass API calls."""
    try:
        # Import MCP server utilities
        mcp_server_path = Path(__file__).parent.parent.parent.parent.parent / "encompass-mcp-server"
        
        if not mcp_server_path.exists():
            logger.error(f"MCP server not found at: {mcp_server_path}")
            return None
        
        sys.path.insert(0, str(mcp_server_path))
        
        # Load MCP server .env
        mcp_env_path = mcp_server_path / ".env"
        if mcp_env_path.exists():
            load_dotenv(mcp_env_path, override=False)
        
        from encompass_http_client import EncompassHttpClient
        from encompass_auth import EncompassAuthManager
        
        # Initialize auth manager
        api_server = os.getenv("ENCOMPASS_API_SERVER", "https://concept.api.elliemae.com")
        api_host = api_server.replace("https://", "").replace("http://", "")
        
        auth_manager = EncompassAuthManager(api_server=api_server)
        
        # Initialize HTTP client
        http_client = EncompassHttpClient(
            auth_manager=auth_manager,
            api_host=api_host
        )
        
        return http_client
        
    except Exception as e:
        logger.error(f"Failed to initialize MCP client: {e}")
        return None


def _poll_until_complete(
    client,
    location_path: str,
    max_attempts: int = 60,
    poll_interval: int = 5,
    resource_type: str = "resource"
) -> Dict[str, Any]:
    """Poll a resource until it completes.
    
    Args:
        client: MCP HTTP client
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
            # Make GET request
            response = client.make_request(
                method="GET",
                path=location_path,
                token_source="client_credentials"
            )
            
            # Parse response
            if isinstance(response, dict) and 'body' in response:
                data = json.loads(response['body']) if isinstance(response['body'], str) else response['body']
            else:
                data = response
            
            status = data.get('status', 'Unknown')
            logger.info(f"[POLL] Attempt {attempt}/{max_attempts}: {resource_type} status = {status}")
            
            # Check if complete
            if status in ['Completed', 'Complete', 'Success']:
                logger.info(f"[POLL] {resource_type} completed successfully!")
                return data
            
            # Check if failed
            if status in ['Failed', 'Error']:
                logger.error(f"[POLL] {resource_type} failed!")
                return data
            
            # Wait before next poll
            if attempt < max_attempts:
                logger.debug(f"[POLL] Waiting {poll_interval}s before next poll...")
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
        # Get MCP client
        client = _get_mcp_client()
        if not client:
            return {"error": "Failed to initialize MCP client", "status": "Error"}
        
        # Default application_id to loan_id if not provided
        if not application_id:
            application_id = loan_id
        
        # Step 1: Create Loan Audit
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
        response = client.make_request(
            method="POST",
            path=audit_endpoint,
            token_source="client_credentials",
            json_body=audit_body
        )
        
        # Parse response
        if isinstance(response, dict):
            location = response.get('headers', {}).get('Location', '')
            body = response.get('body', {})
            if isinstance(body, str):
                body = json.loads(body)
            audit_id = body.get('id', '')
        else:
            location = ''
            audit_id = ''
        
        if not location or not audit_id:
            logger.error("[MAVENT] Failed to get audit location or ID from response")
            return {"error": "Failed to create audit", "status": "Error"}
        
        logger.info(f"[MAVENT] Audit created: {audit_id}")
        logger.info(f"[MAVENT] Polling location: {location}")
        
        # Step 2: Poll until audit completes
        audit_data = _poll_until_complete(
            client=client,
            location_path=location,
            max_attempts=60,
            poll_interval=5,
            resource_type="Mavent Audit"
        )
        
        # Step 3: Check for issues
        issues = audit_data.get('issues', [])
        status = audit_data.get('status', 'Unknown')
        
        if issues:
            logger.warning(f"[MAVENT] Found {len(issues)} compliance issues")
            for i, issue in enumerate(issues[:5]):  # Show first 5
                logger.warning(f"[MAVENT] Issue {i+1}: {issue}")
        else:
            logger.info("[MAVENT] No compliance issues found")
        
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
        # Get MCP client
        client = _get_mcp_client()
        if not client:
            return {"error": "Failed to initialize MCP client", "status": "Error"}
        
        # Step 1: Create Document Order
        order_endpoint = f"/encompassdocs/v1/documentOrders/{order_type}"
        order_body = {
            "auditId": audit_id,
            "printMode": print_mode
        }
        
        logger.info(f"[ORDER_DOCS] Creating order: POST {order_endpoint}")
        response = client.make_request(
            method="POST",
            path=order_endpoint,
            token_source="client_credentials",
            json_body=order_body
        )
        
        # Parse response
        if isinstance(response, dict):
            location = response.get('headers', {}).get('Location', '')
            body = response.get('body', {})
            if isinstance(body, str):
                body = json.loads(body)
            doc_set_id = body.get('id', '')
        else:
            location = ''
            doc_set_id = ''
        
        if not location or not doc_set_id:
            logger.error("[ORDER_DOCS] Failed to get order location or docSetId from response")
            return {"error": "Failed to create order", "status": "Error"}
        
        logger.info(f"[ORDER_DOCS] Order created: {doc_set_id}")
        logger.info(f"[ORDER_DOCS] Polling location: {location}")
        
        # Step 2: Poll until order completes
        order_data = _poll_until_complete(
            client=client,
            location_path=location,
            max_attempts=120,  # Document generation can take longer
            poll_interval=5,
            resource_type="Document Order"
        )
        
        # Step 3: Get document list
        documents = order_data.get('documents', [])
        status = order_data.get('status', 'Unknown')
        
        if documents:
            logger.info(f"[ORDER_DOCS] Order contains {len(documents)} documents")
            for i, doc in enumerate(documents[:5]):  # Show first 5
                doc_name = doc.get('name', 'Unknown')
                logger.info(f"[ORDER_DOCS] Document {i+1}: {doc_name}")
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
    
    if dry_run:
        logger.warning("[DELIVER] DRY RUN - Not making actual API calls")
        return {
            "status": "Success",
            "delivery_method": delivery_method,
            "error": None,
            "dry_run": True
        }
    
    try:
        # Get MCP client
        client = _get_mcp_client()
        if not client:
            return {"error": "Failed to initialize MCP client", "status": "Error"}
        
        # Create delivery request
        delivery_endpoint = f"/encompassdocs/v1/documentOrders/{order_type}/{doc_set_id}/delivery"
        delivery_body = {
            "deliveryMethod": delivery_method
        }
        
        if recipients:
            delivery_body["recipients"] = recipients
        
        logger.info(f"[DELIVER] Requesting delivery: POST {delivery_endpoint}")
        response = client.make_request(
            method="POST",
            path=delivery_endpoint,
            token_source="client_credentials",
            json_body=delivery_body
        )
        
        # Parse response
        if isinstance(response, dict):
            body = response.get('body', {})
            if isinstance(body, str):
                body = json.loads(body)
        else:
            body = response
        
        logger.info("[DELIVER] Delivery requested successfully")
        
        return {
            "status": "Success",
            "delivery_method": delivery_method,
            "response": body,
            "error": None
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
        "steps": {}
    }
    
    try:
        # Step 1: Run Mavent Check
        logger.info("\n[STEP 1/3] Running Mavent compliance check...")
        mavent_result = run_mavent_check(
            loan_id=loan_id,
            application_id=application_id,
            audit_type=audit_type,
            dry_run=dry_run
        )
        results["steps"]["mavent_check"] = mavent_result
        
        if mavent_result.get("error"):
            logger.error(f"[ORDERDOCS AGENT] Mavent check failed: {mavent_result['error']}")
            results["status"] = "Failed"
            results["error"] = f"Mavent check failed: {mavent_result['error']}"
            return results
        
        # Check for critical issues
        issues = mavent_result.get("issues", [])
        if issues:
            logger.warning(f"[ORDERDOCS AGENT] Found {len(issues)} compliance issues")
            # For now, continue anyway (in production, might want to halt here)
        
        audit_id = mavent_result.get("audit_id")
        if not audit_id:
            logger.error("[ORDERDOCS AGENT] No audit ID returned from Mavent check")
            results["status"] = "Failed"
            results["error"] = "No audit ID returned"
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
        
        if order_result.get("error"):
            logger.error(f"[ORDERDOCS AGENT] Document ordering failed: {order_result['error']}")
            results["status"] = "Failed"
            results["error"] = f"Document ordering failed: {order_result['error']}"
            return results
        
        doc_set_id = order_result.get("doc_set_id")
        if not doc_set_id:
            logger.error("[ORDERDOCS AGENT] No docSetId returned from order")
            results["status"] = "Failed"
            results["error"] = "No docSetId returned"
            return results
        
        # Step 3: Request Delivery
        logger.info("\n[STEP 3/3] Requesting document delivery...")
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
