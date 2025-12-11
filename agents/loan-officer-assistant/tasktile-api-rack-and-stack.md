# TaskTile API – Client Integration Guide (Rack & Stack)

> **Scope:** Rack & Stack pipeline (v1)  
> **Auth model:** Client credentials (client_id / client_secret → access token)  
> **Format:** JSON over HTTPS

---

## 1. Overview

TaskTile exposes an HTTP API that lets you:

- Register as a **client** and receive API credentials.
- Obtain an **access token** using your client credentials.
- **Upload PDF files** via presigned URLs.
- **Trigger a Rack & Stack pipeline job** on those uploads.
- **Receive a job manifest via webhook** when the pipeline is complete.

**Base URL (example)**

```text
https://tasktile.staging.cybersoftbpo.ai/api
```

In the examples below, assume all endpoints are relative to this base URL.

---

## 2. Authentication Flow

### 2.1. Register as a Client

Before calling any other TaskTile endpoints, you must register as a client.  
This is typically done once per integration.

**Endpoint**

```http
POST /clients
Content-Type: application/json
```

**Request Body**

```json
{
  "name": "Workspace/Client Name",
  "webhook_url": "https://your-system.com/webhooks/tasktile"
}
```

- `name` – Your company/workspace name (used for identification).
- `webhook_url` – Where TaskTile will POST the **job manifest** once a pipeline completes.

**Successful Response – 201 Created**

```json
{
  "client_id": "6e195161-803c-47c7-a4df-458b50e6d0b7",
  "client_secret": "plainSecretValueShownOnce"
}
```

> ⚠️ **Important**
>
> - Store `client_secret` securely. It will not be returned again.
> - Treat it like a password or private key.

---

### 2.2. Get an Access Token

Use your `client_id` and `client_secret` to obtain an access token.

**Endpoint**

```http
POST /auth/token
Content-Type: application/json
```

**Request Body**

```json
{
  "client_id": "6e195161-803c-47c7-a4df-458b50e6d0b7",
  "client_secret": "plainSecretValueShownOnce"
}
```

**Successful Response – 200 OK**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

- `access_token` – Use this in the `Authorization` header.
- `expires_in` – Token lifetime in seconds (e.g., 3600 = 1 hour).

**Error – 401 Unauthorized**

```json
{
  "error": "Unauthorized"
}
```

> After you receive an `access_token`, include it in **all subsequent API calls** using the `Authorization` header:
>
> ```http
> Authorization: Bearer {access_token}
> ```

---

## 3. Rack & Stack Pipeline – End-to-End Flow

High-level steps:

1. **Initiate upload** and get a presigned URL (`POST /uploads/initiate`).
2. **Upload the PDF file** directly to the returned `put_url`.
3. **Confirm upload completion** (`POST /uploads/complete`).
4. **Create a Rack & Stack job** using the list of completed `upload_ids` (`POST /jobs`).
5. **Wait for webhook**: TaskTile sends a **job manifest** to your `webhook_url` when done.

---

## 3.1. Initiate Upload

Create an upload session and get a presigned PUT URL.

**Endpoint**

```http
POST /uploads/initiate
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body**

```json
{
  "filename": "demo_Blob.pdf",
  "content_type": "application/pdf",
  "size": 1234567
}
```

- `filename` – Original file name (used for references/logging).
- `content_type` – Must be `"application/pdf"`.
- `size` – File size in bytes.

**Successful Response – 200 OK**

```json
{
  "upload_id": "f72678f7-b4db-4f3e-8144-77feb51ef8fa",
  "bucket": "tasktile-dev",
  "key": "clients/{client_id}/uploads/2025-12-10/demo_Blob.pdf",
  "put_url": "https://s3-presigned-url-here",
  "expires_in": 900
}
```

- `upload_id` – **Save this.** You will use it later when creating a job.
- `put_url` – Presigned URL where you upload the file (single PUT request).
- `expires_in` – URL validity in seconds (here `15 * 60 = 900` seconds = 15 minutes).

**Error Responses**

- `400 Bad Request`

  ```json
  { "error": "filename, content_type, size are required" }
  ```

- `415 Unsupported Media Type`

  ```json
  { "error": "Only application/pdf supported" }
  ```

- `409 Conflict`

  ```json
  { "error": "File too large for single upload (max 200MB)" }
  ```

- `500 Internal Server Error`

  ```json
  { "error": "Failed to create upload session" }
  ```

---

## 3.2. Upload File to the Presigned URL

This step is **directly to storage** (e.g., S3), not to TaskTile’s domain.  
You **do not** include your TaskTile `Authorization` header here.

### Example – Node.js (stream)

```ts
const putRes = await fetch(put_url, {
  method: 'PUT',
  headers: {
    'Content-Type': mime_type!,
    'Content-Length': String(byte_size!),
  },
  body: getObj.Body as unknown as ReadableStream,
  duplex: 'half',
} as any)
```

### Example – Browser File upload

```ts
const uploadRes = await fetch(put_url, {
  method: 'PUT',
  headers: {
    'Content-Type': file.type,
  },
  body: file, // File object from input[type=file]
})
```

> ✅ **Requirements**
>
> - Upload the file exactly once using `PUT` to `put_url`.
> - Do not modify query parameters or headers beyond `Content-Type` (and optionally `Content-Length` if required).

---

## 3.3. Confirm Upload Completion

Once the file is successfully uploaded to the `put_url`, notify TaskTile.

**Endpoint**

```http
POST /uploads/complete
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body**

```json
{
  "upload_id": "f72678f7-b4db-4f3e-8144-77feb51ef8fa"
}
```

**Successful Response – 200 OK**

```json
{
  "upload_id": "f72678f7-b4db-4f3e-8144-77feb51ef8fa",
  "source_bucket": "tasktile-dev",
  "source_key": "clients/{client_id}/uploads/2025-12-10/demo_Blob.pdf",
  "page_count": 5
}
```

**Error Responses**

- `400 Bad Request`

  ```json
  { "error": "upload_id is required" }
  ```

- `404 Not Found`

  ```json
  { "error": "Upload not found" }
  ```

- `403 Forbidden` – Upload does not belong to this client

  ```json
  { "error": "Forbidden" }
  ```

- `409 Conflict` – Invalid upload state

  ```json
  { "error": "Upload not in ongoing state" }
  ```

- `409 Conflict` – File missing or zero size

  ```json
  { "error": "Object not found or zero size" }
  ```

- `500 Internal Server Error`

  ```json
  { "error": "Failed to update upload" }
  ```

> Repeat **3.1 → 3.3** for each PDF you want to include in the Rack & Stack job, collecting all `upload_id`s.

---

## 3.4. Create a Rack & Stack Job

Once all uploads are completed, create a job that runs the **Rack & Stack** pipeline.

**Endpoint**

```http
POST /jobs
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body**

```json
{
  "pipeline_name": "rack-and-stack",
  "upload_ids": ["f72678f7-b4db-4f3e-8144-77feb51ef8fa"],
  "categories_url": "https://sbiqai.staging.cybersoftbpo.ai/api/workspaces/1/categories",
  "entity": {
    "example_field": "example value"
  }
}
```

- `pipeline_name` – Currently `"rack-and-stack"` for this flow.
- `upload_ids` – Non-empty array of upload IDs from `/uploads/complete`.
- `categories_url` – URL where TaskTile can retrieve **category schema** definitions.
- `entity` – Free-form JSON describing the entity/loan/context.

**Successful Response – 201 Created**

```json
{
  "job_id": "c081f2c5-7c3f-41a2-ad55-603280f1eead",
  "pipeline": [
    "ai:pagegen",
    "hil:splicer",
    "hil:splitter",
    "ai:ocr_partial",
    "ai:classify",
    "hil:classify",
    "ai:indexing",
    "hil:indexing"
  ],
  "blobs": [
    {
      "id": "6f7a53a2-50c3-4254-baac-e637026f46b9",
      "bucket": "tasktile-dev",
      "source_key": "clients/{client_id}/uploads/2025-12-10/demo_Blob.pdf",
      "metadata": {
        "example": "metadata"
      }
    }
  ],
  "groups": [
    {
      "id": "4b70db7c-a7ad-4729-be4e-fb0b174c309b",
      "blob_id": "6f7a53a2-50c3-4254-baac-e637026f46b9",
      "type": "pagegen",
      "tool": "ai",
      "status": "pending",
      "user_id": null
    }
  ]
}
```

**Error Responses**

- `400 Bad Request`

  ```json
  { "error": "upload_ids is required (non-empty array)" }
  ```

- `403 Forbidden` – Some uploads belong to another client

  ```json
  { "error": "One or more upload_ids do not belong to the client" }
  ```

- `400 Bad Request` – Uploads not found

  ```json
  { "error": "Some upload_ids not found: {id1}, {id2}" }
  ```

- `400 Bad Request` – Infected uploads

  ```json
  {
    "error": "One or more uploads are infected: f72678f7-b4db-4f3e-8144-77feb51ef8fa",
    "uploads": [
      {
        "id": "f72678f7-b4db-4f3e-8144-77feb51ef8fa",
        "scan_status": "infected",
        "status": "errored"
      }
    ]
  }
  ```

- `400 Bad Request` – Uploads with errors

  ```json
  {
    "error": "One or more uploads have errored: f72678f7-b4db-4f3e-8144-77feb51ef8fa",
    "uploads": [
      {
        "id": "f72678f7-b4db-4f3e-8144-77feb51ef8fa",
        "scan_status": "error",
        "status": "errored"
      }
    ],
    "hint": "Please re-upload or contact support"
  }
  ```

- `400 Bad Request` – Uploads still pending

  ```json
  {
    "error": "One or more uploads are still pending: f72678f7-b4db-4f3e-8144-77feb51ef8fa",
    "uploads": [
      {
        "id": "f72678f7-b4db-4f3e-8144-77feb51ef8fa",
        "scan_status": "pending",
        "status": "ongoing"
      }
    ],
    "retry_after_seconds": 10
  }
  ```

- `400 Bad Request` – Pipeline/template errors

  ```json
  { "error": "Pipeline template not found" }
  ```

  or

  ```json
  { "error": "No pipeline or template provided" }
  ```

> After a successful response from `/jobs`, the pipeline is queued and will go through AI and HIL steps asynchronously.  
> You do **not** need to poll; final results are delivered via the webhook manifest.

---

## 4. Webhook: Job Manifest

When the job finishes (success or failure), TaskTile sends a **manifest** to your `webhook_url` configured during client registration.

### 4.1. Example Manifest (Minimal)

```jsonc
{
  "version": "1.0.0",
  "job": {
    "id": "c081f2c5-7c3f-41a2-ad55-603280f1eead",
    "pipeline_name": "rack_and_stack_v1",
    "steps": [
      "ai:pagegen",
      "hil:splicer",
      "hil:splitter",
      "ai:ocr_partial",
      "ai:classify",
      "hil:classify",
      "ai:indexing",
      "hil:indexing"
    ],
    "status": "success",
    "created_at": "1765376136675",
    "completed_at": "1765376547817",
    "task_groups": [
      {
        "id": "4b70db7c-a7ad-4729-be4e-fb0b174c309b",
        "blob_id": "6f7a53a2-50c3-4254-baac-e637026f46b9",
        "type": "pagegen",
        "tool": "ai",
        "end_time": "1765376179269",
        "created_at": "1765376136729"
      }
    ],
    "tasks": [
      {
        "id": "9e55f318-76ba-4cbe-af47-85e29f52517b",
        "task_group_id": "fc3dec8b-e257-40f5-968a-073a0d1f4b73",
        "blob_id": "6f7a53a2-50c3-4254-baac-e637026f46b9",
        "document_id": "78a48052-ec2f-401b-9d71-3469ac053b76",
        "type": "classify",
        "tool": "ai",
        "attempt": 1,
        "start_time": "1765376274209",
        "end_time": "1765376290187",
        "created_at": "1765376271387",
        "output": {
          "id": "4b549320-b395-48dc-89cc-69e41cd2b34a",
          "bucket": "tasktile-dev",
          "output_key": "",
          "content_type": "application/json",
          "created_at": "1765376290191"
        }
      },
      {
        "id": "100e68ad-4355-4ce9-bf1f-d7a6a418cb52",
        "task_group_id": "0dd8b87c-8a31-4a66-b2f3-b1db368c7cde",
        "blob_id": "6f7a53a2-50c3-4254-baac-e637026f46b9",
        "type": "indexing",
        "tool": "hil",
        "attempt": 1,
        "start_time": "1765376547462",
        "end_time": "1765376547808",
        "created_at": "1765376355256",
        "output": {
          "id": "d069eff4-f916-46f5-85d0-f790e7577e6b",
          "bucket": "tasktile-dev",
          "output_key": "clients/6e195161-803c-47c7-a4df-458b50e6d0b7/jobs/c081f2c5-7c3f-41a2-ad55-603280f1eead/blobs/6f7a53a2-50c3-4254-baac-e637026f46b9/indexing/hil/7de0cfcf-2a13-40f9-a55c-2a5eabb13911_content.json",
          "content_type": "application/json",
          "created_at": "1765376547811"
        }
      }
    ]
  },
  "tenant": {
    "client_id": "6e195161-803c-47c7-a4df-458b50e6d0b7"
  },
  "counts": {
    "blobs": 1,
    "documents": 5
  },
  "input": [
    {
      "id": "6f7a53a2-50c3-4254-baac-e637026f46b9",
      "type": "blob",
      "upload_id": "f72678f7-b4db-4f3e-8144-77feb51ef8fa",
      "source": {
        "bucket": "tasktile-dev",
        "key": "clients/6e195161-803c-47c7-a4df-458b50e6d0b7/uploads/2025-12-10/demo_Blob.pdf"
      }
    }
  ],
  "documents": [
    {
      "id": "78a48052-ec2f-401b-9d71-3469ac053b76",
      "blob_id": "6f7a53a2-50c3-4254-baac-e637026f46b9",
      "source": {
        "bucket": "tasktile-dev",
        "key": "clients/6e195161-803c-47c7-a4df-458b50e6d0b7/jobs/c081f2c5-7c3f-41a2-ad55-603280f1eead/blobs/6f7a53a2-50c3-4254-baac-e637026f46b9/documents/78a48052-ec2f-401b-9d71-3469ac053b76.pdf"
      },
      "category": {
        "category_id": 2174,
        "category_name": "SmartFees",
        "source": "hil"
      },
      "metadata": {
        "group_name": "4",
        "group_index": 3,
        "total_pages": 1,
        "object_name": "clients/6e195161-803c-47c7-a4df-458b50e6d0b7/jobs/c081f2c5-7c3f-41a2-ad55-603280f1eead/blobs/6f7a53a2-50c3-4254-baac-e637026f46b9/documents/78a48052-ec2f-401b-9d71-3469ac053b76.pdf",
        "category": "2174_SmartFees",
        "borrowers": [
          {
            "lastName": "Dailamy",
            "firstName": "Ramin",
            "middleName": null,
            "suffix": null,
            "dateSigned": null,
            "signed": null
          }
        ],
        "confidence": 0.9939765930175781,
        "exceptions": {
          "for_bullzip": false,
          "possible_wrong_upload": false,
          "unsupported_language": false,
          "is_missing_pages": false,
          "copy_is_not_clear": false,
          "truncated": false,
          "blank_page": false,
          "split_document": false,
          "clarify_information_with_client": false,
          "refer_to_qc": false,
          "not_for_encoding": false,
          "incomplete_unitization": false,
          "corrupted": false,
          "expired": false,
          "insufficient_information": false,
          "other_exception": false,
          "other_exception_text": ""
        },
        "vision_check": "passed"
      }
    }
  ]
}
```

---

## 4.2. Key Sections

- `version` – Manifest schema version.
- `job` – Job-level info:
  - `id`, `pipeline_name`, `steps[]`, `status`, `created_at`, `completed_at`.
  - `task_groups[]` & `tasks[]` – Execution breakdown by AI/HIL tools.
- `tenant.client_id` – Your TaskTile client ID.
- `counts` – Summary counts of blobs/documents.
- `input[]` – Original uploaded blobs (referencing `upload_id`, S3 bucket/key).
- `documents[]` – Final documents after Rack & Stack:
  - `id`, `blob_id`
  - `source.bucket` / `source.key` – where the processed PDF now resides.
  - `category` – Chosen category from category schema.
  - `metadata` – Category-specific metadata (driven by `categories_url` schema).

> Typical usage:
>
> 1. Use `documents[].source.bucket` + `source.key` to fetch the split PDFs via presigned URLs from TaskTile.
> 2. Use `documents[].category` and `metadata` to integrate into your own system.

---

## 5. Download Final Documents

To download the final processed documents, generate presigned URLs using the `source.bucket` and `source.key` from each document in the webhook manifest.

**Endpoint**

```http
POST /files/presign-get/batch
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body**

```json
{
  "files": [
    {
      "bucket": "tasktile-dev",
      "key": "clients/.../final.pdf",
      "expires_seconds": 1800,
      "response_content_disposition": "attachment; filename=\"final.pdf\""
    }
  ]
}
```

- `bucket` – From `documents[].source.bucket`.
- `key` – From `documents[].source.key`.
- `expires_seconds` – (Optional) URL validity in seconds (default 1800s).
- `response_content_disposition` – (Optional) Sets the `Content-Disposition` header for download filename.

**Successful Response – 200 OK**

```json
[
  {
    "url": "https://s3-presigned-url",
    "expires_at": 1765379000000
  }
]
```

---

## 6. Summary of Endpoints

### Authentication & Clients

- `POST /clients`  
  Register a new client and obtain `client_id` + `client_secret`.

- `POST /auth/token`  
  Exchange `client_id` + `client_secret` for an `access_token`.

### Uploads

- `POST /uploads/initiate`  
  Create an upload session and receive a presigned `put_url`.

- `PUT {put_url}`  
  Upload the PDF file directly to storage (no TaskTile auth header).

- `POST /uploads/complete`  
  Confirm that the upload to `put_url` is done and valid.

### Jobs

- `POST /jobs`  
  Create and start a job for the `rack-and-stack` pipeline using `upload_ids`.

### Webhooks

- `POST {webhook_url}` (from TaskTile to you)  
  Receive the final **manifest** once the job completes.

### Files

- `POST /files/presign-get/batch`  
  Generate presigned URLs to download final processed documents.
