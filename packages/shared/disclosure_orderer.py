"""Disclosure Orderer for Disclosure Agent.

Per Disclosure Desk SOP:
- Click on eFolder → eDisclosures button
- Select Generic Product and click Order eDisclosures
- Clear any mandatory audits before proceeding

API Flow (from Postman Collection):
1. Audit: POST /encompassdocs/v1/documentAudits/opening
2. Order: POST /encompassdocs/v1/documentOrders/opening
3. Deliver: POST /encompassdocs/v1/documentOrders/opening/{docSetId}/delivery
"""

import logging
import os
import requests
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .auth import get_access_token
from .encompass_io import read_fields

logger = logging.getLogger(__name__)


# =============================================================================
# API CONFIGURATION
# =============================================================================

# Send Encompass Docs endpoints
DOCS_BASE_PATH = "/encompassdocs/v1"
DOCUMENT_AUDITS_OPENING = f"{DOCS_BASE_PATH}/documentAudits/opening"
DOCUMENT_ORDERS_OPENING = f"{DOCS_BASE_PATH}/documentOrders/opening"


# =============================================================================
# ENCOMPASS FIELD IDS
# =============================================================================

class DisclosureFields:
    """Field IDs for disclosure ordering."""
    
    # Loan
    LOAN_ID = "364"  # Loan Number
    
    # Borrower info for delivery
    BORROWER_FIRST_NAME = "4000"
    BORROWER_LAST_NAME = "4002"
    BORROWER_EMAIL = "1240"
    BORROWER_PHONE = "66"
    
    # Co-Borrower
    COBORROWER_FIRST_NAME = "4004"
    COBORROWER_LAST_NAME = "4006"
    COBORROWER_EMAIL = "1268"
    
    # Loan Officer (sender)
    LO_NAME = "317"
    LO_EMAIL = "1862"
    LO_USER_ID = "1612"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class AuditIssue:
    """A single audit issue."""
    
    code: Optional[str] = None
    message: Optional[str] = None
    severity: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass
class AuditResult:
    """Result of document audit."""
    
    success: bool
    audit_id: Optional[str] = None
    has_issues: bool = False
    issues: List[AuditIssue] = field(default_factory=list)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "audit_id": self.audit_id,
            "has_issues": self.has_issues,
            "issues": [i.to_dict() for i in self.issues],
            "error": self.error,
        }


@dataclass
class OrderResult:
    """Result of disclosure ordering."""
    
    success: bool
    tracking_id: Optional[str] = None
    doc_set_id: Optional[str] = None
    audit_id: Optional[str] = None
    documents: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    action: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "tracking_id": self.tracking_id,
            "doc_set_id": self.doc_set_id,
            "audit_id": self.audit_id,
            "documents": self.documents,
            "error": self.error,
            "action": self.action,
            "blocking": not self.success,
        }


# =============================================================================
# DISCLOSURE ORDERER CLASS
# =============================================================================

class DisclosureOrderer:
    """Orders Initial Disclosure packages via eDisclosures API."""
    
    def __init__(self):
        """Initialize disclosure orderer."""
        self.api_base_url = os.getenv("ENCOMPASS_API_BASE_URL", "https://api.elliemae.com")
    
    def order_initial_disclosure(
        self,
        loan_id: str,
        application_id: Optional[str] = None,
        dry_run: bool = True
    ) -> OrderResult:
        """Order Initial Disclosure package.
        
        Full flow:
        1. Audit loan (check for issues)
        2. Create document order
        3. Deliver to borrower
        
        Args:
            loan_id: Encompass loan GUID
            application_id: Application ID (fetched if not provided)
            dry_run: If True, only run audit without ordering
            
        Returns:
            OrderResult with tracking info
        """
        logger.info(f"[DISCLOSURE] Ordering Initial Disclosure for loan {loan_id[:8]}...")
        
        try:
            # Get application ID if not provided
            if application_id is None:
                application_id = self._get_application_id(loan_id)
                if application_id is None:
                    return OrderResult(
                        success=False,
                        error="Could not get application ID from loan",
                        action="Unable to order disclosure - application ID not found"
                    )
            
            # Step 1: Audit loan
            logger.info("[DISCLOSURE] Step 1: Running audit...")
            audit_result = self.audit_loan(loan_id, application_id)
            
            if not audit_result.success:
                return OrderResult(
                    success=False,
                    audit_id=audit_result.audit_id,
                    error=audit_result.error,
                    action="Clear audit issues before ordering"
                )
            
            if audit_result.has_issues:
                issues = [i.message for i in audit_result.issues[:5]]
                return OrderResult(
                    success=False,
                    audit_id=audit_result.audit_id,
                    error=f"Audit has {len(audit_result.issues)} issues",
                    action=f"Clear mandatory audits: {'; '.join(issues)}"
                )
            
            if dry_run:
                logger.info("[DISCLOSURE] [DRY RUN] Audit passed, would proceed with order")
                return OrderResult(
                    success=True,
                    audit_id=audit_result.audit_id,
                    action="[DRY RUN] Ready to order disclosure"
                )
            
            # Step 2: Create document order
            logger.info("[DISCLOSURE] Step 2: Creating document order...")
            doc_set_id = self._create_document_order(audit_result.audit_id)
            
            if doc_set_id is None:
                return OrderResult(
                    success=False,
                    audit_id=audit_result.audit_id,
                    error="Failed to create document order"
                )
            
            # Step 3: Deliver to borrower
            logger.info("[DISCLOSURE] Step 3: Delivering to borrower...")
            delivery_result = self._deliver_package(loan_id, doc_set_id)
            
            if not delivery_result.get("success"):
                return OrderResult(
                    success=False,
                    audit_id=audit_result.audit_id,
                    doc_set_id=doc_set_id,
                    error=delivery_result.get("error", "Failed to deliver package")
                )
            
            logger.info(f"[DISCLOSURE] Success! Tracking ID: {delivery_result.get('tracking_id')}")
            
            return OrderResult(
                success=True,
                tracking_id=delivery_result.get("tracking_id"),
                doc_set_id=doc_set_id,
                audit_id=audit_result.audit_id,
                documents=delivery_result.get("documents", [])
            )
            
        except Exception as e:
            logger.error(f"[DISCLOSURE] Error ordering disclosure: {e}")
            return OrderResult(
                success=False,
                error=str(e),
                action="Error ordering disclosure - see error details"
            )
    
    def audit_loan(self, loan_id: str, application_id: str) -> AuditResult:
        """Run audit before ordering disclosure.
        
        API: POST /encompassdocs/v1/documentAudits/opening
        
        Args:
            loan_id: Encompass loan GUID
            application_id: Application ID (borrower scope)
            
        Returns:
            AuditResult with audit status
        """
        access_token = get_access_token()
        
        url = f"{self.api_base_url}{DOCUMENT_AUDITS_OPENING}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        body = {
            "entity": {
                "entityId": loan_id,
                "entityType": "urn:elli:encompass:loan"
            },
            "scope": {
                "entityId": application_id,
                "entityType": "urn:elli:encompass:loan:borrower"
            },
            "packageTypes": ["AtApp"]  # At Application = Initial Disclosure
        }
        
        try:
            response = requests.post(url, json=body, headers=headers, timeout=120)
            response.raise_for_status()
            
            # Get audit ID from Location header
            location = response.headers.get("Location", "")
            audit_id = location.split("/")[-1] if location else None
            
            # Parse response for issues
            result = response.json() if response.text else {}
            issues = self._parse_audit_issues(result)
            
            return AuditResult(
                success=True,
                audit_id=audit_id,
                has_issues=len(issues) > 0,
                issues=issues
            )
            
        except requests.HTTPError as e:
            logger.error(f"[DISCLOSURE] Audit API error: {e.response.text}")
            return AuditResult(
                success=False,
                error=f"Audit failed: {e.response.status_code}"
            )
        except Exception as e:
            logger.error(f"[DISCLOSURE] Audit error: {e}")
            return AuditResult(
                success=False,
                error=str(e)
            )
    
    def _create_document_order(self, audit_id: str) -> Optional[str]:
        """Create document order from audit.
        
        API: POST /encompassdocs/v1/documentOrders/opening
        
        Args:
            audit_id: Audit snapshot ID from Step 1
            
        Returns:
            Doc set ID, or None if failed
        """
        access_token = get_access_token()
        
        url = f"{self.api_base_url}{DOCUMENT_ORDERS_OPENING}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        body = {
            "auditId": audit_id,
            "printMode": "LoanData"
        }
        
        try:
            response = requests.post(url, json=body, headers=headers, timeout=120)
            response.raise_for_status()
            
            # Get doc set ID from Location header
            location = response.headers.get("Location", "")
            doc_set_id = location.split("/")[-1] if location else None
            
            # Or from response body
            if not doc_set_id:
                result = response.json() if response.text else {}
                doc_set_id = result.get("id")
            
            return doc_set_id
            
        except Exception as e:
            logger.error(f"[DISCLOSURE] Create order error: {e}")
            return None
    
    def _deliver_package(self, loan_id: str, doc_set_id: str) -> Dict[str, Any]:
        """Deliver disclosure package to borrower.
        
        API: POST /encompassdocs/v1/documentOrders/opening/{docSetId}/delivery
        
        Uses "Without Fulfillment" for electronic-only delivery.
        
        Args:
            loan_id: Encompass loan GUID
            doc_set_id: Document set ID from Step 2
            
        Returns:
            Dictionary with success status and tracking info
        """
        access_token = get_access_token()
        
        url = f"{self.api_base_url}{DOCUMENT_ORDERS_OPENING}/{doc_set_id}/delivery"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        # Get borrower and sender info
        borrower_info = self._get_borrower_info(loan_id)
        sender_info = self._get_sender_info(loan_id)
        
        # Build recipients list
        recipients = []
        
        if borrower_info.get("email"):
            borrower_name = f"{borrower_info.get('first_name', '')} {borrower_info.get('last_name', '')}".strip()
            recipients.append({
                "id": f"Borrower-{borrower_name}",
                "fullName": borrower_name,
                "emailAddress": borrower_info.get("email"),
                "phoneNumber": borrower_info.get("phone", "")
            })
        
        # Add co-borrower if exists
        if borrower_info.get("coborrower_email"):
            coborrower_name = f"{borrower_info.get('coborrower_first_name', '')} {borrower_info.get('coborrower_last_name', '')}".strip()
            recipients.append({
                "id": f"CoBorrower-{coborrower_name}",
                "fullName": coborrower_name,
                "emailAddress": borrower_info.get("coborrower_email"),
            })
        
        if not recipients:
            return {
                "success": False,
                "error": "No borrower email found for delivery"
            }
        
        body = {
            "documents": [],  # Empty = all documents in package
            "package": {
                "from": {
                    "fullName": sender_info.get("name", "Disclosure Desk"),
                    "emailAddress": sender_info.get("email", ""),
                    "entityId": sender_info.get("user_id", ""),
                    "entityType": "urn:elli:encompass:user"
                },
                "to": recipients
            }
        }
        
        try:
            response = requests.post(url, json=body, headers=headers, timeout=120)
            response.raise_for_status()
            
            result = response.json() if response.text else {}
            
            return {
                "success": True,
                "tracking_id": result.get("id") or result.get("trackingId"),
                "documents": result.get("documents", [])
            }
            
        except requests.HTTPError as e:
            logger.error(f"[DISCLOSURE] Delivery API error: {e.response.text}")
            return {
                "success": False,
                "error": f"Delivery failed: {e.response.status_code}"
            }
        except Exception as e:
            logger.error(f"[DISCLOSURE] Delivery error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_application_id(self, loan_id: str) -> Optional[str]:
        """Get application ID from loan.
        
        The application ID is in the loan's applications array.
        """
        access_token = get_access_token()
        
        url = f"{self.api_base_url}/encompass/v3/loans/{loan_id}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            
            loan = response.json()
            applications = loan.get("applications", [])
            
            if applications:
                return applications[0].get("id")
            
            return None
            
        except Exception as e:
            logger.error(f"[DISCLOSURE] Error getting application ID: {e}")
            return None
    
    def _get_borrower_info(self, loan_id: str) -> Dict[str, Any]:
        """Get borrower info for delivery."""
        field_ids = [
            DisclosureFields.BORROWER_FIRST_NAME,
            DisclosureFields.BORROWER_LAST_NAME,
            DisclosureFields.BORROWER_EMAIL,
            DisclosureFields.BORROWER_PHONE,
            DisclosureFields.COBORROWER_FIRST_NAME,
            DisclosureFields.COBORROWER_LAST_NAME,
            DisclosureFields.COBORROWER_EMAIL,
        ]
        
        values = read_fields(loan_id, field_ids)
        
        return {
            "first_name": values.get(DisclosureFields.BORROWER_FIRST_NAME),
            "last_name": values.get(DisclosureFields.BORROWER_LAST_NAME),
            "email": values.get(DisclosureFields.BORROWER_EMAIL),
            "phone": values.get(DisclosureFields.BORROWER_PHONE),
            "coborrower_first_name": values.get(DisclosureFields.COBORROWER_FIRST_NAME),
            "coborrower_last_name": values.get(DisclosureFields.COBORROWER_LAST_NAME),
            "coborrower_email": values.get(DisclosureFields.COBORROWER_EMAIL),
        }
    
    def _get_sender_info(self, loan_id: str) -> Dict[str, Any]:
        """Get sender (LO) info for delivery."""
        field_ids = [
            DisclosureFields.LO_NAME,
            DisclosureFields.LO_EMAIL,
            DisclosureFields.LO_USER_ID,
        ]
        
        values = read_fields(loan_id, field_ids)
        
        return {
            "name": values.get(DisclosureFields.LO_NAME),
            "email": values.get(DisclosureFields.LO_EMAIL),
            "user_id": values.get(DisclosureFields.LO_USER_ID),
        }
    
    def _parse_audit_issues(self, result: Dict[str, Any]) -> List[AuditIssue]:
        """Parse audit issues from response."""
        issues = []
        
        # Parse from various possible response structures
        audit_issues = result.get("issues", []) or result.get("auditIssues", []) or result.get("errors", [])
        
        for issue in audit_issues:
            issues.append(AuditIssue(
                code=issue.get("code"),
                message=issue.get("message") or issue.get("description"),
                severity=issue.get("severity", "Error")
            ))
        
        return issues


# =============================================================================
# MODULE-LEVEL FUNCTIONS
# =============================================================================

# Singleton instance
_orderer: Optional[DisclosureOrderer] = None


def get_disclosure_orderer() -> DisclosureOrderer:
    """Get the disclosure orderer singleton."""
    global _orderer
    if _orderer is None:
        _orderer = DisclosureOrderer()
    return _orderer


def order_initial_disclosure(
    loan_id: str,
    application_id: Optional[str] = None,
    dry_run: bool = True
) -> Dict[str, Any]:
    """Order Initial Disclosure package.
    
    Convenience function that returns a dictionary.
    
    Args:
        loan_id: Encompass loan GUID
        application_id: Application ID (fetched if not provided)
        dry_run: If True, only run audit without ordering
        
    Returns:
        Dictionary with order results
    """
    orderer = get_disclosure_orderer()
    result = orderer.order_initial_disclosure(loan_id, application_id, dry_run)
    return result.to_dict()


def audit_loan_for_disclosure(loan_id: str, application_id: str) -> Dict[str, Any]:
    """Run disclosure audit for a loan.
    
    Convenience function.
    
    Args:
        loan_id: Encompass loan GUID
        application_id: Application ID
        
    Returns:
        Dictionary with audit results
    """
    orderer = get_disclosure_orderer()
    result = orderer.audit_loan(loan_id, application_id)
    return result.to_dict()

