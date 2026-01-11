#!/usr/bin/env python3
"""Test script to verify all imports work correctly."""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

errors = []

try:
    from app.api.routes.documents import router
    print("✅ SUCCESS: documents.py imports correctly")
    print("✅ Optional is imported")
except Exception as e:
    errors.append(f"documents.py: {e}")
    print(f"❌ ERROR in documents.py: {e}")

try:
    from app.api.routes import business, documents, chat, conversations, auth
    print("✅ SUCCESS: All route modules import correctly")
except Exception as e:
    errors.append(f"routes/__init__.py: {e}")
    print(f"❌ ERROR in routes: {e}")

try:
    from app.main import app
    print("✅ SUCCESS: main.py imports correctly")
except Exception as e:
    errors.append(f"main.py: {e}")
    print(f"❌ ERROR in main.py: {e}")

if errors:
    print(f"\n❌ Found {len(errors)} error(s):")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)
else:
    print("\n✅ ALL IMPORTS SUCCESSFUL!")
    sys.exit(0)
