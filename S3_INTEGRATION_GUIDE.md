# DocRepo S3 Integration Guide

## Overview

The DrawDoc-AWM agent now integrates with docRepo S3 storage to make downloaded files accessible to the UI. When documents are downloaded from Encompass, they are automatically uploaded to per-client S3 buckets and the S3 keys are stored in the agent state.

## How It Works

### 1. Document Download Flow

```
Encompass → download_loan_document() → Local /tmp + docRepo S3 → UI Access
```

When a W-2 document is downloaded:
1. **Download from Encompass**: Document bytes are fetched from Encompass API
2. **Save Locally**: File is saved to `/tmp` for AI extraction
3. **Upload to S3**: Document is uploaded to docRepo S3 with metadata
4. **Return S3 Info**: S3 keys (client_id, doc_id) are returned in tool response

### 2. State Structure for UI

The `download_loan_document` tool returns:

```json
{
  "file_path": "/tmp/document_d78186cc_1762141512.pdf",
  "file_size_bytes": 583789,
  "file_size_kb": 570.11,
  "attachment_id": "d78186cc-a8a2-454f-beaf-19f0e6c3aa8c",
  "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
  "s3_info": {
    "s3_uploaded": true,
    "client_id": "docAgent",
    "doc_id": "387596ee_d78186cc",
    "message": "Uploaded",
    "data_object_stored": true,
    "bucket_created": false
  }
}
```

**Note**: All documents use the consistent client ID `"docAgent"`, ensuring they all go to the same S3 bucket. The bucket is created automatically on first upload.

### 3. UI Access Pattern

The UI can retrieve documents using the S3 keys:

```typescript
// From agent state, get s3_info
const { client_id, doc_id } = state.s3_info;

// Call your backend to get presigned URL
const response = await fetch(
  `${DOCREPO_GET_API_BASE}/doc?clientId=${client_id}&docId=${doc_id}`,
  {
    headers: {
      'Authorization': `Bearer ${DOCREPO_AUTH_TOKEN}`
    }
  }
);

const { url, expiresInSeconds } = await response.json();

// Use the presigned URL to display or download the file
window.open(url);
```

## Environment Variables

Add these to your `.env` file:

```bash
# DocRepo S3 Storage Configuration
DOCREPO_AUTH_TOKEN=esfuse-token
DOCREPO_PUT_API_BASE=https://ekrhupxp1d.execute-api.us-west-1.amazonaws.com/prod
DOCREPO_GET_API_BASE=https://m49lxh6q5d.execute-api.us-west-1.amazonaws.com/prod
DOCREPO_CREATE_API_BASE=https://dnobbdlzyb.execute-api.us-west-1.amazonaws.com/prod
```

See `env.example` for a complete template.

## DocRepo API Endpoints

### 1. Upload (PUT)
**Endpoint**: `POST /put`
**Purpose**: Upload PDF with metadata to client's S3 bucket

```bash
curl -X POST "${DOCREPO_PUT_API_BASE}/put" \
  -H "Authorization: Bearer ${DOCREPO_AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "clientId": "387596ee",
    "docId": "d78186cc",
    "content_base64": "<base64_pdf_content>",
    "dataObject": {
      "document_type": "W2",
      "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
      "file_size_bytes": 583789
    }
  }'
```

### 2. Get (GET)
**Endpoint**: `GET /doc`
**Purpose**: Retrieve presigned URL for document

```bash
curl -X GET "${DOCREPO_GET_API_BASE}/doc?clientId=docAgent&docId=387596ee_d78186cc" \
  -H "Authorization: Bearer ${DOCREPO_AUTH_TOKEN}"
```

**Response**:
```json
{
  "clientId": "docagent",
  "docId": "387596ee_d78186cc",
  "url": "https://bucket.s3.amazonaws.com/key?X-Amz-Signature=...",
  "expiresInSeconds": 300,
  "hasDataObject": true,
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

### 3. Create Bucket (POST)
**Endpoint**: `POST /create-bucket`
**Purpose**: Create or confirm S3 bucket for client

```bash
curl -X POST "${DOCREPO_CREATE_API_BASE}/create-bucket" \
  -H "Authorization: Bearer ${DOCREPO_AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"clientId": "387596ee"}'
```

## Data Object Structure

Each uploaded document includes a `dataObject` with metadata:

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

This metadata is stored in DynamoDB alongside the S3 URL and can be retrieved with the document.

## Integration Points

### Agent Tools

- **`_upload_to_docrepo_s3()`**: Helper function to upload documents
- **`_get_docrepo_signed_url()`**: Helper function to retrieve signed URLs
- **`download_loan_document()`**: Main tool that orchestrates download + upload

### Planning Prompt

Updated terminology:
- ❌ Old: "Download W-2 Document"
- ✅ New: "Get W-2 Document"

### System Prompt

Updated to reflect S3 upload in Phase 2:
> Phase 2: download_loan_document(loan_id, attachment_id) → Get W-2 and upload to S3, returns file_path and s3_info

## Security

- **Authentication**: All API calls require Bearer token in `Authorization` header
- **Per-Client Buckets**: Each client ID gets its own isolated S3 bucket
- **Encryption**: Buckets have SSE-AES256 encryption enabled
- **Access Control**: Public access is blocked, only presigned URLs work
- **Short-Lived URLs**: Presigned URLs expire in 300 seconds (5 minutes)

## LangGraph Cloud Deployment

When deploying to LangGraph Cloud:

1. **Set Environment Variables**: Add docRepo variables in LangGraph Cloud dashboard
2. **Network Access**: Ensure LangGraph Cloud can reach docRepo API endpoints
3. **Token Management**: Use secure environment variables, not hardcoded tokens

## Testing

Test the S3 integration locally:

```bash
# Run with test data
cd agents/DrawDoc-AWM
python drawdoc_agent.py --test-tools

# Check logs for [DOCREPO] entries
# ✅ Success: "[DOCREPO] Success - Uploaded to S3 for client 387596ee"
# ❌ Failed: "[DOCREPO] Upload failed - Status 401: Unauthorized"
```

## Troubleshooting

### S3 Upload Fails

**Symptom**: `s3_uploaded: false` in tool response

**Common Causes**:
1. Invalid or missing `DOCREPO_AUTH_TOKEN`
2. Network connectivity issues
3. Bucket doesn't exist for client

**Solution**:
```bash
# Verify token
echo $DOCREPO_AUTH_TOKEN

# Test connectivity
curl -I https://ekrhupxp1d.execute-api.us-west-1.amazonaws.com/prod

# Create bucket if needed
curl -X POST "${DOCREPO_CREATE_API_BASE}/create-bucket" \
  -H "Authorization: Bearer ${DOCREPO_AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"clientId": "387596ee"}'
```

### Missing S3 Info in State

**Symptom**: UI can't find `s3_info` in agent state

**Solution**: Ensure the agent stores the full tool response including `s3_info` in state. The response should be available in the message history.

### Presigned URL Expired

**Symptom**: 403 Forbidden when accessing S3 URL

**Solution**: URLs expire after 5 minutes. Call the Get endpoint again to generate a fresh URL.

## API Reference

Full API documentation: `/Users/masoud/Desktop/WORK/WindowsEC2LangGraph/APIDOCS/docRepo/README.md`

## Next Steps

1. **UI Integration**: Update UI to retrieve and display files using S3 keys
2. **Bucket Creation**: Ensure buckets are created for new client IDs
3. **Monitoring**: Add logging/metrics for S3 upload success/failure rates
4. **Cleanup**: Implement lifecycle policies to expire old documents

