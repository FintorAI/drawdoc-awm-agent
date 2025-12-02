# Simple Loan Files Solution - Minimal Approach ✅

## Problem
Agent uploads files to S3 but doesn't populate state, so UI shows empty file list.

## Solution (IMPLEMENTED)
Add `loan_files` to state using `context_schema`. Just 4 lines of code!

---

## Implementation (DONE ✅)

### Step 1: Define State Schema (4 lines)

Added to `drawdoc_agent.py` before creating agent (around line 1125):

```python
from typing import TypedDict
from typing_extensions import NotRequired

class DrawDocState(TypedDict):
    """Custom state schema for DrawDoc agent."""
    loan_files: NotRequired[dict[str, dict]]  # Loan documents from Encompass
```

### Step 2: Use context_schema in Agent

```python
agent = create_deep_agent(
    agent_type="DrawDoc-AWM",
    context_schema=DrawDocState,  # ← Add this!
    # ... rest of config
)
```

### Step 3: Modified download_loan_document Tool

Changed to return `Command` that updates `loan_files` state:

Now the tool returns:

```python
@tool
def download_loan_document(
    loan_id: str,
    attachment_id: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    # ... download and S3 upload code ...
    
    loan_file_metadata = {
        "name": "W-2 Document (2024)",
        "size": 583789,
        "type": "application/pdf",
        "document_type": "W2",
        "uploaded_at": "2025-11-03T...",
        "s3_client_id": "docAgent",
        "s3_doc_id": "387596ee...d78186cc",
        "s3_uploaded": True,
    }
    
    return Command(
        update={
            "loan_files": {"W-2 Document (2024)": loan_file_metadata},
            "messages": [
                ToolMessage(content=json.dumps({
                    "file_path": "/tmp/document_d78186cc_xxx.pdf",
                    "file_size_bytes": 583789,
                    "added_to_ui": True
                }), tool_call_id=tool_call_id)
            ],
        }
    )
```

### Why This Works

**Answer**: We defined `loan_files` in the `context_schema` parameter of `create_deep_agent()`. This adds `loan_files` to the agent's state schema, so tools can update it with Command.

---

## UI-Side: Read loan_files and files

### State Structure

```typescript
{
  "todos": [...],              // From PlanningMiddleware
  "files": {...},              // From FilesystemMiddleware (agent-created files)
  "loan_files": {              // From download_loan_document tool
    "W-2 Document (2024)": {
      "name": "W-2 Document (2024)",
      "size": 583789,
      "type": "application/pdf",
      "document_type": "W2",
      "s3_client_id": "docAgent",
      "s3_doc_id": "387596ee...d78186cc",
      "s3_uploaded": true
    }
  }
}
```

### HomePage.tsx Changes

```typescript
const [loanFiles, setLoanFiles] = useState<Record<string, any>>({});
const [agentFiles, setAgentFiles] = useState<Record<string, any>>({});

// Fetch state
const state = await client.threads.getState(threadId);
if (state.values.loan_files) setLoanFiles(state.values.loan_files);
if (state.values.files) setAgentFiles(state.values.files);

// Pass both to sidebar
<ModeSidebar loanFiles={loanFiles} agentFiles={agentFiles} />
```

### ModernFileTree.tsx

Show two folders:
- **📄 Loan Files** (from `loan_files` state)
- **🤖 Agent Files** (from `files` state)

```typescript
// Loan Files
Object.entries(loanFiles).map(([filename, metadata]) => (
  <div onClick={() => onFileClick(metadata)}>
    {metadata.name}
    <span>{metadata.document_type}</span>
  </div>
))

// Agent Files  
Object.entries(agentFiles).map(([path, fileData]) => (
  <div onClick={() => onFileClick({ path, content: fileData.content.join('\n') })}>
    {path}
  </div>
))
```

### FileViewer Logic

```typescript
// Loan file? Fetch from DocRepo
if (file.s3_client_id && file.s3_doc_id) {
  const url = await getDocRepoPresignedUrl(file.s3_client_id, file.s3_doc_id);
  // Display PDF from URL
}

// Agent file? Display inline
if (file.content) {
  // Display content directly
}
```

---

## Summary

### Agent Changes
1. ✅ Import Command, ToolMessage, InjectedToolCallId
2. ✅ Change `download_loan_document` return type to `Command`
3. ✅ Return `Command(update={"loan_files": {...}})`
4. ✅ Remove references to add_loan_file() from instructions

### UI Changes
1. Read `loan_files` from state
2. Read `files` from state (already exists)
3. Show both in file tree (two folders)
4. Handle S3 files vs inline files in viewer

**That's it! No middleware, no complex changes.**

