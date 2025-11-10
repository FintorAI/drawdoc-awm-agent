# Station & Server Middleware Setup for DrawDoc-AWM Agent

## Overview

The DrawDoc-AWM agent now supports optional Station and Server middleware from `copilotagent>=0.1.20` for coordinating tool execution with CuteAgent's StationAgent.

## Environment Variables Required

Add these to your `.env` file:

```bash
# Required for Station & Server Middleware
STATION_TOKEN=your-station-token-here

# Optional for pause/unpause features
LANGGRAPH_TOKEN=your-langgraph-token-here
```

## How to Use Station Middleware

Station Middleware syncs tool outputs to shared state after tool execution.

### Example: Encompass Tool with Station Middleware

```python
from langchain_core.tools import StructuredTool

# Your existing tool
def read_loan_fields(loan_id: str, field_ids: list[str]) -> dict:
    """Read field values from an Encompass loan."""
    client = _get_encompass_client()
    values = client.read_loan_fields(loan_id, field_ids)
    return {
        "loan_id": loan_id,
        "field_values": values,
        "field_count": len(values)
    }

# Wrap as StructuredTool
tool = StructuredTool.from_function(
    name="read_loan_fields",
    func=read_loan_fields,
)

# Configure Station Middleware
tool.metadata = {
    "station_middleware": {
        "variables": ["loan_id", "field_values"],  # These will be synced
        "station_id": "drawdoc-awm-station-1"
    }
}
```

## How to Use Server Middleware

Server Middleware coordinates exclusive access to servers (e.g., browser agents, API services).

### Example: Browser Tool with Server Middleware

```python
# Tool that needs exclusive browser access
def extract_document_data(document_url: str) -> dict:
    """Extract data from document using browser automation."""
    # Your browser automation code here
    return {
        "document_data": {...},
        "extracted_fields": [...]
    }

tool = StructuredTool.from_function(
    name="extract_document_data",
    func=extract_document_data,
)

# Configure Server Middleware
tool.metadata = {
    "server_middleware": {
        "server_id": "BrowserAgent",    # Default
        "checkpoint": "Chrome",          # Default
        "server_task_type": "DocumentExtraction"
    }
}
```

## Using Both Middleware Together

```python
tool.metadata = {
    "station_middleware": {
        "variables": ["document_data", "extracted_fields"],
        "station_id": "drawdoc-awm-station-1"
    },
    "server_middleware": {
        "server_id": "BrowserAgent",
        "checkpoint": "Chrome"
    }
}
```

## Agent Integration

The middleware are automatically available when you create an agent with `create_deep_agent()`:

```python
from copilotagent import create_deep_agent
from copilotagent.middleware import StationMiddleware, ServerMiddleware

agent = create_deep_agent(
    model="anthropic:claude-3-5-sonnet-20241022",
    middleware=[
        ServerMiddleware(),   # Coordinates server access
        StationMiddleware(),  # Syncs outputs to shared state
    ],
    tools=[your_tools_with_metadata],
    system_prompt="Your system prompt here..."
)
```

## Agent State Requirements

For Server Middleware to work, your agent state must include `station_thread_id`:

```python
initial_state = {
    "station_thread_id": "drawdoc-awm-station-1",
    # ... other state
}
```

## Error Handling

Both middleware handle errors gracefully:

- **Missing `STATION_TOKEN`**: Returns error message asking agent to report to human
- **No middleware config**: Tool executes normally without middleware
- **Variable not in output**: Skipped with warning logged
- **Server busy**: Retries every 30 seconds for up to 10 minutes
- **Server error**: Fails immediately with error message

## Testing

1. **Verify environment variables**:
```bash
cd /Users/masoud/Desktop/WORK/DeepCopilotAgent2/agents/DrawDoc-AWM
python3 -c "
from dotenv import load_dotenv
import os
load_dotenv()
print('STATION_TOKEN:', 'SET ✅' if os.getenv('STATION_TOKEN') else 'NOT SET ❌')
print('LANGGRAPH_TOKEN:', 'SET ✅' if os.getenv('LANGGRAPH_TOKEN') else 'NOT SET ❌')
"
```

2. **Test middleware imports**:
```bash
python3 -c "from copilotagent.middleware import StationMiddleware, ServerMiddleware; print('✅ Middleware available')"
```

## Documentation References

- Main Middleware Guide: `/baseCopilotAgent/MIDDLEWARE_USAGE_GUIDE.md`
- Architecture Notes: `/baseCopilotAgent/MIDDLEWARE_ARCHITECTURE_NOTES.md`
- Environment Setup: `/baseCopilotAgent/ENV_VARIABLES_SETUP.md`

## Current Status

- ✅ `copilotagent>=0.1.20` with middleware support
- ✅ `cuteagent>=0.2.24` for StationAgent integration
- ⚠️ Middleware are **optional** - tools work without them
- ⚠️ Configure `.env` file with `STATION_TOKEN` to enable

