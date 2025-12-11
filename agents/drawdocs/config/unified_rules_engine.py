"""
Unified Rule Engine for DrawDocs

Consolidates all business rules into a single, extensible system:
- Discrepancy detection rules
- SOP condition checks
- Pre-flight validation
- Insurance validation
- State-specific rules
- Loan-type specific rules

Features:
- Prerequisites (loan type, state, purpose)
- Auto-generate PTF conditions
- Severity levels (CRITICAL, HIGH, MEDIUM, LOW)
- Self-documenting with SOP references
- Easy to extend and test

Created: December 9, 2025
"""

from typing import Dict, List, Optional, Any, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & DATA CLASSES
# ============================================================================

class RuleSeverity(str, Enum):
    """Severity levels for rule violations"""
    CRITICAL = "CRITICAL"  # Hard stop - must fix before proceeding
    HIGH = "HIGH"          # PTF condition - must acknowledge before funding
    MEDIUM = "MEDIUM"      # Warning - log and continue
    LOW = "LOW"            # Info only
    IGNORE = "IGNORE"      # Known acceptable variance


class RuleCategory(str, Enum):
    """Categories for organizing rules"""
    DISCREPANCY = "Data Discrepancy"
    MISSING_DOC = "Missing Document"
    INSURANCE = "Insurance Issue"
    VESTING = "Vesting Issue"
    PROPERTY = "Property Information"
    BORROWER = "Borrower Information"
    FINANCIAL = "Financial Discrepancy"
    COMPLIANCE = "Compliance Check"
    PREFLIGHT = "Pre-flight Check"
    STATE_SPECIFIC = "State Specific Rule"
    LOAN_TYPE = "Loan Type Rule"
    OTHER = "Other"


@dataclass
class RulePrerequisites:
    """Prerequisites that determine when a rule should be checked"""
    loan_types: List[str] = field(default_factory=lambda: ["ALL"])  # FHA, VA, CONV, NON_QM, ALL
    loan_purposes: List[str] = field(default_factory=lambda: ["ALL"])  # PURCHASE, REFINANCE, CASHOUT, ALL
    states: List[str] = field(default_factory=lambda: ["ALL"])  # CA, TX, FL, ALL
    occupancy_types: List[str] = field(default_factory=lambda: ["ALL"])  # PRIMARY, SECONDARY, INVESTMENT, ALL
    property_types: List[str] = field(default_factory=lambda: ["ALL"])  # SFR, CONDO, TOWNHOUSE, ALL
    min_loan_amount: Optional[float] = None
    max_loan_amount: Optional[float] = None
    custom_condition: Optional[Callable[[Dict[str, Any]], bool]] = None


@dataclass
class PTFCondition:
    """PTF condition to be written if rule fails"""
    category: str  # From RuleCategory
    description_template: str  # Can use {field_name}, {extracted}, {encompass}, etc.
    assigned_to: str = "Loan Processor"
    severity: str = "PTF"  # PTF, HOLD, INFO


@dataclass
class RuleResult:
    """Result of rule execution"""
    rule_id: str
    rule_name: str
    passed: bool
    severity: str
    category: str
    message: str
    field_id: Optional[str] = None
    field_name: Optional[str] = None
    extracted_value: Optional[Any] = None
    encompass_value: Optional[Any] = None
    expected_value: Optional[Any] = None
    ptf_condition: Optional[PTFCondition] = None
    sop_reference: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Rule:
    """Base rule definition"""
    rule_id: str
    name: str
    description: str
    category: RuleCategory
    severity: RuleSeverity
    fields_required: List[str]  # Encompass field IDs needed
    validation_function: Callable[[Dict[str, Any], Dict[str, Any]], RuleResult]
    prerequisites: RulePrerequisites = field(default_factory=RulePrerequisites)
    ptf_template: Optional[PTFCondition] = None
    sop_reference: Optional[str] = None
    enabled: bool = True


# ============================================================================
# VALIDATION HELPER FUNCTIONS
# ============================================================================

def normalize_string(value: str) -> str:
    """Normalize string for comparison"""
    if not value:
        return ""
    return re.sub(r'\s+', ' ', value.strip().upper())


def compare_names(extracted: str, encompass: str, ignore_middle_initial: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Compare names with tolerance for middle initials
    
    Returns:
        (is_match, difference_description)
    """
    if not extracted or not encompass:
        return False, "One name is empty"
    
    ext_norm = normalize_string(extracted)
    enc_norm = normalize_string(encompass)
    
    # Exact match
    if ext_norm == enc_norm:
        return True, None
    
    # If ignore middle initial, remove single letters
    if ignore_middle_initial:
        ext_no_mi = re.sub(r'\b[A-Z]\b', '', ext_norm).strip()
        enc_no_mi = re.sub(r'\b[A-Z]\b', '', enc_norm).strip()
        
        if ext_no_mi == enc_no_mi:
            return True, None  # Only middle initial difference
    
    # Name mismatch
    return False, f"Name mismatch: '{extracted}' vs '{encompass}'"


def compare_addresses(extracted: str, encompass: str) -> Tuple[bool, Optional[str]]:
    """
    Compare addresses with fuzzy matching for acceptable variances
    
    Returns:
        (is_match, difference_description)
    """
    if not extracted or not encompass:
        return False, "One address is empty"
    
    # Normalize both
    ext_norm = normalize_string(extracted)
    enc_norm = normalize_string(encompass)
    
    # Exact match
    if ext_norm == enc_norm:
        return True, None
    
    # Check if only difference is suffix (DR vs DRIVE)
    address_suffixes = {
        "DR": "DRIVE", "DRIVE": "DR",
        "AVE": "AVENUE", "AVENUE": "AVE",
        "ST": "STREET", "STREET": "ST",
        "RD": "ROAD", "ROAD": "RD",
        "LN": "LANE", "LANE": "LN",
        "BLVD": "BOULEVARD", "BOULEVARD": "BLVD",
    }
    
    for short, long in address_suffixes.items():
        if ext_norm.replace(short, long) == enc_norm or ext_norm == enc_norm.replace(short, long):
            return True, None  # Acceptable variance
    
    # Substantive difference
    return False, f"Address mismatch: '{extracted}' vs '{encompass}'"


def compare_amounts(extracted: Any, encompass: Any, tolerance: float = 0) -> Tuple[bool, Optional[str]]:
    """
    Compare monetary amounts with optional tolerance
    
    Args:
        tolerance: Maximum acceptable difference (0 = no tolerance)
    
    Returns:
        (is_match, difference_description)
    """
    try:
        # Convert to float
        ext_val = float(str(extracted).replace('$', '').replace(',', ''))
        enc_val = float(str(encompass).replace('$', '').replace(',', ''))
        
        diff = abs(ext_val - enc_val)
        
        if diff <= tolerance:
            return True, None
        
        return False, f"Amount mismatch: ${ext_val:,.2f} vs ${enc_val:,.2f} (diff: ${diff:,.2f})"
    
    except (ValueError, TypeError):
        return False, f"Cannot compare amounts: '{extracted}' vs '{encompass}'"


def parse_date(date_value: Any) -> Optional[datetime]:
    """Parse date from various formats"""
    if not date_value:
        return None
    
    try:
        if 'T' in str(date_value):
            return datetime.fromisoformat(str(date_value).split('T')[0])
        else:
            return datetime.strptime(str(date_value)[:10], "%Y-%m-%d")
    except Exception as e:
        logger.error(f"Date parsing error: {e}")
        return None


# ============================================================================
# RULE ENGINE
# ============================================================================

class UnifiedRuleEngine:
    """Central rule engine that manages and executes all business rules"""
    
    def __init__(self):
        self.rules: Dict[str, Rule] = {}
        self._register_default_rules()
    
    def register_rule(self, rule: Rule) -> None:
        """Register a new rule"""
        if rule.rule_id in self.rules:
            logger.warning(f"Overwriting existing rule: {rule.rule_id}")
        self.rules[rule.rule_id] = rule
        logger.info(f"Registered rule: {rule.rule_id} - {rule.name}")
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get a rule by ID"""
        return self.rules.get(rule_id)
    
    def list_rules(
        self,
        category: Optional[RuleCategory] = None,
        severity: Optional[RuleSeverity] = None,
        enabled_only: bool = True
    ) -> List[Rule]:
        """List all rules, optionally filtered"""
        rules = list(self.rules.values())
        
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        
        if category:
            rules = [r for r in rules if r.category == category]
        
        if severity:
            rules = [r for r in rules if r.severity == severity]
        
        return rules
    
    def check_prerequisites(
        self,
        rule: Rule,
        loan_context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if rule prerequisites are met
        
        Returns:
            (should_run, skip_reason)
        """
        prereqs = rule.prerequisites
        
        # Check loan type
        loan_type = loan_context.get("loan_type", "").upper()
        if "ALL" not in prereqs.loan_types and loan_type:
            if loan_type not in prereqs.loan_types:
                return False, f"Loan type {loan_type} not in {prereqs.loan_types}"
        
        # Check loan purpose
        loan_purpose = loan_context.get("loan_purpose", "").upper()
        if "ALL" not in prereqs.loan_purposes and loan_purpose:
            if loan_purpose not in prereqs.loan_purposes:
                return False, f"Loan purpose {loan_purpose} not in {prereqs.loan_purposes}"
        
        # Check state
        state = loan_context.get("state", "").upper()
        if "ALL" not in prereqs.states and state:
            if state not in prereqs.states:
                return False, f"State {state} not in {prereqs.states}"
        
        # Check occupancy
        occupancy = loan_context.get("occupancy_type", "").upper()
        if "ALL" not in prereqs.occupancy_types and occupancy:
            if occupancy not in prereqs.occupancy_types:
                return False, f"Occupancy {occupancy} not in {prereqs.occupancy_types}"
        
        # Check property type
        prop_type = loan_context.get("property_type", "").upper()
        if "ALL" not in prereqs.property_types and prop_type:
            if prop_type not in prereqs.property_types:
                return False, f"Property type {prop_type} not in {prereqs.property_types}"
        
        # Check loan amount range
        loan_amount = loan_context.get("loan_amount")
        if loan_amount:
            try:
                amount = float(loan_amount)
                if prereqs.min_loan_amount and amount < prereqs.min_loan_amount:
                    return False, f"Loan amount ${amount:,.2f} below min ${prereqs.min_loan_amount:,.2f}"
                if prereqs.max_loan_amount and amount > prereqs.max_loan_amount:
                    return False, f"Loan amount ${amount:,.2f} above max ${prereqs.max_loan_amount:,.2f}"
            except (ValueError, TypeError):
                pass
        
        # Check custom condition
        if prereqs.custom_condition:
            try:
                if not prereqs.custom_condition(loan_context):
                    return False, "Custom prerequisite condition not met"
            except Exception as e:
                logger.error(f"Custom prerequisite check failed: {e}")
                return False, f"Custom prerequisite error: {str(e)}"
        
        return True, None
    
    def execute_rule(
        self,
        rule_id: str,
        field_values: Dict[str, Any],
        loan_context: Dict[str, Any]
    ) -> Optional[RuleResult]:
        """
        Execute a single rule
        
        Args:
            rule_id: ID of rule to execute
            field_values: Dict of Encompass field IDs and their values
            loan_context: Dict with loan metadata (loan_type, state, etc.)
        
        Returns:
            RuleResult or None if rule not found/not applicable
        """
        rule = self.get_rule(rule_id)
        if not rule:
            logger.error(f"Rule not found: {rule_id}")
            return None
        
        if not rule.enabled:
            logger.debug(f"Rule {rule_id} is disabled, skipping")
            return None
        
        # Check prerequisites
        should_run, skip_reason = self.check_prerequisites(rule, loan_context)
        if not should_run:
            logger.debug(f"Skipping rule {rule_id}: {skip_reason}")
            return None
        
        # Check if all required fields are present and have values
        missing_fields = []
        for field_id in rule.fields_required:
            if field_id not in field_values:
                missing_fields.append(field_id)
            else:
                value = field_values[field_id]
                # Consider None, empty string, or whitespace-only as missing
                if value is None or (isinstance(value, str) and value.strip() == ""):
                    missing_fields.append(field_id)
        
        if missing_fields:
            logger.debug(f"Rule {rule_id} skipped - missing/empty required fields: {missing_fields}")
            # Return None to skip this rule instead of treating it as a failure
            # This prevents false positives when data simply wasn't extracted
            return None
        
        # Execute validation function
        try:
            result = rule.validation_function(field_values, loan_context)
            result.sop_reference = rule.sop_reference
            return result
        except Exception as e:
            logger.error(f"Rule {rule_id} execution failed: {e}", exc_info=True)
            return RuleResult(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                passed=False,
                severity=RuleSeverity.CRITICAL.value,
                category=rule.category.value,
                message=f"Rule execution error: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def execute_all_rules(
        self,
        field_values: Dict[str, Any],
        loan_context: Dict[str, Any],
        category: Optional[RuleCategory] = None,
        severity: Optional[RuleSeverity] = None
    ) -> List[RuleResult]:
        """
        Execute all applicable rules
        
        Args:
            field_values: Dict of Encompass field IDs and their values
            loan_context: Dict with loan metadata
            category: Optional filter by category
            severity: Optional filter by severity
        
        Returns:
            List of RuleResults
        """
        rules_to_run = self.list_rules(category=category, severity=severity, enabled_only=True)
        
        logger.info(f"Executing {len(rules_to_run)} rules...")
        
        results = []
        for rule in rules_to_run:
            result = self.execute_rule(rule.rule_id, field_values, loan_context)
            if result:  # Only include if rule was actually executed
                results.append(result)
        
        # Summary
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)
        critical = sum(1 for r in results if not r.passed and r.severity == RuleSeverity.CRITICAL.value)
        
        logger.info(f"Rule execution complete: {passed} passed, {failed} failed ({critical} critical)")
        
        return results
    
    def get_failed_rules(
        self,
        results: List[RuleResult],
        severity: Optional[RuleSeverity] = None
    ) -> List[RuleResult]:
        """Get only failed rules, optionally filtered by severity"""
        failed = [r for r in results if not r.passed]
        
        if severity:
            failed = [r for r in failed if r.severity == severity.value]
        
        return failed
    
    def generate_ptf_conditions(self, results: List[RuleResult]) -> List[Dict[str, Any]]:
        """
        Generate PTF conditions from rule results
        
        Returns:
            List of PTF conditions ready to write to Encompass
        """
        ptf_conditions = []
        
        for result in results:
            if not result.passed and result.ptf_condition:
                # Format the description
                description = result.ptf_condition.description_template.format(
                    field_name=result.field_name or "Unknown",
                    extracted=result.extracted_value or "N/A",
                    encompass=result.encompass_value or "N/A",
                    expected=result.expected_value or "N/A",
                    message=result.message
                )
                
                ptf_conditions.append({
                    "category": result.ptf_condition.category,
                    "description": description,
                    "assigned_to": result.ptf_condition.assigned_to,
                    "severity": result.ptf_condition.severity,
                    "source_rule": result.rule_id,
                    "sop_reference": result.sop_reference
                })
        
        return ptf_conditions
    
    def _register_default_rules(self) -> None:
        """Register all default rules (called at initialization)"""
        # Don't auto-import rule_definitions to avoid circular imports
        # Rules will be registered when rule_definitions is explicitly imported
        logger.debug("Rule engine initialized - rules not yet registered")


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

# Global rule engine instance
_rule_engine_instance: Optional[UnifiedRuleEngine] = None


def get_rule_engine() -> UnifiedRuleEngine:
    """Get the global rule engine instance (singleton pattern)"""
    global _rule_engine_instance
    if _rule_engine_instance is None:
        _rule_engine_instance = UnifiedRuleEngine()
    return _rule_engine_instance

