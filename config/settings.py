"""
config/settings.py - Centralized configuration for the autoblog system.

All settings are loaded from environment variables with sensible defaults.
No hardcoded API keys or sensitive values should exist here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ---------------------------------------------------------------------------
# Base paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
SRC_DIR = BASE_DIR / "src"
CONFIG_DIR = BASE_DIR / "config"

# ---------------------------------------------------------------------------
# LLM Configuration (OpenAI)
# ---------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "4000"))

# ---------------------------------------------------------------------------
# LLM Configuration (Gemini - for images and fallback text)
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

# ---------------------------------------------------------------------------
# Sanity CMS Configuration
# ---------------------------------------------------------------------------
SANITY_PROJECT_ID = os.getenv("SANITY_PROJECT_ID")
SANITY_DATASET = os.getenv("SANITY_DATASET", "production")
SANITY_WRITE_TOKEN = os.getenv("SANITY_WRITE_TOKEN")

# Build the Sanity API URL
SANITY_API_URL = f"https://{SANITY_PROJECT_ID}.api.sanity.io/v1/data/mutate/{SANITY_DATASET}"

# Sanity CDN URL for assets
SANITY_CDN_URL = f"https://cdn.sanity.io/images/{SANITY_PROJECT_ID}/{SANITY_DATASET}"

# ---------------------------------------------------------------------------
# Deployment
# ---------------------------------------------------------------------------
DEPLOYMENT_WEBHOOK_URL = os.getenv("DEPLOYMENT_WEBHOOK_URL")

# ---------------------------------------------------------------------------
# Image Generation Settings
# ---------------------------------------------------------------------------
DEFAULT_IMAGE_OUTPUT_DIR = os.getenv("IMAGE_OUTPUT_DIR", "generated_images")
MAX_PARALLEL_IMAGES = int(os.getenv("MAX_PARALLEL_IMAGES", "3"))
IMAGE_ENHANCEMENT_ENABLED = os.getenv("IMAGE_ENHANCEMENT", "true").lower() == "true"

# ---------------------------------------------------------------------------
# Content Generation Settings
# ---------------------------------------------------------------------------
MIN_SECTIONS = int(os.getenv("MIN_SECTIONS", "4"))
MIN_SECTION_IMAGES = int(os.getenv("MIN_SECTION_IMAGES", "2"))
DEFAULT_READING_TIME = int(os.getenv("DEFAULT_READING_TIME", "5"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ---------------------------------------------------------------------------
# Author & Website Info
# ---------------------------------------------------------------------------
AUTHOR = {
    "name": os.getenv("AUTHOR_NAME", "Joseph Henry"),
    "title": os.getenv("AUTHOR_TITLE", "Founder, GlideX Outsourcing"),
    "linkedin": os.getenv("AUTHOR_LINKEDIN", "https://www.linkedin.com/in/joseph-henry-280b4b121"),
    "email": os.getenv("AUTHOR_EMAIL", "jhenry@glidexoutsourcing.com"),
    "slug": "autoblog-ai"
}

SITE_INFO = {
    "name": os.getenv("SITE_NAME", "GlideX Outsourcing"),
    "url": os.getenv("SITE_URL", "https://www.glidexoutsourcing.com"),
    "blog_path": "/blog",
    "calendly_url": os.getenv("CALENDLY_URL", "https://calendly.com/glide-xpp/30min"),
    "logo": "/logo.png"
}

# ---------------------------------------------------------------------------
# SEO Defaults
# ---------------------------------------------------------------------------
SEO_DEFAULTS = {
    "max_meta_title_length": int(os.getenv("MAX_META_TITLE_LENGTH", "60")),
    "max_meta_description_length": int(os.getenv("MAX_META_DESCRIPTION_LENGTH", "160")),
    "max_keywords": int(os.getenv("MAX_KEYWORDS", "6")),
    "reading_speed_wpm": int(os.getenv("READING_SPEED_WPM", "200"))
}

# ---------------------------------------------------------------------------
# Content Niche Fallbacks
# ---------------------------------------------------------------------------
NICHE_DETAILS = {
    "Medical Virtual Assistants": [
        "Appointment Scheduling & Calendar Management",
        "Medical Coding and Billing Support",
        "Patient Intake and Triage",
        "EMR/EHR Management for Private Practices",
        "Handling Insurance Verifications"
    ],
    "Voice Automation AI": [
        "Handling Inbound Customer Support 24/7",
        "Automating Appointment Reminders",
        "Lead Qualification via Voice AI",
        "Replacing Traditional Call Centers"
    ],
    "Real Estate Virtual Assistants": [
        "Cold Calling and Lead Generation",
        "Managing Property Listings",
        "CRM Data Entry and Maintenance",
        "Coordinating Showings for Realtors"
    ],
    "Executive Virtual Assistants": [
        "Inbox Zero and Email Management",
        "Travel Planning and Itinerary Management",
        "Meeting Minute Taking and Organization",
        "Personal Lifestyle Management for CEOs"
    ]
}

# ---------------------------------------------------------------------------
# Sanity Post Document Template
# ---------------------------------------------------------------------------
def get_post_document_template(title: str, slug: str, body_portable_text: list, author_id: str = AUTHOR["slug"]):
    """
    Returns a Sanity document structure ready for submission.
    'body_portable_text' must be an array of Portable Text blocks.
    """
    import datetime
    
    current_time_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    return {
        "_type": "post",
        "title": title,
        "slug": {"_type": "slug", "current": slug},
        "author": {"_type": "reference", "_ref": author_id},
        "mainImage": None,
        "categories": [],
        "publishedAt": current_time_utc,
        "body": body_portable_text
    }

# ---------------------------------------------------------------------------
# Environment Validation
# ---------------------------------------------------------------------------
def validate_environment():
    """Validate that required environment variables are set."""
    required_vars = {
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "SANITY_PROJECT_ID": SANITY_PROJECT_ID,
        "SANITY_WRITE_TOKEN": SANITY_WRITE_TOKEN,
    }
    
    missing = [name for name, value in required_vars.items() if not value]
    
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Please set them in your .env file."
        )