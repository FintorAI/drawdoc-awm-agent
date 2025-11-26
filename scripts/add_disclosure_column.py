"""
Script to add 'required_disclosure' column to DrawingDoc Verifications CSV.

This column will be 'yes' if the field's document types contain 'disclosure',
otherwise 'no'. This helps the disclosure verification agent filter relevant fields.
"""

import csv
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Path to the CSV file
CSV_PATH = project_root / "packages" / "data" / "DrawingDoc Verifications - Sheet1.csv"
BACKUP_PATH = CSV_PATH.with_suffix('.csv.backup')

def add_disclosure_column():
    """Add required_disclosure column to the CSV."""
    
    print(f"Reading CSV from: {CSV_PATH}")
    
    # Create backup
    if CSV_PATH.exists():
        import shutil
        shutil.copy(CSV_PATH, BACKUP_PATH)
        print(f"✓ Backup created: {BACKUP_PATH}")
    
    # Read existing data
    rows = []
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            rows.append(row)
    
    print(f"✓ Read {len(rows)} rows")
    
    # Find the column index for Primary document and Secondary documents
    header = rows[0]
    try:
        primary_doc_idx = header.index('Primary document')
        secondary_doc_idx = header.index('Secondary documents')
        print(f"✓ Found Primary document at column {primary_doc_idx}")
        print(f"✓ Found Secondary documents at column {secondary_doc_idx}")
    except ValueError as e:
        print(f"✗ Error: Could not find required columns: {e}")
        return
    
    # Check if required_disclosure column already exists
    if 'required_disclosure' in header:
        print("⚠ Column 'required_disclosure' already exists. Will update values.")
        disclosure_idx = header.index('required_disclosure')
    else:
        # Add new column header
        header.append('required_disclosure')
        disclosure_idx = len(header) - 1
        print(f"✓ Added 'required_disclosure' column at index {disclosure_idx}")
    
    # Process each row
    disclosure_count = 0
    non_disclosure_count = 0
    
    for i, row in enumerate(rows[1:], start=1):  # Skip header
        # Ensure row has enough columns
        while len(row) < len(header):
            row.append('')
        
        # Get primary and secondary document values
        primary_doc = row[primary_doc_idx].lower() if primary_doc_idx < len(row) else ''
        secondary_doc = row[secondary_doc_idx].lower() if secondary_doc_idx < len(row) else ''
        
        # Check if 'disclosure' appears in either column
        has_disclosure = 'disclosure' in primary_doc or 'disclosure' in secondary_doc
        
        # Set the value
        row[disclosure_idx] = 'yes' if has_disclosure else 'no'
        
        if has_disclosure:
            disclosure_count += 1
        else:
            non_disclosure_count += 1
    
    print(f"\n✓ Processed {len(rows) - 1} data rows:")
    print(f"  - {disclosure_count} fields marked as disclosure-required")
    print(f"  - {non_disclosure_count} fields marked as non-disclosure")
    
    # Write back to CSV
    with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    
    print(f"\n✓ Updated CSV saved to: {CSV_PATH}")
    print(f"✓ Backup available at: {BACKUP_PATH}")
    
    # Show some examples
    print("\nExamples of disclosure-required fields:")
    count = 0
    for row in rows[1:]:
        if count >= 5:
            break
        if row[disclosure_idx] == 'yes':
            name = row[0] if len(row) > 0 else ''
            field_id = row[1] if len(row) > 1 else ''
            primary = row[primary_doc_idx] if primary_doc_idx < len(row) else ''
            print(f"  - {name} ({field_id}): {primary}")
            count += 1

if __name__ == "__main__":
    print("="*80)
    print("Adding 'required_disclosure' column to CSV")
    print("="*80)
    add_disclosure_column()
    print("\n" + "="*80)
    print("Done!")
    print("="*80)

