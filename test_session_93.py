"""Test script to reproduce session evaluation 500 error."""
import sys
import traceback
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from elmetron.reporting.session import build_session_evaluation
from elmetron.storage.database import Database

# Test with session 93 that's failing
session_id = 93
anchor = 'start'
db_path = Path('data/elmetron.sqlite')

print(f"Testing session evaluation for session_id={session_id}, anchor={anchor}")
print(f"Database: {db_path}")
print(f"Database exists: {db_path.exists()}")
print()

try:
    # Just pass the database path directly
    payload = build_session_evaluation(db_path, session_id, anchor=anchor)
    
    if payload is None:
        print("[X] Session not found (returned None)")
    else:
        print("[OK] Session evaluation succeeded!")
        print(f"  Series count: {len(payload.get('series', []))}")
        print(f"  Markers count: {len(payload.get('markers', []))}")
        
        # Now test JSON serialization (like the server does)
        import json
        print()
        print("Testing JSON serialization...")
        try:
            body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            print(f"[OK] JSON serialization succeeded! ({len(body)} bytes)")
        except Exception as json_exc:
            print(f"[ERROR] JSON serialization failed: {json_exc}")
            print(f"  Type: {type(json_exc).__name__}")
            traceback.print_exc()
            
except Exception as exc:
    print(f"[ERROR] {exc}")
    print(f"  Type: {type(exc).__name__}")
    print()
    print("Full traceback:")
    traceback.print_exc()
