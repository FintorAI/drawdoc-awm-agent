#!/usr/bin/env python3
"""
Test script to verify both .env files are loaded correctly
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import primitives which loads both .env files
from agents.drawdocs.tools import primitives

print("=" * 80)
print("ENVIRONMENT VARIABLE LOADING TEST")
print("=" * 80)
print()

# Test variables that should come from LOCAL .env
print("📋 Variables from LOCAL .env (drawdoc-awm-agent):")
print("-" * 80)

local_vars = {
    "LANDINGAI_API_KEY": "LandingAI API Key",
    "ENABLE_ENCOMPASS_WRITES": "Encompass Write Safety Flag",
    "DOCREPO_AUTH_TOKEN": "DocRepo Auth Token (optional)",
}

for var_name, description in local_vars.items():
    value = os.getenv(var_name)
    if value:
        masked = value[:10] + "..." if len(value) > 10 else value
        print(f"✅ {var_name}: {masked}")
        print(f"   └─ {description}")
    else:
        print(f"❌ {var_name}: NOT SET")
        print(f"   └─ {description}")
        if var_name == "LANDINGAI_API_KEY":
            print(f"   └─ ⚠️  CRITICAL: Required for document extraction!")

print()
print("📋 Variables from MCP SERVER .env (encompass-mcp-server):")
print("-" * 80)

mcp_vars = {
    "ENCOMPASS_CLIENT_ID": "Client ID for OAuth",
    "ENCOMPASS_CLIENT_SECRET": "Client Secret for OAuth",
    "ENCOMPASS_INSTANCE_ID": "Instance ID",
    "ENCOMPASS_API_SERVER": "API Server URL",
    "ENCOMPASS_SCOPE": "OAuth Scope",
}

for var_name, description in mcp_vars.items():
    value = os.getenv(var_name)
    if value:
        if "SECRET" in var_name:
            masked = value[:4] + "*" * 20 + value[-4:] if len(value) > 8 else "***"
        else:
            masked = value
        print(f"✅ {var_name}: {masked}")
        print(f"   └─ {description}")
    else:
        print(f"❌ {var_name}: NOT SET")
        print(f"   └─ {description}")

print()
print("=" * 80)
print("MCP HTTP CLIENT STATUS")
print("=" * 80)
print(f"Available: {primitives.MCP_HTTP_CLIENT_AVAILABLE}")
print()

if primitives.MCP_HTTP_CLIENT_AVAILABLE:
    print("✅ MCP HTTP client is available and ready to use")
else:
    print("❌ MCP HTTP client is NOT available")
    print("   Check if encompass-mcp-server directory exists in parent folder")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)

# Check if critical variables are present
landingai = bool(os.getenv("LANDINGAI_API_KEY"))
encompass_client = bool(os.getenv("ENCOMPASS_CLIENT_ID"))
encompass_instance = bool(os.getenv("ENCOMPASS_INSTANCE_ID"))

print()
if landingai and encompass_client and encompass_instance:
    print("✅ ALL CRITICAL VARIABLES PRESENT")
    print("   Your agents should work correctly!")
else:
    print("❌ MISSING CRITICAL VARIABLES:")
    if not landingai:
        print("   • LANDINGAI_API_KEY - Required for document extraction")
    if not encompass_client:
        print("   • ENCOMPASS_CLIENT_ID - Required for Encompass API")
    if not encompass_instance:
        print("   • ENCOMPASS_INSTANCE_ID - Required for Encompass API")
    print()
    print("Fix: Add missing variables to the appropriate .env file")

print()
print("=" * 80)

