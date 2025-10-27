"""DrawDoc-AWM Agent - Document Drawing and Annotation Agent.

This agent is specialized for drawing and annotating documents for AWM
(Asset and Wealth Management) workflows.
"""

import os
from pathlib import Path

from copilotagent import create_deep_agent

# Simple system prompt - detailed workflow guidance is handled by the planner
drawdoc_instructions = """You are a document drawing and annotation specialist for AWM (Asset and Wealth Management).

Your job is to create, annotate, and prepare professional documents for AWM clients. Use the planner to organize your work."""

# Load local planning prompt
planner_prompt_file = Path(__file__).parent / "planner_prompt.md"
planning_prompt = planner_prompt_file.read_text() if planner_prompt_file.exists() else None

# Create the DrawDoc-AWM agent
agent = create_deep_agent(
    agent_type="DrawDoc-AWM",
    system_prompt=drawdoc_instructions,
    planning_prompt=planning_prompt,  # Use local planning prompt
)

# When this agent is invoked without messages, it will present the default message:
# "Let's draw the docs for AWM"
# The user can approve or modify this message before proceeding.

if __name__ == "__main__":
    print("DrawDoc-AWM Agent created successfully!")
    print("This agent is configured for document drawing and annotation workflows.")
    print()
    print("Default starting message:")
    print("'Let's draw the docs for AWM'")
    print()
    print("To use this agent:")
    print("1. Invoke with no messages to use the default starting message")
    print("2. Or provide specific document drawing instructions")
    print()
    print("Example usage:")
    print('agent.invoke({"messages": []})')
    print('# or')
    print('agent.invoke({"messages": [{"role": "user", "content": "Draw the quarterly report for client XYZ"}]})')

