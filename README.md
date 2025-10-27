# DrawDoc-AWM Agent

Document Drawing and Annotation Agent for Asset and Wealth Management

## Overview

This agent is specialized for drawing, annotating, and preparing documents for AWM (Asset and Wealth Management) workflows. It follows a structured multi-phase approach to ensure high-quality document production.

## Features

- **Structured Workflow**: Five-phase approach from analysis to delivery
- **Document Annotation**: Automated markup and annotation capabilities
- **Visual Element Creation**: Support for charts, diagrams, and tables
- **Quality Assurance**: Built-in review and verification steps
- **Task Tracking**: Uses todo list for workflow management
- **Default Starting Message**: Automatically presents "Let's draw the docs for AWM" when invoked

## Agent Capabilities

### Document Processing Workflow

1. **Document Analysis Phase**
   - Understand requirements
   - Identify key sections
   - Determine annotation needs

2. **Annotation and Markup Phase**
   - Add annotations and markups
   - Highlight critical information
   - Add explanatory notes

3. **Drawing and Visual Elements Phase**
   - Create visual elements
   - Ensure proper formatting
   - Add signatures, stamps, seals

4. **Review and Quality Assurance Phase**
   - Verify element placement
   - Check completeness and accuracy
   - Ensure AWM standards compliance

5. **Export and Delivery Phase**
   - Prepare final format
   - Generate supporting documents
   - Create delivery package

### Built-in Tools
- `write_todos`: Plan and track document workflow
- `ls`: List template and source files
- `read_file`: Read source documents
- `write_file`: Create annotated documents
- `edit_file`: Update document drafts

## Usage

### Basic Usage

```python
from copilotagent import create_deep_agent

# Create the agent
agent = create_deep_agent(
    agent_type="DrawDoc-AWM",
    system_prompt="Additional custom instructions..."
)

# Use with default starting message
result = agent.invoke({"messages": []})
# Presents: "Let's draw the docs for AWM"

# Or provide specific task
result = agent.invoke({
    "messages": [{"role": "user", "content": "Draw quarterly report for client XYZ"}]
})
```

### Running the Example

```bash
cd agent/DrawDoc-AWM
python drawdoc_agent.py
```

## Configuration

The agent is configured with:
- **Agent Type**: `DrawDoc-AWM`
- **Default Model**: Claude Sonnet 4.5
- **Planning**: DrawDoc-specific planning prompts with phase tracking
- **Default Message**: "Let's draw the docs for AWM"

## Workflow Example

When you invoke the agent, it will:

1. **Accept or modify the starting message** (if invoked without messages)
2. **Create a document workflow plan** using the todo list tool
3. **Analyze document requirements** and templates
4. **Create annotations and markup** based on requirements
5. **Generate visual elements** as needed
6. **Perform quality review** against AWM standards
7. **Prepare final delivery package**

## Document Types Supported

The agent can handle various AWM document types:
- Client reports (quarterly, annual)
- Portfolio summaries
- Investment proposals
- Compliance documents
- Client presentations
- Executive summaries

## Requirements

- Python 3.11+
- copilotagent package (from PyPI)
- LangChain dependencies (installed with copilotagent)

See `requirements.txt` for full list of dependencies.

## Integration

This agent can be integrated into:
- Document management systems
- Client reporting workflows
- Compliance tracking systems
- Portfolio management platforms
- Automated reporting pipelines

## Support

For questions or issues with the DrawDoc-AWM agent, refer to the main CopilotAgent documentation.

