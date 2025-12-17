import os
import json
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path('.env'))

LOAN_ID = '59d7a711-70f4-4b12-a3b5-bbefb3ff7dbc'

# 1. Get OAuth token
api_base_url = os.getenv('ENCOMPASS_API_BASE_URL')
client_id = os.getenv('ENCOMPASS_CLIENT_ID')
client_secret = os.getenv('ENCOMPASS_CLIENT_SECRET')
instance_id = os.getenv('ENCOMPASS_INSTANCE_ID')
scope = os.getenv('ENCOMPASS_SCOPE', 'lp')

token_url = f'{api_base_url}/oauth2/v1/token'
token_data = {'grant_type': 'client_credentials', 'instance_id': instance_id, 'scope': scope}
resp = requests.post(token_url, data=token_data, auth=HTTPBasicAuth(client_id, client_secret), timeout=30)
token = resp.json()['access_token']

# 2. Fetch ENTIRE loan object (this is the key difference!)
loan_url = f'{api_base_url}/encompass/v3/loans/{LOAN_ID}'
resp = requests.get(loan_url, headers={'Authorization': f'Bearer {token}'}, timeout=60)
loan = resp.json()

# 3. Save to file
with open('loan_full_object.json', 'w') as f:
    json.dump(loan, f, indent=2)