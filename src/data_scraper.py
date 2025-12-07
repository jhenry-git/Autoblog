import time
import random
from pytrends.request import TrendReq
import logging

# Configure logging
logger = logging.getLogger()

# Increase the default connection timeout for better stability
TRENDS_TIMEOUT = 10

# Use a seed list of general high-level topics to find breakout trends within them.
# This serves as a backup if no specific niche query is provided.
SEED_KEYWORDS = ['AI technology', 'software development', 'cloud computing', 'cybersecurity']

def get_trending_topic(query=None):
    """
    Attempts to fetch a trending topic from Google Trends.
    
    Args:
        query (str, optional): A specific keyword to search for (e.g., "Medical VA").
                               If None, searches for general tech trends using SEED_KEYWORDS.
    
    Returns:
        tuple: (topic_title, list_of_context_points) OR (None, None) if failed.
    """
    target = query if query else "General Tech Seeds"
    print(f"--- 1. Sourcing data from Google Trends (Target: {target}) ---")

    try:
        # 1. Initialize Pytrends with strict timeout settings
        # This prevents the script from hanging if Google blocks the IP.
        pytrends = TrendReq(
            hl='en-US',
            tz=360,
            timeout=(5, TRENDS_TIMEOUT),
            retries=2,
            backoff_factor=1
        )
        
        # --- PATH A: Specific Niche Query (from main.py) ---
        if query:
            print(f"  -> Searching trends for specific niche: '{query}'")
            pytrends.build_payload([query], timeframe='now 7-d')
            related_queries = pytrends.related_queries()
            
            # Check if we got valid data for this query
            if related_queries and query in related_queries:
                rising_df = related_queries[query]['rising']
                top_df = related_queries[query]['top']
                
                # Priority 1: Rising queries (Breakout trends)
                if rising_df is not None and not rising_df.empty:
                    trend_row = rising_df.sample().iloc[0]
                    trend_name = trend_row['query']
                    print(f"  -> Found rising trend: {trend_name}")
                    return trend_name, [f"Rising trend related to {query}", "Current market interest"]
                
                # Priority 2: Top queries (Consistent interest)
                elif top_df is not None and not top_df.empty:
                    trend_row = top_df.head(5).sample().iloc[0]
                    trend_name = trend_row['query']
                    print(f"  -> Found top trend: {trend_name}")
                    return trend_name, [f"Popular search related to {query}", "High search volume topic"]
            
            print("  -> No specific trends found for this niche. Falling back...")

        # --- PATH B: General Seed Keywords (Backup) ---
        # If no query provided, OR if specific query returned no results:
        print("  -> Checking general seed keywords for trends...")
        all_rising_queries = []
        
        for seed in SEED_KEYWORDS:
            try:
                pytrends.build_payload([seed], timeframe='now 7-d')
                related = pytrends.related_queries()
                if seed in related and 'rising' in related[seed]:
                    r_df = related[seed]['rising']
                    if r_df is not None and not r_df.empty:
                        all_rising_queries.extend(r_df['query'].tolist())
            except Exception:
                continue # Skip this seed if it fails, try the next
        
        if all_rising_queries:
            # Pick a random trend from the list
            selected_topic = random.choice(list(set(all_rising_queries)))
            print(f"-> Selected General Trend: {selected_topic}")
            return selected_topic, ["Tech industry trend", "Rising interest"]

    except Exception as e:
        # --- CRITICAL SAFETY NET ---
        # Catches 429 (Too Many Requests) and ConnectTimeout errors.
        # Returns None so main.py can use the Educational Fallback instead of crashing.
        print(f"  -> Google Trends Error (Likely blocked or timed out): {e}")
        print("  -> Skipping Trends. Engaging Fallback Protocol.")
        return None, None

    print("  -> No trends found.")
    return None, None
