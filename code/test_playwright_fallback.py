#!/usr/bin/env python3
"""
Test script for Playwright Facebook fallback functionality
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from playwright.sync_api import sync_playwright
    print("✅ Playwright imported successfully")
    
    # Test basic Playwright functionality
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.google.com")
        title = page.title()
        print(f"✅ Playwright test successful - page title: {title}")
        browser.close()
        
except ImportError as e:
    print(f"❌ Playwright import failed: {e}")
    print("Install with: pip install playwright")
    print("Then install browsers: python -m playwright install")
except Exception as e:
    print(f"❌ Playwright test failed: {e}")

print("\n🎯 To test the full application:")
print("python video_translation_app.py")
print("\n🌐 The Playwright fallback button will appear in the 'Post na social media' tab")
print("   when Playwright is available.")
