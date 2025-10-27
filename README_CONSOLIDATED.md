# 📝 DrawDoc-AWM Agent

**Document Drawing and Annotation Agent for Asset and Wealth Management**

[![LangGraph Cloud](https://img.shields.io/badge/LangGraph-Cloud-blue)](https://smith.langchain.com/)
[![GitHub](https://img.shields.io/badge/GitHub-DrawDoc--AWM-green)](https://github.com/FintorAI/drawdoc-awm-agent)

---

## 📋 Overview

This agent specializes in drawing, annotating, and preparing professional documents for AWM (Asset and Wealth Management) workflows. It follows a structured 5-phase approach for high-quality document production.

---

## ✨ Features

- ✅ **Structured 5-Phase Workflow** - Analysis → Markup → Drawing → QA → Delivery
- ✅ **Document Annotation** - Automated markup and highlighting
- ✅ **Visual Elements** - Charts, diagrams, tables, and graphics
- ✅ **Quality Assurance** - Built-in review and verification
- ✅ **Custom Planning** - Local `planner_prompt.md` for workflow customization
- ✅ **Default Starting Message** - "Let's draw the docs for AWM"

---

## 🚀 Quick Start

### Local Development

```bash
cd agents/DrawDoc-AWM

# Create .env file
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-api03-...
EOF

# Start dev server
langgraph dev

# Open http://localhost:2024
```

### GitHub Repository

**Repo**: https://github.com/FintorAI/drawdoc-awm-agent

**Deploy Command:**
```bash
git add .
git commit -m "Update agent"
git push origin main
# → LangGraph Cloud auto-deploys!
```

---

## 🔐 Environment Variables

### Required Variables

**ANTHROPIC_API_KEY** ✅ Required
- **Purpose**: Claude Sonnet 4.5 model (main agent LLM)
- **Get from**: https://console.anthropic.com/settings/keys
- **Format**: `sk-ant-api03-...`

### Setting Variables

**For Local Development:**
```bash
# Create .env in agent directory
ANTHROPIC_API_KEY=sk-ant-api03-your-key
```

**For LangGraph Cloud:**
1. Go to: https://smith.langchain.com/deployments
2. Select deployment → Environment Variables
3. Add `ANTHROPIC_API_KEY`

---

## 🔄 Document Workflow

The agent follows a structured 5-phase approach:

### Phase 1: Document Analysis
- Understand requirements
- Review templates and source materials
- Identify key sections and annotation needs
- Use `read_file` to examine existing documents

### Phase 2: Annotation and Markup
- Add annotations and callouts
- Highlight critical information
- Insert explanatory notes
- Use `edit_file` to markup documents

### Phase 3: Drawing and Visual Elements
- Create charts and diagrams
- Design visual components
- Add signatures, stamps, seals
- Ensure proper formatting

### Phase 4: Review and Quality Assurance
- Verify element placement
- Check completeness and accuracy
- Ensure AWM standards compliance
- Validate client requirements

### Phase 5: Export and Delivery
- Prepare final format
- Generate supporting documents
- Create delivery package
- Use `write_file` for final output

---

## 🛠️ Available Tools

### Planning Tool
- `write_todos` - Break down document workflow into phases

### File System Tools
- `ls` - List templates and source files
- `read_file` - Read source documents and templates
- `write_file` - Create annotated documents and reports
- `edit_file` - Update and refine document drafts

### Subagent Tool
- `task` - Spawn subagents for parallel work (charts, sections, QA reviews)

---

## 📂 File Structure

```
DrawDoc-AWM/
├── drawdoc_agent.py       # Agent implementation
├── planner_prompt.md      # Custom planning workflow (editable!)
├── requirements.txt       # Dependencies (copilotagent>=0.1.8)
├── langgraph.json         # LangGraph Cloud config
├── .gitignore             # Python + LangGraph ignores
└── README_CONSOLIDATED.md # This file
```

---

## 🎨 Customization

### Edit Planning Workflow

The agent uses `planner_prompt.md` for planning strategy:

```bash
# Edit the 5-phase workflow
nano planner_prompt.md

# Commit and push
git add planner_prompt.md
git commit -m "Customize document workflow phases"
git push origin main

# → LangGraph Cloud auto-deploys! ✅
```

### Add Custom Tools

```python
# In drawdoc_agent.py
from langchain_core.tools import tool
from pathlib import Path

@tool
def load_template(template_name: str) -> str:
    """Load a document template."""
    return Path(f"templates/{template_name}").read_text()

# Load custom planning prompt
planning_prompt = Path("planner_prompt.md").read_text()

agent = create_deep_agent(
    agent_type="DrawDoc-AWM",
    system_prompt=drawdoc_instructions,
    planning_prompt=planning_prompt,
    tools=[load_template],  # Add custom tool
)
```

---

## 📄 Document Types Supported

- ✅ Client reports (quarterly, annual)
- ✅ Portfolio summaries
- ✅ Investment proposals
- ✅ Compliance documents
- ✅ Client presentations
- ✅ Executive summaries

---

## 🌐 LangGraph Cloud Deployment

### Initial Setup

1. **Deploy to GitHub** (already done):
   - Repo: https://github.com/FintorAI/drawdoc-awm-agent

2. **Connect to LangGraph Cloud**:
   - Go to: https://smith.langchain.com/deployments
   - Click "+ New Deployment"
   - Select: GitHub → FintorAI/drawdoc-awm-agent
   - Branch: main

3. **Configure Environment Variables**:
   - `ANTHROPIC_API_KEY`

4. **Deploy**:
   - Click "Submit"
   - Wait ~5 minutes
   - Test in playground!

### Auto-Deploy

After initial setup, pushes to GitHub automatically redeploy!

---

## 📊 Dependencies

```txt
copilotagent>=0.1.8      # Core framework (from PyPI)
langchain>=1.0.0         # LangChain framework
langchain-anthropic>=1.0.0  # Claude model
langchain-core>=1.0.0    # LangChain core
```

---

## 💡 Usage Example

```python
from copilotagent import create_deep_agent
from pathlib import Path

# Load custom planning prompt
planning_prompt = Path("planner_prompt.md").read_text()

# Create agent
agent = create_deep_agent(
    agent_type="DrawDoc-AWM",
    system_prompt="You are a document specialist for AWM.",
    planning_prompt=planning_prompt,  # Custom 5-phase workflow
)

# Invoke with default message
result = agent.invoke({"messages": []})
# Presents: "Let's draw the docs for AWM"

# Or with custom task
result = agent.invoke({
    "messages": [{"role": "user", "content": "Draw quarterly report for client XYZ"}]
})
```

---

## 🐛 Troubleshooting

### Local dev server won't start
**Fix**: Ensure `.env` has `ANTHROPIC_API_KEY`

### LangGraph Cloud build fails
**Fix**: Wait 10-15 minutes after new `copilotagent` version (PyPI propagation)

### Planning doesn't follow custom workflow
**Fix**: Verify `planner_prompt.md` exists and is loaded in `drawdoc_agent.py`

---

## 📚 Related Documentation

- **Base Package**: https://github.com/FintorAI/copilotBase
- **ITP-Princeton Agent**: https://github.com/FintorAI/itp-princeton-agent
- **Research Agent**: https://github.com/FintorAI/research-agent

---

## ✅ Current Status

- ✅ Deployed to GitHub: https://github.com/FintorAI/drawdoc-awm-agent
- ✅ Using copilotagent v0.1.8 from PyPI
- ✅ Custom planning prompt: `planner_prompt.md`
- ✅ Auto-deploy on push enabled

---

**Ready for LangGraph Cloud deployment!** 🚀

