# Disclosure Agent v2 - Test Loan Fields Summary

## Quick Reference: All Required Fields for Happy Path

### 📋 MVP Eligibility (MUST PASS)

| Field ID | Field Name | Expected Value | Notes |
|----------|------------|----------------|-------|
| `1172` | Loan Type | `Conventional` | Only Conventional supported in MVP |
| `14` | Property State | `CA` or `NV` | Texas excluded |
| `19` | Loan Purpose | `Purchase` or `Refinance` | |

---

### 📅 TRID Compliance Fields

| Field ID | Field Name | Expected Value | Action |
|----------|------------|----------------|--------|
| `745` | Application Date | Recent date (e.g., `2024-12-01`) | READ - Must be within 3 business days |
| `LE1.X1` | LE Date Issued | Current date | WRITE by Preparation Agent |
| `3152` | Disclosure Sent Date | Calculated (App + 3 biz days) | READ - Verify not passed |
| `761` | Lock Date | Lock date if locked | READ |
| `432` | Lock Expiration | Expiration date | READ |
| `2400` | Rate Locked | `Y` or `N` | READ |

---

### 👤 Borrower Fields (1003 URLA)

| Field ID | Field Name | Expected Value | Status |
|----------|------------|----------------|--------|
| `4000` | Borrower First Name | `ATHENA` | Required |
| `4002` | Borrower Last Name | `WHITE` | Required |
| `65` | Borrower SSN | `900-88-7799` | Required |
| `1402` | Borrower Email | `toktok8calabarzon@gmail.com` | Required for eDisclosures |

---

### 🏠 Property Fields

| Field ID | Field Name | Expected Value | Status |
|----------|------------|----------------|--------|
| `11` | Property Address | `8080 BALLER ST` | Required |
| `12` | Property City | `Garden Grove` | Required |
| `14` | Property State | `CA` | Required (MVP: CA/NV only) |
| `15` | Property Zip | `92840` | Required |
| `1041` | Property Type | `Detached` | Required |
| `1811` | Occupancy Type | `PrimaryResidence` | Required |

---

### 💰 Loan Terms

| Field ID | Field Name | Expected Value | Notes |
|----------|------------|----------------|-------|
| `1109` | Loan Amount | `968877.00` | Required |
| `3` | Interest Rate | `6.0` | Required |
| `4` | Loan Term | `360` | Required (months) |
| `353` | LTV | `98.865` | If > 80%, MI required |
| `976` | CLTV | `98.865` | |
| `356` | Appraised Value | `980000` | Required |
| `136` | Purchase Price | `980000.00` | Required for Purchase |

---

### 📝 RegZ-LE Fields (Preparation Agent Updates)

| Field ID | Field Name | Expected Value | Action |
|----------|------------|----------------|--------|
| `LE1.X1` | LE Date Issued | Current date | **WRITE** |
| `1176` | Interest Days/Year | `360/360` | **WRITE** |
| `3514` | 0% Payment Option | (blank) | **VERIFY BLANK** |
| `3515` | Simple Interest | (blank) | **VERIFY BLANK** |
| `3516` | Biweekly Days | `365` | **WRITE** |
| `672` | Late Charge Days | `15` | **WRITE** (Conv=15) |
| `673` | Late Charge % | `5.0` | **WRITE** (Conv=5%, FHA/VA=4%) |
| `3517` | Assumption | `may not` | **WRITE** (Conv="may not") |
| `1751` | Buydown Marked | (check) | **READ** - If marked, update buydown fields |
| `664` | Prepay Indicator | `Will not` | **READ** - If "Will/May", update prepay fields |

---

### 💵 Cash to Close Fields

#### For PURCHASE loans:
| Field ID | Field Name | Expected Value | Action |
|----------|------------|----------------|--------|
| `NEWHUD2.X55` | Use Actual Down Payment | `true` | **WRITE** |
| `NEWHUD2.X56` | Closing Costs Financed | `true` | **WRITE** |
| `NEWHUD2.X57` | Include Payoffs in Adjustments | `true` | **WRITE** |

#### For REFINANCE loans:
| Field ID | Field Name | Expected Value | Action |
|----------|------------|----------------|--------|
| `NEWHUD2.X58` | Alternative Form Checkbox | `true` | **WRITE** |

#### CTC Verification:
| Field ID | Field Name | Expected Value | Notes |
|----------|------------|----------------|-------|
| `LE1.X77` | Displayed CTC (LE Page 2) | `44690.00` | Must match calculated |

---

### ✅ ATR/QM Flags (MANDATORY - All Must Be GREEN)

| Field ID | Field Name | Expected Value | Blocking If |
|----------|------------|----------------|-------------|
| `ATRQM.X1` | Loan Features Flag | `Meets Standard` (Green) | Red = BLOCK |
| `ATRQM.X2` | Points and Fees Flag | `Meets Standard` (Green) | Red = BLOCK |
| `ATRQM.X3` | Price Limit Flag | `Meets Standard` (Green) | Red = BLOCK |

---

### 🛡️ Mavent Compliance (MANDATORY)

| Check | Expected | Blocking If |
|-------|----------|-------------|
| Fails | `0` | Any Fail = BLOCK |
| Alerts | `0` | Any Alert = BLOCK |
| Warnings | `0` | Any Warning = Review |

---

### 📧 eDisclosures API (Required IDs)

| ID | Source | Value in Test Loan |
|----|--------|-------------------|
| `loanId` | Input | `b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6` |
| `applicationId` | `GET /encompass/v3/loans/{loanId}` → `applications[0].id` | `2a5e4b26-212e-4ce4-a1d5-04b6e353646b` |

---

### 👔 LO Info (Verification)

| Field ID | Field Name | Expected Value |
|----------|------------|----------------|
| `317` | LO Name | `Loan Officer 1` |
| `3238` | LO NMLS ID | (valid NMLS) |
| `3330` | Company NMLS | (valid NMLS) |

---

## 🚨 Current Test Loan Issues

The test loan `b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6` has these issues that need fixing for happy path:

| Field | Current Value | Needed Value | Reason |
|-------|---------------|--------------|--------|
| `745` (Application Date) | `2022-11-15` | Recent date | LE due date is passed |
| `LE1.X1` (LE Date Issued) | (empty) | Current date | LE not yet issued |
| `ATRQM.X1` | `Review Needed` | `Meets Standard` | ATR/QM blocking |
| `ATRQM.X2` | `Not Meet` | `Meets Standard` | ATR/QM blocking |
| `ATRQM.X3` | `Not Meet` | `Meets Standard` | ATR/QM blocking |

---

## 📊 Field Count Summary

| Category | Field Count | Required Actions |
|----------|-------------|------------------|
| MVP Eligibility | 3 | READ only |
| TRID | 6 | READ + check timing |
| Borrower | 4 | READ - verify populated |
| Property | 6 | READ - verify populated |
| Loan Terms | 7 | READ |
| RegZ-LE | 10 | READ + WRITE |
| CTC | 4-5 | WRITE based on loan purpose |
| ATR/QM | 3 | READ - must be GREEN |
| LO Info | 3 | READ - verify |
| **Total** | **~47** | |

---

## 🔄 Agent Workflow Summary

```
VERIFICATION AGENT:
├── Check MVP eligibility (1172, 14, 19)
├── Check TRID compliance (745, 3152)
├── Validate all forms (47 fields)
└── Check lock status (761, 432, 2400)

PREPARATION AGENT:
├── Update RegZ-LE (LE1.X1, 672, 673, 3517, etc.)
├── Calculate MI if LTV > 80%
└── Match CTC (NEWHUD2.X55-X58)

SEND AGENT:
├── Run Mavent check (API call)
├── Check ATR/QM flags (ATRQM.X1-X3)
└── Order eDisclosures (3 API calls)
```

