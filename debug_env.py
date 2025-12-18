"""Debug environment variable loading."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Check if .env file exists
env_path = Path(__file__).parent / ".env"
print(f"Looking for .env at: {env_path}")
print(f".env exists: {env_path.exists()}")

if env_path.exists():
    print(f"\nLoading .env from {env_path}...")
    load_dotenv(env_path, override=True)
    print("✓ .env loaded")
else:
    print("\n✗ .env file not found!")

# Check environment variables
print("\n" + "="*80)
print("ENVIRONMENT VARIABLES:")
print("="*80)

env_vars = [
    "ENCOMPASS_CLIENT_ID",
    "ENCOMPASS_CLIENT_SECRET",
    "ENCOMPASS_INSTANCE_ID",
    "ENCOMPASS_ACCESS_TOKEN",
    "ENCOMPASS_API_BASE_URL",
    "ENCOMPASS_USERNAME",
    "ENCOMPASS_PASSWORD",
    "ENCOMPASS_SUBJECT_USER_ID",
    "ENCOMPASS_SCOPE",
]

for var in env_vars:
    value = os.getenv(var)
    if value:
        # Mask sensitive values
        if "SECRET" in var or "PASSWORD" in var or "TOKEN" in var:
            display = value[:8] + "..." if len(value) > 8 else "***"
        else:
            display = value
        print(f"✓ {var:30} = {display}")
    else:
        print(f"✗ {var:30} = NOT SET")

print("\n" + "="*80)



