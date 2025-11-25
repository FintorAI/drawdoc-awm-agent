"""
Load SOP rules from preprocessed JSON file.
"""

import json
from pathlib import Path
from typing import Dict, Any


def load_sop_rules() -> Dict[str, Any]:
    """
    Load SOP rules from preprocessed JSON file.
    
    Returns:
        Dictionary containing page-indexed SOP rules and sections
    """
    sop_path = Path(__file__).parent / "sop_rules.json"
    
    if not sop_path.exists():
        print(f"⚠️  SOP rules file not found at {sop_path}")
        print("Run: python scripts/preprocess_sop.py")
        return {
            "page_indexed_rules": {},
            "sop_sections": {},
            "metadata": {}
        }
    
    with open(sop_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# Load SOP rules at module import
SOP_RULES = load_sop_rules()


if __name__ == "__main__":
    """Test loading SOP rules."""
    print(f"Loaded SOP rules:")
    print(f"  - Pages indexed: {len(SOP_RULES.get('page_indexed_rules', {}))}")
    print(f"  - Sections: {len(SOP_RULES.get('sop_sections', {}))}")
    
    # Show sample page
    if "20" in SOP_RULES.get("page_indexed_rules", {}):
        print(f"\nSample - Page 20:")
        page_20 = SOP_RULES["page_indexed_rules"]["20"]
        print(f"  - Fields: {len(page_20.get('fields', []))}")
        print(f"  - Rules: {len(page_20.get('rules', []))}")

