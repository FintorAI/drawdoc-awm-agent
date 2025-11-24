# Tools Module

This module contains all the tools and utilities used by the preparation agent. All tools are **CSV-driven** and dynamically load data from `DrawingDoc Verifications.csv`.

## Structure

```
tools/
├── __init__.py              # Module exports
├── csv_loader.py            # Central CSV data loader (single source of truth)
├── extraction_schemas.py    # Dynamic extraction schema generation
└── field_mappings.py        # Dynamic field mapping from extracted fields to Encompass IDs
```

## CSV-Driven Architecture

All tools now read dynamically from `DrawingDoc Verifications.csv` instead of using hardcoded values:

### Before (Hardcoded)
- ❌ Hardcoded schemas in `extraction_schemas.py`
- ❌ Hardcoded field mappings in `field_mappings.py`
- ❌ Hardcoded preferred document mappings

### After (Dynamic)
- ✅ Schemas generated from CSV field data
- ✅ Field mappings derived from CSV
- ✅ Preferred documents loaded from CSV

## Usage

### CSV Loader

```python
from tools.csv_loader import get_csv_loader

loader = get_csv_loader()

# Get all document types
doc_types = loader.get_document_types()

# Get fields for a document type
fields = loader.get_fields_for_document("Final 1003")

# Get field-to-document mappings
mappings = loader.get_field_to_documents_mapping()
```

### Extraction Schemas

```python
from tools.extraction_schemas import get_extraction_schema, list_supported_document_types

# Get schema for a document type (generated from CSV)
schema = get_extraction_schema("W-2")

# List all supported document types (from CSV)
doc_types = list_supported_document_types()
```

### Field Mappings

```python
from tools.field_mappings import (
    get_field_mapping,
    get_all_mappings_for_document,
    get_preferred_documents_for_field,
)

# Get Encompass field ID for an extracted field
field_id = get_field_mapping("ID", "first_name")  # Returns "4000"

# Get all mappings for a document type
mappings = get_all_mappings_for_document("Final 1003")

# Get preferred documents for a field
preferred = get_preferred_documents_for_field("4000")  # Returns ["ID"]
```

## Benefits

1. **Single Source of Truth**: CSV file is the only place to update field mappings
2. **Automatic Updates**: Changes to CSV automatically reflect in schemas and mappings
3. **No Code Changes**: Adding new fields or documents only requires CSV updates
4. **Better Organization**: Tools are separated into logical modules
5. **Easier Maintenance**: Clear separation of concerns

## Migration Notes

- Old `extraction_schemas.py` and `field_mappings.py` in the root `preparation_agent/` folder are kept for backward compatibility but are deprecated
- All new code should use `tools.extraction_schemas` and `tools.field_mappings`
- The CSV file must be present in the `preparation_agent/` directory


