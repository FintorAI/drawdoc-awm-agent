"""Sub-agents for the Disclosure Agent (v2).

v2 agents:
- verification_agent: TRID compliance, form validation, MVP eligibility
- preparation_agent: RegZ-LE updates, MI calculation, CTC matching
- send_agent: Mavent check, ATR/QM check, eDisclosures ordering

Deprecated:
- request_agent: Replaced by send_agent in v2
"""

from .verification_agent import run_disclosure_verification
from .preparation_agent import run_disclosure_preparation
from .send_agent import run_disclosure_send

__all__ = [
    "run_disclosure_verification",
    "run_disclosure_preparation",
    "run_disclosure_send",
]
