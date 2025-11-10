# 📝 DrawDoc-AWM Agent

**Document Drawing and Annotation Agent for Asset and Wealth Management**

[![LangGraph Cloud](https://img.shields.io/badge/LangGraph-Cloud-blue)](https://smith.langchain.com/)
[![GitHub](https://img.shields.io/badge/GitHub-DrawDoc--AWM-green)](https://github.com/FintorAI/drawdoc-awm-agent)

---

## 📋 Overview

A LangGraph agent that specializes in processing Encompass loan documents and extracting structured data using LandingAI. The agent has 6 specialized tools for interacting with the Encompass API and follows a structured 5-phase testing workflow for comprehensive READ operations.

---

## ✨ Features

- ✅ **6 Specialized Tools** - 5 READ operations + 1 WRITE operation for Encompass
- ✅ **Encompass API Integration** - Direct access to loan data, documents, and entities
- ✅ **LandingAI Document Extraction** - Automated structured data extraction with AI
- ✅ **Comprehensive 5-Phase Testing** - Read Fields → List Docs → Get Entity → Download → Extract
- ✅ **Token-Optimized** - Large responses saved to files, avoiding 200K token limits
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

### 2. `get_loan_documents`
List all documents and attachments in an Encompass loan.

**Parameters:**
- `loan_id` (str): The Encompass loan GUID
- `max_documents` (int, optional): Maximum documents to return in response (default: 10)

**Example:**
```python
result = get_loan_documents.invoke({
    "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
    "max_documents": 5
})
# Returns: {
#   "total_documents": 159,
#   "total_attachments": 207,
#   "file_path": "/tmp/loan_documents_387596ee.json",
#   "sample_documents": [
#     {"title": "W2", "documentId": "0985d4a6-f92...", "attachment_count": 1},
#     ...
#   ],
#   "showing_first": 5,
#   "loan_id": "..."
# }
```

**Returns:**
- Total counts for documents and attachments
- JSON file path with complete document list (always saved)
- Sample summaries of first N documents (title, ID, attachment count only)
- **Token-optimized**: Full data saved to JSON, only summaries in conversation

---

### 3. `get_loan_entity`
Get complete loan data including all fields and custom fields.

**Parameters:**
- `loan_id` (str): The Encompass loan GUID

**Example:**
```python
result = get_loan_entity.invoke({
    "loan_id": "65ec32a1-99df-4685-92ce-41a08fd3b64e"
})
# Returns: {
#   "field_count": 247,
#   "loan_number": "12345",
#   "file_path": "/tmp/loan_entity_65ec32a1.json",
#   "key_fields": {
#     "loanNumber": "12345",
#     "borrowerFirstName": "John",
#     "borrowerLastName": "Doe"
#   },
#   "loan_id": "..."
# }
```

**Returns:**
- Field count showing how many fields have data
- Loan number for quick reference
- JSON file path with complete loan entity data
- Key fields extracted for quick access (borrower name, loan amount, etc.)
- **Token-optimized**: Full loan data saved to file, not returned in conversation

---

### 4. `write_loan_field`
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

### 5. `download_loan_document`
Download a document attachment from an Encompass loan to a temporary file.

**Parameters:**
- `loan_id` (str): The Encompass loan GUID
- `attachment_id` (str): The attachment entity ID

**Example:**
```python
result = download_loan_document.invoke({
    "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
    "attachment_id": "d78186cc-a8a2-454f-beaf-19f0e6c3aa8c"
})
# Returns: {
#   "file_path": "/tmp/encompass_doc_abc123.pdf",
#   "file_size_bytes": 583789,
#   "file_size_kb": 570.11,
#   "attachment_id": "...",
#   "loan_id": "..."
# }
```

**Returns:**
- `file_path`: Path to temporary file containing the document
- `file_size_bytes`: Size of document in bytes
- `file_size_kb`: Size in kilobytes for readability
- The file path can be passed directly to `extract_document_data`

---

### 6. `extract_document_data`
Extract structured data from documents using LandingAI.

**Parameters:**
- `file_path` (str): Path to the PDF file (from `download_loan_document` result)
- `extraction_schema` (dict): JSON schema defining what to extract
- `document_type` (str, optional): Label for document type (default: "Document")

**Example - W-2 Extraction:**
```python
# Step 1: Download document
doc = download_loan_document.invoke({
    "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
    "attachment_id": "d78186cc-a8a2-454f-beaf-19f0e6c3aa8c"
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

# Step 3: Extract using file_path from download result
result = extract_document_data.invoke({
    "file_path": doc["file_path"],
    "extraction_schema": schema,
    "document_type": "W2"
})
# Returns: {"extracted_schema": {...}, "doc_type": "W2", "extraction_method": "landingai-agentic"}
```

---

## 🔄 5-Phase Testing Workflow

The agent follows a structured 5-phase comprehensive READ testing approach:

### Phase 1: Read Loan Fields
**Goal:** Test reading specific field values from Encompass loans

**Actions:**
- Call `read_loan_fields(loan_id, field_ids)` with specific field IDs
- Verify correct field values are returned

**Reports:** Display actual field values (Loan Amount, Borrower Name, etc.)

### Phase 2: List All Documents
**Goal:** Test listing all documents and attachments in a loan

**Actions:**
- Call `get_loan_documents(loan_id)` to retrieve document metadata
- Get attachment IDs needed for downloading

**Reports:** Show document count, attachment count, and document titles

### Phase 3: Get Complete Loan Entity
**Goal:** Test retrieving complete loan data with all fields

**Actions:**
- Call `get_loan_entity(loan_id)` to get full loan object
- Verify comprehensive data access

**Reports:** Display field count, loan number, and sample fields

### Phase 4: Download Document
**Goal:** Test downloading document attachments from Encompass

**Actions:**
- Call `download_loan_document(loan_id, attachment_id)` to download
- Save to temporary file for processing

**Reports:** Confirm download success, show file size and path

### Phase 5: Extract Document Data
**Goal:** Test AI-powered structured data extraction from documents

**Actions:**
- Use file path from Phase 4 download
- Call `extract_document_data(file_path, schema, doc_type)` with extraction schema
- Verify extracted data matches expectations

**Reports:** Display extracted fields and complete test summary

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

## 💡 Complete 5-Phase Testing Example

### Running the Test Suite

**Option 1: Individual Tool Tests**
```bash
cd agents/DrawDoc-AWM
python drawdoc_agent.py --test-tools
```

This runs all 5 tests sequentially:
- ✅ Test 1: Read loan fields
- ✅ Test 2: Get loan documents list
- ✅ Test 3: Get complete loan entity
- ✅ Test 4: Download document
- ✅ Test 5: Extract data with AI

**Option 2: Agent Workflow Demo**
```bash
python drawdoc_agent.py --demo
```

This invokes the agent with a comprehensive 5-phase test task that creates a plan and executes all phases.

### Programmatic Testing Example

```python
from langchain_core.messages import HumanMessage

# Task: Complete 5-phase Encompass READ operation test
task = """
Test all Encompass READ operations. Execute the complete 5-phase test:

Phase 1: Read loan fields from loan 65ec32a1-99df-4685-92ce-41a08fd3b64e
- Get fields: 4000, 4002, 4004, 353

Phase 2: Get loan documents list from loan 387596ee-7090-47ca-8385-206e22c9c9da
- Show all documents and attachments available

Phase 3: Get complete loan entity from loan 65ec32a1-99df-4685-92ce-41a08fd3b64e
- Show field count and loan number

Phase 4: Download the W-2 document
- Loan: 387596ee-7090-47ca-8385-206e22c9c9da
- Attachment: d78186cc-a8a2-454f-beaf-19f0e6c3aa8c

Phase 5: Extract data from the W-2 document
- Extract: employer name, employee name, and tax year

Create a plan with write_todos and execute all 5 phases, showing results for each.
"""

result = agent.invoke({"messages": [HumanMessage(content=task)]})
```

The agent will automatically:
1. Create a 5-phase todo plan with `write_todos`
2. Execute Phase 1: Call `read_loan_fields` to get specific fields
3. Execute Phase 2: Call `get_loan_documents` to list all documents
4. Execute Phase 3: Call `get_loan_entity` to get complete loan data
5. Execute Phase 4: Call `download_loan_document` to download attachment
6. Execute Phase 5: Call `extract_document_data` to extract structured data
7. Provide comprehensive test summary with results from all phases

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
├── drawdoc_agent.py       # Main agent with 6 tools (5 READ + 1 WRITE)
├── planner_prompt.md      # 5-phase testing workflow
├── requirements.txt       # Dependencies (copilotagent>=0.1.20)
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
copilotagent>=0.1.20        # Core framework (from PyPI)
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
- Documents are automatically saved to temporary files
- File paths are returned and can be passed to `extract_document_data`
- Temp files are auto-cleaned by the OS
- No need to manage file cleanup manually

### Schema Design
- Provide detailed descriptions to help AI understand
- Use appropriate types (string, number, array, object)
- Test schemas with sample documents first
- Start simple, add fields incrementally

### Performance
- Phase 1 (Read Fields): < 2 seconds
- Phase 2 (List Documents): < 3 seconds
- Phase 3 (Get Entity): < 3 seconds
- Phase 4 (Download Document): 2-5 seconds depending on file size
- Phase 5 (Extract Data): 8-12 seconds for AI extraction
- **Total 5-Phase Test**: ~15-25 seconds end-to-end

---

**Ready for LangGraph Cloud deployment!** 🚀

**Status**: ✅ Production Ready  
**Version**: 2.1 (6 Tools + 5-Phase Testing)  
**Tools**: 5 READ + 1 WRITE operations  
**Testing**: Comprehensive 5-phase workflow

