# 📝 DrawDoc-AWM Agent

**Document Drawing and Annotation Agent for Asset and Wealth Management**

[![LangGraph Cloud](https://img.shields.io/badge/LangGraph-Cloud-blue)](https://smith.langchain.com/)
[![GitHub](https://img.shields.io/badge/GitHub-DrawDoc--AWM-green)](https://github.com/FintorAI/drawdoc-awm-agent)

---

## 📋 Overview

A LangGraph agent that specializes in processing Encompass loan documents and extracting structured data using LandingAI. The agent has 4 specialized tools for interacting with the Encompass API and follows a structured 5-phase workflow for document production.

---

## ✨ Features

- ✅ **4 Specialized Tools** - Read/write loan fields, download documents, extract data
- ✅ **Encompass API Integration** - Direct access to loan data and documents
- ✅ **LandingAI Document Extraction** - Automated structured data extraction
- ✅ **Structured 5-Phase Workflow** - Analysis → Markup → Drawing → QA → Delivery
- ✅ **Custom Planning** - Local `planner_prompt.md` for workflow customization
- ✅ **LangGraph Cloud Ready** - Deploy and auto-update from GitHub

---

## 🚀 Quick Start

### Local Development

```bash
cd agents/DrawDoc-AWM

# Create .env file
cat > .env << 'EOF'
# Required
ANTHROPIC_API_KEY=sk-ant-api03-...

# Encompass API
ENCOMPASS_ACCESS_TOKEN=your_token
ENCOMPASS_API_BASE_URL=https://api.elliemae.com
ENCOMPASS_USERNAME=your_username
ENCOMPASS_PASSWORD=your_password
ENCOMPASS_CLIENT_ID=your_client_id
ENCOMPASS_CLIENT_SECRET=your_client_secret
ENCOMPASS_INSTANCE_ID=your_instance_id
ENCOMPASS_SUBJECT_USER_ID=your_subject_user_id

# LandingAI
LANDINGAI_API_KEY=your_landingai_key
EOF

# Install dependencies
pip install -r requirements.txt

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

## 🛠️ Available Tools

### 1. `read_loan_fields`
Read one or multiple field values from an Encompass loan.

**Parameters:**
- `loan_id` (str): The Encompass loan GUID
- `field_ids` (list[str]): List of field IDs to retrieve

**Example:**
```python
result = read_loan_fields.invoke({
    "loan_id": "65ec32a1-99df-4685-92ce-41a08fd3b64e",
    "field_ids": ["4000", "4002", "4004"]
})
# Returns: {"4000": "350000", "4002": "John", "4004": "Doe"}
```

**Common Field IDs:**
- `4000` - Loan Amount
- `4002` - Borrower First Name
- `4004` - Borrower Last Name
- `353` - Loan Number
- `1109` - Property Street Address
- `12` - Property City
- `14` - Property State
- `748` - Loan Purpose

---

### 2. `write_loan_field`
Update a single field value in an Encompass loan.

**Parameters:**
- `loan_id` (str): The Encompass loan GUID
- `field_id` (str): The field ID to update
- `value` (any): The value to write

**Example:**
```python
result = write_loan_field.invoke({
    "loan_id": "65ec32a1-99df-4685-92ce-41a08fd3b64e",
    "field_id": "4000",
    "value": 350000
})
```

---

### 3. `download_loan_document`
Download a document attachment from an Encompass loan.

**Parameters:**
- `loan_id` (str): The Encompass loan GUID
- `attachment_id` (str): The attachment entity ID
- `save_to_memory` (bool): 
  - `True`: Returns base64 data (keeps in agent state)
  - `False`: Saves to temp file

**Example:**
```python
# Option A - Keep in Memory (for immediate processing)
result = download_loan_document.invoke({
    "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
    "attachment_id": "d78186cc-a8a2-454f-beaf-19f0e6c3aa8c",
    "save_to_memory": True
})
# Returns: {"document_bytes_length": 583789, "base64_data": "...", "storage_type": "memory"}

# Option B - Save to Temp File (for large documents)
result = download_loan_document.invoke({
    "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
    "attachment_id": "d78186cc-a8a2-454f-beaf-19f0e6c3aa8c",
    "save_to_memory": False
})
# Returns: {"document_bytes_length": 583789, "file_path": "/tmp/...", "storage_type": "temp_file"}
```

---

### 4. `extract_document_data`
Extract structured data from documents using LandingAI.

**Parameters:**
- `document_source` (dict): Either:
  - `{"base64_data": "..."}` for in-memory documents
  - `{"file_path": "/path/to/file"}` for file documents
- `extraction_schema` (dict): JSON schema defining what to extract
- `document_type` (str, optional): Label for document type

**Example - W-2 Extraction:**
```python
# Step 1: Download document
doc = download_loan_document.invoke({
    "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
    "attachment_id": "d78186cc-a8a2-454f-beaf-19f0e6c3aa8c",
    "save_to_memory": True
})

# Step 2: Define schema
schema = {
    "type": "object",
    "properties": {
        "employer_name": {
            "type": "string",
            "title": "Employer Name",
            "description": "Name of employer from W-2"
        },
        "employee_name": {
            "type": "string",
            "title": "Employee Name",
            "description": "Full name of employee"
        },
        "wages": {
            "type": "number",
            "title": "Total Wages",
            "description": "Total wages from box 1"
        }
    }
}

# Step 3: Extract
result = extract_document_data.invoke({
    "document_source": {"base64_data": doc["base64_data"]},
    "extraction_schema": schema,
    "document_type": "W2"
})
# Returns: {"extracted_schema": {...}, "doc_type": "W2", "extraction_method": "landingai-agentic"}
```

---

## 🔄 Document Workflow

The agent follows a structured 5-phase approach:

### Phase 1: Document Analysis
- Understand requirements
- Review templates and source materials
- Identify key sections and annotation needs

### Phase 2: Annotation and Markup
- Add annotations and callouts
- Highlight critical information
- Insert explanatory notes

### Phase 3: Drawing and Visual Elements
- Create charts and diagrams
- Design visual components
- Add signatures, stamps, seals

### Phase 4: Review and Quality Assurance
- Verify element placement
- Check completeness and accuracy
- Ensure AWM standards compliance

### Phase 5: Export and Delivery
- Prepare final format
- Generate supporting documents
- Create delivery package

---

## 📊 Example Extraction Schemas

### W-2 Form
```python
{
    "type": "object",
    "properties": {
        "employer_name": {
            "type": "string",
            "title": "Employer Name",
            "description": "Name of the employer/company"
        },
        "employee_name": {
            "type": "string",
            "title": "Employee Name",
            "description": "Full name of the employee"
        },
        "tax_year": {
            "type": "string",
            "title": "Tax Year",
            "description": "The tax year for this W-2"
        },
        "wages": {
            "type": "number",
            "title": "Wages and Tips",
            "description": "Total wages, tips, and compensation (Box 1)"
        },
        "federal_tax": {
            "type": "number",
            "title": "Federal Tax Withheld",
            "description": "Federal income tax withheld (Box 2)"
        }
    }
}
```

### Bank Statement
```python
{
    "type": "object",
    "properties": {
        "bank_name": {"type": "string", "title": "Bank Name"},
        "account_holder": {"type": "string", "title": "Account Holder"},
        "account_number": {"type": "string", "title": "Account Number"},
        "statement_period": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string"},
                "end_date": {"type": "string"}
            }
        },
        "ending_balance": {"type": "number", "title": "Ending Balance"}
    }
}
```

### 1003 (Loan Application)
```python
{
    "type": "object",
    "properties": {
        "borrower_name": {"type": "string", "title": "Borrower Name"},
        "co_borrower_name": {"type": "string", "title": "Co-Borrower Name"},
        "property_address": {"type": "string", "title": "Property Address"},
        "purchase_price": {"type": "number", "title": "Purchase Price"},
        "loan_amount": {"type": "number", "title": "Loan Amount"}
    }
}
```

---

## 💡 Complete Workflow Example

```python
from langchain_core.messages import HumanMessage

# Task: Process a W-2 and update loan fields
task = """
Process the W-2 document from loan 387596ee-7090-47ca-8385-206e22c9c9da:

1. Download attachment d78186cc-a8a2-454f-beaf-19f0e6c3aa8c
2. Extract employer name, employee name, and wages
3. Read the current borrower name from the loan (field 4002)
4. If the extracted employee name matches, update the loan amount field (4000) with the extracted wages
5. Provide a summary of what was done
"""

result = agent.invoke({"messages": [HumanMessage(content=task)]})
```

The agent will automatically:
1. Call `download_loan_document` to get the W-2
2. Call `extract_document_data` to extract information
3. Call `read_loan_fields` to check borrower name
4. Call `write_loan_field` to update if needed
5. Provide a natural language summary

---

## 🔐 Environment Variables

### Required

**ANTHROPIC_API_KEY** ✅ Required
- **Purpose**: Claude Sonnet 4.5 model (main agent LLM)
- **Get from**: https://console.anthropic.com/settings/keys
- **Format**: `sk-ant-api03-...`

### Encompass API

- `ENCOMPASS_ACCESS_TOKEN` - Current API token
- `ENCOMPASS_API_BASE_URL` - Usually `https://api.elliemae.com`
- `ENCOMPASS_USERNAME` - Your Encompass username
- `ENCOMPASS_PASSWORD` - Your Encompass password
- `ENCOMPASS_CLIENT_ID` - OAuth client ID
- `ENCOMPASS_CLIENT_SECRET` - OAuth client secret
- `ENCOMPASS_INSTANCE_ID` - Encompass instance ID
- `ENCOMPASS_SUBJECT_USER_ID` - Subject user ID for token

### LandingAI

- `LANDINGAI_API_KEY` - LandingAI API key for document extraction

### Setting Variables

**For Local Development:**
Create a `.env` file in the agent directory with all the variables above.

**For LangGraph Cloud:**
1. Go to: https://smith.langchain.com/deployments
2. Select deployment → Environment Variables
3. Add all required variables

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
   - Add all required environment variables

4. **Deploy**:
   - Click "Submit"
   - Wait ~5 minutes
   - Test in playground!

### Auto-Deploy

After initial setup, pushes to GitHub automatically redeploy!

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

---

## 📂 File Structure

```
DrawDoc-AWM/
├── drawdoc_agent.py       # Main agent with 4 tools
├── planner_prompt.md      # Custom planning workflow
├── requirements.txt       # Dependencies (copilotagent>=0.1.9)
├── langgraph.json         # LangGraph Cloud config
├── .env                   # Local credentials (gitignored)
├── .env.example           # Template for credentials
├── .gitignore             # Python + LangGraph ignores
└── README.md              # This file
```

---

## 🐛 Troubleshooting

### Local dev server won't start
**Fix**: Ensure `.env` has all required variables

### LangGraph Cloud build fails
**Fix**: Wait 10-15 minutes after new `copilotagent` version (PyPI propagation)

### "Failed to get token"
**Fix**: Check credentials in `.env` file, run token refresh script

### "Document not found"
**Fix**: Verify loan ID and attachment ID are correct, check permissions

### "LandingAI extraction failed"
**Fix**: Check `LANDINGAI_API_KEY`, verify document is valid PDF/image

---

## 📊 Dependencies

```txt
copilotagent>=0.1.9         # Core framework (from PyPI)
langchain>=1.0.0            # LangChain framework
langchain-anthropic>=1.0.0  # Claude model
langchain-core>=1.0.0       # LangChain core
python-dotenv>=1.0.0        # Environment variable loading
```

---

## 📚 Related Documentation

- **Base Package**: https://github.com/FintorAI/copilotBase
- **Encompass API**: https://developer.icemortgagetechnology.com/
- **LandingAI**: https://landing.ai/
- **LangGraph**: https://langchain-ai.github.io/langgraph/

---

## ✅ Best Practices

### Security
- ✅ Store credentials in `.env` file (gitignored)
- ✅ Use environment variables in production
- ✅ Never commit credentials to git
- ✅ Rotate tokens regularly

### Document Storage
- Use `save_to_memory=True` for immediate processing
- Use `save_to_memory=False` for large documents
- Temp files are auto-cleaned by the OS

### Schema Design
- Provide detailed descriptions to help AI understand
- Use appropriate types (string, number, array, object)
- Test schemas with sample documents first
- Start simple, add fields incrementally

### Performance
- Download + Extract workflow: ~10-15 seconds
- Field operations: < 2 seconds
- Batch operations: Use multiple tool calls in sequence

---

**Ready for LangGraph Cloud deployment!** 🚀

**Status**: ✅ Production Ready  
**Version**: 2.0 (LangGraph Tools)

