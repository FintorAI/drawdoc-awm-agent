"""
Unit tests for fetch_loan_context tool.

Tests the loan context retrieval and normalization from Encompass.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys

# Add the loan-officer-assistant directory to path for imports
LOA_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(LOA_DIR))
sys.path.insert(0, str(LOA_DIR.parent.parent))  # Project root for packages.shared

from state import (
    BorrowerFacts,
    LoanFacts,
    PropertyFacts,
)
from tools.fetch_loan_context import (
    _is_populated,
    _normalize_borrower,
    _normalize_property,
    _parse_float,
    _parse_int,
    _parse_bool,
    _compute_scenario_tag,
    _is_mvp_supported,
)


# =============================================================================
# TEST DATA
# =============================================================================

SAMPLE_FIELDS = {
    # Loan identification
    "364": "2512926137",
    "1172": "Conventional",
    "1401": "30-Year Fixed",
    "19": "Purchase",
    
    # Primary borrower
    "4000": "John",
    "4001": "Michael",
    "4002": "Smith",
    "65": "529-55-3694",
    "52": "1985-03-15",
    "1268": "john@example.com",
    "66": "970-631-6317",
    "471": "Married",
    "1523": "U.S. Citizen",
    
    # Borrower address
    "FR0104": "123 Main St",
    "FR0106": "Denver",
    "FR0107": "CO",
    "FR0108": "80202",
    "1402": "3.5",
    
    # Borrower employment
    "BE0015": "Acme Corp",
    "BE0003": "Software Engineer",
    "BE0012": "303-555-1234",
    "BE0002": "N",
    "BE0005": "5",
    
    # Borrower income
    "1759": "8500.00",
    
    # Property
    "11": "456 Oak Ave",
    "12": "Boulder",
    "14": "CO",
    "15": "80301",
    "13": "Boulder",
    "1041": "SingleFamily",
    "1811": "PrimaryResidence",
    
    # Loan amounts
    "1109": "450,000.00",
    "136": "550,000.00",
    "356": "560,000",
    "353": "81.818",
    "3": "6.5",
    "4": "360",
}


# =============================================================================
# PARSING TESTS
# =============================================================================

class TestParseFunctions:
    """Tests for value parsing utilities."""
    
    def test_parse_float_valid(self):
        """Test parsing valid float values."""
        assert _parse_float("100.50") == 100.50
        assert _parse_float("1,234.56") == 1234.56
        assert _parse_float("$500.00") == 500.00
        assert _parse_float("75.5%") == 75.5
        assert _parse_float(100) == 100.0
    
    def test_parse_float_invalid(self):
        """Test parsing invalid float values."""
        assert _parse_float(None) is None
        assert _parse_float("") is None
        assert _parse_float("invalid") is None
    
    def test_parse_int_valid(self):
        """Test parsing valid int values."""
        assert _parse_int("360") == 360
        assert _parse_int("1,234") == 1234
        assert _parse_int(100.9) == 100
    
    def test_parse_int_invalid(self):
        """Test parsing invalid int values."""
        assert _parse_int(None) is None
        assert _parse_int("") is None
    
    def test_parse_bool_valid(self):
        """Test parsing valid boolean values."""
        assert _parse_bool("Y") is True
        assert _parse_bool("Yes") is True
        assert _parse_bool("true") is True
        assert _parse_bool("1") is True
        assert _parse_bool("N") is False
        assert _parse_bool("No") is False
        assert _parse_bool("false") is False
        assert _parse_bool(True) is True
        assert _parse_bool(False) is False
    
    def test_parse_bool_invalid(self):
        """Test parsing invalid boolean values."""
        assert _parse_bool(None) is None
        assert _parse_bool("") is None
    
    def test_is_populated(self):
        """Test field population check."""
        assert _is_populated("value") is True
        assert _is_populated(123) is True
        assert _is_populated(0) is True  # 0 is a valid value
        assert _is_populated([1, 2]) is True
        
        assert _is_populated(None) is False
        assert _is_populated("") is False
        assert _is_populated("   ") is False
        assert _is_populated([]) is False


# =============================================================================
# BORROWER NORMALIZATION TESTS
# =============================================================================

class TestBorrowerNormalization:
    """Tests for borrower data normalization."""
    
    def test_normalize_primary_borrower(self):
        """Test normalizing primary borrower from fields."""
        borrower = _normalize_borrower(SAMPLE_FIELDS, "", "PRIMARY")
        
        assert borrower is not None
        assert borrower.borrower_type == "PRIMARY"
        assert borrower.first_name == "John"
        assert borrower.middle_name == "Michael"
        assert borrower.last_name == "Smith"
        assert borrower.ssn == "529-55-3694"
        assert borrower.dob == "1985-03-15"
        assert borrower.email == "john@example.com"
        assert borrower.phone == "970-631-6317"
        assert borrower.marital_status == "Married"
        assert borrower.employer_name == "Acme Corp"
        assert borrower.is_self_employed is False
        assert borrower.years_on_job == 5.0
    
    def test_normalize_missing_borrower(self):
        """Test normalizing when borrower data is missing."""
        empty_fields = {"4000": "", "4002": None}
        borrower = _normalize_borrower(empty_fields, "", "PRIMARY")
        
        assert borrower is None
    
    def test_normalize_coborrower_not_present(self):
        """Test normalizing co-borrower when not present."""
        borrower = _normalize_borrower(SAMPLE_FIELDS, "", "CO_BORROWER")
        
        # Co-borrower fields not in SAMPLE_FIELDS, should return None
        assert borrower is None


# =============================================================================
# PROPERTY NORMALIZATION TESTS
# =============================================================================

class TestPropertyNormalization:
    """Tests for property data normalization."""
    
    def test_normalize_property(self):
        """Test normalizing property from fields."""
        prop = _normalize_property(SAMPLE_FIELDS)
        
        assert prop is not None
        assert prop.address == "456 Oak Ave"
        assert prop.city == "Boulder"
        assert prop.state == "CO"
        assert prop.zip == "80301"
        assert prop.county == "Boulder"
        assert prop.property_type == "SingleFamily"
        assert prop.occupancy_type == "PrimaryResidence"
    
    def test_normalize_empty_property(self):
        """Test normalizing with no property data."""
        empty_fields = {}
        prop = _normalize_property(empty_fields)
        
        # Should return PropertyFacts with all None values
        assert prop is not None
        assert prop.address is None


# =============================================================================
# SCENARIO TAG TESTS
# =============================================================================

class TestScenarioTag:
    """Tests for scenario tag computation."""
    
    def test_conventional_purchase_primary(self):
        """Test conventional purchase primary residence tag."""
        loan_facts = LoanFacts(
            loan_id="test",
            loan_type="Conventional",
            loan_purpose="Purchase",
            subject_property=PropertyFacts(occupancy_type="PrimaryResidence"),
        )
        
        tag = _compute_scenario_tag(loan_facts)
        assert tag == "CONV_PURCHASE_PRIMARY"
    
    def test_fha_purchase(self):
        """Test FHA purchase tag."""
        loan_facts = LoanFacts(
            loan_id="test",
            loan_type="FHA",
            loan_purpose="Purchase",
            subject_property=PropertyFacts(occupancy_type="PrimaryResidence"),
        )
        
        tag = _compute_scenario_tag(loan_facts)
        assert tag == "FHA_PURCHASE_PRIMARY"
    
    def test_va_refinance(self):
        """Test VA refinance tag."""
        loan_facts = LoanFacts(
            loan_id="test",
            loan_type="VA",
            loan_purpose="Refinance",
            subject_property=PropertyFacts(occupancy_type="PrimaryResidence"),
        )
        
        tag = _compute_scenario_tag(loan_facts)
        assert tag == "VA_REFI_PRIMARY"
    
    def test_investment_property(self):
        """Test investment property tag."""
        loan_facts = LoanFacts(
            loan_id="test",
            loan_type="Conventional",
            loan_purpose="Purchase",
            subject_property=PropertyFacts(occupancy_type="Investment"),
        )
        
        tag = _compute_scenario_tag(loan_facts)
        assert tag == "CONV_PURCHASE_INVESTMENT"


# =============================================================================
# MVP SUPPORT TESTS
# =============================================================================

class TestMVPSupport:
    """Tests for MVP scope checking."""
    
    def test_conventional_is_mvp(self):
        """Conventional loans should be MVP supported."""
        loan_facts = LoanFacts(loan_id="test", loan_type="Conventional")
        assert _is_mvp_supported(loan_facts) is True
    
    def test_fha_not_mvp(self):
        """FHA loans should NOT be MVP supported."""
        loan_facts = LoanFacts(loan_id="test", loan_type="FHA")
        assert _is_mvp_supported(loan_facts) is False
    
    def test_va_not_mvp(self):
        """VA loans should NOT be MVP supported."""
        loan_facts = LoanFacts(loan_id="test", loan_type="VA")
        assert _is_mvp_supported(loan_facts) is False
    
    def test_usda_not_mvp(self):
        """USDA loans should NOT be MVP supported."""
        loan_facts = LoanFacts(loan_id="test", loan_type="USDA")
        assert _is_mvp_supported(loan_facts) is False


# =============================================================================
# INTEGRATION TEST (with mocked API)
# =============================================================================

class TestFetchLoanContextIntegration:
    """Integration tests with mocked Encompass API."""
    
    @pytest.mark.asyncio
    @patch('tools.fetch_loan_context.read_fields')
    @patch('tools.fetch_loan_context._fetch_milestones')
    @patch('tools.fetch_loan_context._fetch_attachments')
    async def test_fetch_loan_context_success(
        self,
        mock_attachments,
        mock_milestones,
        mock_read_fields,
    ):
        """Test successful loan context fetch with mocked API."""
        from tools.fetch_loan_context import fetch_loan_context
        
        # Setup mocks
        mock_read_fields.return_value = SAMPLE_FIELDS
        mock_milestones.return_value = [
            {"milestoneName": "Started", "doneIndicator": True},
            {"milestoneName": "Application", "doneIndicator": False},
        ]
        mock_attachments.return_value = [
            {"id": "doc1", "title": "W-2", "isRemoved": False},
            {"id": "doc2", "title": "Paystub", "isRemoved": False},
        ]
        
        # Execute
        loan_facts = await fetch_loan_context("test-loan-id")
        
        # Verify
        assert loan_facts.loan_id == "test-loan-id"
        assert loan_facts.loan_number == "2512926137"
        assert loan_facts.loan_type == "Conventional"
        assert loan_facts.loan_purpose == "Purchase"
        assert loan_facts.loan_amount == 450000.0
        assert loan_facts.interest_rate == 6.5
        
        assert len(loan_facts.borrowers) == 1
        assert loan_facts.borrowers[0].first_name == "John"
        
        assert loan_facts.subject_property.address == "456 Oak Ave"
        
        assert len(loan_facts.milestones) == 2
        assert len(loan_facts.efolder_docs) == 2
        
        assert loan_facts.scenario_tag == "CONV_PURCHASE_PRIMARY"
        assert loan_facts.is_mvp_supported is True


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

