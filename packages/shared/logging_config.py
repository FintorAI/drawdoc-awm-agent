"""Shared logging configuration for disclosure agents.

Logs to both console and file with structured format for frontend timeline.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional


class TimelineLogFormatter(logging.Formatter):
    """Custom formatter for timeline-friendly logs with agent context."""
    
    def format(self, record):
        """Format log record as structured JSON for easy frontend parsing."""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "agent": getattr(record, "agent", "SYSTEM"),
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter."""
    
    def format(self, record):
        # Add agent context to console output if present
        agent = getattr(record, "agent", None)
        prefix = f"[{agent}] " if agent else ""
        
        # Original format: HH:MM:SS [LEVEL] [logger] message
        return f"{self.formatTime(record, '%H:%M:%S')} [{record.levelname}] {prefix}[{record.name}] {record.getMessage()}"


def setup_logging(
    loan_id: str,
    agent_name: str = "SYSTEM",
    level: int = logging.INFO,
    log_to_file: bool = True
) -> logging.Logger:
    """Setup logging for disclosure agents with file and console output.
    
    Args:
        loan_id: Loan GUID for log file naming
        agent_name: Agent name (VERIFICATION, PREPARATION, SEND, ORCHESTRATOR)
        level: Logging level (default: INFO)
        log_to_file: Whether to write to file (default: True)
        
    Returns:
        Configured logger instance
    """
    # Create logs directory
    project_root = Path(__file__).parent.parent.parent
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Create session-specific log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"disclosure_{loan_id[:8]}_{timestamp}.jsonl"
    
    # Get or create root logger
    logger = logging.getLogger()
    
    # Clear existing handlers to avoid duplicates
    logger.handlers = []
    logger.setLevel(level)
    
    # Console handler (human-readable)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(ConsoleFormatter())
    logger.addHandler(console_handler)
    
    # File handler (JSON lines for frontend parsing)
    if log_to_file:
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # Capture all levels to file
        file_handler.setFormatter(TimelineLogFormatter())
        logger.addHandler(file_handler)
        
        logger.info(f"Logging to: {log_file}")
    
    return logger


class AgentContextFilter(logging.Filter):
    """Add agent context to all log records."""
    
    def __init__(self, agent_name: str):
        super().__init__()
        self.agent_name = agent_name
    
    def filter(self, record):
        # Add agent name to record for formatting
        if not hasattr(record, 'agent'):
            record.agent = self.agent_name
        return True


def add_agent_context(logger: logging.Logger, agent_name: str):
    """Add agent context filter to existing logger.
    
    Args:
        logger: Logger instance
        agent_name: Agent name (VERIFICATION, PREPARATION, SEND, etc.)
    """
    # Remove existing AgentContextFilter if present
    logger.filters = [f for f in logger.filters if not isinstance(f, AgentContextFilter)]
    
    # Add new context filter
    logger.addFilter(AgentContextFilter(agent_name))


def get_recent_logs(loan_id: str = None, limit: int = 100) -> list:
    """Get recent log entries for frontend display.
    
    Args:
        loan_id: Optional loan ID to filter logs
        limit: Maximum number of entries to return
        
    Returns:
        List of log entry dictionaries
    """
    project_root = Path(__file__).parent.parent.parent
    logs_dir = project_root / "logs"
    
    if not logs_dir.exists():
        return []
    
    # Get all log files
    log_files = sorted(logs_dir.glob("disclosure_*.jsonl"), reverse=True)
    
    # Filter by loan_id if provided
    if loan_id:
        log_files = [f for f in log_files if loan_id[:8] in f.name]
    
    entries = []
    
    # Read logs from most recent files first
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        entries.append(entry)
                        if len(entries) >= limit:
                            break
                    except json.JSONDecodeError:
                        continue
            
            if len(entries) >= limit:
                break
        except Exception as e:
            logging.error(f"Error reading log file {log_file}: {e}")
            continue
    
    return entries[:limit]


def get_agent_timeline(loan_id: str) -> dict:
    """Get structured timeline of agent execution for frontend display.
    
    Args:
        loan_id: Loan GUID
        
    Returns:
        Dictionary with timeline data structured by agent
    """
    logs = get_recent_logs(loan_id, limit=1000)
    
    timeline = {
        "loan_id": loan_id,
        "agents": {
            "ORCHESTRATOR": [],
            "VERIFICATION": [],
            "PREPARATION": [],
            "SEND": [],
        },
        "total_entries": len(logs),
    }
    
    for entry in logs:
        agent = entry.get("agent", "SYSTEM")
        if agent in timeline["agents"]:
            timeline["agents"][agent].append(entry)
    
    return timeline

