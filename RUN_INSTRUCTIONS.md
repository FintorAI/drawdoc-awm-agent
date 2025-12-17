# 🚀 How to Run DrawDoc Agent (Frontend + Backend)

## ✅ Prerequisites

- Python 3.11+
- Node.js 18+
- Virtual environment activated
- `.env` file configured with MCP credentials

---

## 📋 Quick Reference

| Component | Port | Command | URL |
|-----------|------|---------|-----|
| **Backend API** | 8000 | `python backend/main.py` | http://localhost:8000 |
| **Gradio UI** | 7860 | `python agents/drawdocs/gradio_app.py` | http://localhost:7860 |
| **Frontend** | 3000 | `cd frontend && npm run dev` | http://localhost:3000 |

---

## 🎯 Option 1: Full Stack (Recommended)

Run all three components for complete functionality.

### Terminal 1: Backend API
```bash
cd /Users/antonboquer/Documents/Fintor/drawdoc-awm-agent

# Activate virtual environment
source venv/bin/activate

# Run FastAPI backend
python backend/main.py

# Expected output:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# ✅ Backend ready at http://localhost:8000
```

### Terminal 2: Frontend (Next.js)
```bash
cd /Users/antonboquer/Documents/Fintor/drawdoc-awm-agent/frontend

# Install dependencies (first time only)
npm install

# Run Next.js dev server
npm run dev

# Expected output:
# ▲ Next.js 16.x.x
# - Local: http://localhost:3000
# ✅ Frontend ready at http://localhost:3000
```

### Terminal 3: Gradio UI (Optional)
```bash
cd /Users/antonboquer/Documents/Fintor/drawdoc-awm-agent

# Activate virtual environment
source venv/bin/activate

# Run Gradio interface
python agents/drawdocs/gradio_app.py

# Expected output:
# Running on local URL: http://127.0.0.1:7860
# ✅ Gradio UI ready at http://localhost:7860
```

---

## 🧪 Option 2: Backend + API Only (Testing)

For testing the verification agent with new field IDs:

### Single Terminal:
```bash
cd /Users/antonboquer/Documents/Fintor/drawdoc-awm-agent

# Activate virtual environment
source venv/bin/activate

# Run backend
python backend/main.py
```

### Test the API:
```bash
# In another terminal, test with curl:
curl http://localhost:8000/api/health

# Start a DrawDocs run:
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "drawdocs",
    "loan_id": "e0353726-87e6-4ac1-940c-cdde87ddc8e3"
  }'
```

---

## 🎨 Option 3: Gradio UI Only (Quick Testing)

Simplest option for testing the orchestrator:

```bash
cd /Users/antonboquer/Documents/Fintor/drawdoc-awm-agent
source venv/bin/activate
python agents/drawdocs/gradio_app.py
```

Then:
1. Open http://localhost:7860
2. Enter loan ID: `e0353726-87e6-4ac1-940c-cdde87ddc8e3`
3. Click "Run Orchestrator"
4. Watch live progress

---

## 🔧 Verify New Fields Are Working

### Quick Test Script:
```bash
cd /Users/antonboquer/Documents/Fintor/drawdoc-awm-agent
source venv/bin/activate
python test_verification_demo.py
```

**Expected Output:**
```
================================================================================
TEST SUMMARY
================================================================================
✅ Field Mappings: PASS
✅ Demo Mode: ACTIVE
✅ Validation Functions: PASS

🎉 ALL TESTS PASSED - Ready for frontend/backend integration!

New fields implemented:
  - Closing Date (748)
  - Disbursement Date (2553)
  - First Payment Date (682)
  - Property Tax Amount (HUD41)
  - HOI Annual Premium (HUD42)
  - Vesting (1872)
  - Marital Status (52)
  - Product/Amortization (LE1.X5)

Demo mode is ACTIVE - safe to test!
```

---

## 🔒 Demo Mode (Safe Testing)

### Current Status:
```bash
ENABLE_ENCOMPASS_WRITES=false  # ✅ Demo mode ACTIVE
```

**What this means:**
- ✅ All validations run normally
- ✅ All field IDs read data correctly
- ✅ All checks execute
- ❌ NO writes to Encompass (safe!)

### To Enable Writes (Production):
Edit `.env`:
```bash
ENABLE_ENCOMPASS_WRITES=true  # ⚠️ Use with caution!
```

---

## 📊 Accessing the Interfaces

### Backend API Documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Frontend Dashboard:
- **Home**: http://localhost:3000
- **Runs List**: http://localhost:3000/runs
- **Run Detail**: http://localhost:3000/runs/{run_id}

### Gradio UI:
- **Interface**: http://localhost:7860

---

## 🧪 Test Loan for New Fields

Use this loan to test all new field IDs:

```
Loan ID: e0353726-87e6-4ac1-940c-cdde87ddc8e3
Loan Number: 2512926182
Type: Conventional (ARM)
State: CA
```

**What it tests:**
- ✅ ARM detection (LE1.X5)
- ✅ Property Tax (HUD41)
- ✅ HOI Premium (HUD42)
- ✅ Vesting (1872)
- ✅ Marital Status (52)
- ✅ State rules (CA)

---

## 🐛 Troubleshooting

### Backend won't start:
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill the process if needed
kill -9 <PID>
```

### Frontend won't start:
```bash
# Clear Next.js cache
cd frontend
rm -rf .next
npm install
npm run dev
```

### Gradio won't start:
```bash
# Check if port 7860 is in use
lsof -i :7860

# Kill the process if needed
kill -9 <PID>
```

### MCP Authentication fails:
```bash
# Verify MCP credentials in .env
grep MCP_ .env

# Should see:
# MCP_ENCOMPASS_API_SERVER=https://concept.api.elliemae.com
# MCP_ENCOMPASS_CLIENT_ID=uexzo92
# MCP_ENCOMPASS_INSTANCE_ID=TEBE11215893
```

---

## 📝 Environment Variables

Required in `.env`:

```bash
# MCP Encompass (Demo Environment)
MCP_ENCOMPASS_API_SERVER=https://concept.api.elliemae.com
MCP_ENCOMPASS_CLIENT_ID=uexzo92
MCP_ENCOMPASS_CLIENT_SECRET=<your_secret>
MCP_ENCOMPASS_INSTANCE_ID=TEBE11215893
MCP_ENCOMPASS_SMART_USER=smartuser@encompass:
MCP_ENCOMPASS_SCOPE=lp

# Regular Encompass (Production Environment)
ENCOMPASS_API_BASE_URL=https://api.elliemae.com
ENCOMPASS_USERNAME=<your_username>
ENCOMPASS_PASSWORD=<your_password>
ENCOMPASS_CLIENT_ID=<your_client_id>
ENCOMPASS_CLIENT_SECRET=<your_secret>
ENCOMPASS_INSTANCE_ID=<your_instance>

# Write Safety
ENABLE_ENCOMPASS_WRITES=false  # Keep false for testing!

# LandingAI (for document OCR)
LANDINGAI_API_KEY=<your_api_key>
```

---

## ✅ Success Checklist

- [ ] Virtual environment activated
- [ ] `.env` file configured
- [ ] Backend running on port 8000
- [ ] Frontend running on port 3000 (optional)
- [ ] Gradio running on port 7860 (optional)
- [ ] Demo mode active (`ENABLE_ENCOMPASS_WRITES=false`)
- [ ] Test verification script passes
- [ ] Can access backend at http://localhost:8000/docs
- [ ] Can access frontend at http://localhost:3000 (if running)

---

## 🎉 Ready to Test!

Once all components are running:

1. **Backend API**: http://localhost:8000/docs
2. **Frontend Dashboard**: http://localhost:3000
3. **Gradio UI**: http://localhost:7860

Use test loan: `e0353726-87e6-4ac1-940c-cdde87ddc8e3`

All new field IDs are implemented and working! 🚀

