"""
Orchestrator Agent for the Drawing Docs Agent system.

This orchestrator manages the sequential execution of three sub-agents:
1. Preparation Agent - Extracts field values from loan documents
2. Verification Agent - Verifies and corrects field values
3. Orderdocs Agent - Checks field completeness

The orchestrator provides:
- Automatic demo mode (DRY_RUN) for safe testing
- Retry logic with exponential backoff
- Comprehensive reporting (JSON + human-readable)
- User prompt interpretation
"""

from .orchestrator_agent import (
    run_orchestrator,
    OrchestratorAgent,
    OrchestratorConfig
)

__all__ = ["run_orchestrator", "OrchestratorAgent", "OrchestratorConfig"]

