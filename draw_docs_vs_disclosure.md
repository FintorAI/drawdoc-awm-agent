# Draw Docs vs Disclosure: Quick Reference

**Created**: November 28, 2025 | **Naomi**: Disclosure | **Anton**: Draw Docs

---

## TL;DR

| | Disclosure (Naomi) | Draw Docs (Anton) |
|--|-------------------|-------------------|
| **When** | Before CTC | After CTC + CD ACK + 3-day wait |
| **What** | Create CD, calculate MI, send for signature | Verify docs, update forms, order package |
| **Docs** | None - trust processor | Verify 35+ documents |
| **Output** | Signed CD → hands off to Draw Docs | Closing package → send to title |

---

## What Do I Build? (MVP)

### Naomi - Disclosure (~5 days)

| Feature | Status |
|---------|--------|
| Field existence check (~20 fields) | ✅ KEEP |
| Conventional MI calculation | ✅ KEEP |
| Basic CD population (pages 1-3) | ✅ KEEP |
| Send email to LO | ✅ KEEP |
| Fee tolerance - flag only | ⚠️ SIMPLIFY |
| FHA/VA/USDA MI | 🔴 CUT |
| APR calculation | 🔴 CUT |
| COC CD detection | 🔴 CUT |
| Signature tracking | 🔴 CUT |
| 3-day wait automation | 🔴 CUT |

### Anton - Draw Docs (~7 days)

| Feature | Status |
|---------|--------|
| Doc download (10 key docs) | ✅ KEEP |
| Basic entity extraction | ✅ KEEP |
| Conventional loans only | ✅ KEEP |
| NV + CA states only | ✅ KEEP |
| Basic form updates | ✅ KEEP |
| Generate package | ✅ KEEP |
| Update milestone + send to title | ✅ KEEP |
| PTF conditions - log only | ⚠️ SIMPLIFY |
| FHA/VA/USDA handlers | 🔴 CUT |
| TX/FL/CO/IL state rules | 🔴 CUT |
| Branch/Investor config | 🔴 CUT |
| Trust, MERS, Mavent | 🔴 CUT |

---

## Shared Components

| Component | Owner | When |
|-----------|-------|------|
| `shared/encompass_io.py` | **Naomi** | Day 1-2 |
| `shared/mi_calculator.py` | **Naomi** | Day 3-4 |
| `shared/fee_tolerance.py` | **Naomi** | Day 5 |

Anton imports from `shared/` as needed.

---

## 2-Week Sprint

```
WEEK 1
──────
Naomi:
├── Day 1-2: shared/encompass_io.py + field checker
├── Day 3-4: shared/mi_calculator.py + CD population
└── Day 5: shared/fee_tolerance.py + email to LO

Anton:
├── Day 1-2: Doc download + extraction
├── Day 3-4: Conventional form updates (NV/CA)
└── Day 5: Field verification (imports shared/)

WEEK 2
──────
Naomi:
├── Day 1-2: Polish + edge cases
└── Day 3-5: Integration + testing

Anton:
├── Day 1-2: Package generation + milestone
└── Day 3-5: Handoff wiring + testing
```

---

## MVP Success = Done If:

**Disclosure:**
- [ ] Checks ~20 key fields exist
- [ ] Calculates Conventional MI
- [ ] Populates basic CD
- [ ] Sends email to LO
- [ ] Flags fee tolerance issues

**Draw Docs:**
- [ ] Downloads 10 key documents
- [ ] Extracts borrower/property/loan basics
- [ ] Updates core fields (Conventional, NV/CA)
- [ ] Generates closing package
- [ ] Sends to title

**Non-MVP cases:** Log "Requires manual processing" → hand off to human

---

## Handoff: Disclosure → Draw Docs

```python
class DisclosureHandoff:
    cd_status: str          # "CD Approved"
    cd_ack_date: date       # When borrower signed
    waiting_period_ends: date
    tolerance_issues: List[str]  # Flagged, not auto-cured
```

Draw Docs checks: `cd_status == "CD Approved"` and `today >= waiting_period_ends`

---

## Phase 2 Backlog

| Priority | Feature | Owner |
|----------|---------|-------|
| P1 | FHA/VA loan types | Both |
| P2 | USDA + Texas rules | Both/Anton |
| P3 | APR calc, Mavent, PTF auto-add | Naomi/Anton |
| P4 | Branch/Investor, Trust | Anton |
| P5 | ARM, Non-QM, DPA, Construction | Both |

---

*Full architecture details: see `disclosure_architecture.md` and `draw_docs_architecture.md`*
