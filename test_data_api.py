"""Quick test script for Data API service endpoints."""
import sys
import urllib.request
import json
from typing import Any, Dict

def test_endpoint(url: str, description: str) -> None:
    """Test a single API endpoint."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            status = response.getcode()
            content_type = response.headers.get('Content-Type', '')
            
            print(f"[OK] Status: {status}")
            print(f"   Content-Type: {content_type}")
            
            if 'json' in content_type:
                data = json.loads(response.read().decode('utf-8'))
                print(f"   Response:")
                print(f"   {json.dumps(data, indent=2)}")
            else:
                print(f"   Response (first 200 chars):")
                print(f"   {response.read(200).decode('utf-8', errors='ignore')}")
                
    except urllib.error.HTTPError as e:
        print(f"[ERROR] HTTP Error {e.code}: {e.reason}")
        print(f"   {e.read().decode('utf-8', errors='ignore')}")
    except urllib.error.URLError as e:
        print(f"[ERROR] URL Error: {e.reason}")
    except Exception as e:
        print(f"[ERROR] Error: {e}")


def main():
    """Run all API tests."""
    print("=" * 60)
    print("Elmetron Data API Service - Test Suite")
    print("=" * 60)
    
    base_url = "http://localhost:8050"
    
    # Test health endpoint
    test_endpoint(f"{base_url}/health", "Health Check")
    
    # Test live status
    test_endpoint(f"{base_url}/api/live/status", "Live Capture Status")
    
    # Test sessions list
    test_endpoint(f"{base_url}/api/sessions?limit=5", "Recent Sessions (limit=5)")
    
    # Test instruments
    test_endpoint(f"{base_url}/api/instruments", "Instruments List")
    
    # Test database stats
    test_endpoint(f"{base_url}/api/stats", "Database Statistics")
    
    print("\n" + "=" * 60)
    print("Test suite complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. If all tests pass -> Data API is working!")
    print("2. Try accessing specific session:")
    print(f"   {base_url}/api/sessions/1")
    print("3. Try getting measurements:")
    print(f"   {base_url}/api/sessions/1/measurements")
    print("4. Try exporting data:")
    print(f"   {base_url}/api/sessions/1/export?format=csv")
    print("=" * 60)


if __name__ == "__main__":
    main()
