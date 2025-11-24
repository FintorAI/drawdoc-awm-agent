# Drawing Docs - Verification Agent

Automated field verification for loan documents. Compares prep agent output against Encompass values and corrects mismatches.

## 🔒 Safe Testing with Dry Run Mode

**Default:** Dry run enabled - no writes to production Encompass!

## Quick Start

```bash
# 1. Pull latest
git pull origin main

# 2. Run test (safe - dry run mode)
python test_verification_agent.py

# 3. Review results
# - Console: Summary
# - verification_results.json: Structured data
# - logs/*.log: Detailed debug info
```

## Documentation

📘 **[Quick Start Guide](VERIFICATION_AGENT_README.md)** - Usage, examples, commands  
🔧 **[Technical Details](TECHNICAL_DETAILS.md)** - Architecture, troubleshooting, implementation

## What It Does

```
Prep Output (correct values) → Compare → Encompass (potentially wrong)
                                   ↓
                           Track Corrections
                                   ↓
                           Dry Run: Print Only
                           Production: Write to Encompass
```

## Key Files

- `agents/verification_agent.py` - Main agent
- `tools/verification_tools.py` - Verification tools
- `tools/field_lookup_tools.py` - Field lookup tools
- `test_verification_agent.py` - Test script
- `data/prep_output.json` - Input (prep agent results)
- `verification_results.json` - Output (corrections found)
- `logs/verification_test_*.log` - Debug logs

## Features

✅ Dry run mode (safe testing)  
✅ Comprehensive logging  
✅ Structured JSON output  
✅ Field-by-field comparison  
✅ Automatic correction tracking  
✅ SOP compliance checking  

---

**Need help?** See [Quick Start Guide](VERIFICATION_AGENT_README.md) or [Technical Details](TECHNICAL_DETAILS.md)
