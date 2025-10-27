# Agent Deployment

## LangGraph Cloud Deployment

This agent is deployed to LangGraph Cloud.

### Repository Structure

```
agent/
├── *_agent.py              # Agent implementation
├── langgraph.json          # LangGraph Cloud config
├── requirements.txt        # Dependencies (includes copilotagent from PyPI)
├── .env                    # Environment variables (not in git)
└── README.md               # Agent documentation
```

### Deployment Status

[![LangGraph Cloud](https://img.shields.io/badge/LangGraph-Cloud-blue)](https://smith.langchain.com/)

### Quick Deploy

1. **GitHub Repository**: Connected to GitHub
2. **LangGraph Cloud**: Connected via web dashboard at https://smith.langchain.com/deployments

### Environment Variables Required

Configure these in LangGraph Cloud dashboard:
- `ANTHROPIC_API_KEY` - For Claude model
- `LANGCHAIN_API_KEY` - For cloud subagents (if using)
- `TAVILY_API_KEY` - For web search (research agent only)

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally with langgraph dev
langgraph dev
```

### Updating the Agent

1. Make changes to agent code
2. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Update agent"
   git push origin main
   ```
3. LangGraph Cloud will auto-deploy on push

### Package Dependency

This agent uses `copilotagent` from PyPI:
- Package: https://pypi.org/project/copilotagent/
- Source: https://github.com/FintorAI/copilotBase

To update the package version, modify `requirements.txt`.
