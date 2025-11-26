"""Disclosure Agent for Encompass loan processing.

This agent manages disclosure preparation and review for loans:
1. Verification: Check if required disclosure fields have values
2. Preparation: Clean and populate missing fields using AI
3. Request: Send disclosure to LO for review via email
"""

from .orchestrator_agent import run_disclosure_orchestrator

__all__ = ["run_disclosure_orchestrator"]

