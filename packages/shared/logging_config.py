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


def log_agent_messages(messages: list, agent_name: str, logger: logging.Logger = None):
    """Log LLM agent messages to make logs more human-readable.
    
    Args:
        messages: List of agent messages from LangChain/LangGraph
        agent_name: Name of the agent (VERIFICATION, PREPARATION, SEND)
        logger: Logger instance (uses root logger if None)
    """
    if logger is None:
        logger = logging.getLogger()
    
    for i, message in enumerate(messages):
        try:
            # Handle different message types
            message_type = type(message).__name__
            
            # HumanMessage - The task given to the agent
            if message_type == "HumanMessage":
                content = getattr(message, 'content', '')
                if content and len(content) > 100:
                    # Log the task being given to the agent
                    logger.info(f"🎯 TASK: {content[:200]}...")
            
            # AIMessage - The agent's response
            elif message_type == "AIMessage":
                content = getattr(message, 'content', '')
                
                # Check if this is a tool call message
                tool_calls = getattr(message, 'tool_calls', [])
                if tool_calls:
                    # Log tool calls
                    for tool_call in tool_calls:
                        tool_name = tool_call.get('name', 'unknown')
                        logger.info(f"🔧 CALLING TOOL: {tool_name}")
                
                # If there's text content (reasoning or final response)
                elif content:
                    # Check if it's markdown (starts with # or ---)
                    if content.startswith('#') or content.startswith('---'):
                        # This is likely a final report - log key sections
                        lines = content.split('\n')
                        in_important_section = False
                        for line in lines[:50]:  # First 50 lines
                            # Log headers and important sections
                            if line.startswith('#'):
                                logger.info(f"📋 {line.strip()}")
                                in_important_section = True
                            elif line.strip().startswith('- **') or line.strip().startswith('**'):
                                if in_important_section:
                                    logger.info(f"   {line.strip()}")
                            elif line.strip() and line.strip() not in ['---', '']:
                                # Don't log too much detail
                                pass
                    else:
                        # Regular reasoning text
                        logger.info(f"💭 {content[:300]}...")
            
            # ToolMessage - Results from tool calls
            elif message_type == "ToolMessage":
                tool_name = getattr(message, 'name', 'unknown')
                content = getattr(message, 'content', '')
                
                # Try to parse JSON content
                try:
                    import json
                    data = json.loads(content) if content else {}
                    
                    # Log key information based on tool
                    if tool_name == "check_trid_dates":
                        is_compliant = data.get('compliant', False)
                        action = data.get('action', 'Unknown')
                        logger.info(f"✓ TRID Check: {'✅ Compliant' if is_compliant else '❌ ' + action}")
                    
                    elif tool_name == "check_hard_stops":
                        has_stops = data.get('has_hard_stops', False)
                        logger.info(f"✓ Hard Stops: {'❌ Missing fields' if has_stops else '✅ All present'}")
                    
                    elif tool_name == "update_regz_le_fields":
                        updates = data.get('updates_made', {})
                        logger.info(f"✓ RegZ-LE Updated: {len(updates)} fields")
                    
                    elif tool_name == "match_ctc":
                        matched = data.get('matched', False)
                        diff = data.get('difference', 0)
                        logger.info(f"✓ CTC: {'✅ Matched' if matched else f'⚠️ Mismatch: ${diff:,.2f}'}")
                    
                    elif tool_name == "check_mavent":
                        passed = data.get('passed', False)
                        total = data.get('total_issues', 0)
                        logger.info(f"✓ Mavent: {'✅ Passed' if passed else f'❌ {total} issues'}")
                    
                    elif tool_name == "order_disclosure_package":
                        success = data.get('success', False)
                        tracking_id = data.get('tracking_id', 'N/A')
                        logger.info(f"✓ Order: {'✅ Success' if success else '❌ Failed'} (ID: {tracking_id})")
                    
                    else:
                        # For other tools, just log success/failure
                        if 'success' in data:
                            status = '✅' if data['success'] else '❌'
                            logger.info(f"✓ {tool_name}: {status}")
                
                except (json.JSONDecodeError, Exception):
                    # Not JSON or error parsing - skip
                    pass
        
        except Exception as e:
            # Don't let logging errors break the agent
            logger.debug(f"Error logging agent message {i}: {e}")


def log_agent_summary(result: dict, agent_name: str, logger: logging.Logger = None):
    """Log a summary of agent execution.
    
    Args:
        result: Agent result dictionary
        agent_name: Name of the agent
        logger: Logger instance (uses root logger if None)
    """
    if logger is None:
        logger = logging.getLogger()
    
    logger.info("=" * 80)
    logger.info(f"📊 {agent_name} EXECUTION SUMMARY")
    logger.info("=" * 80)
    
    # Status
    status = result.get('status', 'unknown')
    status_emoji = '✅' if status == 'success' else '❌' if status == 'failed' else '⚠️'
    logger.info(f"Status: {status_emoji} {status.upper()}")
    
    # Summary if available
    summary = result.get('summary', '')
    if summary:
        for line in summary.split('\n')[:10]:  # First 10 lines
            if line.strip():
                logger.info(line)
    
    # Blocking issues
    blocking_issues = result.get('blocking_issues', [])
    if blocking_issues:
        logger.warning("⚠️ BLOCKING ISSUES:")
        for issue in blocking_issues:
            logger.warning(f"  - {issue}")
    
    logger.info("=" * 80)


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

