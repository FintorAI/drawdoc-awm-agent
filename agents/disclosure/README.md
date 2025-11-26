# Disclosure Agent

Disclosure agent for Encompass loan processing. This agent ensures all required disclosure fields are populated before sending to the loan officer for review.

## Architecture

The disclosure agent consists of three sub-agents:

1. **Verification Agent**: Checks if required disclosure fields have values in Encompass
2. **Preparation Agent**: Populates missing fields using AI-based derivation and cleans existing values
3. **Request Agent**: Sends disclosure review notification to loan officers via email

## Usage

### Command Line

```bash
python agents/disclosure/orchestrator_agent.py --loan-id <LOAN_ID> --lo-email <EMAIL>
```

### Gradio UI

```bash
python agents/disclosure/gradio_app.py
```

### Python API

```python
from agents.disclosure import run_disclosure_orchestrator

results = run_disclosure_orchestrator(
    loan_id="387596ee-7090-47ca-8385-206e22c9c9da",
    lo_email="loan.officer@example.com",
    demo_mode=True
)
```

## Features

- **Demo Mode**: Test without making actual changes (DRY_RUN)
- **AI-Based Field Derivation**: Uses intelligent search and reasoning to populate missing fields
- **Field Normalization**: Cleans phone numbers, dates, SSNs, and addresses
- **Email Notifications**: Sends status summary to loan officers
- **Retry Logic**: Automatic retry with exponential backoff
- **Progress Tracking**: Real-time updates for UI integration

## Configuration

Set environment variables in `.env`:

```
ENCOMPASS_ACCESS_TOKEN=your_token
ENCOMPASS_CLIENT_ID=your_client_id
ENCOMPASS_CLIENT_SECRET=your_secret
ENCOMPASS_INSTANCE_ID=your_instance

# Email configuration (TBD)
EMAIL_SERVICE=smtp
EMAIL_FROM=noreply@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email
SMTP_PASSWORD=your_password
```

## Input Format

```json
{
  "loan_id": "387596ee-7090-47ca-8385-206e22c9c9da",
  "lo_email": "loan.officer@example.com",
  "demo_mode": true,
  "max_retries": 2
}
```

## Output Format

```json
{
  "loan_id": "...",
  "timestamp": "2025-11-26T...",
  "demo_mode": true,
  "verification": {
    "fields_checked": 50,
    "fields_with_values": 45,
    "fields_missing": 5
  },
  "preparation": {
    "fields_populated": 3,
    "fields_cleaned": 42,
    "fields_failed": 2
  },
  "request": {
    "email_sent": true,
    "lo_email": "loan.officer@example.com"
  },
  "summary": "..."
}
```

## Testing

```bash
python agents/disclosure/test_orchestrator.py
```

