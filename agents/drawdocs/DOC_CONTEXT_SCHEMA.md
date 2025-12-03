# Doc Context Schema - Specification

**Version**: 1.0  
**Date**: December 1, 2025  
**Status**: DRAFT (For Review)

---

## Overview

The `doc_context` is the **internal data contract** between agents in the docs draw pipeline. It standardizes the output from Prep Agent and ensures consistent input to Drawcore, Verification, and Orderdocs agents.

---

## Schema Location

```
agents/drawdocs/doc_context_schema.json
```

---

## Key Design Decisions

### **1. Hybrid Approach**
The schema combines:
- ✅ **Current structure** (`results.field_mappings`, `results.extracted_entities`) - What exists today
- ✅ **Normalized fields** (`borrowers`, `property`, `loan`, `contacts`) - Future semantic access

**Why**: Backward compatibility + future-ready

### **2. Required vs Optional**
**Required fields**:
- `loan_id` - Always needed
- `results` - Core extraction data
- `results.field_mappings` - Used by Drawcore
- `results.extracted_entities` - Used by Verification

**Optional fields**:
- `borrowers`, `property`, `loan`, `contacts`, `fees` - Future enhancements
- `timing`, `errors`, `warnings` - Metadata

### **3. Flexibility**
- `additionalProperties: false` on root level - Prevents unexpected fields
- `additionalProperties: true` on `extracted_entities` - Allows any document type
- `oneOf` for field values - Supports string, number, boolean, null

---

## Core Structure

```json
{
  "loan_id": "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6",
  
  // CRITICAL: Used by all downstream agents
  "results": {
    "field_mappings": {
      "4008": "John Doe",        // Encompass Field ID → Value
      "356": 290000,
      "CD1.X69": "$168,259.37"
    },
    "extracted_entities": {
      "ID": {                    // By document type
        "borrower_first_name": "John"
      },
      "Title Report": {
        "escrow_company_name": "ABC Title"
      }
    }
  },
  
  // METADATA: For tracking and debugging
  "total_documents_found": 172,
  "documents_processed": 17,
  "status": "success",
  "timing": { ... },
  "errors": [],
  "warnings": [],
  
  // FUTURE: Normalized semantic access (optional)
  "borrowers": [],
  "property": {},
  "loan": {},
  "contacts": {},
  "fees": {}
}
```

---

## Field Descriptions

### **Core Fields**

| Field | Type | Required | Description | Used By |
|-------|------|----------|-------------|---------|
| `loan_id` | string (UUID) | ✅ Yes | Encompass loan GUID | All agents |
| `results.field_mappings` | object | ✅ Yes | Field ID → Value mapping | Drawcore, Orderdocs |
| `results.extracted_entities` | object | ✅ Yes | Raw extractions by doc type | Verification |
| `total_documents_found` | integer | ❌ No | Total docs in eFolder | Reporting |
| `documents_processed` | integer | ❌ No | Docs successfully extracted | Reporting |
| `status` | enum | ❌ No | Overall status | Orchestrator |

### **Metadata Fields**

| Field | Type | Description |
|-------|------|-------------|
| `loan_context` | object | Precondition check results |
| `documents_used` | array | List of doc types processed |
| `timing` | object | Performance metrics |
| `errors` | array | Extraction errors |
| `warnings` | array | Non-critical warnings |

### **Normalized Fields (Future)**

| Field | Type | Description | Status |
|-------|------|-------------|--------|
| `borrowers` | array | Structured borrower data | 🔮 Future |
| `property` | object | Structured property data | 🔮 Future |
| `loan` | object | Structured loan data | 🔮 Future |
| `contacts` | object | Structured contact data | 🔮 Future |
| `fees` | object | Structured fee data | 🔮 Future |

---

## Agent Consumption Patterns

### **Drawcore Agent**
```python
# Primary usage: Update Encompass fields
field_mappings = doc_context["results"]["field_mappings"]

for field_id, value in field_mappings.items():
    # Read current value
    current = read_fields(loan_id, [field_id])
    
    # Compare and update
    if current[field_id] != value:
        write_fields(loan_id, {field_id: value})
```

### **Verification Agent**
```python
# Validate extracted values
extracted = doc_context["results"]["extracted_entities"]
field_mappings = doc_context["results"]["field_mappings"]

# Check SOP rules
for field_id, value in field_mappings.items():
    validate_against_sop(field_id, value)
```

### **Orderdocs Agent**
```python
# Check field completeness
field_mappings = doc_context["results"]["field_mappings"]
documents_used = doc_context.get("documents_used", [])

# Verify all required fields exist
required_fields = get_required_fields(documents_used)
missing = [f for f in required_fields if f not in field_mappings]
```

---

## Validation

### **Using Python**
```python
import json
from jsonschema import validate

# Load schema
with open("doc_context_schema.json") as f:
    schema = json.load(f)

# Validate doc_context
def validate_doc_context(doc_context):
    try:
        validate(instance=doc_context, schema=schema)
        return True, None
    except Exception as e:
        return False, str(e)

# Usage
valid, error = validate_doc_context(prep_agent_output)
if not valid:
    raise ValueError(f"Invalid doc_context: {error}")
```

### **Install jsonschema**
```bash
pip install jsonschema
```

---

## Migration Plan

### **Phase 1: Add Schema (Current)**
- ✅ Create schema file
- ✅ Document structure
- ❌ Don't enforce yet

### **Phase 2: Add Validation (Next)**
- Add validation to Prep Agent output
- Add validation to Drawcore Agent input
- Warnings only (don't break)

### **Phase 3: Enforce (Later)**
- Make validation required
- Reject invalid doc_context
- Update all agents

### **Phase 4: Normalize (Future)**
- Populate `borrowers`, `property`, `loan`, `contacts`
- Update agents to use normalized fields
- Deprecate `extracted_entities` access

---

## Examples

### **Minimal Valid doc_context**
```json
{
  "loan_id": "b73fb60d-8f5d-4cbb-a05d-f1f2d1217af6",
  "results": {
    "field_mappings": {
      "4000": "John",
      "4002": "Doe"
    },
    "extracted_entities": {
      "ID": {
        "borrower_first_name": "John",
        "borrower_last_name": "Doe"
      }
    }
  }
}
```

### **Complete doc_context**
See `doc_context_schema.json` examples section.

---

## Breaking Changes

### **What Would Break Agents**

❌ **Removing required fields**:
```json
// BREAKS: Missing "results"
{
  "loan_id": "...",
  "field_mappings": {}  // Wrong location
}
```

❌ **Changing structure**:
```json
// BREAKS: Wrong nesting
{
  "loan_id": "...",
  "results": {
    "fields": {}  // Should be "field_mappings"
  }
}
```

### **What Won't Break Agents**

✅ **Adding optional fields**:
```json
{
  "loan_id": "...",
  "results": { ... },
  "new_optional_field": "..."  // OK
}
```

✅ **Adding to normalized fields**:
```json
{
  "loan_id": "...",
  "results": { ... },
  "borrowers": [...]  // OK - currently unused
}
```

---

## Open Questions

### **For Discussion**

1. **Should `loan_context` be required?**
   - Pro: Ensures preconditions checked
   - Con: Prep agent might fail to get it (403, etc.)
   - **Current**: Optional

2. **Should `documents_used` be required?**
   - Pro: Helps Orderdocs know what to check
   - Con: Easy to derive from `extracted_entities`
   - **Current**: Optional

3. **When to populate normalized fields?**
   - Option A: Prep Agent does it (more work now)
   - Option B: Future enhancement (keep simple)
   - **Current**: Future enhancement

4. **Should we version the schema?**
   - Add `"schema_version": "1.0"`?
   - **Current**: No versioning yet

---

## Review Checklist

- [ ] Does the structure match current Prep Agent output?
- [ ] Are all required fields actually required by downstream agents?
- [ ] Are optional fields truly optional?
- [ ] Is the schema flexible enough for future changes?
- [ ] Is it too flexible (allowing bad data)?
- [ ] Are the examples correct and helpful?
- [ ] Does it support all current use cases?

---

## Next Steps

### **After Review**
1. **Get feedback** on schema design
2. **Adjust** based on feedback
3. **Add validation** to Prep Agent (warnings only)
4. **Test** with real data
5. **Document** any edge cases
6. **Version** the schema if needed

---

## Questions?

- Is `results` the right name? Or should it be `data`?
- Should we split `field_mappings` by phase (borrower_fields, property_fields)?
- Should `extracted_entities` use field IDs instead of semantic names?
- Are the normalized fields (borrowers, property, etc.) worth the complexity?

---

**Status**: Ready for review! 📋

Please review and provide feedback before we implement validation.

