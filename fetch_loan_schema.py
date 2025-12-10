#!/usr/bin/env python3
"""
Script to fetch Encompass loan schema and analyze field mappings.

This script:
1. Fetches the loan schema from Encompass API v3
2. Saves it to a file
3. Optionally analyzes which fields from test data are available in schema
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
load_dotenv()

# Configuration
ENCOMPASS_API_BASE_URL = os.getenv('ENCOMPASS_API_BASE_URL')
ENCOMPASS_ACCESS_TOKEN = os.getenv('ENCOMPASS_ACCESS_TOKEN')  # Optional - will generate if not provided
ENCOMPASS_INSTANCE_ID = os.getenv('ENCOMPASS_INSTANCE_ID')

# Output files
SCHEMA_OUTPUT_FILE = 'encompass_loan_schema.json'
FIELD_MAPPING_OUTPUT = 'field_mapping_analysis.json'
TEST_DATA_FILE = 'agents/disclosure/test_loan_data_happy_path_simple.json'


def fetch_loan_schema():
    """Fetch the loan schema from Encompass API."""
    # Get access token (either from env or generate via OAuth2)
    access_token = ENCOMPASS_ACCESS_TOKEN
    
    if not access_token:
        print("No ENCOMPASS_ACCESS_TOKEN found - generating via OAuth2...")
        try:
            from packages.shared.auth import get_access_token
            access_token = get_access_token()
            print(f"✓ Generated OAuth2 token: {access_token[:20]}...")
        except Exception as e:
            print(f"✗ Failed to generate token: {e}")
            return None
    else:
        print(f"Using provided token: {access_token[:20]}...")
    
    url = f"{ENCOMPASS_API_BASE_URL}/encompass/v3/schemas/loan"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    
    # Add instance ID if provided
    if ENCOMPASS_INSTANCE_ID:
        headers['Encompass-Instance-Id'] = ENCOMPASS_INSTANCE_ID
    
    print(f"Fetching loan schema from: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        schema = response.json()
        print(f"✓ Successfully fetched loan schema")
        print(f"  Schema contains {len(schema.get('properties', {}))} top-level properties")
        
        return schema
        
    except requests.exceptions.HTTPError as e:
        print(f"✗ HTTP Error: {e}")
        print(f"  Response: {e.response.text if e.response else 'No response'}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"✗ Request Error: {e}")
        return None
    except Exception as e:
        print(f"✗ Unexpected Error: {e}")
        return None


def save_schema(schema, filename=SCHEMA_OUTPUT_FILE):
    """Save schema to a JSON file."""
    with open(filename, 'w') as f:
        json.dump(schema, f, indent=2)
    print(f"✓ Schema saved to: {filename}")


def load_test_data():
    """Load the test data file."""
    try:
        with open(TEST_DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"✗ Test data file not found: {TEST_DATA_FILE}")
        return None


def extract_field_ids_from_test_data(test_data):
    """Extract all field IDs from test data."""
    field_ids = {}
    
    for category, fields in test_data.items():
        for field_id, field_info in fields.items():
            field_ids[field_id] = {
                'category': category,
                'field_name': field_info.get('field_name'),
                'expected_value': field_info.get('value'),
                'rule': field_info.get('rule')
            }
    
    return field_ids


def find_field_in_schema(field_id, schema):
    """
    Search for a field ID in the schema.
    Returns the field definition if found.
    """
    properties = schema.get('properties', {})
    
    # Direct property lookup
    if field_id in properties:
        return {
            'location': 'root',
            'path': field_id,
            'definition': properties[field_id]
        }
    
    # Search in customFields
    if 'customFields' in properties:
        custom_props = properties['customFields'].get('items', {}).get('properties', {})
        if 'fieldName' in custom_props:
            return {
                'location': 'customFields',
                'path': f'customFields[].fieldName={field_id}',
                'definition': custom_props
            }
    
    # Search in applications array (for borrower fields)
    if 'applications' in properties:
        app_items = properties['applications'].get('items', {}).get('properties', {})
        
        # Check in borrower
        if 'borrower' in app_items:
            borrower_props = app_items['borrower'].get('properties', {})
            if field_id in borrower_props:
                return {
                    'location': 'applications[].borrower',
                    'path': f'applications[].borrower.{field_id}',
                    'definition': borrower_props[field_id]
                }
        
        # Check in coborrower
        if 'coborrower' in app_items:
            coborrower_props = app_items['coborrower'].get('properties', {})
            if field_id in coborrower_props:
                return {
                    'location': 'applications[].coborrower',
                    'path': f'applications[].coborrower.{field_id}',
                    'definition': coborrower_props[field_id]
                }
    
    # Recursive search in nested objects (simplified)
    def search_nested(obj, path=''):
        if not isinstance(obj, dict):
            return None
        
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key
            
            if key == field_id:
                return {
                    'location': 'nested',
                    'path': current_path,
                    'definition': value
                }
            
            if isinstance(value, dict):
                result = search_nested(value, current_path)
                if result:
                    return result
        
        return None
    
    return search_nested(properties)


def analyze_field_mappings(test_data, schema):
    """Analyze which test data fields exist in the schema."""
    field_ids = extract_field_ids_from_test_data(test_data)
    
    analysis = {
        'found': [],
        'not_found': [],
        'summary': {
            'total_fields': len(field_ids),
            'found_count': 0,
            'not_found_count': 0
        }
    }
    
    print("\n" + "="*80)
    print("FIELD MAPPING ANALYSIS")
    print("="*80)
    
    for field_id, field_info in field_ids.items():
        schema_location = find_field_in_schema(field_id, schema)
        
        if schema_location:
            field_data = {
                'field_id': field_id,
                'field_name': field_info['field_name'],
                'category': field_info['category'],
                'expected_value': field_info['expected_value'],
                'schema_location': schema_location['location'],
                'schema_path': schema_location['path'],
                'schema_definition': schema_location['definition']
            }
            analysis['found'].append(field_data)
            analysis['summary']['found_count'] += 1
            
            print(f"✓ {field_id} ({field_info['field_name']})")
            print(f"  Location: {schema_location['path']}")
        else:
            field_data = {
                'field_id': field_id,
                'field_name': field_info['field_name'],
                'category': field_info['category'],
                'expected_value': field_info['expected_value'],
                'note': 'Not found in schema - may be custom field or alternative ID'
            }
            analysis['not_found'].append(field_data)
            analysis['summary']['not_found_count'] += 1
            
            print(f"✗ {field_id} ({field_info['field_name']})")
            print(f"  Status: NOT FOUND IN SCHEMA")
    
    print("\n" + "="*80)
    print(f"SUMMARY: {analysis['summary']['found_count']} found, "
          f"{analysis['summary']['not_found_count']} not found")
    print("="*80 + "\n")
    
    return analysis


def main():
    """Main execution function."""
    print("="*80)
    print("ENCOMPASS LOAN SCHEMA FETCHER")
    print("="*80 + "\n")
    
    # Note: Access token will be generated automatically if not provided
    if ENCOMPASS_ACCESS_TOKEN:
        print("✓ Using ENCOMPASS_ACCESS_TOKEN from .env")
    else:
        print("ℹ No ENCOMPASS_ACCESS_TOKEN - will generate via OAuth2 client credentials")
    
    # Step 1: Fetch schema
    schema = fetch_loan_schema()
    
    if not schema:
        print("\n✗ Failed to fetch schema. Exiting.")
        return
    
    # Step 2: Save schema
    save_schema(schema)
    
    # Step 3: Load test data
    print("\nLoading test data...")
    test_data = load_test_data()
    
    if not test_data:
        print("\n⚠ Could not load test data. Skipping field mapping analysis.")
        return
    
    # Step 4: Analyze field mappings
    analysis = analyze_field_mappings(test_data, schema)
    
    # Step 5: Save analysis
    with open(FIELD_MAPPING_OUTPUT, 'w') as f:
        json.dump(analysis, f, indent=2)
    print(f"✓ Field mapping analysis saved to: {FIELD_MAPPING_OUTPUT}")
    
    print("\n" + "="*80)
    print("COMPLETE")
    print("="*80)
    print(f"\nGenerated files:")
    print(f"  1. {SCHEMA_OUTPUT_FILE} - Full Encompass loan schema")
    print(f"  2. {FIELD_MAPPING_OUTPUT} - Field mapping analysis")


if __name__ == "__main__":
    main()

