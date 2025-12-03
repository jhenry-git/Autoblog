import datetime
import time
from pytrends.request import TrendReq
import pandas as pd

# Increase the default connection timeout for better stability
TRENDS_TIMEOUT = 10

# Use a seed list of general high-level topics to find breakout trends within them.
# This method is often more stable than the real-time trending feed.
SEED_KEYWORDS = ['AI technology', 'software development', 'cloud computing', 'cybersecurity']

def get_trending_topic(region='', timeframe='today 3-m', category=0):
    """
    Connects to Google Trends, uses a seed list of keywords to find "Rising" related queries,
    and selects the top rising query as the topic. This avoids the unstable trending_searches endpoint.

    Args:
        region (str): Geographic location code (e.g., 'US', 'GB', '' for global).
        timeframe (str): Time range (e.g., 'today 12-m', 'today 3-m').
        category (int): Topic category ID (0 is all categories).

    Returns:
        tuple: (keyword, context) or (None, None) if no topic is selected.
    """
    print(f"--- 1. Sourcing data from Google Trends (Region: {region or 'Global'}) ---")
    
    # Initialize TrendReq with the extended timeout
    pytrends = TrendReq(hl='en-US', tz=360, timeout=(5, TRENDS_TIMEOUT))

    topic = None
    all_rising_queries = []

    # Iterate through the seed keywords to find rising trends within each category
    for seed in SEED_KEYWORDS:
        print(f"  -> Checking rising queries for seed topic: '{seed}'")
        try:
            # Build payload and fetch related queries
            pytrends.build_payload([seed], cat=category, timeframe=timeframe, geo=region)
            related_queries = pytrends.related_queries()
            
            # The related_queries result is a nested dictionary keyed by the input keyword
            if seed in related_queries and 'rising' in related_queries[seed]:
                rising_df = related_queries[seed]['rising']
                if not rising_df.empty:
                    # Append all rising queries found to the list
                    all_rising_queries.extend(rising_df['query'].tolist())
            
        except Exception as e:
            print(f"  -> Failed to fetch related queries for '{seed}': {e}")
            time.sleep(2) # Brief wait before trying the next seed

    if not all_rising_queries:
        print("Could not find any rising trending queries from the seed list.")
        return None, None
    
    # Select the first unique rising query found as the main topic
    unique_rising_queries = list(set(all_rising_queries))
    topic = unique_rising_queries[0]
    
    print(f"-> Selected Topic (Rising Trend): {topic}")

    # --- Fetch Related Queries for Context (for the chosen topic) ---
    context = []
    try:
        # Get context specifically for the chosen trending topic
        pytrends.build_payload([topic], cat=category, timeframe=timeframe, geo=region)
        related_queries = pytrends.related_queries()
        
        if topic in related_queries and 'top' in related_queries[topic]:
            top_queries = related_queries[topic]['top']
            # Use the top queries as context for the AI writer
            context = top_queries['query'].tolist()[:3]

    except Exception as e:
        print(f"Warning: Could not fetch secondary related queries for context. {e}")

    print(f"-> Related Context: {context}")
    return topic, context

if __name__ == '__main__':
    # Test function
    keyword, context = get_trending_topic(region='')
    if keyword:
        print(f"\nSuccessfully fetched topic: {keyword} with context: {context}")
