"""Shared CSV utilities for loading field mappings."""

import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def load_field_mappings(csv_path: Optional[Path] = None) -> List[Dict[str, str]]:
    """Load field mappings from DrawingDoc Verifications CSV file.
    
    Args:
        csv_path: Path to CSV file. If None, uses default path in packages/data/
        
    Returns:
        List of dictionaries with field information:
        - name: Field name
        - field_id: Encompass field ID
        - primary_document: Primary document type for this field
        - secondary_documents: Secondary document types (semicolon-separated)
        
    Example:
        fields = load_field_mappings()
        for field in fields:
            print(f"{field['name']} (ID: {field['field_id']})")
    """
    if csv_path is None:
        # Default to packages/data/DrawingDoc Verifications - Sheet1.csv
        csv_path = Path(__file__).parent.parent / "data" / "DrawingDoc Verifications - Sheet1.csv"
    
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return []
    
    fields = []
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig to handle BOM
            reader = csv.DictReader(f)
            for row in reader:
                fields.append({
                    'name': row.get('Name', '').strip(),
                    'field_id': row.get('ID', '').strip(),
                    'primary_document': row.get('Primary document', '').strip(),
                    'secondary_documents': row.get('Secondary documents', '').strip(),
                    'notes': row.get('Notes', '').strip() if 'Notes' in row else '',
                    'required_disclosure': row.get('required_disclosure', 'no').strip().lower(),
                })
    except Exception as e:
        logger.error(f"Error loading CSV from {csv_path}: {e}")
        return []
    
    logger.info(f"Loaded {len(fields)} field mappings from {csv_path.name}")
    return fields


def get_field_by_id(field_id: str, csv_path: Optional[Path] = None) -> Optional[Dict[str, str]]:
    """Get a specific field by its ID.
    
    Args:
        field_id: Encompass field ID to search for
        csv_path: Optional path to CSV file
        
    Returns:
        Field dictionary if found, None otherwise
    """
    fields = load_field_mappings(csv_path)
    for field in fields:
        if field['field_id'] == field_id:
            return field
    return None


def get_field_by_name(field_name: str, csv_path: Optional[Path] = None) -> Optional[Dict[str, str]]:
    """Get a specific field by its name.
    
    Args:
        field_name: Field name to search for
        csv_path: Optional path to CSV file
        
    Returns:
        Field dictionary if found, None otherwise
    """
    fields = load_field_mappings(csv_path)
    for field in fields:
        if field['name'].lower() == field_name.lower():
            return field
    return None


def get_fields_for_document_type(document_type: str, csv_path: Optional[Path] = None) -> List[Dict[str, str]]:
    """Get all fields associated with a specific document type.
    
    Args:
        document_type: Document type name (e.g., "ID", "Title Report")
        csv_path: Optional path to CSV file
        
    Returns:
        List of field dictionaries where document_type appears in primary or secondary
    """
    fields = load_field_mappings(csv_path)
    doc_type_lower = document_type.lower().strip()
    
    matching_fields = []
    for field in fields:
        primary = field['primary_document'].lower().strip()
        secondary = field['secondary_documents'].lower().strip()
        
        # Check if document type appears in primary or secondary
        if doc_type_lower in primary or doc_type_lower in secondary:
            matching_fields.append(field)
    
    return matching_fields

