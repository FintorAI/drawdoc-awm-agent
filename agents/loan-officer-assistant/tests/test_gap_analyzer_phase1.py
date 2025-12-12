"""
Unit tests for gap_analyzer Phase 1 (Data Completeness).

Tests the data gap detection logic against questionnaire requirements.
"""

import json
import pytest
from pathlib import Path

import sys

# Add the loan-officer-assistant directory to path for imports
LOA_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(LOA_DIR))
sys.path.insert(0, str(LOA_DIR.parent.parent))  # Project root for packages.shared

from state import (
    BorrowerFacts,
    GapCategory,
    GapItem,
    GapSeverity,
    GapStatus,
    GapType,
    LoanFacts,
    NeedsListResult,
    PropertyFacts,
)
from tools.gap_analyzer import (
    analyze_data_gaps,
    get_critical_gaps,
    get_gaps_by_category,
    format_gaps_summary,
    _get_field_value,
    _is_field_populated,
    _get_severity,
    _humanize_field,
    _question_applies,
    FIELD_PATH_MAP,
)


# =============================================================================
# TEST DATA
# =============================================================================

def create_complete_loan_facts() -> LoanFacts:
    """Create a LoanFacts with all required fields populated."""
    return LoanFacts(
        loan_id="complete-loan-123",
        loan_type="Conventional",
        loan_purpose="Purchase",
        loan_amount=450000.0,
        purchase_price=550000.0,
        borrowers=[
            BorrowerFacts(
                borrower_type="PRIMARY",
                first_name="John",
                last_name="Smith",
                middle_name="Michael",
                ssn="529-55-3694",
                dob="1985-03-15",
                email="john@example.com",
                phone="970-631-6317",
                marital_status="Married",
                citizenship_status="U.S. Citizen",
                current_address_street="123 Main St",
                current_address_city="Denver",
                current_address_state="CO",
                current_address_zip="80202",
                employer_name="Acme Corp",
                employer_phone="303-555-1234",
                total_monthly_income=8500.0,
            )
        ],
        subject_property=PropertyFacts(
            address="456 Oak Ave",
            city="Boulder",
            state="CO",
            zip="80301",
            property_type="SingleFamily",
            occupancy_type="PrimaryResidence",
        ),
    )


def create_incomplete_loan_facts() -> LoanFacts:
    """Create a LoanFacts with several missing fields."""
    return LoanFacts(
        loan_id="incomplete-loan-456",
        loan_type="Conventional",
        loan_purpose="Purchase",
        loan_amount=450000.0,
        borrowers=[
            BorrowerFacts(
                borrower_type="PRIMARY",
                first_name="John",
                last_name="Smith",
                # Missing: ssn, dob, email, phone
                ssn=None,
                dob=None,
                email=None,
                phone=None,
                marital_status="Separated",  # Triggers conditional
                citizenship_status=None,  # Missing
            )
        ],
        subject_property=PropertyFacts(
            address="456 Oak Ave",
            city="Boulder",
            state="CO",
            zip="80301",
            property_type=None,  # Missing
            occupancy_type="PrimaryResidence",
        ),
    )


# =============================================================================
# FIELD VALUE RESOLUTION TESTS
# =============================================================================

class TestFieldValueResolution:
    """Tests for field value resolution from LoanFacts."""
    
    def test_get_simple_field(self):
        """Test getting a simple top-level field."""
        loan_facts = create_complete_loan_facts()
        
        value = _get_field_value(loan_facts, "loan_type")
        assert value == "Conventional"
        
        value = _get_field_value(loan_facts, "loan_amount")
        assert value == 450000.0
    
    def test_get_nested_field(self):
        """Test getting a nested field with dot notation."""
        loan_facts = create_complete_loan_facts()
        
        value = _get_field_value(loan_facts, "subject_property.city")
        assert value == "Boulder"
        
        value = _get_field_value(loan_facts, "subject_property.property_type")
        assert value == "SingleFamily"
    
    def test_get_array_field(self):
        """Test getting an array element field."""
        loan_facts = create_complete_loan_facts()
        
        value = _get_field_value(loan_facts, "borrowers[0].first_name")
        assert value == "John"
        
        value = _get_field_value(loan_facts, "borrowers[0].ssn")
        assert value == "529-55-3694"
    
    def test_get_missing_field(self):
        """Test getting a field that doesn't exist."""
        loan_facts = create_complete_loan_facts()
        
        value = _get_field_value(loan_facts, "nonexistent.field")
        assert value is None
        
        value = _get_field_value(loan_facts, "borrowers[5].first_name")
        assert value is None
    
    def test_get_null_field(self):
        """Test getting a field with null value."""
        loan_facts = create_incomplete_loan_facts()
        
        value = _get_field_value(loan_facts, "borrowers[0].ssn")
        assert value is None


# =============================================================================
# SEVERITY TESTS
# =============================================================================

class TestSeverity:
    """Tests for severity determination."""
    
    def test_critical_fields(self):
        """Test that critical fields get CRITICAL severity."""
        assert _get_severity("borrower_ssn", {}) == GapSeverity.CRITICAL.value
        assert _get_severity("borrower_dob", {}) == GapSeverity.CRITICAL.value
        assert _get_severity("first_name", {}) == GapSeverity.CRITICAL.value
        assert _get_severity("last_name", {}) == GapSeverity.CRITICAL.value
        assert _get_severity("loan_amount", {}) == GapSeverity.CRITICAL.value
    
    def test_warn_fields(self):
        """Test that warning fields get WARN severity."""
        assert _get_severity("email", {}) == GapSeverity.WARN.value
        assert _get_severity("primary_phone", {}) == GapSeverity.WARN.value
        assert _get_severity("employer_name", {}) == GapSeverity.WARN.value
    
    def test_ssn_suffix_critical(self):
        """Test that fields ending with _ssn are critical."""
        assert _get_severity("co_borrower_ssn", {}) == GapSeverity.CRITICAL.value


# =============================================================================
# HUMANIZE FIELD TESTS
# =============================================================================

class TestHumanizeField:
    """Tests for field name humanization."""
    
    def test_humanize_ssn(self):
        """Test SSN field humanization."""
        assert _humanize_field("borrower_ssn") == "SSN"
    
    def test_humanize_dob(self):
        """Test DOB field humanization."""
        assert _humanize_field("borrower_dob") == "Date of Birth"
    
    def test_humanize_boolean(self):
        """Test boolean field humanization."""
        assert _humanize_field("is_self_employed_boolean") == "Self Employed"
    
    def test_humanize_address(self):
        """Test address field humanization."""
        result = _humanize_field("borrower_current_address_street")
        assert "Current Address Street" in result


# =============================================================================
# GAP ANALYSIS TESTS
# =============================================================================

class TestGapAnalysis:
    """Tests for the main gap analysis function."""
    
    def test_complete_loan_no_gaps(self):
        """Test that a complete loan has minimal gaps."""
        loan_facts = create_complete_loan_facts()
        
        result = analyze_data_gaps(loan_facts)
        
        # Should have few or no critical gaps
        critical = get_critical_gaps(result)
        assert len(critical) == 0, f"Complete loan should have no critical gaps: {[g.field_id for g in critical]}"
    
    def test_incomplete_loan_has_gaps(self):
        """Test that an incomplete loan has expected gaps."""
        loan_facts = create_incomplete_loan_facts()
        
        result = analyze_data_gaps(loan_facts)
        
        assert result.summary.total > 0
        
        # Should detect missing SSN (critical)
        ssn_gaps = [g for g in result.items if g.field_id == "borrower_ssn"]
        assert len(ssn_gaps) > 0, "Should detect missing SSN"
        assert ssn_gaps[0].severity == GapSeverity.CRITICAL.value
    
    def test_gap_item_structure(self):
        """Test that gap items have correct structure."""
        loan_facts = create_incomplete_loan_facts()
        
        result = analyze_data_gaps(loan_facts)
        
        # Check first gap has all required fields
        if result.items:
            gap = result.items[0]
            
            assert gap.id is not None
            assert gap.category is not None
            assert gap.type == GapType.DATA.value
            assert gap.status == GapStatus.MISSING.value
            assert gap.severity in [s.value for s in GapSeverity]
            assert gap.label is not None
            assert gap.reason is not None
    
    def test_result_summary_computed(self):
        """Test that result summary is correctly computed."""
        loan_facts = create_incomplete_loan_facts()
        
        result = analyze_data_gaps(loan_facts)
        
        assert result.summary is not None
        assert result.summary.total == len(result.items)
        assert "DATA" in result.phases_completed
    
    def test_can_proceed_flag(self):
        """Test can_proceed flag based on critical gaps."""
        loan_facts = create_incomplete_loan_facts()
        
        result = analyze_data_gaps(loan_facts)
        
        # If there are critical gaps, can_proceed should be False
        if result.summary.critical_count > 0:
            assert result.summary.can_proceed is False
        else:
            assert result.summary.can_proceed is True


# =============================================================================
# CONDITIONAL REQUIREMENT TESTS
# =============================================================================

class TestConditionalRequirements:
    """Tests for conditional requirement evaluation."""
    
    def test_separated_marital_status(self):
        """Test that separated marital status triggers appropriate conditionals."""
        loan_facts = LoanFacts(
            loan_id="test",
            borrowers=[
                BorrowerFacts(
                    borrower_type="PRIMARY",
                    first_name="John",
                    last_name="Doe",
                    marital_status="Separated",
                )
            ],
        )
        
        # The questionnaire has conditional: 
        # "If borrower_marital_status == 'Separated', collect Separation Agreement document."
        # This is a doc requirement (Phase 2), but the condition evaluation should work
        
        result = analyze_data_gaps(loan_facts)
        
        # Should still process the loan and detect other missing fields
        assert result is not None


# =============================================================================
# HELPER FUNCTION TESTS
# =============================================================================

class TestHelperFunctions:
    """Tests for gap analysis helper functions."""
    
    def test_get_critical_gaps(self):
        """Test filtering critical gaps."""
        loan_facts = create_incomplete_loan_facts()
        
        result = analyze_data_gaps(loan_facts)
        critical = get_critical_gaps(result)
        
        for gap in critical:
            assert gap.severity == GapSeverity.CRITICAL.value
    
    def test_get_gaps_by_category(self):
        """Test filtering gaps by category."""
        loan_facts = create_incomplete_loan_facts()
        
        result = analyze_data_gaps(loan_facts)
        borrower_gaps = get_gaps_by_category(result, GapCategory.BORROWER.value)
        
        for gap in borrower_gaps:
            assert gap.category == GapCategory.BORROWER.value
    
    def test_format_gaps_summary(self):
        """Test human-readable summary formatting."""
        loan_facts = create_incomplete_loan_facts()
        
        result = analyze_data_gaps(loan_facts)
        summary = format_gaps_summary(result)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        
        # Should contain key sections
        if result.summary.critical_count > 0:
            assert "CRITICAL" in summary
    
    def test_format_empty_gaps(self):
        """Test formatting when no gaps exist."""
        result = NeedsListResult(
            phases_completed=["DATA"],
            items=[],
        )
        result.compute_summary()
        
        summary = format_gaps_summary(result)
        assert "No data gaps" in summary


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_loan_facts(self):
        """Test handling of minimally populated LoanFacts."""
        loan_facts = LoanFacts(loan_id="empty-loan")
        
        result = analyze_data_gaps(loan_facts)
        
        # Should handle gracefully and detect many missing fields
        assert result is not None
        assert result.summary.total > 0
    
    def test_no_borrowers(self):
        """Test handling when borrowers list is empty."""
        loan_facts = LoanFacts(
            loan_id="no-borrowers",
            loan_type="Conventional",
            borrowers=[],
        )
        
        result = analyze_data_gaps(loan_facts)
        
        # Should handle gracefully
        assert result is not None
    
    def test_null_property(self):
        """Test handling when property is None."""
        loan_facts = LoanFacts(
            loan_id="no-property",
            loan_type="Conventional",
            subject_property=None,
        )
        
        result = analyze_data_gaps(loan_facts)
        
        # Should handle gracefully and detect missing property fields
        assert result is not None


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

