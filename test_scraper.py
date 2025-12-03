
import sys
import os
from dotenv import load_dotenv

# Add src to the system path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables (needed if you plan to use them in the scraper)
load_dotenv()

from src.data_scraper import get_trending_topic

# --- Test 1: Try Global Trends ---
print("--- TEST 1: Attempting to fetch Global Trends (geo='') ---")
keyword_global, context_global = get_trending_topic(region='')

if keyword_global:
    print(f"\nSUCCESS - Global Topic: {keyword_global} with context: {context_global}")
else:
    print("\nFAILED - Global test failed.")
    
print("\n" + "="*30 + "\n")

# --- Test 2: Try US Trends ---
print("--- TEST 2: Attempting to fetch US Trends (geo='US') ---")
keyword_us, context_us = get_trending_topic(region='US')

if keyword_us:
    print(f"\nSUCCESS - US Topic: {keyword_us} with context: {context_us}")
else:
    print("\nFAILED - US test failed.")
