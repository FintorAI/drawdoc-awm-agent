# S3 Auto-Bucket Creation - Implementation Summary

## Overview

The DrawDoc-AWM agent now automatically creates S3 buckets when needed, eliminating the need for manual bucket setup. The first time a document is uploaded for a client, the bucket is created automatically.

## Key Features

### 1. Automatic Bucket Creation

When uploading fails with "No S3 bucket" error, the system:
1. Automatically calls the create-bucket API
2. Retries the upload
3. Returns success with `bucket_created: true` flag

### 2. Consistent Client ID

All documents use `client_id = "docAgent"` to ensure:
- Single bucket for all documents
- Simplified bucket management
- Consistent file organization

### 3. Unique Document IDs

Documents are identified by combining loan ID and attachment ID:
- Format: `{loan_id[:8]}_{attachment_id[:8]}`
- Example: `387596ee_d78186cc`

## Implementation Details

### New Helper Function

```python
def _create_docrepo_bucket(client_id: str) -> dict[str, Any]:
    """Create an S3 bucket for a client in docRepo.
    
    This is idempotent - if the bucket already exists, it returns success.
    """
```

**Location**: Lines 126-201 in `drawdoc_agent.py`

### Updated Upload Function

The `_upload_to_docrepo_s3()` function now:

1. Attempts upload
2. If 400 error with "No S3 bucket" message:
   - Calls `_create_docrepo_bucket()`
   - Retries upload
3. Returns result with `bucket_created` flag if bucket was created

**Location**: Lines 204-349 in `drawdoc_agent.py`

### Document Upload Changes

```python
# OLD: Used loan ID as client ID (different bucket per loan)
client_id = loan_id[:8]
doc_id = attachment_id[:8]

# NEW: Consistent client ID (single bucket for all)
client_id = "docAgent"
doc_id = f"{loan_id[:8]}_{attachment_id[:8]}"
```

## Usage

### No Manual Setup Required

Simply run the agent - the bucket will be created automatically:

```bash
cd agents/DrawDoc-AWM
langgraph dev
```

On first document upload:
```
[DOCREPO] Uploading to S3 - Client: docAgent, Doc: 387596ee_d78186cc
[DOCREPO] Bucket doesn't exist, creating it for client docAgent
[DOCREPO] Creating bucket for client: docAgent
[DOCREPO] Bucket created - windowsec2-docrepo-docagent
[DOCREPO] Retrying upload after bucket creation
[DOCREPO] Success - Uploaded to S3 for client docAgent (after bucket creation)
```

Subsequent uploads use existing bucket:
```
[DOCREPO] Uploading to S3 - Client: docAgent, Doc: 387596ee_d78186cc
[DOCREPO] Success - Uploaded to S3 for client docAgent
```

## API Calls

### 1. Create Bucket (Automatic)

Called automatically when needed:

```http
POST https://dnobbdlzyb.execute-api.us-west-1.amazonaws.com/prod/create-bucket
Authorization: Bearer esfuse-token
Content-Type: application/json

{
  "clientId": "docAgent"
}
```

Response:
```json
{
  "message": "Bucket ready",
  "clientId": "docagent",
  "bucketName": "windowsec2-docrepo-docagent",
  "created": true
}
```

### 2. Upload Document

```http
POST https://ekrhupxp1d.execute-api.us-west-1.amazonaws.com/prod/put
Authorization: Bearer esfuse-token
Content-Type: application/json

{
  "clientId": "docAgent",
  "docId": "387596ee_d78186cc",
  "content_base64": "<base64_pdf>",
  "dataObject": {
    "document_type": "W2",
    "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
    "attachment_id": "d78186cc-a8a2-454f-beaf-19f0e6c3aa8c",
    "file_size_bytes": 583789,
    "uploaded_at": "2025-01-03T10:30:00Z",
    "source": "encompass"
  }
}
```

### 3. Get Document (UI Access)

```http
GET https://m49lxh6q5d.execute-api.us-west-1.amazonaws.com/prod/doc?clientId=docAgent&docId=387596ee_d78186cc
Authorization: Bearer esfuse-token
```

Response includes presigned URL valid for 5 minutes.

## Benefits

### For Development
✅ No manual bucket creation step
✅ Works out of the box with correct auth token
✅ Idempotent - safe to run multiple times

### For Production
✅ Single bucket for all documents
✅ Automatic bucket creation on first use
✅ Clear bucket naming: `windowsec2-docrepo-docagent`

### For UI Integration
✅ Consistent client_id for all API calls
✅ Unique doc_id prevents collisions
✅ Full metadata in dataObject for display

## Testing

### Test Auto-Creation

1. **Clear existing bucket** (optional - only if testing fresh creation):
   ```bash
   # Note: Only needed for testing, not for normal use
   # Bucket deletion would need to be done through AWS Console or CLI
   ```

2. **Run agent**:
   ```bash
   cd agents/DrawDoc-AWM
   langgraph dev
   ```

3. **Trigger W-2 validation**:
   - In LangGraph Studio UI
   - First document triggers bucket creation
   - Check logs for bucket creation messages

4. **Verify bucket exists**:
   ```bash
   curl -X POST "https://dnobbdlzyb.execute-api.us-west-1.amazonaws.com/prod/create-bucket" \
     -H "Authorization: Bearer esfuse-token" \
     -H "Content-Type: application/json" \
     -d '{"clientId": "docAgent"}'
   ```
   
   Should return `"created": false` (bucket already exists)

### Verify Upload

```bash
# Get document with presigned URL
curl -X GET "https://m49lxh6q5d.execute-api.us-west-1.amazonaws.com/prod/doc?clientId=docAgent&docId=387596ee_d78186cc" \
  -H "Authorization: Bearer esfuse-token" | jq '.'
```

Expected response includes:
- `url`: Presigned S3 URL (valid for 5 minutes)
- `hasDataObject`: true
- `dataObject`: Full document metadata

## Bucket Structure

```
windowsec2-docrepo-docagent/
├── 387596ee_d78186cc.pdf
├── 387596ee_e123456f.pdf
├── abc12345_f789abcd.pdf
└── ...
```

All documents in one bucket, identified by `{loanId[:8]}_{attachmentId[:8]}`

## Error Handling

### Scenario 1: Bucket Creation Fails

```python
{
  "s3_uploaded": false,
  "client_id": "docAgent",
  "doc_id": "387596ee_d78186cc",
  "error": "Failed to create bucket",
  "message": "Bucket creation failed"
}
```

**Resolution**: Check auth token and network connectivity

### Scenario 2: Upload Fails After Bucket Creation

```python
{
  "s3_uploaded": false,
  "client_id": "docAgent",
  "doc_id": "387596ee_d78186cc",
  "error": "Upload failed with status 400",
  "message": "Invalid base64 encoding"
}
```

**Resolution**: Check document bytes encoding

## Environment Variables

Required in `.env`:

```bash
DOCREPO_AUTH_TOKEN=esfuse-token
DOCREPO_PUT_API_BASE=https://ekrhupxp1d.execute-api.us-west-1.amazonaws.com/prod
DOCREPO_GET_API_BASE=https://m49lxh6q5d.execute-api.us-west-1.amazonaws.com/prod
DOCREPO_CREATE_API_BASE=https://dnobbdlzyb.execute-api.us-west-1.amazonaws.com/prod
```

## Deployment Checklist

- [x] Add docRepo environment variables to LangGraph Cloud
- [x] Verify network access to docRepo APIs
- [x] Test first document upload (triggers bucket creation)
- [x] Verify subsequent uploads use existing bucket
- [x] Test UI retrieval with presigned URLs

## Summary

✅ **Automatic**: Bucket created on first use
✅ **Idempotent**: Safe to retry, no errors if bucket exists
✅ **Consistent**: All documents use client_id "docAgent"
✅ **Traceable**: Full metadata in dataObject
✅ **UI-Ready**: Presigned URLs for document access

No manual bucket creation needed - just set the auth token and run!

