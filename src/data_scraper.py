"""
data_scraper.py - Enhanced data scraper with multiple fallback strategies.

Replaces the fragile pytrends-only approach with a robust multi-source strategy:
1. First try: Google Trends via pytrends
2. Second try: RSS News feeds (feeds from multiple sources)
3. Third try: Static niche-based fallback (always works)
"""

import time
import random
import feedparser
import requests
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)

# Increase the default connection timeout for better stability
TRENDS_TIMEOUT = 10

# Use a seed list of general high-level topics to find breakout trends within them.
# This serves as a backup if no specific niche query is provided.
SEED_KEYWORDS = ['AI technology', 'software development', 'cloud computing', 'cybersecurity', 
                 'virtual assistants', 'automation tools', 'remote work', 'business outsourcing']

# RSS feeds for reliable trending news (tech and business)
RSS_FEEDS = [
    'http://feeds.feedburner.com/TechCrunch',
    'https://www.wired.com/feed/rss',
    'https://feeds.hbr.org/harvardbusiness',
    'https://www.fastcompany.com/feed',
    'https://www.forbes.com/business/feed/',
    'https://feeds.feedburner.com/venturebeat/SZYF',
    'https://rss.cnn.com/rss/edition.rss',
    'https://feeds.bbci.co.uk/news/technology/rss.xml',
]

# Cache to avoid hitting RSS feeds too often
_cache = {}
_cache_timestamp = None
_CACHE_DURATION = 300  # 5 minutes


def _get_cached_or_fetch():
    """Fetch RSS feeds with caching."""
    global _cache, _cache_timestamp
    
    now = datetime.now()
    if _cache_timestamp and (now - _cache_timestamp).seconds < _CACHE_DURATION:
        if _cache:
            return _cache
    
    # Fetch fresh data
    all_entries = []
    for feed_url in RSS_FEEDS:
        try:
            resp = requests.get(feed_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            if resp.status_code == 200:
                feed_data = feedparser.parse(resp.content)
                all_entries.extend(feed_data.get('entries', []))
        except Exception as e:
            logger.debug(f"Failed to fetch RSS feed {feed_url}: {e}")
            continue
    
    _cache = all_entries
    _cache_timestamp = now
    return all_entries


def _extract_keywords_from_text(text: str, max_keywords=5) -> List[str]:
    """Extract meaningful keywords from text using simple NLP."""
    # Simple keyword extraction - in production, use NLP libraries
    words = text.lower().replace(',', '').replace('.', '').replace('?', '').split()
    # Filter out common words
    stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 
                 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                 'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                 'can', 'need', 'must', 'ought', 'about', 'above', 'across',
                 'after', 'against', 'along', 'among', 'around', 'at', 'before',
                 'behind', 'below', 'beneath', 'beside', 'between', 'beyond',
                 'but', 'by', 'concerning', 'considering', 'despite', 'down',
                 'during', 'except', 'following', 'for', 'from', 'in', 'inside',
                 'into', 'like', 'minus', 'near', 'of', 'off', 'on', 'onto',
                 'opposite', 'out', 'outside', 'over', 'past', 'per', 'plus',
                 'regarding', 'round', 'save', 'since', 'than', 'through',
                 'throughout', 'till', 'to', 'toward', 'towards', 'under',
                 'underneath', 'unlike', 'until', 'up', 'upon', 'versus',
                 'via', 'with', 'within', 'without', 'and', 'or', 'if',
                 'then', 'else', 'when', 'where', 'why', 'how', 'all',
                 'any', 'both', 'each', 'few', 'more', 'most', 'other',
                 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
                 'same', 'so', 'than', 'too', 'very', 'just', 'now'}
    
    filtered = [w for w in words if len(w) > 3 and w not in stopwords]
    
    # Get top words by frequency
    freq = {}
    for w in filtered:
        freq[w] = freq.get(w, 0) + 1
    
    sorted_words = sorted(freq.items(), key=lambda x: -x[1])
    return [w[0] for w in sorted_words[:max_keywords]]


def get_trending_topic_rss(query=None) -> Tuple[Optional[str], List[str]]:
    """
    Get trending topic from RSS feeds.
    
    Returns:
        tuple: (topic_title, list_of_context_points)
    """
    print(f"--- [RSS FALLBACK] Sourcing data from RSS feeds ---")
    
    try:
        entries = _get_cached_or_fetch()
        if not entries:
            print("  -> No RSS entries found.")
            return None, None
        
        # Filter entries if query provided
        if query:
            query_lower = query.lower()
            filtered = [e for e in entries if query_lower in e.get('title', '').lower() or 
                        query_lower in e.get('summary', '').lower()]
            if filtered:
                entries = filtered
        
        # Pick a random recent entry
        entry = random.choice(entries)
        title = entry.get('title', '').strip()
        summary = entry.get('summary', '') or entry.get('description', '')
        
        if not title:
            return None, None
        
        print(f"  -> Found RSS trend: {title}")
        
        # Extract keywords for context
        keywords = _extract_keywords_from_text(f"{title} {summary}", max_keywords=5)
        context = [f"Trending topic: {kw}" for kw in keywords[:3]]
        
        return title, context
    
    except Exception as e:
        print(f"  -> RSS Error: {e}")
        return None, None


def get_trending_topic_google(query=None):
    """
    Attempts to fetch a trending topic from Google Trends using pytrends.
    
    Args:
        query (str, optional): A specific keyword to search for (e.g., "Medical VA").
                               If None, searches for general tech trends using SEED_KEYWORDS.
    
    Returns:
        tuple: (topic_title, list_of_context_points) OR (None, None) if failed.
    """
    target = query if query else "General Tech Seeds"
    print(f"--- 1. Sourcing data from Google Trends (Target: {target}) ---")

    try:
        from pytrends.request import TrendReq
        
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

    except ImportError:
        print("  -> pytrends not installed. Skipping Google Trends.")
        return None, None
    except Exception as e:
        # --- CRITICAL SAFETY NET ---
        # Catches 429 (Too Many Requests) and ConnectTimeout errors.
        print(f"  -> Google Trends Error (Likely blocked or timed out): {e}")
        print("  -> Skipping Trends. Engaging RSS Fallback.")
        return None, None

    print("  -> No trends found.")
    return None, None


def get_trending_topic(query=None) -> Tuple[Optional[str], List[str]]:
    """
    Enhanced trending topic fetcher with multiple fallback strategies.
    
    Strategy:
    1. Try Google Trends (pytrends)
    2. If that fails, try RSS News feeds
    3. If all fails, return None (main.py will use niche fallback)
    
    Args:
        query (str, optional): A specific keyword to search for.
    
    Returns:
        tuple: (topic_title, list_of_context_points) OR (None, None)
    """
    # Strategy 1: Google Trends
    result = get_trending_topic_google(query)
    if result and result[0]:
        return result
    
    # Strategy 2: RSS Feeds
    print("--- [Fallback] Sourcing data from RSS Feeds ---")
    rss_result = get_trending_topic_rss(query)
    if rss_result and rss_result[0]:
        return rss_result
    
    # Strategy 3: Return None (main.py will handle with niche fallback)
    print("  -> All trending sources exhausted. Using niche fallback.")
    return None, None