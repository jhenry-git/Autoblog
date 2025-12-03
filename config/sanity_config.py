import os
from dotenv import load_dotenv
import datetime # NEW: Import datetime

# Load environment variables from .env file
load_dotenv()

# --- Sanity.io Configuration ---
SANITY_PROJECT_ID = os.getenv("SANITY_PROJECT_ID")
SANITY_DATASET = os.getenv("SANITY_DATASET")
SANITY_WRITE_TOKEN = os.getenv("SANITY_WRITE_TOKEN")
# URL to your Sanity project's API endpoint (for mutations)
SANITY_API_URL = f"https://{SANITY_PROJECT_ID}.api.sanity.io/v1/data/mutate/{SANITY_DATASET}"

# --- Other Configurations ---
# Renamed from OPENAI_API_KEY to GEMINI_API_KEY
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEPLOYMENT_WEBHOOK_URL = os.getenv("DEPLOYMENT_WEBHOOK_URL")

# Define the structure of a new blog post document
def get_post_document_template(title, slug, body_portable_text, author_id="ai-bot"):
    """
    Returns a Sanity document structure ready for submission.
    'body_portable_text' must be an array of Portable Text blocks.
    """
    # Generate the current UTC timestamp in ISO 8601 format
    current_time_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    return {
        "_type": "post",
        "title": title,
        "slug": {"_type": "slug", "current": slug},
        "author": {"_type": "reference", "_ref": author_id},
        "mainImage": None,
        "categories": [],
        "publishedAt": current_time_utc, # FIXED: Using the accurate current timestamp
        "body": body_portable_text
    }

# NOTE: The "body" field expects Sanity Portable Text (an array of block objects),
# not raw Markdown. The content_generator.py will need to handle this conversion.
