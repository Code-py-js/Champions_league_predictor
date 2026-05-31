"""Test API with different query parameters and methods."""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('RAPIDAPI_KEY')

headers = {
    "x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com",
    "x-rapidapi-key": api_key,
}

base_url = "https://free-api-live-football-data.p.rapidapi.com"

# Try with query parameters
test_cases = [
    ("/leagues", {}),
    ("/leagues", {"id": "39"}),
    ("/fixtures", {"league_id": "39", "season": "2023"}),
    ("/matches", {}),
    ("/live", {}),
]

for endpoint, params in test_cases:
    try:
        url = f"{base_url}{endpoint}"
        print(f"\n🔧 GET {endpoint}")
        if params:
            print(f"   Params: {params}")
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"   Status: {response.status_code}")
        
        data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        
        if isinstance(data, dict):
            keys = list(data.keys())[:5]
            print(f"   Keys: {keys}")
            print(f"   Data: {str(data)[:150]}")
        else:
            print(f"   Response: {str(data)[:150]}")
            
    except Exception as e:
        print(f"   Error: {e}")

# Try some common football API endpoints
print("\n\n" + "="*60)
print("Trying common football API endpoint patterns...")

common_endpoints = [
    "/competitions",
    "/championships",
    "/standings",
    "/events",
    "/predictions",
    "/odds",
]

for endpoint in common_endpoints:
    try:
        url = f"{base_url}{endpoint}"
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 404:
            print(f"✓ {endpoint}: {response.status_code}")
            data = response.json()
            print(f"   {list(data.keys())[:3] if isinstance(data, dict) else 'Array response'}")
        else:
            msg = response.json().get('message', '')
            if "does not exist" not in msg:
                print(f"  {endpoint}: {response.status_code} - {msg[:50]}")
    except:
        pass

print("\nNote: API documentation is available at https://rapidapi.com/api-sports/api/api-football")
