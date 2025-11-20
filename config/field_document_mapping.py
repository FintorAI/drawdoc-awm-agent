"""
Parse and load the DrawingDoc Verifications CSV into structured field mapping.
"""

import csv
from pathlib import Path
from typing import Dict, List, Any


def parse_csv_field_mapping(csv_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Parse the DrawingDoc Verifications CSV and create a structured field mapping.
    
    Args:
        csv_path: Path to the DrawingDoc Verifications CSV file
        
    Returns:
        Dictionary mapping field IDs to field information including documents and rules
    """
    field_mapping = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            field_name = row.get('Name', '').strip()
            field_id = row.get('ID', '').strip()
            primary_doc = row.get('Primary document', '').strip()
            secondary_docs = row.get('Secondary documents', '').strip()
            notes = row.get('Notes', '').strip()
            sop_pages = row.get('SOP Pages', '').strip()
            
            # Skip rows without field ID
            if not field_id:
                continue
            
            # Parse secondary documents
            secondary_doc_list = []
            if secondary_docs:
                secondary_doc_list = [doc.strip() for doc in secondary_docs.split(';') if doc.strip()]
            
            # Parse SOP pages
            sop_page_list = []
            if sop_pages:
                sop_page_list = [page.strip() for page in sop_pages.split(',') if page.strip()]
            
            # Extract validation rules from notes
            validation_rules = []
            if notes:
                # Split by semicolon or period to get individual rules
                rules = [rule.strip() for rule in notes.split(';') if rule.strip()]
                validation_rules = rules
            
            # Create field mapping entry
            field_mapping[field_id] = {
                "field_id": field_id,
                "field_name": field_name,
                "primary_document": primary_doc,
                "secondary_documents": secondary_doc_list,
                "sop_pages": sop_page_list,
                "notes": notes,
                "validation_rules": validation_rules
            }
    
    return field_mapping


def load_field_mapping() -> Dict[str, Dict[str, Any]]:
    """
    Load the field mapping from the CSV file.
    
    Returns:
        Dictionary mapping field IDs to field information
    """
    base_dir = Path(__file__).parent.parent
    csv_path = base_dir / "DrawingDoc Verifications - Sheet1.csv"
    
    return parse_csv_field_mapping(csv_path)


# Load the field mapping at module import
FIELD_MAPPING = load_field_mapping()


# Also create a reverse lookup by field name
FIELD_NAME_TO_ID = {
    mapping["field_name"]: field_id 
    for field_id, mapping in FIELD_MAPPING.items()
    if mapping["field_name"]
}


if __name__ == "__main__":
    """Test the field mapping parser."""
    import json
    
    print(f"Loaded {len(FIELD_MAPPING)} field mappings")
    
    # Print sample mappings
    print("\nSample field mappings:")
    sample_fields = ["4000", "4002", "4004", "1402", "65"]
    
    for field_id in sample_fields:
        if field_id in FIELD_MAPPING:
            print(f"\nField {field_id}:")
            print(json.dumps(FIELD_MAPPING[field_id], indent=2))
    
    print(f"\nTotal field names mapped: {len(FIELD_NAME_TO_ID)}")

