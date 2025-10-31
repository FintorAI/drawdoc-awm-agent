# LangGraph Studio Setup - Quick Start

## Overview

The DrawDoc-AWM agent is now configured to automatically start with a test workflow when launched in LangGraph Studio/Dev.

## Quick Start

### 1. Open in LangGraph Studio

```bash
# Navigate to the agent directory
cd /Users/masoud/Desktop/WORK/DeepCopilotAgent2/agents/DrawDoc-AWM

# Open in LangGraph Studio
langgraph dev
```

Or open LangGraph Studio and select this folder.

### 2. Agent Auto-Starts with Test Message

When you launch the agent, it will **automatically** receive this initial message:

```
Test the Encompass integration tools. Please:

1. Read loan fields from the test loan
   - Get fields: 4000, 4002, 4004, 353 (Loan Amount, Borrower First Name, Last Name, Loan Number)

2. Download the W-2 document from the test loan with documents

3. Download the W-2 document from the test loan with documents

3. Extract data from the W-2 document
   - Extract: employer name, employee name, and tax year

Create a plan and execute each step, showing me the results.
```

### 3. Watch the Agent Work

The agent will automatically:
1. ✅ Create a test plan using `write_todos`
2. ✅ Call `read_loan_fields` with TEST_LOAN_ID
3. ✅ Call `download_loan_document` with TEST_LOAN_WITH_DOCS
4. ✅ Call `extract_document_data` with TEST_W2_SCHEMA
5. ✅ Display all results

## Configuration

### Initial Message Location

The initial message is defined in two places:

**1. `langgraph.json` (for LangGraph Studio):**
```json
{
  "default_input": {
    "messages": [
      {
        "role": "user",
        "content": "Test the Encompass integration tools..."
      }
    ]
  }
}
```

**2. `drawdoc_agent.py` (as a Python constant):**
```python
DEFAULT_INITIAL_MESSAGE = f"""Test the Encompass integration tools. Please:

1. Read loan fields from loan {TEST_LOAN_ID}
   ...
"""
```

### Test Data Used

All test values are hardcoded in `drawdoc_agent.py`:

```python
TEST_LOAN_ID = "65ec32a1-99df-4685-92ce-41a08fd3b64e"
TEST_LOAN_WITH_DOCS = "387596ee-7090-47ca-8385-206e22c9c9da"
TEST_ATTACHMENT_ID = "d78186cc-a8a2-454f-beaf-19f0e6c3aa8c"
TEST_FIELD_IDS = ["4000", "4002", "4004", "353"]
TEST_W2_SCHEMA = {...}  # Pre-configured W-2 extraction schema
```

These values are **known to work** and proven through testing.

## Customizing the Initial Message

### Option 1: Edit `langgraph.json`

Change the `default_input.messages[0].content` to your desired message:

```json
{
  "default_input": {
    "messages": [
      {
        "role": "user",
        "content": "Your custom message here"
      }
    ]
  }
}
```

### Option 2: Edit `DEFAULT_INITIAL_MESSAGE` in Python

Change the `DEFAULT_INITIAL_MESSAGE` constant in `drawdoc_agent.py`:

```python
DEFAULT_INITIAL_MESSAGE = """Your custom message here"""
```

### Option 3: Disable Auto-Start

Remove the `default_input` from `langgraph.json`:

```json
{
  "dependencies": ["."],
  "graphs": {
    "drawdoc-awm": "./drawdoc_agent.py:agent"
  },
  "env": ".env"
}
```

Then manually type your first message in LangGraph Studio.

## Environment Setup

Make sure your `.env` file is configured:

```bash
# Copy the example if you haven't already
cp .env.example .env

# Edit with your credentials
# nano .env
```

Required variables:
- `ENCOMPASS_ACCESS_TOKEN`
- `ENCOMPASS_USERNAME`
- `ENCOMPASS_PASSWORD`
- `ENCOMPASS_CLIENT_ID`
- `ENCOMPASS_CLIENT_SECRET`
- `ENCOMPASS_INSTANCE_ID`
- `ENCOMPASS_SUBJECT_USER_ID`
- `LANDINGAI_API_KEY`

## Expected Behavior

### On Launch:
1. LangGraph Studio loads the agent
2. Agent receives the default message automatically
3. Agent creates a test plan
4. Agent executes all 3 test phases
5. Results displayed in the chat

### You'll See:
```
Agent: I'll create a plan to test the Encompass tools...

[Todo List Created]
✓ Test Setup Phase
□ Field Read Test Phase
□ Document Download Test Phase
□ Data Extraction Test Phase
□ Results Summary Phase

Agent: Executing Field Read Test...
[Calls read_loan_fields tool]
Results: {'4000': 'Felicia', '4002': 'Lamberth', ...}

Agent: Executing Document Download Test...
[Calls download_loan_document tool]
Downloaded 583,789 bytes

Agent: Executing Data Extraction Test...
[Calls extract_document_data tool]
Extracted: 
{
  "employer_name": "Hynds Bros Inc",
  "employee_name": "Aliya Sorenson",
  "tax_year": "2024"
}

Agent: All tests completed successfully! ✅
```

## Troubleshooting

### "No .env file found"
- Make sure `.env` exists in the DrawDoc-AWM directory
- Check `langgraph.json` has `"env": ".env"`

### "Token expired" or "401 Unauthorized"
- Get a fresh token: `../../get_fresh_token_and_test.sh`
- Update `ENCOMPASS_ACCESS_TOKEN` in `.env`

### Agent doesn't auto-start
- Check `langgraph.json` has the `default_input` section
- Verify the JSON syntax is valid
- Try restarting LangGraph Studio

### Tools not found
- Make sure `python-dotenv` is installed: `pip install python-dotenv`
- Check that baseCopilotAgent is in the path
- Verify all 4 tools are defined with `@tool` decorator

## Manual Testing

If you want to test manually without the auto-start:

```bash
# Test individual tools
python drawdoc_agent.py --test-tools

# Test agent workflow
python drawdoc_agent.py --demo
```

## LangGraph Commands

```bash
# Start development server
langgraph dev

# Build the agent
langgraph build

# Test the agent
langgraph test

# Deploy to cloud
langgraph deploy
```

## Studio Features

When running in LangGraph Studio, you can:

- ✅ **See the graph visualization** - Watch agent nodes execute
- ✅ **Inspect state** - View agent state at each step
- ✅ **Step through execution** - Pause and inspect
- ✅ **View tool calls** - See parameters and results
- ✅ **Modify messages** - Change the flow mid-execution
- ✅ **Time travel** - Go back to previous states

## Files

```
DrawDoc-AWM/
├── drawdoc_agent.py          # Main agent with tools and DEFAULT_INITIAL_MESSAGE
├── langgraph.json            # LangGraph config with default_input
├── .env                       # Your credentials (gitignored)
├── .env.example              # Template
├── planner_prompt.md         # Planning guidance
├── LANGGRAPH_STUDIO_SETUP.md # This file
└── requirements.txt          # Dependencies
```

## Next Steps

1. **Launch and Watch**: Start LangGraph Studio and watch the auto-test
2. **Customize**: Modify the initial message for your use case
3. **Build Workflows**: Create custom workflows using the 4 tools
4. **Deploy**: Deploy to LangGraph Cloud when ready

---

**Status**: ✅ Ready for LangGraph Studio  
**Auto-Start**: ✅ Configured  
**Test Data**: ✅ Hardcoded and working  
**Date**: October 30, 2024

