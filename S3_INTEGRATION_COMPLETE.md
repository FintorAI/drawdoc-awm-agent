# ✅ S3 Integration Complete - DrawDoc-AWM Agent

## Summary

Successfully integrated docRepo S3 storage into the DrawDoc-AWM agent. Documents are now automatically uploaded to per-client S3 buckets when downloaded from Encompass, with S3 keys stored in agent state for UI access.

## Changes Made

### 1. ✅ DocRepo S3 Helper Functions (`drawdoc_agent.py`)

Added two new helper functions for S3 operations:

#### `_upload_to_docrepo_s3()`
- Uploads document bytes to docRepo S3 with metadata
- Returns upload status, client_id, doc_id for UI access
- Includes automatic base64 encoding
- Supports optional `dataObject` for structured metadata

#### `_get_docrepo_signed_url()`
- Retrieves presigned URL for document access
- Returns URL valid for 300 seconds (5 minutes)
- Includes dataObject if available

**Location**: Lines 126-283 in `drawdoc_agent.py`

### 2. ✅ Updated `download_loan_document` Tool

Modified the tool to:
- Download document from Encompass
- Save locally to `/tmp` for AI extraction
- **Upload to docRepo S3** with document metadata
- Return both `file_path` (for extraction) and `s3_info` (for UI)

**Key Changes**:
- Tool description now says "Get a W-2 document" instead of "Download"
- Logs use `[GET_W2]` prefix instead of `[DOWNLOAD]`
- Returns comprehensive `s3_info` object with upload status

**Location**: Lines 590-674 in `drawdoc_agent.py`

### 3. ✅ Updated Planning Prompt

**File**: `planner_prompt.md`

**Changes**:
- Phase 2 renamed: "Download W-2 Document" → **"Get W-2 Document"**
- Updated description to mention S3 upload
- Added note about `s3_info` return value for UI access

**Location**: Lines 66-79 in `planner_prompt.md`

### 4. ✅ Updated System Prompt

**File**: `drawdoc_agent.py`

**Changes**:
- Phase 2 description updated to mention S3 upload
- Added note about `s3_info` containing client_id, doc_id, and upload status
- Maintains "Get W-2" terminology throughout

**Location**: Lines 918-944 in `drawdoc_agent.py`

### 5. ✅ Environment Variables Template

**File**: `env.example` (created)

Added required docRepo configuration:
```bash
DOCREPO_AUTH_TOKEN=esfuse-token
DOCREPO_PUT_API_BASE=https://ekrhupxp1d.execute-api.us-west-1.amazonaws.com/prod
DOCREPO_GET_API_BASE=https://m49lxh6q5d.execute-api.us-west-1.amazonaws.com/prod
DOCREPO_CREATE_API_BASE=https://dnobbdlzyb.execute-api.us-west-1.amazonaws.com/prod
```

**Location**: `agents/DrawDoc-AWM/env.example`

### 6. ✅ Integration Guide

**File**: `S3_INTEGRATION_GUIDE.md` (created)

Comprehensive documentation covering:
- How the integration works
- State structure for UI
- Environment variables setup
- DocRepo API endpoints
- Security considerations
- Troubleshooting guide

**Location**: `agents/DrawDoc-AWM/S3_INTEGRATION_GUIDE.md`

## How It Works

### Document Flow

```
┌─────────────┐         ┌──────────────────┐         ┌─────────────┐
│  Encompass  │ ──────> │ download_loan_   │ ──────> │   /tmp/     │
│     API     │         │    document()    │         │  (local)    │
└─────────────┘         └──────────────────┘         └─────────────┘
                                │
                                │ Upload
                                ▼
                        ┌──────────────────┐
                        │   DocRepo S3     │
                        │  (Per-client     │
                        │   buckets)       │
                        └──────────────────┘
                                │
                                │ Return s3_info
                                ▼
                        ┌──────────────────┐
                        │  Agent State     │
                        │  (UI accessible) │
                        └──────────────────┘
```

### Tool Response Structure

```python
{
    "file_path": "/tmp/document_d78186cc_1762141512.pdf",  # For AI extraction
    "file_size_bytes": 583789,
    "file_size_kb": 570.11,
    "attachment_id": "d78186cc-a8a2-454f-beaf-19f0e6c3aa8c",
    "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
    "s3_info": {  # For UI access
        "s3_uploaded": true,
        "client_id": "387596ee",  # Short loan ID
        "doc_id": "d78186cc",     # Short attachment ID
        "message": "Uploaded",
        "data_object_stored": true
    }
}
```

### S3 Data Object

Each uploaded document includes structured metadata:

```json
{
  "document_type": "W2",
  "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
  "attachment_id": "d78186cc-a8a2-454f-beaf-19f0e6c3aa8c",
  "file_size_bytes": 583789,
  "uploaded_at": "2025-01-03T10:30:00Z",
  "source": "encompass"
}
```

## UI Integration

The UI can access files using the S3 keys from agent state:

```typescript
// 1. Get s3_info from agent state
const { client_id, doc_id } = message.s3_info;

// 2. Call docRepo Get API to get presigned URL
const response = await fetch(
  `https://m49lxh6q5d.execute-api.us-west-1.amazonaws.com/prod/doc?clientId=${client_id}&docId=${doc_id}`,
  {
    headers: {
      'Authorization': 'Bearer esfuse-token'
    }
  }
);

const { url, expiresInSeconds, dataObject } = await response.json();

// 3. Use the presigned URL to display or download
// URL is valid for 300 seconds (5 minutes)
```

## Environment Setup

### Required Variables

Add to your `.env` file:

```bash
# DocRepo S3 Storage
DOCREPO_AUTH_TOKEN=esfuse-token
DOCREPO_PUT_API_BASE=https://ekrhupxp1d.execute-api.us-west-1.amazonaws.com/prod
DOCREPO_GET_API_BASE=https://m49lxh6q5d.execute-api.us-west-1.amazonaws.com/prod
```

### Optional Configuration

```bash
# For bucket creation (usually not needed)
DOCREPO_CREATE_API_BASE=https://dnobbdlzyb.execute-api.us-west-1.amazonaws.com/prod
```

## Testing

### Local Testing

```bash
# Test with real Encompass data
cd agents/DrawDoc-AWM
python drawdoc_agent.py --demo

# Check for successful S3 upload in logs:
# [GET_W2] Downloaded - 583,789 bytes (570.11 KB) saved to /tmp/...
# [DOCREPO] Uploading to S3 - Client: 387596ee, Doc: d78186cc
# [DOCREPO] Success - Uploaded to S3 for client 387596ee
```

### Verify S3 Upload

```bash
# Get presigned URL for uploaded document
curl -X GET "https://m49lxh6q5d.execute-api.us-west-1.amazonaws.com/prod/doc?clientId=387596ee&docId=d78186cc" \
  -H "Authorization: Bearer esfuse-token" | jq '.'

# Should return:
# {
#   "url": "https://bucket.s3.amazonaws.com/key?X-Amz-Signature=...",
#   "expiresInSeconds": 300,
#   "hasDataObject": true,
#   "dataObject": {...}
# }
```

## Deployment

### LangGraph Cloud

1. **Set Environment Variables**:
   - Go to LangGraph Cloud dashboard
   - Add `DOCREPO_AUTH_TOKEN`, `DOCREPO_PUT_API_BASE`, `DOCREPO_GET_API_BASE`

2. **Verify Network Access**:
   - Ensure LangGraph Cloud can reach docRepo API endpoints
   - Test connectivity from deployment environment

3. **Monitor Logs**:
   - Check for `[DOCREPO]` log entries
   - Verify successful uploads with `s3_uploaded: true`

## Security

✅ **Authentication**: Bearer token required for all API calls
✅ **Per-Client Isolation**: Each client ID gets separate S3 bucket
✅ **Encryption**: SSE-AES256 encryption enabled on all buckets
✅ **Access Control**: Public access blocked, only presigned URLs work
✅ **Short-Lived URLs**: Presigned URLs expire in 5 minutes

## Benefits

### For Agent
- ✅ Documents stored persistently in S3
- ✅ No need to manage large files in state
- ✅ Metadata stored alongside documents
- ✅ Simple client_id/doc_id key structure

### For UI
- ✅ Presigned URLs for secure file access
- ✅ 5-minute URL validity prevents stale links
- ✅ Document metadata available via API
- ✅ No direct S3 access needed (uses docRepo API)

### For System
- ✅ Per-client bucket isolation
- ✅ Automatic encryption and access control
- ✅ Scalable storage solution
- ✅ Easy cleanup via lifecycle policies

## Terminology Updates

All references updated from "Download" to "Get":

| Component | Old | New |
|-----------|-----|-----|
| Planning Prompt | "Download W-2 Document" | "Get W-2 Document" |
| System Prompt | "download W-2, returns file_path" | "Get W-2 and upload to S3, returns file_path and s3_info" |
| Tool Logs | `[DOWNLOAD]` | `[GET_W2]` |
| Tool Description | "Download a document..." | "Get a W-2 document..." |

## Files Modified

1. ✅ `drawdoc_agent.py` - Added S3 helpers, updated tool
2. ✅ `planner_prompt.md` - Updated Phase 2 description
3. ✅ `env.example` - Created with docRepo variables
4. ✅ `S3_INTEGRATION_GUIDE.md` - Created comprehensive guide
5. ✅ `S3_INTEGRATION_COMPLETE.md` - This summary document

## Next Steps

### For UI Team

1. **Implement File Display**:
   - Extract `s3_info` from agent state/messages
   - Call docRepo Get API with client_id and doc_id
   - Display presigned URL in file viewer component

2. **Handle URL Expiry**:
   - Store client_id/doc_id, not just the URL
   - Regenerate presigned URL on 403 errors
   - Show "loading" state while fetching URL

3. **Display Metadata**:
   - Show dataObject fields in UI (file size, upload time, document type)
   - Use for file categorization (W2, paystubs, etc.)

### For Backend Team

1. **Bucket Management**:
   - Ensure buckets exist for all client IDs
   - Implement lifecycle policies for old documents
   - Monitor storage costs

2. **Monitoring**:
   - Track S3 upload success/failure rates
   - Alert on authentication failures
   - Log presigned URL generation patterns

## Troubleshooting

See `S3_INTEGRATION_GUIDE.md` for detailed troubleshooting steps.

Common issues:
- Invalid auth token → Check `DOCREPO_AUTH_TOKEN` in .env
- Bucket doesn't exist → Call create-bucket endpoint first
- URL expired → Call Get API again for fresh URL

## Documentation

- **Full API Reference**: `/Users/masoud/Desktop/WORK/WindowsEC2LangGraph/APIDOCS/docRepo/README.md`
- **Integration Guide**: `S3_INTEGRATION_GUIDE.md`
- **Environment Template**: `env.example`

---

## Summary of Implementation

✅ **Objective Achieved**: Files are now uploaded to S3 and S3 keys are added to state for UI access

✅ **All Changes Complete**:
- DocRepo S3 upload helper functions
- Updated download_loan_document tool with S3 integration
- Updated planning and system prompts with "Get W2" terminology
- Environment variables documented
- Comprehensive integration guide created

✅ **Ready for Testing**: Agent can now be tested locally or deployed to LangGraph Cloud

✅ **UI Integration Ready**: S3 keys (client_id, doc_id) are available in agent state for UI to retrieve presigned URLs



