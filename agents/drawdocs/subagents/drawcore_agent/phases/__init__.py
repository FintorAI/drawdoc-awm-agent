"""
Phase processors for Docs Draw Core Agent.

Each phase is responsible for updating a specific category of Encompass fields:
- Phase 1: Borrower & LO
- Phase 2: Contacts & Vendors
- Phase 3: Property & Program
- Phase 4: Financial Setup
- Phase 5: Closing Disclosure
"""

from .phase1_borrower_lo import process_borrower_lo_phase
from .phase2_contacts import process_contacts_phase
from .phase3_property import process_property_phase
from .phase4_financial import process_financial_phase
from .phase5_cd import process_cd_phase

__all__ = [
    'process_borrower_lo_phase',
    'process_contacts_phase',
    'process_property_phase',
    'process_financial_phase',
    'process_cd_phase',
]

