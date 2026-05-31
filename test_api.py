"""Test API endpoints to debug the 404 error."""

import requests
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

api_key = os.getenv('RAPIDAPI_KEY')
print(f"API Key available: {'Yes' if api_key else 'No'}")
if api_key:
    print(f"   Key: {api_key[:20]}...")

headers = {
    "x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com",
    "x-rapidapi-key": api_key,
    "User-Agent": "Mozilla/5.0"
}

# Test different endpoints
endpoints = [
    "/leagues",
    "/fixtures",
    "/teams",
    "/",
]

base_url = "https://free-api-live-football-data.p.rapidapi.com"

for endpoint in endpoints:
    try:
        url = f"{base_url}{endpoint}"
        print(f"\n🔧 Testing: {url}")
        
        response = requests.get(url, headers=headers, timeout=10)
        print(f"   Status Code: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
        
        try:
            data = response.json()
            print(f"   Response type: {type(data)}")
            if isinstance(data, dict):
                print(f"   Keys: {list(data.keys())}")
            print(f"   Content: {str(data)[:300]}")
        except:
            print(f"   Raw response: {response.text[:300]}")
            
    except Exception as e:
        print(f"   Exception: {type(e).__name__}: {e}")

print("\n" + "="*60)
print("Endpoint Testing Complete")
