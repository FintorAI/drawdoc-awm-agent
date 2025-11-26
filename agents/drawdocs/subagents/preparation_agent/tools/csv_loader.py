"""CSV Loader - Dynamic loader for DrawingDoc Verifications.csv

This module provides a centralized way to load and access all data from the
DrawingDoc Verifications.csv file. It serves as the single source of truth for:
- Document types and their associated fields
- Field-to-document mappings
- Preferred document types for field extraction
- Field names and IDs
"""

from pathlib import Path
from typing import Dict, List, Optional, Set
import csv
import logging

logger = logging.getLogger(__name__)


class CSVLoader:
    """Loads and caches data from DrawingDoc Verifications.csv"""
    
    def __init__(self, csv_path: Optional[Path] = None):
        """Initialize the CSV loader.
        
        Args:
            csv_path: Path to the CSV file. If None, looks for it in the parent directory.
        """
        if csv_path is None:
            csv_path = Path(__file__).parent.parent / "DrawingDoc Verifications.csv"
        
        self.csv_path = csv_path
        self._data: Optional[List[Dict[str, str]]] = None
        self._field_to_docs: Optional[Dict[str, List[str]]] = None
        self._doc_to_fields: Optional[Dict[str, List[Dict[str, str]]]] = None
        self._document_types: Optional[List[str]] = None
        
    def _load_csv(self) -> List[Dict[str, str]]:
        """Load and parse the CSV file.
        
        Returns:
            List of dictionaries representing CSV rows
        """
        if self._data is not None:
            return self._data
        
        if not self.csv_path.exists():
            logger.warning(f"CSV file not found: {self.csv_path}")
            return []
        
        data = []
        try:
            # Handle BOM (Byte Order Mark) if present
            with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Clean up the row data
                    cleaned_row = {
                        'name': row.get('Name', '').strip(),
                        'id': row.get('ID', '').strip(),
                        'primary_document': row.get('Primary document', '').strip(),
                        'secondary_documents': row.get('Secondary documents', '').strip(),
                        'notes': row.get('Notes', '').strip(),
                    }
                    
                    # Only include rows with at least a field name or ID
                    if cleaned_row['name'] or cleaned_row['id']:
                        data.append(cleaned_row)
                        
        except Exception as e:
            logger.error(f"Error loading CSV file: {e}")
            return []
        
        self._data = data
        logger.info(f"Loaded {len(data)} rows from CSV")
        return data
    
    def get_all_fields(self) -> List[Dict[str, str]]:
        """Get all fields from the CSV.
        
        Returns:
            List of field dictionaries with keys: name, id, primary_document, secondary_documents, notes
        """
        return self._load_csv()
    
    def get_field_by_id(self, field_id: str) -> Optional[Dict[str, str]]:
        """Get a field by its ID.
        
        Args:
            field_id: The Encompass field ID
            
        Returns:
            Field dictionary or None if not found
        """
        for field in self._load_csv():
            if field['id'] == field_id:
                return field
        return None
    
    def get_field_by_name(self, field_name: str) -> Optional[Dict[str, str]]:
        """Get a field by its name.
        
        Args:
            field_name: The field name
            
        Returns:
            Field dictionary or None if not found
        """
        for field in self._load_csv():
            if field['name'].lower() == field_name.lower():
                return field
        return None
    
    def get_document_types(self) -> List[str]:
        """Get all unique document types from the CSV.
        
        Returns:
            List of document type names
        """
        if self._document_types is not None:
            return self._document_types
        
        documents: Set[str] = set()
        
        for row in self._load_csv():
            # Primary document
            primary = row.get('primary_document', '').strip()
            if primary:
                documents.add(primary)
            
            # Secondary documents (split by semicolon and comma)
            secondary = row.get('secondary_documents', '').strip()
            if secondary:
                for doc in secondary.replace(';', ',').split(','):
                    doc = doc.strip()
                    if doc and doc not in ['', 'N/A']:
                        documents.add(doc)
        
        # Filter out non-document types (system references, etc.)
        exclude_prefixes = [
            'Encompass Tools',
            'File Contacts',
            'Mavent report',
            'SOP requirement',
            'Fee classification',
            'Documents tab',
            'Lender location',
        ]
        
        filtered = []
        for doc in sorted(documents):
            if not any(doc.startswith(prefix) for prefix in exclude_prefixes):
                filtered.append(doc)
        
        self._document_types = filtered
        return filtered
    
    def get_fields_for_document(self, document_type: str) -> List[Dict[str, str]]:
        """Get all fields that should be extracted from a specific document type.
        
        Args:
            document_type: The document type (e.g., "Final 1003", "W-2")
            
        Returns:
            List of field dictionaries with an additional 'is_primary' boolean
        """
        if self._doc_to_fields is None:
            self._build_doc_to_fields_index()
        
        # Try exact match first
        if document_type in self._doc_to_fields:
            return self._doc_to_fields[document_type]
        
        # Try case-insensitive match
        doc_lower = document_type.lower()
        for doc, fields in self._doc_to_fields.items():
            if doc.lower() == doc_lower:
                return fields
        
        # Try partial match
        for doc, fields in self._doc_to_fields.items():
            if doc_lower in doc.lower() or doc.lower() in doc_lower:
                return fields
        
        return []
    
    def _build_doc_to_fields_index(self):
        """Build an index mapping document types to their fields."""
        self._doc_to_fields: Dict[str, List[Dict[str, str]]] = {}
        
        for row in self._load_csv():
            field_info = {
                'name': row['name'],
                'id': row['id'],
                'notes': row['notes'],
                'is_primary': True,
            }
            
            # Add to primary document
            primary = row.get('primary_document', '').strip()
            if primary:
                if primary not in self._doc_to_fields:
                    self._doc_to_fields[primary] = []
                self._doc_to_fields[primary].append(field_info.copy())
            
            # Add to secondary documents
            secondary = row.get('secondary_documents', '').strip()
            if secondary:
                for doc in secondary.replace(';', ',').split(','):
                    doc = doc.strip()
                    if doc and doc not in ['', 'N/A']:
                        if doc not in self._doc_to_fields:
                            self._doc_to_fields[doc] = []
                        field_info_secondary = field_info.copy()
                        field_info_secondary['is_primary'] = False
                        self._doc_to_fields[doc].append(field_info_secondary)
    
    def get_field_to_documents_mapping(self) -> Dict[str, List[str]]:
        """Get mapping of field IDs to their preferred document types.
        
        Returns:
            Dictionary mapping field IDs to lists of preferred document types
        """
        if self._field_to_docs is not None:
            return self._field_to_docs
        
        field_to_docs: Dict[str, List[str]] = {}
        
        for row in self._load_csv():
            field_id = row.get('id', '').strip()
            primary_doc = row.get('primary_document', '').strip()
            
            if field_id and primary_doc:
                # Normalize document name
                doc_normalized = self._normalize_document_type(primary_doc)
                
                if doc_normalized:
                    if field_id not in field_to_docs:
                        field_to_docs[field_id] = []
                    
                    if doc_normalized not in field_to_docs[field_id]:
                        field_to_docs[field_id].append(doc_normalized)
        
        self._field_to_docs = field_to_docs
        return field_to_docs
    
    def _normalize_document_type(self, doc_name: str) -> Optional[str]:
        """Normalize document type names to standard types.
        
        Args:
            doc_name: Raw document name from CSV
            
        Returns:
            Normalized document type name or None
        """
        doc_lower = doc_name.lower()
        
        # ID documents
        if 'id' in doc_lower and ('driver' in doc_lower or 'license' in doc_lower):
            return "ID"
        if doc_lower in ['id', 'driver\'s license', 'driver license', 'state id']:
            return "ID"
        
        # W-2 documents
        if 'w-2' in doc_lower or 'w2' in doc_lower or doc_lower == 'w-2 form':
            return "W-2"
        
        # 1003 forms
        if '1003' in doc_lower:
            if 'final' in doc_lower:
                return "Final 1003"
            elif 'initial' in doc_lower:
                return "Initial 1003"
            else:
                return "Final 1003"  # Default to Final 1003
        
        # Title documents
        if 'title' in doc_lower and 'report' in doc_lower:
            if 'prelim' in doc_lower:
                return "Title Report"
            return "Title Report"
        
        # Appraisal documents
        if 'appraisal' in doc_lower:
            if 'report' in doc_lower:
                return "Appraisal Report"
            return "Appraisal Report"
        
        # Loan Estimate
        if 'loan estimate' in doc_lower or 'le' in doc_lower:
            if 'last' in doc_lower:
                return "Last LE"
            return "Last LE"
        
        # Closing Disclosure
        if 'closing disclosure' in doc_lower or 'cd' in doc_lower:
            if 'initial' in doc_lower:
                return "Initial CD"
            elif 'coc' in doc_lower or 'change' in doc_lower:
                return "COC CD"
            elif 'final' in doc_lower:
                return "Final CD"
            return "Closing Disclosure"
        
        # Purchase Agreement
        if 'purchase' in doc_lower and ('agreement' in doc_lower or 'contract' in doc_lower):
            return "Purchase Agreement"
        
        # Trust Document
        if 'trust' in doc_lower:
            return "Trust Document"
        
        # Aggregate Escrow
        if 'aggregate' in doc_lower and 'escrow' in doc_lower:
            return "Aggregate Escrow Account Form"
        
        # 2015 Itemization
        if '2015' in doc_lower and 'itemization' in doc_lower:
            return "2015 Itemization form"
        
        # HOI Policy
        if 'hoi' in doc_lower or ('hazard' in doc_lower and 'insurance' in doc_lower):
            if 'policy' in doc_lower or 'evidence' in doc_lower:
                return "HOI Policy"
        
        # Mortgage Insurance
        if 'mortgage insurance' in doc_lower:
            if 'certificate' in doc_lower:
                return "Mortgage Insurance Certificate"
            return "Mortgage Insurance details"
        
        # FHA Case
        if 'fha' in doc_lower and 'case' in doc_lower:
            return "FHA Case assignment document"
        
        # Escrow Wire
        if 'escrow' in doc_lower and 'wire' in doc_lower:
            return "Escrow wire instruction"
        
        # Credit Report
        if 'credit' in doc_lower and 'report' in doc_lower:
            return "Credit report"
        
        # Loan file
        if 'loan file' in doc_lower:
            return "Loan file"
        
        # Return original if no normalization found
        return doc_name if doc_name else None


# Global instance
_csv_loader = None

def get_csv_loader() -> CSVLoader:
    """Get the global CSV loader instance."""
    global _csv_loader
    if _csv_loader is None:
        _csv_loader = CSVLoader()
    return _csv_loader


