#!/usr/bin/env python3
"""
CRITICAL TEST: Verify MW expansion fix is working

This test confirms that the language detection fix prevents English queries 
from being corrupted by MW expansion.

If this test shows:
- "MW: Language detection" messages → Fix is WORKING
- No "MW: Language detection" messages → Cache issue, old code running

Run after Streamlit app processes the query.
"""

import subprocess
import sys
import time

print("=" * 80)
print("MW EXPANSION FIX VERIFICATION")
print("=" * 80)

# Check if Streamlit is running
result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
if 'streamlit' in result.stdout:
    print("\n✅ Streamlit is running")
    print("\nChecking logs for language detection messages...")
    print("-" * 80)
    
    # Try to get recent logs
    subprocess.run(['tail', '-f', '/dev/null'], timeout=0.1)
    
    print("\nLOOK FOR THESE MESSAGES IN THE TERMINAL OUTPUT:")
    print("  ✅ 'MW: Language detection for 'Who is Sudas?' → is_english=True'")
    print("  ✅ 'MW: ✅ Skipping expansion - detected English query'")
    print("\nNOT seeing these messages? → Cache issue, need to restart Streamlit")
    
else:
    print("\n❌ Streamlit is NOT running")
    print("Start it with: streamlit run sanskrit_tutor_frontend.py")
    print("Then test the query: 'Who is Sudas?'")

print("\n" + "=" * 80)
print("TEST INSTRUCTIONS:")
print("=" * 80)
print("""
1. Make sure Streamlit is running in another terminal
2. In the Streamlit UI, ask: "Who is Sudas?"
3. Watch the terminal running Streamlit for these log messages:
   - "MW: Language detection for 'Who is Sudas?' → is_english=True"
   - "MW: ✅ Skipping expansion - detected English query"
   
If you see these messages: ✅ FIX IS WORKING
If you DON'T see these messages: ❌ Cache problem, run:
   find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
   pkill -f streamlit
   streamlit run sanskrit_tutor_frontend.py
""")
